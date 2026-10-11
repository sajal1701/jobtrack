"""FastAPI entry point. Run with: python -m uvicorn jobtrack.api:app."""

from contextlib import asynccontextmanager
from datetime import date
import csv
from io import StringIO
import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import store

ROOT = Path(__file__).resolve().parent.parent
Status = Literal["saved", "applied", "interview", "offer", "rejected"]


class ApplicationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: str = Field(min_length=1, max_length=150)
    role: str = Field(min_length=1, max_length=200)
    status: Status = "saved"
    url: str = Field(default="", max_length=2000)
    notes: str = Field(default="", max_length=5000)
    follow_up_date: date | None = None

    @field_validator("company", "role")
    @classmethod
    def meaningful_text(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank.")
        return value

    @field_validator("url")
    @classmethod
    def web_url(cls, value: str):
        value = value.strip()
        parts = urlsplit(value)
        if value and (parts.scheme not in {"http", "https"} or not parts.hostname):
            raise ValueError("Use a complete http or https URL.")
        return value


class ApplicationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Status | None = None
    notes: str | None = Field(default=None, max_length=5000)
    follow_up_date: date | None = None

    @model_validator(mode="before")
    @classmethod
    def non_nullable_fields(cls, value):
        if isinstance(value, dict):
            for key in ("status", "notes"):
                if key in value and value[key] is None:
                    raise ValueError(f"{key} cannot be null.")
        return value


def create_app(db_path: str | Path | None = None) -> FastAPI:
    database = Path(db_path or os.environ.get("JOBTRACK_DB", ROOT / ".data/jobtrack.sqlite3"))

    @asynccontextmanager
    async def lifespan(_app):
        store.initialize(database)
        yield

    application = FastAPI(title="JobTrack", version="0.1.0", lifespan=lifespan)
    application.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")

    @application.get("/", include_in_schema=False)
    def home():
        return FileResponse(ROOT / "web/index.html")

    @application.get("/api/health")
    def health():
        return {"status": "ok"}

    @application.get("/api/applications")
    def applications(search: str = Query(default="", max_length=200), status: Status | None = None,
                     limit: int = Query(default=100, ge=1, le=100), offset: int = Query(default=0, ge=0)):
        return store.list_applications(database, search.strip(), status, limit, offset)

    @application.post("/api/applications", status_code=201)
    def add_application(payload: ApplicationInput):
        return store.create_application(database, payload.model_dump(mode="json"))

    @application.get("/api/applications/export")
    def export_applications(search: str = Query(default="", max_length=200), status: Status | None = None):
        records = store.list_applications(database, search.strip(), status, limit=None)
        output = StringIO(newline="")
        fields = ["id", "company", "role", "status", "url", "notes", "follow_up_date", "created_at", "updated_at"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
        return Response(output.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="jobtrack-applications.csv"'})

    @application.get("/api/applications/{application_id}")
    def get_application(application_id: int):
        result = store.get_application(database, application_id)
        if result is None:
            raise HTTPException(404, "Application not found.")
        return result

    @application.patch("/api/applications/{application_id}")
    def update(application_id: int, payload: ApplicationPatch):
        changes = payload.model_dump(mode="json", exclude_unset=True)
        if not changes:
            raise HTTPException(400, "Provide at least one field to update.")
        result = store.update_application(database, application_id, changes)
        if result is None:
            raise HTTPException(404, "Application not found.")
        return result

    @application.delete("/api/applications/{application_id}", status_code=204)
    def remove(application_id: int):
        if not store.delete_application(database, application_id):
            raise HTTPException(404, "Application not found.")
        return Response(status_code=204)

    @application.get("/api/stats")
    def stats():
        return store.statistics(database)

    return application


app = create_app()

"""FastAPI entry point. Run with: python -m uvicorn jobtrack.api:app."""

from contextlib import asynccontextmanager
from datetime import date
import csv
from io import StringIO
import os
import secrets
import time
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from . import auth, store

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


class ApplicationPatch(ApplicationInput):
    # Inherit creation validators, but distinguish omitted fields from updates.
    company: str | None = Field(default=None, min_length=1, max_length=150)
    role: str | None = Field(default=None, min_length=1, max_length=200)
    url: str | None = Field(default=None, max_length=2000)
    status: Status | None = None
    notes: str | None = Field(default=None, max_length=5000)
    follow_up_date: date | None = None

    @model_validator(mode="before")
    @classmethod
    def non_nullable_fields(cls, value):
        if isinstance(value, dict):
            for key in ("company", "role", "url", "status", "notes"):
                if key in value and value[key] is None:
                    raise ValueError(f"{key} cannot be null.")
        return value


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=12, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str):
        return value.lower()


def create_app(db_path: str | Path | None = None) -> FastAPI:
    database = Path(db_path or os.environ.get("JOBTRACK_DB", ROOT / ".data/jobtrack.sqlite3"))

    @asynccontextmanager
    async def lifespan(_app):
        store.initialize(database)
        yield

    application = FastAPI(title="JobTrack", version="0.1.0", lifespan=lifespan)
    application.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")

    secure_cookie = os.environ.get("JOBTRACK_SECURE_COOKIE", "0") == "1"

    @application.middleware("http")
    async def protect_requests(request: Request, call_next):
        if request.method in {"POST", "PATCH", "DELETE", "PUT"}:
            if request.headers.get("X-JobTrack") != "1":
                return Response("Missing request protection header.", status_code=403)
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return Response("Cross-origin request rejected.", status_code=403)
        if request.method == "POST" and request.url.path in {"/api/auth/login", "/api/auth/register"}:
            client = request.client.host if request.client else "unknown"
            if not store.allow_auth_attempt(database, client, int(time.time())):
                return Response("Too many sign-in attempts. Try again in a minute.", status_code=429,
                                headers={"Retry-After": "60", "Cache-Control": "no-store"})
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def current_user(request: Request):
        token = request.cookies.get("jobtrack_session", "")
        user = store.session_user(database, auth.token_hash(token), int(time.time()))
        if user is None:
            raise HTTPException(401, "Please sign in.")
        return user

    def start_session(response: Response, request: Request, user: dict):
        old_token = request.cookies.get("jobtrack_session", "")
        store.delete_session(database, auth.token_hash(old_token))
        token = secrets.token_urlsafe(32)
        store.save_session(database, auth.token_hash(token), user["id"], int(time.time()) + 86400)
        response.set_cookie("jobtrack_session", token, max_age=86400, httponly=True,
                            secure=secure_cookie, samesite="strict")
        return user

    @application.post("/api/auth/register", status_code=201)
    def register(payload: Credentials, response: Response, request: Request):
        user = store.create_user(database, payload.username, auth.hash_password(payload.password))
        if user is None:
            raise HTTPException(409, "Username unavailable.")
        return start_session(response, request, user)

    @application.post("/api/auth/login")
    def login(payload: Credentials, response: Response, request: Request):
        user = store.find_user(database, payload.username)
        # Perform the same expensive hash even when the username does not exist.
        encoded = user["password_hash"] if user else auth.DUMMY_PASSWORD_HASH
        if not auth.verify_password(payload.password, encoded) or user is None:
            raise HTTPException(401, "Invalid username or password.")
        return start_session(response, request, {"id": user["id"], "username": user["username"]})

    @application.get("/api/auth/me")
    def me(user: dict = Depends(current_user)):
        return user

    @application.post("/api/auth/logout", status_code=204)
    def logout(request: Request):
        store.delete_session(database, auth.token_hash(request.cookies.get("jobtrack_session", "")))
        response = Response(status_code=204)
        response.delete_cookie("jobtrack_session", httponly=True, secure=secure_cookie, samesite="strict")
        return response

    @application.get("/", include_in_schema=False)
    def home():
        return FileResponse(ROOT / "web/index.html")

    @application.get("/api/health")
    def health():
        return {"status": "ok"}

    @application.get("/api/applications")
    def applications(search: str = Query(default="", max_length=200), status: Status | None = None,
                     limit: int = Query(default=100, ge=1, le=100), offset: int = Query(default=0, ge=0), user: dict = Depends(current_user)):
        return store.list_applications(database, search.strip(), status, limit, offset, owner_id=user["id"])

    @application.post("/api/applications", status_code=201)
    def add_application(payload: ApplicationInput, user: dict = Depends(current_user)):
        return store.create_application(database, payload.model_dump(mode="json"), user["id"])

    @application.get("/api/applications/export")
    def export_applications(search: str = Query(default="", max_length=200), status: Status | None = None, user: dict = Depends(current_user)):
        records = store.list_applications(database, search.strip(), status, limit=None, owner_id=user["id"])
        output = StringIO(newline="")
        fields = ["id", "company", "role", "status", "url", "notes", "follow_up_date", "created_at", "updated_at"]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
        return Response(output.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="jobtrack-applications.csv"'})

    @application.get("/api/applications/{application_id}")
    def get_application(application_id: int, user: dict = Depends(current_user)):
        result = store.get_application(database, application_id, user["id"])
        if result is None:
            raise HTTPException(404, "Application not found.")
        return result

    @application.patch("/api/applications/{application_id}")
    def update(application_id: int, payload: ApplicationPatch, user: dict = Depends(current_user)):
        changes = payload.model_dump(mode="json", exclude_unset=True)
        if not changes:
            raise HTTPException(400, "Provide at least one field to update.")
        result = store.update_application(database, application_id, changes, user["id"])
        if result is None:
            raise HTTPException(404, "Application not found.")
        return result

    @application.delete("/api/applications/{application_id}", status_code=204)
    def remove(application_id: int, user: dict = Depends(current_user)):
        if not store.delete_application(database, application_id, user["id"]):
            raise HTTPException(404, "Application not found.")
        return Response(status_code=204)

    @application.get("/api/stats")
    def stats(user: dict = Depends(current_user)):
        return store.statistics(database, user["id"])

    return application


app = create_app()

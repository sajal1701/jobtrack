import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from jobtrack.api import create_app


class JobTrackTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "jobs.sqlite3"
        self.client = TestClient(create_app(self.path))
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.directory.cleanup()

    def add(self, **changes):
        payload = {"company": "Example Labs", "role": "Junior Engineer", **changes}
        response = self.client.post("/api/applications", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_create_and_read(self):
        item = self.add(company="  Example Labs  ", follow_up_date="2026-10-20")
        self.assertEqual(item["company"], "Example Labs")
        self.assertEqual(item["status"], "saved")
        self.assertEqual(self.client.get(f"/api/applications/{item['id']}").json(), item)

    def test_state_change_updates_statistics(self):
        item = self.add()
        response = self.client.patch(f"/api/applications/{item['id']}", json={"status": "interview"})
        self.assertEqual(response.status_code, 200)
        stats = self.client.get("/api/stats").json()
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["by_status"]["saved"], 0)
        self.assertEqual(stats["by_status"]["interview"], 1)

    def test_filter_and_search(self):
        self.add(company="Example Labs", status="applied")
        self.add(company="Other Company", role="Data Analyst")
        results = self.client.get("/api/applications", params={"search": "LABS", "status": "applied"}).json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["company"], "Example Labs")

    def test_search_wildcards_are_literal(self):
        self.add(company="100% Labs")
        self.add(company="Other Labs")
        self.assertEqual(len(self.client.get("/api/applications", params={"search": "%"}).json()), 1)

    def test_sql_text_is_data(self):
        self.add(company="Robert'); DROP TABLE applications;--")
        self.add()
        self.assertEqual(self.client.get("/api/stats").json()["total"], 2)

    def test_validation_rejects_invalid_fields(self):
        for changes in ({"company": "   "}, {"status": "fake"}, {"url": "javascript:alert(1)"},
                        {"follow_up_date": "2026-02-31"}, {"surprise": "extra"}):
            with self.subTest(changes=changes):
                response = self.client.post("/api/applications", json={"company": "A", "role": "B", **changes})
                self.assertEqual(response.status_code, 422)

    def test_patch_is_partial_and_can_clear_date(self):
        item = self.add(notes="Old notes", follow_up_date="2026-10-20")
        updated = self.client.patch(f"/api/applications/{item['id']}", json={"notes": "New notes", "follow_up_date": None}).json()
        self.assertEqual(updated["notes"], "New notes")
        self.assertEqual(updated["status"], "saved")
        self.assertIsNone(updated["follow_up_date"])

    def test_empty_or_null_patch_rejected(self):
        item = self.add()
        self.assertEqual(self.client.patch(f"/api/applications/{item['id']}", json={}).status_code, 400)
        self.assertEqual(self.client.patch(f"/api/applications/{item['id']}", json={"status": None}).status_code, 422)

    def test_delete_and_missing_records(self):
        item = self.add()
        endpoint = f"/api/applications/{item['id']}"
        self.assertEqual(self.client.delete(endpoint).status_code, 204)
        self.assertEqual(self.client.get(endpoint).status_code, 404)
        self.assertEqual(self.client.delete(endpoint).status_code, 404)
        self.assertEqual(self.client.patch(endpoint, json={"status": "offer"}).status_code, 404)

    def test_pagination_has_stable_order(self):
        older = self.add(company="Older")
        newer = self.add(company="Newer")
        self.assertEqual(self.client.get("/api/applications?limit=1").json()[0]["id"], newer["id"])
        self.assertEqual(self.client.get("/api/applications?limit=1&offset=1").json()[0]["id"], older["id"])
        self.assertEqual(self.client.get("/api/applications?limit=0").status_code, 422)

    def test_persistence_survives_new_app(self):
        item = self.add()
        with TestClient(create_app(self.path)) as another:
            self.assertEqual(another.get(f"/api/applications/{item['id']}").json()["company"], "Example Labs")

    def test_frontend_and_health(self):
        self.assertEqual(self.client.get("/api/health").json(), {"status": "ok"})
        self.assertIn("JobTrack", self.client.get("/").text)
        self.assertEqual(self.client.get("/static/app.js").status_code, 200)


if __name__ == "__main__":
    unittest.main()

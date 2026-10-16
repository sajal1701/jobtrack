import csv
from io import StringIO
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from jobtrack.api import create_app
from jobtrack import auth, store


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "auth.sqlite3"
        self.client = TestClient(create_app(self.path))
        self.client.__enter__()
        self.client.headers["X-JobTrack"] = "1"

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.directory.cleanup()

    def register(self, username="alice"):
        response = self.client.post("/api/auth/register", json={"username": username, "password": "a-long-test-password"})
        self.assertEqual(response.status_code, 201, response.text)
        return response

    def test_registration_hashing_login_logout_and_rotation(self):
        response = self.register("Alice")
        self.assertEqual(response.json()["username"], "alice")
        self.assertNotIn("password", response.text)
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=strict", cookie)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 200)
        old_token = self.client.cookies.get("jobtrack_session")
        with store.connection(self.path) as db:
            encoded = db.execute("SELECT password_hash FROM users").fetchone()[0]
            stored_token = db.execute("SELECT token_hash FROM sessions").fetchone()[0]
        self.assertTrue(encoded.startswith("scrypt$"))
        self.assertNotIn("a-long-test-password", encoded)
        self.assertNotEqual(old_token, stored_token)
        self.assertTrue(auth.verify_password("a-long-test-password", encoded))
        self.assertNotEqual(auth.hash_password("a-long-test-password"), encoded)
        login = self.client.post("/api/auth/login", json={"username": "ALICE", "password": "a-long-test-password"})
        self.assertEqual(login.status_code, 200)
        self.assertNotEqual(old_token, self.client.cookies.get("jobtrack_session"))
        self.assertIsNone(store.session_user(self.path, auth.token_hash(old_token), int(time.time())))
        token = self.client.cookies.get("jobtrack_session")
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.client.cookies.set("jobtrack_session", token)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_credentials_validation_duplicate_and_failed_login(self):
        self.register()
        duplicate = self.client.post("/api/auth/register", json={"username": "ALICE", "password": "a-long-test-password"})
        self.assertEqual(duplicate.status_code, 409)
        for username in ("alice", "missing"):
            response = self.client.post("/api/auth/login", json={"username": username, "password": "wrong-password-long"})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Invalid username or password.")
        for payload in ({"username": "aa", "password": "a-long-test-password"},
                        {"username": "space name", "password": "a-long-test-password"},
                        {"username": "bob", "password": "short"},
                        {"username": "bob", "password": "x" * 129}):
            self.assertEqual(self.client.post("/api/auth/register", json=payload).status_code, 422)

    def test_unauthenticated_routes_and_expired_sessions(self):
        for method, endpoint, payload in (
            ("GET", "/api/applications", None), ("GET", "/api/applications/export", None),
            ("GET", "/api/stats", None), ("GET", "/api/applications/1", None),
            ("POST", "/api/applications", {"company": "A", "role": "B"}),
            ("PATCH", "/api/applications/1", {"status": "offer"}),
            ("DELETE", "/api/applications/1", None)):
            self.assertEqual(self.client.request(method, endpoint, json=payload).status_code, 401)
        self.register()
        with store.connection(self.path) as db:
            db.execute("UPDATE sessions SET expires_at = ?", (int(time.time()) - 1,))
        self.assertEqual(self.client.get("/api/applications").status_code, 401)
        self.client.cookies.set("jobtrack_session", "forged")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_accounts_cannot_access_each_others_records(self):
        self.register()
        item = self.client.post("/api/applications", json={"company": "Alice Co", "role": "Engineer"}).json()
        self.client.post("/api/auth/logout")
        self.register("bob")
        self.client.post("/api/applications", json={"company": "Bob Co", "role": "Designer"})
        self.assertEqual([row["company"] for row in self.client.get("/api/applications").json()], ["Bob Co"])
        self.assertEqual(self.client.get("/api/stats").json()["total"], 1)
        rows = list(csv.DictReader(StringIO(self.client.get("/api/applications/export").text)))
        self.assertEqual([row["company"] for row in rows], ["Bob Co"])
        self.assertEqual(self.client.post("/api/applications", json={
            "company": "Forged", "role": "Engineer", "owner_id": 1,
        }).status_code, 422)
        endpoint = f"/api/applications/{item['id']}"
        self.assertEqual(self.client.get(endpoint).status_code, 404)
        self.assertEqual(self.client.patch(endpoint, json={"status": "offer"}).status_code, 404)
        self.assertEqual(self.client.patch(endpoint, json={"company": "Stolen", "role": "Changed", "url": "https://example.com"}).status_code, 404)
        self.assertEqual(self.client.delete(endpoint).status_code, 404)
        self.client.post("/api/auth/login", json={"username": "alice", "password": "a-long-test-password"})
        self.assertEqual(self.client.get(endpoint).json(), item)

    def test_mutations_require_protection_and_reject_foreign_origins(self):
        self.client.headers.pop("X-JobTrack")
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 403)
        self.client.headers["X-JobTrack"] = "1"
        self.assertEqual(self.client.post("/api/auth/logout", headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.post("/api/auth/logout", headers={"Origin": "http://testserver"}).status_code, 204)

    def test_legacy_records_preserved_and_not_claimed_by_registration(self):
        legacy = Path(self.directory.name) / "legacy.sqlite3"
        # Build the schema used before account ownership was introduced.
        with store.connection(legacy) as db:
            db.execute("CREATE TABLE applications (id INTEGER PRIMARY KEY, company TEXT, role TEXT, status TEXT, url TEXT, notes TEXT, follow_up_date TEXT, created_at TEXT, updated_at TEXT)")
            db.execute("INSERT INTO applications VALUES (1, 'Private Co', 'Engineer', 'saved', '', '', NULL, '', '')")
        with TestClient(create_app(legacy)) as client:
            client.headers["X-JobTrack"] = "1"
            client.post("/api/auth/register", json={"username": "newuser", "password": "a-long-test-password"})
            self.assertEqual(client.get("/api/applications").json(), [])
            self.assertEqual(client.get("/api/applications/1").status_code, 404)
        store.initialize(legacy)
        with store.connection(legacy) as db:
            self.assertEqual([tuple(row) for row in db.execute("SELECT company, owner_id FROM applications")], [("Private Co", None)])

    def test_session_survives_app_restart(self):
        self.register()
        with TestClient(create_app(self.path)) as another:
            another.cookies.update(self.client.cookies)
            response = another.get("/api/auth/me")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["username"], "alice")
            self.assertEqual(response.headers["cache-control"], "no-store")

    def test_throttle_resets_after_window(self):
        now = int(time.time())
        for _ in range(20):
            self.assertTrue(store.allow_auth_attempt(self.path, "testclient", now))
        response = self.client.post("/api/auth/login", json={"username": "alice", "password": "a-long-test-password"})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "60")
        self.assertTrue(store.allow_auth_attempt(self.path, "testclient", now + 60))

    def test_legacy_claim_requires_existing_user_and_preserves_ownership(self):
        self.register()
        with store.connection(self.path) as db:
            db.execute("INSERT INTO applications (company, role, status, created_at, updated_at) VALUES ('Legacy', 'Engineer', 'saved', '', '')")
        with self.assertRaises(ValueError):
            store.claim_legacy_applications(self.path, "missing")
        self.assertEqual(store.claim_legacy_applications(self.path, "alice"), 1)
        self.assertEqual(self.client.get("/api/applications").json()[0]["company"], "Legacy")
        self.register("bob")
        self.assertEqual(store.claim_legacy_applications(self.path, "bob"), 0)
        self.assertEqual(self.client.get("/api/applications").json(), [])

    def test_secure_cookie_configuration(self):
        from unittest.mock import patch
        with patch.dict("os.environ", {"JOBTRACK_SECURE_COOKIE": "1"}):
            with TestClient(create_app(Path(self.directory.name) / "secure.sqlite3"), base_url="https://testserver") as client:
                response = client.post("/api/auth/register", headers={"X-JobTrack": "1"}, json={"username": "secure", "password": "a-long-test-password"})
                self.assertIn("Secure", response.headers["set-cookie"])
                self.assertEqual(client.get("/api/auth/me").status_code, 200)

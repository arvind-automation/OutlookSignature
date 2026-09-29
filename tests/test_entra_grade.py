import unittest
from unittest.mock import Mock, patch

import requests

from app import create_app
from app.config import Config
from app.extensions import db
from app.grades import GRADE_CONFIG, get_allowed_team
from app.microsoft_sso import fetch_graph_profile
from app.models import AuditLog, Organization, User


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    MICROSOFT_SSO_ENABLED = True
    LOCAL_DEV_LOGIN_ENABLED = False


def graph_response(payload=None, status=200):
    return Mock(ok=status == 200, status_code=status, text="mock response",
                json=Mock(return_value=payload))


class EntraGradeTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.logger.disabled = True
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        db.session.add(Organization(
            slug="arvind-gcc", label="Arvind GCC", organization="Arvind GCC",
            website="www.arvind.com", logo_path="assets/arvind-gcc-logo.png",
            watermark_path="assets/watermark-a.png",
        ))
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def user(self):
        return User.query.filter_by(email="test.user@arvind.in").one()

    def login(self, attributes=None, *, access_token="token", profile_status=200,
              manager=None):
        with self.client.session_transaction() as session:
            session.clear()
            session["ms_oauth_state"] = "state"
        profile = {
            "givenName": "Test", "surname": "User", "mail": "test.user@arvind.in",
            "jobTitle": "Engineer", "onPremisesExtensionAttributes": attributes,
        }
        token = {"id_token_claims": {"preferred_username": "test.user@arvind.in"},
                 "access_token": access_token}
        with patch("app.routes.auth_routes.exchange_code_for_token", return_value=token), \
             patch("app.microsoft_sso.requests.get", side_effect=[
                 graph_response(profile, profile_status),
                 manager or graph_response({"givenName": "Manager", "mail": "manager@arvind.in"}),
             ]) as get:
            response = self.client.get("/auth/microsoft/callback?state=state&code=code")
        return response, get

    def test_all_mapped_grades_are_accepted_and_locked(self):
        for grade in GRADE_CONFIG:
            with self.subTest(grade=grade):
                response, get = self.login({"extensionAttribute12": f" {grade.lower()} "})
                self.assertEqual(response.location, "/generator")
                self.assertEqual(self.user().grade, grade)
                self.assertEqual(self.user().grade_source, "entra")
                self.assertIn("onPremisesExtensionAttributes", get.call_args_list[0].kwargs["params"]["$select"])
                self.assertEqual(self.client.get("/api/signature").json["team"], get_allowed_team(grade))

    def test_invalid_values_clear_previous_grade_and_require_manual_selection(self):
        invalid = [None, {}, [], "malformed", {"extensionAttribute12": None},
                   {"extensionAttribute12": ""}, {"extensionAttribute12": "  "},
                   {"extensionAttribute12": "unknown"}, {"extensionAttribute12": 12},
                   {"extensionAttribute12": ["M1"]}, {"extensionAttribute12": {"grade": "M1"}}]
        for attributes in invalid:
            with self.subTest(attributes=attributes):
                self.login({"extensionAttribute12": "M1"})
                response, _ = self.login(attributes)
                self.assertEqual(response.location, "/grade")
                self.assertIsNone(self.user().grade)
                self.assertIsNone(self.user().grade_source)
                self.assertEqual(self.client.get("/grade").status_code, 200)
                self.assertEqual(self.client.get("/generator").location, "/grade")
                self.assertEqual(self.client.get("/api/signature").status_code, 409)
                self.assertEqual(self.client.post("/api/preview", json={}).status_code, 409)
                self.assertEqual(self.client.post("/api/signature", json={}).status_code, 409)

    def test_lock_persists_across_sessions_and_hides_both_links(self):
        self.login({"extensionAttribute12": "M1"})
        user_id = self.user().id
        with self.client.session_transaction() as session:
            session.clear()
            session["user_id"] = user_id
        for url in ("/grade", "/grade?change=1"):
            self.assertEqual(self.client.get(url).location, "/generator")
            self.assertEqual(self.client.post(url, data={"grade": "1|A"}).status_code, 403)
        self.assertEqual(self.user().grade, "M1")
        page = self.client.get("/generator")
        self.assertEqual(page.status_code, 200)
        self.assertNotIn(b"Change Grade", page.data)

    def test_manual_fallback_and_next_login_refresh(self):
        self.login()
        self.assertEqual(self.client.post("/grade", data={"grade": "unknown"}).status_code, 200)
        self.assertIsNone(self.user().grade)
        response = self.client.post("/grade", data={"grade": "3|B"})
        self.assertEqual(response.location, "/generator")
        self.assertEqual(self.user().grade_source, "manual")
        self.assertEqual(self.client.get("/generator").data.count(b"Change Grade"), 2)
        self.assertEqual(self.client.get("/api/signature").json["team"], "gcc")
        self.assertEqual(self.client.post("/api/signature", json={"form": {}}).status_code, 200)
        self.assertEqual(self.client.post("/api/preview", json={"form": {}}).status_code, 200)
        self.login()
        self.assertIsNone(self.user().grade)
        self.client.post("/grade", data={"grade": "3|B"})
        self.login({"extensionAttribute12": "M1"})
        self.assertEqual(self.user().grade, "M1")
        self.assertEqual(self.user().grade_source, "entra")

    def test_prefill_preserved_without_grade_and_audited(self):
        self.login({"extensionAttribute12": "M1"})
        with self.client.session_transaction() as session:
            prefill = session["profile_prefill"]
            self.assertEqual(prefill["firstName"], "Test")
            self.assertEqual(prefill["designation"], "Engineer")
            self.assertEqual(prefill["managerEmail"], "manager@arvind.in")
            self.assertNotIn("grade", prefill)
        self.assertEqual(AuditLog.query.filter_by(action="grade_synced").one().details,
                         {"grade": "M1", "source": "entra"})
        self.login({"extensionAttribute12": "PRIVATE-UNKNOWN-VALUE"})
        self.assertEqual(AuditLog.query.filter_by(action="grade_fallback").one().details,
                         {"reason": "unmapped"})

    def test_graph_failure_and_missing_token_fall_back(self):
        for kwargs in ({"profile_status": 403}, {"access_token": ""}):
            with self.subTest(kwargs=kwargs):
                self.login({"extensionAttribute12": "M1"})
                response, _ = self.login(**kwargs)
                self.assertEqual(response.location, "/grade")
                self.assertIsNone(self.user().grade)
        with patch("app.microsoft_sso.requests.get", side_effect=requests.Timeout):
            self.assertEqual(fetch_graph_profile("token"), {})
        with patch("app.routes.auth_routes.fetch_graph_profile", side_effect=requests.Timeout):
            response, _ = self.login()
        self.assertEqual(response.location, "/grade")

    def test_manager_failure_keeps_grade(self):
        for manager in (graph_response(status=403), requests.Timeout()):
            response, _ = self.login({"extensionAttribute12": "M1"}, manager=manager)
            self.assertEqual(response.location, "/generator")
            self.assertEqual(self.user().grade, "M1")

    def test_oauth_validation_and_unauthenticated_access(self):
        with patch("app.routes.auth_routes.exchange_code_for_token") as exchange:
            response = self.client.get("/auth/microsoft/callback?state=wrong&code=code")
            self.assertEqual(response.location, "/login")
            exchange.assert_not_called()
        self.assertEqual(User.query.count(), 0)
        self.assertEqual(self.client.get("/grade").location, "/login")
        self.assertEqual(self.client.post("/grade", data={"grade": "M1"}).location, "/login")

    def test_local_login_retains_manual_selection(self):
        self.app.config.update(MICROSOFT_SSO_ENABLED=False, LOCAL_DEV_LOGIN_ENABLED=True,
                               LOCAL_DEV_EMAIL="test.user@arvind.in")
        self.assertEqual(self.client.post("/auth/local").location, "/grade")
        self.assertIsNone(self.user().grade_source)
        self.client.post("/grade", data={"grade": "4|A"})
        self.assertEqual(self.user().grade_source, "manual")

    def test_existing_database_upgrade_is_idempotent(self):
        from init_db import ensure_user_columns

        columns = {"id", "email", "is_admin", "grade"}
        alterations = []

        def execute(statement):
            sql = str(statement)
            if sql.startswith("SELECT COLUMN_NAME"):
                return Mock(fetchall=Mock(return_value=[(name,) for name in columns]))
            alterations.append(sql)
            columns.add("grade_source")
            return Mock()

        with patch.object(db.session, "execute", side_effect=execute), \
             patch.object(db.session, "commit"):
            ensure_user_columns(self.app)
            ensure_user_columns(self.app)
        self.assertEqual(alterations, ["ALTER TABLE users ADD COLUMN grade_source VARCHAR(16) NULL"])


if __name__ == "__main__":
    unittest.main()

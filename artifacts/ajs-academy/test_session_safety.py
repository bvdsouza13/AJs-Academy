"""Isolated session tests; no real credentials, family data, or database writes."""
import copy
import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.applications import Starlette
from starlette.testclient import TestClient
from streamlit.testing.v1 import AppTest
import store
import secure_media


class SessionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.load = patch("store.load", side_effect=lambda: copy.deepcopy(store.DEFAULT))
        self.load.start()
        self.addCleanup(self.load.stop)
        self.app = AppTest.from_file(str(Path(__file__).with_name("app.py")))

    def signed_in(self, role="parent", page="Parent portal", age=0):
        self.app.session_state["role"] = role
        self.app.session_state["page"] = page
        self.app.session_state["last_active"] = store.now().timestamp() - age
        self.app.run(timeout=30)
        self.assertFalse(self.app.exception)

    def click(self, label):
        next(b for b in self.app.button if b.label == label).click().run(timeout=30)
        self.assertFalse(self.app.exception)

    def test_signed_out_cannot_load_family_state(self):
        self.app.run(timeout=30)
        self.assertFalse(self.app.exception)
        store.load.assert_not_called()
        self.assertFalse(self.app.text_input)
        self.assertFalse(self.app.radio)
        self.assertTrue(any(b.label == "Let’s Begin" for b in self.app.button))

    def test_parent_session_is_active_just_before_idle_timeout(self):
        self.signed_in(age=1799)
        self.assertEqual(self.app.session_state["role"], "parent")
        store.load.assert_called_once()

    def test_parent_session_expires_at_idle_timeout_before_loading_data(self):
        nonce = secure_media.new_session_nonce()
        secure_media.grant_session(nonce, "parent", time.time() + 60)
        self.app.session_state["media_session_nonce"] = nonce
        self.app.session_state["draft"] = "synthetic parent-only draft"
        self.signed_in(age=1800)
        store.load.assert_not_called()
        self.assertNotIn("role", self.app.session_state)
        self.assertNotIn("draft", self.app.session_state)
        self.assertNotIn(nonce, secure_media._sessions)
        self.assertTrue(any(b.label == "Let’s Begin" for b in self.app.button))

    def test_handoff_clears_parent_drafts_and_requires_reauthentication(self):
        self.app.session_state["draft"] = "synthetic parent-only draft"
        old_nonce = secure_media.new_session_nonce()
        secure_media.grant_session(old_nonce, "parent", time.time() + 60)
        old_url = secure_media.register(
            b"private parent video",
            "video/mp4",
            None,
            nonce=old_nonce,
            role="parent",
            allowed_roles=("parent",),
        )
        self.app.session_state["media_session_nonce"] = old_nonce
        self.signed_in()
        self.click("Switch to AJ’s view")
        self.assertEqual(self.app.session_state["role"], "child")
        self.assertNotEqual(self.app.session_state["media_session_nonce"], old_nonce)
        old_client = TestClient(Starlette(routes=secure_media.routes()))
        old_client.cookies.set(secure_media.COOKIE_NAME, old_nonce)
        self.assertEqual(old_client.get(old_url).status_code, 401)
        self.assertNotIn("draft", self.app.session_state)
        self.app.session_state["page"] = "Parent portal"
        self.app.run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertTrue(any(t.label == "Parent password" for t in self.app.text_input))
        self.assertFalse(any(s.label == "Manage" for s in self.app.selectbox))

    def test_child_cannot_access_parent_backup_controls(self):
        self.signed_in(role="child")
        self.app.session_state["page"] = "Parent portal"
        self.app.run(timeout=30)
        self.assertFalse(any(s.label == "Manage" for s in self.app.selectbox))
        self.assertTrue(any(t.label == "Parent password" for t in self.app.text_input))

    def test_parent_portal_lists_private_family_backup(self):
        self.signed_in()
        manage = next(select for select in self.app.selectbox if select.label == "Manage")
        self.assertIn("Family backup", manage.options)

    def test_parent_backup_download_is_bound_to_parent_session(self):
        self.signed_in()
        next(select for select in self.app.selectbox if select.label == "Manage").set_value("Family backup").run(timeout=30)
        self.click("Prepare family backup")
        self.assertTrue(self.app.session_state["academy-backup-download"].startswith(b"PK"))
        with secure_media._lock:
            records = [record for record in secure_media._media.values()
                       if record.filename and record.filename.startswith("ajs-academy-backup-")]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].allowed_roles, frozenset({"parent"}))

    def test_logout_clears_role_and_drafts(self):
        self.signed_in()
        self.app.session_state["draft"] = "synthetic draft"
        self.click("Sign out")
        self.assertNotIn("role", self.app.session_state)
        self.assertNotIn("draft", self.app.session_state)

    def test_child_entry_needs_no_auth_and_clears_stale_drafts(self):
        with patch("store.authenticate", return_value=(False, "Not authorized")) as auth:
            self.app.session_state["draft"] = "stale parent draft"
            self.app.run(timeout=30)
            self.click("Let’s Begin")
            auth.assert_not_called()
        self.assertEqual(self.app.session_state["role"], "child")
        self.assertNotIn("draft", self.app.session_state)
        self.assertEqual(self.app.session_state["page"], "Home")

    def test_parent_password_failure_and_success(self):
        self.signed_in(role="child", page="Parent portal")
        with patch("store.authenticate", return_value=(False, "That password did not match.")) as auth:
            self.app.text_input[0].set_value("synthetic-wrong")
            self.click("Unlock parent portal")
            auth.assert_called_once_with("parent", "synthetic-wrong")
        self.assertEqual(self.app.session_state["role"], "child")
        self.assertFalse(any(s.label == "Manage" for s in self.app.selectbox))
        old_nonce = self.app.session_state["media_session_nonce"]
        with patch("store.authenticate", return_value=(True, "")):
            self.app.text_input[0].set_value("synthetic-correct")
            self.click("Unlock parent portal")
        self.assertEqual(self.app.session_state["role"], "parent")
        self.assertNotIn(old_nonce, secure_media._sessions)
        self.assertTrue(any(s.label == "Manage" for s in self.app.selectbox))

    def test_preview_names_all_nine_sections_without_family_data(self):
        self.app.run(timeout=30)
        rendered = " ".join(str(element.value) for element in self.app.main
                            if element.type in ("markdown", "subheader", "caption", "title"))
        for label in ("My Investments", "My College Dream", "My Diary", "AJ’s Reminders",
                      "Soccer", "LEGO", "AI Discoveries", "My Arcade", "AJ’s Social Skills"):
            self.assertIn(label, rendered)
        self.assertNotIn("Preview Watson", rendered)
        store.load.assert_not_called()

    def test_private_media_rejects_requests_without_a_live_session(self):
        nonce = secure_media.new_session_nonce()
        secure_media.grant_session(nonce, "parent", time.time() + 60)
        url = secure_media.register(
            b"private evidence",
            "text/csv",
            "family.csv",
            nonce=nonce,
            role="parent",
            allowed_roles=("parent",),
        )
        client = TestClient(Starlette(routes=secure_media.routes()))
        path = url

        response = client.get(path)
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(b"private evidence", response.content)

        client.cookies.set(secure_media.COOKIE_NAME, nonce)
        response = client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"private evidence")
        self.assertIn("no-store", response.headers["cache-control"])
        self.assertIn("attachment", response.headers["content-disposition"])

        secure_media.revoke_session(nonce)
        response = client.get(path)
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(b"private evidence", response.content)

    def test_child_session_cannot_use_copied_parent_url(self):
        parent_nonce = secure_media.new_session_nonce()
        child_nonce = secure_media.new_session_nonce()
        secure_media.grant_session(parent_nonce, "parent", time.time() + 60)
        secure_media.grant_session(child_nonce, "child", time.time() + 60)
        parent_url = secure_media.register(
            b"parent-only statement",
            "text/csv",
            "statement.csv",
            nonce=parent_nonce,
            role="parent",
            allowed_roles=("parent",),
        )
        child_url = secure_media.register(
            b"child-visible photo",
            "image/jpeg",
            None,
            nonce=child_nonce,
            role="child",
            allowed_roles=("parent", "child"),
        )
        client = TestClient(Starlette(routes=secure_media.routes()))

        client.cookies.set(secure_media.COOKIE_NAME, child_nonce)
        response = client.get(parent_url)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"parent-only statement", response.content)
        self.assertEqual(client.get(child_url).content, b"child-visible photo")

        secure_media.revoke_session(parent_nonce)
        self.assertEqual(client.get(parent_url).status_code, 403)

    def test_video_range_requests_are_authorized_and_return_partial_bytes(self):
        nonce = secure_media.new_session_nonce()
        child_nonce = secure_media.new_session_nonce()
        secure_media.grant_session(nonce, "parent", time.time() + 60)
        secure_media.grant_session(child_nonce, "child", time.time() + 60)
        url = secure_media.register(
            b"0123456789",
            "video/mp4",
            None,
            nonce=nonce,
            role="parent",
            allowed_roles=("parent",),
        )
        client = TestClient(Starlette(routes=secure_media.routes()))

        response = client.get(url, headers={"Range": "bytes=2-5"})
        self.assertEqual(response.status_code, 401)

        client.cookies.set(secure_media.COOKIE_NAME, child_nonce)
        response = client.get(url, headers={"Range": "bytes=2-5"})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"2345", response.content)

        client.cookies.set(secure_media.COOKIE_NAME, nonce)
        response = client.get(url, headers={"Range": "bytes=2-5"})
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.content, b"2345")
        self.assertEqual(response.headers["content-range"], "bytes 2-5/10")
        self.assertEqual(response.headers["content-length"], "4")

    def tearDown(self):
        with secure_media._lock:
            nonces = list(secure_media._sessions)
        for nonce in nonces:
            secure_media.revoke_session(nonce)


class ParentAuthenticationTests(unittest.TestCase):
    def test_missing_secret_fails_closed_and_only_configured_secret_works(self):
        for configured, supplied, allowed in (
            ("", "", False), ("", "synthetic-wrong", False),
            ("synthetic-test-only", "synthetic-wrong", False),
            ("synthetic-test-only", "synthetic-test-only", True),
        ):
            with self.subTest(configured=bool(configured), allowed=allowed):
                with patch.dict(os.environ, {"PARENT_PASSWORD": configured}), \
                     patch("store.connection") as connect:
                    c = connect.return_value.__enter__.return_value
                    c.execute.return_value.fetchone.return_value = (0, None)
                    self.assertEqual(store.authenticate("parent", supplied)[0], allowed)

    def test_lockout_prevents_even_correct_password(self):
        from datetime import timedelta
        with patch.dict(os.environ, {"PARENT_PASSWORD": "synthetic-test-only"}), \
             patch("store.connection") as connect:
            c = connect.return_value.__enter__.return_value
            c.execute.return_value.fetchone.return_value = (5, store.now() + timedelta(minutes=5))
            allowed, reason = store.authenticate("parent", "synthetic-test-only")
            self.assertFalse(allowed)
            self.assertIn("wait", reason)
            self.assertEqual(c.execute.call_count, 2)

    def test_fifth_failure_sets_lockout(self):
        with patch.dict(os.environ, {"PARENT_PASSWORD": "synthetic-test-only"}), \
             patch("store.connection") as connect:
            c = connect.return_value.__enter__.return_value
            c.execute.return_value.fetchone.return_value = (4, None)
            self.assertFalse(store.authenticate("parent", "synthetic-wrong")[0])
            params = c.execute.call_args.args[1]
            self.assertEqual(params[0], 5)
            self.assertGreater(params[1], store.now())

    def test_non_parent_password_role_is_rejected(self):
        with patch("store.connection") as connect:
            self.assertFalse(store.authenticate("child", "synthetic-test-only")[0])
            connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()

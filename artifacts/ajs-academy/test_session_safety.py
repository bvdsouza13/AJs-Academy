"""Isolated session tests; no real credentials, family data, or database writes."""
import copy
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
        self.assertTrue(any(t.label == "Your password" for t in self.app.text_input))

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
        self.assertTrue(any(t.label == "Your password" for t in self.app.text_input))

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

    def test_logout_clears_role_and_drafts(self):
        self.signed_in()
        self.app.session_state["draft"] = "synthetic draft"
        self.click("Sign out")
        self.assertNotIn("role", self.app.session_state)
        self.assertNotIn("draft", self.app.session_state)

    def test_child_login_requires_parent_approval(self):
        with patch("store.authenticate", return_value=(False, "Not authorized")) as auth:
            self.app.run(timeout=30)
            self.click("Let’s begin")
            auth.assert_called_once_with("parent", "")
        self.assertNotIn("role", self.app.session_state)
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


if __name__ == "__main__":
    unittest.main()

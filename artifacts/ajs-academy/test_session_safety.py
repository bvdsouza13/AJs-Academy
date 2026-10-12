"""Isolated session tests; no real credentials, family data, or database writes."""
import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
import store


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

    def test_expired_parent_session_requires_login_before_loading_data(self):
        self.signed_in(age=1801)
        store.load.assert_not_called()
        self.assertNotIn("role", self.app.session_state)

    def test_handoff_clears_parent_drafts_and_requires_reauthentication(self):
        self.app.session_state["draft"] = "synthetic parent-only draft"
        self.signed_in()
        self.click("Switch to AJ’s view")
        self.assertEqual(self.app.session_state["role"], "child")
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


if __name__ == "__main__":
    unittest.main()

"""Synthetic checks for demo isolation, read-only views and reversibility."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import financial_demo as demo
import store


class FinancialDemoTests(unittest.TestCase):
    def setUp(self):
        self.saved = copy.deepcopy(store.DEFAULT)
        self.saved["settings"].update(
            financial_demo_enabled=True, custody_balance=987654.32,
            custody_asof="2026-01-01", goal=765432, favorite_school="MIT",
            school_costs={"Stanford|Florida": {"annual": 123456}},
        )
        self.saved["finance"] = {
            "custody": {"records": [], "start": "2025-01-01", "end": "2025-01-02",
                        "private_marker": "ORIGINAL_EXPORT"},
            "college": {"balance": 654321},
            "custody_statements": {"private_marker": "ORIGINAL_STATEMENTS"},
            "college_statements": {"private_marker": "ORIGINAL_COLLEGE_STATEMENTS"},
        }
        self.saved["diary"] = [{"id": "synthetic-diary", "answers": ["keep this"]}]
        self.original = copy.deepcopy(self.saved)

    def run_page(self, role, page):
        with patch("store.load", side_effect=lambda: copy.deepcopy(self.saved)), \
             patch("store.change", side_effect=lambda fn: fn(self.saved)):
            app = AppTest.from_file(str(Path(__file__).with_name("app.py")))
            for key, value in {"role": role, "page": page,
                               "last_active": store.now().timestamp()}.items():
                app.session_state[key] = value
            app.run(timeout=30)
        self.assertFalse(app.exception)
        return app

    def test_overlay_uses_fixtures_without_modifying_originals(self):
        shown = demo.view(self.saved)
        self.assertEqual(len(shown["finance"]["custody"]["records"]), 407)
        self.assertEqual(len(shown["finance"]["college"]["records"]), 32)
        self.assertEqual(shown["finance"]["college"]["balance"], 5915.35)
        self.assertEqual(shown["finance"]["college"]["fund"], "Demo 2036-2037 Enrollment Portfolio")
        self.assertEqual(set(shown["finance"]), {"custody", "college"})
        self.assertIsNone(shown["settings"]["custody_balance"])
        self.assertEqual(shown["settings"]["school_costs"], {})
        self.assertEqual(shown["diary"], self.saved["diary"])
        shown["finance"]["college"]["balance"] = 0
        self.assertEqual(self.saved, self.original)

    def test_original_evidence_restores_exactly(self):
        self.saved["settings"][demo.SETTING] = False
        self.assertIs(demo.view(self.saved), self.saved)
        self.assertEqual(demo.view(self.saved)["finance"], self.original["finance"])
        self.assertEqual(demo.view(self.saved)["settings"]["custody_balance"], 987654.32)

    def test_legacy_state_is_not_silently_switched(self):
        self.saved["settings"].pop(demo.SETTING)
        self.assertFalse(demo.enabled(self.saved))
        self.assertIs(demo.view(self.saved), self.saved)

    def test_child_views_hide_original_finances(self):
        for page in ("My Investments", "My College Dream"):
            with self.subTest(page=page):
                app = self.run_page("child", page)
                for private in ("987654", "654321", "ORIGINAL_EXPORT", "ORIGINAL_STATEMENTS"):
                    self.assertNotIn(private, repr(app.main))
                self.assertTrue(any("DEMO financial data" in item.value for item in app.info))
                self.assertFalse(any(b.key and b.key.startswith("financial-demo-toggle") for b in app.button))
        self.assertEqual(self.saved, self.original)

    def test_parent_demo_is_read_only(self):
        for page in ("My Investments", "My College Dream"):
            with self.subTest(page=page):
                app = self.run_page("parent", page)
                self.assertFalse(app.get("file_uploader"))
                labels = [b.label for b in app.button]
                for forbidden in ("Import this CSV", "Replace statement history",
                                  "Save parent-only figures", "Save college assumptions"):
                    self.assertNotIn(forbidden, labels)
                self.assertIn("Show original financial data", labels)
                self.assertNotIn("ORIGINAL_STATEMENTS", repr(app.main))
        self.assertEqual(self.saved, self.original)

    def test_parent_toggle_only_changes_mode_flag(self):
        app = self.run_page("parent", "My Investments")
        with patch("store.load", side_effect=lambda: copy.deepcopy(self.saved)), \
             patch("store.change", side_effect=lambda fn: fn(self.saved)):
            app.button(key="financial-demo-toggle-custody").click().run(timeout=30)
        expected = copy.deepcopy(self.original)
        expected["settings"][demo.SETTING] = False
        self.assertEqual(self.saved, expected)
        self.assertTrue(app.get("file_uploader"))
        self.assertFalse(any("DEMO financial data" in item.value for item in app.info))


if __name__ == "__main__":
    unittest.main()

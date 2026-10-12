"""App-level tests for parent-managed support choices and child help wording."""
import copy
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
import store


class SocialCustomizationTests(unittest.TestCase):
    def setUp(self):
        self.state = copy.deepcopy(store.DEFAULT)
        self.load_patch = patch("store.load", side_effect=lambda: copy.deepcopy(self.state))
        self.change_patch = patch("store.change", side_effect=self._change)
        self.load_patch.start()
        self.change_patch.start()
        self.addCleanup(self.load_patch.stop)
        self.addCleanup(self.change_patch.stop)
        self.app = AppTest.from_file(str(Path(__file__).with_name("app.py")))
        self.app.session_state["role"] = "parent"
        self.app.session_state["page"] = "Parent portal"
        self.app.session_state["last_active"] = store.now().timestamp()
        self.app.run(timeout=30)
        self.app.selectbox[0].select("Social Skills & privacy").run(timeout=30)
        self.assertFalse(self.app.exception)

    def _change(self, callback):
        return callback(self.state)

    def _button(self, key):
        return next(button for button in self.app.button if button.key == key)

    def _submit(self, key):
        self._button(key).click().run(timeout=30)
        self.assertFalse(self.app.exception)

    def test_parent_can_add_edit_reorder_and_remove_support_choices(self):
        add_values = {
            "New support label": "Movement break",
            "Picture symbol": "🏃",
            "Words AJ could use": "Could I walk for a moment?",
            "Words for a grown-up": "Please help AJ take a short walk.",
        }
        for label, value in add_values.items():
            next(widget for widget in self.app.text_input
                 if widget.label == label and widget.key is None).set_value(value)
        self._submit("FormSubmitter:add-social-support-Add support choice")
        created = self.state["settings"]["social_supports"][-1]
        support_id = created["id"]

        self.app.text_input(key=f"social-support-label-{support_id}").set_value("A short walk")
        self.app.text_input(key=f"social-support-kid-{support_id}").set_value("May I walk for a minute?")
        self._submit(f"FormSubmitter:edit-social-support-{support_id}-Save support choice")
        created = next(item for item in self.state["settings"]["social_supports"]
                       if item["id"] == support_id)
        self.assertEqual(created["label"], "A short walk")
        self.assertEqual(created["kid_request"], "May I walk for a minute?")

        self._submit(f"move-social-support-up-{support_id}")
        self.assertEqual(self.state["settings"]["social_supports"][-2]["id"], support_id)
        self._submit(f"move-social-support-down-{support_id}")
        for _ in range(len(self.state["settings"]["social_supports"]) - 1):
            self._submit(f"move-social-support-up-{support_id}")
        self.assertEqual(self.state["settings"]["social_supports"][0]["id"], support_id)
        self._submit(f"remove-social-support-{support_id}")
        self.assertNotIn(support_id, [item["id"] for item in self.state["settings"]["social_supports"]])

    def test_parent_can_add_edit_reorder_and_remove_trusted_adult_labels(self):
        next(widget for widget in self.app.text_input if widget.label == "Trusted-adult label").set_value("Grandma")
        self._submit("FormSubmitter:add-social-trusted-adult-Add trusted grown-up")
        adults = self.state["settings"]["social_trusted_adults"]
        self.assertEqual(adults[-1], "Grandma")

        adult_key = hashlib.sha256(b"Grandma").hexdigest()[:12]
        self.app.text_input(key=f"social-trusted-adult-edit-{adult_key}").set_value("Grandma Lee")
        self._submit(f"FormSubmitter:edit-social-trusted-adult-{adult_key}-Save label")
        adults = self.state["settings"]["social_trusted_adults"]
        self.assertEqual(adults[-1], "Grandma Lee")

        self._submit("move-trusted-adult-up-3")
        self.assertEqual(self.state["settings"]["social_trusted_adults"][2], "Grandma Lee")
        self._submit("move-trusted-adult-down-2")
        self.assertEqual(self.state["settings"]["social_trusted_adults"][3], "Grandma Lee")
        self._submit("remove-trusted-adult-3")
        self.assertNotIn("Grandma Lee", self.state["settings"]["social_trusted_adults"])

    def test_child_can_choose_a_support_without_feeling_rating_ai_or_recording(self):
        self.app.session_state["role"] = "child"
        self.app.session_state["page"] = "AJ’s Social Skills"
        self.app.run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertFalse(any("feeling" in widget.label.lower() for widget in self.app.selectbox))
        self.assertFalse(self.state["settings"]["social_ai_enabled"])
        self.assertFalse(self.state["settings"]["social_audio_enabled"])

        next(button for button in self.app.button if "A little more time" in button.label).click().run(timeout=30)
        self.assertFalse(self.app.exception)
        kid_words = next(widget.value for widget in self.app.text_area if widget.label == "Words for another kid")
        self.assertEqual(kid_words, "Could I have a little more time?")

        adult_select = next(widget for widget in self.app.selectbox
                            if widget.label == "Someone I trust (optional)")
        adult_select.select("My teacher").run(timeout=30)
        next(button for button in self.app.button if button.label == "Make words I can use").click().run(timeout=30)
        kid_words = next(widget.value for widget in self.app.text_area if widget.label == "Words for another kid")
        adult_words = next(widget.value for widget in self.app.text_area if widget.label == "Words for a grown-up")
        self.assertIn("My teacher", kid_words)
        self.assertIn("My teacher", adult_words)
        self.assertFalse(self.app.exception)


class SocialRequestShowcaseTests(unittest.TestCase):
    def setUp(self):
        self.state = copy.deepcopy(store.DEFAULT)
        self.load_patch = patch("store.load", side_effect=lambda: copy.deepcopy(self.state))
        self.change_patch = patch("store.change", side_effect=lambda callback: callback(self.state))
        self.load_patch.start()
        self.change_patch.start()
        self.addCleanup(self.load_patch.stop)
        self.addCleanup(self.change_patch.stop)
        self.app = AppTest.from_file(str(Path(__file__).with_name("app.py")))
        self.app.session_state["role"] = "child"
        self.app.session_state["page"] = "AJ’s Social Skills"
        self.app.session_state["last_active"] = store.now().timestamp()
        self.app.run(timeout=30)
        self.assertFalse(self.app.exception)

    def _show_request(self, widget_key, expected_words, expected_title):
        self.app.text_area(key=widget_key).set_value(expected_words).run(timeout=30)
        next(button for button in self.app.button if button.key == (
            "social-show-kid-request" if widget_key == "social-kid-script"
            else "social-show-adult-request"
        )).click().run(timeout=30)
        self.assertFalse(self.app.exception)
        rendered_markdown = "\n".join(widget.value for widget in self.app.markdown)
        self.assertIn(expected_title, rendered_markdown)
        self.assertIn(expected_words, rendered_markdown)
        self.assertNotIn(widget_key, [widget.key for widget in self.app.text_area])

        next(button for button in self.app.button if button.key == "social-request-back").click().run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertIn(widget_key, [widget.key for widget in self.app.text_area])

    def test_child_and_grown_up_requests_can_be_shown_and_return_to_editing(self):
        self._show_request(
            "social-kid-script",
            "Could I have a little more time?",
            "Words for another kid",
        )
        self._show_request(
            "social-adult-script",
            "Please help me find a quiet place.",
            "Words for a grown-up",
        )


if __name__ == "__main__":
    unittest.main()

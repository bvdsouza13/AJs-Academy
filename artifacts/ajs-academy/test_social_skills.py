import base64
import copy
import io
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image
from streamlit.testing.v1 import AppTest

import content
import store


class SocialSkillsTests(unittest.TestCase):
    def test_starter_visual_scenarios_are_complete_and_valid(self):
        self.assertEqual(len(content.SOCIAL_SCENARIO_STARTERS), 4)
        for starter in content.SOCIAL_SCENARIO_STARTERS:
            self.assertEqual(len(starter["choices"]), 3)
            cleaned = content.validate_social_scenario(
                starter["title"], starter["situation"], starter["example"],
                starter["choices"], starter["art"],
            )
            self.assertEqual(cleaned, {
                "title": starter["title"],
                "situation": starter["situation"],
                "example": starter["example"],
                "choices": starter["choices"],
                "art": starter["art"],
            })

    def test_scenario_validator_cleans_text_and_rejects_incomplete_or_duplicate_choices(self):
        cleaned = content.validate_social_scenario(
            "  Joining\n a game ", "  Kids are playing. ", " I can ask. ",
            [" Can I play? ", "What are the teams?", "I can watch."], "join_game",
        )
        self.assertEqual(cleaned["title"], "Joining a game")
        self.assertEqual(cleaned["choices"][0], "Can I play?")
        with self.assertRaisesRegex(ValueError, "exactly three"):
            content.validate_social_scenario("Title", "Moment", "Example", ["Only one"], "join_game")
        with self.assertRaisesRegex(ValueError, "different"):
            content.validate_social_scenario("Title", "Moment", "Example", ["Same", "same", "Other"], "join_game")
        with self.assertRaisesRegex(ValueError, "illustration"):
            content.validate_social_scenario("Title", "Moment", "Example", ["One", "Two", "Three"], "untrusted")

    def test_child_view_only_receives_unique_valid_parent_approved_scenarios(self):
        approved = {
            **content.SOCIAL_SCENARIO_STARTERS[0],
            "id": "approved-1",
            "approved": True,
        }
        draft = {
            **content.SOCIAL_SCENARIO_STARTERS[1],
            "id": "draft-1",
            "approved": False,
        }
        invalid_approved = {
            **content.SOCIAL_SCENARIO_STARTERS[2],
            "id": "invalid-1",
            "approved": True,
            "choices": ["Only one"],
        }
        duplicate = {**approved, "title": "Duplicate"}
        result = content.approved_social_scenarios(
            [approved, draft, invalid_approved, duplicate, None]
        )
        self.assertEqual([scenario["id"] for scenario in result], ["approved-1"])
        self.assertEqual(result[0]["title"], "Joining a game")

    def test_scripts_are_local_first_person_and_include_chosen_need(self):
        scripts = content.social_scripts("confused", "The words changed quickly", "help understanding")
        self.assertEqual(
            scripts["kid"],
            "I'm feeling confused. The words changed quickly. Could you explain that another way?",
        )
        self.assertIn("AJ is feeling confused.", scripts["adult"])
        self.assertIn("Please explain it another way.", scripts["adult"])

    def test_scripts_use_safe_defaults_for_unrecognized_options(self):
        scripts = content.social_scripts("unexpected", "", "unexpected")
        self.assertEqual(scripts["kid"], "I'm feeling unsure. Could you help me find my parent or another grown-up I trust?")

    def test_parent_support_settings_are_limited_and_normalized(self):
        support = {
            "id": "walk", "icon": " 🌱 ", "label": " Movement break ",
            "kid_request": " Could I walk for a moment? ",
            "adult_request": " Please help AJ take a short walk. ",
        }
        result = content.validate_social_supports([support])
        self.assertEqual(result[0], {
            "id": "walk", "icon": "🌱", "label": "Movement break",
            "kid_request": "Could I walk for a moment?",
            "adult_request": "Please help AJ take a short walk.",
        })
        with self.assertRaisesRegex(ValueError, "different label"):
            content.validate_social_supports([support, {**support, "id": "another"}])
        with self.assertRaisesRegex(ValueError, "between 1 and 6"):
            content.validate_social_supports([])

    def test_trusted_adult_labels_and_local_support_scripts(self):
        support = {
            "label": "A quiet moment",
            "kid_request": "Could I have a quiet moment?",
            "adult_request": "Please help AJ find a quiet place.",
        }
        labels = content.validate_trusted_adults([" My teacher ", "Coach"])
        self.assertEqual(labels, ["My teacher", "Coach"])
        scripts = content.social_support_scripts(
            support, "the room is loud", labels[0]
        )
        self.assertEqual(
            scripts["kid"],
            "Could I have a quiet moment? I want to tell you: the room is loud. "
            "I would like to talk with someone I trust: My teacher.",
        )
        self.assertIn("Please help AJ find a quiet place.", scripts["adult"])
        self.assertIn("AJ chose My teacher", scripts["adult"])
        self.assertNotIn("feeling", scripts["kid"].lower())
        with self.assertRaisesRegex(ValueError, "different"):
            content.validate_trusted_adults(["Teacher", " teacher "])

    def test_interpretation_requires_some_input_without_calling_ai(self):
        with patch.object(content, "client") as client:
            with self.assertRaises(ValueError):
                content.interpret_social()
            client.assert_not_called()

    def test_interpretation_uses_schema_and_marks_image_as_written_context(self):
        image = Image.new("RGB", (10, 10), "white")
        image_bytes = io.BytesIO()
        image.save(image_bytes, format="PNG")
        answer = {
            "literal_meaning": "The words say it is raining.",
            "possible_meaning": "It might be a joke, but I cannot tell.",
            "what_to_say": "Are you joking or serious?",
            "trusted_adult": "Ask a grown-up you trust if you are still unsure.",
        }
        mocked_client = MagicMock()
        mocked_client.chat.completions.create.return_value.choices[0].message.content = json.dumps(answer)
        with patch.object(content, "client", return_value=mocked_client):
            result = content.interpret_social("It is raining cats and dogs.", image_bytes.getvalue())
        self.assertEqual(result, answer)
        kwargs = mocked_client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "gpt-5.4-mini")
        user_content = kwargs["messages"][1]["content"]
        self.assertIn("image_url", [part["type"] for part in user_content])
        data_url = next(part["image_url"]["url"] for part in user_content if part["type"] == "image_url")
        self.assertTrue(base64.b64decode(data_url.split(",", 1)[1]))
        request_instructions = user_content[0]["text"]
        self.assertIn("request to keep a secret", request_instructions)

    def test_invalid_image_fails_before_ai_call(self):
        with patch.object(content, "client") as client:
            with self.assertRaises(ValueError):
                content.interpret_social(image_bytes=b"not an image")
            client.assert_not_called()

    def test_malformed_ai_response_is_not_shown_as_a_confident_answer(self):
        mocked_client = MagicMock()
        mocked_client.chat.completions.create.return_value.choices[0].message.content = "{}"
        with patch.object(content, "client", return_value=mocked_client):
            with self.assertRaisesRegex(ValueError, "trusted grown-up"):
                content.interpret_social("What does this mean?")


class SocialScenarioInteractionTests(unittest.TestCase):
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
        self.assertFalse(self.app.exception)
        next(widget for widget in self.app.selectbox if widget.label == "Manage").select(
            "Social Skills & privacy"
        ).run(timeout=30)
        self.assertFalse(self.app.exception)

    def _change(self, callback):
        return callback(self.state)

    def _button(self, key):
        return next(button for button in self.app.button if button.key == key)

    def _submit(self, key):
        self._button(key).click().run(timeout=30)
        self.assertFalse(self.app.exception)

    def test_parent_adds_starter_drafts_approves_edits_and_removes_story(self):
        self._submit("social-scenarios-add-starters")
        scenarios = self.state["social_scenarios"]
        self.assertEqual(len(scenarios), len(content.SOCIAL_SCENARIO_STARTERS))
        self.assertTrue(all(item["approved"] is False for item in scenarios))
        self.assertEqual(
            {item["starter_id"] for item in scenarios},
            {item["starter_id"] for item in content.SOCIAL_SCENARIO_STARTERS},
        )

        story = scenarios[0]
        story_id = story["id"]
        self.app.text_input(key=f"scenario-title-{story_id}").set_value("Joining at recess")
        self.app.text_area(key=f"scenario-situation-{story_id}").set_value(
            "Some kids are playing at recess, and there may be room."
        )
        self.app.checkbox(key=f"scenario-approved-{story_id}").set_value(True)
        self._submit(f"FormSubmitter:edit-social-scenario-{story_id}-Save story")

        saved = next(item for item in self.state["social_scenarios"] if item["id"] == story_id)
        self.assertEqual(saved["title"], "Joining at recess")
        self.assertEqual(saved["situation"], "Some kids are playing at recess, and there may be room.")
        self.assertTrue(saved["approved"])

        self._submit(f"delete-social-scenario-{story_id}")
        self.assertNotIn(story_id, [item["id"] for item in self.state["social_scenarios"]])
        self.assertEqual(len(self.state["social_scenarios"]), 3)

    def test_child_only_sees_approved_stories_and_can_choose_skip_and_stop(self):
        starters = content.SOCIAL_SCENARIO_STARTERS
        self.state["social_scenarios"] = [
            {**starters[0], "id": "approved-1", "approved": True},
            {**starters[1], "id": "draft-hidden", "approved": False},
            {**starters[2], "id": "approved-2", "approved": True},
        ]
        self.app.session_state["role"] = "child"
        self.app.session_state["page"] = "AJ’s Social Skills"
        self.app.run(timeout=30)
        self.assertFalse(self.app.exception)

        visible_story_text = repr(self.app.main)
        self.assertNotIn("draft-hidden", visible_story_text)
        self.assertNotIn(starters[1]["title"], visible_story_text)
        self.assertIn(starters[0]["title"], visible_story_text)

        story_picker = next(widget for widget in self.app.selectbox if widget.label == "Choose a story")
        story_picker.select("approved-1").run(timeout=30)
        self.assertFalse(self.app.exception)
        self._button("social-story-choice-approved-1-0").click().run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertEqual(
            self.app.session_state["social-scenario-response"],
            ("approved-1", starters[0]["choices"][0]),
        )

        self._button("social-story-skip").click().run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["social-scenario-selected"], "approved-2")
        self.assertNotIn("social-scenario-response", self.app.session_state)

        self._button("social-story-stop").click().run(timeout=30)
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.session_state["social-practice-active"])
        self.assertTrue(any("Practice is paused" in item.value for item in self.app.caption))


if __name__ == "__main__":
    unittest.main()

import base64
import io
import json
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

import content


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


if __name__ == "__main__":
    unittest.main()

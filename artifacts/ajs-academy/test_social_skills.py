import base64
import io
import json
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

import content


class SocialSkillsTests(unittest.TestCase):
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

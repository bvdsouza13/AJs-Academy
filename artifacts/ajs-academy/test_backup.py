"""Backup validation and restore tests use synthetic records and mocked storage."""
import copy
import unittest
from unittest.mock import Mock

import backup
import store


class FamilyBackupTests(unittest.TestCase):
    def setUp(self):
        self.state = copy.deepcopy(store.DEFAULT)
        self.state["settings"]["api_key"] = "should-not-ship"
        self.state["diary"] = [{
            "id": "entry-1",
            "date": "2026-10-12",
            "answers": ["A good day", "", ""],
            "photos": [{
                "bucket": "private-family-bucket",
                "path": "private-folder/academy/photo-object",
                "mime": "image/jpeg",
                "name": "drawing.jpg",
            }],
        }]
        self.photo_bytes = b"synthetic family photo"

    def archive(self):
        return backup.build_archive(
            self.state,
            download=lambda metadata: self.photo_bytes,
        )

    def test_backup_round_trips_records_and_attachment_without_storage_paths_or_secrets(self):
        payload = self.archive()
        restored = backup.inspect_archive(payload)
        self.assertEqual(restored["summary"]["attachments"], 1)
        self.assertEqual(restored["state"]["diary"][0]["answers"][0], "A good day")
        self.assertEqual(len(restored["media"]), 1)
        self.assertNotIn("api_key", restored["state"]["settings"])
        self.assertNotIn(b"private-family-bucket", payload)
        self.assertNotIn(b"private-folder/academy/photo-object", payload)
        self.assertNotIn(b"should-not-ship", payload)

    def test_restore_replaces_state_and_uploads_fresh_private_attachment(self):
        preview = backup.inspect_archive(self.archive())
        current = copy.deepcopy(store.DEFAULT)
        current["ledger"].append({"key": "existing", "points": 1, "label": "Old", "date": "2026-10-12"})
        saved_before = copy.deepcopy(current)
        uploaded = []

        def save(update):
            update(current)

        backup.restore_archive(
            preview,
            backup.state_digest(saved_before),
            upload=lambda content, mime, name: uploaded.append((content, mime, name)) or {
                "bucket": "new-private-bucket",
                "path": "new-family-path",
                "mime": mime,
                "name": name,
            },
            change=save,
            delete=Mock(),
        )
        self.assertEqual(current["diary"][0]["photos"][0]["bucket"], "new-private-bucket")
        self.assertEqual(current["diary"][0]["photos"][0]["path"], "new-family-path")
        self.assertEqual(uploaded, [(self.photo_bytes, "image/jpeg", "drawing.jpg")])
        self.assertEqual(current["ledger"], [])

    def test_restore_aborts_if_current_records_changed_after_preview_and_cleans_upload(self):
        preview = backup.inspect_archive(self.archive())
        current = copy.deepcopy(store.DEFAULT)
        current["ledger"].append({"key": "new", "points": 2, "label": "Recent", "date": "2026-10-12"})
        before = copy.deepcopy(current)
        cleanup = Mock()

        def save(update):
            update(current)

        with self.assertRaisesRegex(ValueError, "changed after the preview"):
            backup.restore_archive(
                preview,
                backup.state_digest(store.DEFAULT),
                upload=lambda content, mime, name: {
                    "bucket": "new-private-bucket", "path": "new-object", "mime": mime, "name": name,
                },
                change=save,
                delete=cleanup,
            )
        self.assertEqual(current, before)
        cleanup.assert_called_once()

    def test_invalid_archive_is_rejected_before_restore(self):
        with self.assertRaisesRegex(ValueError, "valid Academy backup"):
            backup.inspect_archive(b"not a zip")

    def test_media_over_limit_is_rejected_before_creating_archive(self):
        with self.assertRaisesRegex(ValueError, "40 MB limit"):
            backup.build_archive(
                self.state,
                download=lambda metadata: b"x" * (40 * 1024 * 1024 + 1),
            )


if __name__ == "__main__":
    unittest.main()

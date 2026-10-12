"""State evolution tests use only synthetic records and mocked database connections."""
import copy
import unittest
from unittest.mock import Mock, patch

import store


class StateUpgradeTests(unittest.TestCase):
    def test_older_document_gets_missing_defaults_without_changing_saved_records(self):
        old_state = {
            "settings": {
                "task_points": {"wake": 7},
                "conversion": 12,
                "social_supports": [{"id": "family-choice", "label": "My own choice"}],
                "custom_parent_setting": "keep me",
            },
            "ledger": [{"key": "task:old", "points": 42, "label": "Saved points", "date": "2026-01-01"}],
            "diary": [{"id": "diary-old", "answers": ["A saved memory"]}],
            "finance": {"custody": {"balance": 12345}, "custom_financial_record": {"keep": True}},
            "future_section": {"owned_by_newer_version": True},
        }
        original = copy.deepcopy(old_state)

        upgraded = store.upgrade_state(old_state)

        self.assertEqual(old_state, original)
        self.assertEqual(upgraded["settings"]["conversion"], 12)
        self.assertEqual(upgraded["settings"]["task_points"]["wake"], 7)
        self.assertEqual(
            upgraded["settings"]["task_points"]["brush"],
            store.DEFAULT["settings"]["task_points"]["brush"],
        )
        self.assertEqual(upgraded["settings"]["social_supports"], old_state["settings"]["social_supports"])
        self.assertEqual(upgraded["settings"]["custom_parent_setting"], "keep me")
        for section in ("ledger", "diary", "finance", "future_section"):
            self.assertEqual(upgraded[section], old_state[section])
        for key, default in store.DEFAULT.items():
            self.assertIn(key, upgraded)
            if key not in old_state:
                self.assertEqual(upgraded[key], default)

    def test_upgrade_is_repeatable_and_returns_independent_defaults(self):
        old_state = {"settings": {"task_points": {"wake": 3}}, "ledger": []}
        first = store.upgrade_state(old_state)
        second = store.upgrade_state(first)

        self.assertEqual(second, first)
        self.assertIsNot(second, first)
        second["settings"]["task_points"]["brush"] = 99
        self.assertNotEqual(first["settings"]["task_points"]["brush"], 99)
        self.assertEqual(old_state, {"settings": {"task_points": {"wake": 3}}, "ledger": []})

    def test_invalid_document_or_nested_section_fails_without_replacement(self):
        with self.assertRaisesRegex(ValueError, "JSON object"):
            store.upgrade_state([])
        with self.assertRaisesRegex(ValueError, "settings.task_points"):
            store.upgrade_state({"settings": {"task_points": None}})
        with self.assertRaisesRegex(ValueError, "state.diary"):
            store.upgrade_state({"diary": {}})

    def test_load_persists_missing_defaults_and_returns_upgraded_data(self):
        old_state = {"settings": {"conversion": 15}, "diary": [{"id": "keep"}], "ledger": [{"points": 4}]}
        select = Mock()
        select.fetchone.return_value = (old_state,)
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.execute.side_effect = [select, None]

        with patch.object(store, "connection", return_value=connection):
            loaded = store.load()

        self.assertEqual(loaded["settings"]["conversion"], 15)
        self.assertEqual(loaded["diary"], old_state["diary"])
        self.assertEqual(loaded["ledger"], old_state["ledger"])
        self.assertEqual(connection.execute.call_count, 2)
        update_sql, update_args = connection.execute.call_args.args
        self.assertIn("UPDATE academy_state", update_sql)
        self.assertEqual(update_args[0].obj, loaded)

    def test_change_upgrades_before_feature_callback_and_saves_existing_data(self):
        old_state = {
            "settings": {"task_points": {"wake": 9}},
            "ledger": [{"key": "earned", "points": 8}],
            "diary": [{"id": "kept"}],
            "finance": {"college": {"saved": True}},
        }
        insert = Mock()
        select = Mock()
        select.fetchone.return_value = (old_state,)
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        connection.execute.side_effect = [insert, select, None]
        observed = {}

        def update(state):
            observed.update(copy.deepcopy(state))
            state["settings"]["conversion"] = 21

        with patch.object(store, "connection", return_value=connection):
            store.change(update)

        self.assertEqual(observed["settings"]["task_points"]["wake"], 9)
        self.assertIn("social_supports", observed["settings"])
        self.assertEqual(observed["ledger"], old_state["ledger"])
        self.assertEqual(observed["diary"], old_state["diary"])
        self.assertEqual(observed["finance"], old_state["finance"])
        saved = connection.execute.call_args.args[1][0].obj
        self.assertEqual(saved["settings"]["conversion"], 21)
        self.assertEqual(saved["diary"], old_state["diary"])


if __name__ == "__main__":
    unittest.main()

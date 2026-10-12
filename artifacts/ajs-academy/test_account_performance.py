import csv
import io
import unittest
from unittest.mock import patch, MagicMock
from account_performance import FIELDS, parse_statement_csv, export_statement_csv, reconcile, money_weighted
from statement_import import PRESETS, normalize_broker, review_statement, read_broker_csv, stage_statement


def row(kind, day, **kw):
    return dict(type=kind, date=day, **kw)


def parse(records, prefix="r"):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=FIELDS)
    writer.writeheader()
    for i, record in enumerate(records):
        writer.writerow(dict(id=f"{prefix}{i}", **record))
    return parse_statement_csv(out.getvalue().encode())


def fixture():
    return [
        row("balance", "2024-01-01", amount=2000, basis=1000),
        row("position", "2024-01-01", symbol="AAA", quantity=10, amount=1000),
        row("lot", "2024-01-01", symbol="AAA", quantity=6, basis=300, acquired="2020-01-01"),
        row("lot", "2024-01-01", symbol="AAA", quantity=4, basis=400, acquired="2021-01-01"),
        row("deposit", "2024-02-01", amount=100),
        row("split", "2024-03-01", symbol="AAA", quantity=2, other_quantity=1),
        row("sell", "2024-04-01", symbol="AAA", quantity=14, amount=1000),
        row("income", "2024-05-01", amount=20),
        row("fee", "2024-05-02", amount=5),
        row("balance", "2025-01-01", amount=2515, basis=2115),
        row("position", "2025-01-01", symbol="AAA", quantity=6, amount=400),
    ]


class PerformanceTests(unittest.TestCase):
    def test_fifo_split_and_growth_excludes_deposits(self):
        result = reconcile(parse(fixture()))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["realized_total"], 600)
        self.assertEqual(result["growth"], 415)
        self.assertEqual(result["allocations"][0]["Cost basis"], 300)
        self.assertEqual(result["allocations"][0]["Unrealized gain"], 100)
        self.assertAlmostEqual(sum(r["Allocation %"] for r in result["allocations"]), 100)
        self.assertIsNotNone(result["mwr"])

    def test_export_round_trip(self):
        rows = parse(fixture())
        self.assertEqual(parse_statement_csv(export_statement_csv(rows).encode()), rows)

    def test_missing_lot_and_current_position_block_all_metrics(self):
        for index in (2, 10):
            records = fixture()
            records.pop(index)
            result = reconcile(parse(records))
            self.assertFalse(result["ok"])
            self.assertNotIn("realized_total", result)

    def test_cash_or_valuation_mismatch_blocks(self):
        for field in ("basis", "amount"):
            records = fixture()
            records[9][field] += 1
            self.assertFalse(reconcile(parse(records))["ok"])

    def test_exchange_preserves_basis_and_acquisition_order(self):
        records = [
            row("balance", "2024-01-01", amount=100, basis=0),
            row("position", "2024-01-01", symbol="OLD", quantity=10, amount=100),
            row("lot", "2024-01-01", symbol="OLD", quantity=10, basis=50, acquired="2020-01-01"),
            row("exchange", "2024-02-01", symbol="OLD", quantity=10, other_symbol="NEW", other_quantity=20),
            row("balance", "2024-06-01", amount=120, basis=0),
            row("position", "2024-06-01", symbol="NEW", quantity=20, amount=120),
            row("sell", "2024-07-01", symbol="NEW", quantity=10, amount=80),
            row("balance", "2025-01-01", amount=160, basis=80),
            row("position", "2025-01-01", symbol="NEW", quantity=10, amount=80),
        ]
        result = reconcile(parse(records))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["realized_total"], 55)
        self.assertEqual(result["growth"], 60)
        self.assertEqual(result["history"][1]["Investment growth"], 20)

    def test_in_kind_transfers_not_profit(self):
        records = [
            row("balance", "2024-01-01", amount=0, basis=0),
            row("transfer_in", "2024-02-01", symbol="AAA", quantity=10, amount=100, basis=40, acquired="2020-01-01"),
            row("transfer_out", "2024-03-01", symbol="AAA", quantity=5, amount=60),
            row("balance", "2025-01-01", amount=60, basis=0),
            row("position", "2025-01-01", symbol="AAA", quantity=5, amount=60),
        ]
        result = reconcile(parse(records))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["growth"], 20)
        self.assertEqual(result["realized_total"], 0)
        self.assertEqual(result["allocations"][0]["Cost basis"], 20)

    def test_cancelled_sale_does_not_consume_fifo_lots(self):
        records = fixture()
        records.insert(5, row("sell", "2024-02-02", symbol="AAA", quantity=10, amount=300))
        records.insert(6, row("cancel", "2024-02-03", ref="r5"))
        result = reconcile(parse(records))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["realized_total"], 600)
        records[6]["ref"] = "missing"
        self.assertFalse(reconcile(parse(records))["ok"])

    def test_deposits_only_do_not_create_return(self):
        records = [row("balance", "2024-01-01", amount=100, basis=100),
                   row("deposit", "2024-03-01", amount=100),
                   row("withdraw", "2024-06-01", amount=20),
                   row("balance", "2025-01-01", amount=180, basis=180)]
        result = reconcile(parse(records))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["growth"], 0)
        self.assertAlmostEqual(result["mwr"], 0)

    def test_xirr_dates_and_ambiguous_flows(self):
        rate = money_weighted([("2023-01-01", -100), ("2024-01-01", 110)])
        self.assertAlmostEqual(rate, ((1.1 ** (365.25 / 365)) - 1)*100)
        self.assertIsNone(money_weighted([("2023-01-01", -100), ("2023-02-01", 230),
                                        ("2023-03-01", -132), ("2024-01-01", 1)]))
        self.assertIsNone(money_weighted([("2023-01-01", -100)]))

    def test_unknown_nonfinite_and_duplicate_rows_rejected(self):
        for record in [row("mystery", "2024-01-01"),
                       row("balance", "2024-01-01", amount="nan", basis=0),
                       row("balance", "2024-01-01", amount="inf", basis=0),
                       row("balance", "2024-01-01", amount=-1, basis=0),
                       row("buy", "2024-02-01", symbol="AAA", quantity=0, amount=1)]:
            with self.assertRaises(ValueError):
                parse([record])
        text = export_statement_csv(parse(fixture())).replace("r1,", "r0,")
        with self.assertRaises(ValueError):
            parse_statement_csv(text.encode())

    def test_intermediate_checkpoint_must_reconcile(self):
        records = fixture()
        records += [row("balance", "2024-02-01", amount=2101, basis=1100),
                    row("position", "2024-02-01", symbol="AAA", quantity=10, amount=1000)]
        self.assertFalse(reconcile(parse(records))["ok"])

    def test_activity_outside_window_rejected(self):
        for day in ("2024-01-01", "2026-01-01"):
            records = fixture()
            records[4]["date"] = day
            self.assertFalse(reconcile(parse(records))["ok"])

    def test_child_render_has_only_percentage_table_and_no_download_controls(self):
        import finance_views
        state = {"finance": {"custody_statements": {"confirmed": True, "rows": parse(fixture())}}}
        ui = MagicMock()
        with patch.object(finance_views, "st", ui):
            finance_views.child_performance(state, "custody")
        frame = ui.table.call_args.args[0]
        self.assertEqual(list(frame.columns), ["Share of savings"])
        self.assertTrue(all(value.endswith("%") for value in frame["Share of savings"]))
        ui.dataframe.assert_not_called()
        ui.download_button.assert_not_called()
        ui.file_uploader.assert_not_called()
        self.assertNotIn("$", str(ui.mock_calls))


class BrokerImportTests(unittest.TestCase):
    def broker(self, records, broker="Charles Schwab", mapping=None):
        out = io.StringIO()
        mapping = mapping or PRESETS[broker]
        writer = csv.DictWriter(out, fieldnames=list(mapping.values()))
        writer.writeheader()
        for record in records:
            writer.writerow({mapping[k]: v for k, v in record.items()})
        return normalize_broker(out.getvalue().encode(), broker, mapping)

    def test_presets_and_overridden_columns_normalize_without_holdings(self):
        for broker, action in [("Charles Schwab", "Buy"), ("Fidelity", "YOU BOUGHT TEST FUND (AAA)")]:
            result = self.broker([dict(type=action, date="02/01/2024", symbol="aaa",
                                       quantity="10", amount="($1,000.00)")], broker)
            self.assertEqual(result["issues"], [])
            self.assertEqual(result["rows"][0]["type"], "buy")
            self.assertEqual(result["rows"][0]["amount"], 1000)
            self.assertEqual(result["rows"][0]["date"], "2024-02-01")
            self.assertEqual(result["rows"][0]["symbol"], "AAA")
            self.assertFalse(review_statement(result["rows"])["ok"])
        mapping = {k: k.upper() for k in PRESETS["Charles Schwab"]}
        result = self.broker([dict(type="Sell", date="2024-03-01", symbol="AAA",
                                   quantity="-2", amount="$25")], mapping=mapping)
        self.assertEqual(result["rows"][0]["quantity"], 2)

    def test_unsupported_and_malformed_rows_remain_in_preview(self):
        result = self.broker([
            dict(type="Stock Merger", date="02/01/2024", symbol="AAA", quantity="1", amount="0"),
            dict(type="Buy", date="not a date", symbol="AAA", quantity="1", amount="1"),
            dict(type="Sell", date="02/01/2024", symbol="AAA", quantity="1", amount="-1"),
            dict(type="Cash Dividend", date="02/01/2024", symbol="AAA", quantity="2", amount="5"),
            dict(type="Buy", date="02/01/2024", symbol="AAA", quantity="1", amount="nan"),
        ])
        self.assertEqual(len(result["preview"]), 5)
        self.assertEqual(len(result["issues"]), 5)
        self.assertEqual(result["rows"], [])
        for line, issue in enumerate(result["issues"], 2):
            self.assertIn(f"line {line}", issue)

    def test_duplicates_even_with_different_ids_block(self):
        records = parse(fixture())
        records.append(dict(records[4], id="another-id"))
        review = review_statement(records)
        self.assertFalse(review["ok"])
        self.assertIn("possible duplicate", " ".join(review["issues"]))
        self.assertIn("line 6", " ".join(review["issues"]))
        records[-1]["id"] = records[4]["id"]
        self.assertIn("duplicate ID", " ".join(review_statement(records)["issues"]))

    def test_opening_lot_issue_names_source_row_and_symbol(self):
        records = fixture()
        records.pop(2)
        result = review_statement(parse(records))
        self.assertFalse(result["ok"])
        self.assertIn("Statement CSV line 3", result["issues"][0])
        self.assertIn("opening tax lots for AAA", result["issues"][0])

    def test_broker_and_statement_evidence_reconcile(self):
        activity = self.broker([dict(type="Buy", date="02/01/2024", symbol="AAA",
                                     quantity="10", amount="-100")])
        supporting = parse([
            row("balance", "2024-01-01", amount=200, basis=200),
            row("balance", "2025-01-01", amount=220, basis=100),
            row("position", "2025-01-01", symbol="AAA", quantity=10, amount=120),
        ])
        self.assertTrue(review_statement(activity["rows"] + supporting)["ok"])
        self.assertFalse(review_statement(activity["rows"] + supporting[:-1])["ok"])

    def test_append_new_period_uses_saved_history_without_reuploading_it(self):
        saved = parse(fixture())
        new_period = parse([
            row("deposit", "2025-02-01", amount=100),
            row("balance", "2025-03-01", amount=2615, basis=2215),
            row("position", "2025-03-01", symbol="AAA", quantity=6, amount=400),
        ], prefix="new")
        staged = stage_statement(saved, new_period, "append")
        self.assertTrue(staged["ok"], staged["issues"])
        self.assertEqual(staged["summary"]["retained"], len(saved))
        self.assertEqual(staged["summary"]["incoming"], len(new_period))
        self.assertEqual(staged["summary"]["prior_end"], "2025-01-01")
        self.assertEqual(staged["rows"][:len(saved)], saved)
        report = reconcile(staged["rows"])
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["end"], "2025-03-01")
        self.assertEqual(len(report["history"]), 3)

    def test_append_blocks_cross_period_duplicates_and_old_dates(self):
        saved = parse(fixture())
        duplicate = [dict(saved[4])]
        staged = stage_statement(saved, duplicate, "append", incoming_sources=["February activity"])
        self.assertFalse(staged["ok"])
        self.assertIn("strictly later", " ".join(staged["issues"]))
        self.assertIn("possible duplicate", " ".join(staged["issues"]))

    def test_append_requires_explicit_new_positions_not_activity_inference(self):
        saved = parse(fixture())
        new_period = parse([
            row("deposit", "2025-02-01", amount=100),
            row("balance", "2025-03-01", amount=2615, basis=2615),
        ], prefix="new")
        staged = stage_statement(saved, new_period, "append")
        self.assertFalse(staged["ok"])
        self.assertIn("units for AAA", " ".join(staged["issues"]))

    def test_append_requires_confirmed_saved_history_and_replace_is_explicit(self):
        saved = parse(fixture())
        new_period = parse([
            row("balance", "2025-03-01", amount=1, basis=1),
            row("balance", "2025-04-01", amount=1, basis=1),
        ], prefix="new")
        blocked = stage_statement(saved, new_period, "append", existing_confirmed=False)
        self.assertFalse(blocked["ok"])
        replacement = stage_statement(saved, new_period, "replace")
        self.assertEqual(replacement["summary"]["retained"], 0)
        self.assertEqual(replacement["rows"], new_period)

    def test_bad_headers_mapping_and_size(self):
        for raw in (b"Date,Date\n1,2\n", b"\xff", b"x" * 2_000_001):
            with self.assertRaises(ValueError):
                read_broker_csv(raw)
        with self.assertRaises(ValueError):
            normalize_broker(b"Date,Action\n01/01/2024,Buy\n", "Charles Schwab", PRESETS["Charles Schwab"])

    def test_save_requires_ready_and_confirmation_and_keeps_previous_on_failure(self):
        import finance_views
        state = {"finance": {}}
        for ready, confirmed in ((False, True), (True, False)):
            ui = MagicMock()
            ui.session_state = {"role": "parent", "media_session_nonce": "parent-test-session"}
            ui.checkbox.return_value = confirmed
            ui.button.return_value = True
            with patch.object(finance_views, "st", ui), patch.object(
                    finance_views.secure_media, "download_link"), patch.object(
                    finance_views, "prepare_import",
                    return_value=(parse(fixture()), ready, "rev", "replace", parse(fixture()))), patch.object(
                    finance_views.db, "change") as change:
                finance_views.parent_statements(state, "custody")
                change.assert_not_called()
        ui = MagicMock()
        ui.session_state = MagicMock()
        ui.session_state.get.side_effect = lambda key, default=None: (
            "parent" if key == "role" else "parent-test-session" if key == "media_session_nonce" else default
        )
        ui.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        ui.checkbox.return_value = True
        ui.button.side_effect = [True, False]
        with patch.object(finance_views, "st", ui), patch.object(
                finance_views.secure_media, "download_link"), patch.object(
                finance_views, "prepare_import",
                return_value=(parse(fixture()), True, "rev", "replace", parse(fixture()))), patch.object(
                finance_views.db, "change") as change:
            finance_views.parent_statements(state, "custody")
            change.assert_called_once()
            self.assertFalse(ui.button.call_args.kwargs["disabled"])
            change.call_args.args[0](state)
            self.assertTrue(state["finance"]["custody_statements"]["confirmed"])

    def test_append_save_combines_only_after_confirmed_preview_matches_saved_copy(self):
        import finance_views
        saved = parse(fixture())
        uploaded = parse([
            row("deposit", "2025-02-01", amount=100),
            row("balance", "2025-03-01", amount=2615, basis=2215),
            row("position", "2025-03-01", symbol="AAA", quantity=6, amount=400),
        ], prefix="new")
        staged = stage_statement(saved, uploaded, "append")
        state = {"finance": {"custody_statements": {
            "rows": saved, "confirmed": True, "saved": "2025-01-01"
        }}}
        ui = MagicMock()
        ui.session_state = MagicMock()
        ui.session_state.get.side_effect = lambda key, default=None: (
            "parent" if key == "role" else "parent-test-session" if key == "media_session_nonce" else default
        )
        ui.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        ui.checkbox.return_value = True
        ui.button.side_effect = [True, False]
        with patch.object(finance_views, "st", ui), patch.object(
                finance_views.secure_media, "download_link"), patch.object(
                finance_views, "prepare_import",
                return_value=(staged["rows"], True, "rev", "append", uploaded)), patch.object(
                finance_views.db, "change", side_effect=lambda update: update(state)):
            finance_views.parent_statements(state, "custody")
        result = state["finance"]["custody_statements"]
        self.assertEqual(result["rows"], saved + uploaded)
        self.assertTrue(review_statement(result["rows"])["ok"])

    def test_stale_preview_does_not_replace_updated_evidence(self):
        import finance_views
        saved = parse(fixture())
        uploaded = parse([
            row("deposit", "2025-02-01", amount=100),
            row("balance", "2025-03-01", amount=2615, basis=2215),
            row("position", "2025-03-01", symbol="AAA", quantity=6, amount=400),
        ], prefix="new")
        state = {"finance": {"custody_statements": {
            "rows": saved, "confirmed": True, "saved": "2025-01-01"
        }}}
        expected = dict(state["finance"]["custody_statements"])
        state["finance"]["custody_statements"] = dict(expected, saved="2025-01-02")
        ui = MagicMock()
        ui.session_state = MagicMock()
        ui.session_state.get.side_effect = lambda key, default=None: (
            "parent" if key == "role" else "parent-test-session" if key == "media_session_nonce" else default
        )
        ui.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        ui.checkbox.return_value = True
        ui.button.side_effect = [True, False]
        original = {"finance": {"custody_statements": expected}}
        with patch.object(finance_views, "st", ui), patch.object(
                finance_views.secure_media, "download_link"), patch.object(
                finance_views, "prepare_import",
                return_value=(saved + uploaded, True, "rev", "append", uploaded)), patch.object(
                finance_views.db, "change", side_effect=lambda update: update(state)):
            finance_views.parent_statements(original, "custody")
        self.assertEqual(state["finance"]["custody_statements"], dict(expected, saved="2025-01-02"))
        self.assertIn("changed while this preview was open", str(ui.error.call_args))


if __name__ == "__main__":
    unittest.main()

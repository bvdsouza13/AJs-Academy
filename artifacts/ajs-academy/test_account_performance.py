import csv
import io
import unittest
from unittest.mock import patch, MagicMock
from account_performance import FIELDS, parse_statement_csv, export_statement_csv, reconcile, money_weighted


def row(kind, day, **kw):
    return dict(type=kind, date=day, **kw)


def parse(records):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=FIELDS)
    writer.writeheader()
    for i, record in enumerate(records):
        writer.writerow(dict(id=f"r{i}", **record))
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


if __name__ == "__main__":
    unittest.main()

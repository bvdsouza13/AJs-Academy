"""Statement-backed, long-only FIFO accounting. No prices inferred from trades.

The parent supplies a complete normalized ledger, not a holdings reconstruction
from the broker activity export. All checkpoints must reconcile before release.
"""
import csv
import io
import math
from collections import defaultdict
from datetime import date

FIELDS = "type,date,id,ref,symbol,quantity,amount,basis,other_symbol,other_quantity,acquired".split(",")
TYPES = {"balance", "position", "lot", "buy", "sell", "deposit", "withdraw",
         "income", "fee", "transfer_in", "transfer_out", "exchange", "split", "cancel"}
NUMBERS = {"quantity", "amount", "basis", "other_quantity"}
TEMPLATE = ",".join(FIELDS) + "\n"
GUIDE = """
Use ISO dates (YYYY-MM-DD), USD, positive numbers and unique IDs. No account
numbers or personal identifiers. Each balance is an end-of-day statement:
`amount` = total account value; `basis` = cash. Supply a `position` for every
security on each balance date: symbol, quantity, amount = statement market value.
Cash belongs only in the balance row, never in positions. Include at least two
balance dates. Empty security positions are valid for a cash-only account.

Opening `lot` rows: date = opening balance date; symbol, quantity, basis = total
remaining tax cost, acquired = original acquisition date. Include ALL opening
lots, even zero-cost lots, in FIFO order for same-day acquisitions.

Activity is strictly AFTER opening and THROUGH closing. Include every movement,
including cash sweeps only when they cross the account boundary; do not double
count internal sweep activity. Same-day activity uses CSV row order.
• buy / sell: symbol, quantity, amount = net cash paid / received (including fees).
• deposit / withdraw: amount = external cash movement.
• income / fee: amount = cash received / paid inside the account, not deposits.
• transfer_in: symbol, quantity, amount = fair market value at transfer,
  basis = carried tax cost, acquired = original acquisition date; one row per lot.
• transfer_out: symbol, quantity, amount = fair market value at transfer;
  removes FIFO basis without realizing a gain. Specific-lot transfers are unsupported.
• exchange: symbol, quantity delivered, other_symbol, other_quantity received;
  carries FIFO cost and original acquisition dates. ONLY tax-free, no-cash exchanges.
  Taxable exchanges must be sell + buy; cash-in-lieu must be a separate sell.
• split: symbol, quantity = numerator, other_quantity = denominator (e.g. 2 and 1).
• cancel: ref = ID of the fully reversed buy or sell. Both rows are excluded;
  partial corrections must be supplied as the corrected net trade instead.

Other fields must be blank. Unknown activity, short sales, negative cash,
unreconciled checkpoints and unsupported corporate actions block results.
Do not omit them to get a passing result. Include intermediate dated statements
to see historical growth; 529 conversions use exchange, not deposits or gains.
This checks consistency of parent-supplied evidence; it is not broker verification
or tax advice. Review the normalized ledger against the original statements.
"""


ALLOWED = {
        "balance": {"amount", "basis"},
        "position": {"symbol", "quantity", "amount"},
        "lot": {"symbol", "quantity", "basis", "acquired"},
        "buy": {"symbol", "quantity", "amount"},
        "sell": {"symbol", "quantity", "amount"},
        "deposit": {"amount"}, "withdraw": {"amount"},
        "income": {"amount"}, "fee": {"amount"},
        "transfer_in": {"symbol", "quantity", "amount", "basis", "acquired"},
        "transfer_out": {"symbol", "quantity", "amount"},
        "exchange": {"symbol", "quantity", "other_symbol", "other_quantity"},
        "split": {"symbol", "quantity", "other_quantity"}, "cancel": {"ref"},
}


def export_statement_csv(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=FIELDS)
    writer.writeheader()
    for row in rows:
        fields = ALLOWED[row["type"]] | {"type", "date", "id"}
        writer.writerow({k: row[k] if k in fields else "" for k in FIELDS})
    return output.getvalue()


def parse_statement_csv(raw):
    if len(raw) > 2_000_000:
        raise ValueError("Statement CSV must be smaller than 2 MB.")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames != FIELDS:
        raise ValueError("Use the exact columns and order in the statement template.")
    result, ids = [], set()
    for line, row in enumerate(reader, 2):
        try:
            if None in row or any(v is None for v in row.values()):
                raise ValueError("Wrong number of columns.")
            row = {k: v.strip() for k, v in row.items()}
            kind = row["type"]
            if kind not in TYPES:
                raise ValueError("Unknown row type.")
            if not row["id"] or row["id"] in ids:
                raise ValueError("Every row needs a unique ID.")
            ids.add(row["id"])
            date.fromisoformat(row["date"])
            permitted = ALLOWED[kind] | {"type", "date", "id"}
            if any(v for k, v in row.items() if k not in permitted):
                raise ValueError("Unexpected field for this row type.")
            for k in ALLOWED[kind]:
                if not row[k]:
                    raise ValueError(f"Missing {k}; use explicit 0 for zero values.")
            for k in NUMBERS:
                row[k] = float(row[k]) if row[k] else 0.
                if not math.isfinite(row[k]) or row[k] < 0:
                    raise ValueError("Numbers must be finite and nonnegative.")
            if "quantity" in ALLOWED[kind] and row["quantity"] <= 0:
                raise ValueError("Quantity must be positive; omit closed positions.")
            if "other_quantity" in ALLOWED[kind] and row["other_quantity"] <= 0:
                raise ValueError("Other quantity must be positive.")
            if row["acquired"]:
                date.fromisoformat(row["acquired"])
                if date.fromisoformat(row["acquired"]) > date.fromisoformat(row["date"]):
                    raise ValueError("Acquisition date cannot follow the row date.")
            # Canonical dates are essential because reconciliation sorts ISO strings.
            row["date"] = date.fromisoformat(row["date"]).isoformat()
            if row["acquired"]:
                row["acquired"] = date.fromisoformat(row["acquired"]).isoformat()
            result.append(row)
        except (ValueError, OverflowError) as exc:
            raise ValueError(f"CSV line {line}: {exc}") from None
    if not result:
        raise ValueError("No statement records supplied.")
    return result


def money_weighted(flows):
    """Conservative unique-root XIRR; reject nonconventional/ambiguous flows."""
    combined = defaultdict(float)
    for day, value in flows:
        combined[day] += value
    flows = sorted((date.fromisoformat(d), v) for d, v in combined.items() if abs(v) > 1e-9)
    signs = [v > 0 for _, v in flows]
    if len(flows) < 2 or signs[0] or not signs[-1]:
        return None
    if sum(a != b for a, b in zip(signs, signs[1:])) != 1:
        return None
    start = flows[0][0]
    # Solve in log(1+r), avoiding the singularity at -100%.
    def npv(log_rate):
        exponents = [-log_rate * (d-start).days/365.25 for d, _ in flows]
        offset = max(exponents)
        scale = max(abs(v) for _, v in flows)
        return math.fsum(v / scale * math.exp(e - offset)
                         for (_, v), e in zip(flows, exponents))
    lo, hi = -20., 20.
    if npv(lo) <= 0 or npv(hi) >= 0:
        return None
    for _ in range(160):
        mid = (lo + hi) / 2
        if npv(mid) > 0:
            lo = mid
        else:
            hi = mid
    return math.expm1((lo + hi)/2) * 100


def reconcile(rows):
    """Return no financial metrics unless every supplied checkpoint reconciles."""
    try:
        result = _reconcile(rows)
        def finite(value):
            if isinstance(value, float):
                return math.isfinite(value)
            if isinstance(value, dict):
                return all(finite(v) for v in value.values())
            if isinstance(value, list):
                return all(finite(v) for v in value)
            return True
        if not finite(result):
            raise ValueError("Numeric range exceeded; check quantities and amounts.")
        return result
    except (ValueError, ArithmeticError) as exc:
        return {"ok": False, "issues": [str(exc)]}


def _reconcile(rows):
    balances = sorted((r for r in rows if r["type"] == "balance"), key=lambda r: r["date"])
    if len(balances) < 2 or len({r["date"] for r in balances}) != len(balances):
        raise ValueError("Supply at least two balances on distinct dates.")
    start, end = balances[0]["date"], balances[-1]["date"]
    days = {r["date"] for r in balances}
    positions = defaultdict(dict)
    lots = defaultdict(list)
    activity = []
    for r in rows:
        kind, day, symbol = r["type"], r["date"], r["symbol"]
        if kind == "position":
            if day not in days or symbol in positions[day]:
                raise ValueError(f"Record {r['id']}: positions need a balance on the same date and one row per symbol.")
            positions[day][symbol] = r
        elif kind == "lot":
            if day != start:
                raise ValueError(f"Record {r['id']}: opening lots must use the opening balance date.")
            lots[symbol].append([r["quantity"], r["basis"], r["acquired"]])
        elif kind != "balance":
            if not start < day <= end:
                raise ValueError(f"Record {r['id']}: activity must fall after opening and on/before closing.")
            activity.append(r)
    activity.sort(key=lambda r: r["date"])  # stable, preserving same-day row order
    by_id = {r["id"]: r for r in activity}
    cancelled = set()
    for r in activity:
        if r["type"] == "cancel":
            original = by_id.get(r["ref"])
            if (not original or original["type"] not in {"buy", "sell"}
                    or original["date"] > r["date"] or r["ref"] in cancelled):
                raise ValueError(f"Record {r['id']}: cancellation must reference one earlier, unreversed buy or sell.")
            # Don't retroactively alter a statement that predates reversal.
            if any(original["date"] <= d < r["date"] for d in days):
                raise ValueError(f"Record {r['id']}: cancellation crosses a statement date; provide corrected statement evidence.")
            cancelled.add(r["ref"])
    cash = balances[0]["basis"]
    realized = defaultdict(float)
    flows = [(start, -balances[0]["amount"])]
    deposits = withdrawals = transfers_in = transfers_out = 0.
    history = []

    def take(symbol, quantity):
        remaining, removed = quantity, []
        lots[symbol].sort(key=lambda lot: lot[2])
        for lot in lots[symbol]:
            if remaining <= 1e-8:
                break
            if lot[0] <= 1e-8:
                continue
            q = min(lot[0], remaining)
            basis = lot[1] * q / lot[0]
            removed.append([q, basis, lot[2]])
            lot[0] -= q
            lot[1] -= basis
            remaining -= q
        if remaining > 1e-6:
            raise ValueError(f"Record {r['id']}: insufficient reconciled lots for {symbol}; check opening lots and transfers.")
        return removed

    def checkpoint(b):
        day = b["date"]
        supplied = positions[day]
        for symbol in set(lots) | set(supplied):
            actual = sum(l[0] for l in lots[symbol])
            expected = supplied.get(symbol, {}).get("quantity", 0)
            if abs(actual - expected) > 1e-6:
                raise ValueError(f"Record {supplied.get(symbol, b)['id']} ({day}): units for {symbol} do not reconcile with the statement.")
        if abs(cash - b["basis"]) > .02:
            raise ValueError(f"Record {b['id']} ({day}): cash does not reconcile; check deposits, fees and trade cash.")
        if abs(b["basis"] + sum(p["amount"] for p in supplied.values()) - b["amount"]) > .02:
            raise ValueError(f"Record {b['id']} ({day}): position values plus cash do not equal the dated balance.")
        net = deposits - withdrawals + transfers_in - transfers_out
        history.append({"Date": day, "Balance": b["amount"],
                        "Net external funding": net,
                        "Investment growth": b["amount"] - balances[0]["amount"] - net})

    checkpoint(balances[0])
    cursor = 0
    for b in balances[1:]:
        while cursor < len(activity) and activity[cursor]["date"] <= b["date"]:
            r = activity[cursor]
            cursor += 1
            kind, symbol, q, amount = r["type"], r["symbol"], r["quantity"], r["amount"]
            if kind == "cancel" or r["id"] in cancelled:
                continue
            if kind in {"buy", "transfer_in"}:
                lots[symbol].append([q, amount if kind == "buy" else r["basis"],
                                     r["date"] if kind == "buy" else r["acquired"]])
                if kind == "buy":
                    cash -= amount
                else:
                    transfers_in += amount
                    flows.append((r["date"], -amount))
            elif kind in {"sell", "transfer_out", "exchange"}:
                removed = take(symbol, q)
                basis = sum(l[1] for l in removed)
                if kind == "sell":
                    cash += amount
                    realized[symbol] += amount - basis
                elif kind == "transfer_out":
                    transfers_out += amount
                    flows.append((r["date"], amount))
                else:
                    if symbol == r["other_symbol"]:
                        raise ValueError(f"Record {r['id']}: exchange symbols must differ; use split for a same-symbol ratio.")
                    for units, cost, acquired in removed:
                        lots[r["other_symbol"]].append([units / q * r["other_quantity"], cost, acquired])
            elif kind == "split":
                if sum(l[0] for l in lots[symbol]) <= 1e-8:
                    raise ValueError(f"Record {r['id']}: split has no matching position.")
                for lot in lots[symbol]:
                    lot[0] *= q / r["other_quantity"]
            elif kind in {"deposit", "income"}:
                cash += amount
                if kind == "deposit":
                    deposits += amount
                    flows.append((r["date"], -amount))
            elif kind in {"withdraw", "fee"}:
                cash -= amount
                if kind == "withdraw":
                    withdrawals += amount
                    flows.append((r["date"], amount))
            else:
                raise ValueError("Unsupported activity; results withheld.")
            if cash < -.02:
                raise ValueError(f"Record {r['id']}: negative cash: check same-day activity order or missing funding.")
        checkpoint(b)
    closing = balances[-1]["amount"]
    allocations = []
    for symbol, p in sorted(positions[end].items()):
        basis = sum(l[1] for l in lots[symbol])
        allocations.append({"Symbol": symbol, "Units": p["quantity"], "Market value": p["amount"],
                            "Cost basis": basis, "Unrealized gain": p["amount"] - basis,
                            "Allocation %": p["amount"] / closing * 100 if closing else 0})
    allocations.append({"Symbol": "Cash", "Units": None, "Market value": cash,
                        "Cost basis": cash, "Unrealized gain": 0.,
                        "Allocation %": cash / closing * 100 if closing else 0})
    flows.append((end, closing))
    return {"ok": True, "issues": [], "start": start, "end": end, "balance": closing,
            "allocations": allocations, "realized": dict(realized),
            "realized_total": sum(realized.values()), "deposits": deposits,
            "withdrawals": withdrawals, "transfers_in": transfers_in,
            "transfers_out": transfers_out, "growth": history[-1]["Investment growth"],
            "mwr": money_weighted(flows), "history": history}

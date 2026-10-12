"""Conservative broker CSV normalization; never reconstruct statement holdings."""
import csv
import io
from datetime import datetime

from account_performance import FIELDS, parse_statement_csv, reconcile

PRESETS = {
    "Fidelity": {"date": "Run Date", "type": "Action", "symbol": "Symbol",
                 "quantity": "Quantity", "amount": "Amount ($)"},
    "Charles Schwab": {"date": "Date", "type": "Action", "symbol": "Symbol",
                       "quantity": "Quantity", "amount": "Amount"},
}
# Deliberately narrow: ambiguous transfers, reinvestments, cancellations and
# corporate actions need explicit parent-reviewed normalized evidence.
ACTIONS = {
    "Fidelity": {"YOU BOUGHT": "buy", "YOU SOLD": "sell",
                 "DIVIDEND RECEIVED": "income", "INTEREST EARNED": "income"},
    "Charles Schwab": {"BUY": "buy", "SELL": "sell",
                       "CASH DIVIDEND": "income", "CREDIT INTEREST": "income",
                       "SERVICE FEE": "fee"},
}


def read_broker_csv(raw):
    if len(raw) > 2_000_000:
        raise ValueError("Broker CSV must be smaller than 2 MB.")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
        headers = reader.fieldnames
        if not headers or len(headers) != len(set(headers)):
            raise ValueError("A unique header row is required at the top of the CSV.")
        records = list(reader)
        if not records:
            raise ValueError("No broker records supplied.")
        return headers, records
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("Use a UTF-8 CSV with a header row and valid CSV quoting.") from exc


def _date(value):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError("Date must be YYYY-MM-DD or MM/DD/YYYY; settlement qualifiers need review.")


def normalize_broker(raw, broker, mapping):
    """Return every source row in preview, plus blocking row-specific issues."""
    headers, records = read_broker_csv(raw)
    if broker not in PRESETS:
        raise ValueError("Choose a supported broker.")
    required = {"date", "type", "symbol", "quantity", "amount"}
    if any(mapping.get(k) not in headers for k in required):
        raise ValueError("Map date, action, symbol, quantity and net cash amount columns.")
    selected = [v for v in mapping.values() if v]
    if len(selected) != len(set(selected)):
        raise ValueError("Each source column may be mapped only once.")
    rows, sources, preview, issues = [], [], [], []
    for line, source in enumerate(records, 2):
        label = f"Broker CSV line {line}"
        normalized = {k: "" for k in FIELDS}
        try:
            if None in source or any(v is None for v in source.values()):
                raise ValueError("Wrong number of columns; no rows are silently skipped.")
            action = source[mapping["type"]].strip().upper()
            kind = ACTIONS[broker].get(action)
            if not kind and broker == "Fidelity":
                # Fidelity commonly appends a security description to these labels.
                kind = next((value for label, value in ACTIONS[broker].items()
                             if action.startswith(label + " ")), None)
            if not kind:
                raise ValueError(f"Unsupported action '{action}'. Corporate actions, transfers, "
                                 "reinvestments and corrections require explicit normalized review.")
            normalized.update(type=kind, date=_date(source[mapping["date"]].strip()),
                              id=source[mapping["id"]].strip() if mapping.get("id") else f"broker-{line}")
            for field in ("symbol", "quantity", "amount"):
                value = source[mapping[field]].strip()
                if field == "symbol":
                    normalized[field] = value.upper()
                elif value:
                    value = value.replace("$", "").replace(",", "")
                    if value.startswith("(") and value.endswith(")"):
                        value = "-" + value[1:-1]
                    number = float(value)
                    if field == "amount" and number < 0 and kind not in {"buy", "fee"}:
                        raise ValueError("Negative proceeds may be a reversal; review the original record.")
                    if field == "quantity" and number < 0 and kind != "sell":
                        raise ValueError("Negative quantity may be a reversal; review the original record.")
                    normalized[field] = str(abs(number))
            if kind in {"income", "fee"}:
                if normalized["quantity"] and float(normalized["quantity"]) != 0:
                    raise ValueError("Cash activity with a quantity requires review (possible reinvestment).")
                normalized["symbol"] = normalized["quantity"] = ""
            out = io.StringIO()
            writer = csv.DictWriter(out, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerow(normalized)
            parsed = parse_statement_csv(out.getvalue().encode())[0]
            rows.append(parsed)
            sources.append(label)
            preview.append({"Source": label, "Status": "Normalized — review required", **normalized})
        except (ValueError, OverflowError) as exc:
            issues.append(f"{label}: {exc}")
            preview.append({"Source": label, "Status": str(exc), **normalized})
    return {"rows": rows, "sources": sources, "preview": preview, "issues": issues}


def review_statement(rows, sources=None):
    """Pre-save checks supplement, never replace, full reconciliation."""
    sources = sources or [f"Statement CSV line {i}" for i in range(2, len(rows) + 2)]
    issues, ids, fingerprints = [], {}, {}
    for r, source in zip(rows, sources):
        if r["id"] in ids:
            issues.append(f"{source}: duplicate ID '{r['id']}' also at {ids[r['id']]}.")
        ids[r["id"]] = source
        fingerprint = tuple(r[k] for k in FIELDS if k != "id")
        if fingerprint in fingerprints:
            issues.append(f"{source}: possible duplicate record also at {fingerprints[fingerprint]}; "
                          "resolve against the original statement before saving.")
        fingerprints[fingerprint] = source
    balances = [r for r in rows if r["type"] == "balance"]
    if balances:
        opening = min(r["date"] for r in balances)
        for r, source in zip(rows, sources):
            if r["type"] == "position" and r["date"] == opening:
                lots = [(lot, src) for lot, src in zip(rows, sources)
                        if lot["type"] == "lot" and lot["date"] == opening and lot["symbol"] == r["symbol"]]
                if abs(sum(lot["quantity"] for lot, _ in lots) - r["quantity"]) > 1e-6:
                    issues.append(f"{source}: missing or mismatched opening tax lots for {r['symbol']}; "
                                  f"statement requires {r['quantity']:g} units. "
                                  f"Review {', '.join(src for _, src in lots) or 'opening lot entries'}.")
    report = reconcile(rows)
    issues.extend(report["issues"])
    return {"ok": not issues and report["ok"], "issues": issues}


def stage_statement(existing_rows, incoming_rows, mode="replace", incoming_sources=None,
                    existing_confirmed=True):
    """Validate a replacement or a later period against saved statement evidence."""
    incoming_rows = list(incoming_rows)
    incoming_sources = incoming_sources or [
        f"Uploaded statement row {i}" for i in range(1, len(incoming_rows) + 1)
    ]
    if len(incoming_sources) != len(incoming_rows):
        raise ValueError("Each uploaded statement row needs a matching source label.")

    if mode == "replace":
        rows, sources = incoming_rows, incoming_sources
        summary = {"mode": mode, "retained": 0, "incoming": len(incoming_rows),
                   "total": len(incoming_rows), "prior_end": None}
    elif mode == "append":
        if not existing_rows or not existing_confirmed:
            return {"rows": incoming_rows, "sources": incoming_sources, "issues": [
                "Append requires previously saved, parent-confirmed statement evidence."
            ], "ok": False,
                "summary": {"mode": mode, "retained": len(existing_rows),
                            "incoming": len(incoming_rows), "total": len(existing_rows) + len(incoming_rows),
                            "prior_end": None}}

        prior_report = review_statement(existing_rows)
        prior_balances = [r["date"] for r in existing_rows if r["type"] == "balance"]
        prior_end = max(prior_balances) if prior_balances else None
        existing_sources = [f"Previously saved ({r['id']})" for r in existing_rows]
        new_period_issues = []
        if not prior_report["ok"]:
            new_period_issues.append(
                "Previously saved statement evidence no longer passes reconciliation; "
                "append is blocked until it is reviewed."
            )
        if prior_end is None:
            new_period_issues.append("Previously saved evidence has no dated closing balance.")
        else:
            if not any(r["type"] == "balance" and r["date"] > prior_end for r in incoming_rows):
                new_period_issues.append(
                    f"Add at least one new dated balance after the saved closing date {prior_end}."
                )
            earlier = [source for r, source in zip(incoming_rows, incoming_sources)
                       if r["date"] <= prior_end]
            if earlier:
                new_period_issues.append(
                    f"Append rows must be strictly later than the saved closing date {prior_end}; "
                    f"review {', '.join(earlier)}."
                )
        rows = list(existing_rows) + incoming_rows
        sources = existing_sources + incoming_sources
        summary = {"mode": mode, "retained": len(existing_rows), "incoming": len(incoming_rows),
                   "total": len(rows), "prior_end": prior_end}
        review = review_statement(rows, sources)
        issues = new_period_issues + review["issues"]
        return {"rows": rows, "sources": sources, "issues": issues,
                "ok": not issues and review["ok"], "summary": summary}
    else:
        raise ValueError("Choose whether to append the new period or replace saved history.")

    review = review_statement(rows, sources)
    return {"rows": rows, "sources": sources, "issues": review["issues"],
            "ok": review["ok"], "summary": summary}


def parse_evidence_table(records):
    """Parse editable supporting evidence without allowing incomplete rows."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(records)
    return parse_statement_csv(out.getvalue().encode())

"""Parent-only import preparation. No persistence until the caller confirms."""
import hashlib
import json
import streamlit as st
import pandas as pd

from account_performance import FIELDS, parse_statement_csv
from statement_import import PRESETS, read_broker_csv, normalize_broker, review_statement, parse_evidence_table


def prepare_import(kind):
    mode = st.selectbox("Statement import format", ["Generic reviewed CSV", *PRESETS], key="format-" + kind)
    upload = st.file_uploader("Upload statement evidence and reconciled ledger" if mode == "Generic reviewed CSV"
                              else "Upload broker activity CSV", type=["csv"], key="statements-" + kind)
    if upload is None:
        return None, False, "empty"
    raw = upload.getvalue()
    token = hashlib.sha256(raw + mode.encode()).hexdigest()[:16]
    rows, sources, issues = [], [], []
    try:
        if mode == "Generic reviewed CSV":
            rows = parse_statement_csv(raw)
            sources = [f"Statement CSV line {i}" for i in range(2, len(rows) + 2)]
            st.dataframe(pd.DataFrame([{"Source": src, **r} for src, r in zip(sources, rows)]), hide_index=True)
        else:
            headers, _ = read_broker_csv(raw)
            st.caption("Presets are starting points, not broker verification. Map trade date (not settlement date) "
                       "and net cash including fees. Only explicit supported actions are converted. "
                       "No current positions or tax lots are inferred from activity.")
            mapping = {}
            with st.expander("Review broker column mapping", expanded=True):
                for field, label in (("date", "Trade date"), ("type", "Action"), ("symbol", "Symbol"),
                                     ("quantity", "Quantity"), ("amount", "Net cash amount"), ("id", "Transaction ID (optional)")):
                    options = [""] + headers
                    default = PRESETS[mode].get(field, "")
                    mapping[field] = st.selectbox(label, options,
                        index=options.index(default) if default in options else 0,
                        key=f"mapping-{kind}-{token}-{field}")
            result = normalize_broker(raw, mode, mapping)
            st.subheader("Normalized activity preview")
            st.dataframe(pd.DataFrame(result["preview"]), hide_index=True)
            rows, sources, issues = result["rows"], result["sources"], result["issues"]
            st.caption("Add dated statement balances, every opening/closing position, and all opening tax lots "
                       "below. You can upload supporting normalized evidence instead. "
                       "Do not add activity already present in the broker file. Unsupported rows block saving; "
                       "use the generic reviewed CSV route for complex activity after reviewing the original evidence.")
            supporting = st.file_uploader("Supporting statement evidence CSV (optional)", type=["csv"],
                                          key=f"support-{kind}-{token}")
            if supporting is not None:
                try:
                    extra = parse_statement_csv(supporting.getvalue())
                except ValueError as exc:
                    raise ValueError(f"Supporting evidence: {exc}") from None
                extra_sources = [f"Supporting CSV line {i}" for i in range(2, len(extra) + 2)]
            else:
                table = st.data_editor(pd.DataFrame(columns=FIELDS, dtype=str),
                                       num_rows="dynamic", hide_index=True,
                                       key=f"support-table-{kind}-{token}",
                                       column_config={"type": st.column_config.SelectboxColumn(
                                           "type", options=["balance", "position", "lot"], required=True)})
                records = table.fillna("").to_dict("records")
                try:
                    extra = parse_evidence_table(records) if records else []
                except ValueError as exc:
                    raise ValueError(f"Supporting table (CSV line 2 = table row 1): {exc}") from None
                extra_sources = [f"Supporting table row {i}" for i in range(1, len(extra) + 1)]
            rows = rows + extra
            sources = sources + extra_sources
            st.subheader("Complete normalized evidence preview")
            st.dataframe(pd.DataFrame([{"Source": src, **r} for src, r in zip(sources, rows)]), hide_index=True)
        review = review_statement(rows, sources)
        issues.extend(review["issues"])
        for issue in issues:
            st.error(issue)
        if not issues:
            st.success("All supplied statement checkpoints reconcile. Review the preview before confirming.")
        # Any data or mapping change requires fresh confirmation.
        token = hashlib.sha256(json.dumps(
            [token, rows, issues, locals().get("mapping")], sort_keys=True).encode()).hexdigest()[:16]
        return rows, not issues, token
    except (ValueError, UnicodeError) as exc:
        st.error(f"{exc} Existing saved evidence has not changed.")
        return None, False, token

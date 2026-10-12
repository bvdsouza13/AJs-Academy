"""Role-safe statement import and account performance display."""
import streamlit as st
import pandas as pd
import finance as fin
import store as db
from statement_import_views import prepare_import
from statement_import import review_statement


def saved_performance(state, kind):
    evidence = state["finance"].get(kind + "_statements")
    if not evidence or not evidence.get("confirmed"):
        return None
    return fin.reconcile(evidence["rows"])


def child_performance(state, kind):
    report = saved_performance(state, kind)
    if not report or not report["ok"]:
        st.info("Your parent is checking the statements before showing your account performance.")
        return
    st.caption(f"Statement-backed account mix · {report['end']} · not live prices")
    # Explicit allowlist: never send amounts, quantities or basis to the child UI.
    st.table(pd.DataFrame([{"Investment": p["Symbol"],
                           "Share of savings": f"{p['Allocation %']:.1f}%"}
                          for p in report["allocations"]]).set_index("Investment"))
    if report["mwr"] is not None:
        st.metric("Yearly account growth rate", f"{report['mwr']:+.1f}%")
        st.caption("Money-weighted annualized return: accounts for when money was added or taken out. Not a prediction.")
    else:
        st.caption("A reliable yearly return could not be determined for these cash-flow dates.")


def parent_statements(state, kind):
    if st.session_state.get("role") != "parent":
        st.stop()
    st.subheader("Reconciled statement performance")
    st.caption("Separate from the original activity export. Results use only the dated statements and complete ledger supplied here.")
    with st.expander("Prepare opening lots, dated statements and activity"):
        st.markdown(fin.GUIDE)
        st.download_button("Download blank statement template", fin.TEMPLATE,
                           "statement-template.csv", "text/csv", key="template-" + kind)
    rows, ready, revision = prepare_import(kind)
    confirmed = st.checkbox(
        "I checked this complete ledger against the original statements, including all "
        "opening lots, external transfers, exchanges, splits, cancellations and closing positions.",
        key=f"attest-{kind}-{revision}", disabled=not ready)
    st.caption("Saving replaces only this account’s statement evidence, not its original transaction export. "
               "Blocked imports leave existing saved evidence unchanged.")
    if st.button("Save statement evidence", key="save-statements-" + kind, disabled=not (ready and confirmed)):
        if not rows or not ready or not confirmed:
            st.error("Resolve all import issues and confirm the statement review first.")
        else:
            try:
                if not review_statement(rows)["ok"]:
                    raise ValueError("Statement review failed; resolve the preview issues before saving.")
                db.change(lambda s: s["finance"].__setitem__(
                    kind + "_statements", {"rows": rows, "confirmed": True, "saved": db.today()}))
                st.session_state.notice = "Statement evidence saved."
                st.rerun()
            except ValueError as exc:
                st.error(f"{exc} Existing saved evidence has not changed.")
            except Exception:
                st.error("Could not save statement evidence. Please try again.")
    evidence = state["finance"].get(kind + "_statements")
    if not evidence:
        st.info("No dated statement evidence yet. Personal gains, allocations and returns are withheld.")
        return
    with st.expander("Manage saved statement evidence"):
        st.download_button("Download normalized evidence",
                           fin.export_statement_csv(evidence["rows"]),
                           kind + "-statement-evidence.csv", "text/csv", key="evidence-" + kind)
        remove = st.checkbox("Confirm removal of this account’s statement evidence", key="remove-confirm-" + kind)
        if st.button("Remove statement evidence", key="remove-" + kind, disabled=not remove):
            db.change(lambda s: s["finance"].pop(kind + "_statements", None))
            st.rerun()
    report = saved_performance(state, kind)
    if not report or not report["ok"]:
        for issue in (report or {}).get("issues", ["Statement review is not confirmed."]):
            st.warning(issue)
        st.info("Performance withheld until all dated balances, cash and positions reconcile.")
        return
    st.success(f"Reconciled against parent-supplied statements: {report['start']} through {report['end']}")
    st.caption("Consistency checked, not independently verified by a broker. No live valuation or tax certification.")
    a, b, c = st.columns(3)
    a.metric("Closing statement balance", f"${report['balance']:,.2f}")
    b.metric("Investment growth (not deposits)", f"${report['growth']:,.2f}")
    c.metric("Annualized money-weighted return",
             f"{report['mwr']:+.2f}%" if report["mwr"] is not None else "Unavailable")
    if report["mwr"] is None:
        st.info("The dated cash flows do not yield a uniquely supported return in the calculation range. No rate is estimated.")
    st.write(f"Cash deposits: ${report['deposits']:,.2f} · Cash withdrawals: ${report['withdrawals']:,.2f}")
    st.write(f"Securities transferred in: ${report['transfers_in']:,.2f} · Transferred out: ${report['transfers_out']:,.2f}")
    st.caption("Transfers use market value on their transfer dates, not tax cost. Growth = closing minus opening value minus net external funding. "
               "Money-weighted return uses actual dates and a 365.25-day year; short periods are annualized.")
    st.metric("FIFO realized gains / losses", f"${report['realized_total']:,.2f}")
    if report["realized"]:
        st.dataframe(pd.DataFrame([{"Symbol": k, "Realized gain": v}
                                  for k, v in report["realized"].items()]), hide_index=True)
    st.caption("FIFO applies carried tax lots; excludes wash-sale and other tax adjustments. "
               "Distributions and fees affect total growth, not FIFO sale gains.")
    st.subheader("Closing allocation and unrealized gains")
    st.dataframe(pd.DataFrame(report["allocations"]), hide_index=True)
    st.subheader("Dated 529 growth" if kind == "college" else "Dated account growth")
    st.dataframe(pd.DataFrame(report["history"]), hide_index=True)
    st.caption("Only supplied, reconciled statement dates are shown. No interpolated history. "
               "External funding includes securities transfers; internal fund conversions are not growth.")

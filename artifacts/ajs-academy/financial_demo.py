"""Reversible financial-only demo overlay; never replaces saved account evidence."""
import copy
from pathlib import Path

import pandas as pd
import streamlit as st

import finance as fin
import store as db
from schools import baseline

DATA_DIR = Path(__file__).with_name("demo-data")
SETTING = "financial_demo_enabled"


def enabled(state):
    return state["settings"].get(SETTING, False)


def view(state):
    """Return an isolated display state; the original persistence state is untouched."""
    if not enabled(state):
        return state
    result = copy.deepcopy(state)
    result["finance"] = {
        kind: fin.parse_csv((DATA_DIR / f"{kind}.csv").read_bytes(), kind)
        for kind in ("custody", "college")
    }
    for key in (
        "custody_balance", "custody_asof", "opening_complete", "goal", "inflation",
        "school_costs", "favorite_school", "residency", "college_years", "college_inflation",
    ):
        result["settings"][key] = copy.deepcopy(db.DEFAULT["settings"][key])
    return result


def label():
    st.info("DEMO financial data — fictional transactions, not your actual accounts.")


def controls(original_state, kind):
    active = enabled(original_state)
    st.caption("Demo mode changes only the financial display. Original exports, balances, "
               "reviewed statements and planning settings remain saved. Other sections are unchanged.")
    action = "Show original financial data" if active else "Show scrambled demo financial data"
    if st.button(action, key=f"financial-demo-toggle-{kind}"):
        db.change(lambda saved: saved["settings"].__setitem__(SETTING, not active))
        st.rerun()
    return active


def parent_report(state, kind):
    """Read-only demo report: no real imports, statements, figures or save actions."""
    label()
    data = state["finance"][kind]
    settings = state["settings"]
    st.caption(f"Demo history: {data['start']} through {data['end']} · "
               f"{len(data['records'])} transactions")
    st.info("Financial editing is unavailable in demo mode. Switch to original financial "
            "data to import statements or change saved account figures.")
    if kind == "college":
        monthly = fin.contribution_summary(data)
        a, b = st.columns(2)
        a.metric("Fictional 529 snapshot balance", f"${data['balance']:,.2f}")
        b.metric("Fictional contributions in export", f"${sum(monthly.values()):,.2f}")
        st.write("Demo portfolio: " + data["fund"])
        st.caption("The file has no dated valuation checkpoint. Contributions are not investment "
                   "growth; fund conversions are internal transfers, not new savings.")
        st.dataframe(pd.DataFrame(
            [{"Month": month, "Demo contributions": amount} for month, amount in monthly.items()]
        ), hide_index=True)
        school = st.selectbox("Try a school in the demo", [s[0] for s in fin.SCHOOLS],
                              key="demo-school-cost")
        residency = st.radio("Try a residency scenario", ["Florida", "California"],
                              horizontal=True, key="demo-residency")
        cost = baseline(school, residency)
        target = fin.future_cost(cost["annual"], settings["college_years"],
                                 settings["college_inflation"])
        st.caption(cost["note"])
        st.caption(f"Demo assumptions: {settings['college_years']} years until enrollment; "
                   f"{settings['college_inflation']}% annual college-cost increase. "
                   "Four years of full cost; no scholarship assumed. Choices here are not saved.")
        st.metric("Illustrative four-year college cost", f"${target:,.0f}")
        st.dataframe(pd.DataFrame([
            {"Assumed annual return": f"{rate}%",
             "Illustrative monthly saving": round(fin.payment(data["balance"], target,
                                                              settings["college_years"], rate))}
            for rate in (3, 5, 7)
        ]), hide_index=True)
        st.caption("Planning scenarios, not predictions or personal financial advice.")
    else:
        st.dataframe(fin.positions(data), hide_index=True)
        st.caption("Fictional net unit changes and cash flows in this export—not current "
                   "holdings, a balance, profit or personal return. Opening positions and "
                   "reconciled valuation statements were not supplied, so no account return "
                   "or age-21 savings percentage is invented.")
        target = settings["goal"] * (1 + settings["inflation"] / 100) ** 13
        st.subheader("Try the age-21 savings example")
        st.caption("Illustrative assumptions only: start at $0, save for 13 years, "
                   f"target ${settings['goal']:,.0f} in today's dollars, and "
                   f"{settings['inflation']}% inflation. The $0 starting point is not "
                   "a balance derived from this activity file.")
        st.metric("Illustrative inflation-adjusted target", f"${target:,.0f}")
        st.dataframe(pd.DataFrame([
            {"Assumed annual return": f"{rate}%",
             "Illustrative monthly saving": round(fin.payment(0, target, 13, rate)),
             "Illustrative annual saving": round(fin.payment(0, target, 13, rate) * 12)}
            for rate in (3, 5, 7)
        ]), hide_index=True)
        st.caption("Month-end contributions; no taxes or fees modeled. Returns are uncertain.")
    st.info("Real parent-reviewed statement results are hidden, not deleted. "
            "These demo CSVs are activity exports, not reconciled performance evidence.")
    with st.expander("Demo transaction report"):
        st.dataframe(pd.DataFrame(data["records"]), hide_index=True)

"""CSV parsers and explicit-assumption planning; no fabricated account valuations."""
import csv
import io
from collections import defaultdict
from datetime import datetime
import math
import pandas as pd
import streamlit as st

def number(value):
    value = str(value).replace("$", "").replace(",", "").replace("(", "-").replace(")", "").strip()
    return float(value) if value not in ("", "--") else 0.

def parse_csv(raw, kind):
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    heading = "Account Number" if kind == "college" else "Activity/Trade Date"
    idx = next((i for i, r in enumerate(rows) if r and r[0] == heading), None)
    if idx is None:
        raise ValueError("This file does not match the expected account export.")
    headers = rows[idx]
    records = []
    for r in rows[idx + 1:]:
        if len(r) != len(headers):
            continue
        row = dict(zip(headers, r))
        date = row.get("Trade Date" if kind == "college" else "Activity/Trade Date", "")
        try:
            row["date"] = datetime.strptime(date, "%m/%d/%Y").date().isoformat()
        except ValueError:
            continue
        row.pop("Account Number", None)
        row.pop("Cusip", None)
        records.append(row)
    if not records:
        raise ValueError("No dated transactions were found.")
    result = {"records": records, "start": min(r["date"] for r in records), "end": max(r["date"] for r in records)}
    if kind == "college":
        holding_idx = next((i for i,r in enumerate(rows) if r and r[0] == "Fund Account Number"), None)
        if holding_idx is None or holding_idx + 1 >= len(rows):
            raise ValueError("A current 529 holding summary is required.")
        h = dict(zip(rows[holding_idx], rows[holding_idx + 1]))
        result.update(balance=number(h["Total Value"]), fund=h["Fund Name"])
    return result

def contribution_summary(data):
    rows = data["records"]
    monthly = defaultdict(float)
    for r in rows:
        if r["Transaction Type"] == "Recurring Contribution":
            monthly[r["date"][:7]] += number(r["Net Amount"])
    return dict(sorted(monthly.items()))

def college_reconciliation(data):
    """Compare units contributed/converted with closing units; do not infer complete history."""
    current = data["fund"]
    net_units = sum(number(r["Shares"]) for r in data["records"] if r["Investment Name"] == current)
    return net_units

def payment(balance, target, years, rate):
    n = max(1, round(years * 12))
    r = (1 + rate / 100) ** (1 / 12) - 1
    factor = n if abs(r) < 1e-10 else ((1 + r) ** n - 1) / r
    return max(0., (target - balance * (1 + r) ** n) / factor)

def future_cost(annual, years, inflation):
    return sum(annual * (1 + inflation / 100) ** (years + y) for y in range(4))

def xirr(flows):
    if not flows or not any(v < 0 for _,v in flows) or not any(v > 0 for _,v in flows):
        return None
    start = min(d for d,_ in flows)
    def npv(rate):
        return sum(v / (1 + rate) ** ((d-start).days/365.25) for d,v in flows)
    lo, hi = -.999, 10.
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(160):
        mid = (lo+hi)/2
        if npv(lo)*npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo+hi)/2*100

def positions(data):
    amounts, traded, income = defaultdict(float), defaultdict(float), defaultdict(float)
    for r in data["records"]:
        symbol, kind = r["Symbol"], r["Activity Type"]
        q = abs(number(r["Quantity #"]))
        if symbol == "--" or symbol == "MSPBNA":
            continue
        if kind in ("Bought", "Exchange Received In", "Cancel Sold"):
            amounts[symbol] += q
        elif kind in ("Sold", "Exchange Delivered Out"):
            amounts[symbol] -= q
        if kind in ("Bought", "Sold", "Cancel Sold"):
            traded[symbol] += number(r["Amount $"])
        if kind in ("Dividend", "Qualified Dividend"):
            income[symbol] += number(r["Amount $"])
    return pd.DataFrame([{"Symbol": s, "Net units in export": round(q, 6),
                          "Trade cash flow": round(traded[s], 2), "Distributions": round(income[s], 2)}
                         for s,q in sorted(amounts.items())])

@st.cache_data(ttl=3600, show_spinner=False)
def market_history(symbol, start):
    import yfinance as yf
    from curl_cffi import requests
    import certifi
    session = requests.Session(impersonate="chrome", verify=certifi.where())
    df = yf.Ticker(symbol, session=session).history(start=start, auto_adjust=True, timeout=12)
    if df.empty:
        raise ValueError("No market data returned for this symbol.")
    return df[["Close"]]

SCHOOLS = [
    ("Stanford", "California", "Private", "Technology • entrepreneurship • Division I soccer", "https://financialaid.stanford.edu/undergrad/budget/"),
    ("MIT", "Massachusetts", "Private", "Robotics • engineering • Division III soccer", "https://sfs.mit.edu/undergraduate-students/the-cost-of-attendance/annual-student-budget/"),
    ("Harvard", "Massachusetts", "Private", "Science • new ideas • Division I soccer", "https://college.harvard.edu/financial-aid/how-aid-works"),
    ("UC Berkeley", "California", "Public", "Engineering • startups • Division I soccer", "https://financialaid.berkeley.edu/how-aid-works/student-budgets-cost-of-attendance/"),
    ("UCLA", "California", "Public", "Science • entrepreneurship • Division I soccer", "https://financialaid.ucla.edu/undergraduate/cost-of-attendance"),
    ("University of Florida", "Florida", "Public", "STEM • business • men's club soccer, not varsity", "https://www.sfa.ufl.edu/cost/"),
    ("UC San Diego", "California", "Public", "Science • invention • Division I soccer", "https://fas.ucsd.edu/cost-of-attendance/undergraduates/"),
    ("San Diego State", "California", "Public", "Entrepreneurship • engineering • Division I soccer", "https://sacd.sdsu.edu/financial-aid/cost-of-attendance"),
    ("University of San Diego", "California", "Private", "Business • engineering • Division I soccer", "https://www.sandiego.edu/torero-hub/tuition-and-fees/undergraduate.php"),
]

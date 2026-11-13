"""Supa Juice insights: orders and books, in charts.

    streamlit run app.py

Where the numbers come from, in this order:
  1. data.json next to this file: the online dashboard. A GitHub Action makes it every hour
     (scripts/build_site.py), with nothing private in it, and the page runs in the browser.
  2. The order site and the books, read live with the admin keys in .streamlit/secrets.toml.
  3. Made-up sample data.
It never changes anything.
"""
from datetime import date, datetime, timedelta, timezone

import streamlit as st

from sj import charts, metrics, sources

st.set_page_config(page_title="Supa Juice insights", page_icon=":material/monitoring:", layout="wide")


@st.cache_data(ttl=600, show_spinner="Reading the orders and the books…")
def load(mode: str):
    if mode == "snapshot":
        return sources.load_snapshot()
    return sources.load_live(st.secrets) if mode == "live" else sources.load_demo()


@st.cache_data(ttl=600, show_spinner="Asking the books for the report…")
def live_report(start: str, end: str):
    return sources.load_report_live(st.secrets, start, end)


mode = "snapshot" if sources.has_snapshot() else ("live" if sources.configured(st.secrets) else "demo")
data = load(mode)
if data.mode == "live":
    today = datetime.now(timezone(timedelta(hours=2))).date()  # Cape Town, no daylight saving
else:
    today = date.fromisoformat(data.books.get("today") or date.today().isoformat())
orders = metrics.orders_frame(data.orders)
first_day = orders["created_day"].min().date() if len(orders) and not orders["created_day"].isna().all() else date(today.year, 3, 1)
st.session_state["private"] = data.mode != "snapshot"  # names and emails can be shown

charts.style()

pages = st.navigation([
    st.Page("views/overview.py", title="Overview", icon=":material/dashboard:", default=True),
    st.Page("views/sales.py", title="Sales", icon=":material/shopping_bag:"),
    st.Page("views/customers.py", title="Customers", icon=":material/group:"),
    st.Page("views/money.py", title="Money", icon=":material/account_balance:"),
], position="top")

# ---- The same header on every page: the page, the period, where the numbers come from ----
left, right = st.columns([3, 2], vertical_alignment="bottom")
with right:
    if data.mode != "snapshot":
        pick, more = st.columns([3, 2], vertical_alignment="bottom")
    else:
        pick, more = right, None
    choice = pick.selectbox("Period", metrics.PERIODS, index=metrics.PERIODS.index("Last 3 months"), key="period")
    if more is not None and more.button("Refresh", icon=":material/refresh:", width="stretch", help="Read the orders and the books again"):
        load.clear()
        live_report.clear()
        st.rerun()
    custom = None
    if choice == "Custom":
        picked = st.date_input("From – to", value=(first_day, today), min_value=date(2025, 1, 1), max_value=today, format="DD/MM/YYYY")
        if isinstance(picked, tuple) and len(picked) == 2:
            custom = picked
start, end = metrics.period(choice, today, first_day, custom)
with left:
    source = {"snapshot": f"Updated {data.generated}", "demo": "Sample data", "live": "Live"}[data.mode]
    charts.header(pages.title, f"{start.day} {start:%b %Y} – {end.day} {end:%b %Y}  ·  {source}")
if data.mode == "demo":
    st.info("These are made-up numbers. Add the keys to `.streamlit/secrets.toml` to see the real ones (see README).", icon=":material/science:")
for p in data.problems:
    st.warning(p, icon=":material/error:")
st.divider()


def report_for(a: date, b: date) -> dict:
    """The books' report for a period: asked from the books when live, worked out here for samples."""
    if data.mode == "live" and data.books:
        try:
            return live_report(a.isoformat(), b.isoformat())
        except sources.SourceError as err:
            st.warning("Books report: " + str(err), icon=":material/error:")
            return {}
    return metrics.report(data.books, a, b)


st.session_state["ctx"] = {"data": data, "orders": orders, "start": start, "end": end, "today": today, "report_for": report_for}

pages.run()

st.divider()
st.caption({"snapshot": "Refreshed every hour. Read only: no customer names or contact details are on this page.",
            "demo": "Sample data: made-up numbers, to show how the dashboard works.",
            "live": "Live from the orders and the books. Read only: nothing here changes an order or the books."}[data.mode])

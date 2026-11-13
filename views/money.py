import pandas as pd
import streamlit as st

from sj import charts, metrics

c = st.session_state["ctx"]
books, orders, start, end = c["data"].books, c["orders"], c["start"], c["end"]

st.title("Money")
st.caption(f"From the books, {start:%d %b %Y} to {end:%d %b %Y}. Cash basis: costs count when they were paid.")

rep = c["report_for"](start, end)
if not books:
    st.warning("The books could not be read.")
    st.stop()

a, b, d, e = st.columns(4)
charts.tile(a, "Income", charts.rand(rep.get("income")))
charts.tile(b, "Costs", charts.rand(rep.get("costs")))
charts.tile(d, "Profit", charts.rand(rep.get("profit")))
charts.tile(e, "Expenses without a receipt", f"{rep.get('missingReceipts', 0)}", help="SARS expects a receipt for every expense. Add them in the books.")

left, right = st.columns(2)
with left:
    st.subheader("Where the money went")
    cat = metrics.expenses_by_category(books, start, end)
    if cat.empty:
        st.write("No expenses in this period.")
    else:
        charts.show(charts.hbars(cat, "category", "amount", "Rand", charts.CATEGORY_COLOURS),
                    cat.rename(columns={"category": "Category", "amount": "Spent (R)", "entries": "Entries"}), key="m_cat", height=40 * len(cat) + 30)
with right:
    st.subheader("Cash in the account")
    cash = metrics.cash_over_time(books, end)
    cash = cash[cash["day"] >= pd.Timestamp(start)]
    charts.show(charts.line_over_time(cash, "day", "cash", "Rand", zero_rule=True),
                cash.assign(day=cash["day"].dt.strftime("%d %b %Y")).rename(columns={"day": "Day", "cash": "Cash (R)"}), key="m_cash")

st.subheader("Expenses by month")
bm = metrics.expenses_by_month(books, start, end)
if not bm.empty:
    charts.show(charts.stacked_over_time(bm, "month", "amount", "category", charts.CATEGORY_COLOURS, "Rand"),
                bm.pivot(index="month", columns="category", values="amount").fillna(0).reset_index().assign(month=lambda d: d["month"].dt.strftime("%b %Y")).rename(columns={"month": "Month"}),
                key="m_bymonth")

left, right = st.columns(2)
with left:
    st.subheader("Per sachet")
    ps = rep.get("perSachet") or {}
    x, y, z = st.columns(3)
    charts.tile(x, "Average price", charts.rand(ps.get("avgPrice"), True))
    charts.tile(y, "Cost to make", charts.rand(ps.get("costToMake"), True), help="Everything spent on batches so far, divided by the sachets made.")
    charts.tile(z, "Margin", charts.rand(ps.get("margin"), True))
    st.subheader("Stock")
    stock = metrics.stock(books, orders, end)
    stock["left"] = stock["made"] - stock["sold"]
    st.dataframe(stock.rename(columns={"flavour": "Flavour", "made": "Made", "sold": "Sold on the website", "left": "Left (about)"}),
                 hide_index=True, width="stretch")
    st.caption("Left is about right: race-stall sales and free samples aren't split by flavour.")
with right:
    st.subheader("Owners")
    own = pd.DataFrame(rep.get("owners") or [])
    if own.empty:
        st.write("No owner money yet.")
    else:
        cols = {"name": "Owner", "loan": "Loans (R)", "capital": "Capital (R)", "expenses": "Paid themselves (R)", "paidBack": "Paid back (R)", "owed": "Owed to them (R)"}
        st.dataframe(own[[k for k in cols if k in own]].rename(columns=cols), hide_index=True, width="stretch")
        st.caption("Owed = loans + expenses they paid themselves − what was paid back. Capital is their share, not owed.")
    ty = rep.get("taxYear") or {}
    if ty:
        st.subheader(f"Tax year {ty.get('label')}")
        st.progress(min(1.0, (ty.get("percent") or 0) / 100), text=f"{charts.rand(ty.get('turnover'))} of R 1 000 000 turnover ({ty.get('percent')}%)")
        st.caption("Above R 1 million in 12 months, VAT registration becomes compulsory. For information, not tax advice.")

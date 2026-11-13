import pandas as pd
import streamlit as st

from sj import charts, metrics

c = st.session_state["ctx"]
books, orders, start, end = c["data"].books, c["orders"], c["start"], c["end"]

if not books:
    st.warning("The books could not be read.")
    st.stop()

rep = c["report_for"](start, end)
charts.tiles([
    ("Income", charts.rand(rep.get("income")), None, "Website sales and other sales, when they were paid."),
    ("Costs", charts.rand(rep.get("costs")), None, "Every expense, and card fees, when they were paid."),
    ("Profit", charts.rand(rep.get("profit"))),
    ("Missing receipts", charts.count(rep.get("missingReceipts", 0)), None, "Expenses in the period without a receipt. SARS expects one for every expense: add them in the books."),
])

cat = metrics.expenses_by_category(books, start, end)
cash = metrics.cash_over_time(books, end)
cash = cash[cash["day"] >= pd.Timestamp(start)]
left, right = st.columns(2)
with left, charts.card("Where the money went", "Expenses by category."):
    if cat.empty:
        st.caption("No expenses in this period.")
    else:
        charts.show(charts.hbars(cat, "category", "amount", "Spent", charts.CATEGORY_COLOURS, money=True),
                    cat.rename(columns={"category": "Category", "amount": "Spent (R)", "entries": "Entries"}), key="m_cat")
with right, charts.card("Cash in the account", "At the end of each day, counted from the day the books start."):
    charts.show(charts.line_over_time(cash, "day", "cash", "Cash"),
                cash.assign(day=cash["day"].dt.strftime("%d %b %Y")).rename(columns={"day": "Day", "cash": "Cash (R)"}), key="m_cash")

with charts.card("Expenses by month", "Each category keeps its colour on every chart."):
    bm = metrics.expenses_by_month(books, start, end)
    if bm.empty:
        st.caption("No expenses in this period.")
    else:
        charts.show(charts.stacked_months(bm, "category", "amount", charts.CATEGORY_COLOURS, "Spent", money=True),
                    bm.pivot(index="month", columns="category", values="amount").fillna(0).reset_index()
                    .assign(month=lambda d: d["month"].dt.strftime("%b %Y")).rename(columns={"month": "Month"}),
                    key="m_bymonth")

ps = rep.get("perSachet") or {}
stock = metrics.stock(books, orders, end)
stock["left"] = stock["made"] - stock["sold"]
left, right = st.columns(2)
with left, charts.card("Per sachet", "The cost to make is everything spent on batches so far, divided by the sachets made."):
    charts.tiles([
        ("Average price", charts.rand(ps.get("avgPrice"), True)),
        ("Cost to make", charts.rand(ps.get("costToMake"), True)),
        ("Margin", charts.rand(ps.get("margin"), True)),
    ])
    if ps.get("costToMake") is None:
        st.caption("Add a batch in the books (date, flavour, sachets made, cost) to see the cost and margin.")
with right, charts.card("Stock", "Approximate: race-stall sales and samples aren't split by flavour."):
    charts.table(stock.rename(columns={"flavour": "Flavour", "made": "Made", "sold": "Sold on the website", "left": "Left"}))

own = pd.DataFrame(rep.get("owners") or [])
ty = rep.get("taxYear") or {}
left, right = st.columns(2)
with left, charts.card("Owners", "Owed: loans and expenses they paid themselves, minus what was paid back. Capital is their share, not owed."):
    if own.empty:
        st.caption("No owner money yet.")
    else:
        cols = {"name": "Owner", "loan": "Loans", "capital": "Capital", "expenses": "Paid themselves", "paidBack": "Paid back", "owed": "Owed to them"}
        charts.table(own[[k for k in cols if k in own]].rename(columns=cols), money=tuple(v for k, v in cols.items() if k != "name"))
with right, charts.card(f"Tax year {ty.get('label', '')}".strip(), "Above R 1 million in 12 months, VAT registration becomes compulsory. For information, not tax advice."):
    if ty:
        st.progress(min(1.0, (ty.get("percent") or 0) / 100), text=f"{charts.rand(ty.get('turnover'))} of R 1 000 000 turnover ({ty.get('percent')}%)")

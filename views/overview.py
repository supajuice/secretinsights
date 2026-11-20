import pandas as pd
import streamlit as st

from sj import charts, metrics

c = st.session_state["ctx"]
orders, start, end = c["orders"], c["start"], c["end"]
before = metrics.previous(start, end)

now, then = metrics.sales_summary(orders, start, end), metrics.sales_summary(orders, *before)
rep, rep_before = c["report_for"](start, end), c["report_for"](*before)
ps = rep.get("perSachet") or {}
ty = rep.get("taxYear") or {}
profit_before = (rep_before or {}).get("profit") or 0

charts.tiles([
    ("Website sales", charts.rand(now["revenue"]), metrics.change(now["revenue"], then["revenue"]),
     "Paid and delivered website orders, by the day they were paid. Includes delivery fees, after discounts."),
    ("Paid orders", charts.count(now["orders"]), metrics.change(now["orders"], then["orders"]),
     "Paid and delivered website orders, by the day they were paid. Orders still waiting for payment, and cancelled ones, are not counted."),
    ("Sachets sold", charts.count(now["sachets"]), metrics.change(now["sachets"], then["sachets"])),
    ("Average order", charts.rand(now["avg_order"]), metrics.change(now["avg_order"], then["avg_order"])),
])
_unpaid = metrics.unpaid_note(metrics.awaiting_payment(orders, start, end))
if _unpaid:
    st.caption(_unpaid)
charts.tiles([
    ("Profit", charts.rand(rep.get("profit")), metrics.change(rep.get("profit") or 0, profit_before) if profit_before > 0 else None,
     "From the books: all income minus every expense and card fee in the period. Cash basis."),
    ("Cash on hand", charts.rand((rep.get("cash") or {}).get("onHand")), None, "In the business account at the end of the period, from the books."),
    ("Margin per sachet", charts.rand(ps.get("margin"), cents=True), None,
     "Average price minus the cost to make one. Needs at least one batch in the books." if ps.get("margin") is None
     else f"Average price {charts.rand(ps.get('avgPrice'), True)} minus cost to make {charts.rand(ps.get('costToMake'), True)}."),
    (f"Tax year {ty.get('label', '')}".strip(), f"{ty.get('percent', 0)}%", None,
     f"Turnover {charts.rand(ty.get('turnover'))} of the R 1 000 000 VAT and turnover-tax limit."),
])

with charts.card("Sales", "Paid and delivered website orders."):
    every = st.segmented_control("Group by", ["Day", "Week", "Month"], default="Week" if (end - start).days > 31 else "Day",
                                 key="ov_every", label_visibility="collapsed") or "Week"
    t = metrics.sales_over_time(orders, start, end, every)
    charts.show(charts.bars_over_time(t, "period", "revenue", every, "Sales"),
                t.assign(period=t["period"].dt.strftime("%d %b %Y")).rename(
                    columns={"period": every, "revenue": "Sales (R)", "orders": "Orders", "sachets": "Sachets"}), key="ov_sales")

with charts.card("Income and costs by month", "Costs count when they were paid, so a month with a big ingredients order can look like a loss."):
    pnl = metrics.monthly_pnl(c["data"].books, start, end)
    long = pd.concat([pnl.assign(series="Income", value=pnl["income"]), pnl.assign(series="Costs", value=pnl["costs"])])[["month", "series", "value"]]
    charts.show(charts.grouped_months(long, charts.INCOME_COSTS),
                pnl.assign(month=pnl["month"].dt.strftime("%b %Y")).rename(columns={
                    "month": "Month", "income": "Income (R)", "costs": "Costs (R)", "profit": "Profit (R)", "running_profit": "Running profit (R)"}),
                key="ov_pnl")

import pandas as pd
import streamlit as st

from sj import charts, metrics

c = st.session_state["ctx"]
orders, start, end = c["orders"], c["start"], c["end"]
before = metrics.previous(start, end)

st.title("Overview")
st.caption(f"{start:%d %b %Y} to {end:%d %b %Y}. Arrows compare with the {(end - start).days + 1} days before.")

now, then = metrics.sales_summary(orders, start, end), metrics.sales_summary(orders, *before)
rep, rep_before = c["report_for"](start, end), c["report_for"](*before)

a, b, d, e = st.columns(4)
charts.tile(a, "Website sales", charts.rand(now["revenue"]), metrics.change(now["revenue"], then["revenue"]),
            help="Paid and delivered website orders, by the day they were paid. Includes delivery fees, after discounts.")
charts.tile(b, "Orders", f"{now['orders']}", metrics.change(now["orders"], then["orders"]))
charts.tile(d, "Sachets sold", f"{now['sachets']}", metrics.change(now["sachets"], then["sachets"]))
charts.tile(e, "Average order", charts.rand(now["avg_order"]), metrics.change(now["avg_order"], then["avg_order"]))

a, b, d, e = st.columns(4)
if rep:
    charts.tile(a, "Profit", charts.rand(rep.get("profit")), metrics.change(rep.get("profit") or 0, rep_before.get("profit") or 0) if rep_before and (rep_before.get("profit") or 0) > 0 else None,
                help="From the books: all income (website and other sales) minus every expense and card fee in the period. Cash basis.")
    charts.tile(b, "Cash on hand", charts.rand((rep.get("cash") or {}).get("onHand")), help="In the business account at the end of the period, from the books.")
    ps = rep.get("perSachet") or {}
    charts.tile(d, "Margin per sachet", charts.rand(ps.get("margin"), cents=True),
                help=f"Average price {charts.rand(ps.get('avgPrice'), True)} minus cost to make {charts.rand(ps.get('costToMake'), True)} (all batches so far).")
    ty = rep.get("taxYear") or {}
    charts.tile(e, f"Tax year {ty.get('label', '')}", f"{ty.get('percent', 0)}%", help=f"Turnover {charts.rand(ty.get('turnover'))} of the R 1 000 000 VAT and turnover-tax limit, from 1 March to the end of the period.")
else:
    a.info("The books' report could not be read.")

st.subheader("Sales")
every = st.segmented_control("Group by", ["Day", "Week", "Month"], default="Week" if (end - start).days > 31 else "Day", key="ov_every") or "Week"
t = metrics.sales_over_time(orders, start, end, every)
charts.show(charts.bars_over_time(t, "period", "revenue", every, "Sales (R)"),
            t.rename(columns={"period": every, "revenue": "Sales (R)", "orders": "Orders", "sachets": "Sachets"}), key="ov_sales")

st.subheader("Income and costs by month")
pnl = metrics.monthly_pnl(c["data"].books, start, end)
long = pd.concat([pnl.assign(series="Income", value=pnl["income"]), pnl.assign(series="Costs", value=pnl["costs"])])[["month", "series", "value"]]
charts.show(charts.grouped_monthly(long, charts.INCOME_COSTS, "Rand"),
            pnl.assign(month=pnl["month"].dt.strftime("%b %Y")).rename(columns={"month": "Month", "income": "Income (R)", "costs": "Costs (R)", "profit": "Profit (R)", "running_profit": "Running profit (R)"}),
            key="ov_pnl")
st.caption("Costs count when they were paid, so a month with a big ingredients order looks like a loss. The running profit in the table evens that out.")

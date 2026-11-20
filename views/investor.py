"""Investor view: the numbers people ask for in a pitch (Shark Tank style), all time up to the end of the period.

Every figure says how it is worked out. One that can't be worked out yet says what the books need.
"""
import pandas as pd
import streamlit as st

from sj import charts, metrics

c = st.session_state["ctx"]
orders, start, end, books = c["orders"], c["start"], c["end"], c["data"].books
p = metrics.pitch(orders, books, end)
first = p["first_order"] or start
since = f"since the first order on {first.day} {first:%b %Y}" if p["first_order"] else "so far"

st.caption(f"All time, up to {end.day} {end:%b %Y}: the period picker only sets the end day. "
           "Hover the ⓘ on a tile to see how it's worked out.")


def money(v, cents=False):
    return "–" if v is None else charts.rand(v, cents)


def pct(v):
    return "–" if v is None else f"{v:.0f}%"


st.subheader("Traction")
charts.tiles([
    ("Sales to date", money(p["sales_to_date"]), None, f"Every paid order {since}, in rand, after discounts, with delivery fees."),
    ("Orders to date", charts.count(p["orders"]["total"]), metrics.split_note(p["orders"]), "Every order placed, and where it is now."),
    ("Customers to date", charts.count(p["customers"]), None, "Different people (email addresses) with at least one paid order."),
    ("Sachets sold", charts.count(p["sachets"]), None, "In paid orders."),
])

st.subheader("Run rate and growth")
charts.tiles([
    ("Sales, last 30 days", money(p["last30"]), p["growth"], "Paid orders in the 30 days up to the end day. The arrow compares with the 30 days before."),
    ("Annual run rate", money(p["annual_run_rate"]), None, "The last 30 days' sales × 12: what a year would bring at today's pace."),
    ("Average order", money(p["aov"]), None, "Sales to date ÷ paid orders."),
    ("Repeat customers", pct(p["repeat_rate"]), None, "Of everyone who has bought, the share who came back and bought again."),
])

st.subheader("Unit economics, per sachet")
charts.tiles([
    ("Selling price", money(p["price"], True), None, "What a sachet actually sells for: sales after discounts, without delivery fees, ÷ sachets sold."),
    ("Cost to make", money(p["cost"], True), None,
     "Ingredients and packaging per sachet, from the Batches in the books." if p["cost_from"] == "batches"
     else "Ingredients and Packaging expenses so far ÷ sachets sold. Recording batches in the books (sachets made and "
          "what they cost) makes this exact." if p["cost_from"] == "expenses"
     else "Needs a batch, or Ingredients and Packaging expenses, in the books."),
    ("Gross margin", pct(p["margin_pct"]), None, "(Selling price − cost to make) ÷ selling price." if p["margin_pct"] is not None
     else "Needs the cost to make, from Batches in the books."),
    ("Gross profit per sachet", money(p["gross_profit"], True), None, "Selling price − cost to make."),
])

st.subheader("Customers and cash")
runway = ("Profitable" if p["burn"] == 0 and p["avg_monthly_profit"] > 0 else
          "–" if p["runway_months"] is None else f"{p['runway_months']:.0f} months")
charts.tiles([
    ("CAC", money(p["cac"]), None,
     f"Cost to win a customer: marketing to date ÷ customers to date. Marketing = promo code discounts "
     f"({money(p['discounts'])}) + Marketing expenses in the books ({money(p['marketing_spend'])})." if p["cac"] is not None
     else "Cost to win a customer. No promo discounts or Marketing expenses yet."),
    ("LTV", money(p["ltv"]), None,
     "Customer lifetime value: average spend per customer to date × gross margin: the gross profit a customer has brought in so far."
     if p["ltv"] is not None else f"Customer lifetime value. Needs the gross margin. Average spend per customer so far: {money(p['spend_per_customer'])}."),
    ("LTV : CAC", "–" if p["ltv_cac"] is None else f"{p['ltv_cac']:.1f} : 1", None,
     "Lifetime value ÷ cost to win a customer. Investors like 3 : 1 or better."),
    ("Burn / runway", runway, None,
     f"Average profit over the last three months: {money(p['avg_monthly_profit'])} a month. "
     f"Cash on hand {money(p['cash'])}. Runway = cash ÷ monthly loss."),
])

# ---- Charts ----
span_start = first  # from the first order: the whole story
every = st.segmented_control("Group by", ["Week", "Month"], default="Week" if (end - span_start).days <= 120 else "Month",
                             key="inv_every", label_visibility="collapsed") or "Week"

left, right = st.columns(2)
with left, charts.card("Sales growth", f"Paid orders per {every.lower()}, with the change on the {every.lower()} before. The latest one is still running."):
    g = metrics.sales_growth(orders, span_start, end, every)
    charts.show(charts.growth_bars(g, every),
                g.assign(period=g["period"].dt.strftime("%d %b %Y"),
                         growth=[("–" if v is None or pd.isna(v) else f"{v:+.0f}%") for v in g["growth"]])
                .rename(columns={"period": every, "revenue": "Sales (R)", "orders": "Paid orders", "sachets": "Sachets",
                                 "growth": "Change"}), key="inv_growth")
with right, charts.card("Customers to date", f"Different people who had bought by the end of each {every.lower()}."):
    ct = metrics.customers_to_date(orders, span_start, end, every)
    charts.show(charts.line_over_time(ct, "period", "customers", "Customers", money=False),
                ct.assign(period=ct["period"].dt.strftime("%d %b %Y")).rename(columns={"period": every, "customers": "Customers"}),
                key="inv_customers")

ue = metrics.unit_economics(orders, books, end)
if not ue.empty:
    money_in = ue.loc[ue["kind"] == "In", "amount"].sum()
    last = ue.iloc[-1]
    margin = (last["amount"] if last["kind"] == "Profit" else -last["amount"]) / money_in * 100 if money_in else 0
    note = (f"Where the {charts.rand(money_in, True)} a sachet brings in goes (full price + delivery fee, all time). "
            f"Red is spend, darkest for the biggest; green is what's left: {charts.rand(abs(last['amount']), True)}, "
            f"a {margin:.0f}% margin. "
            "Promo codes are counted as a marketing cost. Other costs are every expense in the books so far ÷ sachets sold, "
            "so stock that isn't sold yet makes them look higher.")
else:
    note = "No sales yet."
with charts.card("Unit economics: one sachet", note):
    if ue.empty:
        st.caption("No sales yet.")
    else:
        chart, split_rows = charts.money_split(ue)
        st.altair_chart(chart, width="stretch")
        st.markdown(charts.money_key(split_rows), unsafe_allow_html=True)
        with st.expander("See the numbers", expanded=False):
            st.dataframe(pd.concat([ue[ue["kind"] == "In"][["part", "amount"]].assign(share=float("nan")), split_rows.drop(columns="colour")])
                         .assign(amount=lambda d: d["amount"].round(2), share=lambda d: d["share"].round(0))
                         .rename(columns={"part": " ", "amount": "Per sachet (R)", "share": "Share of money in (%)"}),
                         hide_index=True, width="stretch", key="inv_unit")

pc = metrics.promo_codes(orders, end)
with charts.card("Promo codes: what each one cost, and what it brought",
                 "All time, paid orders. The cost is the discount given. A new customer is someone whose first order used the code."):
    if pc.empty:
        st.caption("No promo codes used yet.")
    else:
        pc_rows = len(pc)
        code_colours = {c: [charts.SLOTS[6], charts.SLOTS[4], charts.SLOTS[3], charts.SLOTS[0]][i % 4] for i, c in enumerate(pc["code"])}  # each code keeps its colour (not green: that means profit)
        left, right = st.columns(2)
        with left:
            st.markdown("**What it cost** (discount given)")
            charts.show(charts.hbars(pc, "code", "discount", "Discount given", code_colours, money=True),
                        pc[["code", "percent", "discount"]].rename(columns={"code": "Code", "percent": "Off (%)", "discount": "Discount given (R)"}),
                        key="inv_pc_cost", height=charts.hbars_height(pc_rows))
        with right:
            st.markdown("**What it brought** (sales from orders using it)")
            charts.show(charts.hbars(pc, "code", "sales", "Sales", code_colours, money=True),
                        pc[["code", "orders", "sachets", "sales"]].rename(columns={"code": "Code", "orders": "Paid orders", "sachets": "Sachets",
                                                                                   "sales": "Sales (R)"}),
                        key="inv_pc_sales", height=charts.hbars_height(pc_rows))
        left, right = st.columns(2)
        with left:
            st.markdown("**New customers it brought**")
            charts.show(charts.hbars(pc, "code", "new", "New customers", code_colours),
                        pc[["code", "new"]].rename(columns={"code": "Code", "new": "New customers"}), key="inv_pc_new",
                        height=charts.hbars_height(pc_rows))
        with right:
            st.markdown("**Cost per new customer**")
            pn = pc[pc["per_new"].notna()]
            if pn.empty:
                st.caption("None of the codes was used on a first order.")
            else:
                charts.show(charts.hbars(pn, "code", "per_new", "Per new customer", code_colours, money=True),
                            pn[["code", "discount", "new", "per_new"]].rename(columns={"code": "Code", "discount": "Discount given (R)",
                                                                                     "new": "New customers", "per_new": "Cost per new customer (R)"}),
                            key="inv_pc_pernew", height=charts.hbars_height(pc_rows))
        waiting = pc[pc["waiting"] > 0]
        if not waiting.empty:
            st.caption("Not counted yet, waiting for payment: " + ", ".join(f"{r.waiting} with {r.code}" for r in waiting.itertuples()) + ".")

with charts.card("Orders placed, paid and unpaid", f"Per {every.lower()}, by the day each order was placed."):
    ot = metrics.orders_over_time(orders, span_start, end, every)
    charts.show(charts.stacked_over_time(ot, "kind", "orders", every, charts.PAID_UNPAID, "Orders"),
                ot.pivot(index="period", columns="kind", values="orders").reset_index()
                .assign(period=lambda d: d["period"].dt.strftime("%d %b %Y")).rename(columns={"period": every}),
                key="inv_orders")

with charts.card("The questions, answered", "What investors usually ask, with today's answer and where it comes from."):
    rows = [
        ("What are your sales to date?", money(p["sales_to_date"]), f"Paid orders {since}"),
        ("What's your monthly run rate?", money(p["last30"]), "Paid orders in the last 30 days"),
        ("And your annual run rate?", money(p["annual_run_rate"]), "Last 30 days × 12"),
        ("How fast are you growing?", "–" if p["growth"] is None else f"{p['growth']:+.0f}% on the 30 days before", "Last 30 days vs the 30 before"),
        ("How many customers?", f"{p['customers']}, {pct(p['repeat_rate'])} came back", "Email addresses with a paid order"),
        ("What does a sachet sell for, and cost to make?", f"{money(p['price'], True)} / {money(p['cost'], True)}", "Sales; batches, or ingredient + packaging costs"),
        ("What's your gross margin?", pct(p["margin_pct"]), "(Price − cost) ÷ price"),
        ("What does it cost to get a customer?", money(p["cac"]) if p["cac"] is not None else "No marketing cost yet",
         "(Promo code discounts + Marketing expenses) ÷ customers"),
        ("How much have the founders put in?", money(p["put_in"]),
         "Loans and capital in the books, plus costs the owners paid themselves"),
        ("Are you profitable?", "Yes" if p["avg_monthly_profit"] > 0 else f"Not yet: {money(p['avg_monthly_profit'])} a month",
         "Average profit over the last three months, from the books"),
    ]
    charts.table(pd.DataFrame(rows, columns=["Question", "Answer", "Worked out from"]), key="inv_qa")

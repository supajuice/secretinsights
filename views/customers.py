import streamlit as st

from sj import charts, metrics

c = st.session_state["ctx"]
orders, start, end = c["orders"], c["start"], c["end"]

everyone = metrics.customers(orders)
rate = metrics.repeat_rate(orders, end)
period = metrics.sales_summary(orders, start, end)
charts.tiles([
    ("Customers so far", charts.count(len(everyone)), None, "A customer is one email address (or a name, for DM orders without one), all time."),
    ("Bought in this period", charts.count(period["customers"])),
    ("Bought more than once", "–" if rate is None else f"{rate:.0f}%", None, "Of everyone who has bought, up to the end of the period."),
    ("Spent per customer", charts.rand(everyone["spent"].mean() if len(everyone) else None), None, "All time."),
])

with charts.card("New and returning, by month", "New: their first order that month. Returning: they had bought before."):
    nr = metrics.new_and_returning(orders, start, end)
    if nr.empty:
        st.caption("No sales in this period.")
    else:
        charts.show(charts.stacked_months(nr, "kind", "customers", charts.NEW_RETURNING, "Customers"),
                    nr.pivot(index="month", columns="kind", values="customers").reset_index()
                    .assign(month=lambda d: d["month"].dt.strftime("%b %Y")).rename(columns={"month": "Month"}),
                    key="c_nr")

if not st.session_state.get("private"):
    st.caption("Best customers, with names and emails, are only on the private version on your laptop.")
else:
    with charts.card("Best customers", "All time. Private: names and emails are only for you and Greg. Don't share this screen or use it for marketing."):
        top = everyone.head(15).copy()
        if top.empty:
            st.caption("No customers yet.")
        else:
            top["first"] = top["first"].dt.strftime("%d %b %Y")
            top["last"] = top["last"].dt.strftime("%d %b %Y")
            charts.table(top.rename(columns={"customer": "Email", "name": "Name", "first": "First bought", "last": "Last bought",
                                             "orders": "Orders", "sachets": "Sachets", "spent": "Spent"}), money=("Spent",))

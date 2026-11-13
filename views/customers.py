import streamlit as st

from sj import charts, metrics

c = st.session_state["ctx"]
orders, start, end = c["orders"], c["start"], c["end"]

st.title("Customers")
st.caption("A customer is one email address (or a name, for DM orders without one). Only paid and delivered orders count.")

everyone = metrics.customers(orders)
a, b, d = st.columns(3)
charts.tile(a, "Customers so far", f"{len(everyone)}")
rate = metrics.repeat_rate(orders, end)
charts.tile(b, "Bought more than once", "–" if rate is None else f"{rate:.0f}%", help="Of everyone who has bought, up to the end of the period.")
charts.tile(d, "Average spent per customer", charts.rand(everyone["spent"].mean() if len(everyone) else None))

st.subheader("New and returning, by month")
nr = metrics.new_and_returning(orders, start, end)
if nr.empty:
    st.write("No sales in this period.")
else:
    charts.show(charts.stacked_over_time(nr, "month", "customers", "kind", charts.NEW_RETURNING, "Customers"),
                nr.pivot(index="month", columns="kind", values="customers").reset_index().assign(month=lambda d: d["month"].dt.strftime("%b %Y")).rename(columns={"month": "Month"}),
                key="c_nr")

if not st.session_state.get("private"):
    st.caption("Best customers, with names and emails, are only on the private version on your laptop.")
    st.stop()

st.subheader("Best customers")
st.caption("All time. Private: names and emails are only for you and Greg. Don't share this screen or use it for marketing.")
top = everyone.head(15).copy()
if not top.empty:
    top["first"] = top["first"].dt.strftime("%d %b %Y")
    top["last"] = top["last"].dt.strftime("%d %b %Y")
    st.dataframe(top.rename(columns={"customer": "Email", "name": "Name", "first": "First bought", "last": "Last bought",
                                     "orders": "Orders", "sachets": "Sachets", "spent": "Spent (R)"}),
                 hide_index=True, width="stretch",
                 column_config={"Spent (R)": st.column_config.NumberColumn(format="%.0f")})

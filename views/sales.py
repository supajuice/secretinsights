import streamlit as st

from sj import charts, metrics

c = st.session_state["ctx"]
orders, start, end = c["orders"], c["start"], c["end"]

s = metrics.sales_summary(orders, start, end)
charts.tiles([
    ("Paid orders", charts.count(s["orders"]), None, "Paid and delivered website orders, by the day they were paid. Orders still waiting for payment, and cancelled ones, are not counted."),
    ("Customers", charts.count(s["customers"]), None, "Different people who bought in the period."),
    ("Delivery fees charged", charts.rand(s["delivery_fees"])),
    ("Discounts given", charts.rand(s["discounts"]), None, "What the sachets would have cost without a discount code, minus what was paid."),
])
_unpaid = metrics.unpaid_note(metrics.awaiting_payment(orders, start, end))
if _unpaid:
    st.caption(_unpaid)

f = metrics.flavour_mix(orders, start, end)
stt = metrics.status_counts(orders, start, end)
rows = max(len(f), len(stt))
left, right = st.columns(2)
with left, charts.card("Flavours", "Sachets sold. Orders from before flavours could be picked are Not chosen."):
    charts.show(charts.hbars(f, "flavour", "sachets", "Sachets", charts.FLAVOUR_COLOURS),
                f.rename(columns={"flavour": "Flavour", "sachets": "Sachets"}), key="s_flav", height=charts.hbars_height(rows))
with right, charts.card("Where orders are now", "Every order placed in the period, by its status today."):
    charts.show(charts.hbars(stt, "status", "orders", "Orders", charts.STATUS_COLOURS),
                stt.rename(columns={"status": "Status", "orders": "Orders"}), key="s_status", height=charts.hbars_height(rows))

w = metrics.weekdays(orders, start, end)
z = metrics.order_sizes(orders, start, end)
rows = max(len(w), len(z))
left, right = st.columns(2)
with left, charts.card("Which day people order", "Orders placed, not counting cancelled ones."):
    charts.show(charts.hbars(w, "day", "orders", "Orders"),
                w.rename(columns={"day": "Day", "orders": "Orders"}), key="s_wd", height=charts.hbars_height(rows))
with right, charts.card("Order sizes", "How many sachets each paid order had."):
    if z.empty:
        st.caption("No sales in this period.")
    else:
        z["label"] = z["sachets"].astype(str) + " sachets"
        charts.show(charts.hbars(z, "label", "orders", "Orders"),
                    z[["sachets", "orders"]].rename(columns={"sachets": "Sachets in the order", "orders": "Orders"}), key="s_size",
                    height=charts.hbars_height(rows))

fu = metrics.fulfilment(orders, start, end)
k = metrics.codes(orders, start, end)
left, right = st.columns(2)
with left, charts.card("Collected or sent", "Paid and delivered orders."):
    charts.show(charts.hbars(fu, "how", "orders", "Orders"),
                fu.rename(columns={"how": "How", "orders": "Orders", "revenue": "Sales (R)"}), key="s_ful", height=charts.hbars_height(len(fu)))
with right, charts.card("Discount codes", "Paid orders that used a code."):
    if k.empty:
        st.caption("No discount codes were used in this period.")
    else:
        charts.table(k.rename(columns={"code": "Code", "orders": "Orders", "discount": "Discount given", "revenue": "Sales"}),
                     money=("Discount given", "Sales"))

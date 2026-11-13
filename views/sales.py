import streamlit as st

from sj import charts, metrics

c = st.session_state["ctx"]
orders, start, end = c["orders"], c["start"], c["end"]

st.title("Sales")
st.caption(f"Website orders, {start:%d %b %Y} to {end:%d %b %Y}. Sales are paid and delivered orders.")

s = metrics.sales_summary(orders, start, end)
a, b, d = st.columns(3)
charts.tile(a, "Delivery fees charged", charts.rand(s["delivery_fees"]))
charts.tile(b, "Discounts given", charts.rand(s["discounts"]), help="What the sachets would have cost without a discount code, minus what was paid.")
charts.tile(d, "Customers", f"{s['customers']}", help="Different people who bought in the period.")

left, right = st.columns(2)
with left:
    st.subheader("Flavours")
    f = metrics.flavour_mix(orders, start, end)
    charts.show(charts.hbars(f, "flavour", "sachets", "Sachets", charts.FLAVOUR_COLOURS), f.rename(columns={"flavour": "Flavour", "sachets": "Sachets"}), key="s_flav", height=150)
    st.caption("Older orders from before flavours could be picked show as *Not chosen*.")
with right:
    st.subheader("Where orders are now")
    stt = metrics.status_counts(orders, start, end)
    charts.show(charts.hbars(stt, "status", "orders", "Orders", charts.STATUS_COLOURS), stt.rename(columns={"status": "Status", "orders": "Orders"}), key="s_status", height=200)
    st.caption("Every order placed in the period, by its status today.")

left, right = st.columns(2)
with left:
    st.subheader("Collected or sent")
    fu = metrics.fulfilment(orders, start, end)
    charts.show(charts.hbars(fu, "how", "orders", "Orders"), fu.rename(columns={"how": "How", "orders": "Orders", "revenue": "Sales (R)"}), key="s_ful", height=120)
with right:
    st.subheader("Which day people order")
    w = metrics.weekdays(orders, start, end)
    charts.show(charts.hbars(w, "day", "orders", "Orders"), w.rename(columns={"day": "Day", "orders": "Orders"}), key="s_wd", height=230)

left, right = st.columns(2)
with left:
    st.subheader("Order sizes")
    z = metrics.order_sizes(orders, start, end)
    z["label"] = z["sachets"].astype(str) + " sachets"
    charts.show(charts.hbars(z, "label", "orders", "Orders"), z[["sachets", "orders"]].rename(columns={"sachets": "Sachets in the order", "orders": "Orders"}), key="s_size", height=max(120, 28 * len(z)))
with right:
    st.subheader("Discount codes")
    k = metrics.codes(orders, start, end)
    if k.empty:
        st.write("No discount codes were used in this period.")
    else:
        st.dataframe(k.rename(columns={"code": "Code", "orders": "Orders", "discount": "Discount given (R)", "revenue": "Sales (R)"}),
                     hide_index=True, width="stretch")

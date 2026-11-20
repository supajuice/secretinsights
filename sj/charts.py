"""The look: page styles, cards, tiles and charts, so every page is built from the same few pieces.

Charts follow one set of rules: thin bars with rounded ends, 2px lines, a quiet grid, one axis,
a tooltip on every mark, each thing keeps its colour (a flavour is always its fruit colour),
numbers written the same way everywhere (R 2 000), and the numbers one click away underneath.
"""
from __future__ import annotations

from contextlib import contextmanager

import altair as alt
import pandas as pd
import streamlit as st

# Colours
BLUE = "#1340c8"  # one series, and the accent
INK = "#0e1a3d"
MUTED = "#5b6383"
LINE = "#e7e3d4"  # card borders and the grid
AXIS = "#cfc9b3"
PAGE = "#faf9f5"

# Each thing keeps its colour everywhere. Flavours are their fruit (validated as a pair).
FLAVOUR_COLOURS = {"Orange": "#f7931e", "Cranberry": "#a3102f", "Not chosen": "#9a9fb3"}
# Categories, statuses and the like: the validated categorical order, assigned in this order, never cycled.
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
CATEGORY_COLOURS = dict(zip(["Ingredients", "Packaging", "Shipping & boxes", "Payment fees", "Tech & software", "Marketing", "Other"], SLOTS))
STATUS_COLOURS = {"New request": SLOTS[6], "Awaiting payment": SLOTS[3], "Paid": SLOTS[0], "Delivered": SLOTS[2], "Cancelled": "#9a9fb3"}
NEW_RETURNING = {"New": SLOTS[0], "Returning": SLOTS[2]}
PAID_UNPAID = {"Paid": SLOTS[0], "Unpaid": SLOTS[3], "Cancelled": "#9a9fb3"}
UNIT = {"In": SLOTS[0], "Promo": SLOTS[4], "Cost": SLOTS[1], "Profit": SLOTS[2], "Loss": SLOTS[7]}
INCOME_COSTS = {"Income": SLOTS[0], "Costs": SLOTS[1]}

FONT = "Source Sans 3, Source Sans Pro, system-ui, -apple-system, Segoe UI, sans-serif"  # Streamlit's own
HEIGHT = 240  # every chart in a two-up row is this tall, so the cards line up
LABELS = 112  # the width of the label column on bar charts

# ---------------------------------------------------------------------------
# Page styles
# ---------------------------------------------------------------------------

CSS = """
<style>
.stApp { background: %(page)s; }
.block-container { max-width: 1180px; padding-top: 4.5rem; padding-bottom: 4rem; }
h1 { font-size: 1.75rem !important; font-weight: 700 !important; padding: 0 !important; color: %(ink)s; }
/* Cards (charts.card): white, thin border, soft corners, small heading */
[class*="st-key-card-"] { background: #fff; border: 1px solid %(line)s !important; border-radius: 12px !important; padding: 18px 20px 6px !important; }
[class*="st-key-card-"] h3 { font-size: 1rem !important; font-weight: 650 !important; padding: 0 !important; color: %(ink)s; }
/* Tiles: all the same height and type */
[data-testid="stMetric"] { background: #fff; border-color: %(line)s !important; border-radius: 12px !important; padding: 16px 20px !important; }
@media (min-width: 640px) { [data-testid="stMetric"] { min-height: 148px; } }
[data-testid="stMetricLabel"] p { font-size: 0.85rem !important; color: %(muted)s !important; font-weight: 500 !important; }
[data-testid="stMetricValue"] { font-size: 1.7rem !important; font-weight: 650 !important; color: %(ink)s !important; }
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }
/* A note under a number ("31 paid · 4 unpaid · 1 cancelled") wraps instead of being cut off */
[data-testid="stMetricDelta"], [data-testid="stMetricDelta"] * { white-space: normal !important; overflow: visible !important; text-overflow: clip !important; height: auto !important; }
/* "See the numbers": a quiet line, not a box */
[data-testid="stExpander"] details { border: 0 !important; border-top: 1px solid %(line)s !important; border-radius: 0 !important; background: transparent !important; }
[data-testid="stExpander"] summary { padding-left: 0 !important; padding-right: 0 !important; }
[data-testid="stExpander"] summary p { font-size: 0.85rem !important; color: %(muted)s !important; }
[data-testid="stCaptionContainer"] { color: %(muted)s !important; }
hr { margin: 0.5rem 0 1.25rem !important; border-color: %(line)s !important; }
</style>
""" % {"page": PAGE, "ink": INK, "muted": MUTED, "line": LINE}


def style() -> None:
    st.html(CSS)


# ---------------------------------------------------------------------------
# Numbers
# ---------------------------------------------------------------------------

def rand(v: float | None, cents: bool = False) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    sign = "-" if v < 0 else ""
    v = abs(v)
    return sign + "R " + (f"{v:,.2f}" if cents else f"{v:,.0f}").replace(",", " ")


def count(v) -> str:
    return f"{int(v):,}".replace(",", " ")


def _num(expr: str, money: bool) -> str:
    """A Vega expression writing a number the dashboard's way: 2 000, or R 2 000."""
    text = "replace(format(%s, ',.0f'), regexp(',', 'g'), ' ')" % expr
    return ("'R ' + " + text) if money else text


def _axis(money: bool, **kw) -> alt.Axis:
    return alt.Axis(labelExpr=_num("datum.value", money), tickCount=4, **kw)


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

def header(title: str, note: str) -> None:
    st.title(title)
    st.caption(note)


@contextmanager
def card(title: str, note: str | None = None):
    """A white card with a heading, an optional one-line note, and whatever goes inside."""
    slug = "".join(ch if ch.isalnum() else "-" for ch in title.lower()).strip("-")
    with st.container(border=True, key="card-" + slug):
        st.subheader(title, anchor=False)
        if note:
            st.caption(note)
        yield


def tiles(items: list[tuple]) -> None:
    """A row of stat tiles: (label, value, change %% or None, help or None). The arrow compares
    with the same length of time just before."""
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value = item[0], item[1]
        delta = item[2] if len(item) > 2 else None
        help_ = item[3] if len(item) > 3 else None
        if isinstance(delta, str):  # a note under the number, such as "31 paid · 4 unpaid", in grey with no arrow
            col.metric(label, value, delta=delta, delta_color="off", delta_arrow="off", help=help_, border=True)
        else:
            col.metric(label, value, delta=None if delta is None else f"{delta:+.0f}% vs before", help=help_, border=True)


def show(chart: alt.Chart, table: pd.DataFrame, key: str, height: int = HEIGHT) -> None:
    """The chart, then its numbers in a fold-out table (for screen readers, and for exact figures)."""
    st.altair_chart(chart.properties(height=height), width="stretch")
    with st.expander("See the numbers", expanded=False):
        st.dataframe(table, hide_index=True, width="stretch", key=key)


def table(df: pd.DataFrame, money: tuple[str, ...] = (), key: str | None = None) -> None:
    """A plain table, with rand columns written as R 2 000."""
    out = df.copy()
    for c in money:
        if c in out:
            out[c] = out[c].map(lambda v: rand(v))
    st.dataframe(out, hide_index=True, width="stretch", key=key)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _theme():
    return {
        "config": {
            "background": "transparent",
            "font": FONT,
            "view": {"stroke": None},
            "axis": {"labelColor": MUTED, "titleColor": MUTED, "gridColor": LINE, "domainColor": AXIS, "tickColor": AXIS,
                     "labelFontSize": 12, "titleFontSize": 12, "titleFontWeight": 500, "labelPadding": 6, "ticks": False},
            "axisX": {"grid": False},
            "axisY": {"domain": False, "title": None},
            "legend": {"labelColor": INK, "orient": "top", "labelFontSize": 12, "symbolType": "circle", "title": None, "offset": 4},
            "bar": {"cornerRadiusEnd": 4},
            "line": {"strokeWidth": 2},
            "point": {"size": 64, "filled": True},
            "text": {"font": FONT},
        }
    }


alt.theme.register("supajuice", enable=True)(_theme)


def bars_over_time(df: pd.DataFrame, x: str, y: str, every: str, label: str, money: bool = True) -> alt.Chart:
    fmt = {"Day": "%d %b", "Week": "%d %b", "Month": "%b %Y"}[every]
    unit = {"Day": "yearmonthdate", "Week": "yearmonthdate", "Month": "yearmonth"}[every]
    return alt.Chart(df).transform_calculate(_v=_num("datum." + y, money)).mark_bar(color=BLUE, width={"band": 0.65}).encode(
        x=alt.X(f"{unit}({x}):O", title=None, axis=alt.Axis(format=fmt, labelAngle=0, labelOverlap="greedy")),
        y=alt.Y(f"{y}:Q", axis=_axis(money)),
        tooltip=[alt.Tooltip(f"{x}:T", title={"Day": "Day", "Week": "Week from", "Month": "Month"}[every], format=fmt),
                 alt.Tooltip("_v:N", title=label)],
    )


def stacked_over_time(df: pd.DataFrame, group: str, value: str, every: str, colours: dict, label: str) -> alt.Chart:
    """df: period, group, value. Stacked bars per week or month, each group in its own colour."""
    fmt = {"Week": "%d %b", "Month": "%b %Y"}[every]
    unit = {"Week": "yearmonthdate", "Month": "yearmonth"}[every]
    present = [k for k in colours if k in set(df[group])]
    return alt.Chart(df).mark_bar(stroke="white", strokeWidth=1, width={"band": 0.6}).encode(
        x=alt.X(f"{unit}(period):O", title=None, axis=alt.Axis(format=fmt, labelAngle=0, labelOverlap="greedy")),
        y=alt.Y(f"{value}:Q", stack=True, axis=_axis(False)),
        color=alt.Color(f"{group}:N", scale=alt.Scale(domain=present, range=[colours[k] for k in present]), sort=present),
        order=alt.Order("_o:Q"),
        tooltip=[alt.Tooltip("period:T", title={"Week": "Week from", "Month": "Month"}[every], format=fmt),
                 alt.Tooltip(f"{group}:N", title=" "), alt.Tooltip(f"{value}:Q", title=label)],
    ).transform_calculate(_o=" + ".join(f"(datum.{group} == '{k}' ? {i} : 0)" for i, k in enumerate(present)) or "0")


def growth_bars(df: pd.DataFrame, every: str) -> alt.Chart:
    """df: period, revenue, growth. Sales bars with the change on the period before written above each one."""
    fmt = {"Week": "%d %b", "Month": "%b %Y"}[every]
    unit = {"Week": "yearmonthdate", "Month": "yearmonth"}[every]
    d = df.assign(_g=[("" if g is None or pd.isna(g) else f"{g:+.0f}%") for g in df["growth"]])
    base = alt.Chart(d).transform_calculate(_v=_num("datum.revenue", True)).encode(
        x=alt.X(f"{unit}(period):O", title=None, axis=alt.Axis(format=fmt, labelAngle=0, labelOverlap="greedy")),
        y=alt.Y("revenue:Q", axis=_axis(True), scale=alt.Scale(padding=18)),
        tooltip=[alt.Tooltip("period:T", title={"Week": "Week from", "Month": "Month"}[every], format=fmt),
                 alt.Tooltip("_v:N", title="Sales"), alt.Tooltip("_g:N", title="Change on the one before")],
    )
    bars = base.mark_bar(color=BLUE, width={"band": 0.6})
    text = base.mark_text(dy=-8, color=MUTED, fontSize=11).encode(text="_g:N")
    return bars + text


def unit_bars(df: pd.DataFrame) -> alt.Chart:
    """df: part, amount, kind. One bar per line of a sachet's money, coloured by In, Cost or Profit,
    with + / − written before the amount."""
    order = df["part"].tolist()
    present = [k for k in UNIT if k in set(df["kind"])]
    sign = "(datum.kind == 'Cost' || datum.kind == 'Promo' || datum.kind == 'Loss' ? '−' : (datum.kind == 'In' ? '+' : '='))"
    base = alt.Chart(df).transform_calculate(
        _v=sign + " + ' R ' + format(datum.amount, ',.2f')").encode(
        y=alt.Y("part:N", sort=order, title=None,
                axis=alt.Axis(domain=False, labelAlign="left", labelPadding=168, minExtent=168, maxExtent=168, labelLimit=156)),
        x=alt.X("amount:Q", title=None, axis=None, scale=alt.Scale(domainMin=0, nice=False, padding=64)),
        tooltip=[alt.Tooltip("part:N", title=" "), alt.Tooltip("_v:N", title="Per sachet")],
    )
    bars = base.mark_bar(size=18).encode(color=alt.Color("kind:N", scale=alt.Scale(domain=present, range=[UNIT[k] for k in present]),
                                                         legend=alt.Legend(orient="top", labelExpr="datum.label == 'In' ? 'Money in' : datum.label == 'Promo' ? 'Promo codes' : datum.label")))
    text = base.mark_text(align="left", dx=6, color=INK, fontSize=12).encode(text="_v:N")
    return bars + text


def hbars(df: pd.DataFrame, cat: str, value: str, label: str, colours: dict | None = None, money: bool = False) -> alt.Chart:
    """Horizontal bars, one per row, labelled at the end. Rows keep the order they come in."""
    order = df[cat].tolist()
    present = set(order)
    colour = (alt.Color(f"{cat}:N", scale=alt.Scale(domain=[k for k in colours if k in present], range=[colours[k] for k in colours if k in present]), legend=None)
              if colours else alt.value(BLUE))
    # The number sits at the end of each bar, so there's no x axis. The bars are always the same
    # thickness, whatever the height of the chart, so charts side by side match.
    base = alt.Chart(df).transform_calculate(_v=_num("datum." + value, money)).encode(
        # Labels in a fixed, left-aligned column, so every bar chart lines up the same way.
        y=alt.Y(f"{cat}:N", sort=order, title=None,
                axis=alt.Axis(domain=False, labelAlign="left", labelPadding=LABELS, minExtent=LABELS, maxExtent=LABELS, labelLimit=LABELS - 12)),
        x=alt.X(f"{value}:Q", title=None, axis=None, scale=alt.Scale(domainMin=0, nice=False, padding=48)),
        tooltip=[alt.Tooltip(f"{cat}:N", title=" "), alt.Tooltip("_v:N", title=label)],
    )
    bars = base.mark_bar(size=18).encode(color=colour)
    text = base.mark_text(align="left", dx=6, color=INK, fontSize=12).encode(text="_v:N")
    return bars + text


def hbars_height(n: int) -> int:
    return max(96, 34 * n)


def stacked_months(df: pd.DataFrame, group: str, value: str, colours: dict, label: str, money: bool = False) -> alt.Chart:
    """df: month, group, value, one row per month and group."""
    present = [k for k in colours if k in set(df[group])] + [g for g in df[group].unique() if g not in colours]
    return alt.Chart(df).transform_calculate(_v=_num("datum." + value, money)).mark_bar(stroke="white", strokeWidth=2, width={"band": 0.55}).encode(
        x=alt.X("yearmonth(month):O", title=None, axis=alt.Axis(format="%b %Y", labelAngle=0)),
        y=alt.Y(f"{value}:Q", stack=True, axis=_axis(money)),
        color=alt.Color(f"{group}:N", scale=alt.Scale(domain=present, range=[colours.get(k, "#9a9fb3") for k in present]), sort=present),
        order=alt.Order(f"{group}:N"),
        tooltip=[alt.Tooltip("yearmonth(month):O", title="Month", format="%b %Y"), alt.Tooltip(f"{group}:N", title=" "),
                 alt.Tooltip("_v:N", title=label)],
    )


def grouped_months(df: pd.DataFrame, colours: dict, money: bool = True) -> alt.Chart:
    """df: month, series, value. Bars side by side per month."""
    present = [k for k in colours if k in set(df["series"])]
    return alt.Chart(df).transform_calculate(_v=_num("datum.value", money)).mark_bar(width={"band": 0.85}).encode(
        x=alt.X("yearmonth(month):O", title=None, axis=alt.Axis(format="%b %Y", labelAngle=0)),
        xOffset=alt.XOffset("series:N", sort=present),
        y=alt.Y("value:Q", axis=_axis(money)),
        color=alt.Color("series:N", scale=alt.Scale(domain=present, range=[colours[k] for k in present]), sort=present),
        tooltip=[alt.Tooltip("yearmonth(month):O", title="Month", format="%b %Y"), alt.Tooltip("series:N", title=" "),
                 alt.Tooltip("_v:N", title="Amount")],
    )


def line_over_time(df: pd.DataFrame, x: str, y: str, label: str, money: bool = True) -> alt.Chart:
    hover = alt.selection_point(fields=[x], nearest=True, on="pointerover", empty=False, clear="pointerout")
    base = alt.Chart(df).transform_calculate(_v=_num("datum." + y, money)).encode(
        x=alt.X(f"{x}:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0, tickCount=4, labelOverlap="greedy", labelSeparation=12)))
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=AXIS, strokeDash=[3, 3]).encode(y="y:Q")
    line = base.mark_line(color=BLUE, interpolate="monotone").encode(y=alt.Y(f"{y}:Q", axis=_axis(money)))
    points = base.mark_point(color=BLUE, size=70, stroke="white", strokeWidth=2).encode(
        y=f"{y}:Q", opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip(f"{x}:T", title="Day", format="%d %b %Y"), alt.Tooltip("_v:N", title=label)],
    ).add_params(hover)
    rule = base.mark_rule(color=AXIS).encode(opacity=alt.condition(hover, alt.value(1), alt.value(0))).transform_filter(hover)
    return alt.layer(zero, line, rule, points)

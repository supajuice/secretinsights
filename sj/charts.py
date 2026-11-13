"""Chart building blocks, so every chart looks the same and follows the same rules:
thin bars with rounded ends, 2px lines, quiet grid, one axis, a tooltip on every mark,
fixed colours per thing (a flavour is always its fruit colour), and the numbers one click away.
"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

# Brand
BLUE = "#1340c8"  # one series
INK = "#0e1a3d"
MUTED = "#5b6383"
GRID = "#ece7cf"
AXIS = "#c9c2a0"
GOOD = "#0ca30c"
CRITICAL = "#d03b3b"

# Each thing keeps its colour everywhere. Flavours are their fruit (validated as a pair).
FLAVOUR_COLOURS = {"Orange": "#f7931e", "Cranberry": "#a3102f", "Not chosen": "#9a9fb3"}
# Categories, statuses and the like: the validated categorical order, assigned in this order, never cycled.
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
CATEGORY_COLOURS = dict(zip(["Ingredients", "Packaging", "Shipping & boxes", "Payment fees", "Tech & software", "Marketing", "Other"], SLOTS))
STATUS_COLOURS = {"New request": SLOTS[6], "Awaiting payment": SLOTS[3], "Paid": SLOTS[0], "Delivered, not paid": SLOTS[1],
                  "Delivered": SLOTS[2], "Cancelled": "#9a9fb3"}
NEW_RETURNING = {"New": SLOTS[0], "Returning": SLOTS[2]}
INCOME_COSTS = {"Income": SLOTS[0], "Costs": SLOTS[1]}

FONT = "Public Sans, system-ui, -apple-system, Segoe UI, sans-serif"


def _theme():
    return {
        "config": {
            "background": "transparent",
            "font": FONT,
            "view": {"stroke": None},
            "axis": {"labelColor": MUTED, "titleColor": MUTED, "gridColor": GRID, "domainColor": AXIS, "tickColor": AXIS,
                     "labelFontSize": 12, "titleFontSize": 12, "titleFontWeight": 500},
            "axisX": {"grid": False},
            "legend": {"labelColor": INK, "titleColor": MUTED, "orient": "top", "labelFontSize": 12, "titleFontSize": 12, "symbolType": "circle"},
            "bar": {"cornerRadiusEnd": 4},
            "line": {"strokeWidth": 2},
            "point": {"size": 64, "filled": True},
        }
    }


alt.theme.register("supajuice", enable=True)(_theme)


def rand(v: float | None, cents: bool = False) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    sign = "-" if v < 0 else ""
    v = abs(v)
    return sign + "R " + (f"{v:,.2f}" if cents else f"{v:,.0f}").replace(",", " ")


def _scale(colours: dict, present) -> alt.Scale:
    keys = [k for k in colours if k in set(present)]
    return alt.Scale(domain=keys, range=[colours[k] for k in keys])


def show(chart: alt.Chart, table: pd.DataFrame, key: str, height: int = 260):
    """The chart, then its numbers in a fold-out table (for screen readers, and for exact figures)."""
    st.altair_chart(chart.properties(height=height), width="stretch")
    with st.expander("See the numbers", expanded=False):
        st.dataframe(table, hide_index=True, width="stretch", key=key)


def bars_over_time(df: pd.DataFrame, x: str, y: str, every: str, title_y: str, money: bool = True) -> alt.Chart:
    fmt = {"Day": "%d %b", "Week": "%d %b", "Month": "%b %Y"}[every]
    unit = {"Day": "yearmonthdate", "Week": "yearmonthdate", "Month": "yearmonth"}[every]
    tip = [alt.Tooltip(f"{x}:T", title={"Day": "Day", "Week": "Week from", "Month": "Month"}[every], format=fmt),
           alt.Tooltip(f"{y}:Q", title=title_y, format=",.0f")]
    return alt.Chart(df).mark_bar(color=BLUE, width={"band": 0.7}).encode(
        x=alt.X(f"{unit}({x}):O", title=None, axis=alt.Axis(format=fmt, labelAngle=0, labelOverlap="greedy")),
        y=alt.Y(f"{y}:Q", title=title_y, axis=alt.Axis(format=",.0f", tickCount=5)),
        tooltip=tip,
    )


def hbars(df: pd.DataFrame, label: str, value: str, title: str, colours: dict | None = None, fmt: str = ",.0f") -> alt.Chart:
    order = df[label].tolist()
    colour = alt.Color(f"{label}:N", scale=_scale(colours, order), legend=None) if colours else alt.value(BLUE)
    base = alt.Chart(df).encode(
        y=alt.Y(f"{label}:N", sort=order, title=None, axis=alt.Axis(labelLimit=180)),
        x=alt.X(f"{value}:Q", title=title, axis=alt.Axis(format=fmt, tickCount=4)),
        tooltip=[alt.Tooltip(f"{label}:N", title=label.capitalize()), alt.Tooltip(f"{value}:Q", title=title, format=fmt)],
    )
    bars = base.mark_bar(height={"band": 0.6}).encode(color=colour)
    labels = base.mark_text(align="left", dx=6, color=INK, fontSize=12).encode(text=alt.Text(f"{value}:Q", format=fmt))
    return bars + labels


def stacked_over_time(df: pd.DataFrame, x: str, y: str, group: str, colours: dict, title_y: str) -> alt.Chart:
    present = df[group].unique().tolist()
    return alt.Chart(df).mark_bar(stroke="white", strokeWidth=2, width={"band": 0.7}).encode(
        x=alt.X(f"yearmonth({x}):O", title=None, axis=alt.Axis(format="%b %Y", labelAngle=0)),
        y=alt.Y(f"sum({y}):Q", title=title_y, axis=alt.Axis(format=",.0f", tickCount=5)),
        color=alt.Color(f"{group}:N", scale=_scale(colours, present), title=None),
        order=alt.Order(f"{group}:N"),
        tooltip=[alt.Tooltip(f"yearmonth({x}):O", title="Month", format="%b %Y"), alt.Tooltip(f"{group}:N", title=group.capitalize()),
                 alt.Tooltip(f"sum({y}):Q", title=title_y, format=",.0f")],
    )


def grouped_monthly(df: pd.DataFrame, colours: dict, title_y: str) -> alt.Chart:
    """df: month, series, value. Bars side by side per month."""
    present = df["series"].unique().tolist()
    return alt.Chart(df).mark_bar(width={"band": 0.9}).encode(
        x=alt.X("yearmonth(month):O", title=None, axis=alt.Axis(format="%b %Y", labelAngle=0)),
        xOffset=alt.XOffset("series:N", sort=present),
        y=alt.Y("value:Q", title=title_y, axis=alt.Axis(format=",.0f", tickCount=5)),
        color=alt.Color("series:N", scale=_scale(colours, present), title=None, sort=present),
        tooltip=[alt.Tooltip("yearmonth(month):O", title="Month", format="%b %Y"), alt.Tooltip("series:N", title=" "),
                 alt.Tooltip("value:Q", title="Rand", format=",.0f")],
    )


def line_over_time(df: pd.DataFrame, x: str, y: str, title_y: str, colour: str = BLUE, zero_rule: bool = False) -> alt.Chart:
    hover = alt.selection_point(fields=[x], nearest=True, on="pointerover", empty=False, clear="pointerout")
    base = alt.Chart(df).encode(x=alt.X(f"{x}:T", title=None, axis=alt.Axis(format="%d %b", labelAngle=0, tickCount=6)))
    line = base.mark_line(color=colour, interpolate="monotone").encode(y=alt.Y(f"{y}:Q", title=title_y, axis=alt.Axis(format=",.0f", tickCount=5)))
    points = base.mark_point(color=colour, size=70, stroke="white", strokeWidth=2).encode(
        y=f"{y}:Q", opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip(f"{x}:T", title="Day", format="%d %b %Y"), alt.Tooltip(f"{y}:Q", title=title_y, format=",.0f")],
    ).add_params(hover)
    rule = base.mark_rule(color=AXIS).encode(opacity=alt.condition(hover, alt.value(1), alt.value(0))).transform_filter(hover)
    layers = [line, rule, points]
    if zero_rule:
        layers.insert(0, alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=AXIS, strokeDash=[3, 3]).encode(y="y:Q"))
    return alt.layer(*layers)


def tile(col, label: str, value: str, delta: float | None = None, help: str | None = None, good_when_up: bool = True):
    """A stat tile; the arrow compares with the same length of time just before."""
    d = None if delta is None else f"{delta:+.0f}% vs before"
    col.metric(label, value, delta=d, delta_color="normal" if good_when_up else "inverse", help=help, border=True)

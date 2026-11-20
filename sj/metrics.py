"""The sums. Plain pandas, no Streamlit, so they can be tested on their own.

Rules copied from the order site and the books, so the numbers agree:
  - an order counts as a sale when its status is Paid or Delivered (the books' SOLD);
  - its sale day is the day it was paid, or the day it was created when that is blank;
  - money is in rand; the SARS tax year runs 1 March to the end of February.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

import pandas as pd

SOLD = ("Paid", "Delivered")
FLAVOURS = (("orange", "Orange"), ("cranberry", "Cranberry"))
CATEGORIES = ["Ingredients", "Packaging", "Shipping & boxes", "Payment fees", "Tech & software", "Marketing", "Other"]
TURNOVER_LIMIT = 1_000_000  # VAT registration and the micro-business turnover tax limit, in rand
BUSINESS = "Business"


# ---------------------------------------------------------------------------
# Periods
# ---------------------------------------------------------------------------

def tax_year(day: date) -> tuple[date, date, str]:
    start_year = day.year if day.month >= 3 else day.year - 1
    end = date(start_year + 1, 3, 1) - timedelta(days=1)
    return date(start_year, 3, 1), end, "%d/%02d" % (start_year, (start_year + 1) % 100)


PERIODS = ["This month", "Last month", "Last 30 days", "Last 3 months", "This tax year", "All time", "Custom"]


def period(name: str, today: date, first: date | None = None, custom: tuple[date, date] | None = None) -> tuple[date, date]:
    """(start, end), both included."""
    if name == "This month":
        return today.replace(day=1), today
    if name == "Last month":
        end = today.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end
    if name == "Last 30 days":
        return today - timedelta(days=29), today
    if name == "Last 3 months":
        m = today.month - 2
        y = today.year + (m - 1) // 12
        return date(y, (m - 1) % 12 + 1, 1), today
    if name == "This tax year":
        return tax_year(today)[0], today
    if name == "Custom" and custom:
        return custom
    return (first or date(today.year, 1, 1)), today


def previous(start: date, end: date) -> tuple[date, date]:
    """The same length of time just before, for the 'compared with' arrows."""
    days = (end - start).days + 1
    return start - timedelta(days=days), start - timedelta(days=1)


def change(now: float, before: float) -> float | None:
    """Percent change, or None when there is nothing to compare with."""
    if not before:
        return None
    return (now - before) / before * 100


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def _when(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series.fillna("").astype(str).str.slice(0, 16), errors="coerce", format="mixed")


def orders_frame(orders: list[dict]) -> pd.DataFrame:
    cols = ["invoice", "created", "status", "qty", "price", "fee", "total", "items", "discount", "collect", "code", "source",
            "customer", "email", "name", "orange", "cranberry", "sold", "sale_day", "created_day"]
    df = pd.DataFrame(orders) if orders else pd.DataFrame({"invoice": pd.Series(dtype=str), "created": pd.Series(dtype=str),
                                                         "status": pd.Series(dtype=str)})
    for c, default in (("fee", 0), ("price", 0), ("qty", 0), ("total", 0), ("code", ""), ("source", ""), ("email", ""), ("name", ""),
                       ("collect", False), ("paidOn", ""), ("flavours", None)):
        if c not in df:
            df[c] = default
    df["created"] = _when(df["created"])
    paid = _when(df["paidOn"])
    for c in ("qty", "price", "fee", "total"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["items"] = df["qty"] * df["price"]
    df["discount"] = (df["items"] + df["fee"] - df["total"]).clip(lower=0)
    df["collect"] = df["collect"].fillna(False).astype(bool)
    df["code"] = df["code"].fillna("").astype(str).str.upper()
    df["sold"] = df["status"].isin(SOLD)
    df["sale_day"] = paid.fillna(df["created"]).dt.normalize()
    df.loc[~df["sold"], "sale_day"] = pd.NaT
    df["created_day"] = df["created"].dt.normalize()
    # One customer per email; orders taken by DM without an email go by name. The public
    # snapshot has no emails or names, only a number per customer, made the same way.
    if "customer" not in df:
        email = df["email"].fillna("").astype(str).str.strip().str.lower()
        name = df["name"].fillna("").astype(str).str.strip().str.lower()
        df["customer"] = email.where(email != "", "name:" + name)
    for key, _ in FLAVOURS:
        df[key] = df["flavours"].map(lambda f, k=key: (f or {}).get(k, 0) if isinstance(f, dict) else math.nan)
    return df[cols]


def between(df: pd.DataFrame, column: str, start: date, end: date) -> pd.DataFrame:
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    return df[(df[column] >= s) & (df[column] <= e)]


def sales(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    return between(df[df["sold"]], "sale_day", start, end)


def sales_summary(df: pd.DataFrame, start: date, end: date) -> dict:
    s = sales(df, start, end)
    n = len(s)
    return {
        "revenue": float(s["total"].sum()),
        "orders": n,
        "sachets": int(s["qty"].sum()),
        "avg_order": float(s["total"].sum() / n) if n else 0.0,
        "delivery_fees": float(s["fee"].sum()),
        "discounts": float(s["discount"].sum()),
        "customers": int(s["customer"].nunique()),
    }


def awaiting_payment(df: pd.DataFrame, start: date, end: date) -> int:
    """Orders placed in the period that aren't paid yet (not counted as sales until they are).
    Cancelled orders are left out."""
    s = between(df, "created_day", start, end)
    return int((~s["sold"] & (s["status"] != "Cancelled")).sum())


def unpaid_note(n: int) -> str:
    """The line under the order tiles, or '' when every order in the period is paid."""
    if not n:
        return ""
    word = "order" if n == 1 else "orders"
    return f"Plus {n} {word} waiting for payment. They count once they're paid; Orders by status on the Sales page shows every order."


def sales_over_time(df: pd.DataFrame, start: date, end: date, every: str) -> pd.DataFrame:
    """Revenue, orders and sachets per day, week (starting Monday) or month, with empty ones as zero."""
    s = sales(df, start, end)
    if every == "Week":
        keys = s["sale_day"] - pd.to_timedelta(s["sale_day"].dt.weekday, unit="D")
        first = pd.Timestamp(start) - pd.Timedelta(days=start.weekday())
        index = pd.date_range(first, pd.Timestamp(end), freq="7D")
    elif every == "Month":
        keys = s["sale_day"].dt.to_period("M").dt.to_timestamp()
        index = pd.date_range(pd.Timestamp(start).replace(day=1), pd.Timestamp(end), freq="MS")
    else:
        keys = s["sale_day"]
        index = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq="D")
    g = s.groupby(keys).agg(revenue=("total", "sum"), orders=("invoice", "count"), sachets=("qty", "sum"))
    g = g.reindex(index, fill_value=0)
    g.index.name = "period"
    return g.reset_index()


def status_counts(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Every order created in the period, by where it is now."""
    order = ["New request", "Awaiting payment", "Paid", "Delivered, not paid", "Delivered", "Cancelled"]
    c = between(df, "created_day", start, end)["status"].value_counts()
    rows = [(s, int(c.get(s, 0))) for s in order if c.get(s, 0)] + [(s, int(n)) for s, n in c.items() if s not in order]
    return pd.DataFrame(rows, columns=["status", "orders"])


def flavour_mix(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    s = sales(df, start, end)
    rows = [(label, int(s[key].fillna(0).sum())) for key, label in FLAVOURS]
    unknown = int(s.loc[s["orange"].isna(), "qty"].sum())
    if unknown:
        rows.append(("Not chosen", unknown))
    return pd.DataFrame(rows, columns=["flavour", "sachets"])


def fulfilment(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    s = sales(df, start, end)
    rows = [("Collected", int((s["collect"]).sum()), float(s.loc[s["collect"], "total"].sum())),
            ("Sent", int((~s["collect"]).sum()), float(s.loc[~s["collect"], "total"].sum()))]
    return pd.DataFrame(rows, columns=["how", "orders", "revenue"])


def codes(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    s = sales(df, start, end)
    s = s[s["code"] != ""]
    g = s.groupby("code").agg(orders=("invoice", "count"), discount=("discount", "sum"), revenue=("total", "sum"))
    return g.sort_values("orders", ascending=False).reset_index()


def weekdays(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    s = between(df[df["status"] != "Cancelled"], "created_day", start, end)
    c = s["created"].dt.weekday.value_counts()
    return pd.DataFrame({"day": names, "orders": [int(c.get(i, 0)) for i in range(7)]})


def order_sizes(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    s = sales(df, start, end)
    c = s["qty"].astype(int).value_counts().sort_index()
    return pd.DataFrame({"sachets": c.index.astype(int), "orders": c.values.astype(int)})


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

def customers(df: pd.DataFrame) -> pd.DataFrame:
    """One row per customer, all time: when they first and last bought, how often, how much."""
    s = df[df["sold"]]
    if s.empty:
        return pd.DataFrame(columns=["customer", "name", "first", "last", "orders", "sachets", "spent"])
    g = s.sort_values("sale_day").groupby("customer").agg(
        name=("name", "last"), first=("sale_day", "min"), last=("sale_day", "max"),
        orders=("invoice", "count"), sachets=("qty", "sum"), spent=("total", "sum"))
    return g.sort_values("spent", ascending=False).reset_index()


def new_and_returning(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Per month: customers buying for the first time, and ones who had bought before."""
    s = df[df["sold"]].copy()
    if s.empty:
        return pd.DataFrame(columns=["month", "kind", "customers"])
    first = s.groupby("customer")["sale_day"].min()
    s["month"] = s["sale_day"].dt.to_period("M").dt.to_timestamp()
    s = s[(s["sale_day"] >= pd.Timestamp(start)) & (s["sale_day"] <= pd.Timestamp(end))]
    s["first_month"] = s["customer"].map(first).dt.to_period("M").dt.to_timestamp()
    s["kind"] = (s["month"] == s["first_month"]).map({True: "New", False: "Returning"})
    g = s.groupby(["month", "kind"])["customer"].nunique().rename("customers").reset_index()
    months = pd.date_range(pd.Timestamp(start).replace(day=1), pd.Timestamp(end), freq="MS")
    full = pd.MultiIndex.from_product([months, ["New", "Returning"]], names=["month", "kind"])
    return g.set_index(["month", "kind"]).reindex(full, fill_value=0).reset_index()


def repeat_rate(df: pd.DataFrame, end: date) -> float | None:
    """Of everyone who has bought up to `end`, the share who bought more than once."""
    s = df[df["sold"] & (df["sale_day"] <= pd.Timestamp(end))]
    if s.empty:
        return None
    n = s.groupby("customer")["invoice"].count()
    return float((n > 1).mean() * 100)


# ---------------------------------------------------------------------------
# Books
# ---------------------------------------------------------------------------

def _table(rows: list, cols: list[str], money: tuple[str, ...] = ("amount",), numbers: tuple[str, ...] = ()) -> pd.DataFrame:
    df = pd.DataFrame(rows or [], columns=None if rows else cols)
    for c in cols:
        if c not in df:
            df[c] = ""
    for c in money + numbers:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["day"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def books_frames(books: dict) -> dict:
    e = books.get("entries", {}) if books else {}
    return {
        "expense": _table(e.get("expense"), ["id", "date", "amount", "category", "supplier", "what", "paidBy", "receipt"]),
        "money": _table(e.get("money"), ["id", "date", "amount", "kind", "who", "sachets"], numbers=("sachets",)),
        "batch": _table(e.get("batch"), ["id", "date", "flavour", "sachets", "cost"], money=("cost",), numbers=("sachets",)),
        "sales": _table(books.get("sales") if books else [], ["id", "date", "qty", "total", "fee", "discount", "card"],
                        money=("total", "fee", "discount"), numbers=("qty",)),
    }


def _settings(books: dict) -> dict:
    raw = (books or {}).get("settings", {}) or {}
    def num(k, d):
        try:
            return float(raw.get(k, d))
        except (TypeError, ValueError):
            return d
    return {
        "card_fees": raw.get("card_fees", "estimate"), "card_percent": num("card_fee_percent", 2.9), "card_fixed": num("card_fee_fixed", 1),
        "books_start": pd.to_datetime(raw.get("books_start", "2026-03-01"), errors="coerce"), "opening": num("opening_balance", 0),
    }


def card_fee(sales_rows: pd.DataFrame, books: dict) -> pd.Series:
    s = _settings(books)
    if s["card_fees"] != "estimate" or sales_rows.empty:
        return pd.Series(0.0, index=sales_rows.index)
    card = sales_rows["card"].astype(bool)
    return (sales_rows["total"] * s["card_percent"] / 100 + s["card_fixed"]).round(2).where(card, 0.0)


def monthly_pnl(books: dict, start: date, end: date) -> pd.DataFrame:
    """Per month, the books' way (cash basis): income (website and other sales) and costs (expenses and card fees)."""
    f = books_frames(books)
    months = pd.date_range(pd.Timestamp(start).replace(day=1), pd.Timestamp(end), freq="MS")
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    def per_month(df, value):
        df = df[(df["day"] >= s) & (df["day"] <= e)]
        return value(df).groupby(df["day"].dt.to_period("M").dt.to_timestamp()).sum().reindex(months, fill_value=0)
    web = f["sales"].copy()
    web["card_fee"] = card_fee(web, books)
    other = f["money"][f["money"]["kind"] == "Other sale"]
    income = per_month(web, lambda d: d["total"]) + per_month(other, lambda d: d["amount"])
    costs = per_month(f["expense"], lambda d: d["amount"]) + per_month(web, lambda d: d["card_fee"])
    out = pd.DataFrame({"month": months, "income": income.values, "costs": costs.values})
    out["profit"] = out["income"] - out["costs"]
    out["running_profit"] = out["profit"].cumsum()
    return out


def expenses_by_category(books: dict, start: date, end: date) -> pd.DataFrame:
    x = books_frames(books)["expense"]
    x = x[(x["day"] >= pd.Timestamp(start)) & (x["day"] <= pd.Timestamp(end))]
    g = x.groupby("category")["amount"].agg(["sum", "count"])
    rows = [(c, float(g.loc[c, "sum"]), int(g.loc[c, "count"])) for c in CATEGORIES if c in g.index]
    rows += [(c, float(r["sum"]), int(r["count"])) for c, r in g.iterrows() if c not in CATEGORIES]
    return pd.DataFrame(rows, columns=["category", "amount", "entries"])


def expenses_by_month(books: dict, start: date, end: date) -> pd.DataFrame:
    x = books_frames(books)["expense"]
    x = x[(x["day"] >= pd.Timestamp(start)) & (x["day"] <= pd.Timestamp(end))].copy()
    x["month"] = x["day"].dt.to_period("M").dt.to_timestamp()
    return x.groupby(["month", "category"])["amount"].sum().reset_index()


def cash_over_time(books: dict, end: date) -> pd.DataFrame:
    """Cash in the business account at the end of each day, counted from the books' start day."""
    st = _settings(books)
    f = books_frames(books)
    start = st["books_start"]
    e = pd.Timestamp(end)
    moves = []
    m = f["money"]
    moves.append(m[m["kind"].isin(["Loan", "Capital", "Other sale"])][["day", "amount"]])
    paid_back = m[m["kind"] == "Paid back"][["day", "amount"]].copy()
    paid_back["amount"] *= -1
    moves.append(paid_back)
    web = f["sales"].copy()
    web["amount"] = web["total"] - card_fee(web, books)
    moves.append(web[["day", "amount"]])
    spent = f["expense"][f["expense"]["paidBy"] == BUSINESS][["day", "amount"]].copy()
    spent["amount"] *= -1
    moves.append(spent)
    all_moves = pd.concat(moves)
    all_moves = all_moves[(all_moves["day"] >= start) & (all_moves["day"] <= e)]
    days = pd.date_range(start, e, freq="D")
    daily = all_moves.groupby("day")["amount"].sum().reindex(days, fill_value=0)
    return pd.DataFrame({"day": days, "cash": st["opening"] + daily.cumsum().values})


def stock(books: dict, orders_df: pd.DataFrame, end: date) -> pd.DataFrame:
    """Per flavour: sachets made (Batches) and sold (website orders with flavours), up to `end`."""
    b = books_frames(books)["batch"]
    b = b[b["day"] <= pd.Timestamp(end)]
    made = b.groupby("flavour")["sachets"].sum()
    s = orders_df[orders_df["sold"] & (orders_df["sale_day"] <= pd.Timestamp(end))]
    rows = []
    for key, label in FLAVOURS:
        rows.append((label, int(made.get(label, 0)), int(s[key].fillna(0).sum())))
    return pd.DataFrame(rows, columns=["flavour", "made", "sold"])


def report(books: dict, start: date, end: date) -> dict:
    """The books' report for a period, worked out here. Used in demo mode; live mode asks the books."""
    f = books_frames(books)
    st = _settings(books)
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    within = lambda df: df[(df["day"] >= s) & (df["day"] <= e)]
    upto = lambda df: df[df["day"] <= e]
    web = f["sales"].copy()
    web["card_fee"] = card_fee(web, books)
    m = f["money"]
    other = m[m["kind"] == "Other sale"]
    income = within(web)["total"].sum() + within(other)["amount"].sum()
    costs = within(f["expense"])["amount"].sum() + within(web)["card_fee"].sum()
    made = upto(f["batch"])
    sold_in = within(web)["qty"].sum() + within(other)["sachets"].sum()
    sachet_income = (within(web)["total"] - within(web)["fee"]).sum() + within(other)["amount"].sum()
    cost_each = made["cost"].sum() / made["sachets"].sum() if made["sachets"].sum() else None
    avg_price = sachet_income / sold_in if sold_in else None
    cash = cash_over_time(books, end)
    owners = []
    names = list((books or {}).get("owners", []))
    exp = upto(f["expense"])
    for n in exp.loc[exp["paidBy"] != BUSINESS, "paidBy"].unique().tolist() + upto(m)["who"].unique().tolist():
        if n and n not in names:
            names.append(n)
    for n in names:
        mine = upto(m[m["who"] == n])
        o = {"name": n, "loan": float(mine.loc[mine["kind"] == "Loan", "amount"].sum()),
             "capital": float(mine.loc[mine["kind"] == "Capital", "amount"].sum()),
             "expenses": float(exp.loc[exp["paidBy"] == n, "amount"].sum()),
             "paidBack": float(mine.loc[mine["kind"] == "Paid back", "amount"].sum())}
        o["owed"] = o["loan"] + o["expenses"] - o["paidBack"]
        owners.append(o)
    ty_start, ty_end, ty_label = tax_year(end)
    in_year = lambda df: df[(df["day"] >= pd.Timestamp(ty_start)) & (df["day"] <= e)]
    turnover = in_year(web)["total"].sum() + in_year(other)["amount"].sum()
    return {
        "from": start.isoformat(), "to": end.isoformat(),
        "income": float(income), "costs": float(costs), "profit": float(income - costs),
        "perSachet": {"sold": int(sold_in), "avgPrice": avg_price, "costToMake": cost_each,
                      "margin": (avg_price - cost_each) if avg_price is not None and cost_each is not None else None},
        "cash": {"onHand": float(cash["cash"].iloc[-1]) if len(cash) else st["opening"]},
        "owners": owners,
        "taxYear": {"label": ty_label, "start": ty_start.isoformat(), "end": ty_end.isoformat(), "turnover": float(turnover),
                    "limit": TURNOVER_LIMIT, "percent": round(float(turnover) / TURNOVER_LIMIT * 100, 1)},
        "missingReceipts": int((within(f["expense"])["receipt"].fillna("") == "").sum()),
    }

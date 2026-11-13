"""The public snapshot: the numbers the online dashboard shows, with nothing private in it.

Made by the GitHub Action (scripts/build_site.py) from the orders and the books. Kept:
amounts, dates, statuses, flavours, categories, owners' names. Left out: customers' names,
emails, phone numbers, addresses and order notes, receipt links, and notes on books entries.
Each customer becomes a number (C1, C2, ...) so repeat customers can still be counted.
The admin keys are never in it: they are only used to read, before this is made.
"""
from __future__ import annotations

import json
import re

VERSION = 1
CARD_TAG = re.compile(r"Paid by card \(Paystack")

ORDER_FIELDS = ["invoice", "created", "source", "qty", "price", "fee", "total", "status", "paidOn", "deliveredOn",
                "collect", "code", "discountPct", "freeDelivery", "flavours"]
EXPENSE_FIELDS = ["id", "date", "amount", "category", "supplier", "what", "paidBy", "vat"]
MONEY_FIELDS = ["id", "date", "amount", "kind", "who", "sachets"]
BATCH_FIELDS = ["id", "date", "flavour", "sachets", "cost"]
SALE_FIELDS = ["id", "date", "qty", "total", "fee", "discount", "card"]
SETTINGS = ["books_start", "opening_balance", "card_fees", "card_fee_percent", "card_fee_fixed", "vat_registered"]


def _pick(row: dict, fields: list[str]) -> dict:
    return {k: row.get(k) for k in fields if k in row}


def make(orders: list[dict], books: dict, generated: str, today: str) -> dict:
    ids: dict[str, str] = {}

    def customer(o: dict) -> str:
        if o.get("customer"):  # already a number: the read-only insights action sends them so
            return str(o["customer"])
        email = str(o.get("email") or "").strip().lower()
        who = email or "name:" + str(o.get("name") or "").strip().lower()
        if who not in ids:
            ids[who] = "C%d" % (len(ids) + 1)
        return ids[who]

    # Oldest first, so the numbers follow the order people first bought.
    ordered = sorted(orders or [], key=lambda o: str(o.get("created") or ""))
    safe_orders = []
    for o in ordered:
        row = _pick(o, ORDER_FIELDS)
        row["customer"] = customer(o)
        row["card"] = bool(o["card"]) if "card" in o else bool(CARD_TAG.search(str(o.get("notes") or "")))
        safe_orders.append(row)

    entries = (books or {}).get("entries", {}) or {}
    expenses = []
    for e in entries.get("expense", []) or []:
        row = _pick(e, EXPENSE_FIELDS)
        row["receipt"] = "yes" if e.get("receipt") else ""  # whether there is one, not the link
        expenses.append(row)
    raw = (books or {}).get("settings", {}) or {}
    return {
        "version": VERSION,
        "generated": generated,
        "today": today,
        "orders": safe_orders,
        "books": {
            "entries": {
                "expense": expenses,
                "money": [_pick(m, MONEY_FIELDS) for m in entries.get("money", []) or []],
                "batch": [_pick(b, BATCH_FIELDS) for b in entries.get("batch", []) or []],
            },
            "sales": [_pick(s, SALE_FIELDS) for s in (books or {}).get("sales", []) or []],
            "settings": {k: raw[k] for k in SETTINGS if k in raw},
            "owners": list((books or {}).get("owners", []) or []),
            "salesConnected": bool((books or {}).get("salesConnected", True)),
            "today": today,
        },
    }


def dumps(snap: dict) -> str:
    return json.dumps(snap, ensure_ascii=False, separators=(",", ":"))

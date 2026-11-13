"""Made-up sample data in the same shape as the live sources, for trying the dashboard.

The same every time (a fixed random seed), so the tests can rely on it.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

TODAY = date(2026, 11, 11)
START = date(2026, 6, 1)

PEOPLE = [
    ("Thandi Mokoena", "thandi@example.com"), ("Liam Botha", "liam@example.com"), ("Aisha Patel", "aisha@example.com"),
    ("Pieter van Wyk", "pieter@example.com"), ("Naledi Dlamini", "naledi@example.com"), ("Sam Jacobs", "sam@example.com"),
    ("Zoe Adams", "zoe@example.com"), ("Kabelo Nkosi", "kabelo@example.com"), ("Megan Smith", "megan@example.com"),
    ("Yusuf Khan", "yusuf@example.com"), ("Lerato Molefe", "lerato@example.com"), ("Chris Fourie", "chris@example.com"),
    ("Anele Zulu", "anele@example.com"), ("Jess Muller", "jess@example.com"), ("Ravi Naidoo", "ravi@example.com"),
    ("Emma Louw", "emma@example.com"), ("Sipho Ndlovu", "sipho@example.com"), ("Kate Ferreira", "kate@example.com"),
]


def _stamp(d: date, rng: random.Random) -> str:
    t = datetime(d.year, d.month, d.day, rng.randint(6, 21), rng.choice([0, 10, 15, 20, 30, 40, 45, 50]))
    return t.strftime("%Y-%m-%d %H:%M")


def orders() -> list[dict]:
    rng = random.Random(15)
    out = []
    regulars = PEOPLE[:6]  # these come back
    d = START
    n = 0
    while d <= TODAY:
        # More orders as word spreads, and on race weekends (Saturdays).
        weeks = (d - START).days / 7
        chance = 0.18 + weeks * 0.012 + (0.25 if d.weekday() == 5 else 0)
        if rng.random() < chance:
            n += 1
            name, email = rng.choice(regulars) if rng.random() < 0.45 else rng.choice(PEOPLE)
            qty = rng.choice([5, 5, 5, 6, 8, 10, 10, 12, 15, 20])
            orange = rng.randint(0, qty) if rng.random() < 0.85 else None
            collect = rng.random() < 0.55
            fee = 0 if collect else rng.choice([69, 69, 99, 120])
            code = "SUPA15" if rng.random() < 0.15 else ""
            pct = 15 if code else 0
            price = 40 if d < date(2026, 9, 1) else 42
            items = qty * price
            total = round(items * (100 - pct) / 100) + fee
            created = _stamp(d, rng)
            age = (TODAY - d).days
            r = rng.random()
            if age <= 2 and r < 0.6:
                status = "Awaiting payment"
            elif r < 0.07:
                status = "Cancelled"
            elif age <= 6 and r < 0.5:
                status = "Paid"
            else:
                status = "Delivered"
            paid = created if status in ("Paid", "Delivered") else ""
            card = rng.random() < 0.35
            out.append({
                "invoice": "SJ-%04d" % n, "created": created, "source": "dm" if rng.random() < 0.2 else "kiosk",
                "name": name, "contact": "", "address": "", "notes": ("Paid by card (Paystack SJ-%04d-x)" % n) if card and paid else "",
                "qty": qty, "price": price, "fee": fee, "total": total, "status": status,
                "paidOn": paid, "deliveredOn": created if status == "Delivered" else "", "email": email,
                "collect": collect, "code": code, "discountPct": pct, "freeDelivery": False,
                "flavours": None if orange is None else {"orange": orange, "cranberry": qty - orange},
            })
        d += timedelta(days=1)
    return out


def books() -> dict:
    sold = [o for o in orders() if o["status"] in ("Paid", "Delivered")]
    sales = [{
        "id": o["invoice"], "date": (o["paidOn"] or o["created"])[:10], "qty": o["qty"], "total": o["total"], "fee": o["fee"],
        "discount": o["qty"] * o["price"] + o["fee"] - o["total"], "card": "Paystack" in o["notes"],
    } for o in sold]
    expense = [
        ("2026-05-20", 2400, "Ingredients", "Bulk Nutrients", "Maltodextrin and fructose", "Greg"),
        ("2026-05-22", 980, "Packaging", "PackRite", "Sachets x 1000", "Greg"),
        ("2026-05-25", 189, "Tech & software", "Domains.co.za", "Domain for a year", "Greg"),
        ("2026-06-02", 650, "Marketing", "Instagram", "Ads, June", "Business"),
        ("2026-06-14", 850, "Marketing", "Sea Point 10K", "Race stall", "Business"),
        ("2026-06-30", 360, "Tech & software", "Anthropic", "Claude Code, June", "Sam"),
        ("2026-07-05", 420, "Shipping & boxes", "Pudo", "Lockers and boxes", "Business"),
        ("2026-07-18", 1800, "Ingredients", "Bulk Nutrients", "Restock", "Business"),
        ("2026-07-31", 360, "Tech & software", "Anthropic", "Claude Code, July", "Sam"),
        ("2026-08-09", 300, "Marketing", "Samples", "Free samples at parkrun", "Business"),
        ("2026-08-20", 1200, "Packaging", "PackRite", "Sachets x 1200", "Business"),
        ("2026-08-31", 360, "Tech & software", "Anthropic", "Claude Code, August", "Sam"),
        ("2026-09-06", 900, "Marketing", "Cape Town Marathon expo", "Stall", "Business"),
        ("2026-09-15", 2600, "Ingredients", "Bulk Nutrients", "Restock", "Business"),
        ("2026-09-30", 360, "Tech & software", "Anthropic", "Claude Code, September", "Sam"),
        ("2026-10-04", 510, "Shipping & boxes", "Pudo", "Lockers", "Business"),
        ("2026-10-12", 750, "Marketing", "Instagram", "Ads, October", "Business"),
        ("2026-10-31", 360, "Tech & software", "Anthropic", "Claude Code, October", "Sam"),
        ("2026-11-03", 2900, "Ingredients", "Bulk Nutrients", "Restock", "Business"),
        ("2026-11-05", 140, "Other", "Builders", "Scale batteries and labels", "Business"),
    ]
    money = [
        ("2026-05-18", 8000, "Loan", "Greg", 0, "Start-up money"),
        ("2026-06-14", 640, "Other sale", "", 16, "Cash at the race stall"),
        ("2026-09-06", 1260, "Other sale", "", 30, "Marathon expo"),
        ("2026-09-10", 5000, "Capital", "Sam", 0, "Sam joins"),
        ("2026-10-30", 1500, "Paid back", "Greg", 0, ""),
    ]
    batch = [
        ("2026-05-28", "Orange", 300, 1900), ("2026-05-29", "Cranberry", 200, 1350),
        ("2026-07-20", "Orange", 250, 1500), ("2026-07-21", "Cranberry", 150, 950),
        ("2026-09-17", "Orange", 350, 2050), ("2026-09-18", "Cranberry", 250, 1550),
        ("2026-11-04", "Orange", 300, 1800), ("2026-11-05", "Cranberry", 200, 1250),
    ]
    return {
        "ok": True,
        "entries": {
            "expense": [{"id": "E%d" % (i + 1), "date": d, "amount": a, "category": c, "supplier": s, "what": w, "paidBy": p, "vat": 0,
                         "receipt": "" if i % 5 == 3 else "https://drive.google.com/file/d/sample/view", "notes": ""}
                        for i, (d, a, c, s, w, p) in enumerate(expense)],
            "money": [{"id": "M%d" % (i + 1), "date": d, "amount": a, "kind": k, "who": w, "sachets": s, "notes": n}
                      for i, (d, a, k, w, s, n) in enumerate(money)],
            "batch": [{"id": "B%d" % (i + 1), "date": d, "flavour": f, "sachets": s, "cost": c, "notes": ""}
                      for i, (d, f, s, c) in enumerate(batch)],
        },
        "sales": sales,
        "settings": {"brand_name": "Supa Juice", "owners": "Greg, Sam", "books_start": "2026-05-01", "opening_balance": "0",
                     "card_fees": "estimate", "card_fee_percent": "2.9", "card_fee_fixed": "1", "vat_registered": "no"},
        "owners": ["Greg", "Sam"],
        "salesConnected": True,
        "today": TODAY.isoformat(),
    }

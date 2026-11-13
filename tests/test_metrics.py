"""The sums, checked by hand on small examples, and against the sample data."""
import unittest
from datetime import date

from sj import demo, metrics


def order(invoice, created, status, qty=5, price=40, fee=0, total=None, email="a@example.com", name="A", paid=None, flavours=None, collect=True, code=""):
    if total is None:
        total = qty * price + fee
    return {"invoice": invoice, "created": created, "status": status, "qty": qty, "price": price, "fee": fee, "total": total,
            "email": email, "name": name, "paidOn": paid if paid is not None else (created if status in ("Paid", "Delivered") else ""),
            "flavours": flavours, "collect": collect, "code": code, "source": "kiosk"}


class Orders(unittest.TestCase):
    def setUp(self):
        self.df = metrics.orders_frame([
            order("SJ-1", "2026-10-01 09:00", "Delivered", flavours={"orange": 3, "cranberry": 2}),
            order("SJ-2", "2026-10-02 10:00", "Paid", qty=10, fee=69, email="B@Example.com ", name="B", collect=False,
                  code="supa15", total=round(400 * 0.85) + 69, flavours={"orange": 10, "cranberry": 0}),
            order("SJ-3", "2026-10-03 10:00", "Awaiting payment", email="c@example.com"),
            order("SJ-4", "2026-10-04 10:00", "Cancelled", email="d@example.com"),
            # Created in September, paid in October: a sale in October, like the books count it.
            order("SJ-5", "2026-09-30 22:00", "Paid", paid="2026-10-01 08:00", email="a@example.com"),
            # Delivered before it was paid: no paid day yet, so it goes by the day it was made.
            order("SJ-6", "2026-10-05 10:00", "Delivered, not paid", email="e@example.com"),
        ])

    def test_only_paid_and_delivered_count_by_the_day_they_were_paid(self):
        s = metrics.sales_summary(self.df, date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(s["orders"], 3)
        self.assertEqual(s["sachets"], 20)
        self.assertEqual(s["revenue"], 200 + 409 + 200)
        self.assertEqual(s["delivery_fees"], 69)
        self.assertEqual(s["discounts"], 60)
        self.assertEqual(s["customers"], 2, "emails are matched without case or spaces")
        self.assertEqual(metrics.sales_summary(self.df, date(2026, 9, 1), date(2026, 9, 30))["orders"], 0)

    def test_codes_flavours_and_fulfilment(self):
        k = metrics.codes(self.df, date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(k.to_dict("records"), [{"code": "SUPA15", "orders": 1, "discount": 60.0, "revenue": 409.0}])
        f = metrics.flavour_mix(self.df, date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(f.to_dict("records"), [{"flavour": "Orange", "sachets": 13}, {"flavour": "Cranberry", "sachets": 2}, {"flavour": "Not chosen", "sachets": 5}])
        fu = metrics.fulfilment(self.df, date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(fu["orders"].tolist(), [2, 1])

    def test_statuses_cover_every_order_placed(self):
        s = metrics.status_counts(self.df, date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(dict(zip(s["status"], s["orders"])), {"Awaiting payment": 1, "Paid": 1, "Delivered, not paid": 1, "Delivered": 1, "Cancelled": 1})

    def test_weeks_start_on_monday_and_empty_weeks_are_zero(self):
        t = metrics.sales_over_time(self.df, date(2026, 9, 28), date(2026, 10, 18), "Week")
        self.assertEqual([d.strftime("%Y-%m-%d") for d in t["period"]], ["2026-09-28", "2026-10-05", "2026-10-12"])
        self.assertEqual(t["orders"].tolist(), [3, 0, 0])

    def test_customers_new_and_returning(self):
        df = metrics.orders_frame([
            order("SJ-1", "2026-09-10 09:00", "Paid", email="a@example.com"),
            order("SJ-2", "2026-10-10 09:00", "Paid", email="a@example.com"),
            order("SJ-3", "2026-10-11 09:00", "Paid", email="b@example.com"),
            order("SJ-4", "2026-10-12 09:00", "Paid", email="", name="Cash Carl"),
        ])
        nr = metrics.new_and_returning(df, date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(dict(zip(nr["kind"], nr["customers"])), {"New": 2, "Returning": 1})
        self.assertAlmostEqual(metrics.repeat_rate(df, date(2026, 10, 31)), 100 / 3)
        top = metrics.customers(df)
        self.assertEqual(top.iloc[0]["customer"], "a@example.com")
        self.assertEqual(top.iloc[0]["orders"], 2)


class Periods(unittest.TestCase):
    def test_tax_year_runs_march_to_february(self):
        self.assertEqual(metrics.tax_year(date(2026, 11, 11)), (date(2026, 3, 1), date(2027, 2, 28), "2026/27"))
        self.assertEqual(metrics.tax_year(date(2028, 2, 29)), (date(2027, 3, 1), date(2028, 2, 29), "2027/28"))

    def test_periods(self):
        t = date(2026, 11, 11)
        self.assertEqual(metrics.period("This month", t), (date(2026, 11, 1), t))
        self.assertEqual(metrics.period("Last month", t), (date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(metrics.period("Last 3 months", t), (date(2026, 9, 1), t))
        self.assertEqual(metrics.period("Last 3 months", date(2026, 1, 5)), (date(2025, 11, 1), date(2026, 1, 5)))
        self.assertEqual(metrics.period("This tax year", date(2027, 1, 2)), (date(2026, 3, 1), date(2027, 1, 2)))
        self.assertEqual(metrics.previous(date(2026, 10, 1), date(2026, 10, 31)), (date(2026, 8, 31), date(2026, 9, 30)))
        self.assertIsNone(metrics.change(5, 0))
        self.assertEqual(metrics.change(150, 100), 50)


class Books(unittest.TestCase):
    books = {
        "entries": {
            "expense": [
                {"date": "2026-10-02", "amount": 1000, "category": "Ingredients", "paidBy": "Business", "receipt": "x"},
                {"date": "2026-10-05", "amount": 200, "category": "Tech & software", "paidBy": "Greg", "receipt": ""},
            ],
            "money": [
                {"date": "2026-10-01", "amount": 3000, "kind": "Loan", "who": "Greg", "sachets": 0},
                {"date": "2026-10-10", "amount": 400, "kind": "Other sale", "who": "", "sachets": 10},
                {"date": "2026-10-20", "amount": 500, "kind": "Paid back", "who": "Greg", "sachets": 0},
            ],
            "batch": [{"date": "2026-10-03", "flavour": "Orange", "sachets": 100, "cost": 1500}],
        },
        "sales": [
            {"id": "SJ-1", "date": "2026-10-04", "qty": 5, "total": 269, "fee": 69, "discount": 0, "card": True},
            {"id": "SJ-2", "date": "2026-10-06", "qty": 10, "total": 400, "fee": 0, "discount": 0, "card": False},
        ],
        "settings": {"books_start": "2026-10-01", "opening_balance": "100", "card_fees": "estimate", "card_fee_percent": "2.9", "card_fee_fixed": "1"},
        "owners": ["Greg"],
    }

    def test_report_by_hand(self):
        r = metrics.report(self.books, date(2026, 10, 1), date(2026, 10, 31))
        fee = round(269 * 0.029 + 1, 2)  # 8.80, the one card order
        self.assertEqual(r["income"], 269 + 400 + 400)
        self.assertAlmostEqual(r["costs"], 1200 + fee)
        self.assertAlmostEqual(r["profit"], 1069 - 1200 - fee)
        # Cash: opening 100 + loan 3000 + other sale 400 + website (669 - card fee) - business expense 1000 - paid back 500.
        self.assertAlmostEqual(r["cash"]["onHand"], 100 + 3000 + 400 + 669 - fee - 1000 - 500)
        self.assertEqual(r["owners"], [{"name": "Greg", "loan": 3000, "capital": 0, "expenses": 200, "paidBack": 500, "owed": 2700}])
        ps = r["perSachet"]
        self.assertEqual(ps["sold"], 25)
        self.assertAlmostEqual(ps["avgPrice"], (200 + 400 + 400) / 25)
        self.assertEqual(ps["costToMake"], 15)
        self.assertEqual(r["missingReceipts"], 1)
        self.assertEqual(r["taxYear"]["label"], "2026/27")

    def test_months_and_categories(self):
        p = metrics.monthly_pnl(self.books, date(2026, 9, 1), date(2026, 10, 31))
        self.assertEqual(p["income"].tolist(), [0, 1069])
        self.assertEqual(p["running_profit"].iloc[-1], p["profit"].sum())
        c = metrics.expenses_by_category(self.books, date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(c["category"].tolist(), ["Ingredients", "Tech & software"], "in the books' category order")

    def test_card_fees_off_when_they_are_recorded_as_expenses(self):
        books = dict(self.books, settings=dict(self.books["settings"], card_fees="recorded"))
        self.assertEqual(metrics.report(books, date(2026, 10, 1), date(2026, 10, 31))["costs"], 1200)

    def test_empty_books_and_orders_do_not_break(self):
        empty = {"entries": {}, "sales": [], "settings": {}}
        r = metrics.report(empty, date(2026, 10, 1), date(2026, 10, 31))
        self.assertEqual(r["income"], 0)
        self.assertIsNone(r["perSachet"]["margin"])
        df = metrics.orders_frame([])
        self.assertEqual(metrics.sales_summary(df, date(2026, 10, 1), date(2026, 10, 31))["orders"], 0)
        self.assertTrue(metrics.customers(df).empty)


class Sample(unittest.TestCase):
    def test_the_sample_books_agree_with_the_sample_orders(self):
        df = metrics.orders_frame(demo.orders())
        books = demo.books()
        s = metrics.sales_summary(df, date(2026, 6, 1), date(2026, 11, 11))
        web = sum(x["total"] for x in books["sales"])
        self.assertEqual(s["revenue"], web)
        self.assertGreater(s["orders"], 40)


if __name__ == "__main__":
    unittest.main()

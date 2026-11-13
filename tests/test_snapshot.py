"""The public snapshot has nothing private in it, and the online dashboard shows the same numbers."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date

from sj import demo, metrics, snapshot, sources

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_site  # noqa: E402


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.orders = demo.orders()
        self.books = demo.books()
        # Things that must never get out, planted in the source data.
        self.orders[0]["contact"] = "082 555 1234"
        self.orders[0]["address"] = "12 Beach Road, Sea Point"
        self.orders[0]["notes"] = "Ring the bell twice. Paid by card (Paystack SJ-0001-x)"
        self.books["entries"]["money"][0]["notes"] = "Greg's private note"
        self.snap = snapshot.make(self.orders, self.books, "12 Nov 2026, 09:07", "2026-11-11")
        self.text = snapshot.dumps(self.snap)

    def test_no_names_emails_contacts_notes_or_receipt_links(self):
        for name, email in demo.PEOPLE:
            self.assertNotIn(email, self.text)
            self.assertNotIn(name, self.text)
        for secret in ("082 555 1234", "Beach Road", "Ring the bell", "private note", "drive.google.com", "@"):
            self.assertNotIn(secret, self.text)
        self.assertEqual(build_site.private_bits(self.text, ["k-orders", "k-books"]), [])

    def test_the_check_catches_private_things(self):
        self.assertEqual(build_site.private_bits('{"x":"k-orders"}', ["k-orders"]), ["an admin key"])
        self.assertIn("an email address", build_site.private_bits('{"what":"ask jo@shop.co.za"}', []))
        self.assertIn("a Google Drive link", build_site.private_bits('{"r":"https://drive.google.com/x"}', []))
        self.assertIn('the field "email"', build_site.private_bits('{"email":""}', []))

    def test_card_payments_and_receipts_are_kept_as_yes_or_no(self):
        self.assertIs(self.snap["orders"][0]["card"], True)
        receipts = [e["receipt"] for e in self.snap["books"]["entries"]["expense"]]
        self.assertEqual(set(receipts), {"yes", ""})

    def test_the_same_numbers_as_the_private_version(self):
        private = metrics.orders_frame(self.orders)
        public = metrics.orders_frame(self.snap["orders"])
        for start, end in [(date(2026, 6, 1), date(2026, 11, 11)), (date(2026, 10, 1), date(2026, 10, 31))]:
            self.assertEqual(metrics.sales_summary(public, start, end), metrics.sales_summary(private, start, end))
            self.assertEqual(metrics.repeat_rate(public, end), metrics.repeat_rate(private, end))
            a, b = metrics.report(self.snap["books"], start, end), metrics.report(self.books, start, end)
            for k in ("income", "costs", "profit", "cash", "owners", "perSachet", "taxYear", "missingReceipts"):
                self.assertEqual(a[k], b[k], k)
        # Customers keep one number each, in the order they first bought.
        self.assertEqual(self.snap["orders"][0]["customer"], "C1")


class ReadOnly(unittest.TestCase):
    """What the order and books scripts' insights action sends is already anonymous: kept as it is."""

    def test_customer_numbers_and_card_from_the_insights_action_are_kept(self):
        base = {"status": "Paid", "qty": 5, "price": 40, "fee": 0, "total": 200}
        orders = [
            dict(base, invoice="SJ-0001", created="2026-10-01 09:00", paidOn="2026-10-01 09:00", customer="C1", card=True),
            dict(base, invoice="SJ-0002", created="2026-10-02 09:00", paidOn="2026-10-02 09:00", customer="C1", card=False),
            dict(base, invoice="SJ-0003", created="2026-10-03 09:00", paidOn="2026-10-03 09:00", customer="C2", card=False),
        ]
        snap = snapshot.make(orders, {"entries": {}, "sales": [], "settings": {}}, "now", "2026-10-31")
        self.assertEqual([o["customer"] for o in snap["orders"]], ["C1", "C1", "C2"])
        self.assertEqual([o["card"] for o in snap["orders"]], [True, False, False])
        df = metrics.orders_frame(snap["orders"])
        self.assertAlmostEqual(metrics.repeat_rate(df, date(2026, 10, 31)), 50.0)

    def test_the_build_only_asks_for_insights_with_the_read_keys(self):
        sent = []

        def fake(url, body):
            sent.append((body["action"], body["key"]))
            if "orders" in url:
                return {"ok": True, "orders": []}
            return {"ok": True, "entries": {}, "sales": [], "settings": {}, "owners": [], "today": "2026-11-13"}

        real = sources._post
        sources._post = fake
        try:
            d = sources.load_insights("https://x/orders", "read-o", "https://x/books", "read-b")
        finally:
            sources._post = real
        self.assertEqual(sent, [("insights", "read-o"), ("insights", "read-b")])
        self.assertEqual(d.problems, [])
        self.assertNotIn("ok", d.books)


class Build(unittest.TestCase):
    def test_build_the_site_from_the_sample_data(self):
        out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_site.py"), "--demo"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        site = os.path.join(ROOT, "_site")
        try:
            for f in build_site.APP_FILES + ["data.json", "index.html", ".nojekyll"]:
                self.assertTrue(os.path.exists(os.path.join(site, f)), f)
            with open(os.path.join(site, "index.html"), encoding="utf-8") as f:
                html = f.read()
            self.assertIn("@stlite/browser@" + build_site.STLITE + "/build/stlite.js", html)
            self.assertIn('"data.json": { url: "./data.json" }', html)
            self.assertIn("noindex", html)
            # The dashboard reads it as a snapshot.
            d = sources.load_snapshot(os.path.join(site, "data.json"))
            self.assertEqual(d.mode, "snapshot")
            self.assertGreater(len(d.orders), 40)
        finally:
            shutil.rmtree(site, ignore_errors=True)

    def test_without_keys_it_publishes_nothing(self):
        env = {k: v for k, v in os.environ.items() if k not in ("ORDERS_READ_KEY", "BOOKS_READ_KEY")}
        with tempfile.TemporaryDirectory():
            out = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "build_site.py")], cwd=ROOT, capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 1)
        self.assertIn("ORDERS_READ_KEY and BOOKS_READ_KEY are not set", out.stdout)
        self.assertFalse(os.path.exists(os.path.join(ROOT, "_site")))


if __name__ == "__main__":
    unittest.main()

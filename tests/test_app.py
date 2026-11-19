"""Every page opens with the sample data, for every period, without an error."""
import os
import unittest

from streamlit.testing.v1 import AppTest

from sj import metrics, sources

ROOT = os.path.join(os.path.dirname(__file__), "..")
PAGES = ["views/overview.py", "views/sales.py", "views/customers.py", "views/money.py"]


def app():
    at = AppTest.from_file(os.path.join(ROOT, "app.py"), default_timeout=60)
    at.secrets["unused"] = "1"  # no orders/books keys: sample data
    return at


class Pages(unittest.TestCase):
    def test_every_page_and_period(self):
        for period in metrics.PERIODS[:-1]:
            for page in PAGES:
                with self.subTest(period=period, page=page):
                    at = app()
                    at.session_state["period"] = period
                    at.switch_page(page)
                    at.run()
                    self.assertEqual(list(at.exception), [], f"{page} / {period}")
                    self.assertTrue(at.title, "the page has a title")

    def test_sample_data_says_so(self):
        at = app().run()
        self.assertTrue(any("Sample data" in c.value for c in at.caption))
        self.assertTrue(any("made-up numbers" in i.value for i in at.info))
        self.assertTrue(any(m.label == "Website sales" for m in at.metric))


class Online(unittest.TestCase):
    """The online version: the pages run on the public snapshot, and never list customers."""

    def setUp(self):
        import tempfile
        from sj import demo, snapshot
        self.dir = tempfile.TemporaryDirectory()
        path = os.path.join(self.dir.name, "data.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(snapshot.dumps(snapshot.make(demo.orders(), demo.books(), "12 Nov 2026, 09:07", "2026-11-11")))
        self.real = sources.SNAPSHOT
        sources.SNAPSHOT = path

    def tearDown(self):
        sources.SNAPSHOT = self.real
        self.dir.cleanup()

    def test_every_page_on_the_snapshot(self):
        for page in PAGES:
            with self.subTest(page=page):
                at = app()
                at.switch_page(page)
                at.run()
                self.assertEqual(list(at.exception), [], page)
                self.assertTrue(any("Updated 12 Nov 2026, 09:07" in c.value for c in at.caption))
                self.assertEqual(len(at.button), 0, "no refresh button: the Action refreshes it")
                if page == "views/customers.py":
                    for table in at.dataframe:
                        self.assertNotIn("Email", list(table.value.columns), "no list of customers online")
                        self.assertNotIn("Name", list(table.value.columns))
                    self.assertTrue(any("only on the private version" in c.value for c in at.caption))


class Sources(unittest.TestCase):
    def test_configured_needs_both_urls_and_keys(self):
        full = {"orders": {"url": "u", "key": "k"}, "books": {"url": "u", "key": "k"}}
        self.assertTrue(sources.configured(full))
        self.assertFalse(sources.configured({"orders": {"url": "u", "key": ""}, "books": {"url": "u", "key": "k"}}))
        self.assertFalse(sources.configured({}))

    def test_only_read_actions_are_sent(self):
        sent = []

        def fake(url, body):
            sent.append(body["action"])
            return {"ok": True, "orders": [], "report": {}}

        real = sources._post
        sources._post = fake
        try:
            secrets = {"orders": {"url": "u", "key": "k"}, "books": {"url": "u", "key": "k"}}
            sources.load_live(secrets)
            sources.load_report_live(secrets, "2026-10-01", "2026-10-31")
        finally:
            sources._post = real
        self.assertEqual(sent, ["list", "list", "report"])

    def test_no_answer_is_tried_again_but_a_refusal_is_not(self):
        import requests

        calls = []

        class Reply:
            status_code = 200

            def __init__(self, body):
                self.body = body

            def json(self):
                return self.body

        def flaky(url, **kw):
            calls.append(url)
            if len(calls) < 3:
                raise requests.ReadTimeout("slow")
            return Reply({"ok": True, "orders": []})

        real_post, real_pauses, real_sleep = requests.post, sources.RETRY_PAUSES, sources.time.sleep
        requests.post, sources.RETRY_PAUSES, sources.time.sleep = flaky, (10, 30), lambda s: None
        try:
            self.assertEqual(sources._post("https://x/exec", {"action": "insights"}), {"ok": True, "orders": []})
            self.assertEqual(len(calls), 3, "two slow tries, then it answered")

            calls.clear()
            requests.post = lambda url, **kw: (calls.append(url), (_ for _ in ()).throw(requests.ReadTimeout("slow")))[1]
            with self.assertRaises(sources.SourceError) as ctx:
                sources._post("https://x/exec", {"action": "insights"})
            self.assertEqual(len(calls), 3)
            self.assertIn("after 3 tries", str(ctx.exception))

            calls.clear()
            requests.post = lambda url, **kw: (calls.append(url), Reply({"ok": False, "message": "That read key is not right."}))[1]
            with self.assertRaises(sources.SourceError) as ctx:
                sources._post("https://x/exec", {"action": "insights"})
            self.assertEqual(len(calls), 1, "an answer, even a refusal, is not asked again")
            self.assertEqual(str(ctx.exception), "That read key is not right.")
        finally:
            requests.post, sources.RETRY_PAUSES, sources.time.sleep = real_post, real_pauses, real_sleep

    def test_a_refusal_is_shown_not_crashed(self):
        def fake(url, body):
            raise sources.SourceError("That key is not right.")

        real = sources._post
        sources._post = fake
        try:
            d = sources.load_live({"orders": {"url": "u", "key": "k"}, "books": {"url": "u", "key": "k"}})
        finally:
            sources._post = real
        self.assertEqual(d.problems, ["Orders: That key is not right.", "Books: That key is not right."])


if __name__ == "__main__":
    unittest.main()

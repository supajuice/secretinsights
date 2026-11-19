"""Where the numbers come from.

Live: the order site's and the books' Apps Scripts, using their admin keys from
.streamlit/secrets.toml. Only read actions are ever sent:
  orders  {"action": "list"}                        the newest 500 orders
  books   {"action": "list"}, {"action": "report"}  entries, website sales, settings, a period report
Nothing here can change an order or a books entry.

Insights: what the GitHub Action reads for the online dashboard, with the READ-ONLY keys
(ORDERS_READ_KEY, BOOKS_READ_KEY). Both scripts answer {"action": "insights"} with numbers only:
no customer names, emails, phone numbers, addresses, notes or receipt links. Those keys can't
change anything or open anything else.

Snapshot: the online dashboard. A GitHub Action reads the live sources and saves data.json
next to app.py, with nothing private in it (see snapshot.py). The page only reads that file.

Demo: made-up sample data, used when there are no keys yet, so the dashboard can be tried.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

from . import demo

SNAPSHOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.json")

TIMEOUT = 90  # seconds per try; Apps Script can be slow to wake up
# Google's Apps Scripts now and then take over a minute to answer (a "cold start" after a quiet
# spell). When there's no answer at all, try again after these pauses (seconds). A script that
# answers, even with an error such as a wrong key, is never asked again.
RETRY_PAUSES = (10, 30)


class SourceError(Exception):
    """A source could not be read. The message is safe to show on screen."""


@dataclass
class Data:
    mode: str  # 'live', 'snapshot' or 'demo'
    orders: list = field(default_factory=list)  # from the order site's list action
    books: dict = field(default_factory=dict)  # from the books' list action
    problems: list = field(default_factory=list)  # what could not be read, for the sidebar
    generated: str = ""  # snapshot only: when it was made, Cape Town time


def _post(url: str, body: dict) -> dict:
    # JSON as text/plain, like the websites send it. Apps Script answers with a redirect to the
    # JSON, which requests follows as a GET. (Imported here: the online page never needs it.)
    import requests

    pauses = list(RETRY_PAUSES)
    while True:
        try:
            res = requests.post(url, data=json.dumps(body), headers={"Content-Type": "text/plain;charset=utf-8"}, timeout=TIMEOUT)
            break
        except (requests.Timeout, requests.ConnectionError) as err:
            if not pauses:
                tries = len(RETRY_PAUSES) + 1
                raise SourceError("Could not reach it after " + str(tries) + " tries (" + type(err).__name__ + ").") from err
            time.sleep(pauses.pop(0))
        except requests.RequestException as err:
            raise SourceError("Could not reach it (" + type(err).__name__ + ").") from err
    try:
        reply = res.json()
    except ValueError as err:
        raise SourceError("It did not answer with data (HTTP " + str(res.status_code) + "). Check the address.") from err
    if not isinstance(reply, dict) or reply.get("ok") is not True:
        message = reply.get("message") if isinstance(reply, dict) else None
        raise SourceError(message or "It said no.")
    return reply


def configured(secrets) -> bool:
    try:
        return bool(secrets["orders"]["url"] and secrets["orders"]["key"] and secrets["books"]["url"] and secrets["books"]["key"])
    except Exception:  # no secrets file, or a part missing
        return False


def load_live(secrets) -> Data:
    data = Data(mode="live")
    try:
        data.orders = _post(secrets["orders"]["url"], {"action": "list", "key": secrets["orders"]["key"]}).get("orders", [])
    except SourceError as err:
        data.problems.append("Orders: " + str(err))
    try:
        data.books = _post(secrets["books"]["url"], {"action": "list", "key": secrets["books"]["key"]})
    except SourceError as err:
        data.problems.append("Books: " + str(err))
    return data


def load_insights(orders_url: str, orders_key: str, books_url: str, books_key: str) -> Data:
    """The read-only numbers, for the online dashboard. Only the insights action is sent."""
    data = Data(mode="live")
    try:
        data.orders = _post(orders_url, {"action": "insights", "key": orders_key}).get("orders", [])
    except SourceError as err:
        data.problems.append("Orders: " + str(err))
    try:
        reply = _post(books_url, {"action": "insights", "key": books_key})
        data.books = {k: v for k, v in reply.items() if k != "ok"}
    except SourceError as err:
        data.problems.append("Books: " + str(err))
    return data


def load_report_live(secrets, start: str, end: str) -> dict:
    return _post(secrets["books"]["url"], {"action": "report", "key": secrets["books"]["key"], "from": start, "to": end}).get("report", {})


def load_demo() -> Data:
    return Data(mode="demo", orders=demo.orders(), books=demo.books())


def has_snapshot() -> bool:
    return os.path.exists(SNAPSHOT)


def load_snapshot(path: str | None = None) -> Data:
    with open(path or SNAPSHOT, encoding="utf-8") as f:
        snap = json.load(f)
    return Data(mode="snapshot", orders=snap.get("orders", []), books=snap.get("books", {}), generated=snap.get("generated", ""))

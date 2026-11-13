"""Build the online dashboard into _site/, ready for GitHub Pages.

    python scripts/build_site.py            # live: reads the orders and books with the keys below
    python scripts/build_site.py --demo     # the made-up sample data, for trying it on a laptop

The GitHub Action runs it every hour with these, from the repo's secrets and variables:
    ORDERS_READ_KEY, BOOKS_READ_KEY   the READ-ONLY keys (READ_KEY in each Apps Script, made with
                                      makeReadKey). They only open the insights action: numbers,
                                      no customer details, and they can't change anything.
    ORDERS_URL, BOOKS_URL             the web app addresses (default: the ones in secrets.toml.example)
The admin keys are never needed here.

What it writes:
    _site/index.html     loads Streamlit in the visitor's browser (stlite) and runs app.py
    _site/app.py, views/, sj/, data.json
data.json is the public snapshot (sj/snapshot.py): no keys, no customer names or contact details.
It stops with an error, and publishes nothing, if a source cannot be read or the snapshot
looks like it holds something private, so the last good dashboard stays up.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sj import snapshot, sources  # noqa: E402

OUT = os.path.join(ROOT, "_site")
STLITE = "1.12.0"  # @stlite/browser; bundles Streamlit 1.65 and runs Python in the browser (Pyodide)
DEFAULT_URLS = {
    "ORDERS_URL": "https://script.google.com/macros/s/AKfycbxEIuI6sClunrjlo5O8raoGk67ue7txtJgD6OrLrAxlg90Qa99-1DoyqDZJWmQbX1or/exec",
    "BOOKS_URL": "https://script.google.com/macros/s/AKfycbxCm5RUemZnUjcHdsTgroL8rXJbOHyc0vUWQ9SkBxGBw2fSwWMeqK7B9TnZkhyV86SEpA/exec",
}
APP_FILES = ["app.py", "sj/__init__.py", "sj/metrics.py", "sj/charts.py", "sj/sources.py", "sj/demo.py", "sj/snapshot.py",
             "views/overview.py", "views/sales.py", "views/customers.py", "views/money.py"]
CAPE_TOWN = timezone(timedelta(hours=2))


def fail(message: str) -> None:
    print("::error::" + message)
    sys.exit(1)


def private_bits(text: str, keys: list[str]) -> list[str]:
    """Things that must never be in the public snapshot."""
    found = []
    for k in keys:
        if k and k in text:
            found.append("an admin key")
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]", text):
        found.append("an email address")
    if "drive.google.com" in text or "docs.google.com" in text:
        found.append("a Google Drive link")
    for field in ('"email"', '"name"', '"contact"', '"address"', '"notes"', '"receipt":"http'):
        if field in text:
            found.append("the field " + field)
    return found


def index_html() -> str:
    files = ",\n        ".join('"%s": { url: "./%s" }' % (f, f) for f in APP_FILES + ["data.json"])
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <title>Supa Juice insights</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@%(v)s/build/stlite.css">
  <style>
    html, body { margin: 0; background: #faf9f5; color: #0e1a3d; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
    #loading { display: grid; place-items: center; min-height: 100vh; padding: 16px; text-align: center; }
    #loading p { max-width: 28rem; line-height: 1.5; }
    #loading strong { display: block; font-size: 1.4rem; margin-bottom: .4rem; }
  </style>
</head>
<body>
  <div id="root">
    <div id="loading"><p><strong>Supa Juice insights</strong>Loading the charts. The first visit takes about 20 seconds while your browser sets up; after that it's quicker.</p></div>
  </div>
  <script type="module">
    import { mount } from "https://cdn.jsdelivr.net/npm/@stlite/browser@%(v)s/build/stlite.js";
    mount({
      entrypoint: "app.py",
      requirements: ["pandas", "altair"],
      streamlitConfig: {
        "theme.base": "light",
        "theme.primaryColor": "#1340c8",
        "theme.backgroundColor": "#faf9f5",
        "theme.secondaryBackgroundColor": "#f2f0e8",
        "theme.textColor": "#0e1a3d",
        "client.toolbarMode": "viewer"
      },
      files: {
        %(files)s
      }
    }, document.getElementById("root"));
  </script>
</body>
</html>
""" % {"v": STLITE, "files": files}


def main() -> None:
    demo = "--demo" in sys.argv
    now = datetime.now(CAPE_TOWN)
    keys: list[str] = []
    if demo:
        data = sources.load_demo()
        today = data.books["today"]
    else:
        keys = [os.environ.get("ORDERS_READ_KEY", ""), os.environ.get("BOOKS_READ_KEY", "")]
        if not all(keys):
            fail("ORDERS_READ_KEY and BOOKS_READ_KEY are not set. Add them in the repo: Settings > Secrets and variables > Actions.")
        data = sources.load_insights(os.environ.get("ORDERS_URL") or DEFAULT_URLS["ORDERS_URL"], keys[0],
                                     os.environ.get("BOOKS_URL") or DEFAULT_URLS["BOOKS_URL"], keys[1])
        if data.problems:
            fail("Could not read everything, so nothing was published: " + "; ".join(data.problems))
        today = data.books.get("today") or now.date().isoformat()

    snap = snapshot.make(data.orders, data.books, now.strftime("%d %b %Y, %H:%M"), today)
    text = snapshot.dumps(snap)
    bad = private_bits(text, keys)
    if bad:
        fail("The snapshot would have had " + ", ".join(sorted(set(bad))) + " in it, so nothing was published.")

    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    for f in APP_FILES:
        os.makedirs(os.path.dirname(os.path.join(OUT, f)) or OUT, exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, f), os.path.join(OUT, f))
    with open(os.path.join(OUT, "data.json"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html())
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    print("Built _site/: %d orders, %d expenses, updated %s%s." % (
        len(snap["orders"]), len(snap["books"]["entries"]["expense"]), snap["generated"], " (sample data)" if demo else ""))


if __name__ == "__main__":
    main()

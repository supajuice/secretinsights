# Supa Juice insights

Charts for the business: sales, flavours, customers, costs, profit, cash and owners, in one place. A [Streamlit](https://streamlit.io) app.

There are two versions of the same app:
- **Online**, at https://supajuice.co.za/secretinsights/: public, anyone with the link. Refreshed every hour by a GitHub Action. No customer names or contact details.
- **On your laptop**: the full version, read live, including best customers.

## How the online version keeps the keys private

```
Repo secrets ORDERS_READ_KEY, BOOKS_READ_KEY  (read-only keys; only the Action can use them)
        |
GitHub Action, every hour  -- "insights" -->  order + books Apps Scripts
        |                                      (they answer with numbers only)
        |  data.json: no keys, names, emails, phone numbers, addresses,
        |  order notes or receipt links. Customers are C1, C2, ...
        v
GitHub Pages  -->  index.html runs the same Streamlit app in the visitor's browser (stlite)
```

- **Read-only keys.** The order and books scripts each have a `READ_KEY`, separate from their admin key. It opens one thing only, the `insights` action, which returns the numbers without any customer details. It can't change an order, a setting or a books entry, and it can't open Greg's admin page or the books page. The admin keys never leave Google and your laptop.
- The page never talks to Google, so there is nothing on it that could reach the Sheets.
- `scripts/build_site.py` checks the snapshot before publishing: if it finds a key, an email address, a Drive link or a private field, it stops and publishes nothing. If a source can't be read, it also stops, and the last good dashboard stays up. GitHub emails a failure notice.
- The first visit takes about 20-30 seconds while the browser loads Python; after that it's quicker.

## Setting up the online version (once)

**Greg, in Google (signed in with the shop account), for the order script and then the books script:**
1. Open the Sheet > **Extensions > Apps Script**. Replace all of `Code.gs` with the new one from GitHub (`supajuice/supajuice.github.io` > `apps-script/Code.gs`, then `supajuice/books` > `apps-script/Code.gs`) and **Save**.
2. **Deploy > Manage deployments >** pencil **> Version: New version > Deploy**. (Not *New deployment*: the address must stay the same.)
3. In the drop-down above the code choose **makeReadKey**, then **Run**. The log shows `Read-only key (for the insights dashboard): ...`. Copy that key. No need to run setup again.

**Greg, in GitHub (signed in with the account that manages supajuice):**
1. **+** (top right) > **New repository**. Owner `supajuice`, name `secretinsights`, **Public**, tick nothing else. **Create repository**.
2. **Settings > Collaborators > Add people**: add Vishwesh with **Write**.
3. **Settings > Secrets and variables > Actions > New repository secret**, twice:
   - Name `ORDERS_READ_KEY`, secret: the read-only key from the **order** script.
   - Name `BOOKS_READ_KEY`, secret: the read-only key from the **books** script.
   Once saved, nobody can read them back, not even Greg. To change one, add it again with the same name.
4. **Settings > Pages > Build and deployment > Source: GitHub Actions**.

**Then:** the code is pushed to `main`. The Action runs straight away (the **Actions** tab shows it) and the dashboard appears at https://supajuice.co.za/secretinsights/ a minute or two later.

**To refresh now:** **Actions > Publish the dashboard > Run workflow**.

**If a read-only key ever leaks:** run **rotateReadKey** in that script (it logs a new one) and put the new key in the GitHub secret. The old one stops working at once. Even a leaked read key only shows what the public dashboard already shows.

If the order or books web app address ever changes, add it under **Settings > Secrets and variables > Actions > Variables** as `ORDERS_URL` or `BOOKS_URL`.

GitHub pauses hourly runs in a repo with no new commits for 60 days. The Action makes an empty "keep the hourly refresh switched on" commit when the repo has been quiet for 30 days, so that never happens.

## The laptop version

```
Order site's Apps Script  --list-->                                                           Supa Juice insights on your laptop
Books' Apps Script        --list, report-->   /
```

- **Read only.** It only ever asks for `list` (and the books' `report`). It cannot change an order, a setting or a books entry. A test checks this.
- It uses the **admin keys**, from `.streamlit/secrets.toml` on your laptop, because it shows best customers by name. They never go to GitHub.
- **Its own folder**, separate from the order site, the books and the feedback. Changing it never affects them.

## The pages

| Page | What it shows |
|---|---|
| **Overview** | Website sales, orders, sachets, average order, profit, cash on hand, margin per sachet, and the tax year against the R 1 million limit. Sales by day, week or month. Income and costs by month |
| **Sales** | Flavours, where orders are now (status), collected or sent, which day people order, order sizes, discount codes |
| **Customers** | Customers so far, how many came back, new and returning by month, best customers |
| **Money** | Income, costs, profit, expenses without a receipt, where the money went, cash in the account over time, expenses by month, per-sachet numbers, stock by flavour, owners, tax year |

Pick the period in the sidebar: this month, last month, last 30 days, last 3 months, this tax year (1 March to the end of February), all time, or your own dates. The arrows on the tiles compare with the same length of time just before. Every chart has **See the numbers** underneath.

The money figures (profit, cash, owners, margin) come from the books' own report, so they match the books page exactly. Sales are counted the books' way: paid and delivered orders, on the day they were paid.

## Trying the online version on your laptop

```
python scripts/build_site.py --demo
python -m http.server 8502 --directory _site
```

Then open http://127.0.0.1:8502/. It's built from the sample data; `_site/` is never committed.

## Running it on your laptop

You need Python 3.11 or newer.

```
pip install -r requirements.txt
streamlit run app.py
```

It opens at **http://localhost:8501**. Without keys it shows **made-up sample data** (the sidebar says so), so you can look around first.

## Connecting it to the real numbers

1. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, in the same folder.
2. The two web app addresses are already filled in. Add the two keys:
   - `[orders] key`: the order site's admin key (the part after `#` in Greg's admin page link, or **ADMIN_KEY** in the order Apps Script's *Project Settings > Script Properties*);
   - `[books] key`: the books' admin key (the same, for the books).
3. Save, then press **Refresh the numbers** in the sidebar (or restart).

`secrets.toml` is in `.gitignore`, so the keys are never committed. Anyone with those keys can change orders and the books from the admin pages, so keep the file on your own laptop and don't send it to anyone.

The numbers are kept for 10 minutes. **Refresh the numbers** reads them again straight away.

## Limits

- The order site sends its newest **500** orders. Fine for now; when there are more, older months in "All time" will be short. (A bigger list would need a small change in the order site's `Code.gs`.)
- Stock by flavour is approximate: race-stall sales and samples aren't split by flavour.
- Reviews and suggestions aren't shown yet: the feedback script has no read action, on purpose.

## Tests

```
python -m unittest discover -s tests -t .
```

`tests/test_snapshot.py` plants a phone number, an address and notes in the data and checks none of them, nor any name, email or Drive link, gets into the snapshot; and that the online numbers match the private ones. `tests/test_metrics.py` checks the sums by hand (sales, statuses, weeks, customers, profit, cash, owners, tax year). `tests/test_app.py` opens every page for every period with the sample data, and checks that only read actions are ever sent.

## Files

| File | What it is |
|---|---|
| `app.py` | The sidebar (period, source, refresh) and the page list |
| `scripts/build_site.py` | Builds the online version into `_site/`: reads the sources, makes the snapshot, checks it, writes the page |
| `sj/snapshot.py` | The public snapshot: what is kept and what is left out |
| `.github/workflows/publish.yml` | The hourly Action |
| `views/` | The four pages |
| `sj/sources.py` | Reading the order site and the books (read actions only), or the sample data |
| `sj/metrics.py` | The sums, in plain pandas |
| `sj/charts.py` | The chart styles and colours (flavours are always their fruit colour) |
| `sj/demo.py` | The made-up sample data |
| `.streamlit/config.toml` | Supa Juice colours |
| `.streamlit/secrets.toml.example` | The template for the addresses and keys |

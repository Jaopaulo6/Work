# NCR Tracking System

A lightweight internal **Non-Conformance Report (NCR)** tracking system for an
electronics manufacturing floor (Tekmar / Watts Water). Operators flag defective
parts and get an NCR number + bin assignment; repair technicians look up the NCR,
review the operator's report, and record the repair outcome and root cause.

Runs on a single machine on the LAN — everyone accesses it via a browser, no
installs. Built with Flask + SQLite + vanilla JS (no frameworks).

---

## Features

- **Operator form** — large touch-friendly inputs, dropdowns seeded from IFS
  data, dynamic "add component" line items (up to 5), live search filter on the
  64-item NC-code list. Auto-generates a sequential NCR number.
- **Printable slip** — confirmation page prints as a clean half-page bin tag
  (`@media print`) with a large NCR number.
- **Repair form** — look up an NCR, see the operator's full read-only report,
  add technician initials, root cause (searchable 58-item list), pass/fail,
  disposition, and return-to-production step. Status flows
  `Open → In Repair → Closed`.
- **Dashboard** — last 50 NCRs with Status / Location / Date-range filters and a
  read-only detail view per NCR.
- **CSV export** — flattened one-row-per-line-item export for Power BI; also
  writes `export/ncr_export.csv` to disk for a scheduled pickup.

No authentication, no HTTPS — pilot phase, single trusted LAN only.

---

## Requirements

- Python 3.9+ (developed on 3.11)
- Flask (see `requirements.txt`)

## Setup & run

```bash
cd ncr_system
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python3 database.py                # create + seed ncr.db, print a verification report
python3 app.py                     # serve on http://0.0.0.0:5000
```

Then open `http://[machine-ip]:5000` from any browser on the LAN. The app also
calls `init_db()` on startup, so the database is created automatically on first
run if `database.py` wasn't run first.

### Useful commands

```bash
python3 database.py            # create/seed if missing, then print row-count report
python3 database.py --reset    # delete ncr.db and rebuild from scratch
```

---

## Routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Redirects to `/operator` |
| GET | `/operator` | Operator NCR entry form |
| POST | `/operator` | Insert NCR + line items, redirect to success |
| GET | `/success/<ncr_number>` | Confirmation + printable slip |
| GET | `/repair` | Repair lookup form |
| GET | `/repair/<ncr_number>` | Repair form pre-loaded with NCR data |
| POST | `/repair/<ncr_number>` | Submit repair record, close NCR |
| GET | `/dashboard` | NCR list with filters |
| GET | `/ncr/<ncr_number>` | Read-only NCR detail |
| GET | `/export/csv` | Download flattened CSV export |

---

## Project layout

```
ncr_system/
├── app.py            # Flask app + routes
├── database.py       # schema, IFS seed data, helper functions
├── ncr.db            # SQLite database (auto-created, not committed)
├── requirements.txt
├── templates/        # base, operator, success, repair, dashboard, detail
├── static/           # style.css (floor-friendly + print styles)
└── export/           # ncr_export.csv generated on demand (not committed)
```

---

## Configuration

`database.py` has a single constant for the starting NCR number:

```python
NCR_NUMBER_SEED = 212800  # First NCR number to issue on an empty DB
```

Change it to `(last NCR number issued in IFS) + 1` before first run if needed.
Once NCRs exist, the next number is derived from `MAX(ncr_number) + 1`.

---

## Power BI

The flattened export (`/export/csv` or the on-disk `export/ncr_export.csv`)
gives one row per NCR line item with all reference descriptions joined. Two
connection options:

- **Option A (simplest):** schedule a periodic hit of `/export/csv` (or a script
  calling `database.get_export_rows`) and point Power BI at the CSV.
- **Option B (live):** Power BI Desktop → Get Data → ODBC → SQLite ODBC driver
  against `ncr.db`. The same flattened query lives in `database.FLATTENED_QUERY`.

---

## Notes / not yet built

- **No `product` field** on the form yet — a `ref_product` reference table will
  be added once the IFS product list is available. The schema and form are
  structured to drop it in.
- `cal_err_code` is free text for now; it can become a reference table later.
- `shop_order` is stored as TEXT (alphanumeric).

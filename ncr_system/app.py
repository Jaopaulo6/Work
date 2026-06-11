"""
app.py — Flask entry point for the NCR tracking system.

Run locally:
    python app.py
Then open http://[machine-ip]:5000 from any browser on the LAN.

Routes implemented in Step 2:
    GET  /                     -> redirect to /operator
    GET  /operator             -> operator NCR entry form
    POST /operator             -> insert NCR + line items, redirect to success
    GET  /success/<ncr_number> -> confirmation + (later) printable slip
"""

from flask import (
    Flask, render_template, request, redirect, url_for, abort
)

import database as db

app = Flask(__name__)

# Build/seed the database on startup. Idempotent — safe every launch.
db.init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean(value):
    """Trim a form string; return None if empty so blanks store as NULL."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def _to_int(value):
    """Parse an optional integer form field; return None on blank/invalid."""
    value = _clean(value)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Operator routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("operator_form"))


@app.route("/operator", methods=["GET"])
def operator_form():
    conn = db.get_connection()
    try:
        return render_template(
            "operator.html",
            locations=db.get_locations(conn),
            sources=db.get_sources(conn),
            nc_codes=db.get_nc_codes(conn),
        )
    finally:
        conn.close()


@app.route("/operator", methods=["POST"])
def operator_submit():
    f = request.form

    header = {
        "date_created": _clean(f.get("date_created")),
        "shop_order": _clean(f.get("shop_order")),
        "qty_affected": _to_int(f.get("qty_affected")),
        "operator_init": (_clean(f.get("operator_init")) or "").upper()[:4] or None,
        "notes": _clean(f.get("notes")),
        "bin_number": _clean(f.get("bin_number")),
        "source_id": _to_int(f.get("source_id")),
        "location_code": _clean(f.get("location_code")),
    }

    # Line items arrive as parallel lists (one entry per row in the form).
    components = f.getlist("component_number")
    designators = f.getlist("designator")
    quantities = f.getlist("quantity")
    nc_codes = f.getlist("nc_code")
    cal_err_codes = f.getlist("cal_err_code")

    line_items = []
    for i in range(len(components)):
        row = {
            "component_number": _clean(components[i]) if i < len(components) else None,
            "designator": _clean(designators[i]) if i < len(designators) else None,
            "quantity": _to_int(quantities[i]) if i < len(quantities) else None,
            "nc_code": _clean(nc_codes[i]) if i < len(nc_codes) else None,
            "cal_err_code": _clean(cal_err_codes[i]) if i < len(cal_err_codes) else None,
        }
        # Skip fully blank rows so a stray empty row doesn't create noise.
        if any(v is not None for v in row.values()):
            line_items.append(row)

    ncr_number = db.create_ncr(header, line_items)
    return redirect(url_for("success", ncr_number=ncr_number))


@app.route("/success/<ncr_number>")
def success(ncr_number):
    conn = db.get_connection()
    try:
        ncr = db.get_ncr_by_number(conn, ncr_number)
        if ncr is None:
            abort(404)
        line_items = db.get_line_items(conn, ncr["ncr_id"])
        return render_template("success.html", ncr=ncr, line_items=line_items)
    finally:
        conn.close()


if __name__ == "__main__":
    # host=0.0.0.0 so other machines on the LAN can reach it.
    app.run(host="0.0.0.0", port=5000, debug=True)

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

import csv
import io
import os
from datetime import date

from flask import (
    Flask, render_template, request, redirect, url_for, abort, Response
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


# ---------------------------------------------------------------------------
# Repair tech routes
# ---------------------------------------------------------------------------

@app.route("/repair", methods=["GET"])
def repair_lookup():
    """Lookup form. If ?ncr_number=... is supplied (from the search box),
    redirect to the detail route; otherwise just show the search box."""
    ncr_number = _clean(request.args.get("ncr_number"))
    if ncr_number:
        return redirect(url_for("repair_detail", ncr_number=ncr_number))
    return render_template("repair.html", ncr=None)


@app.route("/repair/<ncr_number>", methods=["GET"])
def repair_detail(ncr_number):
    """Show the operator's read-only report plus the repair entry form.
    If a repair already exists, show it read-only instead of the form."""
    conn = db.get_connection()
    try:
        ncr = db.get_ncr_by_number(conn, ncr_number)
        if ncr is None:
            # Clear, non-crashing error on the lookup page.
            return render_template(
                "repair.html", ncr=None,
                error="No NCR found with number \"%s\". Check the number and try again." % ncr_number,
            ), 404

        line_items = db.get_line_items(conn, ncr["ncr_id"])
        existing = db.get_repair(conn, ncr["ncr_id"])
        root_causes = db.get_root_causes(conn)
        dispositions = db.get_dispositions(conn)
    finally:
        conn.close()

    # Opening an Open NCR moves it to 'In Repair'. Done after the read so the
    # summary reflects the state the tech is acting on.
    if existing is None and ncr["status"] == "Open":
        db.mark_in_repair(ncr["ncr_id"])
        ncr = dict(ncr)
        ncr["status"] = "In Repair"

    return render_template(
        "repair.html",
        ncr=ncr,
        line_items=line_items,
        existing=existing,
        root_causes=root_causes,
        dispositions=dispositions,
    )


@app.route("/repair/<ncr_number>", methods=["POST"])
def repair_submit(ncr_number):
    conn = db.get_connection()
    try:
        ncr = db.get_ncr_by_number(conn, ncr_number)
        if ncr is None:
            return render_template(
                "repair.html", ncr=None,
                error="No NCR found with number \"%s\"." % ncr_number,
            ), 404
        already = db.get_repair(conn, ncr["ncr_id"]) is not None
        ncr_id = ncr["ncr_id"]
    finally:
        conn.close()

    # Guard against a double submit (UNIQUE on ncr_repair.ncr_id).
    if already:
        return redirect(url_for("repair_detail", ncr_number=ncr_number))

    f = request.form
    passed_raw = _clean(f.get("repair_passed"))
    repair = {
        "date_updated": _clean(f.get("date_updated")),
        "technician_init": (_clean(f.get("technician_init")) or "").upper()[:4] or None,
        "root_cause_id": _to_int(f.get("root_cause_id")),
        "root_cause_notes": _clean(f.get("root_cause_notes")),
        "repair_passed": int(passed_raw) if passed_raw in ("0", "1") else None,
        "disposition_code": _clean(f.get("disposition_code")),
        "production_step": _clean(f.get("production_step")),
    }
    db.create_repair(ncr_id, repair)
    return redirect(url_for("repair_detail", ncr_number=ncr_number))


# ---------------------------------------------------------------------------
# Dashboard + detail + CSV export (Phase 2)
# ---------------------------------------------------------------------------

@app.route("/dashboard")
def dashboard():
    status = _clean(request.args.get("status"))
    location_code = _clean(request.args.get("location_code"))
    date_from = _clean(request.args.get("date_from"))
    date_to = _clean(request.args.get("date_to"))

    conn = db.get_connection()
    try:
        ncrs = db.get_dashboard_ncrs(
            conn, status=status, location_code=location_code,
            date_from=date_from, date_to=date_to,
        )
        locations = db.get_locations(conn)
    finally:
        conn.close()

    return render_template(
        "dashboard.html",
        ncrs=ncrs,
        locations=locations,
        statuses=["Open", "In Repair", "Closed"],
        # Echo filters back so the form stays populated.
        f_status=status, f_location=location_code,
        f_date_from=date_from, f_date_to=date_to,
    )


@app.route("/ncr/<ncr_number>")
def ncr_detail(ncr_number):
    """Read-only detail view for one NCR (operator report + repair record)."""
    conn = db.get_connection()
    try:
        ncr = db.get_ncr_by_number(conn, ncr_number)
        if ncr is None:
            abort(404)
        line_items = db.get_line_items(conn, ncr["ncr_id"])
        repair = db.get_repair(conn, ncr["ncr_id"])
        return render_template(
            "detail.html", ncr=ncr, line_items=line_items, repair=repair,
        )
    finally:
        conn.close()


@app.route("/export/csv")
def export_csv():
    """Stream the flattened NCR export as a CSV download. Also writes a copy to
    export/ncr_export.csv so a scheduled Power BI pickup can read it from disk."""
    conn = db.get_connection()
    try:
        rows = db.get_export_rows(conn)
    finally:
        conn.close()

    # Column order = the flattened query's select list.
    headers = [
        "ncr_number", "date_created", "shop_order", "qty_affected",
        "operator_init", "notes", "bin_number", "status",
        "location_description", "source_description",
        "component_number", "designator", "quantity", "nc_code", "nc_description",
        "cal_err_code", "repair_date", "technician_init",
        "root_cause_description", "root_cause_notes", "repair_passed",
        "disposition_description", "production_step",
    ]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row[h] for h in headers])
    csv_text = buf.getvalue()

    # Persist a copy to disk for Option A (timed pickup) in the brief.
    export_dir = os.path.join(db.BASE_DIR, "export")
    os.makedirs(export_dir, exist_ok=True)
    with open(os.path.join(export_dir, "ncr_export.csv"), "w", newline="") as fh:
        fh.write(csv_text)

    filename = "ncr_export_%s.csv" % date.today().isoformat()
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=%s" % filename},
    )


if __name__ == "__main__":
    # host=0.0.0.0 so other machines on the LAN can reach it.
    app.run(host="0.0.0.0", port=5000, debug=True)

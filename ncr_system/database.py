"""
database.py — SQLite setup, seed data, and helper functions for the NCR system.

Run this file directly to (re)build the database and verify it:
    python database.py            # create + seed if missing, then print a report
    python database.py --reset    # delete ncr.db first, then rebuild from scratch

All schema and seed data come from the Tekmar IFS exports in the project brief.
"""

import os
import sqlite3
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Folder this file lives in, so the DB path is stable no matter where Flask is
# launched from.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "ncr.db")

# First NCR number to issue on an empty database. Jay: change this to
# (last NCR number issued in IFS) + 1 if you ever rebuild the DB.
# Last IFS number was in the 212700s range; we start fresh at 212800.
NCR_NUMBER_SEED = 212800


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

def get_connection():
    """Return a SQLite connection with rows accessible by column name and
    foreign-key enforcement turned on (off by default in SQLite)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS ref_source (
    source_id           INTEGER PRIMARY KEY,
    source_description  TEXT NOT NULL,
    validity            TEXT DEFAULT 'Active'
);

CREATE TABLE IF NOT EXISTS ref_location (
    location_code        TEXT PRIMARY KEY,
    location_description TEXT NOT NULL,
    validity             TEXT DEFAULT 'Active'
);

CREATE TABLE IF NOT EXISTS ref_nc_code (
    nc_code         TEXT PRIMARY KEY,
    nc_description  TEXT NOT NULL,
    validity        TEXT DEFAULT 'Active'
);

CREATE TABLE IF NOT EXISTS ref_root_cause (
    root_cause_id          INTEGER PRIMARY KEY,
    root_cause_description TEXT NOT NULL,
    validity               TEXT DEFAULT 'Active'
);

CREATE TABLE IF NOT EXISTS ref_disposition (
    disposition_code        TEXT PRIMARY KEY,
    disposition_description TEXT NOT NULL,
    validity                TEXT DEFAULT 'Active'
);

CREATE TABLE IF NOT EXISTS ncr (
    ncr_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ncr_number      TEXT NOT NULL UNIQUE,
    date_created    DATE NOT NULL,
    shop_order      TEXT,
    qty_affected    INTEGER,
    operator_init   TEXT NOT NULL,
    notes           TEXT,
    bin_number      TEXT,
    source_id       INTEGER REFERENCES ref_source(source_id),
    location_code   TEXT REFERENCES ref_location(location_code),
    status          TEXT NOT NULL DEFAULT 'Open'
);

CREATE TABLE IF NOT EXISTS ncr_line_item (
    line_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ncr_id           INTEGER NOT NULL REFERENCES ncr(ncr_id),
    component_number TEXT,
    designator       TEXT,
    quantity         INTEGER,
    nc_code          TEXT REFERENCES ref_nc_code(nc_code),
    cal_err_code     TEXT
);

CREATE TABLE IF NOT EXISTS ncr_repair (
    repair_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ncr_id           INTEGER NOT NULL UNIQUE REFERENCES ncr(ncr_id),
    date_updated     DATE NOT NULL,
    technician_init  TEXT NOT NULL,
    root_cause_id    INTEGER REFERENCES ref_root_cause(root_cause_id),
    root_cause_notes TEXT,
    repair_passed    INTEGER,
    disposition_code TEXT REFERENCES ref_disposition(disposition_code),
    production_step  TEXT
);
"""


# ---------------------------------------------------------------------------
# Seed data (from IFS exports)
# ---------------------------------------------------------------------------

SEED_SOURCE = [
    (1000, "External Audit"),
    (1001, "Client Audit"),
    (1002, "Internal Audit"),
    (1003, "Customer Complaint"),
    (1004, "Non-conformance Report"),
    (1005, "Supplier Discrepancy"),
    (1006, "Supplier Deviation"),
    (1007, "Supplier Clarification"),
    (1008, "Tekmar"),
]

SEED_LOCATION = [
    ("A", "Receiving"),
    ("C", "Calibration"),
    ("C10", "Programming"),
    ("D", "Sealing & Coating"),
    ("E", "Enclosing"),
    ("ENG", "Engineering"),
    ("F", "Hi-Pot"),
    ("H", "Handstuffing"),
    ("H05", "Handstuffing Preparation"),
    ("HS1", "Ersa Selective Soldering"),
    ("HS2", "SEHO Selective Soldering"),
    ("I", "Shipping"),
    ("J", "H-Inspection"),
    ("M", "Mechanical Assembly"),
    ("N", "Repair"),
    ("P", "Packaging"),
    ("P05", "Packaging Preparation"),
    ("Q", "Finished Goods Warehouse"),
    ("R", "SMT"),
    ("R20", "PCB Cutting / Separation"),
    ("S", "Sensors"),
    ("T", "Component Storage"),
    ("U", "Customer"),
    ("X", "Unknown"),
]

SEED_NC_CODE = [
    ("RMA-SUP", "Part supplier caused failure"),
    ("RMA-MAN", "Manufacturing error cause failure"),
    ("RMA-SHI", "Shipping cause failure"),
    ("RMA-CUS", "Customer caused failure"),
    ("PROD-PE", "Workcell - Programming Error"),
    ("PROD-PI", "Workcell - Packaged Incorrectly"),
    ("PROD-MS", "Workcell - Missing / Ghosting Segments"),
    ("PROD-FH", "Workcell - Failed Hi-Pot"),
    ("PROD-EI", "Workcell - Enclosed Incorrectly"),
    ("PROD-CE", "Workcell - Calibration Error"),
    ("PROD-BB", "Product - Buttons Binding"),
    ("WS-WP", "Water Spider - Wrong Parts"),
    ("WS-PE", "Water Spider - Prep Error"),
    ("WS-MP", "Water Spider - Missing Parts"),
    ("WS-CE", "Water Spider - Count Error"),
    ("SOLDER-SM", "Solder - Missing"),
    ("SOLDER-ISJ", "Solder - Insufficient Joint"),
    ("SOLDER-IFT", "Solder - Insufficient Flow Through"),
    ("SOLDER-SB", "Solder - Bridge"),
    ("SOFT", "Software"),
    ("PART-TMB", "Part - TombStoned"),
    ("SOLDER-LNS", "Solder - Lead Not Soldered"),
    ("DOC-DNE", "Documentation - Does Not Exist"),
    ("DF", "Design Fault"),
    ("CUS-PA", "Customer - Physical Abuse"),
    ("CUS-NR", "Customer - Not Repairable"),
    ("CUS-NP", "Customer - Not Programmed"),
    ("CUS-NC", "Customer - Not Calibrated"),
    ("CUS-EV", "Customer - Excess Voltage"),
    ("COAT-WL", "Coating - Wrong Location"),
    ("COAT-MM", "Coating - Missing Masking"),
    ("COAT-MWL", "Coating - Masking Wrong Location"),
    ("COAT-I", "Coating - Incomplete"),
    ("PART-PNTP", "Part - Not Trimmed Properly"),
    ("PART-PNPC", "Part - Not Positioned Correctly"),
    ("PART-PNI", "Part - Not Installed"),
    ("PART-PLW", "Part - Location Wrong"),
    ("PART-PDF", "Part - Defective"),
    ("PART-DMG", "Part - Damaged"),
    ("PART-CON", "Part - Contaminated"),
    ("PART-COM", "Part - Component Issue"),
    ("CUS-NFF", "No Fault Found"),
    ("SENS-LF", "Lathe Fail"),
    ("SENS-EP", "Epoxy - Fail"),
    ("DOC-DWV", "Documentation - Wrong Version"),
    ("DOC-DNF", "Documentation - Not Followed"),
    ("DOC-DE", "Documentation - Error"),
    ("SHIP-WQS", "Shipping - Wrong Quantity Shipped"),
    ("SHIP-WPP", "Shipping - Wrong Product Picked"),
    ("SENS-OHM", "Sensor - Failed OHM Test"),
    ("REC-WSL", "Receiving - Wrong Storage Location"),
    ("REC-WQ", "Receiving - Wrong Quantity"),
    ("REC-WP", "Receiving - Wrong Part"),
    ("REC-PD", "Receiving - Part Damaged"),
    ("REC-PKD", "Receiving - Packaging Damaged"),
    ("REC-NPO", "Receiving - No PO Number"),
    ("REC-NPN", "Receiving - No Part Number"),
    ("PRO-PNF", "Process - Not Followed"),
    ("PRO-PNE", "Process - Does Not Exist"),
    ("PART-WPI", "Part - Wrong Part Installed"),
    ("PART-PS", "Part - Shortage"),
    ("PART-POOS", "Part - Out of Spec"),
    ("PART-POW", "Part - Orientation Wrong"),
    ("PART-EOR", "End of Roll"),
]

SEED_ROOT_CAUSE = [
    (1000, "DRM - Defective Raw Material"),
    (1001, "PNI - Part Not Installed"),
    (1002, "ITS - Incorrect Tool Selection"),
    (1003, "DET - Defective Equipment or Tool"),
    (1004, "DD - Direction Documents Issues"),
    (1005, "PNF - Procedures Not Followed"),
    (1006, "LT - Lack of Training"),
    (1007, "PHR - Poor Recognition of Hazard"),
    (1008, "HE - Human Error"),
    (1009, "ME - Machine Error"),
    (1010, "NFF - No Fault Found"),
    (1012, "CEV - Customer - Excess Voltage"),
    (1013, "CINF - Customer - Instructions Not Followed"),
    (1014, "COTH - Customer - Other"),
    (1015, "CA - Customer - Physical Abuse"),
    (1016, "CPD - Customer - Product Damaged"),
    (1017, "CESD - Customer - Power Surge / ESD / Lightning"),
    (1018, "CC - Customer - Contamination"),
    (1019, "CONT - Contamination"),
    (1020, "SE - Software Error"),
    (1021, "WPI - Wrong Part Installed"),
    (1022, "POW - Part Orientation Wrong"),
    (1023, "PLW - Part Location Wrong"),
    (1024, "PNPC - Part Not Positioned Correctly"),
    (1025, "HPD - Handstuffing Part Damage"),
    (1026, "SPD - SMT Part Damaged"),
    (1027, "PNTP - Part Not Trimmed Properly"),
    (1029, "LNS - Lead Not Soldered"),
    (1030, "ISJ - Inadequate Solder Joint"),
    (1031, "IFTL - Insufficient Flow Through on Leads"),
    (1032, "SB - Solder Bridge"),
    (1033, "BB - Buttons Binding"),
    (1034, "DPE - Dipping Error"),
    (1035, "EI - Enclosed Incorrectly"),
    (1036, "MS - Missing / Ghosting Segments"),
    (1037, "NFC - Not Fully Calibrated / Programmed"),
    (1038, "PI - Packaged Incorrectly"),
    (1039, "PM - Part Missing"),
    (1040, "CPD - Carrier - Part Damaged"),
    (1041, "CPKD - Carrier - Packaging Damaged"),
    (1042, "CWQ - Carrier - Wrong Quantity"),
    (1043, "NPN - No PO Number"),
    (1044, "NPO - No Part Number"),
    (1045, "POoS - Part Out of Spec"),
    (1046, "SPDA - Supplier Part Damaged"),
    (1047, "SPKD - Supplier Packaging Damaged"),
    (1048, "SWP - Supplier Wrong Part"),
    (1049, "SWQ - Supplier Wrong Quantity"),
    (1050, "NP - Not Programmed"),
    (1051, "PNFC - Program Not Functioning Correctly"),
    (1052, "CST - Calibration Stand Failure"),
    (1053, "PD - Part Damaged"),
    (1054, "DNF - Directions Not Followed"),
    (1055, "MPE - Machine Program Error"),
    (1056, "X - Unknown"),
    (1057, "CWA - Coating in Wrong Spot / Area"),
    (1058, "CM - Coating Missing"),
    (1059, "CLS - Component Lifespan"),
]

SEED_DISPOSITION = [
    ("1", "Use As Is"),
    ("2", "Diverted to Repair"),
    ("3", "Corrected"),
    ("4", "Reject / Scrap"),
    ("5", "Inventory Adjustment"),
    ("6", "Rework in House"),
    ("7", "Diverted to R&D"),
    ("MFGSTOP", "Manufacturing Stop"),
    ("SCRAP", "Scrapped"),
    ("REWORK", "Rework"),
]


def _seed_reference_tables(conn):
    """Insert reference data. Uses INSERT OR IGNORE so re-running is safe and
    never duplicates or overwrites existing rows."""
    conn.executemany(
        "INSERT OR IGNORE INTO ref_source (source_id, source_description) VALUES (?, ?)",
        SEED_SOURCE,
    )
    conn.executemany(
        "INSERT OR IGNORE INTO ref_location (location_code, location_description) VALUES (?, ?)",
        SEED_LOCATION,
    )
    conn.executemany(
        "INSERT OR IGNORE INTO ref_nc_code (nc_code, nc_description) VALUES (?, ?)",
        SEED_NC_CODE,
    )
    conn.executemany(
        "INSERT OR IGNORE INTO ref_root_cause (root_cause_id, root_cause_description) VALUES (?, ?)",
        SEED_ROOT_CAUSE,
    )
    conn.executemany(
        "INSERT OR IGNORE INTO ref_disposition (disposition_code, disposition_description) VALUES (?, ?)",
        SEED_DISPOSITION,
    )


def init_db():
    """Create the schema (if absent) and seed reference tables. Idempotent:
    safe to call on every app startup."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        _seed_reference_tables(conn)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# NCR number generation
# ---------------------------------------------------------------------------

def get_next_ncr_number(conn):
    """Return the next sequential NCR number as a string.

    Uses MAX over the existing numbers (cast to INTEGER for correct numeric
    ordering); on an empty table, falls back to NCR_NUMBER_SEED.
    """
    row = conn.execute(
        "SELECT MAX(CAST(ncr_number AS INTEGER)) AS max_num FROM ncr"
    ).fetchone()
    if row is None or row["max_num"] is None:
        return str(NCR_NUMBER_SEED)
    return str(row["max_num"] + 1)


# ---------------------------------------------------------------------------
# Reference-data getters (for populating dropdowns)
# ---------------------------------------------------------------------------

def get_locations(conn):
    """Active locations ordered by code, for the Location dropdown."""
    return conn.execute(
        "SELECT location_code, location_description FROM ref_location "
        "WHERE validity = 'Active' ORDER BY location_code"
    ).fetchall()


def get_sources(conn):
    """Active sources ordered by id, for the Source dropdown."""
    return conn.execute(
        "SELECT source_id, source_description FROM ref_source "
        "WHERE validity = 'Active' ORDER BY source_id"
    ).fetchall()


def get_nc_codes(conn):
    """Active NC codes ordered by code, for the (searchable) NC Code dropdown."""
    return conn.execute(
        "SELECT nc_code, nc_description FROM ref_nc_code "
        "WHERE validity = 'Active' ORDER BY nc_code"
    ).fetchall()


def get_root_causes(conn):
    """Active root causes ordered by id, for the (searchable) Root Cause dropdown."""
    return conn.execute(
        "SELECT root_cause_id, root_cause_description FROM ref_root_cause "
        "WHERE validity = 'Active' ORDER BY root_cause_id"
    ).fetchall()


def get_dispositions(conn):
    """Active dispositions ordered by code, for the Disposition dropdown."""
    return conn.execute(
        "SELECT disposition_code, disposition_description FROM ref_disposition "
        "WHERE validity = 'Active' ORDER BY disposition_code"
    ).fetchall()


# ---------------------------------------------------------------------------
# NCR creation
# ---------------------------------------------------------------------------

def create_ncr(header, line_items):
    """Insert one NCR header plus its line items inside a single transaction.

    header: dict with keys date_created, shop_order, qty_affected,
            operator_init, notes, bin_number, source_id, location_code.
    line_items: list of dicts with keys component_number, designator,
            quantity, nc_code, cal_err_code.

    Returns the generated ncr_number (str). Status defaults to 'Open'.
    """
    conn = get_connection()
    try:
        ncr_number = get_next_ncr_number(conn)
        cur = conn.execute(
            """
            INSERT INTO ncr (
                ncr_number, date_created, shop_order, qty_affected,
                operator_init, notes, bin_number, source_id, location_code, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Open')
            """,
            (
                ncr_number,
                header.get("date_created"),
                header.get("shop_order"),
                header.get("qty_affected"),
                header.get("operator_init"),
                header.get("notes"),
                header.get("bin_number"),
                header.get("source_id"),
                header.get("location_code"),
            ),
        )
        ncr_id = cur.lastrowid

        rows = [
            (
                ncr_id,
                li.get("component_number"),
                li.get("designator"),
                li.get("quantity"),
                li.get("nc_code"),
                li.get("cal_err_code"),
            )
            for li in line_items
        ]
        if rows:
            conn.executemany(
                """
                INSERT INTO ncr_line_item (
                    ncr_id, component_number, designator, quantity, nc_code, cal_err_code
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        conn.commit()
        return ncr_number
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_ncr_by_number(conn, ncr_number):
    """Return the NCR header (joined to location/source descriptions) for a
    given ncr_number, or None if not found."""
    return conn.execute(
        """
        SELECT n.*, l.location_description, s.source_description
        FROM ncr n
        LEFT JOIN ref_location l ON n.location_code = l.location_code
        LEFT JOIN ref_source s   ON n.source_id = s.source_id
        WHERE n.ncr_number = ?
        """,
        (ncr_number,),
    ).fetchone()


def get_repair(conn, ncr_id):
    """Return the repair record (joined to root-cause/disposition descriptions)
    for an NCR, or None if the tech hasn't filled it in yet."""
    return conn.execute(
        """
        SELECT r.*, rc.root_cause_description, d.disposition_description
        FROM ncr_repair r
        LEFT JOIN ref_root_cause rc ON r.root_cause_id = rc.root_cause_id
        LEFT JOIN ref_disposition d ON r.disposition_code = d.disposition_code
        WHERE r.ncr_id = ?
        """,
        (ncr_id,),
    ).fetchone()


def mark_in_repair(ncr_id):
    """Move an NCR from 'Open' to 'In Repair' when a tech opens it. Leaves
    'In Repair' and 'Closed' untouched so we never walk the status backwards."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE ncr SET status = 'In Repair' WHERE ncr_id = ? AND status = 'Open'",
            (ncr_id,),
        )
        conn.commit()
    finally:
        conn.close()


def create_repair(ncr_id, repair):
    """Insert the repair record and close out the NCR in one transaction.

    repair: dict with keys date_updated, technician_init, root_cause_id,
            root_cause_notes, repair_passed, disposition_code, production_step.

    Returns nothing. Raises sqlite3.IntegrityError if a repair already exists
    for this NCR (ncr_repair.ncr_id is UNIQUE) — callers should guard first.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO ncr_repair (
                ncr_id, date_updated, technician_init, root_cause_id,
                root_cause_notes, repair_passed, disposition_code, production_step
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ncr_id,
                repair.get("date_updated"),
                repair.get("technician_init"),
                repair.get("root_cause_id"),
                repair.get("root_cause_notes"),
                repair.get("repair_passed"),
                repair.get("disposition_code"),
                repair.get("production_step"),
            ),
        )
        conn.execute(
            "UPDATE ncr SET status = 'Closed' WHERE ncr_id = ?", (ncr_id,)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_line_items(conn, ncr_id):
    """Return all line items (joined to NC code description) for an NCR."""
    return conn.execute(
        """
        SELECT li.*, nc.nc_description
        FROM ncr_line_item li
        LEFT JOIN ref_nc_code nc ON li.nc_code = nc.nc_code
        WHERE li.ncr_id = ?
        ORDER BY li.line_id
        """,
        (ncr_id,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Dashboard + export (Phase 2)
# ---------------------------------------------------------------------------

# Flattened one-row-per-line-item view used both for the CSV export and as the
# canonical Power BI query (matches the brief exactly).
FLATTENED_QUERY = """
SELECT
    n.ncr_number,
    n.date_created,
    n.shop_order,
    n.qty_affected,
    n.operator_init,
    n.notes,
    n.bin_number,
    n.status,
    l.location_description,
    s.source_description,
    li.component_number,
    li.designator,
    li.quantity,
    li.nc_code,
    nc.nc_description,
    li.cal_err_code,
    r.date_updated         AS repair_date,
    r.technician_init,
    rc.root_cause_description,
    r.root_cause_notes,
    r.repair_passed,
    d.disposition_description,
    r.production_step
FROM ncr n
LEFT JOIN ref_location l    ON n.location_code = l.location_code
LEFT JOIN ref_source s      ON n.source_id = s.source_id
LEFT JOIN ncr_line_item li  ON n.ncr_id = li.ncr_id
LEFT JOIN ref_nc_code nc    ON li.nc_code = nc.nc_code
LEFT JOIN ncr_repair r      ON n.ncr_id = r.ncr_id
LEFT JOIN ref_root_cause rc ON r.root_cause_id = rc.root_cause_id
LEFT JOIN ref_disposition d ON r.disposition_code = d.disposition_code
ORDER BY n.date_created DESC, n.ncr_number DESC
"""


def get_export_rows(conn):
    """Return all rows of the flattened view (one row per line item) for CSV
    export / Power BI."""
    return conn.execute(FLATTENED_QUERY).fetchall()


def get_dashboard_ncrs(conn, status=None, location_code=None,
                       date_from=None, date_to=None, limit=50):
    """Return up to `limit` NCR headers (most recent first) matching the
    optional filters, with line-item and component counts per NCR."""
    where = []
    params = []
    if status:
        where.append("n.status = ?")
        params.append(status)
    if location_code:
        where.append("n.location_code = ?")
        params.append(location_code)
    if date_from:
        where.append("n.date_created >= ?")
        params.append(date_from)
    if date_to:
        where.append("n.date_created <= ?")
        params.append(date_to)

    sql = """
        SELECT n.ncr_number, n.date_created, n.shop_order, n.qty_affected,
               n.operator_init, n.bin_number, n.status,
               l.location_description,
               (SELECT COUNT(*) FROM ncr_line_item li WHERE li.ncr_id = n.ncr_id) AS line_count
        FROM ncr n
        LEFT JOIN ref_location l ON n.location_code = l.location_code
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY n.date_created DESC, CAST(n.ncr_number AS INTEGER) DESC LIMIT ?"
    params.append(limit)
    return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------------------
# Run directly: build + verify
# ---------------------------------------------------------------------------

def _report():
    """Print a verification report of table row counts and the next NCR number."""
    conn = get_connection()
    try:
        ref_tables = [
            ("ref_source", 9),
            ("ref_location", 24),
            ("ref_nc_code", 64),
            ("ref_root_cause", 58),  # brief prose says "52" but IFS list is 58 rows (IDs 1000-1059 skipping 1011, 1028)
            ("ref_disposition", 10),
        ]
        print(f"Database: {DB_PATH}\n")
        print("Reference table row counts (expected from IFS seed):")
        all_ok = True
        for name, expected in ref_tables:
            count = conn.execute(f"SELECT COUNT(*) AS c FROM {name}").fetchone()["c"]
            ok = "OK" if count == expected else f"MISMATCH (expected {expected})"
            if count != expected:
                all_ok = False
            print(f"  {name:<18} {count:>4}  {ok}")

        print("\nData table row counts:")
        for name in ("ncr", "ncr_line_item", "ncr_repair"):
            count = conn.execute(f"SELECT COUNT(*) AS c FROM {name}").fetchone()["c"]
            print(f"  {name:<18} {count:>4}")

        print(f"\nNext NCR number to issue: {get_next_ncr_number(conn)}")

        # Spot-check a couple of rows so we can see real data, not just counts.
        print("\nSample ref_location rows:")
        for r in conn.execute(
            "SELECT location_code, location_description FROM ref_location ORDER BY location_code LIMIT 3"
        ):
            print(f"  {r['location_code']:<5} {r['location_description']}")

        print("\nSample ref_nc_code rows (filter 'SOLDER'):")
        for r in conn.execute(
            "SELECT nc_code, nc_description FROM ref_nc_code WHERE nc_code LIKE 'SOLDER%' ORDER BY nc_code"
        ):
            print(f"  {r['nc_code']:<12} {r['nc_description']}")

        print("\n" + ("All reference tables seeded correctly." if all_ok
                       else "WARNING: one or more reference tables did not match expected counts."))
    finally:
        conn.close()


if __name__ == "__main__":
    if "--reset" in sys.argv and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing {DB_PATH}\n")
    init_db()
    _report()

"""Study 14 held-out layouts C1 and C2 (machine / system exports).

  C1  a SQL dump: a commented CREATE TABLE followed by INSERT statements, one tuple per
      record (single-row INSERTs or batched multi-row VALUES, chosen per document). Dates are
      INTEGER epoch days (days since 1970-01-01), money is integer US cents, loads are
      decanewtons (1 kN = 100 daN), NULL means not recorded; non-key column order varies.
  C2  a pivoted cross-tab (TSV): one COLUMN per record and one ROW per attribute, records
      headed "rec.NN" with the entity id on the first attribute row. Dates are ISO 8601 week
      dates (YYYY-Www-D), money in US dollars, loads in kN, "~" means not recorded.

Interface: fn(doc, columns, rows, key, rng) -> (extension_without_dot, text).
Standard library only. Run `python3 layouts.py --selftest`.
"""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

EPOCH = date(1970, 1, 1)


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _dec(v) -> Decimal:
    return Decimal(str(v))


def _plain(d: Decimal) -> str:
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _date(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v))


# =============================================================== C1: SQL INSERT dump
C1_TABLES = {
    "hr_roster": ("staff_master", "Staff master list"),
    "work_authorizations": ("eligibility_doc", "Employment eligibility documents held"),
    "ead_cards": ("ead_card", "EAD card register"),
    "reverifications": ("i9_redo", "I-9 re-check events"),
    "lca_notices": ("lca_board_notice", "Worksite LCA notice postings"),
    "lca_filings": ("lca_lodgement", "LCA submissions"),
    "dol_receipts": ("agency_ack", "Department of Labor acknowledgements"),
    "requisitions": ("purchase_request", "Purchase request queue"),
    "purchase_orders": ("order_commitment", "Committed orders"),
    "invoices": ("supplier_bill", "Supplier bills"),
    "receipts": ("goods_in_note", "Goods-in notes"),
    "warehouse_scans": ("dock_scanner_event", "Dock scanner events"),
    "payments": ("remittance", "Remittance ledger"),
    "parts": ("component_master", "Component master"),
    "calibration_log": ("rig_calibration", "Test rig calibration history"),
    "test_reports": ("inhouse_break_test", "In-house break tests"),
    "lab_certificates": ("lab_cert", "External laboratory certificates"),
    "spec_sheets": ("design_spec", "Design specification extracts"),
}

# column -> (sql column name, comment)
C1_COLS = {
    "employee_id": ("wkr_code", "worker reference"),
    "po_id": ("ord_code", "order reference"),
    "part_id": ("cmp_code", "component reference"),
    "reverification_status": ("i9_redo_state", "state of the I-9 re-check"),
    "visa_end_date": ("immig_lapse_epd", "immigration status lapses (epoch day)"),
    "notice_status": ("lca_board_state", "state of the worksite LCA posting"),
    "planned_filing_date": ("lca_intended_lodge_epd", "intended LCA submission (epoch day)"),
    "document_type": ("eligibility_doc_kind", "kind of eligibility document"),
    "expires_on": ("eligibility_doc_lapse_epd", "eligibility document lapses (epoch day)"),
    "card_expiry": ("ead_lapse_epd", "EAD card lapses (epoch day)"),
    "completed_on": ("i9_redo_done_epd", "I-9 re-check carried out (epoch day)"),
    "posted_on": ("board_pinned_epd", "notice pinned up at worksite (epoch day)"),
    "removed_on": ("board_unpinned_epd", "notice taken off the board (epoch day)"),
    "filed_on": ("lca_lodge_epd", "LCA lodged with the agency (epoch day)"),
    "receipt_date": ("agency_stamp_epd", "agency acknowledgement stamped (epoch day)"),
    "status": ("req_state_cd", "state of the purchase request"),
    "requested_amount": ("ask_cents", "sum asked for, US cents"),
    "expected_delivery": ("eta_epd", "anticipated arrival (epoch day)"),
    "po_amount": ("commit_cents", "committed order value, US cents"),
    "invoice_amount": ("billed_cents", "supplier bill total, US cents"),
    "invoiced_qty": ("billed_unit_ct", "units on the supplier bill"),
    "due_on": ("pay_deadline_epd", "latest settle day on the bill (epoch day)"),
    "received_qty": ("dock_unit_ct", "units counted at goods-in"),
    "received_on": ("goods_in_epd", "goods booked in (epoch day)"),
    "scan_date": ("scanner_hit_epd", "dock scanner recorded the delivery (epoch day)"),
    "paid_on": ("funds_out_epd", "funds sent (epoch day)"),
    "qa_status": ("qa_verdict_cd", "quality disposition"),
    "target_load_kn": ("design_force_dan", "design target force, decanewtons"),
    "planned_test_date": ("rig_booking_epd", "booked test slot (epoch day)"),
    "calibrated_on": ("rig_cal_epd", "test rig calibrated (epoch day)"),
    "tested_on": ("inhouse_break_epd", "in-house break test run (epoch day)"),
    "measured_load_kn": ("inhouse_break_dan", "breaking force seen in-house, decanewtons"),
    "test_date": ("lab_break_epd", "laboratory ran the trial (epoch day)"),
    "certified_load_kn": ("lab_break_dan", "breaking force attested by the lab, decanewtons"),
    "min_load_kn": ("floor_force_dan", "required minimum breaking force, decanewtons"),
}


def _c1_type(kind, unit) -> str:
    if kind == "date":
        return "INTEGER"
    if kind == "amount":
        return "NUMERIC"
    return "TEXT"


def _c1_lit(kind, unit, v) -> str:
    if _blank(v):
        return "NULL"
    if kind == "date":
        return str((_date(v) - EPOCH).days)
    if kind == "amount":
        d = _dec(v)
        if unit == "USD":
            return _plain(d * 100)
        if unit == "kN":
            return _plain(d * 100)
        return _plain(d)
    return "'" + str(v).replace("'", "''") + "'"


def render_c1(doc, columns, rows, key, rng):
    table, title = C1_TABLES.get(doc, (doc + "_t", doc))
    key_col = columns[0]
    rest = list(columns[1:])
    rng.shuffle(rest)
    cols = [key_col] + rest
    names = ["row_seq"] + [C1_COLS[c][0] for c, *_ in cols]
    batch = rng.choice([0, 0, 4, 8])  # 0 = one INSERT per record, else multi-row VALUES batches
    out = [
        f"-- {title}",
        f"-- source dataset: {doc}; {len(rows)} record(s); one VALUES tuple per record, in row_seq order",
        "-- conventions:",
        "--   *_epd   INTEGER epoch day = whole days since 1970-01-01 (0 = 1970-01-01, 20454 = 2026-01-01)",
        "--   *_cents US money in cents (100 = $1.00)",
        "--   *_dan   force in decanewtons (100 daN = 1 kN)",
        "--   *_ct    unit counts",
        "--   NULL    = not recorded (never zero)",
        "--   the same reference may occur in several tuples; each tuple is a separate record",
        "BEGIN;",
        f"CREATE TABLE {table} (",
        "    row_seq INTEGER PRIMARY KEY,  -- position in the extract",
    ]
    defs = []
    for c, kind, unit, _lab in cols:
        n, cm = C1_COLS[c]
        null = " NOT NULL" if kind == "id" else ""
        defs.append((f"    {n} {_c1_type(kind, unit)}{null}", cm))
    for i, (d, cm) in enumerate(defs):
        sep = "," if i < len(defs) - 1 else ""
        out.append(f"{d}{sep}  -- {cm}")
    out.append(");")
    head = f"INSERT INTO {table} ({', '.join(names)}) VALUES"
    tuples = []
    for i, r in enumerate(rows, 1):
        vals = [str(i)] + ["'" + str(r[c]).replace("'", "''") + "'" if kind == "id"
                           else _c1_lit(kind, unit, r.get(c, ""))
                           for c, kind, unit, _ in cols]
        tuples.append("(" + ", ".join(vals) + ")")
    if not tuples:
        out.append(f"-- no records in this extract ({table} is empty)")
    elif batch == 0:
        for t in tuples:
            out.append(f"{head} {t};")
    else:
        for s in range(0, len(tuples), batch):
            chunk = tuples[s:s + batch]
            out.append(head)
            for j, t in enumerate(chunk):
                out.append(f"  {t}{';' if j == len(chunk) - 1 else ','}")
    out.append("COMMIT;")
    return "sql", "\n".join(out) + "\n"


# =============================================================== C2: pivoted cross-tab TSV
C2_TITLES = {
    "hr_roster": "staff master", "work_authorizations": "eligibility documents",
    "ead_cards": "EAD card register", "reverifications": "I-9 re-check events",
    "lca_notices": "worksite notice postings", "lca_filings": "LCA submissions",
    "dol_receipts": "agency acknowledgements", "requisitions": "purchase request queue",
    "purchase_orders": "committed orders", "invoices": "supplier bills",
    "receipts": "goods-in notes", "warehouse_scans": "dock scanner events",
    "payments": "remittance ledger", "parts": "component master",
    "calibration_log": "rig calibration history", "test_reports": "in-house break tests",
    "lab_certificates": "external lab certificates", "spec_sheets": "design spec extracts",
}

C2_ROWS = {
    "employee_id": "worker.key", "po_id": "order.key", "part_id": "component.key",
    "reverification_status": "i9.redo.state", "visa_end_date": "immigration.lapse.wk",
    "notice_status": "lca.board.state", "planned_filing_date": "lca.lodge.intended.wk",
    "document_type": "eligibility.doc.kind", "expires_on": "eligibility.doc.lapse.wk",
    "card_expiry": "ead.lapse.wk", "completed_on": "i9.redo.done.wk",
    "posted_on": "board.pinned.wk", "removed_on": "board.unpinned.wk",
    "filed_on": "lca.lodge.wk", "receipt_date": "agency.stamp.wk",
    "status": "request.phase", "requested_amount": "request.ask.usd",
    "expected_delivery": "request.eta.wk", "po_amount": "order.commit.usd",
    "invoice_amount": "bill.value.usd", "invoiced_qty": "bill.qty.units",
    "due_on": "bill.deadline.wk", "received_qty": "goodsin.units",
    "received_on": "goodsin.day.wk", "scan_date": "scanner.hit.wk",
    "paid_on": "funds.out.wk", "qa_status": "qa.verdict",
    "target_load_kn": "design.force.kn", "planned_test_date": "rig.booking.wk",
    "calibrated_on": "rig.cal.wk", "tested_on": "inhouse.break.wk",
    "measured_load_kn": "inhouse.break.kn", "test_date": "lab.break.wk",
    "certified_load_kn": "lab.break.kn", "min_load_kn": "floor.force.kn",
}
C2_NA = "~"


def _isoweek(d: date) -> str:
    y, w, wd = d.isocalendar()
    return f"{y}-W{w:02d}-{wd}"


def _c2_cell(kind, unit, v) -> str:
    if _blank(v):
        return C2_NA
    if kind == "date":
        return _isoweek(_date(v))
    if kind == "amount":
        return _plain(_dec(v))
    return str(v)


def render_c2(doc, columns, rows, key, rng):
    title = C2_TITLES.get(doc, doc)
    attrs = list(columns[1:])
    rng.shuffle(attrs)
    attrs = [columns[0]] + attrs
    run = rng.randrange(100000, 999999)
    out = [
        f"# cross-tab export {run}: {title} (dataset {doc})",
        "# orientation: each COLUMN after the first is one record (rec.NN, in extract order);",
        "#   each ROW is one attribute. A key may head several columns; every column is a separate record.",
        "# *.wk  = ISO 8601 week date YYYY-Www-D (ISO week-numbering year, week 01-53, D 1=Mon..7=Sun);",
        "#         e.g. 2026-W01-4 = Thursday 1 January 2026",
        "# *.usd = US dollars, plain decimal; *.kn = kilonewtons; *.units = unit count",
        f"# {C2_NA} = not recorded (never zero). Fields are TAB-separated.",
        f"# records: {len(rows)}",
    ]
    header = ["attribute"] + [f"rec.{i:02d}" for i in range(1, len(rows) + 1)]
    out.append("\t".join(header))
    for c, kind, unit, _lab in attrs:
        cells = [str(r[c]) if kind == "id" else _c2_cell(kind, unit, r.get(c, "")) for r in rows]
        out.append("\t".join([C2_ROWS[c]] + cells))
    if not rows:
        out.append("# (no record columns: this extract holds no records)")
    return "tsv", "\n".join(out) + "\n"


LAYOUTS = {"C1": render_c1, "C2": render_c2}


# =============================================================== readers (self-test only)
def _read_c1(txt: str, columns: list) -> list:
    """Return list of dicts {canonical_column: canonical string ('' if NULL)} in row_seq order."""
    import re
    back = {C1_COLS[c][0]: (c, k, u) for c, k, u, _ in columns}
    recs = []
    names = None
    for line in txt.splitlines():
        m = re.match(r"INSERT INTO \w+ \(([^)]*)\) VALUES(.*)$", line)
        if m:
            names = [x.strip() for x in m.group(1).split(",")]
            rest = m.group(2).strip()
            if not rest:
                continue
            line = rest
        s = line.strip()
        if names and s.startswith("("):
            body = s.rstrip(";,")
            assert body.startswith("(") and body.endswith(")")
            vals = re.findall(r"'(?:[^']|'')*'|[^,\s][^,]*", body[1:-1])
            vals = [v.strip() for v in vals]
            assert len(vals) == len(names), (vals, names)
            rec = {}
            for n, v in zip(names, vals):
                if n == "row_seq":
                    rec["_seq"] = int(v)
                    continue
                c, kind, unit = back[n]
                if v == "NULL":
                    rec[c] = ""
                elif v.startswith("'"):
                    rec[c] = v[1:-1].replace("''", "'")
                elif kind == "date":
                    rec[c] = date.fromordinal(EPOCH.toordinal() + int(v)).isoformat()
                elif unit in ("USD", "kN"):
                    rec[c] = Decimal(v) / 100
                else:
                    rec[c] = Decimal(v)
            recs.append(rec)
    return recs


def _read_c2(txt: str, columns: list) -> list:
    back = {C2_ROWS[c]: (c, k, u) for c, k, u, _ in columns}
    lines = [ln for ln in txt.splitlines() if ln and not ln.startswith("#")]
    header = lines[0].split("\t")
    n = len(header) - 1
    recs = [{"_col": header[i + 1]} for i in range(n)]
    for ln in lines[1:]:
        parts = ln.split("\t")
        c, kind, unit = back[parts[0]]
        assert len(parts) == n + 1
        for i, v in enumerate(parts[1:]):
            if v == C2_NA:
                recs[i][c] = ""
            elif kind == "date":
                y, w, d = v.split("-")
                recs[i][c] = date.fromisocalendar(int(y), int(w[1:]), int(d)).isoformat()
            elif kind == "amount":
                recs[i][c] = Decimal(v)
            else:
                recs[i][c] = v
    return recs


READERS = {"C1": _read_c1, "C2": _read_c2}


# =============================================================== self-test
def _selftest() -> int:
    import sys
    sys.path.insert(0, "/Users/roydi/Desktop/nofalsegreen")
    from nofalsegreen import study13 as s13
    from nofalsegreen import study13_heldout as h

    fails = []

    def chk(cond, msg):
        if not cond:
            fails.append(msg)

    # field names must differ from canonical names, L2 headers, plain labels, L4 keys, L6 headers
    def norm(x):
        return x.lower().replace("_", " ").replace(".", " ").replace("-", " ").strip()
    for docs in s13.DOCS.values():
        for cols in docs.values():
            for c, _k, _u, lab in cols:
                bad = {norm(c), norm(lab), norm(s13.L2_HEADERS[c]), norm(h.L4_KEYS[c][1]),
                       norm(h.L6_COLS[c][0])}
                chk(norm(C1_COLS[c][0]) not in bad, f"C1 name {C1_COLS[c][0]} for {c}")
                chk(norm(C2_ROWS[c]) not in bad, f"C2 name {C2_ROWS[c]} for {c}")
    chk(len({v[0] for v in C1_COLS.values()}) == len(C1_COLS), "C1 names not unique")
    chk(len(set(C2_ROWS.values())) == len(C2_ROWS), "C2 names not unique")

    # empty documents render a valid file
    for name, fn in LAYOUTS.items():
        ext, txt = fn("payments", s13.DOCS["purchasing"]["payments"], [], "po_id", random.Random(1))
        chk(bool(txt.strip()) and READERS[name](txt, s13.DOCS["purchasing"]["payments"]) == [],
            f"{name} empty doc")

    samples = {}
    n_docs = n_rows = n_blank = n_vals = 0
    seeds = (1401, 1402, 1403, 1404)
    for wf in s13.WORKFLOWS:
        for seed in seeds:
            p = s13.make_packet(wf, seed)
            key = s13.KEY[wf]
            for doc, cols in s13.DOCS[wf].items():
                rows = p.tables[doc]
                n_docs += 1
                n_rows += len(rows)
                for name, fn in LAYOUTS.items():
                    rs = f"study14-render-{name}-{p.packet_id}-{doc}"
                    ext, txt = fn(doc, cols, rows, key, random.Random(rs))
                    chk(fn(doc, cols, rows, key, random.Random(rs)) == (ext, txt),
                        f"{name} nondeterministic {doc}")
                    tag = f"{name} {wf}-{seed} {doc}"
                    try:
                        recs = READERS[name](txt, cols)
                    except Exception as e:  # noqa: BLE001
                        chk(False, f"{tag}: reader error {e!r}")
                        continue
                    chk(len(recs) == len(rows), f"{tag}: {len(recs)} records != {len(rows)} rows")
                    if len(recs) != len(rows):
                        continue
                    for i, (r, rec) in enumerate(zip(rows, recs), 1):
                        if name == "C1":
                            chk(rec["_seq"] == i, f"{tag}: row_seq order")
                        else:
                            chk(rec["_col"] == f"rec.{i:02d}", f"{tag}: column order")
                        chk(rec.get(key) == str(r[key]), f"{tag}: id {r[key]} missing in its record")
                        for c, kind, unit, _lab in cols[1:]:
                            v = r.get(c, "")
                            got = rec.get(c, None)
                            if _blank(v):
                                n_blank += 1
                                chk(got == "", f"{tag}: blank {c} rendered as {got!r}")
                                continue
                            n_vals += 1
                            if kind == "date":
                                chk(got == _date(v).isoformat(), f"{tag}: {c} {got} != {v}")
                            elif kind == "amount":
                                chk(got == _dec(v), f"{tag}: {c} {got} != {v}")
                            else:
                                chk(got == str(v), f"{tag}: {c} {got!r} != {v!r}")
                    if seed == 1401 and doc in ("work_authorizations", "invoices", "lab_certificates"):
                        samples[(name, wf)] = (doc, txt)

    for name in LAYOUTS:
        for wf in s13.WORKFLOWS:
            doc, txt = samples[(name, wf)]
            lines = txt.splitlines()
            print(f"===== {name} / {wf} / {doc} (seed 1401), first 18 lines =====")
            for ln in lines[:18]:
                print(ln if len(ln) <= 160 else ln[:157] + "...")
            print()
    print(f"documents checked: {n_docs} per layout; rows: {n_rows}; blank cells: {n_blank}; "
          f"non-blank values round-tripped: {n_vals} per layout")
    if fails:
        print(f"SELFTEST FAILED: {len(fails)} problems")
        for f in fails[:40]:
            print("  -", f)
        return 1
    print("SELFTEST PASSED (ids in every record, record counts and order match, blanks never "
          "rendered as values, every date/amount/text recovered exactly, names distinct, deterministic)")
    return 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)

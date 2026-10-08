"""Study 13 held-out layouts L4-L6.

Three record layouts designed independently of the development layouts (L1 canonical CSV,
L2 renamed-header CSV, L3 long record/entity/field/value CSV):

  L4  a nested YAML-style system export: one list item per record, fields grouped into
      sections under paraphrased snake_case keys; money in integer cents, loads in
      kilonewtons under a unit-named key, dates in ISO or "Jun 19 2026" form per record.
  L5  a prose register: one numbered paragraph ("Entry N.") per record, written as a
      clerk's log line with varied phrasings; quantities in words, money in dollars or
      "USD x thousand", loads in kN or newtons, dates spelled with month names.
  L6  a fixed-width mainframe-style report: abbreviated column headers, a legend, money
      in USD thousands, loads in newtons, dates as DD-MON-YYYY, "--" for not recorded.

Contract (from the brief): each row is its own record, in order; a blank cell is never
rendered as a value; every non-blank value is exactly recoverable; entity ids verbatim;
deterministic given rng; empty documents still render.

Standard library only. Run `python3 study13_heldout.py --selftest`.
"""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

TITLES = {
    "hr_roster": "Staff master list",
    "work_authorizations": "Employment eligibility documents",
    "ead_cards": "EAD card register",
    "reverifications": "I-9 re-check log",
    "lca_notices": "Worksite posting log (LCA)",
    "lca_filings": "Labor condition application submissions",
    "dol_receipts": "Department of Labor acknowledgements",
    "requisitions": "Purchase request queue",
    "purchase_orders": "Committed orders",
    "invoices": "Supplier bills",
    "receipts": "Goods-in notes",
    "warehouse_scans": "Dock scanner events",
    "payments": "Remittance ledger",
    "parts": "Component master",
    "calibration_log": "Test rig calibration history",
    "test_reports": "In-house break test results",
    "lab_certificates": "External laboratory certificates",
    "spec_sheets": "Design specification extracts",
}

TEXT_PARAPHRASE = {
    "EAD": "Employment Authorization Document (EAD)",
    "Complete": "completed",
    "Posted": "posted at worksite",
    "Approved": "approved",
    "Pass": "passed",
}


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _dec(v) -> Decimal:
    d = Decimal(str(v))
    return d


def _plain(d: Decimal) -> str:
    """Exact plain-decimal string, no exponent, no trailing zeros after the point."""
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _commas(d: Decimal) -> str:
    s = _plain(d)
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    whole, _, frac = s.partition(".")
    whole = f"{int(whole):,}"
    return ("-" if neg else "") + whole + ("." + frac if frac else "")


def _usd(d: Decimal) -> str:
    s = _plain(d)
    if "." in s:
        whole, frac = s.split(".")
        if len(frac) == 1:
            frac += "0"
        return f"${int(whole):,}.{frac}" if len(frac) == 2 else f"${_commas(d)}"
    return f"${int(s):,}"


def _date(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
         "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _words(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else "-" + _ONES[n % 10])
    if n < 1000:
        rest = n % 100
        return _ONES[n // 100] + " hundred" + ("" if rest == 0 else " and " + _words(rest))
    for size, name in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= size:
            rest = n % size
            head = _words(n // size) + " " + name
            if rest == 0:
                return head
            return head + (" and " if rest < 100 else " ") + _words(rest)
    raise ValueError(n)


def _text(v) -> str:
    return TEXT_PARAPHRASE.get(str(v), str(v))


# =============================================================== L4: nested YAML export
# column -> (section, key). Amount handling is by unit.
L4_KEYS = {
    "employee_id": ("subject", "worker_ref"), "po_id": ("subject", "order_ref"),
    "part_id": ("subject", "component_ref"),
    "reverification_status": ("flags", "i9_recheck_state"),
    "visa_end_date": ("timeline", "status_valid_through"),
    "notice_status": ("flags", "posting_state"),
    "planned_filing_date": ("timeline", "lca_submission_target"),
    "document_type": ("credential", "kind"),
    "expires_on": ("credential", "valid_until"),
    "card_expiry": ("credential", "card_void_after"),
    "completed_on": ("event", "recheck_done"),
    "posted_on": ("notice_window", "put_up"),
    "removed_on": ("notice_window", "taken_down"),
    "filed_on": ("submission", "lodged"),
    "receipt_date": ("submission", "acknowledged_by_agency"),
    "status": ("workflow", "request_state"),
    "requested_amount": ("money", "asked_for"),
    "expected_delivery": ("logistics", "eta"),
    "po_amount": ("money", "committed"),
    "invoice_amount": ("money", "billed"),
    "invoiced_qty": ("quantity", "billed_units"),
    "due_on": ("terms", "settle_by"),
    "received_qty": ("quantity", "counted_in"),
    "received_on": ("logistics", "arrived"),
    "scan_date": ("logistics", "dock_scan"),
    "paid_on": ("settlement", "remitted"),
    "qa_status": ("quality", "disposition"),
    "target_load_kn": ("load", "design_target"),
    "planned_test_date": ("schedule", "test_slot"),
    "calibrated_on": ("rig", "calibration_stamp"),
    "tested_on": ("trial", "run_date"),
    "measured_load_kn": ("load", "break_observed"),
    "test_date": ("certificate", "trial_performed"),
    "certified_load_kn": ("load", "break_attested"),
    "min_load_kn": ("load", "floor_required"),
}


def _l4_date(v, style: int) -> str:
    d = _date(v)
    if style == 0:
        return f'"{d.isoformat()}"'
    return f'"{MONTHS[d.month - 1][:3]} {d.day} {d.year}"'


def _l4_value(kind, unit, v, style) -> list:
    """Return either a scalar string, or a list of (subkey, scalar) for a nested mapping."""
    if kind == "date":
        return _l4_date(v, style)
    if kind == "amount":
        d = _dec(v)
        if unit == "USD":
            cents = d * 100
            if cents == cents.to_integral_value():
                return [("currency", "USD"), ("cents", _plain(cents))]
            return [("currency", "USD"), ("dollars", _plain(d))]
        if unit == "kN":
            return [("kilonewtons", _plain(d))]
        return _plain(d)
    return '"' + _text(v).replace('"', "'") + '"'


def render_l4(doc, columns, rows, key, rng):
    lines = [f"# {TITLES.get(doc, doc)}", "# exported by records service; absent keys = not captured",
             "export:", f"  dataset: {doc}", f"  entries: {len(rows)}"]
    if not rows:
        lines += ["  note: no records in this extract", "  records: []"]
        return "yaml", "\n".join(lines) + "\n"
    lines.append("  records:")
    for i, r in enumerate(rows, 1):
        style = rng.randrange(2)
        lines.append(f"    - entry_no: {i}")
        sections = {}
        order = []
        for c, kind, unit, _lab in columns:
            v = r.get(c, "")
            if _blank(v):
                continue
            sec, k = L4_KEYS[c]
            if sec not in sections:
                sections[sec] = []
                order.append(sec)
            if kind == "id":
                sections[sec].append((k, f'"{v}"'))
            else:
                sections[sec].append((k, _l4_value(kind, unit, v, style)))
        # subject first, other sections in a per-record shuffled order (key order is not meaningful)
        rest = [s for s in order if s != "subject"]
        rng.shuffle(rest)
        for sec in (["subject"] if "subject" in sections else []) + rest:
            lines.append(f"      {sec}:")
            for k, val in sections[sec]:
                if isinstance(val, list):
                    lines.append(f"        {k}:")
                    for sk, sv in val:
                        lines.append(f"          {sk}: {sv}")
                else:
                    lines.append(f"        {k}: {val}")
    return "yaml", "\n".join(lines) + "\n"


# =============================================================== L5: prose register
def _l5_date(v, rng) -> str:
    d = _date(v)
    m = MONTHS[d.month - 1]
    style = rng.randrange(4)
    if style == 0:
        return f"{d.day} {m} {d.year}"
    if style == 1:
        return f"{m} {d.day}, {d.year}"
    if style == 2:
        return f"the {_ordinal(d.day)} of {m} {d.year}"
    return f"{DAYS[d.weekday()]}, {d.day} {m} {d.year}"


def _l5_amount(unit, v, rng) -> str:
    d = _dec(v)
    if unit == "USD":
        opts = [_usd(d), f"{_commas(d)} US dollars"]
        k = d / 1000
        if k == k.to_integral_value() or len(_plain(k).split(".")[-1]) <= 3:
            opts.append(f"USD {_plain(k)} thousand")
        return rng.choice(opts)
    if unit == "kN":
        n = d * 1000
        return rng.choice([f"{_commas(d)} kN", f"{_commas(n)} newtons"])
    if unit == "units" and d == d.to_integral_value() and 0 <= d < 10 ** 9:
        return rng.choice([_words(int(d)), f"{_words(int(d))} ({_commas(d)})"])
    return _commas(d)


# column -> (present phrasings with {v}, phrase when not recorded)
L5_PHRASES = {
    "reverification_status": (["I-9 re-check marked {v}", "re-check state: {v}"],
                              "no re-check state noted"),
    "visa_end_date": (["immigration status good through {v}", "status ends {v}"],
                      "no status end noted"),
    "notice_status": (["posting state {v}", "the worksite notice is {v}"], "no posting state noted"),
    "planned_filing_date": (["LCA submission targeted for {v}", "aiming to lodge the LCA on {v}"],
                            "no target submission day noted"),
    "document_type": (["document held: {v}", "presented {v}"], "kind of document not recorded"),
    "expires_on": (["valid until {v}", "lapses after {v}"], "validity end not recorded"),
    "card_expiry": (["card good through {v}", "the card runs out on {v}"], "card end not recorded"),
    "completed_on": (["re-check done on {v}", "re-examined the documents on {v}"],
                     "re-check day not recorded"),
    "posted_on": (["notice put up on {v}", "notice went on the board {v}"],
                  "day the notice went up not recorded"),
    "removed_on": (["taken down on {v}", "came off the board {v}"],
                   "day the notice came down not recorded"),
    "filed_on": (["application lodged on {v}", "submitted to the agency on {v}"],
                 "lodging day not recorded"),
    "receipt_date": (["agency acknowledged on {v}", "acknowledgement stamped {v}"],
                     "acknowledgement day not recorded"),
    "status": (["request {v}", "request state {v}"], "request state not recorded"),
    "requested_amount": (["asked for {v}", "sought {v}"], "sum asked for not recorded"),
    "expected_delivery": (["due to arrive {v}", "ETA {v}"], "ETA not recorded"),
    "po_amount": (["committed for {v}", "order placed at {v}"], "committed sum not recorded"),
    "invoice_amount": (["supplier billed {v}", "bill total {v}"], "billed sum not recorded"),
    "invoiced_qty": (["billed for {v} units", "{v} units on the bill"], "billed unit count not recorded"),
    "due_on": (["settle by {v}", "to be paid no later than {v}"], "settle-by day not recorded"),
    "received_qty": (["{v} units counted in", "counted {v} units at goods-in"],
                     "count at goods-in not recorded"),
    "received_on": (["goods arrived {v}", "booked in on {v}"], "arrival day not recorded"),
    "scan_date": (["scanned at the dock on {v}", "dock scanner fired {v}"], "scan day not recorded"),
    "paid_on": (["remitted on {v}", "funds sent {v}"], "remittance day not recorded"),
    "qa_status": (["quality disposition {v}", "QA outcome {v}"], "quality disposition not recorded"),
    "target_load_kn": (["design target {v}", "designed to carry {v}"], "design target not recorded"),
    "planned_test_date": (["test slot booked for {v}", "scheduled for testing {v}"],
                          "test slot not recorded"),
    "calibrated_on": (["rig calibrated {v}", "rig last calibrated on {v}"],
                      "rig calibration day not recorded"),
    "tested_on": (["broken on the rig on {v}", "trial run {v}"], "trial day not recorded"),
    "measured_load_kn": (["failed at {v}", "breaking force observed {v}"],
                         "breaking force not recorded"),
    "test_date": (["the lab ran the trial on {v}", "lab trial performed {v}"],
                  "lab trial day not recorded"),
    "certified_load_kn": (["lab attests failure at {v}", "attested breaking force {v}"],
                          "attested breaking force not recorded"),
    "min_load_kn": (["must withstand at least {v}", "required floor {v}"],
                    "required floor not recorded"),
}

L5_SUBJECT = {"employee_id": ["Worker {k}", "Staff member {k}", "Employee ref {k}"],
              "po_id": ["Order {k}", "Order ref {k}", "{k}"],
              "part_id": ["Component {k}", "Item {k}", "Component ref {k}"]}


def render_l5(doc, columns, rows, key, rng):
    title = TITLES.get(doc, doc)
    out = [title.upper(), "Register kept as running notes, one numbered entry per record.", ""]
    if not rows:
        out.append("No records have been entered in this register.")
        return "txt", "\n".join(out) + "\n"
    for i, r in enumerate(rows, 1):
        subj = rng.choice(L5_SUBJECT[key]).format(k=r[key])
        parts = []
        for c, kind, unit, _lab in columns[1:]:
            v = r.get(c, "")
            present, absent = L5_PHRASES[c]
            if _blank(v):
                parts.append(absent)
                continue
            if kind == "date":
                s = _l5_date(v, rng)
            elif kind == "amount":
                s = _l5_amount(unit, v, rng)
            else:
                s = _text(v)
            parts.append(rng.choice(present).format(v=s))
        body = "; ".join(parts) if parts else "no details noted"
        out.append(f"Entry {i}. {subj}: {body}.")
        out.append("")
    return "txt", "\n".join(out)


# =============================================================== L6: fixed-width report
# column -> (header, legend text, value transform kind)
L6_COLS = {
    "employee_id": ("WORKER#", "worker reference"),
    "po_id": ("ORDER#", "order reference"),
    "part_id": ("COMPONENT#", "component reference"),
    "reverification_status": ("I9-RCHK", "state of the I-9 re-check"),
    "visa_end_date": ("STAT-THRU", "immigration status good through"),
    "notice_status": ("PST-STAT", "state of the worksite posting"),
    "planned_filing_date": ("LCA-TGT", "targeted LCA submission day"),
    "document_type": ("AUTH-DOC", "kind of eligibility document held"),
    "expires_on": ("AUTH-THRU", "eligibility document valid until"),
    "card_expiry": ("CARD-THRU", "EAD card good through"),
    "completed_on": ("RCHK-DONE", "day the I-9 re-check was done"),
    "posted_on": ("PUT-UP", "day the LCA notice went up"),
    "removed_on": ("TAKEN-DN", "day the LCA notice came down"),
    "filed_on": ("LCA-LODGED", "day the LCA was lodged"),
    "receipt_date": ("DOL-ACK", "day the Department of Labor acknowledged"),
    "status": ("REQ-ST", "state of the purchase request"),
    "requested_amount": ("ASK-USDK", "sum asked for, USD thousands"),
    "expected_delivery": ("ETA", "anticipated arrival"),
    "po_amount": ("CMT-USDK", "committed order value, USD thousands"),
    "invoice_amount": ("BILL-USDK", "supplier bill total, USD thousands"),
    "invoiced_qty": ("BILL-UNITS", "units on the supplier bill"),
    "due_on": ("PAY-BY", "settle-by day on the bill"),
    "received_qty": ("IN-UNITS", "units counted at goods-in"),
    "received_on": ("IN-DATE", "day the goods were booked in"),
    "scan_date": ("DOCK-SCAN", "day the dock scanner recorded the delivery"),
    "paid_on": ("REMITTED", "day the funds were sent"),
    "qa_status": ("QA-DISP", "quality disposition"),
    "target_load_kn": ("TGT-N", "design target force, newtons"),
    "planned_test_date": ("TEST-SLOT", "booked test slot"),
    "calibrated_on": ("RIG-CAL", "day the test rig was calibrated"),
    "tested_on": ("RUN-DATE", "day of the in-house break test"),
    "measured_load_kn": ("BREAK-N", "breaking force observed in-house, newtons"),
    "test_date": ("CERT-RUN", "day the laboratory ran the trial"),
    "certified_load_kn": ("CERT-BREAK-N", "breaking force attested by the laboratory, newtons"),
    "min_load_kn": ("FLOOR-N", "required minimum breaking force, newtons"),
}
L6_TEXT = {"EAD": "EAD", "Complete": "COMPLETED", "Posted": "POSTED", "Approved": "APPROVED", "Pass": "PASSED"}
MON3 = [m[:3].upper() for m in MONTHS]


def _l6_cell(kind, unit, v) -> str:
    if _blank(v):
        return "--"
    if kind == "date":
        d = _date(v)
        return f"{d.day:02d}-{MON3[d.month - 1]}-{d.year}"
    if kind == "amount":
        d = _dec(v)
        if unit == "USD":
            return _plain(d / 1000)
        if unit == "kN":
            return _plain(d * 1000)
        return _plain(d)
    if kind == "text":
        return L6_TEXT.get(str(v), str(v).upper())
    return str(v)


def render_l6(doc, columns, rows, key, rng):
    heads = [L6_COLS[c][0] for c, *_ in columns]
    cells = [[_l6_cell(k, u, r.get(c, "")) if k != "id" else str(r[c]) for c, k, u, _ in columns]
             for r in rows]
    widths = [max([len(h)] + [len(row[j]) for row in cells]) for j, h in enumerate(heads)]
    gap = " " * (2 + rng.randrange(2))
    run = rng.randrange(1000, 9999)
    num_cols = {j for j, (c, k, u, _) in enumerate(columns) if k == "amount"}

    def fmt(vals):
        return gap.join(v.rjust(widths[j]) if j in num_cols else v.ljust(widths[j])
                        for j, v in enumerate(vals)).rstrip()

    title = f"{TITLES.get(doc, doc).upper()}  ({doc})"
    out = [f"RPT-{run}   {title}", f"PAGE 1   RECORDS: {len(rows)}", ""]
    hdr = "SEQ   " + fmt(heads)
    out += [hdr, "-" * len(hdr)]
    if not rows:
        out.append("      *** NO RECORDS ON FILE ***")
    for i, row in enumerate(cells, 1):
        out.append(f"{i:04d}  " + fmt(row))
    out += ["-" * len(hdr), f"END OF REPORT - {len(rows)} RECORD(S)", "", "LEGEND"]
    for c, *_ in columns:
        h, txt = L6_COLS[c]
        out.append(f"  {h:<14}{txt}")
    out += ["  Dates are DD-MON-YYYY. USDK columns are in thousands of US dollars (185.5 = $185,500).",
            "  -N columns are in newtons (1 kN = 1,000 N). '--' means not recorded.",
            "  Each SEQ line is a separate record; a reference may appear on several lines."]
    return "txt", "\n".join(out) + "\n"


LAYOUTS = {"L4": render_l4, "L5": render_l5, "L6": render_l6}


# =============================================================== self-test
def _selftest() -> int:
    import re
    import sys
    from pathlib import Path
    sys.path.insert(0, "/Users/roydi/Desktop/nofalsegreen")
    from nofalsegreen import study13 as s13

    fails = []

    def chk(cond, msg):
        if not cond:
            fails.append(msg)

    # labels must differ from canonical names, L2 headers and plain labels
    forbidden = {}
    for docs in s13.DOCS.values():
        for cols in docs.values():
            for c, _k, _u, lab in cols:
                forbidden.setdefault(c, set()).update(
                    {c.lower(), lab.lower(), s13.L2_HEADERS[c].lower(),
                     c.replace("_", " ").lower()})
    for c, bad in forbidden.items():
        k4 = L4_KEYS[c][1]
        chk(k4.lower() not in bad and k4.replace("_", " ").lower() not in bad, f"L4 key {k4} for {c}")
        h6, leg = L6_COLS[c]
        chk(h6.lower() not in bad and leg.lower() not in bad, f"L6 header {h6} for {c}")
        if c in L5_PHRASES:
            for p in L5_PHRASES[c][0] + [L5_PHRASES[c][1]]:
                chk(not any(b == p.lower().replace("{v}", "").strip() for b in bad), f"L5 phrase {p}")

    # an empty document renders
    for name, fn in LAYOUTS.items():
        ext, txt = fn("payments", s13.DOCS["purchasing"]["payments"], [], "po_id", random.Random(1))
        chk(bool(txt.strip()) and "record" in txt.lower(), f"{name} empty doc")

    samples = {}
    n_docs = n_rows = n_blank = 0
    for wf in s13.WORKFLOWS:
        for seed in s13.SEEDS:
            p = s13.make_packet(wf, seed)
            for doc, cols in s13.DOCS[wf].items():
                rows = p.tables[doc]
                key = s13.KEY[wf]
                n_docs += 1
                n_rows += len(rows)
                for name, fn in LAYOUTS.items():
                    rng = random.Random(f"study13-render-{name}-{p.packet_id}-{doc}")
                    ext, txt = fn(doc, cols, rows, key, rng)
                    rng2 = random.Random(f"study13-render-{name}-{p.packet_id}-{doc}")
                    chk(fn(doc, cols, rows, key, rng2) == (ext, txt), f"{name} nondeterministic {doc}")
                    tag = f"{name} {wf}-{seed} {doc}"
                    # split into records by the layout's own marker
                    if name == "L4":
                        blocks = re.split(r"^    - entry_no: \d+\n", txt, flags=re.M)[1:]
                    elif name == "L5":
                        blocks = re.findall(r"^Entry \d+\. .*$", txt, flags=re.M)
                    else:
                        blocks = re.findall(r"^\d{4}  .*$", txt, flags=re.M)
                    chk(len(blocks) == len(rows), f"{tag}: {len(blocks)} records != {len(rows)} rows")
                    if len(blocks) != len(rows):
                        continue
                    for r, b in zip(rows, blocks):
                        chk(r[key] in b, f"{tag}: id {r[key]} missing in its record")
                        if name == "L6":
                            # alignment-independent: split on 2+ spaces
                            vals = re.split(r"\s{2,}", b.strip())[1:]
                            chk(len(vals) == len(cols), f"{tag}: cell count")
                        for j, (c, kind, unit, _lab) in enumerate(cols):
                            v = r.get(c, "")
                            if kind == "id":
                                continue
                            if _blank(v):
                                n_blank += 1
                                if name == "L4":
                                    chk(f" {L4_KEYS[c][1]}:" not in b, f"{tag}: blank {c} rendered")
                                elif name == "L5":
                                    chk(L5_PHRASES[c][1] in b, f"{tag}: blank {c} not stated as missing")
                                else:
                                    chk(vals[j] == "--", f"{tag}: blank {c} rendered as {vals[j]}")
                                continue
                            # exact recovery for L4 and L6; presence of the rendered form for L5
                            if name == "L6":
                                cell = vals[j]
                                if kind == "date":
                                    dd, mm, yy = cell.split("-")
                                    got = date(int(yy), MON3.index(mm) + 1, int(dd)).isoformat()
                                    chk(got == str(v), f"{tag}: {c} {cell} != {v}")
                                elif kind == "amount":
                                    f = {"USD": Decimal(1000), "kN": Decimal("0.001")}.get(unit, Decimal(1))
                                    chk(Decimal(cell) * f == _dec(v), f"{tag}: {c} {cell} != {v}")
                            elif name == "L4":
                                k4 = L4_KEYS[c][1]
                                m = re.search(rf"^ +{k4}:(.*)$", b, flags=re.M)
                                chk(m is not None, f"{tag}: {c} absent")
                                if m and kind == "date":
                                    s = m.group(1).strip().strip('"')
                                    if "-" in s:
                                        got = s
                                    else:
                                        mo, dd, yy = s.split()
                                        got = date(int(yy), [x[:3] for x in MONTHS].index(mo) + 1,
                                                   int(dd)).isoformat()
                                    chk(got == str(v), f"{tag}: {c} {s} != {v}")
                                elif m and kind == "amount":
                                    after = b[m.end():].split("\n")
                                    sub = dict(re.match(r" +(\w+): (\S+)", x).groups()
                                               for x in after[1:3] if re.match(r" {10}\w+: ", x))
                                    raw = m.group(1).strip()
                                    if raw:
                                        got = Decimal(raw)
                                    elif "cents" in sub:
                                        got = Decimal(sub["cents"]) / 100
                                    elif "dollars" in sub:
                                        got = Decimal(sub["dollars"])
                                    else:
                                        got = Decimal(sub["kilonewtons"])
                                    chk(got == _dec(v), f"{tag}: {c} {got} != {v}")
                            else:
                                if kind == "text":
                                    chk(_text(v) in b, f"{tag}: text {c} missing")
                                elif kind == "date":
                                    d = _date(v)
                                    chk(MONTHS[d.month - 1] in b and str(d.year) in b, f"{tag}: date {c}")
                    if seed == 1301 and doc in ("work_authorizations", "invoices", "lab_certificates"):
                        samples[(name, wf)] = (doc, txt)

    for name in LAYOUTS:
        for wf in s13.WORKFLOWS:
            doc, txt = samples[(name, wf)]
            print(f"===== {name} / {wf} / {doc} (seed 1301), first 15 lines =====")
            print("\n".join(txt.splitlines()[:15]))
            print()
    print(f"documents checked: {n_docs} per layout; rows: {n_rows}; blank cells: {n_blank}")
    if fails:
        print(f"SELFTEST FAILED: {len(fails)} problems")
        for f in fails[:40]:
            print("  -", f)
        return 1
    print("SELFTEST PASSED (ids present, record counts match, blanks never rendered as values, "
          "L4/L6 values recovered exactly, labels distinct, deterministic)")
    return 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)

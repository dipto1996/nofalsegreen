"""Study 14 held-out layouts A1 and A2 (direction: authentic public / standard record formats).

  A1  a government bulk-disclosure-style wide extract (modelled on the US DOL OFLC LCA
      disclosure file and similar agency bulk downloads): pipe-delimited, one row per
      record, UPPER_SNAKE column names, many irrelevant administrative columns (case
      numbers, employer/vendor names, FEINs, state codes, load dates), a "#" record-layout
      preamble that declares MM/DD/YYYY dates, and load values split into a value column
      plus a unit-of-measure column (KN or N) as the disclosure files do for wage + unit.
  A2  an ANSI X12-flavoured EDI interchange: ISA/GS/ST envelope, NTE companion-guide notes
      that declare every qualifier code, one LX loop per record with the entity id in a
      REF/LIN segment, dates in DTP*<code>*D8*CCYYMMDD, money in AMT (or TDS with implied
      two decimals for bill totals), counts in QTY, loads in MEA with KN or NT unit codes;
      blank values are simply absent segments; SE/GE/IEA trailers carry control counts.

Interface: fn(doc, columns, rows, key, rng) -> (extension_without_dot, text).
Standard library only. Run `python3 layouts.py --selftest`.
"""

from __future__ import annotations

import random
from datetime import date
from decimal import Decimal


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _dec(v) -> Decimal:
    return Decimal(str(v))


def _plain(d: Decimal) -> str:
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _money2(d: Decimal) -> str:
    """At least two decimals, more only if the value needs them (exact)."""
    s = _plain(d)
    whole, _, frac = s.partition(".")
    return f"{whole}.{frac.ljust(2, '0')}"


def _date(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def _clean(v, bad) -> str:
    s = str(v)
    for ch in bad:
        s = s.replace(ch, "/")
    return s


# ====================================================================== A1: disclosure extract
A1_TITLES = {
    "hr_roster": "WORKFORCE MASTER EXTRACT",
    "work_authorizations": "EMPLOYMENT ELIGIBILITY EVIDENCE DISCLOSURE",
    "ead_cards": "FORM I-766 CARD DISCLOSURE",
    "reverifications": "FORM I-9 SUPPLEMENT B DISCLOSURE",
    "lca_notices": "LCA PUBLIC ACCESS NOTICE DISCLOSURE",
    "lca_filings": "ETA-9035 SUBMISSION DISCLOSURE",
    "dol_receipts": "OFLC INTAKE ACKNOWLEDGEMENT DISCLOSURE",
    "requisitions": "PURCHASE REQUEST DISCLOSURE",
    "purchase_orders": "ORDER COMMITMENT DISCLOSURE",
    "invoices": "VENDOR BILLING DISCLOSURE",
    "receipts": "GOODS RECEIPT DISCLOSURE",
    "warehouse_scans": "INBOUND DOOR EVENT DISCLOSURE",
    "payments": "DISBURSEMENT DISCLOSURE",
    "parts": "COMPONENT CATALOG DISCLOSURE",
    "calibration_log": "LOAD FRAME CALIBRATION DISCLOSURE",
    "test_reports": "INTERNAL DESTRUCTIVE TEST DISCLOSURE",
    "lab_certificates": "ACCREDITED LABORATORY RESULT DISCLOSURE",
    "spec_sheets": "DESIGN REQUIREMENT DISCLOSURE",
}

# canonical column -> (A1 column name, layout description)
A1_COLS = {
    "employee_id": ("WORKER_FILE_NUMBER", "Employer-assigned worker file number"),
    "po_id": ("PURCHASE_DOCUMENT_KEY", "Purchasing document key"),
    "part_id": ("COMPONENT_CATALOG_KEY", "Catalog key of the component"),
    "reverification_status": ("I9_SUPPLEMENT_B_STANDING", "Standing of the Form I-9 Supplement B"),
    "visa_end_date": ("NONIMMIGRANT_STAY_END", "Last day of admitted nonimmigrant stay"),
    "notice_status": ("PUBLIC_ACCESS_NOTICE_FLAG", "Public access notice indicator"),
    "planned_filing_date": ("INTENDED_ETA9035_DATE", "Day the ETA-9035 is intended to be submitted"),
    "document_type": ("EMPLOYABILITY_EVIDENCE_TITLE", "Title of the employability evidence"),
    "expires_on": ("EMPLOYABILITY_EVIDENCE_LAPSE", "Day the employability evidence lapses"),
    "card_expiry": ("I766_VALID_TO", "Last valid day printed on the I-766 card"),
    "completed_on": ("SUPPLEMENT_B_EXECUTED", "Day Supplement B was executed"),
    "posted_on": ("NOTICE_DISPLAY_BEGIN", "First day the notice was displayed"),
    "removed_on": ("NOTICE_DISPLAY_END", "Day the notice display ended"),
    "filed_on": ("ETA9035_SUBMISSION_DAY", "Day the ETA-9035 was submitted"),
    "receipt_date": ("OFLC_INTAKE_DAY", "Day OFLC logged intake of the submission"),
    "status": ("REQ_ROUTING_OUTCOME", "Routing outcome of the purchase request"),
    "requested_amount": ("REQ_ESTIMATED_SPEND", "Estimated spend on the request, US dollars"),
    "expected_delivery": ("NEED_BY_DAY", "Need-by day for the goods"),
    "po_amount": ("ORDER_NET_VALUE", "Net value committed on the order, US dollars"),
    "invoice_amount": ("VENDOR_BILLED_TOTAL", "Gross total of the vendor bill, US dollars"),
    "invoiced_qty": ("BILLED_UNIT_COUNT", "Units charged on the vendor bill"),
    "due_on": ("NET_DUE_DAY", "Net due day under the payment terms"),
    "received_qty": ("GR_ACCEPTED_UNITS", "Units accepted at goods receipt"),
    "received_on": ("GR_POSTING_DAY", "Goods receipt posting day"),
    "scan_date": ("INBOUND_DOOR_EVENT_DAY", "Day of the handheld capture at the inbound door"),
    "paid_on": ("DISBURSEMENT_CLEARED_DAY", "Day the disbursement to the vendor cleared"),
    "qa_status": ("INSPECTION_RELEASE_DECISION", "Quality release decision"),
    "target_load_kn": ("DESIGN_ULTIMATE_FORCE", "Design ultimate force (unit in _UOM column)"),
    "planned_test_date": ("TEST_BOOKING_DAY", "Day a test is booked for"),
    "calibrated_on": ("LOAD_FRAME_CAL_DAY", "Day the load frame was calibrated"),
    "tested_on": ("INTERNAL_TRIAL_DAY", "Day of the in-house destructive trial"),
    "measured_load_kn": ("INTERNAL_ULTIMATE_FORCE", "Ultimate force reached in-house (unit in _UOM column)"),
    "test_date": ("ACCREDITED_TRIAL_DAY", "Day the accredited laboratory ran its trial"),
    "certified_load_kn": ("ACCREDITED_ULTIMATE_FORCE", "Ultimate force attested by the laboratory (unit in _UOM column)"),
    "min_load_kn": ("REQUIRED_ULTIMATE_FORCE", "Lowest acceptable ultimate force (unit in _UOM column)"),
}

A1_PARTIES = {
    "workforce": ["NORTHWIND ANALYTICS LLC", "BLUE HERON SYSTEMS INC", "CASCADE DATAWORKS CORP"],
    "purchasing": ["FERRO SUPPLY CO", "KESTREL INDUSTRIAL INC", "OAKLINE DISTRIBUTION LLC"],
    "engineering": ["TALUS FASTENING LTD", "GRANITE TESTING SERVICES", "MERIDIAN ALLOYS INC"],
}
A1_STATES = ["CA", "TX", "NY", "WA", "IL", "NJ", "MA", "GA", "NC", "VA"]


def _wf_of(key):
    return {"employee_id": "workforce", "po_id": "purchasing", "part_id": "engineering"}[key]


def _a1_extras(wf):
    """Administrative columns, as (name, description) — irrelevant to any value of interest."""
    if wf == "workforce":
        return [("CASE_NUMBER", "Agency-style case number of the record"),
                ("FISCAL_YEAR", "Federal fiscal year of the extract"),
                ("EMPLOYER_NAME", "Employer legal name"),
                ("EMPLOYER_FEIN_MASKED", "Employer FEIN, masked"),
                ("WORKSITE_STATE", "Worksite state code"),
                ("SOC_CODE", "Standard Occupational Classification code"),
                ("FULL_TIME_POSITION", "Y/N full-time indicator"),
                ("RECORD_LOAD_DATE", "Day this row was loaded to the extract (MM/DD/YYYY)")]
    if wf == "purchasing":
        return [("TRANSACTION_ID", "System transaction id of the record"),
                ("FISCAL_YEAR", "Fiscal year of the extract"),
                ("VENDOR_NAME", "Vendor legal name"),
                ("VENDOR_UEI", "Vendor unique entity identifier"),
                ("PLANT_CODE", "Receiving plant"),
                ("CURRENCY_CODE", "ISO 4217 currency of every money column"),
                ("BUYER_GROUP", "Purchasing group"),
                ("RECORD_LOAD_DATE", "Day this row was loaded to the extract (MM/DD/YYYY)")]
    return [("DOCUMENT_SERIAL", "Document serial of the record"),
            ("FISCAL_YEAR", "Fiscal year of the extract"),
            ("SUPPLIER_NAME", "Supplier legal name"),
            ("DRAWING_REVISION", "Drawing revision letter"),
            ("TEST_STANDARD", "Test method standard reference"),
            ("LAB_ACCREDITATION_NO", "Accreditation certificate number"),
            ("RECORD_LOAD_DATE", "Day this row was loaded to the extract (MM/DD/YYYY)")]


def _a1_extra_value(name, wf, rng, i):
    if name == "CASE_NUMBER":
        return f"I-200-26{rng.randint(1, 365):03d}-{rng.randint(100000, 999999)}"
    if name == "TRANSACTION_ID":
        return f"45{rng.randint(10000000, 99999999)}"
    if name == "DOCUMENT_SERIAL":
        return f"QD{rng.randint(100000, 999999)}"
    if name == "FISCAL_YEAR":
        return "2026"
    if name in ("EMPLOYER_NAME", "VENDOR_NAME", "SUPPLIER_NAME"):
        return rng.choice(A1_PARTIES[wf])
    if name == "EMPLOYER_FEIN_MASKED":
        return f"XX-XXX{rng.randint(1000, 9999)}"
    if name == "WORKSITE_STATE":
        return rng.choice(A1_STATES)
    if name == "SOC_CODE":
        return rng.choice(["15-1252", "15-1211", "15-2051", "17-2141", "13-2011"])
    if name == "FULL_TIME_POSITION":
        return rng.choice(["Y", "Y", "Y", "N"])
    if name == "VENDOR_UEI":
        return "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789") for _ in range(12))
    if name == "PLANT_CODE":
        return rng.choice(["1000", "1100", "2010", "3005"])
    if name == "CURRENCY_CODE":
        return "USD"
    if name == "BUYER_GROUP":
        return rng.choice(["P01", "P02", "P07", "P11"])
    if name == "DRAWING_REVISION":
        return rng.choice("ABCDEFG")
    if name == "TEST_STANDARD":
        return rng.choice(["ASTM F606", "ISO 898-1", "ASTM E8", "NASM 1312-8"])
    if name == "LAB_ACCREDITATION_NO":
        return f"{rng.randint(1000, 9999)}.0{rng.randint(1, 9)}"
    if name == "RECORD_LOAD_DATE":
        return "10/07/2026"
    raise KeyError(name)


def _a1_date(v) -> str:
    d = _date(v)
    return f"{d.month:02d}/{d.day:02d}/{d.year}"


def render_a1(doc, columns, rows, key, rng):
    wf = _wf_of(key)
    extras = _a1_extras(wf)
    # header: id first, then administrative columns interleaved with data columns
    header, desc = [], {}
    plan = []  # list of ("x", name) | ("c", col, kind, unit) | ("u", col)
    lead = extras[:3]
    for name, d in [lead[0]]:
        plan.append(("x", name))
        desc[name] = d
    c0, _k0, _u0, _l0 = columns[0]
    plan.append(("c", c0, "id", None))
    for name, d in lead[1:]:
        plan.append(("x", name))
        desc[name] = d
    data = columns[1:]
    tail = list(extras[3:])
    for idx, (c, kind, unit, _lab) in enumerate(data):
        plan.append(("c", c, kind, unit))
        if kind == "amount" and unit == "kN":
            plan.append(("u", c))
        if tail and idx % 2 == 0:
            name, d = tail.pop(0)
            plan.append(("x", name))
            desc[name] = d
    for name, d in tail:
        plan.append(("x", name))
        desc[name] = d
    for p in plan:
        if p[0] == "x":
            header.append(p[1])
        elif p[0] == "c":
            header.append(A1_COLS[p[1]][0])
        else:
            header.append(A1_COLS[p[1]][0] + "_UOM")

    out = [f"# {A1_TITLES.get(doc, doc)} -- PUBLIC DISCLOSURE FILE (dataset {doc})",
           "# Extract run 10/07/2026. Delimiter '|'. First non-'#' line is the column header.",
           "# One data line per record; a reference may repeat on several lines and each line stands alone.",
           "# Empty field = not reported. All dates are MM/DD/YYYY (two-digit month first, then day, then year).",
           "# Money columns are US dollars with a '.' decimal point and no thousands separators.",
           "# _UOM columns give the unit of the force column to their left: KN = kilonewtons, N = newtons.",
           "# RECORD LAYOUT"]
    for i, h in enumerate(header, 1):
        if h.endswith("_UOM"):
            d = "Unit of measure of " + h[:-4]
        elif h in desc:
            d = desc[h]
        else:
            d = next(v[1] for v in A1_COLS.values() if v[0] == h)
        out.append(f"#   {i:>2}  {h:<30} {d}")
    out.append(f"# RECORD COUNT: {len(rows)}")
    out.append("|".join(header))
    for i, r in enumerate(rows):
        cells, pending_unit = [], ""
        for p in plan:
            if p[0] == "x":
                cells.append(_a1_extra_value(p[1], wf, rng, i))
                continue
            if p[0] == "u":
                cells.append(pending_unit)
                pending_unit = ""
                continue
            c, kind, unit = p[1], p[2], p[3]
            v = r.get(c, "")
            if kind == "id":
                cells.append(str(v))
            elif _blank(v):
                cells.append("")
            elif kind == "date":
                cells.append(_a1_date(v))
            elif kind == "amount" and unit == "USD":
                cells.append(_money2(_dec(v)))
            elif kind == "amount" and unit == "kN":
                if rng.random() < 0.5:
                    cells.append(_plain(_dec(v)))
                    pending_unit = "KN"
                else:
                    cells.append(_plain(_dec(v) * 1000))
                    pending_unit = "N"
                continue
            elif kind == "amount":
                cells.append(_plain(_dec(v)))
            else:
                cells.append(_clean(v, "|\n").upper())
        out.append("|".join(cells))  # a blank force leaves its unit blank too
    if not rows:
        out.append("# NO RECORDS MET THE EXTRACT CRITERIA")
    return "txt", "\n".join(out) + "\n"


# ====================================================================== A2: X12-style EDI
A2_SETS = {
    "hr_roster": ("ZW1", "WORKFORCE STATUS"), "work_authorizations": ("ZW2", "ELIGIBILITY EVIDENCE"),
    "ead_cards": ("ZW3", "I-766 CARD REGISTER"), "reverifications": ("ZW4", "SUPPLEMENT B EVENTS"),
    "lca_notices": ("ZW5", "PUBLIC ACCESS NOTICE EVENTS"), "lca_filings": ("ZW6", "ETA-9035 SUBMISSIONS"),
    "dol_receipts": ("ZW7", "OFLC INTAKE ADVICE"),
    "requisitions": ("850", "PURCHASE REQUEST (BEG01=RQ)"), "purchase_orders": ("850", "PURCHASE ORDER"),
    "invoices": ("810", "INVOICE"), "receipts": ("861", "RECEIVING ADVICE"),
    "warehouse_scans": ("944", "WAREHOUSE STOCK TRANSFER RECEIPT ADVICE"),
    "payments": ("820", "PAYMENT ORDER/REMITTANCE ADVICE"),
    "parts": ("ZE1", "COMPONENT MASTER"), "calibration_log": ("ZE2", "LOAD FRAME CALIBRATION EVENTS"),
    "test_reports": ("863", "REPORT OF TEST RESULTS (INTERNAL)"),
    "lab_certificates": ("863", "REPORT OF TEST RESULTS (ACCREDITED LAB)"),
    "spec_sheets": ("ZE3", "DESIGN REQUIREMENTS"),
}

# entity id segment per key: (segment template prefix, companion note)
A2_ID = {
    "employee_id": ("REF*EI", "REF*EI = EMPLOYER-ASSIGNED WORKER FILE NUMBER"),
    "po_id": ("REF*PO", "REF*PO = PURCHASING DOCUMENT KEY"),
    "part_id": ("LIN**BP", "LIN**BP = BUYER CATALOG KEY OF THE COMPONENT"),
}

# canonical column -> (segment, qualifier, companion description)
A2_MAP = {
    "reverification_status": ("REF", "RVS", "STANDING OF FORM I-9 SUPPLEMENT B"),
    "notice_status": ("REF", "NPS", "PUBLIC ACCESS NOTICE INDICATOR"),
    "document_type": ("REF", "ADT", "TITLE OF EMPLOYABILITY EVIDENCE PRESENTED"),
    "status": ("REF", "RQS", "ROUTING OUTCOME OF THE PURCHASE REQUEST"),
    "qa_status": ("REF", "QAD", "QUALITY RELEASE DECISION"),
    "visa_end_date": ("DTP", "337", "ADMITTED NONIMMIGRANT STAY ENDS"),
    "planned_filing_date": ("DTP", "814", "ETA-9035 SUBMISSION INTENDED FOR"),
    "expires_on": ("DTP", "036", "EMPLOYABILITY EVIDENCE LAPSES"),
    "card_expiry": ("DTP", "438", "LAST VALID DAY ON I-766 CARD"),
    "completed_on": ("DTP", "572", "SUPPLEMENT B EXECUTED"),
    "posted_on": ("DTP", "196", "NOTICE DISPLAY BEGAN"),
    "removed_on": ("DTP", "197", "NOTICE DISPLAY ENDED"),
    "filed_on": ("DTP", "640", "ETA-9035 SUBMITTED"),
    "receipt_date": ("DTP", "009", "OFLC LOGGED INTAKE"),
    "expected_delivery": ("DTP", "002", "DELIVERY REQUESTED BY"),
    "due_on": ("DTP", "481", "NET DUE UNDER TERMS"),
    "received_on": ("DTP", "050", "GOODS RECEIPT POSTED"),
    "scan_date": ("DTP", "945", "HANDHELD CAPTURE AT INBOUND DOOR"),
    "paid_on": ("DTP", "234", "DISBURSEMENT CLEARED"),
    "planned_test_date": ("DTP", "690", "TEST BOOKED FOR"),
    "calibrated_on": ("DTP", "300", "LOAD FRAME CALIBRATION PERFORMED"),
    "tested_on": ("DTP", "301", "IN-HOUSE DESTRUCTIVE TRIAL RUN"),
    "test_date": ("DTP", "302", "ACCREDITED LAB DESTRUCTIVE TRIAL RUN"),
    "requested_amount": ("AMT", "EST", "ESTIMATED SPEND ON THE REQUEST"),
    "po_amount": ("AMT", "TT", "NET VALUE COMMITTED ON THE ORDER"),
    "invoice_amount": ("TDS", "", "GROSS BILL TOTAL"),
    "invoiced_qty": ("QTY", "D1", "UNITS CHARGED ON THE BILL"),
    "received_qty": ("QTY", "RC", "UNITS ACCEPTED AT GOODS RECEIPT"),
    "target_load_kn": ("MEA", "DUF", "DESIGN ULTIMATE FORCE"),
    "measured_load_kn": ("MEA", "UFH", "ULTIMATE FORCE REACHED IN-HOUSE"),
    "certified_load_kn": ("MEA", "UFL", "ULTIMATE FORCE ATTESTED BY LABORATORY"),
    "min_load_kn": ("MEA", "UFM", "LOWEST ACCEPTABLE ULTIMATE FORCE"),
}

A2_FILLER_NOTES = {
    "workforce": ["N1*EM = EMPLOYING ENTITY", "REF*ZZ = SOURCE SYSTEM ROW TOKEN",
                  "DTP*097*D8 = TRANSACTION CREATED (ADMINISTRATIVE)"],
    "purchasing": ["N1*VN = VENDOR", "N1*ST = SHIP-TO PLANT", "REF*ZZ = SOURCE SYSTEM ROW TOKEN",
                   "DTP*097*D8 = TRANSACTION CREATED (ADMINISTRATIVE)"],
    "engineering": ["N1*SU = SUPPLIER", "REF*DR = DRAWING REVISION", "REF*ZZ = SOURCE SYSTEM ROW TOKEN",
                    "DTP*097*D8 = TRANSACTION CREATED (ADMINISTRATIVE)"],
}


def _a2_date(v) -> str:
    return _date(v).strftime("%Y%m%d")


def render_a2(doc, columns, rows, key, rng):
    wf = _wf_of(key)
    st_id, st_name = A2_SETS.get(doc, ("ZZZ", doc.upper()))
    ctl = rng.randint(100000000, 999999999)
    grp = rng.randint(1000, 99999)
    sender = rng.choice(["HRISPROD01", "ERPPROD01", "PLMEXPORT"])
    segs = []  # transaction-set segments (ST..SE)
    segs.append(f"ST*{st_id}*0001")
    if st_id == "850":
        segs.append(f"BEG*00*{'RQ' if doc == 'requisitions' else 'SA'}*BATCH{grp}**20261007")
    else:
        segs.append(f"BGN*00*{doc.upper()}-{grp}*20261007*1200")
    notes = [f"TRANSACTION CONTENT: {st_name} (dataset {doc})",
             "ONE LX LOOP PER RECORD. A KEY MAY APPEAR IN SEVERAL LOOPS; EACH LOOP STANDS ALONE",
             "A SEGMENT ABSENT FROM A LOOP MEANS THE VALUE WAS NOT REPORTED",
             "DTP FORMAT QUALIFIER D8 = DATE AS CCYYMMDD (FOUR-DIGIT YEAR, MONTH, DAY)",
             "AMT VALUES ARE US DOLLARS WITH EXPLICIT DECIMAL POINT",
             "TDS01 IS US DOLLARS WITH IMPLIED TWO DECIMAL PLACES (TDS*4400000 = 44000.00)",
             "QTY UNIT EA = EACH; MEA UNIT KN = KILONEWTON, NT = NEWTON",
             A2_ID[key][1]]
    for c, kind, unit, _l in columns[1:]:
        seg, q, d = A2_MAP[c]
        if seg == "DTP":
            notes.append(f"DTP*{q}*D8 = {d}")
        elif seg == "TDS":
            notes.append(f"TDS = {d}")
        elif seg == "MEA":
            notes.append(f"MEA*TE*{q} = {d}")
        else:
            notes.append(f"{seg}*{q} = {d}")
    notes += A2_FILLER_NOTES[wf]
    for n in notes:
        segs.append(f"NTE*GEN*{n}")
    if not rows:
        segs.append("NTE*GEN*NO RECORDS IN THIS TRANSMISSION")
    idseg = A2_ID[key][0]
    for i, r in enumerate(rows, 1):
        segs.append(f"LX*{i}")
        segs.append(f"{idseg}*{r[key]}")
        if wf == "workforce":
            segs.append(f"N1*EM*{rng.choice(A1_PARTIES[wf])}")
        elif wf == "purchasing":
            segs.append(f"N1*VN*{rng.choice(A1_PARTIES[wf])}*92*V{rng.randint(10000, 99999)}")
            segs.append(f"N1*ST*PLANT {rng.choice(['1000', '1100', '2010'])}")
        else:
            segs.append(f"N1*SU*{rng.choice(A1_PARTIES[wf])}")
            segs.append(f"REF*DR*{rng.choice('ABCDEF')}")
        body = []
        for c, kind, unit, _l in columns[1:]:
            v = r.get(c, "")
            if _blank(v):
                continue
            seg, q, _d = A2_MAP[c]
            if seg == "DTP":
                body.append(f"DTP*{q}*D8*{_a2_date(v)}")
            elif seg == "REF":
                body.append(f"REF*{q}*{_clean(v, '*~').upper()}")
            elif seg == "AMT":
                body.append(f"AMT*{q}*{_money2(_dec(v))}")
            elif seg == "TDS":
                cents = _dec(v) * 100
                if cents == cents.to_integral_value():
                    body.append(f"TDS*{int(cents)}")
                else:
                    body.append(f"AMT*BAP*{_plain(_dec(v))}")  # declared below if ever used
            elif seg == "QTY":
                body.append(f"QTY*{q}*{_plain(_dec(v))}*EA")
            elif seg == "MEA":
                if rng.random() < 0.5:
                    body.append(f"MEA*TE*{q}*{_plain(_dec(v))}*KN")
                else:
                    body.append(f"MEA*TE*{q}*{_plain(_dec(v) * 1000)}*NT")
        rng.shuffle(body)  # segment order within a loop carries no meaning
        segs.extend(body)
        segs.append(f"REF*ZZ*{rng.randint(10 ** 9, 10 ** 10 - 1)}")
        segs.append(f"DTP*097*D8*2026{rng.randint(1, 9):02d}{rng.randint(1, 28):02d}")
    if any(s.startswith("AMT*BAP*") for s in segs):
        segs.insert(2, "NTE*GEN*AMT*BAP = GROSS BILL TOTAL, US DOLLARS (USED WHEN NOT WHOLE CENTS)")
    segs.append(f"CTT*{len(rows)}")
    segs.append(f"SE*{len(segs) + 1}*0001")
    isa = (f"ISA*00*{' ' * 10}*00*{' ' * 10}*ZZ*{sender:<15}*ZZ*{'COMPLIANCEHUB':<15}"
           f"*261007*1200*U*00401*{ctl:09d}*0*P*>")
    out = [isa, f"GS*XX*{sender}*COMPLIANCEHUB*20261007*1200*{grp}*X*004010"] + segs + \
          [f"GE*1*{grp}", f"IEA*1*{ctl:09d}"]
    return "edi", "~\n".join(out) + "~\n"


LAYOUTS = {"A1": render_a1, "A2": render_a2}


# ====================================================================== readers (self-test only)
def _read_a1(text):
    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
    header = lines[0].split("|")
    recs = []
    for ln in lines[1:]:
        cells = ln.split("|")
        assert len(cells) == len(header), "cell count"
        recs.append(dict(zip(header, cells)))
    return header, recs


def _a1_value(rec, c, kind, unit):
    col = A1_COLS[c][0]
    raw = rec[col]
    if raw == "":
        return None
    if kind == "date":
        mm, dd, yy = raw.split("/")
        return date(int(yy), int(mm), int(dd)).isoformat()
    if kind == "amount" and unit == "kN":
        u = rec[col + "_UOM"]
        return Decimal(raw) / (1000 if u == "N" else 1) if u in ("N", "KN") else "BADUNIT"
    if kind == "amount":
        return Decimal(raw)
    return raw


def _read_a2(text):
    segs = [s.strip() for s in text.split("~") if s.strip()]
    loops, cur = [], None
    for s in segs:
        if s.startswith("LX*"):
            cur = [s]
            loops.append(cur)
        elif s.startswith(("CTT*", "SE*")):
            cur = None
        elif cur is not None:
            cur.append(s)
    return segs, loops


def _a2_value(loop, c, kind, unit):
    seg, q, _d = A2_MAP[c]
    found = []
    for s in loop:
        e = s.split("*")
        if seg == "DTP" and e[0] == "DTP" and e[1] == q:
            assert e[2] == "D8"
            found.append(date(int(e[3][:4]), int(e[3][4:6]), int(e[3][6:])).isoformat())
        elif seg == "REF" and e[0] == "REF" and e[1] == q:
            found.append(e[2])
        elif seg == "AMT" and e[0] == "AMT" and e[1] == q:
            found.append(Decimal(e[2]))
        elif seg == "TDS" and e[0] == "TDS":
            found.append(Decimal(e[1]) / 100)
        elif seg == "TDS" and e[0] == "AMT" and e[1] == "BAP":
            found.append(Decimal(e[2]))
        elif seg == "QTY" and e[0] == "QTY" and e[1] == q:
            found.append(Decimal(e[2]))
        elif seg == "MEA" and e[0] == "MEA" and e[2] == q:
            found.append(Decimal(e[3]) / (1000 if e[4] == "NT" else 1))
    assert len(found) <= 1, f"duplicate segment for {c}"
    return found[0] if found else None


def _norm(s):
    return " ".join(str(s).lower().replace("_", " ").replace("-", " ").replace("#", " ").split())


def _selftest() -> int:
    import sys
    sys.path.insert(0, "/Users/roydi/Desktop/nofalsegreen")
    from nofalsegreen import study13 as s13
    from nofalsegreen import study13_heldout as h

    fails = []

    def chk(cond, msg):
        if not cond:
            fails.append(msg)

    # ---- labels distinct from canonical names, plain labels, L2 headers and L4-L6 labels
    forbidden = set()
    for docs in s13.DOCS.values():
        for cols in docs.values():
            for c, _k, _u, lab in cols:
                forbidden |= {_norm(c), _norm(lab), _norm(s13.L2_HEADERS[c])}
    for c, (_sec, k) in h.L4_KEYS.items():
        forbidden.add(_norm(k))
    for c, (hd, leg) in h.L6_COLS.items():
        forbidden |= {_norm(hd), _norm(leg)}
    for c, (pres, absent) in h.L5_PHRASES.items():
        forbidden |= {_norm(p.replace("{v}", "")) for p in pres} | {_norm(absent)}
    for c, (col, d) in A1_COLS.items():
        chk(_norm(col) not in forbidden and _norm(d) not in forbidden, f"A1 label {col} for {c}")
    for c, (_seg, q, d) in A2_MAP.items():
        chk(_norm(d) not in forbidden, f"A2 label {d} for {c}")
    for c, (_s, d) in A2_ID.items():
        chk(_norm(d.split("=")[1]) not in forbidden, f"A2 id label {d}")

    # ---- empty documents
    for name, fn in LAYOUTS.items():
        for wf in s13.WORKFLOWS:
            for doc, cols in s13.DOCS[wf].items():
                ext, txt = fn(doc, cols, [], s13.KEY[wf], random.Random(1))
                if name == "A1":
                    hdr, recs = _read_a1(txt)
                    chk(len(recs) == 0 and len(hdr) >= len(cols), f"A1 empty {doc}")
                else:
                    segs, loops = _read_a2(txt)
                    chk(len(loops) == 0 and segs[-1].startswith("IEA"), f"A2 empty {doc}")

    samples = {}
    n_docs = n_rows = n_blank = n_vals = 0
    seeds = (1401, 1402, 1403, 1404)
    for wf in s13.WORKFLOWS:
        key = s13.KEY[wf]
        for seed in seeds:
            p = s13.make_packet(wf, seed)
            for doc, cols in s13.DOCS[wf].items():
                rows = p.tables[doc]
                n_docs += 1
                n_rows += len(rows)
                for name, fn in LAYOUTS.items():
                    seedstr = f"study14-render-{name}-{p.packet_id}-{doc}"
                    ext, txt = fn(doc, cols, rows, key, random.Random(seedstr))
                    chk(fn(doc, cols, rows, key, random.Random(seedstr)) == (ext, txt),
                        f"{name} nondeterministic {doc}")
                    tag = f"{name} {wf}-{seed} {doc}"
                    if name == "A1":
                        _hdr, recs = _read_a1(txt)
                    else:
                        segs, recs = _read_a2(txt)
                        # control counts in trailers
                        st_i = next(i for i, s in enumerate(segs) if s.startswith("ST*"))
                        se = next(s for s in segs if s.startswith("SE*"))
                        chk(int(se.split("*")[1]) == len(segs) - st_i - 2, f"{tag}: SE count")
                        ctt = next(s for s in segs if s.startswith("CTT*"))
                        chk(int(ctt.split("*")[1]) == len(rows), f"{tag}: CTT count")
                    chk(len(recs) == len(rows), f"{tag}: {len(recs)} records != {len(rows)} rows")
                    if len(recs) != len(rows):
                        continue
                    for r, rec in zip(rows, recs):
                        if name == "A1":
                            chk(rec[A1_COLS[key][0]] == r[key], f"{tag}: id {r[key]}")
                        else:
                            chk(rec[1] == f"{A2_ID[key][0]}*{r[key]}", f"{tag}: id {r[key]}")
                        for c, kind, unit, _lab in cols[1:]:
                            v = r.get(c, "")
                            got = (_a1_value(rec, c, kind, unit) if name == "A1"
                                   else _a2_value(rec, c, kind, unit))
                            if _blank(v):
                                n_blank += 1
                                chk(got is None, f"{tag}: blank {c} rendered as {got}")
                                if name == "A1" and kind == "amount" and unit == "kN":
                                    chk(rec[A1_COLS[c][0] + "_UOM"] == "", f"{tag}: blank {c} has unit")
                                continue
                            n_vals += 1
                            if kind == "date":
                                chk(got == str(v), f"{tag}: {c} {got} != {v}")
                            elif kind == "amount":
                                chk(got == _dec(v), f"{tag}: {c} {got} != {v}")
                            else:
                                chk(got is not None and got.upper() == str(v).upper(),
                                    f"{tag}: text {c} {got} != {v}")
                    if seed == 1401 and doc in ("work_authorizations", "invoices", "lab_certificates"):
                        samples[(name, wf)] = (doc, txt)

    for name in LAYOUTS:
        for wf in s13.WORKFLOWS:
            doc, txt = samples[(name, wf)]
            lines = txt.splitlines()
            if name == "A1":
                body = [ln for ln in lines if not ln.startswith("#")]
                show = lines[:6] + ["# ..."] + body[:4]
            else:
                lx = next(i for i, ln in enumerate(lines) if ln.startswith("LX*"))
                show = lines[:4] + ["..."] + lines[lx:lx + 16] + ["..."] + lines[-4:]
            print(f"===== {name} / {wf} / {doc} (seed 1401) =====")
            print("\n".join(show))
            print()
    print(f"documents checked: {n_docs} per layout; rows: {n_rows}; "
          f"blank cells: {n_blank}; non-blank values recovered: {n_vals} per layout")
    if fails:
        print(f"SELFTEST FAILED: {len(fails)} problems")
        for f in fails[:40]:
            print("  -", f)
        return 1
    print("SELFTEST PASSED (ids per record, record counts, blanks never rendered, every non-blank "
          "date/amount/text recovered exactly, labels distinct from canonical/L2/plain/L4-L6, deterministic, "
          "empty docs render)")
    return 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)

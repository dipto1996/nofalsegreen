"""Study 14 held-out layouts B1 and B2 (human-facing documents).

  B1  an intranet HTML report of printed forms: one <article> "form sheet" per record, each a
      caption/entry table with a control number, sheet counter and a reviewer sign-off line.
      Dates carry a weekday and AP-style month ("Tue., Sept. 3, 2026"); money as "USD 1,234.00";
      loads in kN; counts as "pcs". A blank field is either left out of the sheet or shown
      as "left blank on form".
  B2  a mailbox export: one standalone e-mail per record (headers, greeting, free sentences,
      signature). Dates as "March 3rd, 2026" or "3rd Mar 2026"; money as "$1,234" or
      "1,234 dollars"; loads in kN or kilonewtons. Blank fields are stated as not on hand.
      A notice take-down date is sometimes given relative to its posting day in the same mail.

Standard library only. `python3 layouts.py --selftest`.
"""

from __future__ import annotations

import html
import random
import re
from datetime import date, timedelta
from decimal import Decimal

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
AP_MON = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.",
          "Nov.", "Dec."]
MON3 = [m[:3] for m in MONTHS]
WD_AP = ["Mon.", "Tue.", "Wed.", "Thu.", "Fri.", "Sat.", "Sun."]
WD = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def _date(v) -> date:
    return v if isinstance(v, date) else date.fromisoformat(str(v))


def _plain(d: Decimal) -> str:
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def _commas(d: Decimal) -> str:
    s = _plain(d)
    neg = s.startswith("-")
    s = s.lstrip("-")
    whole, _, frac = s.partition(".")
    return ("-" if neg else "") + f"{int(whole):,}" + ("." + frac if frac else "")


def _ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


# =============================================================== B1: HTML form sheets
B1_TITLES = {
    "hr_roster": "People file &mdash; personnel snapshot",
    "work_authorizations": "Right-to-work evidence sheets",
    "ead_cards": "Employment authorization card sheets",
    "reverifications": "Supplement B (I-9) sign-off sheets",
    "lca_notices": "Notice of filing &mdash; display sheets",
    "lca_filings": "FLAG submission sheets",
    "dol_receipts": "Agency receipt notices",
    "requisitions": "Department spend requests",
    "purchase_orders": "Order commitment sheets",
    "invoices": "Vendor billing sheets",
    "receipts": "Delivery count sheets",
    "warehouse_scans": "Inbound dock scan sheets",
    "payments": "Disbursement sheets",
    "parts": "Item master sheets",
    "calibration_log": "Load frame calibration sheets",
    "test_reports": "In-house destructive test sheets",
    "lab_certificates": "Accredited laboratory certificates",
    "spec_sheets": "Drawing requirement sheets",
}
B1_CODES = {
    "hr_roster": "HR-01", "work_authorizations": "HR-12", "ead_cards": "HR-13",
    "reverifications": "HR-19", "lca_notices": "IM-04", "lca_filings": "IM-07",
    "dol_receipts": "IM-08", "requisitions": "PR-02", "purchase_orders": "PR-05",
    "invoices": "AP-11", "receipts": "WH-03", "warehouse_scans": "WH-09", "payments": "AP-17",
    "parts": "EN-01", "calibration_log": "QL-22", "test_reports": "QL-30",
    "lab_certificates": "QL-31", "spec_sheets": "EN-06",
}
B1_LABELS = {
    "employee_id": "Staff badge",
    "po_id": "Procurement reference",
    "part_id": "Item code",
    "reverification_status": "Re-verification outcome",
    "visa_end_date": "Authorized stay ends",
    "notice_status": "Notice-of-filing posting",
    "planned_filing_date": "Intended LCA submission",
    "document_type": "Evidence presented",
    "expires_on": "Evidence expires",
    "card_expiry": "EAD valid to",
    "completed_on": "Supplement B signed on",
    "posted_on": "Notice first displayed",
    "removed_on": "Notice withdrawn from display",
    "filed_on": "Submitted through FLAG",
    "receipt_date": "Agency receipt notice dated",
    "status": "Request disposition",
    "requested_amount": "Budget ask",
    "expected_delivery": "Promised arrival",
    "po_amount": "Total order value",
    "invoice_amount": "Invoice grand total",
    "invoiced_qty": "Units charged",
    "due_on": "Payment deadline",
    "received_qty": "Units counted on delivery",
    "received_on": "Delivery booked",
    "scan_date": "Dock scanner stamp",
    "paid_on": "Funds released",
    "qa_status": "Inspection verdict",
    "target_load_kn": "Design load objective",
    "planned_test_date": "Test booked for",
    "calibrated_on": "Frame last calibrated",
    "tested_on": "Break test performed",
    "measured_load_kn": "Load at failure (in-house)",
    "test_date": "Laboratory test performed",
    "certified_load_kn": "Load at failure (lab certified)",
    "min_load_kn": "Drawing minimum at failure",
}
B1_NONE = "&mdash; left blank on form &mdash;"
B1_REVIEWERS = ["K. Mbeki", "J. Ortega", "S. Lindqvist", "R. Haddad", "M. Okafor", "T. Nguyen"]


def _b1_date(v, rng) -> str:
    d = _date(v)
    return f"{WD_AP[d.weekday()]}, {AP_MON[d.month - 1]} {d.day}, {d.year}"


def _b1_amount(unit, v) -> str:
    d = Decimal(str(v))
    if unit == "USD":
        return _b1_usd(d)
    if unit == "kN":
        return f"{_commas(d)} kN"
    if unit == "units":
        return f"{_commas(d)} pcs"
    return _commas(d)


def _b1_usd(d: Decimal) -> str:
    s = _plain(d)
    whole, _, frac = s.partition(".")
    if len(frac) <= 2:
        frac = (frac + "00")[:2]
        return f"USD {int(whole):,}.{frac}"
    return f"USD {_commas(d)}"


def _b1_value(kind, unit, v, rng) -> str:
    if kind == "date":
        return _b1_date(v, rng)
    if kind == "amount":
        if unit == "USD":
            return _b1_usd(Decimal(str(v)))
        return _b1_amount(unit, v)
    return html.escape(str(v))


B1_CSS = """body{font-family:Georgia,serif;background:#fafaf7;color:#222;margin:2em}
header{border-bottom:3px double #555;margin-bottom:1.5em}
article.sheet{border:1px solid #999;padding:.8em 1.2em;margin:1.2em 0;background:#fff;page-break-after:always}
article.sheet h2{font-size:1em;margin:0 0 .5em;display:flex;justify-content:space-between}
table.fields{border-collapse:collapse;width:100%}
table.fields th{text-align:left;width:40%;font-weight:normal;color:#555;border-bottom:1px dotted #bbb;padding:3px}
table.fields td{border-bottom:1px dotted #bbb;padding:3px}
td.void{color:#999;font-style:italic}
p.signoff{font-size:.85em;color:#666;margin-top:.8em}
footer{font-size:.8em;color:#777;border-top:1px solid #ccc;margin-top:2em}"""


def render_b1(doc, columns, rows, key, rng):
    title = B1_TITLES.get(doc, html.escape(doc))
    code = B1_CODES.get(doc, "XX-00")
    batch = rng.randrange(10000, 99999)
    n = len(rows)
    out = ["<!DOCTYPE html>", "<html lang=\"en\">", "<head>", "<meta charset=\"utf-8\">",
           f"<title>{title} | Records portal</title>", f"<style>\n{B1_CSS}\n</style>", "</head>",
           "<body>", "<header>",
           f"<p class=\"crumbs\">Intranet &rsaquo; Records portal &rsaquo; Form {code}</p>",
           f"<h1>{title}</h1>",
           f"<p>Print batch {batch} &middot; {n} sheet{'s' if n != 1 else ''} in this batch &middot; "
           f"source register <code>{html.escape(doc)}</code></p>",
           "<p class=\"note\">Each sheet below is a separate filed form. Captions on a sheet with "
           "no entry were left blank by the preparer; captions not printed were not completed.</p>",
           "</header>", "<main>"]
    if not rows:
        out.append("<p class=\"empty\">This batch contains no filed sheets.</p>")
    for i, r in enumerate(rows, 1):
        ctrl = f"{code}-{rng.randrange(100000, 999999)}"
        out.append(f"<article class=\"sheet\" id=\"sheet-{i}\">")
        out.append(f"<h2><span>Form {code} &mdash; sheet {i} of {n}</span>"
                   f"<span>Control no. {ctrl}</span></h2>")
        out.append("<table class=\"fields\">")
        omit_style = rng.random() < 0.5  # this sheet leaves blank captions out entirely
        for c, kind, unit, _lab in columns:
            v = r.get(c, "")
            lab = html.escape(B1_LABELS[c])
            if kind == "id":
                out.append(f"<tr><th>{lab}</th><td><strong>{html.escape(str(v))}</strong></td></tr>")
            elif _blank(v):
                if not omit_style:
                    out.append(f"<tr><th>{lab}</th><td class=\"void\">{B1_NONE}</td></tr>")
            else:
                out.append(f"<tr><th>{lab}</th><td>{_b1_value(kind, unit, v, rng)}</td></tr>")
        out.append("</table>")
        out.append(f"<p class=\"signoff\">Reviewed by: {rng.choice(B1_REVIEWERS)} &nbsp;&middot;&nbsp; "
                   f"Initials: ______ &nbsp;&middot;&nbsp; Page {i} of {max(n, 1)}</p>")
        out.append("</article>")
    out += ["</main>",
            "<footer><p>Printed on Wed., Oct. 7, 2026 from the records portal. Internal use only. "
            "Retention class R-7.</p></footer>", "</body>", "</html>"]
    return "html", "\n".join(out) + "\n"


# =============================================================== B2: mailbox export
B2_SUBJECT = {
    "hr_roster": "people file snapshot",
    "work_authorizations": "work permission evidence",
    "ead_cards": "EAD card on file",
    "reverifications": "I-9 Supplement B done",
    "lca_notices": "LCA notice on the board",
    "lca_filings": "LCA went in",
    "dol_receipts": "DOL acknowledgment",
    "requisitions": "spend request",
    "purchase_orders": "PO commitment",
    "invoices": "vendor bill",
    "receipts": "delivery count",
    "warehouse_scans": "dock scan",
    "payments": "payment out",
    "parts": "item master",
    "calibration_log": "frame calibration",
    "test_reports": "break test result",
    "lab_certificates": "lab cert received",
    "spec_sheets": "drawing requirement",
}
B2_SENDERS = {
    "employee_id": [("Dana Whitfield", "dwhitfield", "People Operations", "ext. 4471"),
                    ("Priya Raman", "praman", "Immigration Desk", "ext. 4410"),
                    ("Marcus Bell", "mbell", "HR Compliance", "ext. 4402")],
    "po_id": [("Lena Fischer", "lfischer", "Accounts Payable", "ext. 2290"),
              ("Omar Saleh", "osaleh", "Receiving", "ext. 2214"),
              ("Grace Kim", "gkim", "Procurement", "ext. 2203")],
    "part_id": [("Ivan Petrov", "ipetrov", "Test Lab", "ext. 7712"),
                ("Hannah Cole", "hcole", "Quality Engineering", "ext. 7740"),
                ("Tomas Reyes", "treyes", "Design Engineering", "ext. 7705")],
}
B2_ID_INTRO = {
    "employee_id": ["Quick note on {k}.", "Writing about team member {k}.", "Re {k}:"],
    "po_id": ["Update on {k}.", "For {k}:", "Regarding {k}."],
    "part_id": ["Note on {k}.", "For item {k}:", "About {k}."],
}
# column -> (sentence templates with {v}; sentence used when the field is blank)
B2_SENT = {
    "reverification_status": (["Their re-verification shows as {v} in the system.",
                               "Re-verification flag reads {v} for them."],
                              "I don't have a re-verification outcome for them."),
    "visa_end_date": (["Their authorized stay runs out on {v}.",
                       "Stay end per the I-94 we hold is {v}."],
                      "I don't have an end of stay for them."),
    "notice_status": (["Posting flag for the notice of filing reads {v}.",
                       "On the posting side they are marked {v}."],
                      "There is no posting flag against them."),
    "planned_filing_date": (["We intend to put the LCA in on {v}.",
                             "The plan is to submit their LCA on {v}."],
                            "No intended LCA submission day has been set."),
    "document_type": (["The evidence they showed us was a {v}.",
                       "Document category on file: {v}."],
                      "Nobody noted what evidence they showed."),
    "expires_on": (["That evidence stops being valid on {v}.",
                    "It is good only up to {v}."],
                   "We have no end-of-validity for that evidence."),
    "card_expiry": (["Their EAD card is printed with an end date of {v}.",
                     "Card says it runs to {v}."],
                    "The card's end date wasn't copied down."),
    "completed_on": (["Supplement B was signed off on {v}.",
                      "We finished the re-verification on {v}."],
                     "There is no sign-off day for the Supplement B."),
    "posted_on": (["The notice went up on the board on {v}.",
                   "We pinned the notice up on {v}."],
                  "I can't tell you when the notice went up."),
    "removed_on": (["It was taken off the board on {v}.",
                    "We pulled the notice down on {v}."],
                   "There's no record of when it was pulled down."),
    "filed_on": (["The LCA was submitted through FLAG on {v}.",
                  "We pushed the LCA into FLAG on {v}."],
                 "I don't have a FLAG submission day."),
    "receipt_date": (["DOL's acknowledgment is dated {v}.",
                      "The agency acknowledged it on {v}."],
                     "No acknowledgment date from DOL is on hand."),
    "status": (["Request disposition: {v}.", "The request currently sits at {v}."],
               "The request has no disposition yet."),
    "requested_amount": (["The department asked for {v} all-in.",
                          "Budget ask on the request was {v} in total."],
                         "No budget figure was put on the request."),
    "expected_delivery": (["Supplier promised it would land on {v}.",
                           "Promised arrival is {v}."],
                          "No promised arrival day was given."),
    "po_amount": (["The PO was raised for {v} in total.",
                   "Committed value on the PO is {v} overall."],
                  "The PO value is missing from what I have."),
    "invoice_amount": (["The vendor's bill comes to {v} in total.",
                        "Invoice total is {v} all told."],
                       "The bill total isn't on the copy I have."),
    "invoiced_qty": (["They charged us for {v} on that bill.",
                      "Bill lists {v} as the chargeable count."],
                     "The bill doesn't show a unit count."),
    "due_on": (["Payment has to go out by {v}.",
                "The bill must be settled no later than {v}."],
               "There's no payment deadline printed on the bill."),
    "received_qty": (["We counted {v} on arrival.", "Receiving tallied {v} off the truck."],
                     "No count was taken on arrival."),
    "received_on": (["It was booked in on {v}.", "The delivery was logged as received on {v}."],
                    "I don't have a booking-in day."),
    "scan_date": (["The dock scanner picked it up on {v}.",
                   "Scanner stamp at the dock reads {v}."],
                  "The scanner stamp is missing."),
    "paid_on": (["Funds were released to the vendor on {v}.",
                 "We sent the money on {v}."],
                "I have no release-of-funds day."),
    "qa_status": (["Inspection verdict is {v}.", "QA signed it off as {v}."],
                  "There's no inspection verdict yet."),
    "target_load_kn": (["We designed it to carry {v} before letting go.",
                        "Design objective is {v} at failure."],
                       "No design load objective is noted."),
    "planned_test_date": (["The break test is booked for {v}.",
                           "Rig time is reserved for {v}."],
                          "No rig time has been booked."),
    "calibrated_on": (["The load frame was last calibrated on {v}.",
                       "Frame calibration sticker says {v}."],
                      "I can't find the frame calibration day."),
    "tested_on": (["We broke it on the frame on {v}.",
                   "In-house break test ran on {v}."],
                  "The in-house break test day isn't recorded."),
    "measured_load_kn": (["In our test it let go at {v}.",
                          "Our frame recorded failure at {v}."],
                         "Our test sheet doesn't give the failure load."),
    "test_date": (["The accredited lab ran it on {v}.",
                   "Per the certificate the lab test happened on {v}."],
                  "The certificate doesn't say when the lab ran it."),
    "certified_load_kn": (["The lab certifies failure at {v}.",
                           "Certificate states it failed at {v}."],
                          "The certificate leaves the failure load empty."),
    "min_load_kn": (["The drawing calls for at least {v} at failure.",
                     "Drawing minimum at failure is {v}."],
                    "The drawing gives no minimum failure load."),
}
B2_REL = "The notice went up on the board on {p} and came down {n} days later."
B2_GREET = ["Hi all,", "Hello team,", "Hi,", "Morning all,"]
B2_CLOSE = ["Thanks,", "Best,", "Cheers,", "Regards,"]


def _b2_date(v, rng) -> str:
    d = _date(v)
    if rng.random() < 0.5:
        return f"{MONTHS[d.month - 1]} {_ordinal(d.day)}, {d.year}"
    return f"{_ordinal(d.day)} {MON3[d.month - 1]} {d.year}"


def _b2_amount(unit, v, rng) -> str:
    d = Decimal(str(v))
    if unit == "USD":
        s = _plain(d)
        whole, _, frac = s.partition(".")
        if frac:
            frac = (frac + "0")[:2] if len(frac) <= 2 else frac
            dollars = f"{int(whole):,}.{frac}"
        else:
            dollars = f"{int(whole):,}"
        return f"${dollars}" if rng.random() < 0.6 else f"{dollars} dollars"
    if unit == "kN":
        return f"{_commas(d)} kN" if rng.random() < 0.5 else f"{_commas(d)} kilonewtons"
    if unit == "units":
        return f"{_commas(d)} " + rng.choice(["units", "pieces"])
    return _commas(d)


def _rfc_date(d: date, rng) -> str:
    h, m, s = rng.randrange(7, 19), rng.randrange(60), rng.randrange(60)
    return f"{WD[d.weekday()][:3]}, {d.day} {MON3[d.month - 1]} {d.year} {h:02d}:{m:02d}:{s:02d} -0500"


B2_SEP = "=" * 72


def render_b2(doc, columns, rows, key, rng):
    subj = B2_SUBJECT.get(doc, doc)
    ticket = rng.randrange(40000, 49999)
    out = ["MAILBOX EXPORT", f"Folder: Shared/records-{doc.replace('_', '-')}",
           f"Messages in folder: {len(rows)}",
           "Each message reports one record; the same reference may be reported in more than one message.",
           ""]
    if not rows:
        out += [B2_SEP, "(folder is empty -- no messages)", B2_SEP]
        return "txt", "\n".join(out) + "\n"
    names = [c for c, *_ in columns]
    for i, r in enumerate(rows, 1):
        k = str(r[key])
        name, user, team, ext = rng.choice(B2_SENDERS[key])
        dates = [_date(r[c]) for c, kind, *_ in columns if kind == "date" and not _blank(r.get(c, ""))]
        sent = (max(dates) if dates else date(2026, 1, 5)) + timedelta(days=rng.randrange(1, 15))
        sentences = []
        handled = set()
        if doc == "lca_notices" and "posted_on" in names and "removed_on" in names:
            p, q = r.get("posted_on", ""), r.get("removed_on", "")
            if not _blank(p) and not _blank(q):
                gap = (_date(q) - _date(p)).days
                if 1 < gap <= 60 and rng.random() < 0.35:
                    sentences.append(B2_REL.format(p=_b2_date(p, rng), n=gap))
                    handled |= {"posted_on", "removed_on"}
        for c, kind, unit, _lab in columns[1:]:
            if c in handled:
                continue
            v = r.get(c, "")
            present, absent = B2_SENT[c]
            if _blank(v):
                sentences.append(absent)
                continue
            if kind == "date":
                s = _b2_date(v, rng)
            elif kind == "amount":
                s = _b2_amount(unit, v, rng)
            else:
                s = str(v)
            sentences.append(rng.choice(present).format(v=s))
        if len(sentences) > 2:
            head, tail = sentences[:1], sentences[1:]
            rng.shuffle(tail)
            sentences = head + tail
        body = " ".join(sentences) if sentences else "Nothing further to add on this one."
        out += [B2_SEP,
                f"From: {name} <{user}@corp.example>",
                f"To: records-desk@corp.example",
                f"Date: {_rfc_date(sent, rng)}",
                f"Subject: [TKT-{ticket}] {subj} - {k}",
                f"Message-ID: <{rng.randrange(10**8, 10**9)}.{i}@mail.corp.example>",
                "",
                rng.choice(B2_GREET),
                "",
                rng.choice(B2_ID_INTRO[key]).format(k=k) + " " + body,
                "",
                rng.choice(B2_CLOSE),
                name,
                f"{team} | {ext}",
                "This message may contain confidential information. If received in error, delete it.",
                ""]
    out.append(B2_SEP)
    return "txt", "\n".join(out) + "\n"


LAYOUTS = {"B1": render_b1, "B2": render_b2}


# =============================================================== self-test readers
def _parse_b1_date(s: str) -> str:
    m = re.fullmatch(r"(\w+)\., (\S+) (\d{1,2}), (\d{4})", s)
    assert m and m.group(1) + "." in WD_AP, s
    d = date(int(m.group(4)), AP_MON.index(m.group(2)) + 1, int(m.group(3)))
    assert WD_AP[d.weekday()] == m.group(1) + ".", s
    return d.isoformat()


def _parse_b2_date(s: str) -> str:
    m = re.fullmatch(r"([A-Z][a-z]+) (\d{1,2})(?:st|nd|rd|th), (\d{4})", s)
    if m:
        return date(int(m.group(3)), MONTHS.index(m.group(1)) + 1, int(m.group(2))).isoformat()
    m = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th) ([A-Z][a-z]{2}) (\d{4})", s)
    assert m, s
    return date(int(m.group(3)), MON3.index(m.group(2)) + 1, int(m.group(1))).isoformat()


def _num(s: str) -> Decimal:
    return Decimal(s.replace(",", ""))


def _parse_b1_amount(unit, s) -> Decimal:
    if unit == "USD":
        m = re.fullmatch(r"USD ([\d,]+(?:\.\d+)?)", s)
    elif unit == "kN":
        m = re.fullmatch(r"([\d,]+(?:\.\d+)?) kN", s)
    else:
        m = re.fullmatch(r"([\d,]+(?:\.\d+)?) pcs", s)
    assert m, s
    return _num(m.group(1))


B2_DATE_RE = r"(?:[A-Z][a-z]+ \d{1,2}(?:st|nd|rd|th), \d{4}|\d{1,2}(?:st|nd|rd|th) [A-Z][a-z]{2} \d{4})"
B2_AMT_RE = {"USD": r"(?:\$[\d,]+(?:\.\d+)?|[\d,]+(?:\.\d+)? dollars)",
             "kN": r"[\d,]+(?:\.\d+)? (?:kN|kilonewtons)",
             "units": r"[\d,]+(?:\.\d+)? (?:units|pieces)"}


def _parse_b2_amount(s) -> Decimal:
    return _num(re.match(r"\$?([\d,]+(?:\.\d+)?)", s).group(1))


def read_b1(txt, columns):
    """Return a list of {column: rendered string or None (blank shown)} per sheet."""
    inv = {B1_LABELS[c]: c for c, *_ in columns}
    recs = []
    for art in re.findall(r"<article class=\"sheet\".*?</article>", txt, flags=re.S):
        rec = {}
        for th, td in re.findall(r"<tr><th>(.*?)</th><td[^>]*>(.*?)</td></tr>", art):
            c = inv[html.unescape(th)]
            val = html.unescape(re.sub(r"</?strong>", "", td))
            rec[c] = None if td == B1_NONE else val
        recs.append(rec)
    return recs


def read_b2(txt, columns, key):
    msgs = txt.split(B2_SEP + "\nFrom: ")[1:]
    recs = []
    for m in msgs:
        m = m.split("\n" + B2_SEP)[0]
        body = m.split("\n\n", 3)[2] if m.count("\n\n") >= 3 else m
        rec = {"__text": m, "__body": body}
        rel = re.search(r"The notice went up on the board on (" + B2_DATE_RE + r") and came down (\d+) days later\.", body)
        if rel:
            p = _parse_b2_date(rel.group(1))
            rec["posted_on"] = p
            rec["removed_on"] = (date.fromisoformat(p) + timedelta(days=int(rel.group(2)))).isoformat()
        for c, kind, unit, _lab in columns[1:]:
            if c in rec:
                continue
            present, absent = B2_SENT[c]
            if absent in body:
                rec[c] = None
                continue
            vre = B2_DATE_RE if kind == "date" else B2_AMT_RE.get(unit, r".+?") if kind == "amount" else r".+?"
            for t in present:
                pre, suf = t.split("{v}")
                mm = re.search(re.escape(pre) + "(" + vre + ")" + re.escape(suf), body)
                if mm:
                    s = mm.group(1)
                    if kind == "date":
                        rec[c] = _parse_b2_date(s)
                    elif kind == "amount":
                        rec[c] = _parse_b2_amount(s)
                    else:
                        rec[c] = s
                    break
        recs.append(rec)
    return recs


def _selftest() -> int:
    import sys
    sys.path.insert(0, "/Users/roydi/Desktop/nofalsegreen")
    from nofalsegreen import study13 as s13
    from nofalsegreen import study13_heldout as h

    fails = []

    def chk(cond, msg):
        if not cond:
            fails.append(msg)

    # label distinctness against canonical names, plain labels, L2 headers, L4-L6 phrasings
    bad = set()
    for docs in s13.DOCS.values():
        for cols in docs.values():
            for c, _k, _u, lab in cols:
                bad |= {c.lower(), c.replace("_", " ").lower(), lab.lower(), s13.L2_HEADERS[c].lower()}
    for c, (_sec, k4) in h.L4_KEYS.items():
        bad |= {k4.lower(), k4.replace("_", " ").lower()}
    for c, (h6, leg) in h.L6_COLS.items():
        bad |= {h6.lower(), leg.lower()}
    l5 = set()
    for c, (pres, absent) in h.L5_PHRASES.items():
        l5 |= {p.lower() for p in pres} | {absent.lower()}
    for c, lab in B1_LABELS.items():
        chk(lab.lower() not in bad, f"B1 label {lab!r} for {c} collides")
    for c, (pres, absent) in B2_SENT.items():
        for p in pres + [absent]:
            chk(p.lower() not in l5 and p.lower().replace("{v}", "").strip(" .") not in bad,
                f"B2 phrase {p!r} collides")

    for name, fn in LAYOUTS.items():
        ext, txt = fn("payments", s13.DOCS["purchasing"]["payments"], [], "po_id", random.Random(1))
        chk(bool(txt.strip()), f"{name} empty doc")
        chk((len(read_b1(txt, s13.DOCS["purchasing"]["payments"])) if name == "B1"
             else len(read_b2(txt, s13.DOCS["purchasing"]["payments"], "po_id"))) == 0, f"{name} empty count")

    samples = {}
    n_docs = n_rows = n_blank = n_vals = n_rel = 0
    for wf in s13.WORKFLOWS:
        key = s13.KEY[wf]
        for seed in (1401, 1402, 1403, 1404):
            p = s13.make_packet(wf, seed)
            for doc, cols in s13.DOCS[wf].items():
                rows = p.tables[doc]
                n_docs += 1
                n_rows += len(rows)
                for name, fn in LAYOUTS.items():
                    seed_s = f"study14-render-{name}-{p.packet_id}-{doc}"
                    ext, txt = fn(doc, cols, rows, key, random.Random(seed_s))
                    chk(fn(doc, cols, rows, key, random.Random(seed_s)) == (ext, txt),
                        f"{name} nondeterministic {doc}")
                    tag = f"{name} {wf}-{seed} {doc}"
                    if name == "B1":
                        recs = read_b1(txt, cols)
                        blocks = re.findall(r"<article class=\"sheet\".*?</article>", txt, flags=re.S)
                    else:
                        recs = read_b2(txt, cols, key)
                        blocks = [x["__text"] for x in recs]
                    chk(len(recs) == len(rows), f"{tag}: {len(recs)} records != {len(rows)} rows")
                    if len(recs) != len(rows):
                        continue
                    for r, rec, b in zip(rows, recs, blocks):
                        chk(str(r[key]) in b, f"{tag}: id {r[key]} missing")
                        if name == "B1":
                            chk(rec.get(key) == str(r[key]), f"{tag}: id cell")
                        for c, kind, unit, _lab in cols[1:]:
                            v = r.get(c, "")
                            got = rec.get(c, None)
                            if _blank(v):
                                n_blank += 1
                                chk(got is None, f"{tag}: blank {c} rendered as {got!r}")
                                if name == "B2":
                                    chk(B2_SENT[c][1] in rec["__body"], f"{tag}: blank {c} not stated")
                                continue
                            n_vals += 1
                            if got is None:
                                fails.append(f"{tag}: {c} value {v!r} not recovered")
                                continue
                            if kind == "date":
                                iso = _parse_b1_date(got) if name == "B1" else got
                                chk(iso == str(v), f"{tag}: {c} {got!r} != {v}")
                            elif kind == "amount":
                                amt = _parse_b1_amount(unit, got) if name == "B1" else got
                                chk(amt == Decimal(str(v)), f"{tag}: {c} {got!r} != {v}")
                            else:
                                chk(got == str(v), f"{tag}: text {c} {got!r} != {v!r}")
                        if name == "B2" and "came down" in rec["__body"]:
                            n_rel += 1
                    if seed == 1401 and doc in ("lca_notices", "invoices", "lab_certificates"):
                        samples[(name, wf)] = (doc, txt)

    for name in LAYOUTS:
        for wf in s13.WORKFLOWS:
            doc, txt = samples[(name, wf)]
            lines = txt.splitlines()
            if name == "B1":
                start = next(i for i, l in enumerate(lines) if l.startswith("<header>"))
                lines = lines[start:start + 26]
            else:
                lines = lines[:22]
            print(f"===== {name} / {wf} / {doc} (seed 1401) =====")
            print("\n".join(lines))
            print()
    print(f"documents: {n_docs} per layout; rows: {n_rows}; blank cells: {n_blank} per layout; "
          f"non-blank dates/amounts/text checked: {n_vals} per layout; B2 relative-date notices: {n_rel}")
    if fails:
        print(f"SELFTEST FAILED: {len(fails)} problems")
        for f in fails[:40]:
            print("  -", f)
        return 1
    print("SELFTEST PASSED")
    return 0


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)

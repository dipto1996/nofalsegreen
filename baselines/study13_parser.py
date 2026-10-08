#!/usr/bin/env python3
"""Rule-based extraction baseline for Study 13 (standard library only; no model, no network).

    extract(workflow, packet_dir) -> {"<rule_id>::<entity>": {fact_name: (value, document) | "ABSENT" | "CONFLICT"}}

How it works
------------
1. Every file in the packet is turned into *observations* (entity, label, raw value) by a
   format-specific reader: delimited tables (CSV/TSV/pipe/semicolon, wide, long
   "entity/field/value" and transposed), JSON / JSON-lines (records, dicts keyed by entity,
   columnar and pandas-style orients, field/value pairs, {value, unit} objects), XML,
   HTML (tables, definition lists, text), XLSX and DOCX (zip + XML), Markdown / ASCII /
   fixed-width tables in text, key-value blocks, YAML-like and INI-like text and free prose.
   In text, each date / amount span becomes an observation whose label is the words
   around it; entities are attached by block, record marker, sentence and position.
2. The file stem names the document (fuzzy-matched to the canonical document names).
3. Each observation is mapped to a canonical column of that document by
   (a) the value's kind (date / amount) and unit class (USD / units / kN),
   (b) a concept score of its label against the column (synonym table + stems, built from
       the canonical names, the plain-language labels in study13.DOCS and common business
       vocabulary), and (c) when the label says nothing, the only compatible column of the
       document, or column order.
4. Values are normalised: many date formats (ISO, numeric D/M/Y vs M/D/Y decided from the
   packet's own evidence, month names in six languages, ordinals, 2-digit years, compact
   yyyymmdd, Excel serials, epoch), numbers with US / European / Swiss / spaced grouping,
   multipliers (k, thousand, M) and units (cents, N, daN, MN, kgf, lbf, kip, tonne-force,
   dozen), taken from the value or from the label/header/unit column. Non-USD currencies
   are not converted (abstain).
5. The spec's priority semantics are applied: the first listed source document that holds
   a value for the entity decides; disagreeing values there -> CONFLICT; a non-blank value
   that cannot be read in the deciding document -> ABSENT (abstain, no fall-through).

CLI: python3 baselines/study13_parser.py --dev   (verdict + slot accuracy on parser_dev)
"""

from __future__ import annotations

import csv
import difflib
import io
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from nofalsegreen.study13 import CONTRACTS, DOCS, KEY, RULES, verdict_from_facts  # noqa: E402

try:
    from nofalsegreen.study13 import PREFIX
except ImportError:  # pragma: no cover
    PREFIX = {"workforce": "E", "purchasing": "PO", "engineering": "P"}

# --------------------------------------------------------------------------- text basics
_TRANS = {0xA0: " ", 0x2007: " ", 0x2009: " ", 0x202F: " ", 0x200B: "", 0xFEFF: "",
          0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-", 0x2014: "-", 0x2015: "-", 0x2212: "-",
          0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"', 0x2032: "'"}


def norm(s) -> str:
    return str(s).translate(_TRANS)


BLANKS = {"", "-", "--", "---", "n/a", "na", "n.a.", "none", "null", "nil", "nan", "nat", "?", "tbd", "tba",
          "unknown", "not recorded", "not available", "missing", "blank", "empty", "pending", "(blank)",
          "(none)", "(empty)", "not provided", "no value", "no data", "undefined", "x", "--/--/----"}


def is_blank(raw) -> bool:
    if raw is None:
        return True
    s = norm(raw).strip().strip('"\'').strip()
    return s.lower() in BLANKS


# --------------------------------------------------------------------------- entities
_ALIASES = {"workforce": ["EMP", "EE"], "purchasing": ["P.O."], "engineering": ["PN", "PART"]}


class Ctx:
    def __init__(self, wf: str):
        self.wf = wf
        self.prefix = PREFIX[wf]
        alts = sorted({a.upper() for a in [self.prefix] + _ALIASES.get(wf, [])}, key=len, reverse=True)
        multi = [a for a in alts if len(a.replace(".", "")) > 1]
        single = [a for a in alts if len(a.replace(".", "")) == 1]
        pats = []
        if multi:
            pats.append(r"(?:%s)(?:\s?[-_#:.]\s?|\s)?" % "|".join(re.escape(a) for a in multi))
        if single:
            pats.append(r"(?:%s)[-_#]?" % "|".join(re.escape(a) for a in single))
        self.re = re.compile(r"(?<![A-Za-z0-9])(?:%s)(\d{3,7})(?![\d])" % "|".join(pats), re.I)
        self.digits_len = Counter()

    def canon(self, digits: str) -> str:
        return f"{self.prefix}-{digits}"

    def find(self, s) -> list:
        """[(start, end, entity)] for every entity id mentioned in s."""
        out = []
        for m in self.re.finditer(norm(s)):
            out.append((m.start(), m.end(), self.canon(m.group(1))))
            self.digits_len[len(m.group(1))] += 1
        return out

    def ents(self, s) -> list:
        seen = []
        for _, _, e in self.find(s):
            if e not in seen:
                seen.append(e)
        return seen

    def cell_ent(self, s):
        e = self.ents(s)
        return e[0] if len(e) == 1 else None

    def digit_key(self, s):
        s = norm(s).strip()
        if re.fullmatch(r"\d{3,7}", s) and (not self.digits_len or len(s) in self.digits_len):
            return self.canon(s)
        return None


# --------------------------------------------------------------------------- vocabulary
_SPEC = {
    "date": {1: "date dated dt day on when time timestamp ts"},
    "expir": {3: "expires expire expiry expiration expiring expired exp expiries lapse lapses lapsing",
              2: "valid validity until thru through end ends ending"},
    "card": {1: "card ead cards"},
    "auth": {1: "authorization authorisation authorizations auth permit work employment document i9 visa"},
    "complet": {3: "completed complete completion done finished performed reverified conducted executed verified",
                2: "reverification reverify reverif reverifications signed"},
    "post": {3: "posted", 2: "post start started starting begin began beginning displayed display published "
                             "put hung placed first opened up from",
             1: "posting postings"},
    "remov": {3: "removed removal remove takendown takedown withdrawn unposted",
              2: "taken down end ended ending until through thru last pulled closed stop stopped to off"},
    "file": {3: "filed filing file submitted submission submit lodged", 1: "lca eta"},
    "dolrec": {3: "receipt receipted acknowledged acknowledgement acknowledgment ack", 2: "dol received stamped"},
    "amount": {3: "amount amt total value sum price cost charge charged gross net usd dollars dollar money $",
               1: "billed bill"},
    "qty": {3: "qty quantity quantities units unit count pcs pieces items volume", 1: "number num"},
    "invoic": {2: "invoice invoiced invoicing inv billed bill billing"},
    "order": {2: "order ordered po purchase", 1: "contract committed authorized approved"},
    "due": {3: "due payable deadline maturity", 1: "terms latest by owed"},
    "receiv": {3: "received receive receiving delivered delivery arrived arrival grn",
               2: "receipt goods accepted inbound"},
    "scan": {3: "scan scanned scanning", 1: "warehouse logged checked"},
    "paid": {3: "paid payment payments settled settlement remitted remittance disbursed",
             1: "pay cleared transferred wired"},
    "calibr": {3: "calibrated calibration calibrate calib cal recalibrated", 1: "rig"},
    "test": {3: "tested test testing", 1: "trial examined"},
    "measur": {3: "measured measurement measure observed actual achieved",
               2: "failure failed break breaking ultimate peak recorded"},
    "certif": {3: "certified certificate cert certification attested", 1: "lab laboratory"},
    "minimum": {3: "min minimum required requirement specified threshold",
                2: "spec specification rated floor allowable design"},
    "load": {2: "load force capacity strength kn newton newtons kilonewton kilonewtons"},
    "meta": {3: "record row line index idx seq sequence page entry rec serial generated printed exported "
                "created updated modified retrieved report extracted batch source sheet version"},
    "id": {2: "id identifier no nr num number ref reference code key #"},
    "entity": {2: "employee emp worker staff person personnel ee part component sku"},
}
SYN: dict = {}
for _c, _groups in _SPEC.items():
    for _w, _words in _groups.items():
        for _t in _words.split():
            SYN.setdefault(_t, {})
            SYN[_t][_c] = max(_w, SYN[_t].get(_c, 0))
_STEMS = [("expir", "expir", 3), ("calibr", "calibr", 3), ("certif", "certif", 3), ("reverif", "complet", 2),
          ("invoic", "invoic", 2), ("remov", "remov", 3), ("measur", "measur", 3), ("quantit", "qty", 3),
          ("receiv", "receiv", 3), ("receipt", "dolrec", 3), ("complet", "complet", 3), ("submi", "file", 3),
          ("acknowl", "dolrec", 3), ("deliver", "receiv", 3), ("withdr", "remov", 3), ("scann", "scan", 3),
          ("settl", "paid", 3), ("remit", "paid", 3), ("disburs", "paid", 3), ("minim", "minimum", 3),
          ("specif", "minimum", 2), ("requir", "minimum", 3), ("authori", "auth", 1), ("employ", "entity", 2)]

COLPROF = {
    "expires_on": {"expir": 1, "auth": .3, "date": .1},
    "card_expiry": {"expir": 1, "card": .3, "date": .1},
    "completed_on": {"complet": 1, "date": .1},
    "posted_on": {"post": 1},
    "removed_on": {"remov": 1},
    "filed_on": {"file": 1, "date": .1},
    "receipt_date": {"dolrec": 1, "file": .3, "date": .1},
    "po_amount": {"amount": 1, "order": .5},
    "invoice_amount": {"amount": 1, "invoic": .2},
    "invoiced_qty": {"qty": 1, "invoic": .2},
    "due_on": {"due": 1, "date": .1},
    "received_qty": {"qty": 1, "receiv": .2},
    "received_on": {"receiv": 1, "date": .3},
    "scan_date": {"scan": 1, "date": .3},
    "paid_on": {"paid": 1, "date": .3},
    "calibrated_on": {"calibr": 1, "date": .3},
    "tested_on": {"test": 1, "date": .3},
    "measured_load_kn": {"measur": 1, "load": .5},
    "test_date": {"test": 1, "date": .3},
    "certified_load_kn": {"certif": 1, "load": .5, "measur": .5},
    "min_load_kn": {"minimum": 1, "load": .5},
}
_SCORE_CONCEPTS = {c for prof in COLPROF.values() for c in prof if c != "date"}


def tokens(label) -> list:
    s = norm(label)
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s).lower()
    s = re.sub(r"(?<=[a-z])-(?=[a-z])", "", s)
    s = s.replace("taken down", "takendown").replace("take down", "takedown")
    toks = re.findall(r"[a-z]+|\d+|[$#]", s)
    out = []
    for t in toks:   # "re verified" / "re_verification" -> one word
        if out and out[-1] == "re" and t.isalpha():
            out[-1] = "re" + t
        else:
            out.append(t)
    return out


_VEC_CACHE: dict = {}


def concepts(label) -> dict:
    key = str(label)
    if key in _VEC_CACHE:
        return _VEC_CACHE[key]
    vec: dict = {}
    for t in tokens(label):
        cands = SYN.get(t)
        if cands is None:
            cands = {}
            for p, c, w in _STEMS:
                if t.startswith(p):
                    cands[c] = max(w, cands.get(c, 0))
            if not cands and len(t) > 3 and t.endswith("s") and t[:-1] in SYN:
                cands = SYN[t[:-1]]
        for c, w in cands.items():
            vec[c] = max(w, vec.get(c, 0))
    _VEC_CACHE[key] = vec
    return vec


def col_score(label, col) -> float:
    vec = concepts(label)
    return sum(vec.get(c, 0) * w for c, w in COLPROF.get(col, {}).items())


def is_meta_label(label) -> bool:
    vec = concepts(label)
    if vec.get("meta", 0) <= 0:
        return False
    return not any(vec.get(c, 0) > 0 for c in _SCORE_CONCEPTS)


def is_key_label(label) -> bool:
    vec = concepts(label)
    return vec.get("id", 0) > 0 and not any(vec.get(c, 0) > 0 for c in _SCORE_CONCEPTS - {"order"})


# --------------------------------------------------------------------------- dates
_MONTH_NAMES = {
    1: "january jan janvier janv enero ene januar jänner jaenner gennaio gen januari janeiro",
    2: "february feb fevrier février fev févr febrero februar febbraio februari fevereiro",
    3: "march mar mars marzo märz maerz mrz maart março marco",
    4: "april apr avril avr abril aprile",
    5: "may mai mayo maggio mag mei maio",
    6: "june jun juin junio juni giugno giu junho",
    7: "july jul juillet juil julio juli luglio lug julho",
    8: "august aug aout août agosto ago augustus",
    9: "september sep sept septembre septiembre setiembre settembre set setembro",
    10: "october oct octobre octubre oktober okt ottobre ott outubro out",
    11: "november nov novembre noviembre novembro",
    12: "december dec decembre décembre diciembre dic dezember dez dicembre dezembro",
}
MONTHS = {}
for _n, _ws in _MONTH_NAMES.items():
    for _w in _ws.split():
        MONTHS[_w] = _n
_MW = r"[A-Za-zÀ-ÿ]{3,10}\.?"
_DATE_RES = [
    ("iso", re.compile(r"(?<!\d)(?<!\d\.)(\d{4})([-/.])(\d{1,2})\2(\d{1,2})(?![\d])(?:[T ]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?")),
    ("dmy", re.compile(r"(?<![\w])(\d{1,2})(?:st|nd|rd|th)?\.?(?:\s+of)?[\s\-/]*(" + _MW + r")[\s\-/.,]*(\d{4}|'\d{2}|\d{2})(?![\d:])")),
    ("mdy", re.compile(r"(?<![\w])(" + _MW + r")[\s\-/.]*(\d{1,2})(?:st|nd|rd|th)?,?[\s\-/,]+(\d{4}|'\d{2})(?![\d])")),
    ("ymd", re.compile(r"(?<![\d])(\d{4})[\s\-/.,]+(" + _MW + r")[\s\-/.,]+(\d{1,2})(?![\d])")),
    ("compact", re.compile(r"(?<!\d)(?<!\d[.,])((?:19|20)\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?![\d.,])")),
    ("num", re.compile(r"(?<!\d)(?<!\d[.\-/])(\d{1,2})([-/.])(\d{1,2})\2(\d{4}|\d{2})(?![\d])(?![.\-/]\d)")),
]


def _month(w):
    w = w.lower().rstrip(".")
    return MONTHS.get(w)


def _year(y: str) -> int:
    y = y.lstrip("'")
    v = int(y)
    if len(y) == 2:
        v += 2000 if v < 70 else 1900
    return v


def _mk(y, m, d):
    try:
        return date(y, m, d)
    except (ValueError, TypeError):
        return None


def find_dates(s: str) -> list:
    """[(start, end, kind, groups)] non-overlapping date spans (raw, not yet interpreted)."""
    s = norm(s)
    found = []
    for kind, rx in _DATE_RES:
        for m in rx.finditer(s):
            g = m.groups()
            if kind in ("dmy", "mdy", "ymd"):
                mw = g[1] if kind in ("dmy", "ymd") else g[0]
                if _month(mw) is None:
                    continue
            if any(not (m.end() <= a or m.start() >= b) for a, b, _, _ in found):
                continue
            found.append((m.start(), m.end(), kind, g))
    out = []
    for a, b, kind, g in sorted(found):   # a leading weekday ("Tuesday, 2 June 2026") belongs to the date
        w = _WEEKDAY.search(s[:a])
        out.append((w.start() if w else a, b, kind, g))
    return out


_WEEKDAY = re.compile(r"(?<![A-Za-z])(?:mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)(?:day|nesday|rsday|urday|sday)?\.?,?\s*(?:the\s+)?$",
                      re.I)


def interpret_date(kind, g, conv) -> date | None:
    if kind == "iso":
        return _mk(int(g[0]), int(g[2]), int(g[3]))
    if kind == "dmy":
        return _mk(_year(g[2]), _month(g[1]), int(g[0]))
    if kind == "mdy":
        return _mk(_year(g[2]), _month(g[0]), int(g[1]))
    if kind == "ymd":
        return _mk(int(g[0]), _month(g[1]), int(g[2]))
    if kind == "compact":
        return _mk(int(g[0]), int(g[1]), int(g[2]))
    a, sep, b, y = int(g[0]), g[1], int(g[2]), _year(g[3])
    if a > 12 and b <= 12:
        return _mk(y, b, a)
    if b > 12 and a <= 12:
        return _mk(y, a, b)
    order = conv.get(sep) or ("DMY" if sep == "." else "MDY")
    return _mk(y, b, a) if order == "DMY" else _mk(y, a, b)


def date_conventions(raws) -> dict:
    """Per separator, D/M/Y vs M/D/Y from unambiguous evidence in the same file/packet."""
    ev = defaultdict(Counter)
    for r in raws:
        for _, _, kind, g in find_dates(r):
            if kind == "num":
                a, b = int(g[0]), int(g[2])
                if a > 12 and b <= 12:
                    ev[g[1]]["DMY"] += 1
                elif b > 12 and a <= 12:
                    ev[g[1]]["MDY"] += 1
    return {sep: c.most_common(1)[0][0] for sep, c in ev.items() if c}


def serial_to_date(x: float):
    if 20000 <= x <= 80000 and float(x).is_integer():          # Excel serial (1900 system)
        return date(1899, 12, 30) + timedelta(days=int(x))
    if 3e8 <= x <= 4.2e9:                                      # epoch seconds
        return datetime.fromtimestamp(x, tz=timezone.utc).date()
    if 3e11 <= x <= 4.2e12:                                    # epoch milliseconds
        return datetime.fromtimestamp(x / 1000, tz=timezone.utc).date()
    return None


# --------------------------------------------------------------------------- numbers and units
# unit token -> (class, factor to the class's canonical unit); factor None = not convertible
UNITS = {
    "usd": ("USD", 1), "$": ("USD", 1), "us$": ("USD", 1), "dollar": ("USD", 1), "dollars": ("USD", 1),
    "kusd": ("USD", 1e3), "usdk": ("USD", 1e3), "musd": ("USD", 1e6), "usdm": ("USD", 1e6),
    "cents": ("USD", 0.01), "cent": ("USD", 0.01), "¢": ("USD", 0.01),
    "eur": ("USD", None), "€": ("USD", None), "euro": ("USD", None), "euros": ("USD", None),
    "gbp": ("USD", None), "£": ("USD", None), "cad": ("USD", None), "chf": ("USD", None), "jpy": ("USD", None),
    "units": ("units", 1), "unit": ("units", 1), "pcs": ("units", 1), "pc": ("units", 1), "pieces": ("units", 1),
    "piece": ("units", 1), "ea": ("units", 1), "each": ("units", 1), "items": ("units", 1), "item": ("units", 1),
    "nos": ("units", 1), "qty": ("units", 1), "dozen": ("units", 12), "dz": ("units", 12), "doz": ("units", 12),
    "kn": ("kN", 1), "kilonewton": ("kN", 1), "kilonewtons": ("kN", 1),
    "n": ("kN", 0.001), "newton": ("kN", 0.001), "newtons": ("kN", 0.001),
    "meganewton": ("kN", 1000), "meganewtons": ("kN", 1000),
    "dan": ("kN", 0.01), "decanewton": ("kN", 0.01), "decanewtons": ("kN", 0.01),
    "kgf": ("kN", 0.00980665), "kp": ("kN", 0.00980665), "kilogram-force": ("kN", 0.00980665),
    "lbf": ("kN", 0.0044482216152605), "lb": ("kN", 0.0044482216152605), "lbs": ("kN", 0.0044482216152605),
    "pound-force": ("kN", 0.0044482216152605), "pounds-force": ("kN", 0.0044482216152605),
    "kip": ("kN", 4.4482216152605), "kips": ("kN", 4.4482216152605), "klbf": ("kN", 4.4482216152605),
    "tf": ("kN", 9.80665), "tonne-force": ("kN", 9.80665), "tonnes-force": ("kN", 9.80665),
}
MULTS = {"k": 1e3, "thousand": 1e3, "thousands": 1e3, "m": 1e6, "mm": 1e6, "mn": 1e6, "mio": 1e6,
         "million": 1e6, "millions": 1e6, "bn": 1e9, "billion": 1e9, "000s": 1e3, "'000": 1e3, "000": 1e3}
_CUR_PREFIX = re.compile(r"(US\$|USD|EUR|GBP|CAD|CHF|\$|€|£)\s?$")
_NUM_RE = re.compile(r"(?<!\d)(?<!\d[.,])[-+]?\d+(?:[,.' ]\d{3}(?![\d]))*(?:[.,]\d+)?(?:[eE][-+]?\d+)?")


class Amount:
    __slots__ = ("num", "unit", "mult", "explicit", "decimals", "raw")

    def __init__(self, num, unit, mult, explicit, decimals, raw):
        self.num, self.unit, self.mult, self.explicit, self.decimals, self.raw = num, unit, mult, explicit, decimals, raw

    def uclass(self):
        return UNITS[self.unit][0] if self.unit else None


def interpret_number(tok: str, eu: bool):
    t = tok.replace("'", "").replace(" ", "")
    neg = t.startswith("-")
    t = t.lstrip("+-")
    if "e" in t.lower():
        try:
            return (-1 if neg else 1) * float(t.replace(",", "")), 0
        except ValueError:
            return None
    has_c, has_d = "," in t, "." in t
    if has_c and has_d:
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        t = t.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif has_c:
        parts = t.split(",")
        if len(parts) > 2 or (len(parts[-1]) == 3 and not eu):
            t = t.replace(",", "")
        else:
            t = t.replace(",", ".")
    elif has_d:
        parts = t.split(".")
        if len(parts) > 2 or (len(parts[-1]) == 3 and eu):
            t = t.replace(".", "")
    try:
        v = float(t)
    except ValueError:
        return None
    decimals = len(t.split(".")[1]) if "." in t else 0
    return (-v if neg else v), decimals


def number_convention(raws) -> bool:
    """True when the packet writes numbers European-style (1.234,56)."""
    eu = us = dotted_dates = 0
    for r in raws:
        s = norm(r)
        found = find_dates(s)
        dotted_dates += sum(1 for _, _, k, g in found if k == "num" and g[1] == ".")
        masked = _mask(s, [(a, b) for a, b, _, _ in found])
        for m in _NUM_RE.finditer(masked):
            t = m.group(0).replace(" ", "")
            if re.search(r"\d\.\d{3},\d", t) or re.fullmatch(r"[-+]?\d+,\d{1,2}", t) \
                    or re.search(r"\d\.\d{3}\.\d{3}", t):
                eu += 1
            elif re.search(r"\d,\d{3}\.\d", t) or re.fullmatch(r"[-+]?\d+\.\d{1,2}", t) \
                    or re.search(r"\d,\d{3},\d{3}", t):
                us += 1
    if eu == us == 0:   # no direct evidence: day.month.year dates indicate a European locale
        return dotted_dates > 0
    return eu > us


def _mask(s, spans, ch=" "):
    s = list(s)
    for a, b in spans:
        for i in range(a, min(b, len(s))):
            s[i] = ch
    return "".join(s)


def find_amounts(s: str, eu: bool) -> list:
    """[(start, end, Amount)] numbers with their currency / multiplier / unit."""
    out = []
    for m in _NUM_RE.finditer(s):
        a, b = m.start(), m.end()
        if a > 0 and (s[a - 1].isalpha() and not _CUR_PREFIX.search(s[:a])):
            continue
        tok = m.group(0).rstrip(" ")
        b = a + len(tok)
        r = interpret_number(tok, eu)
        if r is None:
            continue
        v, dec = r
        unit, mult, explicit = None, 1.0, False
        pm = _CUR_PREFIX.search(s[max(0, a - 6):a])
        if pm:
            unit, explicit = pm.group(1).lower(), True
            a = a - (len(s[max(0, a - 6):a]) - pm.start())
        rest = s[b:]
        mm = re.match(r"\s?(thousands?|millions?|billion|mio|mn|bn|k|K|M|MM)(?![A-Za-z])", rest)
        if mm and not re.match(r"\s?(MN|mN)\b", rest):
            mult, explicit = MULTS[mm.group(1).lower()], True
            b += mm.end()
            rest = s[b:]
        um = re.match(r"\s?(US\$|\$|€|£|¢|[A-Za-z][A-Za-z\-]*)", rest)
        if um:
            w = um.group(1)
            wl = w.lower()
            if w == "MN":
                unit, explicit = "meganewton", True
                b += um.end()
            elif wl in UNITS and not (wl in ("n",) and w == "N" and re.match(r"\s?N/A", rest)):
                if unit is None or UNITS[unit][0] == UNITS[wl][0]:
                    unit, explicit = wl, True
                b += um.end()
        out.append((a, b, Amount(v, unit, mult, explicit, dec, s[a:b])))
    return out


_DECL = re.compile(r"""(?:\b(?:in|unit|units|uom|currency|ccy)\b["']?\s*[:=]?\s*["']?)
    ((?:thousands?|millions?)\s+of\s+|'000\s+|000s\s+)?
    (US\$|\$|€|£|[A-Za-z]+(?:-force)?)
    (\s*(?:thousands?|millions?|'000|000s)\b)?""", re.X | re.I)


def declared_units(text: str) -> dict:
    """Units a document declares for its bare numbers: {"kN": ("n", 1.0), "USD": ("usd", 1000.0)}."""
    found = defaultdict(set)
    for m in _DECL.finditer(norm(text)):
        w = m.group(2)
        wl = w.lower()
        mult = 1.0
        for g in (m.group(1), m.group(3)):
            if g:
                g = g.strip().lower()
                mult *= 1e6 if g.startswith("million") else 1e3
        if w == "MN":
            wl = "meganewton"
        elif wl == "n" and w != "N":
            continue
        if wl in UNITS:
            found[UNITS[wl][0]].add((wl, mult))
        elif wl in ("thousand", "thousands", "millions", "million") and not m.group(1):
            found["USD"].add(("usd", 1e3 if wl.startswith("thousand") else 1e6))
    return {cls: next(iter(v)) for cls, v in found.items() if len(v) == 1}


def _meta_units(node, out, depth=0, ctx=None):
    """(key, value) scalars of entity-free parts of a JSON tree, for unit declarations."""
    if depth > 4:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if _scalar(v):
                out.append((str(k), _sval(v)))
            elif not _has_ent(v, ctx):
                _meta_units(v, out, depth + 1, ctx)
            elif isinstance(v, dict):
                _meta_units({kk: vv for kk, vv in v.items() if not _has_ent(vv, ctx)}, out, depth + 1, ctx)


def _has_ent(node, ctx):
    found = set()
    _subtree_ents(node, ctx, found, 0)
    return bool(found)


def json_declared_units(obj, ctx) -> dict:
    pairs = []
    if isinstance(obj, dict):
        _meta_units({k: v for k, v in obj.items() if not _has_ent(v, ctx) or _scalar(v)}, pairs, 0, ctx)
    found, scale = defaultdict(set), None
    for k, v in pairs:
        vl = v.strip().lower()
        if v.strip() == "MN":
            vl = "meganewton"
        if vl in UNITS and len(vl) <= 20:
            found[UNITS[vl][0]].add(vl)
        elif vl in ("thousand", "thousands", "k", "000s", "'000", "million", "millions", "m") and \
                re.search(r"scale|multipl|factor|unit|denominat|in", k.lower()):
            scale = 1e6 if vl.startswith("m") else 1e3
    res = {cls: (next(iter(v)), 1.0) for cls, v in found.items() if len(v) == 1}
    if scale:
        res["USD"] = (res.get("USD", ("usd", 1.0))[0], scale)
    return res


def label_unit(label):
    """Unit / multiplier announced by a header: 'Load (N)', 'Amount [USD 000s]', 'load_lbf'."""
    s = norm(label)
    unit, mult = None, 1.0
    parts = re.findall(r"[\(\[{]([^\)\]}]*)[\)\]}]", s)
    m = re.search(r"\bin\s+([A-Za-z$€£' ]+)$", s)
    if m:
        parts.append(m.group(1))
    tail = re.split(r"[_\s]+", s.strip())
    if len(tail) > 1:
        parts.append(tail[-1])
    for p in parts:
        for w in re.findall(r"US\$|\$|€|£|¢|'000|000s|[A-Za-z][A-Za-z\-]*", p):
            wl = w.lower()
            if w == "MN":
                unit = "meganewton"
            elif wl in UNITS and unit is None:
                unit = wl
            elif wl in MULTS and wl not in ("m", "mn") or w in ("K",):
                mult = MULTS.get(wl, 1e3)
    return unit, mult


def convert(am: Amount, target_unit: str, lab_unit, lab_mult):
    """Value in the column's unit, or None when the unit is incompatible / not convertible."""
    unit, mult = am.unit, am.mult
    if not am.explicit:
        unit, mult = lab_unit, lab_mult
    elif unit is None and am.mult == 1.0:
        unit = lab_unit
    if unit is not None:
        cls, fac = UNITS[unit]
        if cls != target_unit or fac is None:
            return None
    else:
        fac = 1.0
    total = fac * mult
    x = am.num * total
    if total != 1.0:  # snap to the simplest value consistent with the source's precision
        half = 0.5 * 10 ** (-am.decimals) * abs(total)
        r = round(x)
        if abs(x - r) <= half + 1e-9:
            x = float(r)
        else:
            x = float(f"{x:.6g}")
    return float(x)


# --------------------------------------------------------------------------- observations
class Obs:
    """One value seen in a file: entity, the words that label it, the raw text.
    mode 'cell' = a structured field (table cell, JSON/XML leaf); 'span' = a value found in text."""
    __slots__ = ("ent", "label", "raw", "mode", "kind", "after", "group", "order")

    def __init__(self, ent, label, raw, mode="cell", kind=None, after="", group=None, order=0):
        self.ent, self.label, self.raw, self.mode, self.kind = ent, label, raw, mode, kind
        self.after, self.group, self.order = after, group, order


# ---------------------------------------------------------------- tables (rows of cells)
_FIELD_HDR = {"field", "fieldname", "attribute", "name", "property", "metric", "item", "label", "key",
              "variable", "characteristic", "parameter", "measure", "column", "element", "detail", "type"}
_VALUE_HDR = {"value", "val", "reading", "data", "content", "entry", "result", "amount"}
_UNIT_HDR = {"unit", "units", "uom", "currency", "ccy", "measure unit"}


def _is_unit_token(s):
    s = norm(s).strip().lower().strip("()[]")
    return s in UNITS or s in ("k usd", "usd 000s", "'000 usd")


def rows_to_obs(rows, ctx: Ctx, out: list, default_ent=None, group_prefix="t"):
    rows = [[norm("" if c is None else c).strip().strip("*_`").strip() for c in r] for r in rows]
    rows = [r for r in rows if any(c for c in r)]
    if not rows:
        return
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    has_ent = [any(ctx.find(c) for c in r) for r in rows]
    # transposed: entities across the first row, labels down the first column
    if len(rows) >= 2 and sum(1 for c in rows[0][1:] if ctx.cell_ent(c)) >= 1 \
            and not any(ctx.cell_ent(r[0]) for r in rows[1:]) and not ctx.cell_ent(rows[0][0]) \
            and sum(1 for c in rows[0] if ctx.cell_ent(c)) >= max(1, (width - 1) // 2):
        rows = [list(col) for col in zip(*rows)]
        width = len(rows[0])
        has_ent = [any(ctx.find(c) for c in r) for r in rows]
    if not any(has_ent):
        # no entity column: a key column of plain digits, or a label/value list for default_ent
        hdr = rows[0]
        kc = next((j for j, h in enumerate(hdr) if is_key_label(h)), None)
        if kc is not None and any(ctx.digit_key(r[kc]) for r in rows[1:]):
            for r in rows[1:]:
                r[kc] = ctx.digit_key(r[kc]) or r[kc]
            return rows_to_obs(rows, ctx, out, default_ent, group_prefix)
        if default_ent:
            if width == 2 or (width >= 2 and all(not c for r in rows for c in r[2:])):
                for i, r in enumerate(rows):
                    out.append(Obs(default_ent, r[0], r[1], group=f"{group_prefix}kv", order=i))
            else:
                for i, r in enumerate(rows[1:]):
                    for j, c in enumerate(r):
                        out.append(Obs(default_ent, hdr[j], c, group=f"{group_prefix}", order=j))
        return
    # segment into (header, data rows)
    segs, header, data, pending = [], None, [], []
    for r, he in zip(rows, has_ent):
        nonempty = sum(1 for c in r if c)
        if he:
            if pending:
                header = pending[0] if len(pending) == 1 else [" ".join(x for x in col if x) for col in zip(*pending)]
                pending = []
            data.append(r)
        else:
            if nonempty < 2:
                continue  # title / note line
            if data:
                segs.append((header, data))
                data = []
            pending.append(r)
    if data:
        segs.append((header, data))
    for si, (header, data) in enumerate(segs):
        _segment_obs(header or [""] * width, data, ctx, out, f"{group_prefix}{si}")


def _segment_obs(header, data, ctx, out, group):
    width = len(header)
    hl = [re.sub(r"[^a-z ]", "", h.lower()).strip() for h in header]
    ht = [set(tokens(h)) for h in header]
    counts = [sum(1 for r in data if ctx.cell_ent(r[j])) for j in range(width)]
    kc = max(range(width), key=lambda j: (counts[j], -j))

    def pick(names, strict_tokens, exclude):
        j = next((j for j in range(width) if hl[j] in names and j not in exclude), None)
        if j is None:   # "Attribute name", "Reading value": distinctive words only
            j = next((j for j in range(width) if ht[j] & strict_tokens and len(ht[j]) <= 3 and j not in exclude), None)
        return j

    fcol = pick(_FIELD_HDR, {"field", "attribute", "property", "metric", "parameter", "variable", "characteristic"}, {kc})
    vcol = pick(_VALUE_HDR, {"value", "val", "reading"}, {kc, fcol}) if fcol is not None else None
    ucol = pick(_UNIT_HDR, {"unit", "units", "uom", "currency"}, {kc, fcol, vcol}) if vcol is not None else None
    if (fcol is None or vcol is None) and not any(header) and width <= 5 and len(data) >= 4:
        # header-less long table: a column of repeated words (field names) next to a column of values
        def texty(j):
            vs = [r[j] for r in data if r[j]]
            return vs and not any(re.search(r"\d", v) for v in vs) and len(set(vs)) <= max(3, len(vs) // 2)

        def valuey(j):
            vs = [r[j] for r in data if r[j]]
            return vs and sum(1 for v in vs if re.search(r"\d", v)) >= 0.3 * len(vs)
        fs = [j for j in range(width) if j != kc and texty(j)]
        vs_ = [j for j in range(width) if j != kc and j not in fs and valuey(j) and counts[j] == 0]
        if len(fs) == 1 and len(vs_) == 1:
            fcol, vcol = fs[0], vs_[0]
    if width > 6:
        fcol = vcol = None
    prev = None
    if fcol is not None and vcol is not None:   # long format
        for i, r in enumerate(data):
            ent = ctx.cell_ent(r[kc]) or (prev if not r[kc] else None)
            prev = ent
            if ent:
                raw = r[vcol] + (" " + r[ucol] if ucol is not None and r[ucol] and r[vcol] else "")
                out.append(Obs(ent, r[fcol], raw, group=group + "L", order=i))
        return
    # unit columns attach to the nearest numeric column on their left
    unit_of = {}
    for j in range(width):
        vals = [r[j] for r in data if r[j]]
        if j != kc and vals and all(_is_unit_token(v) for v in vals):
            k = j - 1
            while k >= 0 and (k == kc or k in unit_of.values()):
                k -= 1
            if k >= 0:
                unit_of[j] = k
    attach = {v: k for k, v in unit_of.items()}
    for r in data:
        ent = ctx.cell_ent(r[kc])
        if ent is None:
            ents = [e for c in r for e in ctx.ents(c)]
            ent = ents[0] if len(set(ents)) == 1 else (prev if not r[kc] else None)
        prev = ent
        if not ent:
            continue
        for j in range(width):
            if j == kc or j in unit_of:
                continue
            raw = r[j]
            if j in attach and raw and r[attach[j]]:
                raw = raw + " " + r[attach[j]]
            out.append(Obs(ent, header[j] or f"#col{j}", raw, group=group, order=j))


# ---------------------------------------------------------------- JSON
_GENERIC_KEYS = {"records", "record", "data", "items", "rows", "entries", "results", "list", "documents",
                 "document", "docs", "values_list", "payload", "body", "content", "table", "rows_data", "fields",
                 "attributes", "properties", "details", "info", "values", "facts", "columns_data"}
_NAME_KEYS = ("field", "fieldname", "field_name", "name", "attribute", "label", "key", "property", "metric",
              "parameter", "item", "column", "characteristic")
_VAL_KEYS = ("value", "val", "reading", "data", "content", "amount", "quantity", "magnitude", "number")
_UNIT_KEYS = ("unit", "units", "uom", "currency", "ccy", "unit_of_measure", "currency_code")


def _scalar(v):
    return v is None or isinstance(v, (str, int, float, bool))


def _sval(v):
    if v is None or isinstance(v, bool):
        return ""
    if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
        return str(int(v))
    return str(v)


def json_obs(node, ctx: Ctx, out: list, ent=None, path=(), docnames=()):
    def label_of(p):
        keys = [k for k in p if k and k.lower() not in _GENERIC_KEYS and k.lower() not in docnames
                and not ctx.cell_ent(k) and not re.fullmatch(r"\d+", k)]
        return " ".join(keys[-2:])

    if isinstance(node, list):
        if node and all(isinstance(x, list) for x in node):
            rows_to_obs([[_sval(c) for c in r] for r in node], ctx, out, ent, "j")
            return
        for x in node:
            if _scalar(x):
                if ent and not is_blank(_sval(x)) and not ctx.cell_ent(_sval(x)):
                    out.append(Obs(ent, label_of(path), _sval(x), group="j" + label_of(path)))
            else:
                json_obs(x, ctx, out, ent, path, docnames)
        return
    if not isinstance(node, dict):
        return
    lk = {str(k).lower(): k for k in node}
    # table orients
    if "columns" in lk and isinstance(node[lk["columns"]], list) and any(
            k in lk and isinstance(node[lk[k]], list) for k in ("data", "rows", "values")):
        dk = next(lk[k] for k in ("data", "rows", "values") if k in lk and isinstance(node[lk[k]], list))
        rows = node[dk]
        cols = [_sval(c) if _scalar(c) else str(c.get("name", "")) if isinstance(c, dict) else "" for c in node[lk["columns"]]]
        if rows and all(isinstance(r, list) for r in rows):
            rows_to_obs([cols] + [[_sval(c) for c in r] for r in rows], ctx, out, ent, "j")
            return
        if rows and all(isinstance(r, dict) for r in rows):
            for r in rows:
                json_obs(r, ctx, out, ent, path, docnames)
            return
    vals = list(node.values())
    if len(vals) >= 2 and all(isinstance(v, list) for v in vals) and len({len(v) for v in vals}) == 1 \
            and all(all(_scalar(x) for x in v) for v in vals) \
            and any(any(ctx.cell_ent(_sval(x)) for x in v) for v in vals):          # columnar
        keys = list(node.keys())
        rows_to_obs([keys] + [[_sval(node[k][i]) for k in keys] for i in range(len(vals[0]))], ctx, out, ent, "j")
        return
    if len(vals) >= 2 and all(isinstance(v, dict) for v in vals) \
            and len({tuple(sorted(v.keys())) for v in vals}) == 1 and all(all(_scalar(x) for x in v.values()) for v in vals) \
            and any(any(ctx.cell_ent(_sval(x)) for x in v.values()) for v in vals) \
            and not any(ctx.cell_ent(str(k)) for k in node):                          # pandas "columns" orient
        keys = list(node.keys())
        idx = list(vals[0].keys())
        rows_to_obs([keys] + [[_sval(node[k][i]) for k in keys] for i in idx], ctx, out, ent, "j")
        return
    # field/value pair
    nk = next((lk[k] for k in _NAME_KEYS if k in lk and isinstance(node[lk[k]], str)), None)
    vk = next((lk[k] for k in _VAL_KEYS if k in lk and lk[k] != nk and _scalar(node[lk[k]])), None)
    uk = next((lk[k] for k in _UNIT_KEYS if k in lk and isinstance(node[lk[k]], str)), None)
    # the record's own entity: a short scalar naming one entity, preferring id-like keys
    own = None
    short = [(k, v) for k, v in node.items() if _scalar(v) and len(_sval(v)) < 40 and ctx.cell_ent(_sval(v))]
    short.sort(key=lambda kv: not is_key_label(str(kv[0])))
    if short:
        own = ctx.cell_ent(_sval(short[0][1]))
    if own is None:
        for k, v in node.items():
            if _scalar(v) and is_key_label(str(k)) and ctx.digit_key(_sval(v)):
                own = ctx.digit_key(_sval(v))
                break
    if own is None and ent is None:
        found = set()
        _subtree_ents(node, ctx, found, 0)
        if len(found) == 1:
            own = found.pop()
    e = own or ent
    scalar_keys = [k for k, v in node.items() if _scalar(v)]
    if nk and vk and set(scalar_keys) <= {nk, vk, uk} | {k for k in scalar_keys if ctx.cell_ent(_sval(node[k]))} \
            | {k for k in scalar_keys if str(k).lower() in ("record", "record_id", "id", "row", "source", "doc", "document")}:
        if e:
            raw = _sval(node[vk]) + (" " + node[uk] if uk and _sval(node[vk]) else "")
            out.append(Obs(e, node[nk], raw, group="jpair"))
        return
    if vk and uk and set(scalar_keys) <= {vk, uk}:    # {value, unit} object
        if e:
            raw = _sval(node[vk]) + (" " + node[uk] if _sval(node[vk]) else "")
            out.append(Obs(e, label_of(path), raw, group="j" + label_of(path)))
        return
    # unit siblings: "load_unit" -> "load"; "currency" -> money-like siblings
    unit_for = {}
    numeric = [k for k in scalar_keys if re.search(r"\d", _sval(node[k])) and not find_dates(_sval(node[k]))
               and not ctx.cell_ent(_sval(node[k]))]
    for k in scalar_keys:
        kl = str(k).lower()
        v = _sval(node[k])
        if not _is_unit_token(v):
            continue
        base = re.sub(r"[_\s-]*(unit|units|uom|currency|ccy)$", "", kl)
        if base != kl:
            tgt = [n for n in numeric if str(n).lower().startswith(base)] if base else []
            if not tgt and kl in ("currency", "ccy", "currency_code"):
                tgt = [n for n in numeric if concepts(n).get("amount")] or (numeric if len(numeric) == 1 else [])
            if not tgt and kl in ("unit", "units", "uom"):
                tgt = numeric if len(numeric) == 1 else []
            for n in tgt:
                unit_for[n] = v
            unit_for[k] = None
    for k, v in node.items():
        ks = str(k)
        if ctx.cell_ent(ks) and len(ks) < 20:
            if _scalar(v):
                if not is_blank(_sval(v)):
                    out.append(Obs(ctx.cell_ent(ks), label_of(path), _sval(v), group="j" + label_of(path)))
            else:
                json_obs(v, ctx, out, ctx.cell_ent(ks), path, docnames)
            continue
        if _scalar(v):
            if k in unit_for and unit_for[k] is None:
                continue
            sv = _sval(v)
            if not e or (ctx.cell_ent(sv) and len(sv) < 20):
                continue
            if k in unit_for and sv:
                sv = sv + " " + unit_for[k]
            lab = label_of(path + (ks,))
            out.append(Obs(e, lab, sv, group="j" + lab))
        else:
            json_obs(v, ctx, out, e, path + (ks,), docnames)


def _subtree_ents(node, ctx, found, depth):
    if depth > 6 or len(found) > 1:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            e = ctx.cell_ent(str(k)) if len(str(k)) < 20 else None
            if e:
                found.add(e)
            _subtree_ents(v, ctx, found, depth + 1)
    elif isinstance(node, list):
        for v in node:
            _subtree_ents(v, ctx, found, depth + 1)
    elif _scalar(node):
        sv = _sval(node)
        if len(sv) < 20 and ctx.cell_ent(sv):
            found.add(ctx.cell_ent(sv))


# ---------------------------------------------------------------- XML
_NAME_ATTRS = ("name", "field", "key", "label", "attribute", "property", "metric", "param", "parameter")


def _xml_to_json(e):
    tag = e.tag.split("}")[-1]
    attrs = {k.split("}")[-1]: v for k, v in e.attrib.items()}
    kids = list(e)
    text = (e.text or "").strip()
    if not kids:
        unit = next((attrs.pop(k) for k in list(attrs) if k.lower() in _UNIT_KEYS), None)
        name = next((attrs.pop(k) for k in list(attrs) if k.lower() in _NAME_ATTRS), None)
        if "value" in attrs and not text:
            text = attrs.pop("value")
        val = text + (" " + unit if unit and text else "")
        if name is not None:
            return tag, {"field": name, "value": val, **attrs}
        if attrs:
            if text:
                return tag, {**attrs, tag: val}
            if unit:
                attrs["unit"] = unit
            return tag, attrs
        return tag, val
    d = dict(attrs)
    if text:
        d["#text"] = text
    grouped = defaultdict(list)
    for k in kids:
        t, v = _xml_to_json(k)
        grouped[t].append(v)
    for t, vs in grouped.items():
        d[t] = vs if len(vs) > 1 else vs[0]
    return tag, d


# ---------------------------------------------------------------- HTML
def _expand_spans(rows):
    """Rows of (text, (rowspan, colspan)) -> rectangular rows of text."""
    out, carry = [], {}
    for r in rows:
        line, cells, j = [], list(r), 0
        while cells or any(k >= j for k in carry):
            if j in carry:
                txt, left = carry[j]
                line.append(txt)
                if left > 1:
                    carry[j] = (txt, left - 1)
                else:
                    del carry[j]
                j += 1
                continue
            if not cells:
                break
            txt, (rs, cs) = cells.pop(0)
            for _ in range(cs):
                line.append(txt)
                if rs > 1:
                    carry[j] = (txt, rs - 1)
                j += 1
        out.append(line)
    return out


def _pipe_lines(rows):
    return ["| " + " | ".join(c.replace("|", "/") for c in r) + " |" for r in rows if any(x.strip() for x in r)]


class _HTML(HTMLParser):
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "ul", "ol",
             "dl", "header", "footer", "table", "pre", "blockquote", "hr", "dd", "caption"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.stack, self.lines, self.cur = [], [], [], []
        self.row = None
        self.cell = None
        self.span = (1, 1)
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head", "title"):
            self.skip += 1
        if tag == "table":
            self._flush()
            self.stack.append([])
        elif tag == "tr" and self.stack:
            self.row = []
        elif tag in ("td", "th") and self.stack:
            self.cell = []
            a = dict(attrs)
            try:
                self.span = (max(1, int(a.get("rowspan") or 1)), max(1, int(a.get("colspan") or 1)))
            except ValueError:
                self.span = (1, 1)
        elif tag in self.BLOCK and tag != "dd" and not self.stack:
            self._flush()
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                self.cur.append("#" * int(tag[1]) + " ")
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "title"):
            self.skip = max(0, self.skip - 1)
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append((" ".join("".join(self.cell).split()), self.span))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.stack:
            self.stack[-1].append(self.row)
            self.row = None
        elif tag == "table" and self.stack:
            rows = _expand_spans(self.stack.pop())
            self.tables.append(rows)
            self.lines.extend([""] + _pipe_lines(rows) + [""])
        elif tag == "dt" and not self.stack:
            self.cur.append(": ")
        elif tag in self.BLOCK and tag != "dd" and not self.stack:
            self._flush()
        elif tag == "dd" and not self.stack:
            self._flush()

    def handle_data(self, data):
        if self.skip:
            return
        if self.cell is not None:
            self.cell.append(data)
        elif not self.stack:
            self.cur.append(data)

    def _flush(self):
        s = " ".join("".join(self.cur).split())
        self.lines.append(s)
        self.cur = []

    def close(self):
        super().close()
        self._flush()


# ---------------------------------------------------------------- free text
_SEP_LINE = re.compile(r"^\s*[-=*_+~#|:. ]{3,}\s*$")
_REC_MARK = re.compile(r"^\s*(?:-\s|\*\s|\d+[.)]\s|(?:record|entry|item|row|rec)\b\s*#?\s*\d*|\[[^\]]+\]\s*$)", re.I)
_HEAD = re.compile(r"^\s*(#{1,6})\s")


def _split_cells_pipe(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _fixed_width(lines):
    """Split aligned columns at character positions blank in every line."""
    w = max(len(l) for l in lines)
    pad = [l.ljust(w) for l in lines]
    blank = [all(l[i] == " " for l in pad) for i in range(w)]
    for minrun in (2, 1):
        cuts, i = [], 0
        while i < w:
            if blank[i]:
                j = i
                while j < w and blank[j]:
                    j += 1
                if j - i >= minrun and i > 0 and j < w:
                    cuts.append((i, j))
                i = j
            else:
                i += 1
        if cuts:
            bounds, start = [], 0
            for a, b in cuts:
                bounds.append((start, a))
                start = b
            bounds.append((start, w))
            return [[l[a:b].strip() for a, b in bounds] for l in pad]
    return None


def _space_split(lines):
    """Columns separated by runs of 2+ spaces; a run twice as long as usual hides an empty cell."""
    for strip in (str.strip, str.lstrip):   # (a trailing run of spaces can be an empty last cell)
        sp = [re.split(r"\s{2,}|\t", strip(l)) for l in lines]
        if len({len(r) for r in sp}) == 1 and len(sp[0]) >= 2:
            return sp
    sp = [re.split(r"\s{2,}|\t", l.strip()) for l in lines]
    width = max(len(r) for r in sp)
    runs = [len(m.group(0)) for l, r in zip(lines, sp) if len(r) == width for m in re.finditer(r" {2,}", l.strip())]
    if runs and width >= 2:
        sep = min(runs)
        out = []
        for l in lines:
            cells, pos, t = [], 0, l.strip()
            for m in re.finditer(r" {2,}", t):
                cells.append(t[pos:m.start()])
                cells += [""] * max(0, round(len(m.group(0)) / sep) - 1)
                pos = m.end()
            cells.append(t[pos:])
            out.append(cells)
        if len({len(r) for r in out}) == 1:
            return out
    return _fixed_width(lines)


def _table_segments(lines, ctx):
    """Pipe (Markdown / ASCII grid) and tab-separated tables inside a block: [(start, end, rows)]."""
    segs = []
    n = len(lines)
    i = 0
    while i < n:
        l = lines[i]
        kind = "pipe" if l.count("|") >= 1 and not _SEP_LINE.match(l) else ("tab" if "\t" in l else None)
        if kind:
            j, rows = i, []
            while j < n and ((kind == "pipe" and ("|" in lines[j] or (_SEP_LINE.match(lines[j]) and lines[j].strip())))
                             or (kind == "tab" and "\t" in lines[j])):
                if not _SEP_LINE.match(lines[j]) or kind == "tab":
                    rows.append(_split_cells_pipe(lines[j]) if kind == "pipe" else lines[j].split("\t"))
                j += 1
            if len(rows) >= 2:
                segs.append((i, j, rows))
                i = j
                continue
        i += 1
    return segs


def _looks_kv(line):
    return bool(re.match(r"^\s*[-*]?\s*[A-Za-z][^:=]{0,60}\s*[:=]\s*\S", line))


class TextReader:
    def __init__(self, ctx: Ctx, out: list, gid: str):
        self.ctx, self.out, self.gid = ctx, out, gid
        self.cur = None
        self.ent_level = None
        self.sent_id = 0

    def run(self, text):
        raw_lines = norm(text).replace("\r", "").split("\n")   # trailing spaces kept: they can be empty cells
        lines = []
        for l in raw_lines:   # "Label:" on one line, its value on the next
            if lines and re.search(r"[A-Za-z)\]]\s*:\s*$", lines[-1]) and l.strip() and not re.search(r":\s*$", l) \
                    and "|" not in lines[-1] and not _HEAD.match(lines[-1]) and not _looks_kv(l) \
                    and not l.lstrip().startswith(("-", "*", "+")) \
                    and len(l) - len(l.lstrip()) <= len(lines[-1]) - len(lines[-1].lstrip()):
                lines[-1] = lines[-1].rstrip() + " " + l.strip()
            else:
                lines.append(l)
        blocks, b = [], []
        for i, l in enumerate(lines):
            if _SEP_LINE.match(l) and "|" not in l and "\t" not in l and not any(ch.isalnum() for ch in l) \
                    and b and i + 1 < len(lines) and lines[i + 1].strip():
                continue  # rule under a header row: not a block boundary
            if not l.strip() or (_SEP_LINE.match(l) and "|" not in l and "\t" not in l and not any(
                    ch.isalnum() for ch in l)):
                if b:
                    blocks.append(b)
                b = []
                continue
            if _HEAD.match(l):
                if b:
                    blocks.append(b)
                blocks.append([l])
                b = []
                continue
            b.append(l)
        if b:
            blocks.append(b)
        for bl in blocks:
            self.block(bl)

    def block(self, lines):
        ctx = self.ctx
        hm = _HEAD.match(lines[0]) if len(lines) == 1 else None
        if hm:
            es = ctx.ents(lines[0])
            lvl = len(hm.group(1))
            if es:
                self.cur, self.ent_level = es[-1], lvl
            elif self.ent_level is not None and lvl <= self.ent_level:
                self.cur, self.ent_level = None, None
            return
        # tables inside the block
        segs = _table_segments(lines, ctx)
        rest = list(lines)
        for a, bnd, rows in segs:
            block_ents = [e for l in lines[:a] for e in ctx.ents(l)]
            dflt = block_ents[-1] if block_ents else self.cur
            before = len(self.out)
            rows_to_obs(rows, ctx, self.out, dflt, f"{self.gid}p{a}")
            for k in range(a, bnd):
                rest[k] = ""
            tab_ents = [o.ent for o in self.out[before:]]
            if tab_ents:
                self.cur = tab_ents[-1]
        if segs:
            rest = [l for l in rest if l.strip()]
            if not rest:
                return
            lines = rest
        # fixed-width / comma table: header without entity, rows with entities, no key: value lines
        if len(lines) >= 2 and not ctx.find(lines[0]) and sum(1 for l in lines[1:] if ctx.find(l)) >= max(1, (len(lines) - 1) * 0.6) \
                and sum(1 for l in lines if _looks_kv(l)) < len(lines) / 2:
            rows = None
            try:
                cr = list(csv.reader(lines))
                if len({len(r) for r in cr}) == 1 and len(cr[0]) >= 2:
                    rows = cr
            except csv.Error:
                rows = None
            if rows is None:   # columns separated by runs of spaces (consistent count), else by position
                rows = _space_split(lines)
            if rows and len(rows[0]) >= 2:
                before = len(self.out)
                rows_to_obs(rows, ctx, self.out, self.cur, f"{self.gid}f{id(lines)}")
                if len(self.out) > before:
                    self.cur = self.out[-1].ent
                    return
        ents = []
        for l in lines:
            for e in ctx.ents(l):
                if e not in ents:
                    ents.append(e)
        if len(ents) <= 1:
            e = ents[0] if ents else self.cur
            self.span_lines(lines, fixed=e)
            if ents:
                self.cur = ents[0]
            return
        # several entities: split at record markers when they separate them cleanly
        idx = [k for k, l in enumerate(lines) if _REC_MARK.match(l)]
        if idx:
            ind = min(len(lines[k]) - len(lines[k].lstrip()) for k in idx)
            idx = [k for k in idx if len(lines[k]) - len(lines[k].lstrip()) == ind]
        if idx and len(idx) >= len(ents):
            parts = [lines[a:b] for a, b in zip([0] + idx, idx + [len(lines)]) if lines[a:b]]
            if all(len({e for l in p for e in ctx.ents(l)}) <= 1 for p in parts):
                for p in parts:
                    pe = [e for l in p for e in ctx.ents(l)]
                    self.span_lines(p, fixed=pe[0] if pe else self.cur)
                    if pe:
                        self.cur = pe[0]
                return
        self.span_lines(lines, fixed=None)

    def span_lines(self, lines, fixed):
        """Value spans with their context; entity = fixed, else by sentence / position."""
        for line in lines:
            for sent in self.split_sentences(line):
                self.sentence(sent, fixed)

    _ABBREV = {"no", "nr", "approx", "inc", "ltd", "co", "corp", "vs", "eg", "ie", "st", "dept", "ref", "fig", "mr",
               "mrs", "ms", "dr", "est", "qty", "amt", "exp", "dt"}

    def split_sentences(self, line):
        protected = [(a, b) for a, b, _, _ in find_dates(line)] + [(a, b) for a, b, _ in self.ctx.find(line)]
        protected += [(m.start(), m.end()) for m in re.finditer(r"\d[\d,.]*\d", line)]
        cuts = []
        for m in re.finditer(r"[.!?;]\s+(?=[^a-z\s])", line):
            p = m.start()
            if any(a <= p < b for a, b in protected):
                continue
            w = re.search(r"([A-Za-z]+)\.$", line[:p + 1])
            if line[p] == "." and w and (w.group(1).lower() in self._ABBREV or w.group(1).lower() in MONTHS
                                         or len(w.group(1)) == 1):
                continue
            cuts.append(m.end())
        out, start = [], 0
        for c in cuts:
            out.append(line[start:c])
            start = c
        out.append(line[start:])
        return [x for x in out if x.strip()]

    def sentence(self, s, fixed):
        ctx = self.ctx
        self.sent_id += 1
        ents = ctx.find(s)
        masked = _mask(s, [(a, b) for a, b, _ in ents], "\x00")
        spans = []
        dates = find_dates(masked)
        for a, b, kind, g in dates:
            spans.append((a, b, "date", masked[a:b]))
        m2 = _mask(masked, [(a, b) for a, b, _, _ in dates])
        for a, b, am in find_amounts(m2, False):
            spans.append((a, b, "amount", m2[a:b]))
        spans.sort()
        if not spans:
            if ents and fixed is None:
                self.cur = ents[-1][2]
            return
        bounds = [0] + [b for _, b, _, _ in spans]
        for k, (a, b, kind, raw) in enumerate(spans):
            before = masked[bounds[k]:a].replace("\x00", " ")
            nxt = spans[k + 1][0] if k + 1 < len(spans) else len(s)
            after = masked[b:nxt].replace("\x00", " ")
            # label: the words before the value (since the previous value), at most 8 words
            words = re.findall(r"[^\s]+", re.sub(r"[\x00]", " ", before))
            lab = " ".join(words[-10:])
            aft = " ".join(re.findall(r"[^\s]+", after)[:10])
            if fixed is not None:
                ent = fixed
            elif ents:
                prev = [e for ea, eb, e in ents if eb <= a]
                ent = prev[-1] if prev else ents[0][2]
            else:
                ent = self.cur
            if ent is None:
                continue
            self.out.append(Obs(ent, lab, raw, mode="span", kind=kind, after=aft,
                                group=f"{self.gid}s{self.sent_id}", order=k))
        if ents and fixed is None:
            self.cur = ents[-1][2]
        elif fixed is not None:
            self.cur = fixed


# ---------------------------------------------------------------- zip formats
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_xlsx(data: bytes):
    z = zipfile.ZipFile(io.BytesIO(data))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", _NS):
            shared.append("".join(t.text or "" for t in si.iter("{%s}t" % _NS["m"])))
    date_styles = set()
    if "xl/styles.xml" in z.namelist():
        st = ET.fromstring(z.read("xl/styles.xml"))
        custom = {}
        for nf in st.iter("{%s}numFmt" % _NS["m"]):
            code = nf.get("formatCode", "").lower()
            if re.search(r"[dy]", re.sub(r"\[[^\]]*\]|\"[^\"]*\"", "", code)):
                custom[int(nf.get("numFmtId"))] = True
        xfs = st.find("m:cellXfs", _NS)
        if xfs is not None:
            for i, xf in enumerate(xfs.findall("m:xf", _NS)):
                fid = int(xf.get("numFmtId", "0"))
                if 14 <= fid <= 22 or 45 <= fid <= 47 or fid in custom:
                    date_styles.add(i)
    tables = []
    for name in sorted(n for n in z.namelist() if n.startswith("xl/worksheets/") and n.endswith(".xml")):
        rows = []
        for row in ET.fromstring(z.read(name)).iter("{%s}row" % _NS["m"]):
            cells = {}
            for c in row.findall("m:c", _NS):
                t, s = c.get("t"), int(c.get("s", "0"))
                v = c.find("m:v", _NS)
                txt = v.text if v is not None else ""
                if t == "s" and txt:
                    txt = shared[int(txt)]
                elif t == "inlineStr":
                    txt = "".join(x.text or "" for x in c.iter("{%s}t" % _NS["m"]))
                elif t in (None, "n") and txt and s in date_styles:
                    try:
                        txt = (date(1899, 12, 30) + timedelta(days=int(float(txt)))).isoformat()
                    except ValueError:
                        pass
                cells[_col_index(c.get("r", "A1"))] = txt or ""
            if cells:
                rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
        tables.append(rows)
    return tables


def read_docx(data: bytes):
    z = zipfile.ZipFile(io.BytesIO(data))
    root = ET.fromstring(z.read("word/document.xml"))
    body = root.find("w:body", _NS)
    W = "{%s}" % _NS["w"]
    lines, tables = [], []

    def ptext(p):
        return "".join(t.text or "" for t in p.iter(W + "t"))

    for el in list(body) if body is not None else []:
        if el.tag == W + "p":
            lines.append(ptext(el))
        elif el.tag == W + "tbl":
            rows = []
            for tr in el.iter(W + "tr"):
                rows.append([" ".join(ptext(p) for p in tc.iter(W + "p")) for tc in tr.findall(W + "tc")])
            tables.append(rows)
            lines.extend([""] + _pipe_lines(rows) + [""])
    return lines, tables


# ---------------------------------------------------------------- dispatch
def _decode(data: bytes) -> str:
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", "replace")


def _sniff_delim(text):
    lines = [l for l in text.splitlines() if l.strip()][:30]
    best, bscore = ",", -1
    for d in (",", ";", "\t", "|"):
        try:
            counts = [len(r) for r in csv.reader(lines, delimiter=d)]
        except csv.Error:
            continue
        if not counts or max(counts) < 2:
            continue
        c = Counter(counts).most_common(1)[0]
        score = c[1] * 10 + c[0]
        if score > bscore:
            best, bscore = d, score
    return best


def parse_file(path: Path, ctx: Ctx, docnames=()) -> list:
    data = path.read_bytes()
    ext = path.suffix.lower()
    out: list = []
    gid = path.stem
    if data[:2] == b"PK":
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
            names = z.namelist()
            if any(n.startswith("xl/") for n in names):
                for t in read_xlsx(data):
                    rows_to_obs(t, ctx, out, None, gid + "x")
                return out
            if "word/document.xml" in names:
                lines, tables = read_docx(data)
                TextReader(ctx, out, gid).run("\n".join(lines))
                return out
        except (zipfile.BadZipFile, KeyError, ET.ParseError):
            pass
    text = _decode(data)
    s = text.lstrip()
    if ext in (".json", ".jsonl", ".ndjson", ".geojson") or s[:1] in "[{":
        try:
            json_obs(json.loads(s), ctx, out, None, (), docnames)
            return out
        except ValueError:
            objs = []
            for l in s.splitlines():
                l = l.strip().rstrip(",")
                if not l:
                    continue
                try:
                    objs.append(json.loads(l))
                except ValueError:
                    objs = None
                    break
            if objs:
                json_obs(objs, ctx, out, None, (), docnames)
                return out
    if s.startswith("<"):
        low = s[:2000].lower()
        if "<html" in low or "<table" in low or "<body" in low or "<!doctype html" in low or "<div" in low or "<p>" in low:
            h = _HTML()
            h.feed(s)
            h.close()
            TextReader(ctx, out, gid).run("\n".join(h.lines))
            return out
        try:
            root = ET.fromstring(re.sub(r"^<\?xml[^>]*\?>", "", s).strip().encode("utf-8"))
            tag, j = _xml_to_json(root)
            json_obs(j if isinstance(j, dict) else {tag: j}, ctx, out, None, (), docnames)
            return out
        except ET.ParseError:
            h = _HTML()
            h.feed(s)
            h.close()
            TextReader(ctx, out, gid).run("\n".join(h.lines))
            return out
    if ext in (".csv", ".tsv", ".psv", ".tab", ".dsv"):
        delim = "\t" if ext in (".tsv", ".tab") else _sniff_delim(text)
        rows = list(csv.reader(io.StringIO(text), delimiter=delim))
        rows_to_obs(rows, ctx, out, None, gid + "c")
        return out
    TextReader(ctx, out, gid).run(text)
    return out


# --------------------------------------------------------------------------- documents
def match_doc(stem: str, wf: str):
    names = list(DOCS[wf])
    s = re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")
    if s in names:
        return s
    for n in names:
        if s.replace("_", "") == n.replace("_", ""):
            return n
    for n in names:   # stem contains the doc name ("packet_invoices", "03-invoices")
        if re.search(r"(^|_)" + re.escape(n) + r"($|_)", s):
            return n
    best = difflib.get_close_matches(s, names, n=1, cutoff=0.75)
    return best[0] if best else None


def _column_info(wf, doc):
    cols = []
    for c, kind, unit, lab in DOCS[wf][doc]:
        if kind in ("date", "amount") and c != KEY[wf]:
            cols.append((c, kind, unit))
    return cols


def _readings(o: Obs, conv, eu, ctx):
    """Possible readings of an observation: ('date', [dates]) / ('amount', [Amount]) / None."""
    raw = norm(o.raw).strip()
    if o.mode == "span":
        if o.kind == "date":
            ds = [interpret_date(k, g, conv) for _, _, k, g in find_dates(raw)]
            return ("date", [d for d in ds if d]) if ds and all(ds) else ("bad", [])
        ams = [x for _, _, x in find_amounts(raw, eu)]
        return ("amount", ams) if ams else ("bad", [])
    m = re.fullmatch(r"\s*(\d{4})(\d{2})(\d{2})\s*", raw)
    if m and _mk(int(m.group(1)), int(m.group(2)), int(m.group(3))) and 1900 <= int(m.group(1)) <= 2100:
        return ("date", [_mk(int(m.group(1)), int(m.group(2)), int(m.group(3)))])
    found = find_dates(raw)
    if found:
        ds = [interpret_date(k, g, conv) for _, _, k, g in found]
        if all(ds):
            return ("date", ds)
        return ("bad", [])
    masked = _mask(raw, [(a, b) for a, b, _ in ctx.find(raw)])   # ids inside a cell are not numbers
    ams = [x for _, _, x in find_amounts(masked, eu)]
    if ams:
        rest = masked
        for a, b, _ in find_amounts(masked, eu):
            rest = rest[:a] + " " * (b - a) + rest[b:]
        if len(ams) > 1 and not re.fullmatch(r"[\s;/|,&+]*(?:(?:and|or)\s*)*[\s;/|,]*", re.sub(r"\b(and|or)\b", " ", rest)):
            return ("bad", [])
        return ("amount", ams)
    return ("bad", [])




def _snapkey(v):
    if isinstance(v, float):
        return round(v, 6)
    return v


def map_document(wf, doc, obs, conv, eu, docunits=None, ctx=None):
    """-> {(col, ent): {'vals': set, 'bad': bool}} for the document's date / amount columns."""
    cols = _column_info(wf, doc)
    res = defaultdict(lambda: {"vals": set(), "bad": False})
    if not cols:
        return res
    parsed = []
    for o in obs:
        if o.ent is None or is_blank(o.raw):
            continue
        if o.mode == "cell" and (is_meta_label(o.label) or is_key_label(o.label) and not concepts(o.label).get("qty")):
            continue
        kind, vals = _readings(o, conv, eu, ctx or Ctx(wf))
        if kind == "bad" and not re.search(r"\d", norm(o.raw)):
            continue   # words only (a unit, a status, "see note"): not an attempted value
        parsed.append((o, kind, vals))

    lunit_cache = {}

    def lunit(label, cu=None):
        if label not in lunit_cache:
            lunit_cache[label] = label_unit(label)
        lu, lm = lunit_cache[label]
        if lu is None and lm == 1.0 and docunits and cu in docunits:
            return docunits[cu]   # the document declares the unit ("loads in N")
        return lu, lm

    def compatible(o, kind, vals, c, ck, cu):
        if kind == "date":
            return ck == "date"
        if kind == "amount":
            if ck == "date":
                return False
            lu, lm = lunit(o.label, cu)
            if lu and UNITS[lu][0] != cu:
                return False
            return all(convert(a, cu, lu, lm) is not None or (a.uclass() == cu and UNITS[a.unit][1] is None)
                       for a in vals)
        return False

    # ---- structured labels: one decision per (group, label)
    by_label = defaultdict(list)
    for o, kind, vals in parsed:
        if o.mode == "cell":
            by_label[(o.group, str(o.label))].append((o, kind, vals))
    assign = {}
    pending = defaultdict(list)
    for (g, lab), items in by_label.items():
        kinds = Counter(k for _, k, _ in items if k != "bad")
        if not kinds:
            # unreadable values: claim the column only on a strong, unique label match
            sc = sorted(((col_score(lab, c), c) for c, ck, cu in cols), reverse=True)
            if sc and sc[0][0] >= 1.5 and (len(sc) == 1 or sc[1][0] < sc[0][0]):
                assign[(g, lab)] = sc[0][1]
            continue
        kind = kinds.most_common(1)[0][0]
        good = [(o, k, v) for o, k, v in items if k == kind]
        cands = [(c, ck, cu) for c, ck, cu in cols if all(compatible(o, k, v, c, ck, cu) for o, k, v in good)]
        if not cands and kind == "amount":   # numbers that may be Excel serial dates in a date column
            dcols = [(c, ck, cu) for c, ck, cu in cols if ck == "date"]
            if dcols and all(len(v) == 1 and v[0].unit is None and serial_to_date(v[0].num) for _, _, v in good):
                sc = max((col_score(lab, c), c) for c, _, _ in dcols)
                if sc[0] > 0 or len(dcols) == 1:
                    assign[(g, lab)] = ("serial", sc[1])
                    continue
        if not cands:
            # the label clearly names a column but the values do not read as its kind ("26 Jul",
            # a non-USD currency): the slot holds something unreadable -> abstain, no fall-through
            sc = sorted(((col_score(lab, c), c) for c, ck, cu in cols), reverse=True)
            if sc and sc[0][0] >= 1.5 and (len(sc) == 1 or sc[1][0] < sc[0][0]):
                assign[(g, lab)] = ("bad", sc[0][1])
            continue
        sc = sorted(((col_score(lab, c), -i, c) for i, (c, ck, cu) in enumerate(cands)), reverse=True)
        pending[(g, kind)].append((lab, sc, min(o.order for o, _, _ in items)))
    for (g, kind), labs in pending.items():
        taken = {}
        flat = sorted(((s, -order, lab, c) for lab, sc, order in labs for s, _, c in sc if s > 0), reverse=True)
        for s, _, lab, c in flat:
            if lab in taken.values() or (g, lab) in assign:
                continue
            if c not in taken:
                taken[c] = lab
                assign[(g, lab)] = c
        for lab, sc, order in labs:   # positive but beaten: keep its best column (strong only)
            if (g, lab) not in assign and sc[0][0] >= 2:
                assign[(g, lab)] = sc[0][2]
        rest = sorted((order, lab, sc) for lab, sc, order in labs if (g, lab) not in assign)
        for order, lab, sc in rest:   # silent labels: the remaining compatible columns, in order
            free = [c for _, negi, c in sorted(sc, key=lambda x: -x[1]) if c not in taken]
            if free:
                taken[free[0]] = lab
                assign[(g, lab)] = free[0]
    for o, kind, vals in parsed:
        if o.mode != "cell":
            continue
        a = assign.get((o.group, str(o.label)))
        if a is None:
            continue
        if isinstance(a, tuple) and a[0] == "bad":
            res[(a[1], o.ent)]["bad"] = True
            continue
        if isinstance(a, tuple):
            d = serial_to_date(vals[0].num) if kind == "amount" and vals else None
            if d:
                res[(a[1], o.ent)]["vals"].add(d)
            continue
        col, ck, cu = next(x for x in cols if x[0] == a)
        if kind == "bad" or (kind == "date") != (ck == "date"):
            if kind == "bad":
                res[(col, o.ent)]["bad"] = True
            continue
        if kind == "date":
            for d in vals:
                res[(col, o.ent)]["vals"].add(d)
        else:
            lu, lm = lunit(o.label, cu)
            for am in vals:
                x = convert(am, cu, lu, lm)
                if x is None:
                    res[(col, o.ent)]["bad"] = True
                else:
                    res[(col, o.ent)]["vals"].add(_snapkey(x))

    # ---- spans from free text: one decision per value, using the words around it
    items = []
    for o, kind, vals in parsed:
        if o.mode != "span" or kind == "bad":
            continue
        if is_meta_label(o.label) and not is_meta_label(o.after or "x"):
            continue
        cands = [c for c, ck, cu in cols if compatible(o, kind, vals, c, ck, cu)]
        if not cands:
            continue
        sc = sorted(((col_score(o.label, c), c) for c in cands), reverse=True)
        if sc[0][0] <= 0:
            sc2 = sorted(((col_score(o.after, c), c) for c in cands), reverse=True)
            if sc2[0][0] > 0:
                sc = sc2
        items.append([o, kind, vals, cands, sc, None])
    # decisions per distinct label (by the text that scored): strongest labels first; a label that
    # repeats across records (template / key-value list) yields a column a stronger label already
    # holds when it has another positive column ("First day posted" / "Last day posted")
    keyed = defaultdict(list)
    for it in items:
        txt = it[0].label if col_score(it[0].label, it[4][0][1]) > 0 or not it[0].after else it[0].after
        keyed[(it[1], " ".join(tokens(txt)))].append(it)
    taken = defaultdict(dict)
    for (kind, key), its in sorted(keyed.items(), key=lambda kv: -kv[1][0][4][0][0]):
        sc = its[0][4]
        if sc[0][0] <= 0:
            continue
        tied = [c for v, c in sc if v == sc[0][0]]
        free_tied = [c for c in tied if c not in taken[kind]]
        col = None
        if len(tied) == 1:
            col = tied[0]
            if col in taken[kind] and len(its) >= 2:
                alt = [c for v, c in sc if v > 0 and c not in taken[kind]]
                if alt:
                    col = alt[0]
        elif len(free_tied) == 1:
            col = free_tied[0]
        if col is None:
            continue
        taken[kind].setdefault(col, key)
        for it in its:
            if col in it[3]:
                it[5] = col
    groups = defaultdict(list)
    for it in items:
        groups[it[0].group].append(it)
    for g, lst in groups.items():
        lst.sort(key=lambda x: x[0].order)
        # one record rarely states a field under two different labels: when two labels of the
        # same sentence/record claim one column, the weaker moves to its next positive column
        by_col = defaultdict(list)
        for it in lst:
            if it[5] is not None:
                by_col[it[5]].append(it)
        for col, its in list(by_col.items()):
            keys = {" ".join(tokens(it[0].label)) for it in its}
            if len(its) < 2 or len(keys) < 2:
                continue
            score = lambda it: max(v for v, c in it[4] if c == col)
            best = max(its, key=score)
            bk = " ".join(tokens(best[0].label))
            for it in its:
                if " ".join(tokens(it[0].label)) == bk:
                    continue
                alt = [c for v, c in it[4] if c != col and v > 0 and c not in by_col]
                if alt:
                    it[5] = alt[0]
                    by_col[alt[0]] = [it]
        # coordination: "one says X, another Y" / "X and Y" -> Y belongs to X's field
        prev, prev_lab = {}, {}
        for it in lst:
            o, kind = it[0], it[1]
            conn = re.sub(r"[\s,;:()]+", " ", o.label).strip().lower()
            opener = set(tokens(prev_lab.get(kind, ""))) & _RANGE_OPEN
            if it[5] is None and kind in prev and len(it[3]) == 2 and prev[kind] in it[3] and (
                    conn in ("-", "to", "until", "till", "through", "thru", "->") or (conn == "and" and opener)):
                it[5] = next(c for c in it[3] if c != prev[kind])   # a range: start -> end column
            if it[5] is None and it[4][0][0] <= 0 and kind in prev and len(o.label.split()) <= 4:
                if prev[kind] in it[3]:
                    it[5] = prev[kind]
            if it[5] is not None:
                prev[kind] = it[5]
                prev_lab[kind] = o.label
        unresolved = defaultdict(list)
        for it in lst:
            o, kind, vals, cands, sc, col = it
            if col is not None:
                _put(res, o, col, kind, vals, cols, lunit)
            elif sc[0][0] <= 0 and (kind == "date" or any(x.explicit for x in vals)):
                unresolved[kind].append((o, vals, cands))
        for kind, ul in unresolved.items():
            colset = [c for c, ck, cu in cols if all(c in cs for _, _, cs in ul)]
            if len(ul) == 1 and len(ul[0][2]) == 1:
                _put(res, ul[0][0], ul[0][2][0], kind, ul[0][1], cols, lunit)
            elif len(ul) == len(colset):
                for (o, vals, _), c in zip(ul, colset):
                    _put(res, o, c, kind, vals, cols, lunit)
    return res


_RANGE_OPEN = {"between", "from", "period", "window", "range", "span", "during"}


def _put(res, o, col, kind, vals, cols, lunit):
    _, ck, cu = next(x for x in cols if x[0] == col)
    if kind == "date":
        for d in vals:
            res[(col, o.ent)]["vals"].add(d)
    else:
        lu, lm = lunit(o.label, cu)
        for am in vals:
            x = convert(am, cu, lu, lm)
            if x is None:
                res[(col, o.ent)]["bad"] = True
            else:
                res[(col, o.ent)]["vals"].add(_snapkey(x))


# --------------------------------------------------------------------------- extract
def extract(workflow: str, packet_dir: str) -> dict:
    wf = workflow
    ctx = Ctx(wf)
    pdir = Path(packet_dir)
    files = sorted(p for p in pdir.rglob("*") if p.is_file()
                   and not any(x.startswith(".") for x in p.relative_to(pdir).parts))
    docnames = tuple(DOCS[wf])
    per_doc = defaultdict(list)
    entities: list = []
    raws = defaultdict(list)
    docunits = {}
    for p in files:
        try:
            obs = parse_file(p, ctx, docnames)
        except Exception:  # an unreadable file contributes nothing (abstain)
            obs = []
        try:
            text = _decode(p.read_bytes()) if p.read_bytes()[:2] != b"PK" else ""
        except Exception:
            text = ""
        for e in ctx.ents(text) + [o.ent for o in obs if o.ent]:
            if e not in entities:
                entities.append(e)
        doc = match_doc(p.stem, wf)
        if doc:
            per_doc[doc].extend(obs)
            du = declared_units(text)
            if text.lstrip()[:1] in "[{":
                try:
                    du.update(json_declared_units(json.loads(text), ctx))
                except ValueError:
                    pass
            if doc in docunits and docunits[doc] != du:
                du = {k: v for k, v in du.items() if docunits[doc].get(k) == v}
            docunits[doc] = du
            raws[doc].extend(o.raw for o in obs)
    allraw = [r for v in raws.values() for r in v]
    packet_conv = date_conventions(allraw)
    eu = number_convention(allraw)
    values = {}
    for doc, obs in per_doc.items():
        conv = dict(packet_conv)
        conv.update(date_conventions(raws[doc]))
        values[doc] = map_document(wf, doc, obs, conv, eu, docunits.get(doc), ctx)

    out = {}
    for c in RULES[wf]:
        for e in entities:
            facts = {}
            for f in c.facts:
                rep = "ABSENT"
                for s in f.sources:
                    cell = values.get(s.table, {}).get((s.column, e))
                    if not cell or (not cell["vals"] and not cell["bad"]):
                        continue
                    if len(cell["vals"]) > 1:
                        rep = "CONFLICT"
                    elif cell["bad"] or not cell["vals"]:
                        rep = "ABSENT"   # the deciding document has a value we cannot read: abstain
                    else:
                        v = next(iter(cell["vals"]))
                        if isinstance(v, date):
                            v = v.isoformat()
                        elif isinstance(v, float) and v.is_integer():
                            v = int(v) if f.kind == "amount" else v
                        rep = (v, s.table)
                    break
                facts[f.name] = rep
            out[f"{c.rule_id}::{e}"] = facts
    return out


# --------------------------------------------------------------------------- dev harness
def _canonical_slots(wf, cdir: Path):
    tables = {}
    for t in DOCS[wf]:
        p = cdir / f"{t}.csv"
        tables[t] = list(csv.DictReader(p.open())) if p.exists() else []
    ents = []
    for rows in tables.values():
        for r in rows:
            e = r.get(KEY[wf])
            if e and e not in ents:
                ents.append(e)
    exp = {}
    for c in RULES[wf]:
        for e in ents:
            facts = {}
            for f in c.facts:
                rep = "ABSENT"
                for s in f.sources:
                    vals = {(float(r[s.column]) if f.kind == "amount" else r[s.column]) for r in tables[s.table]
                            if r.get(s.key) == e and r.get(s.column) not in (None, "")}
                    if len(vals) > 1:
                        rep = "CONFLICT"
                        break
                    if vals:
                        rep = (vals.pop(), s.table)
                        break
                facts[f.name] = rep
            exp[f"{c.rule_id}::{e}"] = facts
    return exp


def _slot_eq(a, b):
    if isinstance(a, tuple) and isinstance(b, tuple):
        if a[1] != b[1]:
            return False
        try:
            return abs(float(a[0]) - float(b[0])) < 1e-6
        except (TypeError, ValueError):
            return str(a[0]) == str(b[0])
    return a == b


def run_dev(root: Path, layouts=None, verbose=False):
    labels_dir = root / "labels"
    layouts = layouts or sorted(p.name for p in root.iterdir() if p.is_dir() and p.name not in ("labels", "canonical"))
    tot = Counter()
    by_l, by_w = defaultdict(Counter), defaultdict(Counter)
    errs = []
    for L in layouts:
        for wf in sorted(p.name for p in (root / L).iterdir() if p.is_dir()):
            for sd in sorted(p.name for p in (root / L / wf).iterdir() if p.is_dir()):
                facts = extract(wf, str(root / L / wf / sd))
                gold = json.loads((labels_dir / wf / f"{sd}.json").read_text())
                exp = _canonical_slots(wf, root / "canonical" / wf / sd)
                for pid, lab in gold.items():
                    rid = pid.split("::")[0]
                    rep = facts.get(pid, {})
                    v = verdict_from_facts(CONTRACTS[rid], rep)
                    ok = v == lab
                    for C in (tot, by_l[L], by_w[wf]):
                        C["v_n"] += 1
                        C["v_ok"] += ok
                    if not ok:
                        errs.append(f"verdict {L}/{wf}/{sd} {pid}: got {v} want {lab}")
                    for fn, ev in exp.get(pid, {}).items():
                        sok = _slot_eq(rep.get(fn, "ABSENT"), ev)
                        for C in (tot, by_l[L], by_w[wf]):
                            C["s_n"] += 1
                            C["s_ok"] += sok
                        if not sok:
                            errs.append(f"slot {L}/{wf}/{sd} {pid} {fn}: got {rep.get(fn)} want {ev}")
                extra = set(facts) - set(gold)
                missing = set(gold) - set(facts)
                if extra or missing:
                    errs.append(f"pairs {L}/{wf}/{sd}: extra={sorted(extra)[:3]} missing={sorted(missing)[:3]}")

    def fmt(C):
        return (f"verdicts {C['v_ok']}/{C['v_n']} = {C['v_ok'] / max(1, C['v_n']):.4f}   "
                f"slots {C['s_ok']}/{C['s_n']} = {C['s_ok'] / max(1, C['s_n']):.4f}")

    print("per layout:")
    for L in layouts:
        print(f"  {L:<10} {fmt(by_l[L])}")
    print("per workflow:")
    for w in sorted(by_w):
        print(f"  {w:<12} {fmt(by_w[w])}")
    print(f"overall      {fmt(tot)}")
    if errs:
        print(f"\n{len(errs)} mismatches" + ("" if verbose else " (first 30; --verbose for all)"))
        for e in errs if verbose else errs[:30]:
            print("  " + e)
    return tot


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dev", action="store_true", help="evaluate on data/study13/parser_dev")
    ap.add_argument("--root", default=str(_ROOT / "data" / "study13" / "parser_dev"))
    ap.add_argument("--layouts", nargs="*")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--extract", nargs=2, metavar=("WORKFLOW", "PACKET_DIR"))
    a = ap.parse_args(argv)
    if a.extract:
        print(json.dumps(extract(*a.extract), indent=1, default=str))
    elif a.dev:
        run_dev(Path(a.root), a.layouts, a.verbose)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()

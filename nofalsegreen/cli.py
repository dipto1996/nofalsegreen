"""Command line entry point.

    python -m nofalsegreen.cli score --firm northwind --baseline always_pass
    python -m nofalsegreen.cli generate --seed 7 --out data/firms/synthetic-000007
    python -m nofalsegreen.cli describe
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from baselines.trivial import REGISTRY  # noqa: E402
from nofalsegreen import northwind  # noqa: E402
from nofalsegreen.generator import FirmGenerator, GeneratorConfig  # noqa: E402
from nofalsegreen.metrics import score  # noqa: E402
from nofalsegreen.rulebook import Rulebook  # noqa: E402

RULEBOOK = ROOT / "rulebook" / "rulebook.json"
ANCHOR = ROOT / "data" / "firms" / "northwind-robotics"


def _load_firm(name: str):
    if name in ("northwind", "northwind-robotics"):
        return northwind.load(ANCHOR, ANCHOR / "expectations.json")
    d = ROOT / "data" / "firms" / name
    firm_json = d / "firm.json"
    if not firm_json.exists():
        raise SystemExit(f"no such firm: {name} (expected {firm_json})")
    raw = json.loads(firm_json.read_text())
    from nofalsegreen.schema import Entity, Firm, Label, Pair, Severity, Verdict

    return Firm(
        firm_id=raw["firm_id"], name=raw["name"], as_of=raw["as_of"],
        sources={k: Path(v) for k, v in raw["sources"].items()},
        entities=[Entity(**e) for e in raw["entities"]],
        pairs=[Pair(**p) for p in raw["pairs"]],
        labels=[
            Label(
                pair_id=l["pair_id"], verdict=Verdict(l["verdict"]), basis=l["basis"],
                severity=Severity(l["severity"]) if l.get("severity") else None,
                evidence_fields=tuple(l.get("evidence_fields", ())), note=l.get("note", ""),
            ) for l in raw["labels"]
        ],
        provenance=raw.get("provenance", {}),
    )


def cmd_score(args) -> int:
    firm = _load_firm(args.firm)
    rb = Rulebook.load(RULEBOOK)
    fn = REGISTRY.get(args.baseline)
    if not fn:
        raise SystemExit(f"unknown baseline {args.baseline}; have {sorted(REGISTRY)}")
    report = score(firm.labels, fn(firm), rule_regimes=rb.rule_regimes())
    print(f"firm      {firm.name}  ({firm.firm_id}, as of {firm.as_of})")
    print(f"system    {args.baseline}\n")
    print(report.summary())
    if args.json:
        Path(args.json).write_text(json.dumps(report.__dict__, indent=2, default=str))
        print(f"\nwrote {args.json}")
    return 0


def cmd_generate(args) -> int:
    rb = Rulebook.load(RULEBOOK)
    cfg = GeneratorConfig(n_workers=args.workers)
    gen = FirmGenerator(rb, cfg)
    out = Path(args.out)
    firm = gen.generate(args.seed, out)
    (out / "firm.json").write_text(firm.to_json())
    import collections
    counts = collections.Counter(l.verdict.value for l in firm.labels)
    print(f"generated {firm.firm_id} -> {out}")
    print(f"  entities {len(firm.entities)}  pairs {len(firm.pairs)}")
    print(f"  labels   {dict(counts)}")
    return 0


def cmd_describe(args) -> int:
    rb = Rulebook.load(RULEBOOK)
    firm = _load_firm("northwind")
    print(f"rulebook  {len(rb.obligations)} obligations, version {rb.version}")
    for regime, n in rb.regimes().items():
        print(f"    {n:3d}  {regime}")
    print(f"\nanchor firm  {firm.name}: {len(firm.pairs)} pairs, {len(firm.sources)} sources")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="nofalsegreen")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="score a baseline on a firm")
    s.add_argument("--firm", default="northwind")
    s.add_argument("--baseline", default="always_pass")
    s.add_argument("--json", default=None)
    s.set_defaults(fn=cmd_score)

    g = sub.add_parser("generate", help="generate a synthetic firm")
    g.add_argument("--seed", type=int, required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--workers", type=int, default=12)
    g.set_defaults(fn=cmd_generate)

    d = sub.add_parser("describe", help="print rulebook and anchor firm stats")
    d.set_defaults(fn=cmd_describe)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

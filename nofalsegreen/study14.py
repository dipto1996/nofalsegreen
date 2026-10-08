"""Study 14: a powered transfer test on fresh contents and six new layouts.

DECLARED before any Study 14 call (docs/STUDY14_DECLARATION.md).

The rules, labeller, solver and prompts are Study 13's, frozen as corrected (study13.CONTRACTS,
study13.statement_r2, the contract13b_* prompts). New here:

  contents  30 fresh packets, ten seeds per workflow (power analysis: docs/study14/power.json).
  layouts   six layouts from three designers who worked separately from each other, from the
            parser's author and from us: A1-A2 modelled on public and standard formats (a
            pipe-delimited disclosure-style export, an X12-style interchange), B1-B2 on human
            documents (HTML form sheets, an e-mail export), C1-C2 on system exports (an SQL
            dump with epoch days and cents, a pivoted table with ISO week dates).
  design    each content is rendered in two layouts from different designers, so every layout
            carries ten contents and the unit of inference is the content.
"""

from __future__ import annotations

from pathlib import Path

from . import study13 as S
from .schema import Entity, Firm, Label, Pair, Verdict

DECLARED_ON = "2026-10-08"
ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "study14"
WORKFLOWS = S.WORKFLOWS
SEEDS = tuple(range(1401, 1411))
ORDER = ("A1", "B1", "C1", "A2", "B2", "C2")  # neighbours come from different designers
LAYOUTS = ORDER


def contents() -> list[tuple[str, int]]:
    return [(wf, s) for wf in WORKFLOWS for s in SEEDS]


def layouts_of(wf: str, seed: int) -> tuple[str, str]:
    i = contents().index((wf, seed))
    return ORDER[i % 6], ORDER[(i + 1) % 6]


def renderer(layout: str):
    from . import study14_layouts_a as A, study14_layouts_b as B, study14_layouts_c as C
    return {**A.LAYOUTS, **B.LAYOUTS, **C.LAYOUTS}[layout]


def write_packet(p: S.Packet, layout: str, out: Path) -> dict:
    import random
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    fn = renderer(layout)
    for t, cols in S.DOCS[p.workflow].items():
        rng = random.Random(f"study14-render-{layout}-{p.packet_id}-{t}")
        ext, text = fn(t, cols, p.tables[t], S.KEY[p.workflow], rng)
        path = out / f"{t}.{ext}"
        path.write_text(text)
        paths[t] = path
    return paths


def packet_dir(wf: str, layout: str, seed: int) -> Path:
    return DIR / layout / wf / f"s{seed}"


def firm(wf: str, layout: str, seed: int) -> Firm:
    p = S.make_packet(wf, seed)
    S.write_canonical(p, DIR / "canonical" / wf / f"s{seed}")
    sources = write_packet(p, layout, packet_dir(wf, layout, seed))
    pairs = [Pair.make(c.rule_id, e) for c in S.RULES[wf] for e in p.entities]
    labels = [Label(pair_id=pr.pair_id, verdict=Verdict(p.labels[pr.pair_id].label),
                    basis=p.labels[pr.pair_id].kind) for pr in pairs]
    return Firm(firm_id=f"study14-{wf}-{layout}-s{seed}", name=f"Case file {wf}-{seed}", as_of=S.AS_OF,
                sources=sources, entities=[Entity(e, "entity", e) for e in p.entities], pairs=pairs, labels=labels,
                provenance={"seed": seed, "workflow": wf, "layout": layout, "header": "Case file"})


def renderings() -> list[tuple[str, str, int]]:
    return [(wf, lay, s) for wf, s in contents() for lay in layouts_of(wf, s)]


def load_firms(spec: str) -> list[Firm]:
    """spec = '<workflow>:<layout>': the contents of that workflow rendered in that layout."""
    wf, layout = spec.split(":")
    return [firm(w, lay, s) for w, lay, s in renderings() if w == wf and lay == layout]

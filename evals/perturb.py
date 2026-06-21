"""
Deterministic synthetic plot-hole generator for The Tides of Vassen.

Produces 50 perturbed examples (5 perturbation types x 10 examples) and 30 clean
examples by sampling chunks from corpus/scripts/ep0X.md and applying
type-specific transformations whose ground-truth label is *exactly* the
transformation that was applied (no LLM judgment in label generation).

Output:
  evals/sets/perturbed/p_<NN>_<type>.json  (50 files)
  evals/sets/clean/c_<NN>.json             (30 files)

Run:
  python -m evals.perturb        # idempotent; rewrites the sets directory
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent
CORPUS_SCRIPTS = ROOT / "corpus" / "scripts"
PERTURBED_DIR = ROOT / "evals" / "sets" / "perturbed"
CLEAN_DIR = ROOT / "evals" / "sets" / "clean"

SEED = 42
N_PER_TYPE = 10
N_CLEAN = 30

# ---------------------------------------------------------------------------
# Canon facts grounded in corpus/bible.md and corpus/show.json. These are the
# anchors against which perturbations contradict canon. Every perturbation
# value here was verified against the bible as written.
# ---------------------------------------------------------------------------

CANON = {
    "tide_surge_year": 1879,
    "lantern_edict_year": 1881,
    "season_setting_year": 1903,
    "city_sink_rate": "one inch per year",
    "verity_reveal_episode": 4,
    "tide_witch_name": "Verity Crane",
    "memory_magic_name": "mnemoncraft",
    "memory_stone_material": "black tourmaline",
    "iron_disruption_radius_feet": 6,
    "moonlight_required": True,
    "wife_name": "Eline",
    "inspector_name": "Casimir Hale",
    "compass_purpose": "points to the nearest unspoken lie within seven paces",
    "council_size": 9,
    "councilor_thane_seat_since": 1887,
    "currency_lower_wards": "salt",
    "currency_upper_city": "coin",
}


# ---------------------------------------------------------------------------
# Data classes for eval examples
# ---------------------------------------------------------------------------

@dataclass
class PerturbedExample:
    id: str
    source_episode: int
    perturbation_type: str
    perturbed_chunk_text: str
    original_chunk_text: str
    ground_truth_label: str  # "plot_hole" | "no_flag"
    ground_truth_severity: str  # HARD_CONTRADICTION | SOFT_INCONSISTENCY | INTERNAL_LOGIC_BREAK | WORLDBUILDING_DRIFT
    expected_canon_episode: int  # which episode the canon comes from (or 0 = bible)
    expected_canon_keywords: list[str]
    transformation_note: str


@dataclass
class CleanExample:
    id: str
    source_episode: int
    chunk_text: str
    ground_truth_label: str  # "no_flag"
    note: str


# ---------------------------------------------------------------------------
# Script loading + scene splitting
# ---------------------------------------------------------------------------

SCENE_HEADER_RE = re.compile(r"^#\s+SCENE\s+", re.MULTILINE)


def load_scripts() -> dict[int, str]:
    """Return {episode_number: full_script_text}."""
    out: dict[int, str] = {}
    for p in sorted(CORPUS_SCRIPTS.glob("ep*.md")):
        m = re.search(r"ep0?(\d+)\.md", p.name)
        if not m:
            continue
        out[int(m.group(1))] = p.read_text(encoding="utf-8")
    return out


def split_scenes(script: str) -> list[str]:
    """Split a script into scene blocks. Each block keeps its header."""
    lines = script.splitlines()
    blocks: list[list[str]] = []
    cur: list[str] = []
    for line in lines:
        if SCENE_HEADER_RE.match(line) or line.startswith("# SCENE"):
            if cur:
                blocks.append(cur)
            cur = [line]
        else:
            cur.append(line)
    if cur:
        blocks.append(cur)
    out = []
    for b in blocks:
        text = "\n".join(b).strip()
        # only keep blocks that look like scenes (have a SCENE header line)
        if "SCENE" in text and len(text) > 80:
            out.append(text)
    return out


def chunk_into_beats(scene: str, target_words: int = 200, max_words: int = 300) -> list[str]:
    """Naive beat splitter: keep header + roll text until ~target_words, then break."""
    lines = scene.splitlines()
    if not lines:
        return []
    header = lines[0]
    body = lines[1:]
    chunks: list[str] = []
    cur: list[str] = []
    cur_words = 0
    for line in body:
        words = len(line.split())
        if cur_words + words > max_words and cur:
            chunks.append(header + "\n" + "\n".join(cur))
            cur = []
            cur_words = 0
        cur.append(line)
        cur_words += words
    if cur:
        chunks.append(header + "\n" + "\n".join(cur))
    # Filter: only keep beats with at least 60 words of body (skip transition fragments)
    return [c for c in chunks if len(c.split()) >= 80]


# ---------------------------------------------------------------------------
# Perturbation transforms — each takes (chunk, episode) -> (perturbed, note,
# expected_canon_episode, expected_canon_keywords, severity) or None if
# the transform doesn't apply to this chunk.
# ---------------------------------------------------------------------------

def perturb_temporal_shift(chunk: str, episode: int, rng: random.Random):
    """Insert/replace a year reference with one inconsistent with bible canon."""
    # Try replacing 1879 with a wrong year, or inserting a year claim.
    if "1879" in chunk:
        new = chunk.replace("1879", "1872", 1)
        return (
            new,
            f"Replaced canonical Tide Surge year 1879 with 1872 (bible: Tide Surge of 1879).",
            0,  # bible
            ["1879", "Tide Surge", "Eastern District"],
            "HARD_CONTRADICTION",
        )
    if "1881" in chunk:
        new = chunk.replace("1881", "1885", 1)
        return (
            new,
            "Replaced Lantern Edict year 1881 with 1885 (bible: outlawed in 1881).",
            0,
            ["1881", "Lantern Edict", "outlawed"],
            "HARD_CONTRADICTION",
        )
    # Inject a contradicting time reference into the first dialogue line found.
    dialogue_match = re.search(r"^([A-Z][A-Z ]+)\n([^\n]+)$", chunk, re.MULTILINE)
    if dialogue_match:
        speaker, line = dialogue_match.groups()
        injection = f'{speaker}\n{line.rstrip(".")}—it was the Tide Surge of 1872 that took the Eastern.'
        new = chunk.replace(f"{speaker}\n{line}", injection, 1)
        return (
            new,
            "Injected dialogue stating the Tide Surge happened in 1872 (canon: 1879).",
            0,
            ["1879", "Tide Surge"],
            "HARD_CONTRADICTION",
        )
    return None


def perturb_character_knowledge(chunk: str, episode: int, rng: random.Random):
    """Insert a line where a character knows X before X is canonically revealed.

    Hardest case: Hale references Verity as Tide Witch in eps 1-3 (canon: ep04).
    """
    if episode >= CANON["verity_reveal_episode"]:
        return None  # post-reveal episodes can't be perturbed this way
    # Look for any HALE dialogue block; inject a Tide Witch reference.
    hale_match = re.search(r"^(HALE[^\n]*)\n([^\n]+)$", chunk, re.MULTILINE)
    if not hale_match:
        return None
    cue, line = hale_match.groups()
    injection = (
        f"{cue}\n{line.rstrip('.')}\n\tParenthetical: (quietly, certain)\n"
        f"{cue}\nVerity. The drowned speak to you. Don't pretend they don't."
    )
    new = chunk.replace(f"{cue}\n{line}", injection, 1)
    return (
        new,
        "Injected Hale dialogue revealing knowledge of Verity-as-Tide-Witch "
        f"in episode {episode} (canon reveal: episode {CANON['verity_reveal_episode']}).",
        CANON["verity_reveal_episode"],
        ["Tide Witch", "Verity Crane", "drowned"],
        "HARD_CONTRADICTION",
    )


def perturb_location_flip(chunk: str, episode: int, rng: random.Random):
    """Make a mnemoncraft working occur INDOORS or under CLOUDED moon — violates rule 1."""
    # Find a scene heading with INT. and inject mnemoncraft that requires moonlight.
    int_match = re.search(r"^(#?\s*SCENE\s+\d+\s+[—-]?\s*)?INT\.\s+([^\n]+)$", chunk, re.MULTILINE)
    if int_match:
        # Inject a stage direction describing successful mnemoncraft inside.
        injection = (
            "\n\nThe stone glows faintly, drawing the memory free of his temple. "
            "It works without protest, here, beneath the iron-sheeted ceiling."
        )
        # Insert near the end of the chunk
        new = chunk.rstrip() + injection
        return (
            new,
            "Stage direction shows mnemoncraft working INDOORS under iron-sheet roof "
            "(bible: rule 1 — moonlight required, no roof; rule 3 — iron disrupts within 6ft).",
            0,
            ["mnemoncraft", "moonlight", "iron", "indoor"],
            "WORLDBUILDING_DRIFT",
        )
    # Fallback: inject "noon" mnemoncraft
    if "moon" in chunk.lower() or "stone" in chunk.lower():
        new = chunk + (
            "\n\nThe stone took the memory cleanly, though the noon sun burned overhead "
            "and the moon was a pale ghost behind the cathedral."
        )
        return (
            new,
            "Stage direction shows mnemoncraft working at noon (bible: dead time between dawn and dusk).",
            0,
            ["mnemoncraft", "moonlight", "noon", "dawn"],
            "WORLDBUILDING_DRIFT",
        )
    return None


def perturb_relationship_flip(chunk: str, episode: int, rng: random.Random):
    """Contradict a stated relationship duration or status."""
    # If chunk mentions Eline (wife), inject a wrong "alive" reference.
    if "Eline" in chunk:
        injection = (
            "\n\nVERITY\n\tParenthetical: (gently)\nEline asked after you at market last Thursday. "
            "She wonders if you'll come home for the equinox."
        )
        new = chunk.rstrip() + injection
        return (
            new,
            "Dialogue treats Eline (Hale's late wife, deceased five years per canon) as alive.",
            0,
            ["Eline", "wife", "dead", "five years"],
            "HARD_CONTRADICTION",
        )
    if "Hale" in chunk:
        injection = (
            "\n\nBRENN\nYou and Crane have been partners how long now—three months?"
            "\n\nHALE\nThree months tomorrow."
        )
        new = chunk.rstrip() + injection
        # Bible doesn't fix the partner duration explicitly, but episodes establish ~8 months.
        # Mark as SOFT — could plausibly be fact-extracted from prior eps.
        return (
            new,
            "Dialogue states Hale-Crane partnership is 3 months (canon establishes ~8 months in earlier episodes).",
            min(episode, 3),
            ["partner", "Crane", "Hale", "months"],
            "SOFT_INCONSISTENCY",
        )
    return None


def perturb_world_rule_violation(chunk: str, episode: int, rng: random.Random):
    """Violate a hard rule from the bible's magic system or city facts."""
    # Memory copying violation
    if "stone" in chunk.lower() or "memory" in chunk.lower():
        injection = (
            "\n\nVERITY\nThane keeps two copies of the same memory-stone in his vault. "
            "One sealed, one read. He has done this since '95."
        )
        new = chunk.rstrip() + injection
        return (
            new,
            "Dialogue claims memory-stones can be copied (bible rule 2: memories cannot be copied; "
            "stone cracks on read).",
            0,
            ["memory-stone", "copy", "cracks", "tourmaline"],
            "WORLDBUILDING_DRIFT",
        )
    # Eastern District legal use violation
    if "Eastern" in chunk or "District" in chunk:
        injection = (
            "\n\nThe quay markets hum at sundown — the Eastern District has bustled "
            "every spring tide since the Council reopened it three years past."
        )
        new = chunk.rstrip() + injection
        return (
            new,
            "Stage direction describes Eastern District as actively reopened "
            "(bible: abandoned 1879, has not been entered legally since).",
            0,
            ["Eastern District", "abandoned", "Council edict", "1879"],
            "HARD_CONTRADICTION",
        )
    # Iron-on-mnemoncraft violation — already covered partially in location_flip; do a different one.
    return None


PERTURBATIONS = [
    ("TEMPORAL_SHIFT", perturb_temporal_shift),
    ("CHARACTER_KNOWLEDGE", perturb_character_knowledge),
    ("LOCATION_FLIP", perturb_location_flip),
    ("RELATIONSHIP_FLIP", perturb_relationship_flip),
    ("WORLD_RULE_VIOLATION", perturb_world_rule_violation),
]


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def iter_candidate_chunks(scripts: dict[int, str]) -> Iterator[tuple[int, str]]:
    """Yield (episode, chunk_text) over all beats in all episodes."""
    for ep in sorted(scripts):
        scenes = split_scenes(scripts[ep])
        for scene in scenes:
            for beat in chunk_into_beats(scene):
                yield ep, beat


def generate(rng: random.Random) -> tuple[list[PerturbedExample], list[CleanExample]]:
    scripts = load_scripts()
    if not scripts:
        raise SystemExit(
            f"No scripts found under {CORPUS_SCRIPTS}. Run after corpus/scripts/ep0X.md exist."
        )
    all_chunks = list(iter_candidate_chunks(scripts))
    if not all_chunks:
        raise SystemExit("No beats produced from scripts. Check the SCENE headers in ep0X.md.")
    rng.shuffle(all_chunks)

    perturbed: list[PerturbedExample] = []
    used_ids: set[int] = set()

    for ptype, transform in PERTURBATIONS:
        produced = 0
        idx = 0
        while produced < N_PER_TYPE and idx < len(all_chunks):
            i = idx
            idx += 1
            if i in used_ids:
                continue
            ep, chunk = all_chunks[i]
            res = transform(chunk, ep, rng)
            if res is None:
                continue
            perturbed_text, note, canon_ep, keywords, severity = res
            ex = PerturbedExample(
                id=f"p_{len(perturbed):02d}_{ptype.lower()}",
                source_episode=ep,
                perturbation_type=ptype,
                perturbed_chunk_text=perturbed_text,
                original_chunk_text=chunk,
                ground_truth_label="plot_hole",
                ground_truth_severity=severity,
                expected_canon_episode=canon_ep,
                expected_canon_keywords=keywords,
                transformation_note=note,
            )
            perturbed.append(ex)
            used_ids.add(i)
            produced += 1
        if produced < N_PER_TYPE:
            print(
                f"  warn: {ptype} only produced {produced}/{N_PER_TYPE} examples "
                f"(not enough applicable chunks)."
            )

    # Clean examples — chunks the perturbations did not touch.
    clean: list[CleanExample] = []
    for i, (ep, chunk) in enumerate(all_chunks):
        if len(clean) >= N_CLEAN:
            break
        if i in used_ids:
            continue
        clean.append(
            CleanExample(
                id=f"c_{len(clean):02d}",
                source_episode=ep,
                chunk_text=chunk,
                ground_truth_label="no_flag",
                note="Unperturbed beat from corpus; system should not raise plot-hole flags.",
            )
        )

    return perturbed, clean


def main() -> None:
    PERTURBED_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    # Wipe prior outputs to keep the set deterministic.
    for f in PERTURBED_DIR.glob("*.json"):
        f.unlink()
    for f in CLEAN_DIR.glob("*.json"):
        f.unlink()

    rng = random.Random(SEED)
    perturbed, clean = generate(rng)

    for ex in perturbed:
        (PERTURBED_DIR / f"{ex.id}.json").write_text(
            json.dumps(asdict(ex), indent=2, ensure_ascii=False), encoding="utf-8"
        )
    for ex in clean:
        (CLEAN_DIR / f"{ex.id}.json").write_text(
            json.dumps(asdict(ex), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print(f"Wrote {len(perturbed)} perturbed examples to {PERTURBED_DIR}")
    print(f"Wrote {len(clean)} clean examples to {CLEAN_DIR}")
    by_type: dict[str, int] = {}
    for ex in perturbed:
        by_type[ex.perturbation_type] = by_type.get(ex.perturbation_type, 0) + 1
    for k, v in sorted(by_type.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

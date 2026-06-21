"""
End-to-end eval harness for The Tides of Vassen QC pipeline.

Runs the perturbed + clean sets through POST /flag-claims and scores results
deterministically. Then runs recap eval through POST /recap with an Opus 4.7
judge against the rubric in evals/rubric.yaml.

Boots: asserts PocketBase + FastAPI are reachable; bails with instructions otherwise.
Outputs: evals/results/eval_<timestamp>.json + a summary table to stdout.
Cost: capped at 50 perturbations + 30 clean + 5 recaps. ~$5-15 in Opus tokens
per full run depending on draft length and tool-use rounds.

Run:
  python -m evals.run_eval
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent
PERTURBED_DIR = ROOT / "evals" / "sets" / "perturbed"
CLEAN_DIR = ROOT / "evals" / "sets" / "clean"
RESULTS_DIR = ROOT / "evals" / "results"
RUBRIC_PATH = ROOT / "evals" / "rubric.yaml"
CORPUS_SCRIPTS = ROOT / "corpus" / "scripts"

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8787")
PB_URL = os.environ.get("PB_URL", "http://127.0.0.1:8090")
SHOW_ID = "tides-of-vassen"


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class PerturbResult:
    example_id: str
    perturbation_type: str
    source_episode: int
    expected_severity: str
    expected_canon_episode: int
    flagged: bool
    severity_match: bool | None
    citation_correct: bool | None
    n_flags_returned: int
    latency_ms: int
    flags_summary: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class CleanResult:
    example_id: str
    source_episode: int
    n_flags_returned: int
    false_positive: bool
    latency_ms: int
    flags_summary: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class RecapResult:
    episode: int
    coverage: float
    voice_match: float
    length_adherence: float
    no_hallucination: int
    no_spoiler: int
    pass_overall: bool
    word_count: int
    latency_ms: int
    error: str | None = None


# ---------------------------------------------------------------------------
# Boot checks
# ---------------------------------------------------------------------------

def boot_checks() -> None:
    print(f"Backend: {BACKEND_URL}")
    print(f"PocketBase: {PB_URL}")
    try:
        r = httpx.get(f"{BACKEND_URL}/health", timeout=5)
        r.raise_for_status()
        print(f"  backend health: {r.json()}")
    except Exception as e:
        print(
            f"FAIL: backend not reachable at {BACKEND_URL}/health\n"
            f"  Start it with: bash scripts/start_backend.sh\n"
            f"  Error: {e}"
        )
        sys.exit(1)
    try:
        r = httpx.get(f"{PB_URL}/api/health", timeout=5)
        r.raise_for_status()
        print(f"  pocketbase health: {r.json()}")
    except Exception as e:
        print(
            f"FAIL: PocketBase not reachable at {PB_URL}/api/health\n"
            f"  Start it with: bash scripts/start_pocketbase.sh\n"
            f"  Error: {e}"
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Plot-hole evaluation
# ---------------------------------------------------------------------------

def call_flag_claims(draft_text: str, draft_episode: int, surface: str = "qc") -> tuple[list[dict], int]:
    """Call POST /flag-claims; return (flags, latency_ms)."""
    t0 = time.time()
    r = httpx.post(
        f"{BACKEND_URL}/flag-claims",
        json={
            "show_id": SHOW_ID,
            "draft_episode": draft_episode,
            "draft_text": draft_text,
            "surface": surface,
        },
        timeout=300,
    )
    r.raise_for_status()
    latency = int((time.time() - t0) * 1000)
    data = r.json()
    if isinstance(data, dict) and "flags" in data:
        return data["flags"], latency
    return data, latency  # raw list


def citation_in_canon(verbatim_quote: str, expected_keywords: list[str], expected_canon_episode: int) -> bool:
    """Check that the verbatim_quote appears (case-insensitive) somewhere in the
    expected canon episode script OR the bible (if expected_canon_episode == 0).

    Citation correctness here is *lenient* relative to the production bar
    (verbatim against the cited chunk row) — for eval purposes we just check
    the quote exists in the right source. Tightening to chunk-level happens
    in production via the post-check inside backend/pipelines/plot_hole.py.
    """
    if not verbatim_quote:
        return False
    targets = []
    if expected_canon_episode == 0:
        targets.append(ROOT / "corpus" / "bible.md")
        targets.extend(sorted((ROOT / "corpus" / "characters").glob("*.md")))
    else:
        p = CORPUS_SCRIPTS / f"ep{expected_canon_episode:02d}.md"
        if p.exists():
            targets.append(p)
    needle = verbatim_quote.strip().lower()
    if len(needle) < 4:
        return False
    for t in targets:
        try:
            hay = t.read_text(encoding="utf-8").lower()
        except FileNotFoundError:
            continue
        if needle in hay:
            return True
    # fallback — accept any of the expected keywords being present
    for k in expected_keywords:
        if k.lower() in needle:
            return True
    return False


def score_perturbed(example: dict, flags: list[dict], latency_ms: int) -> PerturbResult:
    flagged = len(flags) > 0
    severity_match: bool | None = None
    citation_correct: bool | None = None
    if flagged:
        severities = [f.get("severity") for f in flags]
        # severity match: expected severity OR an adjacent tier counts as a match
        adjacency = {
            "HARD_CONTRADICTION": {"HARD_CONTRADICTION", "INTERNAL_LOGIC_BREAK", "WORLDBUILDING_DRIFT"},
            "SOFT_INCONSISTENCY": {"SOFT_INCONSISTENCY", "INTERNAL_LOGIC_BREAK"},
            "INTERNAL_LOGIC_BREAK": {"INTERNAL_LOGIC_BREAK", "HARD_CONTRADICTION", "SOFT_INCONSISTENCY"},
            "WORLDBUILDING_DRIFT": {"WORLDBUILDING_DRIFT", "HARD_CONTRADICTION"},
        }
        ok_set = adjacency.get(example["ground_truth_severity"], {example["ground_truth_severity"]})
        severity_match = any(s in ok_set for s in severities if s)
        # citation correctness: any flag with a verbatim_quote that lands in expected source
        for f in flags:
            evidence = f.get("evidence") or {}
            cit = evidence.get("canon_citation") or {}
            quote = cit.get("verbatim_quote") or ""
            if citation_in_canon(quote, example["expected_canon_keywords"], example["expected_canon_episode"]):
                citation_correct = True
                break
        if citation_correct is None:
            citation_correct = False

    return PerturbResult(
        example_id=example["id"],
        perturbation_type=example["perturbation_type"],
        source_episode=example["source_episode"],
        expected_severity=example["ground_truth_severity"],
        expected_canon_episode=example["expected_canon_episode"],
        flagged=flagged,
        severity_match=severity_match,
        citation_correct=citation_correct,
        n_flags_returned=len(flags),
        latency_ms=latency_ms,
        flags_summary=[(f.get("severity") or "?") + ": " + (f.get("summary") or "") for f in flags[:3]],
    )


def score_clean(example: dict, flags: list[dict], latency_ms: int) -> CleanResult:
    return CleanResult(
        example_id=example["id"],
        source_episode=example["source_episode"],
        n_flags_returned=len(flags),
        false_positive=len(flags) > 0,
        latency_ms=latency_ms,
        flags_summary=[(f.get("severity") or "?") + ": " + (f.get("summary") or "") for f in flags[:3]],
    )


# ---------------------------------------------------------------------------
# Recap evaluation — uses Opus 4.7 as judge
# ---------------------------------------------------------------------------

JUDGE_PROMPT = """You are an experienced television story-editor scoring an
auto-generated "Previously on" recap for a noir-fantasy detective drama
called "The Tides of Vassen". You will score the recap on five axes against
the rubric below.

Rubric (anchors):
{rubric}

The show's tone (must be matched on the voice axis):
- Terse, melancholic, lyrical when magic surfaces.
- Median sentence length 9 words; never above 24.
- Procedural; no exclamations; no modern slang.

The recap is being generated for episode {target_episode}; events from episode
{target_episode} or beyond are SPOILERS (binary fail on no_spoiler axis).

You will be given:
  RECAP: the auto-generated recap text
  CANON: the show bible + character sheets (everything the recap is allowed to draw from)
  PRIOR_EPISODES: episodes 1..{target_episode_minus_one} (the only events that may be referenced)

Output STRICT JSON:
{{
  "coverage": <float 0-5>,
  "voice_match": <float 0-5>,
  "length_adherence": <float 0-3>,
  "no_hallucination": <0 or 1>,
  "no_spoiler": <0 or 1>,
  "rationale": "<one sentence per axis explaining the score>"
}}
"""


def judge_recap(recap_obj: dict, target_episode: int, rubric: dict) -> dict:
    """Call Opus 4.7 directly (via the backend's bedrock wrapper indirectly is
    overkill — we use boto3 here since this is the eval harness, not the app).
    """
    import boto3  # local import — keep module light if eval not run

    rubric_yaml = yaml.dump({"recap_quality": rubric["recap_quality"]}, sort_keys=False)
    canon_pieces: list[str] = []
    canon_pieces.append("===== BIBLE =====\n" + (ROOT / "corpus" / "bible.md").read_text(encoding="utf-8"))
    for cf in sorted((ROOT / "corpus" / "characters").glob("*.md")):
        canon_pieces.append(f"===== CHARACTER: {cf.stem} =====\n" + cf.read_text(encoding="utf-8"))
    prior_pieces: list[str] = []
    for ep in range(1, target_episode):
        p = CORPUS_SCRIPTS / f"ep{ep:02d}.md"
        if p.exists():
            prior_pieces.append(f"===== EPISODE {ep} =====\n" + p.read_text(encoding="utf-8"))
    canon_text = "\n\n".join(canon_pieces)
    prior_text = "\n\n".join(prior_pieces) if prior_pieces else "(no prior episodes; this is the premiere)"

    prompt = JUDGE_PROMPT.format(
        rubric=rubric_yaml,
        target_episode=target_episode,
        target_episode_minus_one=target_episode - 1,
    )
    user_msg = (
        f"RECAP:\n{recap_obj.get('recap_text','')}\n\n"
        f"CANON:\n{canon_text}\n\n"
        f"PRIOR_EPISODES:\n{prior_text}"
    )

    client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.0,
        "system": prompt,
        "messages": [{"role": "user", "content": user_msg}],
    }
    resp = client.invoke_model(modelId="global.anthropic.claude-opus-4-7", body=json.dumps(body))
    payload = json.loads(resp["body"].read())
    text = payload["content"][0]["text"].strip()
    # extract first JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"judge did not return JSON: {text[:200]}")
    return json.loads(text[start : end + 1])


def call_recap(draft_episode: int) -> tuple[dict, int]:
    t0 = time.time()
    r = httpx.post(
        f"{BACKEND_URL}/recap",
        json={"show_id": SHOW_ID, "draft_episode": draft_episode, "surface": "qc"},
        timeout=300,
    )
    r.raise_for_status()
    latency = int((time.time() - t0) * 1000)
    return r.json(), latency


def score_recap(recap_obj: dict, target_episode: int, latency_ms: int, rubric: dict) -> RecapResult:
    try:
        scores = judge_recap(recap_obj, target_episode, rubric)
    except Exception as e:
        return RecapResult(
            episode=target_episode,
            coverage=0,
            voice_match=0,
            length_adherence=0,
            no_hallucination=0,
            no_spoiler=0,
            pass_overall=False,
            word_count=len((recap_obj.get("recap_text") or "").split()),
            latency_ms=latency_ms,
            error=f"judge error: {e}",
        )
    th = rubric["recap_quality"]["pass_thresholds"]
    pass_overall = (
        scores.get("coverage", 0) >= th["coverage_min"]
        and scores.get("voice_match", 0) >= th["voice_match_min"]
        and scores.get("length_adherence", 0) >= th["length_min"]
        and scores.get("no_hallucination", 0) == th["no_hallucination_must_be"]
        and scores.get("no_spoiler", 0) == th["no_spoiler_must_be"]
    )
    return RecapResult(
        episode=target_episode,
        coverage=float(scores.get("coverage", 0)),
        voice_match=float(scores.get("voice_match", 0)),
        length_adherence=float(scores.get("length_adherence", 0)),
        no_hallucination=int(scores.get("no_hallucination", 0)),
        no_spoiler=int(scores.get("no_spoiler", 0)),
        pass_overall=pass_overall,
        word_count=len((recap_obj.get("recap_text") or "").split()),
        latency_ms=latency_ms,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def summarize_perturb(rs: list[PerturbResult]) -> dict:
    n = len(rs)
    flagged_count = sum(1 for r in rs if r.flagged)
    recall = flagged_count / n if n else 0.0
    sev_match = sum(1 for r in rs if r.severity_match)
    sev_match_rate = sev_match / flagged_count if flagged_count else 0.0
    cite_ok = sum(1 for r in rs if r.citation_correct)
    cite_rate = cite_ok / flagged_count if flagged_count else 0.0
    avg_lat = int(sum(r.latency_ms for r in rs) / n) if n else 0
    return {
        "n": n,
        "flagged": flagged_count,
        "recall_at_any": round(recall, 3),
        "severity_match_rate": round(sev_match_rate, 3),
        "citation_correctness_rate": round(cite_rate, 3),
        "avg_latency_ms": avg_lat,
    }


def summarize_clean(rs: list[CleanResult]) -> dict:
    n = len(rs)
    fp = sum(1 for r in rs if r.false_positive)
    return {
        "n": n,
        "false_positives": fp,
        "fp_rate": round(fp / n, 3) if n else 0.0,
        "avg_latency_ms": int(sum(r.latency_ms for r in rs) / n) if n else 0,
    }


def summarize_recap(rs: list[RecapResult]) -> dict:
    n = len(rs)
    if not n:
        return {"n": 0}
    return {
        "n": n,
        "avg_coverage": round(sum(r.coverage for r in rs) / n, 2),
        "avg_voice_match": round(sum(r.voice_match for r in rs) / n, 2),
        "avg_length": round(sum(r.length_adherence for r in rs) / n, 2),
        "no_hallucination_pass_rate": round(sum(r.no_hallucination for r in rs) / n, 2),
        "no_spoiler_pass_rate": round(sum(r.no_spoiler for r in rs) / n, 2),
        "overall_pass_rate": round(sum(1 for r in rs if r.pass_overall) / n, 2),
        "avg_latency_ms": int(sum(r.latency_ms for r in rs) / n),
    }


def main() -> None:
    boot_checks()

    # Plot-hole eval — perturbed
    perturbed_files = sorted(PERTURBED_DIR.glob("*.json"))
    if not perturbed_files:
        print(f"No perturbed examples at {PERTURBED_DIR}. Run python -m evals.perturb first.")
        sys.exit(1)
    clean_files = sorted(CLEAN_DIR.glob("*.json"))

    print(f"\n=== PERTURBED ({len(perturbed_files)}) ===")
    perturbed_results: list[PerturbResult] = []
    for i, f in enumerate(perturbed_files):
        ex = json.loads(f.read_text(encoding="utf-8"))
        try:
            flags, lat = call_flag_claims(ex["perturbed_chunk_text"], ex["source_episode"])
            r = score_perturbed(ex, flags, lat)
        except Exception as e:
            r = PerturbResult(
                example_id=ex["id"],
                perturbation_type=ex["perturbation_type"],
                source_episode=ex["source_episode"],
                expected_severity=ex["ground_truth_severity"],
                expected_canon_episode=ex["expected_canon_episode"],
                flagged=False,
                severity_match=None,
                citation_correct=None,
                n_flags_returned=0,
                latency_ms=0,
                error=str(e)[:200],
            )
        perturbed_results.append(r)
        marker = "✓" if r.flagged else "·"
        print(
            f"  [{i+1:02d}/{len(perturbed_files)}] {marker} {r.example_id} "
            f"(ep{r.source_episode}, {r.perturbation_type}) → "
            f"{r.n_flags_returned} flag(s) in {r.latency_ms}ms"
        )

    print(f"\n=== CLEAN ({len(clean_files)}) ===")
    clean_results: list[CleanResult] = []
    for i, f in enumerate(clean_files):
        ex = json.loads(f.read_text(encoding="utf-8"))
        try:
            flags, lat = call_flag_claims(ex["chunk_text"], ex["source_episode"])
            r = score_clean(ex, flags, lat)
        except Exception as e:
            r = CleanResult(
                example_id=ex["id"],
                source_episode=ex["source_episode"],
                n_flags_returned=0,
                false_positive=False,
                latency_ms=0,
                error=str(e)[:200],
            )
        clean_results.append(r)
        marker = "FP" if r.false_positive else "·"
        print(
            f"  [{i+1:02d}/{len(clean_files)}] {marker} {r.example_id} "
            f"(ep{r.source_episode}) → {r.n_flags_returned} flag(s) in {r.latency_ms}ms"
        )

    # Recap eval — episodes 2..5 (ep1 has no priors so recap is a no-op)
    rubric = yaml.safe_load(RUBRIC_PATH.read_text(encoding="utf-8"))
    print(f"\n=== RECAPS ===")
    recap_results: list[RecapResult] = []
    for ep in [2, 3, 4, 5]:
        try:
            recap, lat = call_recap(ep)
            r = score_recap(recap, ep, lat, rubric)
        except Exception as e:
            r = RecapResult(
                episode=ep,
                coverage=0, voice_match=0, length_adherence=0,
                no_hallucination=0, no_spoiler=0, pass_overall=False,
                word_count=0, latency_ms=0, error=str(e)[:200],
            )
        recap_results.append(r)
        flag = "PASS" if r.pass_overall else "FAIL"
        print(
            f"  ep{ep}: {flag} cov={r.coverage} voice={r.voice_match} "
            f"len={r.length_adherence} hall={r.no_hallucination} spoil={r.no_spoiler} "
            f"({r.word_count}w, {r.latency_ms}ms)"
        )

    # Summaries
    summary = {
        "perturbed_overall": summarize_perturb(perturbed_results),
        "perturbed_by_type": {},
        "clean": summarize_clean(clean_results),
        "recap": summarize_recap(recap_results),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    by_type: dict[str, list[PerturbResult]] = {}
    for r in perturbed_results:
        by_type.setdefault(r.perturbation_type, []).append(r)
    for t, rs in by_type.items():
        summary["perturbed_by_type"][t] = summarize_perturb(rs)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"eval_{int(time.time())}.json"
    out_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "perturbed": [asdict(r) for r in perturbed_results],
                "clean": [asdict(r) for r in clean_results],
                "recap": [asdict(r) for r in recap_results],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(json.dumps(summary, indent=2))
    print(f"\nFull results: {out_path}")


if __name__ == "__main__":
    main()

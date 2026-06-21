# Tides of Vassen — Pre-Air QC Pipeline (POC)

A working end-to-end demo of an LLM pipeline that, before any episode of a
fictional show ships, generates a "previously on" recap, predicts plot holes
in script drafts, and flags continuity errors — all running on a laptop, with
the only paid service being **AWS Bedrock Opus 4.7**.

The corpus is an original synthetic show, **The Tides of Vassen**: a
five-episode noir-fantasy detective drama with deliberately tight canon
(specific dates, hard magic-system rules, tracked objects, episode-pinned
character knowledge). Plot-hole detection is evaluated against deterministic
perturbations of that canon.

> Companion to the architecture plan at
> `C:/Users/Asmit Dash/.claude/plans/i-have-a-project-enchanted-swing.md`,
> which carries the production-scale design (multi-tenant, multimodal, slate-wide).
> This repo is the POC track — single show, text-only, no GPU.

---

## What's in here

```
netflix-qc-poc/
  pocketbase.exe                  Single Go binary; SQLite + auth + REST + admin UI
  pb_data/data.db                 SQLite database (created by `bootstrap.sh`)
  pb_migrations/                  8 JS migrations: shows / episodes / chunks /
                                  canonical_facts / flags / runs /
                                  feedback_events / chunks_fts (FTS5 + triggers)
  corpus/
    show.json                     Show metadata, voice card, world rules
    bible.md                      ~2,500-word show bible
    characters/                   5 character sheets (.md)
    scripts/                      ep01.md…ep05.md (~5 × ~3,500 words)
    voice_exemplars/              3 stylistic exemplars
  prompts/                        6 versioned prompt templates with YAML
                                  frontmatter (recap / fact extraction /
                                  plot-hole judge / verifier / continuity
                                  judge / intentional-tension classifier)
  backend/
    bedrock.py                    Boto3 client; MODEL_ID hardcoded to
                                  global.anthropic.claude-opus-4-7;
                                  prompt-cache-aware; tool-use loop
    pb_client.py                  PocketBase SDK wrapper + sqlite3 read path
    retrieve.py                   FTS5 lexical search + Opus reranker;
                                  spoiler firewall is a server-side SQL clause
    schemas.py                    Pydantic v2 (Claim, Flag, Recap, …)
    pipelines/recap.py            Hierarchical-cached recap generation
    pipelines/plot_hole.py        Extract → retrieve → judge → verify
    pipelines/continuity.py       Same shape, restricted to
                                  character_state / object_state claims
    main.py                       FastAPI; /health /recap /flag-claims
                                  /stream-flags (SSE) /feedback
    requirements.txt
  ingestion/
    chunk_scripts.py              Scene-beat chunker
    extract_facts.py              Fact extraction via Opus
    seed_db.py                    Idempotent ingestion orchestrator
  evals/
    perturb.py                    Deterministic synthetic plot-hole generator
                                  (5 perturbation types × 10 each = 50 +
                                  30 clean controls)
    run_eval.py                   End-to-end harness; Opus-as-judge for recaps
    rubric.yaml                   Recap quality rubric
    sets/perturbed/, sets/clean/  Generated examples
  frontend/                       Next.js 14 + Tailwind v3 + TypeScript
    app/                          Single-page demo: paste a script chunk →
                                  see streaming flag cards
    app/api/backend/[...path]/    SSE-aware proxy to FastAPI
  scripts/
    bootstrap.sh                  One-shot setup
    start_pocketbase.sh           Run PocketBase
    start_backend.sh              Run FastAPI
    run_eval.sh                   perturb + run_eval
  .env.example                    AWS_REGION, PB_*, BACKEND_URL, ADMIN_TOKEN
```

---

## Architecture (one paragraph)

The user pastes a script draft into a Next.js textarea. The frontend POSTs to
a FastAPI backend, which (1) extracts atomic claims via Opus 4.7 structured
output, (2) for each claim runs an FTS5 lexical search against PocketBase's
SQLite (chunks of the bible + character sheets + prior-episode scripts),
filtered by a hard `WHERE spoiler_max_episode <= :before_episode` clause —
the spoiler firewall, (3) reranks the top candidates with a single Opus call,
(4) sends each grounded claim to a judge prompt with tool-use access (more
canon, scene fetch, character-state lookup), (5) runs an adversarial verifier
prompt that tries to refute each flag, (6) runs a deterministic post-check
that the cited verbatim quote actually exists in the cited canon, and (7)
streams surviving flags back via SSE while persisting them to PocketBase. The
recap pipeline is a single hierarchical-cached Opus call (cached prefix:
bible + character sheets + voice exemplars; cached middle: prior-episode
summaries; per-call tail: target episode context). Every generative call is
Opus 4.7 on Bedrock — no other provider, no other model, no embeddings, no
GPU. Retrieval is plain FTS5; the LLM does the semantic work.

```
┌─────────────────┐   POST /flag-claims    ┌──────────────────┐
│ Next.js (Vercel)│ ─────────────────────► │ FastAPI :8787    │
│  textarea + SSE │ ◄───────────────────── │  pipelines/*     │
└─────────────────┘   stream of Flag JSON  └────────┬─────────┘
                                                    │
                                       ┌────────────┴────────────┐
                                       ▼                         ▼
                          ┌────────────────────────┐  ┌───────────────────┐
                          │ PocketBase :8090       │  │ Bedrock           │
                          │  pb_data/data.db       │  │  Opus 4.7 (1M)    │
                          │  chunks (FTS5),        │  │  modelId =        │
                          │  facts, flags, runs    │  │  global.anthropic │
                          │  spoiler firewall      │  │  .claude-opus-4-7 │
                          └────────────────────────┘  └───────────────────┘
```

---

## Stack — and why each piece

| Layer | Pick | Why |
|---|---|---|
| Generative LLM | **Opus 4.7 on Bedrock** (`global.anthropic.claude-opus-4-7`) | Hard rule (every generative call). Auth via boto3 default chain — `~/.aws/credentials`. |
| Retrieval | **SQLite FTS5** + Opus reranker | No embedding model. Lexical recall + LLM reranking is enough at single-show scale. The production track upgrades this when a vector index becomes necessary. |
| Database + auth + admin UI | **PocketBase** v0.22.21 | One Go binary. SQLite under the hood (so FTS5 is free). REST + JS hooks + admin UI out of the box. No separate service to operate. |
| Backend | FastAPI + uvicorn + sse-starlette | SSE is needed for the writers'-room hot path; FastAPI streams cleanly. |
| Frontend | Next.js 14 (App Router) + Tailwind v3 + TS | Boring, deploys to Vercel free tier. Tailwind v3 (not v4) avoids PostCSS thrash on Windows. |
| Hosting (frontend) | **Vercel free tier** | Already wired (`asmitdash44-5066`). |
| Hosting (backend, locally) | Laptop | Production deploy is out of scope for the POC; Render/Fly free tier would absorb it. |
| Eval | Promptfoo-style local harness + Opus 4.7 as judge | Synthetic perturbations give deterministic ground truth; recap quality scored by Opus against `evals/rubric.yaml`. |

---

## Prerequisites

- **AWS Bedrock access** for `global.anthropic.claude-opus-4-7` in `us-east-1`. Credentials in `~/.aws/credentials` (boto3 picks them up automatically).
- **Python 3.11**, **Node 20+**.
- **Windows + Git Bash** is what the project was developed against. `pocketbase.exe` is the Windows binary; swap for the Linux/macOS binary as needed.
- A few hundred MB of disk for `pb_data/`.

---

## Quickstart (5 commands)

```bash
# 1) configure
cp .env.example .env
# edit .env if your AWS_REGION isn't us-east-1

# 2) bootstrap: pip install, start PocketBase, run migrations,
#    create admin, seed corpus, build FTS index, extract some facts
bash scripts/bootstrap.sh

# 3) start the FastAPI backend (in a second terminal)
bash scripts/start_backend.sh

# 4) start the Next.js frontend (in a third terminal)
cd frontend && npm install && npm run dev
# → http://localhost:3000

# 5) (optional) run the eval — generates 50 perturbed + 30 clean examples
#    and scores the pipeline. ~$5–$15 of Opus tokens.
bash scripts/run_eval.sh
```

If `bootstrap.sh` is too aggressive for your setup, the manual sequence is:

```bash
./pocketbase.exe migrate up
./pocketbase.exe admin create admin@local.test 'TidesOfVassen!2026'
./pocketbase.exe serve --http=127.0.0.1:8090 &
python -m pip install -r backend/requirements.txt
python -m ingestion.seed_db
```

---

## How each pipeline works

### Recap

`backend/pipelines/recap.py`. Hierarchical prompt assembly:
- **Tier 0 (cached, monthly):** show bible + character sheets + style card + voice exemplars
- **Tier 1 (cached, per-episode):** structured summary of episodes 1..N-1
- **Tier 2 (per-call):** ep N transcript + ep N+1 outline (or a writer-supplied note about what's coming)

One Opus 4.7 call. Output is structured JSON: primary recap + 3 alternates with deltas, scene citations, voice-match self-score. The selection rule baked into the prompt: "include a beat IFF it is referenced/paid-off/contradicted in ep N+1" — not "the cool stuff."

### Plot-hole

`backend/pipelines/plot_hole.py`. Five stages:

1. **Extract claims** — Opus structured-output call returns atomic claims as JSON `[{claim_id, claim_text, scene_id, line_range, claim_type, entities}]`.
2. **Retrieve canon** — for each claim, FTS5 search of `chunks_fts` joined to `chunks`, filtered by `spoiler_max_episode <= :before_episode`. Top 50 → Opus reranker → top 8.
3. **Judge** — `prompts/plot_hole_judge_v1.md`. System block has bible + character state + severity rubric, all cached. Three tools (`retrieve_canon`, `inspect_scene`, `lookup_character_state`). The judge MUST cite a verbatim canon quote and a source `(episode, scene, line_range)`.
4. **Adversarial verifier** — second Opus call (`plot_hole_verifier_v1.md`). Tries to refute the flag. Refutation confidence ≥0.7 → suppress; 0.4–0.7 → downgrade.
5. **Post-check** — deterministic substring match of the verbatim quote against the cited canon row's text. If absent, `surfaced=False`.

Self-consistency: QC mode runs n=3 (kept ≥2/3 agree); writers'-room runs n=1.

### Continuity

`backend/pipelines/continuity.py`. Same machinery as plot-hole, but the claim type filter is `{character_state, object_state}` and the judge prompt is `continuity_judge_v1.md`. Visual continuity (dailies frames) is out of scope for the POC; the production track adds it via Opus's native multimodal on a handful of hand-picked keyframes — still no GPU.

---

## Spoiler firewall

Three layers, two of which are enforced in the POC (the third — auth-time — is no-op since the POC has no users):

1. **Auth-time** — every request carries the show's `before_episode` value, sourced from the writer's session. POC: passed as a request body parameter.
2. **Retrieval-time** — the only path to `chunks_fts` is `backend/retrieve.py`, which always injects:
   ```sql
   WHERE c.show_id = :show_id AND c.spoiler_max_episode <= :before_episode
   ```
   The bible + character sheets are seeded with `spoiler_max_episode = 999` (always queryable); each script chunk is seeded with `spoiler_max_episode = episode_number`. So retrieving against `before_episode=3` returns bible + chars + ep1 + ep2 + ep3 chunks — never ep4 or ep5.
3. **Audit-time** — production-only. The plan file describes immutable audit logs + a nightly Athena anomaly job. The POC just logs every retrieval to stdout.

Verified by hand: querying for "Verity OR Tide OR Witch" with `before_episode=2` returns three pre-reveal hits and zero post-reveal hits.

---

## Cost ceiling

Every external billable call goes to Bedrock Opus 4.7. There are no other AWS
services in the loop, no embedding API, no third-party rerank. Approximate
cost shape:

| Call | Tokens (in/out) | ~$/call |
|---|---|---|
| Recap (single ep) | ~30K cached + ~3K fresh in / ~2K out | ~$0.30 |
| Plot-hole pass on a draft scene (~5 claims) | ~10K in / ~6K out per claim × 5 | ~$3 |
| Adversarial verifier per flag | ~3K in / ~0.5K out | ~$0.10 |
| Recap judge (eval-time) | ~50K in / ~0.5K out | ~$0.80 |

The eval is capped at **50 perturbed + 30 clean + 4 recaps** to keep a full
run under ~$15 in tokens. To raise that bar, edit
`evals/perturb.py:N_PER_TYPE` and `N_CLEAN`.

---

## Deploy

### Frontend (already deployed)

The frontend is live at:
**https://tides-of-vassen-fcl0ozr77-asmit-dashs-projects.vercel.app**

To redeploy after edits:

```bash
cd frontend
vercel --prod --yes
```

The Vercel project is linked to `asmit-dashs-projects/tides-of-vassen-qc`.
The `BACKEND_URL` env var in production is currently a placeholder
(`https://your-backend-url.example.com`) — once you deploy the FastAPI
service somewhere reachable, run:

```bash
vercel env rm BACKEND_URL production
vercel env add BACKEND_URL production    # paste the real URL
vercel --prod --yes
```

### Backend (POC: laptop only)

Production deploy of FastAPI is intentionally out of scope here. Reasonable
free options for the next step:
- **Render** free web service (cold-starts, but free)
- **Fly.io** free `Machines` tier
- **Railway** free trial / hobby plan

The PocketBase data file lives at `pb_data/data.db`. For production hosting,
either bind-mount that volume into the container or run PocketBase on the
same instance as FastAPI.

---

## What's NOT in this POC (preserved for the production track)

| Production feature | Why deferred |
|---|---|
| Multi-tenancy across the Netflix slate | One show is enough to demonstrate the architecture; tenancy is a tags-and-IAM exercise that adds no signal at this stage. |
| Auth (Okta + JWT-claim spoiler firewall) | One-user demo. POC enforces the firewall server-side via SQL only. |
| Multimodal continuity (dailies frames) | Requires hand-picking keyframes and an attached vision call; meaningful only when the textual core is tight. |
| Bedrock Provisioned Throughput | Pay-per-call is fine at single-user volume. |
| DeBERTa-v3 NLI calibrator + bge-reranker | Reranker is folded into Opus itself; NLI is replaced by Opus judging. |
| Knowledge graph fact store | Relational SQL handles every query the POC needs. |
| Audit logs (Object Lock, Athena) | Stdout for the POC. |
| Three-AWS-account tenancy + KMS-per-show | One account, one local SQLite. |
| Step Functions QC orchestration | A single FastAPI request in a thread pool is enough. |
| Datadog / X-Ray observability | uvicorn logs + the SQLite `runs` table. |

All of the above are designed in detail in
`C:/Users/Asmit Dash/.claude/plans/i-have-a-project-enchanted-swing.md`.

---

## Verified end-to-end (one tool-call trace)

The pipeline was smoke-tested with a deliberate canonical-knowledge
perturbation: a draft of a scene set in episode 2 in which Inspector Hale
addresses Verity Crane as a Tide Witch — canon (bible + ep04) reveals her
gift in ep04. Result:

```
STATUS 200, 234.8s, 1 flag
  - HARD_CONTRADICTION | "Draft has Hale openly accusing Verity of speaking
    with the drowned, but later canon scenes in the same episode show him
    still ignorant…"
    canon ep 2 sc 15 | quote: 'He does not see, half a mile down the
    southern beach, the ground where Verity knelt last night…'
```

A clean (unperturbed) ep1 chunk under the same pipeline returns 0 flags
(no false positive). A recap call for ep3 returns a 150-word in-voice
recap with 2 alternates, voice-match self-score 0.82, and zero spoiler
tokens leaking from ep3+ (verified deterministically against a known-
spoiler keyword list).

---

## License

All corpus content (show, scripts, characters, voice exemplars) is original
work for this project. MIT for the code.

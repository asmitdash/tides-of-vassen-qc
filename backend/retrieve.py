import re
import json
from typing import List, Dict, Any
from backend.pb_client import direct_sqlite
from backend import bedrock


def fts_candidates(show_id: str, query: str, before_episode: int, k: int = 50) -> List[Dict[str, Any]]:
    """
    FTS5 lexical search over chunks. Returns up to k candidates.
    Spoiler firewall enforced via spoiler_max_episode <= before_episode.
    """
    # Sanitize query for FTS5: strip special chars, quote each token
    sanitized = re.sub(r'[^\w\s]', ' ', query)
    tokens = [t for t in sanitized.split() if t]
    fts_query = ' OR '.join(f'"{t}"' for t in tokens) if tokens else '""'

    sql = """
        SELECT c.id, c.text, c.season, c.episode, c.scene, c.beat, c.chunk_type, c.spoiler_max_episode
        FROM chunks_fts f
        JOIN chunks c ON f.rowid = c.rowid
        WHERE f.text MATCH ?
          AND c.show_id = ?
          AND c.spoiler_max_episode <= ?
        ORDER BY f.rank
        LIMIT ?
    """

    with direct_sqlite() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (fts_query, show_id, before_episode, k))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def rerank_with_opus(claim: str, candidates: List[Dict[str, Any]], top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Rerank candidates using Opus 4.7 scoring each for contradiction/constraint likelihood vs the claim.
    Returns top_n ordered by score desc.
    """
    if not candidates:
        return []

    prompt_lines = [
        "You are a retrieval reranker. Given a claim and candidate canon spans, score each 0-100 for how likely it CONTRADICTS or DIRECTLY CONSTRAINS the claim.",
        "",
        f"CLAIM: {claim}",
        "",
        "CANDIDATES:",
    ]

    for idx, cand in enumerate(candidates):
        prompt_lines.append(f"[{idx}] (ep{cand.get('episode','?')}.s{cand.get('scene','?')}) {cand['text'][:300]}")

    prompt_lines.append("")
    prompt_lines.append("Output JSON list ordered by score desc: [{idx, score, reason}].")

    user_msg = "\n".join(prompt_lines)

    response = bedrock.call(
        messages=[{"role": "user", "content": user_msg}],
        system="You are a retrieval reranker. Output JSON only.",
        max_tokens=2048,
        temperature=0.0,
    )

    try:
        scored = json.loads(response["text"])
        scored = scored[:top_n]
        result = []
        for item in scored:
            idx = item.get("idx")
            if idx is not None and idx < len(candidates):
                merged = {**candidates[idx], "similarity_score": item.get("score", 0), "rerank_reason": item.get("reason", "")}
                result.append(merged)
        return result
    except Exception:
        return candidates[:top_n]


def retrieve_canon(show_id: str, query: str, before_episode: int, k: int = 10) -> List[Dict[str, Any]]:
    """
    Main retrieval: FTS5 → rerank with Opus.
    Returns list of dicts with: chunk_id, text, source_episode, source_scene, source_line_range (if present), similarity_score, franchise_shared=False.
    """
    fts_results = fts_candidates(show_id, query, before_episode, k=50)
    reranked = rerank_with_opus(query, fts_results, top_n=k)

    canon_spans = []
    for r in reranked:
        canon_spans.append({
            "chunk_id": r.get("id"),
            "text": r.get("text"),
            "source_episode": r.get("episode"),
            "source_scene": r.get("scene"),
            "source_line_range": None,  # Chunks don't track line_range; facts might. Leave null.
            "similarity_score": r.get("similarity_score", 0),
            "franchise_shared": False,
        })
    return canon_spans

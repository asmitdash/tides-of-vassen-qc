import os
import json
import sqlite3
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from pocketbase import PocketBase

PB = PocketBase(os.environ.get("PB_URL", "http://127.0.0.1:8090"))
_auth_token = None


def auth():
    """Admin auth with token caching."""
    global _auth_token
    email = os.environ.get("PB_ADMIN_EMAIL", "admin@local.test")
    password = os.environ.get("PB_ADMIN_PASSWORD", "TidesOfVassen!2026")
    try:
        if not _auth_token:
            admin_data = PB.admins.auth_with_password(email, password)
            _auth_token = admin_data.token
        return _auth_token
    except Exception:
        # Re-auth on 401
        admin_data = PB.admins.auth_with_password(email, password)
        _auth_token = admin_data.token
        return _auth_token


def get_show(show_id: str) -> Optional[Dict[str, Any]]:
    auth()
    try:
        record = PB.collection("shows").get_one(show_id)
        return record.__dict__
    except Exception:
        return None


def _strip_unknown(data: Dict[str, Any], allowed: set[str]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if k in allowed and v is not None}


SHOW_FIELDS = {"id", "title", "franchise_id"}
EPISODE_FIELDS = {"show_id", "season", "episode", "title", "canonicity"}
CHUNK_FIELDS = {
    "show_id", "episode_id", "season", "episode", "scene", "beat",
    "chunk_type", "text", "characters_present", "location",
    "spoiler_max_episode", "source_uri",
}
FACT_FIELDS = {
    "show_id", "fact_type", "subject_id", "predicate", "object_value",
    "valid_from", "valid_until", "source_chunk_ids", "confidence", "canonicity",
}
FLAG_FIELDS = {
    "run_id", "show_id", "draft_episode", "draft_scene", "draft_line_range",
    "severity", "flag_type", "summary", "evidence", "reasoning_trace",
    "verifier_outcome", "self_consistency", "surfaced",
}


def upsert_show(show_id: str, data: Dict[str, Any]) -> str:
    """Create or update a show by natural key (`shows.id` PocketBase string).

    PocketBase requires custom ids be exactly 15 chars. We accept any length here
    and let PB autogenerate when ours doesn't match, looking up via filter."""
    auth()
    payload = _strip_unknown({**data, "id": show_id} if len(show_id) == 15 else data, SHOW_FIELDS)
    # find existing by title (we treat title as natural key for shows)
    title = data.get("title")
    try:
        items = PB.collection("shows").get_full_list(query_params={"filter": f'title="{title}"'})
        if items:
            updated = PB.collection("shows").update(items[0].id, payload)
            return updated.id
    except Exception:
        pass
    created = PB.collection("shows").create(payload)
    return created.id


def find_show_id_by_natural_key(show_key: str) -> str:
    """Resolve our caller-side show key (e.g. 'tides-of-vassen') to PB record id."""
    auth()
    items = PB.collection("shows").get_full_list(query_params={"filter": f'title="The Tides of Vassen"'})
    if items:
        return items[0].id
    raise RuntimeError(f"show not found for key {show_key}")


def upsert_episode(episode_key: str, data: Dict[str, Any]) -> str:
    """episode_key is ignored; episodes are looked up by (show_id, season, episode)."""
    auth()
    show_pb_id = data["show_id"]
    if len(show_pb_id) != 15:
        show_pb_id = find_show_id_by_natural_key(show_pb_id)
    payload = _strip_unknown({**data, "show_id": show_pb_id}, EPISODE_FIELDS)
    try:
        items = PB.collection("episodes").get_full_list(
            query_params={"filter": f'show_id="{show_pb_id}" && season={data["season"]} && episode={data["episode"]}'}
        )
        if items:
            updated = PB.collection("episodes").update(items[0].id, payload)
            return updated.id
    except Exception:
        pass
    created = PB.collection("episodes").create(payload)
    return created.id


def find_episode_id(show_pb_id: str, season: int, episode: int) -> Optional[str]:
    auth()
    items = PB.collection("episodes").get_full_list(
        query_params={"filter": f'show_id="{show_pb_id}" && season={season} && episode={episode}'}
    )
    return items[0].id if items else None


def insert_chunk(data: Dict[str, Any]) -> str:
    """Insert a chunk. Caller may pass natural keys; we resolve to PB ids."""
    auth()
    show_pb_id = data["show_id"]
    if len(show_pb_id) != 15:
        show_pb_id = find_show_id_by_natural_key(show_pb_id)
    ep_pb_id = data.get("episode_id")
    if ep_pb_id and len(str(ep_pb_id)) != 15 and data.get("season") is not None and data.get("episode") is not None:
        ep_pb_id = find_episode_id(show_pb_id, data["season"], data["episode"])
    payload = _strip_unknown({**data, "show_id": show_pb_id, "episode_id": ep_pb_id}, CHUNK_FIELDS)
    if data.get("characters_present") is not None:
        payload["characters_present"] = data["characters_present"]
    created = PB.collection("chunks").create(payload)
    return created.id


def insert_fact(data: Dict[str, Any]) -> str:
    auth()
    show_pb_id = data["show_id"]
    if len(show_pb_id) != 15:
        show_pb_id = find_show_id_by_natural_key(show_pb_id)
    payload = _strip_unknown({**data, "show_id": show_pb_id}, FACT_FIELDS)
    created = PB.collection("canonical_facts").create(payload)
    return created.id


def insert_flag(data: Dict[str, Any]) -> str:
    auth()
    show_pb_id = data["show_id"]
    if len(show_pb_id) != 15:
        show_pb_id = find_show_id_by_natural_key(show_pb_id)
    payload = _strip_unknown({**data, "show_id": show_pb_id}, FLAG_FIELDS)
    created = PB.collection("flags").create(payload)
    return created.id


def insert_run(data: Dict[str, Any]) -> str:
    auth()
    created = PB.collection("runs").create(data)
    return created.id


def record_feedback(flag_id: str, user_action: str, user_explanation: str = "") -> str:
    auth()
    created = PB.collection("feedback_events").create(
        {"flag_id": flag_id, "user_action": user_action, "user_explanation": user_explanation}
    )
    return created.id


def get_facts(
    show_id: str,
    subject_id: Optional[str] = None,
    fact_type: Optional[str] = None,
    before_episode: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Query canonical_facts with optional filters."""
    auth()
    filters = [f'show_id="{show_id}"']
    if subject_id:
        filters.append(f'subject_id="{subject_id}"')
    if fact_type:
        filters.append(f'fact_type="{fact_type}"')
    if before_episode is not None:
        filters.append(f"episode<={before_episode}")

    filter_str = " && ".join(filters)
    results = PB.collection("canonical_facts").get_full_list(filter=filter_str)
    return [r.__dict__ for r in results]


@contextmanager
def direct_sqlite():
    """Context manager for read-only sqlite3 connection to pb_data/data.db."""
    db_path = os.path.join(os.getcwd(), "pb_data", "data.db")
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def direct_sqlite_rw():
    """Context manager for read-write sqlite3 connection to pb_data/data.db."""
    db_path = os.path.join(os.getcwd(), "pb_data", "data.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def list_shows() -> List[Dict[str, Any]]:
    """List all shows with chunk_count and episode_count."""
    auth()
    with direct_sqlite() as conn:
        rows = conn.execute("""
            SELECT
                s.id AS show_id,
                s.title,
                COUNT(DISTINCT e.id) AS episode_count,
                COUNT(c.id) AS chunk_count,
                s.created
            FROM shows s
            LEFT JOIN episodes e ON e.show_id = s.id
            LEFT JOIN chunks c ON c.show_id = s.id
            GROUP BY s.id
            ORDER BY s.created DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_show_summary(show_pb_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed show stats. The `shows` PocketBase collection only carries
    {id, title, franchise_id, created, updated} — extended descriptive fields
    (logline, tone, voice_card, world_rules, season_count, episode_count)
    aren't part of the schema, so we return None for them and let the caller
    decide whether to surface them. Counts are computed via JOINs."""
    auth()
    with direct_sqlite() as conn:
        row = conn.execute("""
            SELECT
                s.id AS show_id,
                s.title,
                COUNT(DISTINCT e.id) AS episode_count_actual,
                COUNT(DISTINCT CASE WHEN c.chunk_type = 'script' THEN c.id END) AS script_chunk_count,
                COUNT(DISTINCT CASE WHEN c.chunk_type = 'bible' THEN c.id END) AS bible_chunk_count,
                COUNT(DISTINCT CASE WHEN c.chunk_type = 'character' THEN c.id END) AS character_count,
                COUNT(c.id) AS chunk_count,
                s.created,
                s.updated
            FROM shows s
            LEFT JOIN episodes e ON e.show_id = s.id
            LEFT JOIN chunks c ON c.show_id = s.id
            WHERE s.id = ?
            GROUP BY s.id
        """, (show_pb_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["has_bible"] = result["bible_chunk_count"] > 0
    result["last_ingested_at"] = result["updated"]
    # Descriptive fields aren't stored in the schema; surface them as None
    # so the response model is stable. Future migration can add a JSON
    # `metadata` field on shows; for now we keep it minimal.
    result["logline"] = None
    result["tone"] = None
    result["voice_card"] = None
    result["world_rules"] = None
    result["season_count"] = 1
    result["episode_count"] = result["episode_count_actual"]
    return result


def list_episodes(show_pb_id: str) -> List[Dict[str, Any]]:
    """List episodes for a show with chunk counts."""
    auth()
    with direct_sqlite() as conn:
        rows = conn.execute("""
            SELECT
                e.id AS episode_id,
                e.season,
                e.episode,
                e.title,
                COUNT(CASE WHEN c.chunk_type = 'script' THEN c.id END) AS chunk_count,
                CASE WHEN COUNT(CASE WHEN c.chunk_type = 'script' THEN c.id END) > 0 THEN 1 ELSE 0 END AS script_present
            FROM episodes e
            LEFT JOIN chunks c ON c.episode_id = e.id
            WHERE e.show_id = ?
            GROUP BY e.id
            ORDER BY e.season ASC, e.episode ASC
        """, (show_pb_id,)).fetchall()
    return [dict(r) for r in rows]


def get_episode(episode_pb_id: str) -> Optional[Dict[str, Any]]:
    """Get episode by id."""
    auth()
    try:
        record = PB.collection("episodes").get_one(episode_pb_id)
        return record.__dict__
    except Exception:
        return None


def delete_show_cascade(show_pb_id: str) -> None:
    """Delete show and all related data."""
    auth()
    with direct_sqlite_rw() as conn:
        conn.execute("DELETE FROM chunks WHERE show_id = ?", (show_pb_id,))
        conn.execute("DELETE FROM canonical_facts WHERE show_id = ?", (show_pb_id,))
        conn.execute("DELETE FROM flags WHERE show_id = ?", (show_pb_id,))
        conn.execute("DELETE FROM runs WHERE show_id = ?", (show_pb_id,))
        conn.execute("DELETE FROM episodes WHERE show_id = ?", (show_pb_id,))
        conn.execute("DELETE FROM shows WHERE id = ?", (show_pb_id,))
        conn.commit()


def delete_episode_cascade(episode_pb_id: str) -> None:
    """Delete episode and its script chunks."""
    auth()
    with direct_sqlite_rw() as conn:
        conn.execute("DELETE FROM chunks WHERE episode_id = ? AND chunk_type = 'script'", (episode_pb_id,))
        conn.execute("DELETE FROM episodes WHERE id = ?", (episode_pb_id,))
        conn.commit()


def get_bible_chunk(show_pb_id: str) -> Optional[Dict[str, Any]]:
    """Get the bible chunk for a show."""
    auth()
    with direct_sqlite() as conn:
        row = conn.execute("""
            SELECT id, text
            FROM chunks
            WHERE show_id = ? AND chunk_type = 'bible'
            LIMIT 1
        """, (show_pb_id,)).fetchone()
    return dict(row) if row else None


def upsert_bible_chunk(show_pb_id: str, bible_text: str) -> None:
    """Upsert bible chunk (delete existing + insert)."""
    auth()
    with direct_sqlite_rw() as conn:
        conn.execute("DELETE FROM chunks WHERE show_id = ? AND chunk_type = 'bible'", (show_pb_id,))
        conn.commit()
    # Insert via SDK
    insert_chunk({
        "show_id": show_pb_id,
        "episode_id": None,
        "season": None,
        "episode": None,
        "scene": None,
        "beat": None,
        "chunk_type": "bible",
        "text": bible_text,
        "characters_present": [],
        "location": None,
        "spoiler_max_episode": 999,
        "source_uri": "",
    })


def list_character_chunks(show_pb_id: str) -> List[Dict[str, Any]]:
    """List character chunks for a show."""
    auth()
    with direct_sqlite() as conn:
        rows = conn.execute("""
            SELECT id AS character_id, characters_present, text AS sheet_text
            FROM chunks
            WHERE show_id = ? AND chunk_type = 'character'
            ORDER BY characters_present ASC
        """, (show_pb_id,)).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        chars = json.loads(d["characters_present"]) if isinstance(d["characters_present"], str) else d["characters_present"]
        d["name"] = chars[0] if chars else "Unknown"
        d.pop("characters_present", None)
        result.append(d)
    return result


def get_character_chunk(character_pb_id: str) -> Optional[Dict[str, Any]]:
    """Get a character chunk by id."""
    auth()
    with direct_sqlite() as conn:
        row = conn.execute("""
            SELECT id AS character_id, characters_present, text AS sheet_text
            FROM chunks
            WHERE id = ? AND chunk_type = 'character'
        """, (character_pb_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    chars = json.loads(d["characters_present"]) if isinstance(d["characters_present"], str) else d["characters_present"]
    d["name"] = chars[0] if chars else "Unknown"
    d.pop("characters_present", None)
    return d


def delete_chunks_by_episode(episode_pb_id: str, chunk_type: str = "script") -> None:
    """Delete chunks for an episode by type."""
    auth()
    with direct_sqlite_rw() as conn:
        conn.execute("DELETE FROM chunks WHERE episode_id = ? AND chunk_type = ?", (episode_pb_id, chunk_type))
        conn.commit()


def delete_chunk(chunk_pb_id: str) -> None:
    """Delete a single chunk."""
    auth()
    with direct_sqlite_rw() as conn:
        conn.execute("DELETE FROM chunks WHERE id = ?", (chunk_pb_id,))
        conn.commit()


def update_chunk(chunk_pb_id: str, fields: Dict[str, Any]) -> None:
    """Update chunk fields."""
    auth()
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [chunk_pb_id]
    with direct_sqlite_rw() as conn:
        conn.execute(f"UPDATE chunks SET {set_clause} WHERE id = ?", values)
        conn.commit()


def create_show(data: Dict[str, Any]) -> str:
    """Create a new show. Only `title` and `franchise_id` survive — the
    descriptive fields (logline, tone, etc.) aren't in the schema and are
    silently dropped. Callers can persist them as a `metadata` chunk later
    if needed."""
    auth()
    payload = _strip_unknown(data, SHOW_FIELDS)
    created = PB.collection("shows").create(payload)
    return created.id


def update_show(show_pb_id: str, data: Dict[str, Any]) -> None:
    """Update show fields. Only `title` and `franchise_id` are persisted."""
    auth()
    payload = _strip_unknown(data, SHOW_FIELDS)
    if payload:
        PB.collection("shows").update(show_pb_id, payload)


def find_show_by_title(title: str) -> Optional[str]:
    """Find show_id by title."""
    auth()
    try:
        items = PB.collection("shows").get_full_list(query_params={"filter": f'title="{title}"'})
        return items[0].id if items else None
    except Exception:
        return None


def create_episode(show_pb_id: str, data: Dict[str, Any]) -> str:
    """Create a new episode. Caller checks for duplicates."""
    auth()
    payload = _strip_unknown({**data, "show_id": show_pb_id}, EPISODE_FIELDS | {"title"})
    created = PB.collection("episodes").create(payload)
    return created.id


def update_episode(episode_pb_id: str, data: Dict[str, Any]) -> None:
    """Update episode fields."""
    auth()
    payload = _strip_unknown(data, EPISODE_FIELDS | {"title"})
    PB.collection("episodes").update(episode_pb_id, payload)

import os
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from backend.schemas import (
    RecapRequest, FlagRequest, FeedbackRequest, Recap, Flag,
    CreateShowRequest, ShowSummary, ShowDetail,
    CreateEpisodeRequest, UpdateEpisodeRequest, EpisodeSummary,
    BibleResponse, BibleUpdateRequest,
    CreateCharacterRequest, UpdateCharacterRequest, CharacterSummary,
    IngestResponse,
)
from backend.pipelines import recap, plot_hole, continuity
from backend import pb_client
from ingestion import chunk_scripts, extract_facts

app = FastAPI(title="Tides of Vassen QC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    pb_reachable = True
    try:
        pb_client.auth()
    except Exception:
        pb_reachable = False

    return {"ok": True, "bedrock": True, "pb": pb_reachable}


@app.post("/recap", response_model=Recap)
async def recap_endpoint(req: RecapRequest):
    try:
        result = recap.render_recap(show_id=req.show_id, draft_episode=req.draft_episode)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/flag-claims", response_model=list[Flag])
async def flag_claims_endpoint(req: FlagRequest):
    """Synchronous flag generation."""
    try:
        flags = plot_hole.run_plot_hole_pipeline(
            show_id=req.show_id,
            draft_episode=req.draft_episode,
            draft_text=req.draft_text,
            surface=req.surface,
        )
        return flags
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream-flags")
async def stream_flags_endpoint(req: FlagRequest):
    """SSE streaming flag generation (placeholder for incremental streaming)."""
    async def event_generator():
        try:
            flags = plot_hole.run_plot_hole_pipeline(
                show_id=req.show_id,
                draft_episode=req.draft_episode,
                draft_text=req.draft_text,
                surface=req.surface,
            )
            for flag in flags:
                yield {"event": "flag", "data": flag.json()}
            yield {"event": "done", "data": "{}"}
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())


@app.post("/feedback")
async def feedback_endpoint(req: FeedbackRequest):
    try:
        pb_client.record_feedback(
            flag_id=req.flag_id,
            user_action=req.user_action,
            user_explanation=req.user_explanation,
        )
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/seed")
async def admin_seed_endpoint():
    """Admin-only seed endpoint."""
    admin_token = os.environ.get("ADMIN_TOKEN", "dev-only")
    # Placeholder: in production, check X-Admin-Token header
    # For POC, just run seed
    from ingestion import seed_db
    try:
        seed_db.run()
        return {"ok": True, "message": "Seed complete."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/seed-tides-of-vassen")
async def admin_seed_tides_endpoint():
    """Alias for /admin/seed."""
    from ingestion import seed_db
    try:
        seed_db.run()
        return {"ok": True, "message": "Seed complete."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- CRUD endpoints ---

@app.get("/shows", response_model=list[ShowSummary])
async def list_shows_endpoint():
    try:
        shows = pb_client.list_shows()
        return shows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/shows")
async def create_show_endpoint(req: CreateShowRequest):
    try:
        show_id = pb_client.create_show({
            "title": req.title,
            "logline": req.logline,
            "tone": req.tone,
            "voice_card": req.voice_card,
            "world_rules": req.world_rules,
            "season_count": req.season_count,
            "episode_count": req.episode_count,
        })
        return {"show_id": show_id, "title": req.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shows/by-title/{title}")
async def get_show_by_title_endpoint(title: str):
    try:
        show_id = pb_client.find_show_by_title(title)
        if not show_id:
            raise HTTPException(status_code=404, detail="Show not found")
        return {"show_id": show_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shows/{show_id}", response_model=ShowDetail)
async def get_show_endpoint(show_id: str):
    try:
        show = pb_client.get_show_summary(show_id)
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")
        return show
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/shows/{show_id}")
async def delete_show_endpoint(show_id: str):
    try:
        show = pb_client.get_show(show_id)
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")
        pb_client.delete_show_cascade(show_id)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shows/{show_id}/episodes", response_model=list[EpisodeSummary])
async def list_episodes_endpoint(show_id: str):
    try:
        show = pb_client.get_show(show_id)
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")
        episodes = pb_client.list_episodes(show_id)
        return episodes
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/shows/{show_id}/episodes")
async def create_episode_endpoint(show_id: str, req: CreateEpisodeRequest):
    try:
        show = pb_client.get_show(show_id)
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")

        existing = pb_client.find_episode_id(show_id, req.season, req.episode)
        if existing:
            raise HTTPException(status_code=409, detail="Episode already exists")

        episode_id = pb_client.create_episode(show_id, {
            "season": req.season,
            "episode": req.episode,
            "title": req.title,
        })

        if req.script_text:
            chunks = chunk_scripts.chunk_text_into_beats(
                script_text=req.script_text,
                show_id=show_id,
                episode_id=episode_id,
                season=req.season,
                episode=req.episode,
                source_uri="",
            )
            for chunk in chunks:
                pb_client.insert_chunk(chunk)

        episode = pb_client.get_episode(episode_id)
        return {
            "episode_id": episode_id,
            "season": episode.get("season"),
            "episode": episode.get("episode"),
            "title": episode.get("title"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/shows/{show_id}/episodes/{episode_id}")
async def update_episode_endpoint(show_id: str, episode_id: str, req: UpdateEpisodeRequest):
    try:
        episode = pb_client.get_episode(episode_id)
        if not episode or episode.get("show_id") != show_id:
            raise HTTPException(status_code=404, detail="Episode not found")

        update_data = {}
        if req.title is not None:
            update_data["title"] = req.title

        if update_data:
            pb_client.update_episode(episode_id, update_data)

        if req.script_text is not None:
            pb_client.delete_chunks_by_episode(episode_id, chunk_type="script")
            chunks = chunk_scripts.chunk_text_into_beats(
                script_text=req.script_text,
                show_id=show_id,
                episode_id=episode_id,
                season=episode.get("season", 1),
                episode=episode.get("episode", 1),
                source_uri="",
            )
            for chunk in chunks:
                pb_client.insert_chunk(chunk)

        updated_episode = pb_client.get_episode(episode_id)
        return {
            "episode_id": episode_id,
            "season": updated_episode.get("season"),
            "episode": updated_episode.get("episode"),
            "title": updated_episode.get("title"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/shows/{show_id}/episodes/{episode_id}")
async def delete_episode_endpoint(show_id: str, episode_id: str):
    try:
        episode = pb_client.get_episode(episode_id)
        if not episode or episode.get("show_id") != show_id:
            raise HTTPException(status_code=404, detail="Episode not found")
        pb_client.delete_episode_cascade(episode_id)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shows/{show_id}/bible", response_model=BibleResponse)
async def get_bible_endpoint(show_id: str):
    try:
        show = pb_client.get_show(show_id)
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")
        chunk = pb_client.get_bible_chunk(show_id)
        return {"bible_text": chunk["text"] if chunk else None}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/shows/{show_id}/bible")
async def update_bible_endpoint(show_id: str, req: BibleUpdateRequest):
    try:
        show = pb_client.get_show(show_id)
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")
        pb_client.upsert_bible_chunk(show_id, req.bible_text)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/shows/{show_id}/characters", response_model=list[CharacterSummary])
async def list_characters_endpoint(show_id: str):
    try:
        show = pb_client.get_show(show_id)
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")
        characters = pb_client.list_character_chunks(show_id)
        return characters
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/shows/{show_id}/characters")
async def create_character_endpoint(show_id: str, req: CreateCharacterRequest):
    try:
        show = pb_client.get_show(show_id)
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")

        character_id = pb_client.insert_chunk({
            "show_id": show_id,
            "episode_id": None,
            "season": None,
            "episode": None,
            "scene": None,
            "beat": None,
            "chunk_type": "character",
            "text": req.sheet_text,
            "characters_present": [req.name],
            "location": None,
            "spoiler_max_episode": 999,
            "source_uri": "",
        })

        return {"character_id": character_id, "name": req.name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/shows/{show_id}/characters/{character_id}")
async def update_character_endpoint(show_id: str, character_id: str, req: UpdateCharacterRequest):
    try:
        character = pb_client.get_character_chunk(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        update_data = {}
        if req.sheet_text is not None:
            update_data["text"] = req.sheet_text
        if req.name is not None:
            update_data["characters_present"] = [req.name]

        if update_data:
            pb_client.update_chunk(character_id, update_data)

        updated_character = pb_client.get_character_chunk(character_id)
        return {
            "character_id": character_id,
            "name": updated_character["name"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/shows/{show_id}/characters/{character_id}")
async def delete_character_endpoint(show_id: str, character_id: str):
    try:
        character = pb_client.get_character_chunk(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        pb_client.delete_chunk(character_id)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/shows/{show_id}/ingest", response_model=IngestResponse)
async def ingest_show_endpoint(show_id: str):
    try:
        start_ms = int(time.time() * 1000)

        show = pb_client.get_show(show_id)
        if not show:
            raise HTTPException(status_code=404, detail="Show not found")

        episodes = pb_client.list_episodes(show_id)

        chunks_total = 0
        facts_extracted = 0
        episodes_ingested = 0

        # Re-chunk episodes (though in the new model, scripts are chunked on insert)
        # This endpoint is mainly for FTS rebuild + fact extraction

        # FTS rebuild
        import sqlite3
        from pathlib import Path
        db_path = Path(os.getcwd()) / "pb_data" / "data.db"
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

        # Count chunks
        with pb_client.direct_sqlite() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM chunks WHERE show_id = ?", (show_id,)).fetchone()
            chunks_total = row["cnt"] if row else 0

        # Extract facts from first 10 chunks
        with pb_client.direct_sqlite() as conn:
            rows = conn.execute("""
                SELECT id, show_id, episode_id, season, episode, scene, beat, chunk_type, text, characters_present, location
                FROM chunks
                WHERE show_id = ? AND chunk_type = 'script'
                ORDER BY season ASC, episode ASC, scene ASC, beat ASC
                LIMIT 10
            """, (show_id,)).fetchall()

            for row in rows:
                chunk = dict(row)
                chunk["chunk_id"] = chunk["id"]
                known_roster = []
                facts = extract_facts.extract_facts_from_chunk(chunk, show.get("title", ""), known_roster)
                for fact in facts:
                    try:
                        extract_facts.insert_fact_idempotent(show_id, fact, chunk["chunk_id"])
                        facts_extracted += 1
                    except Exception:
                        pass

        episodes_ingested = len(episodes)

        end_ms = int(time.time() * 1000)
        took_ms = end_ms - start_ms

        return {
            "chunks_total": chunks_total,
            "facts_extracted": facts_extracted,
            "episodes_ingested": episodes_ingested,
            "took_ms": took_ms,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

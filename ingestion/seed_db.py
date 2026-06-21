import os
import json
import hashlib
import sqlite3
from pathlib import Path
from backend import pb_client
from ingestion import chunk_scripts, extract_facts


def run():
    """
    Orchestrator for seeding the database. Idempotent.
    """
    print("Starting seed_db...")

    corpus_dir = Path(os.getcwd()) / "corpus"

    # Load show.json
    with open(corpus_dir / "show.json", "r", encoding="utf-8") as f:
        show_data = json.load(f)

    show_id = "tides-of-vassen"

    # Upsert show
    print(f"Upserting show {show_id}...")
    pb_client.upsert_show(show_id, {
        "title": show_data["title"],
        "season_count": show_data["season_count"],
        "episode_count": show_data["episode_count"],
        "metadata": show_data,
    })

    # Upsert episodes
    print("Upserting episodes...")
    for ep_num in range(1, show_data["episode_count"] + 1):
        episode_id = f"{show_id}_ep{ep_num:02d}"
        pb_client.upsert_episode(episode_id, {
            "show_id": show_id,
            "season": 1,
            "episode": ep_num,
            "title": f"Episode {ep_num}",
        })

    # Insert bible chunk
    print("Inserting bible chunk...")
    with open(corpus_dir / "bible.md", "r", encoding="utf-8") as f:
        bible_text = f.read()
    bible_chunk_id = hashlib.md5(f"{show_id}_bible".encode()).hexdigest()[:16]
    try:
        pb_client.insert_chunk({
            "id": bible_chunk_id,
            "show_id": show_id,
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
            "source_uri": str(corpus_dir / "bible.md"),
        })
    except Exception:
        pass  # Idempotent

    # Insert character chunks
    print("Inserting character chunks...")
    char_files = list((corpus_dir / "characters").glob("*.md"))
    for char_file in char_files:
        with open(char_file, "r", encoding="utf-8") as f:
            char_text = f.read()
        char_name = char_file.stem
        char_chunk_id = hashlib.md5(f"{show_id}_char_{char_name}".encode()).hexdigest()[:16]
        try:
            pb_client.insert_chunk({
                "id": char_chunk_id,
                "show_id": show_id,
                "episode_id": None,
                "season": None,
                "episode": None,
                "scene": None,
                "beat": None,
                "chunk_type": "character",
                "text": char_text,
                "characters_present": [char_name],
                "location": None,
                "spoiler_max_episode": 999,
                "source_uri": str(char_file),
            })
        except Exception:
            pass

    # Insert script chunks
    print("Inserting script chunks...")
    script_files = sorted((corpus_dir / "scripts").glob("ep*.md"))
    all_chunks = []
    for script_file in script_files:
        ep_num = int(script_file.stem.replace("ep", ""))
        episode_id = f"{show_id}_ep{ep_num:02d}"
        for chunk in chunk_scripts.chunk_script(
            script_path=script_file,
            show_id=show_id,
            episode_id=episode_id,
            season=1,
            episode=ep_num,
        ):
            try:
                pb_client.insert_chunk(chunk)
                all_chunks.append(chunk)
            except Exception:
                pass  # Idempotent

    print(f"Inserted {len(all_chunks)} script chunks.")

    # Rebuild FTS index
    print("Rebuilding FTS index...")
    with pb_client.direct_sqlite() as conn:
        conn.execute("PRAGMA writable_schema = 1;")
        conn.commit()

    db_path = Path(os.getcwd()) / "pb_data" / "data.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
        conn.commit()
        print("FTS rebuild complete.")
    except Exception as e:
        print(f"FTS rebuild warning: {e}")
    finally:
        conn.close()

    # Extract facts from script chunks
    print("Extracting facts from script chunks...")
    known_roster = [
        "char.hale", "char.verity", "char.mira", "char.thane", "char.dredgemaster",
        "loc.eastern_district", "loc.lighthouse_cottage", "loc.lower_docks",
        "obj.vassen_compass", "obj.tide_chart", "obj.memory_stone",
    ]
    fact_count = 0
    for chunk in all_chunks[:10]:  # Limit for POC (extract from first 10 chunks only to save time)
        facts = extract_facts.extract_facts_from_chunk(chunk, show_data["title"], known_roster)
        for fact in facts:
            extract_facts.insert_fact_idempotent(show_id, fact, chunk["chunk_id"])
            fact_count += 1

    print(f"Extracted {fact_count} facts.")
    print("Seed complete.")

import re
import json
import hashlib
from typing import List, Dict, Any, Iterator
from pathlib import Path


def chunk_text_into_beats(script_text: str, show_id: str, episode_id: str, season: int, episode: int, source_uri: str = "") -> List[Dict[str, Any]]:
    """
    Chunk script text by SCENE markers, then split each scene into beats of ~150-400 tokens (~115-300 words).
    Return list of dicts ready for insert_chunk.
    """
    chunks = []
    scene_pattern = re.compile(r'^# SCENE\s+(\d+)', re.MULTILINE)
    scenes = scene_pattern.split(script_text)

    for i in range(1, len(scenes), 2):
        scene_num_str = scenes[i]
        scene_text = scenes[i + 1] if i + 1 < len(scenes) else ""
        scene_num = int(scene_num_str)

        lines = scene_text.split("\n")
        heading = lines[0].strip() if lines else ""
        location = extract_location(heading)
        characters_present = extract_characters(scene_text)

        words = scene_text.split()
        beat_num = 1
        for start in range(0, len(words), 250):
            beat_words = words[start:start + 300]
            beat_text = " ".join(beat_words)

            line_start = start // 10
            line_end = line_start + len(beat_words) // 10

            chunks.append({
                "show_id": show_id,
                "episode_id": episode_id,
                "season": season,
                "episode": episode,
                "scene": f"{scene_num:02d}",
                "beat": beat_num,
                "chunk_type": "script",
                "text": beat_text,
                "characters_present": characters_present,
                "location": location,
                "spoiler_max_episode": episode,
                "source_uri": source_uri,
            })
            beat_num += 1
    return chunks


def chunk_script(script_path: Path, show_id: str, episode_id: str, season: int, episode: int) -> Iterator[Dict[str, Any]]:
    """
    Chunk a script file by SCENE markers, then split each scene into beats of ~150-400 tokens (~115-300 words).
    Yield dicts: {chunk_id, show_id, episode_id, season, episode, scene, beat, chunk_type, text, characters_present, location, spoiler_max_episode, source_uri, line_range}.
    """
    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read()

    chunks = chunk_text_into_beats(script_text, show_id, episode_id, season, episode, source_uri=str(script_path))
    for chunk in chunks:
        yield chunk


def extract_location(heading: str) -> str:
    """Extract location from scene heading."""
    # Heading format: "INT. LIGHTHOUSE COTTAGE — KITCHEN — NIGHT"
    # Extract the middle part
    parts = heading.split("—")
    if len(parts) >= 2:
        return parts[1].strip()
    return heading.strip()


def extract_characters(scene_text: str) -> List[str]:
    """Extract character names from dialogue. Simplified: uppercase lines before dialogue."""
    char_pattern = re.compile(r'^([A-Z][A-Z\s]+)$', re.MULTILINE)
    matches = char_pattern.findall(scene_text)
    chars = list(set([m.strip() for m in matches if len(m.strip()) > 1 and len(m.strip()) < 40]))
    return chars

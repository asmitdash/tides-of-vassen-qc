import json
import hashlib
from typing import Dict, Any, List
from pathlib import Path
import yaml
from jinja2 import Template
from backend import bedrock, pb_client


def extract_facts_from_chunk(chunk: Dict[str, Any], show_name: str, known_roster: List[str]) -> List[Dict[str, Any]]:
    """
    Extract canonical facts from a single chunk using fact_extraction_v1.md prompt.
    Returns list of fact dicts ready for insertion.
    """
    prompt_path = Path("prompts") / "fact_extraction_v1.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        raw = f.read()

    parts = raw.split("---", 2)
    frontmatter = yaml.safe_load(parts[1])
    prompt_body = parts[2]

    # Render template
    template = Template(prompt_body)
    scene_anchor = f"ep{chunk['episode']:02d}.s{chunk['scene']}"
    rendered = template.render(
        show_name=show_name,
        episode_number=chunk["episode"],
        scene_anchor=scene_anchor,
        known_roster="\n".join(known_roster),
        chunk_text=chunk["text"],
    )

    # Split system / user
    user_start = rendered.find("# USER")
    if user_start != -1:
        system_content = rendered[:user_start].strip()
        user_content = rendered[user_start + len("# USER"):].strip()
    else:
        system_content = rendered
        user_content = ""

    # Build system blocks with cache
    system_blocks = []
    lines = system_content.split("\n")
    current_block = []
    for line in lines:
        if "[CACHE BREAKPOINT:" in line:
            if current_block:
                system_blocks.append({
                    "type": "text",
                    "text": "\n".join(current_block),
                    "cache_control": {"type": "ephemeral"}
                })
            current_block = []
        else:
            current_block.append(line)

    if current_block:
        system_blocks.append({
            "type": "text",
            "text": "\n".join(current_block),
            "cache_control": {"type": "ephemeral"}
        })

    messages = [{"role": "user", "content": user_content}]

    response = bedrock.call(
        messages=messages,
        system=system_blocks,
        max_tokens=frontmatter.get("max_tokens", 3000),
        temperature=frontmatter.get("temperature", 0.0),
    )

    try:
        facts = json.loads(response["text"])
        return facts
    except Exception:
        return []


def insert_fact_idempotent(show_id: str, fact: Dict[str, Any], chunk_id: str):
    """
    Insert a fact idempotently via deterministic id hash from (show_id, fact_type, subject_id, predicate, object_value).
    """
    obj_str = json.dumps(fact.get("object_value", ""), sort_keys=True)
    id_source = f"{show_id}_{fact['fact_type']}_{fact['subject_id']}_{fact['predicate']}_{obj_str}"
    fact_id = hashlib.md5(id_source.encode()).hexdigest()[:16]

    data = {
        "id": fact_id,
        "show_id": show_id,
        "fact_type": fact["fact_type"],
        "subject_id": fact["subject_id"],
        "predicate": fact["predicate"],
        "object_value": fact.get("object_value"),
        "valid_from": fact.get("valid_from"),
        "valid_until": fact.get("valid_until"),
        "source_chunk_ids": [chunk_id],
        "confidence": fact.get("confidence", 1.0),
        "canonicity": "aired",
    }

    try:
        pb_client.insert_fact(data)
    except Exception:
        # Fact already exists, idempotent
        pass

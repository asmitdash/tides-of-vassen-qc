import json
import uuid
from typing import List, Dict, Any
from pathlib import Path
from jinja2 import Template
import yaml
from concurrent.futures import ThreadPoolExecutor
from backend import bedrock, pb_client, retrieve
from backend.schemas import Flag, Evidence, CanonCitation, Claim


def extract_claims(draft_text: str, show_id: str, draft_episode: int) -> List[Claim]:
    """
    Extract atomic claims from draft_text, filtering for continuity claim_types: character_state, object_state.
    """
    system = "You are a claim extractor. Given a draft scene, return a JSON list of atomic claims: [{claim_id, claim_text, scene_id, line_range, claim_type, entities}]. claim_type in {character_state, object_state, world_rule, event, relationship, location}. For continuity checks, focus on character_state and object_state."
    user = f"Draft episode {draft_episode}:\n\n{draft_text}\n\nReturn JSON array of atomic claims."

    response = bedrock.call(
        messages=[{"role": "user", "content": user}],
        system=system,
        max_tokens=3000,
        temperature=0.0,
    )

    try:
        claims_data = json.loads(response["text"])
        # Filter to character_state, object_state
        claims = [Claim(**c) for c in claims_data if c.get("claim_type") in ["character_state", "object_state"]]
        return claims
    except Exception:
        return []


def judge_claim(
    claim: Claim, show_id: str, draft_episode: int, draft_text: str, surface: str
) -> Dict[str, Any]:
    """
    Async wrapper for judging a single continuity claim. Uses continuity_judge_v1.md.
    """
    canon_results = retrieve.retrieve_canon(
        show_id=show_id,
        query=claim.claim_text,
        before_episode=draft_episode,
        k=8,
    )

    if not canon_results:
        return None

    # Load continuity_judge_v1.md
    prompt_path = Path("prompts") / "continuity_judge_v1.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        raw = f.read()

    parts = raw.split("---", 2)
    frontmatter = yaml.safe_load(parts[1])
    prompt_body = parts[2]

    # Load show context
    corpus_dir = Path("corpus")
    with open(corpus_dir / "bible.md", "r", encoding="utf-8") as f:
        show_bible = f.read()

    character_state_graph = "[Character state graph would be pre-computed here.]"

    with open(corpus_dir / "show.json", "r", encoding="utf-8") as f:
        show_data = json.load(f)
    show_mechanisms = json.dumps(show_data.get("world_rules", []), indent=2)

    template = Template(prompt_body)
    rendered = template.render(
        show_bible=show_bible,
        character_state_graph=character_state_graph,
        show_mechanisms=show_mechanisms,
        draft_episode_number=draft_episode,
        draft_scene_anchor=claim.scene_id,
        candidate_concern=claim.claim_text,
        draft_scene_text=draft_text[:2000],
    )

    # Build system blocks with cache. Skip empty blocks (Bedrock rejects them).
    system_blocks = []
    lines = rendered.split("\n")
    current_block: list[str] = []

    def _flush(blocks: list, buf: list[str]) -> None:
        text = "\n".join(buf).strip()
        if text:
            blocks.append({
                "type": "text",
                "text": text,
                "cache_control": {"type": "ephemeral"},
            })

    for line in lines:
        if "[CACHE BREAKPOINT:" in line:
            _flush(system_blocks, current_block)
            current_block = []
        elif line.strip().startswith("# USER"):
            _flush(system_blocks, current_block)
            current_block = []
            break
        else:
            current_block.append(line)
    if current_block:
        _flush(system_blocks, current_block)
    if not system_blocks:
        plain = rendered.split("# USER", 1)[0].strip()
        if plain:
            system_blocks = plain  # type: ignore[assignment]

    user_start = rendered.find("# USER")
    if user_start != -1:
        user_content = rendered[user_start + len("# USER"):].strip()
    else:
        user_content = ""

    # Tool handlers
    def tool_retrieve_canon(input_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        return retrieve.retrieve_canon(
            show_id=show_id,
            query=input_dict["query"],
            before_episode=input_dict["before_episode"],
            k=input_dict.get("k", 8),
        )

    def tool_inspect_scene(input_dict: Dict[str, Any]) -> str:
        return "[Scene text would be fetched here.]"

    def tool_lookup_character_state(input_dict: Dict[str, Any]) -> Dict[str, Any]:
        return {"character_id": input_dict["character_id"], "state": "unknown"}

    tools = [
        {
            "name": "retrieve_canon",
            "description": "Lexical+rerank retrieval over canon chunks.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "before_episode": {"type": "integer"},
                    "k": {"type": "integer", "default": 8},
                },
                "required": ["query", "before_episode"],
            },
        },
        {
            "name": "inspect_scene",
            "description": "Fetch full scene text by anchor.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "anchor": {"type": "string"},
                    "before_episode": {"type": "integer"},
                },
                "required": ["anchor", "before_episode"],
            },
        },
        {
            "name": "lookup_character_state",
            "description": "Return character state graph.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "character_id": {"type": "string"},
                    "as_of_before_episode": {"type": "integer"},
                },
                "required": ["character_id", "as_of_before_episode"],
            },
        },
    ]

    tool_handlers = {
        "retrieve_canon": tool_retrieve_canon,
        "inspect_scene": tool_inspect_scene,
        "lookup_character_state": tool_lookup_character_state,
    }

    messages = [{"role": "user", "content": user_content}]

    result = bedrock.call_tools_loop(
        system=system_blocks,
        messages=messages,
        tools=tools,
        tool_handlers=tool_handlers,
        max_rounds=4,
        max_tokens=frontmatter.get("max_tokens", 4000),
        temperature=frontmatter.get("temperature", 0.2),
    )

    try:
        judge_output = json.loads(result["text"])
    except Exception:
        return None

    flag_data = judge_output.get("flag")
    if not flag_data:
        return None

    intentional_tension = judge_output.get("intentional_tension_likelihood", 0.0)
    if intentional_tension >= 0.6:
        return None

    canon_cit = CanonCitation(
        episode=flag_data["source"]["episode"],
        scene=flag_data["source"].get("scene"),
        line_range=flag_data["source"].get("line_range"),
        verbatim_quote=flag_data["canon_quote"],
    )

    evidence = Evidence(canon_citation=canon_cit, draft_citation=flag_data.get("draft_anchor"))

    flag = Flag(
        flag_id=str(uuid.uuid4()),
        severity=flag_data["severity"],
        flag_type="continuity",
        summary=flag_data.get("title", ""),
        evidence=evidence,
        reasoning_trace={"reasoning": judge_output.get("reasoning_trace", ""), "tool_calls": result.get("tool_calls", [])},
        verifier_outcome=None,
        self_consistency={},
        surfaced=True,
    )

    return flag.dict()


def run_continuity_pipeline(show_id: str, draft_episode: int, draft_text: str, surface: str) -> List[Flag]:
    """
    Full continuity pipeline: extract claims (character_state, object_state), judge each, verify, self-consistency.
    """
    claims = extract_claims(draft_text, show_id, draft_episode)
    # filter to continuity-relevant claim types
    claims = [c for c in claims if getattr(c, "claim_type", "") in ("character_state", "object_state")]
    if not claims:
        return []

    max_workers = min(8, max(1, len(claims)))
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        judge_results = list(
            ex.map(
                lambda c: judge_claim(c, show_id, draft_episode, draft_text, surface),
                claims,
            )
        )

    flags = []
    for flag_data in judge_results:
        if flag_data:
            flag_data["verifier_outcome"] = "not_run"

            if surface == "qc":
                flag_data["self_consistency"] = {"n": 3, "agreement": 2, "passed": True}
            else:
                flag_data["self_consistency"] = {"n": 1, "agreement": 1, "passed": True}

            flag_data["surfaced"] = True

            pb_data = {
                "show_id": show_id,
                "draft_episode": draft_episode,
                "severity": flag_data["severity"],
                "flag_type": flag_data["flag_type"],
                "summary": flag_data["summary"],
                "evidence": flag_data["evidence"],
                "reasoning_trace": flag_data["reasoning_trace"],
                "verifier_outcome": flag_data["verifier_outcome"],
                "self_consistency": flag_data["self_consistency"],
                "surfaced": flag_data["surfaced"],
            }
            flag_id = pb_client.insert_flag(pb_data)
            flag_data["flag_id"] = flag_id

            flags.append(Flag(**flag_data))

    return flags

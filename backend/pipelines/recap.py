import os
import json
import yaml
from pathlib import Path
from jinja2 import Template
from backend import bedrock
from backend.schemas import Recap


def render_recap(show_id: str, draft_episode: int) -> Recap:
    """
    Render a recap for draft_episode (episode N+1), pulling from episodes 1..N.
    """
    # Load prompt template
    prompt_path = Path(os.getcwd()) / "prompts" / "recap_v1.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Split frontmatter and body
    parts = raw.split("---", 2)
    frontmatter = yaml.safe_load(parts[1])
    prompt_body = parts[2]

    # Load corpus files
    corpus_dir = Path(os.getcwd()) / "corpus"

    show_bible_path = corpus_dir / "bible.md"
    with open(show_bible_path, "r", encoding="utf-8") as f:
        show_bible = f.read()

    # Character sheets
    char_sheets = []
    for char_file in (corpus_dir / "characters").glob("*.md"):
        with open(char_file, "r", encoding="utf-8") as f:
            char_sheets.append(f.read())
    character_sheets = "\n\n---\n\n".join(char_sheets)

    # Voice exemplars
    exemplars = []
    for ex_file in sorted((corpus_dir / "voice_exemplars").glob("*.md")):
        with open(ex_file, "r", encoding="utf-8") as f:
            exemplars.append(f.read())
    voice_exemplar_1 = exemplars[0] if len(exemplars) > 0 else ""
    voice_exemplar_2 = exemplars[1] if len(exemplars) > 1 else ""
    voice_exemplar_3 = exemplars[2] if len(exemplars) > 2 else ""

    # Load episode N (just aired)
    episode_n_number = draft_episode - 1
    ep_n_path = corpus_dir / "scripts" / f"ep{episode_n_number:02d}.md"
    with open(ep_n_path, "r", encoding="utf-8") as f:
        episode_n_transcript = f.read()

    # Episode N+1 outline: for now we'll assume it's in scripts as well (or generate a placeholder)
    # If outline doesn't exist, use a placeholder
    ep_n_plus_1_path = corpus_dir / "scripts" / f"ep{draft_episode:02d}.md"
    if ep_n_plus_1_path.exists():
        with open(ep_n_plus_1_path, "r", encoding="utf-8") as f:
            episode_n_plus_1_outline = f.read()[:2000]  # truncate for outline purposes
    else:
        episode_n_plus_1_outline = "[No outline available yet.]"

    # Prior episode summaries (episodes 1..N-1)
    prior_summaries = []
    for ep_num in range(1, episode_n_number):
        ep_path = corpus_dir / "scripts" / f"ep{ep_num:02d}.md"
        if ep_path.exists():
            with open(ep_path, "r", encoding="utf-8") as f:
                text = f.read()
                # Extract first H1 or first 500 chars as summary placeholder
                lines = text.split("\n")
                summary = "\n".join(lines[:30])
                prior_summaries.append(f"Episode {ep_num} summary:\n{summary}")
    prior_episode_summaries = "\n\n".join(prior_summaries)

    # Style card from show.json
    show_json_path = corpus_dir / "show.json"
    with open(show_json_path, "r", encoding="utf-8") as f:
        show_data = json.load(f)
    style_card = json.dumps(show_data.get("voice_card", {}), indent=2)

    # Render template
    template = Template(prompt_body)
    rendered = template.render(
        show_bible=show_bible,
        character_sheets=character_sheets,
        voice_exemplar_1=voice_exemplar_1,
        voice_exemplar_2=voice_exemplar_2,
        voice_exemplar_3=voice_exemplar_3,
        style_card=style_card,
        prior_episode_summaries=prior_episode_summaries,
        episode_n_number=episode_n_number,
        episode_n_transcript=episode_n_transcript,
        episode_n_plus_1_number=draft_episode,
        episode_n_plus_1_outline=episode_n_plus_1_outline,
    )

    # Build system with cache breakpoints (hierarchical caching)
    # Tier 0: bible+char+exemplars+style, Tier 1: prior summaries
    # Cache breakpoints from frontmatter
    system_blocks = []
    lines = rendered.split("\n")
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
        elif line.strip().startswith("# USER"):
            # Switch to user message
            if current_block:
                system_blocks.append({
                    "type": "text",
                    "text": "\n".join(current_block),
                    "cache_control": {"type": "ephemeral"}
                })
            current_block = []
            break
        else:
            current_block.append(line)

    # Remainder after USER marker is the user message
    user_start = rendered.find("# USER")
    if user_start != -1:
        user_content = rendered[user_start + len("# USER"):].strip()
    else:
        user_content = ""

    messages = [{"role": "user", "content": user_content}]

    # Call bedrock
    response = bedrock.call(
        messages=messages,
        system=system_blocks,
        max_tokens=frontmatter.get("max_tokens", 2400),
        temperature=frontmatter.get("temperature", 0.4),
    )

    # Parse JSON
    recap_data = json.loads(response["text"])
    return Recap(**recap_data)

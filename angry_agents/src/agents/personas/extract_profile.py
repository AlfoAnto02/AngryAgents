"""
Offline persona profile extractor.

Reads raw transcript data (YouTube or movie script) and calls a local Ollama
model to produce a structured JSON profile saved to data/personas/.

Requires Ollama running locally: https://ollama.com
Default model: llama3.2 — change with --model or OLLAMA_MODEL env var.

Usage:
    python -m angry_agents.src.agents.personas.extract_profile \
        --input data/youtube/cicciogamer89.json \
        --name cicciogamer89 \
        --type podcast

    python -m angry_agents.src.agents.personas.extract_profile \
        --input data/movies/pulp_fiction.txt \
        --name vincent_vega \
        --type fiction \
        --character "VINCENT"

    # JSON transcript — character auto-detected from file root
    python -m angry_agents.src.agents.personas.extract_profile \
        --input angry_agents/src/scraping/movies_transcripts/PO.json \
        --name po \
        --type fiction

    # use a different model
    python -m angry_agents.src.agents.personas.extract_profile \
        --input data/youtube/cicciogamer89.json \
        --name cicciogamer89 \
        --type podcast \
        --model mistral
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "mistral"
MAX_TRANSCRIPT_TOKENS = 40_000
CHARS_PER_TOKEN = 4
OUTPUT_DIR = Path("data/personas")

# ---------------------------------------------------------------------------
# Extraction prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert at analyzing text corpora to extract structured behavioral profiles.
Your output must always be valid JSON. No markdown fences, no explanation — raw JSON only.\
"""

PODCAST_USER_PROMPT = """\
Below is a collection of transcripts from {name}'s YouTube videos or podcast.
Extract a structured behavioral profile that captures how this person communicates.

Focus on patterns that are consistent across multiple excerpts, not one-off moments.
Be specific: prefer concrete examples over vague descriptors.

Return this exact JSON structure (fill every field):

{{
  "persona_name": "{name}",
  "source_type": "podcast",
  "core_style": "<1-2 sentences: sentence length, register, rhythm>",
  "humor": "<how they use humor: type, frequency, targets>",
  "vocabulary_markers": ["<word or phrase>", "..."],
  "ideological_positions": {{
    "<topic>": "<their consistent stance>",
    "<topic>": "<their consistent stance>"
  }},
  "emotional_triggers": {{
    "positive": "<what generates enthusiasm or approval>",
    "negative": "<what generates irritation or rejection>"
  }},
  "response_patterns": {{
    "when_disagreeing": "<how they push back>",
    "when_enthusiastic": "<how they express excitement>",
    "when_uncertain": "<how they handle not knowing>"
  }},
  "social_positioning": "<how they position themselves relative to audience and guests>",
  "exemplar_quotes": [
    "<direct quote from transcripts, verbatim>",
    "<direct quote>",
    "<direct quote>",
    "<direct quote>",
    "<direct quote>"
  ]
}}

--- TRANSCRIPTS ---
{transcript_text}
"""

FICTION_USER_PROMPT = """\
Below is a movie/TV script. Extract a behavioral profile for the character "{character}" \
precise enough to simulate how they speak and react in novel situations.

Rules before you start:
- Only use lines actually spoken by "{character}" in the script below.
- Do NOT infer from cultural knowledge or reputation. Every field must be grounded \
in specific lines from this transcript.
- For worldview: only assert a belief if "{character}" explicitly states it OR \
demonstrates it across at least 3 distinct scenes. No reputation-based inference.
- For annotated_quotes: pick only lines that ONLY "{character}" would say in this way. \
Reject anything a generic protagonist could say. Maximum 5 quotes, each proving a \
different dimension.

Return this exact JSON structure (fill every field):

{{
  "persona_name": "{character}",
  "source_type": "fiction",
  "source_title": "{name}",
  "core_style": {{
    "default_register": "<the dominant register when performing or guarded: formal/casual/street/sardonic/etc — one word + one clause with a concrete example from the script>",
    "sentence_shape": "<dominant pattern: clipped fragments / compound runs / self-interrupting pivots / etc — describe the shape, not just the length>",
    "rhythm": "<fast-associative / slow-deliberate / staccato / etc — what drives the cadence>",
    "two_registers": "<does this character have a second, rarer register they drop into? describe both ends and what separates them>"
  }},
  "humor": {{
    "style": "<dark/self-deprecating/absurdist/deadpan/deflecting/none>",
    "frequency": "<rare/occasional/constant — and when it spikes or disappears entirely>",
    "mechanism": "<the structural move that makes jokes land: setup-then-subvert, nickname-as-weapon, understatement, callback, irony — be specific, not generic>"
  }},
  "speech_signature": {{
    "structural_patterns": ["<a recurring syntactic construction, not a word: e.g. 'builds a list and corrupts the last entry', 'asks a question then answers it immediately', 'self-interrupts before an emotional pivot'>"],
    "naming_behavior": "<does this character rename people or things? if so, what does that naming reveal about their relationship to power or control>",
    "armor_off_register": "<what the speech looks like when the default register drops: shorter/longer/slower/specific word choices — give a concrete marker>"
  }},
  "worldview": {{
    "<belief or value grounded in the transcript>": "<how it concretely manifests in behavior or speech — cite the pattern, not the conclusion>",
    "<belief or value grounded in the transcript>": "<how it concretely manifests in behavior or speech>"
  }},
  "emotional_tells": {{
    "when_guarded": "<what speech looks like in default protective mode — the surface the world sees>",
    "when_genuinely_afraid": "<what changes in speech when fear is real: pace, line length, register, specific markers>",
    "when_grieving_or_defeated": "<what the speech compresses to when the armor comes off — word count, directness, what disappears>",
    "when_in_control": "<what signals confidence and dominance in their speech>"
  }},
  "situational_behavior": {{
    "when_outmatched": "<what is their first move — banter/stall/attack/flee — and what do they do if that fails>",
    "when_disagreeing_with_authority": "<how they push back against people who outrank them>",
    "when_someone_they_protect_is_at_risk": "<how behavior and speech change>",
    "when_proven_wrong": "<do they admit it, redirect, double down, or go silent>"
  }},
  "register_shift_triggers": [
    "<concrete situation or topic from the script that causes the default register to break — describe what happens to the speech>",
    "<another trigger>",
    "<another trigger>"
  ],
  "social_positioning": "<one sentence: how they position themselves relative to others, what it costs them, and what contradiction it creates>",
  "annotated_quotes": [
    {{
      "quote": "<verbatim line — must be exact, must be a line only this character would say this way>",
      "context": "<one clause: the situation or emotional state that produced it>",
      "illustrates": "<which specific profile dimension this proves>"
    }},
    {{
      "quote": "<verbatim line>",
      "context": "<one clause>",
      "illustrates": "<specific dimension>"
    }},
    {{
      "quote": "<verbatim line>",
      "context": "<one clause>",
      "illustrates": "<specific dimension>"
    }},
    {{
      "quote": "<verbatim line>",
      "context": "<one clause>",
      "illustrates": "<specific dimension>"
    }},
    {{
      "quote": "<verbatim line>",
      "context": "<one clause>",
      "illustrates": "<specific dimension>"
    }}
  ]
}}

--- SCRIPT ---
{transcript_text}
"""

# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_podcast_transcripts(input_path: Path, max_chars: int) -> str:
    with open(input_path, encoding="utf-8") as f:
        videos = json.load(f)

    parts = []
    total = 0
    for v in videos:
        transcript = v.get("transcript") or ""
        if not transcript:
            continue
        header = f"=== {v.get('title', 'untitled')} ===\n"
        block = header + transcript + "\n\n"
        if total + len(block) > max_chars:
            remaining = max_chars - total
            if remaining > len(header):
                parts.append(header + transcript[: remaining - len(header)])
            break
        parts.append(block)
        total += len(block)

    return "".join(parts)


def load_fiction_script(
    input_path: Path, max_chars: int, character: str | None = None
) -> tuple[str, str, str]:
    """Return (transcript_text, character_name, source_title)."""
    raw = input_path.read_text(encoding="utf-8")

    if input_path.suffix.lower() == ".json":
        data = json.loads(raw)
        char = character or data.get("character") or ""
        if not char:
            raise ValueError(
                f"No character found in {input_path}. "
                "Pass --character or add 'character' key to JSON root."
            )
        films = data.get("films", [])
        source_title = ", ".join(films) if films else input_path.stem

        lines = data.get("lines", [])
        parts: list[str] = []
        total = 0
        for entry in lines:
            scene = entry.get("scene", "")
            dialogue = entry.get("dialogue", "")
            block = f"{scene}\n{char}: {dialogue}\n\n"
            if total + len(block) > max_chars:
                break
            parts.append(block)
            total += len(block)
        return "".join(parts), char, source_title

    return raw[:max_chars], character or input_path.stem, input_path.stem


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def check_ollama(model: str) -> None:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.ConnectionError:
        sys.exit("Error: Ollama not running. Start it with: ollama serve")

    available = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
    if model not in available and model.split(":")[0] not in available:
        sys.exit(
            f"Error: model '{model}' not found in Ollama.\n"
            f"Available: {available}\n"
            f"Pull it with: ollama pull {model}"
        )


def _parse_json_from_response(raw: str) -> dict:
    """Try strict parse, then extract first {...} block, then fail loudly."""
    raw = raw.strip()

    # strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    if not raw:
        raise ValueError(
            "Model returned an empty response. "
            "Try --max-tokens 8000 to reduce input size, or use a larger model (e.g. --model mistral)."
        )

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # fallback: extract first top-level {...} block
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    print("\n--- RAW MODEL OUTPUT (for debugging) ---")
    print(raw[:2000])
    print("--- END ---\n")
    raise ValueError(
        "Could not parse JSON from model output. "
        "Try --max-tokens 8000 or a larger model (--model mistral)."
    )


def extract_profile(transcript_text: str, prompt_template: str, template_vars: dict, model: str) -> dict:
    user_content = prompt_template.format(
        transcript_text=transcript_text,
        **template_vars,
    )
    
    payload = {
        "model": model,
        "stream": False,
        "format": "json",  # Ollama native JSON mode — forces valid JSON output
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "options": {
            "temperature": 0.2,
            "num_predict": 2048,
            "num_ctx": 32768,
        },
    }

    resp = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=600,
    )
    resp.raise_for_status()

    raw = resp.json()["message"]["content"]
    return _parse_json_from_response(raw)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured persona profile from transcript.")
    parser.add_argument("--input", required=True, help="Path to transcript file (JSON for podcast, .txt for fiction)")
    parser.add_argument("--name", required=True, help="Persona or source title (used for output filename)")
    parser.add_argument("--type", required=True, choices=["podcast", "fiction"], help="Source type")
    parser.add_argument("--character", default=None, help="Character name in script (fiction only, ALL CAPS)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-tokens", type=int, default=MAX_TRANSCRIPT_TOKENS, help="Max transcript tokens to send")
    parser.add_argument("--out-dir", default=str(OUTPUT_DIR), help="Output directory")
    args = parser.parse_args()

    check_ollama(args.model)

    input_path = Path(args.input)
    is_json = input_path.suffix.lower() == ".json"

    if args.type == "fiction" and not args.character and not is_json:
        sys.exit("Error: --character required for non-JSON fiction input.")

    if not input_path.exists():
        sys.exit(f"Error: input file not found: {input_path}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{args.name}_profile.json"

    max_chars = args.max_tokens * CHARS_PER_TOKEN

    print(f"Loading {args.type} source: {input_path}")

    if args.type == "podcast":
        transcript_text = load_podcast_transcripts(input_path, max_chars)
        prompt_template = PODCAST_USER_PROMPT
        template_vars = {"name": args.name}
    else:
        transcript_text, character, source_title = load_fiction_script(
            input_path, max_chars, character=args.character
        )
        print(f"Character: {character} | Source: {source_title}")
        prompt_template = FICTION_USER_PROMPT
        template_vars = {"name": source_title, "character": character}

    approx_tokens = len(transcript_text) // CHARS_PER_TOKEN
    print(f"Transcript loaded: ~{approx_tokens:,} tokens")
    print(f"Calling Ollama ({args.model})... this may take a few minutes.")

    profile = extract_profile(transcript_text, prompt_template, template_vars, args.model)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    print(f"\nProfile saved → {out_file}")
    print(json.dumps(profile, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

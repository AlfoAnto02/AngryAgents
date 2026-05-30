"""
Persona profile extractor using OpenAI API.

Reads raw transcript data (YouTube or movie script) and calls OpenAI's API
to produce a structured JSON profile saved to data/personas/.

Requires OPENAI_API_KEY environment variable to be set.
Default model: gpt-4o-mini — change with --model.

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
        --model gpt-4-turbo

    # batch: process multiple personas from a JSON config file
    python -m angry_agents.src.agents.personas.extract_profile \
        --batch data/batch_personas.json \
        --model gpt-4o-mini

    Batch config format (array of objects, same fields as CLI args):
    [
      {"input": "data/youtube/cicciogamer89.json", "name": "cicciogamer89", "type": "podcast"},
      {"input": "angry_agents/src/scraping/movies_transcripts/PO.json", "name": "po", "type": "fiction"},
      {"input": "data/movies/pulp_fiction.txt", "name": "vincent_vega", "type": "fiction", "character": "VINCENT"},
      {"input": "data/youtube/trump.json", "name": "trump", "type": "podcast",
       "model": "gpt-4o", "knowledge_model": "gpt-4o"}
    ]
    Per-spec "model" and "knowledge_model" override the CLI --model / --knowledge-model flags.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

_URL_RE = re.compile(r"https?://\S+")

from angry_agents.src.agents.personas.templates import render_prompt

import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load .env file
load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = "gpt-4o-mini"
MAX_TRANSCRIPT_TOKENS = 40_000
CHARS_PER_TOKEN = 4
OUTPUT_DIR = Path("data/personas")

# ---------------------------------------------------------------------------
# Extraction prompts live in templates/extract_*.j2 — loaded via render_prompt()
# ---------------------------------------------------------------------------




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


def load_twitter_tweets(input_path: Path, max_chars: int) -> str:
    with open(input_path, encoding="utf-8") as f:
        batches = json.load(f)

    parts = []
    total = 0
    for batch in batches:
        for tweet in batch.get("tweets", []):
            text = tweet.get("text", "")
            if text.startswith("RT @"):
                continue
            clean = _URL_RE.sub("", text).strip()
            if not clean:
                continue
            line = clean + "\n"
            if total + len(line) > max_chars:
                return "".join(parts)
            parts.append(line)
            total += len(line)

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
# Logging
# ---------------------------------------------------------------------------

class TokenUsageLogger:
    """Tracks and logs token usage from OpenAI API calls."""
    
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
    
    @staticmethod
    def get_cost_per_token(model: str) -> tuple[float, float]:
        """Return (input_cost_per_1M, output_cost_per_1M) for a model."""
        pricing = {
            "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
            "gpt-4-turbo": (10.0 / 1_000_000, 30.0 / 1_000_000),
            "gpt-4o": (5.0 / 1_000_000, 15.0 / 1_000_000),
            "gpt-5.2": (1.75 / 1_000_000, 14.0 / 1_000_000),
            "gpt-5.2-pro": (21.0 / 1_000_000, 168.0 / 1_000_000),
            "gpt-5.1": (1.25 / 1_000_000, 10.0 / 1_000_000),
            "gpt-5": (1.25 / 1_000_000, 10.0 / 1_000_000),
            "gpt-5-mini": (0.25 / 1_000_000, 2.0 / 1_000_000),
            "gpt-5-nano": (0.05 / 1_000_000, 0.40 / 1_000_000),
            "gpt-5-pro": (15.0 / 1_000_000, 120.0 / 1_000_000),
            "gpt-4.1": (2.0 / 1_000_000, 8.0 / 1_000_000),
            "gpt-4.1-mini": (0.40 / 1_000_000, 1.60 / 1_000_000),
            "gpt-4.1-nano": (0.10 / 1_000_000, 0.40 / 1_000_000),
            "gpt-4o": (2.50 / 1_000_000, 10.0 / 1_000_000),
            "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
            "o4-mini": (1.10 / 1_000_000, 4.40 / 1_000_000),
            "o3": (2.0 / 1_000_000, 8.0 / 1_000_000),
            "o3-mini": (1.10 / 1_000_000, 4.40 / 1_000_000),
        }
        return pricing.get(model, (0, 0))
    
    def log_usage(self, usage, model: str) -> None:
        """Log token usage from an OpenAI API response."""
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        input_cost, output_cost = self.get_cost_per_token(model)
        call_cost = (input_tokens * input_cost) + (output_tokens * output_cost)
        self.total_cost += call_cost
    
    def report(self) -> str:
        """Return a formatted token usage report."""
        total_tokens = self.total_input_tokens + self.total_output_tokens
        return (
            f"\n{'='*60}\n"
            f"TOKEN USAGE REPORT\n"
            f"{'='*60}\n"
            f"Input tokens:  {self.total_input_tokens:,}\n"
            f"Output tokens: {self.total_output_tokens:,}\n"
            f"Total tokens:  {total_tokens:,}\n"
            f"Estimated cost: ${self.total_cost:.4f}\n"
            f"{'='*60}\n"
        )


# ---------------------------------------------------------------------------
# API validation
# ---------------------------------------------------------------------------

def check_openai_api_key() -> None:
    """Validate that OpenAI API key is set."""
    if not OPENAI_API_KEY:
        sys.exit(
            "Error: OPENAI_API_KEY environment variable not set.\n"
            "Set it with: export OPENAI_API_KEY='sk-...'"
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


def extract_profile(
    system: str,
    user: str,
    model: str,
    usage_logger: TokenUsageLogger,
) -> dict:
    """Call OpenAI API to extract persona profile from pre-rendered prompt strings."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=8192,
        response_format={"type": "json_object"},
    )
    usage_logger.log_usage(response.usage, model)
    raw = response.choices[0].message.content
    return _parse_json_from_response(raw)




def extract_knowledge_fields(
    name: str,
    source_type: str,
    model: str,
    usage_logger: TokenUsageLogger,
) -> dict:
    """Call 2: extract favored_words, structural_patterns, do_not_say using model knowledge only — no transcript."""
    system, user = render_prompt("extract_knowledge.j2", name=name, source_type=source_type)
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )
    usage_logger.log_usage(response.usage, model)
    return _parse_json_from_response(response.choices[0].message.content)


def _merge_knowledge(profile: dict, knowledge: dict) -> dict:
    """Merge knowledge-call fields into the transcript-call profile."""
    result = dict(profile)
    if words := knowledge.get("vocabulary_fingerprint", {}).get("favored_words"):
        result.setdefault("vocabulary_fingerprint", {})["favored_words"] = words
    if patterns := knowledge.get("speech_signature", {}).get("structural_patterns"):
        result.setdefault("speech_signature", {})["structural_patterns"] = patterns
    if dns := knowledge.get("do_not_say"):
        result["do_not_say"] = dns
    return result


# ---------------------------------------------------------------------------
# Single-persona processing
# ---------------------------------------------------------------------------

def process_one(
    *,
    input: str,
    name: str,
    type: str,
    character: str | None = None,
    model: str = DEFAULT_MODEL,
    knowledge_model: str | None = None,
    max_tokens: int = MAX_TRANSCRIPT_TOKENS,
    out_dir: Path,
    usage_logger: TokenUsageLogger,
) -> Path:
    """Process one persona spec and return the output file path."""
    input_path = Path(input)
    is_json = input_path.suffix.lower() == ".json"

    if type == "fiction" and not character and not is_json:
        raise ValueError(f"--character required for non-JSON fiction input: {input_path}")

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    out_file = out_dir / f"{name}_profile.json"
    max_chars = max_tokens * CHARS_PER_TOKEN

    print(f"\n[{name}] Loading {type} source: {input_path}")

    if type == "podcast":
        transcript_text = load_podcast_transcripts(input_path, max_chars)
        system, user = render_prompt("extract_podcast.j2", name=name, transcript_text=transcript_text)
    elif type == "twitter":
        transcript_text = load_twitter_tweets(input_path, max_chars)
        system, user = render_prompt("extract_twitter.j2", name=name, transcript_text=transcript_text)
    else:
        transcript_text, char, source_title = load_fiction_script(
            input_path, max_chars, character=character
        )
        print(f"[{name}] Character: {char} | Source: {source_title}")
        system, user = render_prompt("extract_fiction.j2", name=source_title, character=char, transcript_text=transcript_text)

    approx_tokens = len(transcript_text) // CHARS_PER_TOKEN
    print(f"[{name}] Transcript loaded: ~{approx_tokens:,} tokens")
    print(f"[{name}] Calling OpenAI ({model}) — transcript pass...")
    profile = extract_profile(system, user, model, usage_logger)

    _kmodel = knowledge_model or model
    print(f"[{name}] Calling OpenAI ({_kmodel}) — knowledge pass...")
    knowledge = extract_knowledge_fields(name, type, _kmodel, usage_logger)
    profile = _merge_knowledge(profile, knowledge)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    print(f"[{name}] Profile saved → {out_file}")
    return out_file


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured persona profile from transcript using OpenAI API.")
    parser.add_argument("--input", help="Path to transcript file (JSON for podcast, .txt for fiction)")
    parser.add_argument("--name", help="Persona or source title (used for output filename)")
    parser.add_argument("--type", choices=["podcast", "fiction", "twitter"], help="Source type")
    parser.add_argument("--character", default=None, help="Character name in script (fiction only, ALL CAPS)")
    parser.add_argument("--batch", help="Path to JSON batch config file (array of persona specs)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenAI model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--knowledge-model", default=None, help="Model for the knowledge pass (default: same as --model). Use gpt-4o or gpt-4.1 for richer fingerprints on famous personas.")
    parser.add_argument("--max-tokens", type=int, default=MAX_TRANSCRIPT_TOKENS, help="Max transcript tokens to send")
    parser.add_argument("--out-dir", default=str(OUTPUT_DIR), help="Output directory")
    args = parser.parse_args()

    check_openai_api_key()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    usage_logger = TokenUsageLogger()

    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            sys.exit(f"Error: batch file not found: {batch_path}")
        with open(batch_path, encoding="utf-8") as f:
            specs = json.load(f)
        if not isinstance(specs, list):
            sys.exit("Error: batch file must be a JSON array of persona specs.")

        print(f"Batch mode: {len(specs)} persona(s) to process.")
        saved = []
        for i, spec in enumerate(specs, 1):
            print(f"\n--- [{i}/{len(specs)}] ---")
            try:
                out_file = process_one(
                    input=spec["input"],
                    name=spec["name"],
                    type=spec["type"],
                    character=spec.get("character"),
                    model=spec.get("model", args.model),
                    knowledge_model=spec.get("knowledge_model", args.knowledge_model),
                    max_tokens=args.max_tokens,
                    out_dir=out_dir,
                    usage_logger=usage_logger,
                )
                saved.append(out_file)
            except (FileNotFoundError, ValueError) as e:
                sys.exit(f"Error processing spec {i}: {e}")

        print(f"\nDone. {len(saved)} profile(s) saved:")
        for p in saved:
            print(f"  {p}")

    else:
        if not args.input or not args.name or not args.type:
            sys.exit("Error: --input, --name, and --type are required (or use --batch).")

        out_file = process_one(
            input=args.input,
            name=args.name,
            type=args.type,
            character=args.character,
            model=args.model,
            knowledge_model=args.knowledge_model,
            max_tokens=args.max_tokens,
            out_dir=out_dir,
            usage_logger=usage_logger,
        )
        with open(out_file, encoding="utf-8") as f:
            print(json.dumps(json.load(f), ensure_ascii=False, indent=2))

    print(usage_logger.report())


if __name__ == "__main__":
    main()
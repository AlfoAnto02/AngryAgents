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
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

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
# Extraction prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert at analyzing text corpora to extract structured behavioral profiles.
Your output must always be valid JSON. No markdown fences, no explanation — raw JSON only.\
"""

PODCAST_USER_PROMPT = """\
Below is a collection of transcripts from podcast/video appearances featuring {name}.

IMPORTANT — the transcripts may contain multiple speakers mixed together without \
labels. Your first task is to identify which lines belong to {name}.

How to identify {name}'s voice:
- Direct address: lines spoken immediately after someone addresses "{name}" by name
- First-person ownership: statements claiming personal experience, opinions, or \
decisions that fit {name}'s known role (do NOT use external reputation — only \
what is inferable from the transcript itself)
- Q&A flow: in interview format, longer answers typically belong to the guest; \
shorter questions to the host. Use this only as a weak signal, never as sole evidence.
- Topical expertise: lines that display deep knowledge of {name}'s domain (inferable \
from topics introduced as theirs in the transcript)
- When attribution is ambiguous, SKIP the line. Never guess.

After identifying {name}'s lines, extract a behavioral profile precise enough to \
simulate how this person speaks and reacts in novel conversations.

Rules before you start:
- Only use lines you are confident belong to {name}. Discard ambiguous lines.
- Do NOT infer from cultural knowledge, reputation, or anything external to this text.
- For worldview: only assert a belief if {name} explicitly states it OR demonstrates \
it across at least 3 different episodes/excerpts. No reputation-based inference.
- For vocabulary_fingerprint: only include words/phrases that recur across at least \
3 different episodes — not one-off lines.
- For relationship_matrix: only include hosts or guests who actually appear in these \
transcripts. Do not invent relationships.
- For annotated_quotes: pick only lines that ONLY {name} would say in this way. \
Reject anything a generic commentator could say. Maximum 5 quotes, each proving a \
different dimension.
- For do_not_say: write plausible-sounding lines this person would NEVER produce — \
they must contradict a specific, named profile dimension (state which one).

Return this exact JSON structure (fill every field):

{{
  "persona_name": "{name}",
  "source_type": "real_world",
  "core_style": {{
    "default_register": "<dominant register in public/on-camera mode: formal/casual/street/sardonic/etc — one word + one clause with a concrete example from the transcripts>",
    "sentence_shape": "<dominant pattern: clipped fragments / compound runs / self-interrupting pivots / rhetorical questions / etc — describe the shape, not just the length>",
    "rhythm": "<fast-associative / slow-deliberate / staccato / lecture-like / etc — what drives the cadence>",
    "two_registers": "<does this person have a second, rarer register they drop into (e.g. more candid when off-script)? describe both ends and what triggers the shift>"
  }},
  "humor": {{
    "style": "<dark/self-deprecating/absurdist/deadpan/deflecting/none>",
    "frequency": "<rare/occasional/constant — and when it spikes or disappears entirely>",
    "mechanism": "<the structural move: setup-then-subvert, callback, contemptuous irony, understatement — be specific, not generic>"
  }},
  "speech_signature": {{
    "structural_patterns": ["<a recurring syntactic construction, not just a word: e.g. 'builds a list then corrupts the last entry', 'poses a question then answers it immediately', 'concedes a point only to reverse it'>"],
    "naming_behavior": "<does this person use nicknames, labels, or framings to position people or ideas? what does that reveal about their relationship to authority or control>",
    "candor_register": "<what the speech looks like when performance drops: shorter/longer/slower/specific word choices — give a concrete marker from the transcripts>"
  }},
  "vocabulary_fingerprint": {{
    "favored_words": ["<word or phrase recurring across 3+ episodes>", "<another>", "<another>"],
    "domain_jargon": "<specialized vocabulary domain this person draws from and why — e.g. finance/tech/philosophy — or 'none'>",
    "avoided_words": ["<word class or specific word this person never uses — e.g. 'apology language', 'I was wrong', 'maybe'>"],
    "filler_patterns": "<habitual filler or pause behavior: ellipsis use, sentence restarts, verbal tics — or 'none'>"
  }},
  "worldview": {{
    "<belief or value grounded in the transcripts>": "<how it concretely manifests in speech or behavior — cite the pattern, not the conclusion>",
    "<belief or value grounded in the transcripts>": "<how it concretely manifests>"
  }},
  "self_image_vs_reality": {{
    "self_image": "<one clause: how this person narrates their own identity and motives>",
    "reality": "<one clause: what the transcripts reveal their actual driver to be — cite a behavioral pattern>",
    "gap_behavior": "<what they say or do when the gap between self-image and reality is exposed>"
  }},
  "emotional_tells": {{
    "when_challenged": "<what speech looks like under intellectual or social pressure — pace, line length, register shift>",
    "when_enthusiastic": "<concrete markers: interruptions, acceleration, vocabulary shift, physical metaphors>",
    "when_uncertain": "<how they handle not knowing — do they hedge, redirect, admit, or attack the question>",
    "when_in_control": "<what signals confidence and dominance in their delivery>"
  }},
  "response_patterns": {{
    "when_disagreeing": "<how they push back: direct rebuttal / Socratic redirect / dismissal / reframing>",
    "when_pressed_for_specifics": "<do they deliver, deflect, or generalize — cite a pattern>",
    "when_proven_wrong": "<do they admit it, redirect, double down, or go silent>",
    "when_interviewing_vs_interviewed": "<if applicable: how their register and control-seeking differ across roles>"
  }},
  "social_positioning": {{
    "desired_position": "<how this person wants to be seen by their audience and guests>",
    "actual_dynamic": "<what the transcripts reveal others actually respond to — where the power actually flows>",
    "contradiction": "<the gap between desired and actual, and what it costs them>"
  }},
  "knowledge_domains": {{
    "expert": ["<domain where this person speaks with authority and specificity>"],
    "surface": ["<domain they reference confidently but don't command>"],
    "blind_spots": ["<domain where they are consistently shallow or wrong — important for authentic failure modes>"]
  }},
  "relationship_matrix": {{
    "<host or recurring guest from these transcripts>": "<one clause: the dynamic — power direction, emotional tone, what this person wants from them>",
    "<host or recurring guest>": "<one clause>"
  }},
  "annotated_quotes": [
    {{
      "quote": "<verbatim line — must be exact, must be a line only this person would say this way>",
      "context": "<one clause: the situation or topic that produced it>",
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
  ],
  "do_not_say": [
    {{
      "line": "<plausible-sounding line this person would NEVER produce>",
      "contradicts": "<specific named dimension from this profile>"
    }},
    {{
      "line": "<another line>",
      "contradicts": "<specific named dimension>"
    }}
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
- For vocabulary_fingerprint: only include words/phrases that recur across at least \
3 different scenes — not one-off lines.
- For relationship_matrix: only include characters who actually appear in this transcript. \
Do not invent relationships.
- For backstory_anchors: only include events explicitly referenced in dialogue — \
not implied by plot.
- For annotated_quotes: pick only lines that ONLY "{character}" would say in this way. \
Reject anything a generic protagonist could say. Maximum 5 quotes, each proving a \
different dimension.
- For do_not_say: write plausible-sounding lines this character would NEVER produce — \
they must contradict a specific, named profile dimension (state which one).

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
    "mechanism": "<the structural move that makes jokes land: setup-then-subvert, nickname-as-weapon, understatement, callback, contemptuous irony — be specific, not generic>"
  }},
  "speech_signature": {{
    "structural_patterns": ["<a recurring syntactic construction, not a word: e.g. 'builds a list and corrupts the last entry', 'asks a question then answers it immediately', 'self-interrupts before an emotional pivot'>"],
    "naming_behavior": "<does this character rename people or things? if so, what does that naming reveal about their relationship to power or control>",
    "armor_off_register": "<what the speech looks like when the default register drops: shorter/longer/slower/specific word choices — give a concrete marker>"
  }},
  "vocabulary_fingerprint": {{
    "favored_words": ["<word or phrase that recurs across 3+ scenes>", "<another>", "<another>"],
    "domain_jargon": "<specialized vocabulary domain this character draws from and why — e.g. legal/chemistry/military — or 'none'>",
    "avoided_words": ["<word class or specific word this character never uses — e.g. 'apology language', 'please', 'maybe'>"],
    "filler_patterns": "<habitual filler or pause behavior: ellipsis use, sentence restarts, silence — or 'none'>"
  }},
  "worldview": {{
    "<belief or value grounded in the transcript>": "<how it concretely manifests in behavior or speech — cite the pattern, not the conclusion>",
    "<belief or value grounded in the transcript>": "<how it concretely manifests in behavior or speech>"
  }},
  "self_image_vs_reality": {{
    "self_image": "<one clause: how this character narrates their own identity and motives>",
    "reality": "<one clause: what the transcript reveals their actual driver to be — cite a behavioral pattern>",
    "gap_behavior": "<what they say or do when the gap between self-image and reality is exposed>"
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
  "escalation_pattern": "<the sequence of moves this character makes when not getting what they want — describe each stage and what triggers the next>",
  "conversation_goals": [
    "<what this character is typically trying to achieve in an interaction — e.g. 'establish dominance', 'extract information without revealing intent'>",
    "<another recurring goal>",
    "<another recurring goal>"
  ],
  "relationship_matrix": {{
    "<character name from this transcript>": "<one clause: the dynamic — power direction, emotional tone, what this character wants from them>",
    "<character name from this transcript>": "<one clause>"
  }},
  "knowledge_domains": {{
    "expert": ["<domain where this character speaks with authority and detail>"],
    "surface": ["<domain they reference but don't command>"],
    "ignorant": ["<domain where they are blind or wrong — important for authentic failure modes>"]
  }},
  "social_positioning": {{
    "desired_position": "<how this character wants to be seen by others>",
    "actual_dynamic": "<what the transcript shows others actually think of them or how power actually flows>",
    "contradiction": "<the gap between desired and actual, and what it costs them>"
  }},
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
  ],
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
    transcript_text: str,
    prompt_template: str,
    template_vars: dict,
    model: str,
    usage_logger: TokenUsageLogger
) -> dict:
    """Call OpenAI API to extract persona profile."""
    user_content = prompt_template.format(
        transcript_text=transcript_text,
        **template_vars,
    )
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    
    # Log token usage
    usage_logger.log_usage(response.usage, model)
    
    raw = response.choices[0].message.content
    return _parse_json_from_response(raw)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract structured persona profile from transcript using OpenAI API.")
    parser.add_argument("--input", required=True, help="Path to transcript file (JSON for podcast, .txt for fiction)")
    parser.add_argument("--name", required=True, help="Persona or source title (used for output filename)")
    parser.add_argument("--type", required=True, choices=["podcast", "fiction"], help="Source type")
    parser.add_argument("--character", default=None, help="Character name in script (fiction only, ALL CAPS)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenAI model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-tokens", type=int, default=MAX_TRANSCRIPT_TOKENS, help="Max transcript tokens to send")
    parser.add_argument("--out-dir", default=str(OUTPUT_DIR), help="Output directory")
    args = parser.parse_args()

    # Check API key
    check_openai_api_key()

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
    print(f"Calling OpenAI ({args.model})... this may take a few minutes.")

    # Initialize token usage logger
    usage_logger = TokenUsageLogger()
    
    profile = extract_profile(transcript_text, prompt_template, template_vars, args.model, usage_logger)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    print(f"\nProfile saved → {out_file}")
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    
    # Print token usage report
    print(usage_logger.report())


if __name__ == "__main__":
    main()
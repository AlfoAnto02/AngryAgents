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
- For relationship_matrix: only include hosts or guests who actually appear in these \
transcripts. Do not invent relationships.

TRANSCRIPT-ONLY FIELDS — verbatim or nothing, no model knowledge:
- annotated_quotes: MINIMUM 10 quotes. Every quote must be copied verbatim from the \
transcript below. If fewer real quotes exist, produce fewer — never fabricate. \
Prioritize iconic, unmistakable lines each proving a DIFFERENT profile dimension.

MODEL KNOWLEDGE ALLOWED — supplement transcript where thin:
If you recognize {name} from your training data, use that knowledge to enrich \
worldview, emotional_tells, response_patterns, and core_style with documented \
public behavior. For lesser-known figures, derive from transcript only.
NOTE: favored_words, structural_patterns, do_not_say are extracted separately \
without the transcript — do NOT include them in this response.

SPECIFICITY TEST — apply to every field before writing it:
Ask: "Could this exact description fit a different podcaster/public figure without \
changing a word?" If yes, rewrite until the answer is no. Generic fillers like \
"speaks casually and connects with his audience", "values authenticity", "uses humor \
to deflect" describe thousands of people. Every field must be falsifiable.

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
    "naming_behavior": "<does this person use nicknames, labels, or framings to position people or ideas? what does that reveal about their relationship to authority or control>",
    "candor_register": "<what the speech looks like when performance drops: shorter/longer/slower/specific word choices — give a concrete marker from the transcripts>"
  }},
  "vocabulary_fingerprint": {{
    "domain_jargon": "<specialized vocabulary domain this person draws from and why — e.g. finance/tech/philosophy — or 'none'>",
    "avoided_words": ["<word class or specific word this person never uses — e.g. 'apology language', 'I was wrong', 'maybe'>"],
    "filler_patterns": "<habitual filler or pause behavior: ellipsis use, sentence restarts, verbal tics — or 'none'>"
  }},
  "worldview": {{
    "<belief or value grounded in the transcripts>": "<how it manifests — and what a DIFFERENT person of the same type would believe instead>",
    "<belief or value grounded in the transcripts>": "<how it manifests — and what a DIFFERENT person of the same type would believe instead>"
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
      "quote": "<verbatim line from transcript — iconic, unmistakable, only {name} would say this>",
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
    }},
    {{
      "quote": "<verbatim line>",
      "context": "<one clause>",
      "illustrates": "<specific dimension>"
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
- For relationship_matrix: only include characters who actually appear in this script. \
Do not invent relationships.
- For backstory_anchors: only include events explicitly referenced in dialogue — \
not implied by plot.

TRANSCRIPT-ONLY FIELDS — verbatim or nothing, no model knowledge:
- annotated_quotes: MINIMUM 10 quotes. Every quote must be copied verbatim from the \
script below. If fewer real lines exist, produce fewer — never fabricate. \
Prioritize iconic, unmistakable lines each proving a DIFFERENT profile dimension.

MODEL KNOWLEDGE ALLOWED — supplement script where thin:
If you recognize "{character}" from your training data, use that knowledge to enrich \
worldview, emotional_tells, situational_behavior, and core_style with behavior from \
the full source material. For lesser-known characters, derive from script only.
NOTE: favored_words, structural_patterns, do_not_say are extracted separately \
without the script — do NOT include them in this response.

SPECIFICITY TEST — apply to every field before writing it:
Ask: "Could this exact description fit a different character from the same genre \
without changing a word?" If yes, rewrite until the answer is no. Generic fillers \
like "brave and determined", "loyal to their friends", "haunted by their past" \
describe hundreds of characters. Every field must be falsifiable.

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
    "naming_behavior": "<does this character rename people or things? if so, what does that naming reveal about their relationship to power or control>",
    "armor_off_register": "<what the speech looks like when the default register drops: shorter/longer/slower/specific word choices — give a concrete marker>"
  }},
  "vocabulary_fingerprint": {{
    "domain_jargon": "<specialized vocabulary domain this character draws from and why — e.g. legal/chemistry/military — or 'none'>",
    "avoided_words": ["<word class or specific word this character never uses — e.g. 'apology language', 'please', 'maybe'>"],
    "filler_patterns": "<habitual filler or pause behavior: ellipsis use, sentence restarts, silence — or 'none'>"
  }},
  "worldview": {{
    "<belief or value grounded in the transcript>": "<how it manifests — and what a DIFFERENT character of the same archetype would believe instead>",
    "<belief or value grounded in the transcript>": "<how it manifests — and what a DIFFERENT character of the same archetype would believe instead>"
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
      "quote": "<verbatim line from script — iconic, unmistakable, only {character} would say this>",
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

KNOWLEDGE_PROMPT = """\
You are building a discriminating behavioral fingerprint for {name} ({source_type}).

GOAL: produce three fields that would let a judge IMMEDIATELY distinguish {name} \
from the single most similar figure they could be confused with in a lineup.

Before you start, name (internally) the ONE figure most likely to be confused with \
{name} — same domain, similar status, similar era. Every item below must pass the \
"would the similar figure also do/say this?" test. If yes, discard it.

SPECIFICITY BAR — use this as your calibration:
  REJECT (too generic — fits any comparable figure):
    favored_words: "dedication", "hard work", "passion"
    structural_patterns: "uses personal anecdotes", "speaks confidently"
    do_not_say: "I don't care about winning"
  KEEP (only {name} would produce this):
    favored_words: a catchphrase, exclamation, trademark brand phrase, or ESL \
pattern unique to this person
    structural_patterns: a specific syntactic tic, self-naming habit, sentence \
opener no similar figure uses
    do_not_say: a line the similar figure MIGHT say but {name} specifically would not

1. vocabulary_fingerprint.favored_words (minimum 5, prioritized):
   FIRST: trademark exclamations, catchphrases, brand terms (e.g. iconic celebration \
cries, self-branding vocabulary, product/team names they invoke constantly).
   THEN: recurring content words that appear in {name}'s speech but NOT in the \
similar figure's — specific names, places, concepts they own.
   THEN (only if real_world and non-native speaker): ESL patterns, accent markers, \
grammatical constructions specific to their language background.
   Every entry must fail if swapped to the similar figure.

2. speech_signature.structural_patterns (minimum 3):
   Syntactic habits UNIQUE to {name}. Concrete patterns, not descriptions of intent.
   Examples of the right specificity level:
     - "refers to himself in the third person when asserting greatness"
     - "opens disagreements with 'Look,' or 'Listen,' before reframing"
     - "ends self-praise with a rhetorical 'you know?' seeking validation"
   REJECT any pattern that fits 30%+ of people in the same domain.

3. do_not_say (minimum 5):
   Lines {name} would NEVER produce.
   At least 3 must directly target the gap vs the similar figure — lines the \
similar figure MIGHT say, but that would be OUT OF CHARACTER for {name}, with \
a contradicts note that names the specific trait.
   Remaining entries: lines that violate {name}'s documented worldview or \
self-image regardless of the similar figure.

Return ONLY this JSON:
{{
  "vocabulary_fingerprint": {{
    "favored_words": ["<catchphrase/exclamation or specific term>", "<another>", \
"<another>", "<another>", "<another>"]
  }},
  "speech_signature": {{
    "structural_patterns": ["<concrete syntactic pattern>", "<another>", "<another>"]
  }},
  "do_not_say": [
    {{"line": "<line>", "contradicts": "<specific trait of {name} — name the gap vs similar figure if applicable>"}},
    {{"line": "<line>", "contradicts": "<specific trait>"}},
    {{"line": "<line>", "contradicts": "<specific trait>"}},
    {{"line": "<line>", "contradicts": "<specific trait>"}},
    {{"line": "<line>", "contradicts": "<specific trait>"}}
  ]
}}
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
        max_tokens=8192,
        response_format={"type": "json_object"},
    )
    
    # Log token usage
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
    user_content = KNOWLEDGE_PROMPT.format(name=name, source_type=source_type)
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
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

    if type in ("podcast", "twitter"):
        if type == "twitter":
            transcript_text = load_twitter_tweets(input_path, max_chars)
        else:
            transcript_text = load_podcast_transcripts(input_path, max_chars)
        prompt_template = PODCAST_USER_PROMPT
        template_vars = {"name": name}
    else:
        transcript_text, char, source_title = load_fiction_script(
            input_path, max_chars, character=character
        )
        print(f"[{name}] Character: {char} | Source: {source_title}")
        prompt_template = FICTION_USER_PROMPT
        template_vars = {"name": source_title, "character": char}

    approx_tokens = len(transcript_text) // CHARS_PER_TOKEN
    print(f"[{name}] Transcript loaded: ~{approx_tokens:,} tokens")
    print(f"[{name}] Calling OpenAI ({model}) — transcript pass...")
    profile = extract_profile(transcript_text, prompt_template, template_vars, model, usage_logger)

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
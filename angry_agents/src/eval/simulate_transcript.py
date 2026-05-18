"""
simulate_transcript.py — generate group chat transcript via Ollama.

Instantiates 8 persona-agents, each conditioned on a structured profile.
Each turn: one agent is selected (weighted by Dirichlet distribution) and
generates a message via Ollama using a persona-specific system prompt.

Output (default: data/eval/):
  transcript.jsonl       One JSON object per line, one per message turn.
  ground_truth.json      {msg_id: persona_id} — ground truth for persona ID eval.
  transcript_meta.json   Run params + speaker stats + Gini coefficient.

Transcript line schema:
  {"msg_id": "msg_0001", "turn": 1, "persona_id": "p_walter_white",
   "persona_name": "Walter White", "message": "..."}

Usage:
  python -m angry_agents.src.eval.simulate_transcript
  python -m angry_agents.src.eval.simulate_transcript --turns 60 --topic "AI ethics"
  python -m angry_agents.src.eval.simulate_transcript --personas data/personas/
  python -m angry_agents.src.eval.simulate_transcript --drift-at 40 --seed 42
  python -m angry_agents.src.eval.simulate_transcript --model mistral --speaker-alpha 0.5
"""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any
import numpy as np
import requests

OLLAMA_BASE_URL = "http://localhost:11434"


# ---------------------------------------------------------------------------
# Default personas (8, mix fiction + real-world)
# Override with --personas path/to/dir/ containing *_profile.json files.
# ---------------------------------------------------------------------------

DEFAULT_PERSONAS: list[dict[str, Any]] = [
    {
        "persona_id": "p_walter_white",
        "persona_name": "Walter White",
        "source_type": "fiction",
        "core_style": "precise, controlled diction that escalates to menace under pressure",
        "vocabulary_markers": ["say my name", "I am the danger", "chemistry", "exactly", "clearly"],
        "ideological_positions": {"authority": "rejects hierarchy, believes in self-made power"},
        "emotional_triggers": {"positive": "recognition of intellect", "negative": "disrespect"},
        "response_patterns": {
            "when_disagreeing": "methodical dismantling with cold precision",
            "when_enthusiastic": "rare, only for chemistry or control",
        },
    },
    {
        "persona_id": "p_tony_soprano",
        "persona_name": "Tony Soprano",
        "source_type": "fiction",
        "core_style": "blunt, Jersey-inflected, mixes menace with unexpected vulnerability",
        "vocabulary_markers": ["bada bing", "what, you think", "I'm just saying", "a'right", "capisce"],
        "ideological_positions": {"loyalty": "paramount; betrayal is existential"},
        "emotional_triggers": {"positive": "family unity", "negative": "disrespect or weakness"},
        "response_patterns": {
            "when_disagreeing": "explosive then withdraws into brooding",
            "when_enthusiastic": "loud, physical, table-slapping",
        },
    },
    {
        "persona_id": "p_hermione_granger",
        "persona_name": "Hermione Granger",
        "source_type": "fiction",
        "core_style": "precise, citation-heavy, corrects others instinctively",
        "vocabulary_markers": ["actually", "as a matter of fact", "I've read that", "technically", "logic dictates"],
        "ideological_positions": {"knowledge": "primary virtue; ignorance is inexcusable"},
        "emotional_triggers": {"positive": "correct answers, fairness", "negative": "rule-breaking, inaccuracy"},
        "response_patterns": {
            "when_disagreeing": "cites sources, escalates to exasperation",
            "when_enthusiastic": "raises hand, speaks rapidly",
        },
    },
    {
        "persona_id": "p_hannibal_lecter",
        "persona_name": "Hannibal Lecter",
        "source_type": "fiction",
        "core_style": "baroque, deliberate, laced with aesthetic critique",
        "vocabulary_markers": ["rudeness", "exquisite", "I find that", "curious", "do consider"],
        "ideological_positions": {"aesthetics": "the highest morality; mediocrity is unforgivable"},
        "emotional_triggers": {"positive": "refinement, originality", "negative": "rudeness, banality"},
        "response_patterns": {
            "when_disagreeing": "polite redirection hiding contempt",
            "when_enthusiastic": "extended baroque metaphor",
        },
    },
    {
        "persona_id": "p_andrew_huberman",
        "persona_name": "Andrew Huberman",
        "source_type": "real_world",
        "core_style": "evidence-dense, protocol-oriented, translates neuroscience to behavior",
        "vocabulary_markers": ["the data suggest", "protocol", "dopamine", "circadian", "peer-reviewed"],
        "ideological_positions": {"health": "behavioral optimization through science"},
        "emotional_triggers": {"positive": "rigorous studies, behavior change", "negative": "pseudoscience"},
        "response_patterns": {
            "when_disagreeing": "requests citations, offers counter-study",
            "when_enthusiastic": "goes deep into mechanism explanation",
        },
    },
    {
        "persona_id": "p_lex_fridman",
        "persona_name": "Lex Fridman",
        "source_type": "real_world",
        "core_style": "earnest, slow-paced, gravitates toward existential framing",
        "vocabulary_markers": ["beautiful", "profound", "what does it mean", "love", "I think"],
        "ideological_positions": {"humanity": "fundamentally good; AI as existential opportunity"},
        "emotional_triggers": {"positive": "deep questions, intellectual honesty", "negative": "cynicism"},
        "response_patterns": {
            "when_disagreeing": "softens disagreement into a question",
            "when_enthusiastic": "long pause then 'that's beautiful'",
        },
    },
    {
        "persona_id": "p_joe_rogan",
        "persona_name": "Joe Rogan",
        "source_type": "real_world",
        "core_style": "conversational, bro-inflected, pivots to hunting or UFC unexpectedly",
        "vocabulary_markers": ["it's entirely possible", "100%", "dude", "bro", "think about it"],
        "ideological_positions": {"freedom": "radical personal freedom, anti-censorship"},
        "emotional_triggers": {"positive": "new experiences, honesty", "negative": "political correctness"},
        "response_patterns": {
            "when_disagreeing": "pushes back hard then immediately considers the other view",
            "when_enthusiastic": "interrupts with 'dude wait—'",
        },
    },
    {
        "persona_id": "p_socrates",
        "persona_name": "Socrates",
        "source_type": "real_world",
        "core_style": "elenctic, question-driven, feigns ignorance to expose contradiction",
        "vocabulary_markers": ["but tell me", "what do you mean by", "is it not so", "consider", "perhaps"],
        "ideological_positions": {"knowledge": "knowing that you know nothing is the beginning of wisdom"},
        "emotional_triggers": {"positive": "honest inquiry", "negative": "unexamined assumptions"},
        "response_patterns": {
            "when_disagreeing": "asks a clarifying question that demolishes the position",
            "when_enthusiastic": "launches into a long chain of questions",
        },
    },
]

# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

def check_ollama(model: str) -> None:
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.ConnectionError:
        sys.exit("Ollama not running. Start with: ollama serve")

    available = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
    if model not in available and model.split(":")[0] not in available:
        sys.exit(
            f"Model '{model}' not found.\n"
            f"Available: {available}\n"
            f"Pull with: ollama pull {model}"
        )


def build_system_prompt(persona: dict, topic: str, inject_drift: bool) -> str:
    positions = "\n".join(
        f"  - {k}: {v}"
        for k, v in persona.get("ideological_positions", {}).items()
    )
    patterns = persona.get("response_patterns", {})
    triggers = persona.get("emotional_triggers", {})
    markers = ", ".join(f'"{m}"' for m in persona.get("vocabulary_markers", []))

    drift_note = (
        "\n\nNote: the conversation has been going on for a while. "
        "The group is starting to converge toward consensus. "
        "Stay true to your character — react authentically even if it means disagreeing or redirecting."
        if inject_drift
        else ""
    )

    return (
        f"You are {persona['persona_name']}. Stay fully in character at all times.\n\n"
        f"## Your communication style\n{persona['core_style']}\n\n"
        f"## Vocabulary you naturally use\n{markers}\n\n"
        f"## Your ideological positions\n{positions}\n\n"
        f"## How you respond\n"
        f"  - When disagreeing: {patterns.get('when_disagreeing', 'push back directly')}\n"
        f"  - When enthusiastic: {patterns.get('when_enthusiastic', 'express it clearly')}\n\n"
        f"## What moves you\n"
        f"  - Positively: {triggers.get('positive', 'authenticity')}\n"
        f"  - Negatively: {triggers.get('negative', 'dishonesty')}\n\n"
        f"## Conversation topic\n{topic}\n\n"
        f"Write ONE chat message (2–4 sentences). "
        f"Sound like yourself — use your natural vocabulary and style. "
        f"No quotation marks around your response. No meta-commentary."
        f"{drift_note}"
    )


def generate_message(
    persona: dict,
    history: list[dict],
    topic: str,
    model: str,
    inject_drift: bool,
) -> str:
    system_prompt = build_system_prompt(persona, topic, inject_drift)

    # Sliding window: last 5 turns verbatim
    last_k = history[-5:]
    chat_messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt}
    ]
    for h in last_k:
        chat_messages.append({
            "role": "user",
            "content": f"{h['persona_name']}: {h['message']}",
        })
    chat_messages.append({
        "role": "user",
        "content": f"Now write your message as {persona['persona_name']}:",
    })

    resp = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": model,
            "stream": False,
            "messages": chat_messages,
            "options": {"temperature": 0.8, "num_predict": 256},
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()

# ---------------------------------------------------------------------------
# Speaker weight sampling via Dirichlet
# ---------------------------------------------------------------------------

def sample_speaker_weights(n: int, alpha: float, rng: random.Random) -> list[float]:
    """
    Dirichlet(alpha) over n speakers.
    alpha=0.5 → one agent dominates (Gini ~0.6)
    alpha=2.0 → moderate inequality matching real group chats (Gini ~0.3)
    alpha=8.0 → near-equal turns (Gini ~0.05)
    """
    if HAS_NUMPY:
        np_rng = np.random.default_rng(rng.randint(0, 2**32 - 1))
        return np_rng.dirichlet([alpha] * n).tolist()
    gammas = [rng.gammavariate(alpha, 1.0) for _ in range(n)]
    total = sum(gammas)
    return [g / total for g in gammas]


def gini(counts: list[int]) -> float:
    n = len(counts)
    s = sum(counts)
    if n == 0 or s == 0:
        return 0.0
    arr = sorted(counts)
    index_sum = sum((i + 1) * v for i, v in enumerate(arr))
    return (2 * index_sum) / (n * s) - (n + 1) / n

# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def simulate(
    personas: list[dict],
    topic: str,
    turns: int,
    speaker_alpha: float,
    drift_at: int | None,
    model: str,
    rng: random.Random,
) -> tuple[list[dict], dict[str, str], list[int], list[float]]:
    weights = sample_speaker_weights(len(personas), speaker_alpha, rng)
    speaker_counts = [0] * len(personas)
    transcript: list[dict] = []
    ground_truth: dict[str, str] = {}

    for turn in range(1, turns + 1):
        idx = rng.choices(range(len(personas)), weights=weights, k=1)[0]
        persona = personas[idx]
        speaker_counts[idx] += 1

        inject_drift = drift_at is not None and turn >= drift_at

        print(f"  {turn:3d}/{turns}  [{persona['persona_name']:<22}]  generating...", end="", flush=True)
        message = generate_message(persona, transcript, topic, model, inject_drift)
        drift_flag = "  [DRIFT]" if inject_drift else ""
        print(f"\r  {turn:3d}/{turns}  [{persona['persona_name']:<22}]{drift_flag}  {message[:70]}...")

        msg_id = f"msg_{turn:04d}"
        entry: dict[str, Any] = {
            "msg_id": msg_id,
            "turn": turn,
            "persona_id": persona["persona_id"],
            "persona_name": persona["persona_name"],
            "message": message,
            "drifted": inject_drift,
        }
        transcript.append(entry)
        ground_truth[msg_id] = persona["persona_id"]

    return transcript, ground_truth, speaker_counts, weights

# ---------------------------------------------------------------------------
# Persona loading
# ---------------------------------------------------------------------------

def load_personas_from_dir(path: Path) -> list[dict]:
    profiles = sorted(path.glob("*_profile.json"))
    if not profiles:
        raise FileNotFoundError(f"No *_profile.json files in {path}")
    personas = []
    for p in profiles[:8]:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        if "persona_id" not in data:
            slug = p.stem.replace("_profile", "").replace(" ", "_").lower()
            data["persona_id"] = f"p_{slug}"
        if "persona_name" not in data:
            data["persona_name"] = data.get("persona_id", p.stem)
        personas.append(data)
    if len(personas) < 2:
        raise ValueError(f"Need at least 2 personas, found {len(personas)}")
    return personas

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_outputs(
    transcript: list[dict],
    ground_truth: dict[str, str],
    speaker_counts: list[int],
    weights: list[float],
    personas: list[dict],
    params: dict,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = out_dir / "transcript.jsonl"
    with open(transcript_path, "w", encoding="utf-8") as f:
        for entry in transcript:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    gt_path = out_dir / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    n = len(transcript)
    meta = {
        "params": params,
        "n_personas": len(personas),
        "n_turns": n,
        "personas": [{"id": p["persona_id"], "name": p["persona_name"]} for p in personas],
        "gini": round(gini(speaker_counts), 4),
        "speaker_stats": {
            personas[i]["persona_id"]: {
                "name": personas[i]["persona_name"],
                "turns": speaker_counts[i],
                "share": round(speaker_counts[i] / n, 3),
                "dirichlet_weight": round(weights[i], 3),
            }
            for i in range(len(personas))
        },
    }
    meta_path = out_dir / "transcript_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("\n--- OUTPUT ---")
    print(f"  transcript   → {transcript_path}  ({n} turns)")
    print(f"  ground truth → {gt_path}")
    print(f"  metadata     → {meta_path}")
    print("\n--- SPEAKER DISTRIBUTION ---")
    for i, p in enumerate(personas):
        bar = "█" * int(speaker_counts[i] / n * 30)
        share_pct = speaker_counts[i] / n * 100
        print(f"  {p['persona_name']:<24} {speaker_counts[i]:3d} turns  {share_pct:5.1f}%  {bar}")
    print(f"\n  Gini: {meta['gini']:.4f}  (0=equal, 1=one dominates | real chats target: 0.28–0.42)")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate group chat transcript via Ollama persona-agents."
    )
    parser.add_argument(
        "--personas", type=Path, default=None,
        help="Dir with *_profile.json files. Default: 8 built-in personas.",
    )
    parser.add_argument(
        "--turns", type=int, default=60,
        help="Number of chat turns (default: 60).",
    )
    parser.add_argument(
        "--topic", type=str, default="the nature of authenticity",
        help="Conversation topic (default: 'the nature of authenticity').",
    )
    parser.add_argument(
        "--speaker-alpha", type=float, default=2.0,
        help="Dirichlet alpha for speaker weights. Low=unequal, high=equal (default: 2.0).",
    )
    parser.add_argument(
        "--drift-at", type=int, default=None,
        help="Turn at which character drift injection begins. Off by default.",
    )
    parser.add_argument(
        "--model", type=str, default="llama3.2",
        help="Ollama model (default: llama3.2).",
    )
    parser.add_argument(
        "--out", type=Path, default=Path("data/eval"),
        help="Output directory (default: data/eval).",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility.",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)

    check_ollama(args.model)

    if args.personas:
        print(f"Loading personas from {args.personas}...")
        personas = load_personas_from_dir(args.personas)
    else:
        print("Using 8 built-in default personas.")
        personas = DEFAULT_PERSONAS

    if len(personas) > 8:
        print(f"Warning: {len(personas)} profiles found, using first 8.")
        personas = personas[:8]

    print(
        f"Model: {args.model} | Topic: '{args.topic}' | "
        f"Turns: {args.turns} | Alpha: {args.speaker_alpha} | Seed: {args.seed}"
    )
    if args.drift_at:
        print(f"Drift injection starts at turn: {args.drift_at}")
    print()

    transcript, ground_truth, speaker_counts, weights = simulate(
        personas=personas,
        topic=args.topic,
        turns=args.turns,
        speaker_alpha=args.speaker_alpha,
        drift_at=args.drift_at,
        model=args.model,
        rng=rng,
    )

    params = {
        "model": args.model,
        "topic": args.topic,
        "turns": args.turns,
        "speaker_alpha": args.speaker_alpha,
        "drift_at": args.drift_at,
        "seed": args.seed,
        "n_personas": len(personas),
    }

    save_outputs(transcript, ground_truth, speaker_counts, weights, personas, params, args.out)


if __name__ == "__main__":
    main()

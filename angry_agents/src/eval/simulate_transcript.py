"""
simulate_transcript.py — generate group chat transcript via Ollama.

Instantiates persona-agents (up to 8), each conditioned on a structured profile
loaded from data/personas/*_profile.json. Each turn: one agent is selected via
Dirichlet-weighted sampling and generates a message via Ollama.

Output (default: data/eval/):
  transcript.jsonl       One JSON object per line, one per message turn.
  ground_truth.json      {msg_id: persona_id} — ground truth for persona ID eval.
  transcript_meta.json   Run params + speaker stats + Gini coefficient.

Transcript line schema:
  {"msg_id": "msg_0001", "turn": 1, "persona_id": "p_vader",
   "persona_name": "VADER", "message": "..."}

Usage:
  python -m angry_agents.src.eval.simulate_transcript
  python -m angry_agents.src.eval.simulate_transcript --turns 60 --topic "power and control"
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
DEFAULT_PERSONAS_DIR = Path("data/personas")

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

# ---------------------------------------------------------------------------
# System prompt — uses all fields present in real profile JSONs
# ---------------------------------------------------------------------------

def build_system_prompt(persona: dict, topic: str, inject_drift: bool) -> str:
    name = persona["persona_name"]

    # Ideological positions
    positions_raw = persona.get("ideological_positions", {})
    positions = "\n".join(f"  - {k}: {v}" for k, v in positions_raw.items()) if positions_raw else "  - not defined"

    # Humor (can be str or dict)
    humor_raw = persona.get("humor")
    if isinstance(humor_raw, dict):
        humor = f"{humor_raw.get('type', '')} — frequency: {humor_raw.get('frequency', '')} — targets: {humor_raw.get('targets', '')}"
    elif isinstance(humor_raw, str) and humor_raw:
        humor = humor_raw
    else:
        humor = "not defined"

    # Response patterns
    patterns = persona.get("response_patterns", {})
    pattern_lines = "\n".join(f"  - {k}: {v}" for k, v in patterns.items()) if patterns else "  - not defined"

    # Emotional triggers
    triggers = persona.get("emotional_triggers", {})
    trigger_lines = "\n".join(f"  - {k}: {v}" for k, v in triggers.items()) if triggers else "  - not defined"

    # Vocabulary markers
    markers_raw = persona.get("vocabulary_markers", [])
    markers = ", ".join(f'"{m}"' for m in markers_raw) if markers_raw else "not defined"

    # Social positioning
    social = persona.get("social_positioning", "not defined")

    # Exemplar quotes — most valuable for grounding style
    quotes_raw = persona.get("exemplar_quotes", [])
    if quotes_raw:
        quotes = "\n".join(f'  "{q}"' for q in quotes_raw[:5])
    else:
        quotes = "  (none available)"

    drift_note = (
        "\n\nNote: the conversation has been going on for a while and the group "
        "is starting to converge toward consensus. Stay true to your character — "
        "react authentically, even if it means disagreeing or redirecting."
        if inject_drift
        else ""
    )

    return (
        f"You are {name}. Stay fully in character at all times.\n\n"
        f"## Communication style\n{persona.get('core_style', 'not defined')}\n\n"
        f"## Humor\n{humor}\n\n"
        f"## Vocabulary you naturally use\n{markers}\n\n"
        f"## Ideological positions\n{positions}\n\n"
        f"## Emotional triggers\n{trigger_lines}\n\n"
        f"## How you respond\n{pattern_lines}\n\n"
        f"## Social positioning\n{social}\n\n"
        f"## Examples of how you actually speak\n{quotes}\n\n"
        f"## Conversation topic\n{topic}\n\n"
        f"Write ONE chat message (2–4 sentences). "
        f"Sound exactly like yourself — use your natural vocabulary, rhythm, and style. "
        f"No quotation marks around your response. No meta-commentary."
        f"{drift_note}"
    )

# ---------------------------------------------------------------------------
# Message generation via Ollama
# ---------------------------------------------------------------------------

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
    alpha=0.5 → one agent dominates (Gini ~0.6)
    alpha=2.0 → moderate inequality matching real group chats (Gini ~0.3)
    alpha=8.0 → near-equal turns (Gini ~0.05)
    """
    np_rng = np.random.default_rng(rng.randint(0, 2**32 - 1))
    return np_rng.dirichlet([alpha] * n).tolist()


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

def load_personas(path: Path) -> list[dict]:
    profiles = sorted(path.glob("*_profile.json"))
    if not profiles:
        raise FileNotFoundError(f"No *_profile.json files in {path}")

    personas = []
    for p in profiles[:8]:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        # derive persona_id from filename if missing
        if "persona_id" not in data:
            slug = p.stem.replace("_profile", "").lower()
            data["persona_id"] = f"p_{slug}"
        # persona_name fallback
        if "persona_name" not in data:
            data["persona_name"] = data["persona_id"]
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
        "--personas", type=Path, default=DEFAULT_PERSONAS_DIR,
        help=f"Dir with *_profile.json files (default: {DEFAULT_PERSONAS_DIR}).",
    )
    parser.add_argument(
        "--turns", type=int, default=60,
        help="Number of chat turns (default: 60).",
    )
    parser.add_argument(
        "--topic", type=str, default="the nature of power and authenticity",
        help="Conversation topic (default: 'the nature of power and authenticity').",
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

    print(f"Loading personas from {args.personas}...")
    personas = load_personas(args.personas)
    if len(personas) > 8:
        print(f"Warning: {len(personas)} profiles found, using first 8.")
        personas = personas[:8]

    print(f"Loaded {len(personas)} personas: {[p['persona_name'] for p in personas]}")
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
        "personas_dir": str(args.personas),
    }

    save_outputs(transcript, ground_truth, speaker_counts, weights, personas, params, args.out)


if __name__ == "__main__":
    main()

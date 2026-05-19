"""
simulate_transcript.py — generate group chat transcript via Ollama.

Instantiates persona-agents (up to 8), each conditioned on a structured profile
loaded from data/personas/*_profile.json. Each turn: one agent is selected via
Dirichlet-weighted sampling and generates a message via Ollama.

Anonymity model:
  - Each persona gets an opaque label (Agent A … Agent G), shuffled per run.
  - Author tag produced by chat_messages_service._make_author (HMAC-SHA256).
  - Agents see history with opaque author tags — they don't know who spoke.
  - transcript.jsonl (judge-facing): only {msg_id, turn, author, message, drifted, perturbed}.
    No persona_id, no persona_name.

Secret files (never shown to judges):
  ground_truth.json   {msg_id: persona_id}
  author_map.json     {author_tag: persona_id}  ← needed by compute_metrics.py

Transcript line schema (judge sees):
  {"msg_id": "msg_0001", "turn": 1, "author": "Agent A 4f3a2b1c9d8e",
   "message": "...", "drifted": false, "perturbed": false}

Perturbation system:
  Every N turns of a given agent (N randomised per-agent in [--perturb-min, --perturb-max]),
  a [perturbation] block is appended to that agent's system prompt only. Not visible to other
  agents or judges. Forces character-consistent reaction (may be agreement, silence, challenge).

  Optional drift detection (--embed-model): pairwise cosine similarity across agents'
  last-turn embeddings. If drift_score > --drift-threshold, perturbation fires early.

Usage:
  python -m angry_agents.src.eval.simulate_transcript
  python -m angry_agents.src.eval.simulate_transcript --turns 60 --topic "power and control"
  python -m angry_agents.src.eval.simulate_transcript --personas data/personas/
  python -m angry_agents.src.eval.simulate_transcript --drift-at 40 --seed 42
  python -m angry_agents.src.eval.simulate_transcript --model mistral --speaker-alpha 0.5
  python -m angry_agents.src.eval.simulate_transcript --secret my-secret-key
  python -m angry_agents.src.eval.simulate_transcript --perturb-min 10 --perturb-max 15
  python -m angry_agents.src.eval.simulate_transcript --embed-model nomic-embed-text --drift-threshold 0.85
"""

import argparse
import json
import os
import random
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import requests

from angry_agents.src.db.services.chat_messages_service import _make_author

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_PERSONAS_DIR = Path("data/personas")
DEFAULT_SECRET = os.getenv("AUTHOR_SECRET", "eval-dev-secret")

PERTURBATION_SIGNAL = (
    "\n\n[perturbation]\n"
    "The conversation is moving toward consensus.\n"
    "React to the last message in a way that reflects your genuine position,\n"
    "even if it means disagreeing, redirecting, or introducing a new angle.\n"
    "Stay fully in character."
)

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

def build_system_prompt(persona: dict, topic: str, inject_drift: bool, inject_perturbation: bool = False) -> str:
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

    perturb_note = PERTURBATION_SIGNAL if inject_perturbation else ""

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
        f"{perturb_note}"
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
    inject_perturbation: bool = False,
) -> str:
    system_prompt = build_system_prompt(persona, topic, inject_drift, inject_perturbation)

    # Sliding window: last 5 turns verbatim.
    # Use opaque author tags — agents don't know who they're talking to.
    last_k = history[-5:]
    chat_messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt}
    ]
    for h in last_k:
        chat_messages.append({
            "role": "user",
            "content": f"{h['author']}: {h['message']}",
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
# Drift detection
# ---------------------------------------------------------------------------

def get_embedding(text: str, model: str) -> "np.ndarray | None":
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return np.array(resp.json()["embedding"], dtype=float)
    except Exception:
        return None


def _cosine_sim(a: "np.ndarray", b: "np.ndarray") -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom else 0.0


def drift_score(agent_embeddings: "list[np.ndarray]") -> float:
    """Pairwise cosine similarity across all agents' last-turn embeddings."""
    sims = [_cosine_sim(a, b) for a, b in combinations(agent_embeddings, 2)]
    return float(np.mean(sims)) if sims else 0.0

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
    secret: str,
    perturb_interval: tuple[int, int] = (10, 15),
    drift_threshold: float = 0.85,
    embed_model: str | None = None,
) -> tuple[list[dict], dict[str, str], dict[str, str], list[int], list[float]]:
    # Opaque labels shuffled per run — neither agents nor judges see real names.
    labels = [f"Agent {chr(65 + i)}" for i in range(len(personas))]
    rng.shuffle(labels)
    label_map = {p["persona_id"]: labels[i] for i, p in enumerate(personas)}
    # author_tag = "{opaque_label} {hmac[:12]}" — stable per persona, keyed on persona_id
    author_tag_map = {
        p["persona_id"]: (
            f"{label_map[p['persona_id']]} "
            f"{_make_author(p['persona_id'], '', secret)[:12]}"
        )
        for p in personas
    }
    # Reverse map for metrics: author_tag → persona_id (secret file, never shown to judges)
    author_map = {tag: pid for pid, tag in author_tag_map.items()}

    weights = sample_speaker_weights(len(personas), speaker_alpha, rng)
    speaker_counts = [0] * len(personas)
    transcript: list[dict] = []
    ground_truth: dict[str, str] = {}

    # Per-agent perturbation thresholds: randomised per agent, stable per run.
    perturb_n = {
        p["persona_id"]: rng.randint(perturb_interval[0], perturb_interval[1])
        for p in personas
    }
    agent_turns: dict[str, int] = {p["persona_id"]: 0 for p in personas}
    last_embeddings: dict[str, np.ndarray] = {}

    for turn in range(1, turns + 1):
        idx = rng.choices(range(len(personas)), weights=weights, k=1)[0]
        persona = personas[idx]
        speaker_counts[idx] += 1
        pid = persona["persona_id"]
        agent_turns[pid] += 1

        inject_drift = drift_at is not None and turn >= drift_at

        # Fire perturbation every N-th turn for this specific agent.
        inject_perturbation = agent_turns[pid] % perturb_n[pid] == 0

        # Drift-based early trigger: if agents are converging, perturb regardless of N.
        current_drift = 0.0
        if embed_model and len(last_embeddings) >= 2:
            current_drift = drift_score(list(last_embeddings.values()))
            if current_drift > drift_threshold:
                inject_perturbation = True

        flags = ""
        if inject_perturbation:
            flags += "  [PERTURB]"
        if inject_drift:
            flags += "  [DRIFT]"
        if current_drift > drift_threshold:
            flags += f"  [drift={current_drift:.2f}]"

        print(f"  {turn:3d}/{turns}  [{persona['persona_name']:<22}]{flags}  generating...", end="", flush=True)
        message = generate_message(persona, transcript, topic, model, inject_drift, inject_perturbation)
        print(f"\r  {turn:3d}/{turns}  [{persona['persona_name']:<22}]{flags}  {message[:60]}...")

        if embed_model:
            emb = get_embedding(message, embed_model)
            if emb is not None:
                last_embeddings[pid] = emb

        msg_id = f"msg_{turn:04d}"
        author = author_tag_map[pid]
        entry: dict[str, Any] = {
            "msg_id": msg_id,
            "turn": turn,
            "persona_id": pid,  # stripped before judge output
            "author": author,
            "message": message,
            "drifted": inject_drift,
            "perturbed": inject_perturbation,
            "drift_score": round(current_drift, 4) if embed_model else None,
        }
        transcript.append(entry)
        ground_truth[msg_id] = pid

    return transcript, ground_truth, author_map, speaker_counts, weights

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

_JUDGE_FIELDS = ("msg_id", "turn", "author", "message", "drifted", "perturbed")


def save_outputs(
    transcript: list[dict],
    ground_truth: dict[str, str],
    author_map: dict[str, str],
    speaker_counts: list[int],
    weights: list[float],
    personas: list[dict],
    params: dict,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Judge-facing: only opaque fields — no persona_id, no persona_name.
    transcript_path = out_dir / "transcript.jsonl"
    with open(transcript_path, "w", encoding="utf-8") as f:
        for entry in transcript:
            judge_entry = {k: entry[k] for k in _JUDGE_FIELDS}
            f.write(json.dumps(judge_entry, ensure_ascii=False) + "\n")

    # Secret files — never shown to judges.
    gt_path = out_dir / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)

    am_path = out_dir / "author_map.json"
    with open(am_path, "w", encoding="utf-8") as f:
        json.dump(author_map, f, indent=2, ensure_ascii=False)

    n = len(transcript)
    perturbed_turns = sum(1 for e in transcript if e.get("perturbed"))
    recorded_drift = [e["drift_score"] for e in transcript if e.get("drift_score") is not None]
    meta = {
        "params": params,
        "n_personas": len(personas),
        "n_turns": n,
        "personas": [{"id": p["persona_id"], "name": p["persona_name"]} for p in personas],
        "gini": round(gini(speaker_counts), 4),
        "perturbation": {
            "turns_perturbed": perturbed_turns,
            "perturb_share": round(perturbed_turns / n, 3) if n else 0.0,
            "drift_detection_enabled": params.get("embed_model") is not None,
            "drift_threshold": params.get("drift_threshold"),
            "max_drift_score": round(max(recorded_drift), 4) if recorded_drift else None,
            "mean_drift_score": round(float(np.mean(recorded_drift)), 4) if recorded_drift else None,
        },
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
    print(f"  transcript   → {transcript_path}  ({n} turns)  [judge-safe]")
    print(f"  ground truth → {gt_path}  [secret]")
    print(f"  author map   → {am_path}  [secret]")
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
    parser.add_argument(
        "--secret", type=str, default=DEFAULT_SECRET,
        help="HMAC secret for author tag generation (default: $AUTHOR_SECRET env var).",
    )
    parser.add_argument(
        "--perturb-min", type=int, default=10,
        help="Min agent-turns between perturbations (default: 10).",
    )
    parser.add_argument(
        "--perturb-max", type=int, default=15,
        help="Max agent-turns between perturbations (default: 15).",
    )
    parser.add_argument(
        "--embed-model", type=str, default=None,
        help="Ollama model for drift embeddings (e.g. 'nomic-embed-text'). Omit to disable drift detection.",
    )
    parser.add_argument(
        "--drift-threshold", type=float, default=0.85,
        help="Cosine similarity threshold to trigger early perturbation (default: 0.85).",
    )
    args = parser.parse_args()

    if args.perturb_min > args.perturb_max:
        sys.exit(f"--perturb-min ({args.perturb_min}) must be ≤ --perturb-max ({args.perturb_max})")

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
    print(f"Perturbation: every {args.perturb_min}–{args.perturb_max} agent-turns per persona")
    if args.embed_model:
        print(f"Drift detection: {args.embed_model} | threshold: {args.drift_threshold}")
    if args.drift_at:
        print(f"Global drift injection starts at turn: {args.drift_at}")
    print()

    transcript, ground_truth, author_map, speaker_counts, weights = simulate(
        personas=personas,
        topic=args.topic,
        turns=args.turns,
        speaker_alpha=args.speaker_alpha,
        drift_at=args.drift_at,
        model=args.model,
        rng=rng,
        secret=args.secret,
        perturb_interval=(args.perturb_min, args.perturb_max),
        drift_threshold=args.drift_threshold,
        embed_model=args.embed_model,
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
        "perturb_interval": [args.perturb_min, args.perturb_max],
        "embed_model": args.embed_model,
        "drift_threshold": args.drift_threshold,
    }

    save_outputs(transcript, ground_truth, author_map, speaker_counts, weights, personas, params, args.out)


if __name__ == "__main__":
    main()

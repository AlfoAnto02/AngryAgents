"""
Evaluation — 20 RAG-assisted judges (5 per role × 4 roles).

Each role is instantiated 5 times independently. Instances of the same role
share the same retrieval fields and focus, but run as separate LLM calls,
producing variance that drives Phase 2 deliberation.

Run from the repo root:
    python -m angry_agents.src.rag.evaluation_test_20_judges --chat <path/to/chat.jsonl>

The chat file must be a JSONL file where each line is a message object with at
least "author" (anonymous digest string) and "message" (text) fields — the same
format produced by the UI and stored in Chat_messages.

Requires the ChromaDB index to be built first:
    python -m angry_agents.src.rag.build_index
"""

import argparse
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from .judge_with_tools import run_persona_identification_with_tools
from .retriever import retrieve_candidates

_DEFAULT_CHAT_FILE = Path(__file__).parents[3] / "data" / "eval" / "chat_simulation_with_embedding" / "transcript.jsonl"
PERSONAS_DIR = Path(__file__).parents[3] / "data" / "personas"
EVAL_DIR = Path(__file__).parents[2] / "src" / "agents" / "judge_eval"

_EXCLUDED_PROFILES = {"jimmy_profile_old.json"}

JUDGES_PER_ROLE = 5

_ROLE_CONFIGS: list[dict] = [
    {
        "role": "style",
        "focus": "vocabulary, sentence structure, tone, and rhetorical habits",
        "rag_fields": ["style", "voice"],
        "top_k": 20,
    },
    {
        "role": "ideology",
        "focus": "values, political views, moral stances, and belief systems",
        "rag_fields": ["worldview"],
        "top_k": 20,
    },
    {
        "role": "general",
        "focus": "all observable traits combined: style, ideology, and behaviour",
        "rag_fields": None,
        "top_k": 20,
    },
    {
        "role": "behavioral",
        "focus": "situational reactions, escalation patterns, and conversation goals",
        "rag_fields": ["behavior"],
        "top_k": 20,
    },
]

# 20 judge instances: style_1…style_5, ideology_1…ideology_5, etc.
JUDGES: list[dict] = [
    {**cfg, "name": f"{cfg['role']}_{i}"}
    for cfg in _ROLE_CONFIGS
    for i in range(1, JUDGES_PER_ROLE + 1)
]


def _load_all_profiles() -> dict[str, dict]:
    profiles: dict[str, dict] = {}
    for path in sorted(PERSONAS_DIR.glob("*.json")):
        if path.name in _EXCLUDED_PROFILES:
            continue
        p = json.loads(path.read_text(encoding="utf-8"))
        profiles[p["persona_name"]] = p
    return profiles


def _load_chat(chat_file: Path) -> dict:
    messages = [
        json.loads(line)
        for line in chat_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {"messages": messages}


def _messages_by_digest(chat: dict) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for msg in chat["messages"]:
        if author := msg.get("author"):
            grouped[author].append(msg["message"])
    return dict(grouped)


def _next_eval_path() -> Path:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(EVAL_DIR.glob("eval_20j_*.jsonl"))
    n = len(existing) + 1
    return EVAL_DIR / f"eval_20j_{n}.jsonl"


def _build_record(
    judge_id: int,
    judge: dict,
    chat_id: int,
    result,
    candidate_names: list[str],
) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    # Persona-centric format expected by src/eval/metrics_persona_id.py:
    # for each persona, which author did the judge predict played it + all author scores.
    persona_names = [s.persona_name for s in result.matches[0].scores] if result.matches else []
    persona_identification = []
    for pname in persona_names:
        author_scores = [
            {"author": m.author, "score": next((s.score for s in m.scores if s.persona_name == pname), 1)}
            for m in result.matches
        ]
        predicted = max(author_scores, key=lambda x: x["score"])["author"]
        persona_identification.append({
            "persona_name": pname,
            "predicted": predicted,
            "scores": author_scores,
        })

    return {
        "ID_judge": judge_id,
        "ID_chat": chat_id,
        "Score": None,
        "Created_at": now,
        "Updated_at": now,
        "Deleted_at": None,
        "judge_name": judge["name"],
        "judge_role": judge["role"],
        "rag_candidates": candidate_names,
        "persona_identification": persona_identification,
    }


def _print_result(judge: dict, result, candidate_names: list[str]) -> None:
    print(f"\n{'=' * 60}")
    print(f"  [{judge['name']}]  —  {judge['focus']}")
    print(f"  Candidates ({len(candidate_names)}): {candidate_names}")
    print(f"{'=' * 60}")
    for match in result.matches:
        print(f"\n  Author: {match.author}")
        for s in match.scores:
            print(f"    {s.persona_name}  →  {s.score}/5")
        print(f"    >> Predicted: {match.predicted}")


def run_evaluation_from_db_data(
    chat: dict,
    all_profiles: dict[str, dict],
    chat_id: int,
    progress_callback=None,
    forced_names: list[str] | None = None,
) -> list[dict]:
    """
    Run the 20-judge pipeline on already-loaded chat data (from the database).

    chat: {"messages": [{"author": digest, "message": text}, ...]}
    all_profiles: {persona_name: profile_dict} — loaded from disk or DB
    chat_id: stored in the output records
    progress_callback: optional callable(done_count, total) called after each judge completes
    forced_names: persona names to always include as candidates (e.g. actual chat participants)
    """
    messages_by_digest = _messages_by_digest(chat)

    if not chat["messages"]:
        raise ValueError("Chat has no messages")
    if not all_profiles:
        raise ValueError("No persona profiles loaded")

    _completed = [0]

    def _run_judge(judge_id: int, judge: dict) -> dict:
        candidates = retrieve_candidates(
            messages_by_digest=messages_by_digest,
            profiles_by_name=all_profiles,
            top_k=judge["top_k"],
            field_filter=judge["rag_fields"],
            forced_names=forced_names,
            role=judge["role"],
        )
        candidate_names = [p["persona_name"] for p in candidates]
        result = run_persona_identification_with_tools(
            focus=judge["focus"],
            chat=chat,
            candidates=candidates,
            role=judge["role"],
        )
        _completed[0] += 1
        if progress_callback:
            progress_callback(_completed[0], len(JUDGES))
        return _build_record(judge_id, judge, chat_id, result, candidate_names)

    futures_map: dict = {}
    with ThreadPoolExecutor(max_workers=len(JUDGES)) as pool:
        for judge_id, judge in enumerate(JUDGES, start=1):
            futures_map[pool.submit(_run_judge, judge_id, judge)] = judge_id

    records = [None] * len(JUDGES)
    for future in as_completed(futures_map):
        judge_id = futures_map[future]
        records[judge_id - 1] = future.result()

    return records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run 20-judge RAG evaluation on a chat JSONL file."
    )
    parser.add_argument(
        "--chat",
        type=Path,
        default=_DEFAULT_CHAT_FILE,
        help=(
            "Path to a JSONL chat file. Each line must be a message object with "
            "'author' (digest string) and 'message' fields. "
            f"Defaults to the test chat at {_DEFAULT_CHAT_FILE}."
        ),
    )
    args = parser.parse_args()
    chat_file: Path = args.chat

    chat = _load_chat(chat_file)
    all_profiles = _load_all_profiles()
    messages_by_digest = _messages_by_digest(chat)
    chat_id = 1

    print(f"\nChat file: {chat_file}")
    print(f"Chat: {len(chat['messages'])} messages, {len(messages_by_digest)} agents")
    print(f"Full DB: {len(all_profiles)} personas")
    print(f"Judges: {len(JUDGES)} ({JUDGES_PER_ROLE} per role × {len(_ROLE_CONFIGS)} roles)\n")

    if not chat["messages"]:
        raise ValueError(f"Chat file is empty: {chat_file}")
    if not all_profiles:
        raise ValueError(f"No persona files found in: {PERSONAS_DIR}")

    def _run_judge(judge_id: int, judge: dict) -> dict:
        print(f"[{judge['name']}] starting (fields={judge['rag_fields']})...")
        candidates = retrieve_candidates(
            messages_by_digest=messages_by_digest,
            profiles_by_name=all_profiles,
            top_k=judge["top_k"],
            field_filter=judge["rag_fields"],
            role=judge["role"],
        )
        candidate_names = [p["persona_name"] for p in candidates]
        print(f"  [{judge['name']}] → {candidate_names}")
        result = run_persona_identification_with_tools(
            focus=judge["focus"],
            chat=chat,
            candidates=candidates,
            role=judge["role"],
        )
        _print_result(judge, result, candidate_names)
        return _build_record(judge_id, judge, chat_id, result, candidate_names)

    futures_map: dict = {}
    with ThreadPoolExecutor(max_workers=len(JUDGES)) as pool:
        for judge_id, judge in enumerate(JUDGES, start=1):
            futures_map[pool.submit(_run_judge, judge_id, judge)] = judge_id

    records = [None] * len(JUDGES)
    for future in as_completed(futures_map):
        judge_id = futures_map[future]
        records[judge_id - 1] = future.result()

    out_path = _next_eval_path()
    out_path.write_text(
        "\n".join(json.dumps(r) for r in records), encoding="utf-8"
    )
    print(f"\n{'=' * 60}")
    print(f"  Saved → {out_path}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()

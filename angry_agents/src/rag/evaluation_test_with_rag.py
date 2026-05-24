"""
Evaluation test — RAG pre-filter + LLM tool-use judges.

Each judge role runs its own retrieval against the chunk subset most relevant
to its focus, then uses the LLM with ChromaDB tool access during reasoning.

Run from the repo root:
    python -m angry_agents.src.rag.evaluation_test_with_rag

Requires the ChromaDB index to be built first:
    python -m angry_agents.src.rag.build_index
"""

import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from .judge_with_tools import run_persona_identification_with_tools
from .retriever import retrieve_candidates

CHAT_FILE = Path(__file__).parents[3] / "data" / "eval" / "chat_simulation_with_embedding" / "transcript.jsonl"
PERSONAS_DIR = Path(__file__).parents[3] / "data" / "personas"
EVAL_DIR = Path(__file__).parents[2] / "src" / "agents" / "judge_eval"

_EXCLUDED_PROFILES = {"jimmy_profile_old.json"}

# Each judge role retrieves candidates from its own relevant chunk subset.
# This preserves diversity: a style judge and an ideology judge may receive
# different shortlists because they search on different signals.
JUDGES: list[dict] = [
    {
        "name": "style",
        "focus": "vocabulary, sentence structure, tone, and rhetorical habits",
        "rag_fields": ["style", "voice"],
        "top_k": 20,
    },
    {
        "name": "ideology",
        "focus": "values, political views, moral stances, and belief systems",
        "rag_fields": ["worldview"],
        "top_k": 20,
    },
    {
        "name": "general",
        "focus": "all observable traits combined: style, ideology, and behaviour",
        "rag_fields": None,   # None = search all chunk types
        "top_k": 20,
    },
    {
        "name": "behavioral",
        "focus": "situational reactions, escalation patterns, and conversation goals",
        "rag_fields": ["behavior"],
        "top_k": 20,
    },
]


def _load_all_profiles() -> dict[str, dict]:
    profiles: dict[str, dict] = {}
    for path in sorted(PERSONAS_DIR.glob("*.json")):
        if path.name in _EXCLUDED_PROFILES:
            continue
        p = json.loads(path.read_text(encoding="utf-8"))
        profiles[p["persona_name"]] = p
    return profiles


def _load_chat() -> dict:
    messages = [
        json.loads(line)
        for line in CHAT_FILE.read_text(encoding="utf-8").splitlines()
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
    existing = sorted(EVAL_DIR.glob("eval_rag_*.jsonl"))
    n = len(existing) + 1
    return EVAL_DIR / f"eval_rag_{n}.jsonl"


def _build_record(
    judge_id: int,
    judge_name: str,
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
        "judge_name": judge_name,
        "rag_candidates": candidate_names,
        "persona_identification": persona_identification,
    }


def _print_result(judge_name: str, focus: str, result, candidate_names: list[str]) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {judge_name.upper()}  —  {focus}")
    print(f"  Candidates ({len(candidate_names)}): {candidate_names}")
    print(f"{'=' * 60}")
    for match in result.matches:
        print(f"\n  Author: {match.author}")
        for s in match.scores:
            print(f"    {s.persona_name}  →  {s.score}/5")
        print(f"    >> Predicted: {match.predicted}")


def main() -> None:
    chat = _load_chat()
    all_profiles = _load_all_profiles()
    messages_by_digest = _messages_by_digest(chat)
    chat_id = 1

    print(f"\nChat: {len(chat['messages'])} messages, {len(messages_by_digest)} agents")
    print(f"Full DB: {len(all_profiles)} personas\n")

    if not chat["messages"]:
        raise ValueError(f"Chat file is empty: {CHAT_FILE}")
    if not all_profiles:
        raise ValueError(f"No persona files found in: {PERSONAS_DIR}")

    def _run_judge(judge_id: int, judge: dict) -> dict:
        print(f"[{judge['name']}] Retrieving candidates (fields={judge['rag_fields']})...")
        candidates = retrieve_candidates(
            messages_by_digest=messages_by_digest,
            profiles_by_name=all_profiles,
            top_k=judge["top_k"],
            field_filter=judge["rag_fields"],
        )
        candidate_names = [p["persona_name"] for p in candidates]
        print(f"  [{judge['name']}] → {candidate_names}")
        result = run_persona_identification_with_tools(
            focus=judge["focus"],
            chat=chat,
            candidates=candidates,
        )
        _print_result(judge["name"], judge["focus"], result, candidate_names)
        return _build_record(judge_id, judge["name"], chat_id, result, candidate_names)

    futures_map = {}
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

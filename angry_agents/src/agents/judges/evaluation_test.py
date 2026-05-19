"""
Run from the repo root:
    python -m angry_agents.src.agents.judges.evaluation_test
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from .general_judge import GeneralJudge
from .ideology_judge import IdeologyJudge
from .style_judge import StyleJudge

CHAT_FILE = Path(__file__).parents[4] / "data" / "eval" / "chat_simulation_with_embedding" / "transcript.jsonl"
PERSONAS_DIR = Path(__file__).parents[4] / "data" / "personas"
EVAL_DIR = Path(__file__).parents[2] / "judge_eval"

JUDGES = [
    ("style",    StyleJudge()),
    ("ideology", IdeologyJudge()),
    ("general",  GeneralJudge()),
]


def _load_personas() -> list[dict]:
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(PERSONAS_DIR.glob("*.json"))
    ]


def _load_chat() -> dict:
    messages = [
        json.loads(line)
        for line in CHAT_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {"messages": messages}


def _next_eval_path() -> Path:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(EVAL_DIR.glob("eval_test_*.jsonl"))
    n = len(existing) + 1
    return EVAL_DIR / f"eval_test_{n}.jsonl"


def _build_record(judge_id: int, judge_name: str, chat_id: int, result) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "ID_judge": judge_id,
        "ID_chat": chat_id,
        "Score": None,
        "Created_at": now,
        "Updated_at": now,
        "Deleted_at": None,
        "judge_name": judge_name,
        "persona_identification": [
            {
                "author": match.author,
                "predicted_persona": match.predicted,
                "scores": [
                    {"persona_name": s.persona_name, "score": s.score}
                    for s in match.scores
                ],
            }
            for match in result.matches
        ],
    }


def _print_result(judge_name: str, result) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {judge_name.upper()}")
    print(f"{'=' * 60}")
    for match in result.matches:
        print(f"\n  Author: {match.author}")
        for s in match.scores:
            print(f"    {s.persona_name}  →  {s.score}/5")
        print(f"    >> Predicted persona: {match.predicted}")


def main() -> None:
    chat = _load_chat()
    personas = _load_personas()
    chat_id = 1

    n_agents = len({m["author"] for m in chat["messages"]})
    print(f"\nChat: {len(chat['messages'])} messages, {n_agents} agents")
    print(f"Personas to evaluate: {[p['persona_name'] for p in personas]}\n")

    if not chat["messages"]:
        raise ValueError(f"Chat file is empty: {CHAT_FILE}")
    if not personas:
        raise ValueError(f"No persona files found in: {PERSONAS_DIR}")

    records = []
    for judge_id, (judge_name, judge) in enumerate(JUDGES, start=1):
        result = judge.persona_identification(chat, personas)
        _print_result(judge_name, result)
        records.append(_build_record(judge_id, judge_name, chat_id, result))

    out_path = _next_eval_path()
    out_path.write_text(
        "\n".join(json.dumps(r) for r in records), encoding="utf-8"
    )
    print(f"\n{'=' * 60}")
    print(f"  Saved → {out_path}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()

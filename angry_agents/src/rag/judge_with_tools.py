"""
RAG-assisted judge that combines pre-filtering with LLM tool use.

Flow:
  1. retrieve_candidates() narrows the database to top-K profiles (per judge role).
  2. The judge LLM receives ALL candidates as context in a single call.
  3. During reasoning the judge can call search_persona_profiles() to query
     ChromaDB on demand for deeper investigation.
  4. Final output: PersonaIdentificationResult (same interface as base judges).

One LLM call per judge (not per candidate) — 17x cheaper than the per-candidate loop.
Requires LLM_BACKEND=openai (tool calling).
"""

import json
import logging
import os
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from openai import OpenAI

from ..agents.agent_config import (
    LLM_BACKEND,
    OPENAI_MODEL,
    format_messages,
    format_profile,
)
from ..agents.judges.base_judge import AuthorMatch, PersonaIdentificationResult, PersonaScore
from ..agents.judges.templates import render_prompt
from .tool import SEARCH_TOOL, execute as execute_rag_tool

if TYPE_CHECKING:
    from .token_tracker import TokenTracker

load_dotenv()
log = logging.getLogger(__name__)

_MAX_TOOL_CALLS = 5

_ROLE_TEMPLATES: dict[str, str] = {
    "style": "persona_id_style_batch.j2",
    "ideology": "persona_id_ideology_batch.j2",
    "general": "persona_id_general_batch.j2",
    "behavioral": "persona_id_behavioral_batch.j2",
}


def _openai_tool_loop(
    system: str,
    user: str,
    model: str,
    *,
    tracker: "TokenTracker | None" = None,
    judge_name: str = "unknown",
    judge_role: str = "general",
) -> str:
    """
    Run an OpenAI chat completion that can invoke search_persona_profiles.
    Returns the final text content once the model stops calling tools.

    If *tracker* is provided, records token usage for every API call made
    (initial call, any tool-follow-up calls, and the force-final call).
    """
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    for _ in range(_MAX_TOOL_CALLS + 1):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=[SEARCH_TOOL],
            tool_choice="auto",
            response_format={"type": "json_object"},
            temperature=0,
        )
        choice = response.choices[0]

        if tracker is not None and response.usage:
            call_type = "tool_followup" if _ > 0 else "main"
            tracker.record(
                judge_name=judge_name,
                judge_role=judge_role,
                call_type=call_type,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )

        if choice.finish_reason != "tool_calls":
            content = choice.message.content or ""
            if content.strip():
                return content
            break

        messages.append(choice.message)
        for tc in choice.message.tool_calls:
            args = json.loads(tc.function.arguments)
            result = execute_rag_tool(
                query=args.get("query", ""),
                field=args.get("field"),
            )
            log.debug("tool call: query=%r field=%r → %d chars", args.get("query"), args.get("field"), len(result))
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    messages.append({"role": "user", "content": "Provide your final JSON answer now."})
    final = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
    )
    if tracker is not None and final.usage:
        tracker.record(
            judge_name=judge_name,
            judge_role=judge_role,
            call_type="force_final",
            prompt_tokens=final.usage.prompt_tokens,
            completion_tokens=final.usage.completion_tokens,
        )
    return final.choices[0].message.content


def _parse_batch_scores(
    raw: str,
    authors: list[str],
    candidates: list[dict],
) -> dict[str, list[PersonaScore]]:
    """
    Parse batch JSON output:
      {"scores": {"<author_digest>": {"<PERSONA_NAME>": <1-5>, ...}, ...}}

    Missing authors or personas default to score 1.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("batch parse: invalid JSON, defaulting all scores to 1")
        data = {}

    scores_map: dict = data.get("scores", {})
    result: dict[str, list[PersonaScore]] = {}

    for author in authors:
        author_scores = scores_map.get(author, {})
        result[author] = [
            PersonaScore(
                persona_name=p["persona_name"],
                score=int(author_scores.get(p["persona_name"], 1)),
            )
            for p in candidates
        ]

    return result


def run_persona_identification_with_tools(
    focus: str,
    chat: dict,
    candidates: list[dict],
    model: str = OPENAI_MODEL,
    role: str = "general",
    judge_name: str = "unknown",
    tracker: "TokenTracker | None" = None,
) -> PersonaIdentificationResult:
    """
    Identify personas using a single RAG-assisted LLM call per judge.

    candidates  — pre-filtered profiles from retrieve_candidates().
    focus       — the judge's lens description (used for logging/fallback).
    role        — judge role: "style", "ideology", "general", or "behavioral".
                  Selects the role-specific batch template.
    judge_name  — label used in token tracking (e.g. "style_1").
    tracker     — optional TokenTracker; records usage for every API call made.

    Requires LLM_BACKEND=openai.
    """
    if LLM_BACKEND != "openai":
        raise RuntimeError(
            "run_persona_identification_with_tools requires LLM_BACKEND=openai. "
            f"Current backend: {LLM_BACKEND!r}."
        )

    template = _ROLE_TEMPLATES.get(role, "persona_id_general_batch.j2")

    messages_block, authors = format_messages(chat)
    if not authors:
        raise ValueError(
            "run_persona_identification_with_tools: chat has no messages with authors."
        )

    author_list = ", ".join(authors)
    persona_names = ", ".join(p["persona_name"] for p in candidates)
    candidates_block = "\n\n".join(
        f"--- {p['persona_name']} ---\n{format_profile(p)}"
        for p in candidates
    )

    system, user = render_prompt(
        template,
        n_candidates=len(candidates),
        candidates_block=candidates_block,
        messages_block=messages_block,
        author_list=author_list,
        persona_names=persona_names,
    )

    raw = _openai_tool_loop(
        system,
        user,
        model,
        tracker=tracker,
        judge_name=judge_name,
        judge_role=role,
    )
    author_persona_scores = _parse_batch_scores(raw, authors, candidates)

    matches = [
        AuthorMatch(author=a, scores=author_persona_scores[a])
        for a in authors
    ]
    return PersonaIdentificationResult(matches=matches)

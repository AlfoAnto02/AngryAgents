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

from __future__ import annotations

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

_FIDELITY_TEMPLATES: dict[str, str] = {
    "style": "individual_fidelity_style.j2",
    "ideology": "individual_fidelity_ideology.j2",
    "general": "individual_fidelity_general.j2",
    "behavioral": "individual_fidelity_behavioral.j2",
}


def _openai_tool_loop(
    system: str,
    user: str,
    model: str,
    judge_name: str = "unknown",
    judge_role: str = "general",
    tracker: "TokenTracker | None" = None,
) -> str:
    """
    Run an OpenAI chat completion that can invoke search_persona_profiles.
    Returns the final text content once the model stops calling tools.
    Records token usage into *tracker* when provided.
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
            tool_choice="none",
            response_format={"type": "json_object"},
            temperature=0,
        )
        choice = response.choices[0]

        if tracker and response.usage:
            call_type = "tool_followup" if len(messages) > 2 else "main"
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
    if tracker and final.usage:
        tracker.record(
            judge_name=judge_name,
            judge_role=judge_role,
            call_type="force_final",
            prompt_tokens=final.usage.prompt_tokens,
            completion_tokens=final.usage.completion_tokens,
        )
    return final.choices[0].message.content


def _parse_assignment(
    raw: str,
    authors: list[str],
    candidates: list[dict],
) -> dict[str, list[PersonaScore]]:
    """
    Parse direct assignment JSON output:
      {"assignment": {"<author_digest>": "<PERSONA_NAME>", ...}}

    Each author gets exactly one PersonaScore with a neutral score (3) — fidelity
    is no longer requested during identification; it is evaluated separately via
    run_individual_fidelity_with_tools().
    Validates that no two authors share the same persona (bijection). If violated,
    later duplicate assignments are dropped and logged.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("assignment parse: invalid JSON, using empty assignment")
        data = {}

    assignment: dict = data.get("assignment", {})

    # Validate bijection
    seen_personas: set[str] = set()
    clean_assignment: dict[str, str] = {}
    for author, persona in assignment.items():
        if persona in seen_personas:
            log.warning("assignment parse: duplicate persona '%s' for author %s — dropped", persona, author[:12])
        else:
            seen_personas.add(persona)
            clean_assignment[author] = persona

    fallback_persona = candidates[0]["persona_name"] if candidates else "unknown"
    result: dict[str, list[PersonaScore]] = {}

    unassigned_authors = [a for a in authors if a not in clean_assignment]
    if unassigned_authors:
        log.warning(
            "assignment parse: %d/%d authors unassigned by LLM — using fallback '%s'",
            len(unassigned_authors), len(authors), fallback_persona,
        )

    for author in authors:
        assigned_persona = clean_assignment.get(author, fallback_persona)
        result[author] = [PersonaScore(persona_name=assigned_persona, score=3)]

    log.info(
        "assignment parse: %d authors → %s",
        len(result),
        {a[:8] + "...": ps[0].persona_name for a, ps in result.items()},
    )
    return result


def _openai_simple_call(
    system: str,
    user: str,
    model: str,
    judge_name: str = "unknown",
    judge_role: str = "general",
    tracker: "TokenTracker | None" = None,
) -> str:
    """Single OpenAI completion without tool use. Used for individual fidelity evaluation."""
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    if tracker and response.usage:
        tracker.record(
            judge_name=judge_name,
            judge_role=judge_role,
            call_type="individual_fidelity",
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )
    return response.choices[0].message.content or ""


def run_individual_fidelity_with_tools(
    role: str,
    messages_by_digest: dict[str, list[str]],
    true_mapping: dict[str, str],
    all_profiles: dict[str, dict],
    model: str = OPENAI_MODEL,
    judge_name: str = "unknown",
    tracker: "TokenTracker | None" = None,
) -> dict[str, int]:
    """
    Evaluate individual fidelity given the true author–persona mapping.

    For each (author_digest, persona_name) pair in true_mapping, the judge
    rates how faithfully that author portrays the persona using their role lens.

    Returns {persona_name: fidelity_score} for all pairs in true_mapping.
    Requires LLM_BACKEND=openai.
    """
    if LLM_BACKEND != "openai":
        raise RuntimeError(
            "run_individual_fidelity_with_tools requires LLM_BACKEND=openai. "
            f"Current backend: {LLM_BACKEND!r}."
        )

    template = _FIDELITY_TEMPLATES.get(role, "individual_fidelity_general.j2")

    pair_blocks: list[str] = []
    for i, (digest, persona_name) in enumerate(true_mapping.items(), start=1):
        msgs = messages_by_digest.get(digest, [])
        profile = all_profiles.get(persona_name)
        profile_text = format_profile(profile) if profile else "(profile not found)"
        msg_lines = "\n".join(f"- {m}" for m in msgs) if msgs else "(no messages)"
        pair_blocks.append(
            f"--- Pair {i} ---\n"
            f"Author: {digest}\n"
            f"Messages:\n{msg_lines}\n\n"
            f"Persona: {persona_name}\n"
            f"{profile_text}"
        )

    pairs_block = "\n\n".join(pair_blocks)
    system, user = render_prompt(
        template,
        n_pairs=len(true_mapping),
        pairs_block=pairs_block,
    )

    raw = _openai_simple_call(
        system,
        user,
        model,
        judge_name=judge_name,
        judge_role=role,
        tracker=tracker,
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("individual fidelity parse: invalid JSON for judge %s", judge_name)
        data = {}

    raw_scores: dict = data.get("individual_fidelity", {})
    result: dict[str, int] = {}
    for pname in true_mapping.values():
        score = raw_scores.get(pname)
        if isinstance(score, int):
            result[pname] = max(1, min(5, score))
        else:
            log.warning("individual fidelity: missing score for '%s' in judge %s, defaulting to 1", pname, judge_name)
            result[pname] = 1

    log.info(
        "individual fidelity judge %s [%s]: %s",
        judge_name, role,
        {p: s for p, s in result.items()},
    )
    return result


def run_persona_identification_with_tools(
    focus: str,
    chat: dict,
    candidates: list[dict],
    model: str = OPENAI_MODEL,
    role: str = "general",
    judge_name: str = "unknown",
    tracker: "TokenTracker | None" = None,
    gini_data: dict | None = None,
) -> tuple[PersonaIdentificationResult, int]:
    """
    Identify personas using a single RAG-assisted LLM call per judge.

    candidates  — pre-filtered profiles from retrieve_candidates().
    focus       — the judge's lens description (used for logging/fallback).
    role        — judge role: "style", "ideology", "general", or "behavioral".
                  Selects the role-specific batch template.
    judge_name  — identifier recorded in the token tracker (e.g. "style_3").
    tracker     — optional TokenTracker; records all API call token counts.

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

    gini_value = gini_data.get("gini") if gini_data else None
    gini_within_range = gini_data.get("within_reference_range") if gini_data else None
    gini_z = gini_data.get("z_vs_reference") if gini_data else None

    system, user = render_prompt(
        template,
        n_candidates=len(candidates),
        candidates_block=candidates_block,
        messages_block=messages_block,
        author_list=author_list,
        persona_names=persona_names,
        gini_value=gini_value,
        gini_within_range=gini_within_range,
        gini_z=gini_z,
    )

    raw = _openai_tool_loop(
        system,
        user,
        model,
        judge_name=judge_name,
        judge_role=role,
        tracker=tracker,
    )

    try:
        raw_data = json.loads(raw)
    except json.JSONDecodeError:
        raw_data = {}

    gf_score = raw_data.get("group_fidelity_score")
    if not isinstance(gf_score, int) or not (1 <= gf_score <= 5):
        log.warning("judge %s: missing or invalid group_fidelity_score, defaulting to 3", judge_name)
        gf_score = 3

    author_persona_scores = _parse_assignment(raw, authors, candidates)

    matches = [
        AuthorMatch(author=a, scores=author_persona_scores[a])
        for a in authors
    ]
    return PersonaIdentificationResult(matches=matches), gf_score

"""
RAG-assisted judge that combines pre-filtering with LLM tool use.

Flow:
  1. retrieve_candidates() narrows the database to top-K profiles (per judge role).
  2. The judge LLM receives those candidates as starting context.
  3. During reasoning the judge can call search_persona_profiles() to query
     ChromaDB on demand for deeper investigation.
  4. Final output: PersonaIdentificationResult (same interface as base judges).

Only works with LLM_BACKEND=openai. Falls back to standard run_persona_identification
when Ollama is configured (Ollama tool-calling support varies by model).
"""

import json
import logging
import os
from collections import defaultdict

from dotenv import load_dotenv
from openai import OpenAI

from ..agents.agent_config import (
    LLM_BACKEND,
    OPENAI_MODEL,
    format_messages,
    format_profile,
    run_persona_identification,
    _parse_json_scores,
)
from ..agents.judges.base_judge import AuthorMatch, PersonaIdentificationResult, PersonaScore
from ..agents.judges.templates import render_prompt
from .tool import SEARCH_TOOL, execute as execute_rag_tool

load_dotenv()
log = logging.getLogger(__name__)

# Maximum tool calls allowed per LLM turn before forcing a final answer.
_MAX_TOOL_CALLS = 3


def _openai_tool_loop(system: str, user: str, model: str) -> str:
    """
    Run an OpenAI chat completion that can invoke search_persona_profiles.
    Returns the final text content once the model stops calling tools.
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
            temperature=0,
        )
        choice = response.choices[0]

        if choice.finish_reason != "tool_calls":
            return choice.message.content

        # Execute every tool call the model requested
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

    # Max tool calls reached — force a final answer without tools
    messages.append({"role": "user", "content": "Provide your final JSON answer now."})
    final = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
    )
    return final.choices[0].message.content


def run_persona_identification_with_tools(
    focus: str,
    chat: dict,
    candidates: list[dict],
    model: str = OPENAI_MODEL,
) -> PersonaIdentificationResult:
    """
    Identify personas using RAG-assisted tool-use judges.

    candidates  — pre-filtered profiles from retrieve_candidates().
    focus       — the judge's lens, e.g. "vocabulary, sentence structure, tone".

    Falls back to standard run_persona_identification when LLM_BACKEND=ollama.
    """
    if LLM_BACKEND != "openai":
        log.warning(
            "run_persona_identification_with_tools: tool use requires openai backend. "
            "Falling back to standard persona identification."
        )
        return run_persona_identification("persona_id_general.j2", chat, candidates, model)

    messages_block, authors = format_messages(chat)
    if not authors:
        raise ValueError(
            "run_persona_identification_with_tools: chat has no messages with authors."
        )

    author_list = ", ".join(authors)
    candidates_block = "\n\n".join(
        f"--- {p['persona_name']} ---\n{format_profile(p)}"
        for p in candidates
    )

    author_persona_scores: dict[str, list[PersonaScore]] = {a: [] for a in authors}

    for persona in candidates:
        name = persona["persona_name"]
        system, user = render_prompt(
            "persona_id_rag.j2",
            focus=focus,
            persona_name=name,
            n_candidates=len(candidates),
            candidates_block=candidates_block,
            messages_block=messages_block,
            author_list=author_list,
        )
        raw = _openai_tool_loop(system, user, model)
        author_scores = _parse_json_scores(raw, authors)
        for author, score in author_scores.items():
            author_persona_scores[author].append(PersonaScore(persona_name=name, score=score))

    matches = [
        AuthorMatch(author=a, scores=author_persona_scores[a])
        for a in authors
    ]
    return PersonaIdentificationResult(matches=matches)

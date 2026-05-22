import json
import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

_CHROMA_DIR = Path(__file__).parents[3] / "data" / "chroma"
_COLLECTION = "persona_profiles"
_EMBEDDING_MODEL = "text-embedding-3-small"

# OpenAI-compatible tool schema passed to the judge LLM.
SEARCH_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "search_persona_profiles",
        "description": (
            "Search the full persona database for characters matching a behavioral "
            "or stylistic pattern. Use this when a message pattern does not clearly "
            "match any pre-filtered candidate, or when you need to verify a specific "
            "trait before scoring."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "A description of the pattern to look up. Write it as a "
                        "behavioral or stylistic observation, e.g. "
                        "'inverted syntax slow deliberate formal mentor figure' or "
                        "'self-deprecating slang fast casual deflects with humor'."
                    ),
                },
                "field": {
                    "type": "string",
                    "enum": ["style", "voice", "worldview", "behavior", "quote"],
                    "description": (
                        "Optional. Restrict the search to one profile dimension. "
                        "Omit to search all dimensions."
                    ),
                },
            },
            "required": ["query"],
        },
    },
}


def execute(query: str, field: str | None = None, n_results: int = 5) -> str:
    """
    Run a semantic search against ChromaDB and return formatted results.
    Called by the tool-call loop whenever the judge invokes search_persona_profiles.
    """
    client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    ef = OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"],
        model_name=_EMBEDDING_MODEL,
    )
    collection = client.get_or_create_collection(_COLLECTION, embedding_function=ef)

    total = collection.count()
    if total == 0:
        return "Index is empty — run build_index.py first."

    where = {"field": field} if field else None
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, total),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    lines: list[str] = []
    seen: set[str] = set()
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        name = meta["persona_name"]
        if name in seen:
            continue
        seen.add(name)
        score = round(1.0 / (1.0 + dist), 3)
        lines.append(f"[{name} | similarity {score}]\n{doc}")

    return "\n\n".join(lines) if lines else "No results found for that query."

import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from .builder import build_chunks

_CHROMA_DIR = Path(__file__).parents[3] / "data" / "chroma"
_COLLECTION = "persona_profiles"
_EMBEDDING_MODEL = "text-embedding-3-small"


def _get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    ef = OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"],
        model_name=_EMBEDDING_MODEL,
    )
    return client.get_or_create_collection(_COLLECTION, embedding_function=ef)


def index_profile(profile: dict) -> None:
    """Upsert all chunks for one persona. Safe to call multiple times (idempotent)."""
    chunks = build_chunks(profile)
    if not chunks:
        return
    collection = _get_collection()
    collection.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )


def remove_profile(persona_name: str) -> None:
    """Delete all chunks for a persona. Call this on soft-delete of an agent."""
    collection = _get_collection()
    results = collection.get(where={"persona_name": persona_name})
    if results["ids"]:
        collection.delete(ids=results["ids"])


def index_all(profiles: list[dict]) -> None:
    """Bulk-index a list of profiles. Run once to build the initial index."""
    for profile in profiles:
        index_profile(profile)

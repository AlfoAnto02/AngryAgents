"""
Shared ChromaDB collection singleton — thread-safe.

Both retriever.py and tool.py import _get_collection() from here so that only
one PersistentClient is ever opened per process, avoiding SQLite lock conflicts
when multiple threads call ChromaDB concurrently.
"""

import os
import threading
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

_CHROMA_DIR = Path(__file__).parents[3] / "data" / "chroma"
_COLLECTION = "persona_profiles"
_EMBEDDING_MODEL = "text-embedding-3-small"

_lock = threading.Lock()
_collection: chromadb.Collection | None = None


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is not None:
        return _collection
    with _lock:
        if _collection is None:
            client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
            ef = OpenAIEmbeddingFunction(
                api_key=os.environ["OPENAI_API_KEY"],
                model_name=_EMBEDDING_MODEL,
            )
            _collection = client.get_or_create_collection(_COLLECTION, embedding_function=ef)
    return _collection

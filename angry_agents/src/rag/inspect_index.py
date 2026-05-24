"""
Inspect the ChromaDB index contents.

Usage:
    python -m angry_agents.src.rag.inspect_index
    python -m angry_agents.src.rag.inspect_index --persona JIMMY
    python -m angry_agents.src.rag.inspect_index --persona JIMMY --vectors
"""

import argparse

from dotenv import load_dotenv

load_dotenv()

from ._chroma import _get_collection


def inspect_all(show_vectors: bool = False) -> None:
    collection = _get_collection()
    total = collection.count()
    print(f"\nTotal chunks in index: {total}\n")

    include = ["documents", "metadatas"]
    if show_vectors:
        include.append("embeddings")

    results = collection.get(include=include)

    # Group by persona
    by_persona: dict[str, list[dict]] = {}
    for i, meta in enumerate(results["metadatas"]):
        name = meta["persona_name"]
        if name not in by_persona:
            by_persona[name] = []
        entry = {
            "id": results["ids"][i],
            "field": meta["field"],
            "text": results["documents"][i],
        }
        if show_vectors:
            vec = results["embeddings"][i]
            entry["vector_preview"] = f"[{vec[0]:.4f}, {vec[1]:.4f}, {vec[2]:.4f}, ... {vec[-1]:.4f}]  (dim={len(vec)})"
        by_persona[name].append(entry)

    for persona, chunks in sorted(by_persona.items()):
        print(f"{'─' * 60}")
        print(f"  {persona}  ({len(chunks)} chunks)")
        print(f"{'─' * 60}")
        for c in chunks:
            print(f"  [{c['field']}]  id: {c['id']}")
            print(f"    {c['text'][:120]}{'...' if len(c['text']) > 120 else ''}")
            if "vector_preview" in c:
                print(f"    vector: {c['vector_preview']}")
        print()


def inspect_persona(persona_name: str, show_vectors: bool = False) -> None:
    collection = _get_collection()

    include = ["documents", "metadatas"]
    if show_vectors:
        include.append("embeddings")

    results = collection.get(
        where={"persona_name": persona_name},
        include=include,
    )

    if not results["ids"]:
        print(f"\nNo chunks found for persona: {persona_name}")
        return

    print(f"\n{persona_name}  —  {len(results['ids'])} chunks\n")
    for i, chunk_id in enumerate(results["ids"]):
        meta = results["metadatas"][i]
        text = results["documents"][i]
        print(f"  [{meta['field']}]  {chunk_id}")
        print(f"  {text}")
        if show_vectors:
            vec = results["embeddings"][i]
            print(f"  vector (dim={len(vec)}): [{vec[0]:.4f}, {vec[1]:.4f}, {vec[2]:.4f}, ...]")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect ChromaDB persona index.")
    parser.add_argument("--persona", default=None, help="Show chunks for a specific persona only")
    parser.add_argument("--vectors", action="store_true", help="Show vector preview (first 3 + last dim)")
    args = parser.parse_args()

    if args.persona:
        inspect_persona(args.persona, show_vectors=args.vectors)
    else:
        inspect_all(show_vectors=args.vectors)


if __name__ == "__main__":
    main()

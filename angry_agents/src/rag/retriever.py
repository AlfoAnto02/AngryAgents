from ._chroma import _get_collection

# How many of the author's most recent messages to use as the query.
# More messages = richer query, but beyond ~5 the signal flattens.
_QUERY_MESSAGES = 5

_DEFAULT_TOP_K = 20


def retrieve_candidates(
    messages_by_digest: dict[str, list[str]],
    profiles_by_name: dict[str, dict],
    top_k: int = _DEFAULT_TOP_K,
    field_filter: list[str] | None = None,
) -> list[dict]:
    """
    Return the top_k most relevant persona profiles for a given set of authors.

    For each anonymous digest, the author's messages are used as a query against
    ChromaDB. Scores are merged across all authors (best score per persona wins),
    then the top_k distinct personas are returned as full profile dicts.

    messages_by_digest: {digest: [msg1, msg2, ...]}  — from format_messages()
    profiles_by_name:   {persona_name: profile_dict} — full profiles for lookup
    field_filter:       restrict search to specific chunk types, e.g. ["style", "voice"].
                        None searches all chunk types (default).
    """
    collection = _get_collection()
    total = collection.count()
    if total == 0:
        return list(profiles_by_name.values())[:top_k]

    n_results = min(top_k * 3, total)
    candidate_scores: dict[str, float] = {}

    # Build the ChromaDB where clause for field filtering.
    # Single field → {"field": value}, multiple → {"$or": [{"field": v}, ...]}
    where: dict | None = None
    if field_filter:
        if len(field_filter) == 1:
            where = {"field": field_filter[0]}
        else:
            where = {"$or": [{"field": f} for f in field_filter]}

    for messages in messages_by_digest.values():
        query_text = " ".join(messages[-_QUERY_MESSAGES:])
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
            include=["metadatas", "distances"],
        )
        for metadata, distance in zip(results["metadatas"][0], results["distances"][0]):
            name = metadata["persona_name"]
            # ChromaDB returns L2 distance: lower = more similar
            score = 1.0 / (1.0 + distance)
            if score > candidate_scores.get(name, 0.0):
                candidate_scores[name] = score

    ranked = sorted(candidate_scores, key=candidate_scores.__getitem__, reverse=True)
    top_names = ranked[:top_k]

    return [profiles_by_name[name] for name in top_names if name in profiles_by_name]

from ._chroma import _get_collection

# How many of the author's most recent messages to use as the query.
# More messages = richer query, but beyond ~5 the signal flattens.
_QUERY_MESSAGES = 5

_DEFAULT_TOP_K = 20

# Per-role chunk weights for aggregation.
# Fields not listed default to 1.0.
# Boosts the chunks most relevant to each judge's lens so the shortlist
# reflects the role's perspective rather than a flat average.
_ROLE_FIELD_WEIGHTS: dict[str, dict[str, float]] = {
    "style":      {"style": 3.0, "voice": 2.0, "vocabulary": 3.0, "quote": 1.5, "do_not_say": 1.5, "worldview": 0.5, "behavior": 0.5},
    "ideology":   {"worldview": 3.0, "quote": 1.5, "do_not_say": 1.5, "behavior": 1.0, "style": 0.5, "voice": 0.5, "vocabulary": 0.5},
    "behavioral": {"behavior": 3.0, "quote": 1.5, "do_not_say": 1.5, "worldview": 1.0, "style": 0.5, "voice": 0.5, "vocabulary": 0.5},
    "general":    {},  # empty → all fields weight 1.0
}


def retrieve_candidates(
    messages_by_digest: dict[str, list[str]],
    profiles_by_name: dict[str, dict],
    top_k: int = _DEFAULT_TOP_K,
    field_filter: list[str] | None = None,
    forced_names: list[str] | None = None,
    role: str = "general",
) -> list[dict]:
    """
    Return the top_k most relevant persona profiles for a given set of authors.

    For each anonymous digest, the author's messages are used as a query against
    ChromaDB. Scores are merged across all authors (best score per persona wins),
    then the top_k distinct personas are returned as full profile dicts.

    forced_names: persona names that must always appear in the result regardless
                  of semantic rank (e.g. the actual chat participants). They are
                  appended after the top_k semantic hits if not already present.

    messages_by_digest: {digest: [msg1, msg2, ...]}  — from format_messages()
    profiles_by_name:   {persona_name: profile_dict} — full profiles for lookup
    field_filter:       restrict search to specific chunk types, e.g. ["style", "voice"].
                        None searches all chunk types (default).
    role:               judge role used to select per-field score weights.
                        One of "style", "ideology", "behavioral", "general".
    """
    collection = _get_collection()
    total = collection.count()
    if total == 0:
        return list(profiles_by_name.values())[:top_k]

    n_results = min(top_k * 3, total)
    field_weights = _ROLE_FIELD_WEIGHTS.get(role, {})

    # Accumulate weighted chunk scores per persona.
    # Mean over weights prevents a single generic chunk from dominating
    # (attractor problem) while role-specific weights ensure each judge's
    # shortlist reflects its own lens.
    weighted_sum: dict[str, float] = {}
    weight_total: dict[str, float] = {}

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
            field = metadata.get("field", "")
            score = 1.0 / (1.0 + distance)
            w = field_weights.get(field, 1.0)
            weighted_sum[name] = weighted_sum.get(name, 0.0) + score * w
            weight_total[name] = weight_total.get(name, 0.0) + w

    candidate_scores = {
        name: weighted_sum[name] / weight_total[name] for name in weighted_sum
    }

    ranked = sorted(candidate_scores, key=candidate_scores.__getitem__, reverse=True)
    top_names = list(ranked[:top_k])

    # Always include the actual chat participants even if RAG ranked them below top_k
    if forced_names:
        seen = set(top_names)
        for name in forced_names:
            if name not in seen and name in profiles_by_name:
                top_names.append(name)
                seen.add(name)

    return [profiles_by_name[name] for name in top_names if name in profiles_by_name]

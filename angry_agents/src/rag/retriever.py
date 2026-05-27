import numpy as np
from numpy.typing import NDArray

from ._chroma import _get_collection

# How many of the author's most recent messages to use as the query.
# More messages = richer query, but beyond ~5 the signal flattens.
_QUERY_MESSAGES = 5

_DEFAULT_TOP_K = 20

# MMR lambda: 1.0 = pure relevance (no diversity), 0.0 = pure diversity.
# 0.7 keeps the top candidate by relevance but diversifies the rest,
# preventing one "attractor" persona from filling multiple slots.
_MMR_LAMBDA = 0.7

# Per-role chunk weights for aggregation.
# Fields not listed default to 1.0.
# Boosts the chunks most relevant to each judge's lens so the shortlist
# reflects the role's perspective rather than a flat average.
#
# New fields added alongside the builder refactor:
#   emotional_tells   — per-emotion register shifts (style + behavioral signal)
#   social_positioning — desired vs actual role gap (ideology + behavioral signal)
#   knowledge         — expert/surface/ignorant domains (ideology signal)
_ROLE_FIELD_WEIGHTS: dict[str, dict[str, float]] = {
    "style": {
        "style": 2.5, "structure": 3.5, "voice": 2.0, "vocabulary": 3.0,
        "emotional_tells": 1.5,
        "quote": 1.5, "do_not_say": 1.5,
        "worldview": 0.5, "behavior": 0.5, "self_image": 0.3, "escalation": 0.5,
        "social_positioning": 0.3, "knowledge": 0.3,
    },
    "ideology": {
        "worldview": 3.0, "self_image": 3.0,
        "social_positioning": 2.5, "knowledge": 2.5,
        "quote": 1.5, "do_not_say": 1.5,
        "behavior": 1.0, "escalation": 0.8,
        "emotional_tells": 0.5,
        "style": 0.5, "structure": 0.5, "voice": 0.5, "vocabulary": 0.5,
    },
    "behavioral": {
        "behavior": 3.0, "escalation": 3.0,
        "emotional_tells": 2.5, "social_positioning": 1.5,
        "quote": 1.5, "do_not_say": 1.5,
        "worldview": 1.0, "self_image": 1.0, "knowledge": 0.5,
        "style": 0.5, "structure": 0.5, "voice": 0.5, "vocabulary": 0.5,
    },
    "general": {},  # empty → all fields weight 1.0
}


def _cosine_sim(a: NDArray, b: NDArray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _mmr_select(
    centroids: dict[str, NDArray],
    scores: dict[str, float],
    top_k: int,
    lambda_: float,
) -> list[str]:
    """
    Maximal Marginal Relevance selection over personas.

    Each iteration picks the candidate that maximises:
        lambda_ * relevance_score  -  (1 - lambda_) * max_similarity_to_selected

    This prevents a single attractor persona from dominating the shortlist by
    penalising candidates that are close in embedding space to already-selected ones.
    """
    selected: list[str] = []
    remaining = list(centroids.keys())

    while remaining and len(selected) < top_k:
        if not selected:
            best = max(remaining, key=lambda n: scores.get(n, 0.0))
        else:
            best = max(
                remaining,
                key=lambda n: (
                    lambda_ * scores.get(n, 0.0)
                    - (1.0 - lambda_) * max(
                        _cosine_sim(centroids[n], centroids[s]) for s in selected
                    )
                ),
            )
        selected.append(best)
        remaining.remove(best)

    return selected


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
    then MMR re-ranking selects the top_k with diversity to avoid attractor dominance.

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

    weighted_sum: dict[str, float] = {}
    weight_total: dict[str, float] = {}
    chunk_embeddings: dict[str, list[NDArray]] = {}  # persona → chunk vectors

    # Build the ChromaDB where clause for field filtering.
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
            include=["metadatas", "distances", "embeddings"],
        )
        for metadata, distance, embedding in zip(
            results["metadatas"][0],
            results["distances"][0],
            results["embeddings"][0],
        ):
            name = metadata["persona_name"]
            field = metadata.get("field", "")
            score = 1.0 / (1.0 + distance)
            w = field_weights.get(field, 1.0)
            weighted_sum[name] = weighted_sum.get(name, 0.0) + score * w
            weight_total[name] = weight_total.get(name, 0.0) + w
            chunk_embeddings.setdefault(name, []).append(np.array(embedding))

    candidate_scores = {
        name: weighted_sum[name] / weight_total[name] for name in weighted_sum
    }

    # Compute per-persona centroid embedding (mean of all matched chunks).
    centroids: dict[str, NDArray] = {
        name: np.mean(vecs, axis=0)
        for name, vecs in chunk_embeddings.items()
    }

    # MMR re-ranking: balance relevance vs inter-candidate diversity.
    top_names = _mmr_select(centroids, candidate_scores, top_k, _MMR_LAMBDA)

    # Always include the actual chat participants even if MMR ranked them below top_k.
    if forced_names:
        seen = set(top_names)
        for name in forced_names:
            if name not in seen and name in profiles_by_name:
                top_names.append(name)
                seen.add(name)

    return [profiles_by_name[name] for name in top_names if name in profiles_by_name]

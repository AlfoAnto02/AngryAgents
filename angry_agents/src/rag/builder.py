import json


def _vocab_to_natural(name: str, vf: dict) -> str:
    """
    Convert a vocabulary_fingerprint dict into a natural-language sentence
    that the embedding model can meaningfully encode.

    A JSON list like {"favored_words": ["cunt", "mate"]} produces an
    embedding close to any list of words. Rendering the same data as prose
    — 'Billy Butcher habitually says "cunt", "mate"' — anchors the vector
    to actual speech, making it far more discriminating at query time.
    """
    parts: list[str] = []

    favored = vf.get("favored_words") or []
    if favored:
        quoted = ", ".join(f'"{w}"' for w in favored)
        parts.append(f'{name} habitually uses the words {quoted}.')

    avoided = vf.get("avoided_words") or []
    if avoided:
        quoted = ", ".join(f'"{w}"' for w in avoided)
        parts.append(f'{name} never says {quoted}.')

    jargon = vf.get("domain_jargon")
    if jargon and jargon not in ("none", "None", "", None):
        parts.append(f'Domain jargon: {jargon}.')

    markers = vf.get("vocabulary_markers") or []
    if markers:
        parts.append("Characteristic markers: " + "; ".join(str(m) for m in markers) + ".")

    fillers = vf.get("filler_patterns")
    if fillers and fillers not in ("none", "None", "", None):
        parts.append(f'Filler patterns: {fillers}.')

    return " ".join(parts) if parts else ""


def build_chunks(profile: dict) -> list[dict]:
    """
    Split a persona profile into semantic chunks for embedding.
    Returns list of {"id": str, "text": str, "metadata": dict}.
    Each chunk covers one dimension so retrieval is field-aware.
    """
    name = profile["persona_name"]
    source_type = profile.get("source_type", "unknown")
    chunks: list[dict] = []

    def _add(field: str, text: str, idx: int = 0) -> None:
        chunks.append({
            "id": f"{name}__{field}__{idx}",
            "text": text,
            "metadata": {"persona_name": name, "source_type": source_type, "field": field},
        })

    def _dump(v: object) -> str:
        return json.dumps(v) if isinstance(v, (dict, list)) else str(v)

    # Style — primary signature, most useful for style/general judges
    style_parts: list[str] = []
    if cs := profile.get("core_style"):
        style_parts.append(f"core style: {_dump(cs)}")
    if ss := profile.get("speech_signature"):
        style_parts.append(f"speech signature: {_dump(ss)}")
    if rst := profile.get("register_shift_triggers"):
        style_parts.append(f"register shifts when: {_dump(rst)}")
    if style_parts:
        _add("style", f"{name} — " + " | ".join(style_parts))

    # Voice — humor + vocabulary as natural language (Fix A + Fix D)
    voice_parts: list[str] = []
    if h := profile.get("humor"):
        voice_parts.append(f"humor: {_dump(h)}")
    if vf := profile.get("vocabulary_fingerprint"):
        natural = _vocab_to_natural(name, vf)
        if natural:
            voice_parts.append(natural)
        else:
            voice_parts.append(f"vocabulary: {_dump(vf)}")
    if voice_parts:
        _add("voice", f"{name} — " + " | ".join(voice_parts))

    # Vocabulary in context — dedicated chunk for lexical fingerprint (Fix D)
    # Separate from voice so style judges can query it independently.
    if vf := profile.get("vocabulary_fingerprint"):
        natural = _vocab_to_natural(name, vf)
        if natural:
            _add("vocabulary", natural)

    # Worldview — ideology/behavioral judges
    world_parts: list[str] = []
    if wv := profile.get("worldview"):
        world_parts.append(f"worldview: {_dump(wv)}")
    if sivr := profile.get("self_image_vs_reality"):
        world_parts.append(f"self image vs reality: {_dump(sivr)}")
    if et := profile.get("emotional_tells"):
        world_parts.append(f"emotional tells: {_dump(et)}")
    if kd := profile.get("knowledge_domains"):
        world_parts.append(f"knowledge domains: {_dump(kd)}")
    if rm := profile.get("relationship_matrix"):
        world_parts.append(f"relationship matrix: {_dump(rm)}")
    if world_parts:
        _add("worldview", f"{name} — " + " | ".join(world_parts))

    # Behavior — behavioral judge
    # response_patterns (real_world) is the equivalent of situational_behavior (fiction)
    beh_parts: list[str] = []
    if rp := profile.get("response_patterns"):
        beh_parts.append(f"response patterns: {_dump(rp)}")
    if sb := profile.get("situational_behavior"):
        beh_parts.append(f"situational behavior: {_dump(sb)}")
    if ep := profile.get("escalation_pattern"):
        beh_parts.append(f"escalation: {ep}")
    if cg := profile.get("conversation_goals"):
        beh_parts.append(f"conversation goals: {_dump(cg)}")
    if sp := profile.get("social_positioning"):
        beh_parts.append(f"social positioning: {_dump(sp)}")
    if beh_parts:
        _add("behavior", f"{name} — " + " | ".join(beh_parts))

    # Quotes — most discriminating; one chunk per quote
    for i, q in enumerate(profile.get("annotated_quotes", [])):
        text = (
            f'{name} says: "{q["quote"]}" (context: {q.get("context", "")})'
            if isinstance(q, dict)
            else f'{name} says: "{q}"'
        )
        _add("quote", text, i)

    # Do-not-say — negative examples; highly discriminating for persona identity
    for i, d in enumerate(profile.get("do_not_say", [])):
        text = (
            f'{name} would NEVER say: "{d["line"]}" (contradicts: {d.get("contradicts", "")})'
            if isinstance(d, dict)
            else f'{name} would NEVER say: "{d}"'
        )
        _add("do_not_say", text, i)

    return chunks
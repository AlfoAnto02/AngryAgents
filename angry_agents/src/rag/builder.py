import json


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

    # Voice — surface-level signals
    voice_parts: list[str] = []
    if h := profile.get("humor"):
        voice_parts.append(f"humor: {_dump(h)}")
    if vf := profile.get("vocabulary_fingerprint"):
        voice_parts.append(f"vocabulary: {_dump(vf)}")
    if voice_parts:
        _add("voice", f"{name} — " + " | ".join(voice_parts))

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
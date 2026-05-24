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
    if rp := profile.get("response_patterns"):
        style_parts.append(f"response patterns: {_dump(rp)}")
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
    if vm := profile.get("vocabulary_markers"):
        voice_parts.append(f"vocabulary markers: {', '.join(vm)}")
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
    if ip := profile.get("ideological_positions"):
        world_parts.append(f"ideology: {_dump(ip)}")
    if triggers := profile.get("emotional_triggers"):
        world_parts.append(f"emotional triggers: {_dump(triggers)}")
    if kd := profile.get("knowledge_domains"):
        world_parts.append(f"knowledge domains: {_dump(kd)}")
    if world_parts:
        _add("worldview", f"{name} — " + " | ".join(world_parts))

    # Behavior — behavioral judge
    beh_parts: list[str] = []
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
    base = 0
    for i, q in enumerate(profile.get("annotated_quotes", [])):
        text = (
            f'{name} says: "{q["quote"]}" (context: {q.get("context", "")})'
            if isinstance(q, dict)
            else f'{name} says: "{q}"'
        )
        _add("quote", text, i)
        base = i + 1

    for i, q in enumerate(profile.get("exemplar_quotes", [])):
        _add("quote", f'{name} says: "{q}"', base + i)

    return chunks

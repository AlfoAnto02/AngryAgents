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

    # Style — register, rhythm, sentence shape (broad style signal)
    style_parts: list[str] = []
    if cs := profile.get("core_style"):
        style_parts.append(f"core style: {_dump(cs)}")
    if ss := profile.get("speech_signature"):
        # Include naming_behavior and armor_off_register but NOT structural_patterns
        # (those go in the dedicated structure chunk below for sharper retrieval)
        ss_summary = {k: v for k, v in ss.items() if k != "structural_patterns"}
        if ss_summary:
            style_parts.append(f"speech signature: {_dump(ss_summary)}")
    if rst := profile.get("register_shift_triggers"):
        style_parts.append(f"register shifts when: {_dump(rst)}")
    if style_parts:
        _add("style", f"{name} — " + " | ".join(style_parts))

    # Structure — dedicated chunk for structural_patterns + armor_off_register.
    # Most discriminating style feature: Yoda's OVS syntax, Rick's *burp*,
    # Gollum's self-dialogue, Sheldon's Bazinga. Kept separate so it is not
    # diluted by the broader style embedding.
    if ss := profile.get("speech_signature"):
        struct_parts: list[str] = []
        if sp := ss.get("structural_patterns"):
            struct_parts.append(f"structural patterns: {_dump(sp)}")
        if aor := ss.get("armor_off_register"):
            struct_parts.append(f"armor off register: {aor}")
        if struct_parts:
            _add("structure", f"{name} — " + " | ".join(struct_parts))

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

    # Worldview — ideology judges: values, beliefs, knowledge domains
    world_parts: list[str] = []
    if wv := profile.get("worldview"):
        world_parts.append(f"worldview: {_dump(wv)}")
    if kd := profile.get("knowledge_domains"):
        world_parts.append(f"knowledge domains: {_dump(kd)}")
    if world_parts:
        _add("worldview", f"{name} — " + " | ".join(world_parts))

    # Self-image — dedicated chunk for self_image_vs_reality.
    # The gap between a character's self-image and reality is highly discriminating
    # for ideology judges and unique per persona (e.g. "I did it for me" — Walter White).
    if sivr := profile.get("self_image_vs_reality"):
        self_img = sivr.get("self_image", "")
        reality = sivr.get("reality", "")
        gap = sivr.get("gap_behavior", "")
        parts = [f'{name} self-image: "{self_img}"']
        if reality:
            parts.append(f"reality: {reality}")
        if gap:
            parts.append(f"gap behavior: {gap}")
        _add("self_image", " | ".join(parts))

    # Behavior — behavioral judges: reactions, goals, social, emotional tells,
    # relationship dynamics. emotional_tells and relationship_matrix moved here from
    # worldview because they describe how the persona acts, not what they believe.
    beh_parts: list[str] = []
    if rp := profile.get("response_patterns"):
        beh_parts.append(f"response patterns: {_dump(rp)}")
    if sb := profile.get("situational_behavior"):
        beh_parts.append(f"situational behavior: {_dump(sb)}")
    if cg := profile.get("conversation_goals"):
        beh_parts.append(f"conversation goals: {_dump(cg)}")
    if sp := profile.get("social_positioning"):
        beh_parts.append(f"social positioning: {_dump(sp)}")
    if et := profile.get("emotional_tells"):
        beh_parts.append(f"emotional tells: {_dump(et)}")
    if rm := profile.get("relationship_matrix"):
        beh_parts.append(f"relationship matrix: {_dump(rm)}")
    if beh_parts:
        _add("behavior", f"{name} — " + " | ".join(beh_parts))

    # Escalation — dedicated chunk for escalation_pattern.
    # Single sentence, highly distinctive per persona, currently diluted in behavior blob.
    # e.g. Yoda: "calm advice -> urgent warnings -> firm directives"
    # vs Rick: "snark -> lecture -> planet-destroying threat delivered casually"
    if ep := profile.get("escalation_pattern"):
        _add("escalation", f"{name} escalation pattern: {ep}")

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
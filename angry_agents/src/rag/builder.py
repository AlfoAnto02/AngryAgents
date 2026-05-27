import json


# ── Natural-language converters ────────────────────────────────────────────────
# Each converter turns a profile dict-field into prose that embeds well.
# JSON dumps produce vectors close to any similar list of words; prose anchors
# the vector to semantics, making retrieval far more discriminating.


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


def _emotional_tells_to_natural(name: str, et: dict) -> str:
    """
    Convert an emotional_tells dict into natural-language prose.

    Fiction profiles use keys: when_guarded, when_genuinely_afraid,
    when_grieving_or_defeated, when_in_control.

    Real-world profiles use keys: when_challenged, when_enthusiastic,
    when_uncertain, when_in_control.

    Both are handled — any unknown key is rendered with its name converted
    to words so no signal is silently dropped.
    """
    if not et:
        return ""

    _LABEL = {
        "when_guarded":             "when guarded",
        "when_genuinely_afraid":    "when genuinely afraid",
        "when_grieving_or_defeated": "when grieving or defeated",
        "when_in_control":          "when in control",
        "when_challenged":          "when challenged",
        "when_enthusiastic":        "when enthusiastic",
        "when_uncertain":           "when uncertain",
    }

    parts = []
    for key, value in et.items():
        label = _LABEL.get(key, key.replace("_", " "))
        parts.append(f"{label}: {value}")

    return f"{name}'s emotional register — " + "; ".join(parts) + "." if parts else ""


def _knowledge_to_natural(name: str, kd: dict) -> str:
    """
    Convert a knowledge_domains dict into natural-language prose.

    Fiction profiles use 'ignorant' for blind spots.
    Real-world profiles use 'blind_spots'.
    Both are handled explicitly so the prose is always fluent.
    """
    if not kd:
        return ""

    clauses: list[str] = []

    expert = kd.get("expert") or []
    if expert:
        items = ", ".join(expert) if isinstance(expert, list) else str(expert)
        clauses.append(f"{name} is expert in {items}")

    surface = kd.get("surface") or []
    if surface:
        items = ", ".join(surface) if isinstance(surface, list) else str(surface)
        clauses.append(f"has surface knowledge of {items}")

    # Fiction uses 'ignorant'; real-world uses 'blind_spots'
    gaps = kd.get("blind_spots") or kd.get("ignorant") or []
    if gaps:
        items = ", ".join(gaps) if isinstance(gaps, list) else str(gaps)
        label = "has blind spots in" if kd.get("blind_spots") else "is ignorant of"
        clauses.append(f"{label} {items}")

    return ". ".join(clauses) + "." if clauses else ""


def _social_positioning_to_natural(name: str, sp: dict) -> str:
    """
    Convert a social_positioning dict into natural-language prose.

    Encodes the gap between a persona's desired social role and how they are
    actually perceived — a core ideological and behavioral signal.
    """
    if not sp:
        return ""

    parts: list[str] = []

    desired = sp.get("desired_position", "")
    if desired:
        parts.append(f'{name} wants to be seen as: "{desired}"')

    actual = sp.get("actual_dynamic", "")
    if actual:
        parts.append(f'but is actually perceived as: "{actual}"')

    contradiction = sp.get("contradiction", "")
    if contradiction:
        parts.append(f"The gap: {contradiction}")

    return " | ".join(parts) + "." if parts else ""


# ── Chunk builder ──────────────────────────────────────────────────────────────


def build_chunks(profile: dict) -> list[dict]:
    """
    Split a persona profile into semantic chunks for embedding.
    Returns list of {"id": str, "text": str, "metadata": dict}.

    Each chunk covers one dimension so retrieval is field-aware and
    role-specific field weights in retriever.py can boost the most relevant
    dimensions per judge type (style / ideology / behavioral / general).

    Chunk field inventory
    ─────────────────────
    style          register, rhythm, sentence shape, speech signature summary
    structure      structural_patterns + off-guard register (armor_off / candor)
    voice          humor + vocabulary prose (broad style signal)
    vocabulary     lexical fingerprint prose only (sharper style signal)
    worldview      values and beliefs (ideology judge)
    self_image     self-image vs reality gap (ideology judge)
    knowledge      expert/surface/ignorant knowledge domains (ideology judge)
    behavior       situational reactions, conversation goals, relationship matrix
    emotional_tells emotion-keyed register shifts (style + behavioral judges)
    social_positioning desired vs actual role and contradiction (ideology + behavioral)
    escalation     escalation arc, one sentence per persona (behavioral judge)
    quote          one chunk per annotated quote (all judges — highest signal)
    do_not_say     one chunk per negative example (all judges — negative fingerprint)
    """
    name = profile["persona_name"]
    source_type = profile.get("source_type", "unknown")
    source_title = profile.get("source_title", "")
    chunks: list[dict] = []

    def _add(field: str, text: str, idx: int = 0) -> None:
        metadata: dict = {
            "persona_name": name,
            "source_type": source_type,
            "field": field,
        }
        # Expose source_title for fiction profiles so downstream filters can
        # restrict searches to a specific show/film without a post-hoc decode.
        if source_title:
            metadata["source_title"] = source_title
        chunks.append({
            "id": f"{name}__{field}__{idx}",
            "text": text,
            "metadata": metadata,
        })

    def _dump(v: object) -> str:
        return json.dumps(v) if isinstance(v, (dict, list)) else str(v)

    # ── Style ──────────────────────────────────────────────────────────────────
    # Broad style signal: register, rhythm, sentence shape.
    # speech_signature summary WITHOUT structural_patterns (those go in structure).
    style_parts: list[str] = []
    if cs := profile.get("core_style"):
        style_parts.append(f"core style: {_dump(cs)}")
    if ss := profile.get("speech_signature"):
        ss_summary = {k: v for k, v in ss.items() if k != "structural_patterns"}
        if ss_summary:
            style_parts.append(f"speech signature: {_dump(ss_summary)}")
    if rst := profile.get("register_shift_triggers"):
        style_parts.append(f"register shifts when: {_dump(rst)}")
    if style_parts:
        _add("style", f"{name} — " + " | ".join(style_parts))

    # ── Structure ──────────────────────────────────────────────────────────────
    # Most discriminating style feature: Yoda's OVS syntax, Rick's *burp*,
    # Gollum's self-dialogue, Sheldon's Bazinga. Kept separate so it is not
    # diluted by the broader style embedding.
    #
    # Off-guard register name differs by source_type:
    #   fiction     → speech_signature.armor_off_register
    #   real_world  → speech_signature.candor_register
    # Both describe the same concept (register when the persona's guard is down).
    # Previously only armor_off_register was checked, silently dropping candor_register
    # for ALL real-world personas.
    if ss := profile.get("speech_signature"):
        struct_parts: list[str] = []
        if sp := ss.get("structural_patterns"):
            struct_parts.append(f"structural patterns: {_dump(sp)}")
        off_guard = ss.get("armor_off_register") or ss.get("candor_register")
        if off_guard:
            struct_parts.append(f"off-guard register: {off_guard}")
        if struct_parts:
            _add("structure", f"{name} — " + " | ".join(struct_parts))

    # ── Voice ──────────────────────────────────────────────────────────────────
    # Humor + vocabulary as natural language (Fix A + Fix D).
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

    # ── Vocabulary ─────────────────────────────────────────────────────────────
    # Dedicated chunk for lexical fingerprint so style judges can query it
    # independently of humor (sharper retrieval than the combined voice chunk).
    if vf := profile.get("vocabulary_fingerprint"):
        natural = _vocab_to_natural(name, vf)
        if natural:
            _add("vocabulary", natural)

    # ── Worldview ──────────────────────────────────────────────────────────────
    # Values and beliefs only. knowledge_domains moved to its own chunk so the
    # ideology judge can query it independently at higher weight.
    world_parts: list[str] = []
    if wv := profile.get("worldview"):
        world_parts.append(f"worldview: {_dump(wv)}")
    if world_parts:
        _add("worldview", f"{name} — " + " | ".join(world_parts))

    # ── Self-image ─────────────────────────────────────────────────────────────
    # The gap between self-image and reality is highly discriminating for ideology
    # judges — e.g. "I did it for me" (Walter White) vs "I am the damage" (Homelander).
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

    # ── Knowledge ──────────────────────────────────────────────────────────────
    # Dedicated chunk for expert / surface / ignorant knowledge domains.
    # Extracted from the worldview blob so ideology judges can weight it
    # independently via _ROLE_FIELD_WEIGHTS.
    #
    # Schema variants:
    #   fiction     → knowledge_domains.ignorant
    #   real_world  → knowledge_domains.blind_spots
    # Both are handled by _knowledge_to_natural().
    if kd := profile.get("knowledge_domains"):
        natural = _knowledge_to_natural(name, kd)
        if natural:
            _add("knowledge", natural)

    # ── Behavior ───────────────────────────────────────────────────────────────
    # Situational reactions, conversation goals, relationship dynamics.
    #
    # Schema variants:
    #   fiction     → situational_behavior + conversation_goals
    #   real_world  → response_patterns
    # Both are included; each key is labelled so the judge can distinguish them.
    #
    # emotional_tells and social_positioning were previously in this blob but
    # are now extracted into their own chunks (below) for sharper retrieval.
    beh_parts: list[str] = []
    if rp := profile.get("response_patterns"):
        beh_parts.append(f"response patterns: {_dump(rp)}")
    if sb := profile.get("situational_behavior"):
        beh_parts.append(f"situational behavior: {_dump(sb)}")
    if cg := profile.get("conversation_goals"):
        beh_parts.append(f"conversation goals: {_dump(cg)}")
    if rm := profile.get("relationship_matrix"):
        beh_parts.append(f"relationship matrix: {_dump(rm)}")
    if beh_parts:
        _add("behavior", f"{name} — " + " | ".join(beh_parts))

    # ── Escalation ─────────────────────────────────────────────────────────────
    # Single sentence, highly distinctive per persona.
    # e.g. Yoda: "calm advice → urgent warnings → firm directives"
    # vs Rick: "snark → lecture → planet-destroying threat delivered casually"
    if ep := profile.get("escalation_pattern"):
        _add("escalation", f"{name} escalation pattern: {ep}")

    # ── Emotional tells ────────────────────────────────────────────────────────
    # Dedicated chunk for per-emotion register shifts.
    # Valuable for BOTH style judges (tone changes signal identity) and behavioral
    # judges (emotional reactions signal character).
    #
    # Schema variants (keys differ, concept is the same):
    #   fiction     → when_guarded, when_genuinely_afraid, when_grieving_or_defeated
    #   real_world  → when_challenged, when_enthusiastic, when_uncertain
    #   both        → when_in_control
    #
    # _emotional_tells_to_natural() handles all keys generically so no signal
    # is lost when new key variants are added to profiles.
    if et := profile.get("emotional_tells"):
        natural = _emotional_tells_to_natural(name, et)
        if natural:
            _add("emotional_tells", natural)

    # ── Social positioning ─────────────────────────────────────────────────────
    # Dedicated chunk for desired vs actual social role and the contradiction
    # between them. Core signal for ideology judges (how does the persona
    # perceive their place in the world?) and behavioral judges (does the
    # observed behavior match the desired vs actual position?).
    if sp := profile.get("social_positioning"):
        natural = _social_positioning_to_natural(name, sp)
        if natural:
            _add("social_positioning", natural)

    # ── Quotes ─────────────────────────────────────────────────────────────────
    # Most discriminating chunks: one per quote. Linguistic fingerprint
    # (rhythm, register, irony) that the embedding model captures even without
    # lexical overlap with the query.
    for i, q in enumerate(profile.get("annotated_quotes", [])):
        text = (
            f'{name} says: "{q["quote"]}" (context: {q.get("context", "")})'
            if isinstance(q, dict)
            else f'{name} says: "{q}"'
        )
        _add("quote", text, i)

    # ── Do-not-say ─────────────────────────────────────────────────────────────
    # Negative examples: highly discriminating for persona identity.
    # A persona that says what another would NEVER say is a strong disconfirmation.
    #
    # Chunk format leads with the PERSONALITY VIOLATION (contradicts), not the
    # banned phrase. Many profiles share generic "winning isn't everything" lines —
    # leading with the trait violation ensures embedding vectors diverge even when
    # the banned line text is shared across profiles.
    #   Old: '{name} would NEVER say: "line" (contradicts: trait)'
    #   New: '{name} — trait violated: "trait" — would never say: "line"'
    for i, d in enumerate(profile.get("do_not_say", [])):
        if isinstance(d, dict):
            line = d.get("line", "")
            contradicts = d.get("contradicts", "")
            if contradicts:
                text = f'{name} — trait violated: "{contradicts}" — would never say: "{line}"'
            else:
                text = f'{name} would NEVER say: "{line}"'
        else:
            text = f'{name} would NEVER say: "{d}"'
        _add("do_not_say", text, i)

    return chunks

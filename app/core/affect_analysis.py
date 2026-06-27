"""
Emotional Taxonomy & Cultural RAG Layer.

Scans incoming messages for:
  1. Cultural & somatic distress expressions (Urdu/Romanized Pakistani context)
  2. Cognitive distortions (catastrophizing, black-white thinking, etc.)

Returns an AffectResult that:
  - Classifies primary_affect for risk tiering
  - Produces enriched English RAG query terms for culturally resonant vector search
  - Lists matched cultural markers so the LLM prompt can acknowledge them
"""
import re
from dataclasses import dataclass

# ── Cultural & Somatic Dictionary ─────────────────────────────────────────────
# Each entry: (list_of_phrases, clinical_affect_label, english_rag_terms)
# Phrases are matched case-insensitively via substring search on lowercased text.

_CULTURAL_MAP: list[tuple[list[str], str, list[str]]] = [
    (
        ["dil ghabra raha hai", "dil ghabrata hai", "dil ghabra raha",
         "bechaini", "bechain", "ghabrahat"],
        "ANXIETY_PANIC",
        ["anxiety", "panic", "restlessness", "unease", "heart palpitations",
         "nervous tension", "worry"],
    ),
    (
        ["zehni bojh", "dimagh sun ho raha hai", "dimag sun ho gaya",
         "sochna band ho gaya", "dimagh kaam nahi kar raha",
         "zehni thakaan"],
        "COGNITIVE_OVERLOAD",
        ["cognitive overload", "mental exhaustion", "emotional numbness",
         "depressive state", "mental shutdown", "brain fog"],
    ),
    (
        ["saans ghut rahi hai", "saans lena mushkil", "dam ghut raha hai",
         "saans nahi aa rahi", "seena bhari hai"],
        "PANIC_ATTACK",
        ["panic attack", "breathlessness", "suffocation", "severe anxiety",
         "chest tightness", "somatic distress", "hyperventilation"],
    ),
    (
        ["andhera lag raha hai", "kuch samajh nahi aa raha",
         "kuch nahi pata", "rasta nahi dikhta", "ummeed nahi",
         "koi raasta nahi", "sab khatam"],
        "HOPELESSNESS",
        ["hopelessness", "overwhelm", "confusion", "despair", "darkness",
         "feeling lost", "no way out"],
    ),
    (
        ["thaka hua hoon", "thak gaya hoon", "thak gayi hoon",
         "bilkul thaka", "jism aur rooh thak gayi"],
        "EXHAUSTION",
        ["burnout", "exhaustion", "fatigue", "depletion", "energy loss",
         "emotional drain"],
    ),
    (
        ["akela feel hota", "akela hoon", "akeli hoon",
         "koi nahi hai mera", "koi samajhta nahi", "koi nahi sunta"],
        "ISOLATION",
        ["loneliness", "isolation", "abandonment", "social withdrawal",
         "feeling unseen", "disconnection"],
    ),
    (
        ["bohat gussa", "gussa aa raha hai", "ghussa", "gussa",
         "cheekh-na chahta", "sabse naraaz"],
        "ANGER_FRUSTRATION",
        ["anger", "frustration", "irritability", "rage", "suppressed emotion",
         "agitation"],
    ),
    # ── English somatic & distress expressions ────────────────────────────────
    (
        ["can't breathe", "cannot breathe", "chest is tight", "chest tightness",
         "heart is racing", "heart pounding", "heart is pounding",
         "can't catch my breath", "shortness of breath"],
        "PANIC_ATTACK",
        ["panic attack", "breathlessness", "chest tightness", "hyperventilation",
         "somatic distress", "acute anxiety", "physical anxiety symptoms"],
    ),
    (
        ["feel hopeless", "feeling hopeless", "no hope", "lost all hope",
         "there is no point", "there's no point", "feel empty",
         "feeling empty", "numb inside", "feel nothing"],
        "HOPELESSNESS",
        ["hopelessness", "despair", "anhedonia", "emotional numbness",
         "feeling lost", "no way out", "existential distress"],
    ),
    (
        ["exhausted", "completely exhausted", "burned out", "burnt out",
         "running on empty", "can't go on like this", "too tired to function",
         "drained", "emotionally drained"],
        "EXHAUSTION",
        ["burnout", "exhaustion", "depletion", "chronic fatigue",
         "emotional drain", "adrenal fatigue"],
    ),
    (
        ["feel so alone", "feel completely alone", "feel isolated",
         "no one understands", "nobody understands", "no one cares",
         "nobody cares", "feel invisible", "like i don't exist"],
        "ISOLATION",
        ["loneliness", "isolation", "social withdrawal", "abandonment",
         "feeling unseen", "lack of social support"],
    ),
    (
        ["can't sleep", "cannot sleep", "haven't slept", "not sleeping",
         "lying awake", "mind won't stop", "thoughts racing at night"],
        "ANXIETY_PANIC",
        ["insomnia", "sleep disturbance", "anxiety", "hyperarousal",
         "rumination", "intrusive thoughts", "sleep anxiety"],
    ),
]

# ── Cognitive Distortion Patterns ─────────────────────────────────────────────
# (distortion_name, trigger_keywords)

_DISTORTIONS: list[tuple[str, list[str]]] = [
    ("catastrophizing",     ["always", "never", "everything is", "it's all ruined",
                             "destroyed", "disaster", "worst", "terrible", "nothing works",
                             "completely ruined"]),
    ("black_white_thinking",["everyone hates", "nobody cares", "all or nothing",
                             "completely worthless", "total failure", "perfect or nothing"]),
    ("mind_reading",        ["they think i'm", "she thinks", "he thinks",
                             "everyone thinks i", "they must think", "i know they"]),
    ("fortune_telling",     ["it will never get better", "nothing will change",
                             "no point", "pointless", "useless to try", "it won't work",
                             "nothing will ever"]),
    ("emotional_reasoning", ["i feel like a burden", "i feel worthless", "i must be",
                             "i know i am bad", "i feel like i am"]),
    ("personalization",     ["my fault", "i caused this", "because of me",
                             "i ruined everything", "i am to blame", "i did this to them"]),
    ("overgeneralization",  ["i always fail", "i never succeed", "this always happens to me",
                             "i can never do anything right"]),
]


@dataclass
class AffectResult:
    primary_affect: str         # dominant clinical affect label (e.g. "ANXIETY_PANIC")
    cultural_markers: list[str] # matched Urdu/somatic phrases from user's message
    distortions: list[str]      # cognitive distortion types detected
    rag_enrichment: str         # English terms to enrich the pgvector RAG query
    clinical_note: str          # one-line note for LLM system prompt injection
    raw_score: float            # 0.0–1.0 distress signal density (not clinical)


def analyze_affect(text: str) -> AffectResult:
    """
    Scan text for cultural distress expressions and cognitive distortions.

    Returns AffectResult. Always returns a valid result; NEUTRAL when nothing detected.
    """
    lower = text.lower()

    primary_affect = "NEUTRAL"
    cultural_markers: list[str] = []
    enrichment_terms: list[str] = []

    # Pass 1 — cultural & somatic dictionary scan
    for phrases, affect_label, english_terms in _CULTURAL_MAP:
        for phrase in phrases:
            if phrase in lower:
                cultural_markers.append(phrase)
                if primary_affect == "NEUTRAL":
                    primary_affect = affect_label
                enrichment_terms.extend(english_terms)
                break  # one match per category is sufficient

    # Pass 2 — cognitive distortion detection
    detected_distortions: list[str] = []
    for distortion_name, keywords in _DISTORTIONS:
        for kw in keywords:
            if kw in lower:
                detected_distortions.append(distortion_name)
                break

    # Compute raw distress score (density heuristic, not clinical diagnosis)
    signal_count = len(cultural_markers) * 2 + len(detected_distortions)
    raw_score = min(1.0, signal_count / 6.0)

    # Build enriched RAG query — deduped English terms + original text fallback
    unique_terms = list(dict.fromkeys(enrichment_terms))
    rag_enrichment = " ".join(unique_terms) if unique_terms else text

    # Build a one-line clinical note for the LLM system prompt
    clinical_note = _build_clinical_note(primary_affect, cultural_markers, detected_distortions)

    return AffectResult(
        primary_affect=primary_affect,
        cultural_markers=cultural_markers,
        distortions=detected_distortions,
        rag_enrichment=rag_enrichment,
        clinical_note=clinical_note,
        raw_score=raw_score,
    )


def _build_clinical_note(affect: str, markers: list[str], distortions: list[str]) -> str:
    """Compose a concise clinical context note for the LLM system prompt."""
    parts: list[str] = []

    if markers:
        phrase_display = f'"{markers[0]}"' if len(markers) == 1 else f'"{markers[0]}" and {len(markers)-1} more'
        affect_readable = affect.replace("_", " ").title()
        parts.append(
            f"The user expressed distress through the cultural phrase {phrase_display}, "
            f"which maps to: {affect_readable}. "
            f"Acknowledge this somatic or emotional experience without naming the clinical label."
        )

    if distortions:
        dist_list = ", ".join(d.replace("_", " ") for d in distortions[:3])
        parts.append(
            f"Cognitive pattern(s) detected: {dist_list}. "
            f"Gently challenge these patterns through the Empower step — do not label them to the user."
        )

    return " ".join(parts) if parts else ""

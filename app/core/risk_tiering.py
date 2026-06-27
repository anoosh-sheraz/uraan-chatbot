"""
Dynamic Clinical Risk Tiering — 3-Tier System.

TIER 1 (LOW):      Standard VEE pipeline. temperature=0.30 (0.25 when distress keywords detected).
TIER 2 (MODERATE): Lowered temperature=0.15. Passive resource array injected into SSE meta.
TIER 3 (CRISIS):   LLM generation halted. Hard-coded Urdu emergency intercept returned.

Tier 3 is reached via two independent gates:
  a) is_crisis() returns True (existing spaCy phrase/lemma scanner)
  b) High-risk affect (HOPELESSNESS) with raw_score >= 0.4
"""
from enum import IntEnum
from dataclasses import dataclass, field
from app.core.affect_analysis import AffectResult


class RiskTier(IntEnum):
    LOW      = 1
    MODERATE = 2
    CRISIS   = 3


# ── Distress keyword gate ─────────────────────────────────────────────────────
# Used to lower temperature and trigger helpline-first retrieval even for
# messages that don't reach MODERATE tier via affect/distortion scoring.

DISTRESS_KEYWORDS: frozenset[str] = frozenset({
    "depression", "depressed", "sad", "sadness", "hopeless", "hopelessness",
    "distress", "distressed", "anxious", "anxiety", "overwhelmed", "worried",
    "grief", "lonely", "alone", "suicidal", "self-harm", "helpless",
    "desperate", "worthless", "empty", "numb", "exhausted", "burned out",
    "burnt out", "panic", "scared", "afraid", "fearful", "drained",
})

DISTRESS_TEMPERATURE = 0.25  # More conservative than LOW default (0.30)


def is_distress_query(text: str) -> bool:
    """
    Returns True if the message contains explicit distress keywords.
    Used to trigger helpline-first RAG retrieval and lower response temperature.
    """
    lower = text.lower()
    return any(kw in lower for kw in DISTRESS_KEYWORDS)


WORK_KEYWORDS: frozenset[str] = frozenset({
    "work", "job", "boss", "manager", "colleague", "coworker", "office",
    "career", "profession", "leadership", "team", "employee", "employer",
    "workplace", "meeting", "deadline", "salary", "promotion", "business",
    "client", "presentation", "performance", "productivity",
    "work stress", "work pressure", "professional",
})


def is_work_query(text: str) -> bool:
    """
    Returns True if the message relates to work, leadership, or professional contexts.
    Used to trigger the EI Professional Success Protocol.
    """
    lower = text.lower()
    return any(kw in lower for kw in WORK_KEYWORDS)


# Affect labels that can independently trigger Tier 3 when score is high enough.
# PANIC_ATTACK is intentionally excluded: even severe panic attacks need the
# VEE somatic technique (Tier 2) not the LLM-bypass emergency intercept.
_CRISIS_TIER_AFFECTS = {"HOPELESSNESS"}

# Affect labels that automatically place the user in at least Tier 2
_MODERATE_TIER_AFFECTS = {
    "ANXIETY_PANIC", "COGNITIVE_OVERLOAD", "ISOLATION", "EXHAUSTION", "PANIC_ATTACK",
}

# Passive resource array injected into SSE meta for Tier 2
TIER2_RESOURCES: list[dict] = [
    {
        "label":     "Umang Mental Health Helpline",
        "number":    "0317-4288665",
        "available": "24/7",
        "type":      "call",
    },
    {
        "label":     "Rozan Counselling Helpline",
        "number":    "051-2890505",
        "available": "Monday–Saturday, 9 am – 5 pm",
        "type":      "call",
    },
    {
        "label":     "Pakistan Psychological Association",
        "url":       "https://www.ppa.org.pk",
        "available": "Referral directory",
        "type":      "web",
    },
]

# Hard-coded Tier 3 Urdu emergency intercept — never passes through the LLM
TIER3_INTERCEPT = (
    "Aap akele nahi hain. Fauri madad ke liye in numbers par abhi rabta karein:\n\n"
    "🚨  Ambulance / Rescue Pakistan: 115\n"
    "💙  Umang Mental Health Helpline: 0317-4288665\n"
    "💚  Rozan Counselling Helpline: 051-2890505\n\n"
    "Ek trained counselor aapki baat sunne ke liye tayar hai. Abhi call karein.\n"
    "You are not alone. Help is one call away."
)


@dataclass
class TierResult:
    tier: RiskTier
    temperature: float
    resources: list[dict]     # non-empty for Tier 2
    intercept_message: str    # non-empty for Tier 3
    reason: str               # audit trail string


def classify_risk(affect: AffectResult, crisis_detected: bool, text: str = "") -> TierResult:
    """
    Classify message into Tier 1 / 2 / 3 given affect analysis and binary crisis flag.

    Args:
        affect:          Result from analyze_affect()
        crisis_detected: True if is_crisis() returned True (spaCy gate)
        text:            Optional raw message text — enables distress keyword temperature adjustment

    Returns:
        TierResult with tier, temperature, resources, and optional intercept message.
    """
    # ── Tier 3 Gate A: existing spaCy crisis scanner ──────────────────────────
    if crisis_detected:
        return TierResult(
            tier=RiskTier.CRISIS,
            temperature=0.0,
            resources=[],
            intercept_message=TIER3_INTERCEPT,
            reason="spacy_crisis_gate",
        )

    # ── Tier 3 Gate B: high-risk affect with significant distress density ─────
    if affect.primary_affect in _CRISIS_TIER_AFFECTS and affect.raw_score >= 0.4:
        return TierResult(
            tier=RiskTier.CRISIS,
            temperature=0.0,
            resources=[],
            intercept_message=TIER3_INTERCEPT,
            reason=f"high_risk_affect:{affect.primary_affect}:score={affect.raw_score:.2f}",
        )

    # ── Tier 2: moderate distress signals ────────────────────────────────────
    if (
        affect.raw_score >= 0.3
        or len(affect.distortions) >= 2
        or affect.primary_affect in _MODERATE_TIER_AFFECTS
    ):
        return TierResult(
            tier=RiskTier.MODERATE,
            temperature=0.15,
            resources=TIER2_RESOURCES,
            intercept_message="",
            reason=f"moderate_distress:affect={affect.primary_affect}:score={affect.raw_score:.2f}:distortions={len(affect.distortions)}",
        )

    # ── Tier 1: low distress — standard VEE ──────────────────────────────────
    # Apply DISTRESS_TEMPERATURE (0.25) if message contains explicit distress
    # keywords even though it didn't hit MODERATE thresholds. Keeps responses
    # conservative for sadness/depression mentions that score below the numeric gate.
    distress = is_distress_query(text) if text else False
    return TierResult(
        tier=RiskTier.LOW,
        temperature=DISTRESS_TEMPERATURE if distress else 0.30,
        resources=[],
        intercept_message="",
        reason="low_distress" + (":distress_keyword" if distress else ""),
    )

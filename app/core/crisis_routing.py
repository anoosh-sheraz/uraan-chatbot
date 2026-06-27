import spacy

_nlp = spacy.load("en_core_web_sm")

# Exact multi-word phrases checked before token-level scan
_CRISIS_PHRASES = [
    "kill myself",
    "killing myself",
    "end my life",
    "take my life",
    "want to die",
    "wish i was dead",
    "wish i were dead",
    "better off dead",
    "no reason to live",
    "don't want to live",
    "dont want to live",
    "hurt myself",
    "harm myself",
    "cut myself",
    "cutting myself",
    "hang myself",
    "shoot myself",
    "overdose on",
]

# Lemma-level keywords — strictly suicidal ideation and direct harm signals only.
# "hopeless", "helpless", "worthless", "despair", "desperate" are handled at the
# affect/risk-tier layer (Tier 2) — they are too common in non-suicidal distress to
# warrant the Tier 3 LLM bypass here.
_CRISIS_LEMMAS = {
    "suicide",
    "suicidal",
    "self-harm",
    "selfharm",
    "overdose",
    "molest",
    "assault",
    "rape",
}

_EMERGENCY_RESPONSE = (
    "I'm very concerned about what you've shared. "
    "Please reach out for immediate help right now:\n\n"
    "- Emergency: 115 (Rescue Pakistan)\n"
    "- Umang Mental Health Helpline: 0317-4288665\n"
    "- Rozan Counselling Helpline: 051-2890505\n\n"
    "You are not alone. A trained counselor is ready to listen. "
    "Please call one of these numbers now."
)


def is_crisis(text: str) -> tuple[bool, str]:
    """
    Scan text for high-risk psychiatric signals.

    Returns (crisis_detected: bool, reason: str).
    reason is empty string when no crisis is found.
    """
    lower = text.lower()

    for phrase in _CRISIS_PHRASES:
        if phrase in lower:
            return True, f"phrase_match: '{phrase}'"

    doc = _nlp(lower)
    for token in doc:
        if token.lemma_ in _CRISIS_LEMMAS:
            return True, f"lemma_match: '{token.lemma_}'"

    return False, ""


def get_emergency_response() -> str:
    return _EMERGENCY_RESPONSE

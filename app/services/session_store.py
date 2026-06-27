"""
In-memory session store.

Tracks:
  - Conversation history (last 20 messages per session)
  - Emotional state log (last 5 turns per session) for sentiment drift detection

Drift detection logic:
  A "sharp downward drift" is declared when ANY of these conditions hold
  across the last 5 emotional states:
    a) 3 or more states are MODERATE (tier 2) or CRISIS (tier 3)
    b) Distress scores show a monotonically worsening trend
"""
from collections import defaultdict, deque
from collections import Counter
from datetime import datetime


# ── Conversation history ──────────────────────────────────────────────────────
# Stores {role, content} dicts. maxlen=20 gives 10 full turns.

_sessions:  dict[str, deque] = defaultdict(lambda: deque(maxlen=20))
_metadata:  dict[str, dict]  = {}

# ── Emotional state log ───────────────────────────────────────────────────────
# Stores {affect, tier, score, ts} for last 5 turns.

_emotion_logs: dict[str, deque] = defaultdict(lambda: deque(maxlen=5))


# ── Conversation history API ──────────────────────────────────────────────────

def add_turn(session_id: str, user_msg: str, assistant_msg: str) -> None:
    if session_id not in _metadata:
        _metadata[session_id] = {
            "created_at": datetime.utcnow().isoformat(),
            "turn_count":  0,
        }
    _sessions[session_id].append({"role": "user",      "content": user_msg})
    _sessions[session_id].append({"role": "assistant", "content": assistant_msg})
    _metadata[session_id]["turn_count"] += 1
    _metadata[session_id]["last_active"] = datetime.utcnow().isoformat()


def get_history(session_id: str) -> list[dict]:
    return list(_sessions.get(session_id, []))


def get_session_info(session_id: str) -> dict | None:
    if session_id not in _metadata:
        return None
    return {
        "session_id":    session_id,
        **_metadata[session_id],
        "message_count": len(_sessions[session_id]),
    }


def clear_session(session_id: str) -> bool:
    if session_id not in _sessions and session_id not in _metadata:
        return False
    _sessions.pop(session_id, None)
    _metadata.pop(session_id, None)
    _emotion_logs.pop(session_id, None)
    return True


def list_sessions() -> list[dict]:
    return [{"session_id": sid, **meta} for sid, meta in _metadata.items()]


# ── Emotional state tracking API ──────────────────────────────────────────────

def add_emotional_state(
    session_id: str,
    affect: str,
    tier: int,
    score: float,
) -> None:
    """Record the emotional state for one turn. Keeps last 5."""
    _emotion_logs[session_id].append({
        "affect": affect,
        "tier":   tier,
        "score":  round(score, 3),
        "ts":     datetime.utcnow().isoformat(),
    })


def get_sentiment_drift(session_id: str) -> dict:
    """
    Analyze the last 5 emotional states for a downward drift.

    Returns:
        drift_detected (bool)  — True if worsening trend found
        trend          (str)   — "worsening" | "stable_low" | "mixed" | "insufficient_data"
        dominant_affect (str)  — most common affect label in the window
        states_analyzed (int)  — how many states were available
        recent_tiers   (list)  — raw tier values for frontend display
    """
    log = list(_emotion_logs.get(session_id, []))

    if len(log) < 2:
        return {
            "drift_detected":  False,
            "trend":           "insufficient_data",
            "dominant_affect": "NEUTRAL",
            "states_analyzed": len(log),
            "recent_tiers":    [e["tier"] for e in log],
        }

    tiers  = [e["tier"]  for e in log]
    scores = [e["score"] for e in log]

    # Condition A: 3 or more of last 5 turns are tier 2+ (moderate or crisis)
    moderate_or_worse = sum(1 for t in tiers if t >= 2)

    # Condition B: scores are monotonically non-decreasing (pure worsening)
    is_monotone_worse = all(scores[i] <= scores[i + 1] for i in range(len(scores) - 1))

    # Condition C: last 2 turns both tier 2+ AND score increased
    recent_worsening = (
        len(tiers) >= 2
        and tiers[-1] >= 2
        and tiers[-2] >= 2
        and scores[-1] >= scores[-2]
    )

    drift = moderate_or_worse >= 3 or is_monotone_worse or recent_worsening

    # Dominant affect
    affect_counter = Counter(e["affect"] for e in log)
    dominant = affect_counter.most_common(1)[0][0] if affect_counter else "NEUTRAL"

    # Trend label
    if drift:
        trend = "worsening"
    elif moderate_or_worse == 0:
        trend = "stable_low"
    else:
        trend = "mixed"

    return {
        "drift_detected":  drift,
        "trend":           trend,
        "dominant_affect": dominant,
        "states_analyzed": len(log),
        "recent_tiers":    tiers,
    }

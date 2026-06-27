"""
URAAN Safe Voice — FastAPI Application
Hospital-compliant mental health chatbot backend.

7-Step Clinical Pipeline (per /chat request):
  1. Emotional Taxonomy    — cultural/somatic affect analysis + cognitive distortion scan
  2. Risk Tiering          — 3-tier classification (LOW / MODERATE / CRISIS)
  3. Tier 3 Intercept      — immediate Urdu emergency response, LLM never called
  4. PII Scrubbing         — Presidio removes names, phones, emails, locations
  5. Enriched RAG          — affect-enriched pgvector query; helpline docs prepended for distress
  6. Sentiment Drift Check — rolling 5-turn emotional trajectory analysis
  7. VEE Streaming         — sentence-buffered GPT-4o response (Validate→Explore→Empower)
"""
import json
from fastapi import FastAPI, HTTPException, Path
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from app.core.crisis_routing   import is_crisis, get_emergency_response
from app.core.security         import scrub_pii
from app.core.affect_analysis  import analyze_affect
from app.core.risk_tiering     import classify_risk, RiskTier, TIER3_INTERCEPT, is_distress_query, is_work_query
from app.services.rag_service  import retrieve_context, seed_vector_store
from app.services.llm_service  import stream_chat_response
from app.services.session_store import (
    add_turn, add_emotional_state,
    get_history, get_sentiment_drift,
    get_session_info, clear_session, list_sessions,
)

load_dotenv()

# ── API Metadata ──────────────────────────────────────────────────────────────

_TAGS = [
    {
        "name": "Chat",
        "description": (
            "Core mental health chat endpoint. Runs the full 7-step clinical pipeline: "
            "emotional taxonomy → risk tiering → PII scrubbing → enriched RAG retrieval "
            "→ sentiment drift check → sentence-buffered VEE streaming."
        ),
    },
    {
        "name": "Analysis",
        "description": (
            "Analyze a message for crisis signals, PII, cultural affect markers, "
            "and cognitive distortions without calling the AI model."
        ),
    },
    {
        "name": "Session",
        "description": (
            "Manage multi-turn conversation sessions with emotional state tracking. "
            "Sessions persist conversation history and the last 5 emotional states."
        ),
    },
    {
        "name": "RAG",
        "description": (
            "Manage the pgvector knowledge base of Pakistani socio-economic context documents. "
            "Seed, search, and check status."
        ),
    },
    {
        "name": "System",
        "description": "Health check and service metadata.",
    },
]

app = FastAPI(
    title="URAAN Safe Voice",
    description=(
        "## Hospital-Compliant Mental Health Chatbot — v2.0\n\n"
        "URAAN Safe Voice is a clinically-informed AI assistant for Pakistani users. "
        "Every message passes through a **7-step clinical pipeline**:\n\n"
        "1. **Emotional Taxonomy** — cultural/somatic dictionary + cognitive distortion scan\n"
        "2. **Risk Tiering** — 3-tier classification (LOW / MODERATE / CRISIS)\n"
        "3. **Tier 3 Intercept** — immediate Urdu emergency response, LLM never called\n"
        "4. **PII Scrubbing** — Microsoft Presidio strips all identifying information\n"
        "5. **Enriched RAG** — affect-enriched pgvector semantic search; helpline docs first for distress\n"
        "6. **Sentiment Drift** — rolling 5-turn emotional trajectory monitoring\n"
        "7. **VEE Streaming** — sentence-buffered GPT-4o via Validate → Explore → Empower\n\n"
        "**Emergency contacts:** 115 (Rescue Pakistan) | Umang: 0317-4288665 | Rozan: 051-2890505"
    ),
    version="2.0.0",
    openapi_tags=_TAGS,
    contact={"name": "Project Uraan", "email": "anooshaiofficials@gmail.com"},
    license_info={"name": "Private — Project Uraan"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message:    str = Field(..., min_length=1, max_length=2000,
                            example="Mera dil ghabra raha hai aur kuch samajh nahi aa raha.")
    session_id: str = Field(default="default", max_length=64, example="user-session-001")
    mode:       str = Field(default="empathetic", example="empathetic")


class AnalyzeRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000,
                         example="Saans ghut rahi hai, zehni bojh bohat zyada hai.")


class AnalyzeResponse(BaseModel):
    crisis_detected:  bool
    crisis_trigger:   str
    risk_tier:        int
    tier_reason:      str
    primary_affect:   str
    cultural_markers: list[str]
    distortions:      list[str]
    pii_detected:     bool
    scrubbed_message: str
    raw_distress_score: float


class SearchRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000,
                         example="I cannot afford therapy and live in a rural area.")
    top_k: int = Field(default=3, ge=1, le=10)


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", tags=["System"], summary="API Welcome")
async def root():
    return {
        "service":     "URAAN Safe Voice",
        "version":     "2.0.0",
        "pipeline":    "7-step clinical pipeline",
        "framework":   "Validate → Explore → Empower (VEE)",
        "risk_tiers":  {"1": "LOW", "2": "MODERATE", "3": "CRISIS"},
        "docs":        "/docs",
        "health":      "/health",
    }


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.post(
    "/chat",
    tags=["Chat"],
    summary="Send a message — full 7-step clinical pipeline",
    response_description=(
        "SSE stream (meta → chunk(s) → done). "
        "Crisis (Tier 3) returns SSE with a single Urdu emergency chunk — LLM never called."
    ),
)
async def chat(request: ChatRequest):
    """
    **7-Step Clinical Pipeline:**

    | Step | Name | Description |
    |------|------|-------------|
    | 1 | Emotional Taxonomy | Cultural/somatic dictionary + cognitive distortion scan |
    | 2 | Risk Tiering | Tier 1 (LOW) / Tier 2 (MODERATE) / Tier 3 (CRISIS) |
    | 3 | Tier 3 Gate | Urdu emergency intercept — no LLM call |
    | 4 | PII Scrubbing | Presidio anonymizer |
    | 5 | Enriched RAG | Affect-enriched pgvector query; helpline docs prepended for distress |
    | 6 | Sentiment Drift | 5-turn rolling emotional trajectory |
    | 7 | VEE Stream | Sentence-buffered GPT-4o |

    **SSE event schema:**
    ```
    meta  → { type, risk_tier, primary_affect, distortions, cultural_markers,
               pii_scrubbed, rag_docs_retrieved, sentiment_drift, resources,
               session_id, is_distress }
    chunk → { type, content }   ← one complete sentence per chunk
    error → { type, detail }    ← pipeline error surfaced to client
    done  → { type }
    ```
    """
    # ── Step 1: Emotional Taxonomy ────────────────────────────────────────────
    affect = analyze_affect(request.message)

    # ── Step 2: Risk Tiering + distress keyword detection ────────────────────
    crisis_flag, crisis_trigger = is_crisis(request.message)
    distress_flag = is_distress_query(request.message)
    work_flag     = is_work_query(request.message)
    tier_result   = classify_risk(affect, crisis_flag, request.message)

    # ── Step 3: Tier 3 Intercept — LLM never called ──────────────────────────
    if tier_result.tier == RiskTier.CRISIS:
        async def crisis_stream():
            yield f"data: {json.dumps({'type': 'meta', 'risk_tier': 3, 'crisis': True, 'session_id': request.session_id, 'primary_affect': affect.primary_affect, 'tier_reason': tier_result.reason})}\n\n"
            yield f"data: {json.dumps({'type': 'chunk', 'content': tier_result.intercept_message})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return StreamingResponse(crisis_stream(), media_type="text/event-stream")

    # ── Step 4: PII Scrubbing ─────────────────────────────────────────────────
    scrubbed    = scrub_pii(request.message)
    pii_scrubbed = scrubbed != request.message

    # ── Step 5: Enriched RAG retrieval ────────────────────────────────────────
    # When distress_flag=True, helpline/referral docs are prepended so the LLM
    # reads support-service information before any grounding technique.
    rag_query = affect.rag_enrichment if affect.rag_enrichment != request.message else scrubbed
    try:
        rag_docs = retrieve_context(rag_query, k=3, is_distress=distress_flag)
    except Exception:
        rag_docs = []

    # ── Step 6: Session history + sentiment drift ─────────────────────────────
    history = get_history(request.session_id)
    drift   = get_sentiment_drift(request.session_id)

    # ── Step 7: Sentence-buffered VEE streaming ───────────────────────────────
    async def event_stream():
        meta_event = {
            "type":               "meta",
            "risk_tier":          tier_result.tier.value,
            "tier_reason":        tier_result.reason,
            "primary_affect":     affect.primary_affect,
            "cultural_markers":   affect.cultural_markers,
            "distortions":        affect.distortions,
            "pii_scrubbed":       pii_scrubbed,
            "rag_docs_retrieved": len(rag_docs),
            "sentiment_drift":    drift["drift_detected"],
            "drift_trend":        drift["trend"],
            "resources":          tier_result.resources,   # populated for Tier 2
            "session_id":         request.session_id,
            "is_distress":        distress_flag,
            "is_work":            work_flag,
        }
        yield f"data: {json.dumps(meta_event)}\n\n"

        full_response = ""
        try:
            async for sentence in stream_chat_response(
                scrubbed, rag_docs, history, tier_result, affect, drift,
                mode=request.mode,
                is_distress=distress_flag,
                is_work=work_flag,
            ):
                full_response += sentence
                yield f"data: {json.dumps({'type': 'chunk', 'content': sentence})}\n\n"
        except Exception as exc:
            err_detail = f"{type(exc).__name__}: {str(exc)[:300]}"
            yield f"data: {json.dumps({'type': 'error', 'detail': err_detail})}\n\n"
            yield f"data: {json.dumps({'type': 'chunk', 'content': f'[Pipeline error — {err_detail}]'})}\n\n"

        if full_response:
            add_turn(request.session_id, scrubbed, full_response)
            add_emotional_state(
                request.session_id,
                affect.primary_affect,
                tier_result.tier.value,
                affect.raw_score,
            )
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Analysis ──────────────────────────────────────────────────────────────────

@app.post(
    "/analyze",
    tags=["Analysis"],
    response_model=AnalyzeResponse,
    summary="Full pipeline analysis without AI response",
)
async def analyze(request: AnalyzeRequest):
    """
    Runs the full analysis pipeline (Steps 1–4) **without calling the AI model**.

    Returns crisis status, risk tier, cultural affect markers, cognitive distortions, and PII report.
    Use this for audit logging, moderation dashboards, or pre-flight checks.
    """
    affect                   = analyze_affect(request.message)
    crisis_flag, crisis_trigger = is_crisis(request.message)
    tier_result              = classify_risk(affect, crisis_flag)
    scrubbed                 = scrub_pii(request.message)

    return AnalyzeResponse(
        crisis_detected    = crisis_flag,
        crisis_trigger     = crisis_trigger,
        risk_tier          = tier_result.tier.value,
        tier_reason        = tier_result.reason,
        primary_affect     = affect.primary_affect,
        cultural_markers   = affect.cultural_markers,
        distortions        = affect.distortions,
        pii_detected       = scrubbed != request.message,
        scrubbed_message   = scrubbed,
        raw_distress_score = affect.raw_score,
    )


# ── Session Management ────────────────────────────────────────────────────────

@app.get(
    "/session/{session_id}",
    tags=["Session"],
    summary="Get conversation history and emotional state log",
)
async def get_session(session_id: str = Path(..., example="user-session-001")):
    info = get_session_info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    drift = get_sentiment_drift(session_id)
    return {**info, "history": get_history(session_id), "sentiment": drift}


@app.delete(
    "/session/{session_id}",
    tags=["Session"],
    summary="Clear a conversation session",
)
async def delete_session(session_id: str = Path(..., example="user-session-001")):
    if not clear_session(session_id):
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {"message": f"Session '{session_id}' cleared successfully."}


@app.get("/sessions", tags=["Session"], summary="List all active sessions")
async def sessions():
    all_sessions = list_sessions()
    return {"total": len(all_sessions), "sessions": all_sessions}


# ── RAG ───────────────────────────────────────────────────────────────────────

@app.post("/rag/seed", tags=["RAG"], summary="Seed the vector store")
async def rag_seed():
    try:
        count = seed_vector_store()
        return {"seeded": count, "collection": "uraan_context_docs", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Seed failed: {str(e)}")


@app.post("/rag/search", tags=["RAG"], summary="Semantic similarity search")
async def rag_search(request: SearchRequest):
    crisis_flag, _ = is_crisis(request.message)
    if crisis_flag:
        return {"crisis_detected": True, "response": get_emergency_response(), "context_docs": []}
    affect    = analyze_affect(request.message)
    rag_query = affect.rag_enrichment if affect.rag_enrichment != request.message else request.message
    scrubbed  = scrub_pii(rag_query)
    try:
        docs = retrieve_context(scrubbed, k=request.top_k)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Vector store unavailable: {str(e)}")
    return {
        "crisis_detected":  False,
        "primary_affect":   affect.primary_affect,
        "enriched_query":   rag_query,
        "context_docs":     docs,
    }


@app.get("/rag/status", tags=["RAG"], summary="Vector store connection status")
async def rag_status():
    from app.core.database import check_db_connection
    connected = check_db_connection()
    return {
        "database_connected": connected,
        "collection":         "uraan_context_docs",
        "embedding_model":    "text-embedding-3-small",
        "status": "ready" if connected else "offline — run POST /rag/seed after connecting",
    }


# ── System ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="Service health check")
async def health_check():
    from app.core.database import engine
    from sqlalchemy import text
    db_status = "unavailable"
    db_error = ""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_error = str(e)[:120]
    return {
        "status":    "healthy",
        "service":   "uraan-safe-voice",
        "version":   "2.0.0",
        "pipeline":  "7-step",
        "database":  db_status,
        "llm_model": "gpt-4o",
        "framework": "Validate → Explore → Empower",
    }

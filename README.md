# URAAN Safe Voice

> Hospital-grade mental health chatbot backend for **Project Uraan** — built for Pakistani users with clinical safety, PII protection, crisis intervention, and culturally-grounded AI responses.

**Version:** 1.0.0 | **Stack:** FastAPI · LangChain · GPT-4o · PostgreSQL · pgvector · Microsoft Presidio · spaCy

---

## Architecture Overview

Every user message passes through a strict, ordered clinical pipeline before the LLM is ever called:

```
User Message
     │
     ▼
┌─────────────────────┐
│  1. Crisis Detection │  ← spaCy lemma + phrase scan
│  (crisis_routing.py) │    If triggered → immediate helplines, NO LLM call
└──────────┬──────────┘
           │ safe
           ▼
┌─────────────────────┐
│  2. PII Scrubbing   │  ← Microsoft Presidio
│  (security.py)      │    Names, phones, emails, locations → [NAME], [PHONE]…
└──────────┬──────────┘
           │ anonymized
           ▼
┌─────────────────────┐
│  3. RAG Retrieval   │  ← pgvector similarity search
│  (rag_service.py)   │    Top-3 socio-economic context docs retrieved
└──────────┬──────────┘
           │ context
           ▼
┌─────────────────────┐
│  4. LLM Streaming   │  ← GPT-4o · temp 0.3 · VEE Framework
│  (llm_service.py)   │    Validate → Explore → Empower
└──────────┬──────────┘
           │ SSE stream
           ▼
      Client Response
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| API Framework | FastAPI 0.138 | REST endpoints, SSE streaming |
| LLM Orchestration | LangChain + LangChain-OpenAI | Chain management, streaming |
| Language Model | OpenAI GPT-4o (temp 0.3) | Clinical-consistency chat |
| PII Scrubbing | Microsoft Presidio | HIPAA-aligned anonymization |
| NLP Engine | spaCy `en_core_web_sm` | Crisis keyword detection |
| Vector Store | PostgreSQL + pgvector | RAG similarity search |
| ORM | SQLAlchemy | Database session management |
| Database | PostgreSQL (via Docker) | Persistent vector + session storage |
| Server | Uvicorn | ASGI server |
| Config | python-dotenv | Environment variable management |

---

## Project Structure

```
URAAN/
├── app/
│   ├── main.py                     # App entry point, all route wiring
│   ├── api/
│   │   └── chat.py                 # Legacy /api/v1/chat/ route
│   ├── core/
│   │   ├── config.py               # Settings loaded from .env
│   │   ├── database.py             # SQLAlchemy engine + session + health check
│   │   ├── security.py             # Presidio PII scrubber → scrub_pii()
│   │   └── crisis_routing.py       # Crisis detector → is_crisis(), emergency response
│   └── services/
│       ├── anonymizer.py           # Presidio wrapper (used by Phase 2 pipeline)
│       ├── chat.py                 # Direct GPT-4o (legacy /api/v1/chat/)
│       ├── rag_service.py          # pgvector init, seed, retrieve_context()
│       └── llm_service.py          # VEE system prompt + streaming response
├── .env                            # Secret keys — NEVER commit
├── .env.example                    # Template
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- Docker Desktop
- OpenAI API key

### 1. Clone and enter the project
```bash
git clone <repo-url>
cd URAAN
```

### 2. Create and activate virtual environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Download the spaCy model
```bash
python -m spacy download en_core_web_sm
```

### 5. Configure environment
```bash
cp .env.example .env
```

Edit `.env`:
```env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://uraan:devpass@localhost:5432/uraan_db
MODEL_NAME=gpt-4o
```

### 6. Start PostgreSQL with pgvector (Docker)
```bash
docker run -d \
  --name uraan-db \
  -e POSTGRES_USER=uraan \
  -e POSTGRES_PASSWORD=devpass \
  -e POSTGRES_DB=uraan_db \
  -p 5432:5432 \
  ankane/pgvector
```

### 7. Start the API server
```bash
uvicorn app.main:app --reload --port 8000
```

### 8. Seed the vector store (run once)
```bash
curl -X POST http://127.0.0.1:8000/rag/seed
```

---

## API Reference

### `GET /health`
Returns server and database status.

```json
{
  "status": "healthy",
  "service": "uraan-safe-voice",
  "version": "1.0.0",
  "database": "connected"
}
```

---

### `POST /chat` — Main Endpoint (Full Pipeline)

Runs the complete 4-step clinical pipeline. Returns a **Server-Sent Events (SSE) stream**.

**Request:**
```json
{
  "message": "I feel overwhelmed and cannot afford therapy",
  "session_id": "user-123"
}
```

**Response — Safe message (SSE stream):**
```
data: {"type": "meta", "pii_scrubbed": false, "rag_docs_retrieved": 3, "session_id": "user-123"}

data: {"type": "chunk", "content": "What you are feeling makes complete sense."}

data: {"type": "chunk", "content": " It sounds incredibly challenging..."}

data: {"type": "done"}
```

**Response — Crisis detected (JSON, immediate):**
```json
{
  "crisis_detected": true,
  "trigger": "phrase_match: 'end my life'",
  "response": "I'm very concerned... 115 (Rescue Pakistan)... Umang: 0317-4288665...",
  "pii_scrubbed": false,
  "session_id": "user-123"
}
```

---

### `POST /rag/seed`
Populate the pgvector collection with the 8 regional context documents.

```json
{"seeded": 8, "collection": "uraan_context_docs"}
```

### `POST /rag/search`
Run the security pipeline + similarity search and return context documents.

**Request:**
```json
{"message": "I cannot afford therapy in rural Pakistan", "top_k": 3}
```

**Response:**
```json
{
  "crisis_detected": false,
  "scrubbed_input": "I cannot afford therapy in rural Pakistan",
  "context_docs": [
    {
      "content": "Pakistan's mental health infrastructure...",
      "category": "healthcare_access",
      "similarity_score": 0.8743
    }
  ]
}
```

---

## Clinical Design

### The VEE Framework (Validate → Explore → Empower)

Every LLM response is structured by the system prompt into three mandatory steps:

| Step | Purpose | Example |
|---|---|---|
| **Validate** | Acknowledge the user's emotion first, without minimizing | *"What you are feeling makes complete sense."* |
| **Explore** | Ask exactly ONE gentle open-ended question | *"Would you feel comfortable sharing what has been weighing on you most?"* |
| **Empower** | Guide toward self-reflection, never give direct advice | *"You have navigated difficult times before — what helped you then?"* |

### Crisis Detection (Two-Pass)

1. **Phrase scan** — exact multi-word matches: `"kill myself"`, `"end my life"`, `"want to die"`, etc.
2. **Lemma scan** — spaCy tokenization catches variations: `"suicidal"`, `"harming"`, `"abused"`, etc.

If either pass triggers: LLM is **never called**. Emergency response is returned immediately.

### PII Anonymization (Presidio)

| Entity | Replaced With |
|---|---|
| Person name | `[NAME]` |
| Phone number | `[PHONE]` |
| Email address | `[EMAIL]` |
| Location | `[LOCATION]` |
| Date / Time | `[DATE]` |
| Social Security Number | `[SSN]` |
| Credit card | `[CARD]` |
| Medical license | `[MED_ID]` |

### RAG Knowledge Base (8 Documents)

The vector store is seeded with documents covering:
- Digital divide in rural Pakistan (KPK, Balochistan)
- Pakistan's psychiatrist shortage (1 per 500,000 citizens)
- Poverty-driven psychological distress (38% below poverty line)
- Cultural stigma and religious interpretation of mental illness
- Gender barriers — restricted mobility, domestic violence
- Youth unemployment and social media anxiety
- 2022 flood trauma (33 million displaced)
- Informal economy workers and economic precarity

### Zero Data Retention

- The system prompt instructs the model to treat every conversation as new
- No messages are persisted to any database in the current build
- PII is stripped before any text reaches the LLM

---

## Emergency Resources

| Service | Contact |
|---|---|
| Emergency (Rescue Pakistan) | **115** |
| Umang Mental Health Helpline | **0317-4288665** |
| Rozan Counselling Helpline | **051-2890505** |

---

## Interactive Docs

- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI secret key | required |
| `DATABASE_URL` | PostgreSQL connection string | required |
| `MODEL_NAME` | OpenAI model ID | `gpt-4o` |

---

## License

Project Uraan — mental health initiative. All rights reserved.

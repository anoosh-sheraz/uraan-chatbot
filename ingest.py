#!/usr/bin/env python3
"""
ingest.py — Knowledge Base Ingestion Script for URAAN Safe Voice

Loads every PDF from knowledge_base/, splits the text into sentence-preserving
chunks, embeds them with OpenAI text-embedding-3-small, and upserts the
resulting vectors into the pgvector collection that the /chat pipeline queries.

Re-runs are fully idempotent: each chunk is keyed by a SHA-256 hash of its
content, so the database will update existing chunks rather than duplicate them.

Usage
-----
    # Activate the virtual environment first, then run from the project root:

    # Windows
    .venv\\Scripts\\activate
    python ingest.py

    # macOS / Linux
    source .venv/bin/activate
    python ingest.py

    # Inspect chunks without writing to the database:
    python ingest.py --dry-run

Dependencies
------------
    All are already in requirements.txt. If 'pypdf' is missing:
        pip install pypdf
"""

import argparse
import hashlib
import sys
from pathlib import Path

# ── Path bootstrap ────────────────────────────────────────────────────────────
# Allows `from app.core.config import settings` without installing the package.
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# Import shared settings — same object used by the FastAPI app at runtime.
from app.core.config import settings  # noqa: E402  (after sys.path fix)

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings


# ── Ingest configuration ──────────────────────────────────────────────────────

KNOWLEDGE_BASE_DIR = ROOT / "knowledge_base"

# Must match the collection name queried by app/services/rag_service.py so the
# clinical PDF chunks are returned alongside the seed context documents.
COLLECTION_NAME = "uraan_context_docs"

# Chunk geometry for clinical / research PDFs.
#
# 1 000 chars ≈ 200–250 OpenAI tokens at average English density — large enough
# to keep a complete clinical paragraph together (diagnostic criteria,
# treatment protocols), small enough for precise similarity retrieval.
# 200-char overlap prevents context loss at chunk boundaries.
CHUNK_SIZE    = 1000
CHUNK_OVERLAP = 200

# Separators are tried in priority order. The splitter only falls back to the
# next separator when the current one cannot fit the text within CHUNK_SIZE.
# The ordering guarantees that a split always lands at the coarsest natural
# boundary available — paragraph > line > sentence — never mid-word.
_SEPARATORS = [
    "\n\n",   # paragraph break  (highest priority)
    "\n",     # line break
    ". ",     # sentence end
    "! ",
    "? ",
    "; ",
    ", ",     # clause boundary  (last resort before character split)
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _connection_string() -> str:
    """Return DATABASE_URL normalised to the psycopg2 SQLAlchemy driver prefix.

    Mirrors the same logic in app/services/rag_service.py so the ingest script
    and the FastAPI app always connect to the same database instance.
    """
    url = settings.DATABASE_URL
    if not url:
        raise ValueError(
            "DATABASE_URL is empty.\n"
            "Copy .env.example → .env and set the PostgreSQL connection string."
        )
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def _chunk_id(text: str) -> str:
    """Deterministic SHA-256 ID for a chunk.

    Using content-based IDs means re-running the script will *update* existing
    vectors rather than insert duplicates.  Any chunk whose text has changed
    (e.g. after a PDF revision) will receive a new ID and be treated as new.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── Category detection ────────────────────────────────────────────────────────

_CATEGORY_KEYWORDS: list[tuple[list[str], str]] = [
    (["psychological first aid", "pfa", "pfa-guide"], "psychological_first_aid"),
    (["emotional intelligence"], "emotional_intelligence"),
    (["mental health", "psychiatr", "depression", "anxiety", "counselling"], "mental_health_research"),
]

def _category_from_filename(filename: str) -> str:
    """Infer a semantic category from the PDF filename.

    The category surfaces in the LLM system prompt as [PSYCHOLOGICAL_FIRST_AID]
    or [MENTAL_HEALTH_RESEARCH], helping the model understand the nature of the
    source it is drawing from.  Falls back to 'clinical_guideline' for anything
    that does not match the known keyword sets.
    """
    lower = filename.lower()
    for keywords, category in _CATEGORY_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return category
    return "clinical_guideline"


# ── Pipeline steps ────────────────────────────────────────────────────────────

def _load_pdfs() -> list:
    """Load all PDFs from knowledge_base/ and return a flat list of page docs."""
    if not KNOWLEDGE_BASE_DIR.exists():
        raise FileNotFoundError(
            f"Directory not found: {KNOWLEDGE_BASE_DIR}\n"
            "Create knowledge_base/ in the project root and add your PDF files."
        )

    pdfs = sorted(KNOWLEDGE_BASE_DIR.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(
            f"No PDF files found in {KNOWLEDGE_BASE_DIR}.\n"
            "Add your clinical guidelines and research documents."
        )

    print(f"  Found {len(pdfs)} PDF file(s):")
    for p in pdfs:
        size_kb = p.stat().st_size / 1024
        print(f"    • {p.name:<45}  {size_kb:>8.0f} KB")

    loader = PyPDFDirectoryLoader(str(KNOWLEDGE_BASE_DIR))
    pages  = loader.load()
    print(f"\n  Loaded {len(pages)} page(s) total.\n")
    return pages


def _chunk(pages: list) -> tuple[list, list]:
    """Split page documents into sentence-preserving chunks.

    Returns (chunks, ids) where ids are deterministic content hashes suitable
    for idempotent upsertion into pgvector.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size        = CHUNK_SIZE,
        chunk_overlap     = CHUNK_OVERLAP,
        separators        = _SEPARATORS,
        length_function   = len,
        is_separator_regex = False,
    )

    chunks = splitter.split_documents(pages)

    # Enrich metadata with clinical context flags so the /chat pipeline can
    # distinguish PDF-sourced chunks from the hardcoded seed documents.
    for i, chunk in enumerate(chunks):
        filename = Path(chunk.metadata.get("source", "unknown")).name
        # PyPDFLoader uses 0-based page numbers; convert to 1-based for humans.
        page_num = int(chunk.metadata.get("page", 0)) + 1

        chunk.metadata.update({
            "source"      : filename,
            "page"        : page_num,
            "chunk_index" : i,
            "category"    : _category_from_filename(filename),
            "doc_type"    : "pdf",
        })

    ids = [_chunk_id(c.page_content) for c in chunks]

    avg_len = sum(len(c.page_content) for c in chunks) // max(len(chunks), 1)
    print(f"  Produced {len(chunks)} chunk(s)  (avg {avg_len} chars each)\n")
    return chunks, ids


def _upsert(chunks: list, ids: list) -> None:
    """Embed chunks with OpenAI and upsert into pgvector."""
    if not settings.OPENAI_API_KEY:
        raise ValueError(
            "OPENAI_API_KEY is empty.\n"
            "Set it in .env: OPENAI_API_KEY=sk-..."
        )

    embeddings = OpenAIEmbeddings(
        api_key = settings.OPENAI_API_KEY,
        model   = "text-embedding-3-small",
    )

    conn = _connection_string()
    print(f"  Collection  : {COLLECTION_NAME}")
    print(f"  Embeddings  : text-embedding-3-small")
    print(f"  Chunks      : {len(chunks)}")
    print(f"  Host        : {conn.split('@')[-1].split('/')[0]}")
    print(f"\n  Sending to OpenAI Embeddings API — this may take a moment…\n")

    # from_documents creates the pgvector table if it does not exist, then
    # upserts every chunk.  Deterministic IDs ensure idempotency.
    PGVector.from_documents(
        documents         = chunks,
        embedding         = embeddings,
        collection_name   = COLLECTION_NAME,
        connection_string = conn,
        pre_delete_collection = False,
        ids               = ids,
    )

    print(f"  ✓  {len(chunks)} chunks upserted into collection '{COLLECTION_NAME}'")


# ── Entry point ───────────────────────────────────────────────────────────────

def main(dry_run: bool = False) -> None:
    print("\n" + "=" * 52)
    print("  URAAN Safe Voice -- Knowledge Base Ingest")
    print("=" * 52 + "\n")

    # Step 1 — Load
    print("[ 1 / 3 ]  Loading PDFs from knowledge_base/")
    pages = _load_pdfs()

    # Step 2 — Chunk
    print("[ 2 / 3 ]  Chunking  "
          f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}, sentence-aware)")
    chunks, ids = _chunk(pages)

    if dry_run:
        print("─" * 52)
        print("  DRY RUN — database write skipped")
        print("─" * 52)
        print(f"\nSample — chunk #0 (first {min(600, len(chunks[0].page_content))} chars):")
        print(f"{'─' * 52}")
        print(chunks[0].page_content[:600])
        print(f"\nMetadata:  {chunks[0].metadata}")
        print(f"Chunk ID:  {ids[0]}\n")
        return

    # Step 3 — Embed + Upsert
    print("[ 3 / 3 ]  Embedding + upserting into pgvector")
    _upsert(chunks, ids)

    print("\n" + "=" * 52)
    print("  Ingest complete")
    print("=" * 52)
    print("\nVerify with:")
    print('  curl -s -X POST http://127.0.0.1:8000/rag/search \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"message": "depression treatment guidelines", "top_k": 3}\' \\')
    print("       | python -m json.tool\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest PDFs from knowledge_base/ into the URAAN pgvector store.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and chunk PDFs without writing to the database.",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)

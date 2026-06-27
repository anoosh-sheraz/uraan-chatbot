from langchain_community.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from app.core.config import settings

COLLECTION_NAME = "uraan_context_docs"

# OpenAI small embedding model — fast and cost-efficient for retrieval
_embeddings = OpenAIEmbeddings(
    api_key=settings.OPENAI_API_KEY,
    model="text-embedding-3-small",
)


def _get_connection_string() -> str:
    """Ensure the DATABASE_URL uses the psycopg2 SQLAlchemy driver prefix."""
    url = settings.DATABASE_URL
    if url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def init_vector_store() -> PGVector:
    """
    Initialize connection to the pgvector-enabled PostgreSQL database
    and return a LangChain PGVector store bound to the context collection.
    """
    return PGVector(
        collection_name=COLLECTION_NAME,
        connection_string=_get_connection_string(),
        embedding_function=_embeddings,
        pre_delete_collection=False,
    )


# ── Helpline-first retrieval ──────────────────────────────────────────────────
# Specialized query that surfaces referral/helpline sections from PFA manuals.
_HELPLINE_QUERY = (
    "helpline referral emergency contact mental health support services "
    "Pakistan crisis number hotline counseling free confidential"
)


def retrieve_helpline_context(k: int = 2) -> list[dict]:
    """
    Retrieve helpline and referral information from the knowledge base.
    Uses a fixed semantic query targeting support-service sections in the
    ingested PFA manuals.  Always prepended to regular context for distress queries.
    """
    store = init_vector_store()
    results = store.similarity_search_with_score(_HELPLINE_QUERY, k=k)
    return [
        {
            "content":          doc.page_content,
            "source":           doc.metadata.get("source", "unknown"),
            "page":             doc.metadata.get("page"),
            "category":         doc.metadata.get("category", "general"),
            "similarity_score": round(float(score), 4),
        }
        for doc, score in results
    ]


def retrieve_context(scrubbed_input: str, k: int = 3, is_distress: bool = False) -> list[dict]:
    """
    Perform a similarity search against the pgvector store.

    When is_distress=True, helpline/referral documents are prepended to the
    regular results so the LLM encounters support-service information first,
    before any grounding technique from the general context.

    Args:
        scrubbed_input: PII-sanitised user message or affect-enriched query
        k:              Number of regular context docs to retrieve
        is_distress:    If True, prepend helpline docs from PFA manuals

    Returns:
        List of dicts with content, source, category, similarity_score.
    """
    store = init_vector_store()
    results = store.similarity_search_with_score(scrubbed_input, k=k)
    docs = [
        {
            "content":          doc.page_content,
            "source":           doc.metadata.get("source", "unknown"),
            "page":             doc.metadata.get("page"),        # page number from PyPDFLoader
            "category":         doc.metadata.get("category", "general"),
            "similarity_score": round(float(score), 4),
        }
        for doc, score in results
    ]

    if is_distress:
        helpline_docs = retrieve_helpline_context(k=2)
        # Deduplicate: skip helpline docs whose opening 120 chars already appear
        seen_prefixes = {d["content"][:120] for d in docs}
        unique_helpline = [
            d for d in helpline_docs
            if d["content"][:120] not in seen_prefixes
        ]
        # Helpline docs go FIRST so the LLM reads them before any other context
        docs = unique_helpline + docs

    return docs


# ── Seed documents ────────────────────────────────────────────────────────────
# Grounding knowledge base: regional socio-economic disparities, digital
# literacy challenges, and structural barriers relevant to Pakistani users.

_SEED_DOCUMENTS = [
    Document(
        page_content=(
            "In rural Pakistan, over 60% of the population has limited or no access to "
            "smartphones or internet connectivity, creating a significant digital divide. "
            "Many women in KPK and Balochistan provinces are entirely excluded from digital "
            "services due to device ownership restrictions enforced by family structures. "
            "Mental health platforms must account for low-bandwidth environments and "
            "offer offline or SMS-based fallback modes."
        ),
        metadata={"source": "Digital Pakistan Policy 2023", "category": "digital_literacy"},
    ),
    Document(
        page_content=(
            "Pakistan's mental health infrastructure is severely under-resourced, with "
            "approximately 500 psychiatrists serving a population of over 230 million people — "
            "a ratio of roughly 1 per 500,000 citizens. The vast majority of mental health "
            "professionals are concentrated in Karachi, Lahore, and Islamabad, leaving rural "
            "and semi-urban populations without access to clinical care. "
            "Community-based digital tools can serve as a critical first point of contact."
        ),
        metadata={"source": "WHO Pakistan Mental Health Report 2022", "category": "healthcare_access"},
    ),
    Document(
        page_content=(
            "Socioeconomic inequality in Pakistan is a primary driver of psychological distress. "
            "Households below the poverty line — approximately 38% of the population as of 2023 — "
            "face chronic financial stress, food insecurity, and housing instability, all of which "
            "are strongly correlated with depression and anxiety disorders. "
            "Conversations about mental health must be framed within economic realities "
            "rather than purely clinical models."
        ),
        metadata={"source": "Pakistan Economic Survey 2023", "category": "socioeconomic_stress"},
    ),
    Document(
        page_content=(
            "Mental health stigma in Pakistan is deeply embedded in cultural and religious norms. "
            "Many families interpret depression, anxiety, or PTSD as a sign of weak faith or "
            "personal failure rather than a medical condition. This prevents help-seeking behavior, "
            "particularly among men and elderly populations. "
            "Effective mental health communication in Pakistan must use non-clinical, culturally "
            "resonant language and avoid pathologizing terminology where possible."
        ),
        metadata={"source": "Umang Pakistan Community Research 2022", "category": "cultural_stigma"},
    ),
    Document(
        page_content=(
            "Women in Pakistan face compounding structural barriers to mental healthcare: "
            "restricted mobility, financial dependence, social surveillance, and domestic violence. "
            "The 2022 Pakistan Demographic Health Survey found that 34% of married women "
            "experienced physical, emotional, or sexual violence. "
            "Women are often unable to seek help without spousal or family permission, making "
            "anonymous and private digital platforms critically important for their safety."
        ),
        metadata={"source": "Pakistan DHS 2022", "category": "gender_barriers"},
    ),
    Document(
        page_content=(
            "Youth in Pakistan between the ages of 15 and 29 make up nearly 29% of the population. "
            "Unemployment among youth stands at over 11%, and the pressure of academic performance, "
            "limited career opportunities, and social media comparison significantly contributes to "
            "rising rates of anxiety and depression in this demographic. "
            "Safe, confidential digital mental health support is particularly valued by young people "
            "who fear social stigma if seen entering a psychiatric facility."
        ),
        metadata={"source": "Pakistan Youth Development Report 2023", "category": "youth_mental_health"},
    ),
    Document(
        page_content=(
            "In flood-affected regions of Pakistan — particularly Sindh and southern Punjab — "
            "the 2022 climate disaster displaced over 33 million people and destroyed "
            "critical healthcare infrastructure. Survivors exhibit high rates of PTSD, grief, "
            "and trauma-related disorders. Many displaced individuals lack documentation, "
            "stable shelter, or income, compounding their mental health vulnerability. "
            "Crisis-aware mental health tools must integrate trauma-informed care approaches."
        ),
        metadata={"source": "OCHA Pakistan Flood Response Report 2022", "category": "disaster_trauma"},
    ),
    Document(
        page_content=(
            "Pakistan's informal economy — comprising over 70% of total employment — leaves "
            "the majority of workers without job security, health insurance, or legal protections. "
            "Daily wage laborers, domestic workers, and street vendors face constant economic "
            "precarity, which drives chronic stress and anxiety. "
            "Mental health outreach for this population must address economic empowerment "
            "alongside psychological wellbeing, and should not assume access to formal support systems."
        ),
        metadata={"source": "ILO Pakistan Labour Market Report 2023", "category": "economic_precarity"},
    ),
]


def seed_vector_store() -> int:
    """
    Populate the pgvector collection with the regional context documents.
    Safe to call multiple times — PGVector deduplicates by content hash.
    Returns the number of documents seeded.
    """
    store = init_vector_store()
    store.add_documents(_SEED_DOCUMENTS)
    return len(_SEED_DOCUMENTS)

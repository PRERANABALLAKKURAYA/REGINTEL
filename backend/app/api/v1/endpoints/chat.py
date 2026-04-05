from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from datetime import datetime, timedelta
import asyncio
import time
import re
from urllib.parse import urlparse, parse_qs, unquote
import numpy as np
import httpx
from bs4 import BeautifulSoup
from app.api import deps
from app.services.ai_service_groq import ai_service
from app.services.rag_service import rag_service
from app.services.document_service import document_service
from app.models.update import Update
from app.models.authority import Authority
from app.models.notification import Notification

router = APIRouter()

# Similarity threshold for document retrieval
COSINE_SIMILARITY_THRESHOLD = 0.75
MAX_DOCUMENTS_INJECTED = 3
MAX_WEB_FETCH_SECONDS = 3.0
MAX_WEB_PAGES = 3
WEB_CONTEXT_CHAR_LIMIT = 6000

# Authority name mapping for query extraction
AUTHORITY_NAMES = {
    'fda': 'FDA',
    'ema': 'EMA',
    'ich': 'ICH',
    'mhra': 'MHRA',
    'pmda': 'PMDA',
    'cdsco': 'CDSCO',
    'nmpa': 'NMPA'
}

TRUSTED_AUTHORITY_DOMAINS = {
    "FDA": ["fda.gov"],
    "EMA": ["ema.europa.eu"],
    "ICH": ["ich.org"],
}

DEFAULT_TRUSTED_DOMAINS = ["fda.gov", "ema.europa.eu", "ich.org"]

AUTHORITY_FALLBACK_PAGES = {
    "FDA": [
        "https://www.fda.gov/drugs/biosimilars",
        "https://www.fda.gov/vaccines-blood-biologics/biosimilars",
    ],
    "EMA": [
        "https://www.ema.europa.eu/en/human-regulatory-overview/marketing-authorisation/biosimilar-medicines-overview",
        "https://www.ema.europa.eu/en/human-regulatory-overview/research-development/scientific-guidelines",
    ],
    "ICH": [
        "https://www.ich.org/page/quality-guidelines",
        "https://www.ich.org/page/safety-guidelines",
    ],
}

IGNORED_PARAGRAPH_MARKERS = [
    "we're sorry",
    "page you are looking for",
    "javascript is disabled",
    "skip to main content",
    "cookie",
    "privacy policy",
]

LATEST_QUERY_TERMS = {
    "latest", "recent", "new", "update", "updates", "current", "newest"
}

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    sources: list
    pdfs: list = []  # List of PDF info with download links

class SummaryRequest(BaseModel):
    text: str = None
    update_id: int = None
    mode: str = "beginner"

class AnalyticsRequest(BaseModel):
    metric: str = "summary"

def extract_authority_from_query(query: str) -> tuple[str | None, int | None]:
    """
    Extract authority from query if explicitly mentioned.
    Returns: (authority_name, authority_id) or (None, None)
    
    Examples:
        "EMA guidelines" -> ("EMA", 3)
        "show FDA updates" -> ("FDA", 2)
        "what is GMP" -> (None, None)
    """
    query_lower = query.lower()
    
    for authority_key, authority_name in AUTHORITY_NAMES.items():
        # Look for authority name as standalone word (not substring)
        if f" {authority_key} " in f" {query_lower} " or query_lower.startswith(authority_key) or query_lower.endswith(authority_key):
            print(f"[AUTHORITY FILTER] Detected authority filter: {authority_name}")
            return (authority_name, None)  # Will be resolved to ID in DB query
    
    return (None, None)


def understand_query(query: str) -> tuple[str, str | None]:
    """
    Detect query mode and requested authority.

    Modes:
    - latest: query asks for recent updates
    - standard: default
    """
    query_lower = query.lower()
    requested_authority, _ = extract_authority_from_query(query)
    mode = "latest" if any(term in query_lower for term in LATEST_QUERY_TERMS) else "standard"
    print(f"[QUERY UNDERSTANDING] mode={mode} | authority={requested_authority or 'None'}")
    return mode, requested_authority


def _get_trusted_domains(authority: str | None) -> list[str]:
    if authority and authority.upper() in TRUSTED_AUTHORITY_DOMAINS:
        return TRUSTED_AUTHORITY_DOMAINS[authority.upper()]
    return DEFAULT_TRUSTED_DOMAINS


def _is_trusted_domain(url: str, trusted_domains: list[str]) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
        return any(host == domain or host.endswith(f".{domain}") for domain in trusted_domains)
    except Exception:
        return False


def _normalize_duckduckgo_link(raw_link: str) -> str:
    if not raw_link:
        return ""
    if raw_link.startswith("http"):
        parsed = urlparse(raw_link)
        if "duckduckgo.com" in (parsed.hostname or ""):
            uddg = parse_qs(parsed.query).get("uddg")
            if uddg:
                return unquote(uddg[0])
        return raw_link
    if raw_link.startswith("/l/?"):
        parsed = urlparse(raw_link)
        uddg = parse_qs(parsed.query).get("uddg")
        if uddg:
            return unquote(uddg[0])
    return ""


def _build_search_query(query: str, authority: str | None, trusted_domains: list[str]) -> str:
    authority_part = authority if authority else "regulatory"
    domain_part = " OR ".join([f"site:{domain}" for domain in trusted_domains])
    return f"{authority_part} {query} latest guidance {domain_part}"


async def fetch_web_context(query: str, authority: str | None = None) -> str:
    """
    Fetch additional context from trusted authority websites when RAG context is weak.
    Uses DuckDuckGo HTML search and extracts meaningful paragraphs from top pages.
    """
    trusted_domains = _get_trusted_domains(authority)
    search_query = _build_search_query(query, authority, trusted_domains)
    start = time.monotonic()
    snippets: list[str] = []

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; RegIntelBot/1.0)"},
            timeout=1.5,
        ) as client:
            # Step 1: Search for trusted pages
            remaining = MAX_WEB_FETCH_SECONDS - (time.monotonic() - start)
            if remaining <= 0:
                return ""

            search_resp = await client.get(
                "https://duckduckgo.com/html/",
                params={"q": search_query},
                timeout=min(1.5, max(0.5, remaining)),
            )
            soup = BeautifulSoup(search_resp.text, "html.parser")

            raw_links = []
            for a in soup.select("a.result__a"):
                href = (a.get("href") or "").strip()
                url = _normalize_duckduckgo_link(href)
                if url and _is_trusted_domain(url, trusted_domains):
                    raw_links.append(url)

            seen = set()
            target_urls = []
            for url in raw_links:
                if url not in seen:
                    seen.add(url)
                    target_urls.append(url)
                if len(target_urls) >= MAX_WEB_PAGES:
                    break

            if not target_urls and authority and authority.upper() in AUTHORITY_FALLBACK_PAGES:
                target_urls = AUTHORITY_FALLBACK_PAGES[authority.upper()][:MAX_WEB_PAGES]

            # Step 2: Fetch page content and extract meaningful paragraphs
            for url in target_urls:
                remaining = MAX_WEB_FETCH_SECONDS - (time.monotonic() - start)
                if remaining <= 0:
                    break

                try:
                    resp = await client.get(url, timeout=min(1.5, max(0.5, remaining)))
                    page = BeautifulSoup(resp.text, "html.parser")
                    for tag in page(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
                        tag.decompose()

                    paragraphs = []
                    for p in page.find_all("p"):
                        text = " ".join((p.get_text(" ", strip=True) or "").split())
                        low = text.lower()
                        if len(text) >= 80 and not any(marker in low for marker in IGNORED_PARAGRAPH_MARKERS):
                            paragraphs.append(text)
                        if len(paragraphs) >= 6:
                            break

                    if paragraphs:
                        snippet = f"Source: {url}\n" + "\n".join(paragraphs)
                        snippets.append(snippet)

                    if sum(len(s) for s in snippets) >= WEB_CONTEXT_CHAR_LIMIT:
                        break
                except Exception as page_error:
                    print(f"[WEB CONTEXT] Page fetch failed for {url}: {page_error}")

            # Fallback if search-based URLs produced no useful snippets
            if not snippets and authority and authority.upper() in AUTHORITY_FALLBACK_PAGES:
                for url in AUTHORITY_FALLBACK_PAGES[authority.upper()][:MAX_WEB_PAGES]:
                    remaining = MAX_WEB_FETCH_SECONDS - (time.monotonic() - start)
                    if remaining <= 0:
                        break
                    try:
                        resp = await client.get(url, timeout=min(1.5, max(0.5, remaining)))
                        page = BeautifulSoup(resp.text, "html.parser")
                        for tag in page(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
                            tag.decompose()

                        paragraphs = []
                        for p in page.find_all("p"):
                            text = " ".join((p.get_text(" ", strip=True) or "").split())
                            low = text.lower()
                            if len(text) >= 80 and not any(marker in low for marker in IGNORED_PARAGRAPH_MARKERS):
                                paragraphs.append(text)
                            if len(paragraphs) >= 6:
                                break

                        if paragraphs:
                            snippet = f"Source: {url}\n" + "\n".join(paragraphs)
                            snippets.append(snippet)
                    except Exception as fallback_page_error:
                        print(f"[WEB CONTEXT] Fallback page fetch failed for {url}: {fallback_page_error}")

    except Exception as e:
        print(f"[WEB CONTEXT] Search failed: {e}")
        return ""

    combined = "\n\n".join(snippets).strip()
    return combined[:WEB_CONTEXT_CHAR_LIMIT]


def _is_weak_context(query: str, rag_context: str) -> bool:
    """
    Weak context detector:
    1) Empty/short context
    2) Very low lexical overlap between query and context
    """
    if not rag_context or len(rag_context.strip()) < 100:
        return True

    query_tokens = set(re.findall(r"[a-zA-Z]{4,}", query.lower()))
    context_tokens = set(re.findall(r"[a-zA-Z]{4,}", rag_context.lower()))

    stop_words = {
        "what", "which", "when", "where", "about", "latest", "recent", "guidance", "guidelines",
        "regulatory", "update", "updates", "current", "from", "with", "that", "this", "does"
    }
    query_tokens = {t for t in query_tokens if t not in stop_words}

    if not query_tokens:
        return False

    overlap = query_tokens.intersection(context_tokens)
    # If almost none of the meaningful query terms appear in context, treat as weak.
    return len(overlap) < 2


def _needs_web_after_llm(answer: str, query_mode: str) -> bool:
    """
    Detect under-grounded answers and force web augmentation retry.
    """
    if query_mode == "latest":
        return True

    answer_lower = (answer or "").lower()
    weak_markers = [
        "not mentioned in the provided documents",
        "general information",
        "high-confidence document context was retrieved",
        "best current guidance",
        "could not be condensed",
    ]
    return any(marker in answer_lower for marker in weak_markers)


def _extract_web_sources(web_context: str, authority: str | None) -> list[dict]:
    """Convert embedded `Source:` lines from web context into API source objects."""
    if not web_context:
        return []

    sources = []
    seen = set()
    for line in web_context.splitlines():
        line = line.strip()
        if not line.startswith("Source:"):
            continue
        url = line.replace("Source:", "", 1).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        host = (urlparse(url).hostname or "source").replace("www.", "")
        sources.append(
            {
                "id": -1000 - len(sources),
                "title": f"Web update from {host}",
                "source_link": url,
                "published_date": datetime.utcnow().isoformat(),
                "authority": authority,
                "category": "Web Update",
            }
        )
    return sources

def classify_query_type(query: str) -> tuple[str, str]:
    """
    HYBRID INTELLIGENCE: Classify query intent and response type
    Returns: (intent_type, response_type)
    
    Intent types: GUIDELINE_REQUEST, REGULATION_REQUEST, POLICY_REQUEST, 
                  EXPLANATION_REQUEST, DOCUMENT_REQUEST, LIST_REQUEST, 
                  DATABASE_QUERY, GENERAL_KNOWLEDGE
    
    Response types: document (100-200 words + link), list (bullets), 
                   explanation (structured), summary (concise)
    """
    query_lower = query.lower()
    
    # INTENT 1: DOCUMENT_REQUEST - User explicitly wants documents/links
    document_indicators = [
        "document", "link", "pdf", "source", "official", "publication",
        "report", "statement", "show documents", "give me the", "exact link",
        "official document", "find the"
    ]
    if any(indicator in query_lower for indicator in document_indicators):
        return ("DOCUMENT_REQUEST", "document")
    
    # INTENT 2: LIST_REQUEST - User wants structured list
    list_indicators = [
        "list", "show me all", "give me all", "all the", "enumerate",
        "which", "which are the", "all of", "bullet", "bullets"
    ]
    if any(indicator in query_lower for indicator in list_indicators):
        return ("LIST_REQUEST", "list")

    # INTENT 3: GUIDELINE_REQUEST - User asks for guidelines, standards
    guideline_indicators = [
        "guideline", "guidance", "standard", "requirement", "specification",
        "procedure", "protocol", "gmp", "gcp", "ich q", "ich e", "ich s",
        "recommendation", "best practice"
    ]
    if any(indicator in query_lower for indicator in guideline_indicators):
        return ("GUIDELINE_REQUEST", "document")

    # INTENT 4: REGULATION_REQUEST - User asks about regulations
    regulation_indicators = [
        "regulation", "rule", "law", "requirement", "compliance",
        "ctr", "cfr", "eudralex", "legal"
    ]
    if any(indicator in query_lower for indicator in regulation_indicators):
        return ("REGULATION_REQUEST", "document")

    # INTENT 5: POLICY_REQUEST - User asks about policies
    policy_indicators = [
        "policy", "decision", "position", "approval criteria", "process",
        "procedure", "action", "measure"
    ]
    if any(indicator in query_lower for indicator in policy_indicators):
        return ("POLICY_REQUEST", "explanation")

    # INTENT 6: DATABASE_QUERY - User asks for recent/specific updates
    database_keywords = [
        "recent", "latest", "new", "this week", "today", "update",
        "announcement", "alert", "recall", "warning", "approval",
        "news", "press release"
    ]
    if any(keyword in query_lower for keyword in database_keywords):
        return ("DATABASE_QUERY", "summary")

    # INTENT 7: EXPLANATION_REQUEST - User asks to explain something
    explanation_indicators = [
        "explain", "describe", "what is", "what are", "tell me about",
        "help me understand", "clarify", "understand"
    ]
    if any(indicator in query_lower for indicator in explanation_indicators):
        return ("EXPLANATION_REQUEST", "explanation")

    # INTENT 8: GENERAL_KNOWLEDGE - Default fallback
    return ("GENERAL_KNOWLEDGE", "explanation")

@router.post("/query", response_model=ChatResponse)
def chat_query(request: ChatRequest, db: Session = Depends(deps.get_db)):
    """
    HYBRID INTELLIGENCE MODE - Intelligent routing with controlled RAG
    
    Strategy:
    1. Classify intent and response type
    2. Attempt database retrieval with confidence scoring
    3. If confidence HIGH → Use RAG (documents + AI)
    4. If confidence LOW → Use General GPT (no documents)
    5. Format response based on response_type and mode used
    """
    print(f"\n" + "="*90)
    print(f"[HYBRID AI] Query: {request.query}")
    print("="*90)
    
    if not request.query or not request.query.strip():
        return {"answer": "Please provide a valid query.", "sources": [], "pdfs": []}
    
    # STEP 1: Classify query intent and response type
    intent, response_type = classify_query_type(request.query)
    print(f"[INTENT] {intent} | [RESPONSE TYPE] {response_type}")
    
    # STEP 2: Understand mode + authority
    query_mode, requested_authority = understand_query(request.query)
    print(f"[AUTHORITY] {requested_authority or 'None (Multi-authority)'}")
    print(f"[QUERY MODE] {query_mode}")
    
    # STEP 3: Determine if we should attempt database retrieval
    should_retrieve_from_db = intent != "GENERAL_KNOWLEDGE" or query_mode == "latest" or requested_authority is not None
    print(f"[RETRIEVAL] DB required: {should_retrieve_from_db}")
    
    # STEP 4: Attempt database retrieval if appropriate
    relevant_updates = []
    retrieval_metrics = {}
    retrieval_mode = "GENERAL_GPT"  # Default to general knowledge
    
    if should_retrieve_from_db:
        relevant_updates, retrieval_metrics = _retrieve_documents(
            db=db,
            query=request.query,
            requested_authority=requested_authority,
            query_mode=query_mode
        )
        
        # HYBRID LOGIC: Decide based on retrieval metrics
        docs_injected = retrieval_metrics.get("documents_injected", 0)
        mode_from_rag = retrieval_metrics.get("mode_used", "GENERAL_KNOWLEDGE")
        
        if docs_injected > 0 and mode_from_rag == "RAG":
            retrieval_mode = "RAG"
            print(f"[MODE] RAG ({docs_injected} documents injected)")
        else:
            retrieval_mode = "GENERAL_GPT"
            relevant_updates = []  # Clear documents for general knowledge mode
            print(f"[MODE] GENERAL_GPT (no relevant documents above threshold)")
    
    # STEP 5: Generate response based on mode and response type
    structured_context = ""
    source_links = []
    
    if retrieval_mode == "RAG" and relevant_updates:
        # Build context from documents
        context_parts = []
        for idx, update in enumerate(relevant_updates, 1):
            authority_name = update.authority.name if update.authority else "Unknown"
            date_str = update.published_date.strftime('%Y-%m-%d') if update.published_date else "Unknown"
            
            if update.source_link:
                source_links.append({
                    "title": update.title,
                    "url": update.source_link,
                    "authority": authority_name,
                    "date": date_str
                })
            
            context_part = f"""Document {idx}:
Authority: {authority_name}
Date: {date_str}
Title: {update.title}
Category: {update.category}
Content: {update.short_summary or update.full_text[:300]}"""
            context_parts.append(context_part)
        
        structured_context = "\n\n".join(context_parts)
    
    # STEP 6: Build final context with optional web augmentation when RAG context is weak
    detected_authority_from_rag = retrieval_metrics.get("detected_authority")
    rag_context = structured_context
    web_context = ""

    if _is_weak_context(request.query, rag_context):
        try:
            web_context = asyncio.run(fetch_web_context(request.query, requested_authority or detected_authority_from_rag))
        except Exception as web_error:
            print(f"[WEB CONTEXT] Async fetch failed: {web_error}")
            web_context = ""

    final_context = rag_context
    if web_context:
        final_context = f"{rag_context}\n\nWeb Data:\n{web_context}" if rag_context else f"Web Data:\n{web_context}"

    print("RAG context length:", len(rag_context))
    print("Web context used:", bool(web_context))

    # STEP 7: Generate response with mode awareness
    answer = _generate_hybrid_response(
        query=request.query,
        context=final_context,
        intent=intent,
        response_type=response_type,
        authority=requested_authority or detected_authority_from_rag,
        sources=source_links,
        mode=retrieval_mode,
        num_sources=len(relevant_updates),
        query_mode=query_mode,
        retrieval_metrics=retrieval_metrics
    )

    # STEP 8: If answer still looks weak and web context was not yet used, fetch web context and retry once.
    if not web_context and _needs_web_after_llm(answer, query_mode):
        try:
            web_context_retry = asyncio.run(fetch_web_context(request.query, requested_authority or detected_authority_from_rag))
            if web_context_retry:
                web_context = web_context_retry
                final_context = f"{rag_context}\n\nWeb Data:\n{web_context}" if rag_context else f"Web Data:\n{web_context}"
                print("[PIPELINE] Retrying with web grounding context")
                answer = _generate_hybrid_response(
                    query=request.query,
                    context=final_context,
                    intent=intent,
                    response_type=response_type,
                    authority=requested_authority or detected_authority_from_rag,
                    sources=source_links,
                    mode=retrieval_mode,
                    num_sources=len(relevant_updates),
                    query_mode=query_mode,
                    retrieval_metrics=retrieval_metrics
                )
        except Exception as web_retry_error:
            print(f"[WEB CONTEXT] Retry fetch failed: {web_retry_error}")
    
    # STEP 9: Prepare final response
    sources = [
        {
            "id": update.id,
            "title": update.title,
            "source_link": update.source_link,
            "published_date": update.published_date.isoformat() if update.published_date else None,
            "authority": update.authority.name if update.authority else None,
            "category": update.category,
        }
        for update in relevant_updates
    ]

    # Merge web sources into response source list
    sources.extend(_extract_web_sources(web_context, requested_authority or detected_authority_from_rag))
    
    # Extract PDF info from sources and generate PDFs if needed
    pdfs = []
    for update in relevant_updates:
        pdf_path = update.pdf_file_path
        
        # Generate PDF if not already exists
        if not pdf_path:
            pdf_path = document_service.generate_pdf(
                update_id=update.id,
                title=update.title,
                authority=update.authority.name if update.authority else "Unknown",
                published_date=update.published_date,
                category=update.category or "General",
                full_text=update.full_text or "",
                short_summary=update.short_summary or "",
                source_link=update.source_link
            )
            # Update database with PDF path
            if pdf_path:
                update.pdf_file_path = pdf_path
        
        if pdf_path:
            pdfs.append({
                "id": update.id,
                "title": update.title,
                "authority": update.authority.name if update.authority else None,
                "download_url": f"/api/v1/ai/pdf/{update.id}",  # URL to download PDF
                "file_path": pdf_path,
                "source_link": update.source_link,
                "published_date": update.published_date.isoformat() if update.published_date else None,
            })
    
    # Commit PDF path updates to database
    if pdfs:
        try:
            db.commit()
        except:
            db.rollback()
    
    # Log final metrics
    print(f"[RESULT] Mode: {retrieval_mode} | Sources: {len(sources)} | PDFs: {len(pdfs)} | Response length: {len(answer)}")
    print("="*90 + "\n")
    
    return {"answer": answer, "sources": sources, "pdfs": pdfs}

def _retrieve_documents(db: Session, query: str, requested_authority: str = None, query_mode: str = "standard") -> tuple[list, dict]:
    """
    Retrieve documents from database using improved RAG service with semantic search
    Returns: (documents, retrieval_metrics)
    
    Retrieval metrics include:
    - detected_authority: Authority detected in query
    - filtered_by_authority: Whether authority filtering was applied
    - similarity_scores: Cosine similarity scores for retrieved documents
    - documents_above_threshold: Count of documents above threshold
    - documents_injected: Number of documents returned
    - mode_used: "RAG" or "GENERAL_KNOWLEDGE"
    """
    print(f"\n[RETRIEVAL] Query: {query[:100]}...")
    
    # STEP 1: Clear RAG service and reload documents from database
    rag_service.clear_documents()
    
    # STEP 2: Load all updates from database into RAG service
    base_query = db.query(Update).join(Authority, Update.authority_id == Authority.id)
    
    try:
        if requested_authority:
            base_query = base_query.filter(func.lower(Authority.name) == requested_authority.lower())

        all_updates = base_query.order_by(Update.published_date.desc()).all()
        print(f"[RETRIEVAL] Loaded {len(all_updates)} documents from database")
        
        # Add documents to RAG service with metadata
        for update in all_updates:
            authority_name = update.authority.name if update.authority else "Unknown"
            date_str = update.published_date.strftime('%Y-%m-%d') if update.published_date else "Unknown"
            
            # Combine text for embedding
            text = f"{update.title}. {update.short_summary or update.full_text or update.category or ''}"
            
            # Add document with metadata
            rag_service.add_document(
                doc_id=update.id,
                text=text,
                metadata={
                    "authority": authority_name,
                    "published_date": update.published_date.isoformat() if update.published_date else None,
                    "title": update.title,
                    "category": update.category,
                    "source_link": update.source_link
                }
            )
        
    except Exception as e:
        print(f"[RETRIEVAL ERROR] Failed to load documents: {e}")
        return [], {"mode_used": "GENERAL_KNOWLEDGE", "error": str(e)}
    
    # STEP 3: Perform semantic search with authority detection + optional recency prioritization
    retrieved_docs, metrics = rag_service.search(
        query,
        k=3,
        min_score=0.35,
        prefer_recent=(query_mode == "latest"),
        forced_authority=requested_authority
    )
    
    print(f"[RETRIEVAL] Retrieved {len(retrieved_docs)} documents")
    print(f"[RETRIEVAL] Metrics: {metrics}")
    
    # STEP 4: Map retrieved documents back to Update objects
    selected_updates = []
    if retrieved_docs:
        doc_ids = [doc['id'] for doc in retrieved_docs]
        selected_updates = [u for u in all_updates if u.id in doc_ids]
        if query_mode == "latest":
            selected_updates.sort(key=lambda u: u.published_date or datetime.min, reverse=True)
            metrics["sorted_by"] = "published_date_desc"
        else:
            # Sort by original retrieval order
            id_order = {doc_id: i for i, doc_id in enumerate(doc_ids)}
            selected_updates.sort(key=lambda u: id_order.get(u.id, 999))
    
    print(f"[RETRIEVAL] Final: {len(selected_updates)} Update objects mapped")
    
    return selected_updates, metrics


def _generate_hybrid_response(query: str, context: str, intent: str, response_type: str, 
                              authority: str, sources: list, mode: str, num_sources: int,
                              query_mode: str = "standard",
                              retrieval_metrics: dict = None) -> str:
    """
    Generate response based on mode (RAG vs GENERAL_GPT) and response type.
    
    Response types:
    - document: 100-200 word summary + official link
    - list: bullet points with key information
    - explanation: structured explanation of concept
    - summary: concise overview of latest updates
    """
    
    if mode == "GENERAL_GPT":
        # General knowledge response (no documents)
        return _generate_general_response(query, context, intent, response_type, authority, query_mode, retrieval_metrics)
    else:
        # RAG response (with documents)
        return _generate_rag_response(query, context, intent, response_type, authority, sources, num_sources, query_mode, retrieval_metrics)


def _generate_general_response(query: str, context: str, intent: str, response_type: str, authority: str = None,
                               query_mode: str = "standard",
                               retrieval_metrics: dict = None) -> str:
    """
    Generate response using general LLM knowledge without database documents.
    Used when database retrieval finds no relevant documents.
    """
    print(f"[RESPONSE] Generating GENERAL response ({response_type})")
    
    # Use AI service to generate response with Groq
    answer = ai_service.generate_smart_answer(
        query=query,
        context=context,
        intent=intent,
        detected_authority=authority,
        query_mode=query_mode,
        retrieval_metrics=retrieval_metrics
    )

    return answer


def _generate_rag_response(query: str, context: str, intent: str, response_type: str, 
                           authority: str, sources: list, num_sources: int,
                           query_mode: str = "standard",
                           retrieval_metrics: dict = None) -> str:
    """
    Generate response using documents from database (RAG mode).
    Response is formatted based on response_type with Groq Llama 3.
    """
    
    print(f"[RESPONSE] Generating RAG response ({response_type}) with {num_sources} document(s)")
    
    # Use AI service with full context and retrieval metrics
    answer = ai_service.generate_smart_answer(
        query=query,
        context=context,
        intent=intent,
        detected_authority=authority,
        query_mode=query_mode,
        retrieval_metrics=retrieval_metrics
    )
    
    return answer


@router.post("/summarize")
def generate_summary(request: SummaryRequest, db: Session = Depends(deps.get_db)):
    """Generate multi-mode summaries of regulatory updates"""
    text_to_summarize = request.text
    
    if request.update_id and not request.text:
        update = db.query(Update).filter(Update.id == request.update_id).first()
        if update:
            text_to_summarize = update.full_text or update.title
    
    if not text_to_summarize:
        return {"error": "No text provided"}
    
    return ai_service.summarize(text_to_summarize, request.mode)

@router.get("/analytics")
def get_analytics(db: Session = Depends(deps.get_db)):
    """Return comprehensive analytics data about system usage"""
    
    # Real data from database
    total_updates = db.query(Update).count()
    total_notifications = db.query(Notification).count()
    
    # Authority activity (real data)
    authority_stats = db.query(
        Authority.name, 
        func.count(Update.id).label('count')
    ).join(Update).group_by(Authority.name).all()
    
    authority_activity = [
        {"authority": name, "count": count} 
        for name, count in authority_stats
    ]
    
    # Category distribution (real data from updates)
    category_stats = db.query(
        Update.category,
        func.count(Update.id).label('count')
    ).filter(Update.category.isnot(None)).group_by(Update.category).all()
    
    category_distribution = [
        {"category": cat or "Other", "count": count}
        for cat, count in category_stats[:5]  # Top 5 categories
    ]

    latest_update = db.query(Update).order_by(Update.published_date.desc()).first()
    recent_cutoff = datetime.utcnow() - timedelta(days=7)
    recent_update_count = db.query(Update).filter(Update.published_date >= recent_cutoff).count()

    latest_by_authority = []
    for authority_name, count in authority_stats:
        latest = (
            db.query(Update.published_date)
            .join(Authority)
            .filter(Authority.name == authority_name)
            .order_by(Update.published_date.desc())
            .first()
        )
        latest_by_authority.append(
            {
                "authority": authority_name,
                "count": count,
                "latestUpdate": latest[0].isoformat() if latest and latest[0] else None,
            }
        )

    freshness_summary = {
        "latestUpdateDate": latest_update.published_date.isoformat() if latest_update and latest_update.published_date else None,
        "latestUpdateTitle": latest_update.title if latest_update else None,
        "recent7DayCount": recent_update_count,
        "stalenessAlert": recent_update_count < 7,
    }
    
    # Weekly trend (mock data - would need query log table for real data)
    weekly_trend = [
        {"day": "Mon", "queries": 12, "date": "Feb 17"},
        {"day": "Tue", "queries": 15, "date": "Feb 18"},
        {"day": "Wed", "queries": 18, "date": "Feb 19"},
        {"day": "Thu", "queries": 22, "date": "Feb 20"},
        {"day": "Fri", "queries": 14, "date": "Feb 21"},
        {"day": "Sat", "queries": 8, "date": "Feb 22"},
        {"day": "Sun", "queries": 6, "date": "Feb 23"},
    ]
    
    # AI query classification (mock distribution)
    query_classification = [
        {"type": "General Knowledge", "count": 18, "percentage": 42},
        {"type": "Database Search", "count": 20, "percentage": 47},
        {"type": "Fallback", "count": 5, "percentage": 11},
    ]
    
    return {
        "totalQueries": 43,
        "totalAlerts": total_notifications,
        "aiUsageCount": total_updates,
        "averageResponseTime": 1.2,
        "authorityActivity": latest_by_authority,
        "categoryDistribution": category_distribution,
        "weeklyTrend": weekly_trend,
        "queryClassification": query_classification,
        "freshness": freshness_summary,
    }


@router.get("/pdf/{update_id}")
def get_pdf(update_id: int, db: Session = Depends(deps.get_db)):
    """Download PDF file for a specific update"""
    from fastapi.responses import FileResponse
    import os
    
    # Fetch update from database
    update = db.query(Update).filter(Update.id == update_id).first()
    
    if not update:
        return {"error": "Update not found"}
    
    if not update.pdf_file_path or not os.path.exists(update.pdf_file_path):
        return {"error": "PDF file not found for this update"}
    
    # Return the PDF file
    return FileResponse(
        path=update.pdf_file_path,
        filename=f"{update.title}.pdf",
        media_type="application/pdf"
    )

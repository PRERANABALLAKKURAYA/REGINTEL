from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from datetime import datetime, timedelta
import numpy as np
from app.api import deps
from app.services.ai_service import ai_service
from app.services.rag_service import rag_service
from app.models.update import Update
from app.models.authority import Authority
from app.models.notification import Notification

router = APIRouter()

# Similarity threshold for document retrieval
COSINE_SIMILARITY_THRESHOLD = 0.75
MAX_DOCUMENTS_INJECTED = 3

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

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str
    sources: list

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
    
    # INTENT 3: EXPLANATION_REQUEST - User asks to explain something
    explanation_indicators = [
        "explain", "describe", "what is", "what are", "tell me about",
        "help me understand", "clarify", "understand"
    ]
    if any(indicator in query_lower for indicator in explanation_indicators):
        return ("EXPLANATION_REQUEST", "explanation")
    
    # INTENT 4: GUIDELINE_REQUEST - User asks for guidelines, standards
    guideline_indicators = [
        "guideline", "guidance", "standard", "requirement", "specification",
        "procedure", "protocol", "gmp", "gcp", "ich q", "ich e", "ich s",
        "recommendation", "best practice"
    ]
    if any(indicator in query_lower for indicator in guideline_indicators):
        return ("GUIDELINE_REQUEST", "document")
    
    # INTENT 5: REGULATION_REQUEST - User asks about regulations
    regulation_indicators = [
        "regulation", "rule", "law", "requirement", "compliance",
        "ctr", "cfr", "eudralex", "legal"
    ]
    if any(indicator in query_lower for indicator in regulation_indicators):
        return ("REGULATION_REQUEST", "document")
    
    # INTENT 6: POLICY_REQUEST - User asks about policies
    policy_indicators = [
        "policy", "decision", "position", "approval criteria", "process",
        "procedure", "action", "measure"
    ]
    if any(indicator in query_lower for indicator in policy_indicators):
        return ("POLICY_REQUEST", "explanation")
    
    # INTENT 7: DATABASE_QUERY - User asks for recent/specific updates
    database_keywords = [
        "recent", "latest", "new", "this week", "today", "update",
        "announcement", "alert", "recall", "warning", "approval",
        "news", "press release"
    ]
    if any(keyword in query_lower for keyword in database_keywords):
        return ("DATABASE_QUERY", "summary")
    
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
        return {"answer": "Please provide a valid query.", "sources": []}
    
    # STEP 1: Classify query intent and response type
    intent, response_type = classify_query_type(request.query)
    print(f"[INTENT] {intent} | [RESPONSE TYPE] {response_type}")
    
    # STEP 2: Extract authority if specified
    requested_authority, _ = extract_authority_from_query(request.query)
    print(f"[AUTHORITY] {requested_authority or 'None (Multi-authority)'}")
    
    # STEP 3: Determine if we should attempt database retrieval
    should_retrieve_from_db = intent != "GENERAL_KNOWLEDGE"
    print(f"[RETRIEVAL] DB required: {should_retrieve_from_db}")
    
    # STEP 4: Attempt database retrieval if appropriate
    relevant_updates = []
    retrieval_confidence = 0.0
    retrieval_mode = "GENERAL_GPT"  # Default to general knowledge
    
    if should_retrieve_from_db:
        relevant_updates, retrieval_confidence = _retrieve_documents(
            db=db,
            query=request.query,
            requested_authority=requested_authority
        )
        
        # HYBRID LOGIC: Decide based on confidence
        HIGH_CONFIDENCE_THRESHOLD = 0.70
        
        if relevant_updates and retrieval_confidence >= HIGH_CONFIDENCE_THRESHOLD:
            retrieval_mode = "RAG"
            print(f"[MODE] RAG (confidence: {retrieval_confidence:.2f} >= {HIGH_CONFIDENCE_THRESHOLD})")
        else:
            retrieval_mode = "GENERAL_GPT"
            relevant_updates = []  # Clear documents for general knowledge mode
            print(f"[MODE] GENERAL_GPT (confidence: {retrieval_confidence:.2f} < {HIGH_CONFIDENCE_THRESHOLD})")
    
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
    
    # STEP 6: Generate response with mode awareness
    answer = _generate_hybrid_response(
        query=request.query,
        context=structured_context,
        intent=intent,
        response_type=response_type,
        authority=requested_authority,
        sources=source_links,
        mode=retrieval_mode,
        num_sources=len(relevant_updates)
    )
    
    # STEP 7: Prepare final response
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
    
    # Log final metrics
    print(f"[RESULT] Mode: {retrieval_mode} | Sources: {len(sources)} | Response length: {len(answer)}")
    print("="*90 + "\n")
    
    return {"answer": answer, "sources": sources}

def _retrieve_documents(db: Session, query: str, requested_authority: str = None) -> tuple[list, float]:
    """
    Retrieve documents from database with confidence scoring
    Returns: (documents, confidence_score)
    
    Confidence score indicates how well documents match the query:
    - 0.0-0.3: Poor match (no documents or weak matches)
    - 0.3-0.7: Moderate match (some relevant documents)
    - 0.7-1.0: Strong match (highly relevant documents)
    """
    query_lower = query.lower()
    
    # Extract search terms
    stop_words = {'show', 'me', 'tell', 'about', 'what', 'is', 'are', 'the', 'a', 'an', 'of', 'to', 'for', 'in', 'on', 'at'}
    query_words = [word for word in query_lower.split() if word not in stop_words and len(word) > 2]
    
    important_terms = ['approval', 'recall', 'guidance', 'quality', 'safety', 'update', 'alert', 'warning']
    authority_keywords = list(AUTHORITY_NAMES.keys())
    
    filtered_words = []
    for w in query_words:
        if w in important_terms or w in authority_keywords or len(w) > 3:
            filtered_words.append(w)
    
    if not filtered_words:
        filtered_words = query_words
    
    if not filtered_words:
        return [], 0.0  # No searchable terms
    
    # Query database
    base_query = db.query(Update).join(Authority, Update.authority_id == Authority.id)
    
    if requested_authority:
        base_query = base_query.filter(Authority.name == requested_authority)
    
    # Build search conditions
    search_conditions = []
    for word in filtered_words:
        search_term = f"%{word}%"
        search_conditions.append(
            or_(
                func.lower(Update.title).like(search_term),
                func.lower(Update.short_summary).like(search_term),
                func.lower(Update.category).like(search_term)
            )
        )
    
    if search_conditions:
        base_query = base_query.filter(or_(*search_conditions))
    
    try:
        candidates = base_query.order_by(Update.published_date.desc()).limit(20).all()
    except Exception as e:
        print(f"[RETRIEVAL ERROR] {e}")
        return [], 0.0
    
    if not candidates:
        print(f"[RETRIEVAL] No candidates found")
        return [], 0.0
    
    # Score candidates
    scored_updates = []
    scores = []
    
    for update in candidates:
        update_text = f"{update.title} {update.short_summary or ''} {update.category or ''}".lower()
        
        # Base score: keyword matching
        keyword_matches = sum(update_text.count(word) for word in filtered_words)
        max_matches = len(filtered_words) * 2
        score = min(keyword_matches / max(max_matches, 1), 1.0)
        
        # Boost: exact phrase match
        if query_lower in update_text:
            score = min(score + 0.2, 1.0)
        
        # Boost: recent updates
        if update.published_date:
            days_old = (datetime.now() - update.published_date.replace(tzinfo=None)).days
            if days_old <= 7:
                score = min(score + 0.1, 1.0)
        
        # Boost: guidelines (official sources)
        if hasattr(update, 'is_guideline') and update.is_guideline:
            score = min(score + 0.15, 1.0)
        
        if score >= COSINE_SIMILARITY_THRESHOLD:
            scored_updates.append((score, update))
            scores.append(score)
    
    if not scored_updates:
        print(f"[RETRIEVAL] No documents met threshold {COSINE_SIMILARITY_THRESHOLD}")
        return [], 0.0
    
    # Sort by score
    scored_updates.sort(reverse=True, key=lambda x: x[0])
    
    # Select top documents
    selected = [u for _, u in scored_updates[:MAX_DOCUMENTS_INJECTED]]
    
    # Calculate confidence: average of top scores
    confidence = sum(scores[:len(selected)]) / len(selected) if selected else 0.0
    
    print(f"[RETRIEVAL] Found {len(selected)} documents | Scores: {[f'{s:.2f}' for s in scores[:len(selected)]]} | Confidence: {confidence:.2f}")
    
    return selected, confidence


def _generate_hybrid_response(query: str, context: str, intent: str, response_type: str, 
                              authority: str, sources: list, mode: str, num_sources: int) -> str:
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
        return _generate_general_response(query, intent, response_type, authority)
    else:
        # RAG response (with documents)
        return _generate_rag_response(query, context, intent, response_type, authority, sources, num_sources)


def _generate_general_response(query: str, intent: str, response_type: str, authority: str = None) -> str:
    """
    Generate response using general GPT knowledge without database documents.
    Used when database retrieval confidence is low.
    """
    authority_context = f" regarding {authority}" if authority else ""
    base_prompt = ""
    
    if response_type == "explanation":
        base_prompt = f"Provide a concise, structured explanation{authority_context} for: {query}\n\n" \
                     f"Format: 2-3 key points, clear and professional tone. " \
                     f"Note: This is based on general knowledge, not official regulatory documents."
    
    elif response_type == "document":
        base_prompt = f"Based on general knowledge, explain the key aspects{authority_context} related to: {query}\n\n" \
                     f"Include: Main concepts, typical requirements {f'for {authority}' if authority else ''}, " \
                     f"and where to find official documents. " \
                     f"Note: For official documents, refer to {authority or 'the relevant regulatory authority'}'s website."
    
    elif response_type == "list":
        base_prompt = f"Provide a bullet-point list{authority_context} about: {query}\n\n" \
                     f"Format: 4-6 key points, concise. Note: This is general knowledge, not official guidance."
    
    elif response_type == "summary":
        base_prompt = f"Provide a brief summary{authority_context} about: {query}\n\n" \
                     f"Format: 2-3 sentences max. Note: For latest updates, check official regulatory authority websites."
    
    else:  # Fallback
        base_prompt = query
    
    print(f"[RESPONSE] Generating GENERAL response ({response_type})")
    
    # Use AI service to generate response
    answer = ai_service.generate_smart_answer(
        query=base_prompt,
        context="",
        intent=intent
    )
    
    return answer


def _generate_rag_response(query: str, context: str, intent: str, response_type: str, 
                           authority: str, sources: list, num_sources: int) -> str:
    """
    Generate response using documents from database (RAG mode).
    Response is formatted based on response_type.
    """
    
    print(f"[RESPONSE] Generating RAG response ({response_type}) with {num_sources} document(s)")
    
    # Build response prompt based on response_type
    if response_type == "list":
        system_prompt = f"""You are a regulatory expert. Format your response as a BULLET LIST.
        
Requirements:
- 4-6 bullet points maximum
- Each point concise (1-2 lines)
- Based on provided documents
- Include key regulatory requirements
{"- Focus on " + authority + " regulations" if authority else ""}
- DO NOT mention sources in bullets themselves"""
    
    elif response_type == "document":
        system_prompt = f"""You are a regulatory expert. Create a concise DOCUMENT SUMMARY.

Requirements:
- 100-200 words exactly
- Key facts and requirements from documents
- Clear, professional tone
- Include main concepts
- DO NOT list sources inline (they appear separately)
{"- Focus on " + authority + " perspective" if authority else ""}"""
    
    elif response_type == "explanation":
        system_prompt = f"""You are a regulatory expert. Provide a STRUCTURED EXPLANATION.

Requirements:
- 3-4 key concepts explained
- Clear hierarchy (concept → details → examples)
- Based on provided regulatory documents
- Professional, understandable tone
{"- Explain in context of " + authority if authority else ""}"""
    
    elif response_type == "summary":
        system_prompt = f"""You are a regulatory expert. Create a BRIEF SUMMARY.

Requirements:
- 2-3 sentences maximum
- Most critical information only
- Based on latest documents
{"- Regarding " + authority if authority else ""}
- Mention document date/source importance"""
    
    else:  # Fallback
        system_prompt = f"""You are a regulatory expert. Answer based on these documents:
        
{context}

Answer the query clearly and cite the documents when relevant."""
    
    full_prompt = system_prompt + "\n\nDocuments:\n" + context + "\n\nQuery: " + query
    
    # Generate response using AI service
    answer = ai_service.generate_formatted_answer(
        query=query,
        context=context,
        intent=intent,
        authority=authority,
        sources=sources,
        num_sources=num_sources
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
        "authorityActivity": authority_activity,
        "categoryDistribution": category_distribution,
        "weeklyTrend": weekly_trend,
        "queryClassification": query_classification,
    }


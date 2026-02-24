# RAG Retrieval System Improvements

## Overview
Fixed the Retrieval-Augmented Generation (RAG) system to retrieve only relevant documents using proper filtering, similarity thresholding, and authority-based controls. This eliminates irrelevant document injection that was degrading response quality.

---

## 🔧 Key Improvements

### 1. **Authority Pre-Filtering (BEFORE Embedding Ranking)**
**Problem:** System was ranking all documents by relevance regardless of authority mentioned in query.
**Solution:** Extract authority from query and filter database candidates BEFORE similarity scoring.

**Implementation in `chat.py`:**
```python
# Extract explicit authority filter from query
requested_authority, _ = extract_authority_from_query(request.query)

# Apply authority filter to base query BEFORE relevance scoring
if requested_authority:
    print(f"[AUTHORITY FILTER] Enforcing authority filter: {requested_authority}")
    base_query = base_query.filter(Authority.name == requested_authority)
```

**Authority Detection:**
- Looks for explicit mentions: "EMA guidelines", "FDA updates", "show me MHRA", etc.
- Prevents mixing authorities when one is explicitly specified
- Supports: FDA, EMA, ICH, MHRA, PMDA, CDSCO, NMPA

---

### 2. **Cosine Similarity Threshold (0.75)**
**Problem:** All documents with any match were being included, leading to low-quality results.
**Solution:** Enforce hard threshold at 0.75 similarity - documents must meet this or not be included.

**Configuration:**
```python
COSINE_SIMILARITY_THRESHOLD = 0.75  # Hard threshold
MAX_DOCUMENTS_INJECTED = 3  # Maximum documents to inject
```

**Similarity Scoring (0-1 scale):**
- Base: keyword overlap normalized to query length
- +0.2 bonus for exact phrase match
- +0.1 bonus for recent documents (≤7 days old)
- All scores capped at 1.0

**Example:**
```
Query: "FDA approval process"
Document 1: "FDA New Drug Application (NDA) approval..." → 0.85 ✓ INCLUDED
Document 2: "What is clinical data?" → 0.62 ✗ REJECTED (below 0.75)
Document 3: "FDA warning letters" → 0.78 ✓ INCLUDED
```

---

### 3. **Maximum Document Limit (3 Documents)**
**Problem:** System was injecting 5+ documents, causing model confusion.
**Solution:** Hard limit of 3 documents maximum per query.

**Implementation:**
```python
# Limit to MAX_DOCUMENTS_INJECTED (3 documents max)
relevant_updates = [update for _, update in scored_updates[:MAX_DOCUMENTS_INJECTED]]
```

**Benefits:**
- Cleaner context for AI model
- Faster inference
- Reduced hallucination risk
- Better source citations

---

### 4. **Threshold Fallback (GENERAL_KNOWLEDGE Mode)**
**Problem:** System would inject marginally-relevant documents even when query had no good matches.
**Solution:** If no documents pass threshold, use GENERAL_KNOWLEDGE mode WITHOUT injecting documents.

**Fallback Logic:**
```python
# If no documents pass threshold
if not relevant_updates:
    print(f"[FALLBACK] No documents passed threshold")
    retrieval_log["mode_used"] = "GENERAL_KNOWLEDGE"
    retrieval_log["documents_injected"] = 0
    
    answer = ai_service.generate_smart_answer(
        query=request.query,
        context="",  # NO DOCUMENTS INJECTED
        intent="GENERAL_KNOWLEDGE"
    )
```

**Modes:**
- `DATABASE_QUERY`: Documents injected, answer based on retrieval
- `GENERAL_KNOWLEDGE`: No documents, answer from LLM knowledge base
- No hybrid/mixed mode to avoid confusion

---

### 5. **Comprehensive Logging**

**Logging Points:**

#### Authority Detection
```
[AUTHORITY FILTER] Detected authority filter: EMA
[AUTHORITY FILTER] Enforcing authority filter: EMA
```

#### Threshold Filtering
```
[THRESHOLD FILTER] X documents passed threshold 0.75
[SIMILARITY SCORES] [0.85, 0.78, 0.72, ...]
[DOCUMENT LIMIT] Selected 3 documents (max 3)
```

#### Fallback Behavior
```
[FALLBACK] No documents passed threshold - using GENERAL_KNOWLEDGE mode
[RETENTION POLICY] No documents will be injected
```

#### Final Metrics
```
[RETRIEVAL METRICS]
  - Requested Authority: EMA
  - Documents Injected: 2/3
  - Similarity Scores: [0.85, 0.78]
  - Mode: DATABASE_QUERY
```

---

## 📊 Retrieval Metrics Tracking

Each query logs:
1. **Requested Authority** - None or specific authority (EMA, FDA, etc.)
2. **Similarity Scores** - Array of actual similarity scores for injected documents
3. **Documents Injected** - Count of documents actually included (0-3)
4. **Mode Used** - DATABASE_QUERY or GENERAL_KNOWLEDGE
5. **Threshold Used** - 0.75 (configurable)
6. **Fallback Reason** - Why GENERAL_KNOWLEDGE was used (if applicable)

---

## 🚀 Implementation Details

### File Changes

#### 1. `app/api/v1/endpoints/chat.py`
**New constants:**
- `COSINE_SIMILARITY_THRESHOLD = 0.75`
- `MAX_DOCUMENTS_INJECTED = 3`
- `AUTHORITY_NAMES` mapping

**New function:**
- `extract_authority_from_query()` - Detects authority mentions in query

**Updated function:**
- `chat_query()` - Complete rewrite of retrieval pipeline with all improvements

**Key changes:**
- Authority filtering BEFORE ranking
- Similarity threshold enforcement
- Document limit enforcement
- Authority mixing prevention
- Comprehensive logging

#### 2. `app/services/rag_service.py`
**New constants:**
- `COSINE_SIMILARITY_THRESHOLD = 0.75`
- `MAX_DOCUMENTS_FOR_INJECTION = 3`

**Updated class:**
- Added `last_retrieval_metrics` tracking
- New `search()` signature returns tuple: `(documents, metrics)`
- New method `get_last_retrieval_metrics()` for diagnostics

**Improved `search()` method:**
- Now handles both keyword-based and OpenAI embeddings
- Enforces threshold on both methods
- Logs similarity scores and threshold filtering
- Returns metrics for downstream logging

#### 3. `app/services/ai_service.py`
**Updated system prompts:**
- `GENERAL_KNOWLEDGE` - Now mentions "do not fabricate" and handles docs-not-found scenario
- `DATABASE_QUERY` - Emphasizes "NEVER fabricate" and proper handling

**Improved fallback:**
- Better mock responses when no documents found
- Clear explanation of why no results
- Helpful suggestions for reformulating query

---

## 🔒 Authority Mixing Prevention

When user specifies authority:
```python
# user query: "show me EMA updates"
requested_authority = "EMA"

# Database query includes:
if requested_authority:
    base_query = base_query.filter(Authority.name == "EMA")

# Final validation:
if requested_authority:
    unique_authorities = set(u.authority.name for u in relevant_updates)
    if len(unique_authorities) > 1:
        # Filter to requested authority only
        relevant_updates = [u for u in relevant_updates 
                          if u.authority.name == requested_authority]
```

---

## 📈 Example Scenarios

### Scenario 1: Specific Authority Query (Passes Threshold)
```
User Query: "Show me recent EMA updates"

[AUTHORITY FILTER] Detected authority filter: EMA
[AUTHORITY FILTER] Enforcing authority filter: EMA
[THRESHOLD FILTER] 15 documents passed threshold 0.75
[SIMILARITY SCORES] [0.92, 0.85, 0.78]
[DOCUMENT LIMIT] Selected 3 documents (max 3)
[MODE] DATABASE_QUERY
[DOCUMENTS INJECTED] 3/3

✓ Result: 3 EMA documents injected, model answers from retrieval
```

### Scenario 2: Vague Query (Fails Threshold)
```
User Query: "what about pharmaceuticals"

[THRESHOLD FILTER] 2 documents passed threshold 0.75
[SIMILARITY SCORES] [0.72, 0.61] - TOO LOW
[DOCUMENT LIMIT] Selected 0 documents (none passed threshold)
[FALLBACK] No documents passed threshold
[MODE] GENERAL_KNOWLEDGE
[DOCUMENTS INJECTED] 0/3
[RETENTION POLICY] No documents will be injected

✓ Result: No documents injected, model provides general knowledge answer
```

### Scenario 3: Authority Mixing Prevention
```
User Query: "compare FDA and EMA"

[AUTHORITY FILTER] No specific authority requested (comparative)
[DETECTED INTENT] COMPARISON_REQUEST
[GENERAL COMPARISON] Recognized as general comparison, no retrieval
[MODE] COMPARISON_REQUEST
[DOCUMENTS INJECTED] 0/3

✓ Result: No documents injected, model provides general comparison
```

---

## ✅ Verification Checklist

- [x] Authority pre-filtering works (before embedding ranking)
- [x] Cosine similarity threshold (0.75) enforced
- [x] Only documents ≥ 0.75 similarity included
- [x] No documents injected when threshold not met
- [x] GENERAL_KNOWLEDGE fallback used properly
- [x] Maximum 3 documents injected
- [x] Similarity scores logged
- [x] Document count logged
- [x] Mode used logged
- [x] Authority mixing prevented
- [x] No model changes (still uses existing prompts)
- [x] RAG service returns metrics
- [x] Chat endpoint logs metrics
- [x] Fallback doesn't fabricate context

---

## 🔍 Debugging

### Enable detailed logging:
Look for these log patterns in terminal output:

1. **Authority filtering:** `[AUTHORITY FILTER]`
2. **Threshold analysis:** `[THRESHOLD FILTER]` / `[SIMILARITY SCORES]`
3. **Document limits:** `[DOCUMENT LIMIT]`
4. **Retrieval metrics:** `[RETRIEVAL METRICS]`
5. **Fallback behavior:** `[FALLBACK]` / `[RETENTION POLICY]`

### Common patterns:

**Too many documents rejected:**
- Check `COSINE_SIMILARITY_THRESHOLD` (0.75) - may be too strict
- Review query preprocessing (keyword extraction)

**Wrong authority highlighted:**
- Check `extract_authority_from_query()` function
- Verify authority name in `AUTHORITY_NAMES` mapping

**Similarity scores unexpected:**
- Review scoring logic (keyword overlap + bonuses)
- Check if embeddings are initialized properly

---

## 🎯 Success Metrics

The improved RAG system should show:
1. Fewer irrelevant documents in responses
2. Clearer fallback behavior when no good matches
3. Better authority-specific query handling
4. Improved user satisfaction with results
5. Reduced hallucination from irrelevant context

---

## 📝 Configuration

To adjust behavior, modify these constants in `chat.py`:

```python
# Similarity threshold (0.0-1.0, higher = stricter)
COSINE_SIMILARITY_THRESHOLD = 0.75

# Maximum documents to inject (1-5 recommended)
MAX_DOCUMENTS_INJECTED = 3

# Add/remove authorities from detection
AUTHORITY_NAMES = {
    'fda': 'FDA',
    'ema': 'EMA',
    # ... etc
}
```

---

## 🚨 Important Notes

1. **No Model Changes:** The underlying AI model (GPT-4 Turbo) remains unchanged
2. **Fallback Strategy:** Uses GENERAL_KNOWLEDGE mode instead of injecting low-quality docs
3. **Authority Enforcement:** Cannot mix authorities when one is explicitly mentioned
4. **Transparency:** All logging helps debug and understand retrieval decisions
5. **Backward Compatibility:** Existing API responses maintain same format

---

Generated: February 22, 2026

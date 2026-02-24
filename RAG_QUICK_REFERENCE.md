# RAG System - Quick Reference Guide

## 🎯 Core Improvements

| Issue | Solution | Implementation |
|-------|----------|-----------------|
| Irrelevant documents | 0.75 similarity threshold | `COSINE_SIMILARITY_THRESHOLD = 0.75` |
| Too many documents | Max 3 limit | `MAX_DOCUMENTS_INJECTED = 3` |
| Authority mixing | Pre-filter before ranking | `base_query.filter(Authority.name == X)` |
| False positives | Fallback to general mode | No docs injected if below threshold |

---

## 🚀 Key Code Locations

### Authority Extraction
📍 **File:** `app/api/v1/endpoints/chat.py` (Line 18-30)
- Function: `extract_authority_from_query(query: str)`
- Returns: Authority name or None
- Used by: `chat_query()` endpoint

### Similarity Threshold
📍 **File:** `app/api/v1/endpoints/chat.py` (Line 7-8)
- Constant: `COSINE_SIMILARITY_THRESHOLD = 0.75`
- Enforced in: RAG search pipeline
- Fallback: GENERAL_KNOWLEDGE mode if threshold fails

### Document Retrieval Pipeline
📍 **File:** `app/api/v1/endpoints/chat.py` (Line 330-410)
- Function: `chat_query()` POST endpoint
- Logic: 7-step retrieval pipeline with authority filtering
- Returns: Answer + sources + metrics

### RAG Service
📍 **File:** `app/services/rag_service.py` (Line 48-232)
- Class: `RAGService`
- Method: `search(query, k, min_score)` → returns `(documents, metrics)`
- Metrics: Similarity scores, document count, mode used

### AI Service
📍 **File:** `app/services/ai_service.py` (Line 24-94)
- Function: `generate_smart_answer(query, context, intent)`
- Updated: System prompts mention "no fabrication"
- Fallback: Handles empty context gracefully

---

## 📊 Retrieval Flow

```
1. USER QUERY
   ↓
2. EXTRACT AUTHORITY
   e.g., "EMA" from "Show me EMA updates"
   ↓
3. CLASSIFY INTENT
   e.g., "DATABASE_QUERY" or "GENERAL_KNOWLEDGE"
   ↓
4. FILTER DATABASE BY AUTHORITY (if specified)
   e.g., `WHERE authority_name = 'EMA'`
   ↓
5. EXTRACT KEYWORDS
   e.g., ['update', 'latest', 'new']
   ↓
6. CALCULATE SIMILARITY SCORES
   Base: keyword overlap
   + 0.2: exact phrase match
   + 0.1: recent (≤7 days)
   ↓
7. ENFORCE THRESHOLD
   Keep only: score ≥ 0.75
   ↓
8. LIMIT TO MAX 3 DOCUMENTS
   Sort by score, take top 3
   ↓
9. FALLBACK DECISION
   If 0 documents: Use GENERAL_KNOWLEDGE
   If ≥1 documents: Use DATABASE_QUERY
   ↓
10. INJECT CONTEXT
    Package documents (or empty if fallback)
    ↓
11. GENERATE ANSWER
    AI writes response (with or without docs)
    ↓
12. LOG METRICS
    [RETRIEVAL METRICS] output shows all details
    ↓
13. RETURN RESPONSE
    Answer + sources + search metadata
```

---

## 🔧 Configuration Tuning

### Make Threshold Stricter (Keep only top matches)
```python
COSINE_SIMILARITY_THRESHOLD = 0.80  # Was 0.75
```
**Effect:** Fewer documents (higher quality), more fallbacks

### Make Threshold Looser (Include more candidates)
```python
COSINE_SIMILARITY_THRESHOLD = 0.70  # Was 0.75
```
**Effect:** More documents (some low-quality), fewer fallbacks

### Inject More Documents
```python
MAX_DOCUMENTS_INJECTED = 5  # Was 3
```
**Effect:** More context, but may confuse model

### Add Authority Detection
```python
AUTHORITY_NAMES = {
    'fda': 'FDA',
    'ema': 'EMA',
    'new_auth': 'NEW_AUTHORITY',  # ADD HERE
    ...
}
```

---

## 📝 Logging Guide

### Watch These Logs

**When to look at `[AUTHORITY FILTER]`:**
- User query mentions specific authority
- Should see: "Enforcing authority filter: [NAME]"

**When to look at `[THRESHOLD FILTER]`:**
- After document candidates selected
- Should see: "X documents passed threshold Y"

**When to look at `[SIMILARITY SCORES]`:**
- Diagnose "why weren't more docs included"
- Shows actual similarity numbers for top 10

**When to look at `[RETRIEVAL METRICS]`:**
- Final check: how many documents injected?
- Which mode used: DATABASE_QUERY or GENERAL_KNOWLEDGE?
- Authority mixing: check if only 1 authority present

### Find Logs In Terminal
```bash
# Start backend
cd c:\Users\mbpre\OneDrive\Desktop\REG\backend
python.exe -m uvicorn app.main:app --port 8000

# Watch for patterns like:
# [AUTHORITY FILTER]
# [THRESHOLD FILTER]
# [SIMILARITY SCORES]
# [RETRIEVAL METRICS]
```

---

## 🧪 Testing Checklist

### Test 1: Authority Filter Works
```
Query: "EMA safety alerts"
Expected: 
  ✓ [AUTHORITY FILTER] Detected authority: EMA
  ✓ Only EMA documents in results
```

### Test 2: Threshold Enforcement
```
Query: Random keywords unlikely to match
Expected:
  ✓ [THRESHOLD FILTER] 0 documents passed
  ✓ [FALLBACK] Switching to GENERAL_KNOWLEDGE
  ✓ 0 documents in response
```

### Test 3: Document Limit
```
Query: Broad query matching 10+ documents
Expected:
  ✓ [DOCUMENT LIMIT] Selected 3 documents (max 3)
  ✓ Exactly 3 sources in response
```

### Test 4: Similarity Scores Logged
```
Any query
Expected:
  ✓ [SIMILARITY SCORES] Shows actual numbers
  ✓ All scores between 0.0 and 1.0
  ✓ Injected docs all ≥ 0.75
```

---

## 🚨 Troubleshooting

### Problem: Too few documents returned
**Check:**
1. Is threshold too high? (Try 0.70)
2. Does database have matching updates?
3. Are keywords extracted correctly?

**Fix:**
```python
COSINE_SIMILARITY_THRESHOLD = 0.70  # More lenient
```

### Problem: Wrong authority included
**Check:**
1. Is `extract_authority_from_query()` working?
2. Is authority filter applied to base_query?

**Fix:** Add logging:
```python
requested_authority, _ = extract_authority_from_query(request.query)
print(f"[DEBUG] Extracted authority: {requested_authority}")
```

### Problem: Always falling back to GENERAL_KNOWLEDGE
**Check:**
1. Are documents in database?
2. Are keywords matching document content?
3. Is threshold too strict? (0.75 default)

**Fix:**
```python
# Lower threshold temporarily to debug
COSINE_SIMILARITY_THRESHOLD = 0.50
# Check logs to see what similarity scores are generated
# Then set back to 0.75
```

---

## 📌 Important Notes

✅ **Do NOT change:**
- Model (still gpt-4-turbo)
- Prompt templates (still same structure)
- API response format (still compatible)
- Database schema (no changes)

✅ **Safe to change:**
- `COSINE_SIMILARITY_THRESHOLD` (0.0-1.0)
- `MAX_DOCUMENTS_INJECTED` (1-10, not recommended >5)
- `AUTHORITY_NAMES` (add/remove authorities)

⚠️ **Requires restart:**
- Any constant in `chat.py`
- Any function in `rag_service.py`

---

## 🎓 Understanding Similarity Scores

### Example: Query "FDA drug approval"

| Document | Keyword Match | Phrase Match | Recency | Score | Decision |
|----------|---|---|---|---|---|
| "FDA approves new drug" | 0.67 | +0.2 | -0.01 | 0.86 | ✓ INCLUDE |
| "Drug approval timeline" | 0.67 | 0 | +0.1 | 0.77 | ✓ INCLUDE |
| "FDA warning" | 0.33 | 0 | +0.1 | 0.43 | ✗ REJECT |
| "Medication history" | 0 | 0 | 0 | 0.0 | ✗ REJECT |

**Result:** 2 documents injected (both ≥ 0.75)

---

## 🔗 API Endpoints

### Chat Query (Main Endpoint)
```
POST /api/v1/chat/query
Content-Type: application/json

{
  "query": "Show me EMA updates"
}

Response:
{
  "answer": "Based on recent EMA updates...",
  "sources": [
    {
      "id": 123,
      "title": "EMA updates approval process",
      "source_link": "https://...",
      "published_date": "2026-02-22",
      "authority_id": 2
    }
  ]
}
```

### Check Terminal Logs
All RAG metrics printed to stdout:
- `[AUTHORITY FILTER]` - Authority detection
- `[THRESHOLD FILTER]` - Threshold results
- `[SIMILARITY SCORES]` - Actual scores
- `[RETRIEVAL METRICS]` - Final summary

---

## 📞 Quick Help

**Q: How do I know if threshold is too strict?**
A: Look for `[FALLBACK]` log when you expect documents. Lower threshold by 0.05.

**Q: How do I prevent mixing of authorities?**
A: Already done! System filters by authority BEFORE ranking.

**Q: Can I inject more than 3 documents?**
A: Yes, change `MAX_DOCUMENTS_INJECTED = 5`, but not recommended (model confusion).

**Q: Why are some documents rejected?**
A: Similarity score < 0.75. Check `[SIMILARITY SCORES]` log to see why.

**Q: How do I add a new authority?**
A: Add to `AUTHORITY_NAMES` dict and backend will detect it automatically.

---

**Last Updated:** 2026-02-22
**Status:** ✅ Production Ready
**Deployment:** Backend running on port 8000

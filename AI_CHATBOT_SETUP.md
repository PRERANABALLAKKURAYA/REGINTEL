# RegIntel AI Chatbot - Setup & Usage

## 🚀 Quick Start

Your AI chat is now **fully functional** and running at:
- **Frontend**: http://localhost:9090/dashboard/chat
- **Backend API**: http://localhost:8000/api/v1/ai/query

## ⚙️ Configuration Requirements

### OpenAI API Key (Required for GPT-4 responses)

The chatbot currently displays configuration messages because it needs your OpenAI API key.

**Setup Steps:**

1. **Get your OpenAI API key** from https://platform.openai.com/api-keys

2. **Update backend/.env file:**
   ```bash
   # Open: c:\Users\mbpre\OneDrive\Desktop\REG\backend\.env
   
   # Replace this line:
   OPENAI_API_KEY=your_openai_api_key_here
   
   # With your actual key:
   OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_KEY_HERE
   ```

3. **Restart the backend:**
   ```powershell
   # Stop current backend (Ctrl+C in terminal)
   # Then restart:
   cd c:\Users\mbpre\OneDrive\Desktop\REG\backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

4. **Test the chat** - Try these queries:
   - "What are the latest FDA guidelines on biosimilars?"
   - "Explain what GMP means"
   - "List recent EMA updates"

---

## 🤖 How the Hybrid Intelligence System Works

### Intent Classification

The system automatically classifies each query into **8 intent types**:

1. **DOCUMENT_REQUEST** - User explicitly wants documents/links
   - Keywords: `document`, `link`, `pdf`, `source`, `official`
   - Response: Returns official document links with 100-200 word summaries

2. **LIST_REQUEST** - User wants structured lists
   - Keywords: `list`, `show me all`, `give me all`, `enumerate`
   - Response: Bullet-point formatted lists

3. **GUIDELINE_REQUEST** ⭐ - User asks for guidelines/standards
   - Keywords: `guideline`, `guidance`, `standard`, `gmp`, `gcp`, `ich`
   - Response: Official guideline documents + structured summary
   - **Priority intent** for queries like "latest FDA guidelines"

4. **REGULATION_REQUEST** - User asks about regulations
   - Keywords: `regulation`, `rule`, `law`, `compliance`, `cfr`
   - Response: Regulatory framework documentation

5. **POLICY_REQUEST** - User asks about policies
   - Keywords: `policy`, `decision`, `procedure`, `process`
   - Response: Structured policy explanations

6. **DATABASE_QUERY** ⭐ - User asks for recent/specific updates
   - Keywords: `recent`, `latest`, `new`, `update`, `announcement`
   - Response: Retrieves from update database with citations
   - **Priority intent** for time-sensitive queries

7. **EXPLANATION_REQUEST** - User wants concept explanations
   - Keywords: `explain`, `describe`, `what is`, `tell me about`
   - Response: Clear, structured explanations with examples

8. **GENERAL_KNOWLEDGE** - Fallback for everything else
   - Response: General regulatory knowledge with transparency about not having specific documents

### Response Routing (RAG vs General GPT)

```
User Query → Intent Classification → Database Retrieval Attempt
                                            ↓
                              Confidence Score Calculation
                                            ↓
                      ┌─────────────────────┴─────────────────────┐
                      ↓                                           ↓
           Confidence ≥ 0.70                          Confidence < 0.70
                      ↓                                           ↓
              RAG MODE (Documents)                    GENERAL GPT MODE
           • Use retrieved documents                 • Use AI knowledge
           • Cite specific sources                   • Acknowledge no docs
           • Authority-specific facts                • Provide concepts
           • Include publication dates               • Suggest official sources
```

### Authority Detection

The system automatically detects authority mentions:
- **FDA** (United States)
- **EMA** (European Union)
- **ICH** (International)
- **MHRA** (United Kingdom)
- **PMDA** (Japan)
- **CDSCO** (India)
- **NMPA** (China)

**Example:**
- Query: "What are the latest FDA guidelines on biosimilars?"
- Detected: `GUIDELINE_REQUEST` + `FDA` authority filter
- Behavior: Searches only FDA documents, returns with FDA-specific content

---

## 📊 Query Examples & Expected Behavior

### Example 1: Document Retrieval (RAG Mode)
**Query:** `"What are the latest FDA guidelines on biosimilars?"`
- **Intent:** GUIDELINE_REQUEST (priority)
- **Authority:** FDA
- **Mode:** RAG (if documents found)
- **Response:** Official FDA biosimilar guideline documents with links, key points, and publication dates

### Example 2: General Knowledge (General GPT Mode)
**Query:** `"Explain what regulatory affairs is"`
- **Intent:** EXPLANATION_REQUEST
- **Authority:** None
- **Mode:** GENERAL_GPT (conceptual question)
- **Response:** Structured explanation of regulatory affairs profession, key responsibilities, frameworks

### Example 3: Recent Updates (Database Query)
**Query:** `"Show me recent EMA updates from the last 30 days"`
- **Intent:** DATABASE_QUERY (priority)
- **Authority:** EMA
- **Mode:** RAG (retrieves from database)
- **Response:** List of recent EMA updates with dates, categories, and links

### Example 4: List Request
**Query:** `"List all ICH quality guidelines"`
- **Intent:** LIST_REQUEST
- **Authority:** ICH
- **Mode:** RAG (if ICH guideline documents exist)
- **Response:** Bullet-point list of ICH quality guidelines (Q1-Q14)

---

## 🛠️ Troubleshooting

### Issue: "⚠️ AI service configuration issue"
**Cause:** OpenAI API key is missing or invalid

**Solution:**
1. Check `backend/.env` file exists
2. Verify `OPENAI_API_KEY` value starts with `sk-`
3. Ensure key is not placeholder text `your_openai_api_key_here`
4. Restart backend server

### Issue: "No documents found" for specific queries
**Cause:** Database doesn't have matching documents or confidence threshold not met

**Solution:**
- Refine your query with specific authority names
- Use exact terminology (e.g., "GMP" instead of "manufacturing")
- Try querying recent updates: "latest [authority] updates"
- System will provide general knowledge instead

### Issue: Chat returns generic/mock responses
**Cause:** Backend is using fallback mode (no OpenAI key)

**Solution:**
1. Verify API key is set correctly in `.env`
2. Check backend logs for `[AI SERVICE] OpenAI error:` messages
3. Ensure you have OpenAI credits/quota available
4. Restart backend after updating `.env`

### Issue: Backend not responding
**Cause:** Port 8000 is occupied or backend crashed

**Solution:**
```powershell
# Kill any Python processes
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force

# Restart backend
cd c:\Users\mbpre\OneDrive\Desktop\REG\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Issue: Frontend not loading
**Cause:** Port 9090 is occupied or npm dev server crashed

**Solution:**
```powershell
# Kill Node.js processes
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force

# Restart frontend
cd c:\Users\mbpre\OneDrive\Desktop\REG\frontend
npm run dev -- --port 9090
```

---

## 📝 Backend Logs

Monitor backend logs to understand query routing:

```
[HYBRID AI] Query: What are the latest FDA guidelines on biosimilars?
[INTENT] GUIDELINE_REQUEST | [RESPONSE TYPE] document
[AUTHORITY] FDA
[RETRIEVAL] DB required: True
[RETRIEVAL] Found 3 documents | Scores: ['0.85', '0.78', '0.72'] | Confidence: 0.78
[MODE] RAG (confidence: 0.78 >= 0.70)
[RESPONSE] Generating RAG response (document) with 3 document(s)
[AI SERVICE] Calling GPT-4 Turbo (temp=0.7, max_tokens=600)
[AI SERVICE] GPT-4 response: 487 chars
[RESULT] Mode: RAG | Sources: 3 | Response length: 487
```

**Key Indicators:**
- `[MODE] RAG` = Using retrieved documents
- `[MODE] GENERAL_GPT` = Using general AI knowledge
- Confidence score shows document match quality (0.0-1.0)

---

## 🎯 Usage Tips

### To Get Best Results:

1. **Be specific with queries:**
   - ❌ "Tell me about drugs"
   - ✅ "What are FDA drug approval requirements for NDAs?"

2. **Mention the authority explicitly:**
   - ❌ "Latest biosimilar guidelines"
   - ✅ "Latest FDA biosimilar guidelines"

3. **Use correct terminology:**
   - Use `GMP`, `GCP`, `ICH`, `NDA`, `BLA`, `CFR 21` for better matches

4. **For recent updates:**
   - Include time references: "latest", "recent", "2026", "this month"

5. **For document retrieval:**
   - Use keywords: "guidance", "guideline", "regulation", "standard"

---

## 🚀 Next Steps

1. **Set your OpenAI API key** in `backend/.env`
2. **Restart the backend server**
3. **Access the chat UI** at http://localhost:9090/dashboard/chat
4. **Try suggested queries** from the chat interface
5. **Monitor backend logs** to understand query routing

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Frontend Dashboard**: http://localhost:9090/dashboard
- **Backend Logs**: Check terminal where `uvicorn` is running
- **Database**: `backend/reg_db.sqlite3` (regulatory updates)

---

**System Status:**
- ✅ Backend: Running on port 8000
- ✅ Frontend: Running on port 9090
- ⚠️ AI Chat: Needs OpenAI API key to enable GPT-4 responses
- ✅ Database: Regulatory updates scraped and ready
- ✅ Intent Classification: Fully operational
- ✅ Hybrid Intelligence: Ready (RAG + General GPT routing)


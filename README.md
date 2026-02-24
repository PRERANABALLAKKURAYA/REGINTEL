# Pharmaceutical Regulatory Intelligence Platform

A centralized SaaS platform to track, summarize, and query global pharmaceutical regulatory updates from FDA, CDSCO, EMA, and more.

## Features
- **Data Aggregation**: Automated scraping from 6+ major authorities.
- **AI-Powered Summaries**: "Beginner", "Professional", and "Legal" modes.
- **RAG Chatbot**: Ask questions about specific regulations.
- **Smart Notifications**: Alerts based on preference.
- **Gamification**: Earn badges for staying updated.

## Tech Stack
- **Backend**: FastAPI, PostgreSQL, SQLAlchemy, Pydantic
- **Frontend**: Next.js (App Router), Tailwind CSS
- **AI**: OpenAI/LLM Wrapper, FAISS (Vector Store)
- **Deployment**: Docker Compose

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (if running locally without Docker)
- Python 3.9+ (if running locally without Docker)

### Running with Docker (Recommended)
1. Set up `.env` files:
   - Backend: `backend/.env` (Copy from example or set `DATABASE_URL`, `SECRET_KEY`, `OPENAI_API_KEY`)
   - Frontend: `frontend/.env.local`

2. Build and run:
   ```bash
   docker-compose up --build
   ```

3. Access the app:
   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Local Development
**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Project Structure
```
/backend
  /app
    /api        # Routes
    /core       # Config, Security
    /db         # Database Session
    /models     # Database Models
    /schemas    # Pydantic Models
    /services   # AI, RAG, Notification Logic
    /scrapers   # Data Ingestion
/frontend
  /src
    /app        # Next.js Pages
    /components # React Components
```

## Legal Disclaimer
This platform is an independent regulatory intelligence tool and is not affiliated with any regulatory authority.

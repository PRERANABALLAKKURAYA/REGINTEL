from datetime import datetime, timedelta
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.db.base_class import Base
from app.db.session import SessionLocal, engine
from app.models.authority import Authority
from app.models.user import User
from app.models.update import Update
from app.models.notification import Notification
from app.models.gamification import Badge, UserBadge, UserStats
from app.scrapers.scheduler import start_scheduler

app = FastAPI(title="Pharma Regulatory Intelligence API")

allowed_origins = [
    "http://localhost:9090",
    "http://127.0.0.1:9090",
    "https://frontend-production-a2ce3.up.railway.app",
    "https://regintel.up.railway.app",
]

# Optional single-origin override
frontend_origin = os.getenv("FRONTEND_ORIGIN")
if frontend_origin:
    allowed_origins.append(frontend_origin)

# Optional multi-origin config (comma-separated)
frontend_origins = os.getenv("FRONTEND_ORIGINS")
if frontend_origins:
    allowed_origins.extend([origin.strip() for origin in frontend_origins.split(",") if origin.strip()])

# Keep order stable while removing duplicates
allowed_origins = list(dict.fromkeys(allowed_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


def seed_data() -> None:
    db = SessionLocal()
    try:
        if db.query(Authority).first() is None:
            authorities = [
                Authority(name="CDSCO", country="India", website_url="https://cdsco.gov.in/"),
                Authority(name="FDA", country="USA", website_url="https://www.fda.gov/"),
                Authority(name="EMA", country="EU", website_url="https://www.ema.europa.eu/"),
                Authority(name="ICH", country="International", website_url="https://www.ich.org/"),
                Authority(name="MHRA", country="UK", website_url="https://www.gov.uk/government/organisations/medicines-and-healthcare-products-regulatory-agency"),
                Authority(name="PMDA", country="Japan", website_url="https://www.pmda.go.jp/"),
                Authority(name="NMPA", country="China", website_url="https://www.nmpa.gov.cn/"),
            ]
            db.add_all(authorities)
            db.commit()

        if db.query(Update).first() is None:
            # Seed data removed - scrapers will populate real updates with working URLs
            pass
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    seed_data()
    start_scheduler()

@app.get("/")
def root():
    return {"message": "Welcome to the Pharmaceutical Regulatory Intelligence Platform API"}

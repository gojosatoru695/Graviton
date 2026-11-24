from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api import dashboard, cases, money, promises, actions, receipts, upload, chat, seed, runs, approvals
from app.seed.generator import generate_synthetic_data
from app.engines.synthesizer import CaseSynthesizer
from app.models.cases import Case

# Ensure tables exist and initial synthetic dataset is seeded
Base.metadata.create_all(bind=engine)

def ensure_initial_seed():
    db = SessionLocal()
    try:
        case_count = db.query(Case).count()
        if case_count == 0:
            generate_synthetic_data(db_session=db)
            synth = CaseSynthesizer(db)
            synth.synthesize_all_cases()
    finally:
        db.close()

ensure_initial_seed()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Jarvis: Evidence-backed reconciliation and promise engine for micro-sellers",
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(cases.router, prefix=settings.API_V1_STR)
app.include_router(money.router, prefix=settings.API_V1_STR)
app.include_router(promises.router, prefix=settings.API_V1_STR)
app.include_router(actions.router, prefix=settings.API_V1_STR)
app.include_router(receipts.router, prefix=settings.API_V1_STR)
app.include_router(upload.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(seed.router, prefix=settings.API_V1_STR)
app.include_router(runs.router, prefix=settings.API_V1_STR)
app.include_router(approvals.router, prefix=settings.API_V1_STR)





@app.get("/")
def root():
    return {
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "HEALTHY",
        "watermark": settings.DATASET_WATERMARK,
    }

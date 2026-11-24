from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db
from app.seed.generator import generate_synthetic_data
from app.engines.synthesizer import CaseSynthesizer

router = APIRouter(prefix="/seed", tags=["seed"])


@router.post("")
def seed_database(db: Session = Depends(get_db)) -> Dict[str, Any]:
    stats = generate_synthetic_data(db_session=db)
    synth = CaseSynthesizer(db)
    cases = synth.synthesize_all_cases()
    stats["cases_created"] = len(cases)
    return {
        "status": "SUCCESS",
        "message": "Realistic synthetic Indian seller dataset regenerated successfully.",
        "stats": stats,
    }

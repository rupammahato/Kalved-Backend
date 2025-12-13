"""Patient endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_patient
from app.dependencies.rate_limit import rate_limit
from app.schemas.patient import PatientProfileUpdate, PatientRead
from app.services.patient_service import PatientService
from app.utils.errors import UserNotFoundError

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/me", response_model=PatientRead)
async def get_patient(current_user = Depends(get_current_patient), db: Session = Depends(get_db)):
    patient = PatientService.ensure_patient(db, current_user["sub"])
    return patient


@router.post("/me", response_model=PatientRead)
async def update_patient(
    payload: PatientProfileUpdate,
    current_user = Depends(get_current_patient),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    try:
        patient = PatientService.update_profile(
            db,
            current_user["sub"],
            payload.model_dump(exclude_none=True),
        )
        return patient
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

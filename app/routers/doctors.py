"""Doctor endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_doctor
from app.dependencies.rate_limit import rate_limit
from app.schemas.doctor import DoctorProfileUpdate, DoctorRead
from app.schemas.clinic import ClinicBase, ClinicRead
from app.services.doctor_service import DoctorService
from app.utils.errors import UserNotFoundError

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.post("/profile", response_model=DoctorRead)
async def complete_profile(
    payload: DoctorProfileUpdate,
    current_doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    try:
        doctor = DoctorService.update_profile(
            db,
            current_doctor["sub"],
            payload.model_dump(exclude_none=True),
        )
        return doctor
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/clinics", response_model=ClinicRead)
async def add_clinic(
    payload: ClinicBase,
    current_doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    try:
        clinic = DoctorService.add_clinic(
            db,
            current_doctor["sub"],
            payload.model_dump(exclude_none=True),
        )
        return clinic
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{doctor_id}", response_model=DoctorRead)
async def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = DoctorService.get_by_id(db, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

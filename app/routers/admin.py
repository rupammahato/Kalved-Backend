"""Admin endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_admin
from app.dependencies.rate_limit import rate_limit
from app.services.doctor_service import DoctorService
from app.schemas.doctor import DoctorRead
from app.utils.errors import UserNotFoundError

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/pending-doctors", response_model=list[DoctorRead])
async def pending_doctors(
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit),
):
    return DoctorService.list_pending(db)


@router.post("/doctors/{doctor_id}/approve", response_model=DoctorRead)
async def approve_doctor(
    doctor_id: int,
    notes: str | None = None,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        return DoctorService.approve_doctor(db, current_admin["sub"], doctor_id, notes)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/doctors/{doctor_id}/reject", response_model=DoctorRead)
async def reject_doctor(
    doctor_id: int,
    reason: str | None = None,
    current_admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        return DoctorService.reject_doctor(db, current_admin["sub"], doctor_id, reason)
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

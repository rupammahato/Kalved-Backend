# app/routers/appointments.py
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.appointment import (
    AppointmentBookRequest,
    AppointmentCancelRequest,
    AppointmentBookResponse,
    AppointmentListResponse,
    AppointmentDetail,
)
from app.services.appointment_service import AppointmentService
from app.models.appointment import Appointment

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("/available-slots")
async def get_available_slots(
    clinic_id: int = Query(..., gt=0),
    doctor_id: int = Query(..., gt=0),
    query_date: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
):
    """
    Get available appointment slots for a doctor in a clinic on a given date.
    Cached via Redis for 1 hour.
    """
    try:
        slots = await AppointmentService.get_available_slots(
            db=db,
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            query_date=query_date,
        )
        return {
            "success": True,
            "data": {
                "clinic_id": clinic_id,
                "doctor_id": doctor_id,
                "date": query_date,
                "slots": slots,
                "total_available": len(slots),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/book",
    response_model=AppointmentBookResponse,
    status_code=status.HTTP_201_CREATED,
)
async def book_appointment(
    payload: AppointmentBookRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Book a free appointment.
    - Only patients are allowed.
    - No payment step; confirmation is separate.
    """
    if current_user.get("user_type") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can book appointments.",
        )

    try:
        result = await AppointmentService.book_appointment(
            db=db,
            patient_id=current_user["sub"],
            slot_id=payload.slot_id,
            appointment_type=payload.appointment_type,
            reason_for_visit=payload.reason_for_visit,
        )
        return AppointmentBookResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{appointment_id}/confirm", response_model=dict)
async def confirm_appointment(
    appointment_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Patient confirms they will attend the appointment.
    """
    if current_user.get("user_type") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can confirm appointments.",
        )
    try:
        result = await AppointmentService.confirm_appointment(
            db=db,
            appointment_id=appointment_id,
            patient_id=current_user["sub"],
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{appointment_id}/cancel", response_model=dict)
async def cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancelRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancel an appointment (free booking, so no refund logic).
    Both patient and doctor can cancel (depending on your business rules).
    """
    try:
        result = await AppointmentService.cancel_appointment(
            db=db,
            appointment_id=appointment_id,
            cancelled_by_user_id=current_user["sub"],
            reason=payload.cancellation_reason,
        )
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my-appointments", response_model=AppointmentListResponse)
async def get_my_appointments(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 20,
):
    """
    Get appointments for the current patient.
    """
    if current_user.get("user_type") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can view their appointments.",
        )

    appts = AppointmentService.list_patient_appointments(
        db=db, patient_id=current_user["sub"], skip=skip, limit=limit
    )
    return AppointmentListResponse(
        items=[AppointmentDetail.from_orm(a) for a in appts],
        total=len(appts),
    )


@router.get("/doctor-appointments", response_model=AppointmentListResponse)
async def get_doctor_appointments(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    skip: int = 0,
    limit: int = 20,
):
    """
    Get appointments for the current doctor.
    """
    if current_user.get("user_type") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can view doctor appointments.",
        )

    appts = AppointmentService.list_doctor_appointments(
        db=db,
        doctor_id=current_user["sub"],
        status=status_filter,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
    )
    return AppointmentListResponse(
        items=[AppointmentDetail.from_orm(a) for a in appts],
        total=len(appts),
    )

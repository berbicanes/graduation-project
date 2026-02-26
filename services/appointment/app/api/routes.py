import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, require_role
from app.crud import (
    cancel_appointment,
    check_scheduling_conflict,
    create_appointment,
    create_doctor_availability,
    get_appointment_by_id,
    get_doctor_availability,
    list_appointments,
    update_appointment,
)
from app.db import get_db
from app.events.publisher import publish_event
from app.schemas import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
    DoctorAvailabilityCreate,
    DoctorAvailabilityResponse,
    PaginatedAppointmentResponse,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create(
    body: AppointmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "doctor", "nurse", "receptionist")),
) -> AppointmentResponse:
    # Check for scheduling conflicts
    conflict = await check_scheduling_conflict(db, body.doctor_id, body.scheduled_at, body.duration_minutes)
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor has a scheduling conflict at the requested time",
        )

    appointment = await create_appointment(db, body)
    await publish_event(
        "appointment.created",
        {
            "id": str(appointment.id),
            "patient_id": str(appointment.patient_id),
            "doctor_id": str(appointment.doctor_id),
            "scheduled_at": appointment.scheduled_at.isoformat(),
        },
    )
    return AppointmentResponse.model_validate(appointment)


@router.get("", response_model=PaginatedAppointmentResponse)
async def list_all(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    patient_id: uuid.UUID | None = Query(None),
    doctor_id: uuid.UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PaginatedAppointmentResponse:
    appointments, total = await list_appointments(
        db, page=page, per_page=per_page, patient_id=patient_id, doctor_id=doctor_id, status=status_filter
    )
    return PaginatedAppointmentResponse(
        total=total,
        page=page,
        per_page=per_page,
        items=[AppointmentResponse.model_validate(a) for a in appointments],
    )


@router.get("/availability", response_model=list[DoctorAvailabilityResponse])
async def check_availability(
    doctor_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[DoctorAvailabilityResponse]:
    availability = await get_doctor_availability(db, doctor_id)
    return [DoctorAvailabilityResponse.model_validate(a) for a in availability]


@router.post("/availability", response_model=DoctorAvailabilityResponse, status_code=status.HTTP_201_CREATED)
async def set_availability(
    body: DoctorAvailabilityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "doctor")),
) -> DoctorAvailabilityResponse:
    availability = await create_doctor_availability(db, body)
    return DoctorAvailabilityResponse.model_validate(availability)


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_one(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> AppointmentResponse:
    appointment = await get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return AppointmentResponse.model_validate(appointment)


@router.put("/{appointment_id}", response_model=AppointmentResponse)
async def reschedule(
    appointment_id: uuid.UUID,
    body: AppointmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "doctor", "nurse", "receptionist")),
) -> AppointmentResponse:
    appointment = await get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    if appointment.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot reschedule a cancelled appointment")

    # Check for conflicts if time is being changed
    scheduled_at = body.scheduled_at or appointment.scheduled_at
    duration = body.duration_minutes or appointment.duration_minutes
    conflict = await check_scheduling_conflict(db, appointment.doctor_id, scheduled_at, duration, exclude_id=appointment_id)
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor has a scheduling conflict at the requested time",
        )

    appointment = await update_appointment(db, appointment, body)
    return AppointmentResponse.model_validate(appointment)


@router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel(
    appointment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "doctor", "nurse", "receptionist")),
) -> AppointmentResponse:
    appointment = await get_appointment_by_id(db, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    if appointment.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Appointment is already cancelled")

    appointment = await cancel_appointment(db, appointment)
    await publish_event(
        "appointment.cancelled",
        {"id": str(appointment.id), "patient_id": str(appointment.patient_id), "doctor_id": str(appointment.doctor_id)},
    )
    return AppointmentResponse.model_validate(appointment)

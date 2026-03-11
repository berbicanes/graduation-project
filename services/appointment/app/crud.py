import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appointment, DoctorAvailability, PatientCache
from app.schemas import AppointmentCreate, AppointmentUpdate, DoctorAvailabilityCreate


async def create_appointment(db: AsyncSession, data: AppointmentCreate) -> Appointment:
    appointment = Appointment(**data.model_dump())
    db.add(appointment)
    await db.flush()
    return appointment


async def get_appointment_by_id(db: AsyncSession, appointment_id: uuid.UUID) -> Appointment | None:
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    return result.scalar_one_or_none()


async def list_appointments(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    patient_id: uuid.UUID | None = None,
    doctor_id: uuid.UUID | None = None,
    status: str | None = None,
) -> tuple[list[Appointment], int]:
    query = select(Appointment)

    if patient_id:
        query = query.where(Appointment.patient_id == patient_id)
    if doctor_id:
        query = query.where(Appointment.doctor_id == doctor_id)
    if status:
        query = query.where(Appointment.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Appointment.scheduled_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    appointments = list(result.scalars().all())

    return appointments, total


async def update_appointment(db: AsyncSession, appointment: Appointment, data: AppointmentUpdate) -> Appointment:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)
    await db.flush()
    await db.refresh(appointment)
    return appointment


async def cancel_appointment(db: AsyncSession, appointment: Appointment) -> Appointment:
    appointment.status = "cancelled"
    await db.flush()
    await db.refresh(appointment)
    return appointment


async def check_scheduling_conflict(
    db: AsyncSession,
    doctor_id: uuid.UUID,
    scheduled_at: datetime,
    duration_minutes: int,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    """Check if a doctor has a conflicting appointment. Returns True if conflict exists."""
    start = scheduled_at
    end = scheduled_at + timedelta(minutes=duration_minutes)

    # Get all active appointments for this doctor on the same day
    day_start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    query = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.status.in_(["scheduled", "completed"]),
        Appointment.scheduled_at >= day_start,
        Appointment.scheduled_at < day_end,
    )
    if exclude_id:
        query = query.where(Appointment.id != exclude_id)

    result = await db.execute(query)
    existing = result.scalars().all()

    # Check overlap in Python (DB-agnostic)
    for appt in existing:
        appt_start = appt.scheduled_at
        if appt_start.tzinfo is None:
            appt_start = appt_start.replace(tzinfo=UTC)
        appt_end = appt_start + timedelta(minutes=appt.duration_minutes)

        check_start = start
        if check_start.tzinfo is None:
            check_start = check_start.replace(tzinfo=UTC)
        check_end = end
        if check_end.tzinfo is None:
            check_end = check_end.replace(tzinfo=UTC)

        if check_start < appt_end and check_end > appt_start:
            return True

    return False


# Doctor availability
async def create_doctor_availability(db: AsyncSession, data: DoctorAvailabilityCreate) -> DoctorAvailability:
    availability = DoctorAvailability(**data.model_dump())
    db.add(availability)
    await db.flush()
    return availability


async def get_doctor_availability(db: AsyncSession, doctor_id: uuid.UUID) -> list[DoctorAvailability]:
    result = await db.execute(
        select(DoctorAvailability)
        .where(DoctorAvailability.doctor_id == doctor_id)
        .order_by(DoctorAvailability.day_of_week)
    )
    return list(result.scalars().all())


# Patient cache
async def cache_patient(db: AsyncSession, patient_id: uuid.UUID, first_name: str, last_name: str) -> PatientCache:
    existing = await db.execute(select(PatientCache).where(PatientCache.id == patient_id))
    cached = existing.scalar_one_or_none()
    if cached:
        cached.first_name = first_name
        cached.last_name = last_name
    else:
        cached = PatientCache(id=patient_id, first_name=first_name, last_name=last_name)
        db.add(cached)
    await db.flush()
    return cached


async def get_cached_patient(db: AsyncSession, patient_id: uuid.UUID) -> PatientCache | None:
    result = await db.execute(select(PatientCache).where(PatientCache.id == patient_id))
    return result.scalar_one_or_none()

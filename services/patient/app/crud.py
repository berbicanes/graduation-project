import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Patient
from app.schemas import PatientCreate, PatientUpdate


async def create_patient(db: AsyncSession, data: PatientCreate) -> Patient:
    patient = Patient(**data.model_dump())
    db.add(patient)
    await db.flush()
    return patient


async def get_patient_by_id(db: AsyncSession, patient_id: uuid.UUID) -> Patient | None:
    result = await db.execute(select(Patient).where(Patient.id == patient_id, Patient.is_active == True))  # noqa: E712
    return result.scalar_one_or_none()


async def list_patients(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search: str | None = None,
) -> tuple[list[Patient], int]:
    query = select(Patient).where(Patient.is_active == True)  # noqa: E712

    if search:
        search_filter = or_(
            Patient.first_name.ilike(f"%{search}%"),
            Patient.last_name.ilike(f"%{search}%"),
            Patient.email.ilike(f"%{search}%"),
            Patient.phone.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Paginate
    query = query.order_by(Patient.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    patients = list(result.scalars().all())

    return patients, total


async def update_patient(db: AsyncSession, patient: Patient, data: PatientUpdate) -> Patient:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)
    await db.flush()
    await db.refresh(patient)
    return patient


async def soft_delete_patient(db: AsyncSession, patient: Patient) -> Patient:
    patient.is_active = False
    await db.flush()
    return patient

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClinicalNote, NoteAuditLog
from app.schemas import NoteCreate, NoteUpdate


async def create_note(db: AsyncSession, data: NoteCreate, changed_by: uuid.UUID) -> ClinicalNote:
    note = ClinicalNote(**data.model_dump())
    db.add(note)
    await db.flush()
    await db.refresh(note)

    # Create audit log entry
    audit = NoteAuditLog(
        note_id=note.id,
        changed_by=changed_by,
        change_type="created",
        old_values=None,
        new_values=data.model_dump(mode="json"),
    )
    db.add(audit)
    await db.flush()

    return note


async def get_note_by_id(db: AsyncSession, note_id: uuid.UUID) -> ClinicalNote | None:
    result = await db.execute(select(ClinicalNote).where(ClinicalNote.id == note_id))
    return result.scalar_one_or_none()


async def list_notes(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    patient_id: uuid.UUID | None = None,
    appointment_id: uuid.UUID | None = None,
) -> tuple[list[ClinicalNote], int]:
    query = select(ClinicalNote)

    if patient_id:
        query = query.where(ClinicalNote.patient_id == patient_id)
    if appointment_id:
        query = query.where(ClinicalNote.appointment_id == appointment_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(ClinicalNote.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    notes = list(result.scalars().all())

    return notes, total


async def update_note(db: AsyncSession, note: ClinicalNote, data: NoteUpdate, changed_by: uuid.UUID) -> ClinicalNote:
    # Capture old values before mutation
    old_values = {
        "subjective": note.subjective,
        "objective": note.objective,
        "assessment": note.assessment,
        "plan": note.plan,
    }

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(note, field, value)
    await db.flush()
    await db.refresh(note)

    # Capture new values after mutation
    new_values = {
        "subjective": note.subjective,
        "objective": note.objective,
        "assessment": note.assessment,
        "plan": note.plan,
    }

    audit = NoteAuditLog(
        note_id=note.id,
        changed_by=changed_by,
        change_type="updated",
        old_values=old_values,
        new_values=new_values,
    )
    db.add(audit)
    await db.flush()

    return note


async def get_note_history(db: AsyncSession, note_id: uuid.UUID) -> list[NoteAuditLog]:
    result = await db.execute(
        select(NoteAuditLog).where(NoteAuditLog.note_id == note_id).order_by(NoteAuditLog.changed_at.desc())
    )
    return list(result.scalars().all())


async def create_stub_note(
    db: AsyncSession,
    appointment_id: uuid.UUID,
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
) -> ClinicalNote:
    """Create a stub note from an appointment.created event (empty SOAP fields)."""
    note = ClinicalNote(
        appointment_id=appointment_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
    )
    db.add(note)
    await db.flush()
    await db.refresh(note)

    audit = NoteAuditLog(
        note_id=note.id,
        changed_by=doctor_id,
        change_type="created",
        old_values=None,
        new_values={
            "appointment_id": str(appointment_id),
            "patient_id": str(patient_id),
            "doctor_id": str(doctor_id),
        },
    )
    db.add(audit)
    await db.flush()

    return note

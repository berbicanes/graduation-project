import uuid
from datetime import datetime

from pydantic import BaseModel


class NoteCreate(BaseModel):
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None


class NoteUpdate(BaseModel):
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None


class NoteResponse(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    subjective: str | None
    objective: str | None
    assessment: str | None
    plan: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedNoteResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[NoteResponse]


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    note_id: uuid.UUID
    changed_by: uuid.UUID
    change_type: str
    old_values: dict | None
    new_values: dict | None
    changed_at: datetime

    model_config = {"from_attributes": True}

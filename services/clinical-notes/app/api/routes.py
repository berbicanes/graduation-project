import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, require_role
from app.crud import create_note, get_note_by_id, get_note_history, list_notes, update_note
from app.db import get_db
from app.schemas import AuditLogResponse, NoteCreate, NoteResponse, NoteUpdate, PaginatedNoteResponse

router = APIRouter(prefix="/notes", tags=["clinical-notes"])


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create(
    body: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "doctor")),
) -> NoteResponse:
    note = await create_note(db, body, changed_by=current_user.id)
    return NoteResponse.model_validate(note)


@router.get("", response_model=PaginatedNoteResponse)
async def list_all(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    patient_id: uuid.UUID | None = Query(None),
    appointment_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PaginatedNoteResponse:
    notes, total = await list_notes(
        db, page=page, per_page=per_page, patient_id=patient_id, appointment_id=appointment_id
    )
    return PaginatedNoteResponse(
        total=total,
        page=page,
        per_page=per_page,
        items=[NoteResponse.model_validate(n) for n in notes],
    )


@router.get("/{note_id}", response_model=NoteResponse)
async def get_one(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> NoteResponse:
    note = await get_note_by_id(db, note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical note not found")
    return NoteResponse.model_validate(note)


@router.put("/{note_id}", response_model=NoteResponse)
async def update(
    note_id: uuid.UUID,
    body: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "doctor")),
) -> NoteResponse:
    note = await get_note_by_id(db, note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical note not found")
    note = await update_note(db, note, body, changed_by=current_user.id)
    return NoteResponse.model_validate(note)


@router.get("/{note_id}/history", response_model=list[AuditLogResponse])
async def history(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "doctor", "nurse")),
) -> list[AuditLogResponse]:
    note = await get_note_by_id(db, note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinical note not found")
    audit_logs = await get_note_history(db, note_id)
    return [AuditLogResponse.model_validate(log) for log in audit_logs]

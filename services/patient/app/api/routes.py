import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, require_role
from app.crud import create_patient, get_patient_by_id, list_patients, soft_delete_patient, update_patient
from app.db import get_db
from app.events.publisher import publish_event
from app.schemas import PaginatedResponse, PatientCreate, PatientResponse, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create(
    body: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "doctor", "nurse", "receptionist")),
) -> PatientResponse:
    patient = await create_patient(db, body)
    await publish_event(
        "patient.created", {"id": str(patient.id), "first_name": patient.first_name, "last_name": patient.last_name}
    )
    return PatientResponse.model_validate(patient)


@router.get("", response_model=PaginatedResponse)
async def list_all(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PaginatedResponse:
    patients, total = await list_patients(db, page=page, per_page=per_page, search=search)
    return PaginatedResponse(
        total=total,
        page=page,
        per_page=per_page,
        items=[PatientResponse.model_validate(p) for p in patients],
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_one(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PatientResponse:
    patient = await get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return PatientResponse.model_validate(patient)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update(
    patient_id: uuid.UUID,
    body: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "doctor", "nurse", "receptionist")),
) -> PatientResponse:
    patient = await get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    patient = await update_patient(db, patient, body)
    await publish_event(
        "patient.updated", {"id": str(patient.id), "first_name": patient.first_name, "last_name": patient.last_name}
    )
    return PatientResponse.model_validate(patient)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
) -> None:
    patient = await get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    await soft_delete_patient(db, patient)


@router.get("/{patient_id}/history")
async def get_history(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "doctor", "nurse")),
) -> dict:
    patient = await get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return {
        "patient_id": str(patient_id),
        "appointments": [],
        "clinical_notes": [],
        "invoices": [],
    }

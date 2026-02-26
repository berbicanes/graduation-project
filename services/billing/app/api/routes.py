import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, get_current_user, require_role
from app.crud import create_invoice, get_billing_summary, get_invoice_by_id, list_invoices, mark_invoice_paid
from app.db import get_db
from app.schemas import BillingSummary, InvoiceCreate, InvoiceResponse, PaginatedInvoiceResponse

router = APIRouter(tags=["billing"])


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create(
    body: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "nurse", "receptionist")),
) -> InvoiceResponse:
    invoice = await create_invoice(db, body)
    return InvoiceResponse.model_validate(invoice)


@router.get("/invoices", response_model=PaginatedInvoiceResponse)
async def list_all(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    patient_id: uuid.UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> PaginatedInvoiceResponse:
    invoices, total = await list_invoices(db, page=page, per_page=per_page, patient_id=patient_id, status=status_filter)
    return PaginatedInvoiceResponse(
        total=total,
        page=page,
        per_page=per_page,
        items=[InvoiceResponse.model_validate(inv) for inv in invoices],
    )


@router.get("/billing/summary", response_model=BillingSummary)
async def summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "nurse", "receptionist")),
) -> BillingSummary:
    data = await get_billing_summary(db)
    return BillingSummary(**data)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_one(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> InvoiceResponse:
    invoice = await get_invoice_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return InvoiceResponse.model_validate(invoice)


@router.patch("/invoices/{invoice_id}/pay", response_model=InvoiceResponse)
async def pay(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin", "nurse", "receptionist")),
) -> InvoiceResponse:
    invoice = await get_invoice_by_id(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    if invoice.status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invoice is already paid")
    invoice = await mark_invoice_paid(db, invoice)
    return InvoiceResponse.model_validate(invoice)

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Invoice, LineItem
from app.schemas import InvoiceCreate


async def create_invoice(db: AsyncSession, data: InvoiceCreate) -> Invoice:
    invoice_data = data.model_dump(exclude={"line_items"})
    invoice = Invoice(**invoice_data)
    db.add(invoice)
    await db.flush()

    if data.line_items:
        for item_data in data.line_items:
            line_item = LineItem(invoice_id=invoice.id, **item_data.model_dump())
            db.add(line_item)
        await db.flush()

    await db.refresh(invoice)
    # Eager load line_items after refresh
    result = await db.execute(select(Invoice).where(Invoice.id == invoice.id).options(selectinload(Invoice.line_items)))
    return result.scalar_one()


async def get_invoice_by_id(db: AsyncSession, invoice_id: uuid.UUID) -> Invoice | None:
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id).options(selectinload(Invoice.line_items)))
    return result.scalar_one_or_none()


async def list_invoices(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    patient_id: uuid.UUID | None = None,
    status: str | None = None,
) -> tuple[list[Invoice], int]:
    query = select(Invoice)

    if patient_id:
        query = query.where(Invoice.patient_id == patient_id)
    if status:
        query = query.where(Invoice.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        query.options(selectinload(Invoice.line_items))
        .order_by(Invoice.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(query)
    invoices = list(result.scalars().all())

    return invoices, total


async def mark_invoice_paid(db: AsyncSession, invoice: Invoice) -> Invoice:
    invoice.status = "paid"
    invoice.paid_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(invoice)
    # Reload with line_items
    result = await db.execute(select(Invoice).where(Invoice.id == invoice.id).options(selectinload(Invoice.line_items)))
    return result.scalar_one()


async def get_billing_summary(db: AsyncSession) -> dict:
    total_result = await db.execute(select(func.count()).select_from(Invoice))
    total_invoices = total_result.scalar_one()

    revenue_result = await db.execute(
        select(func.coalesce(func.sum(Invoice.amount), Decimal("0.00"))).where(Invoice.status == "paid")
    )
    total_revenue = revenue_result.scalar_one()

    paid_result = await db.execute(
        select(func.count()).select_from(select(Invoice).where(Invoice.status == "paid").subquery())
    )
    total_paid = paid_result.scalar_one()

    draft_result = await db.execute(
        select(func.count()).select_from(select(Invoice).where(Invoice.status == "draft").subquery())
    )
    total_draft = draft_result.scalar_one()

    issued_result = await db.execute(
        select(func.count()).select_from(select(Invoice).where(Invoice.status == "issued").subquery())
    )
    total_issued = issued_result.scalar_one()

    overdue_result = await db.execute(
        select(func.count()).select_from(select(Invoice).where(Invoice.status == "overdue").subquery())
    )
    total_overdue = overdue_result.scalar_one()

    return {
        "total_invoices": total_invoices,
        "total_revenue": total_revenue,
        "total_paid": total_paid,
        "total_draft": total_draft,
        "total_issued": total_issued,
        "total_overdue": total_overdue,
    }


async def create_draft_invoice(
    db: AsyncSession,
    appointment_id: uuid.UUID,
    patient_id: uuid.UUID,
) -> Invoice:
    """Create a draft invoice from an appointment.created event."""
    invoice = Invoice(
        appointment_id=appointment_id,
        patient_id=patient_id,
        amount=Decimal("0.00"),
        status="draft",
    )
    db.add(invoice)
    await db.flush()
    await db.refresh(invoice)
    return invoice

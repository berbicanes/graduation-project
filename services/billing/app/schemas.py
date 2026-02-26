import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LineItemCreate(BaseModel):
    description: str = Field(min_length=1, max_length=255)
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(ge=0, decimal_places=2)


class LineItemResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    description: str
    quantity: int
    unit_price: Decimal

    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    amount: Decimal = Field(ge=0, decimal_places=2)
    status: str = Field(default="draft", pattern=r"^(draft|issued|paid|overdue)$")
    line_items: list[LineItemCreate] | None = None


class InvoiceUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    status: str | None = Field(default=None, pattern=r"^(draft|issued|paid|overdue)$")


class InvoiceResponse(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    amount: Decimal
    status: str
    issued_at: datetime | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime
    line_items: list[LineItemResponse]

    model_config = {"from_attributes": True}


class PaginatedInvoiceResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[InvoiceResponse]


class BillingSummary(BaseModel):
    total_invoices: int
    total_revenue: Decimal
    total_paid: int
    total_draft: int
    total_issued: int
    total_overdue: int

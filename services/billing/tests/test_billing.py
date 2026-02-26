import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

APPOINTMENT_ID = str(uuid.uuid4())
PATIENT_ID = str(uuid.uuid4())


def make_invoice_data(
    appointment_id: str = APPOINTMENT_ID,
    patient_id: str = PATIENT_ID,
    amount: str = "150.00",
    status: str = "issued",
) -> dict:
    return {
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "amount": amount,
        "status": status,
    }


def make_invoice_with_items(
    appointment_id: str = APPOINTMENT_ID,
    patient_id: str = PATIENT_ID,
) -> dict:
    return {
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "amount": "250.00",
        "status": "issued",
        "line_items": [
            {"description": "Consultation", "quantity": 1, "unit_price": "150.00"},
            {"description": "Lab work", "quantity": 2, "unit_price": "50.00"},
        ],
    }


async def create_invoice(client: AsyncClient, headers: dict, data: dict | None = None) -> dict:
    response = await client.post("/invoices", json=data or make_invoice_data(), headers=headers)
    return response.json()


class TestCreateInvoice:
    async def test_create_success(self, client: AsyncClient, auth_headers: dict):
        data = make_invoice_data()
        response = await client.post("/invoices", json=data, headers=auth_headers)
        assert response.status_code == 201
        result = response.json()
        assert result["appointment_id"] == APPOINTMENT_ID
        assert result["patient_id"] == PATIENT_ID
        assert Decimal(result["amount"]) == Decimal("150.00")
        assert result["status"] == "issued"
        assert result["line_items"] == []
        assert "id" in result

    async def test_create_with_line_items(self, client: AsyncClient, auth_headers: dict):
        data = make_invoice_with_items()
        response = await client.post("/invoices", json=data, headers=auth_headers)
        assert response.status_code == 201
        result = response.json()
        assert len(result["line_items"]) == 2
        assert result["line_items"][0]["description"] == "Consultation"
        assert result["line_items"][1]["description"] == "Lab work"
        assert result["line_items"][1]["quantity"] == 2

    async def test_create_draft(self, client: AsyncClient, auth_headers: dict):
        data = make_invoice_data(amount="0.00", status="draft")
        response = await client.post("/invoices", json=data, headers=auth_headers)
        assert response.status_code == 201
        result = response.json()
        assert result["status"] == "draft"
        assert Decimal(result["amount"]) == Decimal("0.00")

    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post("/invoices", json=make_invoice_data())
        assert response.status_code == 403

    async def test_create_allowed_for_nurse(self, client: AsyncClient, nurse_headers: dict):
        response = await client.post("/invoices", json=make_invoice_data(), headers=nurse_headers)
        assert response.status_code == 201

    async def test_create_allowed_for_receptionist(self, client: AsyncClient, receptionist_headers: dict):
        response = await client.post("/invoices", json=make_invoice_data(), headers=receptionist_headers)
        assert response.status_code == 201

    async def test_create_forbidden_for_doctor(self, client: AsyncClient, doctor_headers: dict):
        response = await client.post("/invoices", json=make_invoice_data(), headers=doctor_headers)
        assert response.status_code == 403

    async def test_create_forbidden_for_patient(self, client: AsyncClient, patient_role_headers: dict):
        response = await client.post("/invoices", json=make_invoice_data(), headers=patient_role_headers)
        assert response.status_code == 403


class TestListInvoices:
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/invoices", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["per_page"] == 20

    async def test_list_with_invoices(self, client: AsyncClient, auth_headers: dict):
        await create_invoice(client, auth_headers)
        await create_invoice(client, auth_headers, make_invoice_data(appointment_id=str(uuid.uuid4())))

        response = await client.get("/invoices", headers=auth_headers)
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_filter_by_patient(self, client: AsyncClient, auth_headers: dict):
        await create_invoice(client, auth_headers)
        other_patient = str(uuid.uuid4())
        await create_invoice(client, auth_headers, make_invoice_data(patient_id=other_patient, appointment_id=str(uuid.uuid4())))

        response = await client.get(f"/invoices?patient_id={PATIENT_ID}", headers=auth_headers)
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["patient_id"] == PATIENT_ID

    async def test_list_filter_by_status(self, client: AsyncClient, auth_headers: dict):
        await create_invoice(client, auth_headers, make_invoice_data(status="issued"))
        await create_invoice(client, auth_headers, make_invoice_data(status="draft", appointment_id=str(uuid.uuid4())))

        response = await client.get("/invoices?status=draft", headers=auth_headers)
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "draft"

    async def test_list_pagination(self, client: AsyncClient, auth_headers: dict):
        for _ in range(3):
            await create_invoice(client, auth_headers, make_invoice_data(appointment_id=str(uuid.uuid4())))

        response = await client.get("/invoices?page=1&per_page=2", headers=auth_headers)
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

        response = await client.get("/invoices?page=2&per_page=2", headers=auth_headers)
        data = response.json()
        assert len(data["items"]) == 1

    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/invoices")
        assert response.status_code == 403


class TestGetInvoice:
    async def test_get_success(self, client: AsyncClient, auth_headers: dict):
        created = await create_invoice(client, auth_headers)
        invoice_id = created["id"]

        response = await client.get(f"/invoices/{invoice_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == invoice_id

    async def test_get_with_line_items(self, client: AsyncClient, auth_headers: dict):
        created = await create_invoice(client, auth_headers, make_invoice_with_items())
        invoice_id = created["id"]

        response = await client.get(f"/invoices/{invoice_id}", headers=auth_headers)
        assert response.status_code == 200
        result = response.json()
        assert len(result["line_items"]) == 2

    async def test_get_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"/invoices/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404


class TestPayInvoice:
    async def test_pay_success(self, client: AsyncClient, auth_headers: dict):
        created = await create_invoice(client, auth_headers)
        invoice_id = created["id"]

        response = await client.patch(f"/invoices/{invoice_id}/pay", headers=auth_headers)
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "paid"
        assert result["paid_at"] is not None

    async def test_pay_already_paid(self, client: AsyncClient, auth_headers: dict):
        created = await create_invoice(client, auth_headers)
        invoice_id = created["id"]

        await client.patch(f"/invoices/{invoice_id}/pay", headers=auth_headers)
        response = await client.patch(f"/invoices/{invoice_id}/pay", headers=auth_headers)
        assert response.status_code == 400
        assert "already paid" in response.json()["detail"].lower()

    async def test_pay_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.patch(f"/invoices/{uuid.uuid4()}/pay", headers=auth_headers)
        assert response.status_code == 404

    async def test_pay_forbidden_for_patient(self, client: AsyncClient, auth_headers: dict, patient_role_headers: dict):
        created = await create_invoice(client, auth_headers)
        invoice_id = created["id"]

        response = await client.patch(f"/invoices/{invoice_id}/pay", headers=patient_role_headers)
        assert response.status_code == 403


class TestBillingSummary:
    async def test_summary_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/billing/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_invoices"] == 0
        assert Decimal(data["total_revenue"]) == Decimal("0.00")
        assert data["total_paid"] == 0
        assert data["total_draft"] == 0

    async def test_summary_with_data(self, client: AsyncClient, auth_headers: dict):
        # Create an issued invoice and pay it
        created = await create_invoice(client, auth_headers, make_invoice_data(amount="100.00", status="issued"))
        await client.patch(f"/invoices/{created['id']}/pay", headers=auth_headers)

        # Create a draft invoice
        await create_invoice(client, auth_headers, make_invoice_data(amount="50.00", status="draft", appointment_id=str(uuid.uuid4())))

        response = await client.get("/billing/summary", headers=auth_headers)
        data = response.json()
        assert data["total_invoices"] == 2
        assert Decimal(data["total_revenue"]) == Decimal("100.00")
        assert data["total_paid"] == 1
        assert data["total_draft"] == 1

    async def test_summary_forbidden_for_patient(self, client: AsyncClient, patient_role_headers: dict):
        response = await client.get("/billing/summary", headers=patient_role_headers)
        assert response.status_code == 403

    async def test_summary_forbidden_for_doctor(self, client: AsyncClient, doctor_headers: dict):
        response = await client.get("/billing/summary", headers=doctor_headers)
        assert response.status_code == 403


class TestHealth:
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

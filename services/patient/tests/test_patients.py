import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

PATIENT_DATA = {
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1990-05-15",
    "gender": "male",
    "phone": "+1234567890",
    "email": "john.doe@example.com",
    "address": "123 Main St",
    "emergency_contact_name": "Jane Doe",
    "emergency_contact_phone": "+0987654321",
    "blood_type": "A+",
    "allergies": ["penicillin", "peanuts"],
}


async def create_patient(client: AsyncClient, headers: dict, data: dict | None = None) -> dict:
    response = await client.post("/patients", json=data or PATIENT_DATA, headers=headers)
    return response.json()


class TestCreatePatient:
    async def test_create_success(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/patients", json=PATIENT_DATA, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["date_of_birth"] == "1990-05-15"
        assert data["blood_type"] == "A+"
        assert data["allergies"] == ["penicillin", "peanuts"]
        assert data["is_active"] is True
        assert "id" in data

    async def test_create_minimal(self, client: AsyncClient, auth_headers: dict):
        minimal = {"first_name": "Jane", "last_name": "Smith", "date_of_birth": "1985-01-01"}
        response = await client.post("/patients", json=minimal, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["gender"] is None
        assert data["allergies"] is None

    async def test_create_invalid_data(self, client: AsyncClient, auth_headers: dict):
        response = await client.post("/patients", json={"first_name": "X"}, headers=auth_headers)
        assert response.status_code == 422

    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post("/patients", json=PATIENT_DATA)
        assert response.status_code == 403

    async def test_create_forbidden_for_patient_role(self, client: AsyncClient, patient_role_headers: dict):
        response = await client.post("/patients", json=PATIENT_DATA, headers=patient_role_headers)
        assert response.status_code == 403

    async def test_create_allowed_for_doctor(self, client: AsyncClient, doctor_headers: dict):
        response = await client.post("/patients", json=PATIENT_DATA, headers=doctor_headers)
        assert response.status_code == 201


class TestListPatients:
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/patients", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["per_page"] == 20

    async def test_list_with_patients(self, client: AsyncClient, auth_headers: dict):
        await create_patient(client, auth_headers)
        await create_patient(client, auth_headers, {**PATIENT_DATA, "first_name": "Jane", "email": "jane@test.com"})

        response = await client.get("/patients", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_pagination(self, client: AsyncClient, auth_headers: dict):
        for i in range(3):
            await create_patient(
                client, auth_headers, {**PATIENT_DATA, "first_name": f"Patient{i}", "email": f"p{i}@test.com"}
            )

        response = await client.get("/patients?page=1&per_page=2", headers=auth_headers)
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1

        response = await client.get("/patients?page=2&per_page=2", headers=auth_headers)
        data = response.json()
        assert len(data["items"]) == 1
        assert data["page"] == 2

    async def test_list_search(self, client: AsyncClient, auth_headers: dict):
        await create_patient(client, auth_headers)
        await create_patient(
            client,
            auth_headers,
            {**PATIENT_DATA, "first_name": "Alice", "last_name": "Wonder", "email": "alice@test.com"},
        )

        response = await client.get("/patients?search=Alice", headers=auth_headers)
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["first_name"] == "Alice"

    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/patients")
        assert response.status_code == 403


class TestGetPatient:
    async def test_get_success(self, client: AsyncClient, auth_headers: dict):
        created = await create_patient(client, auth_headers)
        patient_id = created["id"]

        response = await client.get(f"/patients/{patient_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == patient_id

    async def test_get_not_found(self, client: AsyncClient, auth_headers: dict):
        import uuid

        response = await client.get(f"/patients/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404


class TestUpdatePatient:
    async def test_update_success(self, client: AsyncClient, auth_headers: dict):
        created = await create_patient(client, auth_headers)
        patient_id = created["id"]

        response = await client.put(
            f"/patients/{patient_id}",
            json={"first_name": "Updated", "phone": "+111111"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["phone"] == "+111111"
        assert data["last_name"] == "Doe"  # Unchanged

    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        import uuid

        response = await client.put(f"/patients/{uuid.uuid4()}", json={"first_name": "X"}, headers=auth_headers)
        assert response.status_code == 404


class TestDeletePatient:
    async def test_soft_delete(self, client: AsyncClient, auth_headers: dict):
        created = await create_patient(client, auth_headers)
        patient_id = created["id"]

        response = await client.delete(f"/patients/{patient_id}", headers=auth_headers)
        assert response.status_code == 204

        # Should not be found after soft delete
        response = await client.get(f"/patients/{patient_id}", headers=auth_headers)
        assert response.status_code == 404

    async def test_delete_requires_admin(self, client: AsyncClient, auth_headers: dict, doctor_headers: dict):
        created = await create_patient(client, auth_headers)
        patient_id = created["id"]

        response = await client.delete(f"/patients/{patient_id}", headers=doctor_headers)
        assert response.status_code == 403


class TestPatientHistory:
    async def test_history_stub(self, client: AsyncClient, auth_headers: dict):
        created = await create_patient(client, auth_headers)
        patient_id = created["id"]

        response = await client.get(f"/patients/{patient_id}/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == patient_id
        assert data["appointments"] == []
        assert data["clinical_notes"] == []
        assert data["invoices"] == []


class TestHealth:
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

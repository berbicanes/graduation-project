import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

APPOINTMENT_ID = str(uuid.uuid4())
PATIENT_ID = str(uuid.uuid4())
DOCTOR_ID = str(uuid.uuid4())


def make_note_data(
    appointment_id: str = APPOINTMENT_ID,
    patient_id: str = PATIENT_ID,
    doctor_id: str = DOCTOR_ID,
) -> dict:
    return {
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "subjective": "Patient reports headache for 3 days",
        "objective": "BP 120/80, temp 98.6F",
        "assessment": "Tension headache",
        "plan": "Prescribe ibuprofen, follow up in 1 week",
    }


async def create_note(client: AsyncClient, headers: dict, data: dict | None = None) -> dict:
    response = await client.post("/notes", json=data or make_note_data(), headers=headers)
    return response.json()


class TestCreateNote:
    async def test_create_success(self, client: AsyncClient, auth_headers: dict):
        data = make_note_data()
        response = await client.post("/notes", json=data, headers=auth_headers)
        assert response.status_code == 201
        result = response.json()
        assert result["appointment_id"] == APPOINTMENT_ID
        assert result["patient_id"] == PATIENT_ID
        assert result["doctor_id"] == DOCTOR_ID
        assert result["subjective"] == "Patient reports headache for 3 days"
        assert result["assessment"] == "Tension headache"
        assert "id" in result

    async def test_create_minimal(self, client: AsyncClient, auth_headers: dict):
        data = {
            "appointment_id": str(uuid.uuid4()),
            "patient_id": str(uuid.uuid4()),
            "doctor_id": str(uuid.uuid4()),
        }
        response = await client.post("/notes", json=data, headers=auth_headers)
        assert response.status_code == 201
        result = response.json()
        assert result["subjective"] is None
        assert result["objective"] is None
        assert result["assessment"] is None
        assert result["plan"] is None

    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post("/notes", json=make_note_data())
        assert response.status_code == 403

    async def test_create_allowed_for_doctor(self, client: AsyncClient, doctor_headers: dict):
        response = await client.post("/notes", json=make_note_data(), headers=doctor_headers)
        assert response.status_code == 201

    async def test_create_forbidden_for_patient(self, client: AsyncClient, patient_role_headers: dict):
        response = await client.post("/notes", json=make_note_data(), headers=patient_role_headers)
        assert response.status_code == 403

    async def test_create_forbidden_for_nurse(self, client: AsyncClient, nurse_headers: dict):
        response = await client.post("/notes", json=make_note_data(), headers=nurse_headers)
        assert response.status_code == 403


class TestListNotes:
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/notes", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["per_page"] == 20

    async def test_list_with_notes(self, client: AsyncClient, auth_headers: dict):
        await create_note(client, auth_headers)
        await create_note(client, auth_headers, make_note_data(appointment_id=str(uuid.uuid4())))

        response = await client.get("/notes", headers=auth_headers)
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    async def test_list_filter_by_patient(self, client: AsyncClient, auth_headers: dict):
        await create_note(client, auth_headers)
        other_patient = str(uuid.uuid4())
        await create_note(
            client, auth_headers, make_note_data(patient_id=other_patient, appointment_id=str(uuid.uuid4()))
        )

        response = await client.get(f"/notes?patient_id={PATIENT_ID}", headers=auth_headers)
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["patient_id"] == PATIENT_ID

    async def test_list_filter_by_appointment(self, client: AsyncClient, auth_headers: dict):
        await create_note(client, auth_headers)
        other_appt = str(uuid.uuid4())
        await create_note(client, auth_headers, make_note_data(appointment_id=other_appt))

        response = await client.get(f"/notes?appointment_id={APPOINTMENT_ID}", headers=auth_headers)
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["appointment_id"] == APPOINTMENT_ID

    async def test_list_pagination(self, client: AsyncClient, auth_headers: dict):
        for _ in range(3):
            await create_note(client, auth_headers, make_note_data(appointment_id=str(uuid.uuid4())))

        response = await client.get("/notes?page=1&per_page=2", headers=auth_headers)
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2

        response = await client.get("/notes?page=2&per_page=2", headers=auth_headers)
        data = response.json()
        assert len(data["items"]) == 1

    async def test_list_requires_auth(self, client: AsyncClient):
        response = await client.get("/notes")
        assert response.status_code == 403


class TestGetNote:
    async def test_get_success(self, client: AsyncClient, auth_headers: dict):
        created = await create_note(client, auth_headers)
        note_id = created["id"]

        response = await client.get(f"/notes/{note_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == note_id

    async def test_get_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"/notes/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateNote:
    async def test_update_success(self, client: AsyncClient, auth_headers: dict):
        created = await create_note(client, auth_headers)
        note_id = created["id"]

        response = await client.put(
            f"/notes/{note_id}",
            json={"subjective": "Updated symptoms", "assessment": "Migraine"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["subjective"] == "Updated symptoms"
        assert data["assessment"] == "Migraine"
        assert data["objective"] == "BP 120/80, temp 98.6F"  # Unchanged

    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.put(
            f"/notes/{uuid.uuid4()}",
            json={"subjective": "X"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_update_forbidden_for_patient(
        self, client: AsyncClient, auth_headers: dict, patient_role_headers: dict
    ):
        created = await create_note(client, auth_headers)
        note_id = created["id"]

        response = await client.put(
            f"/notes/{note_id}",
            json={"subjective": "Hacked"},
            headers=patient_role_headers,
        )
        assert response.status_code == 403


class TestNoteHistory:
    async def test_history_after_create(self, client: AsyncClient, auth_headers: dict):
        created = await create_note(client, auth_headers)
        note_id = created["id"]

        response = await client.get(f"/notes/{note_id}/history", headers=auth_headers)
        assert response.status_code == 200
        history = response.json()
        assert len(history) == 1
        assert history[0]["change_type"] == "created"

    async def test_history_after_update(self, client: AsyncClient, auth_headers: dict):
        created = await create_note(client, auth_headers)
        note_id = created["id"]

        await client.put(
            f"/notes/{note_id}",
            json={"subjective": "Updated symptoms"},
            headers=auth_headers,
        )

        response = await client.get(f"/notes/{note_id}/history", headers=auth_headers)
        assert response.status_code == 200
        history = response.json()
        assert len(history) == 2
        # Find each entry by change_type (order may vary when timestamps match)
        types = {h["change_type"] for h in history}
        assert types == {"created", "updated"}
        updated_entry = next(h for h in history if h["change_type"] == "updated")
        assert updated_entry["old_values"]["subjective"] == "Patient reports headache for 3 days"
        assert updated_entry["new_values"]["subjective"] == "Updated symptoms"

    async def test_history_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"/notes/{uuid.uuid4()}/history", headers=auth_headers)
        assert response.status_code == 404

    async def test_history_allowed_for_nurse(self, client: AsyncClient, auth_headers: dict, nurse_headers: dict):
        created = await create_note(client, auth_headers)
        note_id = created["id"]

        response = await client.get(f"/notes/{note_id}/history", headers=nurse_headers)
        assert response.status_code == 200

    async def test_history_forbidden_for_patient(
        self, client: AsyncClient, auth_headers: dict, patient_role_headers: dict
    ):
        created = await create_note(client, auth_headers)
        note_id = created["id"]

        response = await client.get(f"/notes/{note_id}/history", headers=patient_role_headers)
        assert response.status_code == 403


class TestHealth:
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

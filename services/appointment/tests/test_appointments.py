import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

PATIENT_ID = str(uuid.uuid4())
DOCTOR_ID = str(uuid.uuid4())


def make_appointment_data(
    patient_id: str = PATIENT_ID,
    doctor_id: str = DOCTOR_ID,
    hours_from_now: int = 24,
    duration_minutes: int = 30,
    reason: str = "Routine checkup",
) -> dict:
    scheduled = datetime.now(UTC) + timedelta(hours=hours_from_now)
    return {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "scheduled_at": scheduled.isoformat(),
        "duration_minutes": duration_minutes,
        "reason": reason,
    }


async def create_appointment(client: AsyncClient, headers: dict, data: dict | None = None) -> dict:
    response = await client.post("/appointments", json=data or make_appointment_data(), headers=headers)
    return response.json()


class TestCreateAppointment:
    async def test_create_success(self, client: AsyncClient, auth_headers: dict):
        data = make_appointment_data()
        response = await client.post("/appointments", json=data, headers=auth_headers)
        assert response.status_code == 201
        result = response.json()
        assert result["patient_id"] == PATIENT_ID
        assert result["doctor_id"] == DOCTOR_ID
        assert result["status"] == "scheduled"
        assert result["duration_minutes"] == 30
        assert "id" in result

    async def test_create_requires_auth(self, client: AsyncClient):
        response = await client.post("/appointments", json=make_appointment_data())
        assert response.status_code == 403

    async def test_create_forbidden_for_patient(self, client: AsyncClient, patient_role_headers: dict):
        response = await client.post("/appointments", json=make_appointment_data(), headers=patient_role_headers)
        assert response.status_code == 403

    async def test_create_conflict(self, client: AsyncClient, auth_headers: dict):
        data = make_appointment_data(hours_from_now=48)
        response = await client.post("/appointments", json=data, headers=auth_headers)
        assert response.status_code == 201

        # Same doctor, same time
        response = await client.post("/appointments", json=data, headers=auth_headers)
        assert response.status_code == 409
        assert "conflict" in response.json()["detail"].lower()

    async def test_create_no_conflict_different_doctor(self, client: AsyncClient, auth_headers: dict):
        data = make_appointment_data(hours_from_now=72)
        await client.post("/appointments", json=data, headers=auth_headers)

        data2 = make_appointment_data(doctor_id=str(uuid.uuid4()), hours_from_now=72)
        response = await client.post("/appointments", json=data2, headers=auth_headers)
        assert response.status_code == 201


class TestListAppointments:
    async def test_list_empty(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/appointments", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_list_with_filters(self, client: AsyncClient, auth_headers: dict):
        await create_appointment(client, auth_headers)
        other_patient = str(uuid.uuid4())
        await create_appointment(
            client, auth_headers, make_appointment_data(patient_id=other_patient, hours_from_now=96)
        )

        response = await client.get(f"/appointments?patient_id={PATIENT_ID}", headers=auth_headers)
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["patient_id"] == PATIENT_ID


class TestGetAppointment:
    async def test_get_success(self, client: AsyncClient, auth_headers: dict):
        created = await create_appointment(client, auth_headers)
        appt_id = created["id"]

        response = await client.get(f"/appointments/{appt_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == appt_id

    async def test_get_not_found(self, client: AsyncClient, auth_headers: dict):
        response = await client.get(f"/appointments/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404


class TestReschedule:
    async def test_reschedule_success(self, client: AsyncClient, auth_headers: dict):
        created = await create_appointment(client, auth_headers)
        appt_id = created["id"]

        new_time = (datetime.now(UTC) + timedelta(hours=120)).isoformat()
        response = await client.put(
            f"/appointments/{appt_id}",
            json={"scheduled_at": new_time},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["scheduled_at"] != created["scheduled_at"]

    async def test_reschedule_cancelled_fails(self, client: AsyncClient, auth_headers: dict):
        created = await create_appointment(client, auth_headers)
        appt_id = created["id"]

        await client.patch(f"/appointments/{appt_id}/cancel", headers=auth_headers)

        new_time = (datetime.now(UTC) + timedelta(hours=120)).isoformat()
        response = await client.put(
            f"/appointments/{appt_id}",
            json={"scheduled_at": new_time},
            headers=auth_headers,
        )
        assert response.status_code == 400


class TestCancelAppointment:
    async def test_cancel_success(self, client: AsyncClient, auth_headers: dict):
        created = await create_appointment(client, auth_headers)
        appt_id = created["id"]

        response = await client.patch(f"/appointments/{appt_id}/cancel", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_cancel_already_cancelled(self, client: AsyncClient, auth_headers: dict):
        created = await create_appointment(client, auth_headers)
        appt_id = created["id"]

        await client.patch(f"/appointments/{appt_id}/cancel", headers=auth_headers)
        response = await client.patch(f"/appointments/{appt_id}/cancel", headers=auth_headers)
        assert response.status_code == 400


class TestAvailability:
    async def test_set_and_get_availability(self, client: AsyncClient, auth_headers: dict):
        avail_data = {
            "doctor_id": DOCTOR_ID,
            "day_of_week": 0,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        }
        response = await client.post("/appointments/availability", json=avail_data, headers=auth_headers)
        assert response.status_code == 201

        response = await client.get(f"/appointments/availability?doctor_id={DOCTOR_ID}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["day_of_week"] == 0


class TestHealth:
    async def test_health(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

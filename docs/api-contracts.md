# API Contracts

All services are accessed through the Traefik API gateway at `http://localhost` (port 80).

## Conventions

- **Content-Type**: `application/json`
- **Authentication**: `Authorization: Bearer <jwt_token>` (required unless noted)
- **IDs**: UUID format
- **Timestamps**: ISO 8601 with timezone (`2026-03-11T10:30:00Z`)
- **Pagination**: `?page=1&per_page=20` — response includes `total`, `page`, `per_page`, `items`
- **Soft deletes**: Records set `is_active = false`

### Error Response Format

```json
{
  "detail": "Human-readable error message"
}
```

### Roles

| Role           | Description                                    |
|----------------|------------------------------------------------|
| `admin`        | Full access to all operations                  |
| `doctor`       | Clinical operations, notes, availability       |
| `nurse`        | Patient care, history, appointments, invoices  |
| `receptionist` | Patient registration, appointments, invoices   |
| `patient`      | Read-only access to own data                   |

---

## Auth Service — `/auth`

### POST `/auth/register`
Register a new user. **No auth required.**

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe",
  "role": "patient"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "patient",
  "is_active": true,
  "created_at": "2026-03-11T10:00:00Z"
}
```

### POST `/auth/login`
Authenticate and receive JWT tokens. **No auth required.**

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### POST `/auth/refresh`
Get a new access token using a refresh token. **No auth required.**

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response (200):**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### GET `/auth/me`
Get the current authenticated user's profile. **Auth required.**

**Response (200):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "patient",
  "is_active": true,
  "created_at": "2026-03-11T10:00:00Z"
}
```

### GET `/auth/verify`
Validate JWT token (used internally by Traefik ForwardAuth). **Auth required.**

**Response (200):**
```json
{
  "status": "authenticated"
}
```

Response headers: `X-User-Id`, `X-User-Role`, `X-User-Email`

---

## Patient Service — `/patients`

### POST `/patients`
Create a new patient record. **Roles: admin, doctor, nurse, receptionist**

**Request:**
```json
{
  "first_name": "Alice",
  "last_name": "Johnson",
  "date_of_birth": "1985-03-15",
  "gender": "female",
  "phone": "+1-555-0101",
  "email": "alice@email.com",
  "address": "123 Main St",
  "emergency_contact_name": "Bob Johnson",
  "emergency_contact_phone": "+1-555-0102",
  "blood_type": "A+",
  "allergies": ["penicillin"]
}
```

**Response (201):** Full patient object with `id`, `created_at`, `updated_at`, `is_active`.

### GET `/patients`
List patients with pagination and search. **Auth required (any role).**

**Query params:** `page`, `per_page`, `search` (searches first_name, last_name, email)

**Response (200):**
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### GET `/patients/{id}`
Get patient details by ID. **Auth required (any role).**

**Response (200):** Full patient object.

### PUT `/patients/{id}`
Update patient information. **Roles: admin, doctor, nurse, receptionist**

**Request:** Same as POST (partial updates supported).

**Response (200):** Updated patient object.

### DELETE `/patients/{id}`
Soft-delete a patient. **Roles: admin only.**

**Response (204):** No content.

### GET `/patients/{id}/history`
Get medical history summary for a patient. **Roles: admin, doctor, nurse**

**Response (200):**
```json
{
  "patient_id": "uuid",
  "appointments": [...],
  "notes_count": 5,
  "invoices_count": 3
}
```

---

## Appointment Service — `/appointments`

### POST `/appointments`
Create a new appointment. **Roles: admin, doctor, nurse, receptionist**

Publishes `appointment.created` event (triggers clinical note stub + draft invoice).

**Request:**
```json
{
  "patient_id": "uuid",
  "doctor_id": "uuid",
  "scheduled_at": "2026-03-15T09:00:00Z",
  "duration_minutes": 30,
  "reason": "Annual physical examination"
}
```

**Response (201):** Full appointment object with `id`, `status` ("scheduled"), timestamps.

### GET `/appointments`
List appointments with filters. **Auth required (any role).**

**Query params:** `page`, `per_page`, `patient_id`, `doctor_id`, `status`

**Response (200):** Paginated list.

### GET `/appointments/{id}`
Get appointment details. **Auth required (any role).**

**Response (200):** Full appointment object.

### PUT `/appointments/{id}`
Reschedule an appointment. **Roles: admin, doctor, nurse, receptionist**

**Request:**
```json
{
  "scheduled_at": "2026-03-16T10:00:00Z",
  "duration_minutes": 45,
  "reason": "Updated reason"
}
```

**Response (200):** Updated appointment object.

### PATCH `/appointments/{id}/cancel`
Cancel an appointment. **Roles: admin, doctor, nurse, receptionist**

Publishes `appointment.cancelled` event.

**Response (200):** Appointment with `status` = "cancelled".

### GET `/appointments/availability`
Check doctor availability. **Auth required (any role).**

**Query params:** `doctor_id`

**Response (200):**
```json
[
  {
    "id": "uuid",
    "doctor_id": "uuid",
    "day_of_week": 0,
    "start_time": "09:00:00",
    "end_time": "17:00:00"
  }
]
```

### POST `/appointments/availability`
Set doctor availability. **Roles: admin, doctor**

**Request:**
```json
{
  "doctor_id": "uuid",
  "day_of_week": 0,
  "start_time": "09:00:00",
  "end_time": "17:00:00"
}
```

**Response (201):** Availability object.

---

## Clinical Notes Service — `/notes`

### POST `/notes`
Create a clinical note (SOAP format). **Roles: admin, doctor**

**Request:**
```json
{
  "appointment_id": "uuid",
  "patient_id": "uuid",
  "doctor_id": "uuid",
  "subjective": "Patient reports headaches...",
  "objective": "BP 120/80, HR 72...",
  "assessment": "Tension headache",
  "plan": "OTC analgesics, follow-up in 2 weeks"
}
```

**Response (201):** Full note object with `id`, timestamps.

### GET `/notes`
List clinical notes with filters. **Auth required (any role).**

**Query params:** `page`, `per_page`, `patient_id`, `appointment_id`

**Response (200):** Paginated list.

### GET `/notes/{id}`
Get note details. **Auth required (any role).**

**Response (200):** Full note object.

### PUT `/notes/{id}`
Update a clinical note. Creates an audit trail entry. **Roles: admin, doctor**

**Request:** Same fields as POST.

**Response (200):** Updated note object.

### GET `/notes/{id}/history`
Get the audit trail for a note. **Roles: admin, doctor, nurse**

**Response (200):**
```json
[
  {
    "id": "uuid",
    "note_id": "uuid",
    "changed_by": "uuid",
    "change_type": "updated",
    "old_values": {...},
    "new_values": {...},
    "changed_at": "2026-03-11T10:30:00Z"
  }
]
```

---

## Billing Service — `/invoices`

### POST `/invoices`
Create an invoice. **Roles: admin, nurse, receptionist**

**Request:**
```json
{
  "appointment_id": "uuid",
  "patient_id": "uuid",
  "amount": 250.00,
  "status": "draft"
}
```

**Response (201):** Full invoice object.

### GET `/invoices`
List invoices with filters. **Auth required (any role).**

**Query params:** `page`, `per_page`, `patient_id`, `status`

**Response (200):** Paginated list.

### GET `/invoices/{id}`
Get invoice details. **Auth required (any role).**

**Response (200):** Full invoice object.

### PATCH `/invoices/{id}/pay`
Mark an invoice as paid. **Roles: admin, nurse, receptionist**

**Response (200):** Invoice with `status` = "paid" and `paid_at` timestamp.

### GET `/billing/summary`
Get revenue summary and statistics. **Roles: admin, nurse, receptionist**

**Response (200):**
```json
{
  "total_invoices": 42,
  "total_revenue": 10500.00,
  "paid_count": 30,
  "pending_count": 12,
  "by_status": {
    "draft": 5,
    "issued": 7,
    "paid": 30,
    "overdue": 0
  }
}
```

---

## Health Check (All Services)

### GET `/health`
**No auth required.**

**Response (200):**
```json
{
  "status": "healthy"
}
```

---

## Service Ports (Direct Access — Development Only)

| Service         | Port  |
|-----------------|-------|
| Auth            | 8001  |
| Patient         | 8002  |
| Appointment     | 8003  |
| Clinical Notes  | 8004  |
| Billing         | 8005  |
| Traefik Gateway | 80    |
| Traefik Dashboard | 8080 |
| PostgreSQL      | 5432  |
| RabbitMQ        | 5672  |
| RabbitMQ UI     | 15672 |
| Prometheus      | 9090  |
| Grafana         | 3000  |
| Loki            | 3100  |

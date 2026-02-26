# Healthcare Microservices Platform — Project Guide

## Project Overview

A cloud-native healthcare management platform built with a microservices architecture. The system handles patient management, appointment scheduling, clinical notes, and billing through independent, loosely-coupled services communicating via REST APIs and asynchronous messaging.

**Primary goals**: demonstrate microservices design patterns, container orchestration, CI/CD automation, and observability in a real-world healthcare domain.

---

## Tech Stack

| Layer              | Technology             |
|--------------------|------------------------|
| Language/Framework | Python 3.12 + FastAPI  |
| Database           | PostgreSQL 16          |
| ORM                | SQLAlchemy 2.x + Alembic |
| Message Broker     | RabbitMQ               |
| Containerization   | Docker                 |
| Orchestration      | Kubernetes (k8s)       |
| API Gateway        | Traefik                |
| Auth               | JWT + OAuth2           |
| CI/CD              | GitHub Actions         |
| Monitoring         | Prometheus + Grafana   |
| Logging            | Loki + Promtail        |
| Testing            | pytest + httpx         |

---

## Repository Structure

```
graduation-project/
├── CLAUDE.md                          # This file — project master guide
├── docker-compose.yml                 # Local dev orchestration
├── docker-compose.override.yml        # Dev-specific overrides
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Lint, test, build on every PR
│       └── cd.yml                     # Deploy on merge to main
│
├── services/
│   ├── api-gateway/                   # Traefik config + middleware
│   │   ├── traefik.yml
│   │   └── dynamic/
│   │       └── routes.yml
│   │
│   ├── auth/                          # Auth service
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── alembic/
│   │   ├── alembic.ini
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py               # FastAPI app entry
│   │   │   ├── config.py             # Settings via pydantic-settings
│   │   │   ├── models.py             # SQLAlchemy models
│   │   │   ├── schemas.py            # Pydantic request/response schemas
│   │   │   ├── crud.py               # DB operations
│   │   │   ├── api/
│   │   │   │   ├── __init__.py
│   │   │   │   └── routes.py
│   │   │   ├── core/
│   │   │   │   ├── security.py       # JWT encode/decode, password hashing
│   │   │   │   └── dependencies.py   # get_current_user, role checks
│   │   │   └── db.py                 # Session factory, engine
│   │   └── tests/
│   │       ├── conftest.py
│   │       └── test_auth.py
│   │
│   ├── patient/                       # Patient service (same layout)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── alembic/
│   │   ├── alembic.ini
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   ├── api/
│   │   │   │   └── routes.py
│   │   │   ├── events/               # RabbitMQ publisher/consumer
│   │   │   │   ├── publisher.py
│   │   │   │   └── consumer.py
│   │   │   └── db.py
│   │   └── tests/
│   │
│   ├── appointment/                   # Appointment service (same layout)
│   │   └── ...
│   │
│   ├── clinical-notes/                # Clinical Notes service (same layout)
│   │   └── ...
│   │
│   └── billing/                       # Billing service (same layout)
│       └── ...
│
├── k8s/                               # Kubernetes manifests
│   ├── namespace.yml
│   ├── auth/
│   │   ├── deployment.yml
│   │   ├── service.yml
│   │   └── configmap.yml
│   ├── patient/
│   ├── appointment/
│   ├── clinical-notes/
│   ├── billing/
│   ├── traefik/
│   ├── rabbitmq/
│   ├── postgres/
│   └── monitoring/
│       ├── prometheus/
│       │   ├── deployment.yml
│       │   ├── service.yml
│       │   └── config.yml
│       ├── grafana/
│       └── loki/
│
├── scripts/
│   ├── init-db.sh                     # Create databases per service
│   └── seed-data.py                   # Populate dev data
│
└── docs/
    ├── architecture.md
    └── api-contracts.md
```

Each service follows the **identical internal layout** (`app/main.py`, `models.py`, `schemas.py`, `crud.py`, `api/routes.py`, `db.py`, `config.py`) to keep the codebase consistent and navigable.

---

## Microservices Breakdown

### 1. Auth Service (`services/auth/`)

**Responsibility**: User registration, login, JWT issuance, token refresh, role management.

**Endpoints**:
| Method | Path                | Description             |
|--------|---------------------|-------------------------|
| POST   | `/auth/register`    | Register a new user     |
| POST   | `/auth/login`       | Login, returns JWT pair |
| POST   | `/auth/refresh`     | Refresh access token    |
| GET    | `/auth/me`          | Get current user profile|

**Roles**: `admin`, `doctor`, `nurse`, `receptionist`, `patient`

### 2. Patient Service (`services/patient/`)

**Responsibility**: Patient demographics, medical history summary, patient search.

**Endpoints**:
| Method | Path                     | Description                  |
|--------|--------------------------|------------------------------|
| POST   | `/patients`              | Register a new patient       |
| GET    | `/patients`              | List patients (paginated)    |
| GET    | `/patients/{id}`         | Get patient details          |
| PUT    | `/patients/{id}`         | Update patient info          |
| DELETE | `/patients/{id}`         | Soft-delete a patient        |
| GET    | `/patients/{id}/history` | Medical history summary      |

**Events published**: `patient.created`, `patient.updated`

### 3. Appointment Service (`services/appointment/`)

**Responsibility**: Schedule, reschedule, cancel appointments. Manages doctor availability.

**Endpoints**:
| Method | Path                          | Description                    |
|--------|-------------------------------|--------------------------------|
| POST   | `/appointments`               | Create appointment             |
| GET    | `/appointments`               | List (filter by patient/doctor)|
| GET    | `/appointments/{id}`          | Get appointment details        |
| PUT    | `/appointments/{id}`          | Reschedule                     |
| PATCH  | `/appointments/{id}/cancel`   | Cancel appointment             |
| GET    | `/appointments/availability`  | Check doctor availability      |

**Events published**: `appointment.created`, `appointment.cancelled`
**Events consumed**: `patient.created` (cache patient reference)

### 4. Clinical Notes Service (`services/clinical-notes/`)

**Responsibility**: SOAP notes, diagnoses, prescriptions tied to appointments.

**Endpoints**:
| Method | Path                                   | Description               |
|--------|----------------------------------------|---------------------------|
| POST   | `/notes`                               | Create clinical note      |
| GET    | `/notes?patient_id=X`                  | List notes for patient    |
| GET    | `/notes/{id}`                          | Get note details          |
| PUT    | `/notes/{id}`                          | Update note               |
| GET    | `/notes/{id}/history`                  | Audit trail of changes    |

**Events consumed**: `appointment.created` (prepare note stub)

### 5. Billing Service (`services/billing/`)

**Responsibility**: Generate invoices from appointments, track payments.

**Endpoints**:
| Method | Path                         | Description                 |
|--------|------------------------------|-----------------------------|
| POST   | `/invoices`                  | Create invoice              |
| GET    | `/invoices?patient_id=X`     | List invoices for patient   |
| GET    | `/invoices/{id}`             | Get invoice details         |
| PATCH  | `/invoices/{id}/pay`         | Mark invoice as paid        |
| GET    | `/billing/summary`           | Revenue summary / stats     |

**Events consumed**: `appointment.created` (auto-generate draft invoice)

### 6. API Gateway (Traefik)

- Routes external traffic to internal services
- TLS termination
- Rate limiting middleware
- JWT validation middleware (forward auth to auth service)
- Path-based routing: `/auth/**`, `/patients/**`, `/appointments/**`, `/notes/**`, `/invoices/**`

---

## Database Schema Outlines

Each service owns its own PostgreSQL database. **No cross-service JOINs** — services communicate via APIs or events.

### Auth DB (`auth_db`)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'patient',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(512) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Patient DB (`patient_db`)
```sql
CREATE TABLE patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20),
    phone VARCHAR(20),
    email VARCHAR(255),
    address TEXT,
    emergency_contact_name VARCHAR(200),
    emergency_contact_phone VARCHAR(20),
    blood_type VARCHAR(5),
    allergies TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### Appointment DB (`appointment_db`)
```sql
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL,
    doctor_id UUID NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    duration_minutes INT DEFAULT 30,
    status VARCHAR(20) DEFAULT 'scheduled',  -- scheduled, completed, cancelled, no_show
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE doctor_availability (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL,
    day_of_week INT NOT NULL,   -- 0=Monday, 6=Sunday
    start_time TIME NOT NULL,
    end_time TIME NOT NULL
);
```

### Clinical Notes DB (`clinical_notes_db`)
```sql
CREATE TABLE clinical_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL,
    patient_id UUID NOT NULL,
    doctor_id UUID NOT NULL,
    subjective TEXT,     -- SOAP: patient complaints
    objective TEXT,      -- SOAP: examination findings
    assessment TEXT,     -- SOAP: diagnosis
    plan TEXT,           -- SOAP: treatment plan
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE note_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_id UUID REFERENCES clinical_notes(id),
    changed_by UUID NOT NULL,
    change_type VARCHAR(20) NOT NULL,  -- created, updated
    old_values JSONB,
    new_values JSONB,
    changed_at TIMESTAMPTZ DEFAULT now()
);
```

### Billing DB (`billing_db`)
```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL,
    patient_id UUID NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',  -- draft, issued, paid, overdue
    issued_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID REFERENCES invoices(id) ON DELETE CASCADE,
    description VARCHAR(255) NOT NULL,
    quantity INT DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL
);
```

---

## API Contract Conventions

All services follow these conventions:

- **Base path**: Each service mounts its routes under its own prefix (`/auth`, `/patients`, etc.)
- **Content type**: `application/json`
- **Pagination**: `?page=1&per_page=20` — responses include `total`, `page`, `per_page`, `items`
- **Filtering**: Query parameters (e.g., `?status=scheduled&doctor_id=...`)
- **Error format**:
  ```json
  {
    "detail": "Human-readable message",
    "code": "MACHINE_READABLE_CODE",
    "errors": [{"field": "email", "message": "Already exists"}]
  }
  ```
- **HTTP status codes**: 200 (ok), 201 (created), 204 (deleted), 400 (validation), 401 (unauthenticated), 403 (forbidden), 404 (not found), 422 (unprocessable entity), 500 (server error)
- **Auth header**: `Authorization: Bearer <jwt_token>`
- **UUID IDs**: All primary keys are UUIDs
- **Timestamps**: ISO 8601 with timezone (`2026-02-26T10:30:00Z`)
- **Soft deletes**: Records set `is_active = false` rather than being physically deleted

---

## Docker Setup

### Per-Service Dockerfile Pattern
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY alembic.ini .
COPY alembic/ ./alembic/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml Services
- `postgres` — single PostgreSQL instance with multiple databases (dev only)
- `rabbitmq` — message broker with management UI on port 15672
- `auth` — auth service on port 8001
- `patient` — patient service on port 8002
- `appointment` — appointment service on port 8003
- `clinical-notes` — clinical notes service on port 8004
- `billing` — billing service on port 8005
- `traefik` — API gateway on port 80 (routes to services)
- `prometheus` — metrics scraping
- `grafana` — dashboards on port 3000
- `loki` — log aggregation

### Key Docker Compose Patterns
- Shared network: `healthcare-net`
- Health checks on every service
- Volume mounts for local development (code reloading)
- Environment variables via `.env` file (never committed)
- `depends_on` with health check conditions

---

## Kubernetes Setup

### Namespace
All resources live in `namespace: healthcare`.

### Per-Service Manifests
Each service gets:
- `deployment.yml` — 2 replicas, resource limits, liveness/readiness probes
- `service.yml` — ClusterIP service
- `configmap.yml` — non-secret configuration
- `secret.yml` — DB credentials, JWT secret (created via `kubectl create secret`)

### Infrastructure Components
- **PostgreSQL**: StatefulSet with PersistentVolumeClaim
- **RabbitMQ**: StatefulSet with PVC for message persistence
- **Traefik**: Deployment + IngressRoute CRDs for routing
- **Prometheus**: Deployment with ConfigMap for scrape targets
- **Grafana**: Deployment with preconfigured datasources
- **Loki**: Deployment with Promtail DaemonSet

### Probes (applied to all application services)
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

Every service must expose `GET /health` returning `{"status": "healthy"}`.

---

## CI/CD Pipeline (GitHub Actions)

### CI (`ci.yml`) — Runs on every PR and push to `main`
```
Steps:
1. Checkout code
2. Detect which services changed (path filter)
3. Per changed service:
   a. Set up Python 3.12
   b. Install dependencies
   c. Run linting (ruff check + ruff format --check)
   d. Run tests (pytest with PostgreSQL service container)
   e. Build Docker image
   f. Push image to container registry (GitHub Container Registry)
```

### CD (`cd.yml`) — Runs on merge to `main`
```
Steps:
1. Checkout code
2. Build + push Docker images with :latest and :sha tags
3. Update Kubernetes deployment image tags
4. Apply manifests via kubectl
```

### Path Filters
Only build/test services whose files actually changed:
```yaml
paths:
  - 'services/auth/**'
  - 'services/patient/**'
  # etc.
```

---

## Monitoring & Observability

### Prometheus
- Each FastAPI service exposes `/metrics` via `prometheus-fastapi-instrumentator`
- Metrics: request count, latency histograms, error rates, active connections
- Scrape interval: 15s

### Grafana Dashboards
- **Service Overview**: Request rate, error rate, latency p50/p95/p99 per service
- **Infrastructure**: CPU, memory, pod restarts per deployment
- **Business Metrics**: Appointments per day, patients registered, invoices generated

### Loki + Promtail
- Structured JSON logging from all services using `python-json-logger`
- Log fields: `timestamp`, `level`, `service`, `request_id`, `user_id`, `message`
- Promtail collects logs from pod stdout/stderr
- Grafana Explore for log search and correlation

### Distributed Tracing (optional stretch goal)
- OpenTelemetry instrumentation
- Trace context propagation via `X-Request-ID` header

---

## Security Requirements

1. **Authentication**: All endpoints (except `/auth/register`, `/auth/login`, `/health`) require valid JWT
2. **Authorization**: Role-based access control (RBAC) enforced per endpoint
3. **Password Storage**: bcrypt hashing via `passlib`
4. **JWT Configuration**: Access token expires in 30 minutes, refresh token in 7 days
5. **Input Validation**: Pydantic models validate all request bodies
6. **SQL Injection Prevention**: Parameterized queries via SQLAlchemy ORM
7. **CORS**: Configured per environment, restrictive in production
8. **Secrets Management**: Environment variables, never hardcoded; Kubernetes Secrets in production
9. **Rate Limiting**: Traefik middleware, 100 req/min per IP on auth endpoints
10. **HTTPS**: TLS termination at Traefik in production

---

## Coding Conventions

- **Formatter/Linter**: `ruff` (replaces black + isort + flake8)
- **Type hints**: Required on all function signatures
- **Async**: All FastAPI route handlers and DB operations are async
- **Dependency injection**: Use FastAPI `Depends()` for DB sessions, current user, role checks
- **Config**: `pydantic-settings` with `.env` files, never hardcode values
- **Testing**: `pytest` with `httpx.AsyncClient` for API tests, separate test database
- **Git branching**: `main` (production), feature branches named `feat/<description>`, fix branches named `fix/<description>`
- **Commit messages**: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `test:`)

---

## Phased Implementation Roadmap

### Phase 1: Foundation (Project Skeleton + Auth Service)

**Goal**: Set up the mono-repo, Docker Compose, and a fully working auth service.

- [ ] Initialize git repo, create directory structure per the layout above
- [ ] Create root `docker-compose.yml` with PostgreSQL and RabbitMQ
- [ ] Write `scripts/init-db.sh` to create per-service databases
- [ ] Build Auth service:
  - [ ] `config.py` — pydantic-settings with DB URL, JWT secret, token expiry
  - [ ] `db.py` — async SQLAlchemy engine + session factory
  - [ ] `models.py` — User, RefreshToken SQLAlchemy models
  - [ ] `schemas.py` — RegisterRequest, LoginRequest, TokenResponse, UserResponse
  - [ ] `core/security.py` — JWT encode/decode, password hash/verify
  - [ ] `crud.py` — create_user, get_user_by_email, create_refresh_token
  - [ ] `api/routes.py` — register, login, refresh, me endpoints
  - [ ] `core/dependencies.py` — get_current_user, require_role dependencies
  - [ ] `main.py` — FastAPI app with CORS, health endpoint, router include
  - [ ] Alembic migration for users + refresh_tokens tables
  - [ ] Dockerfile
  - [ ] Tests: registration, login, token refresh, protected endpoint access
- [ ] Verify: `docker compose up` starts PostgreSQL, RabbitMQ, auth service; all auth tests pass

### Phase 2: Core Business Services (Patient + Appointment)

**Goal**: Two more services with inter-service communication via RabbitMQ.

- [ ] Build Patient service:
  - [ ] Models, schemas, CRUD, routes (full CRUD + search)
  - [ ] RabbitMQ publisher — emit `patient.created` / `patient.updated`
  - [ ] Alembic migration
  - [ ] Dockerfile + docker-compose entry
  - [ ] Tests
- [ ] Build Appointment service:
  - [ ] Models, schemas, CRUD, routes (create, list, reschedule, cancel, availability)
  - [ ] RabbitMQ consumer — listen for `patient.created`
  - [ ] RabbitMQ publisher — emit `appointment.created` / `appointment.cancelled`
  - [ ] Alembic migration
  - [ ] Dockerfile + docker-compose entry
  - [ ] Tests
- [ ] Shared: Create a reusable `messaging` utility package for RabbitMQ publish/consume (or copy the pattern)
- [ ] Verify: Create patient via API, appointment references that patient; events flow between services

### Phase 3: Remaining Services (Clinical Notes + Billing)

**Goal**: Complete the service mesh with the final two domain services.

- [ ] Build Clinical Notes service:
  - [ ] SOAP note model with audit log
  - [ ] RabbitMQ consumer — listen for `appointment.created` (create note stub)
  - [ ] Note history endpoint (audit trail)
  - [ ] Alembic migration, Dockerfile, tests
- [ ] Build Billing service:
  - [ ] Invoice + line items model
  - [ ] RabbitMQ consumer — listen for `appointment.created` (create draft invoice)
  - [ ] Payment marking endpoint
  - [ ] Revenue summary endpoint
  - [ ] Alembic migration, Dockerfile, tests
- [ ] Verify: Creating an appointment triggers note stub + draft invoice automatically

### Phase 4: API Gateway + Inter-Service Auth

**Goal**: Unified entry point with Traefik, JWT validation at the gateway.

- [ ] Configure Traefik:
  - [ ] `traefik.yml` static config (entrypoints, providers)
  - [ ] `dynamic/routes.yml` route rules per service
  - [ ] ForwardAuth middleware pointing to auth service's `/auth/verify` endpoint
  - [ ] Rate limiting middleware on `/auth/**`
- [ ] Add `GET /auth/verify` endpoint to auth service (validates JWT, returns user info in headers)
- [ ] Update docker-compose to route all traffic through Traefik
- [ ] Verify: All API calls go through `localhost:80`, auth enforced at gateway level

### Phase 5: CI/CD Pipeline

**Goal**: Automated testing and deployment via GitHub Actions.

- [ ] Create `.github/workflows/ci.yml`:
  - [ ] Path-based triggers per service
  - [ ] Matrix strategy for parallel service builds
  - [ ] PostgreSQL service container for tests
  - [ ] Lint with ruff, test with pytest, build Docker image
- [ ] Create `.github/workflows/cd.yml`:
  - [ ] Build and push images to GHCR on merge to main
  - [ ] (Optional) kubectl apply for K8s deployment
- [ ] Add `ruff.toml` config at repo root
- [ ] Verify: Push a PR, CI runs only for changed services; merge triggers image build

### Phase 6: Kubernetes Deployment

**Goal**: Deploy entire stack to a Kubernetes cluster.

- [ ] Write K8s manifests:
  - [ ] Namespace, ConfigMaps, Secrets
  - [ ] PostgreSQL StatefulSet + PVC
  - [ ] RabbitMQ StatefulSet + PVC
  - [ ] Deployment + Service for each application service
  - [ ] Traefik Deployment + IngressRoute
- [ ] Configure health check probes on all deployments
- [ ] Test with minikube or kind locally
- [ ] Verify: `kubectl get pods -n healthcare` shows all services running

### Phase 7: Monitoring & Observability

**Goal**: Full observability stack with metrics, logs, and dashboards.

- [ ] Add `prometheus-fastapi-instrumentator` to each service
- [ ] Deploy Prometheus with scrape config targeting all services
- [ ] Deploy Grafana with preconfigured datasources (Prometheus + Loki)
- [ ] Create Grafana dashboards (service overview, infrastructure, business metrics)
- [ ] Deploy Loki + Promtail for log aggregation
- [ ] Configure structured JSON logging in all services
- [ ] Verify: Grafana shows live metrics and searchable logs from all services

### Phase 8: Polish & Documentation

**Goal**: Final cleanup, security hardening, and documentation.

- [ ] Security audit: verify all endpoints enforce auth + RBAC
- [ ] Add seed data script for demo
- [ ] Write `docs/architecture.md` with system diagrams
- [ ] Write `docs/api-contracts.md` with full OpenAPI references
- [ ] Load testing with locust (optional stretch goal)
- [ ] OpenTelemetry tracing (optional stretch goal)
- [ ] Final README with setup instructions

---

## Quick Reference Commands

```bash
# Start all services locally
docker compose up -d

# Run tests for a specific service
cd services/auth && pytest -v

# Run linting
ruff check services/

# Create a new migration
cd services/auth && alembic revision --autogenerate -m "description"

# Apply migrations
cd services/auth && alembic upgrade head

# View RabbitMQ management UI
open http://localhost:15672  # guest/guest

# View Grafana dashboards
open http://localhost:3000  # admin/admin
```

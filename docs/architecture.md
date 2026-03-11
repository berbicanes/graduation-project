# Architecture Overview

## System Architecture

The Healthcare Management Platform follows a **microservices architecture** with five independent domain services, an API gateway, asynchronous messaging, and a full observability stack.

```
                        ┌──────────────┐
                        │   Clients    │
                        │  (Browser /  │
                        │   Mobile)    │
                        └──────┬───────┘
                               │ HTTPS
                        ┌──────▼───────┐
                        │   Traefik    │
                        │ API Gateway  │
                        │  (port 80)   │
                        └──────┬───────┘
                               │ ForwardAuth
                        ┌──────▼───────┐
          ┌─────────────┤  Auth Service ├─────────────┐
          │             │  (port 8001)  │             │
          │             └───────────────┘             │
          │                                           │
    ┌─────▼──────┐  ┌──────────────┐  ┌──────────────▼──┐  ┌────────────┐
    │  Patient   │  │ Appointment  │  │ Clinical Notes  │  │  Billing   │
    │  Service   │  │   Service    │  │    Service      │  │  Service   │
    │ (port 8002)│  │ (port 8003)  │  │  (port 8004)    │  │ (port 8005)│
    └─────┬──────┘  └──────┬───────┘  └────────▲────────┘  └─────▲──────┘
          │                │                    │                  │
          │         ┌──────▼───────┐            │                  │
          └────────►│   RabbitMQ   ├────────────┴──────────────────┘
                    │  (port 5672) │
                    └──────────────┘
          │
    ┌─────▼──────────────────────────────────────────────────────────────┐
    │                        PostgreSQL                                  │
    │  ┌─────────┐ ┌────────────┐ ┌───────────────┐ ┌─────────────────┐ │
    │  │ auth_db │ │ patient_db │ │appointment_db │ │clinical_notes_db│ │
    │  └─────────┘ └────────────┘ └───────────────┘ └─────────────────┘ │
    │  ┌────────────┐                                                    │
    │  │ billing_db │                                                    │
    │  └────────────┘                                                    │
    └────────────────────────────────────────────────────────────────────┘
```

## Design Principles

### Database per Service
Each microservice owns its dedicated PostgreSQL database. There are no cross-service JOINs. Services communicate exclusively through REST APIs and asynchronous events.

### Event-Driven Communication
Services publish domain events to RabbitMQ when significant actions occur. Other services consume these events to maintain eventual consistency.

**Event flow:**
```
Patient Service ──► patient.created ──► Appointment Service (caches reference)
                    patient.updated

Appointment Service ──► appointment.created ──► Clinical Notes Service (creates note stub)
                                             ──► Billing Service (creates draft invoice)
                        appointment.cancelled
```

### API Gateway Pattern
Traefik acts as the single entry point for all external traffic:
- **Path-based routing**: `/auth/**`, `/patients/**`, `/appointments/**`, `/notes/**`, `/invoices/**`
- **ForwardAuth middleware**: Every request (except `/auth/register`, `/auth/login`, `/health`) is validated against the Auth service's `/auth/verify` endpoint
- **Rate limiting**: 100 requests/minute on auth endpoints

### Authentication & Authorization
- **JWT tokens**: Access token (30 min) + Refresh token (7 days)
- **ForwardAuth**: Traefik forwards each request to Auth service for validation before routing
- **RBAC**: Role-based access control enforced at the service level via `require_role()` dependency injection

**Roles**: `admin`, `doctor`, `nurse`, `receptionist`, `patient`

## Service Details

### Auth Service
Handles user registration, login, JWT issuance, and token refresh. Provides the `/auth/verify` endpoint used by Traefik's ForwardAuth middleware.

### Patient Service
Manages patient demographics, contact information, medical history, and allergies. Publishes events on patient creation and updates.

### Appointment Service
Handles scheduling, rescheduling, and cancellation of appointments. Manages doctor availability. Publishes events consumed by Clinical Notes and Billing services.

### Clinical Notes Service
Manages SOAP-format clinical notes (Subjective, Objective, Assessment, Plan) with a full audit trail. Automatically creates note stubs when appointments are created.

### Billing Service
Manages invoices and payments. Automatically generates draft invoices when appointments are created. Provides revenue summary and statistics.

## Infrastructure

### Container Orchestration
- **Local development**: Docker Compose with all services, databases, message broker, and monitoring
- **Production**: Kubernetes with Deployments (2 replicas per service), StatefulSets for databases, health probes on all pods

### CI/CD Pipeline
- **CI** (GitHub Actions): Triggered on PR/push. Path-filtered per service — only changed services are linted, tested, and built.
- **CD** (GitHub Actions): Triggered on merge to main. Builds and pushes Docker images to GitHub Container Registry.

### Observability Stack

| Component  | Purpose                              | Access               |
|------------|--------------------------------------|-----------------------|
| Prometheus | Metrics collection (15s scrape)      | `http://localhost:9090` |
| Grafana    | Dashboards and log exploration       | `http://localhost:3000` |
| Loki       | Log aggregation                      | Via Grafana Explore    |
| Promtail   | Log collection from containers       | (sidecar)              |

**Metrics exposed**: Request count, latency histograms (p50/p95/p99), error rates, active connections — via `prometheus-fastapi-instrumentator` on each service's `/metrics` endpoint.

**Logging**: Structured JSON logs from all services via `python-json-logger`. Fields: `timestamp`, `level`, `service`, `message`.

## Technology Stack

| Layer              | Technology                          |
|--------------------|-------------------------------------|
| Language           | Python 3.12                         |
| Framework          | FastAPI                             |
| Database           | PostgreSQL 16                       |
| ORM                | SQLAlchemy 2.x (async) + Alembic    |
| Message Broker     | RabbitMQ (aio-pika)                 |
| API Gateway        | Traefik v3.1                        |
| Auth               | JWT (PyJWT) + OAuth2 (passlib/bcrypt)|
| Containerization   | Docker                              |
| Orchestration      | Kubernetes                          |
| CI/CD              | GitHub Actions                      |
| Metrics            | Prometheus + Grafana                |
| Logging            | Loki + Promtail                     |
| Linting            | ruff                                |
| Testing            | pytest + httpx                      |

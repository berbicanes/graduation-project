# Healthcare Microservices Platform

A cloud-native healthcare management platform built with a microservices architecture. Handles patient management, appointment scheduling, clinical notes, and billing through independent services communicating via REST APIs and asynchronous messaging.

## Architecture

```
Clients → Traefik (API Gateway) → Auth Service (JWT validation)
                                 → Patient Service
                                 → Appointment Service
                                 → Clinical Notes Service
                                 → Billing Service
                                        ↕
                                    RabbitMQ (events)
                                        ↕
                                    PostgreSQL (per-service DB)
```

See [docs/architecture.md](docs/architecture.md) for detailed diagrams and design decisions.

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic
- **Database**: PostgreSQL 16 (one database per service)
- **Messaging**: RabbitMQ (aio-pika)
- **Gateway**: Traefik v3.1 with ForwardAuth + rate limiting
- **Auth**: JWT (access + refresh tokens), bcrypt password hashing, RBAC
- **Containers**: Docker, Kubernetes
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus, Grafana, Loki, Promtail

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.12 (for running tests locally)

### Run Locally

```bash
# Start all services
docker compose up -d --build

# Wait for health checks to pass (~30 seconds)
docker compose ps

# Seed demo data
pip install httpx
python scripts/seed-data.py
```

### Access Points

| Service              | URL                         | Credentials      |
|----------------------|-----------------------------|-------------------|
| API Gateway          | http://localhost             | —                 |
| Traefik Dashboard    | http://localhost:8080        | —                 |
| Grafana              | http://localhost:3000        | admin / admin     |
| Prometheus           | http://localhost:9090        | —                 |
| RabbitMQ Management  | http://localhost:15672       | guest / guest     |

### Test the API

```bash
# Register a user
curl -s http://localhost/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234!","full_name":"Test User"}'

# Login
curl -s http://localhost/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Test1234!"}'

# Use the access_token from login response
TOKEN="<access_token>"

# Create a patient
curl -s http://localhost/patients \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Alice","last_name":"Johnson","date_of_birth":"1985-03-15","gender":"female"}'

# List patients
curl -s http://localhost/patients -H "Authorization: Bearer $TOKEN"
```

## Services

| Service         | Port | Description                          |
|-----------------|------|--------------------------------------|
| Auth            | 8001 | Registration, login, JWT, RBAC       |
| Patient         | 8002 | Patient demographics and history     |
| Appointment     | 8003 | Scheduling, availability, cancellation |
| Clinical Notes  | 8004 | SOAP notes with audit trail          |
| Billing         | 8005 | Invoices, payments, revenue summary  |

All endpoints documented in [docs/api-contracts.md](docs/api-contracts.md).

## Event-Driven Flows

Creating an appointment automatically triggers:
1. **Clinical Notes Service** creates a note stub (via `appointment.created` event)
2. **Billing Service** creates a draft invoice (via `appointment.created` event)

## Development

```bash
# Run tests for a specific service
cd services/auth && pip install -r requirements.txt && pytest -v

# Lint all services
ruff check services/

# Format check
ruff format --check services/

# Create a new migration
cd services/<service> && alembic revision --autogenerate -m "description"

# Apply migrations
cd services/<service> && alembic upgrade head
```

## Kubernetes

```bash
# Start minikube
minikube start

# Build images inside minikube
minikube image build -t auth-service ./services/auth
minikube image build -t patient-service ./services/patient
minikube image build -t appointment-service ./services/appointment
minikube image build -t clinical-notes-service ./services/clinical-notes
minikube image build -t billing-service ./services/billing

# Deploy
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/rabbitmq/
kubectl apply -f k8s/auth/
kubectl apply -f k8s/patient/
kubectl apply -f k8s/appointment/
kubectl apply -f k8s/clinical-notes/
kubectl apply -f k8s/billing/
kubectl apply -f k8s/traefik/
kubectl apply -f k8s/monitoring/

# Check status
kubectl get pods -n healthcare
```

## Monitoring

- **Grafana** (http://localhost:3000): Pre-configured dashboards for request rates, latency, and error rates
- **Prometheus** (http://localhost:9090): Raw metrics and service health at Status → Targets
- **Loki**: Log search via Grafana → Explore → Loki datasource

## Project Structure

```
├── services/
│   ├── api-gateway/          # Traefik configuration
│   ├── auth/                 # Auth service
│   ├── patient/              # Patient service
│   ├── appointment/          # Appointment service
│   ├── clinical-notes/       # Clinical Notes service
│   └── billing/              # Billing service
├── k8s/                      # Kubernetes manifests
├── monitoring/               # Prometheus, Grafana, Loki, Promtail configs
├── scripts/                  # DB init and seed data
├── docs/                     # Architecture and API documentation
├── .github/workflows/        # CI/CD pipelines
└── docker-compose.yml        # Local development orchestration
```

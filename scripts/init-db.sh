#!/bin/bash
set -e

# Create per-service databases for the healthcare platform.
# This script is executed by PostgreSQL on first boot via
# docker-entrypoint-initdb.d.

DATABASES=("auth_db" "patient_db" "appointment_db" "clinical_notes_db" "billing_db")

for db in "${DATABASES[@]}"; do
    echo "Creating database: $db"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE DATABASE $db;
        GRANT ALL PRIVILEGES ON DATABASE $db TO $POSTGRES_USER;
EOSQL
done

echo "All databases created successfully."

#!/usr/bin/env python3
"""Seed script to populate the healthcare platform with demo data.

Usage:
    python scripts/seed-data.py [--base-url http://localhost]

Requires: httpx (pip install httpx)
"""

import argparse
import sys

import httpx

DEFAULT_BASE_URL = "http://localhost"


def main(base_url: str) -> None:
    client = httpx.Client(base_url=base_url, timeout=30)

    print("=== Healthcare Platform — Seed Data ===\n")

    # ── 1. Register users ──────────────────────────────────────────────
    users = [
        {"email": "admin@healthcare-demo.com", "password": "Admin1234!", "full_name": "System Admin", "role": "admin"},
        {"email": "dr.smith@healthcare-demo.com", "password": "Doctor1234!", "full_name": "Dr. Sarah Smith", "role": "doctor"},
        {"email": "dr.jones@healthcare-demo.com", "password": "Doctor1234!", "full_name": "Dr. Michael Jones", "role": "doctor"},
        {"email": "nurse.lee@healthcare-demo.com", "password": "Nurse1234!", "full_name": "Emily Lee", "role": "nurse"},
        {"email": "reception@healthcare-demo.com", "password": "Recept1234!", "full_name": "James Wilson", "role": "receptionist"},
    ]

    tokens: dict[str, str] = {}

    for user in users:
        resp = client.post("/auth/register", json=user)
        if resp.status_code == 201:
            print(f"  [+] Registered {user['role']}: {user['email']}")
        elif resp.status_code == 400 and "already" in resp.text.lower():
            print(f"  [=] Already exists: {user['email']}")
        else:
            print(f"  [!] Failed to register {user['email']}: {resp.status_code} {resp.text}")

    # Login as admin for subsequent calls
    for role, email, password in [
        ("admin", "admin@healthcare-demo.com", "Admin1234!"),
        ("doctor", "dr.smith@healthcare-demo.com", "Doctor1234!"),
    ]:
        resp = client.post("/auth/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            tokens[role] = resp.json()["access_token"]
            print(f"  [+] Logged in as {role}")
        else:
            print(f"  [!] Login failed for {email}: {resp.status_code}")
            sys.exit(1)

    admin_headers = {"Authorization": f"Bearer {tokens['admin']}"}
    doctor_headers = {"Authorization": f"Bearer {tokens['doctor']}"}

    # ── 2. Create patients ─────────────────────────────────────────────
    print("\n--- Creating patients ---")
    patients_data = [
        {
            "first_name": "Alice",
            "last_name": "Johnson",
            "date_of_birth": "1985-03-15",
            "gender": "female",
            "phone": "+1-555-0101",
            "email": "alice.johnson@email.com",
            "address": "123 Main St, Springfield, IL 62701",
            "emergency_contact_name": "Bob Johnson",
            "emergency_contact_phone": "+1-555-0102",
            "blood_type": "A+",
            "allergies": ["penicillin"],
        },
        {
            "first_name": "Robert",
            "last_name": "Williams",
            "date_of_birth": "1972-07-22",
            "gender": "male",
            "phone": "+1-555-0201",
            "email": "robert.williams@email.com",
            "address": "456 Oak Ave, Springfield, IL 62702",
            "emergency_contact_name": "Mary Williams",
            "emergency_contact_phone": "+1-555-0202",
            "blood_type": "O-",
            "allergies": ["sulfa", "latex"],
        },
        {
            "first_name": "Maria",
            "last_name": "Garcia",
            "date_of_birth": "1990-11-08",
            "gender": "female",
            "phone": "+1-555-0301",
            "email": "maria.garcia@email.com",
            "address": "789 Elm Rd, Springfield, IL 62703",
            "emergency_contact_name": "Carlos Garcia",
            "emergency_contact_phone": "+1-555-0302",
            "blood_type": "B+",
            "allergies": [],
        },
        {
            "first_name": "David",
            "last_name": "Chen",
            "date_of_birth": "1968-01-30",
            "gender": "male",
            "phone": "+1-555-0401",
            "email": "david.chen@email.com",
            "address": "321 Pine Ln, Springfield, IL 62704",
            "emergency_contact_name": "Lisa Chen",
            "emergency_contact_phone": "+1-555-0402",
            "blood_type": "AB+",
            "allergies": ["aspirin"],
        },
        {
            "first_name": "Sarah",
            "last_name": "Brown",
            "date_of_birth": "1995-06-12",
            "gender": "female",
            "phone": "+1-555-0501",
            "email": "sarah.brown@email.com",
            "address": "654 Maple Dr, Springfield, IL 62705",
            "emergency_contact_name": "Tom Brown",
            "emergency_contact_phone": "+1-555-0502",
            "blood_type": "O+",
            "allergies": [],
        },
    ]

    patient_ids: list[str] = []
    for p in patients_data:
        resp = client.post("/patients", json=p, headers=admin_headers)
        if resp.status_code == 201:
            pid = resp.json()["id"]
            patient_ids.append(pid)
            print(f"  [+] Created patient: {p['first_name']} {p['last_name']} ({pid[:8]}...)")
        else:
            print(f"  [!] Failed: {p['first_name']} {p['last_name']} — {resp.status_code} {resp.text}")

    if len(patient_ids) < 2:
        print("\n[!] Not enough patients created, skipping appointments.")
        sys.exit(1)

    # ── 3. Create appointments ─────────────────────────────────────────
    print("\n--- Creating appointments ---")
    appointments_data = [
        {
            "patient_id": patient_ids[0],
            "doctor_id": str("00000000-0000-0000-0000-000000000001"),
            "scheduled_at": "2026-03-15T09:00:00Z",
            "duration_minutes": 30,
            "reason": "Annual physical examination",
        },
        {
            "patient_id": patient_ids[1],
            "doctor_id": str("00000000-0000-0000-0000-000000000001"),
            "scheduled_at": "2026-03-15T10:00:00Z",
            "duration_minutes": 45,
            "reason": "Follow-up for hypertension management",
        },
        {
            "patient_id": patient_ids[2],
            "doctor_id": str("00000000-0000-0000-0000-000000000002"),
            "scheduled_at": "2026-03-16T14:00:00Z",
            "duration_minutes": 30,
            "reason": "Persistent headaches",
        },
        {
            "patient_id": patient_ids[3],
            "doctor_id": str("00000000-0000-0000-0000-000000000001"),
            "scheduled_at": "2026-03-17T11:00:00Z",
            "duration_minutes": 60,
            "reason": "Comprehensive cardiac evaluation",
        },
        {
            "patient_id": patient_ids[4],
            "doctor_id": str("00000000-0000-0000-0000-000000000002"),
            "scheduled_at": "2026-03-17T15:30:00Z",
            "duration_minutes": 30,
            "reason": "Skin rash evaluation",
        },
    ]

    appointment_ids: list[str] = []
    for a in appointments_data:
        resp = client.post("/appointments", json=a, headers=admin_headers)
        if resp.status_code == 201:
            aid = resp.json()["id"]
            appointment_ids.append(aid)
            print(f"  [+] Appointment {aid[:8]}... — {a['reason']}")
        else:
            print(f"  [!] Failed: {a['reason']} — {resp.status_code} {resp.text}")

    # ── 4. Create clinical notes ───────────────────────────────────────
    print("\n--- Creating clinical notes ---")
    if appointment_ids:
        notes_data = [
            {
                "appointment_id": appointment_ids[0],
                "patient_id": patient_ids[0],
                "doctor_id": "00000000-0000-0000-0000-000000000001",
                "subjective": "Patient reports feeling generally well. No specific complaints. Here for routine annual checkup.",
                "objective": "BP 120/80, HR 72, Temp 98.6F. Heart and lung sounds normal. No abnormalities detected.",
                "assessment": "Healthy adult, no acute issues identified.",
                "plan": "Continue current lifestyle. Schedule follow-up in 12 months. Recommended flu vaccination.",
            },
            {
                "appointment_id": appointment_ids[1],
                "patient_id": patient_ids[1],
                "doctor_id": "00000000-0000-0000-0000-000000000001",
                "subjective": "Patient reports occasional dizziness and headaches. Currently on lisinopril 10mg daily.",
                "objective": "BP 145/92, HR 78. Slight ankle edema bilaterally. Labs: creatinine 1.1, K+ 4.2.",
                "assessment": "Hypertension, suboptimally controlled on current medication.",
                "plan": "Increase lisinopril to 20mg daily. Low-sodium diet counseling. Recheck BP in 4 weeks.",
            },
        ]

        for n in notes_data:
            resp = client.post("/notes", json=n, headers=doctor_headers)
            if resp.status_code == 201:
                nid = resp.json()["id"]
                print(f"  [+] Clinical note {nid[:8]}... for appointment {n['appointment_id'][:8]}...")
            else:
                print(f"  [!] Failed note for {n['appointment_id'][:8]}... — {resp.status_code} {resp.text}")

    # ── 5. Create invoices ─────────────────────────────────────────────
    print("\n--- Creating invoices ---")
    if appointment_ids:
        invoices_data = [
            {
                "appointment_id": appointment_ids[0],
                "patient_id": patient_ids[0],
                "amount": 250.00,
                "status": "issued",
            },
            {
                "appointment_id": appointment_ids[1],
                "patient_id": patient_ids[1],
                "amount": 175.00,
                "status": "issued",
            },
            {
                "appointment_id": appointment_ids[2],
                "patient_id": patient_ids[2],
                "amount": 200.00,
                "status": "draft",
            },
        ]

        invoice_ids: list[str] = []
        for inv in invoices_data:
            resp = client.post("/invoices", json=inv, headers=admin_headers)
            if resp.status_code == 201:
                iid = resp.json()["id"]
                invoice_ids.append(iid)
                print(f"  [+] Invoice {iid[:8]}... — ${inv['amount']} ({inv['status']})")
            else:
                print(f"  [!] Failed invoice — {resp.status_code} {resp.text}")

        # Mark first invoice as paid
        if invoice_ids:
            resp = client.patch(f"/invoices/{invoice_ids[0]}/pay", headers=admin_headers)
            if resp.status_code == 200:
                print(f"  [+] Marked invoice {invoice_ids[0][:8]}... as paid")

    # ── Summary ────────────────────────────────────────────────────────
    print("\n=== Seed Complete ===")
    print(f"  Users:        {len(users)}")
    print(f"  Patients:     {len(patient_ids)}")
    print(f"  Appointments: {len(appointment_ids)}")
    print(f"  Notes:        2")
    print(f"  Invoices:     3 (1 paid)")
    print(f"\nAdmin login:  admin@healthcare-demo.com / Admin1234!")
    print(f"Doctor login: dr.smith@healthcare-demo.com / Doctor1234!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed healthcare platform with demo data")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL of the API gateway")
    args = parser.parse_args()
    main(args.base_url)

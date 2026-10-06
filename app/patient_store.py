from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.local_data import CONDITION_LABELS, condition_label, normalize_custom_condition

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "patients.db"

SEED_PATIENTS = [
    {"name": "Eleanor Morgan", "sex": "Female", "age": 68, "conditions": ["hypertension", "type2_diabetes", "hyperlipidemia", "atrial_fibrillation"], "pill_limit": 5},
    {"name": "James Carter", "sex": "Male", "age": 54, "conditions": ["hypertension", "atrial_fibrillation"], "pill_limit": 3},
    {"name": "Priya Nair", "sex": "Female", "age": 61, "conditions": ["hypertension", "type2_diabetes"], "pill_limit": 4},
]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                sex TEXT NOT NULL,
                age INTEGER NOT NULL,
                conditions_json TEXT NOT NULL,
                pill_limit INTEGER NOT NULL DEFAULT 3,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        if count == 0:
            now = datetime.now(timezone.utc).isoformat()
            for i, patient in enumerate(SEED_PATIENTS, start=1):
                conn.execute(
                    """
                    INSERT INTO patients
                    (patient_id, name, sex, age, conditions_json, pill_limit, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"PT-2026-{[84, 112, 131][i-1]:03d}",
                        patient["name"], patient["sex"], patient["age"],
                        json.dumps(patient["conditions"]), patient["pill_limit"], now, now,
                    ),
                )


def _validate(patient: dict) -> None:
    name = str(patient.get("name", "")).strip()
    sex = str(patient.get("sex", "")).strip()
    age = int(patient.get("age", 0))
    raw_conditions = list(patient.get("conditions", []))
    conditions = []
    seen = set()
    for raw in raw_conditions:
        value = str(raw).strip()
        if not value:
            continue
        if value in CONDITION_LABELS:
            normalized = value
        elif value.startswith("custom:"):
            normalized = normalize_custom_condition(value)
        else:
            normalized = normalize_custom_condition(value)
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            conditions.append(normalized)
    pill_limit = int(patient.get("pill_limit", 3))
    if not name:
        raise ValueError("Patient name is required.")
    if not sex:
        raise ValueError("Sex is required.")
    if age < 0 or age > 120:
        raise ValueError("Age must be between 0 and 120.")
    if not conditions:
        raise ValueError("Select at least one condition.")
    patient["conditions"] = conditions
    if pill_limit < 1 or pill_limit > 8:
        raise ValueError("Daily pill limit must be between 1 and 8.")


def _row(row: sqlite3.Row) -> dict:
    conditions = json.loads(row["conditions_json"])
    return {
        "id": row["patient_id"],
        "name": row["name"],
        "sex": row["sex"],
        "age": row["age"],
        "conditions": conditions,
        "condition_labels": [condition_label(c) for c in conditions],
        "pill_limit": row["pill_limit"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_patients() -> list[dict]:
    init_db()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM patients ORDER BY id").fetchall()
    return [_row(row) for row in rows]


def get_patient(patient_id: str) -> dict | None:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
    return _row(row) if row else None


def create_patient(patient: dict) -> dict:
    _validate(patient)
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        next_num = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM patients").fetchone()[0]
        patient_id = f"PT-{datetime.now().year}-{next_num:03d}"
        conn.execute(
            """
            INSERT INTO patients
            (patient_id, name, sex, age, conditions_json, pill_limit, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (patient_id, patient["name"].strip(), patient["sex"].strip(), int(patient["age"]), json.dumps(patient["conditions"]), int(patient["pill_limit"]), now, now),
        )
        row = conn.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
    return _row(row)


def update_patient(patient_id: str, patient: dict) -> dict | None:
    _validate(patient)
    init_db()
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """
            UPDATE patients
            SET name = ?, sex = ?, age = ?, conditions_json = ?, pill_limit = ?, updated_at = ?
            WHERE patient_id = ?
            """,
            (patient["name"].strip(), patient["sex"].strip(), int(patient["age"]), json.dumps(patient["conditions"]), int(patient["pill_limit"]), now, patient_id),
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM patients WHERE patient_id = ?", (patient_id,)).fetchone()
    return _row(row)

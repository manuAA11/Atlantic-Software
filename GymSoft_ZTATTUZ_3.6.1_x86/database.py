from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from biometric import normalize_biometric_identifier

TICKET_PLAN_NAME = "tiquetera"
TICKET_ENTRY_LIMIT = 15
SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document TEXT NOT NULL UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    birthdate TEXT DEFAULT '',
    emergency_contact TEXT DEFAULT '',
    medical_notes TEXT DEFAULT '',
    biometric_identifier TEXT DEFAULT '',
    photo_path TEXT DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    duration_days INTEGER NOT NULL,
    price INTEGER NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    plan_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    amount INTEGER NOT NULL,
    payment_method TEXT NOT NULL,
    payment_reference TEXT DEFAULT '',
    paid_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT DEFAULT '',
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (plan_id) REFERENCES plans(id)
);

CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    membership_id INTEGER,
    checkin_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    method TEXT NOT NULL,
    result TEXT NOT NULL,
    notes TEXT DEFAULT '',
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE IF NOT EXISTS trainers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    specialty TEXT DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS routines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    trainer_id INTEGER,
    name TEXT NOT NULL,
    goal TEXT DEFAULT '',
    start_date TEXT NOT NULL,
    notes TEXT DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (trainer_id) REFERENCES trainers(id)
);

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    routine_id INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    name TEXT NOT NULL,
    sets TEXT DEFAULT '',
    reps TEXT DEFAULT '',
    weight TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (routine_id) REFERENCES routines(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    trainer_id INTEGER,
    starts_at TEXT NOT NULL,
    capacity INTEGER NOT NULL,
    notes TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'PROGRAMADA',
    FOREIGN KEY (trainer_id) REFERENCES trainers(id)
);

CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    client_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'RESERVADA',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_id, client_id),
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE INDEX IF NOT EXISTS idx_memberships_client_end
    ON memberships(client_id, end_date DESC);
CREATE INDEX IF NOT EXISTS idx_checkins_date
    ON checkins(checkin_at DESC);
CREATE INDEX IF NOT EXISTS idx_classes_start
    ON classes(starts_at);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

            checkin_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(checkins)"
                ).fetchall()
            }

            if "membership_id" not in checkin_columns:
                connection.execute(
                    """
                    ALTER TABLE checkins
                    ADD COLUMN membership_id INTEGER
                    """
                )

            client_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(clients)"
                ).fetchall()
            }
            if "biometric_identifier" not in client_columns:
                connection.execute(
                    "ALTER TABLE clients ADD COLUMN biometric_identifier TEXT DEFAULT ''"
                )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_biometric_identifier
                ON clients(biometric_identifier COLLATE NOCASE)
                WHERE trim(biometric_identifier) <> ''
                """
            )

            plan_count = connection.execute(
                "SELECT COUNT(*) FROM plans"
            ).fetchone()[0]

            if plan_count == 0:
                connection.executemany(
                    """
                    INSERT INTO plans(
                        name,
                        duration_days,
                        price,
                        active
                    )
                    VALUES (?, ?, ?, 1)
                    """,
                    [
                        ("Mensual", 30, 55_000),
                        ("Semanal", 7, 25_000),
                    ],
                )

    @staticmethod
    def _rows(
        rows: list[sqlite3.Row],
    ) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

    def seed_demo_data(self) -> None:
        with self.connect() as connection:
            count = connection.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
            if count:
                return

            connection.execute(
                """
                INSERT INTO clients(
                    document, first_name, last_name, phone, email,
                    emergency_contact, medical_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "DEMO-001",
                    "Valentina",
                    "Gómez",
                    "300 555 0101",
                    "valentina@demo.local",
                    "Carlos Gómez · 300 555 0199",
                    "Registro de demostración",
                ),
            )
            client_id = connection.execute(
                "SELECT id FROM clients WHERE document = 'DEMO-001'"
            ).fetchone()[0]
            monthly = connection.execute(
                "SELECT id, duration_days, price FROM plans WHERE name = 'Mensual'"
            ).fetchone()
            start = date.today()
            end = start + timedelta(days=int(monthly["duration_days"]) - 1)
            connection.execute(
                """
                INSERT INTO memberships(
                    client_id, plan_id, start_date, end_date, amount,
                    payment_method, payment_reference, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    monthly["id"],
                    start.isoformat(),
                    end.isoformat(),
                    monthly["price"],
                    "Efectivo",
                    "DEMO",
                    "Pago de demostración",
                ),
            )
            connection.execute(
                """
                INSERT INTO trainers(name, phone, email, specialty)
                VALUES (?, ?, ?, ?)
                """,
                ("Andrés Martínez", "310 555 0188", "andres@demo.local", "Fuerza"),
            )

    # Dashboard
    def dashboard_metrics(self) -> dict[str, int]:
        today = date.today().isoformat()
        month_start = date.today().replace(day=1).isoformat()
        with self.connect() as connection:
            active_clients = connection.execute(
                "SELECT COUNT(*) FROM clients WHERE active = 1"
            ).fetchone()[0]
            valid_memberships = connection.execute(
                """
                SELECT COUNT(*) FROM clients c
                WHERE c.active = 1 AND EXISTS (
                    SELECT 1 FROM memberships m
                    WHERE m.client_id = c.id AND m.start_date <= ? AND m.end_date >= ?
                )
                """,
                (today, today),
            ).fetchone()[0]
            checkins_today = connection.execute(
                """
                SELECT COUNT(*) FROM checkins
                WHERE date(checkin_at) = ? AND result = 'PERMITIDA'
                """,
                (today,),
            ).fetchone()[0]
            income_month = connection.execute(
                """
                SELECT COALESCE(SUM(amount), 0) FROM memberships
                WHERE date(paid_at) >= ?
                """,
                (month_start,),
            ).fetchone()[0]
        return {
            "active_clients": int(active_clients),
            "valid_memberships": int(valid_memberships),
            "expired_memberships": max(int(active_clients) - int(valid_memberships), 0),
            "checkins_today": int(checkins_today),
            "income_month": int(income_month),
        }

    def upcoming_expirations(self, days: int = 7) -> list[dict[str, Any]]:
        today = date.today()
        limit = today + timedelta(days=days)
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.document,
                       c.first_name || ' ' || c.last_name AS client_name,
                       MAX(m.end_date) AS end_date
                FROM clients c
                JOIN memberships m ON m.client_id = c.id
                WHERE c.active = 1
                GROUP BY c.id
                HAVING MAX(m.end_date) BETWEEN ? AND ?
                ORDER BY end_date
                """,
                (today.isoformat(), limit.isoformat()),
            ).fetchall()
        return self._rows(rows)

    # Clients and memberships
    def list_clients(self, search: str = "") -> list[dict[str, Any]]:
        pattern = f"%{search.strip()}%"
        today = date.today().isoformat()
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.*,
                       COALESCE((
                           SELECT MAX(m.end_date) FROM memberships m
                           WHERE m.client_id = c.id
                       ), '') AS membership_end,
                       CASE
                           WHEN c.active = 0 THEN 'INACTIVO'
                           WHEN COALESCE((
                               SELECT MAX(m.end_date) FROM memberships m
                               WHERE m.client_id = c.id
                           ), '') >= ? THEN 'AL DÍA'
                           ELSE 'VENCIDO'
                       END AS membership_status
                FROM clients c
                WHERE c.document LIKE ?
                   OR c.first_name LIKE ?
                   OR c.last_name LIKE ?
                   OR (c.first_name || ' ' || c.last_name) LIKE ?
                   OR c.phone LIKE ?
                   OR c.email LIKE ?
                   OR c.biometric_identifier LIKE ?
                ORDER BY c.active DESC, c.first_name, c.last_name
                """,
                (
                    today,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                    pattern,
                ),
            ).fetchall()
        return self._rows(rows)

    def get_client(self, client_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM clients WHERE id = ?", (client_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_client_by_document(self, document: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM clients WHERE document = ? COLLATE NOCASE",
                (document.strip(),),
            ).fetchone()
        return dict(row) if row else None

    def get_client_by_biometric_identifier(
        self,
        identifier: str,
    ) -> dict[str, Any] | None:
        code = normalize_biometric_identifier(identifier)
        if not code:
            return None
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM clients
                WHERE biometric_identifier = ? COLLATE NOCASE
                """,
                (code,),
            ).fetchone()
        return dict(row) if row else None

    def save_client(self, data: dict[str, Any], client_id: int | None = None) -> int:
        fields = (
            "document",
            "first_name",
            "last_name",
            "phone",
            "email",
            "birthdate",
            "emergency_contact",
            "biometric_identifier",
            "photo_path",
            "active",
        )
        values = [data.get(field, "") for field in fields]
        biometric_index = fields.index("biometric_identifier")
        values[biometric_index] = normalize_biometric_identifier(
            values[biometric_index]
        )
        if client_id is None:
            placeholders = ", ".join("?" for _ in fields)
            with self.connect() as connection:
                cursor = connection.execute(
                    f"INSERT INTO clients({', '.join(fields)}) VALUES ({placeholders})",
                    values,
                )
                return int(cursor.lastrowid)
        assignments = ", ".join(f"{field} = ?" for field in fields)
        with self.connect() as connection:
            connection.execute(
                f"UPDATE clients SET {assignments} WHERE id = ?", values + [client_id]
            )
        return client_id

    def delete_client(self, client_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM reservations WHERE client_id = ?",
                (client_id,),
            )
            connection.execute(
                "DELETE FROM routines WHERE client_id = ?",
                (client_id,),
            )
            connection.execute(
                "DELETE FROM checkins WHERE client_id = ?",
                (client_id,),
            )
            connection.execute(
                "DELETE FROM memberships WHERE client_id = ?",
                (client_id,),
            )
            connection.execute(
                "DELETE FROM clients WHERE id = ?",
                (client_id,),
            )

    def list_plans(self, active_only: bool = True) -> list[dict[str, Any]]:
        query = "SELECT * FROM plans"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY duration_days"
        with self.connect() as connection:
            rows = connection.execute(query).fetchall()
        return self._rows(rows)

    def add_plan(self, name: str, duration_days: int, price: int) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO plans(name, duration_days, price) VALUES (?, ?, ?)",
                (name.strip(), duration_days, price),
            )
            return int(cursor.lastrowid)
    def update_plan(
        self,
        plan_id: int,
        name: str,
        duration_days: int,
        price: int,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE plans
                SET name = ?, duration_days = ?, price = ?
                WHERE id = ?
                """,
                (
                    name.strip(),
                    duration_days,
                    price,
                    plan_id,
                ),
            )

    def set_plan_active(
        self,
        plan_id: int,
        active: bool,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE plans
                SET active = ?
                WHERE id = ?
                """,
                (int(active), plan_id),
            )
    def add_membership(
        self,
        client_id: int,
        plan_id: int,
        start_date: str,
        amount: int,
        payment_method: str,
        payment_reference: str = "",
        notes: str = "",
    ) -> int:
        start = date.fromisoformat(start_date)
        with self.connect() as connection:
            plan = connection.execute(
                "SELECT duration_days FROM plans WHERE id = ?", (plan_id,)
            ).fetchone()
            if not plan:
                raise ValueError("El plan seleccionado no existe.")
            end = start + timedelta(days=int(plan["duration_days"]) - 1)
            cursor = connection.execute(
                """
                INSERT INTO memberships(
                    client_id, plan_id, start_date, end_date, amount,
                    payment_method, payment_reference, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    plan_id,
                    start.isoformat(),
                    end.isoformat(),
                    amount,
                    payment_method,
                    payment_reference.strip(),
                    notes.strip(),
                ),
            )
            return int(cursor.lastrowid)

    def list_memberships(self, client_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT m.*, p.name AS plan_name
                FROM memberships m
                JOIN plans p ON p.id = m.plan_id
                WHERE m.client_id = ?
                ORDER BY m.paid_at DESC, m.id DESC
                """,
                (client_id,),
            ).fetchall()
        return self._rows(rows)

    def membership_snapshot(
        self,
        client_id: int,
    ) -> dict[str, Any]:
        today = date.today().isoformat()

        with self.connect() as connection:
            client = connection.execute(
                """
                SELECT *
                FROM clients
                WHERE id = ?
                """,
                (client_id,),
            ).fetchone()

            if not client:
                raise ValueError("Cliente no encontrado.")

            membership = connection.execute(
                """
                SELECT m.*, p.name AS plan_name
                FROM memberships m
                JOIN plans p ON p.id = m.plan_id
                WHERE m.client_id = ?
                ORDER BY m.end_date DESC, m.id DESC
                LIMIT 1
                """,
                (client_id,),
            ).fetchone()

            entries_used = 0
            entry_limit = None

            if membership:
                plan_name = (
                    membership["plan_name"]
                    .strip()
                    .lower()
                )

                if plan_name == TICKET_PLAN_NAME:
                    entry_limit = TICKET_ENTRY_LIMIT

                    entries_used = connection.execute(
                        """
                        SELECT COUNT(*)
                        FROM checkins
                        WHERE membership_id = ?
                          AND result = 'PERMITIDA'
                        """,
                        (membership["id"],),
                    ).fetchone()[0]

        result = dict(client)
        result["membership_id"] = (
            int(membership["id"])
            if membership
            else None
        )
        result["client_name"] = (
            f"{client['first_name']} "
            f"{client['last_name']}"
        )

        result["entry_limit"] = entry_limit
        result["entries_used"] = int(entries_used)

        result["entries_remaining"] = (
            max(entry_limit - int(entries_used), 0)
            if entry_limit is not None
            else None
        )

        if not client["active"]:
            result.update(
                status="INACTIVO",
                allowed=False,
                membership_end="",
                plan_name=(
                    membership["plan_name"]
                    if membership
                    else "Sin plan"
                ),
            )

        elif not membership:
            result.update(
                status="VENCIDO",
                allowed=False,
                membership_end="",
                plan_name="Sin plan",
            )

        elif not (
            membership["start_date"]
            <= today
            <= membership["end_date"]
        ):
            result.update(
                status="VENCIDO",
                allowed=False,
                membership_end=membership["end_date"],
                plan_name=membership["plan_name"],
            )

        elif (
            entry_limit is not None
            and entries_used >= entry_limit
        ):
            result.update(
                status="SIN ENTRADAS",
                allowed=False,
                membership_end=membership["end_date"],
                plan_name=membership["plan_name"],
            )

        else:
            result.update(
                status="AL DÍA",
                allowed=True,
                membership_end=membership["end_date"],
                plan_name=membership["plan_name"],
            )

        return result
    # Check-ins
    def register_checkin(
        self, client_id: int, method: str, override: bool = False
    ) -> dict[str, Any]:
        snapshot = self.membership_snapshot(client_id)
        allowed = bool(snapshot["allowed"] or override)
        result = "PERMITIDA" if allowed else "DENEGADA"
        notes = "Autorización manual" if override and not snapshot["allowed"] else ""
        timestamp = datetime.now().isoformat(sep=" ", timespec="seconds")
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO checkins(
                    client_id,
                    membership_id,
                    checkin_at,
                    method,
                    result,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    client_id,
                    snapshot.get("membership_id"),
                    timestamp,
                    method,
                    result,
                    notes,
                ),
            )
        if (
            allowed
            and snapshot["allowed"]
            and snapshot.get("entry_limit") is not None
        ):
            snapshot["entries_used"] += 1
            snapshot["entries_remaining"] = max(
                snapshot["entry_limit"]
                - snapshot["entries_used"],
                0,
            )

        snapshot.update(
            result=result,
            checkin_at=timestamp,
            override=override,
        )

        return snapshot
        return snapshot

    def list_checkins(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT ch.*, c.document,
                       c.first_name || ' ' || c.last_name AS client_name
                FROM checkins ch
                JOIN clients c ON c.id = ch.client_id
                ORDER BY ch.checkin_at DESC, ch.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return self._rows(rows)

    # Trainers and routines
    def list_trainers(self, active_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM trainers"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY active DESC, name"
        with self.connect() as connection:
            rows = connection.execute(query).fetchall()
        return self._rows(rows)

    def save_trainer(self, data: dict[str, Any], trainer_id: int | None = None) -> int:
        values = [
            data.get("name", "").strip(),
            data.get("phone", "").strip(),
            data.get("email", "").strip(),
            data.get("specialty", "").strip(),
            int(data.get("active", 1)),
        ]
        with self.connect() as connection:
            if trainer_id is None:
                cursor = connection.execute(
                    """
                    INSERT INTO trainers(name, phone, email, specialty, active)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    values,
                )
                return int(cursor.lastrowid)
            connection.execute(
                """
                UPDATE trainers
                SET name = ?, phone = ?, email = ?, specialty = ?, active = ?
                WHERE id = ?
                """,
                values + [trainer_id],
            )
        return trainer_id

    def create_routine(
        self,
        client_id: int,
        trainer_id: int | None,
        name: str,
        goal: str,
        start_date: str,
        notes: str,
    ) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO routines(client_id, trainer_id, name, goal, start_date, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (client_id, trainer_id, name.strip(), goal.strip(), start_date, notes.strip()),
            )
            return int(cursor.lastrowid)

    def list_routines(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT r.*, c.first_name || ' ' || c.last_name AS client_name,
                       COALESCE(t.name, 'Sin asignar') AS trainer_name,
                       (SELECT COUNT(*) FROM exercises e WHERE e.routine_id = r.id) AS exercise_count
                FROM routines r
                JOIN clients c ON c.id = r.client_id
                LEFT JOIN trainers t ON t.id = r.trainer_id
                ORDER BY r.active DESC, r.start_date DESC, r.id DESC
                """
            ).fetchall()
        return self._rows(rows)

    def add_exercise(
        self,
        routine_id: int,
        day_name: str,
        name: str,
        sets: str,
        reps: str,
        weight: str,
        notes: str,
    ) -> int:
        with self.connect() as connection:
            position = connection.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM exercises WHERE routine_id = ?",
                (routine_id,),
            ).fetchone()[0]
            cursor = connection.execute(
                """
                INSERT INTO exercises(
                    routine_id, day_name, name, sets, reps, weight, notes, position
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    routine_id,
                    day_name.strip(),
                    name.strip(),
                    sets.strip(),
                    reps.strip(),
                    weight.strip(),
                    notes.strip(),
                    position,
                ),
            )
            return int(cursor.lastrowid)

    def list_exercises(self, routine_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM exercises
                WHERE routine_id = ?
                ORDER BY day_name, position, id
                """,
                (routine_id,),
            ).fetchall()
        return self._rows(rows)

    # Classes and reservations
    def create_class(
        self,
        name: str,
        trainer_id: int | None,
        starts_at: str,
        capacity: int,
        notes: str,
    ) -> int:
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO classes(name, trainer_id, starts_at, capacity, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name.strip(), trainer_id, starts_at, capacity, notes.strip()),
            )
            return int(cursor.lastrowid)

    def list_classes(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT cl.*, COALESCE(t.name, 'Sin asignar') AS trainer_name,
                       SUM(CASE WHEN r.status = 'RESERVADA' THEN 1 ELSE 0 END) AS reserved
                FROM classes cl
                LEFT JOIN trainers t ON t.id = cl.trainer_id
                LEFT JOIN reservations r ON r.class_id = cl.id
                GROUP BY cl.id
                ORDER BY cl.starts_at, cl.id
                """
            ).fetchall()
        return self._rows(rows)

    def reserve_class(self, class_id: int, client_id: int) -> int:
        with self.connect() as connection:
            gym_class = connection.execute(
                """
                SELECT cl.capacity,
                       SUM(CASE WHEN r.status = 'RESERVADA' THEN 1 ELSE 0 END) AS reserved
                FROM classes cl
                LEFT JOIN reservations r ON r.class_id = cl.id
                WHERE cl.id = ?
                GROUP BY cl.id
                """,
                (class_id,),
            ).fetchone()
            if not gym_class:
                raise ValueError("La clase no existe.")
            if int(gym_class["reserved"] or 0) >= int(gym_class["capacity"]):
                raise ValueError("La clase ya no tiene cupos disponibles.")
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO reservations(class_id, client_id, status)
                    VALUES (?, ?, 'RESERVADA')
                    """,
                    (class_id, client_id),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("El cliente ya está reservado en esta clase.") from exc
            return int(cursor.lastrowid)

    def list_reservations(self, class_id: int) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT r.*, c.document,
                       c.first_name || ' ' || c.last_name AS client_name
                FROM reservations r
                JOIN clients c ON c.id = r.client_id
                WHERE r.class_id = ?
                ORDER BY c.first_name, c.last_name
                """,
                (class_id,),
            ).fetchall()
        return self._rows(rows)

    def cancel_reservation(self, reservation_id: int) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE reservations SET status = 'CANCELADA' WHERE id = ?",
                (reservation_id,),
            )

    def backup(self, destination: str | Path) -> Path:
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.path)
        target = sqlite3.connect(destination_path)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return destination_path

    def restore(self, source: str | Path) -> Path:
        source_path = Path(source)

        if not source_path.is_file():
            raise ValueError("El archivo seleccionado no existe.")

        if source_path.resolve() == self.path.resolve():
            raise ValueError(
                "No puedes importar la misma base de datos que está usando el programa."
            )

        required_tables = {
            "clients",
            "plans",
            "memberships",
            "checkins",
            "trainers",
            "routines",
            "exercises",
            "classes",
            "reservations",
        }

        source_connection = sqlite3.connect(source_path)

        try:
            integrity = source_connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()

            if not integrity or integrity[0] != "ok":
                raise ValueError("El respaldo está dañado.")

            existing_tables = {
                row[0]
                for row in source_connection.execute(
                    """
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """
                ).fetchall()
            }

            missing_tables = required_tables - existing_tables

            if missing_tables:
                raise ValueError(
                    "El archivo seleccionado no es un respaldo válido de GymSoft."
                )

            automatic_backup = self.path.parent / (
                f"respaldo-antes-importacion-"
                f"{datetime.now():%Y%m%d-%H%M%S}.db"
            )

            self.backup(automatic_backup)

            destination_connection = sqlite3.connect(self.path)

            try:
                source_connection.backup(destination_connection)
            finally:
                destination_connection.close()

        finally:
            source_connection.close()

        return automatic_backup

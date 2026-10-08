from __future__ import annotations
from gym_time import display_timestamp, local_datetime, timezone_for, parse_instant, parse_instant
from plan_forms import membership_request
from server_date import ServerDate

import sqlite3
from datetime import date
from typing import Any

from biometric import normalize_biometric_identifier

from cloud import CloudService


class ReceptionDatabase:
    """Acceso mínimo permitido para la aplicación de recepción."""

    def __init__(self, cloud: CloudService) -> None:
        if not cloud.gym_id:
            raise ValueError("No hay un gimnasio conectado.")

        self.cloud = cloud
        self.client = cloud.client
        self.gym_id = str(cloud.gym_id)
        self._server_date = ServerDate(getattr(cloud, 'timezone', 'America/Bogota'))

    def _execute(self, query: Any) -> Any:
        try:
            return query.execute()
        except Exception as error:
            code = str(getattr(error, "code", ""))
            message = str(error)
            lowered = message.lower()

            if (
                code == "23505" or "duplicate key" in lowered
            ) and (
                "biometric" in lowered
                or "biométrico" in lowered
            ):
                raise ValueError(
                    "Este identificador biométrico ya pertenece a otro cliente."
                ) from error

            if code == "23505" or "duplicate key" in lowered:
                raise sqlite3.IntegrityError(message) from error

            if code == "42501" or "permission" in lowered:
                raise PermissionError(
                    "Esta cuenta no tiene permiso para realizar esa acción."
                ) from error

            raise

    @staticmethod
    def _json_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)

        if (
            isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], dict)
        ):
            return dict(value[0])

        return {}

    @staticmethod
    def _json_list(value: Any) -> list[Any]:
        if not isinstance(value, list):
            return []

        if len(value) == 1 and isinstance(value[0], list):
            return list(value[0])

        return list(value)

    def _timestamp(self, value: Any) -> str:
        return display_timestamp(value, timezone_for(self))

    @staticmethod
    def _checkin_method(value: Any) -> str:
        method = str(value or "").strip()

        if method.casefold() in {
            "simulación",
            "simulacion",
            "demo",
        }:
            return "REGISTRO MANUAL"

        return method or "REGISTRO MANUAL"

    def today(self) -> date:
        return self._server_date.get(self._fetch_clock)

    def _fetch_clock(self):
        clock = self._execute(self.client.rpc('gym_local_clock', {'p_gym_id': self.gym_id})).data
        if not isinstance(clock, dict):
            raise ValueError('No se pudo consultar el reloj del gimnasio.')
        parse_instant(clock['now'])
        self.cloud.timezone = clock['timezone']
        return clock

    def invalidate_today_cache(self) -> None:
        self._server_date.invalidate()

    def list_clients(
        self,
        search: str = "",
    ) -> list[dict[str, Any]]:
        response = self._execute(
            self.client.rpc(
                "reception_list_clients",
                {
                    "p_gym_id": self.gym_id,
                    "p_search": search.strip(),
                },
            )
        )

        data = self._json_list(response.data)

        if not isinstance(data, list):
            raise ValueError("Supabase devolvió clientes no válidos.")

        return [
            dict(item)
            for item in data
            if isinstance(item, dict)
        ]

    def membership_snapshot(
        self,
        client_id: int,
    ) -> dict[str, Any]:
        response = self._execute(
            self.client.rpc(
                "reception_membership_snapshot",
                {
                    "p_gym_id": self.gym_id,
                    "p_client_id": int(client_id),
                },
            )
        )

        data = self._json_dict(response.data)

        if not isinstance(data, dict):
            raise ValueError("Supabase devolvió una membresía no válida.")

        return dict(data)

    def save_client(
        self,
        data: dict[str, Any],
        client_id: int | None = None,
    ) -> int:
        birthdate = str(data.get("birthdate", "")).strip() or None

        response = self._execute(
            self.client.rpc(
                "reception_save_client",
                {
                    "p_gym_id": self.gym_id,
                    "p_client_id": client_id,
                    "p_document": str(
                        data.get("document", "")
                    ).strip(),
                    "p_first_name": str(
                        data.get("first_name", "")
                    ).strip(),
                    "p_last_name": str(
                        data.get("last_name", "")
                    ).strip(),
                    "p_phone": str(
                        data.get("phone", "")
                    ).strip(),
                    "p_email": str(
                        data.get("email", "")
                    ).strip(),
                    "p_birthdate": birthdate,
                    "p_biometric_identifier": normalize_biometric_identifier(
                        data.get("biometric_identifier", "")
                    ),
                },
            )
        )

        value = response.data

        if isinstance(value, list):
            value = value[0] if value else None

        if isinstance(value, dict):
            value = value.get("reception_save_client")

        if value is None:
            raise ValueError("No fue posible guardar el cliente.")

        return int(value)

    def find_client_by_biometric_identifier(
        self,
        identifier: str,
    ) -> dict[str, Any] | None:
        code = normalize_biometric_identifier(identifier)
        if not code:
            return None
        response = self._execute(
            self.client.rpc(
                "reception_find_client_by_biometric",
                {
                    "p_gym_id": self.gym_id,
                    "p_biometric_identifier": code,
                },
            )
        )
        data = self._json_dict(response.data)
        return dict(data) if data else None

    def create_expense(self, data: dict[str, Any]) -> int:
        # GymSoft-RECEPTION-EXPENSES-2.0.4
        response = self._execute(
            self.client.rpc(
                "reception_create_expense",
                {
                    "p_gym_id": self.gym_id,
                    "p_expense_date": str(data.get("expense_date", "")).strip(),
                    "p_category": str(data.get("category", "")).strip(),
                    "p_description": str(data.get("description", "")).strip(),
                    "p_vendor": str(data.get("vendor", "")).strip(),
                    "p_amount": int(data.get("amount") or 0),
                    "p_payment_method": str(data.get("payment_method", "")).strip(),
                    "p_payment_reference": str(data.get("payment_reference", "")).strip(),
                    "p_receipt_reference": str(data.get("receipt_reference", "")).strip(),
                    "p_notes": str(data.get("notes", "")).strip(),
                },
            )
        )

        value = response.data
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, dict):
            value = value.get("reception_create_expense", value.get("id"))
        if value is None:
            raise ValueError("Supabase no devolvió el número del gasto.")
        return int(value)

    def ticket_followup(self):
        response = self._execute(self.client.rpc('ticket_followup', {'p_gym_id': self.gym_id}))
        rows = response.data or []
        if not isinstance(rows, list):
            raise ValueError('No se pudo consultar el saldo de las tiqueteras.')
        return rows

    def list_plans(self) -> list[dict[str, Any]]:
        response = self._execute(
            self.client.table("plans")
            .select("id, name, duration_days, duration_months, price, entry_limit")
            .eq("gym_id", self.gym_id)
            .eq("active", True)
            .order("duration_days")
        )

        return [
            dict(item)
            for item in list(response.data or [])
        ]

    def add_membership(
        self,
        client_id: int,
        plan_id: int,
        start_date: str,
        amount: int,
        payment_method: str,
        payment_reference: str = "",
        notes: str = "",
        carryover: bool = False,
        initial_entries_used: int = 0,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        rpc_name, params = membership_request(
            self.gym_id, client_id, plan_id, start_date, amount, payment_method,
            payment_reference, notes, carryover=carryover,
            initial_entries_used=initial_entries_used, request_id=request_id)
        response = self._execute(self.client.rpc(rpc_name, params))
        
        rows = list(response.data or [])

        if not rows or not isinstance(rows[0], dict):
            raise ValueError("No fue posible registrar el pago.")

        return dict(rows[0])

    def list_memberships(
        self,
        client_id: int,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        response = self._execute(
            self.client.rpc(
                "reception_list_memberships",
                {
                    "p_gym_id": self.gym_id,
                    "p_client_id": int(client_id),
                    "p_limit": int(limit),
                },
            )
        )

        data = self._json_list(response.data)

        if not isinstance(data, list):
            raise ValueError("Supabase devolvió pagos no válidos.")

        result = []

        for row in data:
            if not isinstance(row, dict):
                continue

            item = dict(row)
            item["amount"] = int(item.get("amount") or 0)
            item["paid_at"] = self._timestamp(item.get("paid_at"))
            result.append(item)

        return result

    def list_store_products(
        self,
        search: str = "",
    ) -> list[dict[str, Any]]:
        response = self._execute(
            self.client.rpc(
                "reception_list_store_products",
                {
                    "p_gym_id": self.gym_id,
                    "p_search": search.strip(),
                },
            )
        )
        return [
            dict(item)
            for item in self._json_list(response.data)
            if isinstance(item, dict)
        ]

    def register_store_sale(
        self,
        product_id: int,
        quantity: int,
        payment_method: str,
        payment_reference: str = "",
        customer_name: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        response = self._execute(
            self.client.rpc(
                "register_store_sale",
                {
                    "p_gym_id": self.gym_id,
                    "p_product_id": int(product_id),
                    "p_quantity": int(quantity),
                    "p_payment_method": payment_method.strip(),
                    "p_payment_reference": payment_reference.strip(),
                    "p_customer_name": customer_name.strip(),
                    "p_notes": notes.strip(),
                },
            )
        )
        data = self._json_dict(response.data)
        if not data:
            raise ValueError("No fue posible registrar la venta.")
        return data

    def register_checkin(
        self,
        client_id: int,
        method: str = "RECEPCIÓN",
    ) -> dict[str, Any]:
        response = self._execute(
            self.client.rpc(
                "reception_register_checkin",
                {
                    "p_gym_id": self.gym_id,
                    "p_client_id": int(client_id),
                    "p_method": method.strip() or "RECEPCIÓN",
                },
            )
        )

        data = self._json_dict(response.data)

        if not isinstance(data, dict):
            raise ValueError("Supabase devolvió una entrada no válida.")

        return dict(data)

    def list_checkins(
        self,
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        response = self._execute(
            self.client.rpc(
                "reception_list_checkins",
                {
                    "p_gym_id": self.gym_id,
                    "p_limit": int(limit),
                },
            )
        )

        data = self._json_list(response.data)

        if not isinstance(data, list):
            raise ValueError("Supabase devolvió entradas no válidas.")

        result = []

        for row in data:
            if not isinstance(row, dict):
                continue

            item = dict(row)
            item["checkin_at"] = self._timestamp(
                item.get("checkin_at")
            )
            item["method"] = self._checkin_method(
                item.get("method")
            )
            result.append(item)

        return result

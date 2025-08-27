"""
Message processor for Partner Sync Service.

Notes:
    - Consumes normalized SQS items produced by the Risk Service.
    - Creates/updates PartnerSyncRecord rows and runs reconciliation.
    - External partner data is simulated for demo purposes.
"""

import json

from .models import PartnerSyncRecord
from .partner_data_simulator import PartnerDataSimulator


class MessageProcessor:
    """Process incoming SQS messages for partner data reconciliation."""

    def parse_message(self, message_body: str) -> list[dict]:
        """
        Parse SQS message body into debtor data array.

        Notes:
            - Expects JSON array format from SQS Message.
            - Each item should have: debtor_id, internal_balance, internal_status, processed_at.

        Args:
            message_body: Raw SQS message body as string.

        Returns:
            list[dict]: Array of debtor data dictionaries.

        Raises:
            ValueError: If the message body is not a valid JSON array.
        """
        try:
            data = json.loads(message_body)
            if not isinstance(data, list):
                raise ValueError("Expected JSON array in message body")
            return data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in message body: {e}")

    def create_sync_records(self, debtor_data: list[dict]) -> list:
        """
        Create or update PartnerSyncRecord entries from debtor data.

        Notes:
            - Uses PartnerDataSimulator to generate external fields.
            - Sets reconciliation_status to PENDING initially.

        Args:
            debtor_data: Parsed debtor data from SQS message.

        Returns:
            list: Created PartnerSyncRecord instances.
        """

        records = []

        simulator = PartnerDataSimulator()
        external_items = simulator.simulate_external_data(debtor_data)

        for item in external_items:
            debtor_id = item.get("debtor_id")
            internal_balance = item.get("internal_balance")
            internal_status = item.get("internal_status")
            external_balance = item.get("external_balance")
            external_status = item.get("external_status")

            if not all(v is not None for v in (external_balance, external_status)):
                missing = []
                if external_balance is None:
                    missing.append("external_balance")
                if external_status is None:
                    missing.append("external_status")
                print(
                    f"[PartnerSync] Warning: Skipping item; missing required fields: {', '.join(missing)}"
                )
                continue

            record, _ = PartnerSyncRecord.objects.update_or_create(
                debtor_id=debtor_id,
                defaults={
                    "internal_balance": internal_balance,
                    "external_balance": external_balance,
                    "internal_status": internal_status,
                    "external_status": external_status,
                    "reconciliation_status": "PENDING",
                },
            )
            records.append(record)

        return records

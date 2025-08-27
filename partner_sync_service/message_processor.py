"""
Message processor for Partner Sync Service.

Notes:
    - Consumes normalized SQS items produced by the Risk Service.
    - Creates/updates PartnerSyncRecord rows and runs reconciliation.
    - External partner data is simulated for demo purposes.
"""

import json


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

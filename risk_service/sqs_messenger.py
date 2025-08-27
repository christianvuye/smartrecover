"""
SQS messaging for high-priority debtor notifications.

Notes:
    - Sends batches of high-priority debtors to Partner Sync Service.
    - Uses dependency injection pattern for clean separation.
    - MAX_LOGGED_DEBTOR_IDS limits how many debtor IDs we preview in prototype logs
      to keep output readable. Adjust if logs become too noisy/quiet.
"""

from datetime import datetime, timezone

MAX_LOGGED_DEBTOR_IDS = 5


class SQSMessenger:
    """Send high-priority debtor batches via SQS."""

    def send_high_priority_batch(self, high_priority_results: list[dict]) -> dict:
        """
        Send batch of high-priority debtors to SQS queue.

        Args:
            high_priority_results: List of debtor processing results above threshold.

        Returns:
            dict: Minimal summary for metrics: {"count": int}.
        """
        count = len(high_priority_results)
        if count == 0:
            return {"count": 0}

        sent_at = datetime.now(timezone.utc).isoformat()
        payload = self.create_payload(high_priority_results, sent_at)

        first_ids: list[int] = []
        for item in payload[:MAX_LOGGED_DEBTOR_IDS]:
            if item.get("debtor_id") is not None:
                first_ids.append(item["debtor_id"])

        self.log_summary(count, first_ids)
        self.send_to_sqs(payload)

        return {"count": count}

    def create_payload(self, results: list[dict], sent_at: str) -> list[dict]:
        """
        Create normalized payload items for Partner Sync Service.

        Args:
            results: Raw debtor processing results from BulkProcessor.
            sent_at: ISO8601 timestamp to include per item.

        Returns:
            list[dict]: Normalized items with required fields.
        """
        payload: list[dict] = []
        for result in results:
            debtor_id = result.get("debtor_id")
            if debtor_id is None:
                print("[SQS] Warning: Skipping result with missing debtor_id")
                continue
            internal_balance = result.get("debt_amount")
            internal_status = result.get("payment_status")
            item = {
                "debtor_id": debtor_id,
                "internal_balance": internal_balance,
                "internal_status": internal_status,
                "processed_at": sent_at,
            }
            payload.append(item)
        return payload

    def log_summary(self, count: int, first_ids: list[int]) -> None:
        """
        Print concise operational summary for prototype visibility.

        Args:
            count: Number of high-priority debtors to send.
            first_ids: List of first debtor IDs to include in the summary.

        Returns:
            None
        """
        print(
            f"[SQS] Sending {count} high-priority debtors to Partner Sync Service; "
            f"first_ids={first_ids}"
        )

    def send_to_sqs(self, items: list[dict]) -> None:
        """
        Transmit items to SQS (prototype no-op; replace with boto3 in production).

        Notes:
            - For debugging, print the first 5 items to console.

        Args:
            items: List of dicts to send to SQS.

        Returns:
            None
        """
        print(f"[SQS DEBUG] Payload format: {items[:5]}")
        return None

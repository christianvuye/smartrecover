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
            dict: Summary with count, first_ids, and timestamp (for testing/observability).
        """
        sent_at = datetime.now(timezone.utc).isoformat()
        count = len(high_priority_results)

        first_ids: list[int] = []
        for result in high_priority_results[:MAX_LOGGED_DEBTOR_IDS]:
            debtor_id = result.get("debtor_id")
            if debtor_id is not None:
                first_ids.append(debtor_id)

        if count > 0:
            print(
                f"[SQS] Sending {count} high-priority debtors to Partner Sync Service; "
                f"first_ids={first_ids}"
            )
            # TODO: For production, use boto3 to send to actual SQS queue

        return {"count": count, "first_ids": first_ids, "timestamp": sent_at}

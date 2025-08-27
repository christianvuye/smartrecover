"""
Reconciliation engine for partner data comparison.

Notes:
    - Compares internal vs external partner data for discrepancies.
    - Sets reconciliation_status based on balance and status differences.
"""

from decimal import Decimal

from .models import PartnerSyncRecord


class ReconciliationEngine:
    """Compares internal vs external data and sets reconciliation status."""

    def reconcile_records(self, records: list, tolerance_percent: float = 1.0) -> dict:
        """
        Analyze records and set reconciliation_status based on discrepancies.

        Notes:
            - Balance tolerance: ±tolerance_percent (default 1.0%) considered MATCHED when
              internal balance is non-zero.
            - Zero-balance handling: if internal balance is 0, matched only when external
              balance is also 0 (no percent tolerance applied).
            - Status comparison: must match exactly for MATCHED; otherwise DISCREPANCY.
            - Updates reconciliation_status directly on each record and saves it.

        Args:
            records: List of PartnerSyncRecord instances to analyze.
            tolerance_percent: Balance variance threshold (default 1.0%).

        Returns:
            dict: Summary with matched_count, discrepancy_count, total_processed.
        """
        if tolerance_percent < 0:
            raise ValueError("tolerance_percent must be >= 0")
        tolerance_percent = min(tolerance_percent, 100.0)

        matched_count = 0
        discrepancy_count = 0

        tolerance_decimal = Decimal(str(tolerance_percent)) / Decimal("100")

        for record in records:
            internal_balance = Decimal(str(record.internal_balance))
            external_balance = Decimal(str(record.external_balance))

            if internal_balance == Decimal("0"):
                balance_matches = external_balance == Decimal("0")
            else:
                variance = abs(external_balance - internal_balance) / internal_balance
                balance_matches = variance <= tolerance_decimal
            status_matches = record.internal_status == record.external_status

            if balance_matches and status_matches:
                record.reconciliation_status = PartnerSyncRecord.STATUS_MATCHED
                matched_count += 1
            else:
                record.reconciliation_status = PartnerSyncRecord.STATUS_DISCREPANCY
                discrepancy_count += 1

            record.save()

        return {
            "matched_count": matched_count,
            "discrepancy_count": discrepancy_count,
            "total_processed": len(records),
        }

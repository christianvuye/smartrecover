"""
Partner sync domain models.

Notes:
    - Tracks reconciliation between internal data and external partner systems.
    - Used by sync jobs to detect and resolve discrepancies.
"""

from django.db import models


class PartnerSyncRecord(models.Model):
    """
    Synchronization record with an external partner.

    Notes:
        - debtor_id: links to internal debtor reference.
        - Balances: internal vs external for reconciliation.
        - Statuses: internal vs external payment states.
        - Reconciliation status: overall reconciliation state and metadata.
    """

    debtor_id = models.IntegerField(unique=True)

    internal_balance = models.DecimalField(max_digits=12, decimal_places=2)
    external_balance = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    internal_status = models.CharField(
        max_length=7,
        choices=[
            ("UNPAID", "Unpaid"),
            ("PARTIAL", "Partial Payment"),
            ("PAID", "Fully Paid"),
        ],
    )
    external_status = models.CharField(
        max_length=7,
        choices=[
            ("UNPAID", "Unpaid"),
            ("PARTIAL", "Partial Payment"),
            ("PAID", "Fully Paid"),
        ],
        null=True,
        blank=True,
    )

    reconciliation_status = models.CharField(
        max_length=12,
        choices=[
            ("PENDING", "Pending Sync"),
            ("MATCHED", "Data Matched"),
            ("DISCREPANCY", "Data Mismatch"),
        ],
        default="PENDING",
    )

    synced_at = models.DateTimeField(auto_now=True)
    partner_name = models.CharField(max_length=50, default="TruAccord")

    class Meta:
        db_table = "partner_sync_records"

    def __str__(self) -> str:
        """
        Return human-readable sync summary.

        Returns:
            str: Partner name, debtor id, and reconciliation status.
        """
        return f"{self.partner_name} • Debtor {self.debtor_id} • {self.reconciliation_status}"

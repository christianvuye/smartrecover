"""
Partner data simulation for external partner integration.

Summary:
    - Generates external_balance and external_status for reconciliation demos.
    - Behavior controlled by VARIANCE_MIN/MAX and STATUS_MISMATCH_PROB.
    - Determinism supported via an injectable RNG; defaults to random.
"""

import random
from decimal import Decimal

VARIANCE_MIN = -0.10
VARIANCE_MAX = 0.10
STATUS_MISMATCH_PROB = 0.2
STATUS_CHOICES = ("UNPAID", "PARTIAL", "PAID")


class PartnerDataSimulator:
    """Simulates external partner data for reconciliation testing."""

    def simulate_external_data(self, internal_data: list[dict], rng=None) -> list[dict]:
        """
        Simulate external partner data using module-level parameters.

        Notes:
            - Skips items missing debtor_id, internal_balance, or internal_status
            - Balance variance ~ U[VARIANCE_MIN, VARIANCE_MAX]; status mismatch ~ STATUS_MISMATCH_PROB
            - Pass an RNG (uniform/random/choice) for reproducible tests

        Args:
            internal_data: list[dict] — Input records with debtor_id, internal_balance, internal_status.
            rng: Optional RNG; defaults to random.

        Returns:
            list[dict]: Items with external_balance and external_status.
        """
        external_data = []
        rng = rng or random

        for item in internal_data:
            if not all(
                k in item for k in ("debtor_id", "internal_balance", "internal_status")
            ):
                print(
                    "[PartnerSimulator] Warning: Skipping item with missing required fields"
                )
                continue

            external_item = item.copy()
            internal_balance = Decimal(str(item["internal_balance"]))
            variance = Decimal(str(rng.uniform(VARIANCE_MIN, VARIANCE_MAX)))
            external_balance = internal_balance * (Decimal("1") + variance)
            external_item["external_balance"] = round(external_balance, 2)
            if rng.random() < STATUS_MISMATCH_PROB:
                other_statuses = [
                    s for s in STATUS_CHOICES if s != item["internal_status"]
                ]
                external_item["external_status"] = (
                    rng.choice(other_statuses)
                    if other_statuses
                    else item["internal_status"]
                )
            else:
                external_item["external_status"] = item["internal_status"]

            external_data.append(external_item)

        return external_data

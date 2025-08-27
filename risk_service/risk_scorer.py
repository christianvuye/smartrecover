"""
Risk scoring engine and helpers for debt recovery.

Notes:
    - Provides normalization, weighting, and persistence of risk scores.
"""

from decimal import Decimal

from .models import Debtor, RiskScore
from .scoring_constants import (
    CONTRACT_RISK_SCORES,
    EMPLOYMENT_RISK_SCORES,
    FAMILY_RISK_SCORES,
    INDUSTRY_RISK_SCORES,
)


class RiskScorer:
    """
    Risk scoring engine for debt recovery.

    Notes:
        - Normalizes multiple factors to 0–10 and applies weights.
        - Uses FACTOR_WEIGHTS to compute a weighted total score.
        - Outputs total_score, risk_level, and a factor breakdown.
    """

    FACTOR_WEIGHTS = {
        "debt_ratio": 9,
        "payment_history": 9,
        "employment_status": 8,
        "contract_type": 7,
        "industry_sector": 6,
        "family_situation": 6,
    }

    def normalize_debt_ratio(self, debtor: Debtor):
        """
        Convert debt-to-income ratio to a 0–10 risk score.

        Notes:
            - No/negative income returns 10 (max risk).
            - Thresholds: ≤1.0→2, ≤3.0→5, ≤6.0→7, else→10.

        Args:
            debtor: Debtor — Source for income and debt amounts.

        Returns:
            int: Risk score on a 0–10 scale.
        """
        if debtor.monthly_income <= 0:
            return 10

        ratio = debtor.total_debt_amount / debtor.monthly_income

        if ratio <= Decimal("1.0"):
            return 2
        elif ratio <= Decimal("3.0"):
            return 5
        elif ratio <= Decimal("6.0"):
            return 7
        else:
            return 10

    def normalize_payment_history(self, debtor: Debtor):
        """
        Convert late payment count to a 0–10 risk score.

        Notes:
            - Thresholds: 0→1, ≤2→4, ≤5→7, else→10.

        Args:
            debtor: Debtor — Source for late payment count.

        Returns:
            int: Risk score on a 0–10 scale.
        """
        late_count = debtor.late_payments_count

        if late_count == 0:
            return 1
        elif late_count <= 2:
            return 4
        elif late_count <= 5:
            return 7
        else:
            return 10

    def get_employment_risk(self, debtor: Debtor) -> int:
        """
        Get employment risk via O(1) lookup.

        Args:
            debtor: Debtor — Source for employment status.

        Returns:
            int: Risk score (default 5 when unknown).
        """
        return EMPLOYMENT_RISK_SCORES.get(debtor.employment_status, 5)

    def get_contract_risk(self, debtor: Debtor) -> int:
        """
        Get contract type risk score.

        Args:
            debtor: Debtor — Source for contract type.

        Returns:
            int: Risk score (default 5 when unknown).
        """
        return CONTRACT_RISK_SCORES.get(debtor.contract_type, 5)

    def get_industry_risk(self, debtor: Debtor) -> int:
        """
        Get industry sector risk score.

        Args:
            debtor: Debtor — Source for industry sector.

        Returns:
            int: Risk score (default 5 when unknown).
        """
        return INDUSTRY_RISK_SCORES.get(debtor.industry_sector, 5)

    def get_family_risk(self, debtor: Debtor) -> int:
        """
        Get family situation risk score.

        Args:
            debtor: Debtor — Source for family situation.

        Returns:
            int: Risk score (default 5 when unknown).
        """
        return FAMILY_RISK_SCORES.get(debtor.family_situation, 5)

    def get_risk_level(self, weighted_score: float) -> str:
        """
        Convert weighted score to a human-readable risk level.

        Notes:
            - Computes percentage of theoretical max using FACTOR_WEIGHTS.
            - Thresholds: ≤30→LOW, ≤60→MEDIUM, ≤80→HIGH, else→CRITICAL.

        Args:
            weighted_score: float — Weighted sum of factor scores.

        Returns:
            str: One of "LOW", "MEDIUM", "HIGH", "CRITICAL".
        """
        max_possible_score = sum(10 * weight for weight in self.FACTOR_WEIGHTS.values())

        risk_percentage = (weighted_score / max_possible_score) * 100

        if risk_percentage <= 30:
            return "LOW"
        elif risk_percentage <= 60:
            return "MEDIUM"
        elif risk_percentage <= 80:
            return "HIGH"
        else:
            return "CRITICAL"

    def calculate_risk_score(self, debtor: Debtor) -> dict:
        """
        Calculate weighted risk score and persist to the database.

        Notes:
            - Normalizes factors, applies weights, derives risk level.
            - Persists via update_or_create on RiskScore.
            - Returns score, breakdown, level, timestamp, and creation flag.

        Args:
            debtor: Debtor — Entity to score and persist.

        Returns:
            dict: {
                "total_score": float,
                "normalized_scores": dict,
                "risk_level": str,
                "calculated_at": str,
                "created": bool,
            }
        """

        normalized_scores = {
            "debt_ratio": self.normalize_debt_ratio(debtor),
            "payment_history": self.normalize_payment_history(debtor),
            "employment_status": self.get_employment_risk(debtor),
            "contract_type": self.get_contract_risk(debtor),
            "industry_sector": self.get_industry_risk(debtor),
            "family_situation": self.get_family_risk(debtor),
        }

        weighted_score = sum(
            score * self.FACTOR_WEIGHTS[factor]
            for factor, score in normalized_scores.items()
        )

        risk_level = self.get_risk_level(weighted_score)

        score_obj, created = RiskScore.objects.update_or_create(
            debtor=debtor,
            defaults={
                "total_score": weighted_score,
                "risk_level": risk_level,
                "factor_breakdown": normalized_scores,
            },
        )

        return {
            "total_score": weighted_score,
            "normalized_scores": normalized_scores,
            "risk_level": risk_level,
            "calculated_at": score_obj.calculated_at.isoformat(),
            "created": created,
        }

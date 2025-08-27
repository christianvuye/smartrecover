"""
Django ORM models for debt recovery domain.

Notes:
    - Debtor stores inputs for scoring; RiskScore stores computed results.
"""

from django.db import models

from .choices import (
    CONTRACT_PERMANENT,
    CONTRACT_TYPE_CHOICES,
    EMPLOYMENT_STATUS_CHOICES,
    FAMILY_SITUATION_CHOICES,
    INDUSTRY_SECTOR_CHOICES,
)


class Debtor(models.Model):
    """
    Debtor model.

    Notes:
        - Stores financial and profile attributes used for risk scoring.
        - Includes audit timestamps: created_at, updated_at.
    """

    name = models.CharField(max_length=255)
    total_debt_amount = models.DecimalField(max_digits=10, decimal_places=2)
    late_payments_count = models.PositiveIntegerField()
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2)
    employment_status = models.CharField(
        max_length=20,
        choices=EMPLOYMENT_STATUS_CHOICES,
        help_text="Employment status affects income stability assessment",
    )
    contract_type = models.CharField(
        max_length=20, choices=CONTRACT_TYPE_CHOICES, default=CONTRACT_PERMANENT
    )
    industry_sector = models.CharField(
        max_length=30,
        choices=INDUSTRY_SECTOR_CHOICES,
        help_text="Industry sector affects risk assessment",
    )
    family_situation = models.CharField(
        max_length=30,
        choices=FAMILY_SITUATION_CHOICES,
        help_text="Family situation affects financial stability assessment",
    )

    # Timestamps for auditing
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """
        Return human-readable debtor representation.

        Returns:
            str: Debtor name and total debt.
        """
        return f"{self.name} - Debt: ${self.total_debt_amount}"

    class Meta:
        verbose_name = "Debtor"
        verbose_name_plural = "Debtors"


class RiskScore(models.Model):
    """
    Stores calculated risk scores for a debtor.

    Notes:
        - One-to-one relation with Debtor (related_name="risk_score").
        - factor_breakdown stores per-factor scores (JSON).
    """

    debtor = models.OneToOneField(
        Debtor, on_delete=models.CASCADE, related_name="risk_score"
    )
    total_score = models.FloatField()
    risk_level = models.CharField(max_length=20)
    factor_breakdown = models.JSONField()
    calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Risk Score"
        verbose_name_plural = "Risk Scores"

    def __str__(self):
        """
        Return human-readable risk score representation.

        Returns:
            str: Debtor name with risk level and total score.
        """
        return f"{self.debtor.name} - {self.risk_level} ({self.total_score})"

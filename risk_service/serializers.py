"""
DRF serializers for risk_service models.

Notes:
    - DebtorSerializer handles CRUD payloads for Debtor.
    - RiskScoreSerializer exposes score fields and debtor_name.
"""

from rest_framework import serializers

from .models import Debtor, RiskScore


class DebtorSerializer(serializers.ModelSerializer):
    """
    Serializer for Debtor model.

    Notes:
        - Converts to/from JSON for Debtor instances.
    """

    class Meta:
        model = Debtor
        fields = [
            "id",
            "name",
            "total_debt_amount",
            "late_payments_count",
            "monthly_income",
            "employment_status",
            "contract_type",
            "industry_sector",
            "family_situation",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "name", "created_at", "updated_at"]


class RiskScoreSerializer(serializers.ModelSerializer):
    """
    Serializer for RiskScore model.

    Notes:
        - Includes read-only debtor_name via nested field.
    """

    debtor_name = serializers.CharField(source="debtor.name", read_only=True)

    class Meta:
        model = RiskScore
        fields = [
            "id",
            "debtor",
            "debtor_name",
            "total_score",
            "risk_level",
            "factor_breakdown",
            "calculated_at",
        ]
        read_only_fields = [
            "id",
            "debtor",
            "debtor_name",
            "total_score",
            "risk_level",
            "factor_breakdown",
            "calculated_at",
        ]

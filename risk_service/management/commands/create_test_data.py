"""
Management command to create sample debtors and print risk scores.

Notes:
    - Creates low- and high-risk example debtors.
    - Runs the risk scoring engine and outputs key fields.
"""

from django.core.management.base import BaseCommand

from risk_service.choices import (
    CONTRACT_FREELANCE,
    CONTRACT_PERMANENT,
    EMPLOYMENT_GOVERNMENT,
    EMPLOYMENT_UNEMPLOYED,
    FAMILY_MARRIED_DUAL_INCOME,
    FAMILY_SINGLE_WITH_DEPENDENTS,
    INDUSTRY_HEALTHCARE,
    INDUSTRY_HOSPITALITY,
)
from risk_service.models import Debtor, RiskScore
from risk_service.risk_scorer import RiskScorer


class Command(BaseCommand):
    help = "Create test debtors and run risk scoring"

    def handle(self, *args, **options):
        Debtor.objects.all().delete()

        low_risk = Debtor.objects.create(
            name="Alice Johnson",
            total_debt_amount=2000.00,
            monthly_income=8000.00,
            late_payments_count=0,
            employment_status=EMPLOYMENT_GOVERNMENT,
            contract_type=CONTRACT_PERMANENT,
            industry_sector=INDUSTRY_HEALTHCARE,
            family_situation=FAMILY_MARRIED_DUAL_INCOME,
        )

        high_risk = Debtor.objects.create(
            name="Bob Smith",
            total_debt_amount=50000.00,
            monthly_income=3000.00,
            late_payments_count=8,
            employment_status=EMPLOYMENT_UNEMPLOYED,
            contract_type=CONTRACT_FREELANCE,
            industry_sector=INDUSTRY_HOSPITALITY,
            family_situation=FAMILY_SINGLE_WITH_DEPENDENTS,
        )

        scorer = RiskScorer()

        self.stdout.write("=== LOW RISK DEBTOR ===")
        low_result = scorer.calculate_risk_score(low_risk)
        self.stdout.write(f"Total Score: {low_result['total_score']}")
        self.stdout.write(f"Risk Level: {low_result['risk_level']}")
        self.stdout.write(f"Factor Breakdown: {low_result['normalized_scores']}")

        self.stdout.write("\n=== HIGH RISK DEBTOR ===")
        high_result = scorer.calculate_risk_score(high_risk)
        self.stdout.write(f"Total Score: {high_result['total_score']}")
        self.stdout.write(f"Risk Level: {high_result['risk_level']}")
        self.stdout.write(f"Factor Breakdown: {high_result['normalized_scores']}")
        self.stdout.write(self.style.SUCCESS("Test data created and scored!"))

        self.stdout.write("\n=== DATABASE VERIFICATION ===")
        for score_record in RiskScore.objects.all():
            self.stdout.write(
                f"{score_record.debtor.name}: {score_record.total_score} ({score_record.risk_level})"
            )
            self.stdout.write(f"Calculated at: {score_record.calculated_at}")

"""
Management command to validate model relationships and BulkProcessor access patterns.

Notes:
    - Verifies basic database access and counts.
    - Checks Debtor→RiskScore relationship and priority calculation path.
    - Exercises BulkProcessor.calculate_priority for a small sample.
"""

from django.core.management import CommandError
from django.core.management.base import BaseCommand

from risk_service.models import Debtor, RiskScore
from risk_service.risk_scorer import RiskScorer


class Command(BaseCommand):
    help = "Test Django model relationships and attribute access for BulkProcessor"

    def handle(self, *args, **options):
        self.stdout.write("=== Testing Model Relationships ===")

        # Test 1: Basic model access
        try:
            debtor_count = Debtor.objects.count()
            risk_score_count = RiskScore.objects.count()

            self.stdout.write(f"Found {debtor_count} debtors")
            self.stdout.write(f"Found {risk_score_count} risk scores")

            if debtor_count == 0:
                raise CommandError(
                    "No debtors found. Run 'python manage.py create_test_data' first"
                )

        except Exception as e:
            raise CommandError(f"Database access failed: {e}")

        self.stdout.write("\n=== Testing Relationship Access ===")

        for debtor in Debtor.objects.all()[:2]:  # Test first 2 debtors
            self.stdout.write(f"\nTesting debtor: {debtor.name}")
            self.stdout.write(f"Debt amount: ${debtor.total_debt_amount}")

            try:
                risk_score_value = debtor.risk_score.total_score
                self.stdout.write(f"✅ Risk score found: {risk_score_value}")

                priority = risk_score_value * float(debtor.total_debt_amount)
                self.stdout.write(f"✅ Priority calculation: {priority:.0f}")

            except RiskScore.DoesNotExist:
                self.stdout.write("❌ No risk score - testing on-demand calculation...")

                try:
                    scorer = RiskScorer()
                    score_result = scorer.calculate_risk_score(debtor)
                    risk_score_value = score_result["total_score"]

                    priority = risk_score_value * float(debtor.total_debt_amount)
                    self.stdout.write(f"✅ Calculated risk score: {risk_score_value}")
                    self.stdout.write(f"✅ Priority: {priority:.0f}")

                except Exception as calc_error:
                    self.stdout.write(f"❌ Calculation failed: {calc_error}")

            except AttributeError as attr_error:
                self.stdout.write(f"❌ Attribute access failed: {attr_error}")

            except Exception as e:
                self.stdout.write(f"❌ Unexpected error: {e}")

        self.stdout.write("\n=== Testing BulkProcessor Priority Method ===")

        try:
            from risk_service.bulk_processor import BulkProcessor

            processor = BulkProcessor()

            for debtor in Debtor.objects.all()[:2]:
                try:
                    priority = processor.calculate_priority(debtor)
                    self.stdout.write(f"✅ {debtor.name} priority: {priority:.0f}")
                except Exception as e:
                    self.stdout.write(
                        f"❌ Priority calculation failed for {debtor.name}: {e}"
                    )

        except ImportError:
            self.stdout.write(
                "❌ BulkProcessor not created yet - will test after implementation"
            )

        self.stdout.write(self.style.SUCCESS("\n=== Relationship Testing Complete ==="))

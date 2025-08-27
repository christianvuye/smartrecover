"""
Test the message processor with actual SQS message formats.
"""

import random

from django.core.management.base import BaseCommand

from partner_sync_service.message_processor import MessageProcessor
from partner_sync_service.models import PartnerSyncRecord
from partner_sync_service.reconciliation_engine import ReconciliationEngine


class Command(BaseCommand):
    help = "Test MessageProcessor with actual SQS message format"

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed", type=int, help="Seed RNG for deterministic simulation"
        )
        parser.add_argument(
            "--tolerance",
            type=float,
            default=5.0,
            help="Reconciliation tolerance percent",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear PartnerSyncRecord table before run",
        )

    def handle(self, *args, **options):
        processor = MessageProcessor()

        # Real SQS message format from your debug output
        test_message = '[{"debtor_id": 35757, "internal_balance": 74331.83, "internal_status": "PAID", "processed_at": "2025-08-27T12:23:12.758932+00:00"}, {"debtor_id": 33458, "internal_balance": 74691.53, "internal_status": "UNPAID", "processed_at": "2025-08-27T12:23:12.758932+00:00"}]'

        self.stdout.write("=== Testing MessageProcessor ===\n")

        # Test valid message
        try:
            result = processor.parse_message(test_message)
            self.stdout.write(f"✅ Successfully parsed {len(result)} debtor records")
            self.stdout.write(f"First record: {result[0]}")
            self.stdout.write(f"Record keys: {list(result[0].keys())}")
        except Exception as e:
            self.stdout.write(f"❌ Failed to parse valid message: {e}")

        # Test invalid JSON
        try:
            processor.parse_message("invalid json")
            self.stdout.write("❌ Should have failed on invalid JSON")
        except ValueError as e:
            self.stdout.write(f"✅ Correctly caught invalid JSON: {e}")

        # Test non-array JSON
        try:
            processor.parse_message('{"not": "an_array"}')
            self.stdout.write("❌ Should have failed on non-array")
        except ValueError as e:
            self.stdout.write(f"✅ Correctly caught non-array: {e}")

        self.stdout.write("\n🎯 MessageProcessor validation complete!")
        self.stdout.write("\n=== Testing Full Integration ===")
        try:
            # Parse -> Simulate -> Create Records
            parsed_data = processor.parse_message(test_message)

            if options.get("seed") is not None:
                random.seed(options["seed"])

            if options.get("clear"):
                PartnerSyncRecord.objects.all().delete()
                self.stdout.write("Cleared PartnerSyncRecord table")

            created_records = processor.create_sync_records(parsed_data)

            self.stdout.write(
                f"✅ Created {len(created_records)} PartnerSyncRecord entries"
            )

            # Show first record details
            if created_records:
                first_record = created_records[0]
                self.stdout.write(f"Debtor {first_record.debtor_id}:")
                self.stdout.write(
                    f"  Internal: ${first_record.internal_balance} | {first_record.internal_status}"
                )
                self.stdout.write(
                    f"  External: ${first_record.external_balance} | {first_record.external_status}"
                )
                self.stdout.write(f"  Status: {first_record.reconciliation_status}")

            self.stdout.write("\n=== Testing Reconciliation Engine ===")

            if not created_records:
                self.stdout.write("No records created; skipping reconciliation test")
                return

            reconciler = ReconciliationEngine()
            tolerance = options.get("tolerance", 5.0)
            result = reconciler.reconcile_records(
                created_records, tolerance_percent=tolerance
            )

            self.stdout.write(f"✅ Reconciliation complete (tolerance={tolerance}%):")
            self.stdout.write(f"  Matched: {result['matched_count']}")
            self.stdout.write(f"  Discrepancies: {result['discrepancy_count']}")
            self.stdout.write(f"  Total processed: {result['total_processed']}")

            # Show updated status
            if created_records:
                first_record.refresh_from_db()
                self.stdout.write(
                    f"  First record status: {first_record.reconciliation_status}"
                )

        except Exception as e:
            self.stdout.write(f"❌ Integration test failed: {e}")

        self.stdout.write("\n🎯 Full message processing pipeline tested!")

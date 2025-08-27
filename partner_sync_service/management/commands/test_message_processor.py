"""
Test the message processor with actual SQS message formats.
"""

from django.core.management.base import BaseCommand

from partner_sync_service.message_processor import MessageProcessor


class Command(BaseCommand):
    help = "Test MessageProcessor with actual SQS message format"

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

        except Exception as e:
            self.stdout.write(f"❌ Integration test failed: {e}")

        self.stdout.write("\n🎯 Full message processing pipeline tested!")

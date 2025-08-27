"""
Management command to process debtors using a heap-based priority queue.

Notes:
    - Supports dry-run preview of top-K priority accounts.
    - Configurable batch size and high-priority threshold.
    - Optional JSON output of the final processing report.
"""

import heapq
import json

from django.core.management.base import BaseCommand

from risk_service.bulk_processor import BulkProcessor


class Command(BaseCommand):
    help = "Process debtors using priority-based debt recovery algorithms"

    def add_arguments(self, parser):
        """
        Define CLI arguments for the command.

        Args:
            parser: ArgumentParser — Django management command parser.

        Returns:
            None
        """
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of debtors to process per batch (default: 100)",
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=500000,
            help="High priority threshold for flagging accounts (default: 500000)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Build priority queue and show top 10 without processing",
        )
        parser.add_argument(
            "--top-k",
            type=int,
            default=10,
            help="Number of top priority accounts to preview in --dry-run (default: 10)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output the final processing report as JSON",
        )

    def handle(self, *args, **options):
        """
        Entry point for the command.

        Notes:
            - Initializes BulkProcessor with provided options.
            - Routes to dry-run or full processing mode.
            - Passes stdout to processor for progress logging.

        Args:
            *args: tuple — Unused positional args.
            **options: dict — Parsed CLI options.

        Returns:
            None
        """
        self.stdout.write("=== SmartRecover Debt Processing System ===\n")

        mode = "DRY RUN" if options["dry_run"] else "FULL"
        self.stdout.write(
            f"Mode: {mode} | batch_size={options['batch_size']} | threshold={options['threshold']} | top_k={options.get('top_k', 10)}\n"
        )

        processor = BulkProcessor(
            batch_size=options["batch_size"],
            high_priority_threshold=options["threshold"],
        )

        processor.stdout = self.stdout

        if options["dry_run"]:
            self._handle_dry_run(processor, options["top_k"])
        else:
            self._handle_full_processing(processor, json_output=options["json"])

    def _handle_dry_run(self, processor, top_k: int):
        """
        Show top-K highest priority debtors without processing.

        Notes:
            - Builds the priority queue and previews the top-K using
              heapq.nsmallest without mutating the heap.

        Args:
            processor: BulkProcessor — Engine to build the priority queue.
            top_k: int — Number of entries to preview.

        Returns:
            None
        """
        self.stdout.write("DRY RUN MODE - Building priority queue...\n")

        priority_queue = processor.build_priority_queue()

        self.stdout.write(f"Built heap with {len(priority_queue)} debtors")
        if not priority_queue:
            self.stdout.write("No debtors found.\n")
            return

        self.stdout.write(f"Top {top_k} highest priority accounts:\n")

        sorted_preview = heapq.nsmallest(top_k, priority_queue)

        for i, (neg_priority, debtor_id) in enumerate(sorted_preview, 1):
            priority = -neg_priority
            self.stdout.write(
                f"{i:2d}. Debtor ID {debtor_id}: Priority {priority:,.2f}"
            )

        self.stdout.write(
            f"\nUse without --dry-run to process all {len(priority_queue)} debtors"
        )

    def _handle_full_processing(self, processor, json_output: bool = False):
        """
        Execute full debt recovery processing.

        Notes:
            - Processes all debtors via BulkProcessor and prints results.
            - Optionally outputs the final report as JSON and exits.

        Args:
            processor: BulkProcessor — Engine to process debtors end-to-end.
            json_output: bool — If True, print JSON report and return.

        Returns:
            None
        """
        self.stdout.write("Starting full debt recovery processing...\n")

        report = processor.process_all_debtors()

        if json_output:
            self.stdout.write(json.dumps(report, indent=2))
            return

        self._display_processing_report(report)

    def _display_processing_report(self, report):
        """
        Format and display the processing report.

        Args:
            report: dict — Processing report from BulkProcessor.

        Returns:
            None
        """
        summary = report["summary"]

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("         PROCESSING COMPLETE")
        self.stdout.write("=" * 50)

        self.stdout.write(
            f"✅ Total debtors processed: {summary['total_debtors_successfully_processed']:,}"
        )
        self.stdout.write(
            f"🔥 High priority accounts: {summary['high_priority_debtors_successfully_processed']:,}"
        )
        self.stdout.write(
            f"⏱️  Processing time: {summary['processing_time_seconds']:.2f} seconds"
        )
        self.stdout.write(f"📦 Batches completed: {summary['batches_processed']}")

        if summary["errors_count"] > 0:
            self.stdout.write(f"⚠️  Errors encountered: {summary['errors_count']}")
            self.stdout.write("\nFirst few errors:")
            for error in report["errors"][:3]:
                self.stdout.write(
                    f"  - Debtor {error['debtor_id']} ({error.get('stage', 'unknown stage')}): {error['error_message']}"
                )
        else:
            self.stdout.write("✅ No processing errors")

        if (
            summary["total_debtors_successfully_processed"] == 0
            and summary["errors_count"] == 0
        ):
            self.stdout.write("(No debtors were available to process.)")

        if report["detailed_results"]:
            self.stdout.write("\nTop 5 Processed Accounts:")
            for i, result in enumerate(report["detailed_results"][:5], 1):
                if result["status"] == "success":
                    self.stdout.write(
                        f"{i}. {result['debtor_name']} - "
                        f"Priority: {result['priority_score']:,.0f} "
                        f"(Risk: {result['risk_score']}, Debt: ${result['debt_amount']:,.0f})"
                    )

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("🎯 Debt recovery processing complete!")

        if summary["processing_time_seconds"] > 0:
            throughput = (
                summary["total_debtors_successfully_processed"]
                / summary["processing_time_seconds"]
            )
            self.stdout.write(
                f"📊 Processing throughput: {throughput:.1f} debtors/second"
            )

        self.stdout.write(
            "\n💡 Algorithm used: Heap-based priority queue (O(log n) extraction)"
        )
        self.stdout.write("🎯 Business logic: Risk score × Debt amount prioritization")

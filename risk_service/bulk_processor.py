"""
Bulk processing engine for debt recovery.

Notes:
    - Builds priority queues and processes debtors in batches.
    - Integrates with RiskScorer and records processing statistics.
"""

import heapq
import time

from django.db.models import QuerySet
from django.utils import timezone

from .models import Debtor, RiskScore
from .risk_scorer import RiskScorer
from .sqs_messenger import SQSMessenger


class BulkProcessor:
    """
    Orchestrates bulk debt recovery processing with a priority queue for scale.
    Uses a min-heap with negative priorities to process highest (risk × debt) first.
    """

    def __init__(
        self,
        batch_size: int = 100,
        high_priority_threshold: float = 500000,
        messenger: SQSMessenger | None = None,
    ) -> None:
        """
        Initialize processor configuration and state.

        Notes:
            - Configure batch size and high-priority threshold
            - Initialize risk scorer and metrics (processed, errors, timing)
            - Threshold is configurable (constructor param), not hardcoded

        Args:
            batch_size: Debtors processed per iteration (resource management)
            high_priority_threshold: Threshold for flagging high-priority accounts
            messenger: SQSMessenger instance for high-priority notifications

        Returns:
            None
        """
        self.batch_size: int = batch_size
        self.high_priority_threshold: float = high_priority_threshold
        self.scorer: RiskScorer = RiskScorer()
        self.stats: dict[str, int | float | list[dict]] = {
            "total_processed": 0,
            "high_priority_count": 0,
            "processing_time": 0,
            "errors": [],
        }
        self.messenger = messenger

    def calculate_priority(self, debtor: Debtor) -> float:
        """
        Compute composite priority (risk_score × debt_amount).

        Notes:
            - Try existing score via debtor.risk_score.total_score
            - If missing, compute on-demand with self.scorer
            - Multiply score by debt amount (float(DecimalField))
            - Exceptions propagate to caller

        Args:
            debtor: Debtor instance to score

        Returns:
            float: Composite priority score
        """
        try:
            risk_score = debtor.risk_score.total_score
        except RiskScore.DoesNotExist:
            score_result = self.scorer.calculate_risk_score(debtor)
            risk_score = score_result["total_score"]

        priority = risk_score * float(debtor.total_debt_amount)
        return priority

    def build_priority_queue(
        self, queryset: QuerySet | None = None
    ) -> list[tuple[float, int]]:
        """
        Build a max-priority heap of debtors (risk_score × debt_amount) using
        negative priorities.

        Notes:
            - Orchestrates queue construction.
            - queryset optional: filter specific debtors or process all.
            - Default: fetch all with select_related("risk_score") to avoid N+1.
            - Flow: _build_priority_tuples(); heapify in O(n); heap used by
              heappop().
            - Metrics and error recording handled in _build_priority_tuples().

        Args:
            queryset: QuerySet | None — Optional queryset; defaults to all debtors.

        Returns:
            list[tuple[float, int]] — (-priority, debtor_id) tuples.
        """
        if queryset is None:
            queryset = Debtor.objects.select_related("risk_score").all()

        priority_tuples = self._build_priority_tuples(queryset)

        heapq.heapify(priority_tuples)

        return priority_tuples

    def _build_priority_tuples(self, queryset: QuerySet) -> list[tuple[float, int]]:
        """
        Build priority tuples from a queryset.

        Notes:
            - Produces (-priority, debtor_id); priority = risk_score × debt_amount.
            - Exceptions from calculate_priority are caught and recorded.

        Args:
            queryset: QuerySet — Debtors to evaluate.

        Returns:
            list[tuple[float, int]] — (-priority, debtor_id) tuples.
        """
        priority_tuples = []
        for debtor in queryset:
            try:
                priority = self.calculate_priority(debtor)
                priority_tuples.append((-priority, debtor.id))
            except Exception as e:
                self._record_error(debtor.id, str(e), "priority_calculation")

        return priority_tuples

    def _update_processing_stats(self, priority: float) -> None:
        """
        Update processing counters and classifications.

        Notes:
            - Increments total_processed counter.
            - Classifies as high priority when priority > high_priority_threshold.

        Args:
            priority: float — Composite priority score for the debtor.

        Returns:
            None
        """
        self.stats["total_processed"] += 1
        if priority > self.high_priority_threshold:
            self.stats["high_priority_count"] += 1

    def _record_error(self, debtor_id: int, error_message: str, stage: str) -> None:
        """
        Record structured error information in processing statistics.

        Notes:
            - Stages tracked: "priority_calculation", "debtor_processing".

        Args:
            debtor_id: int — Identifier of the debtor that failed.
            error_message: str — Exception details or failure reason.
            stage: str — Pipeline stage where the failure occurred.

        Returns:
            None
        """
        self.stats["errors"].append(
            {
                "debtor_id": debtor_id,
                "error_message": error_message,
                "stage": stage,
            }
        )

    def process_batch(
        self, priority_queue: list[tuple[float, int]], batch_size: int | None = None
    ) -> list[dict[str, object]]:
        """
        Process highest-priority debtors from the heap in configurable batches.

        Notes:
            - Pops up to batch_size debtors (highest first) via heappop; mutates
              the heap in place.
            - Fetches each debtor with select_related("risk_score"); delegates
              to _process_single_debtor.
            - Per-debtor failures yield error results and are recorded; batch
              continues.
            - Limits processed count per call to control memory usage.

        Args:
            priority_queue: list[tuple[float, int]] — Heap of
                (-priority, debtor_id) tuples.
            batch_size: int | None — Override default; None uses self.batch_size.

        Returns:
            list[dict[str, object]] — Per-debtor results (success or error).
        """
        if batch_size is None:
            batch_size = self.batch_size

        batch_results = []

        for _ in range(min(batch_size, len(priority_queue))):
            if not priority_queue:
                break

            neg_priority, debtor_id = heapq.heappop(priority_queue)
            heap_priority_snapshot = -neg_priority

            try:
                debtor = Debtor.objects.select_related("risk_score").get(id=debtor_id)
                result = self._process_single_debtor(debtor)
                batch_results.append(result)
            except Exception as e:
                # Use best-available priority for error reporting: stored score if present, else heap snapshot
                try:
                    stored_score = debtor.risk_score.total_score
                    best_priority = stored_score * float(debtor.total_debt_amount)
                except Exception:
                    best_priority = heap_priority_snapshot

                error_result = self._create_error_result(
                    debtor_id, best_priority, str(e)
                )
                batch_results.append(error_result)
                self._record_error(debtor_id, str(e), "debtor_processing")

        # After finishing the batch, delegate high-priority notifications
        self._notify_high_priority_debtors(batch_results)

        return batch_results

    def _process_single_debtor(self, debtor: Debtor) -> dict[str, object]:
        """
        Process a single debtor.

        Notes:
            - Recalculates risk score for fresh data.
            - Builds structured result with debtor, priority, risk, amount,
              timestamp, status.

        Args:
            debtor: Debtor — Instance to process.

        Returns:
            dict[str, object] — Structured processing result.
        """
        score_result = self.scorer.calculate_risk_score(debtor)
        fresh_priority = score_result["total_score"] * float(debtor.total_debt_amount)
        self._update_processing_stats(fresh_priority)
        return {
            "debtor_id": debtor.id,
            "debtor_name": debtor.name,
            "priority_score": fresh_priority,
            "risk_score": score_result["total_score"],
            "risk_level": score_result["risk_level"],
            "debt_amount": float(debtor.total_debt_amount),
            "payment_status": debtor.payment_status,
            "processed_at": timezone.now().isoformat(),
            "status": "success",
        }

    def _create_error_result(
        self, debtor_id: int, priority: float, error_message: str
    ) -> dict[str, object]:
        """
        Create a structured error result matching success result shape.

        Notes:
            - Matches success result interface for uniform handling.

        Args:
            debtor_id: int — Debtor identifier.
            priority: float — Composite priority score.
            error_message: str — Error details.

        Returns:
            dict[str, object] — Structured error result.
        """
        return {
            "debtor_id": debtor_id,
            "priority_score": priority,
            "status": "error",
            "error_message": error_message,
            "processed_at": timezone.now().isoformat(),
        }

    def _notify_high_priority_debtors(self, batch_results: list[dict]) -> None:
        """
        Send high-priority debtors to configured messenger.

        Args:
            batch_results: list[dict] — Per-debtor results for this processed batch.

        Returns:
            None
        """
        messenger = self.messenger
        if messenger is not None:
            high_priority_results: list[dict] = []
            for result in batch_results:
                if result.get("status") != "success":
                    continue
                priority_score = result.get("priority_score", 0)
                if priority_score > self.high_priority_threshold:
                    high_priority_results.append(result)

            if high_priority_results:
                message_result = messenger.send_high_priority_batch(
                    high_priority_results
                )

                if "messages_sent" not in self.stats:
                    self.stats["messages_sent"] = 0
                    self.stats["total_messaged_debtors"] = 0

                self.stats["messages_sent"] += 1
                self.stats["total_messaged_debtors"] += message_result["count"]

    def process_all_debtors(
        self, queryset: QuerySet | None = None
    ) -> dict[str, object]:
        """
        Orchestrate end-to-end processing workflow.

        Notes:
            - Build priority queue via build_priority_queue(queryset).
            - Process in batches until the queue is empty; aggregate results.
            - Generate final report with statistics and results.
            - Tracks total processing time.
            - Optional progress logging if self.stdout exists.

        Args:
            queryset: QuerySet | None — Optional subset to process.

        Returns:
            dict[str, object] — Processing report with summary and results.
        """
        start_time = time.time()
        priority_queue = self.build_priority_queue(queryset)
        all_results = []
        batch_number = 1

        while priority_queue:
            if hasattr(self, "stdout"):
                self.stdout.write(
                    f"Processing batch {batch_number} of {len(priority_queue)} debtors remaining"
                )

            batch_results = self.process_batch(priority_queue)
            all_results.extend(batch_results)
            batch_number += 1

        processing_time = time.time() - start_time
        self.stats["processing_time"] = processing_time

        return self._generate_processing_report(all_results, batch_number - 1)

    def _generate_processing_report(
        self, all_results: list[dict], batch_count: int
    ) -> dict[str, object]:
        """
        Create final processing report with summary metrics.

        Notes:
            - summary: total_debtors, high_priority_debtors,
              processing_time_seconds, batches_processed, errors_count.
            - detailed_results: preview first 10 results only.
            - errors: full error list from self.stats["errors"].

        Args:
            all_results: list[dict] — Per-debtor processing results.
            batch_count: int — Number of processed batches.

        Returns:
            dict[str, object] — Report containing summary, preview results, errors.
        """
        return {
            "summary": {
                "total_debtors_successfully_processed": self.stats["total_processed"],
                "high_priority_debtors_successfully_processed": self.stats[
                    "high_priority_count"
                ],
                "processing_time_seconds": self.stats["processing_time"],
                "batches_processed": batch_count,
                "errors_count": len(self.stats["errors"]),
                "messages_sent": self.stats.get("messages_sent", 0),
                "total_messaged_debtors": self.stats.get("total_messaged_debtors", 0),
            },
            "detailed_results": all_results[:10],
            "errors": self.stats["errors"],
        }

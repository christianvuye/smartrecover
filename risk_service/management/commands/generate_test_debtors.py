"""
Management command to generate large-scale test debtors.

Notes:
    - Supports configurable count, distribution pattern, and RNG seeding.
    - Generates in batches for memory efficiency; optional scoring pass.
    - Prints dataset statistics upon completion.
"""

import random
from decimal import Decimal

from django.core.management.base import BaseCommand

from risk_service.choices import (
    CONTRACT_FREELANCE,
    CONTRACT_PERMANENT,
    CONTRACT_TEMPORARY,
    EMPLOYMENT_EMPLOYED,
    EMPLOYMENT_GOVERNMENT,
    EMPLOYMENT_SELF_EMPLOYED,
    EMPLOYMENT_UNEMPLOYED,
    FAMILY_MARRIED_DUAL_INCOME,
    FAMILY_MARRIED_SINGLE_INCOME,
    FAMILY_SINGLE_NO_DEPENDENTS,
    FAMILY_SINGLE_WITH_DEPENDENTS,
    INDUSTRY_CONSTRUCTION,
    INDUSTRY_EDUCATION,
    INDUSTRY_FINANCE,
    INDUSTRY_HEALTHCARE,
    INDUSTRY_HOSPITALITY,
    INDUSTRY_TECHNOLOGY,
)
from risk_service.models import Debtor, RiskScore
from risk_service.risk_scorer import RiskScorer


class Command(BaseCommand):
    help = "Generate large-scale test data for debt recovery processing"

    def add_arguments(self, parser):
        """Define CLI arguments for the generator.

        Args:
            parser: ArgumentParser — Django management command parser.

        Returns:
            None
        """
        parser.add_argument(
            "--count",
            type=int,
            default=5000,
            help="Number of debtors to generate (default: 5000)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing debtors before generating new ones",
        )
        parser.add_argument(
            "--distribution",
            choices=["balanced", "high-risk", "low-risk"],
            default="balanced",
            help="Risk distribution pattern (default: balanced)",
        )
        parser.add_argument(
            "--seed",
            type=int,
            help="Seed for random number generator to make output reproducible",
        )
        parser.add_argument(
            "--no-scores",
            action="store_true",
            help="Skip scoring pass after creating debtors (faster generation)",
        )
        parser.add_argument(
            "--create-batch-size",
            type=int,
            default=500,
            help="Batch size for bulk_create during generation (default: 500)",
        )
        parser.add_argument(
            "--progress-every",
            type=int,
            default=1000,
            help="Log scoring progress every N debtors (default: 1000)",
        )

    def handle(self, *args, **options):
        """Entry point for dataset generation.

        Notes:
            - Optionally clears existing data.
            - Generates debtors in batches; optionally seeds RNG.
            - Optionally runs scoring pass and prints dataset stats.

        Args:
            *args: tuple — Unused positional args.
            **options: dict — Parsed CLI options.

        Returns:
            None
        """
        count = options["count"]

        if options.get("seed") is not None:
            random.seed(options["seed"])

        if options["clear"]:
            self.stdout.write("Clearing existing debtors...")
            Debtor.objects.all().delete()

        self.stdout.write(
            f"Generating {count:,} test debtors with {options['distribution']} distribution..."
        )

        batch_size = options["create_batch_size"]
        total_generated = 0
        scorer = RiskScorer()

        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            batch_debtors = []

            for i in range(batch_start, batch_end):
                debtor_data = self._generate_debtor_profile(
                    i + 1, options["distribution"]
                )
                batch_debtors.append(Debtor(**debtor_data))

            Debtor.objects.bulk_create(batch_debtors)
            total_generated += len(batch_debtors)

            progress_pct = (total_generated / count) * 100
            self.stdout.write(
                f"Generated {total_generated:,}/{count:,} debtors ({progress_pct:.1f}%)"
            )

        if not options["no_scores"]:
            self.stdout.write("Computing risk scores...")
            self._compute_risk_scores(scorer, progress_every=options["progress_every"])

        self._display_generation_stats(count)

    def _generate_debtor_profile(self, index: int, distribution: str) -> dict:
        """
        Generate a debtor profile with controlled risk distribution.

        Notes:
            - Uses risk_bias to influence debt, income, late payments, and
              categorical choices.
            - Uses cent-precision to avoid float↔Decimal artifacts.

        Args:
            index: int — Sequence number (for reproducibility/hooks).
            distribution: str — One of {"balanced", "high-risk", "low-risk"}.

        Returns:
            dict: Fields suitable for Debtor(**data).
        """

        first_names = [
            "James",
            "Mary",
            "John",
            "Patricia",
            "Robert",
            "Jennifer",
            "Michael",
            "Linda",
            "William",
            "Elizabeth",
            "David",
            "Barbara",
            "Richard",
            "Susan",
            "Joseph",
            "Jessica",
            "Thomas",
            "Sarah",
            "Christopher",
            "Karen",
            "Charles",
            "Nancy",
            "Daniel",
            "Lisa",
            "Matthew",
            "Betty",
            "Anthony",
            "Helen",
            "Mark",
            "Sandra",
            "Donald",
            "Donna",
            "Steven",
            "Carol",
            "Paul",
            "Ruth",
            "Andrew",
            "Sharon",
            "Joshua",
            "Michelle",
            "Kenneth",
            "Laura",
            "Kevin",
            "Emily",
            "Brian",
            "Kimberly",
            "George",
            "Deborah",
        ]

        last_names = [
            "Smith",
            "Johnson",
            "Williams",
            "Brown",
            "Jones",
            "Garcia",
            "Miller",
            "Davis",
            "Rodriguez",
            "Martinez",
            "Hernandez",
            "Lopez",
            "Gonzalez",
            "Wilson",
            "Anderson",
            "Thomas",
            "Taylor",
            "Moore",
            "Jackson",
            "Martin",
            "Lee",
            "Perez",
            "Thompson",
            "White",
            "Harris",
            "Sanchez",
            "Clark",
            "Ramirez",
            "Lewis",
            "Robinson",
            "Walker",
            "Young",
            "Allen",
            "King",
            "Wright",
            "Scott",
            "Torres",
            "Nguyen",
            "Hill",
            "Flores",
        ]

        name = f"{random.choice(first_names)} {random.choice(last_names)}"

        if distribution == "high-risk":
            risk_bias = random.uniform(0.7, 1.0)
        elif distribution == "low-risk":
            risk_bias = random.uniform(0.0, 0.3)
        else:  # balanced
            risk_bias = random.uniform(0.0, 1.0)

        if risk_bias > 0.8:
            debt_cents = random.randrange(1_500_000, 7_500_000 + 1)
        elif risk_bias < 0.2:
            debt_cents = random.randrange(50_000, 2_500_000 + 1)
        else:
            debt_cents = random.randrange(200_000, 5_000_000 + 1)
        debt_amount = Decimal(debt_cents) / Decimal(100)

        if risk_bias > 0.7:
            income_cents = random.randrange(200_000, 500_000 + 1)
        elif risk_bias < 0.3:
            income_cents = random.randrange(600_000, 1_200_000 + 1)
        else:
            income_cents = random.randrange(350_000, 800_000 + 1)
        monthly_income = Decimal(income_cents) / Decimal(100)

        if risk_bias > 0.8:
            late_payments = random.randint(5, 12)
        elif risk_bias > 0.6:
            late_payments = random.randint(2, 6)
        elif risk_bias > 0.3:
            late_payments = random.randint(0, 3)
        else:
            late_payments = 0

        employment_choices = [
            (EMPLOYMENT_EMPLOYED, 0.1),
            (EMPLOYMENT_GOVERNMENT, 0.05),
            (EMPLOYMENT_SELF_EMPLOYED, 0.4),
            (EMPLOYMENT_UNEMPLOYED, 0.9),
        ]
        employment_status = self._weighted_choice(employment_choices, risk_bias)

        if employment_status == EMPLOYMENT_UNEMPLOYED:
            contract_type = CONTRACT_FREELANCE
        else:
            contract_choices = [
                (CONTRACT_PERMANENT, 0.1),
                (CONTRACT_TEMPORARY, 0.5),
                (CONTRACT_FREELANCE, 0.8),
            ]
            contract_type = self._weighted_choice(contract_choices, risk_bias)

        industry_choices = [
            (INDUSTRY_HEALTHCARE, 0.2),
            (INDUSTRY_EDUCATION, 0.25),
            (INDUSTRY_FINANCE, 0.15),
            (INDUSTRY_TECHNOLOGY, 0.1),
            (INDUSTRY_CONSTRUCTION, 0.6),
            (INDUSTRY_HOSPITALITY, 0.8),
        ]
        industry_sector = self._weighted_choice(industry_choices, risk_bias)

        family_choices = [
            (FAMILY_MARRIED_DUAL_INCOME, 0.1),
            (FAMILY_MARRIED_SINGLE_INCOME, 0.4),
            (FAMILY_SINGLE_NO_DEPENDENTS, 0.5),
            (FAMILY_SINGLE_WITH_DEPENDENTS, 0.9),
        ]
        family_situation = self._weighted_choice(family_choices, risk_bias)

        return {
            "name": name,
            "total_debt_amount": debt_amount,
            "monthly_income": monthly_income,
            "late_payments_count": late_payments,
            "employment_status": employment_status,
            "contract_type": contract_type,
            "industry_sector": industry_sector,
            "family_situation": family_situation,
        }

    def _weighted_choice(self, choices, risk_bias):
        """
        Choose from options based on risk bias and choice weights.

        Notes:
            - Filters choices where risk_bias ≥ weight; falls back to lowest
              weight option when none qualify.

        Args:
            choices: list[tuple[str, float]] — (value, weight) pairs.
            risk_bias: float — Bias in [0, 1] guiding selection.

        Returns:
            Any: Selected value from choices.
        """
        available_choices = [
            choice for choice, weight in choices if risk_bias >= weight
        ]
        if not available_choices:
            available_choices = [min(choices, key=lambda x: x[1])[0]]
        return random.choice(available_choices)

    def _compute_risk_scores(self, scorer: RiskScorer, progress_every: int = 1000):
        """
        Compute and store risk scores for all debtors.

        Notes:
            - Iterates via queryset.iterator() for memory efficiency.
            - Logs progress every N debtors; continues on errors.
            - RiskScore rows are created/updated by calculate_risk_score.

        Args:
            scorer: RiskScorer — Scoring engine instance.
            progress_every: int — Progress log interval.

        Returns:
            None
        """
        debtors = Debtor.objects.all()
        total_debtors = debtors.count()
        processed = 0

        for debtor in debtors.iterator():
            try:
                scorer.calculate_risk_score(debtor)
                processed += 1

                if progress_every > 0 and processed % progress_every == 0:
                    progress_pct = (processed / total_debtors) * 100
                    self.stdout.write(
                        f"Scored {processed:,}/{total_debtors:,} debtors ({progress_pct:.1f}%)"
                    )

            except Exception as e:
                self.stdout.write(f"Error scoring debtor {debtor.id}: {e}")

    def _display_generation_stats(self, expected_count: int):
        """
        Display statistics about the generated dataset.

        Notes:
            - Summarizes counts and risk distribution.
            - Shows debt ranges and a top priority preview.

        Args:
            expected_count: int — Intended number of generated debtors.

        Returns:
            None
        """
        actual_count = Debtor.objects.count()
        scored_count = RiskScore.objects.count()

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("           DATASET GENERATION COMPLETE")
        self.stdout.write("=" * 60)

        self.stdout.write(f"Total debtors created: {actual_count:,}")
        self.stdout.write(f"Risk scores computed: {scored_count:,}")

        if scored_count > 0:
            risk_levels = RiskScore.objects.values("risk_level").distinct()
            for level_dict in risk_levels:
                level = level_dict["risk_level"]
                count = RiskScore.objects.filter(risk_level=level).count()
                pct = (count / scored_count) * 100
                self.stdout.write(
                    f"  {level.title()} risk: {count:,} debtors ({pct:.1f}%)"
                )

            from django.db.models import Avg, Max, Min

            debt_stats = Debtor.objects.aggregate(
                min_debt=Min("total_debt_amount"),
                max_debt=Max("total_debt_amount"),
                avg_debt=Avg("total_debt_amount"),
            )

            self.stdout.write("\nDebt amount range:")
            self.stdout.write(f"  Minimum: ${debt_stats['min_debt']:,.2f}")
            self.stdout.write(f"  Maximum: ${debt_stats['max_debt']:,.2f}")
            self.stdout.write(f"  Average: ${debt_stats['avg_debt']:,.2f}")

            self.stdout.write("\nTop 5 priority scores (risk_score × debt_amount):")
            top_priorities = []
            for debtor in Debtor.objects.select_related("risk_score")[:20]:
                try:
                    priority = debtor.risk_score.total_score * float(
                        debtor.total_debt_amount
                    )
                    top_priorities.append(
                        (
                            debtor.name,
                            priority,
                            debtor.risk_score.total_score,
                            debtor.total_debt_amount,
                        )
                    )
                except Exception as e:
                    self.stdout.write(f"Skipping debtor {debtor.id} in preview: {e}")

            top_priorities.sort(key=lambda x: x[1], reverse=True)
            for i, (name, priority, risk_score, debt) in enumerate(
                top_priorities[:5], 1
            ):
                self.stdout.write(
                    f"  {i}. {name}: {priority:,.0f} (risk: {risk_score}, debt: ${debt:,.0f})"
                )

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Ready for bulk processing tests!")
        self.stdout.write("Try: python manage.py process_debtors --dry-run --top-k 10")
        self.stdout.write("=" * 60)

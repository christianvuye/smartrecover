"""
API views for risk_service.

Notes:
    - Debtor CRUD endpoints and risk scoring endpoints.
"""

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Debtor, RiskScore
from .risk_scorer import RiskScorer
from .serializers import DebtorSerializer, RiskScoreSerializer


class DebtorListCreateView(generics.ListCreateAPIView):
    """
    List and create debtors.

    Notes:
        - GET: Return all debtors.
        - POST: Create a debtor from request data.
    """

    queryset = Debtor.objects.all()
    serializer_class = DebtorSerializer


class DebtorDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update a debtor.

    Notes:
        - GET: Return a debtor by id.
        - PUT/PATCH: Update debtor and recalculate risk score.
    """

    queryset = Debtor.objects.all()
    serializer_class = DebtorSerializer

    def perform_update(self, serializer):
        """
        Save and recalculate risk score.

        Args:
            serializer: Serializer — Debtor serializer to save.

        Returns:
            None
        """
        debtor = serializer.save()

        scorer = RiskScorer()
        scorer.calculate_risk_score(debtor)


@api_view(["GET"])
def debtor_risk_score(request, pk):
    """
    Get or calculate risk score for a debtor.

    Notes:
        - Calculates fresh score (creates or updates stored score).

    Args:
        request: HttpRequest — Incoming request.
        pk: int — Debtor primary key.

    Returns:
        Response — Risk score payload.
    """
    debtor = get_object_or_404(Debtor, pk=pk)

    scorer = RiskScorer()
    score_data = scorer.calculate_risk_score(debtor)

    return Response(score_data)


@api_view(["GET"])
def high_risk_debtors(request):
    """
    List debtors with HIGH or CRITICAL risk.

    Args:
        request: HttpRequest — Incoming request.

    Returns:
        Response — Serialized high-risk debtor scores.
    """
    high_risk_scores = RiskScore.objects.filter(
        risk_level__in=["HIGH", "CRITICAL"]
    ).select_related("debtor")

    serializer = RiskScoreSerializer(high_risk_scores, many=True)
    return Response(serializer.data)

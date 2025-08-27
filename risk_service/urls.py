"""
URL configuration for risk_service.

Notes:
    - Namespace: risk_service
    - Endpoints:
        - GET/POST    /debtors/                 → DebtorListCreateView
        - GET/PUT/PATCH /debtors/<int:pk>/      → DebtorDetailView
        - GET         /debtors/<int:pk>/score/  → debtor_risk_score
        - GET         /debtors/high-risk/       → high_risk_debtors
"""

from django.urls import path

from . import views

app_name = "risk_service"

urlpatterns = [
    path("debtors/", views.DebtorListCreateView.as_view(), name="debtor-list-create"),
    path("debtors/<int:pk>/", views.DebtorDetailView.as_view(), name="debtor-detail"),
    path("debtors/<int:pk>/score/", views.debtor_risk_score, name="debtor-score"),
    path("debtors/high-risk/", views.high_risk_debtors, name="high-risk-debtors"),
]

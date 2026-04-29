from django.urls import path
from .views import LowStockAlertView

urlpatterns = [
    path(
        "api/companies/<int:company_id>/alerts/low-stock",
        LowStockAlertView.as_view(),
        name="low-stock-alerts",
    ),
]
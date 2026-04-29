from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Company, Warehouse
from .serializers import LowStockResponseSerializer
from .services import get_low_stock_alerts
from .exceptions import CompanyNotFoundException, NoWarehousesException


class LowStockAlertView(APIView):

    def get(self, request, company_id: int):

        # company must exist
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            raise CompanyNotFoundException()

        # company must have at least one warehouse
        if not Warehouse.objects.filter(company=company).exists():
            raise NoWarehousesException()

        # Delegate all business logic to the service layer
        alerts = get_low_stock_alerts(company_id)

        response_data = {
            "alerts":       alerts,
            "total_alerts": len(alerts),
        }

        # Validate output shape before sending
        serializer = LowStockResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
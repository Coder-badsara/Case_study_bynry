from django.db.models import Avg, Q, Subquery, OuterRef, FloatField
from django.utils import timezone
from datetime import timedelta

from .models import Inventory, InventoryLog, SupplierProduct

RECENT_SALES_DAYS = 30


def get_low_stock_alerts(company_id: int) -> list[dict]:
    cutoff = timezone.now() - timedelta(days=RECENT_SALES_DAYS)

    # find inventory IDs with recent sale activity
    active_inventory_ids = (
        InventoryLog.objects
        .filter(
            change_type="sale",
            created_at__gte=cutoff,
        )
        .values_list("inventory_id", flat=True)
        .distinct()
    )

    # fetch low-stock rows for this company
    low_stock_qs = (
        Inventory.objects
        .select_related(
            "product",
            "warehouse",
            "warehouse__company",
        )
        .filter(
            warehouse__company_id=company_id,
            id__in=active_inventory_ids,
        )
        .filter(
            min_threshold__isnull=False,
            quantity__lte=models_ref("min_threshold"),
        )
        .order_by("quantity")        
    )

    results = []
    for inv in low_stock_qs:
        results.append({
            "product_id":          inv.product.id,
            "product_name":        inv.product.name,
            "sku":                 inv.product.sku,
            "warehouse_id":        inv.warehouse.id,
            "warehouse_name":      inv.warehouse.name,
            "current_stock":       inv.quantity,
            "threshold":           inv.min_threshold,
            "days_until_stockout": _calc_days_until_stockout(inv, cutoff),
            "supplier":            _get_preferred_supplier(inv.product.id),
        })

    return results


def _calc_days_until_stockout(inv: "Inventory", cutoff) -> int | None:
    logs = (
        InventoryLog.objects
        .filter(
            inventory=inv,
            change_type="sale",
            created_at__gte=cutoff,
        )
    )

    total_sold = sum(abs(log.delta) for log in logs)

    if total_sold == 0:
        return None

    avg_daily = total_sold / RECENT_SALES_DAYS

    if avg_daily <= 0:
        return None

def _get_preferred_supplier(product_id: int) -> dict | None:

    supplier_product = (
        SupplierProduct.objects
        .select_related("supplier")
        .filter(product_id=product_id)
        .order_by("-is_preferred", "id")
        .first()
    )

    if not supplier_product:
        return None

    return {
        "id":            supplier_product.supplier.id,
        "name":          supplier_product.supplier.name,
        "contact_email": supplier_product.supplier.email,
    }


from django.db.models import F

def models_ref(field: str):
    """Shorthand: filter quantity <= min_threshold using F() expression."""
    return F(field)
from django.db.models import Avg, Q, Subquery, OuterRef, FloatField
from django.utils import timezone
from datetime import timedelta

from .models import Inventory, InventoryLog, SupplierProduct


# ── Assumption: "recent sales activity" = at least 1 sale in the last 30 days.
# ── Assumption: days_until_stockout = current_stock / avg_daily_sales (last 30d).
#    Returns None if there are no recent sales (can't project without velocity).
# ── Assumption: preferred supplier is returned; if none is preferred, the first
#    supplier by id is returned. None if no supplier is linked.

RECENT_SALES_DAYS = 30


def get_low_stock_alerts(company_id: int) -> list[dict]:
    """
    Returns all low-stock inventory rows for a given company where:
      1. quantity <= min_threshold  (threshold is set on the inventory row)
      2. the product had at least one 'sale' log in the last RECENT_SALES_DAYS days
    """
    cutoff = timezone.now() - timedelta(days=RECENT_SALES_DAYS)

    # ── Step 1: find inventory IDs with recent sale activity ──────────────────
    active_inventory_ids = (
        InventoryLog.objects
        .filter(
            change_type="sale",
            created_at__gte=cutoff,
        )
        .values_list("inventory_id", flat=True)
        .distinct()
    )

    # ── Step 2: fetch low-stock rows for this company ─────────────────────────
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
            # Only rows where threshold is configured AND stock is at/below it
            min_threshold__isnull=False,
            quantity__lte=models_ref("min_threshold"),
        )
        .order_by("quantity")          # most critical first
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
    """
    Estimate days until stockout based on average daily sales in the last 30 days.
    Returns None when there is insufficient sales data to project.
    """
    logs = (
        InventoryLog.objects
        .filter(
            inventory=inv,
            change_type="sale",
            created_at__gte=cutoff,
        )
    )

    # Sum all units sold in the window
    total_sold = sum(abs(log.delta) for log in logs)

    if total_sold == 0:
        # No sales data — cannot compute velocity
        return None

    avg_daily = total_sold / RECENT_SALES_DAYS

    if avg_daily <= 0:
        return None

    # Round up so we never underestimate urgency
    import math
    return math.ceil(inv.quantity / avg_daily)


def _get_preferred_supplier(product_id: int) -> dict | None:
    """
    Returns the preferred supplier for a product.
    Falls back to the first linked supplier if none is marked preferred.
    Returns None if no supplier is linked at all.
    """
    supplier_product = (
        SupplierProduct.objects
        .select_related("supplier")
        .filter(product_id=product_id)
        .order_by("-is_preferred", "id")   # preferred first, then oldest link
        .first()
    )

    if not supplier_product:
        return None

    return {
        "id":            supplier_product.supplier.id,
        "name":          supplier_product.supplier.name,
        "contact_email": supplier_product.supplier.email,
    }


# ── Helper used inline to reference a model field in a filter ─────────────────
from django.db.models import F

def models_ref(field: str):
    """Shorthand: filter quantity <= min_threshold using F() expression."""
    return F(field)
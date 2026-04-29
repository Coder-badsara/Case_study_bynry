from django.db import models


class Company(models.Model):
    name       = models.CharField(max_length=255)
    email      = models.EmailField(unique=True, null=True, blank=True)
    phone      = models.CharField(max_length=30, null=True, blank=True)
    address    = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "companies"

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    company    = models.ForeignKey(Company, on_delete=models.CASCADE,
                                   related_name="warehouses")
    name       = models.CharField(max_length=255)
    address    = models.TextField(null=True, blank=True)
    capacity   = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "warehouses"

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Product(models.Model):
    sku         = models.CharField(max_length=100, unique=True, db_index=True)
    name        = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_bundle   = models.BooleanField(default=False)
    is_active   = models.BooleanField(default=True, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "products"

    def __str__(self):
        return f"{self.sku} - {self.name}"


class Supplier(models.Model):
    name       = models.CharField(max_length=255)
    email      = models.EmailField(null=True, blank=True)
    phone      = models.CharField(max_length=30, null=True, blank=True)
    address    = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "suppliers"

    def __str__(self):
        return self.name


class SupplierProduct(models.Model):
    supplier       = models.ForeignKey(Supplier, on_delete=models.CASCADE,
                                       related_name="supplier_products")
    product        = models.ForeignKey(Product, on_delete=models.CASCADE,
                                       related_name="supplier_products")
    cost_price     = models.DecimalField(max_digits=12, decimal_places=2)
    lead_time_days = models.PositiveSmallIntegerField(null=True, blank=True)
    is_preferred   = models.BooleanField(default=False)

    class Meta:
        db_table = "supplier_products"
        unique_together = ("supplier", "product")

    def __str__(self):
        return f"{self.supplier.name} → {self.product.sku}"


class Inventory(models.Model):
    product       = models.ForeignKey(Product, on_delete=models.CASCADE,
                                      related_name="inventory_records")
    warehouse     = models.ForeignKey(Warehouse, on_delete=models.CASCADE,
                                      related_name="inventory_records")
    quantity      = models.IntegerField(default=0)
    min_threshold = models.PositiveIntegerField(null=True, blank=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table       = "inventory"
        unique_together = ("product", "warehouse")

    def __str__(self):
        return f"{self.product.sku} @ {self.warehouse.name}: {self.quantity}"


class InventoryLog(models.Model):
    CHANGE_TYPES = [
        ("receipt",       "Receipt"),
        ("sale",          "Sale"),
        ("adjustment",    "Adjustment"),
        ("transfer_in",   "Transfer In"),
        ("transfer_out",  "Transfer Out"),
        ("return",        "Return"),
    ]

    inventory       = models.ForeignKey(Inventory, on_delete=models.CASCADE,
                                        related_name="logs")
    changed_by      = models.ForeignKey("auth.User", null=True, blank=True,
                                        on_delete=models.SET_NULL)
    change_type     = models.CharField(max_length=20, choices=CHANGE_TYPES)
    quantity_before = models.IntegerField()
    quantity_after  = models.IntegerField()
    reason          = models.CharField(max_length=500, null=True, blank=True)
    reference_id    = models.CharField(max_length=100, null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "inventory_logs"

    @property
    def delta(self):
        return self.quantity_after - self.quantity_before
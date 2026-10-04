from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Product(TimeStampedModel):
    class Unit(models.TextChoices):
        PCS = "pcs", "Pieces"
        BOX = "box", "Box"
        KG = "kg", "Kilogram"
        L = "l", "Litre"

    sku = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    unit = models.CharField(max_length=10, choices=Unit.choices, default=Unit.PCS)
    description = models.TextField(blank=True)
    reorder_level = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    is_active = models.BooleanField(default=True)
    suppliers = models.ManyToManyField(
        "purchasing.Supplier",
        through="catalog.ProductSupplier",
        related_name="products",
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
        ]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"


class ProductSupplier(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="supplier_links")
    supplier = models.ForeignKey(
        "purchasing.Supplier",
        on_delete=models.CASCADE,
        related_name="product_links",
    )
    supplier_sku = models.CharField(max_length=80, blank=True)
    last_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ("product", "supplier")
        verbose_name = "product supplier"

    def __str__(self) -> str:
        return f"{self.product.sku} / {self.supplier}"

from django.db import models


class DataSource(models.Model):
    name = models.CharField(
        max_length=100
    )

    source_type = models.CharField(
        max_length=50,
        default="api",
    )

    base_url = models.URLField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.name


class PipelineRun(models.Model):

    STATUS_CHOICES = [
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
    ]

    started_at = models.DateTimeField(
        auto_now_add=True
    )

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="running",
    )

    records_created = models.PositiveIntegerField(
        default=0
    )

    records_updated = models.PositiveIntegerField(
        default=0
    )

    records_skipped = models.PositiveIntegerField(
        default=0
    )

    error_message = models.TextField(
        blank=True
    )

    def __str__(self):
        return (
            f"Pipeline Run {self.id} - "
            f"{self.status}"
        )


class RawDataRecord(models.Model):

    source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name="records",
    )

    external_id = models.CharField(
        max_length=255,
        blank=True,
    )

    payload = models.JSONField()

    fetched_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "source",
                    "fetched_at",
                ]
            ),
            models.Index(
                fields=[
                    "external_id",
                ]
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "source",
                    "external_id",
                ],
                name="unique_source_external_id",
            )
        ]

    def __str__(self):
        return (
            f"{self.source.name} - "
            f"{self.external_id}"
        )


class CleanProduct(models.Model):

    product_id = models.CharField(
        max_length=255
    )

    name = models.CharField(
        max_length=255
    )

    category = models.CharField(
        max_length=100
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    rating = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
    )

    stock = models.IntegerField(
        default=0
    )

    brand = models.CharField(
        max_length=150,
        blank=True,
    )

    sku = models.CharField(
        max_length=150,
        blank=True,
    )

    source = models.CharField(
        max_length=100
    )

    raw_record = models.ForeignKey(
        RawDataRecord,
        on_delete=models.CASCADE,
        related_name="clean_product",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "source",
                    "product_id",
                ],
                name="unique_source_product",
            )
        ]

    def __str__(self):
        return self.name


class DataQualityIssue(models.Model):

    raw_record = models.ForeignKey(
        RawDataRecord,
        on_delete=models.CASCADE,
        related_name="quality_issues",
    )

    field_name = models.CharField(
        max_length=100
    )

    issue_type = models.CharField(
        max_length=100
    )

    message = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.field_name} - "
            f"{self.issue_type}"
        )


class ProductSnapshot(models.Model):

    product = models.ForeignKey(
        CleanProduct,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )

    pipeline_run = models.ForeignKey(
        PipelineRun,
        on_delete=models.CASCADE,
        related_name="snapshots",
        null=True,
        blank=True,
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    rating = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
    )

    stock = models.IntegerField(
        default=0
    )

    captured_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "-captured_at"
        ]

        indexes = [
            models.Index(
                fields=[
                    "product",
                    "captured_at",
                ]
            ),
            models.Index(
                fields=[
                    "captured_at",
                ]
            ),
            models.Index(
                fields=[
                    "pipeline_run",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.product.name} - "
            f"{self.captured_at}"
        )

class ProductPrediction(models.Model):
    product = models.ForeignKey(
        CleanProduct,
        on_delete=models.CASCADE,
        related_name="predictions",
    )

    predicted_stock = models.FloatField()

    predicted_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    model_name = models.CharField(
        max_length=100,
    )

    model_version = models.CharField(
        max_length=50,
        default="1.0",
    )

    actual_stock = models.FloatField(
        null=True,
        blank=True,
    )

    prediction_error = models.FloatField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        default="pending",
    )

    class Meta:
        ordering = ["-predicted_at"]
        indexes = [
            models.Index(fields=["product", "-predicted_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return (
            f"{self.product.name} - "
            f"{self.predicted_stock} "
            f"({self.status})"
        )
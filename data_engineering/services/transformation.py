from decimal import Decimal, InvalidOperation

from data_engineering.services.models import RawDataRecord, CleanProduct
from data_engineering.services.data_quality import DataQualityService


def transform_products(only_valid=False):

    records = RawDataRecord.objects.all()

    created = 0
    updated = 0
    skipped = 0

    quality_service = DataQualityService()

    for record in records:

        # Remove old quality issues before fresh validation
        record.quality_issues.all().delete()

        # -------------------------
        # DATA QUALITY CHECK
        # -------------------------
        if only_valid:
            result = quality_service.validate_record(record)

            if not result["is_valid"]:
                skipped += 1
                continue

        data = record.payload

        product_id = str(data.get("id", "")).strip()

        name = str(
            data.get("name")
            or data.get("title")
            or ""
        ).strip()

        category = str(
            data.get("category", "")
        ).strip()

        raw_price = data.get("price")

        # -------------------------
        # BASIC VALIDATION
        # -------------------------
        if not product_id or not name or not category:
            skipped += 1
            continue

        try:
            price = Decimal(str(raw_price))

            if price < 0:
                raise ValueError

        except (InvalidOperation, ValueError, TypeError):
            skipped += 1
            continue

        # -------------------------
        # CLEANING
        # -------------------------
        name = " ".join(name.split())
        category = " ".join(category.split())

        # -------------------------
        # SAVE CLEAN PRODUCT
        # -------------------------
        source_name = record.source.name

        product, was_created = CleanProduct.objects.update_or_create(
            source=source_name,
            product_id=product_id,
            defaults={
                    "name": name,
                    "category": category,
                    "price": price,
                    "discount_percentage": Decimal(str(data.get("discountPercentage") or 0)),
                    "rating": Decimal(str(data.get("rating") or 0)),
                    "stock": int(data.get("stock") or 0),
                    "brand": str(data.get("brand") or "").strip(),
                    "sku": str(data.get("sku") or "").strip(),
                    "source": source_name,
                    "raw_record": record,
                },
        )

        if was_created:
            created += 1
        else:
            updated += 1

    return {
        "total_raw": records.count(),
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }
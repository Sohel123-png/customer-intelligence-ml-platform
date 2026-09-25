from django.core.management.base import BaseCommand

from data_engineering.services.models import RawDataRecord
from data_engineering.services.data_quality import DataQualityService
from data_engineering.services.transformation import transform_products


class Command(BaseCommand):
    help = "Validate, clean and transform raw product data"

    def handle(self, *args, **options):

        records = RawDataRecord.objects.all()

        quality_service = DataQualityService()

        valid_count = 0
        skipped_count = 0

        # -------------------------
        # DATA QUALITY
        # -------------------------

        for record in records:

            # Remove old quality issues for this record
            record.quality_issues.all().delete()

            result = quality_service.validate_record(record)

            if result["is_valid"]:
                valid_count += 1
            else:
                skipped_count += 1

                self.stdout.write(
                    self.style.WARNING(
                        f"Rejected record {record.id}: "
                        f"{len(result['issues'])} quality issue(s)"
                    )
                )

        # -------------------------
        # TRANSFORMATION
        # -------------------------

        result = transform_products(
            only_valid=True
        )

        created = result["created"]
        updated = result["updated"]

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Data transformation completed!"
            )
        )

        self.stdout.write(
            f"Total raw records : {records.count()}"
        )

        self.stdout.write(
            f"Valid records     : {valid_count}"
        )

        self.stdout.write(
            f"Created            : {created}"
        )

        self.stdout.write(
            f"Updated            : {updated}"
        )

        self.stdout.write(
            f"Skipped            : {skipped_count}"
        )

        return {
            "total_raw": records.count(),
            "valid": valid_count,
            "created": created,
            "updated": updated,
            "skipped": skipped_count,
        }
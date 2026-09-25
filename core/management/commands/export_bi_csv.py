import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import Customer

EXPORT_DIR = settings.BASE_DIR / "bi_exports"


class Command(BaseCommand):
    help = "Export flat CSVs for Power BI / Tableau import (run after score_customers)"

    def handle(self, *args, **options):
        EXPORT_DIR.mkdir(exist_ok=True)
        path = EXPORT_DIR / "customer_intelligence.csv"

        fields = [
            "customer_id", "name", "age", "country", "region", "plan",
            "acquisition_channel", "signup_date", "is_active", "churned",
            "monthly_spend", "tenure_months", "total_orders",
            "churn_probability", "risk_level", "segment_name",
        ]

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for c in Customer.objects.select_related(
                "subscription", "churn_prediction", "segment"
            ).prefetch_related("orders"):
                writer.writerow({
                    "customer_id": c.id,
                    "name": c.name,
                    "age": c.age,
                    "country": c.country,
                    "region": c.region,
                    "plan": c.plan,
                    "acquisition_channel": c.acquisition_channel,
                    "signup_date": c.signup_date,
                    "is_active": c.is_active,
                    "churned": c.churned,
                    "monthly_spend": getattr(getattr(c, "subscription", None), "monthly_spend", ""),
                    "tenure_months": getattr(getattr(c, "subscription", None), "tenure_months", ""),
                    "total_orders": c.orders.count(),
                    "churn_probability": getattr(getattr(c, "churn_prediction", None), "churn_probability", ""),
                    "risk_level": getattr(getattr(c, "churn_prediction", None), "risk_level", ""),
                    "segment_name": getattr(getattr(c, "segment", None), "segment_name", ""),
                })

        self.stdout.write(self.style.SUCCESS(f"Exported {path}"))
        self.stdout.write("Import this CSV directly into Power BI (Get Data > Text/CSV) or Tableau (Connect > Text file).")

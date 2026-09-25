from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core import ml
from core.models import Customer, ChurnPrediction, CustomerSegment

CHUNK = 500


class Command(BaseCommand):
    help = "Score every customer with the trained churn model and assign a segment (run after train_models)"

    def handle(self, *args, **options):
        customers = Customer.objects.select_related("subscription").prefetch_related(
            "support_tickets", "payments", "usage_logs", "orders"
        )
        total = customers.count()
        churn_preds, segments = [], []
        batch, batch_features = [], []

        def flush():
            results = ml.predict_churn_batch(batch_features)
            for customer, features, result in zip(batch, batch_features, results):
                churn_preds.append(ChurnPrediction(
                    customer=customer,
                    churn_probability=result["churn_probability"],
                    risk_level=result["risk_level"],
                    top_factors=result["top_factors"],
                ))
                cluster_id, segment_name = ml.assign_segment(features)
                segments.append(CustomerSegment(
                    customer=customer, segment_name=segment_name, cluster_id=cluster_id
                ))
            batch.clear()
            batch_features.clear()

        try:
            for i, customer in enumerate(customers.iterator(chunk_size=CHUNK), start=1):
                try:
                    features = ml.customer_features(customer)
                except ObjectDoesNotExist:  # customer without a subscription
                    continue
                batch.append(customer)
                batch_features.append(features)
                if len(batch) >= CHUNK:
                    flush()
                    self.stdout.write(f"Scored {i}/{total}...")
            if batch:
                flush()
        except ml.ModelNotReadyError as exc:
            raise CommandError(str(exc))

        with transaction.atomic():
            ChurnPrediction.objects.all().delete()
            CustomerSegment.objects.all().delete()
            ChurnPrediction.objects.bulk_create(churn_preds, batch_size=1000)
            CustomerSegment.objects.bulk_create(segments, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(f"Scored {len(churn_preds)} customers."))

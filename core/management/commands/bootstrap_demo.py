"""
One command that makes a fresh deployment usable. Safe to run on every deploy:
each step is skipped when its result already exists.

    python manage.py bootstrap_demo

Why this exists: trained model files (*.joblib) are git-ignored, so a fresh
checkout on Render/Railway has data tables but NO models, and the churn /
forecast / stock-prediction endpoints cannot answer until something trains them.
"""
import io
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.models import ChurnPrediction, Customer
from core import ml
from data_engineering.services.model_registry import MODEL_PATH
from data_engineering.services.models import ProductPrediction, ProductSnapshot


class Command(BaseCommand):
    help = "Create demo data, train models and score customers if they are missing (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--customers",
            type=int,
            default=int(os.getenv("DEMO_CUSTOMERS", "1500")),
            help="Synthetic customers to generate when the database is empty (env DEMO_CUSTOMERS).",
        )
        parser.add_argument(
            "--pipeline-runs",
            type=int,
            default=int(os.getenv("DEMO_PIPELINE_RUNS", "6")),
            help=(
                "Product-pipeline runs used to build snapshot history for the stock model "
                "(at least 5 are needed before a temporal train/test split is possible)."
            ),
        )

    def handle(self, *args, **options):
        # ---- Customer intelligence (churn / segments / revenue) ----
        if not Customer.objects.exists():
            call_command("generate_data", customers=options["customers"])
        else:
            self.stdout.write("Customers already present - skipping generate_data.")

        models_ready = all(
            (ml.MODEL_DIR / f).exists()
            for f in ("churn_model.joblib", "segment_model.joblib", "revenue_model.joblib")
        )
        if not models_ready:
            call_command("train_models")
        else:
            self.stdout.write("Churn models already present - skipping train_models.")

        if not ChurnPrediction.objects.exists() or not models_ready:
            call_command("score_customers")
        else:
            self.stdout.write("Customers already scored - skipping score_customers.")

        # ---- Product pipeline + stock model (needs internet for DummyJSON) ----
        # A failure here must not fail the whole deploy: the site works without it.
        # Once the model exists and predictions are flowing, every later deploy
        # skips this whole block instantly instead of re-running the pipeline.
        stock_ready = MODEL_PATH.exists() and ProductPrediction.objects.count() >= 60
        if stock_ready:
            self.stdout.write("Stock model and predictions already present - skipping product pipeline warm-up.")
        else:
            try:
                if ProductSnapshot.objects.count() < options["pipeline_runs"] * 30:
                    for i in range(options["pipeline_runs"]):
                        self.stdout.write(f"Product pipeline warm-up run {i + 1}/{options['pipeline_runs']}")
                        call_command("run_pipeline", stdout=io.StringIO())  # keep build logs quiet

                if not MODEL_PATH.exists():
                    call_command("train_ml_model")

                if not MODEL_PATH.exists():
                    self.stdout.write(self.style.WARNING(
                        "Stock model was not trained yet (not enough snapshot history). "
                        "Run `python manage.py run_pipeline` a few more times, then `python manage.py train_ml_model`."
                    ))
                else:
                    # The warm-up runs above all happened BEFORE the model existed, so
                    # run_pipeline had nothing to predict with and created zero
                    # predictions. Now that a model exists, run it a few more times so
                    # the Model Monitoring page has real (and some evaluated) predictions.
                    post_train_runs = int(os.getenv("DEMO_POST_TRAIN_RUNS", "4"))
                    for i in range(post_train_runs):
                        self.stdout.write(f"Post-training pipeline run {i + 1}/{post_train_runs} (populating predictions)")
                        call_command("run_pipeline", stdout=io.StringIO())
            except Exception as exc:  # noqa: BLE001 - deliberately broad, see comment above
                self.stdout.write(self.style.WARNING(
                    f"Product pipeline / stock model skipped: {exc}. "
                    "The rest of the app is ready; run `python manage.py run_pipeline` later."
                ))

        self.stdout.write(self.style.SUCCESS("bootstrap_demo finished."))

import tempfile
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from core import ml
from core.management.commands import train_models
from core.models import ChurnPrediction, Customer, CustomerSegment


def _clear_model_caches():
    for fn in (ml._load_churn_model, ml._load_segment_model, ml._load_revenue_model,
               ml._get_explainer, ml._segment_labels):
        fn.cache_clear()


class HealthAndValidationTests(TestCase):
    def test_healthz(self):
        self.assertEqual(self.client.get("/healthz/").status_code, 200)

    def test_bad_query_params_do_not_500(self):
        self.assertEqual(self.client.get("/api/customers/high-risk/?limit=abc").status_code, 200)
        self.assertEqual(self.client.get("/api/customers/high-risk/?limit=-5").status_code, 200)

    def test_dashboard_and_analytics_render_on_empty_db(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/api/analytics/summary/").status_code, 200)
        self.assertEqual(self.client.get("/api/data/analytics/products/").status_code, 200)


class MissingModelTests(TestCase):
    """A fresh deploy has no *.joblib files: endpoints must say 503, not crash with 500."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(ml, "MODEL_DIR", Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        _clear_model_caches()
        self.addCleanup(_clear_model_caches)

    def test_churn_prediction_returns_503(self):
        r = self.client.post("/api/predict/churn/", {}, content_type="application/json")
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["status"], "model_not_ready")

    def test_forecast_returns_503(self):
        self.assertEqual(self.client.get("/api/revenue/forecast/").status_code, 503)

    def test_stock_prediction_returns_503(self):
        with mock.patch("data_engineering.services.prediction.load_model", side_effect=FileNotFoundError):
            r = self.client.post("/api/data/ml/predict/", {"product_id": 1}, content_type="application/json")
        self.assertEqual(r.status_code, 503)


class EndToEndTests(TestCase):
    """generate_data -> train_models -> score_customers -> API, on a small dataset."""

    def test_full_flow(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(ml, "MODEL_DIR", Path(tmp)), \
                mock.patch.object(train_models, "MODEL_DIR", Path(tmp)):
            _clear_model_caches()
            self.addCleanup(_clear_model_caches)

            call_command("generate_data", customers=120, verbosity=0)
            call_command("train_models", verbosity=0)
            call_command("score_customers", verbosity=0)

            n = Customer.objects.count()
            self.assertEqual(n, 120)
            self.assertEqual(ChurnPrediction.objects.count(), n)
            self.assertEqual(CustomerSegment.objects.count(), n)
            # every segment label must be one of the four meaningful names
            names = set(CustomerSegment.objects.values_list("segment_name", flat=True))
            self.assertTrue(names <= set(ml.DEFAULT_SEGMENT_LABELS.values()), names)

            r = self.client.post("/api/predict/churn/", {"customer_id": Customer.objects.first().id},
                                 content_type="application/json")
            self.assertEqual(r.status_code, 200)
            self.assertIn(r.json()["risk_level"], {"LOW", "MEDIUM", "HIGH"})
            self.assertEqual(self.client.get("/api/revenue/forecast/?months=2").status_code, 200)

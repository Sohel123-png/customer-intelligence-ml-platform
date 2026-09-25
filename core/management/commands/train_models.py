import json

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from core import ml
from core.models import Customer, Order

MODEL_DIR = settings.BASE_DIR / "ml_models"


def build_feature_frame():
    """Training rows come from the same `ml.customer_features` used at serving time."""
    rows = []
    qs = Customer.objects.select_related("subscription").prefetch_related(
        "support_tickets", "payments", "usage_logs", "orders"
    )
    for c in qs.iterator(chunk_size=500):
        try:
            features = ml.customer_features(c)
        except ObjectDoesNotExist:  # customer without a subscription
            continue
        rows.append({"customer_id": c.id, **features, "churned": int(c.churned)})
    return pd.DataFrame(rows)


class Command(BaseCommand):
    help = "Train churn prediction, revenue forecasting and customer segmentation models"

    def handle(self, *args, **options):
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        df = build_feature_frame()
        if df.empty:
            self.stdout.write(self.style.ERROR("No data found. Run `python manage.py generate_data` first."))
            return

        feature_cols = [
            "age", "tenure_months", "monthly_spend", "total_orders",
            "days_since_last_purchase", "support_tickets", "login_frequency",
            "payment_failures", "discount_usage", "plan_basic", "plan_pro", "plan_enterprise",
        ]
        X = df[feature_cols]
        y = df["churned"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        models = {
            "logistic_regression": None,  # placeholder for comparison table only
            "random_forest": RandomForestClassifier(n_estimators=300, max_depth=8, random_state=42),
            "xgboost": XGBClassifier(n_estimators=300, max_depth=5, learning_rate=0.05, eval_metric="logloss", random_state=42),
        }

        results = {}
        best_name, best_model, best_auc = None, None, -1
        for name, model in models.items():
            if model is None:
                continue
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            probs = model.predict_proba(X_test)[:, 1]
            metrics = {
                "accuracy": round(accuracy_score(y_test, preds), 4),
                "precision": round(precision_score(y_test, preds, zero_division=0), 4),
                "recall": round(recall_score(y_test, preds, zero_division=0), 4),
                "f1": round(f1_score(y_test, preds, zero_division=0), 4),
                "roc_auc": round(roc_auc_score(y_test, probs), 4),
            }
            results[name] = metrics
            self.stdout.write(f"{name}: {metrics}")
            if metrics["roc_auc"] > best_auc:
                best_auc, best_name, best_model = metrics["roc_auc"], name, model

        joblib.dump(best_model, MODEL_DIR / "churn_model.joblib")
        joblib.dump(feature_cols, MODEL_DIR / "churn_features.joblib")
        with open(MODEL_DIR / "model_comparison.json", "w") as f:
            json.dump({"best_model": best_name, "results": results}, f, indent=2)
        self.stdout.write(self.style.SUCCESS(f"Best model: {best_name} (ROC-AUC {best_auc})"))

        # --- Customer segmentation (KMeans) ---
        seg_features = ["monthly_spend", "total_orders", "tenure_months", "login_frequency"]
        scaler = StandardScaler()
        seg_X = scaler.fit_transform(df[seg_features])
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(seg_X)
        df["cluster"] = clusters
        joblib.dump(kmeans, MODEL_DIR / "segment_model.joblib")
        joblib.dump(scaler, MODEL_DIR / "segment_scaler.joblib")
        joblib.dump(seg_features, MODEL_DIR / "segment_features.joblib")

        labels = ml.label_clusters(kmeans, scaler, seg_features)
        (MODEL_DIR / "segment_labels.json").write_text(json.dumps(labels, indent=2))
        self.stdout.write(f"Segment labels: {labels}")

        cluster_profile = df.groupby("cluster")[seg_features].mean().round(1)
        self.stdout.write("Cluster profile (mean values):")
        self.stdout.write(cluster_profile.to_string())

        # --- Revenue forecast (simple monthly trend regression) ---
        orders_df = pd.DataFrame(
            Order.objects.values("order_date", "amount")
        )
        if orders_df.empty:
            self.stdout.write(self.style.ERROR("No orders found; cannot train revenue model."))
            return
        orders_df["order_date"] = pd.to_datetime(orders_df["order_date"])
        orders_df["month"] = orders_df["order_date"].dt.to_period("M")
        monthly_revenue = orders_df.groupby("month")["amount"].sum().reset_index()
        monthly_revenue["month_index"] = range(len(monthly_revenue))
        monthly_revenue["amount"] = monthly_revenue["amount"].astype(float)

        lr = LinearRegression()
        lr.fit(monthly_revenue[["month_index"]], monthly_revenue["amount"])
        joblib.dump(lr, MODEL_DIR / "revenue_model.joblib")
        monthly_revenue_out = monthly_revenue[["month", "amount"]].copy()
        monthly_revenue_out["month"] = monthly_revenue_out["month"].astype(str)
        monthly_revenue_out.to_json(MODEL_DIR / "monthly_revenue_history.json", orient="records")

        self.stdout.write(self.style.SUCCESS("All models trained and saved to ml_models/"))

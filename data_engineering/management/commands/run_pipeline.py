from django.core.management.base import BaseCommand
from django.utils import timezone
from data_engineering.services.models import ProductPrediction
from data_engineering.services.models import (
    PipelineRun,
    CleanProduct,
    ProductSnapshot,
)

from data_engineering.services.ingestion import (
    APIIngestionService,
)

from data_engineering.services.transformation import (
    transform_products,
)

from data_engineering.services.prediction import (
    predict_next_stock,
)

from data_engineering.services.prediction_evaluation import (
    evaluate_pending_prediction,
)

from data_engineering.services.snapshot_features import (
    build_snapshot_features,
)


class Command(BaseCommand):

    help = "Run complete data engineering pipeline"

    def handle(self, *args, **options):

        # =========================
        # CREATE PIPELINE RUN
        # =========================

        pipeline_run = PipelineRun.objects.create(
            status="running"
        )

        self.stdout.write(
            "Starting data pipeline..."
        )

        try:

            # =========================
            # STEP 1: INGESTION
            # =========================

            self.stdout.write(
                "\nStep 1: Ingestion"
            )

            ingestion_service = APIIngestionService(
                source_name="DummyJSON",
                url="https://dummyjson.com/products",
                params={
                    "limit": 30,
                },
                data_key="products",
            )

            ingestion_result = ingestion_service.run()

            self.stdout.write(
                f"Source: "
                f"{ingestion_result['source']}"
            )

            self.stdout.write(
                f"Created: "
                f"{ingestion_result['records_created']}"
            )

            self.stdout.write(
                f"Updated: "
                f"{ingestion_result['records_updated']}"
            )

            # =========================
            # STEP 2: TRANSFORMATION
            # =========================

            self.stdout.write(
                "\nStep 2: Transformation"
            )

            transformation_result = transform_products(
                only_valid=True
            )

            self.stdout.write("")

            self.stdout.write(
                self.style.SUCCESS(
                    "Data transformation completed!"
                )
            )

            self.stdout.write(
                f"Total raw records : "
                f"{transformation_result['total_raw']}"
            )

            self.stdout.write(
                f"Created           : "
                f"{transformation_result['created']}"
            )

            self.stdout.write(
                f"Updated           : "
                f"{transformation_result['updated']}"
            )

            self.stdout.write(
                f"Skipped           : "
                f"{transformation_result['skipped']}"
            )

            # =========================
            # STEP 3: PRODUCT SNAPSHOTS
            # =========================

            self.stdout.write(
                "\nStep 3: Creating product snapshots"
            )

            products = CleanProduct.objects.filter(
                source="DummyJSON"
            )

            snapshot_count = 0
            prediction_count = 0
            evaluation_count = 0

            for product in products:

                # =========================
                # CREATE SNAPSHOT
                # =========================

                snapshot = ProductSnapshot.objects.create(
                    product=product,
                    pipeline_run=pipeline_run,
                    price=product.price,
                    discount_percentage=product.discount_percentage,
                    rating=product.rating,
                    stock=product.stock,
                )

                snapshot_count += 1

                # =========================
                # EVALUATE PREVIOUS
                # PREDICTION
                # =========================

                evaluation_result = (
                    evaluate_pending_prediction(
                        snapshot
                    )
                )

                if evaluation_result["evaluated"]:

                    evaluation_count += 1

                    self.stdout.write(
                        f"Prediction evaluated | "
                        f"Product: {product.product_id} | "
                        f"Prediction: "
                        f"{evaluation_result['predicted_stock']} | "
                        f"Actual: "
                        f"{evaluation_result['actual_stock']} | "
                        f"Error: "
                        f"{evaluation_result['prediction_error']}"
                    )

                # =========================
                # BUILD FEATURES
                # =========================

                try:

                    feature_df = (
                        build_snapshot_features(
                            ProductSnapshot.objects
                            .filter(
                                product=product
                            )
                        )
                    )

                    if feature_df is None:
                        continue

                    if feature_df.empty:
                        continue

                    # Latest snapshot = current
                    latest = (
                        feature_df
                        .sort_values(
                            "captured_at"
                        )
                        .iloc[-1]
                    )

                    # =========================
                    # MODEL FEATURES
                    # =========================

                    features = {
                        "price": float(
                            latest["price"]
                        ),

                        "discount_percentage": float(
                            latest[
                                "discount_percentage"
                            ]
                        ),

                        "rating": float(
                            latest["rating"]
                        ),

                        "stock": float(
                            latest["stock"]
                        ),

                        "stock_lag_1": float(
                            latest["stock_lag_1"]
                        ),

                        "stock_lag_2": float(
                            latest["stock_lag_2"]
                        ),

                        "price_lag_1": float(
                            latest["price_lag_1"]
                        ),

                        "price_lag_2": float(
                            latest["price_lag_2"]
                        ),

                        "discount_lag_1": float(
                            latest[
                                "discount_lag_1"
                            ]
                        ),

                        "time_since_previous_minutes": float(
                            latest[
                                "time_since_previous_minutes"
                            ]
                        ),

                        "stock_rolling_mean_3": float(
                            latest[
                                "stock_rolling_mean_3"
                            ]
                        ),

                        "stock_rolling_min_3": float(
                            latest[
                                "stock_rolling_min_3"
                            ]
                        ),

                        "stock_rolling_max_3": float(
                            latest[
                                "stock_rolling_max_3"
                            ]
                        ),

                        "price_rolling_mean_3": float(
                            latest[
                                "price_rolling_mean_3"
                            ]
                        ),

                        "discount_rolling_mean_3": float(
                            latest[
                                "discount_rolling_mean_3"
                            ]
                        ),
                    }

                    # =========================
                    # CREATE NEW PREDICTION
                    # =========================

                    prediction_result = (
                        predict_next_stock(
                            features
                        )
                    )

                    if (
                        prediction_result["status"]
                        == "success"
                    ):

                        # Persist the prediction so the next pipeline run
                        # can evaluate it against the next snapshot.
                        ProductPrediction.objects.create(
                            product=product,
                            predicted_stock=prediction_result[
                                "predicted_next_stock"
                            ],
                            model_name=prediction_result["model"],
                            model_version="1.0",
                            status="pending",
                        )

                        prediction_count += 1

                        self.stdout.write(
                            f"Prediction created | "
                            f"Product: "
                            f"{product.product_id} | "
                            f"Next stock: "
                            f"{prediction_result['predicted_next_stock']}"
                        )

                    else:

                        self.stdout.write(
                            self.style.WARNING(
                                f"Prediction skipped | "
                                f"Product: "
                                f"{product.product_id} | "
                                f"Reason: "
                                f"{prediction_result.get('message')}"
                            )
                        )

                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ) as prediction_error:

                    self.stdout.write(
                        self.style.WARNING(
                            f"Prediction skipped | "
                            f"Product: "
                            f"{product.product_id} | "
                            f"Reason: "
                            f"{prediction_error}"
                        )
                    )

            # =========================
            # SNAPSHOT SUMMARY
            # =========================

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nSnapshots created: "
                    f"{snapshot_count}"
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Predictions created: "
                    f"{prediction_count}"
                )
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Predictions evaluated: "
                    f"{evaluation_count}"
                )
            )

            # =========================
            # SAVE PIPELINE METRICS
            # =========================

            pipeline_run.status = "success"

            pipeline_run.finished_at = (
                timezone.now()
            )

            pipeline_run.records_created = (
                transformation_result["created"]
            )

            pipeline_run.records_updated = (
                transformation_result["updated"]
            )

            pipeline_run.records_skipped = (
                transformation_result["skipped"]
            )

            pipeline_run.save()

            # =========================
            # SUCCESS
            # =========================

            self.stdout.write("")

            self.stdout.write(
                self.style.SUCCESS(
                    "Data pipeline completed successfully!"
                )
            )

        except Exception as error:

            # =========================
            # FAILURE
            # =========================

            pipeline_run.status = "failed"

            pipeline_run.finished_at = (
                timezone.now()
            )

            pipeline_run.error_message = str(
                error
            )

            pipeline_run.save()

            self.stdout.write(
                self.style.ERROR(
                    f"\nPipeline failed: {error}"
                )
            )

            raise
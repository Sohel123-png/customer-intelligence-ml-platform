from celery import shared_task
from django.core.cache import cache
from django.core.management import call_command

from data_engineering.services.model_monitoring import (
    check_model_drift,
)

from data_engineering.services.ml_model import (
    evaluate_and_promote_model,
)


PIPELINE_LOCK_KEY = "data_pipeline_running"
PIPELINE_LOCK_TIMEOUT = 10 * 60


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_data_pipeline(self):
    """
    Run the complete data pipeline.
    """

    lock_acquired = cache.add(
        PIPELINE_LOCK_KEY,
        "locked",
        timeout=PIPELINE_LOCK_TIMEOUT,
    )

    if not lock_acquired:
        return {
            "status": "skipped",
            "message": (
                "Another data pipeline is already running."
            ),
        }

    try:
        call_command("run_pipeline")

        return {
            "status": "success",
            "message": (
                "Data pipeline completed successfully."
            ),
        }

    finally:
        cache.delete(
            PIPELINE_LOCK_KEY
        )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def check_model_and_retrain(self):
    """
    Check model drift and retrain/promote a challenger
    only when drift is detected.
    """

    # ---------------------------------
    # 1. Check model drift
    # ---------------------------------

    drift_result = check_model_drift()

    # ---------------------------------
    # 2. Not enough data
    # ---------------------------------

    if drift_result["status"] == "insufficient_data":
        return {
            "status": "skipped",
            "reason": "insufficient_data",
            "drift": drift_result,
        }

    # ---------------------------------
    # 3. Model is healthy
    # ---------------------------------

    if not drift_result["drift_detected"]:
        return {
            "status": "skipped",
            "reason": "no_drift",
            "drift": drift_result,
        }

    # ---------------------------------
    # 4. Drift detected
    # ---------------------------------

    retraining_result = evaluate_and_promote_model()

    return {
        "status": "retraining_completed",
        "drift": drift_result,
        "retraining": retraining_result,
    }
from __future__ import annotations

from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

from data_engineering.services.ml_dataset import (
    prepare_temporal_training_data,
)

from data_engineering.services.model_registry import (
    load_metadata,
    compare_models,
    promote_model,
    save_model,
)


def calculate_metrics(y_true, predictions):
    """
    Calculate regression evaluation metrics.
    """

    mae = mean_absolute_error(
        y_true,
        predictions,
    )

    rmse = mean_squared_error(
        y_true,
        predictions,
    ) ** 0.5

    r2 = r2_score(
        y_true,
        predictions,
    )

    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2": float(r2),
    }


def train_model(
    source="DummyJSON",
    min_history=3,
):
    """
    Train a challenger model without
    modifying the current production model.
    """

    dataset = prepare_temporal_training_data(
        source=source,
        min_history=min_history,
    )

    if dataset["status"] != "ready":
        return dataset

    X_train = dataset["X_train"]
    X_test = dataset["X_test"]

    y_train = dataset["y_train"]
    y_test = dataset["y_test"]

    model = LinearRegression()

    model.fit(
        X_train,
        y_train,
    )

    predictions = model.predict(
        X_test
    )

    metrics = calculate_metrics(
        y_test,
        predictions,
    )

    return {
        "status": "success",
        "model": model,
        "model_type": "LinearRegression",
        "features": dataset["features"],
        "removed_constant_features": dataset[
            "removed_constant_features"
        ],
        "training_rows": len(X_train),
        "test_rows": len(X_test),
        "metrics": metrics,
    }


def train_baseline_model(
    source="DummyJSON",
    min_history=3,
):
    """
    Train and save the baseline production model.
    """

    result = train_model(
        source=source,
        min_history=min_history,
    )

    if result["status"] != "success":
        return result

    registry_result = save_model(
        model=result["model"],
        metrics=result["metrics"],
        feature_names=result["features"],
        training_rows=result["training_rows"],
    )

    return {
        "status": "success",
        "model": result["model_type"],
        "features": result["features"],
        "removed_constant_features": result[
            "removed_constant_features"
        ],
        "training_rows": result["training_rows"],
        "test_rows": result["test_rows"],
        "metrics": result["metrics"],
        "registry": registry_result,
    }


def evaluate_and_promote_model(
    source="DummyJSON",
    min_history=3,
):
    """
    Train challenger and promote it only if
    it performs better than the current model.
    """

    # ---------------------------------
    # 1. Load current production metadata
    # ---------------------------------

    try:
        current_metadata = load_metadata()

    except FileNotFoundError:
        return {
            "status": "no_current_model",
            "message": (
                "No current production model found."
            ),
        }

    current_metrics = current_metadata["metrics"]

    # ---------------------------------
    # 2. Train challenger
    # ---------------------------------

    challenger = train_model(
        source=source,
        min_history=min_history,
    )

    if challenger["status"] != "success":
        return challenger

    challenger_metrics = challenger["metrics"]

    # ---------------------------------
    # 3. Compare models
    # ---------------------------------

    comparison = compare_models(
        current_metrics=current_metrics,
        challenger_metrics=challenger_metrics,
    )

    # ---------------------------------
    # 4. Reject challenger
    # ---------------------------------

    if not comparison["challenger_better"]:
        return {
            "status": "rejected",
            "message": (
                "Challenger model was not better "
                "than the current model."
            ),
            "current_metrics": current_metrics,
            "challenger_metrics": challenger_metrics,
            "comparison": comparison,
        }

    # ---------------------------------
    # 5. Promote challenger
    # ---------------------------------

    promotion = promote_model(
        challenger_model=challenger["model"],
        challenger_metrics=challenger_metrics,
        feature_names=challenger["features"],
        training_rows=challenger["training_rows"],
    )

    return {
        "status": "promoted",
        "message": (
            "Challenger model promoted successfully."
        ),
        "current_metrics": current_metrics,
        "challenger_metrics": challenger_metrics,
        "comparison": comparison,
        "promotion": promotion,
    }
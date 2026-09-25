
from pathlib import Path
from datetime import datetime, timezone
import json
import shutil
import joblib


BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_DIR = BASE_DIR / "ml_models"
MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

MODEL_PATH = MODEL_DIR / "next_stock_model.joblib"
METADATA_PATH = MODEL_DIR / "next_stock_model_metadata.json"


def save_model(
    model,
    metrics,
    feature_names,
    training_rows,
):
    joblib.dump(
        model,
        MODEL_PATH,
    )

    metadata = {
        "model_name": "next_stock_linear_regression",
        "model_type": "LinearRegression",
        "trained_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "training_rows": int(training_rows),
        "features": list(feature_names),
        "metrics": {
            "mae": float(metrics["mae"]),
            "rmse": float(metrics["rmse"]),
            "r2": float(metrics["r2"]),
        },
    }

    with open(
        METADATA_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=4,
        )

    return {
        "model_path": str(MODEL_PATH),
        "metadata_path": str(METADATA_PATH),
    }


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "No trained model found."
        )

    return joblib.load(MODEL_PATH)


def load_metadata():
    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            "No model metadata found."
        )

    with open(
        METADATA_PATH,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)

def compare_models(
    current_metrics,
    challenger_metrics,
):
    current_mae = float(
        current_metrics["mae"]
    )

    challenger_mae = float(
        challenger_metrics["mae"]
    )

    improvement = current_mae - challenger_mae

    return {
        "current_mae": current_mae,
        "challenger_mae": challenger_mae,
        "improvement": improvement,
        "challenger_better": challenger_mae < current_mae,
    }

def promote_model(
    challenger_model,
    challenger_metrics,
    feature_names,
    training_rows,
):
    backup_model_path = MODEL_DIR / "next_stock_model_backup.joblib"
    backup_metadata_path = (
        MODEL_DIR / "next_stock_model_metadata_backup.json"
    )

    # Backup current model if it exists
    if MODEL_PATH.exists():
        shutil.copy2(
            MODEL_PATH,
            backup_model_path,
        )

    if METADATA_PATH.exists():
        shutil.copy2(
            METADATA_PATH,
            backup_metadata_path,
        )

    # Save challenger as production model
    registry_result = save_model(
        model=challenger_model,
        metrics=challenger_metrics,
        feature_names=feature_names,
        training_rows=training_rows,
    )

    return {
        "status": "promoted",
        "message": "Challenger model promoted successfully.",
        "backup_model": str(
            backup_model_path
        ),
        "backup_metadata": str(
            backup_metadata_path
        ),
        "registry": registry_result,
    }
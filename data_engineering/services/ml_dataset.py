from __future__ import annotations

import numpy as np
import pandas as pd

from data_engineering.services.models import ProductSnapshot
from data_engineering.services.snapshot_features import (
    build_snapshot_features,
)


FEATURE_COLUMNS = [
    "price",
    "discount_percentage",
    "rating",
    "stock",
    "stock_lag_1",
    "stock_lag_2",
    "price_lag_1",
    "price_lag_2",
    "discount_lag_1",
    "stock_change",
    "price_change",
    "discount_change",
    "stock_change_pct",
    "price_change_pct",
    "discount_change_pct",
    "time_since_previous_minutes",
    "stock_velocity_per_hour",
    "stock_rolling_mean_3",
    "stock_rolling_min_3",
    "stock_rolling_max_3",
    "price_rolling_mean_3",
    "discount_rolling_mean_3",
    "stock_trend",
]


def get_history_summary(
    source: str | None = None,
):
    """
    Return snapshot history count for every product.

    This is used by the ML readiness service.
    """

    queryset = ProductSnapshot.objects.select_related("product")

    if source:
        queryset = queryset.filter(
            product__source=source
        )

    rows = []

    for snapshot in queryset:
        rows.append(
            {
                "product_id": snapshot.product.product_id,
                "source": snapshot.product.source,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "product_id",
                "source",
                "snapshot_count",
            ]
        )

    df = pd.DataFrame(rows)

    history = (
        df.groupby(
            ["product_id", "source"],
            as_index=False,
        )
        .size()
        .rename(
            columns={
                "size": "snapshot_count",
            }
        )
    )

    return history


def _build_feature_dataset(
    source: str = "DummyJSON",
    min_history: int = 3,
):
    """
    Build snapshot feature dataset for one source.

    One row represents one product snapshot.
    """

    queryset = (
        ProductSnapshot.objects
        .select_related("product")
        .filter(product__source=source)
        .order_by(
            "product__product_id",
            "captured_at",
        )
    )

    dataset = build_snapshot_features(
        queryset=queryset
    )

    if dataset.empty:
        return pd.DataFrame()

    dataset = dataset.copy()

    dataset["captured_at"] = pd.to_datetime(
        dataset["captured_at"]
    )

    dataset = dataset.sort_values(
        [
            "product_id",
            "captured_at",
        ]
    ).reset_index(drop=True)

    # Keep only products having enough snapshot history.
    history_counts = (
        dataset.groupby("product_id")
        .size()
    )

    valid_products = history_counts[
        history_counts >= min_history
    ].index

    dataset = dataset[
        dataset["product_id"].isin(
            valid_products
        )
    ].copy()

    if dataset.empty:
        return pd.DataFrame()

    # Target = next snapshot stock.
    dataset["next_stock"] = (
        dataset.groupby("product_id")[
            "stock"
        ].shift(-1)
    )

    # Remove infinite values created by
    # percentage/velocity calculations.
    dataset = dataset.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    # Every feature and target must be available.
    dataset = dataset.dropna(
        subset=FEATURE_COLUMNS + ["next_stock"]
    )

    return dataset.reset_index(drop=True)


def build_ml_dataset(
    source: str = "DummyJSON",
    min_history: int = 3,
):
    """
    Build the supervised ML dataset.

    Features:
        Current and historical product snapshot features.

    Target:
        next_stock
    """

    dataset = _build_feature_dataset(
        source=source,
        min_history=min_history,
    )

    if dataset.empty:
        return (
            pd.DataFrame(
                columns=FEATURE_COLUMNS
            ),
            pd.Series(
                dtype=float,
                name="next_stock",
            ),
        )

    X = dataset[
        FEATURE_COLUMNS
    ].copy()

    y = dataset[
        "next_stock"
    ].astype(float).copy()

    return X, y


def build_ml_dataset_with_metadata(
    source: str = "DummyJSON",
    min_history: int = 3,
):
    """
    Build ML dataset while preserving:

        product_id
        source
        captured_at
        next_stock

    Used for chronological splitting.
    """

    return _build_feature_dataset(
        source=source,
        min_history=min_history,
    )


def prepare_temporal_training_data(
    source: str = "DummyJSON",
    min_history: int = 3,
    test_size: float = 0.20,
):
    """
    Create a leakage-safe chronological train/test split.

    For every product:

        Older observations -> training
        Newer observations -> testing
    """

    if not 0 < test_size < 1:
        return {
            "status": "not_ready",
            "message": (
                "test_size must be between 0 and 1."
            ),
        }

    dataset = build_ml_dataset_with_metadata(
        source=source,
        min_history=min_history,
    )

    if dataset.empty:
        return {
            "status": "not_ready",
            "message": (
                "No valid ML dataset available."
            ),
        }

    train_parts = []
    test_parts = []

    for product_id, group in dataset.groupby(
        "product_id"
    ):
        group = (
            group
            .sort_values("captured_at")
            .reset_index(drop=True)
        )

        if len(group) < 2:
            continue

        split_index = int(
            len(group) * (1 - test_size)
        )

        # Guarantee at least one row
        # in both train and test.
        split_index = max(
            1,
            min(
                split_index,
                len(group) - 1,
            ),
        )

        train_parts.append(
            group.iloc[:split_index]
        )

        test_parts.append(
            group.iloc[split_index:]
        )

    if not train_parts or not test_parts:
        return {
            "status": "not_ready",
            "message": (
                "Unable to create temporal "
                "train/test split."
            ),
        }

    train_df = pd.concat(
        train_parts,
        ignore_index=True,
    )

    test_df = pd.concat(
        test_parts,
        ignore_index=True,
    )

    # Remove zero-variance features using
    # training data ONLY.
    constant_features = [
        column
        for column in FEATURE_COLUMNS
        if train_df[column].nunique(
            dropna=False
        ) <= 1
    ]

    selected_features = [
        column
        for column in FEATURE_COLUMNS
        if column not in constant_features
    ]

    if not selected_features:
        return {
            "status": "not_ready",
            "message": (
                "No variable ML features "
                "are available."
            ),
        }

    X_train = train_df[
        selected_features
    ].copy()

    X_test = test_df[
        selected_features
    ].copy()

    y_train = train_df[
        "next_stock"
    ].astype(float).copy()

    y_test = test_df[
        "next_stock"
    ].astype(float).copy()

    if X_train.empty or X_test.empty:
        return {
            "status": "not_ready",
            "message": (
                "Training or testing dataset "
                "is empty."
            ),
        }

    return {
        "status": "ready",
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "train_metadata": train_df[
            [
                "product_id",
                "captured_at",
            ]
        ].copy(),
        "test_metadata": test_df[
            [
                "product_id",
                "captured_at",
            ]
        ].copy(),
        "features": selected_features,
        "removed_constant_features": (
            constant_features
        ),
    }
from django.db.models import QuerySet
import pandas as pd

from data_engineering.services.models import ProductSnapshot


def build_snapshot_features(
    queryset: QuerySet | None = None,
):
    if queryset is None:
        queryset = (
            ProductSnapshot.objects
            .select_related("product")
            .order_by("product_id", "captured_at")
        )

    rows = []

    for snapshot in queryset:
        rows.append(
            {
                "product_id": snapshot.product.product_id,
                "source": snapshot.product.source,
                "name": snapshot.product.name,
                "category": snapshot.product.category,
                "captured_at": snapshot.captured_at,
                "price": float(snapshot.price),
                "discount_percentage": float(
                    snapshot.discount_percentage
                ),
                "rating": float(snapshot.rating),
                "stock": int(snapshot.stock),
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Sort history
    df = (
        df.sort_values(
            ["product_id", "captured_at"]
        )
        .reset_index(drop=True)
    )

    grouped = df.groupby("product_id")

    # -------------------------
    # LAG FEATURES
    # -------------------------

    df["stock_lag_1"] = grouped["stock"].shift(1)
    df["stock_lag_2"] = grouped["stock"].shift(2)

    df["price_lag_1"] = grouped["price"].shift(1)
    df["price_lag_2"] = grouped["price"].shift(2)

    df["discount_lag_1"] = (
        grouped["discount_percentage"].shift(1)
    )

    # -------------------------
    # PREVIOUS VALUES
    # -------------------------

    df["previous_stock"] = df["stock_lag_1"]
    df["previous_price"] = df["price_lag_1"]
    df["previous_discount"] = df["discount_lag_1"]

    # -------------------------
    # CHANGE FEATURES
    # -------------------------

    df["stock_change"] = (
        df["stock"] - df["previous_stock"]
    )

    df["price_change"] = (
        df["price"] - df["previous_price"]
    )

    df["discount_change"] = (
        df["discount_percentage"]
        - df["previous_discount"]
    )

    # -------------------------
    # PERCENTAGE CHANGE
    # -------------------------

    df["stock_change_pct"] = (
        df["stock_change"]
        / df["previous_stock"].replace(0, pd.NA)
        * 100
    )

    df["price_change_pct"] = (
        df["price_change"]
        / df["previous_price"].replace(0, pd.NA)
        * 100
    )

    df["discount_change_pct"] = (
        df["discount_change"]
        / df["previous_discount"].replace(0, pd.NA)
        * 100
    )

    # -------------------------
    # TIME DIFFERENCE
    # -------------------------

    df["previous_captured_at"] = (
        grouped["captured_at"].shift(1)
    )

    df["time_since_previous_minutes"] = (
        (
            df["captured_at"]
            - df["previous_captured_at"]
        )
        .dt.total_seconds()
        / 60
    )

    # -------------------------
    # STOCK VELOCITY
    # -------------------------

    df["stock_velocity_per_hour"] = (
        df["stock_change"]
        / (
            df["time_since_previous_minutes"]
            / 60
        )
    )

    # -------------------------
    # ROLLING FEATURES
    # -------------------------

    df["stock_rolling_mean_3"] = (
        grouped["stock"]
        .transform(
            lambda x: x.rolling(
                window=3,
                min_periods=1
            ).mean()
        )
    )

    df["stock_rolling_min_3"] = (
        grouped["stock"]
        .transform(
            lambda x: x.rolling(
                window=3,
                min_periods=1
            ).min()
        )
    )

    df["stock_rolling_max_3"] = (
        grouped["stock"]
        .transform(
            lambda x: x.rolling(
                window=3,
                min_periods=1
            ).max()
        )
    )

    df["price_rolling_mean_3"] = (
        grouped["price"]
        .transform(
            lambda x: x.rolling(
                window=3,
                min_periods=1
            ).mean()
        )
    )

    df["discount_rolling_mean_3"] = (
        grouped["discount_percentage"]
        .transform(
            lambda x: x.rolling(
                window=3,
                min_periods=1
            ).mean()
        )
    )

    # -------------------------
    # STOCK TREND
    # -------------------------

    df["stock_trend"] = (
        df["stock"]
        - df["stock_rolling_mean_3"]
    )

    return df
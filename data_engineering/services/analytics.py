import pandas as pd

from data_engineering.services.feature_engineering import (
    build_product_features,
)


def get_product_dataframe(source=None):
    """
    Build the product analytics DataFrame.

    Parameters
    ----------
    source : str | None
        Optional source filter, e.g. "DummyJSON".

    Returns
    -------
    pandas.DataFrame
        Product-level analytics data.
    """

    features = build_product_features()

    if not features:
        return pd.DataFrame()

    df = pd.DataFrame(features)

    if source:
        df = df[df["source"] == source].copy()

    return df.reset_index(drop=True)


def get_product_summary(source=None):
    """
    Return high-level product KPIs.
    """

    df = get_product_dataframe(source=source)

    if df.empty:
        return {}

    return {
        "total_products": int(len(df)),
        "average_price": round(
            float(df["price"].mean()),
            2,
        ),
        "average_rating": round(
            float(df["rating"].mean()),
            2,
        ),
        "average_discount": round(
            float(df["discount_percentage"].mean()),
            2,
        ),
        "total_stock": int(
            df["stock"].sum()
        ),
        "low_stock_products": int(
            df["is_low_stock"].sum()
        ),
        "out_of_stock_products": int(
            df["is_out_of_stock"].sum()
        ),
    }


def get_discount_analysis(source=None):
    """
    Analyze products by discount category.
    """

    df = get_product_dataframe(source=source)

    if df.empty:
        return pd.DataFrame()

    df = df.copy()

    df["discount_category"] = pd.cut(
        df["discount_percentage"],
        bins=[
            -0.01,
            5,
            10,
            20,
            float("inf"),
        ],
        labels=[
            "Very Low",
            "Low",
            "Moderate",
            "High",
        ],
    )

    result = (
        df.groupby(
            "discount_category",
            observed=False,
        )
        .agg(
            products=("product_id", "count"),
            average_price=("price", "mean"),
            average_rating=("rating", "mean"),
            average_discount=(
                "discount_percentage",
                "mean",
            ),
        )
        .round(2)
    )

    return result


def get_price_analysis(source=None):
    """
    Return basic price statistics.
    """

    df = get_product_dataframe(source=source)

    if df.empty:
        return {}

    return {
        "min_price": round(
            float(df["price"].min()),
            2,
        ),
        "max_price": round(
            float(df["price"].max()),
            2,
        ),
        "average_price": round(
            float(df["price"].mean()),
            2,
        ),
        "median_price": round(
            float(df["price"].median()),
            2,
        ),
    }


def get_rating_analysis(source=None):
    """
    Analyze products by rating category.
    """

    df = get_product_dataframe(source=source)

    if df.empty:
        return pd.DataFrame()

    result = (
        df.groupby("rating_category")
        .agg(
            products=("product_id", "count"),
            average_price=("price", "mean"),
            average_discount=(
                "discount_percentage",
                "mean",
            ),
            total_stock=("stock", "sum"),
        )
        .round(2)
    )

    return result


def get_business_insights(source=None):
    """
    Generate high-level business insights.
    """

    df = get_product_dataframe(source=source)

    if df.empty:
        return {}

    insights = {
        "total_products": int(len(df)),
        "average_price": round(
            float(df["price"].mean()),
            2,
        ),
        "average_rating": round(
            float(df["rating"].mean()),
            2,
        ),
        "average_discount": round(
            float(df["discount_percentage"].mean()),
            2,
        ),
        "total_stock": int(
            df["stock"].sum()
        ),
        "low_stock_products": int(
            df["is_low_stock"].sum()
        ),
        "out_of_stock_products": int(
            df["is_out_of_stock"].sum()
        ),
    }

    if "category" not in df.columns:
        return insights

    category_df = (
        df.groupby("category")
        .agg(
            products=("product_id", "count"),
            average_price=("price", "mean"),
            average_discount=(
                "discount_percentage",
                "mean",
            ),
        )
    )

    if category_df.empty:
        return insights

    # Largest category
    max_products = category_df["products"].max()

    largest_categories = (
        category_df[
            category_df["products"] == max_products
        ]
        .index
        .tolist()
    )

    insights["largest_category"] = (
        largest_categories[0]
    )

    # Highest average price category
    max_price = category_df[
        "average_price"
    ].max()

    highest_price_categories = (
        category_df[
            category_df["average_price"] == max_price
        ]
        .index
        .tolist()
    )

    insights["highest_avg_price_category"] = (
        highest_price_categories[0]
    )

    # Highest average discount category
    max_discount = category_df[
        "average_discount"
    ].max()

    highest_discount_categories = (
        category_df[
            category_df["average_discount"]
            == max_discount
        ]
        .index
        .tolist()
    )

    insights["highest_avg_discount_category"] = (
        highest_discount_categories[0]
    )

    return insights
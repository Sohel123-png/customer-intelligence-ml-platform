from django.db.models import QuerySet

from data_engineering.services.models import CleanProduct


def build_product_features(queryset: QuerySet | None = None):
    """
    Build analytical/ML-ready features from CleanProduct records.
    """

    if queryset is None:
        queryset = CleanProduct.objects.all()

    features = []

    for product in queryset:

        price = float(product.price)
        discount = float(product.discount_percentage)
        rating = float(product.rating)
        stock = int(product.stock)

        discount_amount = price * (discount / 100)
        final_price = price - discount_amount

        # Stock classification
        if stock == 0:
            stock_category = "out_of_stock"
        elif stock <= 10:
            stock_category = "low_stock"
        elif stock <= 50:
            stock_category = "medium_stock"
        else:
            stock_category = "high_stock"

        # Rating classification
        if rating < 2:
            rating_category = "poor"
        elif rating < 3.5:
            rating_category = "average"
        elif rating < 4.5:
            rating_category = "good"
        else:
            rating_category = "excellent"

        features.append({
            "product_id": product.product_id,
            "source": product.source,
            "name": product.name,
            "category": product.category,
            "brand": product.brand,
            "sku": product.sku,

            # Original features
            "price": price,
            "discount_percentage": discount,
            "rating": rating,
            "stock": stock,

            # Derived features
            "discount_amount": round(discount_amount, 2),
            "final_price": round(final_price, 2),
            "is_low_stock": stock <= 10,
            "is_out_of_stock": stock == 0,
            "is_high_discount": discount >= 20,
            "stock_category": stock_category,
            "rating_category": rating_category,
        })

    return features
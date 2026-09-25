from data_engineering.services.ml_dataset import (
    get_history_summary,
)


def get_ml_readiness(min_history=3):
    """
    Check whether enough historical snapshot data
    is available for ML training.
    """

    history = get_history_summary()

    if history.empty:
        return {
            "total_products": 0,
            "ready_products": 0,
            "minimum_history": min_history,
            "ready_percentage": 0.0,
            "status": "not_ready",
        }

    total_products = len(history)

    ready_products = int(
        (
            history["snapshot_count"] >= min_history
        ).sum()
    )

    ready_percentage = round(
        (ready_products / total_products) * 100,
        2,
    )

    if ready_products == 0:
        status = "not_ready"

    elif ready_products < total_products:
        status = "partially_ready"

    else:
        status = "ready"

    return {
        "total_products": total_products,
        "ready_products": ready_products,
        "minimum_history": min_history,
        "ready_percentage": ready_percentage,
        "status": status,
    }
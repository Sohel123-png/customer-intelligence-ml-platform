from decimal import Decimal, InvalidOperation

from data_engineering.services.models import DataQualityIssue


class DataQualityService:

    def validate_record(self, raw_record):
        data = raw_record.payload
        issues = []

        product_id = data.get("id")
        name = data.get("name") or data.get("title")
        category = data.get("category")
        price = data.get("price")

        # Product ID
        if product_id is None or str(product_id).strip() == "":
            issues.append({
                "field_name": "id",
                "issue_type": "missing",
                "message": "Product ID is missing.",
            })

        # Product name
        if name is None or str(name).strip() == "":
            issues.append({
                "field_name": "name",
                "issue_type": "missing",
                "message": "Product name is missing.",
            })

        # Category
        if category is None or str(category).strip() == "":
            issues.append({
                "field_name": "category",
                "issue_type": "missing",
                "message": "Product category is missing.",
            })

        # Price
        if price is None or str(price).strip() == "":
            issues.append({
                "field_name": "price",
                "issue_type": "missing",
                "message": "Product price is missing.",
            })
        else:
            try:
                decimal_price = Decimal(str(price))

                if decimal_price < 0:
                    issues.append({
                        "field_name": "price",
                        "issue_type": "negative",
                        "message": "Product price cannot be negative.",
                    })

            except (InvalidOperation, ValueError, TypeError):
                issues.append({
                    "field_name": "price",
                    "issue_type": "invalid",
                    "message": "Product price must be a valid number.",
                })

        # Save issues
        for issue in issues:
            DataQualityIssue.objects.create(
                raw_record=raw_record,
                field_name=issue["field_name"],
                issue_type=issue["issue_type"],
                message=issue["message"],
            )

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
        }
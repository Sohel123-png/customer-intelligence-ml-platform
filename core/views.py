import re

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Sum, Q, Avg
from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from . import ml
from .models import Customer, ChurnPrediction, CustomerSegment, Order, SupportTicket
from .serializers import CustomerSerializer, ChurnPredictInputSerializer


def _int_param(request, name, default, minimum=1, maximum=100):
    """Read an int query param safely: bad input falls back to the default, and the value is clamped."""
    try:
        value = int(request.query_params.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


class ChurnPredictView(APIView):
    """
    POST /api/predict/churn/
    Body either {"customer_id": 5} to score an existing customer,
    or raw feature values to score a hypothetical one.
    """

    def post(self, request):
        serializer = ChurnPredictInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get("customer_id"):
            customer = get_object_or_404(Customer, id=data["customer_id"])
            try:
                features = ml.customer_features(customer)
            except ObjectDoesNotExist:
                return Response(
                    {"error": "This customer has no subscription record, so it cannot be scored."},
                    status=422,
                )
        else:
            plan = data.get("plan", "pro")
            features = {
                "age": data["age"],
                "tenure_months": data["tenure_months"],
                "monthly_spend": data["monthly_spend"],
                "total_orders": data["total_orders"],
                "days_since_last_purchase": data["days_since_last_purchase"],
                "support_tickets": data["support_tickets"],
                "login_frequency": data["login_frequency"],
                "payment_failures": data["payment_failures"],
                "discount_usage": data["discount_usage"],
                "plan_basic": int(plan == "basic"),
                "plan_pro": int(plan == "pro"),
                "plan_enterprise": int(plan == "enterprise"),
            }
            customer = None

        result = ml.predict_churn(features)

        if customer:
            ChurnPrediction.objects.update_or_create(
                customer=customer,
                defaults={
                    "churn_probability": result["churn_probability"],
                    "risk_level": result["risk_level"],
                    "top_factors": result["top_factors"],
                },
            )

        return Response(result)


@api_view(["GET"])
def high_risk_customers(request):
    limit = _int_param(request, "limit", 20, minimum=1, maximum=100)
    qs = ChurnPrediction.objects.select_related("customer", "customer__subscription") \
        .filter(risk_level="HIGH", customer__subscription__isnull=False) \
        .order_by("-churn_probability")[:limit]
    payload = [{
        "customer_id": p.customer.id,
        "name": p.customer.name,
        "plan": p.customer.plan,
        "region": p.customer.region,
        "churn_probability": p.churn_probability,
        "monthly_spend": float(p.customer.subscription.monthly_spend),
        "top_factors": p.top_factors,
    } for p in qs]
    return Response({"count": len(payload), "results": payload})


@api_view(["GET"])
def customer_segments(request):
    counts = CustomerSegment.objects.values("segment_name").annotate(count=Count("id")).order_by("-count")
    return Response({"segments": list(counts)})


@api_view(["GET"])
def revenue_forecast(request):
    months = _int_param(request, "months", 3, minimum=1, maximum=24)
    return Response(ml.forecast_revenue(months_ahead=months))


@api_view(["GET"])
def analytics_summary(request):
    total_customers = Customer.objects.count()
    churned = Customer.objects.filter(churned=True).count()
    churn_rate = round((churned / total_customers) * 100, 2) if total_customers else 0
    total_revenue = Order.objects.aggregate(total=Sum("amount"))["total"] or 0
    high_risk = ChurnPrediction.objects.filter(risk_level="HIGH").count()
    avg_spend = Customer.objects.filter(is_active=True).aggregate(
        avg=Avg("subscription__monthly_spend"))["avg"] or 0

    by_plan = Customer.objects.values("plan").annotate(
        total=Count("id"), churned=Count("id", filter=Q(churned=True))
    )
    by_region = Customer.objects.values("region").annotate(
        total=Count("id"), churned=Count("id", filter=Q(churned=True))
    ).order_by("-total")[:8]

    return Response({
        "total_customers": total_customers,
        "active_customers": total_customers - churned,
        "churn_rate_pct": churn_rate,
        "total_revenue": float(total_revenue),
        "avg_monthly_spend": round(float(avg_spend), 2),
        "high_risk_customers": high_risk,
        "churn_by_plan": list(by_plan),
        "churn_by_region": list(by_region),
    })


@api_view(["POST"])
def ai_business_analyst(request):
    """
    A lightweight text-to-insight endpoint: matches a business question to a
    canned SQL/ORM query and returns a natural-language summary. This is a
    template layer — swap `generate_explanation()` for a real LLM call
    (see README) to turn it into a full RAG + LLM business analyst.
    """
    question = (request.data.get("question") or "").strip()
    if not question:
        return Response({"error": "Provide a 'question' field."}, status=400)

    q_lower = question.lower()

    if "churn" in q_lower and ("region" in q_lower or "state" in q_lower or any(
            r.lower() in q_lower for r in Customer.objects.values_list("region", flat=True).distinct())):
        region_match = None
        for r in Customer.objects.values_list("region", flat=True).distinct():
            if r.lower() in q_lower:
                region_match = r
                break
        qs = Customer.objects.filter(region=region_match) if region_match else Customer.objects.all()
        total = qs.count()
        churned = qs.filter(churned=True).count()
        rate = round((churned / total) * 100, 2) if total else 0
        top_ticket_category = SupportTicket.objects.filter(customer__in=qs).values("category") \
            .annotate(c=Count("id")).order_by("-c").first()
        explanation = (
            f"In {region_match or 'all regions'}, churn rate is {rate}% ({churned} of {total} customers). "
            f"The most common support issue in this group is '{top_ticket_category['category'] if top_ticket_category else 'n/a'}', "
            f"which correlates with higher churn risk in the model's SHAP explanations."
        )
        return Response({"question": question, "answer": explanation, "data": {"region": region_match, "total": total, "churned": churned, "churn_rate_pct": rate}})

    if "lifetime value" in q_lower or "ltv" in q_lower or ("churn probability" in q_lower and "customers with" in q_lower):
        threshold_match = re.search(r'(\d[\d,]*)', question)
        prob_match = re.search(r'(\d{1,3})\s*%', question)
        min_spend = float(threshold_match.group(1).replace(",", "")) if threshold_match else 0
        min_prob = (float(prob_match.group(1)) / 100) if prob_match else 0.0
        qs = ChurnPrediction.objects.select_related("customer", "customer__subscription").filter(
            churn_probability__gte=min_prob
        )
        results = [
            {"customer_id": p.customer.id, "name": p.customer.name,
             "monthly_spend": float(p.customer.subscription.monthly_spend),
             "churn_probability": p.churn_probability}
            for p in qs if float(p.customer.subscription.monthly_spend) * 12 >= min_spend
        ][:25]
        explanation = f"Found {len(results)} customers matching lifetime value ≥ {min_spend} and churn probability ≥ {min_prob*100:.0f}%."
        return Response({"question": question, "answer": explanation, "data": results})

    total = Customer.objects.count()
    churned = Customer.objects.filter(churned=True).count()
    rate = round((churned / total) * 100, 2) if total else 0
    explanation = (
        f"I can currently answer questions about churn by region and about customers filtered by "
        f"lifetime value and churn probability. Overall churn rate right now is {rate}% "
        f"({churned} of {total} customers). Try asking: "
        f"'Why did churn increase in Maharashtra?' or "
        f"'Show customers with lifetime value above 50000 and churn probability above 70%'."
    )
    return Response({"question": question, "answer": explanation, "data": None})


def dashboard(request):
    return render(request, "core/dashboard.html")

# monetization/views/subscription_views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseNotAllowed
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta
from decimal import Decimal
from monetization.models import Subscription, SubscriptionPlan, Coupon, Order
from monetization.services.paypal_service import get_paypal_credentials, get_paypal_base_url
from monetization.services.email_service import send_order_email


@login_required
def subscription_pricing(request):
    active_subscription = Subscription.objects.filter(
        user=request.user,
        status__in=["active", "canceled"],
        next_billing_date__gte=now()
    ).first()
    if active_subscription:
        messages.warning(
            request,
            f"You already have a valid subscription until {active_subscription.next_billing_date.strftime('%B %d, %Y')}. You can resubscribe after that date."
        )
        return redirect("dashboard")
    subscription_plans = SubscriptionPlan.objects.filter(active=True, duration__in=["monthly", "annual"])
    one_time_plan = SubscriptionPlan.objects.filter(duration="one_time", active=True).first()
    one_time_price = one_time_plan.price if one_time_plan else Decimal("19.99")
    active_coupons = Coupon.objects.filter(
        is_active=True, valid_from__lte=now(), valid_to__gte=now()
    )
    context = {
        "subscription_plans": subscription_plans,
        "one_time_price": one_time_price,
        "active_coupons": active_coupons,
    }
    return render(request, "monetization/subscription_pricing.html", context)


@login_required
def process_subscription(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    from monetization.models import SubscriptionPlan, Subscription
    client_id, secret_key = get_paypal_credentials()
    if not client_id:
        messages.error(request, "PayPal credentials not found.")
        return redirect("subscription_pricing")

    plan_id = request.POST.get("plan_id")
    subscription_plan = SubscriptionPlan.objects.filter(id=plan_id, active=True).first()
    if not subscription_plan or not subscription_plan.paypal_plan_id:
        messages.error(request, "Invalid subscription plan or missing PayPal plan ID.")
        return redirect("subscription_pricing")

    # Optional coupon code processing
    coupon_code = request.POST.get("coupon_code", "").strip()
    discount = Decimal("0.00")
    if coupon_code:
        from monetization.models import Coupon
        coupon = Coupon.objects.filter(code=coupon_code, is_active=True).first()
        if coupon and coupon.is_valid:
            discount = (coupon.discount_percent / Decimal("100.00")) * subscription_plan.price
            messages.success(request, f"Coupon applied: {coupon.discount_percent}% off!")
        else:
            messages.error(request, "Invalid or expired coupon.")
            return redirect("subscription_pricing")

    final_price = subscription_plan.price - discount
    request.session["subscription_final_price"] = str(final_price)
    request.session["subscription_coupon_code"] = coupon_code

    PAYPAL_API_BASE = get_paypal_base_url()
    TOKEN_URL = f"{PAYPAL_API_BASE}/v1/oauth2/token"
    SUBSCRIPTION_URL = f"{PAYPAL_API_BASE}/v1/billing/subscriptions"
    auth = (client_id, secret_key)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials"}
    import requests
    token_response = requests.post(TOKEN_URL, auth=auth, data=data, headers=headers)
    if token_response.status_code != 200:
        messages.error(request, "Failed to authenticate with PayPal.")
        return redirect("subscription_pricing")
    access_token = token_response.json().get("access_token")
    subscription_data = {
        "plan_id": subscription_plan.paypal_plan_id,
        "application_context": {
            "brand_name": "AI Farming Reports",
            "return_url": request.build_absolute_uri(reverse('payment_success')),
            "cancel_url": request.build_absolute_uri(reverse('subscription_pricing'))
        }
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
    subscription_response = requests.post(SUBSCRIPTION_URL, json=subscription_data, headers=headers)
    if subscription_response.status_code != 201:
        messages.error(request, f"Failed to create PayPal subscription. Response: {subscription_response.text}")
        return redirect("subscription_pricing")
    subscription = subscription_response.json()
    approval_url = next(link["href"] for link in subscription["links"] if link["rel"] == "approve")
    if subscription_plan.duration == "monthly":
        next_billing_date = timezone.now() + timedelta(days=30)
    elif subscription_plan.duration == "annual":
        next_billing_date = timezone.now() + timedelta(days=365)
    else:
        next_billing_date = timezone.now()
    Subscription.objects.create(
        user=request.user,
        plan=subscription_plan,
        subscription_id=subscription["id"],
        status="active",
        next_billing_date=next_billing_date
    )
    return redirect(approval_url)

@login_required
def cancel_subscription(request, subscription_id):
    subscription = get_object_or_404(Subscription, subscription_id=subscription_id, user=request.user)
    if subscription.status == "active":
        subscription.status = "canceled"
        subscription.save()
        messages.success(
            request, 
            f"Your subscription has been canceled. You can continue using the service until {subscription.next_billing_date.strftime('%B %d, %Y')}."
        )
    else:
        messages.warning(request, "This subscription is already canceled or expired.")
    return redirect("dashboard")



@login_required
def subscription_renewal(request):
    # Placeholder for webhook-triggered subscription renewal logic:
    messages.info(request, "Subscription renewed successfully.")
    return redirect("dashboard")

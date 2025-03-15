# monetization/views/payment_views.py

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.utils.timezone import now
from django.db import transaction, IntegrityError
from decimal import Decimal
from datetime import timedelta
import os
import requests
import logging

from monetization.models import AIReport, Payment, Order, ReportRequest, Subscription
from monetization.services.paypal_service import get_paypal_credentials, get_paypal_base_url
from monetization.services.email_service import send_order_email, send_report_email
from monetization.services.pdf_generator import generate_pdf

logger = logging.getLogger(__name__)

def process_payment(request):
    if request.method == "POST":
        client_id, secret_key = get_paypal_credentials()
        if not client_id:
            messages.error(request, "PayPal credentials not found.")
            return redirect("checkout")
        amount = Decimal(request.POST.get("amount"))
        payment_type = request.POST.get("payment_type", "one_time")
        coupon_code = request.POST.get("coupon_code", "").strip()
        user = request.user
        if coupon_code:
            from monetization.models import Coupon, UsedCoupon
            coupon = Coupon.objects.filter(code=coupon_code, is_active=True).first()
            if coupon and coupon.is_valid:
                discount = (coupon.discount_percent / Decimal("100.00")) * amount
                amount -= discount
                messages.success(request, f"Coupon applied: {coupon.discount_percent}% off!")
                UsedCoupon.objects.create(user=user, coupon=coupon)
            else:
                messages.error(request, "Invalid or expired coupon.")
                return redirect("checkout")
        PAYPAL_API_BASE = get_paypal_base_url()
        TOKEN_URL = f"{PAYPAL_API_BASE}/v1/oauth2/token"
        ORDER_URL = f"{PAYPAL_API_BASE}/v2/checkout/orders"
        auth = (client_id, secret_key)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "client_credentials"}
        token_response = requests.post(TOKEN_URL, auth=auth, data=data, headers=headers)
        if token_response.status_code != 200:
            messages.error(request, "Failed to authenticate with PayPal.")
            return redirect("checkout")
        access_token = token_response.json().get("access_token")
        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [
                {"amount": {"currency_code": "USD", "value": f"{amount:.2f}"}}
            ],
            "application_context": {
                "return_url": request.build_absolute_uri(reverse('payment_success')),
                "cancel_url": request.build_absolute_uri(reverse('checkout'))
            }
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
        order_response = requests.post(ORDER_URL, json=order_data, headers=headers)
        if order_response.status_code != 201:
            messages.error(request, "Failed to create PayPal order.")
            return redirect("checkout")
        order_json = order_response.json()
        approval_url = next(link["href"] for link in order_json["links"] if link["rel"] == "approve")
        # For donation payments, DO NOT create Payment/Donation records here.
        if payment_type != "donation":
            Payment.objects.create(
                user=user,
                amount=amount,
                payment_method="paypal",
                payment_type=payment_type,
                status="pending",
                transaction_id=order_json["id"],
                discount_code=coupon_code if coupon_code else None
            )
        # For donations, let donation_views.py handle record creation after capture.
        return redirect(approval_url)
    else:
        return redirect("checkout")


def payment_success(request):
    """
    Handle both subscription and one-time payment success.
    We first check for a subscription_id query parameter.
    If found, we update the subscription and return immediately,
    skipping the one-time payment capture flow.
    """
    # --- Subscription branch ---
    subscription_id = request.GET.get("subscription_id")
    if subscription_id:
        subscription = Subscription.objects.filter(subscription_id=subscription_id).first()
        if subscription:
            # If the subscription was canceled before, reactivate it
            if subscription.status == "canceled":
                subscription.status = "active"
                messages.success(request, "Your subscription has been reactivated!")
            else:
                messages.info(request, "Your subscription is now active!")
            # Update next billing date according to plan duration
            if subscription.plan.duration == "monthly":
                subscription.next_billing_date = now() + timedelta(days=30)
            else:  # assuming annual
                subscription.next_billing_date = now() + timedelta(days=365)
            subscription.save()

            # Create a subscription order if not already present.
            order = Order.objects.filter(order_type="subscription", subscription=subscription).first()
            if not order:
                try:
                    order = Order.objects.create(
                        user=request.user,
                        subscription=subscription,  # Link the subscription
                        payment=None,              # Not linked to a one-time payment
                        order_type="subscription",
                        report_request=None,
                        total_amount=subscription.plan.price,
                        currency="USD",  # adjust if needed
                        order_status="completed"
                    )
                    # Refresh to pick up auto-generated fields (order_number, etc.)
                    order.refresh_from_db()
                except IntegrityError:
                    order = Order.objects.filter(order_type="subscription", subscription=subscription).first()

            send_order_email(order, request.user)
        return render(request, 'monetization/payment_success.html', {
            "status": "completed",
            "report_url": None
        })

    # --- One-time payment branch ---
    order_id_param = request.GET.get("token")
    client_id, secret_key = get_paypal_credentials()
    if not client_id:
        return render(request, 'monetization/report_success.html', {"error": "PayPal credentials not found."})

    PAYPAL_API_BASE = get_paypal_base_url()
    TOKEN_URL = f"{PAYPAL_API_BASE}/v1/oauth2/token"
    CAPTURE_URL = f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id_param}/capture"

    auth = (client_id, secret_key)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials"}
    token_response = requests.post(TOKEN_URL, auth=auth, data=data, headers=headers)
    if token_response.status_code != 200:
        return render(request, 'monetization/report_success.html', {"error": "Failed to authenticate with PayPal."})
    access_token = token_response.json().get("access_token")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
    capture_response = requests.post(CAPTURE_URL, headers=headers)
    if capture_response.status_code != 201:
        return render(request, 'monetization/report_success.html', {"error": "Payment capture failed."})
    capture_data = capture_response.json()
    transaction_id = capture_data["id"]
    status_str = capture_data["status"]

    payment = Payment.objects.filter(transaction_id=order_id_param).first()
    if payment:
        payment.status = "completed" if status_str == "COMPLETED" else "failed"
        payment.transaction_id = transaction_id
        payment.save()

    # Create one-time payment order if not already present
    order = Order.objects.filter(payment=payment, order_type="one_time").first()
    if not order:
        try:
            order = Order.objects.create(
                user=request.user,
                payment=payment,
                order_type="one_time",
                report_request=None,
                total_amount=payment.amount,
                discount_code=payment.discount_code,
                currency=payment.currency,
                order_status="completed"
            )
            request.session["order_id"] = order.id
        except IntegrityError:
            order = Order.objects.filter(payment=payment, order_type="one_time").first()

    send_order_email(order, request.user)

    # Optional: Process PDF report generation if a report request exists
    report_url = None
    report_request_id = request.session.get("report_request_id")
    if report_request_id and payment and payment.status == "completed":
        try:
            report_request = ReportRequest.objects.get(id=report_request_id)
            report_data = report_request.report_data or {}
            pdf_path = generate_pdf(
                report_request,
                predictions=report_data.get("predictions", {}),
                crop_details=report_data.get("crop_details", []),
                recommended_crops=report_data.get("recommended_crops", []),
                risk_assessment=report_data.get("risk_assessment", ""),
                mitigation_strategies=report_data.get("mitigation_strategies", ""),
                ai_alerts=report_data.get("ai_alerts", []),
                next_best_action=report_data.get("next_best_action", ""),
                historical_weather=report_data.get("historical_weather", {}),
                regional_avg_yield=report_data.get("regional_avg_yield", {}),
                user_data=report_data.get("user_data", {}),
                future_climate=report_data.get("future_climate", {}),
                rotation_plan=report_data.get("rotation_plan", "")
            )
            relative_path = os.path.relpath(pdf_path, settings.MEDIA_ROOT)
            ai_report = AIReport.objects.create(
                user=request.user,
                report_file=relative_path,
                payment=payment,
                status="completed"
            )
            send_report_email(pdf_path, request.user, report_request.location, None)
            report_url = ai_report.report_file.url
            # Clear the report request from session
            del request.session["report_request_id"]
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
    return render(request, 'monetization/payment_success.html', {
        "status": payment.status if payment else "failed",
        "report_url": report_url
    })

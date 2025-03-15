# monetization/views/donation_views.py
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.contrib import messages
from decimal import Decimal
from django.urls import reverse
import requests

from monetization.models import DonationOrder, Payment, Donation, Order
from monetization.services.paypal_service import get_paypal_credentials, get_paypal_base_url
from monetization.services.email_service import send_order_email


@login_required
def donation_page(request):
    if request.method == "POST":
        amount_str = request.POST.get("amount")
        message_text = request.POST.get("message", "")
        try:
            amount = Decimal(amount_str)
        except:
            messages.error(request, "Invalid amount.")
            return redirect("donation_page")
        request.session["donation_amount"] = str(amount)
        request.session["donation_message"] = message_text
        return redirect("process_donation")
    return render(request, "monetization/donation_page.html")


@login_required
def process_donation(request):
    donation_amount_str = request.session.get("donation_amount")
    donation_message = request.session.get("donation_message", "")
    if not donation_amount_str:
        messages.error(request, "No donation amount found.")
        return redirect("donation_page")
    try:
        amount = Decimal(donation_amount_str)
    except:
        messages.error(request, "Invalid donation amount.")
        return redirect("donation_page")
    client_id, secret_key = get_paypal_credentials()
    if not client_id:
        messages.error(request, "PayPal credentials not found.")
        return redirect("donation_page")
    PAYPAL_API_BASE = get_paypal_base_url()
    TOKEN_URL = f"{PAYPAL_API_BASE}/v1/oauth2/token"
    ORDER_URL = f"{PAYPAL_API_BASE}/v2/checkout/orders"
    auth = (client_id, secret_key)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials"}
    token_response = requests.post(TOKEN_URL, auth=auth, data=data, headers=headers)
    if token_response.status_code != 200:
        messages.error(request, "Failed to authenticate with PayPal.")
        return redirect("donation_page")
    access_token = token_response.json().get("access_token")
    order_data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {"amount": {"currency_code": "USD", "value": f"{amount:.2f}"}}
        ],
        "application_context": {
            "return_url": request.build_absolute_uri(reverse('donation_success')),
            "cancel_url": request.build_absolute_uri(reverse('donation_page'))
        }
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
    order_response = requests.post(ORDER_URL, json=order_data, headers=headers)
    if order_response.status_code != 201:
        messages.error(request, "Failed to create PayPal donation order.")
        return redirect("donation_page")
    order = order_response.json()
    approval_url = next(link["href"] for link in order["links"] if link["rel"] == "approve")
    Payment.objects.create(
        user=request.user if request.user.is_authenticated else None,
        amount=amount,
        payment_method="paypal",
        payment_type="donation",
        status="pending",
        transaction_id=order["id"],
        notes=donation_message
    )
    Donation.objects.create(
        user=request.user if request.user.is_authenticated else None,
        amount=amount,
        message=donation_message
    )
    del request.session["donation_amount"]
    del request.session["donation_message"]
    return redirect(approval_url)



@login_required
def donation_success(request):
    token = request.GET.get("token")

    # Retrieve the payment record
    payment = Payment.objects.filter(transaction_id=token, payment_type="donation").first()

    if not payment:
        messages.error(request, "Donation payment not found.")
        return redirect("donation_page")

    # Ensure payment is not already processed
    if payment.status == "completed":
        messages.info(request, "Your donation was already processed.")
        return redirect("landing_page")

    # Mark the payment as completed
    payment.status = "completed"
    payment.save()

    # Check if a donation order already exists using the DonationOrder model
    existing_order = DonationOrder.objects.filter(payment=payment).first()
    if not existing_order:
        try:
            donation_order = DonationOrder.objects.create(
                user=payment.user,
                payment=payment,
                total_amount=payment.amount,
                currency="USD",
                order_status="completed"
            )
            send_order_email(donation_order, payment.user)
        except IntegrityError:
            messages.warning(request, "This donation order has already been recorded.")
            return redirect("landing_page")
    else:
        messages.info(request, "Donation order already exists.")

    messages.success(request, "Thank you for your donation! Order confirmation sent.")
    return redirect("landing_page")

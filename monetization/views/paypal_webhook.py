# monetization/views/paypal_webhook.py
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import now
from monetization.models import Subscription, Payment, PayPalConfig

logger = logging.getLogger(__name__)

@csrf_exempt
def paypal_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)
    try:
        webhook_data = json.loads(request.body.decode("utf-8"))
        event_type = webhook_data.get("event_type", "")
        resource = webhook_data.get("resource", {})
        logger.info(f"Received PayPal Webhook: {event_type}")
        subscription_id = resource.get("id", None)
        status_str = resource.get("status", "").lower()
        payer_email = resource.get("subscriber", {}).get("email_address", None)
        transaction_id = resource.get("billing_info", {}).get("last_payment", {}).get("amount", {}).get("value", None)
        if "BILLING.SUBSCRIPTION" in event_type:
            return handle_subscription_event(event_type, subscription_id, status_str, payer_email)
        elif "CHECKOUT.ORDER" in event_type or "PAYMENT.CAPTURE" in event_type:
            return handle_payment_event(event_type, transaction_id, status_str, payer_email)
        logger.info(f"Unhandled event type: {event_type}")
        return JsonResponse({"message": "Event received but not processed"}, status=200)
    except Exception as e:
        logger.error(f"Webhook Error: {str(e)}")
        return JsonResponse({"error": "Webhook processing error"}, status=500)

def handle_subscription_event(event_type, subscription_id, status_str, payer_email):
    try:
        subscription = Subscription.objects.filter(subscription_id=subscription_id).first()
        if not subscription:
            logger.warning(f"Subscription ID {subscription_id} not found")
            return JsonResponse({"error": "Subscription not found"}, status=404)
        if "ACTIVATED" in event_type:
            subscription.status = "active"
        elif "CANCELLED" in event_type:
            subscription.status = "canceled"
        elif "SUSPENDED" in event_type:
            subscription.status = "paused"
        elif "EXPIRED" in event_type:
            subscription.status = "expired"
        subscription.save()
        logger.info(f"Subscription {subscription_id} updated to {subscription.status}")
        return JsonResponse({"message": f"Subscription {subscription_id} updated"}, status=200)
    except Exception as e:
        logger.error(f"Error updating subscription: {str(e)}")
        return JsonResponse({"error": "Failed to update subscription"}, status=500)

def handle_payment_event(event_type, transaction_id, status_str, payer_email):
    try:
        payment = Payment.objects.filter(transaction_id=transaction_id).first()
        if not payment:
            logger.warning(f"Payment Transaction {transaction_id} not found")
            return JsonResponse({"error": "Payment not found"}, status=404)
        if "COMPLETED" in event_type:
            payment.status = "completed"
        elif "DENIED" in event_type:
            payment.status = "failed"
        elif "REFUNDED" in event_type:
            payment.status = "failed"
        payment.save()
        logger.info(f"Payment {transaction_id} updated to {payment.status}")
        return JsonResponse({"message": f"Payment {transaction_id} updated"}, status=200)
    except Exception as e:
        logger.error(f"Error updating payment: {str(e)}")
        return JsonResponse({"error": "Failed to update payment"}, status=500)

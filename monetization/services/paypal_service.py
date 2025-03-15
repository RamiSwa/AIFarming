# monetization/services/paypal_service.py
from monetization.models import PayPalConfig

def get_paypal_base_url():
    paypal_config = PayPalConfig.objects.filter(environment="sandbox").first()
    return "https://api-m.sandbox.paypal.com" if paypal_config and paypal_config.environment == "sandbox" else "https://api-m.paypal.com"

def get_paypal_credentials():
    paypal_config = PayPalConfig.objects.filter(environment="sandbox").first()
    if not paypal_config:
        return None, None
    return paypal_config.client_id, paypal_config.secret_key

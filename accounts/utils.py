from .models import Notification
from django.conf import settings  # ✅ Import custom user model

def send_notification(user, message, notification_type="system"):
    """
    Create and send a notification to a user.
    Example usage:
        send_notification(user, "Your payment failed", "payment")
    """
    Notification.objects.create(user=user, message=message, notification_type=notification_type)

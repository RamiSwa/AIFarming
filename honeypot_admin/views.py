from django.shortcuts import render
from .models import FakeAdminAccessLog
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseForbidden



# Setup logger
logger = logging.getLogger(__name__)

def fake_admin_login(request):
    """ Fake admin login page that logs intruder attempts """

    if request.method == "POST":
        # CSRF token is now included
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")

        ip = request.META.get('REMOTE_ADDR', 'Unknown')
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')

        # Save attempt to database
        FakeAdminAccessLog.objects.create(ip_address=ip, user_agent=user_agent)

        # Log the attempt
        logger.warning(f"🚨 Fake Admin Attempt! IP: {ip}, User-Agent: {user_agent}")

        # Send alert email
        # Send email alert
        send_mail(
            subject="🚨 Fake Admin Attempt Detected! - AI FARMING ",
            message=f"Someone tried to access the fake admin page.\n\nIP: {ip}\nUser-Agent: {user_agent}",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[settings.CONTACT_NOTIFICATION_EMAIL],
            fail_silently=False,  # If email fails, it will raise an error
        )
        
        # Show fake "invalid credentials" message
        return HttpResponseForbidden("Invalid credentials", status=403)

    # Respond with a fake "invalid credentials" message
    return render(request, 'honeypot_admin/fake_admin.html', status=401)

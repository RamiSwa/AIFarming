from django.shortcuts import redirect
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponseForbidden

class RestrictAdminAccessMiddleware(MiddlewareMixin):
    """Middleware to restrict access to Django Admin."""
    def process_request(self, request):
        if request.path.startswith("/secure-dashboard/"):  # ✅ Adjust this if needed
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)  # ✅ Send non-auth users to login
            if not request.user.is_superuser:
                return redirect("/")  # ✅ Redirect regular users to homepage
        return None  # ✅ Allow normal request processing


class BlockWordPressScansMiddleware:
    """Middleware to block bots scanning for WordPress paths."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        blocked_paths = [
            "/wp-admin/", "/wp-login.php", "/wordpress/", 
            "/wp-content/", "/wp-includes/"
        ]
        if any(request.path.startswith(bp) for bp in blocked_paths):
            return HttpResponseForbidden("🚫 Forbidden: WordPress is not installed.")
        return self.get_response(request)

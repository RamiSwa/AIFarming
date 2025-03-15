from django.shortcuts import redirect
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

class RestrictAdminAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith("/secure-dashboard/"):  # ✅ Adjust this if needed
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)  # ✅ Send non-auth users to login
            if not request.user.is_superuser:
                return redirect("/")  # ✅ Redirect regular users to homepage

        return None  # ✅ Allow normal request processing

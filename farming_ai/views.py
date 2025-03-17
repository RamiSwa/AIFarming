from django.shortcuts import render
from django.http import HttpResponseNotFound

def custom_404_view(request, exception=None):
    """Force Django to use the custom 404 template."""
    response = render(request, "pages/404.html", status=404)
    response["X-Frame-Options"] = "DENY"  # ✅ Prevent clickjacking
    return response

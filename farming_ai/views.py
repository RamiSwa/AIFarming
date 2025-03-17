from django.shortcuts import render
from django.http import HttpResponse

import logging

logger = logging.getLogger(__name__)

def custom_404_view(request, exception=None):
    try:
        response = render(request, "/templates/pages/404.html", status=404)
        response["X-Frame-Options"] = "DENY"
        return response
    except Exception as e:
        logger.error("Error rendering 404 page: %s", e)
        # Optionally return a simple fallback response
        return HttpResponse("Page not found", status=404)

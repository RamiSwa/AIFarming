from django.shortcuts import render

def custom_404_view(request, exception):
    """Handles 404 errors with a custom template."""
    return render(request, "/templates/pages/404.html", status=404)

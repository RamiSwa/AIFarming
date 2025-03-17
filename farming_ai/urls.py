"""
URL configuration for farming_ai project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""



from django.conf import settings
from django.conf.urls.static import static 
from django.contrib import admin
from django.urls import path, include
from monetization.admin import monetization_admin_site  



# ✅ Correct 404 handler
handler404 = "farming_ai.views.custom_404_view"

urlpatterns = [
    # ✅ Fake Admin Trap (Honeypot)
    path("admin/", include("honeypot_admin.urls")),

    # ✅ Secure Admin Panel with 2FA
    path("secure-dashboard/", admin.site.urls),
    path("secure-dashboard/logout/", include("django.contrib.auth.urls")),
    path("monetization-admin/", monetization_admin_site.urls),  # ✅ Monetization Admin Panel

    # ✅ User Authentication
    path("accounts/", include("accounts.urls")),  

    # ✅ Other App URLs
    path("weather/", include("weather.urls")), 
    path("soil/", include("soil.urls")), 
    path("recommendations/", include("recommendations.urls")), 
    path("", include("pages.urls")),
    path("monetization/", include("monetization.urls")),
]

# ✅ Serve media files in development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

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

from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from monetization.admin import monetization_admin_site  


urlpatterns = [
    # 2FA routes
    # Fake Admin Trap
    path('admin/', include('honeypot_admin.urls')),

    # ✅ Secure Admin Panel with 2FA
    path("secure-dashboard/", admin.site.urls),
  # ✅ Correct 2FA login
    path("secure-dashboard/logout/", include("django.contrib.auth.urls")),
    path("monetization-admin/", monetization_admin_site.urls),  # ✅ Monetization Admin Panel



    # Regular user authentication
    path("accounts/", include("accounts.urls")),  

    # Other App URLs
    path("weather/", include("weather.urls")), 
    path("soil/", include("soil.urls")), 
    path("recommendations/", include("recommendations.urls")), 
    path("", include("pages.urls")),
    path("monetization/", include("monetization.urls")),
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.urls import path
from .views import fake_admin_login

urlpatterns = [
    path("", fake_admin_login, name="fake_admin"),
]

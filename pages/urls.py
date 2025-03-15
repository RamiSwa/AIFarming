from django.urls import path
from .views import landing_page_view, contact_view, blog_list_view, about_page_view, privacy_policy_view, subscribe_view, blog_detail_view

urlpatterns = [
    path("", landing_page_view, name="landing_page"),
    path("contact/", contact_view, name="contact_page"),
    path("blog/", blog_list_view, name="blog_list"),
    path("blog/<slug:slug>/", blog_detail_view, name="blog_detail"),
    path("about/", about_page_view, name="about_page"),
    path("privacy-policy/", privacy_policy_view, name="privacy_policy"),
    path('subscribe/', subscribe_view, name='subscribe'),


]

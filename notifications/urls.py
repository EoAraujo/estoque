from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("vapid-key/", views.vapid_public_key, name="vapid_key"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("unsubscribe/", views.unsubscribe, name="unsubscribe"),
    path("test/", views.test_push, name="test_push"),
]

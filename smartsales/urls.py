from django.urls import path
from .views import MeView, RegisterView, LoginView, HealthCheckView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/",    LoginView.as_view(),    name="login"),
    path("me/",       MeView.as_view(),       name="me"),
    path("health/",   HealthCheckView.as_view(), name="health"),
]

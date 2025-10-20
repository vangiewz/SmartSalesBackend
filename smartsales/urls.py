from django.urls import path, include
from .views import MeView, RegisterView, LoginView, HealthCheckView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/",    LoginView.as_view(),    name="login"),
    path("me/",       MeView.as_view(),       name="me"),
    path("health/",   HealthCheckView.as_view(), name="health"),
    
    # Módulo de recuperación de contraseña
    path(
        "password-reset/",
        include(("smartsales.RecuperarContrasena.urls", "recuperar_contrasena"), namespace="password_reset")
    ),
]

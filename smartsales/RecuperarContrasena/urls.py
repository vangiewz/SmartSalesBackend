"""
URLs para recuperación de contraseña - SIMPLE.
"""
from django.urls import path
from .views import PasswordResetRequestView, PasswordResetConfirmView

app_name = "recuperar_contrasena"

urlpatterns = [
    path("request/", PasswordResetRequestView.as_view(), name="request"),
    path("confirm/", PasswordResetConfirmView.as_view(), name="confirm"),
]

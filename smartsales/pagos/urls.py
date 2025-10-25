from django.urls import path
from .views import ObtenerPublicKeyView, IniciarCheckoutView, ConfirmarPagoView, StripeWebhookView

urlpatterns = [
    path("public-key/", ObtenerPublicKeyView.as_view(), name="stripe-public-key"),
    path("iniciar-checkout/", IniciarCheckoutView.as_view(), name="iniciar-checkout"),
    path("confirmar-pago/", ConfirmarPagoView.as_view(), name="confirmar-pago"),
    path("webhook-stripe/", StripeWebhookView.as_view(), name="webhook-stripe"),
]

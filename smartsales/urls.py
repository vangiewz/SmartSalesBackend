from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import MeView, RegisterView, LoginView

urlpatterns = [
    # Registro con rol Cliente por defecto (email-only)
    path("register/", RegisterView.as_view(), name="register"),

    # Login email+password (tokens + perfil + roles)
    path("login/", LoginView.as_view(), name="login"),

    # Endpoints estándar de SimpleJWT (opcional)
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Perfil protegido
    path("me/", MeView.as_view(), name="me"),
]

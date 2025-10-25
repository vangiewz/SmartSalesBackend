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

    # Módulo de roles de usuario
    path("rolesusuario/",   include(("smartsales.rolesusuario.urls",   "rolesusuario"),   namespace="rolesusuario")),

    # Módulo de gestión de usuarios (solo Admin)
    path("gestionusuario/", include(("smartsales.gestionusuario.urls", "gestionusuario"), namespace="gestionusuario")),

    # Reportes con IA (tu rama ReportesIA)
    path(
        "ai-reports/",
        include(("smartsales.ai_reports.urls", "ai_reports"), namespace="ai_reports")
    ),

    # Cambios que estaban en main
    # Módulo de gestión de productos (Admin y Vendedor)
    path("gestionproducto/", include(("smartsales.gestionproducto.urls", "gestionproducto"), namespace="gestionproducto")),

    # Módulo de listado completo de productos para dashboard (Admin y Vendedor)
    path("listadoproductos/", include(("smartsales.listadoproductos.urls", "listadoproductos"), namespace="listadoproductos")),
    
    # Módulo de gestión de direcciones
    path("direcciones/", include(("smartsales.direcciones.urls", "direcciones"), namespace="direcciones")),
    
    # Módulo de procesamiento de pagos con Stripe
    path("pagos/", include(("smartsales.pagos.urls", "pagos"), namespace="pagos")),
    
    # Módulo de historial de pagos
    path("historial-pagos/", include(("smartsales.historialpagos.urls", "historialpagos"), namespace="historialpagos")),
]
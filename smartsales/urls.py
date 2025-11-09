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

    # Módulo de gestión de garantías y reclamos (Técnico)
    path("garantia/", include(("smartsales.garantia.urls", "garantia"), namespace="garantia")),

    path(
        "gestionclientes/",
        include(("smartsales.gestionclientes.urls", "gestionclientes"), namespace="gestionclientes")
    ),

    path(
        "ventas-historicas/",
        include(("smartsales.ventas_historicas.urls", "ventas_historicas"), namespace="ventas_historicas")
    ),
    # Módulo de configuración del modelo de predicción (UC-25)
    path(
        "ml/",
        include(("smartsales.ml_ventas.urls", "ml_ventas"), namespace="ml_ventas")
    ),

    path(
        "carrito-voz/",
        include(("smartsales.carrito_voz.urls", "carrito_voz"), namespace="carrito_voz")
    ),

    path(
        "carrito-voz/",
        include(("smartsales.carrito_voz.urls", "carrito_voz"), namespace="carrito_voz")
    ),

    path(
        "bitacora/",
        include(("smartsales.bitacora.urls", "bitacora"), namespace="bitacora")
    ),

    # Módulo de notificaciones
    path(
        "notificaciones/",
        include(("smartsales.notificaciones.urls", "notificaciones"), namespace="notificaciones")
    ),

]
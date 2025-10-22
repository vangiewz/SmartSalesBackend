from rest_framework.permissions import BasePermission

class IsAnalystOrAdmin(BasePermission):
    """
    Permite solo usuarios con rol 'Analista' o 'Administrador'.
    Si manejas roles en otro lado, adapta esta verificación.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        # Ajusta a tu lógica real de roles:
        roles = getattr(user, 'roles', [])  # placeholder
        # Si usas JWT/headers añade validación aquí
        names = {str(r).lower() for r in roles} if roles else set()
        return ('analista' in names) or user.is_staff or user.is_superuser

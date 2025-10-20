from django.urls import path
from .views import (
    UsuariosListView,
    UsuarioPerfilUpdateView,
    UsuarioRolesView,      # PUT/POST en el mismo path
    UsuarioRolDeleteView,  # DELETE con rol_id
    UsuarioDeleteView,     # DELETE usuario
)

urlpatterns = [
    path("usuarios/", UsuariosListView.as_view(), name="gu_usuarios_list"),
    path("usuarios/<uuid:user_id>/perfil", UsuarioPerfilUpdateView.as_view(), name="gu_usuario_perfil"),
    path("usuarios/<uuid:user_id>/roles", UsuarioRolesView.as_view(), name="gu_usuario_roles"),          # PUT/POST
    path("usuarios/<uuid:user_id>/roles/<int:rol_id>", UsuarioRolDeleteView.as_view(), name="gu_usuario_rol_del"),
    path("usuarios/<uuid:user_id>", UsuarioDeleteView.as_view(), name="gu_usuario_delete"),
]

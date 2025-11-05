from django.contrib import admin
from .models import Usuario, UsuarioRol

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "correo", "telefono")
    readonly_fields = ("id",)
    search_fields = ("nombre", "correo", "telefono")


@admin.register(UsuarioRol)
class UsuarioRolAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "rol_id", "role")
    search_fields = ("usuario__nombre", "role")
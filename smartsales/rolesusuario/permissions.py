from typing import Optional, Sequence, Tuple, Union
from django.db import connection
from rest_framework.permissions import BasePermission

ROLE_ADMIN_NAME   = "Administrador"
ROLE_VENDEDOR_NAME= "Vendedor"
ROLE_ANALISTA_NAME= "Analista"
ROLE_USUARIO_NAME = "Usuario"

ROLE_ADMIN_ID = 2  # atajo según semilla

def _fetch_role_id_by_name(role_name: str) -> Optional[int]:
    if not role_name:
        return None
    with connection.cursor() as cur:
        cur.execute("SELECT id FROM roles WHERE lower(nombre)=lower(%s) LIMIT 1", [role_name])
        r = cur.fetchone()
    return r[0] if r else None

def _user_has_role_id(user_id, role_id: int) -> bool:
    if not user_id or role_id is None:
        return False
    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM rolesusuario WHERE usuario_id=%s AND rol_id=%s LIMIT 1",
            [user_id, role_id],
        )
        return cur.fetchone() is not None

def user_has_role(user_id, role: Union[int, str]) -> bool:
    if isinstance(role, int):
        return _user_has_role_id(user_id, role)
    if isinstance(role, str):
        rid = _fetch_role_id_by_name(role)
        return _user_has_role_id(user_id, rid) if rid is not None else False
    return False

def user_has_any_role(user_id, roles: Sequence[Union[int, str]]) -> bool:
    if not roles:
        return False
    resolved_ids = []
    for r in roles:
        if isinstance(r, int):
            resolved_ids.append(r)
        else:
            rid = _fetch_role_id_by_name(str(r))
            if rid is not None:
                resolved_ids.append(rid)
    if not resolved_ids:
        return False
    with connection.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM rolesusuario WHERE usuario_id=%s AND rol_id=ANY(%s) LIMIT 1",
            [user_id, resolved_ids],
        )
        return cur.fetchone() is not None

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        uid = getattr(request.user, "id", None)
        return user_has_role(uid, ROLE_ADMIN_ID) or user_has_role(uid, ROLE_ADMIN_NAME)

class IsVendedorRole(BasePermission):
    def has_permission(self, request, view):
        uid = getattr(request.user, "id", None)
        return user_has_role(uid, ROLE_VENDEDOR_NAME)

class IsAnalistaRole(BasePermission):
    def has_permission(self, request, view):
        uid = getattr(request.user, "id", None)
        return user_has_role(uid, ROLE_ANALISTA_NAME)

class IsUsuarioRole(BasePermission):
    def has_permission(self, request, view):
        uid = getattr(request.user, "id", None)
        return user_has_role(uid, ROLE_USUARIO_NAME)

class HasAnyRole(BasePermission):
    required_roles: Tuple[Union[int, str], ...] = tuple()
    def has_permission(self, request, view):
        uid = getattr(request.user, "id", None)
        roles = getattr(view, "required_roles", self.required_roles)
        return bool(uid) and user_has_any_role(uid, roles)

def role_required(*roles: Union[int, str]) -> type:
    class _Dyn(BasePermission):
        def has_permission(self, request, view):
            uid = getattr(request.user, "id", None)
            return bool(uid) and user_has_any_role(uid, roles)
    _Dyn.__name__ = f"RoleRequired_{'_'.join(str(r) for r in roles)}"
    return _Dyn

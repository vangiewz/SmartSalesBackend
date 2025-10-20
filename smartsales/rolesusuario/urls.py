from django.urls import path
from .views import MisRolesView, CheckRoleView

urlpatterns = [
    path("me/",    MisRolesView.as_view(),  name="roles_me"),
    path("check/", CheckRoleView.as_view(), name="roles_check"),
]

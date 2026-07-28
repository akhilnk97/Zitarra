from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.admin_dashboard_view, name="admin_dashboard"),
    path("unimplemented/", views.admin_unimplemented_view, name="admin_unimplemented"),
]

from django.urls import path
from . import views

urlpatterns = [
    path("users/", views.admin_users_view, name="admin_users"),
    path("users/toggle-block/<int:user_id>/", views.admin_toggle_block_view, name="admin_toggle_block"),
]

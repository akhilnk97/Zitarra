from django.urls import path
from . import views

urlpatterns = [
    path("category/", views.admin_category_view, name="admin_category"),
    path("category/add/", views.admin_add_category_view, name="admin_add_category"),
    path("category/edit/<int:category_id>/", views.admin_edit_category_view, name="admin_edit_category"),
    path("category/delete/<int:category_id>/", views.admin_delete_category_view, name="admin_delete_category"),
    path("category/toggle-offer/<int:category_id>/", views.admin_toggle_offer_view, name="admin_toggle_offer"),
]

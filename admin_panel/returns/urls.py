from django.urls import path
from . import views

urlpatterns = [
    path('returns/', views.admin_returns_management_view, name='admin_returns'),
    path('returns/item/<int:item_id>/action/', views.admin_return_action_view, name='admin_return_action'),
]

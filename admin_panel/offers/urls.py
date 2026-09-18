from django.urls import path
from . import views

urlpatterns = [
    path('offers/', views.admin_offers_list_view, name='admin_offers'),
    path('offers/add/', views.admin_add_offer_view, name='admin_add_offer'),
    path('offers/<int:offer_id>/edit/', views.admin_edit_offer_view, name='admin_edit_offer'),
    path('offers/<int:offer_id>/toggle/', views.admin_toggle_offer_view, name='admin_toggle_offer'),
    path('offers/<int:offer_id>/delete/', views.admin_delete_offer_view, name='admin_delete_offer'),
]

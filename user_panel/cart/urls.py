from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_view, name='cart_view'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('move-to-wishlist/<int:item_id>/', views.move_to_wishlist, name='move_to_wishlist'),
    path('update/<int:item_id>/<str:action>/', views.update_quantity, name='update_quantity'),
]

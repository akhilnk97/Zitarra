from django.urls import path
from . import views


urlpatterns = [
    path("", views.shop_view, name="shop"),
    path("product/<int:product_id>/", views.product_detail_view, name="product_detail"),
]
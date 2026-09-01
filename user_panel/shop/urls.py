from django.urls import path
from . import views


urlpatterns = [
    path("", views.shop_view, name="shop"),
    path("product/<int:product_id>/", views.product_detail_view, name="product_detail"),
    path("product/<int:product_id>/review/", views.post_review_view, name="post_review"),
]
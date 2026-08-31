from django.urls import path
from . import views

urlpatterns = [
    path('order/<str:order_id>/return/', views.return_order_view, name='return_order'),
    path('order/<str:order_id>/item/<int:item_id>/return/', views.return_order_item_view, name='return_order_item'),
]

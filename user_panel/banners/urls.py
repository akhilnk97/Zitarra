from django.urls import path
from . import views

urlpatterns = [
    path('banners/click/<int:banner_id>/', views.track_banner_click_view, name='track_banner_click'),
]

from django.urls import path
from . import views

app_name = 'profiles'

urlpatterns = [
    path('', views.profile_view, name='profile'),
    path('edit/', views.profile_edit_view, name='profile_edit'),
    path('edit/send-otp/', views.profile_send_otp_view, name='profile_send_otp'),
    path('edit/resend-otp/', views.profile_resend_otp_view, name='profile_resend_otp'),
    path('addresses/save/', views.address_save_view, name='address_save'),
    path('addresses/delete/<int:address_id>/', views.address_delete_view, name='address_delete'),
    path('password/', views.profile_password_view, name='profile_password'),
    path('password/send-otp/', views.profile_password_send_otp_view, name='profile_password_send_otp'),
]

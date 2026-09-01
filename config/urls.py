from django.contrib import admin
from django.urls import path, include, re_path
from user_panel.authentication import views as auth_views
from user_panel.profiles import views as profiles_views
from user_panel.home.views import custom_404_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/',       admin.site.urls),
    path('accounts/login/', auth_views.login_view, name='account_login'),
    path('accounts/',    include('allauth.urls')),
    path('',             include('user_panel.authentication.urls')),
    path('',             include('user_panel.home.urls')),
    path('profile/',     include('user_panel.profiles.urls')),
    path('addresses/',   profiles_views.addresses_view, name='addresses'),
    path('shop/',        include('user_panel.shop.urls')),
    path('cart/',        include('user_panel.cart.urls')),
    path('wishlist/',    include('user_panel.wishlist.urls')),
    path('',             include('user_panel.orders.urls')),
    path('',             include('user_panel.coupons.urls')),
    path('',             include('user_panel.returns.urls')),
    path('',             include('user_panel.wallet.urls')),
    path('admin-panel/', include('admin_panel.authentication.urls')),
    path('admin-panel/', include('admin_panel.dashboard.urls')),
    path('admin-panel/', include('admin_panel.users.urls')),
    path('admin-panel/', include('admin_panel.category.urls')),
    path('admin-panel/', include('admin_panel.products.urls')),
    path('admin-panel/', include('admin_panel.orders.urls')),
    path('admin-panel/', include('admin_panel.coupons.urls')),
    path('admin-panel/', include('admin_panel.returns.urls')),
    path('admin-panel/', include('admin_panel.sales.urls')),
    path('admin-panel/', include('admin_panel.brands.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r'^.*$', custom_404_view),
]

handler404 = 'user_panel.home.views.custom_404_view'


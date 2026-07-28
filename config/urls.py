from django.contrib import admin
from django.urls import path, include, re_path
from profiles import views as profiles_views
from user_panel.views import custom_404_view
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/',       admin.site.urls),
    path('accounts/',    include('allauth.urls')),
    path('',             include('accounts.urls')),
    path('',             include('user_panel.urls')),
    path('profile/',     include('profiles.urls')),
    path('addresses/',   profiles_views.addresses_view, name='addresses'),
    path('admin-panel/', include('admin_panel.authentication.urls')),
    path('admin-panel/', include('admin_panel.dashboard.urls')),
    path('admin-panel/', include('admin_panel.users.urls')),
    path('admin-panel/', include('admin_panel.category.urls')),
    path('admin-panel/', include('admin_panel.products.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    re_path(r'^.*$', custom_404_view),
]

handler404 = 'user_panel.views.custom_404_view'


from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from app1.views import (
    admin_dashboard_view,
    admin_login_view,
    candidate_register_view,
    company_register_view,
    home,
    password_reset_view,
    signin_view,
)

urlpatterns = [
    path('', home, name='home'),
    path('signin', signin_view, name='signin'),
    path('password-reset', password_reset_view, name='password_reset'),
    path('candidate/register', candidate_register_view, name='candidate_register'),
    path('company/register', company_register_view, name='company_register'),
    path('admin/login', admin_login_view, name='admin_login'),
    path('admin/dashboard', admin_dashboard_view, name='admin_dashboard'),
    path('admin/', admin.site.urls),
]

if settings.HAS_ALLAUTH:
    urlpatterns.append(path('auth/', include('allauth.urls')))

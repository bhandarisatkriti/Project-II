"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
# from django.urls import path

# urlpatterns = [
#     path('admin/', admin.site.urls),
# ]
# apps/accounts/urls.py
#from django.urls import path

# config/urls.py
"""
URL configuration for SkillSync AI project
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from home.views import (
    LoginPageView,
    RegisterPageView,
    LogoutPageView,
    SeekerDashboardView,
    EmployerDashboardView,
    GoogleAuthStartView,
    GoogleAuthCallbackView,
)

# Remove this line if it exists:
# from . import views  # DELETE THIS LINE

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),
    
    # Home page - using TemplateView for landing page
    path('', TemplateView.as_view(template_name='landingpage.html'), name='home'),

    # Frontend pages
    path('login.html', LoginPageView.as_view(), name='login_page'),
    path('register.html', RegisterPageView.as_view(), name='register_page'),
    path('logout/', LogoutPageView.as_view(), name='logout_page'),
    path('google/login/', LoginPageView.as_view(), name='google_login_redirect'),
    path('google/start/', GoogleAuthStartView.as_view(), name='google_auth_start'),
    path('google/callback/', GoogleAuthCallbackView.as_view(), name='google_auth_callback'),
    path('seeker_dashboard.html', SeekerDashboardView.as_view(), name='seeker_dashboard'),
    path('employer_dashboard.html', EmployerDashboardView.as_view(), name='employer_dashboard'),
    
    # Mount API endpoints under /api/
    path('api/', include('home.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
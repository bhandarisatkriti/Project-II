from django.urls import path
from . import views

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='api_register'),
    path('auth/login/', views.LoginView.as_view(), name='api_login'),
    path('auth/profile/', views.ProfileView.as_view(), name='api_profile'),
]
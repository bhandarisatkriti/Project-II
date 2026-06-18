from django.urls import path
from . import views

urlpatterns = [
    # Job seeker CV creation routes
    path('jobseeker/create/', views.create_profile, name='create_profile'),
    path('jobseeker/<int:pk>/generate-cv/', views.generate_cv, name='generate_cv'),

    # Existing API endpoints
    path('auth/register/', views.RegisterView.as_view(), name='api_register'),
    path('auth/login/', views.LoginView.as_view(), name='api_login'),
    path('auth/profile/', views.ProfileView.as_view(), name='api_profile'),
]
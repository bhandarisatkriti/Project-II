from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [
    # =====================
    # FRONTEND PAGES
    # =====================
    path('', TemplateView.as_view(template_name='landingpage.html'), name='home'),

    path('login/', views.LoginPageView.as_view(), name='login_page'),
    path('register/', views.RegisterPageView.as_view(), name='register_page'),
    path('logout/', views.LogoutPageView.as_view(), name='logout_page'),

    path('dashboard/seeker/', views.SeekerDashboardView.as_view(), name='seeker_dashboard'),
    path('dashboard/employer/', views.EmployerDashboardView.as_view(), name='employer_dashboard'),

    # =====================
    # GOOGLE AUTH
    # =====================
    path('auth/google/start/', views.GoogleAuthStartView.as_view(), name='google_auth_start'),
    path('auth/google/callback/', views.GoogleAuthCallbackView.as_view(), name='google_auth_callback'),

    # =====================
    # API ROUTES (AUTH)
    # =====================
    path('api/auth/register/', views.RegisterView.as_view(), name='api_register'),
    path('api/auth/login/', views.LoginView.as_view(), name='api_login'),
    path('api/auth/profile/', views.ProfileView.as_view(), name='api_profile'),

    # =====================
    # API ROUTES (JOBSEEKER)
    # =====================
    path('api/jobseeker/create/', views.create_profile, name='create_profile'),
    path('api/jobseeker/<int:pk>/generate-cv/', views.generate_cv, name='generate_cv'),
]
from django.urls import path
from . import views

app_name = 'cvgen'   # ✅ REQUIRED FIX

urlpatterns = [
    path('create/', views.CreateProfileView.as_view(), name='create_profile'),
    path('<int:pk>/generate/', views.GenerateCvView.as_view(), name='generate_cv'),
]
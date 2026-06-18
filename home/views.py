import json
import os
import re
import secrets
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

# Create your views here.
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/google/callback/')
GOOGLE_AUTH_SCOPE = 'openid email profile'
GOOGLE_AUTH_BASE_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'
GOOGLE_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI)


def generate_unique_username(email):
    base = re.sub(r'[^a-zA-Z0-9_]', '', email.split('@')[0]).lower() or 'user'
    username = base
    suffix = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{suffix}"
        suffix += 1
    return username


def exchange_google_code(code):
    data = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': GOOGLE_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }
    request = Request(GOOGLE_TOKEN_URL, data=urlencode(data).encode(), headers={
        'Content-Type': 'application/x-www-form-urlencoded',
    })
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode())


def fetch_google_userinfo(access_token):
    request = Request(GOOGLE_USERINFO_URL, headers={
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
    })
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode())


class RegisterView(APIView):
    """User registration endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'User created successfully',
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """User login endpoint"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    """Get user profile"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LoginPageView(View):
    template_name = 'login.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form_data': {},
            'google_enabled': GOOGLE_ENABLED,
        })

    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request=request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('seeker_dashboard' if user.role == 'seeker' else 'employer_dashboard')

        return render(request, self.template_name, {
            'form_error': 'Invalid email or password.',
            'form_data': {'email': email},
            'google_enabled': GOOGLE_ENABLED,
        })


class RegisterPageView(View):
    template_name = 'register.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form_data': {},
            'google_enabled': GOOGLE_ENABLED,
        })

    def post(self, request):
        data = {
            'email': request.POST.get('email'),
            'username': request.POST.get('username'),
            'password': request.POST.get('password'),
            'password2': request.POST.get('password2'),
            'role': request.POST.get('role', 'seeker'),
            'phone': request.POST.get('phone', ''),
        }
        serializer = RegisterSerializer(data=data)

        if serializer.is_valid():
            user = serializer.save()
            login(request, user)
            return redirect('seeker_dashboard' if user.role == 'seeker' else 'employer_dashboard')

        error_message = ''
        for errors in serializer.errors.values():
            if isinstance(errors, (list, tuple)) and errors:
                error_message = errors[0]
                break
            if isinstance(errors, dict):
                for inner in errors.values():
                    if inner:
                        error_message = inner[0]
                        break
            if error_message:
                break

        return render(request, self.template_name, {
            'form_error': error_message or 'Registration failed.',
            'form_data': data,
            'google_enabled': GOOGLE_ENABLED,
        })


class GoogleAuthStartView(View):
    def get(self, request):
        if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
            return redirect('login_page')

        state = secrets.token_urlsafe(16)
        request.session['google_oauth_state'] = state
        query = urlencode({
            'client_id': GOOGLE_CLIENT_ID,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'response_type': 'code',
            'scope': GOOGLE_AUTH_SCOPE,
            'access_type': 'offline',
            'prompt': 'select_account',
            'state': state,
        })
        return redirect(f'{GOOGLE_AUTH_BASE_URL}?{query}')


class GoogleAuthCallbackView(View):
    def get(self, request):
        state = request.GET.get('state')
        code = request.GET.get('code')
        session_state = request.session.pop('google_oauth_state', None)

        if not code or state != session_state:
            return redirect('login_page')

        try:
            token_response = exchange_google_code(code)
            userinfo = fetch_google_userinfo(token_response['access_token'])
        except (HTTPError, KeyError, ValueError):
            return redirect('login_page')

        email = userinfo.get('email')
        name = userinfo.get('name') or email.split('@')[0]
        if not email:
            return redirect('login_page')

        user = User.objects.filter(email=email).first()
        if not user:
            username = generate_unique_username(email)
            user = User.objects.create_user(
                email=email,
                username=username,
                password=User.objects.make_random_password(),
                role='seeker',
            )

        login(request, user)
        return redirect('seeker_dashboard' if user.role == 'seeker' else 'employer_dashboard')


class LogoutPageView(View):
    def get(self, request):
        logout(request)
        return redirect('home')


class SeekerDashboardView(LoginRequiredMixin, View):
    login_url = '/login.html'

    def get(self, request):
        return render(request, 'seeker_dashboard.html', {
            'user': request.user,
        })


class EmployerDashboardView(LoginRequiredMixin, View):
    login_url = '/login.html'

    def get(self, request):
        return render(request, 'employer_dashboard.html', {
            'user': request.user,
        })

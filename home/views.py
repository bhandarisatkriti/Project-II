import io
import json
import os
import re
import secrets
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.http import HttpResponse

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, HRFlowable

# Create your views here.
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import JobSeekerProfile, User
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from .forms import JobSeekerProfileForm

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


def _build_pdf_for_profile(profile):
    """Generate a PDF bytes object for a JobSeekerProfile."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        name='NameStyle',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        spaceAfter=6,
        textColor=colors.HexColor('#0a3d62'),
    )
    contact_style = ParagraphStyle(
        name='ContactStyle',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor('#555555'),
        spaceAfter=10,
    )
    section_title_style = ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=14,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor('#10316b'),
    )
    normal_style = ParagraphStyle(
        name='NormalText',
        parent=styles['BodyText'],
        fontSize=10.5,
        leading=14,
        spaceAfter=4,
    )
    bullet_style = ParagraphStyle(
        name='BulletText',
        parent=normal_style,
        leftIndent=12,
        bulletIndent=0,
        spaceAfter=2,
    )

    story = []
    story.append(Paragraph(profile.full_name or 'Job Seeker', name_style))

    contact_parts = []
    if profile.email:
        contact_parts.append(profile.email)
    if profile.phone_number:
        contact_parts.append(profile.phone_number)
    if profile.address:
        contact_parts.append(profile.address)
    if profile.linkedin_url:
        contact_parts.append(profile.linkedin_url)
    if profile.github_url:
        contact_parts.append(profile.github_url)

    if contact_parts:
        story.append(Paragraph(' | '.join(contact_parts), contact_style))

    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#cccccc')))
    story.append(Spacer(1, 12))

    def _format_lines(raw_text):
        return [line.strip() for line in re.split(r'[\r\n]+', raw_text) if line.strip()]

    def _section_bullets(title, raw_text):
        items = _format_lines(raw_text)
        if not items:
            return []
        section = [Paragraph(title, section_title_style)]
        for item in items:
            section.append(Paragraph(f'<bullet>&bull;</bullet> {item}', bullet_style))
        return section

    summary_text = 'Professional job seeker with a strong focus on delivering value in every role.'
    if profile.skills:
        skills_list = [skill.strip() for skill in re.split(r'[\n,]+', profile.skills) if skill.strip()]
        if skills_list:
            summary_text = f"Experienced professional with skills in {skills_list[0]} and a strong record of accomplishment."

    story.append(Paragraph('Professional Summary', section_title_style))
    story.append(Paragraph(summary_text, normal_style))

    skills = [skill.strip() for skill in re.split(r'[\n,]+', profile.skills) if skill.strip()]
    if skills:
        story.append(Paragraph('Skills', section_title_style))
        story.append(Paragraph(', '.join(skills), normal_style))

    story.extend(_section_bullets('Work Experience', profile.work_experience))
    story.extend(_section_bullets('Education', profile.education))
    story.extend(_section_bullets('Projects', profile.projects))
    story.extend(_section_bullets('Certifications', profile.certifications))

    doc.build(story)
    buffer.seek(0)
    return buffer


def create_profile(request):
    """Display the job seeker profile form and save profile data."""
    if request.method == 'POST':
        form = JobSeekerProfileForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save()
            return redirect('generate_cv', pk=profile.pk)
    else:
        form = JobSeekerProfileForm()

    return render(request, 'create_profile.html', {
        'form': form,
    })


def generate_cv(request, pk):
    """Create a PDF CV from saved job seeker profile data and return it as a download."""
    profile = get_object_or_404(JobSeekerProfile, pk=pk)
    pdf_buffer = _build_pdf_for_profile(profile)
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    filename = f"{profile.full_name.replace(' ', '_') if profile.full_name else 'job_seeker'}_cv.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

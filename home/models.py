# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import FileExtensionValidator
import uuid

def user_cv_upload_path(instance, filename):
    """Generate unique filename for CV uploads"""
    ext = filename.split('.')[-1]
    return f'cvs/user_{instance.user.id}/{uuid.uuid4()}.{ext}'

class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    ROLE_CHOICES = (
        ('seeker', 'Job Seeker'),
        ('employer', 'Employer'),
    )
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='seeker')
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']


class UserProfile(models.Model):
    """
    User profile model for additional user information
    """
    EXPERIENCE_LEVELS = (
        ('entry', 'Entry Level (0-2 years)'),
        ('mid', 'Mid Level (3-5 years)'),
        ('senior', 'Senior Level (6+ years)'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True, help_text="Professional title")
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    experience_level = models.CharField(max_length=10, choices=EXPERIENCE_LEVELS, default='entry')
    skills = models.TextField(blank=True, help_text="Comma-separated list of skills")
    education = models.JSONField(default=list, help_text="List of education entries")
    experience = models.JSONField(default=list, help_text="List of work experience entries")
    
    # CV related fields
    cv_file = models.FileField(
        upload_to=user_cv_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx'])],
        null=True,
        blank=True
    )
    cv_text = models.TextField(blank=True, help_text="Extracted text from CV")
    cv_cloudinary_url = models.URLField(blank=True, help_text="Cloudinary URL for CV")
    cv_generated_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile of {self.user.email}"
    
    def get_skills_list(self):
        """Return skills as a list"""
        if self.skills:
            return [skill.strip() for skill in self.skills.split(',') if skill.strip()]
        return []
    
    def set_skills_list(self, skills_list):
        """Set skills from a list"""
        self.skills = ', '.join(skills_list)
    
    class Meta:
        db_table = 'user_profiles'
        ordering = ['-created_at']
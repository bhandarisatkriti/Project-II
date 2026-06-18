from django.contrib import admin

# Register your models here.
# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserProfile

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'role', 'is_active', 'created_at')
    list_filter = ('role', 'is_active')
    search_fields = ('email', 'username')
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'role'),
        }),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(UserProfile)
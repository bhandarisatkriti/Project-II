# apps/accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User
import re

class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'role', 'phone', 'created_at')
        read_only_fields = ('id', 'created_at')


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'password2', 'role', 'phone')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            role=validated_data.get('role', 'seeker'),
            phone=validated_data.get('phone', '')
        )
        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        user = authenticate(request=self.context.get('request'), username=email, password=password)
        
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")
        
        attrs['user'] = user
        return attrs
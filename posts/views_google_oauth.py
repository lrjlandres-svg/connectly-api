from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from allauth.socialaccount.models import SocialAccount
import json

User = get_user_model()

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    """
    Handle Google OAuth login and return JWT tokens
    Expected body: {
        "token": "google_id_token",
        "email": "user@gmail.com",
        "username": "optional_username",
        "google_id": "google_user_id"
    }
    """
    try:
        google_token = request.data.get('token')
        email = request.data.get('email')
        google_id = request.data.get('google_id')
        
        # Validate required fields
        if not google_token:
            return Response({
                'error': 'Google authentication token is required',
                'code': 'missing_token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not email:
            return Response({
                'error': 'Email address is required',
                'code': 'missing_email'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not google_id:
            return Response({
                'error': 'Google user ID is required',
                'code': 'missing_google_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate email format
        if '@' not in email or '.' not in email.split('@')[1]:
            return Response({
                'error': 'Invalid email format',
                'code': 'invalid_email'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create user
        username = request.data.get('username', email.split('@')[0])
        
        # Ensure username is unique
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user, created = User.objects.get_or_create(
            email=email,
            defaults={'username': username}
        )
        
        # Set unusable password for Google-authenticated users
        if created:
            user.set_unusable_password()
            user.save()
        
        # Link Google account
        social_account, social_created = SocialAccount.objects.get_or_create(
            user=user,
            provider='google',
            defaults={
                'uid': google_id,
                'extra_data': request.data
            }
        )
        
        if not social_created:
            # Update existing social account data
            social_account.extra_data = request.data
            social_account.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_new_user': created
            },
            'message': 'Google authentication successful'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Authentication failed',
            'detail': str(e),
            'code': 'auth_error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
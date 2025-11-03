from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
import jwt
from datetime import timedelta
import logging
from uuid import uuid4

from .models import Token, Profile, PasswordResetSession
from .permissions import IsAdmin
from .serializers import (
    RegisterSerializer, SendOTPSerializer, VerifyOTPSerializer, LoginSerializer,
    RefreshTokenSerializer, LogoutSerializer, ForgotPasswordSerializer,
    VerifyResetOTPSerializer, ResetPasswordSerializer, ChangePasswordSerializer,
    Enable2FASerializer, Verify2FASerializer, ResendOTPSerializer, UserProfileSerializer,
    ProfileUpdateSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()

# Existing views (unchanged)
class RegisterView(APIView):
    """Handle user registration with optional email verification OTP."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            send_verification = request.data.get('send_verification_otp', True)
            if send_verification:
                code = user.generate_email_verification_code()
                send_mail(
                    'Verify Your Email',
                    f'Your OTP is {code}. Expires in 5 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                user.is_active = False  # Inactive until verified
                user.save()
                logger.info(f"User registered: {user.email} (verification pending)")
                return Response({
                    "id": user.id,
                    "email": user.email,
                    "is_active": False,
                    "message": "User created. Verification OTP sent to email. OTP expires in 5 minutes."
                }, status=status.HTTP_201_CREATED)
            else:
                user.is_active = True
                user.is_email_verified = True
                user.save()
                logger.info(f"User registered: {user.email} (verification skipped)")
                return Response({
                    "id": user.id,
                    "email": user.email,
                    "is_active": True,
                    "message": "User created successfully."
                }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class InitialAdminSignUpView(APIView):
    """Handle initial admin signup (only one admin allowed initially)."""
    permission_classes = [AllowAny]

    def post(self, request):
        if User.objects.filter(role='admin').exists():
            return Response({"detail": "An admin already exists. Use admin-signup endpoint."}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.role = 'admin'
            user.is_email_verified = True
            user.is_active = True
            user.save()
            
            code = user.generate_email_verification_code()
            send_mail(
                'Verify Your Admin Email',
                f'Your verification code is {code} (already verified for initial admin).',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

            # -------------------------
            # Token generation
            # -------------------------
            refresh = RefreshToken.for_user(user)
            refresh_token = str(refresh)
            access_token = str(refresh.access_token)

            # Use refresh.lifetime and access_token.lifetime instead of decoding manually
            refresh_expires_at = timezone.now() + refresh.lifetime
            access_expires_at = timezone.now() + access_token.lifetime if hasattr(access_token, 'lifetime') else timezone.now() + timedelta(minutes=15)

            Token.objects.create(
                user=user,
                email=user.email,
                refresh_token=refresh_token,
                access_token=access_token,
                refresh_token_expires_at=refresh_expires_at,
                access_token_expires_at=timezone.now() + timedelta(minutes=15)
            )

            logger.info(f"Initial admin created: {user.email}")
            return Response({
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "message": "Initial admin created successfully."
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminSignUpView(APIView):
    """Handle admin signup by an existing admin."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.role = 'admin'
            user.is_active = False
            user.save()
            code = user.generate_email_verification_code()
            send_mail(
                'Verify Your Admin Email',
                f'Your verification code is {code}. Expires in 5 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            logger.info(f"Admin created by {request.user.email}: {user.email}")
            return Response({
                "id": user.id,
                "email": user.email,
                "message": "Admin created. Verification OTP sent to email."
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminUserManagementView(APIView):
    """Manage users (view, update role, delete) by admins."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, user_id=None):
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                serializer = UserProfileSerializer(user)
                logger.info(f"User {user.email} viewed by {request.user.email}")
                return Response(serializer.data, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            users = User.objects.all()
            serializer = UserProfileSerializer(users, many=True)
            logger.info(f"User list accessed by: {request.user.email}")
            return Response({"users": serializer.data}, status=status.HTTP_200_OK)

    def put(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            role = request.data.get('role')
            if role not in ['admin', 'user']:
                return Response({"detail": "Invalid role. Must be 'admin' or 'user'."}, status=status.HTTP_400_BAD_REQUEST)
            user.role = role
            user.save()
            serializer = UserProfileSerializer(user)
            logger.info(f"User {user.email} role updated to {role} by {request.user.email}")
            return Response({"message": "User role updated successfully.", "user": serializer.data}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user_email = user.email
            user.delete()
            logger.info(f"User {user_email} deleted by {request.user.email}")
            return Response({"message": "User deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class SendOTPView(APIView):
    """Send OTP for email verification, password reset, or 2FA and save to Token model."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            purpose = serializer.validated_data['purpose']
            user = User.objects.filter(email=email).first()
            
            if not user:
                logger.info(f"OTP request for non-existent email: {email}")
                return Response({"detail": "If the email exists, an OTP has been sent."}, status=status.HTTP_200_OK)
            
            code = None
            if purpose == 'email_verification' and not user.is_email_verified:
                code = user.generate_email_verification_code()
            elif purpose == 'password_reset':
                code = user.generate_password_reset_code()
            elif purpose == 'two_factor' and user.is_2fa_enabled:
                code = user.generate_email_verification_code()
            else:
                logger.warning(f"Invalid OTP purpose: {purpose} for user: {email}")
                return Response({"detail": f"Invalid request for {purpose}."}, status=status.HTTP_400_BAD_REQUEST)
            
            if code:
                send_mail(
                    f'{purpose.replace("_", " ").title()} OTP',
                    f'Your OTP is {code}. Expires in {"5 minutes" if purpose != "password_reset" else "15 minutes"}.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                logger.info(f"OTP {code} sent for {purpose} to: {user.email} and saved to Token model")
                return Response({"message": f"OTP sent to email. Expires in {'5 minutes' if purpose != 'password_reset' else '15 minutes'}."}, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class VerifyOTPView(APIView):
    """Verify OTP for email verification or password reset."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({"detail": "Invalid OTP or email."}, status=status.HTTP_400_BAD_REQUEST)

            # OTP যদি email verification এর জন্য হয়
            if user.email_verification_code == otp and user.email_verification_code_expires_at >= timezone.now():
                user.is_email_verified = True
                user.is_active = True
                user.email_verification_code = None
                user.email_verification_code_expires_at = None
                user.save()
                logger.info(f"Email verified for: {user.email}")
                return Response({"message": "Email verified successfully."}, status=status.HTTP_200_OK)

            # OTP যদি password reset এর জন্য হয়
            elif user.password_reset_code == otp and user.password_reset_code_expires_at >= timezone.now():
                reset_token = str(uuid4())
                PasswordResetSession.objects.create(user=user, token=reset_token)
                user.password_reset_code = None
                user.password_reset_code_expires_at = None
                user.save()
                logger.info(f"Password reset OTP verified for: {user.email}")
                return Response({
                    "message": "OTP verified. You may now reset your password.",
                    "reset_token": reset_token
                }, status=status.HTTP_200_OK)

            else:
                return Response({"detail": "OTP expired or invalid."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = User.objects.filter(email=email).first()
            if user and user.check_password(password):
                if not user.is_email_verified:
                    return Response({"detail": "Email not verified."}, status=status.HTTP_403_FORBIDDEN)
                if user.is_2fa_enabled:
                    code = user.generate_email_verification_code()
                    send_mail(
                        '2FA Verification',
                        f'Your 2FA OTP is {code}. Expires in 5 minutes.',
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                    return Response({
                        "detail": "2FA required. OTP sent to email.",
                        "next_step": "verify_2fa_otp"
                    }, status=status.HTTP_206_PARTIAL_CONTENT)
                refresh = RefreshToken.for_user(user)
                lifetime = timedelta(days=30) if serializer.validated_data['remember_me'] else timedelta(days=7)
                refresh.set_exp(lifetime=lifetime)
                refresh_token_str = str(refresh)
                access_token_str = str(refresh.access_token)
                access_expires_in = 900  # 15 minutes
                refresh_expires_in = int(refresh.lifetime.total_seconds())  # Use refresh.lifetime
                Token.objects.create(
                    user=user,
                    email=user.email,
                    refresh_token=refresh_token_str,
                    access_token=access_token_str,
                    refresh_token_expires_at=timezone.now() + timedelta(seconds=refresh_expires_in),
                    access_token_expires_at=timezone.now() + timedelta(minutes=15)
                )
                logger.info(f"User logged in: {user.email}")
                return Response({
                    "access_token": access_token_str,
                    "access_token_expires_in": access_expires_in,
                    "refresh_token": refresh_token_str,
                    "refresh_token_expires_in": refresh_expires_in,
                    "token_type": "Bearer",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "email_verified": user.is_email_verified,
                        "role": user.role
                    }
                }, status=status.HTTP_200_OK)
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class RefreshTokenView(APIView):
    """Refresh access token using a valid refresh token."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if serializer.is_valid():
            refresh_token_str = serializer.validated_data['refresh_token']
            try:
                refresh = RefreshToken(refresh_token_str)
                user = User.objects.get(id=refresh.payload['user_id'])
                token_obj = Token.objects.filter(user=user, refresh_token=refresh_token_str, revoked=False).first()
                if not token_obj or token_obj.refresh_token_expires_at < timezone.now():
                    return Response({"detail": "Refresh token invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)
                new_access = refresh.access_token
                access_expires_in = 900
                token_obj.access_token = str(new_access)
                token_obj.access_token_expires_at = timezone.now() + timedelta(minutes=15)
                token_obj.save()
                logger.info(f"Token refreshed for: {user.email}")
                return Response({
                    "access_token": str(new_access),
                    "access_token_expires_in": access_expires_in
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Token refresh failed: {str(e)}")
                return Response({"detail": "Refresh token invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    """Handle user logout by revoking refresh tokens."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token_str = request.data.get('refresh_token')
        if refresh_token_str:
            Token.objects.filter(refresh_token=refresh_token_str, user=request.user, revoked=False).update(revoked=True)
        else:
            Token.objects.filter(user=request.user, revoked=False).update(revoked=True)
        logger.info(f"User logged out: {request.user.email}")
        return Response({"message": "Logged out. Refresh token revoked."}, status=status.HTTP_200_OK)

class ForgotPasswordView(APIView):
    """Initiate password reset by sending an OTP."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.filter(email=email).first()
            if user:
                code = user.generate_password_reset_code()
                send_mail(
                    'Password Reset',
                    f'Your OTP is {code}. Expires in 15 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            logger.info(f"Password reset requested for: {email}")
            return Response({
                "message": "If the email exists, a password reset OTP has been sent. Expires in 15 minutes."
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyResetOTPView(APIView):
    """Verify OTP for password reset."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyResetOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            user = User.objects.filter(email=email).first()
            if not user or user.password_reset_code != otp or user.password_reset_code_expires_at < timezone.now():
                return Response({"detail": "OTP expired or invalid."}, status=status.HTTP_400_BAD_REQUEST)
            reset_token = str(uuid4())
            PasswordResetSession.objects.create(user=user, token=reset_token)
            user.password_reset_code = None
            user.password_reset_code_expires_at = None
            user.save()
            logger.info(f"Password reset OTP verified for: {user.email}")
            return Response({
                "message": "OTP verified. You may now reset your password.",
                "reset_token": reset_token
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordConfirmView(APIView):
    """Confirm password reset with a new password."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            reset_token = serializer.validated_data['reset_token']
            new_password = serializer.validated_data['new_password']
            session = PasswordResetSession.objects.filter(token=reset_token).first()
            if not session or session.is_expired():
                return Response({"detail": "Reset token invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)
            user = session.user
            user.set_password(new_password)
            user.save()
            session.delete()
            Token.objects.filter(user=user).update(revoked=True)
            logger.info(f"Password reset for: {user.email}")
            return Response({"message": "Password reset successfully. Please login with new password."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    """Change password for authenticated users."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            if not request.user.check_password(serializer.validated_data['old_password']):
                return Response({"detail": "Old password incorrect."}, status=status.HTTP_400_BAD_REQUEST)
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            Token.objects.filter(user=request.user).update(revoked=True)
            logger.info(f"Password changed for: {request.user.email}")
            return Response({"message": "Password changed successfully. All existing refresh tokens revoked."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class Enable2FAView(APIView):
    """Initiate 2FA enablement for authenticated users."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = Enable2FASerializer(data=request.data)
        if serializer.is_valid():
            method = serializer.validated_data['method']
            code = request.user.generate_email_verification_code()
            send_mail(
                'Enable 2FA',
                f'Your OTP to enable 2FA is {code}. Expires in 5 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
                fail_silently=False,
            )
            logger.info(f"2FA enable initiated for: {request.user.email}")
            return Response({
                "message": "2FA enable initiated. Verify the OTP sent to your email to finish enabling 2FA.",
                "next_step": "verify_2fa_otp"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class Verify2FAView(APIView):
    """Verify 2FA OTP to enable 2FA."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = Verify2FASerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.validated_data['otp']
            method = serializer.validated_data['method']
            if request.user.email_verification_code != otp or request.user.email_verification_code_expires_at < timezone.now():
                return Response({"detail": "OTP expired or invalid."}, status=status.HTTP_400_BAD_REQUEST)
            request.user.is_2fa_enabled = True
            request.user.email_verification_code = None
            request.user.email_verification_code_expires_at = None
            request.user.save()
            logger.info(f"2FA enabled for: {request.user.email}")
            return Response({"message": "2FA enabled successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResendOTPView(APIView):
    """Resend verification OTP for email verification."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({"detail": "If the email exists, an OTP has been sent."}, status=status.HTTP_200_OK)
            if user.is_email_verified:
                return Response({"detail": "Email already verified."}, status=status.HTTP_400_BAD_REQUEST)
            code = user.generate_email_verification_code()
            send_mail(
                'Resend Verification OTP',
                f'Your new OTP is {code}. Expires in 5 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            logger.info(f"OTP resent for: {user.email}")
            return Response({"message": "Verification OTP resent. Expires in 5 minutes."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
import logging
from .models import Profile
from .serializers import UserProfileSerializer, ProfileUpdateSerializer
from . import views



logger = logging.getLogger(__name__)

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(never_cache)
    def get(self, request):
        logger.debug(f"GET request for user: {request.user.email}")
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        logger.debug(f"PUT request for user: {request.user.email}, data: {request.data}")
        serializer = ProfileUpdateSerializer(profile, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Profile updated for user: {request.user.email}")
            return Response({
                "message": "Profile updated successfully.",
                "user": UserProfileSerializer(request.user, context={'request': request}).data
            }, status=status.HTTP_200_OK)
        logger.error(f"Profile update failed for user: {request.user.email}, errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)
    



import os
import requests
from django.http import JsonResponse, HttpResponseRedirect
from rest_framework.decorators import api_view
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

# ✅ GOOGLE LOGIN
@api_view(['GET'])
def google_login(request):
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={os.getenv('GOOGLE_CLIENT_ID')}&"
        f"redirect_uri={os.getenv('GOOGLE_REDIRECT_URI')}&"
        f"scope=openid%20email%20profile&"
        f"response_type=code&"
        f"access_type=offline&prompt=consent"
    )
    return HttpResponseRedirect(auth_url)

@api_view(['GET'])
def google_callback(request):
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'error': 'Authorization code missing'}, status=400)

    try:
        # 1. Get Access Token
        token_response = requests.post('https://oauth2.googleapis.com/token', data={
            'code': code,
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'redirect_uri': os.getenv('GOOGLE_REDIRECT_URI'),
            'grant_type': 'authorization_code'
        }).json()

        if 'error' in token_response:
            return JsonResponse({'error': 'Google token exchange failed'}, status=400)

        access_token = token_response['access_token']
        user_info = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        ).json()

        email = user_info.get('email')
        if not email:
            return JsonResponse({'error': 'Email not provided by Google'}, status=400)

        # 2. Find or Create User
        user, created = User.objects.get_or_create(email=email, defaults={
            'full_name': user_info.get('name', ''),
            'is_email_verified': True,
            'is_active': True,
        })

        # 3. যদি আগের ইউজার থাকে, তাকে active + verified করো
        if not created:
            user.is_email_verified = True
            user.is_active = True
            user.full_name = user_info.get('name', user.full_name or '')
            if not user.has_usable_password():
                user.set_unusable_password()
            user.save()
            logger.info(f"Existing user activated via Google: {email}")

        # 4. Profile create if not exists
        Profile.objects.get_or_create(user=user)

        # 5. Generate JWT Tokens
        refresh = RefreshToken.for_user(user)
        refresh_token_str = str(refresh)
        access_token_str = str(refresh.access_token)

        refresh_expires_at = timezone.now() + refresh.lifetime
        access_expires_at = timezone.now() + timedelta(minutes=15)

        # Revoke old tokens (optional but secure)
        Token.objects.filter(user=user).update(revoked=True)

        Token.objects.create(
            user=user,
            email=user.email,
            refresh_token=refresh_token_str,
            access_token=access_token_str,
            refresh_token_expires_at=refresh_expires_at,
            access_token_expires_at=access_expires_at
        )

        logger.info(f"Google login successful: {email}")

        return JsonResponse({
            'access_token': access_token_str,
            'access_token_expires_in': 900,
            'refresh_token': refresh_token_str,
            'refresh_token_expires_in': int(refresh.lifetime.total_seconds()),
            'token_type': 'Bearer',
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'email_verified': user.is_email_verified,
                'role': user.role
            }
        })

    except Exception as e:
        logger.error(f"Google login error: {str(e)}")
        return JsonResponse({'error': 'Login failed'}, status=500)

# 🍎 APPLE LOGIN
@api_view(['GET'])
def apple_login(request):
    auth_url = (
        "https://appleid.apple.com/auth/authorize?"
        f"client_id={os.getenv('APPLE_CLIENT_ID')}&"
        f"redirect_uri={os.getenv('APPLE_REDIRECT_URI')}&"
        f"response_type=code%20id_token&"
        f"scope=name%20email&"
        f"response_mode=form_post"
    )
    return HttpResponseRedirect(auth_url)


@api_view(['POST'])
def apple_callback(request):
    code = request.POST.get('code')
    id_token = request.POST.get('id_token')

    if not code and not id_token:
        return JsonResponse({'error': 'Missing authorization data'}, status=400)

    try:
        # Apple থেকে টোকেন নেওয়া
        token_response = requests.post('https://appleid.apple.com/auth/token', data={
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': os.getenv('APPLE_CLIENT_ID'),
            'client_secret': os.getenv('APPLE_CLIENT_SECRET'),
            'redirect_uri': os.getenv('APPLE_REDIRECT_URI'),
        }, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()

        if 'error' in token_response:
            return JsonResponse({'error': token_response['error']}, status=400)

        id_token = token_response.get('id_token', id_token)
        decoded = jwt.decode(id_token, options={"verify_signature": False})  # verify_signature=False শুধু ডেমো

        user_email = decoded.get('email')
        user_id = decoded.get('sub')

        app_token = jwt.encode({
            'user_id': user_id,
            'email': user_email,
        }, settings.JWT_SECRET, algorithm='HS256')


        return JsonResponse({
            'success': True,
            'provider': 'apple',
            'token': app_token,
            'user': {
                'id': user_id,
                'email': user_email,
                'name': decoded.get('name'),
            }
        })
    except Exception as e:
        return JsonResponse({'error': f'Apple login failed: {str(e)}'}, status=500)



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
import jwt
import requests
import logging
from datetime import timedelta
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


# =======================
# USER AUTHENTICATION VIEWS
# =======================

class RegisterView(APIView):
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
                user.is_active = False
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

            refresh = RefreshToken.for_user(user)
            refresh_token = str(refresh)
            access_token = str(refresh.access_token)

            Token.objects.create(
                user=user,
                email=user.email,
                refresh_token=refresh_token,
                access_token=access_token,
                refresh_token_expires_at=timezone.now() + refresh.lifetime,
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
                logger.info(f"OTP {code} sent for {purpose} to: {user.email}")
                return Response({"message": f"OTP sent to email. Expires in {'5 minutes' if purpose != 'password_reset' else '15 minutes'}."}, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({"detail": "Invalid OTP or email."}, status=status.HTTP_400_BAD_REQUEST)

            if user.email_verification_code == otp and user.email_verification_code_expires_at >= timezone.now():
                user.is_email_verified = True
                user.is_active = True
                user.email_verification_code = None
                user.email_verification_code_expires_at = None
                user.save()
                logger.info(f"Email verified for: {user.email}")
                return Response({"message": "Email verified successfully."}, status=status.HTTP_200_OK)

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
                access_expires_in = 900
                refresh_expires_in = int(refresh.lifetime.total_seconds())

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
                token_obj.access_token = str(new_access)
                token_obj.access_token_expires_at = timezone.now() + timedelta(minutes=15)
                token_obj.save()
                logger.info(f"Token refreshed for: {user.email}")
                return Response({
                    "access_token": str(new_access),
                    "access_token_expires_in": 900
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Token refresh failed: {str(e)}")
                return Response({"detail": "Refresh token invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = Enable2FASerializer(data=request.data)
        if serializer.is_valid():
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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = Verify2FASerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.validated_data['otp']
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


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(never_cache)
    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileUpdateSerializer(profile, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Profile updated for user: {request.user.email}")
            return Response({
                "message": "Profile updated successfully.",
                "user": UserProfileSerializer(request.user, context={'request': request}).data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)


# =======================
# SOCIAL LOGIN VIEWS
# =======================

# GOOGLE LOGIN VIEW
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not settings.GOOGLE_REDIRECT_URI:
            return Response({"error": "Google OAuth not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        google_auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={settings.GOOGLE_CLIENT_ID}&"
            f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
            f"scope=openid%20email%20profile&"
            f"response_type=code&"
            f"access_type=offline&prompt=consent"
        )
        return Response({"auth_url": google_auth_url}, status=status.HTTP_200_OK)

    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response({"error": "Authorization code missing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_response = requests.post('https://oauth2.googleapis.com/token', data={
                'code': code,
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'redirect_uri': settings.GOOGLE_REDIRECT_URI,
                'grant_type': 'authorization_code'
            }).json()

            if 'error' in token_response:
                return Response({"error": token_response.get('error_description')}, status=status.HTTP_400_BAD_REQUEST)

            access_token = token_response['access_token']
            user_info = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            ).json()

            email = user_info.get('email')
            if not email:
                return Response({"error": "Google did not provide an email"}, status=status.HTTP_400_BAD_REQUEST)

            user, created = User.objects.get_or_create(email=email, defaults={
                'full_name': user_info.get('name', ''),
                'is_email_verified': True,
                'is_active': True,
            })
            if created:
                user.set_unusable_password()
                user.save()
                Profile.objects.create(user=user)
                logger.info(f"New Google user: {email}")
            else:
                user.is_active = True
                user.is_email_verified = True
                user.save()

            refresh = RefreshToken.for_user(user)
            Token.objects.create(
                user=user,
                email=user.email,
                refresh_token=str(refresh),
                access_token=str(refresh.access_token),
                refresh_token_expires_at=timezone.now() + refresh.lifetime,
                access_token_expires_at=timezone.now() + timedelta(minutes=15)
            )

            logger.info(f"Google login success: {user.email}")
            return Response({
                "access_token": str(refresh.access_token),
                "access_token_expires_in": 900,
                "refresh_token": str(refresh),
                "refresh_token_expires_in": int(refresh.lifetime.total_seconds()),
                "token_type": "Bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "email_verified": user.is_email_verified,
                    "role": user.role
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Google login failed: {e}")
            return Response({"error": "Google login failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# APPLE LOGIN VIEW
# ------------------------------
# Apple Client Secret Generator
# ------------------------------
def generate_apple_client_secret():
    from django.conf import settings
    from datetime import datetime, timedelta
    import jwt

    headers = {"alg": "ES256", "kid": settings.APPLE_KEY_ID}
    payload = {
        "iss": settings.APPLE_TEAM_ID,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=180),
        "aud": "https://appleid.apple.com",
        "sub": settings.APPLE_CLIENT_ID,
    }
    return jwt.encode(payload, settings.APPLE_PRIVATE_KEY, algorithm="ES256", headers=headers)


# ------------------------------
# Apple Login View (FIXED)
# ------------------------------
class AppleLoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if not settings.APPLE_CALLBACK_URL:
            return Response(
                {"error": "Apple OAuth not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        auth_url = (
            f"https://appleid.apple.com/auth/authorize?"
            f"client_id={settings.APPLE_CLIENT_ID}&"
            f"redirect_uri={settings.APPLE_CALLBACK_URL}&"
            f"response_type=code id_token&"
            f"scope=name email&"
            f"response_mode=form_post"
        )
        return Response({"auth_url": auth_url}, status=status.HTTP_200_OK)

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response(
                {"error": "Missing authorization code"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Generate client secret
            client_secret = generate_apple_client_secret()

            # Exchange code for tokens
            token_response = requests.post(
                "https://appleid.apple.com/auth/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": settings.APPLE_CLIENT_ID,
                    "client_secret": client_secret,
                    "redirect_uri": settings.APPLE_CALLBACK_URL,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10
            ).json()

            if token_response.get("error"):
                return Response(
                    {"error": token_response.get("error_description", "Token exchange failed")},
                    status=status.HTTP_400_BAD_REQUEST
                )

            id_token = token_response.get("id_token")
            if not id_token:
                return Response(
                    {"error": "No id_token from Apple"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Decode id_token (no verification needed)
            try:
                decoded = jwt.decode(id_token, options={"verify_signature": False})
            except jwt.PyJWTError as e:
                logger.error(f"Invalid id_token: {e}")
                return Response(
                    {"error": "Invalid Apple token"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            email = decoded.get("email")
            if not email:
                return Response(
                    {"error": "Email not provided by Apple"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Extract name only on first login
            first_name = ""
            last_name = ""
            user_data = request.data.get("user", {})
            if user_data:
                name = user_data.get("name", {})
                first_name = name.get("firstName", "")
                last_name = name.get("lastName", "")

            full_name = f"{first_name} {last_name}".strip() or email.split("@")[0]

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "full_name": full_name,
                    "is_email_verified": True,
                    "is_active": True,
                }
            )

            if created:
                user.set_unusable_password()
                user.save()
                Profile.objects.create(user=user)
                logger.info(f"New Apple user: {email}")
            else:
                # Update name if provided and changed
                if first_name and user.full_name != full_name:
                    user.full_name = full_name
                    user.save()
                user.is_active = True
                user.is_email_verified = True
                user.save()
                logger.info(f"Apple login: {email}")

            # Generate JWT
            refresh = RefreshToken.for_user(user)
            refresh_token_str = str(refresh)
            access_token_str = str(refresh.access_token)

            # Update or create token
            Token.objects.update_or_create(
                user=user,
                defaults={
                    "email": user.email,
                    "refresh_token": refresh_token_str,
                    "access_token": access_token_str,
                    "refresh_token_expires_at": timezone.now() + refresh.lifetime,
                    "access_token_expires_at": timezone.now() + timedelta(minutes=15),
                }
            )

            return Response(
                {
                    "access_token": access_token_str,
                    "access_token_expires_in": 900,
                    "refresh_token": refresh_token_str,
                    "refresh_token_expires_in": int(refresh.lifetime.total_seconds()),
                    "token_type": "Bearer",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "email_verified": user.is_email_verified,
                        "role": user.role,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except requests.RequestException as e:
            logger.error(f"Apple API error: {e}")
            return Response(
                {"error": "Failed to connect to Apple"},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.error(f"Apple login failed: {e}")
            return Response(
                {"error": "Apple login failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # authentication/views.py



# DEBUG CALLBACK (Optional)
# DEBUG CALLBACK (Optional)
class AppleCallbackView(APIView):
    def post(self, request):
        return Response({
            "code": request.data.get("code"),
            "id_token": request.data.get("id_token"),
            "user": request.data.get("user"),
            "state": request.data.get("state")
        })
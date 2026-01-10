from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
import jwt
import requests
import logging
from datetime import datetime, timedelta
from uuid import uuid4
import requests
from django.core.files.base import ContentFile
from django.template.loader import render_to_string

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
                
                # Beautiful HTML email for registration
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        * {{
                            margin: 0;
                            padding: 0;
                            box-sizing: border-box;
                        }}
                        body {{
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            line-height: 1.6;
                            color: #333;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 20px;
                        }}
                        .container {{
                            max-width: 600px;
                            margin: 0 auto;
                            background-color: #ffffff;
                            border-radius: 12px;
                            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                            overflow: hidden;
                        }}
                        .header {{
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 30px 20px;
                            text-align: center;
                            color: #ffffff;
                        }}
                        .header h2 {{
                            font-size: 28px;
                            font-weight: 700;
                            margin: 0;
                            letter-spacing: 1px;
                        }}
                        .header p {{
                            font-size: 14px;
                            margin-top: 5px;
                            opacity: 0.9;
                        }}
                        .content {{
                            padding: 40px 30px;
                        }}
                        .content p {{
                            margin: 15px 0;
                            color: #555;
                            font-size: 15px;
                        }}
                        .otp-box {{
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            border-radius: 10px;
                            padding: 25px;
                            text-align: center;
                            margin: 30px 0;
                            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.3);
                        }}
                        .otp {{
                            font-size: 48px;
                            font-weight: 900;
                            color: #ffffff;
                            letter-spacing: 8px;
                            font-family: 'Courier New', monospace;
                        }}
                        .otp-label {{
                            color: rgba(255, 255, 255, 0.8);
                            font-size: 12px;
                            text-transform: uppercase;
                            margin-top: 10px;
                            letter-spacing: 2px;
                        }}
                        .info-box {{
                            background-color: #f8f9ff;
                            border-left: 4px solid #667eea;
                            padding: 15px;
                            margin: 20px 0;
                            border-radius: 5px;
                        }}
                        .info-box p {{
                            margin: 5px 0;
                            font-size: 14px;
                            color: #666;
                        }}
                        .footer {{
                            background-color: #f8f9ff;
                            padding: 25px;
                            text-align: center;
                            border-top: 1px solid #eee;
                        }}
                        .footer p {{
                            margin: 8px 0;
                            font-size: 12px;
                            color: #999;
                        }}
                        .footer a {{
                            color: #667eea;
                            text-decoration: none;
                            font-weight: 600;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>🎉 Welcome to HelpMeSpeak</h2>
                            <p>Verify Your Email Address</p>
                        </div>
                        
                        <div class="content">
                            <p>Hi <strong>{user.first_name or 'User'}</strong>,</p>
                            
                            <p>Welcome to HelpMeSpeak! We're thrilled to have you join our community.</p>
                            
                            <p>To complete your registration, please verify your email using the code below:</p>
                            
                            <div class="otp-box">
                                <div class="otp">{code}</div>
                                <div class="otp-label">One-Time Password</div>
                            </div>
                            
                            <div class="info-box">
                                <p><strong>⏱️ Valid for:</strong> 5 minutes</p>
                                <p><strong>🔒 Security:</strong> This code is personal & confidential</p>
                                <p><strong>✅ Status:</strong> Active</p>
                            </div>
                            
                            <p style="color: #e74c3c; font-weight: 600; margin-top: 20px;">⚠️ If you didn't create this account, please ignore this email.</p>
                            
                            <p style="margin-top: 20px;">Best regards,<br><strong>The HelpMeSpeak Team</strong></p>
                        </div>
                        
                        <div class="footer">
                            <p>&copy; {datetime.now().year} HelpMeSpeak. All rights reserved.</p>
                            <p><a href="https://helpmespeak.app">Visit our website</a> | <a href="https://helpmespeak.app/support">Get Support</a></p>
                            <p style="margin-top: 15px; font-size: 11px; color: #bbb;">This is an automated message, please do not reply to this email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                text_content = f"""
                HelpMeSpeak - Email Verification
                =================================
                
                Hi {user.first_name or 'User'},
                
                Welcome to HelpMeSpeak!
                
                Your Verification Code:
                {code}
                
                Valid for: 5 minutes
                
                If you didn't create this account, please ignore this email.
                
                Best regards,
                The HelpMeSpeak Team
                
                © {datetime.now().year} HelpMeSpeak. All rights reserved.
                """

                email_message = EmailMultiAlternatives(
                    subject='Verify Your Email - HelpMeSpeak',
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )
                email_message.attach_alternative(html_content, "text/html")
                email_message.send()
                
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

# ... বাকি সব views (GoogleCallbackView, AppleCallbackView ইত্যাদি)


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
            subject = None
            expiry = None
            if purpose == 'email_verification' and not user.is_email_verified:
                code = user.generate_email_verification_code()
                subject = "Verify Your Email Address"
                expiry = "5 minutes"
            elif purpose == 'password_reset':
                code = user.generate_password_reset_code()
                subject = "Reset Your Password"
                expiry = "15 minutes"
            elif purpose == 'two_factor' and user.is_2fa_enabled:
                code = user.generate_email_verification_code()
                subject = "Two-Factor Authentication (2FA) OTP"
                expiry = "5 minutes"
            else:
                logger.warning(f"Invalid OTP purpose: {purpose} for user: {email}")
                return Response({"detail": f"Invalid request for {purpose}."}, status=status.HTTP_400_BAD_REQUEST)
            
            if code:
                # Inline HTML content with beautiful design
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        * {{
                            margin: 0;
                            padding: 0;
                            box-sizing: border-box;
                        }}
                        body {{
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            line-height: 1.6;
                            color: #333;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 20px;
                        }}
                        .container {{
                            max-width: 600px;
                            margin: 0 auto;
                            background-color: #ffffff;
                            border-radius: 12px;
                            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                            overflow: hidden;
                        }}
                        .header {{
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 30px 20px;
                            text-align: center;
                            color: #ffffff;
                        }}
                        .header h2 {{
                            font-size: 28px;
                            font-weight: 700;
                            margin: 0;
                            letter-spacing: 1px;
                        }}
                        .header p {{
                            font-size: 14px;
                            margin-top: 5px;
                            opacity: 0.9;
                        }}
                        .content {{
                            padding: 40px 30px;
                        }}
                        .content h3 {{
                            color: #667eea;
                            font-size: 20px;
                            margin-bottom: 15px;
                        }}
                        .content p {{
                            margin: 15px 0;
                            color: #555;
                            font-size: 15px;
                        }}
                        .otp-box {{
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            border-radius: 10px;
                            padding: 25px;
                            text-align: center;
                            margin: 30px 0;
                            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.3);
                        }}
                        .otp {{
                            font-size: 48px;
                            font-weight: 900;
                            color: #ffffff;
                            letter-spacing: 8px;
                            font-family: 'Courier New', monospace;
                        }}
                        .otp-label {{
                            color: rgba(255, 255, 255, 0.8);
                            font-size: 12px;
                            text-transform: uppercase;
                            margin-top: 10px;
                            letter-spacing: 2px;
                        }}
                        .info-box {{
                            background-color: #f8f9ff;
                            border-left: 4px solid #667eea;
                            padding: 15px;
                            margin: 20px 0;
                            border-radius: 5px;
                        }}
                        .info-box p {{
                            margin: 5px 0;
                            font-size: 14px;
                            color: #666;
                        }}
                        .warning {{
                            color: #e74c3c;
                            font-weight: 600;
                        }}
                        .footer {{
                            background-color: #f8f9ff;
                            padding: 25px;
                            text-align: center;
                            border-top: 1px solid #eee;
                        }}
                        .footer p {{
                            margin: 8px 0;
                            font-size: 12px;
                            color: #999;
                        }}
                        .footer a {{
                            color: #667eea;
                            text-decoration: none;
                            font-weight: 600;
                        }}
                        .footer a:hover {{
                            text-decoration: underline;
                        }}
                        .divider {{
                            height: 2px;
                            background: linear-gradient(to right, #667eea, #764ba2);
                            margin: 20px 0;
                        }}
                        .security-icon {{
                            text-align: center;
                            font-size: 40px;
                            margin: 15px 0;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>🎉 HelpMeSpeak</h2>
                            <p>Secure Verification Code</p>
                        </div>
                        
                        <div class="content">
                            <p>Hi <strong>{user.first_name or 'User'}</strong>,</p>
                            
                            <p>Thank you for using HelpMeSpeak! We're excited to have you on board.</p>
                            
                            <h3>Your Verification Code</h3>
                            <p>Use the code below to {purpose.replace('_', ' ').lower()}:</p>
                            
                            <div class="otp-box">
                                <div class="otp">{code}</div>
                                <div class="otp-label">One-Time Password</div>
                            </div>
                            
                            <div class="info-box">
                                <p><strong>⏱️ Valid for:</strong> {expiry}</p>
                                <p><strong>🔒 This code is:</strong> Personal & Confidential</p>
                                <p><strong>✅ Status:</strong> Active</p>
                            </div>
                            
                            <div class="divider"></div>
                            
                            <p style="color: #e74c3c; font-weight: 600;">⚠️ Important Security Notice</p>
                            <p>If you did not request this code, please <strong>ignore this email immediately</strong> and secure your account.</p>
                            
                            <p style="margin-top: 20px;">Best regards,<br><strong>The HelpMeSpeak Team</strong></p>
                        </div>
                        
                        <div class="footer">
                            <p>&copy; {datetime.now().year} HelpMeSpeak. All rights reserved.</p>
                            <p><a href="https://helpmespeak.app">Visit our website</a> | <a href="https://helpmespeak.app/support">Get Support</a></p>
                            <p style="margin-top: 15px; font-size: 11px; color: #bbb;">This is an automated message, please do not reply to this email.</p>
                        </div>
                    </div>
                </body>
                </html>
                """

                # Plain text content
                text_content = f"""
                HelpMeSpeak - Secure Verification Code
                ========================================
                
                Hi {user.first_name or 'User'},
                
                Thank you for using HelpMeSpeak!
                
                Your Verification Code:
                {code}
                
                Valid for: {expiry}
                
                ⚠️ IMPORTANT: If you did not request this code, please ignore this email immediately.
                
                Best regards,
                The HelpMeSpeak Team
                
                © {datetime.now().year} HelpMeSpeak. All rights reserved.
                """

                # Send email
                email_message = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )
                email_message.attach_alternative(html_content, "text/html")
                email_message.send()

                logger.info(f"OTP {code} sent for {purpose} to: {user.email}")
                return Response({"message": f"OTP sent to email. Expires in {expiry}."}, status=status.HTTP_200_OK)
            
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
                return Response({"message": "Your email has been successfully verified. Thank you!"}, status=status.HTTP_200_OK)

            elif user.password_reset_code == otp and user.password_reset_code_expires_at >= timezone.now():
                reset_token = str(uuid4())
                PasswordResetSession.objects.create(user=user, token=reset_token)
                user.password_reset_code = None
                user.password_reset_code_expires_at = None
                user.save()
                logger.info(f"Password reset OTP verified for: {user.email}")
                return Response({
                    "message": "OTP verified successfully. You may now reset your password.",
                    "reset_token": reset_token
                }, status=status.HTTP_200_OK)

            else:
                return Response({"detail": "The OTP you entered is invalid or has expired."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = User.objects.filter(email=email, role='user').first()  # শুধুমাত্র user

            if not user or not user.check_password(password):
                return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

            if not user.is_email_verified:
                return Response({"detail": "Email not verified."}, status=status.HTTP_403_FORBIDDEN)

            # 2FA check
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

            # Token generation
            Token.objects.filter(user=user).delete()
            refresh = RefreshToken.for_user(user)
            token_obj, _ = Token.objects.get_or_create(user=user)
            token_obj.refresh_token = str(refresh)
            token_obj.access_token = str(refresh.access_token)
            token_obj.refresh_token_expires_at = timezone.now() + refresh.lifetime
            token_obj.access_token_expires_at = timezone.now() + timedelta(days=995)
            token_obj.revoked = False
            token_obj.save()

            return Response({
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "token_type": "Bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": f"{user.first_name} {user.last_name}".strip(),
                    "role": user.role
                }
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = User.objects.filter(email=email, role='admin').first()  # শুধুমাত্র admin

            if not user or not user.check_password(password):
                return Response({"detail": "Invalid credentials or not an admin."}, status=status.HTTP_401_UNAUTHORIZED)

            if not user.is_email_verified:
                return Response({"detail": "Email not verified."}, status=status.HTTP_403_FORBIDDEN)

            # Token generation
            Token.objects.filter(user=user).delete()
            refresh = RefreshToken.for_user(user)
            token_obj, _ = Token.objects.get_or_create(user=user)
            token_obj.refresh_token = str(refresh)
            token_obj.access_token = str(refresh.access_token)
            token_obj.refresh_token_expires_at = timezone.now() + refresh.lifetime
            token_obj.access_token_expires_at = timezone.now() + timedelta(days=995)
            token_obj.revoked = False
            token_obj.save()

            return Response({
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "token_type": "Bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": f"{user.first_name} {user.last_name}".strip(),
                    "role": user.role
                }
            }, status=status.HTTP_200_OK)

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
                token_obj.access_token_expires_at = timezone.now() + timedelta(days=995)
                token_obj.save()
                logger.info(f"Token refreshed for: {user.email}")
                return Response({
                    "access_token": str(new_access),
                    "access_token_expires_in": 995
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Token refresh failed: {str(e)}")
                return Response({"detail": "Refresh token invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 
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
            
            # Generate OTP
            code = user.generate_email_verification_code()
            subject = "Resend Verification OTP"
            expiry = "5 minutes"

            # Inline HTML content with beautiful design
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: #ffffff;
                        border-radius: 12px;
                        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                        overflow: hidden;
                    }}
                    .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 30px 20px;
                        text-align: center;
                        color: #ffffff;
                    }}
                    .header h2 {{
                        font-size: 28px;
                        font-weight: 700;
                        margin: 0;
                        letter-spacing: 1px;
                    }}
                    .header p {{
                        font-size: 14px;
                        margin-top: 5px;
                        opacity: 0.9;
                    }}
                    .content {{
                        padding: 40px 30px;
                    }}
                    .content h3 {{
                        color: #667eea;
                        font-size: 20px;
                        margin-bottom: 15px;
                    }}
                    .content p {{
                        margin: 15px 0;
                        color: #555;
                        font-size: 15px;
                    }}
                    .otp-box {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        border-radius: 10px;
                        padding: 25px;
                        text-align: center;
                        margin: 30px 0;
                        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.3);
                    }}
                    .otp {{
                        font-size: 48px;
                        font-weight: 900;
                        color: #ffffff;
                        letter-spacing: 8px;
                        font-family: 'Courier New', monospace;
                    }}
                    .otp-label {{
                        color: rgba(255, 255, 255, 0.8);
                        font-size: 12px;
                        text-transform: uppercase;
                        margin-top: 10px;
                        letter-spacing: 2px;
                    }}
                    .info-box {{
                        background-color: #f8f9ff;
                        border-left: 4px solid #667eea;
                        padding: 15px;
                        margin: 20px 0;
                        border-radius: 5px;
                    }}
                    .info-box p {{
                        margin: 5px 0;
                        font-size: 14px;
                        color: #666;
                    }}
                    .warning {{
                        color: #e74c3c;
                        font-weight: 600;
                    }}
                    .footer {{
                        background-color: #f8f9ff;
                        padding: 25px;
                        text-align: center;
                        border-top: 1px solid #eee;
                    }}
                    .footer p {{
                        margin: 8px 0;
                        font-size: 12px;
                        color: #999;
                    }}
                    .footer a {{
                        color: #667eea;
                        text-decoration: none;
                        font-weight: 600;
                    }}
                    .footer a:hover {{
                        text-decoration: underline;
                    }}
                    .divider {{
                        height: 2px;
                        background: linear-gradient(to right, #667eea, #764ba2);
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>🎉 HelpMeSpeak</h2>
                        <p>New Verification Code</p>
                    </div>
                    
                    <div class="content">
                        <p>Hi <strong>{user.first_name or 'User'}</strong>,</p>
                        
                        <p>Here's your new verification code to complete your registration.</p>
                        
                        <h3>Your New OTP</h3>
                        
                        <div class="otp-box">
                            <div class="otp">{code}</div>
                            <div class="otp-label">One-Time Password</div>
                        </div>
                        
                        <div class="info-box">
                            <p><strong>⏱️ Valid for:</strong> {expiry}</p>
                            <p><strong>🔒 Type:</strong> Email Verification</p>
                            <p><strong>✅ Status:</strong> Active & Ready to Use</p>
                        </div>
                        
                        <div class="divider"></div>
                        
                        <p><strong style="color: #27ae60;">💡 What to do next:</strong></p>
                        <p>Enter this code in the verification field to activate your account.</p>
                        
                        <p style="color: #e74c3c; font-weight: 600; margin-top: 20px;">⚠️ If you didn't request this, please ignore this email.</p>
                        
                        <p style="margin-top: 20px;">Best regards,<br><strong>The HelpMeSpeak Team</strong></p>
                    </div>
                    
                    <div class="footer">
                        <p>&copy; {datetime.now().year} HelpMeSpeak. All rights reserved.</p>
                        <p><a href="https://helpmespeak.app">Visit our website</a> | <a href="https://helpmespeak.app/support">Get Support</a></p>
                        <p style="margin-top: 15px; font-size: 11px; color: #bbb;">This is an automated message, please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Plain text content
            text_content = f"""
            HelpMeSpeak - New Verification Code
            =====================================
            
            Hi {user.first_name or 'User'},
            
            Here's your new verification code:
            {code}
            
            Valid for: {expiry}
            
            ⚠️ If you didn't request this, please ignore this email.
            
            Best regards,
            The HelpMeSpeak Team
            
            © {datetime.now().year} HelpMeSpeak. All rights reserved.
            """

            # Send email
            email_message = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send()

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
        try:
            profile, _ = Profile.objects.get_or_create(user=request.user)

            # Profile update
            serializer = ProfileUpdateSerializer(
                profile,
                data=request.data,
                partial=True,
                context={'request': request}
            )

            if serializer.is_valid():
                serializer.save()

                # User ফিল্ড আপডেট (full_name, first_name, last_name)
                full_name = request.data.get("full_name")
                if full_name:
                    parts = full_name.strip().split(" ", 1)
                    request.user.first_name = parts[0]
                    request.user.last_name = parts[1] if len(parts) > 1 else ""
                    request.user.full_name = full_name
                    request.user.save(update_fields=['first_name', 'last_name', 'full_name'])

                return Response({
                    "message": "Profile updated successfully",
                    "user": UserProfileSerializer(request.user, context={'request': request}).data
                }, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        return self.put(request)

import random
import string
import time
import logging
import json
import requests

from django.utils import timezone
from datetime import timedelta
from django.core.files.base import ContentFile
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .models import Profile, Token

logger = logging.getLogger(__name__)
User = get_user_model()


def generate_unique_username(email):
    base = email.split("@")[0]
    while True:
        username = f"{base}_{''.join(random.choices(string.digits, k=4))}"
        if not User.objects.filter(username=username).exists():
            return username


@method_decorator(csrf_exempt, name="dispatch")
class GoogleIdTokenLogin(View):

    def post(self, request):
        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        email = data.get("email")
        full_name = data.get("full_name", "").strip()
        photo_url = data.get("photo_url")

        if not email:
            return JsonResponse({"error": "Email is required"}, status=400)

        # User create/get
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": generate_unique_username(email),
                "is_active": True,
                "is_email_verified": True,
            }
        )

        # Update name
        if full_name:
            parts = full_name.split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""
            user.save()

        # Profile
        profile, _ = Profile.objects.get_or_create(user=user)

        # Download profile photo
        if photo_url:
            try:
                res = requests.get(photo_url, timeout=10)
                if res.status_code == 200:
                    ext = photo_url.split(".")[-1].split("?")[0]
                    ext = ext if ext.lower() in ["jpg", "jpeg", "png"] else "jpg"
                    filename = f"google_{user.id}_{int(time.time())}.{ext}"
                    profile.image.save(filename, ContentFile(res.content), save=False)
                    profile.save()
            except Exception as e:
                logger.warning(f"Profile download failed: {e}")

        # Tokens
        refresh = RefreshToken.for_user(user)
        token_obj, _ = Token.objects.get_or_create(user=user)
        token_obj.email = user.email
        token_obj.refresh_token = str(refresh)
        token_obj.access_token = str(refresh.access_token)
        token_obj.refresh_token_expires_at = timezone.now() + refresh.lifetime
        token_obj.access_token_expires_at = timezone.now() + timedelta(minutes=15)
        token_obj.revoked = False
        token_obj.save()

        return JsonResponse({
            "success": True,
            "created": created,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": f"{user.first_name} {user.last_name}".strip(),
                "profile_image": profile.image.url if profile.image else None,
            }
        }, status=200)




import json
from django.views import View
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Profile, Token
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


def random_username():
    return "apple_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


@method_decorator(csrf_exempt, name="dispatch")
class CustomAppleLogin(View):

    def post(self, request):
        try:
            try:
                data = json.loads(request.body)
            except:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

            id_token = data.get("id_token")
            email = data.get("email")
            full_name_raw = data.get("full_name") or ""

            if not id_token:
                return JsonResponse({"error": "id_token is required"}, status=400)

            sub = id_token.strip()

            # Email fallback
            if not email:
                email = f"{sub}@privaterelay.appleid.com"

            # User create/get
            try:
                user = User.objects.get(email=email)
                created = False
            except User.DoesNotExist:
                parts = full_name_raw.split(" ", 1)
                first_name = parts[0] if parts else ""
                last_name = parts[1] if len(parts) > 1 else ""

                user = User.objects.create(
                    username=sub or random_username(),
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,
                )
                created = True

            # Update name
            if full_name_raw:
                parts = full_name_raw.split(" ", 1)
                user.first_name = parts[0]
                user.last_name = parts[1] if len(parts) > 1 else ""
                user.save()

            # Profile
            profile, _ = Profile.objects.get_or_create(user=user)

            # Tokens
            refresh = RefreshToken.for_user(user)

            token_obj, _ = Token.objects.get_or_create(user=user)
            token_obj.email = user.email
            token_obj.refresh_token = str(refresh)
            token_obj.access_token = str(refresh.access_token)
            token_obj.refresh_token_expires_at = timezone.now() + refresh.lifetime
            token_obj.access_token_expires_at = timezone.now() + timedelta(minutes=15)
            token_obj.revoked = False
            token_obj.save()

            return JsonResponse({
                "success": True,
                "created": created,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": f"{user.first_name} {user.last_name}".strip(),
                    "profile_image": profile.image.url if profile.image else None,
                }
            }, status=200)

        except Exception as e:
            return JsonResponse({
                "error": "Apple login failed",
                "details": str(e)
            }, status=500)



import os
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Profile

logger = logging.getLogger(__name__)
class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        if user.role == 'admin':
            return Response({"detail": "Admin accounts cannot be deleted via this endpoint."}, status=status.HTTP_403_FORBIDDEN)

        try:
            # ১️⃣ Profile delete
            profile = getattr(user, 'profile', None)
            if profile:
                if profile.image and profile.image.name != 'profile_images/default_profile.png':
                    image_path = getattr(profile.image, 'path', None)
                    if image_path and os.path.isfile(image_path):
                        os.remove(image_path)
                        logger.info(f"Deleted profile image for user: {user.email}")
                profile.delete()
                logger.info(f"Profile deleted for user: {user.email}")

            # ২️⃣ Token delete
            Token.objects.filter(user=user).delete()
            logger.info(f"Tokens deleted for user: {user.email}")

            # ৩️⃣ PasswordResetSession delete
            PasswordResetSession.objects.filter(user=user).delete()
            logger.info(f"Password reset sessions deleted for user: {user.email}")

            # ৪️⃣ অবশেষে ইউজার ডিলিট
            email = user.email
            user.delete()
            logger.info(f"User account deleted: {email}")

            return Response({"message": "User account and all related data deleted successfully."}, status=200)

        except Exception as e:
            logger.error(f"Failed to delete account for {user.email}: {str(e)}")
            return Response({"error": str(e)}, status=500)
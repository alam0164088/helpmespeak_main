from django.urls import path
from . import views 
from .views import google_login, google_callback

from .views import (
    RegisterView,
    SendOTPView,
    ResendOTPView,
    VerifyOTPView,
    LoginView,
    RefreshTokenView,
    LogoutView,
    ForgotPasswordView,
    VerifyResetOTPView,
    ResetPasswordConfirmView,
    ChangePasswordView,
    Enable2FAView,
    Verify2FAView,
    MeView,
   
)

urlpatterns = [
    # 🔹 Registration & OTP
    path('auth/register/', RegisterView.as_view(), name='register'),
   
    path('auth/otp/resend/', ResendOTPView.as_view(), name='resend-otp'),
    path('auth/otp/verify/', VerifyOTPView.as_view(), name='verify-otp'),

    # 🔹 Login & Tokens
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/token/refresh/', RefreshTokenView.as_view(), name='refresh-token'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    # path('auth/login/google/', GoogleLoginApi.as_view(), name='google_login'),  # Updated path

    # 🔹 Password Management
    path('auth/password/forgot/', ForgotPasswordView.as_view(), name='forgot-password'),
    
    path('auth/password/reset/verify/', VerifyResetOTPView.as_view(), name='verify-reset-otp'),
    path('auth/password/reset/confirm/', ResetPasswordConfirmView.as_view(), name='reset-password-confirm'),
    path('auth/password/change/', ChangePasswordView.as_view(), name='change-password'),

    # 🔹 Two-Factor Authentication (2FA)
    path('auth/2fa/enable/', Enable2FAView.as_view(), name='enable-2fa'),
    path('auth/2fa/verify/', Verify2FAView.as_view(), name='verify-2fa'),

    # 🔹 User Profile
    path('auth/me/', MeView.as_view(), name='me'),



    # 🔹 Google OAuth
    path('auth/google/', google_login, name='google_login'),
    path('auth/google/callback/', google_callback, name='google_callback'),

]
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    is_email_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, blank=True, null=True)
    email_verification_code_expires_at = models.DateTimeField(blank=True, null=True)
    password_reset_code = models.CharField(max_length=6, blank=True, null=True)
    password_reset_code_expires_at = models.DateTimeField(blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True)
    gender = models.CharField(max_length=10, blank=True, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    is_2fa_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

    def generate_email_verification_code(self):
        """Generate and save OTP for email verification."""
        from django.utils.crypto import get_random_string
        code = get_random_string(length=6, allowed_chars='0123456789')
        self.email_verification_code = code
        self.email_verification_code_expires_at = timezone.now() + timedelta(minutes=5)
        self.save(update_fields=['email_verification_code', 'email_verification_code_expires_at'])
        
        # Save OTP to Token model
        token = Token.objects.filter(user=self, email=self.email, revoked=False).first()
        if token:
            token.otp = code
            token.otp_expires_at = self.email_verification_code_expires_at
            token.save(update_fields=['otp', 'otp_expires_at'])
            logger.info(f"Updated OTP {code} for user: {self.email} in Token model")
        else:
            Token.objects.create(
                user=self,
                email=self.email,
                otp=code,
                otp_expires_at=self.email_verification_code_expires_at,
                created_at=timezone.now()
            )
            logger.info(f"Created new Token with OTP {code} for user: {self.email}")
        return code

    def generate_password_reset_code(self):
        """Generate and save OTP for password reset."""
        from django.utils.crypto import get_random_string
        code = get_random_string(length=6, allowed_chars='0123456789')
        self.password_reset_code = code
        self.password_reset_code_expires_at = timezone.now() + timedelta(minutes=15)
        self.save(update_fields=['password_reset_code', 'password_reset_code_expires_at'])
        
        # Save OTP to Token model
        token = Token.objects.filter(user=self, email=self.email, revoked=False).first()
        if token:
            token.otp = code
            token.otp_expires_at = self.password_reset_code_expires_at
            token.save(update_fields=['otp', 'otp_expires_at'])
            logger.info(f"Updated OTP {code} for password reset for user: {self.email} in Token model")
        else:
            Token.objects.create(
                user=self,
                email=self.email,
                otp=code,
                otp_expires_at=self.password_reset_code_expires_at,
                created_at=timezone.now()
            )
            logger.info(f"Created new Token with OTP {code} for password reset for user: {self.email}")
        return code

class Token(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField()
    access_token = models.CharField(max_length=255, blank=True, null=True)
    refresh_token = models.CharField(max_length=255, blank=True, null=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_expires_at = models.DateTimeField(blank=True, null=True)  # Added to track OTP expiration
    access_token_expires_at = models.DateTimeField(blank=True, null=True)
    refresh_token_expires_at = models.DateTimeField(blank=True, null=True)
    revoked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - Token"

class PasswordResetSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return (timezone.now() - self.created_at) > timedelta(minutes=15)

    def __str__(self):
        return f"Password Reset Session for {self.user.email}"



class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    employee_id = models.CharField(max_length=20, unique=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='profile_images/', default='profile_images/default_profile.png')

    def __str__(self):
        return f"Profile for {self.user.email}"

    def save(self, *args, **kwargs):
        if not self.employee_id:
            last_count = Profile.objects.count() + 1
            self.employee_id = f"EMP{last_count:03d}"
        super().save(*args, **kwargs)
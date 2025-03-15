# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth import get_user_model
from django.conf import settings 


# Custom account manager
class UserManager(BaseUserManager):
    def create_user(self, first_name, last_name, username, email, password=None):
        if not email:
            raise ValueError('Users must provide an email address')
        if not username:
            raise ValueError('Users must provide a username')

        user = self.model(
            email=self.normalize_email(email),
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, email, username, password):
        user = self.create_user(
            email=self.normalize_email(email),
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        user.is_admin = True
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("farmer", "Farmer"),
        ("guest", "Guest"),
    ]

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    
    # ✅ Add role field (required)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="guest")

    # System fields
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return self.email


    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True


# Extended user profile
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    address_line_1 = models.CharField(max_length=100, blank=True)
    address_line_2 = models.CharField(max_length=100, blank=True)
    profile_picture = models.ImageField(blank=True, upload_to='userprofile', default='images/default-profile.png')
    city = models.CharField(max_length=50, blank=True)
    state = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=50, blank=True)


    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}'s Profile"

    def full_address(self):
        if self.address_line_2:
            return f"{self.address_line_1}, {self.address_line_2}"
        return self.address_line_1




User = get_user_model()

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=50)  # e.g., "login", "profile_update", "page_visit"
    activity_description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.activity_type} at {self.timestamp}"





class Notification(models.Model):
    """
    Stores notifications for users.
    Example: Payment Failed, AI Report Ready, Subscription Expiring, etc.
    """
    TYPE_CHOICES = [
        ("payment", "Payment Alert"),
        ("subscription", "Subscription Notice"),
        ("ai_report", "AI Report Ready"),
        ("system", "System Alert"),
        ("custom", "Custom Message"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="system")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)  # Users can mark notifications as read

    def __str__(self):
        return f"{self.user.email} - {self.notification_type} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ["-created_at"]

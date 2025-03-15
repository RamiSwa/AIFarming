from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from .models import User, UserProfile

# ✅ Automatically create a UserProfile and API Token when a new User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
        Token.objects.create(user=instance)  # ✅ Generate API Token
        print(f"✅ Profile created for {instance.email}, Token generated.")

# ✅ Save the UserProfile when the User is saved
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

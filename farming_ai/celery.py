import os
from celery import Celery

# Set Django settings module for Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "farming_ai.settings")

# ✅ Create Celery instance
celery_app = Celery("farming_ai")

# ✅ Load configuration from Django settings
celery_app.config_from_object("django.conf:settings", namespace="CELERY")

# ✅ Auto-discover tasks in all installed apps
celery_app.autodiscover_tasks()

@celery_app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")

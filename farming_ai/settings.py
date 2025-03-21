"""
Django settings for farming_ai project.

Generated by 'django-admin startproject' using Django 5.0.11.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import os
from pathlib import Path
from decouple import config
from distutils.util import strtobool



# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dsj68iiok02=&#q56$4+l4x73=3*i7z@e&7o_rwf#@^ei4i@$k")



DEBUG = bool(strtobool(os.getenv('DEBUG', 'False')))


# ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 
#     default='127.0.0.1,localhost,aifarming-production.up.railway.app,smartfarmai.online,www.smartfarmai.online'
# ).split(',')

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "aifarming-production.up.railway.app",
    "smartfarmai.online",
    "www.smartfarmai.online"
]


SITE_URL = os.getenv("SITE_URL", "https://smartfarmai.online")  # ✅ Update to your domain
FRONTEND_URL = "https://smartfarmai.online"  # ✅ Use new domain for frontend



# Application definition

INSTALLED_APPS = [
    'jazzmin',  # ✅ Modern UI for Django Admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 2FA

    # <- if you want phone number capability.

    # preventing brute-force attacks
    'axes',
    'defender',
    
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',  # Enable Token Authentication
    'corsheaders',
    'django_celery_results',
    
    
    # Custom Apps
    'accounts',
    'weather',
    'soil',
    'recommendations',
    'pages',
    'monetization',    
    'honeypot_admin',  
]



REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',  # ✅ Uses Django session cookies
        'rest_framework.authentication.TokenAuthentication',  # ✅ API Token Authentication
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',  # ✅ Requires login for API access
    ),
}


# Middleware Configuration
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    # ✅ Static Files Middleware (for WhiteNoise)
    "whitenoise.middleware.WhiteNoiseMiddleware",

    # ✅ Session & Authentication Middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # ✅ CORS Middleware (should be near the top)
    'corsheaders.middleware.CorsMiddleware',

    # ✅ Django Security Middleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # ✅ Custom Error Handling Middleware
    # 'django.middleware.common.BrokenLinkEmailsMiddleware', 
    
    # ✅ Django Messages Middleware
    'django.contrib.messages.middleware.MessageMiddleware',

    # ✅ Third-Party Middleware
    'axes.middleware.AxesMiddleware',

    # ✅ Custom Middleware (Ensure correct path)
    "farming_ai.middleware.BlockWordPressScansMiddleware", 
    "farming_ai.middleware.RestrictAdminAccessMiddleware",  
]



# CORS & CSRF Settings
CORS_ALLOW_CREDENTIALS = True  # ✅ Allows credentials (cookies, auth headers)
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS', 
    default='http://127.0.0.1:8000,https://aifarming-production.up.railway.app,https://smartfarmai.online,https://www.smartfarmai.online'
).split(',')


CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS', 
    default='https://aifarming-production.up.railway.app,http://127.0.0.1:8000,https://smartfarmai.online,https://www.smartfarmai.online'
).split(',')


# ✅ Allow All Methods
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]



# ✅ Use database-backed session storage
SESSION_ENGINE = "django.contrib.sessions.backends.db"  

# ✅ Cookie Settings
SESSION_COOKIE_NAME = "sessionid"  # Standard session cookie name
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # ✅ Forces logout when browser closes
SESSION_COOKIE_HTTPONLY = True  # ✅ Prevents JavaScript from accessing session cookies

# ✅ CSRF Settings (Important)
CSRF_COOKIE_HTTPONLY = False


# ✅ CORS Os.getenvuration
# ✅ Allow X-Auth-Token in responses
CORS_ALLOW_HEADERS = ["Authorization", "Content-Type", "X-CSRFToken"]



# ✅ Enable CORS for your frontend (Adjust as needed)
# CORS & CSRF Settings

# ✅ Allow X-Auth-Token in Django's security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True


ROOT_URLCONF = 'farming_ai.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'farming_ai.wsgi.application'

AUTH_USER_MODEL = 'accounts.User'

# Axes Os.getenvuration (Brute-force protection)
AXES_FAILURE_LIMIT = 5  # Lockout after 5 failed attempts
AXES_COOLOFF_TIME = 30  # Allow retry after 30 minutes
AXES_RESET_ON_SUCCESS = True  # ✅ Reset failure count after a successful login
AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]  # ✅ Track by username + IP



# Defender Os.getenvuration (Another layer of brute-force protection)
DEFENDER_LOGIN_FAILURE_LIMIT = 5
DEFENDER_COOLOFF_TIME = 60  # 1 hour lockout

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',  # ✅ Required for django-axes
    'django.contrib.auth.backends.ModelBackend',  # ✅ Default Django authentication backend
]

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},

    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# ✅ PostgreSQL Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv("POSTGRES_DB", "railway"),
        'USER': os.getenv("POSTGRES_USER", "postgres"),
        'PASSWORD': os.getenv("POSTGRES_PASSWORD", "EUuywVfrxLjHXmOadsZTuUDeWQCmNzwo"),
        'HOST': os.getenv("PGHOST", "shuttle.proxy.rlwy.net"),
        'PORT': os.getenv("PGPORT", "32356"),
    }
}

if not DATABASES['default']['NAME']:
    raise Exception("PostgreSQL Database not found. Check Railway environment variables.")

# ✅ Static Files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# ✅ WhiteNoise for Static Files (Optimized)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ✅ Enable Cloudflare R2 for Media Storage
USE_CLOUDFLARE_R2 = True  # Ensure R2 is enabled

if USE_CLOUDFLARE_R2:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = "ai-farming-storage"
    AWS_S3_ENDPOINT_URL = "https://5444121f8cb4233466360f77347d47e9.r2.cloudflarestorage.com"

    # ✅ Use the new custom domain instead of R2.dev
    MEDIA_URL = "https://cdn.smartfarmai.online/"
else:
    MEDIA_URL = "/media/"
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

from django.contrib.messages import constants as messages

MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',  # Maps DEBUG level to Bootstrap's 'alert-secondary'
    messages.INFO: 'info',        # Maps INFO level to 'alert-info'
    messages.SUCCESS: 'success',  # Maps SUCCESS level to 'alert-success'
    messages.WARNING: 'warning',  # Maps WARNING level to 'alert-warning'
    messages.ERROR: 'danger',     # Maps ERROR level to 'alert-danger'
}

# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# SMTP os.getenvuration
# SMTP os.getenvuration
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = os.getenv('EMAIL_PORT')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS')

# Email credentials
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')  # your email address
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')  # your app-specific password

# Email recipient for contact notifications (set this in your .env file)
CONTACT_NOTIFICATION_EMAIL = os.getenv('CONTACT_NOTIFICATION_EMAIL', default='contact@smartfarmai.online')


# Path to the trained models directory
TRAINED_MODELS_DIR = os.path.join(BASE_DIR, "trained_models")

# OpenCage API Key
OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY", default="")
# Celery settings


# ✅ Use Redis as the Celery task broker (message queue)
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    "redis://default:sygEFwXsJDTUehgOwKEYWQUdPdfffCfO@aifarming.railway.internal:6379"
)

# ✅ Use PostgreSQL to store Celery task results
CELERY_RESULT_BACKEND = "django-db"

# ✅ Ensure Celery works properly
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"



# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'root': {
#         'handlers': ['console'],
#         'level': 'INFO',
#     },
# }

# Ensure Django Admin uses 2FA login separately
# Regular users login/logout
# Regular users login/logout
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/accounts/dashboard/"
LOGOUT_REDIRECT_URL = "/accounts/login/"


# Admin panel login/logout (with 2FA)


# Ensure admins are redirected correctly
AXES_LOCKOUT_TEMPLATE = "admin/lockout.html"  # Custom lockout page (if needed)



JAZZMIN_SETTINGS = {
    "site_title": "AI Farming Dashboard",
    "site_header": "AI Farming Admin",
    "site_brand": "AI Farming",
    "welcome_sign": "Welcome to AI Farming Admin Panel",
    "site_logo": "images/logo_AI_Farming_round.png",  # ✅ Upload logo in static/images/
    "site_icon": "images/favicon.ico",  # ✅ Change browser tab icon
    "navigation_expanded": False,  # ✅ Sidebar starts collapsed
    "theme": "darkly",  # ✅ Options: "darkly", "cosmo", "flatly", "lux"
    "show_ui_builder": True,  # ✅ Enables UI customization
    "navigation_expanded": False,  # ✅ Collapsible sidebar
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
    ],
}


JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_fixed": True,
    "actions_sticky_top": True,  # ✅ Keep action buttons visible
    "body_small_text": False,  # ✅ Improve readability
    "sidebar_fixed": False,  # ✅ Allow sidebar to collapse properly
}


JAZZMIN_UI_TWEAKS["css_classes"] = {"body": "admin-custom"}

JAZZMIN_SETTINGS["custom_links"] = {
    "accounts": [
        {"name": "View Users", "url": "admin:accounts_user_changelist", "icon": "fas fa-user"},
        {"name": "Add User", "url": "admin:accounts_user_add", "icon": "fas fa-user-plus"},
    ],
    "orders": [
        {"name": "View Orders", "url": "admin:monetization_order_changelist", "icon": "fas fa-shopping-cart"},
    ],
}



SESSION_COOKIE_AGE = 1800  # ✅ Auto logout after 30 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_SSL_REDIRECT = False
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

JAZZMIN_SETTINGS["topmenu_links"] += [
    {"name": "Monetization Dashboard", "url": "monetization_dashboard", "permissions": ["auth.view_user"]},
]


JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": True,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-primary",
    "navbar": "navbar-navy navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": False,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success"
    },
    "actions_sticky_top": False,
    "css_classes": {
        "body": "admin-custom"
    }
}

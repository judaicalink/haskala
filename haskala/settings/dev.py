from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-h_^ko*b=)ayhfhdus(%$=frf8hexku0kzuhpxxfe_ejg11)@nz"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "web"]

# Trust the nginx-fronted dev origins so admin/dashboard POSTs pass CSRF.
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


try:
    from .local import *
except ImportError:
    pass

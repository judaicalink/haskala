from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-h_^ko*b=)ayhfhdus(%$=frf8hexku0kzuhpxxfe_ejg11)@nz"

# SECURITY WARNING: define the correct hosts in production!
ALLOWED_HOSTS = []

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


try:
    from .local import *
except ImportError:
    pass

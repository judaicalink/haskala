from .base import *  # noqa: F401,F403

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

# Dev sends through the bundled MailHog service (host:port from
# base.py's EMAIL_HOST / EMAIL_PORT env-overrides; in the docker
# stack the web container reaches MailHog as mailserver:1025 and
# the inbox UI is at http://localhost:8025/). MailHog is a plain
# SMTP sink — no STARTTLS / SSL.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False

try:
    from .local import *  # noqa: F401,F403
except ImportError:
    pass

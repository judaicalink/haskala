"""
Production settings layer on top of base.

Everything HTTPS / cookie-secure / HSTS related lives here so the dev
stack on http://localhost:8080 keeps working untouched. Every flag is
env-overridable so a staging environment can dial each one back.
"""
from .base import *  # noqa: F401,F403
from .base import env  # explicit so linters don't flag _env usage as undefined

DEBUG = False

# `ALLOWED_HOSTS` must list every public hostname under which Django
# serves. Comma-separated env var ALLOWED_HOSTS, e.g.
#   ALLOWED_HOSTS=haskala-library.net,www.haskala-library.net
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# nginx terminates TLS; Django needs to see the original scheme so that
# request.is_secure() returns True. Match the header nginx already sets
# in nginx.conf: `proxy_set_header X-Forwarded-Proto $scheme;`.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Force every public URL onto https://, redirecting plain HTTP requests.
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)

# Cookies must only travel over TLS in production. SameSite=Lax keeps
# logged-in sessions usable across same-site links.
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)

# CSRF_TRUSTED_ORIGINS must include the public origins under which the
# admin is reachable, otherwise admin POSTs through the proxy fail
# with "Origin checking failed". Same comma-separated env knob.
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# HSTS: tell browsers to remember https for the next year, including
# every subdomain, and to consider opting into the HSTS preload list.
# Start with one year — bring this down only if you need to roll back.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)

# Modern hardening defaults.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = env(
    "SECURE_REFERRER_POLICY", default="strict-origin-when-cross-origin"
)
X_FRAME_OPTIONS = env("X_FRAME_OPTIONS", default="DENY")

try:
    from .local import *  # noqa: F401,F403
except ImportError:
    pass

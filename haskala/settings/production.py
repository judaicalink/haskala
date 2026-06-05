from .base import *  # noqa: F401,F403

DEBUG = False

try:
    from .local import *  # noqa: F401,F403
except ImportError:
    pass

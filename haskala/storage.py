"""
Custom STATICFILES storage backend.

ManifestStaticFilesStorage hashes every collected file and rewrites
url(...) references inside CSS to point at the hashed sibling. Strict
mode is on by default and aborts collectstatic on the first
unresolvable url(...) — a problem for our tree, which still carries
legacy CSS that references images we no longer ship.

The TolerantManifestStaticFilesStorage subclass disables strict mode,
so dangling references log a warning and the build keeps going. The
public site still benefits from the content-hashed filenames and the
cache-invalidation guarantee they bring.
"""
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class TolerantManifestStaticFilesStorage(ManifestStaticFilesStorage):
    manifest_strict = False

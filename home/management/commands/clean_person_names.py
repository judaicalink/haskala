"""
Strip leading punctuation and parens-wrapped titles from Person name
fields. The Drupal-6 importer left strings like ``(Dr.) NAME`` or
``"NAME"`` in pref_label / german_name / hebrew_name; the latter
patterns aren't legitimate name forms and read as broken on the
public detail page.

Transforms applied per field (pref_label, german_name, hebrew_name):

1. Drop one leading ``(...)`` group + the following whitespace
   (handles ``(Dr. med.) Foo`` → ``Foo``).
2. Strip surrounding ``"..."`` quotes (handles ``"Bar"`` → ``Bar``).
3. Strip leading whitespace and stray punctuation
   (``, ``  ``. `` etc.).
4. Collapse runs of internal whitespace.

The command is idempotent and prints what it would do; pass
``--apply`` to commit the changes.
"""
from __future__ import annotations

import re

from django.core.management.base import BaseCommand

from home.models import Person


_PARENS_PREFIX = re.compile(r"^\([^)]*\)\s*")
_QUOTE_WRAP = re.compile(r'^"(.*)"$')
# Leading punctuation strip. Includes the hyphen because `(Feder)-
# Guttmann` would otherwise resolve to `-Guttmann` after the parens
# prefix is dropped.
_LEADING_JUNK = re.compile(r"^[\s,.;:'\"\-]+")
_MULTI_WS = re.compile(r"\s{2,}")


def clean(value: str) -> str:
    if not value:
        return value
    out = value
    out = _PARENS_PREFIX.sub("", out)
    m = _QUOTE_WRAP.match(out)
    if m:
        out = m.group(1)
    out = _LEADING_JUNK.sub("", out)
    out = _MULTI_WS.sub(" ", out).strip()
    return out


class Command(BaseCommand):
    help = "Strip leading punctuation / parens-wrapped titles from Person names."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Commit the changes. Without it the command runs as a dry-run.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        changed = []
        for p in Person.objects.all():
            updates = {}
            for fname in ("pref_label", "german_name", "hebrew_name"):
                current = getattr(p, fname, "") or ""
                new = clean(current)
                if new != current:
                    updates[fname] = (current, new)
            if updates:
                changed.append((p, updates))

        for p, updates in changed:
            for fname, (old, new) in updates.items():
                self.stdout.write(
                    f"{p.pk} {fname}: {old!r} -> {new!r}"
                )

        if not apply:
            self.stdout.write(self.style.WARNING(
                f"DRY RUN: would update {len(changed)} Person rows. "
                f"Re-run with --apply to commit."
            ))
            return

        for p, updates in changed:
            for fname, (_old, new) in updates.items():
                setattr(p, fname, new)
            p.save(update_fields=list(updates))

        self.stdout.write(self.style.SUCCESS(
            f"Updated {len(changed)} Person rows."
        ))

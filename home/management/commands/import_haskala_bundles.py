import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from home.models import (
    Book,
    Person,
    City,
    MentionDescription,
    ProductionRole,
    Edition,
    Translation,
    Preface,
    Mention,
    Production,
)


# ---- Helper-Funktionen -----------------------------------------------------


def parse_int(value):
    """Konvertiert Strings wie '123', '123.0', '' → int oder None."""
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        # manche Exporte haben '402.0'
        if "." in value:
            return int(float(value))
        return int(value)
    except ValueError:
        return None


def parse_bool(value):
    """
    Interpretiert typische Drupal- / CSV-Werte als bool:
    '', None, '0' -> False
    '1', 't', 'true', 'True' -> True
    """
    if value is None:
        return False
    value = str(value).strip().lower()
    if value in ("1", "t", "true", "yes", "y"):
        return True
    return False


def parse_timestamp(value):
    """Drupal-UNIX-Timestamp (Sekunden) →

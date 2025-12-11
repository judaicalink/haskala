import csv
import os
from django.core.management.base import BaseCommand, CommandError

from home.models import (
    Person,
    Gender,
    Occupation,
    City,
)

def parse_tid(value):
    """
    Wandelt TID-Werte wie '402', '402.0', ' 402 ', '' in int oder None um.
    """
    if value is None:
        return None

    v = str(value).strip()

    if v == "":
        return None

    try:
        # Float-Fixes: '402.0' → 402
        return int(float(v))
    except ValueError:
        return None



class Command(BaseCommand):
    help = "Importiert Personen aus einer CSV (Export aus Drupal via Jupyter)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            required=True,
            help="Pfad zur Personen-CSV",
        )

    def handle(self, *args, **options):

        csv_file = options["file"]

        if not os.path.exists(csv_file):
            raise CommandError(f"CSV nicht gefunden: {csv_file}")

        created = 0
        updated = 0

        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Pflichtfelder
                nid = row.get("nid")
                vid = row.get("vid")

                if not nid:
                    continue

                legacy_nid = int(nid)
                legacy_vid = int(vid) if vid else None

                # Namensfelder (variieren je nach Export)
                title = (row.get("title") or "").strip()
                pref_label = (row.get("pref_label") or title).strip()
                german_name = (row.get("german_name") or "").strip()
                hebrew_name = (row.get("hebrew_name") or "").strip()

                # Gender
                gender = None
                gender_tid = parse_tid(row.get("gender_tid"))

                if gender_tid is not None:
                    try:
                        gender = Gender.objects.get(legacy_tid=gender_tid)
                    except Gender.DoesNotExist:
                        pass

                # Place of birth
                pob = None
                pob_tid = parse_tid(row.get("place_of_birth_tid"))
                if pob_tid is not None:
                    try:
                        pob = City.objects.get(legacy_tid=pob_tid)
                    except City.DoesNotExist:
                        pass

                # Place of death
                pod = None
                pod_tid = parse_tid(row.get("place_of_death_tid"))
                if pod_tid is not None:
                    try:
                        pod = City.objects.get(legacy_tid=pod_tid)
                    except City.DoesNotExist:
                        pass

                # Person erstellen/aktualisieren
                person, flag = Person.objects.update_or_create(
                    legacy_nid=legacy_nid,
                    defaults={
                        "legacy_vid": legacy_vid,
                        "pref_label": pref_label,
                        "german_name": german_name,
                        "hebrew_name": hebrew_name,
                        "gender": gender,
                        "place_of_birth": pob,
                        "place_of_death": pod,
                    }
                )

                if flag:
                    created += 1
                else:
                    updated += 1

                # Occupations (M2M)
                occ_raw = row.get("occupation_tid") or row.get("occupation_tids")
                person.occupations.clear()

                if occ_raw:
                    parts = (
                        occ_raw.replace(",", ";")
                        .replace(" ", "")
                        .split(";")
                    )

                    for part in parts:
                        tid_int = parse_tid(part)
                        if tid_int is None:
                            continue
                        try:
                            occ = Occupation.objects.get(legacy_tid=tid_int)
                            person.occupations.add(occ)
                        except Occupation.DoesNotExist:
                            pass

        self.stdout.write(self.style.SUCCESS(
            f"Personen importiert: {created} neu, {updated} aktualisiert."
        ))

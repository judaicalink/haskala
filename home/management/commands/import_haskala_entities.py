from django.core.management.base import BaseCommand, CommandError
import csv
import os

from home.models import (
    Person,
    Book,
    Edition,
    Translation,
    Preface,
    Mention,
    Production,
    City,
    Language,
)


class Command(BaseCommand):
    help = "Importiert Personen, Bücher und Hilfsmodelle aus Export-CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-dir",
            type=str,
            help="Basisverzeichnis für die CSV-Dateien",
            required=True,
        )

    def _open_csv(self, path):
        if not os.path.exists(path):
            raise CommandError(f"CSV-Datei nicht gefunden: {path}")
        self.stdout.write(self.style.NOTICE(f"Lese {path} ..."))
        return open(path, newline="", encoding="utf-8")

    # --------- Beispiel: Personen ----------

    def import_persons(self, base_dir):
        path = os.path.join(base_dir, "persons_for_django.csv")  # anpassen
        created = 0
        updated = 0

        with self._open_csv(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Hier musst du die Spaltennamen an deine CSV anpassen!
                nid = row.get("nid") or row.get("legacy_nid")
                vid = row.get("vid") or row.get("legacy_vid")
                if not nid:
                    continue

                legacy_nid = int(nid)
                legacy_vid = int(vid) if vid else None

                pref_label = (row.get("pref_label") or row.get("title") or "").strip()
                german_name = (row.get("german_name") or "").strip()
                hebrew_name = (row.get("hebrew_name") or "").strip()

                person, created_flag = Person.objects.update_or_create(
                    legacy_nid=legacy_nid,
                    defaults={
                        "legacy_vid": legacy_vid,
                        "pref_label": pref_label,
                        "german_name": german_name,
                        "hebrew_name": hebrew_name,
                        # hier ggf. weitere Felder aus deiner CSV
                    },
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Person: {created} erstellt, {updated} aktualisiert."
            )
        )

    # --------- Beispiel: Bücher ----------

    def import_books(self, base_dir):
        path = os.path.join(base_dir, "books_for_django.csv")  # anpassen
        created = 0
        updated = 0

        with self._open_csv(path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                nid = row.get("nid") or row.get("legacy_nid")
                vid = row.get("vid") or row.get("legacy_vid")
                if not nid:
                    continue

                legacy_nid = int(nid)
                legacy_vid = int(vid) if vid else None

                title = (row.get("title") or row.get("name") or "").strip()
                subtitle = (row.get("subtitle") or "").strip()
                full_title = (row.get("full_title") or "").strip()

                # Beispiel: Publication place über legacy_tid → City
                pub_place_tid = row.get("publication_place_tid")
                publication_place = None
                if pub_place_tid:
                    try:
                        publication_place = City.objects.get(legacy_tid=int(pub_place_tid))
                    except City.DoesNotExist:
                        publication_place = None

                book, created_flag = Book.objects.update_or_create(
                    legacy_nid=legacy_nid,
                    defaults={
                        "legacy_vid": legacy_vid,
                        "name": title,
                        "subtitle": subtitle,
                        "full_title": full_title,
                        "publication_place": publication_place,
                        # hier weitere Felder mappen
                    },
                )

                # Beispiel: Sprachen (tid-Liste → ManyToMany)
                language_tids = (row.get("language_tids") or "").split(";")
                book.languages.clear()
                for tid in language_tids:
                    tid = tid.strip()
                    if not tid:
                        continue
                    try:
                        lang = Language.objects.get(legacy_tid=int(tid))
                        book.languages.add(lang)
                    except Language.DoesNotExist:
                        continue

                if created_flag:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Book: {created} erstellt, {updated} aktualisiert."
            )
        )

    # --------- handle() ----------

    def handle(self, *args, **options):
        base_dir = options["base_dir"]

        if not os.path.isdir(base_dir):
            raise CommandError(f"{base_dir} ist kein Verzeichnis")

        # Reihenfolge: erst Personen, dann Bücher, dann Hilfsmodelle
        self.import_persons(base_dir)
        self.import_books(base_dir)
        # hier kannst du analog import_editions, import_translations, ...
        # implementieren und aufrufen.

        self.stdout.write(self.style.SUCCESS("Entity-Import abgeschlossen."))

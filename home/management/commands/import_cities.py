import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from home.models import City, Geolocation


class Command(BaseCommand):
    help = "Importiert Cities + Geolocation aus der exportierten CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Pfad zur cities_with_geolocation.csv",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"Datei nicht gefunden: {csv_path}"))
            return

        created_cities = 0
        created_geos = 0

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                name = row.get("name", "").strip()
                if not name:
                    continue

                # City anlegen (oder wiederverwenden, falls Name schon existiert)
                city, city_created = City.objects.get_or_create(
                    name=name,
                )

                if city_created:
                    created_cities += 1

                # Geolocation nur anlegen, wenn lat/lng gesetzt sind
                lat = row.get("field_geolocation_lat")
                lng = row.get("field_geolocation_lng")

                if lat or lng:
                    geo, geo_created = Geolocation.objects.get_or_create(
                        city=city,
                        defaults={
                            "lat": float(lat) if lat else None,
                            "lng": float(lng) if lng else None,
                            "lat_sin": float(row["field_geolocation_lat_sin"]) if row.get("field_geolocation_lat_sin") else None,
                            "lat_cos": float(row["field_geolocation_lat_cos"]) if row.get("field_geolocation_lat_cos") else None,
                            "lng_rad": float(row["field_geolocation_lng_rad"]) if row.get("field_geolocation_lng_rad") else None,
                        },
                    )
                    if geo_created:
                        created_geos += 1

        self.stdout.write(self.style.SUCCESS(
            f"Fertig. Cities neu: {created_cities}, Geolocations neu: {created_geos}"
        ))

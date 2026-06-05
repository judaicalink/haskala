import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from home.models import City, Geolocation


class Command(BaseCommand):
    help = "Import cities + geolocation from the exported CSV"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="Path to cities_with_geolocation.csv",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])

        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {csv_path}"))
            return

        created_cities = 0
        created_geos = 0

        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                name = row.get("name", "").strip()
                if not name:
                    continue

                # Create city (or reuse if name already exists)
                city, city_created = City.objects.get_or_create(
                    name=name,
                )

                if city_created:
                    created_cities += 1

                # Only create geolocation if lat/lng are set
                lat = row.get("field_geolocation_lat")
                lng = row.get("field_geolocation_lng")

                if lat or lng:
                    lat_sin = row.get("field_geolocation_lat_sin")
                    lat_cos = row.get("field_geolocation_lat_cos")
                    lng_rad = row.get("field_geolocation_lng_rad")
                    geo, geo_created = Geolocation.objects.get_or_create(
                        city=city,
                        defaults={
                            "lat": float(lat) if lat else None,
                            "lng": float(lng) if lng else None,
                            "lat_sin": float(lat_sin) if lat_sin else None,
                            "lat_cos": float(lat_cos) if lat_cos else None,
                            "lng_rad": float(lng_rad) if lng_rad else None,
                        },
                    )
                    if geo_created:
                        created_geos += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. New cities: {created_cities}, new geolocations: {created_geos}"
        ))

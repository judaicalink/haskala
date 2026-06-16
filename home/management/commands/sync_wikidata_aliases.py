"""
Pull Wikidata labels + aliases for every catalog row that carries a
``wikidata_id`` and upsert them into the AliasName table so the
public site can surface historical/regional name variants ("Lemberg"
/ "Lwów" / "Львів" / "Lviv" all on the same City row).

Per anchored row the command:

1. Fetches the Wikidata entity JSON.
2. Reads ``labels`` (preferred name per language) and ``aliases``
   (additional accepted forms per language).
3. Restricts to the Haskala-relevant language whitelist (see
   ``LANGUAGES_OF_INTEREST``) so the table doesn't grow with
   labels in Vietnamese, Tagalog, etc. that nobody on the site
   reads.
4. Upserts each (target, language, value) triple. Labels become
   ``is_preferred=True``; aliases ``is_preferred=False``.
   ``source="wikidata"``.
5. Never touches rows whose source is ``manual`` -- curator-set
   aliases survive every sync, because the dedup check only
   considers (language, value) and the upsert never overwrites an
   existing row.

Idempotent. Re-running against an already-synced row only writes
the deltas. The (target, language, value) unique constraint at the
DB layer is the ultimate safety net.

Only City is processed today. Person / Topic / Occupation will be
covered once the manual Person cleanup pass is done; the per-model
loop already iterates a TARGET_MODELS list to make extension a
one-liner.

Rate-limited (default 0.6s between requests) and identifies itself
in the User-Agent per Wikidata's API etiquette.
"""
from __future__ import annotations

import time

import requests
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from home.models import AliasName, City


USER_AGENT = (
    "haskala-catalog/1.0 "
    "(https://github.com/judaicalink/haskala; "
    "benjamin.schnabel@ephe.psl.eu) "
    "django-management-command"
)
ENTITY_URL = (
    "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
)


# Whitelist of languages that the Haskala catalog audience is
# expected to read. Wikidata items routinely carry labels in 100+
# languages -- restricting keeps the AliasName table focused and
# the search index small.
LANGUAGES_OF_INTEREST = {
    "be",   # Belarusian -- Brest, Hrodna
    "cs",   # Czech -- Brno, Praha
    "de",   # German -- primary catalog language
    "en",   # English -- public lingua franca
    "fr",   # French -- Alsace
    "he",   # Hebrew -- primary Jewish audience
    "hu",   # Hungarian -- Pressburg, Budapest
    "it",   # Italian -- Padua, Mantua
    "la",   # Latin -- early-modern texts
    "lt",   # Lithuanian -- Vilnius
    "nl",   # Dutch -- Amsterdam, Den Haag
    "pl",   # Polish -- many catalog cities
    "ro",   # Romanian -- Arad
    "ru",   # Russian -- Eastern European corridor
    "sk",   # Slovak -- Bratislava
    "uk",   # Ukrainian -- Lviv, Lemberg
    "yi",   # Yiddish -- historical Maskil writings
}


# Target models considered. Initially only City; Person etc. join
# when their wikidata_id pass is complete.
TARGET_MODELS = [
    ("City", City),
]


class Command(BaseCommand):
    help = (
        "Pull labels + aliases from Wikidata for every anchored "
        "row and upsert them into the AliasName table."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Commit the upserts. Default: dry-run.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.6,
            help="Seconds to sleep between Wikidata requests "
                 "(politeness). Default 0.6.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Process at most N anchored rows. 0 = all.",
        )

    def handle(self, *args, **options):
        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT

        for label, model_cls in TARGET_MODELS:
            self._sync_one_model(
                session, label, model_cls,
                apply=options["apply"],
                delay=options["delay"],
                limit=options["limit"],
            )

    def _sync_one_model(
        self, session, label, model_cls, *, apply, delay, limit,
    ):
        ct = ContentType.objects.get_for_model(model_cls)
        qs = (
            model_cls.objects
            .filter(live=True)
            .exclude(wikidata_id="")
            .order_by("name")
        )
        if limit:
            qs = qs[: limit]
        rows = list(qs)

        self.stdout.write(self.style.WARNING(
            f"[{label}] {len(rows)} anchored rows -- "
            f"apply={apply}, delay={delay}s"
        ))

        created_total = noop_total = noent_total = 0
        for idx, row in enumerate(rows, 1):
            entity = self._fetch_entity(session, row.wikidata_id)
            time.sleep(delay)
            if entity is None:
                noent_total += 1
                self.stdout.write(
                    f"  [{idx}/{len(rows)}] {row.name:30} "
                    f"-> {row.wikidata_id:10} NO ENTITY"
                )
                continue

            triples = self._extract_triples(entity)

            existing = set(
                AliasName.objects
                .filter(content_type=ct, object_id=str(row.pk))
                .values_list("language", "value")
            )

            created_here = 0
            for lang, value, is_pref in triples:
                if (lang, value) in existing:
                    continue
                created_here += 1
                if apply:
                    AliasName.objects.create(
                        content_type=ct,
                        object_id=str(row.pk),
                        language=lang,
                        value=value,
                        source="wikidata",
                        is_preferred=is_pref,
                    )
            if created_here:
                created_total += created_here
                self.stdout.write(
                    f"  [{idx}/{len(rows)}] {row.name:30} "
                    f"-> {row.wikidata_id:10} +{created_here} aliases"
                )
            else:
                noop_total += 1

        self.stdout.write(self.style.SUCCESS(
            f"[{label}] created={created_total}, "
            f"noop(no_new)={noop_total}, "
            f"no_entity={noent_total}"
        ))
        if not apply:
            self.stdout.write(self.style.WARNING(
                "DRY RUN: re-run with --apply to commit."
            ))

    def _extract_triples(self, entity):
        """Materialize (lang, value, is_preferred) tuples for the
        labels + aliases in the whitelist languages. Labels become
        is_preferred=True; aliases is_preferred=False.

        Dedups within the fetch: Wikidata sometimes lists the same
        spelling as both the language's preferred label AND as one
        of its aliases (e.g. ``Бжег`` for Brieg in Ukrainian). The
        label-pass wins because it iterates first and the
        ``seen`` set short-circuits the alias-pass for identical
        (lang, value) pairs."""
        seen = {}
        labels = entity.get("labels", {}) or {}
        aliases = entity.get("aliases", {}) or {}

        for lang, blob in labels.items():
            if lang not in LANGUAGES_OF_INTEREST:
                continue
            val = (blob or {}).get("value", "").strip()
            if val:
                seen[(lang, val)] = True

        for lang, blob_list in aliases.items():
            if lang not in LANGUAGES_OF_INTEREST:
                continue
            for blob in (blob_list or []):
                val = (blob or {}).get("value", "").strip()
                if val:
                    seen.setdefault((lang, val), False)

        return [
            (lang, val, is_pref)
            for (lang, val), is_pref in seen.items()
        ]

    def _fetch_entity(self, session, qid):
        try:
            r = session.get(ENTITY_URL.format(qid=qid), timeout=15)
            r.raise_for_status()
            return r.json().get("entities", {}).get(qid)
        except (requests.RequestException, ValueError) as exc:
            self.stderr.write(f"  entity error for {qid}: {exc}")
            return None

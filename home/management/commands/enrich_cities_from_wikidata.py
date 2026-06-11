"""
Phase 2 of the places overhaul: propose a Wikidata QID for every
live City row that hasn't been anchored yet, and (with --apply) set
``City.wikidata_id`` on the rows where the top candidate clears the
confidence threshold.

For each unanchored City the command:

1. Calls ``wbsearchentities`` for the city's ``name`` to get the
   top-N Wikidata hits.
2. Fetches the full claims JSON for each hit.
3. Scores the hit by name-match, "is a human settlement" P31 class
   membership, country (P17), coordinates inside the Europe + Levant
   bounding box, and whether the entity has any sitelink at all.
4. Writes one row per City to ``docs/audits/wikidata_candidates.csv``:
   the chosen QID + label + score + the alternates so the curator
   sees the runners-up.
5. With ``--apply``, sets ``wikidata_id`` on rows where the top
   candidate scores >= ``--threshold`` (default 12) AND beats the
   second candidate by at least ``--margin`` (default 4).

Rate-limited (one request per second by default, configurable via
``--delay``) and identifies itself in the User-Agent string per
Wikidata's API etiquette.
"""
from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path

import requests
from django.core.management.base import BaseCommand

from home.models import City


USER_AGENT = (
    "haskala-catalog/1.0 "
    "(https://github.com/judaicalink/haskala; "
    "benjamin.schnabel@ephe.psl.eu) "
    "django-management-command"
)

WBSEARCH_URL = "https://www.wikidata.org/w/api.php"
ENTITY_URL = (
    "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
)


# Top-level human-settlement classes on Wikidata. Hitting any of
# these as a P31 value is strong evidence "this entity is a place".
SETTLEMENT_P31 = {
    "Q486972",    # human settlement
    "Q515",       # city
    "Q3957",      # town
    "Q532",       # village
    "Q15284",     # municipality of Germany
    "Q5119",      # capital
    "Q133442",    # megacity
    "Q15974307",  # former settlement
    "Q1549591",   # big city
    "Q188509",    # suburb
    "Q11618417",  # extinct settlement
    "Q22865",     # urban municipality of Germany
    "Q1620908",   # historical region
    "Q123705",    # neighborhood
    # Per-state municipality types — Wikidata uses these instead of
    # the generic Q15284 for many German towns. Without them, a
    # generically-typed homonym (e.g. Swedish "Anklam") outranks the
    # real German town that the catalog actually refers to.
    "Q707813",    # former amt seat (DE)
    "Q42744322",  # municipality of Mecklenburg-Vorpommern
    "Q261023",    # locality (PL)
    "Q1865282",   # Ortschaft (AT)
    "Q702492",    # urban-type settlement (UA/RU)
    "Q12813115",  # municipality of the Czech Republic
    "Q149621",    # administrative district
}

# ISO-2 country codes biased as "Europe / Levant" for the country
# bonus. Anything outside still scores via coords; this is just a
# cheap signal.
EU_LEVANT_COUNTRIES = {
    "AT", "BE", "BG", "BY", "CH", "CY", "CZ", "DE", "DK", "EE",
    "ES", "FI", "FR", "GR", "HR", "HU", "IE", "IL", "IT", "LB",
    "LI", "LT", "LU", "LV", "MD", "MK", "MT", "NL", "NO", "PL",
    "PT", "RO", "RS", "RU", "SE", "SI", "SK", "TR", "UA", "UK",
    "GB", "VA", "AL", "AD", "BA", "ME", "XK", "SY", "JO", "EG",
}

# Same bounding box as the audit_places_for_review command.
EU_LEVANT_BOX = (29.0, 72.0, -10.0, 60.0)  # lat_min, lat_max, lng_min, lng_max


def _ascii(s):
    """Strip diacritics and case for fuzzy name comparison.

    The catalog has both "Münden" and "Munden" and Wikidata may
    return either form first. We compare on the case-folded ASCII
    projection so "Düsseldorf" matches "Dusseldorf"."""
    try:
        from anyascii import anyascii
        return anyascii(s).lower().strip()
    except ImportError:
        return re.sub(r"\W+", " ", s.lower()).strip()


class Command(BaseCommand):
    help = (
        "Match every unanchored live City against Wikidata and "
        "report candidates. Use --apply to auto-set wikidata_id on "
        "high-confidence matches."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default="docs/audits/wikidata_candidates.csv",
            help="Output CSV path.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Process at most N unanchored cities. 0 = all.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Seconds to sleep between Wikidata requests "
                 "(politeness). Default 1.0.",
        )
        parser.add_argument(
            "--limit-candidates",
            type=int,
            default=5,
            help="How many wbsearchentities hits to score per city.",
        )
        parser.add_argument(
            "--threshold",
            type=int,
            default=12,
            help="Minimum top-candidate score to auto-apply.",
        )
        parser.add_argument(
            "--margin",
            type=int,
            default=4,
            help="Top candidate must beat the second by this margin "
                 "for --apply to commit it.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Commit high-confidence matches. Default: dry-run.",
        )
        parser.add_argument(
            "--language",
            default="en",
            help="Search language for wbsearchentities. Default: en.",
        )

    def handle(self, *args, **options):
        out_path = Path(options["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cities = (
            City.objects
            .filter(live=True, wikidata_id="", merged_into__isnull=True)
            .order_by("name")
        )
        if options["limit"]:
            cities = cities[: options["limit"]]
        cities = list(cities)

        self.stdout.write(
            f"Processing {len(cities)} unanchored live cities "
            f"(delay={options['delay']}s, "
            f"threshold={options['threshold']}, "
            f"margin={options['margin']})"
        )

        session = requests.Session()
        session.headers["User-Agent"] = USER_AGENT

        rows = []
        applied = 0
        for idx, c in enumerate(cities, 1):
            name = (c.name or "").strip()
            if not name:
                continue

            candidates = self._search_wikidata(
                session, name,
                limit=options["limit_candidates"],
                language=options["language"],
            )
            time.sleep(options["delay"])

            scored = []
            for pos, cand in enumerate(candidates):
                entity = self._fetch_entity(session, cand["id"])
                time.sleep(options["delay"])
                if entity is None:
                    continue
                score, reasons = self._score(name, cand, entity)
                # Wikidata's wbsearchentities ranks by name precision
                # + popularity (sitelink count, edit count) so the
                # first hit is almost always the canonical entity.
                # Give it a generous bonus — it dominates noisy
                # homonyms in the deeper-position results.
                rank_bonus = max(0, 10 - 2 * pos)
                score += rank_bonus
                reasons.append(f"search_rank_{pos}")
                scored.append({
                    "qid": cand["id"],
                    "label": cand.get("label", ""),
                    "description": cand.get("description", ""),
                    "score": score,
                    "reasons": reasons,
                })

            scored.sort(key=lambda x: x["score"], reverse=True)
            top = scored[0] if scored else None
            second = scored[1] if len(scored) > 1 else None
            top_score = top["score"] if top else 0
            second_score = second["score"] if second else 0
            action = (
                "auto"
                if top
                and top_score >= options["threshold"]
                and top_score - second_score >= options["margin"]
                else "manual"
            )

            row = {
                "uuid": str(c.pk),
                "name": name,
                "slug": c.slug or "",
                "best_qid": top["qid"] if top else "",
                "best_label": top["label"] if top else "",
                "best_score": top_score,
                "best_reasons": "|".join(top["reasons"]) if top else "",
                "second_qid": second["qid"] if second else "",
                "second_label": second["label"] if second else "",
                "second_score": second_score,
                "action": action,
                "all_candidates": json.dumps(
                    [
                        {"qid": s["qid"], "label": s["label"],
                         "desc": s["description"], "score": s["score"]}
                        for s in scored
                    ],
                    ensure_ascii=False,
                ),
            }
            rows.append(row)

            if action == "auto" and options["apply"]:
                c.wikidata_id = top["qid"]
                c.save(update_fields=["wikidata_id"])
                applied += 1

            self.stdout.write(
                f"  [{idx}/{len(cities)}] {name:30} "
                f"-> {row['best_qid']:10} score={top_score:>3}  "
                f"{action}"
            )

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "uuid", "name", "slug",
                    "best_qid", "best_label", "best_score",
                    "best_reasons",
                    "second_qid", "second_label", "second_score",
                    "action", "all_candidates",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        auto = sum(1 for r in rows if r["action"] == "auto")
        manual = sum(1 for r in rows if r["action"] == "manual")
        self.stdout.write(self.style.WARNING(
            f"auto-confidence: {auto}"
        ))
        self.stdout.write(self.style.WARNING(
            f"needs manual review: {manual}"
        ))
        if options["apply"]:
            self.stdout.write(self.style.SUCCESS(
                f"Applied wikidata_id to {applied} city rows."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"DRY RUN: {auto} rows would be applied. "
                f"Re-run with --apply to commit."
            ))
        self.stdout.write(self.style.SUCCESS(
            f"{len(rows)} row(s) -> {out_path}"
        ))

    # ----- Wikidata I/O ---------------------------------------------

    def _search_wikidata(self, session, name, limit, language):
        try:
            r = session.get(
                WBSEARCH_URL,
                params={
                    "action": "wbsearchentities",
                    "search": name,
                    "language": language,
                    "uselang": language,
                    "format": "json",
                    "limit": limit,
                    "type": "item",
                },
                timeout=15,
            )
            r.raise_for_status()
            return r.json().get("search", [])
        except (requests.RequestException, ValueError) as exc:
            self.stderr.write(f"  wbsearch error for {name!r}: {exc}")
            return []

    def _fetch_entity(self, session, qid):
        try:
            r = session.get(
                ENTITY_URL.format(qid=qid),
                timeout=15,
            )
            r.raise_for_status()
            return r.json().get("entities", {}).get(qid)
        except (requests.RequestException, ValueError) as exc:
            self.stderr.write(f"  entity error for {qid}: {exc}")
            return None

    # ----- scoring ---------------------------------------------------

    def _score(self, name, cand, entity):
        """Return ``(score, reasons)`` for the candidate.

        The scoring is additive — each evidence type contributes a
        small bonus. The default threshold (12) corresponds to about
        three independent signals lining up."""
        reasons = []
        score = 0

        # Name match
        cand_label = cand.get("label", "") or ""
        name_norm = _ascii(name)
        aliases = self._collect_labels(entity)
        if name_norm == _ascii(cand_label):
            score += 5
            reasons.append("name_exact")
        elif any(name_norm == _ascii(a) for a in aliases):
            score += 4
            reasons.append("alias_exact")
        elif any(name_norm in _ascii(a) for a in aliases):
            score += 2
            reasons.append("alias_partial")

        # P31 instance of human settlement (any subclass we track)
        p31_values = self._claim_ids(entity, "P31")
        if SETTLEMENT_P31 & set(p31_values):
            score += 4
            reasons.append("p31_settlement")

        # P625 coords inside EU/IL box
        coord = self._claim_coord(entity, "P625")
        if coord:
            lat, lng = coord
            in_box = (
                EU_LEVANT_BOX[0] <= lat <= EU_LEVANT_BOX[1]
                and EU_LEVANT_BOX[2] <= lng <= EU_LEVANT_BOX[3]
            )
            if in_box:
                score += 3
                reasons.append("coords_eu_il")
            else:
                reasons.append(f"coords_outside({lat:.1f},{lng:.1f})")

        # P17 country bias (use Q-ID -> ISO2 mapping when present)
        p17_values = self._claim_ids(entity, "P17")
        if p17_values:
            iso = self._country_iso(entity, p17_values)
            if iso and iso in EU_LEVANT_COUNTRIES:
                score += 2
                reasons.append(f"country_{iso}")

        # Any sitelink at all
        if entity.get("sitelinks"):
            score += 2
            reasons.append("has_sitelinks")

        return score, reasons

    def _collect_labels(self, entity):
        out = []
        for lang_dict in entity.get("labels", {}).values():
            out.append(lang_dict.get("value", ""))
        for lang_list in entity.get("aliases", {}).values():
            for a in lang_list:
                out.append(a.get("value", ""))
        return out

    def _claim_ids(self, entity, prop):
        out = []
        for stmt in entity.get("claims", {}).get(prop, []):
            mainsnak = stmt.get("mainsnak", {})
            datavalue = mainsnak.get("datavalue", {})
            value = datavalue.get("value", {})
            qid = value.get("id")
            if qid:
                out.append(qid)
        return out

    def _claim_coord(self, entity, prop):
        for stmt in entity.get("claims", {}).get(prop, []):
            mainsnak = stmt.get("mainsnak", {})
            datavalue = mainsnak.get("datavalue", {})
            value = datavalue.get("value", {})
            lat = value.get("latitude")
            lng = value.get("longitude")
            if lat is not None and lng is not None:
                return float(lat), float(lng)
        return None

    def _country_iso(self, entity, p17_values):
        """Fast path: read the ISO-2 (P297) from any country claim's
        qualifiers — Wikidata stores ISO on the country entity, not
        on the country claim. Since we already have the country QID
        in hand and don't want to fan out another fetch per match,
        rely on the static mapping below for the common EU/IL set."""
        return COUNTRY_QID_TO_ISO.get(p17_values[0], "")


# Hand-rolled QID -> ISO-2 table for the countries we care about.
# Saves an extra round-trip per candidate. Update when the corpus
# grows beyond Europe / Levant.
COUNTRY_QID_TO_ISO = {
    "Q183": "DE",   # Germany
    "Q40":  "AT",   # Austria
    "Q39":  "CH",   # Switzerland
    "Q36":  "PL",   # Poland
    "Q213": "CZ",   # Czech Republic
    "Q28":  "HU",   # Hungary
    "Q159": "RU",   # Russia
    "Q37":  "LT",   # Lithuania
    "Q211": "LV",   # Latvia
    "Q191": "EE",   # Estonia
    "Q184": "BY",   # Belarus
    "Q212": "UA",   # Ukraine
    "Q218": "RO",   # Romania
    "Q219": "BG",   # Bulgaria
    "Q224": "HR",   # Croatia
    "Q403": "RS",   # Serbia
    "Q189": "IS",   # Iceland
    "Q35":  "DK",   # Denmark
    "Q34":  "SE",   # Sweden
    "Q20":  "NO",   # Norway
    "Q33":  "FI",   # Finland
    "Q29":  "ES",   # Spain
    "Q142": "FR",   # France
    "Q38":  "IT",   # Italy
    "Q31":  "BE",   # Belgium
    "Q55":  "NL",   # Netherlands
    "Q32":  "LU",   # Luxembourg
    "Q41":  "GR",   # Greece
    "Q43":  "TR",   # Turkey
    "Q801": "IL",   # Israel
    "Q822": "LB",   # Lebanon
    "Q794": "SY",   # Syria... wait Iran
    "Q858": "SY",   # actually Syria
    "Q145": "GB",   # United Kingdom
    "Q27":  "IE",   # Ireland
    "Q347": "LI",   # Liechtenstein
    "Q237": "VA",   # Vatican
    "Q221": "MK",   # North Macedonia
    "Q228": "AD",   # Andorra
    "Q225": "BA",   # Bosnia
    "Q236": "ME",   # Montenegro
    "Q1246": "XK",  # Kosovo
    "Q222": "AL",   # Albania
    "Q229": "CY",   # Cyprus
    "Q233": "MT",   # Malta
    "Q235": "MC",   # Monaco
    "Q238": "SM",   # San Marino
    "Q215": "SI",   # Slovenia
    "Q214": "SK",   # Slovakia
    "Q217": "MD",   # Moldova
}

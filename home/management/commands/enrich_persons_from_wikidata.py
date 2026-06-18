"""
Phase 1.5: propose a Wikidata QID for every live Person row whose
``entity_type`` is "person" and whose ``wikidata_id`` is empty.

The matcher uses three layers of evidence, strongest first:

1. **VIAF lookup** -- if ``Person.viaf_id`` is set, ask Wikidata's
   SPARQL endpoint for the QID where P214 == this VIAF. A hit here
   is essentially a perfect match (VIAF is a global authority
   identifier; the chance of two distinct persons sharing one is
   nil).
2. **GND lookup** -- same shape with P227 (GND identifier).
3. **Fuzzy name search** -- en + de + he passes through
   ``wbsearchentities``, scored on rank + P31=Q5 (human) + label
   exact-match + alias match + date-of-birth match + sitelinks.

Per anchored row the command writes:

  docs/audits/person_wikidata_candidates.csv

one row per Person with:

  uuid, name, viaf_id, gnd_id,
  best_qid, best_label, best_description, best_score, best_reasons,
  second_qid, second_score, action, all_candidates

``action`` is "auto" when the top candidate scores >= threshold AND
beats the second by margin; otherwise "manual". With ``--apply``
the "auto" rows get their ``Person.wikidata_id`` set on commit.

Rate-limited (default 0.6s) and identifies itself in the User-Agent
per Wikidata's API etiquette.

Run pattern (same shape as enrich_cities_from_wikidata):

    # dry-run smoke
    python manage.py enrich_persons_from_wikidata --limit 10

    # full apply
    python manage.py enrich_persons_from_wikidata --apply
"""
from __future__ import annotations

import csv
import gc
import json
import re
import time
from pathlib import Path

import requests
from django.core.management.base import BaseCommand

from home.models import Person


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
SPARQL_URL = "https://query.wikidata.org/sparql"

Q_HUMAN = "Q5"


def _ascii(s):
    """Strip diacritics + casefold for fuzzy name compare."""
    try:
        from anyascii import anyascii
        return anyascii(s).lower().strip()
    except ImportError:
        return re.sub(r"\W+", " ", s.lower()).strip()


def _name_variants(person):
    """Yield search strings for the person, most-distinctive first.

    The catalog stores names as ``Surname, Firstname``; Wikidata
    indexes them either way. Trying both orderings catches cases
    like ``Mendelssohn, Moses`` vs ``Moses Mendelssohn``."""
    seen = set()
    for raw in (
        person.pref_label,
        person.german_name,
        person.hebrew_name,
        person.pseudonym,
    ):
        v = (raw or "").strip()
        if not v or v in seen:
            continue
        seen.add(v)
        yield v
        # try the reversed-comma form as a second variant
        if "," in v:
            parts = [p.strip() for p in v.split(",", 1)]
            if len(parts) == 2 and all(parts):
                reversed_form = f"{parts[1]} {parts[0]}"
                if reversed_form not in seen:
                    seen.add(reversed_form)
                    yield reversed_form


YEAR_RE = re.compile(r"(\d{4})")


def _year_from(text):
    """Pull a 4-digit Gregorian year out of mixed date text. Returns
    ``None`` when the row carries only a Hebrew date / a free-text
    description / nothing."""
    if not text:
        return None
    m = YEAR_RE.search(str(text))
    return int(m.group(1)) if m else None


class Command(BaseCommand):
    help = (
        "Match every unanchored live Person against Wikidata via "
        "VIAF / GND / fuzzy name. Report candidates; --apply sets "
        "wikidata_id on the auto-confidence hits."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default="docs/audits/person_wikidata_candidates.csv",
        )
        parser.add_argument(
            "--limit", type=int, default=0,
            help="Process at most N unanchored persons. 0 = all.",
        )
        parser.add_argument(
            "--delay", type=float, default=0.6,
            help="Politeness delay between Wikidata calls. "
                 "Default 0.6s.",
        )
        parser.add_argument(
            "--limit-candidates", type=int, default=5,
            help="Top-N wbsearch hits to score per name variant.",
        )
        parser.add_argument(
            "--threshold", type=int, default=12,
            help="Minimum top-candidate score to auto-apply.",
        )
        parser.add_argument(
            "--margin", type=int, default=4,
            help="Top must beat the second by this margin.",
        )
        parser.add_argument(
            "--apply", action="store_true",
            help="Commit auto-confidence matches. Default dry-run.",
        )

    def handle(self, *args, **options):
        out_path = Path(options["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)

        persons = (
            Person.objects
            .filter(
                live=True,
                entity_type="person",
                merged_into__isnull=True,
            )
            .filter(wikidata_id__in=("", None))
            .order_by("pref_label")
        )
        if options["limit"]:
            persons = persons[: options["limit"]]
        persons = list(persons)

        self.stdout.write(
            f"Processing {len(persons)} unanchored live persons "
            f"(delay={options['delay']}s, "
            f"threshold={options['threshold']}, "
            f"margin={options['margin']})"
        )

        # Recycle the session every ~50 persons. Previous runs
        # died silently after 100-170 rows with no Python
        # traceback -- best guess: requests.Session keeps a TCP
        # pool + reads accumulating response bodies that the
        # garbage collector doesn't free aggressively enough on
        # its own when each Wikidata entity payload is large.
        # Closing the session forces the pool to drain.
        SESSION_RESET_EVERY = 50

        def _new_session():
            s = requests.Session()
            s.headers["User-Agent"] = USER_AGENT
            return s

        session = _new_session()

        rows = []
        applied = 0
        for idx, p in enumerate(persons, 1):
            if idx > 1 and (idx - 1) % SESSION_RESET_EVERY == 0:
                session.close()
                session = _new_session()
                gc.collect()
            scored, signal_source = self._match_one(
                session, p,
                limit_candidates=options["limit_candidates"],
                delay=options["delay"],
            )
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
                "uuid": str(p.pk),
                "name": (
                    p.pref_label or p.german_name
                    or p.hebrew_name or ""
                ),
                "viaf_id": p.viaf_id or "",
                "gnd_id": p.gnd_id or "",
                "best_qid": top["qid"] if top else "",
                "best_label": top["label"] if top else "",
                "best_description":
                    top["description"] if top else "",
                "best_score": top_score,
                "best_reasons":
                    "|".join(top["reasons"]) if top else "",
                "second_qid": second["qid"] if second else "",
                "second_score": second_score,
                "action": action,
                "signal_source": signal_source,
                "all_candidates": json.dumps(
                    [
                        {"qid": s["qid"], "label": s["label"],
                         "desc": s["description"],
                         "score": s["score"]}
                        for s in scored
                    ],
                    ensure_ascii=False,
                ),
            }
            rows.append(row)

            if action == "auto" and options["apply"]:
                p.wikidata_id = top["qid"]
                p.save(update_fields=["wikidata_id"])
                applied += 1

            self.stdout.write(
                f"  [{idx}/{len(persons)}] "
                f"{(p.pref_label or p.german_name or '')[:32]:32} "
                f"-> {row['best_qid']:10} "
                f"score={top_score:>3} {signal_source:8} {action}"
            )

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys())
                                    if rows else [
                "uuid", "name", "viaf_id", "gnd_id",
                "best_qid", "best_label", "best_description",
                "best_score", "best_reasons",
                "second_qid", "second_score",
                "action", "signal_source", "all_candidates",
            ])
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
                f"Applied wikidata_id to {applied} person rows."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"DRY RUN: {auto} rows would be applied."
            ))
        self.stdout.write(self.style.SUCCESS(
            f"{len(rows)} row(s) -> {out_path}"
        ))

    # ----- matcher -------------------------------------------------

    def _match_one(self, session, person, *, limit_candidates, delay):
        """Return ``(scored_list, signal_source)`` for one person.

        ``signal_source`` is "viaf" / "gnd" / "name" -- so the audit
        CSV records which evidence path produced the match."""
        # 1. VIAF
        if (person.viaf_id or "").strip():
            qid = self._sparql_by_property(
                session, "P214", person.viaf_id.strip(),
            )
            time.sleep(delay)
            if qid:
                entity = self._fetch_entity(session, qid)
                time.sleep(delay)
                if entity is not None:
                    score, reasons = self._score(
                        person, qid, entity, pos=0,
                        bonus_signal="viaf_exact",
                    )
                    return ([{
                        "qid": qid,
                        "label": self._best_label(entity),
                        "description": self._best_description(entity),
                        "score": score,
                        "reasons": reasons,
                    }], "viaf")

        # 2. GND
        if (person.gnd_id or "").strip():
            qid = self._sparql_by_property(
                session, "P227", person.gnd_id.strip(),
            )
            time.sleep(delay)
            if qid:
                entity = self._fetch_entity(session, qid)
                time.sleep(delay)
                if entity is not None:
                    score, reasons = self._score(
                        person, qid, entity, pos=0,
                        bonus_signal="gnd_exact",
                    )
                    return ([{
                        "qid": qid,
                        "label": self._best_label(entity),
                        "description": self._best_description(entity),
                        "score": score,
                        "reasons": reasons,
                    }], "gnd")

        # 3. Fuzzy name
        seen_qids = {}
        for variant in _name_variants(person):
            for lang in ("en", "de", "he"):
                hits = self._search(
                    session, variant,
                    limit=limit_candidates,
                    language=lang,
                )
                time.sleep(delay)
                for pos, h in enumerate(hits):
                    qid = h["id"]
                    if qid not in seen_qids or pos < seen_qids[qid][0]:
                        seen_qids[qid] = (pos, h)
        candidates = [h for _, h in sorted(
            seen_qids.values(), key=lambda t: t[0],
        )]
        scored = []
        for pos, cand in enumerate(candidates):
            entity = self._fetch_entity(session, cand["id"])
            time.sleep(delay)
            if entity is None:
                continue
            score, reasons = self._score(
                person, cand["id"], entity, pos=pos,
            )
            scored.append({
                "qid": cand["id"],
                "label": cand.get("label", ""),
                "description": cand.get("description", ""),
                "score": score,
                "reasons": reasons,
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return (scored, "name")

    # ----- scoring -------------------------------------------------

    def _score(self, person, qid, entity, *, pos, bonus_signal=None):
        reasons = []
        score = 0

        rank_bonus = max(0, 10 - 2 * pos)
        if rank_bonus:
            score += rank_bonus
            reasons.append(f"search_rank_{pos}")

        # P31 = Q5 (human)
        if Q_HUMAN in self._claim_ids(entity, "P31"):
            score += 5
            reasons.append("p31_human")

        # Name match against any label/alias on the entity
        labels = self._all_labels_aliases(entity)
        person_keys = {
            _ascii(v) for v in (
                person.pref_label, person.german_name,
                person.hebrew_name, person.pseudonym,
            ) if v
        }
        name_hit = False
        for lab in labels:
            if _ascii(lab) in person_keys:
                score += 5
                reasons.append("name_exact")
                name_hit = True
                break
        if not name_hit:
            for lab in labels:
                if any(pk in _ascii(lab) for pk in person_keys):
                    score += 2
                    reasons.append("name_partial")
                    break

        # Birth / death year match against P569 / P570
        local_birth = _year_from(person.date_of_birth)
        local_death = _year_from(person.date_of_death)
        wd_birth = self._claim_year(entity, "P569")
        wd_death = self._claim_year(entity, "P570")
        if local_birth and wd_birth and abs(local_birth - wd_birth) <= 1:
            score += 4
            reasons.append(f"birth_{wd_birth}")
        if local_death and wd_death and abs(local_death - wd_death) <= 1:
            score += 4
            reasons.append(f"death_{wd_death}")

        # Has at least one sitelink -- weak popularity signal.
        if entity.get("sitelinks"):
            score += 2
            reasons.append("has_sitelinks")

        if bonus_signal:
            score += 10
            reasons.append(bonus_signal)

        return score, reasons

    # ----- API helpers ---------------------------------------------

    def _sparql_by_property(self, session, prop, value):
        """Return the first QID whose ``prop`` claim equals
        ``value``, or None when no row matches."""
        query = (
            f'SELECT ?item WHERE {{ ?item wdt:{prop} "{value}" }} '
            f'LIMIT 1'
        )
        try:
            r = session.get(
                SPARQL_URL,
                params={"query": query, "format": "json"},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
        except (requests.RequestException, ValueError) as exc:
            self.stderr.write(f"  sparql {prop}={value} error: {exc}")
            return None
        bindings = data.get("results", {}).get("bindings", [])
        if not bindings:
            return None
        url = bindings[0].get("item", {}).get("value", "")
        # url is http://www.wikidata.org/entity/Q12345
        m = re.search(r"(Q\d+)$", url)
        return m.group(1) if m else None

    def _search(self, session, name, limit, language):
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
            self.stderr.write(f"  search error for {name!r}: {exc}")
            return []

    def _fetch_entity(self, session, qid):
        try:
            r = session.get(
                ENTITY_URL.format(qid=qid), timeout=15,
            )
            r.raise_for_status()
            return r.json().get("entities", {}).get(qid)
        except (requests.RequestException, ValueError) as exc:
            self.stderr.write(f"  entity error for {qid}: {exc}")
            return None

    # ----- entity readers ------------------------------------------

    def _claim_ids(self, entity, prop):
        out = []
        for stmt in entity.get("claims", {}).get(prop, []):
            value = (stmt.get("mainsnak", {}).get("datavalue", {})
                     .get("value", {}))
            qid = value.get("id")
            if qid:
                out.append(qid)
        return out

    def _claim_year(self, entity, prop):
        for stmt in entity.get("claims", {}).get(prop, []):
            value = (stmt.get("mainsnak", {}).get("datavalue", {})
                     .get("value", {}))
            t = value.get("time", "")
            m = re.match(r"[+-]?(\d{4})-", t)
            if m:
                return int(m.group(1))
        return None

    def _all_labels_aliases(self, entity):
        out = []
        for ldict in entity.get("labels", {}).values():
            v = ldict.get("value")
            if v:
                out.append(v)
        for alist in entity.get("aliases", {}).values():
            for a in alist:
                v = a.get("value")
                if v:
                    out.append(v)
        return out

    def _best_label(self, entity):
        labels = entity.get("labels", {})
        for lang in ("en", "de", "he"):
            v = (labels.get(lang) or {}).get("value")
            if v:
                return v
        for ldict in labels.values():
            v = ldict.get("value")
            if v:
                return v
        return ""

    def _best_description(self, entity):
        descs = entity.get("descriptions", {})
        for lang in ("en", "de", "he"):
            v = (descs.get(lang) or {}).get("value")
            if v:
                return v
        for ddict in descs.values():
            v = ddict.get("value")
            if v:
                return v
        return ""

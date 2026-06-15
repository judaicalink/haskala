"""
Generate a QuickStatements input file that pushes back-links from
the Haskala catalog to the corresponding Wikidata items.

For every Person / Book / City whose ``wikidata_id`` is set, the
command emits statements that enrich the existing Wikidata entity
with:

- ``P973`` "described at URL" pointing at the catalog detail page,
  with the catalog URL as the reference (``S854`` reference URL) and
  the retrieval date (``S813``) as today.
- For Persons, when authority IDs are present:
  - ``P214`` VIAF ID
  - ``P227`` GND ID

QuickStatements is idempotent — re-running monthly and re-uploading
the result is safe: statements that already exist with the same
references are skipped server-side. The TSV format and statement
grammar are documented at:

  https://www.wikidata.org/wiki/Help:QuickStatements

The output goes to ``<HASKALA_DUMPS_ROOT>/<HASKALA_SLUG>/wikidata/
quickstatements_<YYYY-MM-DD>.tsv``. Override the path with ``--out``.

Upload paths (pick the one that fits the operator):

1. Manual (no setup): copy the file's contents and paste into
   https://quickstatements.toolforge.org/ under "Import V1 commands"
   while logged in as your personal Wikidata account. All edits
   land under your contribution history.
2. API (one-time OAuth setup): grab your personal API token from
   https://quickstatements.toolforge.org/#/user and set the env
   vars ``HASKALA_QS_USER`` + ``HASKALA_QS_TOKEN``. Then pass
   ``--upload`` and the command POSTs the batch directly. The
   edits still show up under your Wikidata username because the
   token is bound to your QS profile.

The command is otherwise read-only against the catalog and does NOT
contact Wikidata. Uploading is opt-in.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.dateformat import format as dj_format

from home.models import Book, City, Person


PROP_DESCRIBED_AT_URL = "P973"
PROP_REFERENCE_URL = "S854"
PROP_RETRIEVED = "S813"
PROP_VIAF = "P214"
PROP_GND = "P227"

QS_API_URL = "https://quickstatements.toolforge.org/api.php"


def _base_url():
    """Public-facing catalog URL, used as the back-link target.

    Falls back to ``WAGTAILADMIN_BASE_URL`` because the project keeps
    its canonical site URL there. Trailing slash is stripped so we
    can ``f"{base}/places/{slug}/"`` without doubling slashes."""
    base = (
        getattr(settings, "HASKALA_BASE_URL", "")
        or getattr(settings, "WAGTAILADMIN_BASE_URL", "")
        or "https://www.haskala-library.net"
    )
    return base.rstrip("/")


def _today_iso():
    """QuickStatements expects a TIME value in
    ``+YYYY-MM-DDT00:00:00Z/PRECISION`` form. Precision 11 = day."""
    today = date.today()
    return f"+{dj_format(today, 'Y-m-d')}T00:00:00Z/11"


def _quote(s):
    """QuickStatements string literal: surround with double quotes
    and escape inner double quotes. The catalog's slugs don't carry
    quote characters but we escape defensively in case a future row
    does."""
    return '"' + s.replace('"', '\\"') + '"'


class Command(BaseCommand):
    help = (
        "Emit a QuickStatements TSV that adds 'described at URL' "
        "(P973) plus authority-ID statements on every Wikidata "
        "item the catalog has anchored."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default=None,
            help="Output path. Default: "
                 "<HASKALA_DUMPS_ROOT>/<HASKALA_SLUG>/wikidata/"
                 "quickstatements_<YYYY-MM-DD>.tsv",
        )
        parser.add_argument(
            "--upload",
            action="store_true",
            help="POST the batch to QuickStatements after writing "
                 "the TSV. Requires HASKALA_QS_USER and "
                 "HASKALA_QS_TOKEN env vars (or --user / --token).",
        )
        parser.add_argument(
            "--user",
            default=os.environ.get("HASKALA_QS_USER", ""),
            help="QuickStatements username (your Wikidata handle). "
                 "Falls back to HASKALA_QS_USER env var.",
        )
        parser.add_argument(
            "--token",
            default=os.environ.get("HASKALA_QS_TOKEN", ""),
            help="Personal QuickStatements API token, copied from "
                 "https://quickstatements.toolforge.org/#/user. "
                 "Falls back to HASKALA_QS_TOKEN env var.",
        )
        parser.add_argument(
            "--batchname",
            default="",
            help="Batch label shown in QuickStatements history. "
                 "Default: haskala-sync-<YYYY-MM-DD>.",
        )

    def handle(self, *args, **options):
        out_path = options["out"]
        if out_path is None:
            stamp = dj_format(date.today(), "Y-m-d")
            out_path = (
                Path(settings.HASKALA_DUMPS_ROOT)
                / settings.HASKALA_SLUG
                / "wikidata"
                / f"quickstatements_{stamp}.tsv"
            )
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        base = _base_url()
        retrieved = _today_iso()

        lines = []
        person_count = self._emit_persons(lines, base, retrieved)
        book_count = self._emit_books(lines, base, retrieved)
        city_count = self._emit_cities(lines, base, retrieved)

        with out_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            if lines:
                f.write("\n")

        self.stdout.write(self.style.WARNING(
            f"Persons emitted: {person_count}"
        ))
        self.stdout.write(self.style.WARNING(
            f"Books emitted:   {book_count}"
        ))
        self.stdout.write(self.style.WARNING(
            f"Cities emitted:  {city_count}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"{len(lines)} TSV row(s) -> {out_path}"
        ))

        if options["upload"]:
            self._upload(
                lines,
                user=options["user"],
                token=options["token"],
                batchname=(
                    options["batchname"]
                    or f"haskala-sync-{dj_format(date.today(), 'Y-m-d')}"
                ),
            )

    def _upload(self, lines, user, token, batchname):
        """POST the batch to the QuickStatements API.

        The batch is attributed to the operator's Wikidata account
        because the API token is bound to their QS profile, which
        in turn is bound to their Wikidata OAuth identity. We do
        not pass the token as a URL parameter to avoid leaking it
        in proxy logs."""
        if not user or not token:
            self.stderr.write(self.style.ERROR(
                "Cannot upload: HASKALA_QS_USER and HASKALA_QS_TOKEN "
                "(or --user/--token) must be set."
            ))
            return
        if not lines:
            self.stdout.write(
                "Nothing to upload (zero statements emitted)."
            )
            return

        data = {
            "action": "import",
            "submit": "1",
            "format": "v1",
            "batchname": batchname,
            "username": user,
            "token": token,
            "data": "\n".join(lines),
        }
        try:
            r = requests.post(QS_API_URL, data=data, timeout=60)
            r.raise_for_status()
            body = r.json() if r.headers.get(
                "content-type", ""
            ).startswith("application/json") else {"raw": r.text}
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(
                f"QuickStatements upload failed: {exc}"
            ))
            return

        if body.get("status") == "OK":
            batch_id = body.get("batch_id") or body.get("batchid", "?")
            self.stdout.write(self.style.SUCCESS(
                f"Uploaded as batch {batch_id} for user {user!r} "
                f"(label: {batchname})."
            ))
        else:
            self.stderr.write(self.style.ERROR(
                f"QuickStatements rejected the batch: {body}"
            ))

    # ----- per-model emitters ---------------------------------------

    def _emit_persons(self, lines, base, retrieved):
        count = 0
        wikidata_field_present = hasattr(Person, "wikidata_id")
        qs = Person.objects.filter(live=True)
        if wikidata_field_present:
            qs = qs.exclude(wikidata_id="")
        else:
            return 0
        for p in qs.iterator(chunk_size=200):
            slug = p.slug or str(p.pk)
            url = f"{base}/persons/{slug}/"
            lines.append(self._statement_line(
                p.wikidata_id,
                PROP_DESCRIBED_AT_URL,
                _quote(url),
                ref_url=url,
                retrieved=retrieved,
            ))
            if (p.viaf_id or "").strip():
                lines.append(self._statement_line(
                    p.wikidata_id,
                    PROP_VIAF,
                    _quote(p.viaf_id.strip()),
                    ref_url=url,
                    retrieved=retrieved,
                ))
            if (p.gnd_id or "").strip():
                lines.append(self._statement_line(
                    p.wikidata_id,
                    PROP_GND,
                    _quote(p.gnd_id.strip()),
                    ref_url=url,
                    retrieved=retrieved,
                ))
            count += 1
        return count

    def _emit_books(self, lines, base, retrieved):
        if not hasattr(Book, "wikidata_id"):
            return 0
        count = 0
        for b in (
            Book.objects.filter(live=True)
            .exclude(wikidata_id="")
            .iterator(chunk_size=200)
        ):
            slug = b.slug or str(b.pk)
            url = f"{base}/books/{slug}/"
            lines.append(self._statement_line(
                b.wikidata_id,
                PROP_DESCRIBED_AT_URL,
                _quote(url),
                ref_url=url,
                retrieved=retrieved,
            ))
            count += 1
        return count

    def _emit_cities(self, lines, base, retrieved):
        count = 0
        for c in (
            City.objects.filter(live=True)
            .exclude(wikidata_id="")
            .iterator(chunk_size=200)
        ):
            slug = c.slug or str(c.pk)
            url = f"{base}/places/{slug}/"
            lines.append(self._statement_line(
                c.wikidata_id,
                PROP_DESCRIBED_AT_URL,
                _quote(url),
                ref_url=url,
                retrieved=retrieved,
            ))
            count += 1
        return count

    # ----- TSV formatting -------------------------------------------

    def _statement_line(self, qid, prop, value, *, ref_url, retrieved):
        """Build one QuickStatements V1 line with a reference URL
        and a retrieved date.

        Format (tab-separated):

          QID  prop  value  S854  "ref-url"  S813  +YYYY-MM-DDT00:00:00Z/11
        """
        return "\t".join([
            qid,
            prop,
            value,
            PROP_REFERENCE_URL,
            _quote(ref_url),
            PROP_RETRIEVED,
            retrieved,
        ])

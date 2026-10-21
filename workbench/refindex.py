"""The reference index: one strict reader and one canonical serializer.

The format is in ``docs/specs/groundwork.md`` ("Indexes") and
``docs/decisions/2026-10-21-reference-index-format.md``. The tracked index is
``docs/references/index.json`` and the untracked one ``.workbench/local/refs/index.json``. Each
is UTF-8 JSON ``{"entries": [...], "format": 1}`` with one entry per line, entries sorted by
``file``, and every entry carrying the same eight fields.

The reader accepts nothing but the serializer's own output, as the manifest reader does: a
duplicate key, NaN, a fraction, a non-printable character, an unknown or missing field, a repeated
or unsorted file or a different layout is refused. The index is untrusted text when it is read;
this module checks its shape and nothing else. Whether a named file exists, is tracked or has the
recorded hash is a question for ``wb check``, which asks it of the real files.

A message names the entry (by its place in the list) and the field. It never repeats a value,
because the value is hostile text.
"""

import datetime
import re

from . import declarations, manifest, safefs

PATH = "docs/references/index.json"
AREA = "docs/references"
LOCAL_PATH = ".workbench/local/refs/index.json"
LOCAL_AREA = ".workbench/local/refs"
METADATA = ("index.json", "README.md")
FORMAT = 1
MAX_BYTES = 1024 * 1024
MAX_ENTRIES = 5000

TOP_KEYS = ("entries", "format")
ENTRY_KEYS = ("file", "license", "notes", "retrieved", "sha256", "title", "url", "version")

# The longest value of each text field; ``file`` is bounded by the path rule.
LIMITS = {"title": 300, "url": 2048, "license": 128, "version": 128, "notes": 2000}
# A field that may be empty: a hand-added reference may have no license, version or notes. The
# check warns about a missing license; it does not forbid it.
OPTIONAL = ("license", "version", "notes")

_DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
_URL = re.compile(r"^https?://[^\s/?#]+[^\s]*\Z")


class RefIndexError(Exception):
    """The index, or the document to be written, does not have the required form."""


def _fail(position, field, reason):
    where = "the index" if position is None else "entry %d" % position
    raise RefIndexError("%s: %s %s" % (where, field, reason))


def _text(position, entry, field):
    value = entry[field]
    limit = LIMITS[field]
    if not isinstance(value, str):
        _fail(position, field, "is not text")
    if not value.isprintable():
        _fail(position, field, "has a non-printable character")
    if len(value) > limit:
        _fail(position, field, "is longer than %d characters" % limit)
    if not value and field not in OPTIONAL:
        _fail(position, field, "is empty")
    return value


def _file(position, value, area):
    if not isinstance(value, str):
        _fail(position, "file", "is not text")
    try:
        safefs.validate_relpath(value)
    except safefs.SafeFsError as exc:
        _fail(position, "file", "is not a safe relative path (%s)" % _reason(exc))
    folded = value.casefold()
    prefix = area.casefold() + "/"
    if not folded.startswith(prefix) or folded == prefix:
        _fail(position, "file", "is not a file under %s" % area)
    if "/" not in value[len(prefix):] and value[len(prefix):].casefold() in \
            tuple(name.casefold() for name in METADATA):
        _fail(position, "file", "names the index or the README, which are not references")


def _reason(exc):
    # The path rule quotes the path it refused; the field is named, so the quote is dropped.
    return str(exc).split(":", 1)[0]


def _fields(item, expected, position):
    # Unlike the manifest's key check, this shows no unexpected key: it is hostile text.
    if not isinstance(item, dict):
        _fail(position, "the entry", "is not an object")
    if set(item) != set(expected):
        _fail(position, "the fields", "are not exactly %s" % ", ".join(expected))


def _entry(position, entry, area):
    _fields(entry, ENTRY_KEYS, position)
    _file(position, entry["file"], area)
    for field in LIMITS:
        _text(position, entry, field)
    if not _URL.match(entry["url"]):
        _fail(position, "url", "is not an http or https address")
    retrieved = entry["retrieved"]
    if not isinstance(retrieved, str) or not _DATE.match(retrieved):
        _fail(position, "retrieved", "is not a date as YYYY-MM-DD")
    try:
        datetime.date(int(retrieved[:4]), int(retrieved[5:7]), int(retrieved[8:]))
    except ValueError:
        _fail(position, "retrieved", "is not a real date")
    if not isinstance(entry["sha256"], str) or not manifest._HEX64.match(entry["sha256"]):
        _fail(position, "sha256", "is not a SHA-256 in lowercase hex")


def check_document(document, area=AREA):
    """Raise RefIndexError unless `document` has exactly the shape the serializer writes."""
    _fields(document, TOP_KEYS, None)
    version = document["format"]
    if isinstance(version, bool) or not isinstance(version, int) or version != FORMAT:
        _fail(None, "format", "is not %d" % FORMAT)
    entries = document["entries"]
    if not isinstance(entries, list):
        _fail(None, "entries", "is not a list")
    if len(entries) > MAX_ENTRIES:
        _fail(None, "entries", "has more than %d entries" % MAX_ENTRIES)
    for position, entry in enumerate(entries):
        _entry(position, entry, area)
    try:
        manifest._sorted_by(entries, lambda e: manifest._path_key(e["file"]), "entries")
        safefs.check_tree_paths([e["file"] for e in entries])
    except (manifest.ManifestError, safefs.SafeFsError) as exc:
        raise RefIndexError("the index: %s" % _reason(exc))


def serialize(document, area=AREA):
    """The canonical bytes of `document`; raises RefIndexError for anything not in shape."""
    check_document(document, area)
    entries = document["entries"]
    if entries:
        body = ",\n".join("    " + manifest._line(entry) for entry in entries)
        listed = '  "entries": [\n%s\n  ]' % body
    else:
        listed = '  "entries": []'
    data = ("{\n%s,\n  \"format\": %d\n}\n" % (listed, FORMAT)).encode("ascii")
    if len(data) > MAX_BYTES:
        raise RefIndexError("the index is larger than %d bytes" % MAX_BYTES)
    return data


def parse(data, area=AREA):
    """The document in canonical `data`; raises RefIndexError for anything else."""
    if not isinstance(data, bytes):
        raise RefIndexError("the index is not bytes")
    if len(data) > MAX_BYTES:
        raise RefIndexError("the index is larger than %d bytes" % MAX_BYTES)
    try:
        document = declarations.parse_json(data)
    except ValueError as exc:
        raise RefIndexError("the index is not valid: %s" % exc)
    check_document(document, area)
    if serialize(document, area) != data:
        raise RefIndexError("the index is not in its canonical form")
    return document

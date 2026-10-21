"""The committed manifest: one serializer, one strict reader, the seed and the project ID.

The format is in ``docs/specs/repository-boundary.md`` ("The committed manifest"). The file
is UTF-8 JSON with sorted keys, no timestamp and no per-clone value, and one entry per line, so
two developers who add different modules do not conflict. It never names a harness: the only
keys are the ones below, and any other key (a harness, a time) is refused.

The serializer writes the layout itself and does not depend on a library's formatting. The
reader accepts nothing but the serializer's own output, so a manifest that is not in canonical
form is refused. The manifest is untrusted text when it is read back: this module checks its
shape and nothing else.
"""

import hashlib
import json
import re
import uuid

from . import declarations
from .wbkit import safefs

VERSION = 1
BASE_IGNORE = b"/local/\n"

CLASSES = ("module-owned", "seeded", "slot block")

_HEX64 = re.compile(r"^[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"^([0-9a-f]{40}|[0-9a-f]{64})?\Z")
_SEED = re.compile(r"^[A-Za-z0-9._-]{1,128}\Z")
_WORKBENCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}\Z")
_BLOCK = re.compile(r"^[a-z][a-z0-9-]{0,63}/[a-z][a-z0-9-]{0,63}\Z")
_TEXT_LIMIT = 512

TOP_KEYS = ("base", "files", "packages", "seed", "version", "workbench")
PACKAGE_KEYS = ("commit", "modules", "name", "ref", "source", "tree")
MODULE_KEYS = ("declaration", "name", "tree", "version")
FILE_KEYS = ("class", "hash", "path")
BLOCK_KEYS = ("block", "slot")


class ManifestError(Exception):
    """The manifest or the document to be written does not have the required form."""


def new_seed():
    return str(uuid.uuid4())


def _check_seed(seed):
    if not isinstance(seed, str) or not _SEED.match(seed):
        raise ManifestError("the seed is not a plain token of at most 128 characters")
    return seed


def project_id(seed):
    """The project ID: SHA-256 of the seed as 64 lowercase hex digits."""
    return hashlib.sha256(_check_seed(seed).encode("ascii")).hexdigest()


# --- shape ---------------------------------------------------------------------


def _text(value, what, allow_empty=False):
    if not isinstance(value, str) or not value.isprintable() or len(value) > _TEXT_LIMIT \
            or (not value and not allow_empty):
        raise ManifestError("%s is not printable text of at most %d characters"
                            % (what, _TEXT_LIMIT))
    return value


def _hex(value, what):
    if not isinstance(value, str) or not _HEX64.match(value):
        raise ManifestError("%s is not a SHA-256 in lowercase hex" % what)
    return value


def _keys(item, expected, what, optional=()):
    if not isinstance(item, dict):
        raise ManifestError("%s is not an object" % what)
    keys = set(item)
    if not set(expected) <= keys or not keys <= set(expected) | set(optional):
        extra = sorted(keys - set(expected) - set(optional))
        missing = sorted(set(expected) - keys)
        raise ManifestError("%s has the wrong keys (unexpected %s, missing %s)"
                            % (what, extra, missing))


def _sorted_by(items, key, what):
    keys = [key(item) for item in items]
    if keys != sorted(keys):
        raise ManifestError("%s are not sorted" % what)
    if len(set(keys)) != len(keys):
        raise ManifestError("%s repeat an entry" % what)


def _path_key(rel):
    return rel.encode("utf-8")


def _check_module(item):
    _keys(item, MODULE_KEYS, "a module entry")
    if not isinstance(item["name"], str) or not declarations.NAME_RE.match(item["name"]) \
            or len(item["name"]) > declarations.MAX_NAME_CHARS:
        raise ManifestError("a module name is not valid")
    if not isinstance(item["version"], str) or not declarations._VERSION.match(item["version"]):
        raise ManifestError("a module version is not valid")
    _hex(item["declaration"], "a declaration hash")
    _hex(item["tree"], "a module tree hash")


def _check_package(item):
    _keys(item, PACKAGE_KEYS, "a package entry")
    if not isinstance(item["name"], str) or not declarations.NAME_RE.match(item["name"]) \
            or len(item["name"]) > declarations.MAX_NAME_CHARS:
        raise ManifestError("a package name is not valid")
    _text(item["source"], "a package source")
    _text(item["ref"], "a package ref", allow_empty=True)
    if not isinstance(item["commit"], str) or not _COMMIT.match(item["commit"]):
        raise ManifestError("a package commit is not a full commit hash or empty")
    _hex(item["tree"], "a package tree hash")
    modules = item["modules"]
    if not isinstance(modules, list):
        raise ManifestError("a package's modules are not a list")
    for module in modules:
        _check_module(module)
    _sorted_by(modules, lambda m: m["name"], "a package's modules")


def _check_file(item):
    _keys(item, FILE_KEYS, "a file entry", optional=BLOCK_KEYS)
    if item["class"] not in CLASSES:
        raise ManifestError("a file entry has an unknown class")
    _hex(item["hash"], "a file hash")
    try:
        safefs.validate_relpath(item["path"])
    except safefs.SafeFsError as exc:
        raise ManifestError("a file path is not valid: %s" % exc)
    has_block = [key in item for key in BLOCK_KEYS]
    if any(has_block) != all(has_block) or all(has_block) != (item["class"] == "slot block"):
        raise ManifestError("only a slot block has a slot and a block, and it has both")
    if "slot" in item:
        if not isinstance(item["slot"], str) or not declarations.NAME_RE.match(item["slot"]):
            raise ManifestError("a slot name is not valid")
        if not isinstance(item["block"], str) or not _BLOCK.match(item["block"]):
            raise ManifestError("a block id is not <package>/<module>")


def check_document(document):
    """Raise ManifestError unless `document` has exactly the shape the serializer writes."""
    _keys(document, TOP_KEYS, "the manifest")
    version = document["version"]
    if isinstance(version, bool) or version != VERSION or not isinstance(version, int):
        raise ManifestError("the manifest version is not %d" % VERSION)
    _check_seed(document["seed"])
    _hex(document["base"], "the base tree hash")
    if not isinstance(document["workbench"], str) or not _WORKBENCH.match(document["workbench"]):
        raise ManifestError("the workbench version is not valid")
    packages, files = document["packages"], document["files"]
    if not isinstance(packages, list) or not isinstance(files, list):
        raise ManifestError("packages and files must be lists")
    for package in packages:
        _check_package(package)
    _sorted_by(packages, lambda p: p["name"], "packages")
    for item in files:
        _check_file(item)
    _sorted_by(files, lambda f: (_path_key(f["path"]), f.get("block", "")), "files")


# --- layout --------------------------------------------------------------------


def _line(value):
    return json.dumps(value, sort_keys=True, separators=(", ", ": "), ensure_ascii=True)


def serialize(document):
    """The canonical bytes of `document`; raises ManifestError for anything not in shape."""
    check_document(document)
    lines = []
    for key in TOP_KEYS:
        value = document[key]
        if isinstance(value, list):
            if not value:
                lines.append('  "%s": []' % key)
                continue
            body = ",\n".join("    " + _line(item) for item in value)
            lines.append('  "%s": [\n%s\n  ]' % (key, body))
        else:
            lines.append('  "%s": %s' % (key, _line(value)))
    return ("{\n" + ",\n".join(lines) + "\n}\n").encode("ascii")


def parse(data):
    """The document in canonical `data`; raises ManifestError for anything else."""
    if not isinstance(data, bytes):
        raise ManifestError("the manifest is not bytes")
    try:
        document = declarations.parse_json(data)
    except ValueError as exc:
        raise ManifestError("the manifest is not valid: %s" % exc)
    check_document(document)
    if serialize(document) != data:
        raise ManifestError("the manifest is not in its canonical form")
    return document

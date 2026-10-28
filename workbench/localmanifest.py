"""The local manifest ``.workbench/local/harness.json``: what attach recorded for this clone.

The format is in ``docs/specs/repository-boundary.md`` ("The local manifest"). It names the
attached harness, the pin of the harness module (source, version, tree hash), the workbench
version that attached it, and the hash of each generated file. It is scratch: it is untracked,
grants no authority, and is not evidence that a file is safe, only that it is the file attach
wrote. It is written last, so a clone with none can run attach again.

Like the committed manifest, the file is canonical: sorted keys, ASCII, one entry per line, and
the reader accepts nothing but the serializer's own output. It is untrusted text when read back;
this module checks its shape and nothing else.
"""

from . import declarations, manifest
from .wbkit import safefs

PATH = ".workbench/local/harness.json"
LOCAL = ".workbench/local"
FORMAT = 1
MAX_FILES = 2048
MAX_BYTES = 1024 * 1024

TOP_KEYS = ("files", "format", "harness", "module_version", "source", "tree", "workbench")
FILE_KEYS = ("hash", "path")


class LocalManifestError(Exception):
    """The local manifest, or the document to be written, does not have the required form."""


def _check_name(value, what):
    if not isinstance(value, str) or not declarations.NAME_RE.match(value) \
            or len(value) > declarations.MAX_NAME_CHARS:
        raise LocalManifestError("%s is not a valid name" % what)


def check_document(document):
    """Raise LocalManifestError unless `document` has exactly the shape the serializer writes."""
    try:
        manifest._keys(document, TOP_KEYS, "the local manifest")
        version = document["format"]
        if isinstance(version, bool) or not isinstance(version, int) or version != FORMAT:
            raise LocalManifestError("the local manifest format is not %d" % FORMAT)
        _check_name(document["harness"], "the harness")
        if not isinstance(document["module_version"], str) \
                or not declarations._VERSION.match(document["module_version"]):
            raise LocalManifestError("the harness module version is not valid")
        manifest._text(document["source"], "the harness source")
        manifest._hex(document["tree"], "the harness tree hash")
        if not isinstance(document["workbench"], str) \
                or not manifest._WORKBENCH.match(document["workbench"]):
            raise LocalManifestError("the workbench version is not valid")
        files = document["files"]
        if not isinstance(files, list) or len(files) > MAX_FILES:
            raise LocalManifestError("files must be a list of at most %d entries" % MAX_FILES)
        for item in files:
            manifest._keys(item, FILE_KEYS, "a file entry")
            manifest._hex(item["hash"], "a file hash")
            if not isinstance(item["path"], str):
                raise LocalManifestError("a file path is not text")
            safefs.validate_relpath(item["path"])
            folded = item["path"].casefold()
            if folded == LOCAL or folded.startswith(LOCAL + "/"):
                raise LocalManifestError("a harness file may not be under .workbench/local: %s"
                                         % item["path"])
        manifest._sorted_by(files, lambda f: manifest._path_key(f["path"]), "files")
        _no_overlap([item["path"] for item in files])
    except (manifest.ManifestError, safefs.SafeFsError) as exc:
        raise LocalManifestError(str(exc))


def _no_overlap(paths):
    """A file may not also be a directory above another file, ignoring case."""
    try:
        safefs.check_tree_paths(paths)
    except safefs.SafeFsError as exc:
        raise LocalManifestError(str(exc))


def serialize(document):
    """The canonical bytes of `document`; raises LocalManifestError for anything not in shape."""
    check_document(document)
    lines = []
    for key in TOP_KEYS:
        value = document[key]
        if isinstance(value, list):
            if not value:
                lines.append('  "%s": []' % key)
                continue
            body = ",\n".join("    " + manifest._line(item) for item in value)
            lines.append('  "%s": [\n%s\n  ]' % (key, body))
        else:
            lines.append('  "%s": %s' % (key, manifest._line(value)))
    data = ("{\n" + ",\n".join(lines) + "\n}\n").encode("ascii")
    if len(data) > MAX_BYTES:
        raise LocalManifestError("the local manifest is too large")
    return data


def parse(data):
    """The document in canonical `data`; raises LocalManifestError for anything else."""
    if not isinstance(data, bytes):
        raise LocalManifestError("the local manifest is not bytes")
    if len(data) > MAX_BYTES:
        raise LocalManifestError("the local manifest is too large")
    try:
        document = declarations.parse_json(data)
    except ValueError as exc:
        raise LocalManifestError("the local manifest is not valid: %s" % exc)
    check_document(document)
    if serialize(document) != data:
        raise LocalManifestError("the local manifest is not in its canonical form")
    return document


def read(writer):
    """The recorded document, or None when this clone has none. A file that is not canonical, or
    that is a link or not regular, raises."""
    try:
        state = writer.read_file(PATH)
    except safefs.SafeFsError as exc:
        raise LocalManifestError("the local manifest cannot be read: %s" % exc)
    if state is None:
        return None
    return parse(state.data)


def write(writer, document):
    """Create the local manifest exclusively. An existing file, of any kind, is a conflict."""
    data = serialize(document)
    writer.create_file(PATH, data)
    return data


def replace(writer, expected_hash, document):
    """Replace the local manifest, whose SHA-256 must be `expected_hash`, with `document`. Any other content, a link or a
    missing file is a conflict (``projectfs.Writer.replace_file``)."""
    data = serialize(document)
    writer.replace_file(PATH, expected_hash, data)
    return data

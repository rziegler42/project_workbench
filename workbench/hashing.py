"""The declaration hash and the tree hash, both SHA-256.

An approval binds to these values, so the serializations are fixed here and by
known-answer tests in tests/test_hashing.py. Changing either invalidates every
approval made against it.

Declaration hash
    The declaration is a parsed JSON value. It is serialized as JSON with object
    keys sorted by code point at every level, separators "," and ":" with no other
    whitespace, non-ASCII characters written as themselves (ensure_ascii off), and
    encoded as UTF-8. The hash is the SHA-256 of those bytes, as lowercase hex.
    Only objects with string keys, lists, strings, integers, booleans and null are
    accepted. A float, NaN or any other type is refused, so two implementations
    cannot disagree about number formatting.

Tree hash
    The tree is every regular file below a module root, found by the race-safe
    walk in safefs. For each file one record is built:

        <64 hex characters: SHA-256 of the file content> " " <"x" or "-"> " " <path> "\\n"

    "x" means the owner execute bit is set. The path is relative to the root with
    "/" separators, and is UTF-8 encoded. The path validator forbids a newline in
    a path, so a record cannot be confused with its neighbour. Records are sorted
    by the UTF-8 bytes of the path, concatenated, and hashed with SHA-256, as
    lowercase hex. Directories do not contribute, so an empty directory is not
    part of the tree. A symbolic link, device, socket or FIFO anywhere in the
    tree is a refusal that names the path.

Every file is read once, through safefs, with its size limit.
"""

import collections
import hashlib
import json

from . import safefs


class HashError(safefs.SafeFsError):
    """A tree cannot be hashed."""


def canonical_bytes(declaration):
    """The canonical UTF-8 serialization of a parsed declaration."""
    _check_value(declaration, "declaration")
    text = json.dumps(declaration, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)
    return text.encode("utf-8")


def _check_value(value, where):
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_value(item, "%s[%d]" % (where, index))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise HashError("%s has a key that is not a string" % where)
            _check_value(item, "%s.%s" % (where, key))
        return
    raise HashError("%s holds a %s, which cannot be hashed" % (where, type(value).__name__))


def declaration_hash(declaration):
    return hashlib.sha256(canonical_bytes(declaration)).hexdigest()


TreeInfo = collections.namedtuple("TreeInfo", "hash files dirs contents")


def hash_tree(root_path, what="module", keep=None):
    """Hash every regular file below `root_path`; see the module docstring.

    Returns a ``TreeInfo``: the hash, the sorted regular-file paths, the sorted
    directory paths, and a dict of content for each file `keep(rel)` selects. Each
    file is read once, so the hash and the kept content come from the same bytes.
    """
    records = []
    files = []
    dirs = []
    contents = {}
    with safefs.Root(root_path, what) as root:
        for entry in root.walk():
            if entry.kind == "dir":
                dirs.append(entry.rel)
                continue
            if entry.kind != "file":
                raise HashError("%s contains a %s, which is not allowed: %s/%s"
                                % (what, entry.kind, root_path, entry.rel))
            data = root.read_file(entry.rel, expected=entry.identity)
            files.append(entry.rel)
            if keep is not None and keep(entry.rel):
                contents[entry.rel] = data
            records.append((entry.rel.encode("utf-8"),
                            hashlib.sha256(data).hexdigest(),
                            "x" if entry.executable else "-"))
    records.sort()
    digest = hashlib.sha256()
    for path, content, flag in records:
        digest.update(content.encode("ascii") + b" " + flag.encode("ascii") + b" " + path + b"\n")
    return TreeInfo(digest.hexdigest(), sorted(files), sorted(dirs), contents)


def tree_hash(root_path, what="module"):
    return hash_tree(root_path, what).hash

"""The paths git tracks, read from ``.git/index`` without running git.

``installer-interface.md`` allows a question to git only when git cannot read the repository's own
configuration or run anything it names, and a fixed list of ``-c`` options cannot promise that (a
filesystem monitor, a filter driver and an included file are all named by the repository). The
index is a plain binary file, so the paths are read from its bytes and no program runs and no
configuration is read. The index is untrusted: every length is checked against the bytes that are
there, the whole file is bounded, and anything the reader does not understand is refused.

Supported: index versions 2, 3 and 4, with SHA-1 or SHA-256 object names (told apart by the
checksum that ends the file, so the configuration is not read). Optional extensions (names that
start with an upper-case letter) are skipped. A required extension, such as the split index or a
sparse index, is refused because the paths are not all in this file.

"Tracked" here means "in the index": a file that is staged and not yet committed counts.
"""

import collections
import hashlib
import os
import struct

from . import projectfs
from .wbkit import display, safefs

LIMIT = safefs.MAX_FILE_BYTES
MAX_ENTRIES = 1000000
MAX_PATH = 4096
MAX_PATH_BYTES = 64 * 1024 * 1024

_HEADER = 12
_FIXED = 40  # the stat data in front of the object name
_LINK = 0o120000
_GITLINK = 0o160000
_TYPE = 0o170000

# `files` holds every tracked path, `dirs` every directory that holds one (and each submodule), and
# `links` the tracked paths that are symbolic links.
Tracked = collections.namedtuple("Tracked", "files dirs links")


class GitIndexError(Exception):
    """The index cannot be read as a git index; nothing is changed."""


def _hash_size(data):
    for size, make in ((20, hashlib.sha1), (32, hashlib.sha256)):
        if len(data) >= _HEADER + size and make(data[:-size]).digest() == data[-size:]:
            return size
    raise GitIndexError("the checksum at the end does not match, so it is damaged or is not a "
                        "git index")


def _varint(data, at, end):
    """The offset-encoded number at `at` and the position after it (the index version 4 form)."""
    if at >= end:
        raise GitIndexError("an entry is cut short")
    byte = data[at]
    at += 1
    value = byte & 0x7F
    while byte & 0x80:
        if at >= end or value > 1 << 40:
            raise GitIndexError("an entry has an invalid path length")
        byte = data[at]
        at += 1
        value = ((value + 1) << 7) + (byte & 0x7F)
    return value, at


def parse(data):
    """The ``Tracked`` paths in the index bytes `data`; a ``GitIndexError`` for anything else."""
    if len(data) < _HEADER or data[:4] != b"DIRC":
        raise GitIndexError("it does not start as a git index does")
    size = _hash_size(data)
    version, count = struct.unpack_from(">II", data, 4)
    if version not in (2, 3, 4):
        raise GitIndexError("index version %d is not supported" % version)
    if count > MAX_ENTRIES:
        raise GitIndexError("it lists %d entries, more than the %d that are read" % (count, MAX_ENTRIES))
    end = len(data) - size
    files, dirs, links = set(), set(), set()
    previous = b""
    spent = 0
    pos = _HEADER
    for _ in range(count):
        flags_at = pos + _FIXED + size
        if flags_at + 2 > end:
            raise GitIndexError("an entry is cut short")
        mode = struct.unpack_from(">I", data, pos + 24)[0]
        flags = struct.unpack_from(">H", data, flags_at)[0]
        at = flags_at + 2
        if flags & 0x4000:
            if version < 3:
                raise GitIndexError("a version 2 entry has extended flags")
            at += 2
        if version == 4:
            strip, at = _varint(data, at, end)
            nul = data.find(b"\0", at, end)
            if nul < 0 or strip > len(previous):
                raise GitIndexError("an entry has an invalid path")
            path = previous[:len(previous) - strip] + data[at:nul]
            pos = nul + 1
        else:
            nul = data.find(b"\0", at, end)
            if nul < 0:
                raise GitIndexError("an entry has no end to its path")
            path = data[at:nul]
            pos += (nul - pos + 1 + 7) // 8 * 8
        if not path:
            raise GitIndexError("an entry has an empty path, as in a split index, which is not supported")
        spent += len(path)
        if len(path) > MAX_PATH or spent > MAX_PATH_BYTES:
            raise GitIndexError("a path is longer than %d bytes, or the paths add up to more than "
                                "%d" % (MAX_PATH, MAX_PATH_BYTES))
        previous = path
        name = os.fsdecode(path)
        files.add(name)
        if mode & _TYPE == _LINK:
            links.add(name)
        if mode & _TYPE == _GITLINK:
            dirs.add(name)
        parent = name.rpartition("/")[0]
        while parent and parent not in dirs:
            dirs.add(parent)
            parent = parent.rpartition("/")[0]
    if pos > end:
        raise GitIndexError("the entries run past the end")
    while pos < end:
        if pos + 8 > end:
            raise GitIndexError("an extension is cut short")
        signature = data[pos:pos + 4]
        (length,) = struct.unpack_from(">I", data, pos + 4)
        if not 0x41 <= signature[0] <= 0x5A:
            raise GitIndexError("it needs the %s extension, which is not supported (a split or "
                                "sparse index)" % display.ascii_text(signature.decode("latin-1")))
        if pos + 8 + length > end:
            raise GitIndexError("an extension runs past the end")
        pos += 8 + length
    return Tracked(frozenset(files), frozenset(dirs), frozenset(links))


def read(writer):
    """The ``Tracked`` paths of the project `writer` holds. A project with no index tracks nothing."""
    try:
        data = writer.git_bytes("index", LIMIT)
    except (projectfs.WriteConflict, safefs.SafeFsError) as exc:
        raise GitIndexError("it cannot be read: %s" % display.ascii_text(str(exc))[:200])
    if data is None:
        return Tracked(frozenset(), frozenset(), frozenset())
    return parse(data)

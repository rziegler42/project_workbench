"""The paths git tracks, read from ``.git/index`` without running git.

The parser is the kit's (``wbkit/gitindex.py``, which holds the reasoning and the limits), so that a
check helper and the installer read an index the same way. This module reads the bytes through the
installer's writer and hands them over.
"""

from . import projectfs
from .wbkit import display, safefs
from .wbkit.gitindex import (GitIndexError, LIMIT, MAX_ENTRIES, MAX_PATH, MAX_PATH_BYTES,  # noqa: F401
                             Tracked, parse)


def read(writer):
    """The ``Tracked`` paths of the project `writer` holds. A project with no index tracks nothing."""
    try:
        data = writer.git_bytes("index", LIMIT)
    except (projectfs.WriteConflict, safefs.SafeFsError) as exc:
        raise GitIndexError("it cannot be read: %s" % display.ascii_text(str(exc))[:200])
    if data is None:
        return Tracked(frozenset(), frozenset(), frozenset())
    return parse(data)

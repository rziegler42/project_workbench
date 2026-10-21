"""Where the packages of an install come from: the argument parser and the cache lookup.

``--package <source>`` may repeat; a ``--ref <ref>`` binds to the nearest ``--package`` before it
and may appear at most once per package; ``--select`` names modules as ``verify`` does. The
options are read in order by hand, because ``argparse`` cannot associate them
(``docs/specs/installer-interface.md``).

``resolve_cached`` never contacts the network, never writes and never creates a directory. A
local package directory is used as it is (the approval gate still applies to it). A URL, or a
local repository, must already be in the cache because ``approve --source`` downloaded it.
"""

import collections
import os
import re
import stat

from . import declarations, fetch, safefs

Parsed = collections.namedtuple("Parsed", "positional dir_option packages select")
# What a project command works from once its target has been chosen.
Command = collections.namedtuple("Command", "target packages select")
Resolved = collections.namedtuple("Resolved", "path source ref commit local")

_CACHE_ID = re.compile(r"^[0-9a-f]{20}\Z")


class UsageError(Exception):
    """The arguments are not valid (exit 2)."""


class SourceError(Exception):
    """A source cannot be used; the message names it."""


def _value(tokens, index, option):
    if index + 1 >= len(tokens) or tokens[index + 1] == "" or tokens[index + 1].startswith("-"):
        raise UsageError("%s needs a value" % option)
    return tokens[index + 1]


def parse_install(tokens, upgrade=False):
    """Read the arguments of ``install`` or ``preview install`` into a ``Parsed``.

    With `upgrade`, the arguments of ``upgrade``: ``--package`` is optional, since the project
    records its own, and ``--select`` is not accepted, since the project records its modules.

    The target goes before ``--select`` (which takes every name up to the next option), or
    is given with ``--dir``. Anything unknown, empty or out of place is a ``UsageError``.
    """
    positional = dir_option = None
    packages = []          # [source, ref or None], in order
    select = None
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "":
            raise UsageError("an argument may not be empty")
        if token == "--package":
            packages.append([_value(tokens, index, token), None])
            index += 2
        elif token == "--ref":
            if not packages:
                raise UsageError("--ref needs a --package before it")
            if packages[-1][1] is not None:
                raise UsageError("--ref was given twice for one --package")
            packages[-1][1] = _value(tokens, index, token)
            index += 2
        elif token == "--dir":
            if dir_option is not None:
                raise UsageError("--dir was given twice")
            dir_option = _value(tokens, index, token)
            index += 2
        elif token == "--select":
            if upgrade:
                raise UsageError("--select is not used: the modules are those the project records")
            if select is not None:
                raise UsageError("--select was given twice")
            select = []
            index += 1
            while index < len(tokens) and not tokens[index].startswith("-"):
                if tokens[index] == "":
                    raise UsageError("a module name may not be empty")
                select.append(tokens[index])
                index += 1
            if not select:
                raise UsageError("--select needs at least one module")
        elif token.startswith("-"):
            raise UsageError("unknown option %s" % token)
        else:
            if positional is not None:
                raise UsageError("more than one target was given")
            positional = token
            index += 1
    if upgrade:
        return Parsed(positional, dir_option, [tuple(item) for item in packages], None)
    if not packages:
        raise UsageError("at least one --package is required")
    if select is None:
        raise UsageError("--select is required")
    return Parsed(positional, dir_option, [tuple(item) for item in packages], select)


def parse_packages(tokens):
    """The ordered ``(source, ref or None)`` pairs of `tokens`."""
    return parse_install(tokens).packages


def _shown(source):
    from . import installplan
    from .wbkit import display
    return display.ascii_text(installplan.public_source(source))[:200]


def _is_url(source):
    return "://" in source


def local_package(source):
    if _is_url(source):
        return None
    absolute = os.path.abspath(source)
    try:
        info = os.lstat(absolute)
    except OSError:
        return None
    if stat.S_ISLNK(info.st_mode):
        raise SourceError("%s is a symbolic link; give the real path" % _shown(source))
    if not stat.S_ISDIR(info.st_mode):
        return None
    return absolute if os.path.lexists(os.path.join(absolute, "package.json")) else None


def _plain_directory(source):
    """True for an existing real directory that is not a package (no package.json)."""
    if _is_url(source):
        return False
    try:
        return stat.S_ISDIR(os.lstat(os.path.abspath(source)).st_mode)
    except OSError:
        return False


def _cache_entries(store):
    cache = os.path.join(store.root, "cache")
    try:
        fd = safefs.open_root(cache, "cache")
    except safefs.SafeFsError:
        return []
    try:
        return sorted(name for name in os.listdir(fd) if _CACHE_ID.match(name))
    finally:
        os.close(fd)


def resolve_cached(store, source, ref):
    """The package for `source`: a local package directory, or an approved download's copy.

    Returns a ``Resolved``. Raises ``SourceError`` for a source that is not usable and names it.
    """
    local = local_package(source)
    if local is not None:
        if ref is not None:
            raise SourceError("a --ref cannot apply to the local package directory %s"
                              % _shown(source))
        return Resolved(local, source, "", "", True)
    wanted = ref or "HEAD"
    found = []
    for name in _cache_entries(store):
        try:
            record = declarations.parse_json(store.read("cache/%s/fetch.json" % name))
        except (ValueError, safefs.SafeFsError):
            continue
        if record.get("source") != source or record.get("ref") != wanted:
            continue
        if not all(isinstance(record.get(key), str) for key in ("commit", "time")):
            continue
        try:
            if store.kind("cache/%s/package" % name) != "dir":
                continue
        except safefs.SafeFsError:
            continue
        found.append((record["time"], name, record["commit"]))
    if not found:
        if _plain_directory(source):
            raise SourceError("%s is a directory without a package.json, and no download of it "
                              "(ref %s) is cached" % (_shown(source), wanted))
        raise SourceError("%s (ref %s) has not been downloaded; the owner runs "
                          "`wb approve --source` first, and preview never fetches"
                          % (_shown(source), wanted))
    _, name, commit = max(found)
    return Resolved(os.path.join(store.root, "cache", name, "package"), source, wanted,
                    commit, False)

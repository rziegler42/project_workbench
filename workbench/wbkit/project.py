"""Finding the workbench project around a directory, and the project ID recorded in its manifest.

The finder looks at the filesystem with ``lstat`` only, so a link never makes a directory a project.
``read_id`` reads the committed manifest through the no-follow reader and derives the ID from its
``seed``. It does not validate the manifest: it checks that the file is a JSON object with a plain
``seed`` and nothing else, because the installer's strict parse (``workbench.manifest.parse``) is the
writer-side validator and a helper must not take this for it. The derivation of the ID is here, once;
the installer's ``manifest.project_id`` calls it.
"""

import hashlib
import json
import os
import re
import stat

from . import display, safefs

MANIFEST = ".workbench/manifest.json"
MAX_DEPTH = 64

_SEED = r"[A-Za-z0-9._-]{1,128}"


class ProjectError(Exception):
    """No project was found, or its manifest cannot give an ID; the message says why."""


class SeedError(ProjectError):
    """A seed is not a plain token of at most 128 characters."""


def find_root(start):
    """The nearest directory at or above `start` that holds a `.git` directory and a regular
    `.workbench/manifest.json` in a real `.workbench` directory. Links never count. At most
    `MAX_DEPTH` directories are tried."""
    here = start
    for _ in range(MAX_DEPTH):
        try:
            git = os.lstat(os.path.join(here, ".git"))
            inner = os.lstat(os.path.join(here, ".workbench"))
            document = os.lstat(os.path.join(here, *MANIFEST.split("/")))
        except OSError:
            git = None
        if git is not None and stat.S_ISDIR(git.st_mode) and stat.S_ISDIR(inner.st_mode) \
                and stat.S_ISREG(document.st_mode):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    raise ProjectError("this is not inside a workbench project (no .git with %s at or above %s)"
                       % (MANIFEST, display.ascii_text(start)[:200]))


def check_seed(seed):
    """`seed`, if it is a plain token of at most 128 characters; `SeedError` otherwise."""
    if not isinstance(seed, str) or not re.fullmatch(_SEED, seed):
        raise SeedError("the seed is not a plain token of at most 128 characters")
    return seed


def project_id(seed):
    """The project ID: SHA-256 of the seed as 64 lowercase hex digits."""
    return hashlib.sha256(check_seed(seed).encode("ascii")).hexdigest()


def read_id(root):
    """The project ID recorded in the manifest at `root`. Only the seed is checked."""
    try:
        with safefs.Root(root, "project root") as project:
            document = json.loads(project.read_file(MANIFEST))
    except (safefs.SafeFsError, ValueError, RecursionError) as exc:
        raise ProjectError("the project manifest cannot be used: %s" % display.clean(str(exc))[:200])
    if not isinstance(document, dict) or "seed" not in document:
        raise ProjectError("the project manifest cannot be used: it has no seed")
    try:
        return project_id(document["seed"])
    except SeedError as exc:
        raise ProjectError("the project manifest cannot be used: %s" % exc)

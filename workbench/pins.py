"""Pins: the hash of a helper the owner has allowed to be launched.

A helper such as the commit helper is a file of a module, so a pulled edit could replace it.
The owner pins it: this records, for a project, the helper's path relative to the project
root and the SHA-256 of its content, in the guarded store at ``projects/<id>/pins``. The path is
relative because clones of one project sit at different absolute paths. The launcher
(``launch.py``) runs a helper only when its current bytes match the pin; a pulled edit changes
the hash and the helper is not run until the owner pins it again.

The file is strict JSON::

    {"format": 1, "pins": {"<name>": {"path": "<relative>", "pinned_by": "<user>",
                                      "sha256": "<64 hex>", "time": "<UTC>"}}}

Reading fails closed: a missing file means no pins, and anything unreadable, malformed or not
a regular file raises ``PinError``. The project id is the hash of the project's seed
(``repository-boundary.md``): 64 lowercase hex digits, which also makes it safe as a
directory name. Writing is atomic and is done only by ``run``, the owner-run ``pin`` command,
which needs a terminal in the same way as ``approve`` and asks the owner to type the first
twelve characters of the hash shown. As with approvals, that is friction and not the barrier;
the barrier is the harness's deny rule on this command and on the store.
"""

import collections
import hashlib
import json
import os
import re

from . import approvals, approve, declarations, safefs
from .wbkit import display

FORMAT = 1
CONFIRM_CHARS = 12
PREVIEW_LINES = 15
PREVIEW_WIDTH = 160

_ID = re.compile(r"^[0-9a-f]{64}\Z")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}\Z")
_HEX = re.compile(r"^[0-9a-f]{64}\Z")
_TIME = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_FIELDS = ("path", "pinned_by", "sha256", "time")

Pin = collections.namedtuple("Pin", "name path sha256 pinned_by time")


class PinError(Exception):
    """A pin is missing, malformed or unsafe; nothing is launched."""


def check_id(project_id):
    if not isinstance(project_id, str) or not _ID.match(project_id):
        raise PinError("the project id is 64 lowercase hex digits")
    return project_id


def check_name(name):
    if not isinstance(name, str) or not _NAME.match(name):
        raise PinError("a helper name is letters, digits and ._+-, at most 64 characters, "
                       "starting with a letter or digit")
    return name


def _file(project_id):
    return "projects/%s/pins" % check_id(project_id)


def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


# --- the file -------------------------------------------------------------------


def parse(data):
    """Parse the bytes of a pins file into ``{name: Pin}`` or raise PinError."""
    try:
        document = declarations.parse_json(data)
    except ValueError as exc:
        raise PinError("the pins file is not valid (%s)" % exc)
    if set(document) != {"format", "pins"} or document["format"] != FORMAT \
            or isinstance(document["format"], bool) or not isinstance(document["pins"], dict):
        raise PinError("the pins file does not have the expected format")
    pins = {}
    for name, entry in document["pins"].items():
        check_name(name)
        if not isinstance(entry, dict) or set(entry) != set(_FIELDS):
            raise PinError("pin %s has the wrong fields" % display.ascii_text(name)[:80])
        path = entry["path"]
        if not isinstance(path, str) or not safefs.relpath_ok(path):
            raise PinError("pin %s names an unsafe path" % display.ascii_text(name)[:80])
        if not isinstance(entry["sha256"], str) or not _HEX.match(entry["sha256"]):
            raise PinError("pin %s has a bad hash" % display.ascii_text(name)[:80])
        who = entry["pinned_by"]
        if not isinstance(who, str) or not who or len(who) > 64 or not who.isprintable():
            raise PinError("pin %s has a bad pinned_by" % display.ascii_text(name)[:80])
        if not isinstance(entry["time"], str) or not _TIME.match(entry["time"]):
            raise PinError("pin %s has a bad time" % display.ascii_text(name)[:80])
        pins[name] = Pin(name, path, entry["sha256"], who, entry["time"])
    return pins


def serialize(pins):
    document = {"format": FORMAT, "pins": {
        name: {"path": pin.path, "pinned_by": pin.pinned_by, "sha256": pin.sha256, "time": pin.time}
        for name, pin in sorted(pins.items())}}
    return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def load(store, project_id):
    """All pins of a project, or ``{}`` when there is no file. Raises PinError if unusable."""
    rel = _file(project_id)
    try:
        found = store.kind(rel)
        if found is None:
            return {}
        if found != "file":
            raise PinError("the pins entry is not a regular file (%s)" % found)
        return parse(store.read(rel))
    except safefs.SafeFsError as exc:
        raise PinError("the pins file cannot be read: %s" % exc)


def lookup(store, project_id, name):
    check_name(name)
    pins = load(store, project_id)
    if name not in pins:
        raise PinError("no pin named %s for this project" % display.ascii_text(name)[:80])
    return pins[name]


def set_pin(store, project_id, name, path, sha256, pinned_by, time=None):
    """Record or replace one pin, keeping the others. Refuses to touch a damaged file."""
    check_name(name)
    pins = load(store, project_id)
    pins[name] = Pin(name, path, sha256, pinned_by, time or approvals.utc_now())
    data = serialize(pins)
    parse(data)   # nothing is written that a read would refuse
    try:
        store.write(_file(project_id), data)
    except safefs.SafeFsError as exc:
        raise PinError("the pins file cannot be written: %s" % exc)
    return pins[name]


# --- the owner-run command ------------------------------------------------------


def _refuse(err, text):
    err.write("refused: %s\n" % display.clean(text))
    return 1


def _relative_inside(root, helper):
    root_abs = os.path.abspath(root)
    helper_abs = os.path.abspath(helper)
    prefix = root_abs.rstrip(os.sep) + os.sep
    if not helper_abs.startswith(prefix):
        raise PinError("the helper is not inside the project root")
    rel = helper_abs[len(prefix):]
    if not safefs.relpath_ok(rel):
        raise PinError("the helper's path in the project is not allowed (it may not name .git, "
                       "hold a backslash or colon, or be unprintable)")
    return root_abs, rel


def _read_helper(root_abs, rel):
    try:
        with safefs.Root(root_abs, "project root") as root:
            return root.read_file(rel)
    except safefs.SafeFsError as exc:
        raise PinError("the helper cannot be read: %s" % exc)


def _preview(data):
    text = data.decode("utf-8", "replace")
    lines = text.splitlines()[:PREVIEW_LINES]
    shown = ["    " + display.ascii_text(line)[:PREVIEW_WIDTH] for line in lines]
    more = "    ..." if len(text.splitlines()) > PREVIEW_LINES else ""
    return "\n".join(shown + ([more] if more else []))


def run(store, project_id, name, helper, root, stdin, stdout, err):
    """Pin `helper` (a file inside `root`) under `name`. Returns the exit code."""
    if not (approve.is_terminal(stdin) and approve.is_terminal(stdout)):
        return _refuse(err, "pinning is owner-run: standard input and output must both be "
                            "terminals. Run this command yourself, from your own terminal.")
    try:
        check_id(project_id)
        check_name(name)
        root_abs, rel = _relative_inside(root, helper)
        data = _read_helper(root_abs, rel)
        existing = load(store, project_id).get(name)
    except PinError as exc:
        return _refuse(err, str(exc))
    digest = hash_bytes(data)

    stdout.write("pin helper %s for project %s\n" % (display.ascii_text(name), project_id))
    stdout.write("  path in the project: %s\n" % display.ascii_text(rel))
    stdout.write("  size:   %d bytes\n  sha256: %s\n" % (len(data), digest))
    if existing is not None:
        stdout.write("  this REPLACES the pin %s (hash %s, pinned %s)\n" % (
            display.ascii_text(existing.path), existing.sha256, existing.time))
    stdout.write("  beginning of the file:\n%s\n\n" % _preview(data))
    stdout.write("From now on `launch` runs exactly these bytes and refuses any other. Read the "
                 "file first.\nTo pin it, type the first %d characters of the sha256 shown above "
                 "and press Enter.\nAnything else cancels and records nothing.\n> " % CONFIRM_CHARS)
    stdout.flush()
    if stdin.readline(200).strip() != digest[:CONFIRM_CHARS]:
        stdout.write("cancelled: nothing was recorded\n")
        return 1
    try:
        if hash_bytes(_read_helper(root_abs, rel)) != digest:
            return _refuse(err, "the helper changed while it was shown; nothing was recorded")
        pin = set_pin(store, project_id, name, rel, digest, approve.approver_name())
    except PinError as exc:
        return _refuse(err, str(exc))
    stdout.write("pinned %s -> %s (sha256 %s)\n" % (display.ascii_text(pin.name),
                                                    display.ascii_text(pin.path), pin.sha256))
    return 0

"""Approval records: what the owner has approved on this machine, bound to hashes.

An approval is a file ``packages/<key>/approval.json`` in the guarded store. ``<key>`` is
the SHA-256 of ``"<kind>\\n<declaration hash>\\n<tree hash>\\n"``, so a record is found
only by presenting the hashes it binds to, and a changed declaration or changed content
is a different key and has no approval. Two kinds exist:

* ``module``: subject ``<package>/<module>``, bound to that module's declaration hash
  and tree hash (``docs/specs/module-contract.md``).
* ``package``: subject ``<package>``, bound to the package declaration's hash and the
  tree hash of the whole package directory. It also lists the modules it approved (name
  and both hashes each) and the resolved git commit, when the package came from one.

The record is strict JSON with exactly these fields, no others::

    format 1, kind, subject, declaration_hash, tree_hash, approver, time (UTC,
    ``YYYY-MM-DDTHH:MM:SSZ``), workbench_version, and for a package also modules and
    commit (a lowercase hex commit id, or null).

A check fails closed. A record that is missing, is not a regular file inside a real
directory, cannot be read, is malformed, or whose stored hashes, kind or key differ from
what was presented is no approval, and the reason says which. Nothing here raises for a
bad record. Writers refuse to replace a record that differs in what it binds; approving
the same thing again keeps the first record (and its time and approver).

A record is not signed. Its protection is where it lives: the guarded store, which only
the owner may write (``docs/specs/trust-and-approval.md``). The writers here are called
only by the owner-run approve command and by the release-time generator.

The key covers the hashes only, as the plan states, so the subject is compared by every
check: the same bytes approved as ``a/m`` are not approved as ``b/m``, and recording
``b/m`` while ``a/m`` holds those hashes is refused.

Writers raise ApprovalError for a refusal of their own and SafeFsError when the store
itself is unsafe (the same error the store raises). Checks never raise.
"""

import collections
import datetime
import hashlib
import json
import re

from . import __version__, declarations, safefs

FORMAT = 1
KINDS = ("module", "package")
RECORD_NAME = "approval.json"

_HEX64 = re.compile(r"^[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"^([0-9a-f]{40}|[0-9a-f]{64})\Z")
_TIME = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_COMMON = ("format", "kind", "subject", "declaration_hash", "tree_hash", "approver", "time",
           "workbench_version")
_MODULE_ENTRY = ("name", "declaration_hash", "tree_hash")

Approval = collections.namedtuple(
    "Approval", "kind subject declaration_hash tree_hash approver time workbench_version "
                "modules commit")
Check = collections.namedtuple("Check", "approved record reason")


class ApprovalError(Exception):
    """A record is malformed, or a write would replace a different record."""


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_key(kind, declaration_hash, tree_hash):
    if kind not in KINDS:
        raise ApprovalError("unknown approval kind: %r" % (kind,))
    for name, value in (("declaration hash", declaration_hash), ("tree hash", tree_hash)):
        if not isinstance(value, str) or not _HEX64.match(value):
            raise ApprovalError("the %s is not 64 lowercase hex digits" % name)
    text = "%s\n%s\n%s\n" % (kind, declaration_hash, tree_hash)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def _path(key):
    return "packages/%s/%s" % (key, RECORD_NAME)


# --- parsing --------------------------------------------------------------------


def _text(document, field, limit=64):
    value = document[field]
    if not isinstance(value, str) or not value or len(value) > limit or not value.isprintable():
        raise ApprovalError("'%s' must be non-empty printable text of at most %d characters"
                            % (field, limit))
    return value


def _hash(value, what):
    if not isinstance(value, str) or not _HEX64.match(value):
        raise ApprovalError("%s must be 64 lowercase hex digits" % what)
    return value


def _name(value, what):
    if not isinstance(value, str) or not declarations.NAME_RE.match(value) or len(value) > 64:
        raise ApprovalError("%s is not a valid name" % what)
    return value


def _timestamp(value):
    if not isinstance(value, str) or not _TIME.match(value):
        raise ApprovalError("'time' must be UTC as YYYY-MM-DDTHH:MM:SSZ")
    try:
        datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise ApprovalError("'time' is not a real date and time")
    return value


def parse_record(data):
    """Parse record bytes into an Approval or raise ApprovalError."""
    try:
        document = declarations.parse_json(data)
    except ValueError as exc:
        raise ApprovalError("not a valid record (%s)" % exc)
    kind = document.get("kind")
    if kind not in KINDS:
        raise ApprovalError("'kind' must be 'module' or 'package'")
    expected = set(_COMMON) | ({"modules", "commit"} if kind == "package" else set())
    if set(document) != expected:
        missing = sorted(expected - set(document))
        extra = sorted(set(document) - expected)
        raise ApprovalError("fields differ from the %s record format (missing %s, unknown %s)"
                            % (kind, missing, [declarations._shown(item) for item in extra]))
    if document["format"] != FORMAT or isinstance(document["format"], bool):
        raise ApprovalError("unsupported record format")
    subject = _text(document, "subject", 129)
    if kind == "module":
        parts = subject.split("/")
        if len(parts) != 2:
            raise ApprovalError("a module subject is <package>/<module>")
        for part in parts:
            _name(part, "the subject")
    else:
        _name(subject, "the subject")
    modules, commit = (), None
    if kind == "package":
        modules = _modules(document["modules"])
        commit = document["commit"]
        if commit is not None and (not isinstance(commit, str) or not _COMMIT.match(commit)):
            raise ApprovalError("'commit' must be null or a lowercase hex commit id")
    return Approval(kind, subject,
                    _hash(document["declaration_hash"], "'declaration_hash'"),
                    _hash(document["tree_hash"], "'tree_hash'"),
                    _text(document, "approver"), _timestamp(document["time"]),
                    _text(document, "workbench_version"), modules, commit)


def _modules(value):
    if not isinstance(value, list):
        raise ApprovalError("'modules' must be a list")
    seen, out = set(), []
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != set(_MODULE_ENTRY):
            raise ApprovalError("each module entry has exactly name, declaration_hash and tree_hash")
        name = _name(entry["name"], "a module name")
        if name in seen:
            raise ApprovalError("module %r is listed twice" % name)
        seen.add(name)
        out.append((name, _hash(entry["declaration_hash"], "a module declaration_hash"),
                    _hash(entry["tree_hash"], "a module tree_hash")))
    return tuple(sorted(out))


# --- writing --------------------------------------------------------------------


def _document(approval):
    document = {
        "format": FORMAT, "kind": approval.kind, "subject": approval.subject,
        "declaration_hash": approval.declaration_hash, "tree_hash": approval.tree_hash,
        "approver": approval.approver, "time": approval.time,
        "workbench_version": approval.workbench_version,
    }
    if approval.kind == "package":
        document["modules"] = [
            {"name": n, "declaration_hash": d, "tree_hash": t} for n, d, t in approval.modules]
        document["commit"] = approval.commit
    return document


def serialize(approval):
    text = json.dumps(_document(approval), sort_keys=True, indent=2, ensure_ascii=True) + "\n"
    return text.encode("ascii")


def _binding(approval):
    return (approval.kind, approval.subject, approval.declaration_hash, approval.tree_hash,
            approval.modules, approval.commit)


def _write(store, approval):
    # Round trip through the parser, so nothing is written that a check would refuse.
    candidate = parse_record(serialize(approval))
    key = record_key(candidate.kind, candidate.declaration_hash, candidate.tree_hash)
    path = _path(key)
    found = store.kind("packages/" + key)
    if found is not None:
        existing = _lookup(store, candidate.kind, candidate.declaration_hash,
                           candidate.tree_hash)
        if not existing.approved:
            raise ApprovalError("a record already exists here and is not usable (%s); it is "
                                "not replaced" % existing.reason)
        if _binding(existing.record) != _binding(candidate):
            raise ApprovalError("a different record already binds these hashes; it is not replaced")
        return existing.record
    store.write(path, serialize(candidate))
    return candidate


def record_module(store, subject, declaration_hash, tree_hash, approver, time=None,
                  workbench_version=__version__):
    """Record that the owner approved one module. Returns the Approval now on file."""
    return _write(store, Approval("module", subject, declaration_hash, tree_hash, approver,
                                  utc_now() if time is None else time, workbench_version, (), None))


def record_package(store, subject, declaration_hash, tree_hash, modules, approver, time=None,
                   commit=None, workbench_version=__version__):
    """Record that the owner approved a package and exactly the listed modules.

    `modules` is a list of ``(name, declaration_hash, tree_hash)``.
    """
    if (not isinstance(modules, (list, tuple))
            or any(not isinstance(m, (list, tuple)) or len(m) != 3 for m in modules)):
        raise ApprovalError("modules must be a list of (name, declaration_hash, tree_hash)")
    return _write(store, Approval("package", subject, declaration_hash, tree_hash, approver,
                                  utc_now() if time is None else time, workbench_version,
                                  tuple(sorted(tuple(m) for m in modules)), commit))


# --- checking -------------------------------------------------------------------


def _no(reason):
    return Check(False, None, reason)


def _lookup(store, kind, declaration_hash, tree_hash):
    """The valid record of this kind bound to these hashes, whatever its subject."""
    try:
        key = record_key(kind, declaration_hash, tree_hash)
    except ApprovalError as exc:
        return _no(str(exc))
    directory = "packages/" + key
    try:
        found = store.kind(directory)
        if found is None:
            return _no("no approval is recorded for these hashes")
        if found != "dir":
            return _no("the approval entry is not a directory (%s)" % found)
        found = store.kind(directory + "/" + RECORD_NAME)
        if found is None:
            return _no("the approval entry has no record")
        if found != "file":
            return _no("the approval record is not a regular file (%s)" % found)
        record = parse_record(store.read(directory + "/" + RECORD_NAME))
    except safefs.SafeFsError as exc:
        return _no("the approval record cannot be read (%s)" % exc)
    except ApprovalError as exc:
        return _no("the approval record is malformed (%s)" % exc)
    if record.kind != kind:
        return _no("the approval record is for a %s, not a %s" % (record.kind, kind))
    if (record.declaration_hash, record.tree_hash) != (declaration_hash, tree_hash):
        return _no("the approval record binds different hashes")
    return Check(True, record, "")


def check(store, kind, subject, declaration_hash, tree_hash):
    """Is there a valid approval of this kind, for this subject, bound to these hashes?

    The key covers the hashes only, so the subject is compared here: a byte-identical
    module in another package is not approved by the first package's approval.
    """
    if not isinstance(subject, str):
        return _no("the subject is not text")
    found = _lookup(store, kind, declaration_hash, tree_hash)
    if found.approved and found.record.subject != subject:
        return _no("these hashes are approved for %s, not for %s"
                   % (declarations._shown(found.record.subject), declarations._shown(subject)))
    return found


def check_module(store, subject, declaration_hash, tree_hash):
    """`subject` is ``<package>/<module>``."""
    return check(store, "module", subject, declaration_hash, tree_hash)


def check_package(store, subject, declaration_hash, tree_hash):
    """`subject` is the package name."""
    return check(store, "package", subject, declaration_hash, tree_hash)

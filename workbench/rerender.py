"""``wb preview rerender``: what re-rendering the permissions of an attached harness would change. Read only.

A level in the owner's table is rendered into one file, the harness's permissions file, and into the rendering record in
the guarded store (``rendering.py``). When the table changes after attach the record no longer matches it, so a relaxed
key reads ``block`` until the file and the record are rendered again (``docs/specs/harness-rerender.md``). This module
builds that plan from the harness the clone records and the table now, and prints it with a digest. It writes nothing.

The plan is made as attach makes its own (``attach.stage``), from the packages the project records and the harness
package. It keeps the ``allow`` rules found in the live permissions file, which nothing here renders, and lists every
other entry of the live file that the new file will not have. The digest covers all of it, and the identity of every
package and module the staging read, so that an input that changes without changing the rendered file still changes the
digest.
"""

import collections
import copy
import hashlib
import json
import shutil

from . import attach, declarations, localmanifest, projectfs, refusal, rendering, target
from .wbkit import display, safefs

Command = attach.Command
Refused = refusal.Refused


def parse(tokens):
    """A ``Command`` from ``[<target> | --dir <path>] [--package <source> [--ref <ref>]] ...``. The harness is the one
    the clone records, so there is no ``--harness``."""
    return attach.parse(tokens, harness_required=False)


# `files` are ``(shown name, old hash or None, new hash)`` in the order they are listed; `keys` are ``(key, old, new)``;
# `kept` are the rules carried over; `removed` are ``(path, text)`` entries of the live file the new one will not have.
Plan = collections.namedtuple(
    "Plan", "path token version files keys kept removed notes warnings inputs digest changes settings data record "
            "manifest old_hash")

NOTHING = "nothing to change"
ALLOW = "allow"


def digest_of(body):
    """The digest of a plan's body, a canonical JSON text."""
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def harness_differs(recorded, document):
    """True when the harness module staged now is not the one the local manifest recorded at attach."""
    return (recorded["tree"], recorded["module_version"]) != (document["tree"], document["module_version"])


def _entries(node, path=()):
    """Every leaf of a JSON document as ``(path, text)``; the items of a list are leaves at the list's path."""
    if isinstance(node, dict):
        for key in sorted(node):
            yield from _entries(node[key], path + (key,))
    elif isinstance(node, list):
        for item in node:
            yield (path, json.dumps(item, sort_keys=True))
    else:
        yield (path, json.dumps(node))


def _allow_path(document):
    """The path of the ``allow`` list that sits beside the rendered ``deny`` list, or None. The layout ties the rendered
    actions to ``deny`` and ``ask`` and nothing renders an ``allow``, so the list is the sibling of those two."""
    def find(node, path):
        if isinstance(node, dict):
            if isinstance(node.get("deny"), list):
                return path
            for key in sorted(node):
                found = find(node[key], path + (key,))
                if found is not None:
                    return found
        return None
    return find(document, ())


def _node(document, path):
    for part in path:
        document = document.get(part) if isinstance(document, dict) else None
    return document


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _shown(text):
    return display.ascii_text(str(text))[:200]


def _whole(text):
    """A rule or an entry as the owner reads it before confirming: never cut, because the digest covers all of it and a cut
    would hide the end of a long rule."""
    return display.ascii_text(str(text))


def build(guarded, held, command, distribution=None, version=None, which=shutil.which, home=None):
    """The ``Plan``; raises ``Refused``. Nothing is written."""
    if held.state != "existing":
        raise Refused(["the target is not an existing project; use install"])
    writer = projectfs.Writer(held)
    try:
        recorded = localmanifest.read(writer)
    except localmanifest.LocalManifestError as exc:
        raise Refused(["the local manifest cannot be used: %s" % exc])
    if recorded is None:
        raise Refused(["this clone records no harness; run `wb attach --harness <package>/<module>` first"])
    done = attach.stage(guarded, held, writer, command.packages, (None, recorded["harness"]), distribution, version,
                        which, home)
    staged = done.staged
    if staged.settings is None or staged.rendering is None:
        raise Refused(["this harness renders no permissions, so there is nothing to re-render"])
    path = staged.settings
    planned = next(item for item in staged.files if item.path == path)

    try:
        state = writer.read_file(path)
    except safefs.SafeFsError as exc:
        raise Refused(["%s: %s" % (_shown(path), exc)])
    if state is None:
        raise Refused(["%s: the permissions file is not there, so it cannot be replaced; its absence is not a state "
                       "this command repairs" % _shown(path)])
    try:
        live = declarations.parse_json(state.data)
        fresh = declarations.parse_json(planned.data)
    except ValueError as exc:
        raise Refused(["%s: the file is not valid JSON: %s" % (_shown(path), _shown(exc))])
    if not isinstance(live, dict) or not isinstance(fresh, dict):
        raise Refused(["%s: the file is not a JSON object" % _shown(path)])

    # With no `deny` list in the fresh file there is no `allow` to carry into; the live `allow` rules are then listed as
    # removed. The layout always renders a deny for the guarded store, so this does not arise with a harness we ship.
    allow = _allow_path(fresh)
    carried = []
    if allow is not None:
        found = _node(live, allow)
        found = found.get(ALLOW) if isinstance(found, dict) else None
        if isinstance(found, list):
            carried = sorted({item for item in found if isinstance(item, str)})
    if carried:
        merged = copy.deepcopy(fresh)
        node = merged
        for part in allow:
            node = node.setdefault(part, {})
        node[ALLOW] = carried
        data = (json.dumps(merged, indent=2, sort_keys=True) + "\n").encode("utf-8")
    else:
        data = planned.data
    if len(data) > attach.MAX_WRITE_BYTES:
        raise Refused(["%s: the file would be larger than %d bytes" % (_shown(path), attach.MAX_WRITE_BYTES)])
    new_hash = _sha(data)

    wanted = set(_entries(fresh))
    kept = set((allow + (ALLOW,), json.dumps(item)) for item in carried) if allow is not None else set()
    removed = sorted(entry for entry in set(_entries(live)) if entry not in wanted and entry not in kept)

    old_record = rendering.read(guarded, done.project)
    new_record = rendering.with_shared_hash(dict(staged.rendering, file_hash=new_hash), held.path)
    old_keys = old_record["keys"] if old_record else {}
    keys = [(key, old_keys.get(key, "unrecorded"), new_record["keys"].get(key, "gone"))
            for key in sorted(set(old_keys) | set(new_record["keys"]))
            if old_keys.get(key) != new_record["keys"].get(key)]

    entries = [dict(item) for item in recorded["files"]]
    listed = [item for item in entries if item["path"] == path]
    if len(listed) != 1:
        raise Refused(["the local manifest does not list %s once, so it cannot record the new file" % _shown(path)])
    listed[0]["hash"] = new_hash
    new_manifest = dict(recorded, files=entries)
    try:
        old_manifest_hash = _sha(localmanifest.serialize(recorded))
        new_manifest_hash = _sha(localmanifest.serialize(new_manifest))
    except localmanifest.LocalManifestError as exc:
        raise Refused(["the local manifest cannot record the new file: %s" % exc])
    old_record_hash = _sha(rendering.serialize(old_record)) if old_record else None
    new_record_hash = _sha(rendering.serialize(new_record))

    files = [(path, state.hash, new_hash),
             (localmanifest.PATH, old_manifest_hash, new_manifest_hash),
             ("rendering record (guarded store)", old_record_hash, new_record_hash)]
    notes = []
    if harness_differs(recorded, staged.document):
        notes.append("the harness module differs from the one recorded at attach; only the permissions file is "
                     "replaced, and the other harness files stay as attach wrote them")
    changes = any(old != new for _, old, new in files)
    body = {"project": held.path, "harness": staged.token, "table": new_record["table_digest"],
            "files": [[name, old, new] for name, old, new in files], "kept": carried,
            "removed": [[list(where), text] for where, text in removed], "record": new_record,
            "manifest": new_manifest, "inputs": [list(item) for item in done.inputs]}
    return Plan(held.path, staged.token, staged.version, files, keys, carried, removed, notes, done.warnings,
                done.inputs, digest_of(body), changes, path, data, new_record, new_manifest, state.hash)


def render(plan):
    """The text of the preview."""
    lines = ["project: %s" % display.ascii_text(plan.path),
             "harness: %s %s" % (_shown(plan.token), _shown(plan.version))]
    if plan.keys:
        lines.append("rules:")
        lines.extend("  %s: %s -> %s" % (_shown(key), old, new) for key, old, new in plan.keys)
    lines.append("files:")
    for name, old, new in plan.files:
        if old == new:
            lines.append("  %s: left as it is" % _shown(name))
        else:
            lines.append("  %s: %s -> %s" % (_shown(name), (old or "none")[:12], new[:12]))
    lines.extend("kept: %s" % _whole(rule) for rule in plan.kept)
    lines.extend("removed: %s = %s" % (_whole(".".join(where)), _whole(text)) for where, text in plan.removed)
    lines.extend("note: %s" % _shown(note) for note in plan.notes)
    packages = sum(1 for item in plan.inputs if item[0] == "package")
    modules = sum(1 for item in plan.inputs if item[0] == "module")
    harness = next(item for item in plan.inputs if item[0] == "harness")
    lines.append("inputs: %d packages, %d modules, harness %s %s" % (packages, modules, _shown(harness[1]),
                                                                     _shown(harness[2])))
    lines.append("digest: %s" % plan.digest)
    if not plan.changes:
        lines.append(NOTHING)
    return "\n".join(lines) + "\n"


def run_preview(guarded, command, out, err, distribution=None, version=None, which=shutil.which, home=None):
    """Print the preview and return 0, or print ``refused:`` lines and return 1."""
    try:
        with target.open_target(command.target, guarded.root) as held:
            plan = build(guarded, held, command, distribution, version, which, home)
    except target.TargetError as exc:
        return target.write_refusal(err, exc)
    except Refused as exc:
        return attach._refusal(exc, err)
    except safefs.SafeFsError as exc:
        err.write("refused: %s\n" % display.clean(str(exc)))
        return 1
    for warning in plan.warnings:
        err.write("warning: %s\n" % display.clean(warning))
    out.write(render(plan))
    return 0

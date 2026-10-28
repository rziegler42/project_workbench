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

from . import approve, attach, confirm, declarations, localmanifest, preview, projectfs, refusal, rendering, target
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
            "manifest old_hash project old_manifest_hash")

NOTHING = "nothing to change"
ALLOW = "allow"
RECORD = "rendering record (guarded store)"
TERMINAL_ONLY = ("rerender is owner-run: standard input and output must both be terminals. Run this command yourself, "
                 "from your own terminal; `preview rerender` shows the same plan without writing.")
AGAIN = ("run `wb rerender` again with the same arguments: a file that already holds the new bytes is left as it is, and "
         "until it completes every key the table relaxes reads `block`")


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
    would hide the end of a long rule. Text that is not plain (a control character, a non-ASCII character, a leading or
    trailing space, a backslash) is shown as the JSON string it is, so that two different rules never read alike."""
    text = str(text)
    if text.isascii() and text.isprintable() and text == text.strip() and "\\" not in text:
        return text
    return json.dumps(text, ensure_ascii=True)


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
             (RECORD, old_record_hash, new_record_hash)]
    notes = []
    old_shared = old_record["shared"] if old_record else {"path": None, "hash": None}
    new_shared = new_record["shared"]
    if new_shared["path"] is not None and old_shared["hash"] != new_shared["hash"]:
        notes.append("the shared settings file %s is not what the rendering record watched (%s -> %s); this re-render "
                     "does not write it and records it as it is now, so read it before you confirm"
                     % (new_shared["path"], (old_shared["hash"] or "none")[:12], (new_shared["hash"] or "none")[:12]))
    if harness_differs(recorded, staged.document):
        notes.append("the harness module differs from the one recorded at attach; only the permissions file is "
                     "replaced, and the other harness files stay as attach wrote them")
    changes = any(old != new for _, old, new in files)
    body = {"project": held.path, "harness": staged.token, "table": new_record["table_digest"],
            "files": [[name, old, new] for name, old, new in files], "kept": carried,
            "removed": [[list(where), text] for where, text in removed], "record": new_record,
            "manifest": new_manifest, "inputs": [list(item) for item in done.inputs]}
    return Plan(held.path, staged.token, staged.version, files, keys, carried, removed, notes, done.warnings,
                done.inputs, digest_of(body), changes, path, data, new_record, new_manifest, state.hash, done.project,
                old_manifest_hash)


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


def _write(guarded, held, plan, done):
    """Write what `plan` changes, in this order: the permissions file, the local manifest's hash for it, then the record.
    A key is relaxed only while the record, the permissions file and the shared settings file agree, so until the record
    is written the old one names a hash the replaced file no longer has and every relaxed key reads ``block``: a stop at
    any step leaves the clone stricter than the table says and never looser. `done` lists the names written so far."""
    writer = projectfs.Writer(held)
    changing = [name for name, old, new in plan.files if old != new]
    if plan.settings in changing:
        writer.replace_file(plan.settings, plan.old_hash, plan.data)
        done.append(plan.settings)
    if localmanifest.PATH in changing:
        localmanifest.replace(writer, plan.old_manifest_hash, plan.manifest)
        done.append(localmanifest.PATH)
    if RECORD in changing:
        rendering.write(guarded, plan.project, plan.record)
        done.append(RECORD)


def _listed(out, title, items):
    if not items:
        return
    out.write("%s:\n" % title)
    for item in items[:confirm.LISTED]:
        out.write("  %s\n" % _shown(item))
    if len(items) > confirm.LISTED:
        out.write("  and %d more\n" % (len(items) - confirm.LISTED))


def _reconcile(held, plan, done):
    """Add to `done` a file that was renamed into place although the call did not return (an interrupt right after the
    rename), so that the report of a stop says what is on disk."""
    changing = {name for name, old, new in plan.files if old != new}
    expected = ((plan.settings, _sha(plan.data)), (localmanifest.PATH, _sha(localmanifest.serialize(plan.manifest))))
    for index, (path, wanted) in enumerate(expected):
        if path in changing and path not in done and rendering.live_hash(held.path, path) == wanted:
            done.insert(min(index, len(done)), path)


def _failed(cause, plan, done, err):
    """Report a stop after writing began: what was written, what was not, and how to finish."""
    err.write("failed: %s\n" % _shown(cause))
    _listed(err, "written", done)
    _listed(err, "not written", [name for name, old, new in plan.files if old != new and name not in done])
    err.write("if the failure came while a file was being written, nothing was renamed over the original, so the original "
              "file is as it was\n%s\n" % AGAIN)


def _refuse(err, text):
    err.write("refused: %s\n" % display.clean(text))
    return 1


def run(guarded, command, stdin, out, err, distribution=None, version=None, which=shutil.which, home=None):
    """Re-render after the owner types the digest, at a terminal; at no level does it run without one. Returns 0 done or
    nothing to change, 1 refused or cancelled, 3 stopped after writing began, 130 interrupted before it."""
    if not (approve.is_terminal(stdin) and approve.is_terminal(out)):
        return _refuse(err, TERMINAL_ONLY)
    started = False
    try:
        with target.open_target(command.target, guarded.root) as held:
            plan = build(guarded, held, command, distribution, version, which, home)
            for warning in plan.warnings:
                err.write("warning: %s\n" % display.clean(warning))
            out.write(render(plan))
            if not plan.changes:
                return 0
            out.write("\nTo re-render, type the first %d characters of the digest shown above and press Enter.\n"
                      "Anything else cancels and writes nothing.\n> " % confirm.CONFIRM_CHARS)
            out.flush()
            if not confirm.typed_matches(stdin, plan.digest):
                out.write("cancelled: nothing was written\n")
                return 1
            held.recheck()
            try:
                again = build(guarded, held, command, distribution, version, which, home)
            except Refused as exc:
                raise Refused(["the project, its packages or the settings changed while the plan was shown: %s; nothing "
                               "was written" % "; ".join(exc.lines)])
            if again.digest != plan.digest:
                return _refuse(err, "the plan changed while it was shown; nothing was written")
            done = []
            started = True
            try:
                _write(guarded, held, again, done)
            except (Exception, KeyboardInterrupt) as exc:
                _reconcile(held, again, done)
                if not done and not isinstance(exc, KeyboardInterrupt):
                    # The first replacement failed (a conflict, say): nothing was renamed over anything.
                    return _refuse(err, "%s; nothing was written" % _shown(exc))
                _failed("interrupted" if isinstance(exc, KeyboardInterrupt) else str(exc), again, done, err)
                return 3
            try:
                out.write("re-rendered %s in %s\n" % (_shown(again.token), display.ascii_text(held.path)))
                _listed(out, "wrote %d paths" % len(done), done)
                out.write("nothing was committed\n")
                out.flush()
            except (BrokenPipeError, KeyboardInterrupt):
                pass
            return 0
    except target.TargetError as exc:
        return target.write_refusal(err, exc)
    except Refused as exc:
        return attach._refusal(exc, err)
    except safefs.SafeFsError as exc:
        return _refuse(err, str(exc))
    except KeyboardInterrupt:
        if started:
            return 3
        out.write("\ncancelled: nothing was written\n")
        return 130


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

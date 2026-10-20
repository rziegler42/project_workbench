"""``wb preview upgrade`` and ``wb upgrade``, ``wb preview add`` and ``wb add``: show, and after
the owner types the digest do, an upgrade of an existing project or the addition of modules it
does not have.

``prepare`` is the whole read-only pipeline from a held target to a plan, in the order the spec
gives, and refuses with a reason at the first step that fails: the project is read
(``installed``), must be one this machine knows, must be as last acknowledged, its packages are
found in the cache or given with ``--package`` (nothing is fetched), every module the manifest
records is verified and gated, and only then is the plan built. The project is checked against
its baselines a second time with the files the plan would write into. The write command calls
the same function.

``add`` is the same pipeline with the modules named by ``--select`` added to those the project
records. Each must be new; the installed ones are verified and gated with them, and any change to
an installed file or block is refused (``upgrade`` makes it), so ``add`` writes only new files,
new blocks and the manifest. ``preview upgrade`` writes nothing. ``upgrade`` is owner-run and terminal-only like ``install``:
it prints the plan with its digest, reads the typed first twelve characters, rebuilds the plan
from the packages as they are now and refuses if its digest differs, then writes in this order:
the marker ``.workbench/local/incomplete``, the directories, the created files, the files
replaced (each by a whole-file replace that checks the hash in the plan), the manifest, the
store's baselines, and last removes the marker. Writing is not atomic: a failure stops at once,
lists what was written and what was not, leaves the marker and exits 3. Nothing is committed and
nothing is deleted. Nothing contacts the network.
"""

import collections
import os
import shutil
import stat

from . import (__version__, acknowledgement, approve, base, confirm, declarations, display,
               firstparty, gate, installed, installplan, manifest, preview, projectfs, safefs,
               snapshot, sources, target, upgradeplan, verify)

ENDING = preview.ENDING
LISTED = 40
RECOVERY = ("a file already replaced no longer matches the manifest, so a second run would call "
            "it edited, and there is no automatic repair: put the files listed as written back "
            "from version control or a copy, remove the marker yourself, and run the command "
            "again")
RECOVERY_FILES_DONE = ("the project's files and manifest are complete; only the store entry or "
                       "the marker is left: remove the marker yourself, then run "
                       "`wb acknowledge` and review what it lists")
MAX_PACKAGE_JSON = 1 << 20


def _refuse_differences(found):
    lines = ["the project differs from what was last acknowledged (%d paths):" % len(found)]
    for item in found[:LISTED]:
        why = (" (%s)" % item.reason) if item.reason else ""
        lines.append("  %s %s%s" % (item.kind, display.ascii_text(item.path)[:120], why))
    if len(found) > LISTED:
        lines.append("  and %d more" % (len(found) - LISTED))
    lines.append("  review them and run `wb acknowledge` yourself, then try again")
    raise preview.Refused(lines)


def _package_json(path):
    """The parsed package.json of the package at `path`, read without following a link and only
    if it is a regular file, so a FIFO or a link planted by a caller-chosen directory is refused
    and never opened for a long read."""
    shown = display.ascii_text(path)[:120]
    try:
        fd = os.open(os.path.join(path, "package.json"),
                     os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise preview.Refused(["a given package has no readable package.json: %s" % shown])
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise preview.Refused(["a given package's package.json is not a regular file: %s"
                                   % shown])
        data = b""
        while len(data) <= MAX_PACKAGE_JSON:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            data += chunk
    except OSError:
        raise preview.Refused(["a given package has no readable package.json: %s" % shown])
    finally:
        os.close(fd)
    try:
        if len(data) > MAX_PACKAGE_JSON:
            raise ValueError("too large")
        document = declarations.parse_json(data)
        name, modules = document.get("name"), document.get("modules")
    except (ValueError, AttributeError):
        raise preview.Refused(["a given package has no readable package.json: %s" % shown])
    if not isinstance(name, str) or not isinstance(modules, list):
        raise preview.Refused(["a given package's package.json has no name or module list: %s"
                               % shown])
    return name, [m for m in modules if isinstance(m, str)]


def _resolve(guarded, document, given, adding=False):
    """One ``Resolved`` per package the manifest records: the one given for it, else the cached
    copy of its recorded source and ref. When adding, a given package the project does not
    record is a new one."""
    recorded = {p["name"]: p for p in document["packages"]}
    chosen = {}
    try:
        for source, ref in given:
            resolved = sources.resolve_cached(guarded, source, ref)
            name, _ = _package_json(resolved.path)
            if name not in recorded and not adding:
                raise preview.Refused(["the package %s is not one this project records; adding "
                                       "a module is `wb add`" % display.ascii_text(name)[:80]])
            if name in chosen:
                raise preview.Refused(["the package %s was given twice"
                                       % display.ascii_text(name)[:80]])
            chosen[name] = resolved
        for name, record in recorded.items():
            if name in chosen:
                continue
            if record["source"].startswith("local:"):
                raise preview.Refused(["the package %s was installed from a local directory; "
                                       "give it with --package <directory>"
                                       % display.ascii_text(name)[:80]])
            chosen[name] = sources.resolve_cached(guarded, record["source"],
                                                  record["ref"] or None)
    except sources.SourceError as exc:
        raise preview.Refused([str(exc)])
    return [(name, chosen[name]) for name in sorted(chosen)]


def _already_installed(tokens, recorded):
    """Refuse a selected module the project already has: it changes only with `upgrade`."""
    for token in tokens:
        if "/" in token:
            have = tuple(token.split("/", 1)) in recorded
        else:
            have = any(name == token for _, name in recorded)
        if have:
            raise preview.Refused(["%s is already installed; an installed module changes only "
                                   "with `wb upgrade` (name another package's module of the "
                                   "same name as <package>/<module>)"
                                   % display.ascii_text(token)[:80]])


def _same_provenance(packages, recorded):
    """A package the project already records keeps its source, ref and commit through an add;
    moving it to another origin or commit is an upgrade."""
    old = {p["name"]: p for p in recorded}
    for package in packages:
        was = old.get(package.name)
        if was is not None and (package.source, package.ref, package.commit) != (
                was["source"], was["ref"], was["commit"]):
            raise preview.Refused([
                "add never changes where an installed package comes from: %s is recorded from %s "
                "and was given from %s; use upgrade" % (
                    display.ascii_text(package.name)[:80],
                    display.ascii_text(was["source"])[:120],
                    display.ascii_text(package.source)[:120])])


def _installed_unchanged(changes, recorded):
    """An add does not move an installed module to another version, whatever happens to its
    files: that is `upgrade`."""
    for item in changes:
        if (item["package"], item["name"]) in recorded and item["change"]["kind"] == "changed":
            raise preview.Refused(["add never changes an installed module: %s/%s differs from "
                                   "what is installed; use upgrade"
                                   % (display.ascii_text(item["package"])[:80],
                                      display.ascii_text(item["name"])[:80])])


def prepare(guarded, held, given, distribution, version, which=shutil.which, mode="upgrade",
            add=()):
    """Read, check, verify, gate and plan. Returns a dict with ``plan``, ``existing``,
    ``selection``, ``approvals``, ``warnings`` and ``writer``; raises ``preview.Refused``."""
    if held.state != "existing":
        raise preview.Refused(["the target is not an existing project; use install"])
    distribution = distribution or firstparty.default_distribution()
    writer = projectfs.Writer(held)
    try:
        existing = installed.read(writer, version)
        project = manifest.project_id(existing.document["seed"])
        baselines = acknowledgement.read_baselines(guarded, project)
        acknowledgement.check_known(baselines, acknowledgement.read_seen(guarded, project),
                                    held.path)
        found = acknowledgement.differences(writer, baselines)
    except (installed.InstalledError, acknowledgement.AcknowledgementError,
            manifest.ManifestError) as exc:
        raise preview.Refused([str(exc)])
    if found:
        _refuse_differences(found)

    resolved = _resolve(guarded, existing.document, given, adding=mode == "add")
    # A recorded module its package no longer declares is not selected: its entries are left in
    # place and reported, and nothing of it is deleted.
    declared = {name: _package_json(item.path)[1] for name, item in resolved}
    select = ["%s/%s" % (p["name"], m["name"]) for p in existing.document["packages"]
              for m in p["modules"] if m["name"] in declared[p["name"]]]
    recorded = {(p["name"], m["name"]) for p in existing.document["packages"]
                for m in p["modules"]}
    if mode == "add":
        _already_installed(add, recorded)
        select += list(add)
    elif not select:
        raise preview.Refused(["none of the modules the project records is in its packages"])
    paths = [item.path for _, item in resolved]
    result = verify.verify_packages(
        paths, select, harness_required=False,
        first_party=[p for p in paths if firstparty.is_first_party(p, distribution)],
        which=which)
    if not result.accepted:
        raise preview.Refused([str(problem) for problem in result.problems])
    if [info.name for info in result.packages] != [name for name, _ in resolved]:
        raise preview.Refused(["the packages changed while they were read; nothing was done"])
    # A package's own harness comes with it and is not written; naming one to add is an error.
    named = {name for m in result.modules if m.type == "harness"
             for name in (m.name, "%s/%s" % (m.package, m.name))}
    if mode == "add" and named & set(add):
        raise preview.Refused(["a harness is attached, not added; attach is not built yet"])
    if mode == "add" and not [key for key in result.order if key not in recorded]:
        raise preview.Refused(["none of the selected modules is new to the project"])
    decision = gate.check_selection(guarded, result, distribution)
    if not decision.approved:
        raise preview.Refused(["%s/%s is not approved on this machine: %s" % (
            item.package, item.name, item.reason)
            for item in decision.modules if not item.approved] or [decision.reason])
    roots = dict(zip((info.name for info in result.packages), paths))
    origins = dict(zip((info.name for info in result.packages), (r for _, r in resolved)))
    by_key = {(m.package, m.name): m for m in result.modules}
    modules = tuple(by_key[key] for key in result.order)
    try:
        snaps = {(m.package, m.name): snapshot.take(os.path.join(roots[m.package], m.name), m)
                 for m in modules}
        loaded_base = base.load_base(distribution)
    except safefs.SafeFsError as exc:
        raise preview.Refused([str(exc)])
    used = {m.package for m in modules}
    packages = tuple(installplan.PackageSource(
        info.name, preview._recorded_source(origins[info.name], info.name),
        origins[info.name].ref, origins[info.name].commit, info.tree_hash)
        for info in result.packages if info.name in used)
    selection = installplan.Selection(modules, packages)
    if mode == "add":
        _same_provenance(packages, existing.document["packages"])
        _installed_unchanged(upgradeplan._changes(existing, selection), recorded)
    try:
        plan = upgradeplan.build(existing, writer, baselines, selection, snaps, loaded_base,
                                 version, mode)
        found = acknowledgement.differences(writer, baselines,
                                            writes=upgradeplan.written_paths(plan))
    except (upgradeplan.UpgradeError, acknowledgement.AcknowledgementError,
            manifest.ManifestError) as exc:
        raise preview.Refused([str(exc)])
    if found:
        _refuse_differences(found)
    # The bytes the plan was built from must be the acknowledged ones: the check above read the
    # files again, so a file changed between the two reads is caught here by its hash.
    for write in plan.writes:
        if write.op == "replace" and write.expected != baselines.get(write.path):
            raise preview.Refused([
                "%s is not as last acknowledged; review it and run `wb acknowledge` yourself"
                % display.ascii_text(write.path)[:120]])
    approvals = {(item.package, item.name): (item.via, item.source) for item in decision.modules}
    return {"plan": plan, "existing": existing, "selection": selection, "approvals": approvals,
            "warnings": list(result.warnings), "writer": writer}


def run_preview(guarded, parsed, out, err, distribution=None, version=None,
                which=shutil.which, mode="upgrade"):
    """Print the preview and return 0, or print ``refused:`` lines and return 1."""
    try:
        with target.open_target(parsed.target, guarded.root) as held:
            done = prepare(guarded, held, parsed.packages, distribution,
                           version or __version__, which, mode, parsed.select or ())
            text = upgradeplan.render(done["plan"], done["existing"], done["selection"],
                                      held.path, held.identity, approvals=done["approvals"])
    except target.TargetError as exc:
        err.write("refused: %s\n" % display.clean(str(exc)).replace("refused: ", "", 1))
        return 1
    except preview.Refused as exc:
        for index, line in enumerate(exc.lines):
            err.write(("refused: %s\n" if not line.startswith("  ") or not index else "%s\n")
                      % display.clean(line))
        return 1
    except safefs.SafeFsError as exc:
        err.write("refused: %s\n" % display.clean(str(exc)))
        return 1
    for warning in done["warnings"]:
        err.write("warning: %s\n" % display.clean(warning))
    out.write(text)
    if not done["plan"].writes:
        out.write("nothing to change\n")
    out.write(ENDING + "\n")
    return 0


# --- the write ------------------------------------------------------------------------------

_Action = collections.namedtuple("_Action", "kind path")
_Shown = collections.namedtuple("_Shown", "actions store_writes")


def _shown(plan):
    """The plan as the failure report reads it: what was to be created or replaced."""
    actions = [_Action("create-dir", path) for path in plan.dirs]
    actions += [_Action("create-file", w.path) for w in plan.writes]
    return _Shown(actions, upgradeplan.store_writes(plan))


def _ordered(plan):
    """The file writes in the order they are made: created files, then replaced files, and the
    manifest, which records them, last."""
    manifest_path = upgradeplan.MANIFEST
    creates = [w for w in plan.writes if w.op == "create"]
    replaces = [w for w in plan.writes if w.op == "replace" and w.path != manifest_path]
    last = [w for w in plan.writes if w.path == manifest_path]
    return creates + replaces + last


class NotStarted(Exception):
    """The marker could not be made, so nothing of the upgrade was written."""


def _write(guarded, held, plan, progress):
    writer = progress.writer = projectfs.Writer(held)
    try:
        writer.create_file(projectfs.MARKER, b"")
    except safefs.SafeFsError as exc:
        if projectfs.MARKER in writer.written:
            raise
        raise NotStarted("the marker %s cannot be made (%s); no file of the project was written"
                         % (projectfs.MARKER, exc))
    progress.started = True
    progress.stage = "files"
    for path in plan.dirs:
        writer.create_dir(path)
    for write in _ordered(plan):
        if write.op == "create":
            writer.create_file(write.path, write.data, executable=write.executable)
        else:
            writer.replace_file(write.path, write.expected, write.data,
                                executable=write.executable)
    progress.stage = "store"
    for path, data in upgradeplan.store_writes(plan):
        guarded.write(path, data)
        progress.stored.append(path)
    # What is on disk must be what was shown: a file or a directory moved away after the check
    # would otherwise be reported as written.
    for write in plan.writes:
        state = writer.read_file(write.path)
        if state is None or state.hash != write.hash:
            raise safefs.SafeFsError("%s is not what was written" % display.ascii_text(
                write.path)[:120])
    progress.stage = "marker"
    try:
        writer.remove_marker()
    except projectfs.MarkerMissing:
        progress.warnings.append("the marker %s was already gone" % projectfs.MARKER)


def _finish(plan, progress, held, out, err):
    for warning in progress.warnings:
        err.write("warning: %s\n" % display.clean(warning))
    # The marker and the `.workbench/local/` made for it are the command's own bookkeeping.
    done = [path for path in progress.writer.written
            if path not in (projectfs.MARKER, projectfs.MARKER.rsplit("/", 1)[0] + "/")]
    try:
        out.write("wrote %d paths in %s\n" % (len(done), display.ascii_text(held.path)))
        notes = [r for r in plan.rows if r.kind == upgradeplan.CONFLICT
                 or (r.kind == upgradeplan.SKIP and r.detail)]
        if notes:
            out.write("left as they are:\n")
            for row in notes[:LISTED]:
                out.write("  %s %s%s (%s)\n" % (
                    row.kind, display.ascii_text(row.path)[:120],
                    (" block %s slot %s" % (display.ascii_text(row.block),
                                            display.ascii_text(row.slot))) if row.block else "",
                    display.ascii_text(row.detail)[:160]))
            if len(notes) > LISTED:
                out.write("  and %d more\n" % (len(notes) - LISTED))
        out.write("nothing was committed; committing the result as one change makes it "
                  "revertable\n")
        out.flush()
    except BrokenPipeError:
        pass


def _refuse(err, text):
    err.write("refused: %s\n" % display.clean(text))
    return 1


def _lines(err, exc):
    for index, line in enumerate(exc.lines):
        err.write(("refused: %s\n" if not line.startswith("  ") or not index else "%s\n")
                  % display.clean(line))


def _run(guarded, parsed, stdin, out, err, distribution, version, which, progress, mode):
    try:
        with target.open_target(parsed.target, guarded.root) as held:
            done = prepare(guarded, held, parsed.packages, distribution, version, which, mode,
                           parsed.select or ())
            plan, existing, selection = done["plan"], done["existing"], done["selection"]
            for warning in done["warnings"]:
                err.write("warning: %s\n" % display.clean(warning))
            out.write(upgradeplan.render(plan, existing, selection, held.path, held.identity,
                                         show_digest=True, approvals=done["approvals"]))
            if not plan.writes:
                out.write("nothing to change\n")
                return 0
            digest = upgradeplan.digest(plan, existing, selection, held.identity)
            out.write("\nTo %s, type the first %d characters of the digest shown above and "
                      "press Enter.\nAnything else cancels and writes nothing.\n> "
                      % (mode, confirm.CONFIRM_CHARS))
            out.flush()
            if not confirm.typed_matches(stdin, digest):
                out.write("cancelled: nothing was written\n")
                return 1
            held.recheck()
            try:
                again = prepare(guarded, held, parsed.packages, distribution, version, which,
                                mode, parsed.select or ())
            except preview.Refused as exc:
                raise preview.Refused(["the project or its packages changed while the plan was "
                                       "shown: %s; nothing was written" % "; ".join(exc.lines)])
            if upgradeplan.digest(again["plan"], again["existing"], again["selection"],
                                  held.identity) != digest:
                return _refuse(err, "the plan changed while it was shown; nothing was written")
            progress.plan = _shown(plan)
            try:
                _write(guarded, held, plan, progress)
            except NotStarted as exc:
                return _refuse(err, str(exc))
            except (Exception, KeyboardInterrupt) as exc:
                cause = "interrupted" if isinstance(exc, KeyboardInterrupt) else str(exc)
                if progress.writer is None:
                    raise
                confirm.report_failure(
                    progress, cause, err, what=mode,
                    hint=RECOVERY_FILES_DONE if progress.stage in ("store", "marker")
                    else RECOVERY)
                return 3
            progress.done = True
            try:
                _finish(plan, progress, held, out, err)
            except OSError:
                pass
            return 0
    except target.TargetError as exc:
        return _refuse(err, display.clean(str(exc)).replace("refused: ", "", 1))
    except preview.Refused as exc:
        _lines(err, exc)
        return 1
    except safefs.SafeFsError as exc:
        return _refuse(err, str(exc))


def require_terminal(stdin, out, err, mode="upgrade"):
    """True when both streams are terminals; otherwise print the refusal and return False."""
    if approve.is_terminal(stdin) and approve.is_terminal(out):
        return True
    _refuse(err, "%s is owner-run: standard input and output must both be terminals. Run "
                 "this command yourself, from your own terminal; `preview %s` shows the "
                 "same plan without writing." % (mode, mode))
    return False


def run(guarded, parsed, stdin, out, err, distribution=None, version=None, which=shutil.which,
        mode="upgrade"):
    """Upgrade or add after the owner types the digest. Returns the exit code: 0 done or nothing to
    change, 1 refused or cancelled, 3 stopped after writing began, 130 interrupted before it."""
    if not require_terminal(stdin, out, err, mode):
        return 1
    progress = confirm.Progress()
    progress.warnings = []
    progress.stage = "files"
    progress.done = False
    try:
        return _run(guarded, parsed, stdin, out, err, distribution, version or __version__,
                    which, progress, mode)
    except KeyboardInterrupt:
        if progress.done:
            return 0
        if progress.started:
            try:
                err.write("\ninterrupted after writing began: the project may be partly "
                          "written; check %s\n" % projectfs.MARKER)
            except OSError:
                pass
            return 3
        try:
            out.write("\ncancelled: nothing was written\n")
        except OSError:
            pass
        return 130
    except BrokenPipeError:
        return 3 if progress.started else 1

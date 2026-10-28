"""``wb attach``: write this clone's harness files, its exclude lines and its local manifest.

Attach is for an existing project. It reads the committed manifest and the packages the manifest
records, takes the harness module from ``--harness <package>/<module>``, and writes only per-clone
files, none of which git tracks (``repository-boundary.md``). The order, all of it before the
first write unless noted:

* the target is an existing project, and this clone records no harness yet (a changed harness
  means a new clone);
* the project is as last acknowledged on this machine, as for ``upgrade``;
* the packages the manifest records come from the cache or ``--package``, and the harness package
  from there too. Nothing is fetched: a source the owner has not approved is never contacted;
* every package and module the manifest records equals the lock (tree and declaration hashes), the
  selection is verified as one install, and every module of it, the harness included, is approved
  on this machine. The bytes used are those of a snapshot proved equal to the approved tree;
* the neutral items, the overrides and the exclusions of every module are translated by the
  harness layout (``harnessplan``); the root file and the permission rules are rendered;
* each path to be written is looked at without following a link: absent is created, holding
  exactly the planned bytes is left as it is and reported, anything else is a conflict, and the
  conflicts are reported together with nothing written. The exclude file is checked the same way.

Writing then adds the exclude lines (before any file, so a failure never leaves a file git would
pick up), creates the files and writes the local manifest last, so a
clone that stopped part-way has none and can run attach again; the files already written are then
left as they are. Attach is not terminal-gated and has no digest prompt: it does not change
the project's committed content, and the barrier against an agent running it is the deny rule a
harness renders for it. It runs no git and contacts no network.
"""

import collections
import os
import shutil

from . import (__version__, acknowledgement, declarations, firstparty, gate, harnessstage, installed,
               localmanifest, manifest, preview, projectfs, refusal, rendering, snapshot, sources, target, upgrade,
               verify)
from .wbkit import display, safefs

LISTED = 40
MAX_WRITE_BYTES = harnessstage.MAX_WRITE_BYTES
inputs = harnessstage.inputs
_check_paths = harnessstage.check_paths
Refused = refusal.Refused

Command = collections.namedtuple("Command", "target harness packages")
# `create` and `kept` are lists of ``harnessplan.Planned``; `exclude` the layout's entries;
# `document` the local manifest to write; `reports` the translation's; `warnings` and `notes` text.
# `rendering` is the record of what the levels table rendered and `project_id` the project it belongs to; attach
# writes it to the guarded store before the files (``rendering.py``).
Prepared = collections.namedtuple(
    "Prepared", "path harness version create kept exclude document reports warnings notes "
                "settings rendering project_id", defaults=(None, None))


def parse(tokens, harness_required=True):
    """A ``Command`` from ``[<target> | --dir <path>] --harness <package>/<module> [--package
    <source> [--ref <ref>]] ...``; a ``sources.UsageError`` otherwise. With `harness_required` false there is no
    ``--harness`` (``wb preview rerender`` takes the harness the clone records) and the command's harness is None."""
    positional = dir_option = harness = None
    packages = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "":
            raise sources.UsageError("an argument may not be empty")
        if token == "--harness" and harness_required:
            if harness is not None:
                raise sources.UsageError("--harness was given twice")
            harness = sources._value(tokens, index, token)
            index += 2
        elif token == "--package":
            packages.append([sources._value(tokens, index, token), None])
            index += 2
        elif token == "--ref":
            if not packages:
                raise sources.UsageError("--ref needs a --package before it")
            if packages[-1][1] is not None:
                raise sources.UsageError("--ref was given twice for one --package")
            packages[-1][1] = sources._value(tokens, index, token)
            index += 2
        elif token == "--dir":
            if dir_option is not None:
                raise sources.UsageError("--dir was given twice")
            dir_option = sources._value(tokens, index, token)
            index += 2
        elif token.startswith("-"):
            raise sources.UsageError("unknown option %s" % token)
        else:
            if positional is not None:
                raise sources.UsageError("more than one target was given")
            positional = token
            index += 1
    named = None
    if harness_required:
        if harness is None:
            raise sources.UsageError("--harness <package>/<module> is required")
        package, slash, module = harness.partition("/")
        if not slash or not all(declarations.NAME_RE.match(part)
                                and len(part) <= declarations.MAX_NAME_CHARS
                                for part in (package, module)):
            raise sources.UsageError("--harness takes <package>/<module>, two names joined by one /")
        named = (package, module)
    try:
        spelling = target.choose(positional, dir_option)
    except target.TargetUsage as exc:
        raise sources.UsageError(str(exc))
    return Command(spelling, named, [tuple(item) for item in packages])


def default_home():
    """The home directory the rendered rules name: the account database's, not ``$HOME``."""
    return harnessstage.default_home()


# --- the plan ----------------------------------------------------------------------------------


def _check_lock(document, result):
    """Every package and module the manifest records equals what was verified."""
    infos = {info.name: info for info in result.packages}
    verified = {(m.package, m.name): m for m in result.modules}
    lines = []
    for package in document["packages"]:
        info = infos.get(package["name"])
        if info is None or info.tree_hash != package["tree"]:
            lines.append("the package %s is not the one the lock records (its content hash "
                         "differs from .workbench/manifest.json)" % display.ascii_text(package["name"])[:80])
            continue
        for module in package["modules"]:
            got = verified.get((package["name"], module["name"]))
            if got is None or (got.declaration_hash, got.tree_hash) != (module["declaration"],
                                                                        module["tree"]):
                lines.append("the module %s/%s is not the one the lock records"
                             % (display.ascii_text(package["name"])[:80],
                                display.ascii_text(module["name"])[:80]))
    if lines:
        lines.append("give the recorded version with --package, or bring the project to the new "
                     "one with `wb upgrade` first")
        raise Refused(lines)


def _settings_entries(settings):
    return ["the entries attach would have written to it:"] + [
        "  " + line for line in settings.data.decode("utf-8").splitlines()] + [
        "attach never edits a settings file it did not write; move yours aside, run `wb attach`,"
        " and put your own entries back"]


def preflight(writer, files, exclude, settings_path):
    """``(create, kept)`` for `files`, or a ``Refused`` naming every conflict. Nothing is written."""
    create, kept, conflicts, hand = [], [], [], []
    for planned in files:
        try:
            state = writer.read_file(planned.path)
        except safefs.SafeFsError as exc:
            conflicts.append("%s: %s" % (display.ascii_text(planned.path)[:120], exc))
            continue
        if state is None:
            create.append(planned)
        elif state.hash == planned.sha256:
            kept.append(planned)
        else:
            conflicts.append("%s: it exists with other content, and attach does not overwrite a "
                             "file it did not write" % display.ascii_text(planned.path)[:120])
            if planned.path == settings_path:
                hand = planned
    try:
        writer.check_exclude(exclude)
    except safefs.SafeFsError as exc:
        conflicts.append(".git/info/exclude: %s" % exc)
    if conflicts:
        shown = conflicts[:LISTED]
        if len(conflicts) > LISTED:
            shown.append("and %d more" % (len(conflicts) - LISTED))
        raise Refused(shown, _settings_entries(hand) if hand else ())
    return create, kept


# `staged` is a ``harnessstage.Staged``; `inputs` is what the staging read, as a tuple of tuples, so that a plan can say
# it was made from the same packages (``rerender.py``).
Staging = collections.namedtuple("Staging", "staged project warnings inputs")


def stage(guarded, held, writer, packages, harness, distribution=None, version=None, which=shutil.which,
          home=None):
    """Read, check, verify, gate and translate for the harness `harness`, ``(package, module)``, or ``(None, module)``
    to find the one package of the project that declares the module. Returns a ``Staging``; raises ``Refused``.
    Nothing is written. It does not look at the harness files in the project; that is for the caller."""
    distribution = distribution or firstparty.default_distribution()
    version = version or __version__
    warnings = []
    try:
        existing = installed.read(writer, version)
        project = manifest.project_id(existing.document["seed"])
        baselines = acknowledgement.read_baselines(guarded, project)
        acknowledgement.check_known(baselines, acknowledgement.read_seen(guarded, project),
                                    held.path)
        found = acknowledgement.differences(writer, baselines)
        if installed.version_key(existing.document["workbench"]) != installed.version_key(version):
            warnings.append("the project was written by workbench %s and this is %s"
                            % (display.ascii_text(existing.document["workbench"])[:40],
                               display.ascii_text(version)[:40]))
    except (installed.InstalledError, acknowledgement.AcknowledgementError,
            manifest.ManifestError) as exc:
        raise Refused([str(exc)])
    if found:
        upgrade._refuse_differences(found)

    package_name, module_name = harness
    resolved = upgrade._resolve(guarded, existing.document, packages, adding=True)
    names = [name for name, _ in resolved]
    if package_name is not None and package_name not in names:
        raise Refused(["the harness package %s is not one this project records; give it with "
                       "--package <source>" % display.ascii_text(package_name)[:80]])
    declared = {name: upgrade._package_json(item.path)[1] for name, item in resolved}
    if package_name is None:
        owners = [name for name in names if module_name in declared[name]]
        if len(owners) != 1:
            raise Refused(["the harness module %s is declared by %s package of this project; give the package that "
                           "declares it with --package <source>"
                           % (display.ascii_text(module_name)[:80], "no" if not owners else "more than one")])
        package_name = owners[0]
    token = "%s/%s" % (package_name, module_name)
    if module_name not in declared[package_name]:
        raise Refused(["the package %s declares no module %s"
                       % (display.ascii_text(package_name)[:80], display.ascii_text(module_name)[:80])])
    select = ["%s/%s" % (p["name"], m["name"]) for p in existing.document["packages"]
              for m in p["modules"] if m["name"] in declared[p["name"]]]
    if token in select:
        raise Refused(["%s is recorded as an installed module, not as a harness" % token])
    paths = [item.path for _, item in resolved]
    result = verify.verify_packages(
        paths, select + [token], harness_required=True,
        first_party=[p for p in paths if firstparty.is_first_party(p, distribution)], which=which)
    if not result.accepted:
        raise Refused([str(problem) for problem in result.problems])
    if [info.name for info in result.packages] != names:
        raise Refused(["the packages changed while they were read; nothing was done"])
    by_key = {(m.package, m.name): m for m in result.modules}
    if [key for key in result.order if by_key[key].type == "harness"] != [
            (package_name, module_name)]:
        raise Refused(["%s is not a harness module" % token])
    _check_lock(existing.document, result)
    decision = gate.check_selection(guarded, result, distribution)
    if not decision.approved:
        raise Refused(["%s/%s is not approved on this machine: %s" % (
            item.package, item.name, item.reason)
            for item in decision.modules if not item.approved] or [decision.reason])
    roots = dict(zip((info.name for info in result.packages), paths))
    modules = tuple(by_key[key] for key in result.order)
    try:
        snaps = {(m.package, m.name): snapshot.take(os.path.join(roots[m.package], m.name), m)
                 for m in modules}
    except safefs.SafeFsError as exc:
        raise Refused([str(exc)])

    chosen = by_key[(package_name, module_name)]
    where = home if home is not None else default_home()
    origin = dict(resolved)[package_name]
    staged = harnessstage.stage(guarded.root, chosen, modules, snaps,
                                preview._recorded_source(origin, package_name), version, where, held.path)
    warnings.extend(staged.warnings)
    inputs = (tuple(sorted(("package", info.name, info.tree_hash) for info in result.packages))
              + tuple(sorted(("module", m.package, m.name, m.declaration_hash, m.tree_hash) for m in result.modules))
              + (("harness", token, chosen.version),))
    return Staging(staged, project, warnings, inputs)


def prepare(guarded, held, command, distribution=None, version=None, which=shutil.which,
            home=None):
    """Read, check, verify, gate, translate and look at the paths. Returns a ``Prepared``;
    raises ``Refused``. Nothing is written."""
    if held.state != "existing":
        raise Refused(["the target is not an existing project; use install"])
    writer = projectfs.Writer(held)
    try:
        recorded = localmanifest.read(writer)
    except localmanifest.LocalManifestError as exc:
        raise Refused(["the local manifest cannot be used: %s" % exc])
    if recorded is not None:
        raise Refused(["this clone already records the harness %s; a clone has one harness, so "
                       "use a new clone to change it" % display.ascii_text(recorded["harness"])[:80]])
    done = stage(guarded, held, writer, command.packages, command.harness, distribution, version, which, home)
    staged = done.staged
    create, kept = preflight(writer, staged.files, staged.exclude, staged.settings)
    return Prepared(held.path, staged.token, staged.version, create, kept, staged.exclude,
                    staged.document, staged.reports, done.warnings, staged.notes, staged.settings,
                    staged.rendering, done.project)


# --- the write ---------------------------------------------------------------------------------


def record_rendering(guarded, prepared):
    """Write the rendering record to the guarded store. It comes before the files: if a file is then not written, the
    record names a hash the file does not have and ``ask`` and ``none`` read as ``block``."""
    if prepared.rendering is not None and prepared.project_id is not None:
        rendering.write(guarded, prepared.project_id, rendering.with_shared_hash(prepared.rendering, prepared.path))


def apply(writer, prepared):
    """Write what `prepared` plans through `writer`; return the exclude lines added. Files that
    already hold the planned bytes are not touched. Raises on the first failure and leaves what
    was written, which `writer.written` lists."""
    writer.target.recheck()
    # The ignore lines come first: a failure after them leaves no file that git would pick up.
    added = writer.add_exclude(prepared.exclude)
    for planned in prepared.create:
        writer.create_file(planned.path, planned.data)
    localmanifest.write(writer, prepared.document)
    return added


# --- the report --------------------------------------------------------------------------------


def _listed(out, title, items):
    if not items:
        return
    out.write("%s:\n" % title)
    for item in items[:LISTED]:
        out.write("  %s\n" % display.ascii_text(item))
    if len(items) > LISTED:
        out.write("  and %d more\n" % (len(items) - LISTED))


def _finish(prepared, writer, added, out, err):
    try:
        out.write("attached %s %s in %s\n" % (display.ascii_text(prepared.harness)[:140],
                                              display.ascii_text(prepared.version)[:40],
                                              display.ascii_text(prepared.path)))
        _listed(out, "wrote %d files" % len(prepared.create), [p.path for p in prepared.create])
        _listed(out, "left %d files as they were (they hold the planned bytes)"
                % len(prepared.kept), [p.path for p in prepared.kept])
        if added:
            out.write("added %d lines to .git/info/exclude: %s\n"
                      % (len(added), ", ".join(display.ascii_text(a) for a in added)))
        out.write("recorded %s\nnothing was committed\n" % localmanifest.PATH)
        for report in prepared.reports:
            text = "%s: %s" % (display.ascii_text(report.item), display.clean(report.message))
            if report.level in ("warning", "skipped"):
                err.write("warning: %s: %s\n" % (report.level, text))
            else:
                out.write("%s: %s\n" % (report.level, text))
        if prepared.settings:
            err.write("warning: %s changes what the agent may do here: it denies the owner-run "
                      "commands and writes to the guarded store, and asks before the hard stops\n"
                      % display.ascii_text(prepared.settings))
        for note in prepared.notes:
            out.write("note: %s\n" % display.clean(note))
        out.flush()
    except BrokenPipeError:
        pass


AGAIN = ("run `wb attach` again with the same arguments: a file that holds the planned bytes "
         "is left as it is, and the local manifest is written last\n")


def _failed(cause, prepared, written, err, again=AGAIN,
            complete="the project itself is complete"):
    """Report a stop after writing began. `written` are the paths this attach wrote."""
    have = set(written)
    planned = [p.path for p in prepared.create] + [localmanifest.PATH]
    err.write("failed: %s\n" % display.ascii_text(cause))
    _listed(err, "written", list(written))
    _listed(err, "not written", [path for path in planned if path not in have])
    err.write("%s; only this clone's harness files are part-written\n"
              "if the failure came while a file was being written, that file may be incomplete: "
              "remove it yourself first, since attach does not overwrite a file with other bytes\n"
              % complete)
    err.write(again)


def _refusal(exc, err):
    for line in exc.lines:
        err.write("refused: %s\n" % display.clean(line))
    for line in getattr(exc, "after", ()):
        err.write("  %s\n" % display.clean(line))
    return 1


def run(guarded, command, out, err, distribution=None, version=None, which=shutil.which,
        home=None):
    """Attach and print the result. Returns the exit code: 0 done, 1 refused, 3 stopped after
    writing, 130 interrupted before writing."""
    writer = None
    prepared = None
    try:
        with target.open_target(command.target, guarded.root) as held:
            prepared = prepare(guarded, held, command, distribution, version, which, home)
            for warning in prepared.warnings:
                err.write("warning: %s\n" % display.clean(warning))
            try:
                writer = projectfs.Writer(held)
                record_rendering(guarded, prepared)
                added = apply(writer, prepared)
            except (Exception, KeyboardInterrupt) as exc:
                cause = "interrupted" if isinstance(exc, KeyboardInterrupt) else str(exc)
                _failed(cause, prepared, list(writer.written) if writer is not None else [], err)
                return 3
            try:
                _finish(prepared, writer, added, out, err)
            except KeyboardInterrupt:
                pass
            return 0
    except target.TargetError as exc:
        return target.write_refusal(err, exc)
    except preview.Refused as exc:
        return _refusal(exc, err)
    except safefs.SafeFsError as exc:
        err.write("refused: %s\n" % display.clean(str(exc)))
        return 1
    except KeyboardInterrupt:
        out.write("\ncancelled: nothing was written\n")
        return 130

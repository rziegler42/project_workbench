"""``wb preview upgrade``: show exactly what an upgrade of an existing project would do.

``prepare`` is the whole read-only pipeline from a held target to a plan, in the order the spec
gives, and refuses with a reason at the first step that fails: the project is read
(``installed``), must be one this machine knows, must be as last acknowledged, its packages are
found in the cache or given with ``--package`` (nothing is fetched), every module the manifest
records is verified and gated, and only then is the plan built. The project is checked against
its baselines a second time with the files the plan would write into. The write command calls
the same function.

Nothing here writes the project or the store, and nothing contacts the network.
"""

import os
import shutil
import stat

from . import (__version__, acknowledgement, base, declarations, display, firstparty, gate,
               installed, installplan, manifest, preview, projectfs, safefs, snapshot, sources,
               target, upgradeplan, verify)

ENDING = preview.ENDING
LISTED = 40
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


def _resolve(guarded, document, given):
    """One ``Resolved`` per package the manifest records: the one given for it, else the cached
    copy of its recorded source and ref."""
    recorded = {p["name"]: p for p in document["packages"]}
    chosen = {}
    try:
        for source, ref in given:
            resolved = sources.resolve_cached(guarded, source, ref)
            name, _ = _package_json(resolved.path)
            if name not in recorded:
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


def prepare(guarded, held, given, distribution, version, which=shutil.which, mode="upgrade"):
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

    resolved = _resolve(guarded, existing.document, given)
    # A recorded module its package no longer declares is not selected: its entries are left in
    # place and reported, and nothing of it is deleted.
    declared = {name: _package_json(item.path)[1] for name, item in resolved}
    select = ["%s/%s" % (p["name"], m["name"]) for p in existing.document["packages"]
              for m in p["modules"] if m["name"] in declared[p["name"]]]
    if not select:
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
                which=shutil.which):
    """Print the preview and return 0, or print ``refused:`` lines and return 1."""
    try:
        with target.open_target(parsed.target, guarded.root) as held:
            done = prepare(guarded, held, parsed.packages, distribution,
                           version or __version__, which)
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

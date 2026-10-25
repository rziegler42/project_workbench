"""``wb preview install``: show exactly what an install would do, and write nothing.

The preview contacts no network and writes nothing, not even a cache directory: it reads only
a local package directory or a download that ``approve`` already cached, so an agent cannot
make the workbench contact an address it chose. ``prepare`` is the whole pipeline from a
target and resolved packages to a plan; ``install`` calls the same function, so the preview
and the write cannot differ.
"""

import os
import shutil

from . import (__version__, adoptplan, base, declarations, firstparty, gate, harnessstage, installplan, manifest,
               projectfs, refusal, snapshot, sources, target, verify)
from .wbkit import display, safefs

ENDING = "preview only: nothing was written"


Refused = refusal.Refused


def _recorded_source(resolved, name):
    return ("local:%s" % name) if resolved.local else resolved.source


def _gather(guarded, resolved, select, distribution, which):
    """Verify, gate and snapshot the selection. Returns ``(modules, snaps, loaded_base, packages,
    origins, warnings)``; raises ``Refused``."""
    distribution = distribution or firstparty.default_distribution()
    paths = [item.path for item in resolved]
    result = verify.verify_packages(
        paths, select, harness_required=True,
        first_party=[p for p in paths if firstparty.is_first_party(p, distribution)],
        which=which)
    if not result.accepted:
        raise Refused([str(problem) for problem in result.problems])
    decision = gate.check_selection(guarded, result, distribution)
    if not decision.approved:
        raise Refused(["%s/%s is not approved on this machine: %s" % (item.package, item.name,
                                                                      item.reason)
                       for item in decision.modules if not item.approved]
                      or [decision.reason])
    roots = dict(zip((info.name for info in result.packages), paths))
    origins = dict(zip((info.name for info in result.packages), resolved))
    by_key = {(m.package, m.name): m for m in result.modules}
    modules = tuple(by_key[key] for key in result.order)
    try:
        snaps = {(m.package, m.name): snapshot.take(os.path.join(roots[m.package], m.name), m)
                 for m in modules}
        loaded_base = base.load_base(distribution)
    except safefs.SafeFsError as exc:
        raise Refused([str(exc)])
    used = {m.package for m in modules}
    packages = tuple(installplan.PackageSource(
        info.name, _recorded_source(origins[info.name], info.name), origins[info.name].ref,
        origins[info.name].commit, info.tree_hash) for info in result.packages
        if info.name in used)
    return modules, snaps, loaded_base, packages, origins, list(result.warnings)


def prepare(guarded, held, resolved, select, distribution, seed, version, which=shutil.which,
            home=None, now=None):
    """Verify, gate, snapshot and plan, the harness files included. Returns ``(plan, warnings)``;
    raises ``Refused``. `home` is the directory the rendered permission rules name."""
    modules, snaps, loaded_base, packages, origins, warnings = _gather(
        guarded, resolved, select, distribution, which)
    # `verify` required exactly one harness module in the selection.
    harness = next(m for m in modules if m.type == "harness")
    staged = harnessstage.stage(
        guarded.root, harness, modules, snaps,
        _recorded_source(origins[harness.package], harness.package), version,
        home if home is not None else harnessstage.default_home(), held.path)
    if held.state == "new-git":
        # An existing .git may hold an exclude file attach cannot use: say so before the digest
        # is typed, not after the install is written.
        try:
            projectfs.Writer(held).check_exclude(staged.exclude)
        except safefs.SafeFsError as exc:
            raise Refused([".git/info/exclude: %s" % exc])
    try:
        plan = installplan.build(held, installplan.Selection(modules, packages), snaps,
                                 loaded_base, seed, version, staged, now)
    except (installplan.PlanError, manifest.ManifestError) as exc:
        raise Refused([str(exc)])
    return plan, warnings


def prepare_adopt(guarded, held, resolved, select, distribution, seed, version,
                  which=shutil.which, now=None):
    """The plan of ``wb adopt``: the same verification, gate and snapshots, then what is at each
    planned path. No harness is staged, since adopt attaches nothing. Returns ``(plan, warnings)``;
    raises ``Refused``."""
    if held.state == "existing":
        raise Refused(["the target is an existing project; use wb upgrade or wb add"])
    if held.state != "adoptable":
        raise Refused(["the target holds no content to adopt (%s); use wb install" % held.state])
    modules, snaps, loaded_base, packages, origins, warnings = _gather(
        guarded, resolved, select, distribution, which)
    selection = installplan.Selection(modules, packages)
    try:
        found = adoptplan.inspect(held, selection, snaps, loaded_base)
        plan = installplan.build(held, selection, snaps, loaded_base, seed, version, None, now,
                                 adopted=found)
    except adoptplan.Conflicts as exc:
        raise Refused(exc.lines)
    except (installplan.PlanError, manifest.ManifestError, safefs.SafeFsError) as exc:
        raise Refused([str(exc)])
    return plan, warnings


def resolve_all(guarded, packages):
    try:
        return [sources.resolve_cached(guarded, source, ref) for source, ref in packages]
    except sources.SourceError as exc:
        raise Refused([str(exc)])


def run(guarded, parsed, out, err, distribution=None, seed=None, version=None,
        which=shutil.which, home=None, adopt=False):
    """Print the preview and return 0, or print ``refused:`` lines and return 1. With `adopt`, the
    preview of ``wb adopt``."""
    try:
        with target.open_target(parsed.target, guarded.root, adopt=adopt) as held:
            resolved = resolve_all(guarded, parsed.packages)
            if adopt:
                plan, warnings = prepare_adopt(guarded, held, resolved, parsed.select, distribution,
                                               seed or manifest.new_seed(), version or __version__,
                                               which)
            else:
                plan, warnings = prepare(guarded, held, resolved, parsed.select, distribution,
                                         seed or manifest.new_seed(), version or __version__,
                                         which, home)
            text = installplan.render(plan, held.path)
    except target.TargetError as exc:
        return target.write_refusal(err, exc)
    except Refused as exc:
        for line in exc.lines:
            err.write("refused: %s\n" % display.clean(line))
        return 1
    except safefs.SafeFsError as exc:
        err.write("refused: %s\n" % display.clean(str(exc)))
        return 1
    for warning in warnings:
        err.write("warning: %s\n" % display.clean(warning))
    out.write(text)
    out.write(ENDING + "\n")
    return 0

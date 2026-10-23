"""The approval command: find the one command a project's process module declares for a plan's hashed region,
run it, and read what it reports.

``resolve`` reads the committed manifest and takes the process module that declares ``approval`` from the
installed ``module.json`` of a module the manifest records, only after that file's declaration hash equals the
manifest's. Exactly one such module is needed. The command it names is then held to the same rules as
``wb run``: the owner's pin must record exactly the declared helper, the declaration the owner confirmed and the
declared way of running it (``commands.check_pin``); the launcher still compares the helper's bytes with the pin.

``region`` runs ``<command> <argument> <plan>`` from the project root through the launcher, with standard input
closed, for at most ``TIMEOUT`` seconds and at most ``MAX_REPORT`` bytes of output, and accepts exactly one JSON
object and a newline (``docs/specs/trust-and-approval.md``, "Plan approval records"):
``{"format": 1, "region_hash": "<64 lowercase hex>", "unhashed": ["<name>", ...]}``. Nothing else is accepted.
The output is data: it is validated, never followed, and a helper's own words are shown only as cleaned ASCII.

The installer reads no plan. It hands the helper the plan's path relative to the project root and takes the
helper's report; what the region is belongs to the helper (``2026-10-22-plan-check-in-the-shipped-helper``).
``active_plans`` runs ``<command> <active>`` the same way, for a module that declares ``approval.active``, within
``MAX_ACTIVE_REPORT`` bytes, and accepts exactly one JSON object and a newline: ``{"format": 1, "plans":
["<root-relative path>", ...]}`` of at most ``MAX_ACTIVE`` paths of at most ``MAX_ACTIVE_PATH`` characters, each
passing the path rules, none repeated. The edit gate reads it (``gate_hook.py``).

``resolve_delegation`` also finds the one installed module that provides ``peer-review`` and declares ``convergence``,
held to the same pin rules, and ``delegable`` and ``convergence`` run the two commands a delegated approval reads
(``docs/specs/trust-and-approval.md``, "Delegated plan approval records"), each within its bound, and accept exactly
one JSON object and a newline.

Nothing here writes to the project or to the guarded store. Every refusal is an ``ApprovalError``.
"""

import collections
import re

from . import commands, launch, manifest
from .wbkit import display, jsonstrict, project, safefs

MAX_REPORT = 4096
TIMEOUT = 30
MAX_UNHASHED = 16
MAX_NAME = 64
MAX_ACTIVE_REPORT = 8192
MAX_ACTIVE = 32
MAX_ACTIVE_PATH = 240
MAX_DELEGABLE_REPORT = 1024
MAX_CONVERGENCE_REPORT = 4096
MAX_REASON = 200
MAX_BRIDGE = 64
MAX_MODEL = 200
MAX_ROUNDS = 5

Resolved = collections.namedtuple(
    "Resolved", "root project_id package module declaration helper_sha256 command argument kit active checkpoints "
    "delegable", defaults=(None, (), None))
Provider = collections.namedtuple(
    "Provider", "root project_id package module declaration helper_sha256 command argument kit")
Report = collections.namedtuple("Report", "region_hash unhashed")
Delegability = collections.namedtuple("Delegability", "delegable reason")
Convergence = collections.namedtuple(
    "Convergence", "converged document_sha256 rounds_used bound bridge model review closed")

_HASH = re.compile(r"[0-9a-f]{64}\Z")
_REVIEW = re.compile(r"plan-[0-9a-f]{16}\Z")


class ApprovalError(Exception):
    """The approval command cannot be resolved or run, or its report is not accepted; the message says why."""


def _shown(value, limit=120):
    return display.ascii_text(str(value))[:limit]


Installed = collections.namedtuple("Installed", "root project_id package module declaration")


def installed_modules(start):
    """``(root, project_id, [Installed, ...])`` for the project that holds the directory `start`: every module
    the committed manifest records as installed, each read after its declaration hash equals the manifest's.
    ``ApprovalError`` when the project or any installed declaration cannot be used. Nothing is started and
    nothing is written."""
    try:
        root = project.find_root(start)
        with safefs.Root(root, "project root") as held:
            document = manifest.parse(held.read_file(project.MANIFEST))
            ident = manifest.project_id(document["seed"])
            found = []
            for package in document["packages"]:
                for item in package["modules"]:
                    if commands.is_installed(document, package, item):
                        found.append(Installed(root, ident, package["name"],
                                               commands.installed_module(held, package, item), item["declaration"]))
    except (project.ProjectError, safefs.SafeFsError, manifest.ManifestError, commands.CommandError) as exc:
        raise ApprovalError(display.clean(str(exc))[:300])
    return root, ident, found


def _names(items):
    return ", ".join(sorted("%s/%s" % (item.package, item.module.name) for item in items))


def _approving(found):
    """The one ``Installed`` module of `found` that declares ``approval``, or ``ApprovalError``."""
    declaring = [item for item in found if item.module.approval is not None]
    if not declaring:
        raise ApprovalError("no installed module declares an approval command; nothing was run")
    if len(declaring) > 1:
        raise ApprovalError("more than one installed module declares an approval command: %s; nothing was run"
                            % _names(declaring))
    return declaring[0]


def resolve(guarded, start):
    """The ``Resolved`` approval command of the project that holds the directory `start`, or ``ApprovalError``.
    Nothing is started."""
    root, ident, found = installed_modules(start)
    return resolved(guarded, root, ident, _approving(found))


def resolve_delegation(guarded, start, *, check=None):
    """``(Resolved, Provider)``: the approval command and the one installed module that provides ``peer-review`` and
    declares ``convergence``, each with its pin held to the rules of ``wb run``, or ``ApprovalError``. `check`, when
    given, is called with the ``Resolved`` before the provider is looked for and may raise ``ApprovalError``. Nothing
    is started."""
    root, ident, found = installed_modules(start)
    process = resolved(guarded, root, ident, _approving(found))
    if check is not None:
        check(process)
    if not process.delegable:
        raise ApprovalError("the approval command of %s/%s declares no delegability argument; nothing was run"
                            % (process.package, process.module))
    providers = [item for item in found if "peer-review" in item.module.provides and item.module.convergence]
    what = "installed module provides peer-review with a convergence argument"
    if not providers:
        raise ApprovalError("no %s; nothing was run" % what)
    if len(providers) > 1:
        raise ApprovalError("more than one %s: %s; nothing was run" % (what, _names(providers)))
    item = providers[0]
    module = item.module
    command = next(c for c in module.commands if c.name == module.convergence["command"])
    declared = commands.Declared(item.package, module.name, command, item.declaration, tuple(module.provides))
    try:
        pin = commands.check_pin(guarded, ident, declared)
    except commands.CommandError as exc:
        raise ApprovalError(str(exc))
    return process, Provider(root, ident, item.package, module.name, item.declaration, pin.sha256, command.name,
                             module.convergence["argument"], pin.kit)


def resolved(guarded, root, ident, item):
    """The ``Resolved`` approval command of the ``Installed`` module `item`, which declares ``approval``: its
    pin must record exactly the declared helper (``commands.check_pin``). Nothing is started."""
    module = item.module
    command = next(c for c in module.commands if c.name == module.approval["command"])
    found = commands.Declared(item.package, module.name, command, item.declaration, tuple(module.provides))
    try:
        pin = commands.check_pin(guarded, ident, found)
    except commands.CommandError as exc:
        raise ApprovalError(str(exc))
    return Resolved(root, ident, item.package, module.name, item.declaration, pin.sha256, command.name,
                    module.approval["argument"], pin.kit, module.approval.get("active"), tuple(module.checkpoints),
                    module.approval.get("delegable"))


def _plan_argument(plan):
    """`plan` as the helper is given it: a path relative to the project root that passes the path rules and
    cannot be taken for an option."""
    try:
        parts = safefs.validate_relpath(plan)
    except safefs.SafeFsError as exc:
        raise ApprovalError("the plan path %s is refused: %s" % (_shown(plan, 80), _shown(exc, 120)))
    if parts[0].startswith("-"):
        raise ApprovalError("the plan path %s could be taken for an option" % _shown(plan, 80))
    return plan


def _cleaned_end(data):
    lines = data.decode("utf-8", "replace").strip().splitlines()
    return _shown(lines[-1].strip(), 200) if lines else ""


def _capture(guarded, found, args, limit, timeout, what="the approval command"):
    """The standard output of the command `found` run with `args`, or ``ApprovalError`` naming `what`."""
    try:
        done = launch.launch_captured(guarded, found.project_id, found.command, found.root, args, limit=limit,
                                      timeout=timeout, kit=found.kit, cwd=found.root)
    except launch.LaunchError as exc:
        raise ApprovalError(_shown(exc, 300))
    if done.over:
        raise ApprovalError("%s printed more than %d bytes and was stopped" % (what, limit))
    if done.timed_out:
        raise ApprovalError("%s did not finish within %g seconds and was stopped" % (what, timeout))
    if done.code != 0:
        said = _cleaned_end(done.stderr) or _cleaned_end(done.stdout)
        raise ApprovalError("%s failed (exit %d)%s" % (what, done.code, ": " + said if said else ""))
    return done.stdout


def region(guarded, found, plan, *, timeout=None):
    """The ``Report`` the approval command gives for the root-relative path `plan`, or ``ApprovalError``."""
    plan = _plan_argument(plan)
    return parse_report(_capture(guarded, found, [found.argument, plan], MAX_REPORT, timeout or TIMEOUT))


def active_plans(guarded, found, *, timeout=None):
    """The root-relative paths of the plans under way, as the approval command's ``active`` argument lists
    them, or ``ApprovalError``. The command is run once, with that argument only."""
    if not found.active:
        raise ApprovalError("the approval command declares no argument that lists the plans under way")
    return parse_active(_capture(guarded, found, [found.active], MAX_ACTIVE_REPORT, timeout or TIMEOUT))


def parse_active(data):
    """The list of paths in the bytes `data` an ``active`` command printed, or ``ApprovalError``."""
    if not data.endswith(b"\n") or data.count(b"\n") != 1:
        raise ApprovalError("the active command's report is not one line ending in a newline")
    try:
        report = jsonstrict.parse_object(data[:-1], MAX_ACTIVE_REPORT)
    except ValueError as exc:
        raise ApprovalError("the active command's report is not one JSON object: %s" % _shown(exc, 80))
    if set(report) != {"format", "plans"}:
        raise ApprovalError("the active command's report must hold exactly format and plans")
    if type(report["format"]) is not int or report["format"] != 1:
        raise ApprovalError("the active command's report has a format this workbench does not read")
    plans = report["plans"]
    if not isinstance(plans, list) or len(plans) > MAX_ACTIVE:
        raise ApprovalError("the active command's plans must be a list of at most %d paths" % MAX_ACTIVE)
    for plan in plans:
        if not isinstance(plan, str) or not 1 <= len(plan) <= MAX_ACTIVE_PATH or not safefs.relpath_ok(plan):
            raise ApprovalError("the active command's plans hold a path that is not one to %d characters passing "
                                "the path rules" % MAX_ACTIVE_PATH)
        if plan.startswith("-"):
            raise ApprovalError("the active command's plans hold a path that could be taken for an option")
    if len(set(plans)) != len(plans):
        raise ApprovalError("the active command's plans repeat a path")
    return list(plans)


def parse_report(data):
    """The ``Report`` in the bytes `data` an approval command printed, or ``ApprovalError``."""
    if not data.endswith(b"\n") or data.count(b"\n") != 1:
        raise ApprovalError("the approval command's report is not one line ending in a newline")
    try:
        report = jsonstrict.parse_object(data[:-1], MAX_REPORT)
    except ValueError as exc:
        raise ApprovalError("the approval command's report is not one JSON object: %s" % _shown(exc, 80))
    if set(report) != {"format", "region_hash", "unhashed"}:
        raise ApprovalError("the approval command's report must hold exactly format, region_hash and unhashed")
    if type(report["format"]) is not int or report["format"] != 1:
        raise ApprovalError("the approval command's report has a format this workbench does not read")
    digest = report["region_hash"]
    if not isinstance(digest, str) or not _HASH.match(digest):
        raise ApprovalError("the approval command's region_hash is not 64 lowercase hexadecimal characters")
    names = report["unhashed"]
    if not isinstance(names, list) or len(names) > MAX_UNHASHED:
        raise ApprovalError("the approval command's unhashed must be a list of at most %d names" % MAX_UNHASHED)
    for name in names:
        if not isinstance(name, str) or not 1 <= len(name) <= MAX_NAME or not name.isprintable():
            raise ApprovalError("the approval command's unhashed holds a name that is not one to %d printable "
                                "characters" % MAX_NAME)
    return Report(digest, tuple(names))


def delegable(guarded, found, plan, *, timeout=None):
    """The ``Delegability`` the approval command's ``delegable`` argument gives for the root-relative path `plan`, or
    ``ApprovalError``."""
    if not found.delegable:
        raise ApprovalError("the approval command declares no delegability argument")
    plan = _plan_argument(plan)
    what = "the delegability command"
    return parse_delegable(_capture(guarded, found, [found.delegable, plan], MAX_DELEGABLE_REPORT,
                                    timeout or TIMEOUT, what))


def convergence(guarded, provider, plan, *, timeout=None):
    """The ``Convergence`` the provider's ``convergence`` argument gives for the root-relative path `plan`, or
    ``ApprovalError``."""
    plan = _plan_argument(plan)
    return parse_convergence(_capture(guarded, provider, [provider.argument, plan], MAX_CONVERGENCE_REPORT,
                                      timeout or TIMEOUT, "the convergence command"))


def _object(data, what, limit, fields):
    """The one JSON object in the bytes `data` a command printed, which must hold exactly `fields`."""
    if not data.endswith(b"\n") or data.count(b"\n") != 1:
        raise ApprovalError("%s's report is not one line ending in a newline" % what)
    try:
        report = jsonstrict.parse_object(data[:-1], limit)
    except ValueError as exc:
        raise ApprovalError("%s's report is not one JSON object: %s" % (what, _shown(exc, 80)))
    if set(report) != set(fields):
        raise ApprovalError("%s's report must hold exactly %s" % (what, ", ".join(fields)))
    if type(report["format"]) is not int or report["format"] != 1:
        raise ApprovalError("%s's report has a format this workbench does not read" % what)
    return report


def _flag(report, what, key):
    if type(report[key]) is not bool:
        raise ApprovalError("%s's %s is not true or false" % (what, key))
    return report[key]


def _text(report, what, key, limit, *, empty=False):
    value = report[key]
    if not isinstance(value, str) or len(value) > limit or (not value and not empty) or not value.isprintable():
        raise ApprovalError("%s's %s is not %s printable characters" % (
            what, key, "text of at most %d" % limit if empty else "one to %d" % limit))
    return value


def _count(report, what, key):
    value = report[key]
    if type(value) is not int or not 1 <= value <= MAX_ROUNDS:
        raise ApprovalError("%s's %s is not a number from 1 to %d" % (what, key, MAX_ROUNDS))
    return value


def parse_delegable(data):
    """The ``Delegability`` in the bytes `data` a delegability command printed, or ``ApprovalError``."""
    what = "the delegability command"
    report = _object(data, what, MAX_DELEGABLE_REPORT, ("format", "delegable", "reason"))
    return Delegability(_flag(report, what, "delegable"), _text(report, what, "reason", MAX_REASON, empty=True))


def parse_convergence(data):
    """The ``Convergence`` in the bytes `data` a convergence command printed, or ``ApprovalError``."""
    what = "the convergence command"
    report = _object(data, what, MAX_CONVERGENCE_REPORT, (
        "format", "kind", "converged", "document_sha256", "rounds_used", "bound", "bridge", "model", "review",
        "closed"))
    if report["kind"] != "plan":
        raise ApprovalError("%s's report is not of a plan" % what)
    digest = report["document_sha256"]
    if not isinstance(digest, str) or not _HASH.match(digest):
        raise ApprovalError("%s's document_sha256 is not 64 lowercase hexadecimal characters" % what)
    review = report["review"]
    if not isinstance(review, str) or not _REVIEW.match(review):
        raise ApprovalError("%s's review is not plan- and 16 lowercase hexadecimal characters" % what)
    model = None if report["model"] is None else _text(report, what, "model", MAX_MODEL)
    return Convergence(_flag(report, what, "converged"), digest, _count(report, what, "rounds_used"),
                       _count(report, what, "bound"), _text(report, what, "bridge", MAX_BRIDGE), model, review,
                       _flag(report, what, "closed"))

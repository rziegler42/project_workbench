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

Resolved = collections.namedtuple(
    "Resolved", "root project_id package module declaration helper_sha256 command argument kit")
Report = collections.namedtuple("Report", "region_hash unhashed")

_HASH = re.compile(r"[0-9a-f]{64}\Z")


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


def resolve(guarded, start):
    """The ``Resolved`` approval command of the project that holds the directory `start`, or ``ApprovalError``.
    Nothing is started."""
    root, ident, found = installed_modules(start)
    declaring = [(item.package, item.module, item.declaration) for item in found if item.module.approval is not None]
    if not declaring:
        raise ApprovalError("no installed module declares an approval command; nothing was run")
    if len(declaring) > 1:
        raise ApprovalError("more than one installed module declares an approval command: %s; nothing was run"
                            % ", ".join(sorted("%s/%s" % (package, module.name) for package, module, _ in declaring)))
    package, module, declaration = declaring[0]
    command = next(c for c in module.commands if c.name == module.approval["command"])
    found = commands.Declared(package, module.name, command, declaration, tuple(module.provides))
    try:
        pin = commands.check_pin(guarded, ident, found)
    except commands.CommandError as exc:
        raise ApprovalError(str(exc))
    return Resolved(root, ident, package, module.name, declaration, pin.sha256, command.name,
                    module.approval["argument"], pin.kit)


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


def region(guarded, resolved, plan):
    """The ``Report`` the approval command gives for the root-relative path `plan`, or ``ApprovalError``."""
    plan = _plan_argument(plan)
    try:
        done = launch.launch_captured(guarded, resolved.project_id, resolved.command, resolved.root,
                                      [resolved.argument, plan], limit=MAX_REPORT, timeout=TIMEOUT,
                                      kit=resolved.kit, cwd=resolved.root)
    except launch.LaunchError as exc:
        raise ApprovalError(_shown(exc, 300))
    if done.over:
        raise ApprovalError("the approval command printed more than %d bytes and was stopped" % MAX_REPORT)
    if done.timed_out:
        raise ApprovalError("the approval command did not finish within %d seconds and was stopped" % TIMEOUT)
    if done.code != 0:
        said = _cleaned_end(done.stderr) or _cleaned_end(done.stdout)
        raise ApprovalError("the approval command failed (exit %d)%s" % (done.code, ": " + said if said else ""))
    return parse_report(done.stdout)


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

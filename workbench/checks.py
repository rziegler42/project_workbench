"""Module checks: from a project to the report lines of every recorded module's pinned check helpers.

``run_all`` is what ``wb check`` asks for after its own checks (``docs/specs/module-boundary.md``,
"Module checks"). It reads the committed manifest, takes each recorded module's checks from its
installed ``module.json`` (only after that file's declaration hash equals the manifest's) and starts
each helper through the launcher, from the project root, with its standard output read here.

A check helper writes report lines, ``problem: <text>`` or ``warning: <text>``, and nothing else, and
exits 0. Any other exit, a line in another form, output that is not text, too much output or too
long a run is a problem of the check itself, reported as "the check <name> failed". A check that is
not pinned, whose pin names another helper or kit, or whose bytes changed, is a problem too and runs
nothing; the other checks still run. Every line is cleaned to one line of ASCII, bounded in length
and number, and returned without its prefix, so the caller prints it under the module's name and a
helper cannot write a line that looks like the installer's own.

The order is the manifest's modules sorted by package name and then module name, by code point, and
within a module the order of its ``checks`` list; it does not depend on how the modules were installed.
Nothing here writes to the project.
"""

import collections

from . import commands, launch, manifest, pins
from .wbkit import display, project, safefs

CAPTURE_LIMIT = 256 * 1024
TIMEOUT = 120
MAX_LINES = 200
MAX_LINE = 300
SHOWN_OUTPUT = 120

Section = collections.namedtuple("Section", "label problems warnings")

_PREFIXES = (("problem: ", "problems"), ("warning: ", "warnings"))


def _shown(text, limit=MAX_LINE):
    return display.ascii_text(str(text))[:limit]


def _start_of(data):
    """The cleaned start of what a helper printed, for a message about a failure."""
    return _shown(data.decode("utf-8", "replace").strip(), SHOWN_OUTPUT)


def _end_of(data):
    """The cleaned last line of what a helper wrote to standard error: for a traceback, its reason."""
    lines = data.decode("utf-8", "replace").strip().splitlines()
    return _shown(lines[-1].strip(), SHOWN_OUTPUT) if lines else ""


def _lines(data):
    """``(problems, warnings, left_out, failure)`` for the standard output `data` of a helper that
    exited 0. `failure` is a reason when the output is not in the report form; `left_out` is true
    when more than ``MAX_LINES`` lines were printed and the rest were dropped."""
    if not data:
        return [], [], False, None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return [], [], False, "its output is not text"
    if not text.endswith("\n"):
        return [], [], False, "its last line has no end of line"
    taken = []
    for line in text[:-1].split("\n"):
        for prefix, kind in _PREFIXES:
            if line.startswith(prefix) and line[len(prefix):].strip():
                taken.append((kind, _shown(line[len(prefix):])))
                break
        else:
            return [], [], False, "it printed a line that is neither a problem nor a warning: %s" % _shown(line, 60)
    left_out = len(taken) > MAX_LINES
    taken = taken[:MAX_LINES]
    return ([t for k, t in taken if k == "problems"], [t for k, t in taken if k == "warnings"],
            left_out, None)


def _run_one(guarded, ident, root, package, module_name, check, declaration):
    """``(problems, warnings)`` for one check of the installed module."""
    name = check.pin_name
    shown = _shown(name, 64)
    try:
        pin = pins.lookup(guarded, ident, name)
    except pins.PinError as exc:
        return ["the check %s is not pinned (%s); its owner pins the module's helper with `pin`, "
                "so it did not run" % (shown, _shown(exc, 120))], []
    wanted = ".workbench/%s/%s/%s" % (package, module_name, check.helper)
    if pin.path != wanted:
        return ["the pin named %s records %s, which is not the declared helper %s; the owner pins "
                "the declared helper, so the check did not run" % (shown, _shown(pin.path, 120), wanted)], []
    if pin.declaration is not None and pin.declaration != declaration:
        return ["the declaration of %s/%s has changed since the pin named %s was made; the owner "
                "confirms the module's declaration with `wb upgrade`, or pins the helper again with "
                "`pin`, so the check did not run" % (package, module_name, shown)], []
    if pin.kit != check.kit:
        return ["the pin named %s records %s, but the declaration says the helper runs through kit API "
                "%d; the owner pins it again with `pin --kit %d`, so the check did not run" % (
                    shown, "kit API %d" % pin.kit if pin.kit is not None else "no kit",
                    check.kit, check.kit)], []
    try:
        done = launch.launch_captured(guarded, ident, name, root, [], limit=CAPTURE_LIMIT,
                                      timeout=TIMEOUT, kit=check.kit, cwd=root)
    except launch.LaunchError as exc:
        return ["the check %s did not run: %s" % (shown, _shown(exc, 200))], []
    if done.over:
        return ["the check %s failed: it printed more than %d bytes and was stopped"
                % (shown, CAPTURE_LIMIT)], []
    if done.timed_out:
        return ["the check %s failed: it did not finish within %d second%s and was stopped"
                % (shown, TIMEOUT, "" if TIMEOUT == 1 else "s")], []
    if done.code != 0:
        said = _start_of(done.stdout) or _end_of(done.stderr)
        return ["the check %s failed (exit %d)%s" % (shown, done.code, ": " + said if said else "")], []
    problems, warnings, left_out, failure = _lines(done.stdout)
    if failure:
        return ["the check %s failed: %s" % (shown, failure)], []
    if left_out:
        problems.append("the check %s printed more than %d lines; the rest were not taken"
                        % (shown, MAX_LINES))
    return problems, warnings


def run_all(guarded, root):
    """The ``Section`` of every recorded module that declares checks, for the project at `root`.

    A project with no committed manifest has none. A manifest that cannot be read is reported as a
    section labelled ``manifest``, never as silence."""
    try:
        with safefs.Root(root, "project root") as held:
            data = held.read_if_present(project.MANIFEST)
            if data is None:
                return []
            document = manifest.parse(data)
            ident = manifest.project_id(document["seed"])
            sections = []
            entries = sorted(((package["name"], item["name"], package, item)
                              for package in document["packages"] for item in package["modules"]),
                             key=lambda entry: entry[:2])
            for package_name, module_name, package, item in entries:
                if not commands.is_installed(document, package, item):
                    continue
                label = "%s/%s" % (package_name, module_name)
                try:
                    module = commands.installed_module(held, package, item)
                except commands.CommandError as exc:
                    sections.append(Section(label, [_shown(exc, 300)], []))
                    continue
                if not module.checks:
                    continue
                problems, warnings = [], []
                for check in module.checks:
                    more_problems, more_warnings = _run_one(guarded, ident, root, package_name,
                                                            module_name, check, item["declaration"])
                    problems.extend(more_problems)
                    warnings.extend(more_warnings)
                sections.append(Section(label, problems, warnings))
            return sections
    except (safefs.SafeFsError, manifest.ManifestError) as exc:
        return [Section("manifest", ["the project manifest cannot be used: %s" % _shown(exc, 200)], [])]

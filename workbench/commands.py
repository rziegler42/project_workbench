"""Module commands: from a working directory, a command name and arguments to a launch request.

``resolve`` is what ``wb run`` asks before it starts anything. It finds the project with the kit's
finder, reads the committed manifest, and takes the command from the installed ``module.json`` of a
module the manifest records, but only after that file's declaration hash equals the one the manifest
holds. It then requires the owner's pin under the command's name to record exactly the helper the
declaration names, ``.workbench/<package>/<module>/<helper>``; the launcher still checks the bytes. A
declared first argument is required when the command lists any, and refused when it lists none.

``resolve`` reads and decides; it starts no program and writes nothing. Every refusal is a
``CommandError`` whose message says why, and nothing has run when one is raised. ``run`` is the
``wb run`` command: it resolves, then hands the request to the launcher.

``wb run --provides <capability> <command> ...`` also requires the module that declares the command to
provide the capability. The check is made here, from the declaration whose hash was just compared, so a
helper that runs another module's command (``wbkit.call``) does not make it for itself.
"""

import collections
import os
import re
import sys

from . import approve, declarations, hashing, launch, manifest, pins
from .wbkit import display, project, safefs

Request = collections.namedtuple("Request", "root project_id name arguments kit owner", defaults=((),))
Declared = collections.namedtuple("Declared", "package module command declaration provides")


class CommandError(Exception):
    """Nothing was run; the message says why."""


def _shown(value):
    return display.ascii_text(str(value))[:120]


def installed_module(held, package, item):
    """The ``Module`` read from the installed ``module.json`` of the manifest entry `item` of the
    manifest package `package`, after its declaration hash equals the manifest's. Raises
    ``CommandError`` when the file cannot be used, has changed since it was installed or is not valid."""
    rel = ".workbench/%s/%s/module.json" % (package["name"], item["name"])
    label = "%s/%s" % (package["name"], item["name"])
    try:
        data = held.read_file(rel)
        current = hashing.declaration_hash(declarations.parse_json(data))
    except (safefs.SafeFsError, ValueError) as exc:
        raise CommandError("the installed module.json of %s cannot be used: %s"
                           % (label, display.clean(str(exc))[:200]))
    if current != item["declaration"]:
        raise CommandError("the module.json of %s has changed since it was installed; nothing was run"
                           % label)
    try:
        # First-party only gates which capabilities a module may provide; the declaration
        # was approved at install and its hash was just compared, so only commands are read.
        return declarations.parse_module(data, package["name"], item["name"], first_party=True)
    except declarations.DeclarationError as exc:
        raise CommandError("the installed module.json of %s is not valid: %s"
                           % (label, display.clean(str(exc))[:200]))


def is_installed(document, package, item):
    """Whether the manifest lists the ``module.json`` of the module: a harness module writes nothing
    into the project, so it is not installed and declares nothing here."""
    rel = ".workbench/%s/%s/module.json" % (package["name"], item["name"])
    return any(entry["path"] == rel for entry in document["files"])


def _declared(held, document):
    """Every command declared by an installed module that the manifest records, as ``Declared``.

    An installed declaration that cannot be read, or whose hash differs from the manifest's,
    refuses the whole lookup."""
    found = []
    for package in document["packages"]:
        for item in package["modules"]:
            if not is_installed(document, package, item):
                continue
            module = installed_module(held, package, item)
            for command in module.commands:
                found.append(Declared(package["name"], item["name"], command, item["declaration"],
                                      tuple(module.provides)))
    return found


def _arguments(command, args):
    allowed = command.arguments
    if not allowed:
        if args:
            raise CommandError("the command %s takes no argument" % _shown(command.name))
        return
    if not args:
        raise CommandError("the command %s needs one of: %s" % (_shown(command.name),
                                                                ", ".join(allowed)))
    if args[0] not in allowed:
        raise CommandError("%s is not an argument of the command %s; it takes one of: %s"
                           % (_shown(args[0]), _shown(command.name), ", ".join(allowed)))


def check_pin(guarded, ident, found):
    """The ``Pin`` of the declared command `found` (a ``Declared``), after it records exactly the declared
    helper, the declaration hash the owner confirmed and the way the declaration says it runs. Raises
    ``CommandError``; nothing has run."""
    name, command = found.command.name, found.command
    try:
        pin = pins.lookup(guarded, ident, name)
    except pins.PinError as exc:
        raise CommandError("the command %s is not pinned (%s); its owner pins the module's helper "
                           "with `pin`, and nothing was run" % (_shown(name), display.clean(str(exc))[:200]))
    wanted = ".workbench/%s/%s/%s" % (found.package, found.module, command.helper)
    if pin.path != wanted:
        raise CommandError("the pin named %s records %s, which is not the declared helper %s; the "
                           "owner pins the declared helper, and nothing was run"
                           % (_shown(name), _shown(pin.path), wanted))
    if pin.declaration is not None and pin.declaration != found.declaration:
        raise CommandError("the declaration of %s/%s has changed since the pin named %s was made; the "
                           "owner confirms the module's declaration with `wb upgrade`, or pins the helper "
                           "again with `pin`, and nothing was run" % (found.package, found.module, _shown(name)))
    kit = command.kit if command.runtime == "python" else None
    if pin.kit != kit:
        raise CommandError(
            "the pin named %s records %s, but the declaration says the helper %s; the owner pins it "
            "again with `pin`%s, and nothing was run" % (
                _shown(name), "kit API %d" % pin.kit if pin.kit is not None else "no kit",
                "runs through kit API %d" % kit if kit is not None else "runs directly",
                " --kit %d" % kit if kit is not None else ""))
    return pin


def resolve(guarded, start, name, args, provides=None):
    """The launch request for ``wb run <name> <args>`` run from `start`, or ``CommandError``. With
    `provides`, the module that declares the command must provide that capability."""
    args = list(args)
    try:
        pins.check_name(name)
        if provides is not None and not _CAPABILITY.match(provides):
            raise CommandError("%s is not a capability name" % _shown(provides))
        root = project.find_root(start)
        with safefs.Root(root, "project root") as held:
            # One read: the ID and the modules come from the same bytes.
            document = manifest.parse(held.read_file(project.MANIFEST))
            ident = manifest.project_id(document["seed"])
            declared = [d for d in _declared(held, document) if d.command.name == name]
    except (project.ProjectError, pins.PinError, safefs.SafeFsError, manifest.ManifestError) as exc:
        raise CommandError(display.clean(str(exc))[:300])
    if not declared:
        raise CommandError("no installed module declares the command %s" % _shown(name))
    if len(declared) > 1:
        raise CommandError("more than one installed module declares the command %s: %s" % (
            _shown(name), ", ".join(sorted("%s/%s" % (d.package, d.module) for d in declared))))
    found = declared[0]
    command = found.command
    if provides is not None and provides not in found.provides:
        raise CommandError("the module %s/%s that declares the command %s does not provide %s; nothing was run"
                           % (found.package, found.module, _shown(name), _shown(provides)))
    _arguments(command, args)
    pin = check_pin(guarded, ident, found)
    return Request(root, ident, name, args, pin.kit, command.owner)


def launch_refusal(guarded, project_id, name, root, args, stdin, stdout):
    """Why ``wb launch`` may not run the pinned helper `name` with `args`, or None.

    A pin the installer made records the declaration the owner confirmed. For such a pin the declaration
    installed at `root` must be that one, and its ``owner`` list is applied as ``wb run`` applies it, so a root
    whose declaration drops the list is refused. A pin the owner typed has no declaration and no list."""
    try:
        pin = pins.lookup(guarded, project_id, name)
    except pins.PinError:
        return None  # the launcher says why nothing runs
    if pin.declaration is None:
        return None
    try:
        with safefs.Root(root, "project root") as held:
            document = manifest.parse(held.read_file(project.MANIFEST))
            found = [d for d in _declared(held, document) if d.command.name == name]
    except (safefs.SafeFsError, manifest.ManifestError, pins.PinError) as exc:
        return "the declaration of %s cannot be read at the root: %s" % (_shown(name), display.clean(str(exc))[:200])
    if len(found) != 1 or found[0].declaration != pin.declaration:
        return ("the declaration of %s at the root is not the one the owner confirmed for its pin; nothing was run"
                % _shown(name))
    return owner_refusal(name, found[0].command.owner, args, stdin, stdout)


USAGE = "usage: wb run [--provides <capability>] <command> [<argument> ...]\n"

_CAPABILITY = re.compile(r"[a-z0-9][a-z0-9:._-]{0,63}\Z")


def split(tokens):
    """``(capability or None, command and arguments)`` from the tokens after ``wb run``, or None when
    they are not usable. Only ``--provides <capability>`` first is an option; everything after the
    command is the helper's."""
    tokens = list(tokens)
    provides = None
    if len(tokens) >= 2 and tokens[0] == "--provides":
        provides, tokens = tokens[1], tokens[2:]
    if not tokens or not tokens[0] or tokens[0].startswith("-") or (provides is not None and not provides):
        return None
    return provides, tokens


def owner_refusal(name, owner, args, stdin, stdout):
    """Why the first of `args` may not run, or None. An argument a command declares ``owner`` runs only when
    standard input and output are both terminals, the test ``approve`` and ``pin`` use. It is a mistake guard,
    not a sandbox: it does not read how the command was spelled, but a process that opens its own
    pseudo-terminal passes it."""
    if not args or args[0] not in owner:
        return None
    if approve.is_terminal(stdin) and approve.is_terminal(stdout):
        return None
    return ("%s of the command %s is the owner's; run it yourself, from your own terminal"
            % (_shown(args[0]), _shown(name)))


def run(guarded, tokens, err, *, cwd=None, stdin=None, stdout=None):
    """``wb run [--provides <capability>] <command> [<argument> ...]``: returns the helper's exit code,
    2 for a usage error, or 1 with one ``refused:`` line when nothing was run. It prints nothing of its
    own on success."""
    parts = split(tokens)
    if parts is None:
        err.write(USAGE)
        return 2
    provides, tokens = parts
    try:
        try:
            start = cwd if cwd is not None else os.getcwd()
        except OSError as exc:
            raise CommandError("the working directory cannot be read: %s" % (exc.strerror or "unknown error"))
        request = resolve(guarded, start, tokens[0], tokens[1:], provides)
        reason = owner_refusal(request.name, request.owner, request.arguments,
                               stdin if stdin is not None else sys.stdin,
                               stdout if stdout is not None else sys.stdout)
        if reason:
            raise CommandError(reason)
        return launch.launch(guarded, request.project_id, request.name, request.root,
                             request.arguments, stdout=stdout, kit=request.kit)
    except (CommandError, launch.LaunchError) as exc:
        err.write("refused: %s\n" % display.clean(str(exc)))
        return 1

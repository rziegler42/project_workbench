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
"""

import collections
import os

from . import declarations, hashing, launch, manifest, pins
from .wbkit import display, project, safefs

Request = collections.namedtuple("Request", "root project_id name arguments kit")
Declared = collections.namedtuple("Declared", "package module command")


class CommandError(Exception):
    """Nothing was run; the message says why."""


def _shown(value):
    return display.ascii_text(str(value))[:120]


def _declared(held, document):
    """Every command declared by an installed module that the manifest records, as ``Declared``.

    A module is installed when the manifest lists its ``module.json``; a harness module writes
    nothing into the project, so it is not, and declares no command here. An installed declaration
    that cannot be read, or whose hash differs from the manifest's, refuses the whole lookup."""
    installed = {item["path"] for item in document["files"]}
    found = []
    for package in document["packages"]:
        for item in package["modules"]:
            rel = ".workbench/%s/%s/module.json" % (package["name"], item["name"])
            if rel not in installed:
                continue
            label = "%s/%s" % (package["name"], item["name"])
            try:
                data = held.read_file(rel)
                current = hashing.declaration_hash(declarations.parse_json(data))
            except (safefs.SafeFsError, ValueError) as exc:
                raise CommandError("the installed module.json of %s cannot be used: %s"
                                   % (label, display.clean(str(exc))[:200]))
            if current != item["declaration"]:
                raise CommandError(
                    "the module.json of %s has changed since it was installed; nothing was run" % label)
            try:
                # First-party only gates which capabilities a module may provide; the declaration
                # was approved at install and its hash was just compared, so only commands are read.
                module = declarations.parse_module(data, package["name"], item["name"],
                                                   first_party=True)
            except declarations.DeclarationError as exc:
                raise CommandError("the installed module.json of %s is not valid: %s"
                                   % (label, display.clean(str(exc))[:200]))
            for command in module.commands:
                found.append(Declared(package["name"], item["name"], command))
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


def resolve(guarded, start, name, args):
    """The launch request for ``wb run <name> <args>`` run from `start`, or ``CommandError``."""
    args = list(args)
    try:
        pins.check_name(name)
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
    _arguments(command, args)
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
    kit = command.kit if command.runtime == "python" else None
    if pin.kit != kit:
        raise CommandError(
            "the pin named %s records %s, but the declaration says the helper %s; the owner pins it "
            "again with `pin`%s, and nothing was run" % (
                _shown(name), "kit API %d" % pin.kit if pin.kit is not None else "no kit",
                "runs through kit API %d" % kit if kit is not None else "runs directly",
                " --kit %d" % kit if kit is not None else ""))
    return Request(root, ident, name, args, kit)


USAGE = "usage: wb run <command> [<argument> ...]\n"


def run(guarded, tokens, err, *, cwd=None, stdout=None):
    """``wb run <command> [<argument> ...]``: returns the helper's exit code, 2 for a usage error, or
    1 with one ``refused:`` line when nothing was run. It prints nothing of its own on success."""
    if not tokens or not tokens[0] or tokens[0].startswith("-"):
        err.write(USAGE)
        return 2
    try:
        try:
            start = cwd if cwd is not None else os.getcwd()
        except OSError as exc:
            raise CommandError("the working directory cannot be read: %s" % (exc.strerror or "unknown error"))
        request = resolve(guarded, start, tokens[0], tokens[1:])
        return launch.launch(guarded, request.project_id, request.name, request.root,
                             request.arguments, stdout=stdout, kit=request.kit)
    except (CommandError, launch.LaunchError) as exc:
        err.write("refused: %s\n" % display.clean(str(exc)))
        return 1

"""The command line: ``python3 -m workbench verify``.

Exit codes: 0 accepted, 1 refused, 2 usage error. The command reads the package and
writes nothing there; every command first creates the guarded store if it is missing.
"""

import argparse
import os
import sys

from . import (acknowledge, approve, attach, check, dispatch, firstparty, install, launch, pins, preview, recover,
               safefs, settings, sources, store, target, upgrade, verify)
from .wbkit import display

PROG = "python3 -m workbench"
USAGE = ("usage: python3 -m workbench verify [<package> | --dir <path>] "
         "[--select <module> ...] [--no-harness-required]\n"
         "       python3 -m workbench approve (<package> | --source <url> [--ref <ref>]) [--module <name>]\n"
         "                                                    (owner-run, terminal only)\n"
         "       python3 -m workbench pin <project-id> <name> <helper> --root <dir>   (owner-run, terminal only)\n"
         "       python3 -m workbench launch <project-id> <name> --root <dir> -- <args>\n"
         "       python3 -m workbench code-work check|plans|report   (read-only)\n"
         "       python3 -m workbench release-approvals\n"
         "       python3 -m workbench preview install [<target> | --dir <path>] --package <source> [--ref <ref>] ...\n"
         "                                            [--package ...] --select <module> ...   (read-only)\n"
         "       python3 -m workbench install <same arguments as preview install>   (owner-run, terminal only)\n"
         "       python3 -m workbench preview upgrade [<target> | --dir <path>] [--package <source> [--ref <ref>]] ...\n"
         "                                            (read-only; no --select, no download)\n"
         "       python3 -m workbench upgrade <same arguments as preview upgrade>   (owner-run, terminal only)\n"
         "       python3 -m workbench preview add [<target> | --dir <path>] --package <source> [--ref <ref>] ...\n"
         "                                        --select <module> ...   (read-only; no download)\n"
         "       python3 -m workbench add <same arguments as preview add>   (owner-run, terminal only)\n"
         "       python3 -m workbench acknowledge [<target> | --dir <path>]   (owner-run, terminal only)\n"
         "       python3 -m workbench recover [<target> | --dir <path>]   (owner-run, terminal only)\n"
         "       python3 -m workbench attach [<target> | --dir <path>] --harness <package>/<module>\n"
         "                                   [--package <source> [--ref <ref>]] ...   (owner-run)\n"
         "       python3 -m workbench check [<target> | --dir <path>]   (read-only)\n"
         "The package goes before --select, or use --dir. Options are not abbreviated.\n")


class _Usage(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise _Usage(message)


def _parser():
    parser = _Parser(prog=PROG, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", parser_class=_Parser)
    check = commands.add_parser("verify", help="verify a package and, optionally, a selection",
                                allow_abbrev=False)
    check.add_argument("package", nargs="?", help="the package directory (default: .)")
    check.add_argument("--dir", dest="dir", metavar="PATH",
                       help="the package directory, same as the positional argument")
    check.add_argument("--select", nargs="+", metavar="MODULE",
                       help="check these modules as one install: <module> or <package>/<module>")
    check.add_argument("--no-harness-required", action="store_true",
                       help="do not require a harness module in the selection")
    owner = commands.add_parser("approve", allow_abbrev=False,
                                help="owner-run, from a terminal: approve a package or one module")
    owner.add_argument("package", nargs="?", help="the package directory")
    owner.add_argument("--source", metavar="URL",
                       help="download the package into the cache first: an https, ssh or file URL, "
                            "or a local repository")
    owner.add_argument("--ref", metavar="REF", help="the branch, tag or commit to download "
                                                    "(default: HEAD); only with --source")
    owner.add_argument("--module", metavar="NAME", help="approve only this module")
    pin = commands.add_parser("pin", allow_abbrev=False,
                              help="owner-run, from a terminal: pin a helper's content")
    pin.add_argument("project_id", help="the project id (64 hex digits)")
    pin.add_argument("name", help="the helper's name")
    pin.add_argument("helper", help="the helper file, inside the project root")
    pin.add_argument("--root", required=True, metavar="DIR", help="the project directory")
    run_cmd = commands.add_parser("launch", allow_abbrev=False,
                                  help="run a pinned helper if it still matches its pin")
    run_cmd.add_argument("project_id", help="the project id (64 hex digits)")
    run_cmd.add_argument("name", help="the helper's name")
    run_cmd.add_argument("--root", required=True, metavar="DIR", help="the project directory")
    commands.add_parser("release-approvals", allow_abbrev=False,
                        help="release time: write the approvals shipped for first-party packages")
    return parser


_clean = display.clean


def _target(args):
    given = [value for value in (args.package, args.dir) if value is not None]
    if not all(given):
        raise _Usage("the package path is empty")
    # Same directory means the same place on disk: symlinks and .. are resolved.
    if len(given) == 2 and os.path.realpath(given[0]) != os.path.realpath(given[1]):
        raise _Usage("two different packages were given: %r and --dir %r" % tuple(given))
    return given[0] if given else "."


def _release(distribution, out, err):
    try:
        done = firstparty.release_approvals(distribution)
    except firstparty.ReleaseError as exc:
        err.write("refused: %s\n" % _clean(str(exc)))
        return 1
    if not done.packages:
        out.write("no first-party packages\n")
    else:
        out.write("wrote %d approvals for %d first-party packages\n" % (done.records, done.packages))
    for warning in done.warnings:
        out.write("warning: %s\n" % _clean(warning))
    return 0


def _open_store(store_root, err):
    """Every command first makes sure the guarded store exists, before any check.

    The personal settings are seeded when missing and reported when damaged; a damaged file is
    never overwritten and every checkpoint then stops. Returns ``(store, notes)`` or None.
    """
    try:
        guarded = store.Store(store_root if store_root is not None else store.default_root())
        guarded.ensure()
        return guarded, ["settings: " + problem for problem in settings.initialize(guarded).problems]
    except safefs.SafeFsError as exc:
        err.write("refused: %s\n" % _clean(str(exc)))
        return None


def _project_command(tokens, out, err, store_root, distribution, upgrading=False):
    """Parse and open for ``preview install``, ``preview upgrade`` and ``install``:
    ``(command, guarded)`` or an exit code."""
    try:
        parsed = sources.parse_install(tokens, upgrade=upgrading)
        command = sources.Command(target.choose(parsed.positional, parsed.dir_option),
                                  parsed.packages, parsed.select)
    except (sources.UsageError, target.TargetUsage) as exc:
        err.write("%s\n%s" % (_clean(str(exc)), USAGE))
        return 2
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    guarded, notes = opened
    notes += launch.install_wrapper(guarded, distribution or firstparty.default_distribution())
    for note in notes:
        err.write("warning: %s\n" % _clean(note))
    return command, guarded


def _preview(argv, out, err, store_root, distribution, home=None):
    if len(argv) < 2 or argv[1] not in ("install", "upgrade", "add"):
        err.write("preview takes install, upgrade or add\n%s" % USAGE)
        return 2
    upgrading = argv[1] == "upgrade"
    opened = _project_command(argv[2:], out, err, store_root, distribution, upgrading)
    if isinstance(opened, int):
        return opened
    if argv[1] in ("upgrade", "add"):
        return upgrade.run_preview(opened[1], opened[0], out, err, distribution, mode=argv[1])
    return preview.run(opened[1], opened[0], out, err, distribution, home=home)


def _upgrade(tokens, out, err, store_root, distribution, stdin, mode="upgrade"):
    stdin = stdin if stdin is not None else sys.stdin
    if not upgrade.require_terminal(stdin, out, err, mode):
        return 1
    opened = _project_command(tokens, out, err, store_root, distribution,
                              upgrading=mode == "upgrade")
    if isinstance(opened, int):
        return opened
    return upgrade.run(opened[1], opened[0], stdin, out, err, distribution, mode=mode)


def _install(tokens, out, err, store_root, distribution, stdin, home=None):
    opened = _project_command(tokens, out, err, store_root, distribution)
    if isinstance(opened, int):
        return opened
    return install.run(opened[1], opened[0], stdin if stdin is not None else sys.stdin, out, err,
                       distribution, home=home)


def _acknowledge(tokens, err, out, store_root, stdin):
    try:
        spelling = acknowledge.parse(tokens)
    except sources.UsageError as exc:
        err.write("%s\n%s" % (_clean(str(exc)), USAGE))
        return 2
    stdin = stdin if stdin is not None else sys.stdin
    if not acknowledge.require_terminal(stdin, out, err):
        return 1
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    notes = opened[1] + launch.install_wrapper(opened[0], firstparty.default_distribution())
    for note in notes:
        err.write("warning: %s\n" % _clean(note))
    return acknowledge.run(opened[0], spelling, stdin, out, err)


def _recover(tokens, err, out, store_root, stdin):
    try:
        spelling = recover.parse(tokens)
    except sources.UsageError as exc:
        err.write("%s\n%s" % (_clean(str(exc)), USAGE))
        return 2
    stdin = stdin if stdin is not None else sys.stdin
    if not recover.require_terminal(stdin, out, err):
        return 1
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    notes = opened[1] + launch.install_wrapper(opened[0], firstparty.default_distribution())
    for note in notes:
        err.write("warning: %s\n" % _clean(note))
    return recover.run(opened[0], spelling, stdin, out, err)


def _attach(tokens, out, err, store_root, distribution, home):
    try:
        command = attach.parse(tokens)
    except sources.UsageError as exc:
        err.write("%s\n%s" % (_clean(str(exc)), USAGE))
        return 2
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    guarded, notes = opened
    notes += launch.install_wrapper(guarded, distribution or firstparty.default_distribution())
    for note in notes:
        err.write("warning: %s\n" % _clean(note))
    return attach.run(guarded, command, out, err, distribution, home=home)


def _check(tokens, out, err, store_root, distribution):
    try:
        command = check.parse(tokens)
    except sources.UsageError as exc:
        err.write("%s\n%s" % (_clean(str(exc)), USAGE))
        return 2
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    guarded, notes = opened
    notes += launch.install_wrapper(guarded, distribution or firstparty.default_distribution())
    for note in notes:
        err.write("warning: %s\n" % _clean(note))
    return check.run(guarded, command, out, err)


def _code_work(tokens, out, err, store_root, distribution):
    """``code-work``: the arguments are the helper's and are never parsed as options here."""
    if not dispatch.accepted(tokens):
        err.write(dispatch.USAGE)
        return 2
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    # Only the wrapper is checked; nothing else is printed, so the helper's streams stay clean.
    launch.install_wrapper(opened[0], distribution or firstparty.default_distribution())
    return dispatch.run(opened[0], tokens, err)


def main(argv, out=None, err=None, *, store_root=None, distribution=None, stdin=None, home=None):
    """Run a command. `store_root`, `distribution`, `stdin` and `home` are for tests; the command
    line cannot set them."""
    if out is None and err is None:
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                # A path the terminal's encoding cannot show must not become a traceback.
                stream.reconfigure(errors="backslashreplace")
    out = out or sys.stdout
    err = err or sys.stderr
    # The helper's arguments follow the first `--` and are never parsed as options.
    passthrough = []
    if argv and argv[0] == "launch" and "--" in argv:
        split = argv.index("--")
        argv, passthrough = argv[:split], argv[split + 1:]
    if argv and argv[0] == "code-work":
        return _code_work(argv[1:], out, err, store_root, distribution)
    if argv and argv[0] == "preview":
        return _preview(argv, out, err, store_root, distribution, home)
    if argv and argv[0] == "acknowledge":
        return _acknowledge(argv[1:], err, out, store_root, stdin)
    if argv and argv[0] == "recover":
        return _recover(argv[1:], err, out, store_root, stdin)
    if argv and argv[0] == "attach":
        return _attach(argv[1:], out, err, store_root, distribution, home)
    if argv and argv[0] == "check":
        return _check(argv[1:], out, err, store_root, distribution)
    if argv and argv[0] in ("upgrade", "add"):
        return _upgrade(argv[1:], out, err, store_root, distribution, stdin, argv[0])
    if argv and argv[0] == "install":
        return _install(argv[1:], out, err, store_root, distribution, stdin, home)
    try:
        args = _parser().parse_args(argv)
        if args.command == "launch":
            args.args = passthrough
        if args.command not in ("verify", "release-approvals", "approve", "pin", "launch"):
            raise _Usage("a command is required")
        if args.command in ("pin", "launch") and "" in (args.project_id, args.name, args.root):
            raise _Usage("the project id, name and root may not be empty")
        if args.command == "pin" and not args.helper:
            raise _Usage("the helper path may not be empty")
        if args.command == "approve":
            if (args.package is None) == (args.source is None):
                raise _Usage("give either a package directory or --source, not both and not neither")
            if args.ref is not None and args.source is None:
                raise _Usage("--ref goes with --source")
            if "" in (args.package, args.source, args.ref, args.module):
                raise _Usage("the package, source, ref and module may not be empty")
        path = _target(args) if args.command == "verify" else None
    except _Usage as exc:
        err.write("%s\n%s" % (_clean(str(exc)), USAGE))
        return 2
    except SystemExit as exc:  # --help
        return exc.code if isinstance(exc.code, int) else 2

    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    guarded, notes = opened

    if args.command == "launch":
        # Only the wrapper is checked here; nothing else is printed, so the helper's own
        # streams stay clean.
        launch.install_wrapper(guarded, distribution or firstparty.default_distribution())
        return launch.run(guarded, args.project_id, args.name, args.root, args.args, err)
    notes += launch.install_wrapper(guarded, distribution or firstparty.default_distribution())
    if args.command == "pin":
        for note in notes:
            err.write("warning: %s\n" % _clean(note))
        return pins.run(guarded, args.project_id, args.name, args.helper, args.root,
                        stdin if stdin is not None else sys.stdin, out, err)
    if args.command == "release-approvals":
        return _release(distribution, out, err)
    if args.command == "approve":
        for note in notes:
            err.write("warning: %s\n" % _clean(note))
        return approve.run(guarded, args.package, args.module,
                           stdin if stdin is not None else sys.stdin, out, err, distribution,
                           args.source, args.ref or "HEAD")

    result = verify.verify_package(path, select=args.select,
                                   harness_required=not args.no_harness_required,
                                   first_party=firstparty.is_first_party(path, distribution))
    if result.accepted:
        for module in result.modules:
            out.write("%s/%s %s declaration %s tree %s\n" % (
                module.package, module.name, module.version,
                module.declaration_hash[:12], module.tree_hash[:12]))
        if result.order:
            out.write("install order: %s\n" % " ".join("%s/%s" % key for key in result.order))
    else:
        for problem in result.problems:
            err.write("refused: %s\n" % _clean(str(problem)))
    for warning in notes + list(result.warnings):
        (out if result.accepted else err).write("warning: %s\n" % _clean(warning))
    return 0 if result.accepted else 1

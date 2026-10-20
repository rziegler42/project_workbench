"""The command line: ``python3 -m workbench verify``.

Exit codes: 0 accepted, 1 refused, 2 usage error. The command reads the package and
writes nothing there; every command first creates the guarded store if it is missing.
"""

import argparse
import os
import sys

from . import safefs, store, verify

PROG = "python3 -m workbench"
USAGE = ("usage: python3 -m workbench verify [<package> | --dir <path>] "
         "[--select <module> ...] [--no-harness-required]\n"
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
    return parser


def _clean(text):
    """Escape control characters so nothing read from disk can steer the terminal."""
    return "".join(c if c.isprintable() else repr(c)[1:-1] for c in text)


def _target(args):
    given = [value for value in (args.package, args.dir) if value is not None]
    if not all(given):
        raise _Usage("the package path is empty")
    # Same directory means the same place on disk: symlinks and .. are resolved.
    if len(given) == 2 and os.path.realpath(given[0]) != os.path.realpath(given[1]):
        raise _Usage("two different packages were given: %r and --dir %r" % tuple(given))
    return given[0] if given else "."


def main(argv, out=None, err=None, *, store_root=None):
    """Run a command. `store_root` is for tests; the command line cannot set it."""
    if out is None and err is None:
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                # A path the terminal's encoding cannot show must not become a traceback.
                stream.reconfigure(errors="backslashreplace")
    out = out or sys.stdout
    err = err or sys.stderr
    try:
        args = _parser().parse_args(argv)
        if args.command != "verify":
            raise _Usage("a command is required")
        path = _target(args)
    except _Usage as exc:
        err.write("%s\n%s" % (_clean(str(exc)), USAGE))
        return 2
    except SystemExit as exc:  # --help
        return exc.code if isinstance(exc.code, int) else 2

    # Every command first makes sure the guarded store exists, before any check.
    try:
        store.Store(store_root if store_root is not None else store.default_root()).ensure()
    except safefs.SafeFsError as exc:
        err.write("refused: %s\n" % _clean(str(exc)))
        return 1

    result = verify.verify_package(path, select=args.select,
                                   harness_required=not args.no_harness_required)
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
    for warning in result.warnings:
        (out if result.accepted else err).write("warning: %s\n" % _clean(warning))
    return 0 if result.accepted else 1

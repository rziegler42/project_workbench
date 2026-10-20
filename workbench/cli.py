"""The command line: ``python3 -m workbench verify``.

Exit codes: 0 accepted, 1 refused, 2 usage error. The command reads the package and
writes nothing there; every command first creates the guarded store if it is missing.
"""

import argparse
import os
import sys

from . import approve, display, firstparty, safefs, settings, store, verify

PROG = "python3 -m workbench"
USAGE = ("usage: python3 -m workbench verify [<package> | --dir <path>] "
         "[--select <module> ...] [--no-harness-required]\n"
         "       python3 -m workbench approve (<package> | --source <url> [--ref <ref>]) [--module <name>]\n"
         "                                                    (owner-run, terminal only)\n"
         "       python3 -m workbench release-approvals\n"
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


def main(argv, out=None, err=None, *, store_root=None, distribution=None, stdin=None):
    """Run a command. `store_root`, `distribution` and `stdin` are for tests; the command
    line cannot set them."""
    if out is None and err is None:
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                # A path the terminal's encoding cannot show must not become a traceback.
                stream.reconfigure(errors="backslashreplace")
    out = out or sys.stdout
    err = err or sys.stderr
    try:
        args = _parser().parse_args(argv)
        if args.command not in ("verify", "release-approvals", "approve"):
            raise _Usage("a command is required")
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

    # Every command first makes sure the guarded store exists, before any check.
    # The personal settings are seeded when missing and reported when damaged; a damaged
    # file is never overwritten and every checkpoint then stops.
    try:
        guarded = store.Store(store_root if store_root is not None else store.default_root())
        guarded.ensure()
        notes = ["settings: " + problem for problem in settings.initialize(guarded).problems]
    except safefs.SafeFsError as exc:
        err.write("refused: %s\n" % _clean(str(exc)))
        return 1

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

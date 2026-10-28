"""The command line: ``python3 -m workbench verify``.

Exit codes: 0 accepted, 1 refused, 2 usage error. The command reads the package and
writes nothing there; every command first creates the guarded store if it is missing.
"""

import argparse
import io
import os
import re
import sys

from . import (acknowledge, agent_gate, approvalcmd, approve, attach, check, command_gate, delegation, firstparty,
               gate_hook, harnesses, install, launch, levelrun, levels, pins, planapprovals, preview, recover, rendering,
               rerender, settings, settingscmd, sources, store, target, upgrade, verify)
from . import commands as module_commands
from .wbkit import display, safefs

PROG = "python3 -m workbench"
USAGE = ("usage: python3 -m workbench verify [<package> | --dir <path>] "
         "[--select <module> ...] [--no-harness-required]\n"
         "       python3 -m workbench approve (<package> | --source <url> [--ref <ref>]) [--module <name>]\n"
         "                                                    (owner-run, terminal only)\n"
         "       python3 -m workbench pin <project-id> <name> <helper> --root <dir> [--kit N]   (owner-run, terminal only)\n"
         "       python3 -m workbench launch <project-id> <name> --root <dir> -- <args>\n"
         "       python3 -m workbench run [--provides <capability>] <command> [<argument> ...]\n"
         "       python3 -m workbench release-approvals\n"
         "       python3 -m workbench preview install [<target> | --dir <path>] --package <source> [--ref <ref>] ...\n"
         "                                            [--package ...] --select <module> ...   (read-only)\n"
         "       python3 -m workbench install <same arguments as preview install>   (owner-run, terminal only)\n"
         "       python3 -m workbench adopt <same arguments as preview install>   (owner-run, terminal only)\n"
         "       python3 -m workbench preview adopt <same arguments as preview install>   (read-only;\n"
         "                                            a repository that has content, nothing in it is changed)\n"
         "       python3 -m workbench preview upgrade [<target> | --dir <path>] [--package <source> [--ref <ref>]] ...\n"
         "                                            (read-only; no --select, no download)\n"
         "       python3 -m workbench upgrade <same arguments as preview upgrade>   (owner-run, terminal only)\n"
         "       python3 -m workbench preview rerender [<target> | --dir <path>] [--package <source> [--ref <ref>]] ...\n"
         "       python3 -m workbench rerender <same arguments as preview rerender>   (owner-run, terminal only)\n"
         "       python3 -m workbench preview add [<target> | --dir <path>] --package <source> [--ref <ref>] ...\n"
         "                                        --select <module> ...   (read-only; no download)\n"
         "       python3 -m workbench add <same arguments as preview add>   (owner-run, terminal only)\n"
         "       python3 -m workbench acknowledge [<target> | --dir <path>]   (owner-run, terminal only)\n"
         "       python3 -m workbench recover [<target> | --dir <path>]   (owner-run, terminal only)\n"
         "       python3 -m workbench attach [<target> | --dir <path>] --harness <package>/<module>\n"
         "                                   [--package <source> [--ref <ref>]] ...   (owner-run)\n"
         "       python3 -m workbench check [<target> | --dir <path>]   (read-only)\n"
         "       python3 -m workbench approve-plan <plan>   (owner-run, terminal only)\n"
         "       python3 -m workbench plan-status <plan>   (read-only)\n"
         "       python3 -m workbench delegate-approve-plan <plan>\n"
         "       python3 -m workbench settings   (read-only)\n"
         "       python3 -m workbench gate <harness>   (read-only; the harness's hook runs it)\n"
         "       python3 -m workbench agent-gate <harness> <agent>   (read-only; a confined agent's hook runs it)\n"
         "       python3 -m workbench gate-command <harness>   (read-only; the harness's Bash hook runs it)\n"
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
    pin.add_argument("--kit", type=int, metavar="N", help="run the helper through the kit runner "
                                                         "with this kit API number")
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


def _release(guarded, stdin, distribution, out, err):
    return _unattended_call(guarded, "wb release-approvals", stdin, out, err,
                            lambda: _release_approvals(distribution, out, err))


def _release_approvals(distribution, out, err):
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


def _levelled(guarded, key, terminal_only, stdin, out, err, project_id=None, root=None):
    """``(log, code)`` for an owner-run command whose level the owner may set to ``none`` (``levelrun.route``, read for the
    project the working directory is in). `log` is None at a terminal, and the command goes on as always; at a verified
    ``none`` it is ``log(digest, apply)``, which runs `apply` between the attempt and the outcome. `code` is an exit code
    when the command must stop here. `project_id` and `root` are the project the command acts on, which must be the one the
    level was read for."""
    def refuse(text):
        err.write("refused: %s\n" % _clean(text))
        return None, 1

    try:
        route = levelrun.route(guarded, os.getcwd(), key, stdin, out, terminal_only)
    except levelrun.Refusal as exc:
        return refuse(str(exc) if str(exc) == terminal_only else "%s (%s)" % (terminal_only, exc))
    except OSError as exc:
        return refuse("%s (the working directory cannot be read: %s)" % (terminal_only, exc.strerror or "unknown error"))
    if route.terminal:
        return None, None
    if project_id is not None and project_id != route.project_id:
        return refuse("the project the level was read for is not the project %s; nothing was recorded" % project_id)
    # The root is read as the command spells it (`pins.run` takes its absolute path, `..` collapsed before links are followed),
    # so it must name the project the same way with or without following links.
    if root is not None and not (os.path.abspath(root) == os.path.realpath(root) == os.path.realpath(route.root)):
        return refuse("the project the level was read for is not the one at the root given; nothing was recorded")

    def log(digest, apply):
        return levelrun.apply_logged(guarded, route, key, digest, apply, err, lambda stream, text: refuse(text)[1])

    log.project_id = route.project_id
    return log, None


def _unattended_call(guarded, key, stdin, out, err, call):
    """Run `call()` (the exit code of a command that has no terminal test: ``attach``, ``release-approvals``). Without a
    terminal at a verified ``none`` for the project the working directory is in, the run is logged: the attempt before it and
    the outcome after. Otherwise it goes on exactly as it always did."""
    try:
        route = levelrun.optional(guarded, os.getcwd(), key, stdin, out)
    except OSError:
        route = None
    if route is None:
        return call()

    def refuse(stream, text):
        err.write("refused: %s\n" % _clean(text))
        return 1

    return levelrun.apply_logged(guarded, route, key, "", call, err, refuse)


def _refuse_without_store(store_root, stdin, out, err, terminal_only):
    """True, after refusing, when there is no terminal and no guarded store yet. The level cannot be read from a store that is
    not there, so it reads ``block``, and a refused run must not create the store (it reads and writes nothing)."""
    if approve.is_terminal(stdin) and approve.is_terminal(out):
        return False
    if os.path.lexists(store_root if store_root is not None else store.default_root()):
        return False
    err.write("refused: %s\n" % _clean(terminal_only))
    return True


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


def _preview_rerender(tokens, out, err, store_root, distribution, home=None):
    try:
        command = rerender.parse(tokens)
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
    return rerender.run_preview(guarded, command, out, err, distribution, home=home)


def _rerender(tokens, out, err, store_root, distribution, stdin, home=None):
    try:
        command = rerender.parse(tokens)
    except sources.UsageError as exc:
        err.write("%s\n%s" % (_clean(str(exc)), USAGE))
        return 2
    stdin = stdin if stdin is not None else sys.stdin
    # The key offers `block` only, so there is no level to read: without a terminal it refuses, and a refused run must not
    # create the guarded store.
    if not (approve.is_terminal(stdin) and approve.is_terminal(out)):
        err.write("refused: %s\n" % _clean(rerender.TERMINAL_ONLY))
        return 1
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    guarded, notes = opened
    notes += launch.install_wrapper(guarded, distribution or firstparty.default_distribution())
    for note in notes:
        err.write("warning: %s\n" % _clean(note))
    return rerender.run(guarded, command, stdin, out, err, distribution, home=home)


def _preview(argv, out, err, store_root, distribution, home=None):
    if len(argv) < 2 or argv[1] not in ("install", "adopt", "upgrade", "add", "rerender"):
        err.write("preview takes install, adopt, upgrade, add or rerender\n%s" % USAGE)
        return 2
    if argv[1] == "rerender":
        return _preview_rerender(argv[2:], out, err, store_root, distribution, home)
    upgrading = argv[1] == "upgrade"
    opened = _project_command(argv[2:], out, err, store_root, distribution, upgrading)
    if isinstance(opened, int):
        return opened
    if argv[1] in ("upgrade", "add"):
        return upgrade.run_preview(opened[1], opened[0], out, err, distribution, mode=argv[1])
    return preview.run(opened[1], opened[0], out, err, distribution, home=home,
                       adopt=argv[1] == "adopt")


def _upgrade(tokens, out, err, store_root, distribution, stdin, mode="upgrade"):
    stdin = stdin if stdin is not None else sys.stdin
    if _refuse_without_store(store_root, stdin, out, err, upgrade.terminal_only(mode)):
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


def _adopt(tokens, out, err, store_root, distribution, stdin):
    opened = _project_command(tokens, out, err, store_root, distribution)
    if isinstance(opened, int):
        return opened
    return install.run(opened[1], opened[0], stdin if stdin is not None else sys.stdin, out, err,
                       distribution, adopt=True)


def _acknowledge(tokens, err, out, store_root, stdin):
    try:
        spelling = acknowledge.parse(tokens)
    except sources.UsageError as exc:
        err.write("%s\n%s" % (_clean(str(exc)), USAGE))
        return 2
    stdin = stdin if stdin is not None else sys.stdin
    if _refuse_without_store(store_root, stdin, out, err, acknowledge.TERMINAL_ONLY):
        return 1
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    log, code = _levelled(opened[0], levels.CHECKPOINT_ACKNOWLEDGE, acknowledge.TERMINAL_ONLY, stdin, out, err)
    if code is not None:
        return code
    notes = opened[1] + launch.install_wrapper(opened[0], firstparty.default_distribution())
    for note in notes:
        err.write("warning: %s\n" % _clean(note))
    return acknowledge.run(opened[0], spelling, stdin, out, err, log=log)


def _recover(tokens, err, out, store_root, stdin):
    try:
        spelling = recover.parse(tokens)
    except sources.UsageError as exc:
        err.write("%s\n%s" % (_clean(str(exc)), USAGE))
        return 2
    stdin = stdin if stdin is not None else sys.stdin
    if _refuse_without_store(store_root, stdin, out, err, recover.TERMINAL_ONLY):
        return 1
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    log, code = _levelled(opened[0], "wb recover", recover.TERMINAL_ONLY, stdin, out, err)
    if code is not None:
        return code
    notes = opened[1] + launch.install_wrapper(opened[0], firstparty.default_distribution())
    for note in notes:
        err.write("warning: %s\n" % _clean(note))
    return recover.run(opened[0], spelling, stdin, out, err, log=log)


def _attach(tokens, out, err, store_root, distribution, home, stdin=None):
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
    return _unattended_call(guarded, "wb attach", stdin if stdin is not None else sys.stdin, out, err,
                            lambda: attach.run(guarded, command, out, err, distribution, home=home))


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
    return check.run(guarded, command, out, err, distribution)


def _run(tokens, out, err, store_root, distribution):
    """``run``: the arguments are the helper's and are never parsed as options here."""
    if module_commands.split(tokens) is None:
        err.write(module_commands.USAGE)
        return 2
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    # Only the wrapper is checked; nothing else is printed, so the helper's streams stay clean.
    launch.install_wrapper(opened[0], distribution or firstparty.default_distribution())
    return module_commands.run(opened[0], tokens, err)


def _plan_command(name, tokens, out, err, store_root, distribution, stdin):
    """``approve-plan``, ``plan-status`` and ``delegate-approve-plan``: one argument, never parsed as an option here."""
    grammar = {"approve-plan": planapprovals.approve_arguments, "plan-status": planapprovals.status_arguments}.get(
        name, planapprovals.one_argument)
    if grammar(tokens) is None:
        err.write({"approve-plan": planapprovals.APPROVE_USAGE, "plan-status": planapprovals.STATUS_USAGE}.get(
            name, delegation.USAGE))
        return 2
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    # Only the wrapper is checked; nothing else is printed, so a status line stays alone on its stream.
    launch.install_wrapper(opened[0], distribution or firstparty.default_distribution())
    if name == "plan-status":
        return planapprovals.plan_status(opened[0], tokens, out, err)
    if name == "delegate-approve-plan":
        return delegation.delegate_approve_plan(opened[0], tokens, out, err)
    return planapprovals.approve_plan(opened[0], tokens, stdin if stdin is not None else sys.stdin, out, err)


def _settings(tokens, out, err, store_root, distribution):
    """``settings``: no argument. Only the wrapper is checked; nothing else is printed, so standard output
    holds only the settings lines."""
    if tokens:
        err.write(settingscmd.USAGE)
        return 2
    opened = _open_store(store_root, err)
    if opened is None:
        return 1
    launch.install_wrapper(opened[0], distribution or firstparty.default_distribution())
    return settingscmd.run(opened[0], tokens, out, err)


def _gate(tokens, err, store_root, distribution, stdin):
    """``gate <harness>``: the harness's hook command. Exit 0 allows, 2 refuses with one line on standard error and
    nothing else, and a usage error is 2 as well, because 2 is the only code the harness takes for a block."""
    if len(tokens) != 1 or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", tokens[0]):
        err.write(gate_hook.USAGE)
        return 2

    def prepare():
        said = io.StringIO()
        opened = _open_store(store_root, said)
        if opened is None:
            raise gate_hook.Refusal(said.getvalue().strip().removeprefix("refused: ") or "the store cannot be used")
        launch.install_wrapper(opened[0], distribution or firstparty.default_distribution())
        facts = harnesses.known(distribution).get(tokens[0])
        if not facts or not facts["hook_targets"]:
            raise gate_hook.Refusal("%s is not a known harness whose layout declares the tools its hook covers"
                                    % _clean(tokens[0]))
        return opened[0], dict(facts["hook_targets"])

    return gate_hook.run(stdin if stdin is not None else sys.stdin, err, prepare)


def _gate_command(tokens, err, store_root, distribution, stdin):
    """``gate-command <harness>``: the harness's Bash hook command. Exit 0 allows, 2 refuses with one line on standard
    error and nothing else, and a usage error is 2 as well, as for ``gate``."""
    if len(tokens) != 1 or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", tokens[0]):
        err.write(command_gate.USAGE)
        return 2

    def prepare(cwd):
        facts = harnesses.known(distribution).get(tokens[0])
        gate = facts["command_gate"] if facts else ()
        if not gate:
            raise gate_hook.Refusal("%s is not a known harness whose layout describes the command gate" % _clean(tokens[0]))
        said = io.StringIO()
        opened = _open_store(store_root, said)
        if opened is None:
            raise gate_hook.Refusal(said.getvalue().strip().removeprefix("refused: ") or "the store cannot be used")
        launch.install_wrapper(opened[0], distribution or firstparty.default_distribution())
        try:
            table, _, ident = rendering.current_table(opened[0], cwd)
        except (approvalcmd.ApprovalError, levels.RegistryError) as exc:
            raise gate_hook.Refusal(str(exc))
        # The harness file keeps the ask rule and no deny until it is attached again, so what was rendered is guarded even
        # if the table has since gone back to block.
        record = rendering.read(opened[0], ident)
        if record is not None:
            for key, rule in record["keys"].items():
                if rule in command_gate.RELAXED and table.get(key) not in command_gate.RELAXED:
                    table[key] = rule
        return gate[0], gate[1], table, os.path.join(os.path.realpath(opened[0].root), "bin", "wb")

    return command_gate.run(stdin if stdin is not None else sys.stdin, err, prepare)


def _agent_gate(tokens, err, distribution, stdin):
    """``agent-gate <harness> <agent>``: a confined agent's hook command. Exit 0 allows, 2 refuses with one line on
    standard error and nothing else, and a usage error is 2 as well, as for ``gate``. It opens no store: the limits
    come from the installed module and the layout of the harness."""
    name = r"[a-z0-9][a-z0-9_-]{0,63}"
    if len(tokens) != 2 or not all(re.fullmatch(name, token) for token in tokens):
        err.write(agent_gate.USAGE)
        return 2
    return agent_gate.run(stdin if stdin is not None else sys.stdin, err,
                          lambda: agent_gate.known(distribution, tokens[0]), tokens[1])


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
    if argv and argv[0] == "run":
        return _run(argv[1:], out, err, store_root, distribution)
    if argv and argv[0] == "gate":
        return _gate(argv[1:], err, store_root, distribution, stdin)
    if argv and argv[0] == "agent-gate":
        return _agent_gate(argv[1:], err, distribution, stdin)
    if argv and argv[0] == "gate-command":
        return _gate_command(argv[1:], err, store_root, distribution, stdin)
    if argv and argv[0] == "settings":
        return _settings(argv[1:], out, err, store_root, distribution)
    if argv and argv[0] in ("approve-plan", "plan-status", "delegate-approve-plan"):
        return _plan_command(argv[0], argv[1:], out, err, store_root, distribution, stdin)
    if argv and argv[0] == "preview":
        return _preview(argv, out, err, store_root, distribution, home)
    if argv and argv[0] == "acknowledge":
        return _acknowledge(argv[1:], err, out, store_root, stdin)
    if argv and argv[0] == "recover":
        return _recover(argv[1:], err, out, store_root, stdin)
    if argv and argv[0] == "attach":
        return _attach(argv[1:], out, err, store_root, distribution, home, stdin)
    if argv and argv[0] == "check":
        return _check(argv[1:], out, err, store_root, distribution)
    if argv and argv[0] == "rerender":
        return _rerender(argv[1:], out, err, store_root, distribution, stdin, home)
    if argv and argv[0] in ("upgrade", "add"):
        return _upgrade(argv[1:], out, err, store_root, distribution, stdin, argv[0])
    if argv and argv[0] == "adopt":
        return _adopt(argv[1:], out, err, store_root, distribution, stdin)
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
        reason = module_commands.launch_refusal(guarded, args.project_id, args.name, args.root, args.args,
                                                stdin if stdin is not None else sys.stdin, sys.stdout)
        if reason:
            err.write("refused: %s\n" % _clean(reason))
            return 1
        return launch.run(guarded, args.project_id, args.name, args.root, args.args, err)
    notes += launch.install_wrapper(guarded, distribution or firstparty.default_distribution())
    stdin = stdin if stdin is not None else sys.stdin
    if args.command == "pin":
        for note in notes:
            err.write("warning: %s\n" % _clean(note))
        log, code = _levelled(guarded, "wb pin", pins.TERMINAL_ONLY, stdin, out, err, args.project_id,
                               args.root)
        if code is not None:
            return code
        return pins.run(guarded, args.project_id, args.name, args.helper, args.root, stdin, out, err, kit=args.kit,
                        log=log)
    if args.command == "release-approvals":
        return _release(guarded, stdin if stdin is not None else sys.stdin, distribution, out, err)
    if args.command == "approve":
        for note in notes:
            err.write("warning: %s\n" % _clean(note))
        log, code = _levelled(guarded, "wb approve", approve.TERMINAL_ONLY, stdin, out, err)
        if code is not None:
            return code
        return approve.run(guarded, args.package, args.module, stdin, out, err, distribution,
                           args.source, args.ref or "HEAD", log=log)

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

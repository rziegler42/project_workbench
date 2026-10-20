"""The owner-run ``approve`` command: record an approval of a package or of one module.

The owner runs this from a terminal. The agent's command permissions will deny it (a
harness renders that rule later); the checks here are friction, not the barrier:

* It refuses unless standard input and standard output are both terminals. The test is on
  the file descriptors (``os.isatty``), not on an environment variable or a flag.
* It verifies the package first and refuses on any problem, recording nothing.
* It prints the request (``request.py``), rendered only from objects the verification itself
  produced, and asks the owner to type the first twelve
  characters of the tree hash they were shown: the package's for a package, the module's
  for ``--module``. Anything else cancels and records nothing. There is no ``--yes``.
* Just before writing it verifies the package again and compares every hash with what was
  shown. A package that changed while the owner was reading it is refused.
* It writes only into the guarded store. It reads the package and writes nothing there.

An approval that is already on file keeps its first record (``approvals.py``). The command
therefore reports the record that is on file, not the approver and time it was about to
write.

Limits, on purpose: the typed text is a guard against a mistake, not authentication. The
first twelve characters are printed in the request and by ``verify``, and a process that
opens its own pseudo-terminal passes the terminal test. What stops an agent is the deny rule
a harness renders for this command, and the deny rule on the guarded store.

The approver recorded is the account name from the operating system's user database, not
from an environment variable, and is text only: it grants nothing.
"""

import os

from . import approvals, display, firstparty, request, safefs, verify

try:
    import pwd
except ImportError:  # not POSIX; the safe filesystem layer refuses to run there anyway
    pwd = None

CONFIRM_CHARS = 12
MAX_ANSWER = 200


def _is_terminal(stream):
    try:
        return os.isatty(stream.fileno())
    except (AttributeError, OSError, ValueError):
        return False


def approver_name():
    try:
        name = pwd.getpwuid(os.getuid()).pw_name
    except (AttributeError, KeyError, OSError):
        return "owner"
    return name if name and len(name) <= 64 and name.isprintable() else "owner"


def _refuse(err, text):
    err.write("refused: %s\n" % display.clean(text))
    return 1


def _snapshot(result):
    return (tuple((i.name, i.declaration_hash, i.tree_hash) for i in result.packages),
            tuple((m.package, m.name, m.declaration_hash, m.tree_hash) for m in result.modules))


def _verify(path, distribution):
    return verify.verify_package(path, harness_required=False,
                                 first_party=firstparty.is_first_party(path, distribution))


class _Refused(Exception):
    """The request could not be built; the message is shown to the owner."""


def build(path, module_name, distribution=None):
    """Verify the package and build what the owner is shown.

    Returns ``(result, text, token, what)``. The text is rendered only from objects the
    verification itself produced (the parsed package and modules, the hashes and the execute
    bits from the one tree walk that was hashed), so what is shown cannot differ from what
    is recorded because a file changed between two reads.
    """
    result = _verify(path, distribution)
    if not result.accepted:
        raise _Refused("\n".join("refused: %s" % display.clean(str(p)) for p in result.problems)
                       + "\nnothing was recorded")
    (info,) = result.packages
    verified = {m.name: m for m in result.modules}
    source = os.path.abspath(path)
    if module_name is None:
        entries = [(verified[name].module, verified[name], set(verified[name].executable))
                   for name in sorted(verified)]
        text = request.render_package(info.name, info.package.version, info, entries, source)
        return result, text, info.tree_hash[:CONFIRM_CHARS], "package"
    if module_name not in verified:
        raise _Refused("refused: no module %s in package %s" % (
            display.clean(repr(module_name)), display.clean(info.name)))
    chosen = verified[module_name]
    text = request.render_module(info.name, chosen.module, chosen, source, set(chosen.executable))
    return result, text, chosen.tree_hash[:CONFIRM_CHARS], "module"


def run(store, path, module_name, stdin, stdout, err, distribution=None):
    """Approve the package at `path`, or one of its modules. Returns the exit code."""
    if not (_is_terminal(stdin) and _is_terminal(stdout)):
        return _refuse(err, "approval is owner-run: standard input and output must both be "
                            "terminals. Run this command yourself, from your own terminal.")
    try:
        result, text, token, what = build(path, module_name, distribution)
    except _Refused as exc:
        err.write("%s\n" % exc)
        return 1

    stdout.write(text + "\n\n")
    stdout.write("To approve this %s, type the first %d characters of the tree hash shown "
                 "above and press Enter.\nAnything else cancels and records nothing.\n> "
                 % (what, CONFIRM_CHARS))
    stdout.flush()
    answer = stdin.readline(MAX_ANSWER)
    if answer.strip() != token:
        stdout.write("cancelled: nothing was recorded\n")
        return 1

    again = _verify(path, distribution)
    if not again.accepted or _snapshot(again) != _snapshot(result):
        return _refuse(err, "the package changed while it was shown; nothing was recorded")

    (info,) = result.packages
    return _record(store, info, {m.name: m for m in result.modules}, module_name, stdout, err)


def _existing(store, kind, subject, declaration_hash, tree_hash):
    return approvals.check(store, kind, subject, declaration_hash, tree_hash).approved


def _record(store, info, hashes, module_name, stdout, err):
    who, now = approver_name(), approvals.utc_now()
    done = []
    try:
        names = [module_name] if module_name is not None else sorted(hashes)
        for name in names:
            item = hashes[name]
            subject = "%s/%s" % (info.name, name)
            was = _existing(store, "module", subject, item.declaration_hash, item.tree_hash)
            done.append(("module", was, approvals.record_module(
                store, subject, item.declaration_hash, item.tree_hash, who, now)))
        if module_name is None:
            was = _existing(store, "package", info.name, info.declaration_hash, info.tree_hash)
            done.append(("package", was, approvals.record_package(
                store, info.name, info.declaration_hash, info.tree_hash,
                [(name, item.declaration_hash, item.tree_hash) for name, item in hashes.items()],
                who, now)))
    except (approvals.ApprovalError, safefs.SafeFsError) as exc:
        written = ", ".join("%s %s" % (kind, record.subject) for kind, was, record in done
                            if not was) or "none"
        return _refuse(err, "%s; the approval was not completed. Records written by this run: %s"
                       % (exc, written))
    for kind, was, record in done:
        if was:
            stdout.write("already approved %s %s (by %s on %s); the earlier record is kept\n" % (
                kind, display.clean(record.subject), display.clean(record.approver),
                display.clean(record.time)))
        else:
            stdout.write("approved %s %s\n" % (kind, display.clean(record.subject)))
    return 0

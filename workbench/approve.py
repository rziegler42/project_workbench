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

With ``--source`` the package is downloaded first and everything comes from the cached copy.
The package record stores the resolved commit as provenance. What is approved is the content,
bound by the tree hash, so a ref that later moves to different content is not approved, while
the same content reached by another commit is the same approval (the first record, and its
pin, is kept). A module approved with ``--module`` has no package record and no pin. A copy
that is declined or fails verification stays in the cache, and this plan removes none.

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

from . import approvals, fetch, firstparty, request, verify
from .wbkit import display, safefs

try:
    import pwd
except ImportError:  # not POSIX; the safe filesystem layer refuses to run there anyway
    pwd = None

CONFIRM_CHARS = 12
MAX_ANSWER = 200
TERMINAL_ONLY = ("approval is owner-run: standard input and output must both be terminals. Run this command "
                 "yourself, from your own terminal.")


def is_terminal(stream):
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


def build(path, module_name, distribution=None, origin=None):
    """Verify the package and build what the owner is shown.

    `origin` is the text shown as where the package came from; it defaults to the path.

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
    source = origin or os.path.abspath(path)
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


def run(store, path, module_name, stdin, stdout, err, distribution=None, source=None,
        ref="HEAD", log=None):
    """Approve the package at `path`, or one of its modules. Returns the exit code.

    `log`, given by the command line when the owner has set the level of ``wb approve`` to ``none`` for this project
    (``levelrun.route``), is ``log(digest, apply) -> exit code``: the command then runs without a terminal and asks
    nothing, and `log` runs `apply` (the records) between an attempt and an outcome. An approval already on file
    changes nothing and is not logged.

    With `source` (a URL or a local repository) the package is first downloaded inertly into
    the guarded store's cache (``fetch.py``), and the request, the typed hash and the record
    all come from that cached copy. The first approval pins the resolved commit.
    """
    if log is None and not (is_terminal(stdin) and is_terminal(stdout)):
        return _refuse(err, TERMINAL_ONLY)
    fetched = origin = None
    if source is not None:
        stdout.write("Downloading %s (ref %s) into the cache. Nothing is executed or "
                     "installed.\n" % (display.ascii_text(source)[:200], display.ascii_text(ref)[:80]))
        stdout.flush()
        try:
            fetched = fetch.fetch(store, source, ref)
        except fetch.FetchError as exc:
            return _refuse(err, "the download failed: %s; nothing was recorded" % exc)
        path = fetched.path
        origin = "%s @ %s (ref %s); downloaded copy: %s" % (fetched.source, fetched.commit,
                                                           fetched.ref, fetched.path)

    def kept():
        if fetched is not None:
            stdout.write("The downloaded copy is kept at %s so it can be read again.\n"
                         % display.clean(fetched.path))

    try:
        result, text, token, what = build(path, module_name, distribution, origin)
    except _Refused as exc:
        err.write("%s\n" % exc)
        if fetched is not None:
            err.write("The downloaded copy is kept at %s\n" % display.clean(fetched.path))
        return 1

    stdout.write(text + "\n\n")
    if log is not None:
        stdout.write("The level of wb approve is none here, so nothing is asked: it is recorded now.\n")
        stdout.flush()
    else:
        stdout.write("To approve this %s, type the first %d characters of the tree hash shown "
                     "above and press Enter.\nAnything else cancels and records nothing.\n> "
                     % (what, CONFIRM_CHARS))
        stdout.flush()
        answer = stdin.readline(MAX_ANSWER)
        if answer.strip() != token:
            stdout.write("cancelled: nothing was recorded\n")
            kept()
            return 1

    again = _verify(path, distribution)
    if not again.accepted or _snapshot(again) != _snapshot(result):
        kept()
        return _refuse(err, "the package changed while it was shown; nothing was recorded")

    (info,) = result.packages
    hashes = {m.name: m for m in result.modules}
    commit = fetched.commit if fetched is not None else None

    def apply():
        return _record(store, info, hashes, module_name, stdout, err, commit)

    if log is None or _on_file(store, info, hashes, module_name):
        return apply()
    return log(info.tree_hash if module_name is None else hashes[module_name].tree_hash, apply)


def _on_file(store, info, hashes, module_name):
    """True when every record this approval would write is already on file, so it would change nothing."""
    try:
        names = [module_name] if module_name is not None else sorted(hashes)
        return all(_existing(store, "module", "%s/%s" % (info.name, name), hashes[name].declaration_hash,
                             hashes[name].tree_hash) for name in names) and (
            module_name is not None or _existing(store, "package", info.name, info.declaration_hash, info.tree_hash))
    except (approvals.ApprovalError, safefs.SafeFsError):
        return False


def _existing(store, kind, subject, declaration_hash, tree_hash):
    return approvals.check(store, kind, subject, declaration_hash, tree_hash).approved


def _record(store, info, hashes, module_name, stdout, err, commit=None):
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
                who, now, commit)))
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
        if kind == "package":
            if record.commit and commit and record.commit != commit:
                stdout.write("kept the earlier pin %s; this download was commit %s, which has "
                             "the same content\n" % (display.clean(record.commit), display.clean(commit)))
            elif record.commit:
                stdout.write("pinned commit %s\n" % display.clean(record.commit))
            elif commit:
                stdout.write("no commit is pinned: the earlier approval of this content came from "
                             "a local directory, and the content hash is what is approved\n")
    return 0

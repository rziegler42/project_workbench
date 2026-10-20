"""What the owner-run write commands share: the typed digest and the report of a failed write.

``install`` was the first of them; ``upgrade``, ``add`` and ``acknowledge`` ask the same
question and report a stopped write the same way, so the code is written once:

* the owner types the first twelve characters of a digest. Typed-ahead input is discarded
  first and the answer is bounded, so a pasted or queued line cannot answer for the owner;
* a write that fails after it began lists what was written and what was not, and says the
  marker is left in place.

The typed text is friction, not authentication; what stops an agent is the deny rule a harness
renders for each command and for the guarded store.
"""

from . import display, projectfs

CONFIRM_CHARS = 12
MAX_ANSWER = 200
LISTED = 40            # paths listed per group in a failure report

try:
    import termios
except ImportError:  # not POSIX; the safe filesystem layer refuses to run there anyway
    termios = None


class Progress:
    """What has happened, for the report when something fails."""

    def __init__(self):
        self.started = False
        self.writer = None
        self.plan = None
        self.stored = []


def discard_typed_ahead(stream):
    if termios is None:
        return
    try:
        termios.tcflush(stream.fileno(), termios.TCIFLUSH)
    except (termios.error, AttributeError, OSError, ValueError):
        pass


def token_of(digest):
    """The text the owner types for a digest."""
    return digest[:CONFIRM_CHARS]


def typed_matches(stdin, digest):
    """Discard typed-ahead input, read one bounded answer and compare it with the token."""
    discard_typed_ahead(stdin)
    return stdin.readline(MAX_ANSWER).strip() == token_of(digest)


def _group(title, items, err):
    if not items:
        return
    err.write("%s:\n" % title)
    for item in items[:LISTED]:
        err.write("  %s\n" % display.ascii_text(item))
    if len(items) > LISTED:
        err.write("  and %d more\n" % (len(items) - LISTED))


def report_failure(progress, cause, err, what="install", hint=""):
    writer, plan = progress.writer, progress.plan
    written = list(writer.written)
    if writer.made_target:
        written.insert(0, "./ (the target directory)")
    planned = []
    for action in plan.actions:
        if action.kind in ("create-file", "create-dir"):
            planned.append(action.path + ("/" if action.kind == "create-dir" else ""))
        elif action.kind == "git-init":
            planned.append(".git/")
    have = set(writer.written)
    missing = [path for path in planned if path not in have]
    missing += [path for path, _ in plan.store_writes if path not in progress.stored]
    err.write("failed: %s\n" % display.ascii_text(cause))
    _group("written", written, err)
    _group("not written", missing, err)
    if len(missing) and not [path for path in planned if path not in have]:
        err.write("the project's files are written but its guarded store entries are not\n")
    err.write("the %s is unfinished: %s is left in place, so this directory is not "
              "accepted as a project\n" % (what, projectfs.MARKER))
    if hint:
        err.write("%s\n" % hint)

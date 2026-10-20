"""``wb install``: write a new project, after the owner types the plan's digest.

Owner-run and terminal-only, like ``approve``. The order is fixed by
``docs/specs/installer-interface.md``:

* standard input and output must be terminals, before anything is fetched;
* the target is opened and fully checked first, so a refused target causes no fetch and no
  cache write; only then is each URL source downloaded, inertly, into the cache (the one use
  of the network);
* the same ``preview.prepare`` as ``preview install`` builds the plan, which is printed with
  its digest; the owner types the first twelve characters of it. Typed-ahead input is
  discarded, the answer is bounded, and anything else writes nothing;
* after the answer the target is checked again and the plan is rebuilt from the packages as
  they are now; a different digest is refused. The files written are the bytes of the plan
  that was shown;
* writing creates ``.workbench/local/incomplete`` first and removes it last. Writing is not
  atomic: a failure stops at once, lists what was written and what was not, leaves the marker
  and exits 3.

The typed text is friction, not authentication; what stops an agent is the deny rule a harness
renders for this command and for the guarded store.
"""

import os
import shutil
import stat

from . import (__version__, approve, display, fetch, installplan, manifest, preview, projectfs,
               safefs, sources, target)

CONFIRM_CHARS = 12
MAX_ANSWER = 200
LISTED = 40            # paths listed per group in a failure report

try:
    import termios
except ImportError:  # not POSIX; the safe filesystem layer refuses to run there anyway
    termios = None


class _Progress:
    """What has happened, for the report when something fails."""

    def __init__(self):
        self.started = False
        self.writer = None
        self.plan = None
        self.stored = []


def _text(value):
    return display.clean(str(value))


def _discard_typed_ahead(stream):
    if termios is None:
        return
    try:
        termios.tcflush(stream.fileno(), termios.TCIFLUSH)
    except (termios.error, AttributeError, OSError, ValueError):
        pass


# --- the sources --------------------------------------------------------------------------


def _resolve(guarded, packages, out, fetched):
    """Resolve each source; a URL or repository is downloaded into the inert cache.

    The path of each download is added to `fetched` as it is made."""
    resolved = []
    for source, ref in packages:
        if sources.local_package(source) is not None:
            resolved.append(sources.resolve_cached(guarded, source, ref))
            continue
        wanted = ref or "HEAD"
        shown = display.ascii_text(installplan.public_source(source))[:200]
        out.write("Downloading %s (ref %s) into the cache. Nothing is executed or installed.\n"
                  % (shown, display.ascii_text(wanted)[:80]))
        out.flush()
        try:
            got = fetch.fetch(guarded, source, wanted)
        except fetch.FetchError as exc:
            raise preview.Refused(["the download failed: %s" % exc])
        fetched.append(got.path)
        resolved.append(sources.Resolved(got.path, got.source, got.ref, got.commit, False))
    return resolved


# --- git ----------------------------------------------------------------------------------


def _git_init(held, writer):
    """Write the empty ``.git`` of the plan. Git is not run: a program given a path in the target
    could be sent elsewhere by a link planted after the check; ``mkdir`` and held descriptors
    cannot."""
    writer.create_git(installplan.GIT_SKELETON)


# --- checks before the write ----------------------------------------------------------------


def _still_the_same(held):
    """The held target is the same place, in the same state, as when it was classified."""
    held.recheck()
    if held.state in ("new-empty", "new-git"):
        names = sorted(os.listdir(held.fd))
        if names != ([] if held.state == "new-empty" else [".git"]):
            raise target.TargetError("refused: the target changed: its contents are no longer "
                                     "those that were shown: %s" % held.path)
        if held.state == "new-git" and not stat.S_ISDIR(
                os.stat(".git", dir_fd=held.fd, follow_symlinks=False).st_mode):
            raise target.TargetError("refused: .git is not a real directory: %s" % held.path)


# --- the write ----------------------------------------------------------------------------


def _write(guarded, held, plan, progress):
    writer = progress.writer = projectfs.Writer(held)
    progress.started = True
    for action in plan.actions:
        if action.kind == "make-target":
            writer.make_target()
        elif action.kind == "git-init":
            _git_init(held, writer)
        elif action.kind == "create-dir":
            writer.create_dir(action.path)
        else:
            writer.create_file(action.path, action.data, executable=action.mode == "x")
    for path, data in plan.store_writes:
        if guarded.kind(path) is not None:
            raise safefs.SafeFsError("the guarded store already holds %s" % path)
        guarded.write(path, data)
        progress.stored.append(path)
    writer.remove_marker()


def _group(title, items, err):
    if not items:
        return
    err.write("%s:\n" % title)
    for item in items[:LISTED]:
        err.write("  %s\n" % display.ascii_text(item))
    if len(items) > LISTED:
        err.write("  and %d more\n" % (len(items) - LISTED))


def _report_failure(held, progress, cause, err):
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
    err.write("the install is unfinished: %s is left in place, so this directory is not "
              "accepted as a project\n" % projectfs.MARKER)


def _finish(held, progress, out):
    done = [path for path in progress.writer.written if path != projectfs.MARKER]
    try:
        out.write("wrote %d paths in %s\nnothing was committed\n"
                  % (len(done), display.ascii_text(held.path)))
        out.write("harness not attached: attach is not built yet\n")
        out.flush()
    except BrokenPipeError:
        pass


# --- the command ---------------------------------------------------------------------------


def _refuse(err, text):
    err.write("refused: %s\n" % display.clean(text))
    return 1


def _run(guarded, command, stdin, out, err, distribution, seed, version, which, progress):
    try:
        with target.open_target(command.target, guarded.root) as held:
            fetched = []
            try:
                resolved = _resolve(guarded, command.packages, out, fetched)
                seed = seed or manifest.new_seed()
                version = version or __version__
                plan, warnings = preview.prepare(guarded, held, resolved, command.select,
                                                 distribution, seed, version, which)
            except sources.SourceError as exc:
                raise preview.Refused([str(exc)])
            except preview.Refused as exc:
                for path in fetched:
                    out.write("The downloaded copy is kept at %s\n" % _text(path))
                raise
            progress.plan = plan
            for warning in warnings:
                err.write("warning: %s\n" % _text(warning))
            if held.state == "new-git":
                err.write("warning: the existing .git is used as it is; no remote is recorded\n")
            out.write(installplan.render(plan, held.path, show_digest=True))
            token = plan.digest[:CONFIRM_CHARS]
            out.write("\nTo install, type the first %d characters of the digest shown above and "
                      "press Enter.\nAnything else cancels and writes nothing.\n> "
                      % CONFIRM_CHARS)
            out.flush()
            _discard_typed_ahead(stdin)
            if stdin.readline(MAX_ANSWER).strip() != token:
                out.write("cancelled: nothing was written\n")
                return 1
            try:
                _still_the_same(held)
                again, _ = preview.prepare(guarded, held, resolved, command.select, distribution,
                                           seed, version, which)
            except preview.Refused as exc:
                raise preview.Refused(["the packages changed while the plan was shown: %s; "
                                       "nothing was written" % "; ".join(exc.lines)])
            if again.digest != plan.digest:
                return _refuse(err, "the plan changed while it was shown; nothing was written")
            try:
                _write(guarded, held, plan, progress)
            except (Exception, KeyboardInterrupt) as exc:
                cause = "interrupted" if isinstance(exc, KeyboardInterrupt) else str(exc)
                _report_failure(held, progress, cause, err)
                return 3
            _finish(held, progress, out)
            return 0
    except target.TargetError as exc:
        return _refuse(err, display.clean(str(exc)).replace("refused: ", "", 1))
    except preview.Refused as exc:
        for line in exc.lines:
            err.write("refused: %s\n" % display.clean(line))
        return 1
    except safefs.SafeFsError as exc:
        return _refuse(err, str(exc))


def run(guarded, command, stdin, out, err, distribution=None, seed=None, version=None,
        which=shutil.which):
    """Install into a new target after the owner types the digest. Returns the exit code:
    0 done, 1 refused or cancelled, 3 stopped after writing, 130 interrupted before writing."""
    if not (approve.is_terminal(stdin) and approve.is_terminal(out)):
        return _refuse(err, "install is owner-run: standard input and output must both be "
                            "terminals. Run this command yourself, from your own terminal; "
                            "`preview install` shows the same plan without writing.")
    progress = _Progress()
    try:
        return _run(guarded, command, stdin, out, err, distribution, seed, version, which,
                    progress)
    except KeyboardInterrupt:
        try:
            out.write("\ncancelled: nothing was written\n")
        except OSError:
            pass
        return 130
    except BrokenPipeError:
        return 3 if progress.started else 1

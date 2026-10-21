"""``wb recover``: clear the marker an unfinished ``install``, ``upgrade`` or ``add`` left.

The marker ``.workbench/local/incomplete`` holds a record of the plan that was being written
(``unfinished``). This command is the owner's way past the refusal every other command gives for a
marked project. It is owner-run and terminal-only, like ``acknowledge``:

* standard input and output must be terminals, before anything is read;
* the project and the guarded store are examined as ``unfinished.examine`` does, and the examination
  is shown with what would be removed. The record is unauthenticated text and is said to be;
* the owner types the first twelve characters of the digest of what was shown, which covers the
  marker's bytes, the examination, what would be removed and the target's identity. Typed-ahead
  input is discarded, the answer is bounded, and anything else removes nothing;
* after the answer the project is examined again; a different digest is refused.

The marker is cleared only in these states, and every other is refused with the paths to deal with:

* files ``before`` and store ``none``: nothing the plan wrote is there. The marker goes, and so does
  each directory the plan recorded as created, if it is empty, deepest first, with ``rmdir`` only;
* files ``after`` and store ``all``: the plan was carried out and only the marker was left. The
  marker goes;
* ``upgrade`` and ``add`` only, files ``after`` and store ``none``: the files are written and the
  old baselines are still in the store, so the project differs from them and ``wb acknowledge``
  lists exactly the written paths. The marker goes. An ``install`` in that state has no old
  baselines to fall back on and is refused: the files have to be put back and the install run again.

Nothing else is written or removed: no file is restored or deleted, the store is not touched, no
directory that holds anything is removed and the target directory itself is never removed. The
typed text is friction, not authentication; what stops an agent is the deny rule a harness renders
for this command and for the guarded store.
"""

from . import (acknowledge, approve, confirm, installplan, projectfs, safefs, target,
               unfinished)
from .wbkit import display

MAX_LISTED = 500

_LOCAL = ".workbench/local"
_BEFORE, _AFTER, _UNSTORED = "before", "after", "unstored"

parse = acknowledge.parse


class Refused(Exception):
    """The command stops with these lines, each printed as ``refused: ...``."""

    def __init__(self, lines):
        Exception.__init__(self, "; ".join(lines))
        self.lines = list(lines)


def _depth(path):
    return path.count("/")


def judge(found):
    """``(outcome, lines)``: the outcome is ``before``, ``after`` or ``unstored`` when the marker
    may be cleared, else None and the lines say why not."""
    if found.record is None:
        return None, unfinished.render(found, hint=False)
    record = found.record
    state = (found.files, found.store)
    if state == ("before", "none"):
        return _BEFORE, []
    if state == ("after", "all"):
        return _AFTER, []
    lines = unfinished.render(found, hint=False)
    if found.files == "after" and found.store in ("none", "partial"):
        if state == ("after", "none") and record.command in ("upgrade", "add"):
            return _UNSTORED, []
        if record.command == "install":
            lines.append("an install that wrote its files but not all of its store cannot be "
                         "completed: put the project back as it was before the install (remove "
                         "the files it wrote), run `wb recover` again, then install again")
    return None, lines


def _removals(found):
    """The steps that clear a project whose files are all in the state before the plan: each
    recorded directory that is empty, deepest first; the marker; and, when the plan made
    ``.workbench``, the local directory and then ``.workbench`` itself."""
    state = {i.path: i.state for i in found.items if i.kind == "dir"}
    dirs = sorted((d for d in found.record.dirs if d != ".workbench" and state.get(d) == "empty"),
                  key=lambda d: (-_depth(d), d))
    steps = [("dir", d) for d in dirs] + [("marker", projectfs.MARKER)]
    if ".workbench" in found.record.dirs:
        steps += [("dir", _LOCAL), ("dir", ".workbench")]
    return steps


class Review:
    """What the owner is shown: the examination and the steps that would clear the marker."""

    def __init__(self, found, outcome, removals, identity):
        self.found = found
        self.outcome = outcome
        self.removals = removals
        self.identity = identity
        record = found.record
        self.fields = {
            "command": "recover",
            "target": {"device": identity[0], "inode": identity[1]},
            "marker": unfinished.fingerprint(record),
            "outcome": outcome,
            "files": found.files,
            "store": found.store,
            "items": [[i.kind, i.path, i.state, i.detail] for i in found.items],
            "removals": [[kind, path] for kind, path in removals],
        }
        self.digest = installplan.digest_of(self.fields)


def examine(guarded, held):
    """Examine the marked project and return a ``Review``; raises ``Refused``."""
    if held.state != "existing":
        raise Refused(["the target is not an existing project; there is nothing to recover"])
    writer = projectfs.Writer(held)
    try:
        found = unfinished.examine(writer, guarded.root)
        outcome, lines = judge(found)
        removals = [("marker", projectfs.MARKER)]
        if outcome == _BEFORE:
            removals = _removals(found)
            if ".workbench" in found.record.dirs and writer.dir_holds(_LOCAL, ignore=("incomplete",)):
                outcome, lines = None, unfinished.render(found, hint=False) + [
                    "  holds %s (it holds more than the marker)" % _LOCAL]
    except (safefs.SafeFsError, OSError) as exc:
        raise Refused([str(exc)])
    if outcome is None:
        raise Refused(lines)
    if len(removals) > MAX_LISTED:
        raise Refused(["%d directories would be removed, more than the %d that can be reviewed "
                       "here; deal with the project by hand" % (len(removals), MAX_LISTED)])
    return Review(found, outcome, removals, held.identity)


def render(review, target_path):
    found = review.found
    lines = ["target: %s" % display.ascii_text(target_path), "command: recover"]
    lines += unfinished.render(found, hint=False)
    if review.outcome == _BEFORE:
        lines.append("the project holds nothing the unfinished %s wrote; no file is restored or "
                     "deleted" % found.record.command)
    elif review.outcome == _AFTER:
        lines.append("the unfinished %s was carried out; only its marker was left"
                     % found.record.command)
    else:
        lines.append("the files are written and the store holds the old baselines, so the project "
                     "differs from them; after this, `wb acknowledge` lists exactly the written "
                     "paths for you to accept")
    lines.append("this removes:")
    for kind, path in review.removals[:MAX_LISTED]:
        lines.append("  %s %s" % ("the marker" if kind == "marker" else "the empty directory",
                                  display.ascii_text(path)))
    lines.append("nothing else is written or removed")
    lines.append("digest: %s" % review.digest)
    return "\n".join(lines) + "\n"


def _refuse(err, text):
    err.write("refused: %s\n" % display.clean(text))
    return 1


def _clear(writer, review, out, err):
    """Carry out the steps in order; the marker goes after the directories that do not contain
    it, so a directory that cannot be removed leaves the marker and the record in place."""
    steps = review.removals
    done = []
    try:
        for kind, path in steps:
            if kind == "marker":
                try:
                    writer.remove_marker()
                except projectfs.MarkerMissing:
                    pass        # already gone: the aim is met
            else:
                writer.remove_empty_dir(path)
            done.append((kind, path))
    except (Exception, KeyboardInterrupt) as exc:
        cause = "interrupted" if isinstance(exc, KeyboardInterrupt) else str(exc)
        err.write("failed: %s\n" % display.ascii_text(cause))
        left = steps[len(done):]
        err.write("removed so far: %s\n" % (", ".join(display.ascii_text(p) for _, p in done)
                                             or "nothing"))
        err.write("not removed: %s\n" % ", ".join(display.ascii_text(p) for _, p in left[:20]))
        if any(kind == "marker" for kind, _ in done) or not writer.target.has_incomplete_marker():
            err.write("the marker is gone; remove what is left yourself\n")
        else:
            err.write("the marker is still there; run `wb recover` again\n")
        return 3
    if review.outcome == _UNSTORED:
        out.write("cleared the marker; run `wb acknowledge` to accept the written paths\n")
    else:
        out.write("cleared the marker\n")
    return 0


def _run(guarded, spelling, stdin, out, err):
    try:
        with target.open_target(spelling, guarded.root, marked=True) as held:
            if not held.has_incomplete_marker():
                out.write("no unfinished write here; nothing to recover\n")
                return 0
            review = examine(guarded, held)
            out.write(render(review, held.path))
            out.write("\nTo clear the marker, type the first %d characters of the digest shown "
                      "above and press Enter.\nAnything else cancels and removes nothing.\n> "
                      % confirm.CONFIRM_CHARS)
            out.flush()
            if not confirm.typed_matches(stdin, review.digest):
                out.write("cancelled: nothing was removed\n")
                return 1
            held.recheck()
            again = examine(guarded, held)
            if again.digest != review.digest:
                return _refuse(err, "the project changed while the list was shown; nothing was "
                                    "removed")
            return _clear(projectfs.Writer(held), again, out, err)
    except Refused as exc:
        for index, line in enumerate(exc.lines):
            err.write(("refused: %s\n" if not line.startswith("  ") or not index else "%s\n")
                      % display.clean(line))
        return 1
    except target.TargetError as exc:
        return target.write_refusal(err, exc)
    except safefs.SafeFsError as exc:
        return _refuse(err, str(exc))


def require_terminal(stdin, out, err):
    """True when both streams are terminals; otherwise print the refusal and return False."""
    if approve.is_terminal(stdin) and approve.is_terminal(out):
        return True
    _refuse(err, "recover is owner-run: standard input and output must both be terminals. Run "
                 "this command yourself, from your own terminal.")
    return False


def run(guarded, spelling, stdin, out, err):
    """Clear the marker after the owner types the digest. Returns the exit code: 0 done or
    nothing to recover, 1 refused or cancelled, 3 removal failed, 130 interrupted."""
    if not require_terminal(stdin, out, err):
        return 1
    try:
        return _run(guarded, spelling, stdin, out, err)
    except KeyboardInterrupt:
        try:
            out.write("\ncancelled: nothing was removed\n")
        except OSError:
            pass
        return 130
    except BrokenPipeError:
        return 1

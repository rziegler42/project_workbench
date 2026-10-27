"""``wb recover``: clear the marker an unfinished ``install``, ``adopt``, ``upgrade`` or ``add`` left.

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
  baselines to fall back on and is refused: the files have to be put back and the install run again;
* ``upgrade`` and ``add`` only, files ``after`` and a store that is part old and part new, each entry
  holding exactly the old or exactly the new content (the baselines and the pins are two entries): the
  marker goes. If the baselines are the old ones, ``wb acknowledge`` lists the written paths; if the
  pins are the old ones, the launcher refuses the helpers the plan replaced until the owner pins them
  again with ``wb pin``. An entry that holds other content is refused.

Nothing else is written or removed: no file is restored or deleted, the store is not touched, no
directory that holds anything is removed and the target directory itself is never removed. The
typed text is friction, not authentication; what stops an agent is the deny rule a harness renders
for this command and for the guarded store.

When the owner has set the key ``wb recover`` to ``none`` and the rendering holds (the command line reads it,
``levelrun.route``), the command also runs without a terminal and asks nothing: it prints the same examination and digest,
examines again, and writes the level log's attempt just before the first removal and its outcome after. The level is the
owner's setting for the project the command is run from. A marker that names a project (an unfinished ``upgrade`` or ``add``)
must name that one; the marker of a failed ``install`` or ``adopt`` names none and is in a new directory, so the target is not
compared. The record is unauthenticated text, so this stops a mistake and not a forged marker. A run with no marker writes no entry.
"""

from . import acknowledge, approve, confirm, installplan, projectfs, target, unfinished
from .wbkit import display, safefs

MAX_LISTED = 500
TERMINAL_ONLY = ("recover is owner-run: standard input and output must both be terminals. Run this command yourself, "
                 "from your own terminal.")

_LOCAL = ".workbench/local"
_BEFORE, _AFTER, _UNSTORED, _PARTIAL = "before", "after", "unstored", "partial"

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
    if found.files == "after" and found.store == "partial" and record.command in ("upgrade", "add"):
        # Only a real mix: no store item at all (a record that names none) is no evidence of one.
        if {i.state for i in found.items if i.kind == "store"} == {"before", "after"}:
            return _PARTIAL, []
    lines = unfinished.render(found, hint=False)
    if found.files == "after" and found.store in ("none", "partial"):
        if state == ("after", "none") and record.command in ("upgrade", "add"):
            return _UNSTORED, []
        if record.command in ("install", "adopt"):
            lines.append("an %(c)s that wrote its files but not all of its store cannot be "
                         "completed: put the project back as it was before the %(c)s (remove "
                         "the files it created%(k)s), run `wb recover` again, then %(c)s again"
                         % {"c": record.command,
                            "k": ", never one it kept" if record.command == "adopt" else ""})
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


def _old_entries(found):
    """The store entries the examination found still holding their old content, as their file names."""
    return sorted(i.path.rsplit("/", 1)[-1] for i in found.items
                  if i.kind == "store" and i.state == "before")


def _partial_lines(found):
    old = _old_entries(found)
    lines = ["the files are written and the store is part old and part new; it still holds the old %s"
             % " and the old ".join(old)]
    if "baselines" in old:
        lines.append("the project differs from the old baselines; after this, `wb acknowledge` lists "
                     "exactly the written paths for you to accept")
    if "pins" in old:
        lines.append("the pins are the old ones, so the launcher refuses each helper the unfinished "
                     "command replaced until you pin it again with `wb pin`")
    return lines


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
    elif review.outcome == _PARTIAL:
        lines += _partial_lines(found)
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
    elif review.outcome == _PARTIAL:
        old = _old_entries(review.found)
        out.write("cleared the marker;%s%s\n" % (
            " run `wb acknowledge` to accept the written paths;" if "baselines" in old else "",
            " run `wb pin` for each helper the unfinished command replaced" if "pins" in old else ""))
    else:
        out.write("cleared the marker\n")
    return 0


def _run(guarded, spelling, stdin, out, err, log=None):
    try:
        with target.open_target(spelling, guarded.root, marked=True) as held:
            if not held.has_incomplete_marker():
                out.write("no unfinished write here; nothing to recover\n")
                return 0
            review = examine(guarded, held)
            named = review.found.record.project
            if log is not None and named is not None and named != log.project_id:
                return _refuse(err, "the marker names another project than the one the level was read for; nothing was "
                                    "removed")
            out.write(render(review, held.path))
            if log is not None:
                out.write("\nThe level of wb recover is none here, so nothing is asked: the marker is cleared now.\n")
                out.flush()
            else:
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

            def apply():
                return _clear(projectfs.Writer(held), again, out, err)

            return apply() if log is None else log(again.digest, apply)
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
    _refuse(err, TERMINAL_ONLY)
    return False


def run(guarded, spelling, stdin, out, err, log=None):
    """Clear the marker after the owner types the digest. Returns the exit code: 0 done or
    nothing to recover, 1 refused or cancelled, 3 removal failed, 130 interrupted.

    `log`, given by the command line when the level of ``wb recover`` is ``none`` here, is ``log(digest, apply)``: the command
    then runs without a terminal and asks nothing."""
    if log is None and not require_terminal(stdin, out, err):
        return 1
    try:
        return _run(guarded, spelling, stdin, out, err, log)
    except KeyboardInterrupt:
        try:
            out.write("\ncancelled: nothing was removed\n")
        except OSError:
            pass
        return 130
    except BrokenPipeError:
        return 1

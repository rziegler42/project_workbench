"""``wb acknowledge``: accept the changes made to a project since the owner last accepted it.

``upgrade`` and ``add`` refuse a project whose manifest, or a file under ``.workbench/`` outside
``local/``, differs from the hash last acknowledged (``acknowledgement.differences``). This
command is the owner's way past that refusal. It is owner-run and terminal-only, like
``install``:

* standard input and output must be terminals, before anything is read;
* the project is read as ``upgrade`` reads it, with every path that has a baseline in scope, so
  nothing ``upgrade`` would refuse can be left out; every difference is listed with its path, baseline hash, current hash and
  kind, with a summary of the parsed manifest. The store keeps hashes and not the old bytes, so
  this is a hash list and not a line diff;
* the owner types the first twelve characters of the digest of that list. Typed-ahead input is
  discarded, the answer is bounded, and anything else writes nothing;
* after the answer the project is read again; a different digest is refused. Then the baselines
  of exactly the listed paths are replaced, in one atomic replacement of the store entry, and each
  pin that was holding the bytes last acknowledged for a listed path moves to the bytes now there.
  A pin held at other bytes, for another path, or typed by the owner (it records no declaration) is
  not moved, and no module declaration is read: the differences may include the declarations themselves. Nothing in the project is written.

A path that is a link, a directory or another kind of file where a file is expected has no hash to
accept, so it cannot be acknowledged; the owner deals with it first. The typed text is friction,
not authentication; what stops an agent is the deny rule a harness renders for this command and
for the guarded store.

When the owner has set the checkpoint ``acknowledge-first-tier`` to ``none`` and the rendering holds (the command line reads it,
``levelrun.route``), the command also runs without a terminal and asks nothing: it prints the same list and digest, examines
the project again, and writes the level log's attempt just before the baselines and its outcome after. The project listed must
be the one the level was read for.
"""

import hashlib

from . import (__version__, acknowledgement, approvals, approve, confirm, installed, installplan, manifest,
               pins, projectfs, sources, target)
from .wbkit import display, safefs

MANIFEST = acknowledgement.MANIFEST
MAX_LISTED = 500          # a longer list cannot be reviewed; it is refused, not truncated

_STORE = "projects/%s/baselines"
TERMINAL_ONLY = ("acknowledge is owner-run: standard input and output must both be terminals. Run this command yourself, "
                 "from your own terminal; `preview upgrade` shows what is different without writing.")


class Refused(Exception):
    """The command stops with these lines, each printed as ``refused: ...``."""

    def __init__(self, lines):
        Exception.__init__(self, "; ".join(lines))
        self.lines = list(lines)


def parse(tokens):
    """The target spelling from ``[<target> | --dir <path>]``; a ``sources.UsageError`` otherwise."""
    positional = dir_option = None
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "":
            raise sources.UsageError("an argument may not be empty")
        if token == "--dir":
            if dir_option is not None:
                raise sources.UsageError("--dir was given twice")
            if index + 1 >= len(tokens) or tokens[index + 1].startswith("-"):
                raise sources.UsageError("--dir needs a value")
            dir_option = tokens[index + 1]
            index += 2
        elif token.startswith("-"):
            raise sources.UsageError("unknown option %s" % token)
        else:
            if positional is not None:
                raise sources.UsageError("more than one target was given")
            positional = token
            index += 1
    try:
        return target.choose(positional, dir_option)
    except target.TargetUsage as exc:
        raise sources.UsageError(str(exc))


def _sha(data):
    return hashlib.sha256(data).hexdigest()


class Review:
    """What the owner is shown: the differences and the baselines that would result."""

    def __init__(self, existing, project, store_hash, found, after, identity, held_pins=None,
                 moved=(), pins_hash=None):
        self.existing = existing
        self.project = project
        self.found = found
        self.after = after
        self.store_hash = store_hash
        self.identity = identity
        self.held_pins = held_pins or {}
        self.moved = list(moved)
        self.pins_hash = pins_hash
        self.fields = {
            "command": "acknowledge",
            "target": {"device": identity[0], "inode": identity[1]},
            "project": project,
            "workbench": existing.document["workbench"],
            "manifest": existing.manifest_hash,
            "baselines_before": store_hash,
            "differences": [{"path": d.path, "kind": d.kind, "baseline": d.baseline,
                             "current": d.current} for d in found],
            "baselines_after": after,
            "pins_before": pins_hash,
            "pins_moved": [{"name": new.name, "path": new.path, "from": old.sha256, "to": new.sha256,
                            "kit": new.kit} for old, new in self.moved],
        }
        self.digest = installplan.digest_of(self.fields)

    @property
    def store_bytes(self):
        return installplan.json_store({"baselines": self.after, "format": acknowledgement.FORMAT})

    @property
    def pins_bytes(self):
        """The pins file after the moves, or None when no pin moves."""
        if not self.moved:
            return None
        return pins.serialize(dict(self.held_pins, **{new.name: new for _, new in self.moved}))


def _moves(held_pins, found, now):
    """``[(old pin, new pin)]``: each pin that holds the bytes last acknowledged for a path that now
    holds other bytes moves to them, under the pin's own name, path, kit and declaration. A pin the
    owner typed has no declaration, and acknowledging an edit is not permission to run it."""
    current = {d.path: d for d in found if d.current is not None and d.baseline is not None}
    moved = []
    for name in sorted(held_pins):
        old = held_pins[name]
        item = current.get(old.path)
        if item is not None and old.sha256 == item.baseline and old.declaration is not None:
            moved.append((old, pins.Pin(name, old.path, item.current, "workbench acknowledge", now,
                                        old.kit, old.declaration)))
    return moved


def examine(guarded, held, version, now=None):
    """Read the project and its baselines and return a ``Review``; raises ``Refused``. `now` is the
    time any moved pin records, fixed once by the caller."""
    if held.state != "existing":
        raise Refused(["the target is not an existing project; use install"])
    writer = projectfs.Writer(held)
    try:
        existing = installed.read(writer, version)
        project = manifest.project_id(existing.document["seed"])
        baselines = acknowledgement.read_baselines(guarded, project)
        acknowledgement.check_known(baselines, acknowledgement.read_seen(guarded, project),
                                    held.path)
        # Every baselined path, not only .workbench/: an upgrade also refuses an edited file it
        # would write a block into (AGENTS.md), and this command must be able to clear that.
        found = acknowledgement.differences(writer, baselines, writes=sorted(baselines))
        store_hash = _sha(guarded.read(_STORE % project))
        held_pins = pins.load(guarded, project)
        pins_hash = _pins_hash(guarded, project)
    except (installed.InstalledError, acknowledgement.AcknowledgementError,
            manifest.ManifestError, safefs.SafeFsError, pins.PinError) as exc:
        raise Refused([str(exc)])
    if len(found) > MAX_LISTED:
        raise Refused(["%d paths differ, more than the %d that can be reviewed here; deal with "
                       "the project by hand first" % (len(found), MAX_LISTED)])
    stuck = [d for d in found if d.reason]
    if stuck:
        lines = ["these paths cannot be acknowledged, because they are not regular files or their "
                 "names cannot be accepted:"]
        lines += ["  %s (%s)" % (display.ascii_text(d.path)[:120], d.reason) for d in stuck[:20]]
        lines.append("  put a regular file back, or remove the path yourself, then run this again")
        raise Refused(lines)
    after = dict(baselines)
    for item in found:
        if item.current is None:
            del after[item.path]
        else:
            after[item.path] = item.current
    # The summary shown comes from the read of the manifest above and the baseline written from
    # the read in `differences`; they must be the same bytes, or the owner accepts a manifest
    # other than the one summarised.
    if after.get(MANIFEST) != existing.manifest_hash:
        raise Refused(["the manifest changed while it was read; nothing was done"])
    moved = _moves(held_pins, found, approvals.utc_now() if now is None else now)
    return Review(existing, project, store_hash, found, after, held.identity, held_pins, moved,
                  pins_hash)


def render(review, target_path):
    document = review.existing.document
    lines = ["target: %s" % display.ascii_text(target_path),
             "command: acknowledge",
             "project: %s" % review.project,
             "manifest: sha256 %s" % review.existing.manifest_hash,
             "recorded by workbench %s; base tree %s" % (
                 display.ascii_text(document["workbench"]), document["base"]),
             "packages:"]
    for package in document["packages"]:
        lines.append("  %s from %s ref %s commit %s tree %s" % (
            display.ascii_text(package["name"]), display.ascii_text(package["source"])[:200],
            display.ascii_text(package["ref"] or "(none)")[:80],
            package["commit"] or "(none)", package["tree"]))
        for module in package["modules"]:
            lines.append("    %s %s declaration %s tree %s" % (
                display.ascii_text(module["name"]), display.ascii_text(module["version"]),
                module["declaration"], module["tree"]))
    lines.append("files recorded: %d entries" % len(document["files"]))
    for item in document["files"]:
        lines.append("  %s %s%s sha256 %s" % (
            display.ascii_text(item["path"]), item["class"],
            (" block %s slot %s" % (display.ascii_text(item["block"]), display.ascii_text(
                item["slot"]))) if "block" in item else "", item["hash"]))
    lines.append("differences from what was last acknowledged: %d" % len(review.found))
    for item in review.found:
        lines.append("  %s %s" % (item.kind, display.ascii_text(item.path)))
        lines.append("    baseline %s" % (item.baseline or "(none)"))
        lines.append("    current  %s" % (item.current or "(none)"))
    for old, new in review.moved:
        lines.append("  moves the pin %s: %s from sha256 %s to sha256 %s" % (
            display.ascii_text(new.name), display.ascii_text(new.path), old.sha256[:12],
            new.sha256[:12]))
    lines.append("accepting replaces the baselines of exactly these %d paths%s; nothing in the "
                 "project is written" % (len(review.found), (
                     " and moves %d pin%s, so the launcher runs the bytes now there"
                     % (len(review.moved), "" if len(review.moved) == 1 else "s")) if review.moved else ""))
    lines.append("digest: %s" % review.digest)
    return "\n".join(lines) + "\n"


def _refuse(err, text):
    err.write("refused: %s\n" % display.clean(text))
    return 1


def _stored(guarded, project):
    try:
        return _sha(guarded.read(_STORE % project))
    except safefs.SafeFsError:
        return None


def _pins_hash(guarded, project):
    """The hash of the project's pins file, or None when there is none."""
    rel = "projects/%s/pins" % project
    return None if guarded.kind(rel) is None else _sha(guarded.read(rel))


def _run(guarded, spelling, stdin, out, err, version, log=None):
    try:
        with target.open_target(spelling, guarded.root) as held:
            now = approvals.utc_now()
            review = examine(guarded, held, version, now)
            if not review.found:
                out.write("nothing to acknowledge\n")
                return 0
            if log is not None and review.project != log.project_id:
                return _refuse(err, "the project the level was read for is not the project being acknowledged; nothing was "
                                    "written")
            out.write(render(review, held.path))
            if log is not None:
                out.write("\nThe level of acknowledge-first-tier is none here, so nothing is asked: it is acknowledged now.\n")
                out.flush()
            else:
                out.write("\nTo acknowledge these changes, type the first %d characters of the digest "
                          "shown above and press Enter.\nAnything else cancels and writes nothing.\n> "
                          % confirm.CONFIRM_CHARS)
                out.flush()
                if not confirm.typed_matches(stdin, review.digest):
                    out.write("cancelled: nothing was written\n")
                    return 1
            held.recheck()
            again = examine(guarded, held, version, now)
            if again.digest != review.digest:
                return _refuse(err, "the project changed while the list was shown; nothing was "
                                    "written")

            def apply():
                try:
                    guarded.write(_STORE % review.project, review.store_bytes)
                    if review.pins_bytes is not None:
                        guarded.write("projects/%s/pins" % review.project, review.pins_bytes)
                except (Exception, KeyboardInterrupt) as exc:
                    cause = "interrupted" if isinstance(exc, KeyboardInterrupt) else str(exc)
                    kept = (_stored(guarded, review.project) == review.store_hash
                            and _pins_hash(guarded, review.project) == review.pins_hash)
                    err.write("failed: %s\n%s\n" % (display.ascii_text(cause), (
                        "the baselines were not changed" if kept else
                        "the baselines or the pins may have been replaced; run `wb preview upgrade` to see")))
                    return 3
                out.write("acknowledged %d paths%s; the project was not touched\n" % (
                    len(review.found), (" and moved %d pin%s" % (len(review.moved), "" if len(review.moved) == 1 else "s"))
                    if review.moved else ""))
                return 0

            return apply() if log is None else log(review.digest, apply)
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


def run(guarded, spelling, stdin, out, err, version=None, log=None):
    """Acknowledge the differences after the owner types the digest. Returns the exit code:
    0 done or nothing to do, 1 refused or cancelled, 3 failed while writing, 130 interrupted.

    `log`, given by the command line when the level of ``acknowledge-first-tier`` is ``none`` here, is ``log(digest, apply)``
    with a ``project_id``: the command then runs without a terminal and asks nothing."""
    if log is None and not require_terminal(stdin, out, err):
        return 1
    try:
        return _run(guarded, spelling, stdin, out, err, version or __version__, log)
    except KeyboardInterrupt:
        try:
            out.write("\ncancelled: nothing was written\n")
        except OSError:
            pass
        return 130
    except BrokenPipeError:
        return 1

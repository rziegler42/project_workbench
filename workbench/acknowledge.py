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
  of exactly the listed paths are replaced, in one atomic replacement of the store entry. Nothing
  in the project is written.

A path that is a link, a directory or another kind of file where a file is expected has no hash to
accept, so it cannot be acknowledged; the owner deals with it first. The typed text is friction,
not authentication; what stops an agent is the deny rule a harness renders for this command and
for the guarded store.
"""

import hashlib

from . import (__version__, acknowledgement, approve, confirm, display, installed, installplan,
               manifest, projectfs, safefs, sources, target)

MANIFEST = acknowledgement.MANIFEST
MAX_LISTED = 500          # a longer list cannot be reviewed; it is refused, not truncated

_STORE = "projects/%s/baselines"


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

    def __init__(self, existing, project, store_hash, found, after, identity):
        self.existing = existing
        self.project = project
        self.found = found
        self.after = after
        self.store_hash = store_hash
        self.identity = identity
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
        }
        self.digest = installplan.digest_of(self.fields)

    @property
    def store_bytes(self):
        return installplan.json_store({"baselines": self.after, "format": acknowledgement.FORMAT})


def examine(guarded, held, version):
    """Read the project and its baselines and return a ``Review``; raises ``Refused``."""
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
    except (installed.InstalledError, acknowledgement.AcknowledgementError,
            manifest.ManifestError, safefs.SafeFsError) as exc:
        raise Refused([str(exc)])
    if len(found) > MAX_LISTED:
        raise Refused(["%d paths differ, more than the %d that can be reviewed here; deal with "
                       "the project by hand first" % (len(found), MAX_LISTED)])
    stuck = [d for d in found if d.reason]
    if stuck:
        lines = ["these paths cannot be acknowledged, because they are not regular files:"]
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
    return Review(existing, project, store_hash, found, after, held.identity)


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
    lines.append("accepting replaces the baselines of exactly these %d paths; nothing in the "
                 "project is written" % len(review.found))
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


def _run(guarded, spelling, stdin, out, err, version):
    try:
        with target.open_target(spelling, guarded.root) as held:
            review = examine(guarded, held, version)
            if not review.found:
                out.write("nothing to acknowledge\n")
                return 0
            out.write(render(review, held.path))
            out.write("\nTo acknowledge these changes, type the first %d characters of the digest "
                      "shown above and press Enter.\nAnything else cancels and writes nothing.\n> "
                      % confirm.CONFIRM_CHARS)
            out.flush()
            if not confirm.typed_matches(stdin, review.digest):
                out.write("cancelled: nothing was written\n")
                return 1
            held.recheck()
            again = examine(guarded, held, version)
            if again.digest != review.digest:
                return _refuse(err, "the project changed while the list was shown; nothing was "
                                    "written")
            try:
                guarded.write(_STORE % review.project, review.store_bytes)
            except (Exception, KeyboardInterrupt) as exc:
                cause = "interrupted" if isinstance(exc, KeyboardInterrupt) else str(exc)
                kept = _stored(guarded, review.project) == review.store_hash
                err.write("failed: %s\n%s\n" % (display.ascii_text(cause), (
                    "the baselines were not changed" if kept else
                    "the baselines may have been replaced; run `wb preview upgrade` to see")))
                return 3
            out.write("acknowledged %d paths; the project was not touched\n" % len(review.found))
            return 0
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
    _refuse(err, "acknowledge is owner-run: standard input and output must both be terminals. "
                 "Run this command yourself, from your own terminal; `preview upgrade` shows "
                 "what is different without writing.")
    return False


def run(guarded, spelling, stdin, out, err, version=None):
    """Acknowledge the differences after the owner types the digest. Returns the exit code:
    0 done or nothing to do, 1 refused or cancelled, 3 failed while writing, 130 interrupted."""
    if not require_terminal(stdin, out, err):
        return 1
    try:
        return _run(guarded, spelling, stdin, out, err, version or __version__)
    except KeyboardInterrupt:
        try:
            out.write("\ncancelled: nothing was written\n")
        except OSError:
            pass
        return 130
    except BrokenPipeError:
        return 1

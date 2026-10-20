"""Inert download: bring a package into the guarded store's cache as data only.

The owner cannot judge a package without seeing it, so a package is first downloaded where
nothing can run it and nothing can write it into a project (``docs/specs/trust-and-approval.md``).
``fetch`` does that with git, and never checks anything out:

* The ref is fetched into a private bare repository in a fresh temporary directory outside
  the store, created with an empty template so it has no hooks, and with ``core.hooksPath``
  pointed at an empty directory. Every ``GIT_*`` variable is dropped from the environment,
  the user's and the system's git configuration are ignored, prompts are off, only the
  ``file``, ``https`` and ``ssh`` transports are allowed, and incoming objects are checked.
  No tags and no submodules are fetched.
* The tree is then listed (``git ls-tree``) and the whole listing is checked before any
  content is read: every entry must be a regular file (mode 100644 or 100755), so a symbolic
  link or a submodule refuses the download; every path must pass the path validator; names
  that collide ignoring case are refused; and the file count, each file's size and the total
  are limited (``MAX_FILES``, ``MAX_FILE_BYTES``, ``MAX_TOTAL_BYTES``).
* The files are read with ``git cat-file`` and checked against the listing, then written
  with the safe writer into a staging directory in the cache and moved into place with one
  rename. Files get mode 0644, or 0755 when git recorded the execute bit; nothing else of the
  mode is kept. The temporary repository is then removed, so
  the cache holds data and no repository. On any failure nothing is left in the cache.

A cache directory is never reused: every fetch makes ``cache/<id>/`` with the files under
``package/`` and a ``fetch.json`` (source, ref, resolved commit, counts) beside it, outside the
package so it does not change the package's tree hash.

Every git command runs in its own process group with its output read in chunks and capped, a
timeout, and a limit on the size of any file it writes (``_file_limit``). On a timeout or an
excess, git and everything it started are killed. A tree can share subtrees, so its listing is
read incrementally and git is stopped once it passes what ``MAX_FILES`` allows. The fetch uses
``--depth 1`` and needs git 2.32 or newer (for ``GIT_CONFIG_GLOBAL``); a depth-limited fetch
of a commit id that the server does not advertise can fail on servers that refuse it.

What this does not do: it does not defend against a flaw in git's own handling of objects or
the network transport; a process killed outright (``kill -9``) can leave its temporary
directory behind; it does not verify who runs the server; and an ``ssh`` source uses the
owner's ssh configuration and keys, so it can reach whatever that configuration reaches. The
removal of the temporary and staging directories uses the standard library's descriptor-based
``shutil.rmtree`` on directories this module created.
"""

import collections
import json
import os
import pathlib
import re
import select
import shutil
import signal
import subprocess
import tempfile
import time
import urllib.parse
import uuid

from . import approvals, display, safefs

MAX_FILES = 2048
MAX_FILE_BYTES = safefs.MAX_FILE_BYTES          # 16 MiB
MAX_TOTAL_BYTES = 64 * 1024 * 1024
FETCH_TIMEOUT = 300
GIT_TIMEOUT = 60
MAX_SOURCE_CHARS = 2000
LISTING_RECORD_BYTES = 1200   # a record is a mode, an id, a size and a path of at most 512 bytes
REGULAR_MODES = (b"100644", b"100755")
SCHEMES = ("https", "ssh", "file")

_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/@+-]{0,199}\Z")
_HEX = re.compile(r"^([0-9a-f]{40}|[0-9a-f]{64})\Z")
_LISTING = re.compile(rb"^([0-7]{6}) ([a-z]+) ([0-9a-f]{40,64}) +(\d+|-)\t(.+)\Z", re.S)

Fetched = collections.namedtuple("Fetched", "id path commit source ref files bytes")
Entry = collections.namedtuple("Entry", "path mode oid size")


class FetchError(Exception):
    """The download was refused or failed; nothing was left in the cache."""


# --- the source and the ref -----------------------------------------------------


def normalize_source(source):
    """Return the URL git will be given, or raise FetchError.

    Accepted: an ``https://`` URL without credentials, an ``ssh://`` URL, a ``file://`` URL,
    or a path to a local directory (made absolute and turned into a ``file://`` URL).
    Everything else is refused, including other transports (``ext::``, ``git://``, plain
    ``http://``), scp-style ``host:path``, and anything that starts with ``-`` or holds
    whitespace or control characters.
    """
    if not isinstance(source, str) or not source or len(source) > MAX_SOURCE_CHARS:
        raise FetchError("the source must be a non-empty string of at most %d characters"
                         % MAX_SOURCE_CHARS)
    if source.startswith("-") or not source.isprintable() or any(c.isspace() for c in source):
        raise FetchError("the source may not start with '-' or hold whitespace or control "
                         "characters: %s" % display.ascii_text(source)[:80])
    if "://" in source:
        try:
            parts = urllib.parse.urlsplit(source)
            scheme = parts.scheme.lower()
            if scheme not in SCHEMES:
                raise FetchError("the source scheme %s is not allowed (https, ssh or file)"
                                 % display.ascii_text(scheme)[:20])
            if scheme == "https" and (parts.username is not None or parts.password is not None):
                raise FetchError("an https source may not carry credentials in the URL")
            if scheme == "ssh" and re.search(r"[?#]", source.partition("://")[2].partition("/")[0]):
                raise FetchError("an ssh source may not hold ? or # before its path")
            if scheme != "file" and not parts.hostname:
                raise FetchError("the source has no host")
            if parts.hostname and (parts.hostname.startswith("-") or not parts.hostname.isascii()):
                raise FetchError("the source host is not valid")
        except ValueError:
            raise FetchError("the source is not a valid URL: %s" % display.ascii_text(source)[:80])
        return source
    if ":" in source and not source.startswith(("/", "./", "../")):
        raise FetchError("the source %s is not a URL (https://, ssh://, file://) or a local path"
                         % display.ascii_text(source)[:80])
    path = os.path.abspath(source)
    if not os.path.isdir(path):
        raise FetchError("the local source is not a directory: %s" % display.ascii_text(path)[:200])
    return pathlib.Path(path).as_uri()


def check_ref(ref):
    if not isinstance(ref, str) or not _REF.match(ref) or ".." in ref or ref.endswith(("/", ".lock")):
        raise FetchError("the ref must be a branch, tag or commit name of letters, digits and "
                         "._/@+-, not starting with '-': %s" % display.ascii_text(str(ref))[:80])
    return ref


# --- the listing ----------------------------------------------------------------


def parse_listing(data, max_files=None, max_file_bytes=None, max_total_bytes=None):
    """Check the output of ``git ls-tree -r -z --long`` and return the entries.

    Everything is checked here, before any content is read. Raises FetchError.
    """
    max_files = MAX_FILES if max_files is None else max_files
    max_file_bytes = MAX_FILE_BYTES if max_file_bytes is None else max_file_bytes
    max_total_bytes = MAX_TOTAL_BYTES if max_total_bytes is None else max_total_bytes
    records = [record for record in data.split(b"\0") if record]
    if not records:
        raise FetchError("the repository has no files")
    if len(records) > max_files:
        raise FetchError("the repository has more than %d files" % max_files)
    entries, total = [], 0
    for record in records:
        found = _LISTING.match(record)
        if not found:
            raise FetchError("unreadable tree entry: %s" % display.ascii_text(
                record.decode("utf-8", "backslashreplace"))[:80])
        mode, kind, oid, size, raw = found.groups()
        try:
            path = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise FetchError("a path is not valid UTF-8: %s" % display.ascii_text(
                raw.decode("utf-8", "backslashreplace"))[:80])
        shown = display.ascii_text(path)[:120]
        if kind != b"blob" or mode not in REGULAR_MODES:
            what = {b"120000": "a symbolic link", b"160000": "a submodule"}.get(mode, "not a regular file")
            raise FetchError("%s is %s (mode %s); only regular files are allowed"
                             % (shown, what, mode.decode("ascii")))
        try:
            safefs.validate_relpath(path)
        except safefs.SafeFsError as exc:
            raise FetchError("unsafe path: %s" % display.ascii_text(str(exc))[:200])
        if not size.isdigit():
            raise FetchError("%s has no size in the listing" % shown)
        size = int(size)
        if size > max_file_bytes:
            raise FetchError("%s is %d bytes, over the limit of %d" % (shown, size, max_file_bytes))
        total += size
        if total > max_total_bytes:
            raise FetchError("the files total more than %d bytes" % max_total_bytes)
        entries.append(Entry(path, mode, oid.decode("ascii"), size))
    try:
        safefs.check_tree_paths([e.path for e in entries])
    except safefs.SafeFsError as exc:
        raise FetchError("unsafe paths: %s" % display.ascii_text(str(exc))[:200])
    return entries


def read_objects(output, entries):
    """Split the output of ``git cat-file --batch`` and check it against the listing."""
    contents, position = [], 0
    for entry in entries:
        end = output.find(b"\n", position)
        header = output[position:end].split(b" ") if end >= 0 else []
        if (len(header) != 3 or header[0].decode("ascii", "replace") != entry.oid
                or header[1] != b"blob" or not header[2].isdigit() or int(header[2]) != entry.size):
            raise FetchError("git returned something different from the listing for %s"
                             % display.ascii_text(entry.path)[:120])
        start = end + 1
        stop = start + entry.size
        if output[stop:stop + 1] != b"\n" or stop > len(output):
            raise FetchError("git returned truncated content for %s" % display.ascii_text(entry.path)[:120])
        contents.append(output[start:stop])
        position = stop + 1
    if position != len(output):
        raise FetchError("git returned more content than the listing named")
    return contents


# --- running git ----------------------------------------------------------------


def git_executable():
    found = shutil.which("git")
    if not found:
        raise FetchError("git is not installed or not on PATH")
    # A relative PATH entry must not make the program depend on the directory it is run in.
    return os.path.abspath(found)


def git_environment():
    """The scrubbed environment every git command of the workbench runs in."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ALLOW_PROTOCOL": "file:https:ssh",
        "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ForwardAgent=no -o ClearAllForwardings=yes",
        "GIT_LFS_SKIP_SMUDGE": "1",
        "LC_ALL": "C",
    })
    return env


def _file_limit():
    """The most any one file git writes may hold: a pack larger than this stops the fetch."""
    return 4 * MAX_TOTAL_BYTES


def _limit_child():
    import resource
    limit = _file_limit()
    resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))


def _kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _git(git, args, cwd, nohooks, env, timeout, max_output, data=None):
    """Run git in its own process group; read its output in chunks and stop it at a limit.

    The output is never held beyond `max_output` bytes: git is killed, with everything it
    started, when it produces more, or when `timeout` seconds pass.
    """
    command = [git, "-c", "core.hooksPath=" + nohooks,
               "-c", "transfer.fsckObjects=true", "-c", "fetch.fsckObjects=true",
               "-c", "protocol.version=2"] + args
    errors = tempfile.TemporaryFile()
    source = None
    try:
        if data is not None:
            source = tempfile.TemporaryFile()
            source.write(data)
            source.seek(0)
        try:
            proc = subprocess.Popen(command, cwd=cwd, env=env,
                                    stdin=source if source is not None else subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=errors,
                                    start_new_session=True, preexec_fn=_limit_child)
        except OSError as exc:
            raise FetchError("git could not be run: %s" % (exc.strerror or exc))
        chunks, size = [], 0
        deadline = time.monotonic() + timeout
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise FetchError("git timed out after %d seconds (%s)" % (timeout, args[0]))
                ready, _, _ = select.select([proc.stdout], [], [], min(remaining, 0.5))
                if not ready:
                    continue
                chunk = os.read(proc.stdout.fileno(), 65536)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_output:
                    raise FetchError("git produced more output than the limits allow (%s)" % args[0])
                chunks.append(chunk)
            code = proc.wait(timeout=max(deadline - time.monotonic(), 1))
        except subprocess.TimeoutExpired:
            raise FetchError("git timed out after %d seconds (%s)" % (timeout, args[0]))
        finally:
            _kill_group(proc)
            proc.stdout.close()
            proc.wait()
        if code != 0:
            errors.seek(0)
            message = errors.read(4096).decode("utf-8", "backslashreplace").strip().splitlines()
            raise FetchError("git %s failed: %s" % (args[0], display.ascii_text(
                " ".join(message[-3:]))[:300] or "no message"))
        return b"".join(chunks)
    finally:
        errors.close()
        if source is not None:
            source.close()


# --- the download ---------------------------------------------------------------


def fetch(store, source, ref="HEAD", *, now=None):
    """Download `ref` of `source` into a new directory under the store's cache.

    Returns a ``Fetched``. Raises FetchError and leaves nothing in the cache on any failure.
    """
    url = normalize_source(source)
    check_ref(ref)
    git, env = git_executable(), git_environment()
    try:
        workdir = tempfile.mkdtemp(prefix="workbench-fetch-")
    except OSError as exc:
        raise FetchError("cannot make a temporary directory: %s" % (exc.strerror or exc))
    try:
        nohooks = os.path.join(workdir, "nohooks")
        os.mkdir(nohooks)
        repo = os.path.join(workdir, "repo")

        def git_run(args, cwd, timeout, max_output, data=None):
            return _git(git, args, cwd, nohooks, env, timeout, max_output, data)

        small = 64 * 1024
        git_run(["init", "--bare", "--quiet", "--template=", repo], workdir, GIT_TIMEOUT, small)
        git_run(["fetch", "--quiet", "--no-tags", "--no-recurse-submodules", "--depth", "1",
                 "--", url, ref], repo, FETCH_TIMEOUT, small)
        commit = git_run(["rev-parse", "--verify", "FETCH_HEAD^{commit}"], repo,
                         GIT_TIMEOUT, small).decode("ascii", "replace").strip()
        if not _HEX.match(commit):
            raise FetchError("git did not return a commit id")
        # A tree can share subtrees, so its listing can be far larger than the repository.
        # The listing is read in chunks and git is stopped once it passes what MAX_FILES allows.
        entries = parse_listing(git_run(["ls-tree", "-r", "-z", "--long", commit], repo,
                                        GIT_TIMEOUT, MAX_FILES * LISTING_RECORD_BYTES + small))
        wanted = b"".join(entry.oid.encode("ascii") + b"\n" for entry in entries)
        contents = read_objects(
            git_run(["cat-file", "--batch"], repo, FETCH_TIMEOUT,
                    MAX_TOTAL_BYTES + len(entries) * 128 + small, wanted), entries)
        return _place(store, url, ref, commit, entries, contents, now)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _place(store, url, ref, commit, entries, contents, now):
    cache = os.path.join(store.root, "cache")
    identity = uuid.uuid4().hex[:20]
    staging = ".incoming-" + identity
    tree = {"package/" + entry.path: data for entry, data in zip(entries, contents)}
    executable = {"package/" + entry.path for entry in entries if entry.mode == b"100755"}
    total = sum(len(data) for data in contents)
    tree["fetch.json"] = (json.dumps({
        "bytes": total, "commit": commit, "files": len(entries), "ref": ref,
        "source": url, "time": now or approvals.utc_now()}, sort_keys=True, indent=2)
        + "\n").encode("utf-8")
    try:
        fd = safefs.open_root(cache, "cache")
    except safefs.SafeFsError as exc:
        raise FetchError(str(exc))
    try:
        try:
            os.mkdir(staging, 0o700, dir_fd=fd)
        except OSError as exc:
            raise FetchError("cannot create a cache directory: %s" % (exc.strerror or exc))
        try:
            safefs.write_tree(os.path.join(cache, staging), tree, executable)
            os.rename(staging, identity, src_dir_fd=fd, dst_dir_fd=fd)
        except (safefs.SafeFsError, OSError) as exc:
            shutil.rmtree(os.path.join(cache, staging), ignore_errors=True)
            raise FetchError("cannot write the package into the cache: %s" % exc)
        except BaseException:
            # An interrupt (Ctrl-C) must not leave a half-written staging directory behind.
            shutil.rmtree(os.path.join(cache, staging), ignore_errors=True)
            raise
    finally:
        os.close(fd)
    return Fetched(identity, os.path.join(cache, identity, "package"), commit, url, ref,
                   len(entries), total)

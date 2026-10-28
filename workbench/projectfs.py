"""The project writer: create files and directories inside a held target, read a file, list a
directory and replace a file whose content is as expected, and nothing else.

Every write walks from the held target descriptor one path component at a time, each
directory opened with no-follow and directory-only flags, so a parent swapped for a link
after a check cannot move the write elsewhere. A file is created exclusively and without
following links; an existing path of any kind, or a link at any component, is a conflict.
Nothing is overwritten except through ``replace_file``, which renames a freshly made sibling
over a regular file whose hash is the one expected. Nothing is unlinked except the install
marker and the writer's own sibling when a replace fails. The one write under ``.git`` besides
``create_git`` is ``add_exclude``, which appends literal lines to ``.git/info/exclude``.

Limits, recorded on purpose:

* Writing is not atomic across files. If a write fails, the files already created stay, and
  ``written`` lists them; the caller reports them and exits 3. A file whose write failed
  part-way is listed too, since it exists.
* A process killed mid-write can leave a part-written file. The install marker
  (``.workbench/local/incomplete``) is how a later command finds that directory.
* A file with more than one hard link is refused by every read and replace, since its other name
  may be outside the project. A file whose mode allows no read cannot be replaced.
* A replace checks the original's hash and then renames; the two steps are not one operation, so
  a write made to the file in between is lost. The check is against the project's owner or a
  tool run beside this command, not against an attacker the hash gate already excludes.
* A created directory is made with mode 0755 and a file with 0644, both reduced by the process
  umask. A file marked executable is set to 0755 explicitly, which the umask does not narrow.
  A replaced file keeps its original's narrower mode (see ``replace_file``).
* A signal that lands between creating the replace sibling and noting it can leave a stray
  ``.workbench-<pid>-<hex>.tmp`` and an open descriptor, as a killed process can; it is not
  searched for or removed later.
"""

import collections
import errno
import hashlib
import os
import stat

from .wbkit import safefs

MARKER = ".workbench/local/incomplete"
EXCLUDE = ".git/info/exclude"
MAX_EXCLUDE_ENTRIES = 256
_EXCLUDE_BAD = set("*?[]!# \\")


class WriteConflict(safefs.SafeFsError):
    """The path exists, or a link or a non-directory is in the way."""


class MarkerMissing(safefs.SafeFsError):
    """The install marker is not there (as opposed to being unreadable or in the way)."""


def exclude_line(entry):
    """The line `add_exclude` writes for `entry`: the literal path, anchored with a leading ``/``.

    An entry is a relative path with an optional trailing ``/`` (a directory). A glob character,
    a space, a leading ``!`` or ``#`` (anywhere, in fact), a backslash, a ``.``/``..``/empty
    segment and anything under ``.git`` are refused, so the line can only name that one path.
    """
    if not isinstance(entry, str):
        raise safefs.SafeFsError("an exclude entry is not text: %r" % (entry,))
    body = entry[:-1] if entry.endswith("/") else entry
    safefs.validate_relpath(body)
    if _EXCLUDE_BAD & set(entry):
        raise safefs.SafeFsError(
            "an exclude entry must be a literal path with no glob, space, '#', '!' or backslash: %s"
            % entry)
    return "/" + entry


# What `read_file` returns: the bytes, their SHA-256 (hex) and the permission bits.
FileState = collections.namedtuple("FileState", "data hash mode")


def _os_error(what, shown, exc):
    return safefs.SafeFsError("cannot %s %s: %s" % (what, shown, exc.strerror or exc))


class Writer:
    """Creates files and directories in a held ``Target``.

    ``written`` lists the paths created so far, in order; a directory ends with ``/``. The
    directory made by ``make_target`` is recorded in ``made_target``, not in ``written``.
    """

    def __init__(self, target):
        self.target = target
        self.written = []
        self.made_target = False

    # --- the target itself ---

    def make_target(self):
        """For a ``new-missing`` target, create the directory in the held parent."""
        held = self.target
        if held.state != "new-missing" or held.created:
            raise safefs.SafeFsError("the target already exists: %s" % held.path)
        held.recheck()
        try:
            os.mkdir(held.name, 0o755, dir_fd=held.fd)
        except FileExistsError:
            raise WriteConflict("the target appeared: %s" % held.path)
        except OSError as exc:
            raise _os_error("create", held.path, exc)
        self.made_target = True
        try:
            fd = os.open(held.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=held.fd)
        except OSError as exc:
            raise WriteConflict("the new target cannot be opened: %s: %s"
                                % (held.path, exc.strerror or exc))
        try:
            held.adopt_created(fd)
        except BaseException:
            os.close(fd)
            raise

    # --- walking ---

    def _live_fd(self):
        held = self.target
        if held.fd is None:
            raise safefs.SafeFsError("the target is closed: %s" % held.path)
        if held.state == "new-missing" and not held.created:
            raise safefs.SafeFsError("the target does not exist yet; make it first: %s" % held.path)
        return held.fd

    def _shown(self, rel):
        return "%s/%s" % (self.target.path, rel)

    def _step(self, name, dirfd, shown, make, record_prefix):
        """Open directory `name` in `dirfd` without following links, making it if asked."""
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        try:
            return os.open(name, flags, dir_fd=dirfd)
        except FileNotFoundError:
            if not make:
                raise
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                raise WriteConflict("a link or a file is in the way: %s" % shown)
            raise _os_error("open", shown, exc)
        try:
            os.mkdir(name, 0o755, dir_fd=dirfd)
            self.written.append(record_prefix + "/")
        except FileExistsError:
            pass
        except OSError as exc:
            raise _os_error("create", shown, exc)
        try:
            return os.open(name, flags, dir_fd=dirfd)
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                raise WriteConflict("a link or a file is in the way: %s" % shown)
            raise _os_error("open", shown, exc)

    def _walk(self, parts, fds, make):
        current = self._live_fd()
        for depth, name in enumerate(parts):
            current = self._step(name, current, self._shown("/".join(parts[:depth + 1])),
                                 make, "/".join(parts[:depth + 1]))
            fds.append(current)
        return current

    # --- creating ---

    def create_dir(self, rel):
        """Create `rel` and any missing parents. An existing real directory is accepted;
        a link or a file in the way is a conflict."""
        parts = safefs.validate_relpath(rel)
        safefs._fire("projectfs_validated", root=self.target.path, rel=rel)
        fds = []
        try:
            self._walk(parts, fds, True)
        finally:
            for fd in fds:
                os.close(fd)

    def create_file(self, rel, data, executable=False):
        """Create `rel` exclusively with `data`; mode 0755 only when `executable`.

        The file appears whole or not at all. A sibling in the same directory is created exclusively, filled and synced, then
        linked to `rel`, which fails when anything is there, a link included; the sibling is unlinked on every path out. A
        failure before the link leaves nothing at `rel` and does not list it in `written`. A crash between the link and the
        unlink leaves the finished file with a second name, which a later read refuses (more than one hard link) until the
        sibling, named ``.workbench-<pid>-<hex>.tmp``, is removed."""
        parts = safefs.validate_relpath(rel)
        if not isinstance(data, bytes):
            raise safefs.SafeFsError("content is not bytes: %s" % rel)
        if len(data) > safefs.MAX_FILE_BYTES:
            raise safefs.SafeFsError("file too large: %s" % rel)
        shown = self._shown(rel)
        safefs._fire("projectfs_validated", root=self.target.path, rel=rel)
        fds = []
        sibling = None
        try:
            dirfd = self._walk(parts[:-1], fds, True)
            safefs._fire("projectfs_walked", root=self.target.path, rel=rel)
            try:
                os.stat(parts[-1], dir_fd=dirfd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            except OSError as exc:
                if exc.errno == errno.ENOTDIR:
                    raise WriteConflict("a link or a file is in the way: %s" % shown)
                raise _os_error("create", shown, exc)
            else:
                raise WriteConflict("the path already exists: %s" % shown)
            temp = ".workbench-%d-%s.tmp" % (os.getpid(), os.urandom(6).hex())
            try:
                fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644,
                             dir_fd=dirfd)
            except FileExistsError:
                raise WriteConflict("the temporary name is taken: %s" % self._shown(temp))
            except OSError as exc:
                raise _os_error("create", self._shown(temp), exc)
            sibling = temp
            try:
                try:
                    view = memoryview(data)
                    while view:
                        view = view[os.write(fd, view):]
                    if executable:
                        os.fchmod(fd, 0o755)
                    os.fsync(fd)
                except OSError as exc:
                    raise _os_error("write", shown, exc)
            finally:
                os.close(fd)
            safefs._fire("projectfs_filled", root=self.target.path, rel=rel)
            try:
                os.link(temp, parts[-1], src_dir_fd=dirfd, dst_dir_fd=dirfd, follow_symlinks=False)
            except FileExistsError:
                raise WriteConflict("the path already exists: %s" % shown)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise WriteConflict("a link or a file is in the way: %s" % shown)
                raise _os_error("create", shown, exc)
            self.written.append(rel)
        finally:
            if sibling is not None:
                try:
                    os.unlink(sibling, dir_fd=dirfd)
                except OSError:
                    pass
            for each in fds:
                os.close(each)

    # --- reading and replacing ---

    def _open_regular(self, name, dirfd, shown):
        """Open `name` no-follow for reading. Returns (fd, fstat) for a regular file, or None when
        it is not there; a link or any other kind of file is a conflict."""
        try:
            info = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise _os_error("read", shown, exc)
        if not stat.S_ISREG(info.st_mode):
            raise WriteConflict("not a regular file: %s" % shown)
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dirfd)
        except FileNotFoundError:
            return None
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.ENXIO, errno.ENOTDIR):
                raise WriteConflict("not a regular file: %s" % shown)
            raise _os_error("read", shown, exc)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
                    info.st_dev, info.st_ino):
                raise WriteConflict("the file changed while it was opened: %s" % shown)
            if opened.st_nlink > 1:
                # A name that is also another path may be a file outside the project.
                raise WriteConflict("the file has more than one hard link: %s" % shown)
            if opened.st_size > safefs.MAX_FILE_BYTES:
                raise safefs.SafeFsError("file too large (%d bytes, limit %d): %s"
                                         % (opened.st_size, safefs.MAX_FILE_BYTES, shown))
        except BaseException:
            os.close(fd)
            raise
        return fd, opened

    @staticmethod
    def _read_all(fd, shown):
        chunks, total = [], 0
        limit = safefs.MAX_FILE_BYTES
        try:
            while total <= limit:
                chunk = os.read(fd, min(65536, limit + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
        except OSError as exc:
            raise _os_error("read", shown, exc)
        if total > limit:
            raise safefs.SafeFsError("file too large (over %d bytes): %s" % (limit, shown))
        return b"".join(chunks)

    def read_file(self, rel):
        """The ``FileState`` of the regular file `rel`, or None when it is not there (the file
        or a directory above it). A link, or a file where a directory should be, at any
        component, and a file that is not regular, is a conflict. Bounded by
        ``safefs.MAX_FILE_BYTES``."""
        parts = safefs.validate_relpath(rel)
        shown = self._shown(rel)
        safefs._fire("projectfs_validated", root=self.target.path, rel=rel)
        fds = []
        try:
            try:
                dirfd = self._walk(parts[:-1], fds, False)
            except FileNotFoundError:
                return None
            safefs._fire("projectfs_walked", root=self.target.path, rel=rel)
            got = self._open_regular(parts[-1], dirfd, shown)
            if got is None:
                return None
            fd, opened = got
            try:
                data = self._read_all(fd, shown)
            finally:
                os.close(fd)
            return FileState(data, hashlib.sha256(data).hexdigest(), stat.S_IMODE(opened.st_mode))
        finally:
            for each in fds:
                os.close(each)

    BAD_NAME = "badname"

    def list_dir(self, rel, lenient=False):
        """The entries of directory `rel` as sorted ``(name, kind)`` pairs, `kind` being what
        ``safefs.classify`` says of the entry itself (a link is ``symlink``, never followed), or
        None when the directory is not there. A link or a file in the way of the directory is a
        conflict. A name that fails the path validator is refused, or with `lenient` is listed
        with the kind ``BAD_NAME`` and is not examined further. The empty string is the project
        directory itself."""
        parts = safefs.validate_relpath(rel) if rel else []
        fds = []
        try:
            try:
                dirfd = self._walk(parts, fds, False)
            except FileNotFoundError:
                return None
            try:
                names = sorted(os.listdir(dirfd))
                found = []
                for name in names:
                    try:
                        safefs.validate_relpath(name)
                    except safefs.SafeFsError:
                        if not lenient:
                            raise
                        found.append((name, self.BAD_NAME))
                        continue
                    try:
                        info = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    found.append((name, safefs.classify(info.st_mode)))
            except OSError as exc:
                raise _os_error("list", self._shown(rel), exc)
            return found
        finally:
            for each in fds:
                os.close(each)

    def dir_holds(self, rel, ignore=()):
        """Whether directory `rel` holds any entry not named in `ignore`: None when it is not
        there, else True or False. A link or a file in the way is a conflict. Reads at most the
        first entries; never follows a link."""
        parts = safefs.validate_relpath(rel)
        fds = []
        try:
            try:
                dirfd = self._walk(parts, fds, False)
            except FileNotFoundError:
                return None
            try:
                with os.scandir(dirfd) as entries:
                    return any(entry.name not in ignore for entry in entries)
            except OSError as exc:
                raise _os_error("list", self._shown(rel), exc)
        finally:
            for each in fds:
                os.close(each)

    def git_entry(self, rel="", limit=65536):
        """What is at `rel` below ``.git`` (the empty string is ``.git`` itself): None when it is
        not there, ``("dir", None)`` for a directory, ``("file", sha256)`` for a regular file of at
        most `limit` bytes with one link. Nothing is followed; a link, another kind of file or a
        larger file is a conflict. Read-only, for looking at a ``.git`` the workbench made."""
        found = self._git_look(rel, limit)
        if found is not None and found[0] == "file":
            return ("file", hashlib.sha256(found[1]).hexdigest())
        return found

    def git_bytes(self, rel, limit):
        """The bytes of the regular file `rel` below ``.git`` (at most `limit`, one link), or None
        when it is not there. Nothing is followed; a link, a directory, another kind of file or a
        larger file is a conflict. Read-only."""
        found = self._git_look(rel, limit)
        if found is None:
            return None
        if found[0] != "file":
            raise WriteConflict("not a plain regular file: %s" % self._shown(".git/" + rel))
        return found[1]

    def _git_look(self, rel, limit):
        parts = [".git"] + (rel.split("/") if rel else [])
        for part in parts[1:]:
            safefs.validate_relpath("git/" + part)
        shown = self._shown("/".join(parts))
        fds = []
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        try:
            current = self._live_fd()
            for name in parts[:-1]:
                try:
                    current = os.open(name, flags, dir_fd=current)
                except FileNotFoundError:
                    return None
                except OSError as exc:
                    if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                        raise WriteConflict("a link or a file is in the way: %s" % shown)
                    raise _os_error("open", shown, exc)
                fds.append(current)
            try:
                info = os.stat(parts[-1], dir_fd=current, follow_symlinks=False)
            except FileNotFoundError:
                return None
            except OSError as exc:
                raise _os_error("read", shown, exc)
            if stat.S_ISDIR(info.st_mode):
                return ("dir", None)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1 or info.st_size > limit:
                raise WriteConflict("not a plain small regular file: %s" % shown)
            got = self._open_regular(parts[-1], current, shown)
            if got is None:
                return None
            fd, _ = got
            try:
                data = self._read_all(fd, shown)
            finally:
                os.close(fd)
            return ("file", data)
        finally:
            for each in fds:
                os.close(each)

    def replace_file(self, rel, expected_hash, data, executable=False):
        """Replace the regular file `rel`, whose SHA-256 must be `expected_hash`, with `data`.

        A sibling is created exclusively and filled and synced; the original is then reopened
        no-follow in the same held directory and its hash compared; the sibling is renamed over
        it. A different hash, a link, a file that is not regular or one that is gone raises
        ``WriteConflict``. A sibling this call made is unlinked on every failure; one that was
        already there is never touched. The sibling is private (0600) until the check has passed. The
        mode is then 0755 when `executable`; otherwise the original's mode without any execute,
        group-write or other-write bit, so a private file stays private and no file is widened.
        No setuid or setgid bit is ever set.
        """
        parts = safefs.validate_relpath(rel)
        if not isinstance(data, bytes):
            raise safefs.SafeFsError("content is not bytes: %s" % rel)
        if len(data) > safefs.MAX_FILE_BYTES:
            raise safefs.SafeFsError("file too large: %s" % rel)
        shown = self._shown(rel)
        safefs._fire("projectfs_validated", root=self.target.path, rel=rel)
        fds = []
        sibling = None
        try:
            try:
                dirfd = self._walk(parts[:-1], fds, False)
            except FileNotFoundError:
                raise WriteConflict("the file is not there: %s" % shown)
            safefs._fire("projectfs_walked", root=self.target.path, rel=rel)
            temp = ".workbench-%d-%s.tmp" % (os.getpid(), os.urandom(6).hex())
            try:
                fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                             dir_fd=dirfd)
            except FileExistsError:
                raise WriteConflict("the temporary name is taken: %s" % self._shown(temp))
            except OSError as exc:
                raise _os_error("create", self._shown(temp), exc)
            sibling = temp
            try:
                try:
                    view = memoryview(data)
                    while view:
                        view = view[os.write(fd, view):]
                    os.fsync(fd)
                except OSError as exc:
                    raise _os_error("write", shown, exc)
                got = self._open_regular(parts[-1], dirfd, shown)
                if got is None:
                    raise WriteConflict("the file is not there: %s" % shown)
                original, info = got
                try:
                    current = hashlib.sha256(self._read_all(original, shown)).hexdigest()
                finally:
                    os.close(original)
                if current != expected_hash:
                    raise WriteConflict("the file is not as it was installed: %s" % shown)
                try:
                    os.fchmod(fd, 0o755 if executable else stat.S_IMODE(info.st_mode) & 0o644)
                except OSError as exc:
                    raise _os_error("write", shown, exc)
            finally:
                os.close(fd)
            safefs._fire("projectfs_checked", root=self.target.path, rel=rel)
            try:
                os.rename(temp, parts[-1], src_dir_fd=dirfd, dst_dir_fd=dirfd)
            except OSError as exc:
                raise _os_error("replace", shown, exc)
            sibling = None
            self.written.append(rel)
        finally:
            if sibling is not None:
                try:
                    os.unlink(sibling, dir_fd=dirfd)
                except OSError:
                    pass
            for each in fds:
                os.close(each)

    def _open_git_info(self, fds, make=True):
        """Open ``.git/info`` below the target, making ``info`` when it is missing (and returning
        None instead when `make` is false). ``.git`` must be a real directory: a gitfile (a
        worktree or a submodule), a link or anything else is a conflict."""
        top = self._live_fd()
        shown = self._shown(".git")
        try:
            info = os.stat(".git", dir_fd=top, follow_symlinks=False)
        except FileNotFoundError:
            raise WriteConflict("there is no .git directory: %s" % shown)
        except OSError as exc:
            raise _os_error("read", shown, exc)
        if stat.S_ISREG(info.st_mode):
            raise WriteConflict(".git is a file (a worktree or a submodule), not a directory; "
                                "its exclude file is not edited: %s" % shown)
        if not stat.S_ISDIR(info.st_mode):
            raise WriteConflict(".git is not a real directory: %s" % shown)
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        try:
            git = os.open(".git", flags, dir_fd=top)
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                raise WriteConflict("a link or a file is in the way: %s" % shown)
            raise _os_error("open", shown, exc)
        fds.append(git)
        shown = self._shown(".git/info")
        try:
            if not make:
                try:
                    return os.open("info", flags, dir_fd=git)
                except FileNotFoundError:
                    return None
            return self._open_dir_or_make(git, "info", shown, flags, ".git/info/")
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                raise WriteConflict("a link or a file is in the way: %s" % shown)
            raise _os_error("open", shown, exc)

    def _open_dir_or_make(self, dirfd, name, shown, flags, record):
        try:
            return os.open(name, flags, dir_fd=dirfd)
        except FileNotFoundError:
            pass
        try:
            os.mkdir(name, 0o755, dir_fd=dirfd)
            self.written.append(record)
        except FileExistsError:
            pass
        except OSError as exc:
            raise _os_error("create", shown, exc)
        return os.open(name, flags, dir_fd=dirfd)

    def add_exclude(self, entries):
        """Add the anchored literal lines for `entries` (see ``exclude_line``) to
        ``.git/info/exclude`` and return the entries that were added, in order.

        An entry whose line is already there, byte for byte, is not added again, so a rerun adds
        nothing. Existing lines are kept as they are: the file is opened no-follow, must be a
        regular file with one link, and is appended to, never rewritten. A missing ``info`` or
        ``exclude`` is created. The target is the only place this reads or writes under ``.git``,
        and the path is not a parameter, so no other ``.git`` file can be named.
        """
        if isinstance(entries, (str, bytes)):
            raise safefs.SafeFsError("exclude entries are not a list")
        wanted = []
        for entry in entries:
            line = exclude_line(entry)
            if all(line != other for _, other in wanted):
                wanted.append((entry, line))
        if len(wanted) > MAX_EXCLUDE_ENTRIES:
            raise safefs.SafeFsError("too many exclude entries (limit %d)" % MAX_EXCLUDE_ENTRIES)
        if not wanted:
            return []
        shown = self._shown(EXCLUDE)
        safefs._fire("projectfs_validated", root=self.target.path, rel=EXCLUDE)
        fds = []
        try:
            info = self._open_git_info(fds)
            fds.append(info)
            safefs._fire("projectfs_walked", root=self.target.path, rel=EXCLUDE)
            flags = os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK
            created = False
            try:
                fd = os.open("exclude", flags, dir_fd=info)
            except FileNotFoundError:
                try:
                    fd = os.open("exclude", os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_EXCL
                                 | os.O_NOFOLLOW, 0o644, dir_fd=info)
                except FileExistsError:
                    raise WriteConflict("the exclude file appeared: %s" % shown)
                except OSError as exc:
                    raise _os_error("create", shown, exc)
                created = True
                self.written.append(EXCLUDE)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENXIO, errno.EISDIR, errno.ENOTDIR):
                    raise WriteConflict("the exclude file is not a regular file: %s" % shown)
                raise _os_error("open", shown, exc)
            try:
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode):
                    raise WriteConflict("the exclude file is not a regular file: %s" % shown)
                if opened.st_nlink > 1:
                    raise WriteConflict("the exclude file has more than one hard link: %s" % shown)
                if opened.st_size > safefs.MAX_FILE_BYTES:
                    raise safefs.SafeFsError("file too large (%d bytes, limit %d): %s"
                                             % (opened.st_size, safefs.MAX_FILE_BYTES, shown))
                existing = b""
                if not created:
                    try:
                        chunks, total = [], 0
                        while total <= safefs.MAX_FILE_BYTES:
                            chunk = os.pread(fd, 65536, total)
                            if not chunk:
                                break
                            chunks.append(chunk)
                            total += len(chunk)
                    except OSError as exc:
                        raise _os_error("read", shown, exc)
                    if total > safefs.MAX_FILE_BYTES:
                        raise safefs.SafeFsError("file too large (over %d bytes): %s"
                                                 % (safefs.MAX_FILE_BYTES, shown))
                    existing = b"".join(chunks)
                # A CRLF file's lines end in "\r"; it is not part of the line git reads.
                present = {line[:-1] if line.endswith(b"\r") else line
                           for line in existing.split(b"\n")}
                added = [(entry, line.encode("utf-8")) for entry, line in wanted
                         if line.encode("utf-8") not in present]
                if not added:
                    return []
                text = b"".join(line + b"\n" for _, line in added)
                if existing and not existing.endswith(b"\n"):
                    text = b"\n" + text
                if len(existing) + len(text) > safefs.MAX_FILE_BYTES:
                    raise safefs.SafeFsError("file too large: %s" % shown)
                try:
                    view = memoryview(text)
                    while view:
                        view = view[os.write(fd, view):]
                    os.fsync(fd)
                except OSError as exc:
                    raise _os_error("write", shown, exc)
                return [entry for entry, _ in added]
            finally:
                os.close(fd)
        finally:
            for each in fds:
                os.close(each)

    def check_exclude(self, entries):
        """Raise unless ``add_exclude(entries)`` could run now. Nothing is created or written.

        The entries are checked as ``add_exclude`` checks them. ``.git`` must be a real directory;
        ``info`` and ``exclude`` may be missing (``add_exclude`` makes them), and when they are there
        they must be a real directory and a regular file with one link and a bounded size, looked at
        without following a link. A fault found here is found before any file is written.
        """
        if isinstance(entries, (str, bytes)):
            raise safefs.SafeFsError("exclude entries are not a list")
        lines = {exclude_line(entry) for entry in entries}
        if len(lines) > MAX_EXCLUDE_ENTRIES:
            raise safefs.SafeFsError("too many exclude entries (limit %d)" % MAX_EXCLUDE_ENTRIES)
        shown = self._shown(EXCLUDE)
        fds = []
        try:
            info = self._open_git_info(fds, make=False)
            if info is None:
                return
            fds.append(info)
            try:
                found = os.stat("exclude", dir_fd=info, follow_symlinks=False)
            except FileNotFoundError:
                return
            except OSError as exc:
                raise _os_error("read", shown, exc)
            if not stat.S_ISREG(found.st_mode):
                raise WriteConflict("the exclude file is not a regular file: %s" % shown)
            if found.st_nlink > 1:
                raise WriteConflict("the exclude file has more than one hard link: %s" % shown)
            if found.st_size > safefs.MAX_FILE_BYTES:
                raise safefs.SafeFsError("file too large (%d bytes, limit %d): %s"
                                         % (found.st_size, safefs.MAX_FILE_BYTES, shown))
        finally:
            for each in fds:
                os.close(each)

    def create_git(self, skeleton):
        """Create an empty ``.git`` from `skeleton`, a sequence of ``(path, content or None)``
        where None is a directory, parents first.

        ``.git`` is made with ``mkdir``, which refuses an existing path of any kind (a link
        included), and everything below it is made through descriptors held from that
        directory, so nothing here resolves a path and no program is run.
        """
        top = self._live_fd()
        try:
            os.mkdir(".git", 0o755, dir_fd=top)
        except FileExistsError:
            raise WriteConflict(".git already exists: %s" % self._shown(".git"))
        except OSError as exc:
            raise _os_error("create", self._shown(".git"), exc)
        self.written.append(".git/")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        held = {}
        try:
            try:
                held[""] = os.open(".git", flags, dir_fd=top)
            except OSError as exc:
                raise WriteConflict("the new .git cannot be opened: %s" % (exc.strerror or exc))
            for rel, data in skeleton:
                parent, _, name = rel.rpartition("/")
                shown = self._shown(".git/" + rel)
                try:
                    if data is None:
                        os.mkdir(name, 0o755, dir_fd=held[parent])
                        held[rel] = os.open(name, flags, dir_fd=held[parent])
                        continue
                    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o644, dir_fd=held[parent])
                except OSError as exc:
                    raise _os_error("create", shown, exc)
                try:
                    view = memoryview(data)
                    while view:
                        view = view[os.write(fd, view):]
                    os.fsync(fd)
                except OSError as exc:
                    raise _os_error("write", shown, exc)
                finally:
                    os.close(fd)
        finally:
            for fd in held.values():
                os.close(fd)

    def remove_empty_dir(self, rel):
        """Remove directory `rel` with ``rmdir``, which refuses one that holds anything. True
        when removed, False when it is not there. A link or a file in the way is a conflict and
        is left alone; the target itself cannot be named."""
        parts = safefs.validate_relpath(rel)
        shown = self._shown(rel)
        fds = []
        try:
            try:
                dirfd = self._walk(parts[:-1], fds, False)
                info = os.stat(parts[-1], dir_fd=dirfd, follow_symlinks=False)
            except FileNotFoundError:
                return False
            if not stat.S_ISDIR(info.st_mode):
                raise WriteConflict("not a real directory: %s" % shown)
            os.rmdir(parts[-1], dir_fd=dirfd)
            return True
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise _os_error("remove", shown, exc)
        finally:
            for each in fds:
                os.close(each)

    def remove_marker(self):
        """Unlink ``.workbench/local/incomplete`` and nothing else."""
        parts = MARKER.split("/")
        shown = self._shown(MARKER)
        fds = []
        try:
            dirfd = self._walk(parts[:-1], fds, False)
            info = os.stat(parts[-1], dir_fd=dirfd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):
                raise WriteConflict("the install marker is not a regular file: %s" % shown)
            os.unlink(parts[-1], dir_fd=dirfd)
        except FileNotFoundError:
            raise MarkerMissing("the install marker is missing: %s" % shown)
        except OSError as exc:
            raise _os_error("remove", shown, exc)
        finally:
            for each in fds:
                os.close(each)

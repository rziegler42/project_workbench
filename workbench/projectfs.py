"""The project writer: create files and directories inside a held target, and nothing else.

Every write walks from the held target descriptor one path component at a time, each
directory opened with no-follow and directory-only flags, so a parent swapped for a link
after a check cannot move the write elsewhere. A file is created exclusively and without
following links; an existing path of any kind, or a link at any component, is a conflict.
Nothing is overwritten and nothing is unlinked except the install marker.

Limits, recorded on purpose:

* Writing is not atomic across files. If a write fails, the files already created stay, and
  ``written`` lists them; the caller reports them and exits 3. A file whose write failed
  part-way is listed too, since it exists.
* A process killed mid-write can leave a part-written file. The install marker
  (``.workbench/local/incomplete``) is how a later command finds that directory.
* A created directory is made with mode 0755 and a file with 0644 (0755 when executable), both
  reduced by the process umask and never widened by it.
"""

import errno
import os
import stat

from . import safefs

MARKER = ".workbench/local/incomplete"


class WriteConflict(safefs.SafeFsError):
    """The path exists, or a link or a non-directory is in the way."""


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
        """Create `rel` exclusively with `data`; mode 0755 only when `executable`."""
        parts = safefs.validate_relpath(rel)
        if not isinstance(data, bytes):
            raise safefs.SafeFsError("content is not bytes: %s" % rel)
        if len(data) > safefs.MAX_FILE_BYTES:
            raise safefs.SafeFsError("file too large: %s" % rel)
        shown = self._shown(rel)
        safefs._fire("projectfs_validated", root=self.target.path, rel=rel)
        fds = []
        try:
            dirfd = self._walk(parts[:-1], fds, True)
            safefs._fire("projectfs_walked", root=self.target.path, rel=rel)
            try:
                fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o644, dir_fd=dirfd)
            except FileExistsError:
                raise WriteConflict("the path already exists: %s" % shown)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    raise WriteConflict("a link or a file is in the way: %s" % shown)
                raise _os_error("create", shown, exc)
            self.written.append(rel)
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
            raise safefs.SafeFsError("the install marker is missing: %s" % shown)
        except OSError as exc:
            raise _os_error("remove", shown, exc)
        finally:
            for each in fds:
                os.close(each)

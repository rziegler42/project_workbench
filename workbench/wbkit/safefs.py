"""Safe filesystem layer: a path validator, a race-safe reader and a safe writer.

Every directory is opened with no-follow flags relative to its parent's
descriptor, so a parent swapped for a symbolic link after a check fails to open
instead of redirecting a read or a write. Paths given to this module are
validated first and then used only through descriptors.

Limits of the checks, recorded here on purpose:

* Only the final component of a root path is guarded. Ancestors of the root may
  be symbolic links (for example ``/tmp`` on macOS); the root itself may not.
* A file's identity is its device, inode, type, size, modification time and
  change time (``st_ctime_ns``). Userspace cannot restore the change time, so a
  same-size rewrite with the modification time put back is still detected. The
  precision of that check is the filesystem's timestamp precision: a rewrite
  inside one timestamp tick on a coarse filesystem can go unseen.
* Writing is atomic per file (a temporary sibling is renamed over the
  destination) but not across files: if a later rename fails, earlier files stay
  replaced. Directories created for a failed write are left in place.
* A process killed mid-write can leave a ``.workbench-<pid>-<hex>.tmp`` sibling. On
  macOS ``fsync`` does not force data to disk and directories are not synced, so a
  power loss can lose a rename but cannot leave a partial file.
* A replaced file keeps only its permission bits (without setuid or setgid); its
  owner, ACLs and extended attributes are not carried over.
* Deletion is not provided yet.

A platform that lacks the no-follow and directory-relative calls used here is
refused with a message; nothing falls back to a path-based call.
"""

import collections
import errno
import os
import stat
import unicodedata

MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_PATH_CHARS = 512

Entry = collections.namedtuple("Entry", "rel kind identity executable")

# Test seam: a callable ``hook(stage, **info)`` run at fixed points so a test can
# swap files deterministically. It is None outside tests.
_hook = None


class SafeFsError(Exception):
    """A refusal; the message names the path."""


def _fire(stage, **info):
    if _hook is not None:
        _hook(stage, **info)


def _support_problems():
    missing = []
    for func in (os.open, os.stat, os.mkdir, os.rename, os.unlink, os.access):
        if func not in os.supports_dir_fd:
            missing.append("directory-relative %s" % func.__name__)
    if os.stat not in os.supports_follow_symlinks:
        missing.append("stat without following links")
    if os.listdir not in os.supports_fd:
        missing.append("listing a directory by descriptor")
    for flag in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK"):
        if not hasattr(os, flag):
            missing.append(flag)
    return missing


def require_support():
    problems = _support_problems()
    if problems:
        raise SafeFsError(
            "this platform cannot read or write files safely (missing: %s)" % ", ".join(problems))


# --- relative paths -----------------------------------------------------------


def validate_relpath(rel):
    """Return the segments of a safe relative POSIX path or raise SafeFsError."""
    if not isinstance(rel, str) or not rel:
        raise SafeFsError("path is not a non-empty string: %r" % (rel,))
    shown = rel if len(rel) <= 80 else rel[:77] + "..."
    if len(rel) > MAX_PATH_CHARS:
        raise SafeFsError("path is too long (over %d characters): %r" % (MAX_PATH_CHARS, shown))
    if not rel.isprintable():
        raise SafeFsError("path has a non-printable character: %r" % (shown,))
    if rel.startswith("/"):
        raise SafeFsError("path is absolute: %s" % shown)
    # Windows reads `\` as a separator, `:` as a drive letter or stream, and ignores
    # trailing dots and spaces, so a path a consumer joins later cannot slip through.
    if "\\" in rel or ":" in rel:
        raise SafeFsError("path has a backslash or colon: %s" % shown)
    parts = rel.split("/")
    for part in parts:
        if part in ("", ".", ".."):
            raise SafeFsError("path has an empty, '.' or '..' segment: %s" % shown)
        folded = part.rstrip(" .").casefold()
        # `git~1` is the Windows 8.3 short name of `.git`.
        short = folded[4:]
        if folded == ".git" or (folded.startswith("git~") and short
                                   and all(c in "0123456789" for c in short)):
            raise SafeFsError("path may not touch git metadata: %s" % shown)
    return parts


def relpath_ok(rel):
    try:
        validate_relpath(rel)
    except SafeFsError:
        return False
    return True


# --- containment --------------------------------------------------------------


def real_directory(path, what):
    """Raise unless `path` is a real directory and not a symbolic link."""
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise SafeFsError("%s is not usable: %s: %s" % (what, path, exc.strerror or exc))
    if not stat.S_ISDIR(info.st_mode):
        raise SafeFsError("%s is not a directory (symbolic links are not allowed): %s" % (what, path))


def is_within(child, parent):
    """True when `child` is `parent` or inside it, by real path and file identity."""
    child, parent = os.path.realpath(child), os.path.realpath(parent)
    if child == parent or child.startswith(parent.rstrip(os.sep) + os.sep):
        return True
    if not os.path.exists(parent):
        return False
    probe = child
    while True:
        if os.path.exists(probe) and os.path.samefile(probe, parent):
            return True
        up = os.path.dirname(probe)
        if up == probe:
            return False
        probe = up


# --- identity -----------------------------------------------------------------


def identity(info):
    return (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode), info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def classify(mode):
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "dir"
    if stat.S_ISLNK(mode):
        return "symlink"
    return "other"


def _flags_dir():
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _os_error(what, path, exc):
    return SafeFsError("cannot %s %s: %s" % (what, path, exc.strerror or exc))


def _open_dir(name, dirfd, display):
    """Open one directory relative to `dirfd`, never following a symbolic link."""
    try:
        return os.open(name, _flags_dir(), dir_fd=dirfd)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise SafeFsError("refusing to go through %s (symbolic link or not a directory)" % display)
        raise _os_error("open", display, exc)


def open_root(path, what="directory"):
    """Open a root directory that is a real directory, not a symbolic link."""
    require_support()
    real_directory(path, what)
    try:
        fd = os.open(path, _flags_dir())
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise SafeFsError("%s is not a directory (symbolic links are not allowed): %s" % (what, path))
        raise _os_error("open", path, exc)
    try:
        if identity(os.fstat(fd))[:3] != identity(os.lstat(path))[:3]:
            raise SafeFsError("%s changed while it was opened: %s" % (what, path))
    except BaseException:
        os.close(fd)
        raise
    return fd


# --- reader -------------------------------------------------------------------


class Root:
    """A held root directory. Use as a context manager; reads go through its descriptor."""

    def __init__(self, path, what="directory"):
        self.path = path
        self._fd = open_root(path, what)

    def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _live_fd(self):
        # A closed root must not fall back to a path relative to the working directory.
        if self._fd is None:
            raise SafeFsError("root is closed: %s" % self.path)
        return self._fd

    def _descend(self, parts, fds):
        """Open each directory of `parts` below the root, appending every fd to `fds`."""
        current = self._live_fd()
        shown = self.path
        for part in parts:
            shown = shown + "/" + part
            current = _open_dir(part, current, shown)
            fds.append(current)
        return current

    def walk(self):
        """List every entry below the root, sorted, with its kind and identity.

        Directories are descended with no-follow descriptors and appear as entries
        of kind ``dir``. A name that fails the path validator is refused.
        """
        out = []
        self._walk(self._live_fd(), "", out)
        return out

    def _walk(self, dirfd, prefix, out):
        for name in sorted(os.listdir(dirfd)):
            rel = prefix + name
            validate_relpath(rel)
            try:
                info = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
            except OSError as exc:
                raise _os_error("stat", "%s/%s" % (self.path, rel), exc)
            kind = classify(info.st_mode)
            out.append(Entry(rel, kind, identity(info), bool(info.st_mode & stat.S_IXUSR)))
            if kind != "dir":
                continue
            child = _open_dir(name, dirfd, "%s/%s" % (self.path, rel))
            try:
                if identity(os.fstat(child))[:3] != identity(info)[:3]:
                    raise SafeFsError("directory changed while listing: %s/%s" % (self.path, rel))
                self._walk(child, rel + "/", out)
            finally:
                os.close(child)

    def read_file(self, rel, limit=MAX_FILE_BYTES, expected=None):
        """Read one regular file, refusing on any change of identity.

        `expected` is the identity taken when the directory was listed; without it
        the identity is taken just before the open. It is compared again after the
        open and after the read.
        """
        parts = validate_relpath(rel)
        shown = "%s/%s" % (self.path, rel)
        _fire("validated", root=self.path, rel=rel)
        fds = []
        try:
            dirfd = self._descend(parts[:-1], fds)
            try:
                info = os.stat(parts[-1], dir_fd=dirfd, follow_symlinks=False)
            except OSError as exc:
                raise _os_error("read", shown, exc)
            listed = identity(info)
            if expected is not None and listed != expected:
                raise SafeFsError("file changed since it was listed: %s" % shown)
            kind = classify(info.st_mode)
            if kind != "file":
                raise SafeFsError("not a regular file (%s): %s" % (kind, shown))
            if info.st_size > limit:
                raise SafeFsError("file too large (%d bytes, limit %d): %s" % (info.st_size, limit, shown))
            _fire("listed", root=self.path, rel=rel)
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            try:
                fd = os.open(parts[-1], flags, dir_fd=dirfd)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENXIO):
                    raise SafeFsError("not a regular file: %s" % shown)
                raise _os_error("read", shown, exc)
            try:
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode) or identity(opened) != listed:
                    raise SafeFsError("file changed before it was read: %s" % shown)
                _fire("opened", root=self.path, rel=rel)
                chunks = []
                total = 0
                while total <= limit:
                    chunk = os.read(fd, min(65536, limit + 1 - total))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                if total > limit:
                    raise SafeFsError("file too large (over %d bytes): %s" % (limit, shown))
                _fire("read", root=self.path, rel=rel)
                final = os.fstat(fd)
                if identity(final) != listed or total != final.st_size:
                    raise SafeFsError("file changed while it was read: %s" % shown)
            finally:
                os.close(fd)
        finally:
            for fd in fds:
                os.close(fd)
        return b"".join(chunks)


# --- writer -------------------------------------------------------------------


def _check_tree_paths(rels):
    rels = list(rels)
    for rel in rels:
        validate_relpath(rel)
    # Compare folded, so a case or normalization variant that a case-insensitive
    # filesystem treats as the same name is caught here, not as a silent overwrite.
    def fold(parts):
        return tuple(unicodedata.normalize("NFC", part).casefold() for part in parts)

    chosen = {}
    for rel in rels:
        key = fold(rel.split("/"))
        if key in chosen:
            raise SafeFsError("paths collide (same name ignoring case): %s and %s" % (chosen[key], rel))
        chosen[key] = rel
    for rel in rels:
        parts = rel.split("/")
        for depth in range(1, len(parts)):
            key = fold(parts[:depth])
            if key in chosen:
                raise SafeFsError("path is both a file and a directory: %s" % chosen[key])
    return rels


check_tree_paths = _check_tree_paths  # public name for declaration checks


def _existing_dest(name, dirfd, shown):
    """Refuse a destination that is a symbolic link, a non-file or read-only; None if absent."""
    try:
        info = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _os_error("write", shown, exc)
    kind = classify(info.st_mode)
    if kind == "symlink":
        raise SafeFsError("refusing to write onto a symbolic link: %s" % shown)
    if kind != "file":
        raise SafeFsError("refusing to write onto a non-file (%s): %s" % (kind, shown))
    if not os.access(name, os.W_OK, dir_fd=dirfd):
        raise SafeFsError("not writable: %s" % shown)
    return info


def check_write_paths(root_path, rels):
    """Refuse a write whose path goes through a symbolic link, onto a non-file, or
    onto a read-only file. Nothing is created."""
    rels = _check_tree_paths(rels)
    with Root(root_path, "write target") as root:
        for rel in rels:
            parts = rel.split("/")
            fds = []
            try:
                current = root._live_fd()
                shown = root_path
                missing = False
                for part in parts[:-1]:
                    shown = shown + "/" + part
                    try:
                        os.stat(part, dir_fd=current, follow_symlinks=False)
                    except FileNotFoundError:
                        missing = True
                        break
                    except OSError as exc:
                        raise _os_error("check", shown, exc)
                    current = _open_dir(part, current, shown)
                    fds.append(current)
                if not missing:
                    _existing_dest(parts[-1], current, "%s/%s" % (root_path, rel))
            finally:
                for fd in fds:
                    os.close(fd)


def _open_or_make_dir(name, dirfd, shown):
    try:
        return os.open(name, _flags_dir(), dir_fd=dirfd)
    except FileNotFoundError:
        pass
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise SafeFsError("refusing to write through %s (symbolic link or not a directory)" % shown)
        raise _os_error("open", shown, exc)
    try:
        os.mkdir(name, 0o777, dir_fd=dirfd)
    except FileExistsError:
        pass
    except OSError as exc:
        raise _os_error("create", shown, exc)
    return _open_dir(name, dirfd, shown)


def write_tree(root_path, tree, executable=()):
    """Write ``{relative path: bytes}`` below an existing root and return the sorted paths.

    `executable` names files of `tree` that are set to mode 0755, whether new or existing;
    every other new file keeps the default mode and every other existing file keeps its own.

    The root and every parent directory are opened with no-follow flags and held.
    Each file is staged in an exclusively created sibling and replaced with a rename
    that names both parent descriptors, never a path, so a parent swapped for a
    symbolic link after the check cannot move the write outside the root.
    """
    rels = sorted(_check_tree_paths(tree))
    for rel in rels:
        if not isinstance(tree[rel], bytes):
            raise SafeFsError("content is not bytes: %s" % rel)
    executable = set(executable)
    if not executable <= set(rels):
        raise SafeFsError("executable names a file that is not written: %s"
                          % sorted(executable - set(rels))[0])
    check_write_paths(root_path, rels)
    _fire("after_check", root=root_path)
    dirs = {}
    staged = []
    root = Root(root_path, "write target")
    try:
        dirs[()] = root._live_fd()

        def get_dir(parts):
            if parts not in dirs:
                parent = get_dir(parts[:-1])
                dirs[parts] = _open_or_make_dir(parts[-1], parent, "%s/%s" % (root_path, "/".join(parts)))
            return dirs[parts]

        try:
            for rel in rels:
                parts = rel.split("/")
                dirfd = get_dir(tuple(parts[:-1]))
                shown = "%s/%s" % (root_path, rel)
                existing = _existing_dest(parts[-1], dirfd, shown)
                temp = ".workbench-%d-%s.tmp" % (os.getpid(), os.urandom(6).hex())
                fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666,
                             dir_fd=dirfd)
                staged.append((dirfd, temp, parts[-1], rel))
                try:
                    data = tree[rel]
                    view = memoryview(data)
                    while view:
                        view = view[os.write(fd, view):]
                    if existing is not None:
                        os.fchmod(fd, stat.S_IMODE(existing.st_mode) & 0o777)
                    if rel in executable:
                        os.fchmod(fd, 0o755)
                    os.fsync(fd)
                finally:
                    os.close(fd)
            while staged:
                dirfd, temp, name, rel = staged[0]
                _fire("before_rename", root=root_path, rel=rel)
                os.rename(temp, name, src_dir_fd=dirfd, dst_dir_fd=dirfd)
                staged.pop(0)
        except OSError as exc:
            raise _os_error("write", exc.filename or root_path, exc)
    finally:
        for dirfd, temp, _, _ in staged:
            try:
                os.unlink(temp, dir_fd=dirfd)
            except OSError:
                pass
        for key, fd in dirs.items():
            if key != ():
                os.close(fd)
        root.close()
    return rels

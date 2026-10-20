"""The target of a project command: which directory it works on and what state it is in.

The rules are in ``docs/specs/installer-interface.md`` ("The target" and "States of a
target"). One spelling is chosen, inspected, resolved once and opened without following
links; the open descriptor and its device and inode are kept, and every later check and
write goes through them. The state is decided from the directory's files with no-follow
``stat`` calls. Git is never run and nothing under ``.git`` is opened or read.

Messages name the place; the command that prints one cleans it first (``display.clean``).
"""

import errno
import os
import pwd
import stat

from . import display, projectfs, safefs, unfinished

STATES = ("new-missing", "new-empty", "new-git", "existing")

_MARKER = (".workbench", "local", "incomplete")


class TargetError(Exception):
    """A refusal. The message names the place."""


class UnfinishedMarker(TargetError):
    """A marker of an unfinished write is here. `report` is the examination, as lines."""

    def __init__(self, message, report=()):
        TargetError.__init__(self, message)
        self.report = list(report)


class TargetUsage(TargetError):
    """A usage error (exit 2): an empty spelling, or two spellings that differ."""


# --- choosing -----------------------------------------------------------------


def _absolute(spelling):
    """The spelling made absolute without resolving links, with `.` components and trailing
    separators removed. A `..` component is kept for the resolver."""
    parts = [part for part in spelling.split("/") if part not in ("", ".")]
    if spelling.startswith("/"):
        return "/" + "/".join(parts)
    return os.path.join(os.getcwd(), *parts) if parts else os.getcwd()


def _is_link(path):
    try:
        return stat.S_ISLNK(os.lstat(path).st_mode)
    except OSError:
        return False


def _same_place(first, second):
    one, two = _absolute(first), _absolute(second)
    if one == two:
        return True
    # A link and its destination are never "the same directory" (rule 5).
    if _is_link(one) or _is_link(two):
        return False
    try:
        return os.path.samefile(one, two)
    except OSError:
        return os.path.realpath(one) == os.path.realpath(two)


def choose(positional, dir_option):
    """Return the one spelling to work on, or raise TargetUsage."""
    given = [value for value in (positional, dir_option) if value is not None]
    if any(value == "" for value in given):
        raise TargetUsage("the target is an empty string")
    if not given:
        return "."
    if len(given) == 2 and not _same_place(given[0], given[1]):
        raise TargetUsage("two different targets were given: %r and --dir %r" % tuple(given))
    return given[0]


# --- places that are never a target -------------------------------------------


def _account_home():
    try:
        return pwd.getpwuid(os.getuid()).pw_dir
    except (KeyError, OSError):
        return None


def _same_file(path, info):
    try:
        other = os.stat(path)
    except OSError:
        return False
    return (other.st_dev, other.st_ino) == (info.st_dev, info.st_ino)


def _homes(home):
    found = []
    for candidate in (home if home is not None else os.environ.get("HOME"), _account_home()):
        if candidate and os.path.isabs(candidate):
            found.append(candidate)
    return found


def _check_places(resolved, exists, store_root, home):
    """Refuse the root, a home directory, the store, anything inside it or containing it."""
    if exists:
        info = os.stat(resolved)
        if _same_file("/", info):
            raise TargetError("refused: the target is the filesystem root: %s" % resolved)
        for place in _homes(home):
            if _same_file(place, info):
                raise TargetError("refused: the target is the home directory: %s" % resolved)
    if os.path.lexists(store_root):
        probe = resolved if exists else os.path.dirname(resolved)
        if safefs.is_within(probe, store_root):
            raise TargetError("refused: the target is the guarded store or inside it: %s" % resolved)
        if exists and safefs.is_within(store_root, resolved):
            raise TargetError("refused: the target contains the guarded store: %s" % resolved)


# --- the held target ----------------------------------------------------------


def _open_dir_at(name, dirfd):
    return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dirfd)


def _lstat_at(name, dirfd):
    try:
        return os.stat(name, dir_fd=dirfd, follow_symlinks=False)
    except FileNotFoundError:
        return None


class Target:
    """A target held open. Use as a context manager; ``fd`` is valid until it closes.

    For ``new-missing`` the held descriptor is the parent directory and ``name`` is the
    directory to create in it; for every other state ``fd`` is the target itself and
    ``name`` is its last component.
    """

    def __init__(self, path, state, fd, name, info):
        self.path = path
        self.state = state
        self.fd = fd
        self.name = name
        self.created = False
        self._identity = (info.st_dev, info.st_ino)

    @property
    def identity(self):
        """The held directory's (device, inode)."""
        return self._identity

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _held(self):
        if self.fd is None:
            raise TargetError("refused: the target is closed: %s" % self.path)
        return self.fd

    def recheck(self):
        """Raise TargetError unless the held directory is still the place at the path.

        Called before the first write and again after any approval.
        """
        fd = self._held()
        try:
            held = os.fstat(fd)
            if (held.st_dev, held.st_ino) != self._identity:
                raise TargetError("refused: the target changed: %s" % self.path)
            if self.state == "new-missing" and not self.created:
                parent = os.path.dirname(self.path)
                now = os.lstat(parent)
                if not stat.S_ISDIR(now.st_mode) or (now.st_dev, now.st_ino) != self._identity:
                    raise TargetError("refused: the parent of the target changed: %s" % self.path)
                if _lstat_at(self.name, fd) is not None:
                    raise TargetError("refused: the target appeared: %s" % self.path)
                return
            now = os.lstat(self.path)
        except OSError as exc:
            raise TargetError("refused: the target changed: %s: %s"
                              % (self.path, exc.strerror or exc))
        if not stat.S_ISDIR(now.st_mode) or (now.st_dev, now.st_ino) != self._identity:
            raise TargetError("refused: the target changed: %s" % self.path)

    def adopt_created(self, fd):
        """Make the directory just created in the held parent the held target.

        `fd` is the new directory opened without following links. The parent's descriptor is
        closed and the state becomes ``new-empty``.
        """
        info = os.fstat(fd)
        if self.fd is not None:
            os.close(self.fd)
        self.fd = fd
        self.state = "new-empty"
        self.created = True
        self._identity = (info.st_dev, info.st_ino)

    def has_incomplete_marker(self):
        """True when ``.workbench/local/incomplete`` exists; links are never followed."""
        if self.state == "new-missing":
            return False
        return _marker_present(self._held())


def _marker_present(fd):
    held = []
    try:
        current = fd
        for part in _MARKER[:-1]:
            info = _lstat_at(part, current)
            if info is None:
                return False
            if not stat.S_ISDIR(info.st_mode):
                return False
            current = _open_dir_at(part, current)
            held.append(current)
        return _lstat_at(_MARKER[-1], current) is not None
    except OSError:
        return False
    finally:
        for each in held:
            os.close(each)


# --- classifying --------------------------------------------------------------


def _real_dir_at(name, dirfd):
    info = _lstat_at(name, dirfd)
    return info is not None and stat.S_ISDIR(info.st_mode)


def _classify(fd, resolved):
    names = set(os.listdir(fd))
    if ".workbench" in names and _real_dir_at(".workbench", fd) and _marker_present(fd):
        raise UnfinishedMarker(
            "refused: an unfinished install or upgrade is here (.workbench/local/incomplete "
            "exists), so this is not an existing project: %s" % resolved)
    if not names:
        return "new-empty"
    git = _lstat_at(".git", fd) if ".git" in names else None
    if git is not None and not stat.S_ISDIR(git.st_mode):
        raise TargetError("refused: .git is not a real directory (a file or link is not "
                          "accepted): %s" % resolved)
    if names == {".git"}:
        return "new-git"
    if git is not None and ".workbench" in names:
        work = _lstat_at(".workbench", fd)
        if not stat.S_ISDIR(work.st_mode):
            raise TargetError("refused: .workbench is not a real directory: %s" % resolved)
        inner = _open_dir_at(".workbench", fd)
        try:
            manifest = _lstat_at("manifest.json", inner)
            if manifest is None or not stat.S_ISREG(manifest.st_mode):
                raise TargetError("refused: .workbench/manifest.json is not a regular file: %s"
                                  % resolved)
            local = _lstat_at("local", inner)
            if local is not None and not stat.S_ISDIR(local.st_mode):
                raise TargetError("refused: .workbench/local is not a real directory: %s"
                                  % resolved)
        finally:
            os.close(inner)
        return "existing"
    raise TargetError("refused: the directory holds other content and is not a project: %s"
                      % resolved)


# --- opening ------------------------------------------------------------------


def open_target(spelling, store_root, home=None):
    """Inspect, resolve once, open and classify a target; return a held ``Target``.

    Raises TargetError naming the place and the reason. Nothing is created. `home` replaces
    ``HOME`` for the refused-place check; the account database's home is always checked too.
    """
    safefs.require_support()
    if spelling == "":
        raise TargetUsage("the target is an empty string")
    absolute = _absolute(spelling)
    if _is_link(absolute):
        raise TargetError("refused: the target is a symbolic link; give the real path: %s"
                          % absolute)
    resolved = os.path.realpath(absolute)
    try:
        info = os.lstat(resolved)
    except FileNotFoundError:
        info = None
    except OSError as exc:
        raise TargetError("refused: cannot inspect the target: %s: %s"
                          % (resolved, exc.strerror or exc))
    if info is not None and not stat.S_ISDIR(info.st_mode):
        raise TargetError("refused: the target is not a directory: %s" % resolved)
    _check_places(resolved, info is not None, store_root, home)
    name = os.path.basename(resolved)
    if info is None:
        opened, state = _open_parent(resolved)
    else:
        opened, state = _open_held(resolved, info), None
    fd, held = opened
    try:
        if state is None:
            state = _classify(fd, resolved)
        return Target(resolved, state, fd, name, held)
    except UnfinishedMarker as exc:
        try:
            exc.report = _examination(Target(resolved, "existing", fd, name, held), store_root)
        finally:
            os.close(fd)
        raise
    except BaseException:
        os.close(fd)
        raise


def _examination(held, store_root):
    """The lines that describe what a marked project holds; never raises."""
    try:
        return unfinished.render(unfinished.examine(projectfs.Writer(held), store_root))
    except Exception as exc:
        return ["the marker could not be examined: %s" % display.ascii_text(str(exc))[:200]]


def write_refusal(err, exc):
    """Print a refusal for a ``TargetError`` and return exit code 1. Every command uses this, so
    the report a marked target carries reads the same everywhere."""
    err.write("refused: %s\n" % display.clean(str(exc)).replace("refused: ", "", 1))
    for line in getattr(exc, "report", ()):
        err.write("  %s\n" % display.clean(line))
    return 1


def _open_held(resolved, info):
    try:
        fd = os.open(resolved, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            raise TargetError("refused: the target is not a real directory: %s" % resolved)
        raise TargetError("refused: cannot open the target: %s: %s" % (resolved, exc.strerror or exc))
    held = os.fstat(fd)
    if (held.st_dev, held.st_ino) != (info.st_dev, info.st_ino):
        os.close(fd)
        raise TargetError("refused: the target changed while it was opened: %s" % resolved)
    return fd, held


def _open_parent(resolved):
    parent = os.path.dirname(resolved)
    try:
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise TargetError("refused: the target does not exist and its parent is not usable "
                          "(the installer does not create a chain of directories): %s: %s"
                          % (resolved, exc.strerror or exc))
    try:
        held = os.fstat(fd)
    except BaseException:
        os.close(fd)
        raise
    return (fd, held), "new-missing"

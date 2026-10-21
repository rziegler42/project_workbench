"""The guarded store: ``~/.config/project-workbench/``.

It holds what the agent must not forge: approvals, pinned hashes and the owner's
personal settings (see ``docs/specs/trust-and-approval.md``). Every command calls
``Store.ensure`` first. It creates what is missing and changes nothing else, so a
second call is a no-op.

Checks and limits, recorded on purpose:

* The location is fixed: the account's home directory plus ``.config/project-workbench``.
  No workbench environment variable moves it, because a variable the agent can set in
  a command would let it point the workbench at a store it controls. ``HOME`` itself is
  honoured by the operating system, which is the same-account limit the spec states. The
  root is an argument so tests use a temporary one; the command line never exposes it.
* The store directory and the directories ``ensure`` makes directly below it must be
  real directories (not symbolic links), owned by the current user, with mode exactly
  ``0700`` (so no group, other, setgid or sticky bits). Anything else is refused and named; nothing is
  repaired silently. Ancestors of the store may be symbolic links, because
  ``~/.config`` is often one.
* Directories deeper than that are made by the safe writer with the process umask. They
  sit inside a ``0700`` directory, so nobody else can reach them.
* Reads and writes go through ``safefs`` only: no-follow, descriptor-relative, atomic.
  The store is a mechanical barrier, not an operating-system one; it runs under the
  owner's account.
"""

import os
import stat

from .wbkit import safefs

LAYOUT = ("packages", "cache", "projects", "bin")
DIR_MODE = 0o700


class StoreError(safefs.SafeFsError):
    """The store is missing something it needs, or is in a state that is not safe."""


def _current_uid():
    return os.geteuid()


def default_root():
    home = os.path.expanduser("~")
    if not os.path.isabs(home):
        raise StoreError("cannot find the home directory for the guarded store")
    return os.path.join(home, ".config", "project-workbench")


def _check_directory(fd, shown):
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode):
        raise StoreError("guarded store entry is not a directory: %s" % shown)
    if info.st_uid != _current_uid():
        raise StoreError("guarded store directory is owned by another user: %s" % shown)
    mode = stat.S_IMODE(info.st_mode)
    if mode & 0o077:
        raise StoreError("guarded store directory is open to other users (mode %04o, "
                         "expected 0700): %s" % (mode, shown))
    if mode != DIR_MODE:
        raise StoreError("guarded store directory has an unexpected mode (%04o, "
                         "expected 0700): %s" % (mode, shown))


class Tree:
    """A directory read through the no-follow layer. It has no way to write."""

    what = "directory"

    def __init__(self, root):
        if not isinstance(root, str) or not os.path.isabs(root) or "\0" in root:
            raise StoreError("the %s path is not a usable absolute path: %r" % (self.what, root))
        self.root = root

    def kind(self, rel):
        """What is at `rel`: None when absent, else "file", "dir", "symlink" or "other".

        Every directory on the way is opened with no-follow flags, so a link planted
        inside the store is refused, not followed. Only the last component may be a link
        and it is reported as one.
        """
        parts = safefs.validate_relpath(rel)
        fds = []
        with safefs.Root(self.root, self.what) as root:
            try:
                current = root._live_fd()
                shown = self.root
                for part in parts[:-1]:
                    shown = shown + "/" + part
                    try:
                        os.stat(part, dir_fd=current, follow_symlinks=False)
                    except FileNotFoundError:
                        return None
                    current = safefs._open_dir(part, current, shown)
                    fds.append(current)
                try:
                    info = os.stat(parts[-1], dir_fd=current, follow_symlinks=False)
                except FileNotFoundError:
                    return None
                return safefs.classify(info.st_mode)
            except OSError as exc:
                raise StoreError("cannot look at %s/%s: %s" % (self.root, rel, exc.strerror or exc))
            finally:
                for fd in fds:
                    os.close(fd)

    def read(self, rel):
        with safefs.Root(self.root, self.what) as root:
            return root.read_file(rel)


class Store(Tree):
    what = "guarded store"

    def ensure(self):
        """Create the store and its directories if they are missing; refuse a bad one."""
        safefs.require_support()
        try:
            os.makedirs(os.path.dirname(self.root), exist_ok=True)
            try:
                os.mkdir(self.root, DIR_MODE)
            except FileExistsError:
                pass
        except OSError as exc:
            raise StoreError("cannot create the guarded store %s: %s" % (self.root, exc.strerror or exc))
        fd = safefs.open_root(self.root, "guarded store")
        try:
            _check_directory(fd, self.root)
            for name in LAYOUT:
                shown = "%s/%s" % (self.root, name)
                try:
                    os.mkdir(name, DIR_MODE, dir_fd=fd)
                except FileExistsError:
                    pass
                except OSError as exc:
                    raise StoreError("cannot create %s: %s" % (shown, exc.strerror or exc))
                child = safefs._open_dir(name, fd, shown)
                try:
                    _check_directory(child, shown)
                finally:
                    os.close(child)
        finally:
            os.close(fd)

    def write(self, rel, data):
        safefs.write_tree(self.root, {rel: data})

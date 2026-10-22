"""Running another module's pinned command from a helper, through the launcher.

``run_command`` starts ``wb run [--provides <capability>] <command> <arguments>`` and nothing else. It
does not decide whether the command may run: the launcher does, from the project's manifest and the
owner's pin (``docs/specs/module-boundary.md``), so a command that is not installed, declared, pinned,
unchanged and (with `provides`) provided by its module is refused there and nothing runs.

What this module does:

* finds ``wb`` only in a ``PATH`` entry that is absolute and outside the project, and does not accept a
  file that resolves into the project;
* gives it an environment built here from a short list of the caller's variables and that ``PATH``, so
  no ``GIT_*`` variable, token or ``LD_*`` variable of the caller reaches the command;
* passes the command and every argument as one literal argument, with no shell;
* writes the standard input it is given, reads the standard output to a bound and keeps the end of
  the standard error, with a time limit that kills the command's whole process group.

What comes back is data. The caller validates it and follows nothing in it.
"""

import collections
import os
import re
import selectors
import signal
import subprocess
import time

NAME = r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}"
CAPABILITY = r"[a-z0-9][a-z0-9:._-]{0,63}"

# The caller's variables the command may see: `HOME` finds the guarded store, and the rest are what a
# program that prints text and reads its own sign-in state expects.
KEPT = ("HOME", "XDG_CONFIG_HOME", "USER", "LOGNAME", "LANG", "TZ", "TERM", "TMPDIR")

MAX_INPUT = 1048576
MAX_ARGUMENTS = 64
MAX_ARGUMENT = 4096
STDERR_KEPT = 4096

Result = collections.namedtuple("Result", "code stdout stderr over timed_out")


class CallError(Exception):
    """Nothing was run; the message says why."""


def is_inside(path, boundary):
    """Whether `path`, with links resolved, is `boundary` or below it."""
    path, boundary = os.path.realpath(path), os.path.realpath(boundary)
    return path == boundary or path.startswith(boundary.rstrip(os.sep) + os.sep)


def trusted_entries(boundary):
    """The ``PATH`` entries that are absolute and outside `boundary`: never "", "." or a relative one."""
    return [entry for entry in os.environ.get("PATH", "").split(os.pathsep)
            if entry and os.path.isabs(entry) and not is_inside(entry, boundary)]


def trusted_which(name, boundary):
    """The first executable file `name` in a trusted entry that does not resolve into `boundary`."""
    for entry in trusted_entries(boundary):
        candidate = os.path.join(entry, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK) \
                and not is_inside(candidate, boundary):
            return candidate
    return None


def environment(boundary):
    """The environment the command runs in: the kept variables of the caller, its ``LC_*`` variables and
    the trusted ``PATH``."""
    env = {name: os.environ[name] for name in KEPT if name in os.environ}
    env.update({name: value for name, value in os.environ.items() if name.startswith("LC_")})
    env["PATH"] = os.pathsep.join(trusted_entries(boundary))
    return env


def _kill(process):
    """Stop the command and anything it started in its own process group."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        process.kill()
    except ProcessLookupError:
        pass


def _check(root, command, arguments, stdin, limit, timeout, provides):
    if not isinstance(root, str) or not os.path.isabs(root):
        raise CallError("the project root must be an absolute path")
    if not isinstance(command, str) or not re.fullmatch(NAME, command):
        raise CallError("the command name is letters, digits and ._+-, at most 64 characters")
    if provides is not None and (not isinstance(provides, str) or not re.fullmatch(CAPABILITY, provides)):
        raise CallError("the capability name is not usable")
    if (not isinstance(arguments, (list, tuple)) or len(arguments) > MAX_ARGUMENTS
            or any(not isinstance(a, str) or "\0" in a or len(a) > MAX_ARGUMENT for a in arguments)):
        raise CallError("the arguments are at most %d strings of at most %d characters without a NUL"
                        % (MAX_ARGUMENTS, MAX_ARGUMENT))
    if not isinstance(stdin, bytes) or len(stdin) > MAX_INPUT:
        raise CallError("the standard input is at most %d bytes" % MAX_INPUT)
    if type(limit) is not int or limit < 1 or isinstance(timeout, bool) \
            or not isinstance(timeout, (int, float)) or not 0 < timeout <= 86400:
        raise CallError("the output limit or the time limit is not usable")


def run_command(root, command, arguments=(), *, stdin=b"", limit, timeout, provides=None, cwd=None):
    """Run ``wb run [--provides <provides>] <command> <arguments>`` from `cwd` (default `root`) and return
    ``Result(code, stdout, stderr, over, timed_out)``.

    `stdout` is at most `limit` bytes, `stderr` the last ``STDERR_KEPT`` bytes, `over` says the output
    passed the limit and `timed_out` that `timeout` seconds passed; the command and its process group
    have been stopped in both cases. A refusal by the launcher is code 1 and a ``refused:`` line in
    `stderr`, and the helper's own exit code is returned as it is. Raises ``CallError`` when nothing was
    started: a bad argument, or no ``wb`` outside `root`."""
    _check(root, command, arguments, stdin, limit, timeout, provides)
    arguments = list(arguments)
    wb = trusted_which("wb", root)
    if wb is None:
        raise CallError("the `wb` launcher was not found in an absolute PATH entry outside the project; "
                        "nothing was run")
    argv = [wb, "run"] + (["--provides", provides] if provides is not None else []) + [command] + arguments
    try:
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, cwd=cwd or root, env=environment(root),
                                   start_new_session=True)
    except (OSError, ValueError) as exc:
        raise CallError("the launcher could not be started: %s" % (getattr(exc, "strerror", None) or exc))
    out, err = bytearray(), bytearray()
    over = timed_out = False
    pending = memoryview(stdin)
    try:
        os.set_blocking(process.stdin.fileno(), False)
        with selectors.DefaultSelector() as pipes:
            pipes.register(process.stdout, selectors.EVENT_READ, out)
            pipes.register(process.stderr, selectors.EVENT_READ, err)
            if pending:
                pipes.register(process.stdin, selectors.EVENT_WRITE, None)
            else:
                process.stdin.close()
            deadline = time.monotonic() + timeout
            while (process.stdout in pipes.get_map() or process.stderr in pipes.get_map()) and not over:
                left = deadline - time.monotonic()
                if left <= 0:
                    timed_out = True
                    break
                for key, _ in pipes.select(min(left, 0.2)):
                    if key.data is None:
                        try:
                            pending = pending[os.write(key.fileobj.fileno(), pending[:65536]):]
                        except BlockingIOError:
                            continue
                        except BrokenPipeError:
                            pending = pending[len(pending):]
                        if not pending:
                            pipes.unregister(key.fileobj)
                            process.stdin.close()
                        continue
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        pipes.unregister(key.fileobj)
                    elif key.data is out:
                        out += chunk
                        over = len(out) > limit
                    else:
                        err += chunk
                        del err[:-STDERR_KEPT]
        _kill(process)  # also what a command that has exited left running in its group
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _kill(process)
            process.wait()
        code = process.returncode
        return Result(code if code >= 0 else 128 - code, bytes(out[:limit]), bytes(err), over, timed_out)
    finally:
        if process.poll() is None:  # an interrupt: the command is in its own session, so it would run on
            _kill(process)
            process.wait()
        for pipe in (process.stdin, process.stdout, process.stderr):
            try:
                pipe.close()
            except (OSError, ValueError):
                pass

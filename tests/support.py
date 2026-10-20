"""Shared test helpers."""

import unittest.mock

from workbench import store


def forbid_real_store(case):
    """Fail the test if code asks for the real store location.

    Tests pass a temporary store root, so nothing should call ``default_root``.
    """
    def refuse():
        raise AssertionError("a test reached the real guarded store location")

    patcher = unittest.mock.patch.object(store, "default_root", refuse)
    patcher.start()
    case.addCleanup(patcher.stop)
    # No other `wb` on this machine's PATH (possibly the owner's own) may change what a test
    # prints; the tests of that warning turn the real lookup back on.
    from workbench import launch
    finder = unittest.mock.patch.object(launch, "find_command", lambda name: None)
    finder.start()
    case.addCleanup(finder.stop)


def clean_path():
    """This machine's PATH without any directory that holds a `wb`, for child processes."""
    import os
    keep = [d for d in os.environ.get("PATH", "").split(os.pathsep)
            if not (d and os.path.exists(os.path.join(d, "wb")))]
    return os.pathsep.join(keep)


def drive_pty(case, command, env, cwd, answer=None, prompt=b"> ", between=None,
              stdin="pty", stdout="pty", timeout=30):
    """Run `command` in a child whose terminals are real pseudo-terminals and type `answer`.

    Returns ``(exit code, terminal output, standard error)``. `between` runs once the prompt
    has appeared and before the answer is typed.
    """
    import os
    import pty
    import select
    import subprocess
    import time

    master, slave = pty.openpty()
    proc = subprocess.Popen(
        command, stdin=slave if stdin == "pty" else subprocess.PIPE,
        stdout=slave if stdout == "pty" else subprocess.PIPE,
        stderr=subprocess.PIPE, env=env, cwd=cwd)
    os.close(slave)
    output, sent = b"", False
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            ready, _, _ = select.select([master], [], [], 0.2)
            if not ready:
                if proc.poll() is not None:
                    break
                continue
            try:
                chunk = os.read(master, 4096)
            except OSError:
                chunk = b""
            if not chunk:
                break
            output += chunk
            if not sent and prompt in output:
                sent = True
                if between:
                    between()
                os.write(master, (answer + "\n").encode())
        else:
            proc.kill()
            case.fail("the command did not finish: %r" % output[-300:])
        if stdin != "pty":
            proc.stdin.close()
        code = proc.wait(timeout=timeout)
        piped = proc.stdout.read() if stdout != "pty" else b""
        error = proc.stderr.read()
    finally:
        os.close(master)
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        if proc.stdin is not None:
            proc.stdin.close()
        proc.stderr.close()
        if stdout != "pty":
            proc.stdout.close()
    return code, (output + piped).decode("utf-8", "replace"), error.decode("utf-8", "replace")

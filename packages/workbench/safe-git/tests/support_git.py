"""Real repositories for the tests of the helper's git runner, and a `git` that records how it is run.

Fixtures are made with the real `git` and a clean environment, so nothing of the developer's own
configuration is read. The recording `git` is a shell script that appends its arguments and its
environment to a log and then runs the real one."""

import os
import shutil
import subprocess
import tempfile
import unittest

REAL_GIT = shutil.which("git")
needs_git = unittest.skipUnless(REAL_GIT, "git was not found")

_CLEAN = {"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "GIT_CONFIG_GLOBAL": os.devnull,
          "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
          "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def git(where, *args, check=True):
    """Run the real git in `where` with a clean environment; return the completed process."""
    env = dict(_CLEAN)
    env["HOME"] = tempfile.gettempdir()
    result = subprocess.run([REAL_GIT, *args], cwd=where, env=env, capture_output=True, text=True)
    if check and result.returncode:
        raise AssertionError("git %s failed: %s" % (" ".join(args), result.stderr))
    return result


class Repo(unittest.TestCase):
    """A repository with one commit and the scratch directories a test needs."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.scratch = os.path.realpath(holder.name)
        self.repo = os.path.join(self.scratch, "repo")
        os.mkdir(self.repo)
        git(self.repo, "init", "-q")
        self.write("a.txt", "one\n")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-q", "-m", "first")
        self.outside = os.path.join(self.scratch, "tools")
        os.mkdir(self.outside)
        self.log = os.path.join(self.scratch, "git.log")

    def write(self, rel, data, mode=None):
        full = os.path.join(self.repo, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w" if isinstance(data, str) else "wb") as handle:
            handle.write(data)
        if mode is not None:
            os.chmod(full, mode)
        return full

    def config(self, key, value):
        git(self.repo, "config", key, value)

    def recording_git(self, directory=None):
        """Put a `git` that logs its arguments and environment, then runs the real one, in `directory`
        (default: a directory outside the repository). Returns the directory."""
        directory = directory or self.outside
        script = os.path.join(directory, "git")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\n{ printf 'RUN\\n'; for a in \"$@\"; do printf 'ARG:%%s\\n' \"$a\"; done;"
                         " env; printf 'END\\n'; } >> '%s'\n"
                         "exec '%s' \"$@\"\n" % (self.log, REAL_GIT))
        os.chmod(script, 0o755)
        return directory

    def runs(self):
        """The logged runs: a list of ``(arguments, environment)``."""
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        found = []
        for block in text.split("END\n"):
            lines = [line for line in block.splitlines() if line]
            if not lines or lines[0] != "RUN":
                continue
            arguments = [line[4:] for line in lines[1:] if line.startswith("ARG:")]
            environment = dict(line.split("=", 1) for line in lines[1:]
                               if not line.startswith("ARG:") and "=" in line)
            found.append((arguments, environment))
        return found

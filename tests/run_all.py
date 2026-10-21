"""Run every test: the repository's own `tests/` and each module's `packages/*/*/tests/`.

    python3 -B -W error tests/run_all.py

Each directory is discovered as its own root, with that directory as both the start and the top-level
directory (module directories have hyphens and are not import packages). Between roots the modules the
previous root loaded are dropped, so two modules may each have a `test_helper.py`. The repository root is
on the search path so a module's tests can `from tests import support`. Nothing writes bytecode: a
`__pycache__` in a module fails its verification. The exit status is non-zero if any test fails, if a
test file cannot be imported, or if a tests directory holds no test that ran (all skipped counts).
"""

import os
import sys
import unittest

sys.dont_write_bytecode = True

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def roots(repo):
    """`(name, path)` for the repository's `tests/` and each `packages/*/*/tests/`, in a fixed order.
    A symbolic link in place of a tests directory comes back as `(name, None)`."""
    found = [("tests", os.path.join(repo, "tests"))]
    packages = os.path.join(repo, "packages")
    if os.path.isdir(packages):
        for package in sorted(entry for entry in os.listdir(packages)
                              if os.path.isdir(os.path.join(packages, entry))):
            for module in sorted(entry for entry in os.listdir(os.path.join(packages, package))
                                 if os.path.isdir(os.path.join(packages, package, entry))):
                path = os.path.join(packages, package, module, "tests")
                name = "/".join(("packages", package, module, "tests"))
                if os.path.islink(path):
                    found.append((name, None))
                elif os.path.isdir(path):
                    found.append((name, path))
    return found


def forget(path):
    """Drop every module that was loaded from under `path`, and `path` from the search path."""
    prefix = path + os.sep
    for name, module in list(sys.modules.items()):
        where = getattr(module, "__file__", None)
        if where and os.path.abspath(where).startswith(prefix):
            del sys.modules[name]
            parent, _, child = name.rpartition(".")
            if parent in sys.modules and hasattr(sys.modules[parent], child):
                delattr(sys.modules[parent], child)
    while path in sys.path:
        sys.path.remove(path)


def run_root(name, path, stream):
    """Run one root; return `(tests run, passed)`."""
    stream.write("== %s\n" % name)
    stream.flush()
    if path is None:
        stream.write("refused: %s is a symbolic link, not a directory\n" % name)
        return 0, False
    suite = unittest.defaultTestLoader.discover(path, pattern="test_*.py", top_level_dir=path)
    try:
        result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    finally:
        forget(path)
    if result.testsRun == len(result.skipped):
        stream.write("refused: %s holds no tests that ran\n" % name)
        return 0, False
    return result.testsRun, result.wasSuccessful()


def main(repo=REPO, stream=sys.stdout):
    if repo not in sys.path:
        sys.path.insert(0, repo)
    total, failed = 0, []
    for name, path in roots(repo):
        count, passed = run_root(name, path, stream)
        total += count
        if not passed:
            failed.append(name)
    stream.write("\nRan %d tests in %d roots\n" % (total, len(roots(repo))))
    if failed:
        stream.write("FAILED: %s\n" % ", ".join(failed))
        return 1
    stream.write("OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

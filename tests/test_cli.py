import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import support
from workbench import cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "sample-package")

# The guarded store of the test in progress, set by CliBase.setUp. It lives beside the
# package directory, not in it, so a run can be shown to leave the package untouched.
STORE_ROOT = [None]


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(list(argv), out, err, store_root=STORE_ROOT[0])
    return code, out.getvalue(), err.getvalue()


def snapshot(top):
    found = {}
    for base, dirs, files in os.walk(top):
        for name in dirs:
            full = os.path.join(base, name)
            found[os.path.relpath(full, top)] = "dir"
        for name in files:
            full = os.path.join(base, name)
            with open(full, "rb") as handle:
                found[os.path.relpath(full, top)] = (hashlib.sha256(handle.read()).hexdigest(),
                                                     os.stat(full).st_mtime_ns)
    return found


class CliBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.path = os.path.join(self.base, "pkg")
        shutil.copytree(FIXTURE, self.path)
        support.forbid_real_store(self)
        self.home_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.home_tmp.cleanup)
        self.home = os.path.realpath(self.home_tmp.name)
        self.store_root = os.path.join(self.home, ".config", "project-workbench")
        STORE_ROOT[0] = self.store_root
        self.addCleanup(STORE_ROOT.__setitem__, 0, None)

    def child_env(self, **extra):
        # A child process finds the store from HOME, so it gets a temporary one.
        return dict(os.environ, HOME=self.home, PATH=support.clean_path(), **extra)


class VerifyTest(CliBase):
    def test_valid_package_exits_0_with_a_line_per_module(self):
        code, out, err = run("verify", self.path)
        self.assertEqual((code, err), (0, ""))
        lines = out.splitlines()
        self.assertEqual(len(lines), 2, out)
        self.assertTrue(lines[0].startswith("sample/sample-harness 1.0.0 declaration "))
        self.assertIn("sample/sample-notes 1.2.0", lines[1])
        words = lines[1].split()
        self.assertEqual([len(words[3]), len(words[5])], [12, 12])

    def test_selection_prints_the_install_order(self):
        code, out, err = run("verify", self.path, "--select", "sample-notes", "sample-harness")
        self.assertEqual(code, 0, err)
        self.assertIn("install order: sample/sample-harness sample/sample-notes", out)

    def test_missing_helper_is_a_warning_not_a_refusal(self):
        rel = os.path.join(self.path, "sample-notes", "module.json")
        with open(rel) as handle:
            decl = json.load(handle)
        decl["helpers"] = ["no-such-tool-for-workbench-tests"]
        with open(rel, "w") as handle:
            json.dump(decl, handle)
        code, out, err = run("verify", "--dir", self.path, "--select", "sample-harness",
                             "sample-notes")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("warning: module 'sample-notes' (package 'sample'): helper", out)

    def test_no_harness_required(self):
        args = ("verify", self.path, "--select", "sample-notes")
        code, _, err = run(*args)
        self.assertEqual(code, 1)
        self.assertIn("harness-count", err)
        self.assertEqual(run(*args, "--no-harness-required")[0], 0)

    def test_module_level_refusal_names_module_and_rule(self):
        with open(os.path.join(self.path, "sample-notes", "stray.txt"), "w") as handle:
            handle.write("x")
        code, out, err = run("verify", self.path)
        self.assertEqual((code, out), (1, ""))
        self.assertIn("module 'sample-notes' (package 'sample'): unaccounted-file", err)

    def test_package_level_refusal_names_package_and_rule(self):
        with open(os.path.join(self.path, "package.json"), "w") as handle:
            json.dump({"name": "sample", "version": "1.0.0", "contract": 9,
                       "modules": []}, handle)
        code, out, err = run("verify", self.path)
        self.assertEqual((code, out), (1, ""))
        self.assertIn("package 'sample': contract", err)

    def test_missing_package_is_a_refusal(self):
        code, _, err = run("verify", os.path.join(self.base, "nowhere"))
        self.assertEqual(code, 1)
        self.assertIn("refused:", err)

    def test_set_refusal_names_the_selection(self):
        code, _, err = run("verify", self.path, "--select", "sample-harness", "nope")
        self.assertEqual(code, 1)
        self.assertIn("selection 'nope': select", err)

    def test_control_characters_are_escaped(self):
        code, _, err = run("verify", self.path, "--select", "x\x1b[31m")
        self.assertEqual(code, 1)
        self.assertNotIn("\x1b", err)

    def test_default_target_is_the_current_directory(self):
        before = os.getcwd()
        self.addCleanup(os.chdir, before)
        os.chdir(self.path)
        code, out, _ = run("verify")
        self.assertEqual(code, 0)
        self.assertIn("sample/sample-notes", out)


class UsageTest(CliBase):
    def test_usage_errors_exit_2(self):
        for argv in ([], ["bogus"], ["verify", "--nope"], ["verify", "a", "b"],
                     ["verify", "--select"], ["verify", ""], ["verify", "--dir", ""],
                     ["verify", ".", "--dir", ""], ["verify", "", "--dir", "."],
                     ["verify", "--sel", "a"], ["verify", "--no-harness"]):
            with self.subTest(argv=argv):
                code, out, err = run(*argv)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("usage:", err)

    def test_preview_usage_is_listed_and_bad_forms_exit_2(self):
        code, out, err = run("preview")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("preview install", err)
        for argv in (["preview", "add"], ["preview", "install"],
                     ["preview", "install", "--select", "a"]):
            with self.subTest(argv=argv):
                code, out, err = run(*argv)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("usage:", err)

    def test_install_usage_is_listed_and_bad_forms_exit_2(self):
        for argv in (["install"], ["install", "--select", "a"], ["install", "x", "y", "--package",
                                                                  "p", "--select", "h"]):
            with self.subTest(argv=argv):
                code, out, err = run(*argv)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("python3 -m workbench install", err)

    def test_install_without_a_terminal_refuses_and_names_preview(self):
        code, out, err = run("install", os.path.join(self.base, "x"), "--package", self.path,
                             "--select", "a")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("refused: install is owner-run", err)
        self.assertFalse(os.path.exists(os.path.join(self.base, "x")))

    def test_two_different_paths_are_refused(self):
        code, _, err = run("verify", self.path, "--dir", os.path.join(self.base, "other"))
        self.assertEqual(code, 2)
        self.assertIn("two different packages", err)

    def test_help_exits_0(self):
        with contextlib.redirect_stdout(io.StringIO()) as shown:
            code, _, _ = run("verify", "-h")
        self.assertEqual(code, 0)
        self.assertIn("--select", shown.getvalue())
        self.assertFalse(os.path.exists(self.store_root))

    def test_same_directory_through_a_symlink_is_the_same_path(self):
        link = os.path.join(self.base, "link")
        os.symlink(self.path, link)
        # Not a usage error: the paths agree. The package itself is refused because its
        # root is a symbolic link.
        code, _, err = run("verify", link, "--dir", self.path)
        self.assertEqual(code, 1)
        self.assertIn("symbolic link", err)

    def test_dot_dot_through_a_symlink_is_resolved(self):
        elsewhere = os.path.join(self.base, "elsewhere", "deep")
        os.makedirs(elsewhere)
        link = os.path.join(self.base, "lnk")
        os.symlink(elsewhere, link)
        # lnk/../pkg is elsewhere/pkg on disk, not pkg beside lnk.
        code, _, err = run("verify", os.path.join(link, "..", "pkg"), "--dir", self.path)
        self.assertEqual(code, 2)

    def test_the_same_path_given_both_ways_is_accepted(self):
        self.assertEqual(run("verify", self.path, "--dir", self.path)[0], 0)
        self.assertEqual(run("verify", self.path, "--dir", self.path + "/")[0], 0)


class StoreTest(CliBase):
    def test_a_command_creates_the_store_first(self):
        self.assertFalse(os.path.exists(self.store_root))
        self.assertEqual(run("verify", self.path)[0], 0)
        self.assertEqual(sorted(os.listdir(self.store_root)),
                         ["bin", "cache", "packages", "projects", "settings"])

    def test_a_damaged_settings_file_is_reported_and_kept(self):
        self.assertEqual(run("verify", self.path)[0], 0)
        path = os.path.join(self.store_root, "settings")
        with open(path, "wb") as handle:
            handle.write(b"{ broken")
        code, out, err = run("verify", self.path)
        self.assertEqual((code, err), (0, ""))
        self.assertIn("warning: settings: settings are damaged", out)
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), b"{ broken")

    def test_hostile_settings_never_raise_out_of_main(self):
        self.assertEqual(run("verify", self.path)[0], 0)
        path = os.path.join(self.store_root, "settings")
        hostile = [b"[" * 100000, b'{"version": ' + b"9" * 5000 + b"}", b'{"a": "\\ud800"}',
                   b"\xff\xfe\x00", b"x" * (2 * 1024 * 1024), b'{"version": 1, "evil\\u001b[31m": 1}']
        for data in hostile:
            with self.subTest(data=data[:20]):
                with open(path, "wb") as handle:
                    handle.write(data)
                code, out, err = run("verify", self.path)
                self.assertEqual(code, 0, err)
                self.assertNotIn("\x1b", out + err)

    def test_a_damaged_settings_file_is_reported_on_stderr_when_refused(self):
        self.assertEqual(run("verify", self.path)[0], 0)
        with open(os.path.join(self.store_root, "settings"), "wb") as handle:
            handle.write(b"[]")
        code, out, err = run("verify", os.path.join(self.base, "nowhere"))
        self.assertEqual((code, out), (1, ""))
        self.assertIn("warning: settings: settings are damaged", err)

    def test_the_store_is_created_even_when_the_package_is_refused(self):
        self.assertEqual(run("verify", os.path.join(self.base, "nowhere"))[0], 1)
        self.assertTrue(os.path.isdir(self.store_root))

    def test_usage_errors_do_not_create_the_store(self):
        self.assertEqual(run("verify", "a", "b")[0], 2)
        self.assertFalse(os.path.exists(self.store_root))

    def test_a_bad_store_stops_the_command_before_verifying(self):
        os.makedirs(self.store_root, mode=0o755)
        os.chmod(self.store_root, 0o755)
        code, out, err = run("verify", self.path)
        self.assertEqual((code, out), (1, ""))
        self.assertIn("refused: guarded store directory is open to other users", err)

    def test_a_child_process_uses_home_for_the_store(self):
        env = self.child_env(PYTHONPATH=ROOT)
        done = subprocess.run([sys.executable, "-B", "-m", "workbench", "verify", self.path],
                              cwd=self.base, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(os.path.isdir(self.store_root))


class ReadOnlyTest(CliBase):
    # The store is outside self.base on purpose: these snapshots show that a run adds
    # nothing to the package's surroundings. That the store is created is StoreTest's job.

    def test_accepted_run_changes_nothing_and_creates_nothing(self):
        before = snapshot(self.base)
        self.assertEqual(run("verify", self.path, "--select", "sample-harness",
                             "sample-notes")[0], 0)
        self.assertEqual(snapshot(self.base), before)

    def test_refused_run_changes_nothing_and_creates_nothing(self):
        with open(os.path.join(self.path, "sample-notes", "stray.txt"), "w") as handle:
            handle.write("x")
        before = snapshot(self.base)
        self.assertEqual(run("verify", self.path)[0], 1)
        self.assertEqual(snapshot(self.base), before)

    def test_module_run_leaves_no_bytecode_or_file_in_the_working_directory(self):
        cwd = os.path.join(self.base, "cwd")
        os.makedirs(cwd)
        env = self.child_env(PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE="1")
        before = snapshot(self.base)
        done = subprocess.run([sys.executable, "-B", "-m", "workbench", "verify", self.path],
                              cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(snapshot(self.base), before)

    def test_module_exit_codes(self):
        env = self.child_env(PYTHONPATH=ROOT)
        for argv, expected in ((["verify", self.path], 0), (["verify", "a", "b"], 2),
                               ([], 2)):
            with self.subTest(argv=argv):
                done = subprocess.run([sys.executable, "-B", "-m", "workbench"] + argv,
                                      cwd=self.base, env=env, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
                self.assertEqual(done.returncode, expected)


if __name__ == "__main__":
    unittest.main()

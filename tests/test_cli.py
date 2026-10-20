import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from workbench import cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "sample-package")


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(list(argv), out, err)
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
        code, out, err = run("verify", "--dir", self.path, "--select", "sample-harness",
                             "sample-notes")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

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
                     ["verify", "--select"], ["verify", ""], ["verify", "--dir", ""]):
            with self.subTest(argv=argv):
                code, out, err = run(*argv)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("usage:", err)

    def test_two_different_paths_are_refused(self):
        code, _, err = run("verify", self.path, "--dir", os.path.join(self.base, "other"))
        self.assertEqual(code, 2)
        self.assertIn("two different packages", err)

    def test_the_same_path_given_both_ways_is_accepted(self):
        self.assertEqual(run("verify", self.path, "--dir", self.path)[0], 0)
        self.assertEqual(run("verify", self.path, "--dir", self.path + "/")[0], 0)


class ReadOnlyTest(CliBase):
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
        env = dict(os.environ, PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE="1")
        before = snapshot(self.base)
        done = subprocess.run([sys.executable, "-B", "-m", "workbench", "verify", self.path],
                              cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(snapshot(self.base), before)

    def test_module_exit_codes(self):
        env = dict(os.environ, PYTHONPATH=ROOT)
        for argv, expected in ((["verify", self.path], 0), (["verify", "a", "b"], 2),
                               ([], 2)):
            with self.subTest(argv=argv):
                done = subprocess.run([sys.executable, "-B", "-m", "workbench"] + argv,
                                      cwd=self.base, env=env, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
                self.assertEqual(done.returncode, expected)


if __name__ == "__main__":
    unittest.main()

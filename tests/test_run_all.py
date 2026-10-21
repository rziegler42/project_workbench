"""`tests/run_all.py`: the one command that runs the repository's tests and every module's tests."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "run_all.py")

PASSING = (
    "import unittest\n\n\n"
    "class T(unittest.TestCase):\n"
    "    def test_%s(self):\n"
    "        self.assertEqual(%r, %r)\n\n\n"
    "if __name__ == '__main__':\n"
    "    unittest.main()\n")
FAILING = PASSING.replace("assertEqual(%r, %r)", "assertEqual(1, 2)")


class RunAllTest(unittest.TestCase):
    """Each test builds a small repository: `tests/run_all.py` and a few module test directories."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.repo = os.path.realpath(holder.name)
        os.makedirs(os.path.join(self.repo, "tests"))
        shutil.copy(SCRIPT, os.path.join(self.repo, "tests", "run_all.py"))

    def put(self, rel, text):
        path = os.path.join(self.repo, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def passing(self, rel, name="ok"):
        self.put(rel, PASSING % (name, name, name))

    def run_all(self, *flags):
        # No -B: the script has to stop bytecode itself, as a bare `python3 tests/run_all.py` would.
        env = {key: value for key, value in os.environ.items() if key != "PYTHONDONTWRITEBYTECODE"}
        done = subprocess.run([sys.executable, *flags, os.path.join(self.repo, "tests", "run_all.py")],
                              capture_output=True, text=True, env=env, cwd=self.repo, timeout=60)
        return done.returncode, done.stdout, done.stderr

    def pycaches(self):
        return [base for base, dirs, _ in os.walk(self.repo) if "__pycache__" in dirs]

    def test_it_runs_the_repository_tests_and_each_module_directory_and_names_them(self):
        self.passing("tests/test_root.py", "root")
        self.passing("packages/p/one/tests/test_helper.py", "one")
        self.passing("packages/p/two/tests/test_helper.py", "two")
        code, out, err = self.run_all()
        self.assertEqual(0, code, (out, err))
        for name in ("tests", "packages/p/one/tests", "packages/p/two/tests"):
            self.assertIn("== %s" % name, out + err)
        self.assertIn("3 tests", out + err)

    def test_two_modules_may_each_have_a_test_helper_file(self):
        self.put("packages/p/one/tests/test_helper.py", PASSING % ("a", "a", "a"))
        self.put("packages/p/two/tests/test_helper.py", PASSING % ("b", "b", "b"))
        self.passing("tests/test_root.py", "root")
        code, out, err = self.run_all()
        self.assertEqual(0, code, (out, err))
        # Both ran, not the first one twice.
        self.assertIn("3 tests", out + err)

    def test_a_failure_in_any_root_fails_the_run_and_the_rest_still_run(self):
        self.passing("tests/test_root.py", "root")
        self.put("packages/p/bad/tests/test_bad.py", FAILING % "bad")
        self.passing("packages/p/zed/tests/test_zed.py", "zed")
        code, out, err = self.run_all()
        self.assertNotEqual(0, code)
        self.assertIn("== packages/p/zed/tests", out + err)
        self.assertIn("FAILED", out + err)

    def test_a_test_file_that_cannot_be_imported_fails_the_run(self):
        self.passing("tests/test_root.py", "root")
        self.put("packages/p/m/tests/test_broken.py", "import no_such_module_anywhere\n")
        code, out, err = self.run_all()
        self.assertNotEqual(0, code)

    def test_a_tests_directory_with_no_tests_fails_the_run(self):
        self.passing("tests/test_root.py", "root")
        self.put("packages/p/m/tests/notes.txt", "nothing to run\n")
        code, out, err = self.run_all()
        self.assertNotEqual(0, code)
        self.assertIn("packages/p/m/tests", out + err)

    def test_a_tests_directory_whose_tests_are_all_skipped_fails_the_run(self):
        self.passing("tests/test_root.py", "root")
        self.put("packages/p/m/tests/test_skipped.py",
                 "import unittest\n\n\nclass T(unittest.TestCase):\n    @unittest.skip('never')\n"
                 "    def test_a(self):\n        pass\n")
        code, out, err = self.run_all()
        self.assertNotEqual(0, code)
        self.assertIn("packages/p/m/tests", out + err)

    def test_a_stray_file_beside_the_packages_is_not_a_root(self):
        self.passing("tests/test_root.py", "root")
        self.put("packages/.DS_Store", "x")
        self.put("packages/p/.DS_Store", "x")
        code, out, err = self.run_all()
        self.assertEqual(0, code, (out, err))

    def test_support_imported_by_name_is_fresh_in_each_root(self):
        self.put("tests/support.py", "import itertools\nCOUNT = itertools.count()\n")
        self.put("tests/test_root.py", "import unittest\nfrom tests import support\n\n\n"
                 "class T(unittest.TestCase):\n    def test_a(self):\n"
                 "        self.assertEqual(0, next(support.COUNT))\n")
        self.put("packages/p/m/tests/test_mod.py", "import unittest\nfrom tests import support\n\n\n"
                 "class T(unittest.TestCase):\n    def test_a(self):\n"
                 "        self.assertEqual(0, next(support.COUNT))\n")
        code, out, err = self.run_all()
        self.assertEqual(0, code, (out, err))

    def test_it_leaves_no_bytecode_anywhere_under_the_repository(self):
        self.passing("tests/test_root.py", "root")
        self.passing("packages/p/one/tests/test_helper.py", "one")
        self.assertEqual(0, self.run_all()[0])
        self.assertEqual([], self.pycaches())

    def test_a_module_test_can_import_the_repository_test_support(self):
        self.put("tests/support.py", "VALUE = 7\n")
        self.passing("tests/test_root.py", "root")
        self.put("packages/p/m/tests/test_uses.py",
                 "import unittest\nfrom tests import support\n\n\nclass T(unittest.TestCase):\n"
                 "    def test_value(self):\n        self.assertEqual(7, support.VALUE)\n")
        code, out, err = self.run_all()
        self.assertEqual(0, code, (out, err))

    def test_a_module_directory_without_a_tests_directory_is_not_a_root(self):
        self.passing("tests/test_root.py", "root")
        os.makedirs(os.path.join(self.repo, "packages", "p", "plain", "files"))
        code, out, err = self.run_all()
        self.assertEqual(0, code, (out, err))
        self.assertNotIn("plain", out + err)

    def test_a_symbolic_link_in_place_of_a_tests_directory_fails_the_run(self):
        self.passing("tests/test_root.py", "root")
        os.makedirs(os.path.join(self.repo, "packages", "p", "m"))
        os.symlink(os.path.join(self.repo, "tests"), os.path.join(self.repo, "packages", "p", "m", "tests"))
        code, out, err = self.run_all()
        self.assertNotEqual(0, code)
        self.assertIn("symbolic link", out + err)

    def test_warnings_are_errors_when_the_caller_asks_for_it(self):
        self.put("tests/test_warn.py",
                 "import unittest\nimport warnings\n\n\nclass T(unittest.TestCase):\n"
                 "    def test_warns(self):\n        warnings.warn('careful')\n")
        self.assertNotEqual(0, self.run_all("-W", "error")[0])
        self.assertEqual(0, self.run_all()[0])


if __name__ == "__main__":
    unittest.main()

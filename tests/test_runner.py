"""The runner and the launcher's `kit` parameter (plan `2026-10-21-module-boundary-kit`, increment D).

The helpers here are small Python files that report what they see. The runner is run as the launcher
runs it, `python3 -I workbench/runner.py <kit number> <helper> <arguments...>`, from a directory that
holds hostile files, so what is imported is what the test says."""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

import support
from workbench import launch, pins, store
from workbench.wbkit import safefs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKBENCH = os.path.join(ROOT, "workbench")
RUNNER = os.path.join(WORKBENCH, "runner.py")
API = 1
PROJECT = "a" * 64

REPORT = """\
import json, os, sys
mark = os.environ.get("WB_MARK")
if mark:
    open(mark, "w").close()
import wbkit
import wbkit.display
import wbkit.safefs
print(json.dumps({
    "argv": sys.argv, "path": sys.path, "name": __name__, "api": wbkit.API,
    "kit": wbkit.__file__, "safefs": wbkit.safefs.__file__, "json": json.__file__,
}))
"""
HOSTILE = """\
import os
open(os.environ["WB_HOSTILE"], "a").write(__file__ + "\\n")
"""
HOSTILE_FILES = ("wbkit.py", "json.py", "sitecustomize.py", "usercustomize.py")


class Scratch(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.mark = os.path.join(self.base, "imported")
        self.hostile = os.path.join(self.base, "hostile-ran")

    def directory(self, name):
        path = os.path.join(self.base, name)
        os.makedirs(path, exist_ok=True)
        return path

    def helper(self, text=REPORT, name="helper.py", where=None):
        path = os.path.join(where or self.directory("copy"), name)
        with open(path, "w") as handle:
            handle.write(text)
        return path

    def poisoned(self, name="poison"):
        """A directory holding a file of each name a hostile project could plant."""
        path = self.directory(name)
        for file in HOSTILE_FILES:
            with open(os.path.join(path, file), "w") as handle:
                handle.write(HOSTILE)
        return path

    def run_runner(self, *argv, runner=RUNNER, cwd=None, env=None):
        full = dict(os.environ, WB_MARK=self.mark, WB_HOSTILE=self.hostile)
        full.update(env or {})
        return subprocess.run([sys.executable, "-I", runner, *argv], cwd=cwd or self.base, env=full,
                              capture_output=True, text=True)

    def report(self, *args, **kw):
        done = self.run_runner(str(API), self.helper(), *args, **kw)
        self.assertEqual(0, done.returncode, done.stderr)
        return json.loads(done.stdout)

    def refused(self, done, contains=""):
        self.assertEqual(1, done.returncode, done.stderr)
        self.assertEqual("", done.stdout)
        self.assertTrue(done.stderr.startswith("refused: "), done.stderr)
        self.assertIn(contains, done.stderr)
        self.assertFalse(os.path.exists(self.mark), "the helper was imported")

    def distribution(self, api="API = 1\n", kit=True):
        """A copy of the runner, and of the kit unless `kit` is false, in a directory of their own."""
        path = self.directory("dist%d" % len(os.listdir(self.base)))
        shutil.copy(RUNNER, os.path.join(path, "runner.py"))
        if kit:
            shutil.copytree(os.path.join(WORKBENCH, "wbkit"), os.path.join(path, "wbkit"),
                            ignore=shutil.ignore_patterns("__pycache__"))
            if api is not None:
                with open(os.path.join(path, "wbkit", "__init__.py"), "w") as handle:
                    handle.write(api)
        return os.path.join(path, "runner.py")


class Runs(Scratch):
    def test_the_helper_reaches_the_kit_and_runs_as_main_with_its_arguments(self):
        helper = self.helper()
        done = self.run_runner(str(API), helper, "one", "two words", "--flag", "")
        self.assertEqual(0, done.returncode, done.stderr)
        seen = json.loads(done.stdout)
        self.assertEqual([helper, "one", "two words", "--flag", ""], seen["argv"])
        self.assertEqual("__main__", seen["name"])
        self.assertEqual(API, seen["api"])
        self.assertEqual(os.path.join(WORKBENCH, "wbkit", "__init__.py"), seen["kit"])
        self.assertEqual(os.path.join(WORKBENCH, "wbkit", "safefs.py"), seen["safefs"])

    def test_the_kit_is_the_module_the_installer_imports(self):
        helper = self.helper("import wbkit.safefs, sys\nprint(sys.modules['wbkit'].API, wbkit.safefs.MAX_PATH_CHARS)\n")
        done = self.run_runner(str(API), helper)
        self.assertEqual("%d %d\n" % (API, safefs.MAX_PATH_CHARS), done.stdout, done.stderr)

    def test_no_directory_is_added_to_the_search_path(self):
        seen = self.report()
        baseline = subprocess.run([sys.executable, "-I", "-c", "import json, sys; print(json.dumps(sys.path))"],
                                  capture_output=True, text=True, cwd=self.base).stdout
        self.assertEqual(json.loads(baseline), seen["path"])
        for entry in seen["path"]:
            self.assertNotIn(WORKBENCH, entry)
            self.assertNotIn("wbkit", entry)

    def test_the_rest_of_the_workbench_is_not_importable_by_name(self):
        helper = self.helper("import importlib\n"
                             "for name in ('workbench', 'launch', 'store', 'runner'):\n"
                             "    try:\n"
                             "        importlib.import_module(name)\n"
                             "    except ImportError:\n"
                             "        continue\n"
                             "    raise SystemExit('imported ' + name)\n")
        done = self.run_runner(str(API), helper)
        self.assertEqual((0, ""), (done.returncode, done.stderr))

    def test_exit_codes_reach_the_caller_unchanged(self):
        for code in (0, 1, 2, 3, 77):
            helper = self.helper("import sys\nsys.exit(%d)\n" % code, name="exit%d.py" % code)
            self.assertEqual(code, self.run_runner(str(API), helper).returncode)

    def test_a_signal_that_ends_the_helper_ends_the_runner_the_same_way(self):
        helper = self.helper("import os, signal\nos.kill(os.getpid(), signal.SIGKILL)\n")
        self.assertEqual(-signal.SIGKILL, self.run_runner(str(API), helper).returncode)

    def test_a_text_exit_is_printed_and_exits_1(self):
        done = self.run_runner(str(API), self.helper("raise SystemExit('the reason')\n"))
        self.assertEqual((1, "the reason\n"), (done.returncode, done.stderr))

    def test_an_exception_is_not_hidden(self):
        done = self.run_runner(str(API), self.helper("raise RuntimeError('boom')\n"))
        self.assertEqual(1, done.returncode)
        self.assertIn("Traceback", done.stderr)
        self.assertIn("RuntimeError: boom", done.stderr)
        self.assertFalse(done.stderr.startswith("refused:"))

    def test_standard_input_reaches_the_helper(self):
        helper = self.helper("import sys\nprint(sys.stdin.read().upper())\n")
        done = subprocess.run([sys.executable, "-I", RUNNER, str(API), helper], input="abc", cwd=self.base,
                              capture_output=True, text=True)
        self.assertEqual("ABC\n", done.stdout, done.stderr)


class Hostile(Scratch):
    def assert_nothing_hostile_ran(self, seen):
        self.assertFalse(os.path.exists(self.hostile), "a planted file was imported")
        self.assertEqual(os.path.join(WORKBENCH, "wbkit", "__init__.py"), seen["kit"])
        self.assertNotIn(self.base, seen["json"])

    def test_planted_files_in_the_current_directory_are_never_imported(self):
        self.assert_nothing_hostile_ran(self.report(cwd=self.poisoned()))

    def test_planted_files_in_the_directory_of_the_helper_are_never_imported(self):
        where = self.poisoned("copy")
        helper = self.helper(where=where)
        done = self.run_runner(str(API), helper)
        self.assertEqual(0, done.returncode, done.stderr)
        self.assert_nothing_hostile_ran(json.loads(done.stdout))

    def test_a_hostile_python_path_is_never_used(self):
        where = self.poisoned()
        self.assert_nothing_hostile_ran(self.report(env={"PYTHONPATH": where}))

    def test_other_python_environment_settings_are_ignored(self):
        where = self.poisoned()
        env = {"PYTHONPATH": where, "PYTHONSTARTUP": os.path.join(where, "sitecustomize.py"),
               "PYTHONHOME": os.path.join(self.base, "nowhere"), "PYTHONUSERBASE": where}
        self.assert_nothing_hostile_ran(self.report(cwd=where, env=env))


class Refuses(Scratch):
    def test_a_kit_number_that_differs_is_refused_and_names_both(self):
        done = self.run_runner(str(API + 1), self.helper())
        self.refused(done, "needs kit API %d; this workbench has %d" % (API + 1, API))

    def test_a_kit_number_that_is_not_a_positive_integer_is_refused(self):
        for text in ("0", "-1", "abc", "", "1.0", " 1", "1 ", "+1", "١", "1e0", "9" * 40, "True"):
            self.refused(self.run_runner(text, self.helper()), "not a positive integer")

    def test_a_missing_kit_number_or_helper_is_refused(self):
        self.refused(self.run_runner())
        self.refused(self.run_runner(str(API)))

    def test_a_zip_archive_or_compiled_code_is_not_run_as_a_script(self):
        import py_compile
        import zipfile
        where = self.directory("odd")
        archive = os.path.join(where, "a.zip")
        with zipfile.ZipFile(archive, "w") as handle:
            handle.writestr("__main__.py", "import os\nopen(os.environ['WB_MARK'], 'w').close()\n")
        self.refused(self.run_runner(str(API), archive), "not a script")
        prefixed = os.path.join(where, "p.py")
        with open(archive, "rb") as source, open(prefixed, "wb") as handle:
            handle.write(b"print('script')\n" + source.read())
        self.refused(self.run_runner(str(API), prefixed), "not a script")
        source = self.helper("import os\nopen(os.environ['WB_MARK'], 'w').close()\n", name="c.py", where=where)
        compiled = os.path.join(where, "c.pyc")
        py_compile.compile(source, cfile=compiled)
        self.refused(self.run_runner(str(API), compiled), "not a script")

    def test_an_archive_that_the_archive_check_misses_is_still_never_run(self):
        """`zipfile.is_zipfile` looks only near the end of the file; `zipimport` looks further."""
        import zipfile
        where = self.directory("deep")
        archive = os.path.join(where, "a.zip")
        with zipfile.ZipFile(archive, "w") as handle:
            handle.writestr("__main__.py", "import os\nopen(os.environ['WB_MARK'], 'w').close()\n")
        with open(archive, "rb") as source:
            data = source.read()
        for name, tail in (("comment", None), ("trailing", b"\0" * 65536)):
            path = os.path.join(where, name + ".py")
            with open(path, "wb") as handle:
                handle.write(b"print('benign visible script')\n#")
                if tail is None:
                    handle.write(data[:-2] + (65535).to_bytes(2, "little") + b"x" * 65535 + b"\n")
                else:
                    handle.write(data + tail)
            done = self.run_runner(str(API), path)
            self.assertFalse(os.path.exists(self.mark), "the archive's __main__ ran: " + name)
            self.assertNotEqual("benign visible script\n", done.stdout)

    def test_a_coding_cookie_cannot_make_the_text_that_runs_differ_from_the_bytes(self):
        helper = self.helper(name="u7.py")
        with open(helper, "wb") as handle:
            handle.write(b"# -*- coding: utf-7 -*-\n+AHAAcgBpAG4AdAAoACcAUABXAE4ARQBEACcAKQ-\n")
        done = self.run_runner(str(API), helper)
        self.assertNotIn("PWNED", done.stdout)
        legacy = self.helper(name="l1.py")
        with open(legacy, "wb") as handle:
            handle.write(b"# coding: latin-1\nprint('caf\xe9')\n")
        self.refused(self.run_runner(str(API), legacy), "UTF-8")

    def test_a_helper_that_is_not_a_regular_file_is_refused(self):
        where = self.directory("odd2")
        with open(os.path.join(where, "__main__.py"), "w") as handle:
            handle.write("import os\nopen(os.environ['WB_MARK'], 'w').close()\n")
        self.refused(self.run_runner(str(API), where), "not a regular file")
        fifo = os.path.join(self.base, "fifo.py")
        os.mkfifo(fifo)
        done = subprocess.run([sys.executable, "-I", RUNNER, str(API), fifo], cwd=self.base,
                              capture_output=True, text=True, timeout=20)
        self.assertEqual(1, done.returncode)
        self.assertIn("not a regular file", done.stderr)

    def test_a_helper_that_does_not_exist_is_a_failure_and_not_a_silent_success(self):
        done = self.run_runner(str(API), os.path.join(self.base, "missing.py"))
        self.assertNotEqual(0, done.returncode)

    def test_a_distribution_without_the_kit_runs_nothing(self):
        self.refused(self.run_runner(str(API), self.helper(), runner=self.distribution(kit=False)), "kit is missing")

    def test_a_kit_whose_api_is_not_an_integer_is_refused(self):
        for text in ('API = "1"\n', "API = 1.0\n", "API = True\n", "API = None\n", "API = [1]\n", "X = 1\n"):
            runner = self.distribution(api=text)
            self.refused(self.run_runner(str(API), self.helper(name="h%d.py" % len(text)), runner=runner),
                         "integer API")

    def test_a_kit_that_cannot_be_loaded_is_refused(self):
        for text in ("raise RuntimeError('x')\n", "API = (\n", "import not_a_module_anywhere\n"):
            runner = self.distribution(api=text)
            self.refused(self.run_runner(str(API), self.helper(name="h%d.py" % len(text)), runner=runner),
                         "cannot be loaded")

    def test_a_kit_that_is_a_directory_without_an_init_is_refused(self):
        runner = self.distribution()
        os.unlink(os.path.join(os.path.dirname(runner), "wbkit", "__init__.py"))
        self.refused(self.run_runner(str(API), self.helper(), runner=runner), "kit is missing")

    def test_a_planted_kit_beside_the_helper_or_in_the_current_directory_does_not_stand_in(self):
        """The runner of a distribution with no kit does not fall back to a `wbkit` it can find elsewhere."""
        planted = self.directory("planted")
        os.mkdir(os.path.join(planted, "wbkit"))
        with open(os.path.join(planted, "wbkit", "__init__.py"), "w") as handle:
            handle.write("API = 1\n")
        helper = self.helper(where=planted)
        self.refused(self.run_runner(str(API), helper, runner=self.distribution(kit=False), cwd=planted,
                                     env={"PYTHONPATH": planted}), "kit is missing")


class Launched(unittest.TestCase):
    """`launch.launch(..., kit=n)`: the pinned helper through the runner."""

    def setUp(self):
        support.forbid_real_store(self)
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.store = store.Store(os.path.join(self.base, "store"))
        self.store.ensure()
        self.root = os.path.join(self.base, "project")
        os.makedirs(os.path.join(self.root, "tools"))
        self.mark = os.path.join(self.base, "ran")
        self.pin(REPORT.replace("import wbkit\n", "import wbkit\nopen(os.environ['WB_RAN'], 'a').write('x')\n"))
        patch = unittest.mock.patch.dict(os.environ, {"WB_RAN": self.mark, "WB_MARK": ""})
        patch.start()
        self.addCleanup(patch.stop)

    def pin(self, text):
        path = os.path.join(self.root, "tools", "helper.py")
        with open(path, "w") as handle:
            handle.write(text)
        pins.set_pin(self.store, PROJECT, "check", "tools/helper.py", pins.hash_bytes(text.encode()), "owner")

    def go(self, *args, kit=API):
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            code = launch.launch(self.store, PROJECT, "check", self.root, list(args), stdout=out, stderr=err,
                                 kit=kit)
            out.seek(0)
            err.seek(0)
            return code, out.read().decode(), err.read().decode()

    def test_a_helper_with_the_matching_kit_number_runs_and_reaches_the_kit(self):
        code, out, err = self.go("a", "b")
        self.assertEqual(0, code, err)
        seen = json.loads(out)
        self.assertEqual(["a", "b"], seen["argv"][1:])
        self.assertEqual(os.path.join(self.store.root, "bin", "run"), os.path.dirname(os.path.dirname(seen["argv"][0])))
        self.assertEqual(API, seen["api"])

    def test_a_different_number_runs_nothing_and_prints_the_refusal(self):
        code, out, err = self.go(kit=API + 1)
        self.assertEqual((1, ""), (code, out))
        self.assertTrue(err.startswith("refused: this helper needs kit API"), err)
        self.assertFalse(os.path.exists(self.mark))

    def test_a_number_that_is_not_a_positive_integer_runs_nothing(self):
        for kit in (0, -1, True, "1", 1.0, [1]):
            with self.assertRaises(launch.LaunchError, msg=repr(kit)):
                self.go(kit=kit)
        self.assertFalse(os.path.exists(self.mark))

    def test_with_no_kit_the_helper_runs_as_before_and_gets_nothing(self):
        self.pin("#!/bin/sh\necho \"n:$#\"\n")
        code, out, err = self.go("x", kit=None)
        self.assertEqual((0, "n:1\n"), (code, out), err)

    def test_the_exit_code_of_the_helper_reaches_the_caller(self):
        self.pin("import sys\nsys.exit(3)\n")
        self.assertEqual(3, self.go()[0])

    def test_the_private_copy_is_removed_afterwards(self):
        self.go()
        self.assertEqual([], os.listdir(os.path.join(self.store.root, "bin", "run")))

    def test_the_runner_is_started_in_isolated_mode(self):
        """Planted files in the working directory and a hostile PYTHONPATH are not imported when the
        launcher starts the runner, which holds only if the launcher passes -I."""
        poison = os.path.join(self.base, "poison")
        os.makedirs(poison)
        hostile = os.path.join(self.base, "hostile-ran")
        for file in HOSTILE_FILES:
            with open(os.path.join(poison, file), "w") as handle:
                handle.write(HOSTILE)
        real = subprocess.run
        seen = []

        def run(command, **kw):
            seen.append(command)
            kw["cwd"] = poison
            kw["env"] = dict(os.environ, PYTHONPATH=poison, WB_HOSTILE=hostile)
            return real(command, **kw)

        with unittest.mock.patch.object(subprocess, "run", run):
            code, out, err = self.go()
        self.assertEqual(0, code, err)
        self.assertEqual([sys.executable, "-I", launch.RUNNER], seen[0][:3])
        self.assertFalse(os.path.exists(hostile), "a planted file was imported")

    def test_a_helper_that_changed_since_it_was_pinned_is_not_run_whatever_the_number(self):
        with open(os.path.join(self.root, "tools", "helper.py"), "a") as handle:
            handle.write("# edited\n")
        with self.assertRaises(launch.LaunchError):
            self.go()
        self.assertFalse(os.path.exists(self.mark))


if __name__ == "__main__":
    unittest.main()

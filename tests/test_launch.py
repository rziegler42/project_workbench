import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock

import support
from workbench import cli, launch, pins, store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = "a" * 64
HELPER = """#!/bin/sh
echo "count:$#"
for arg in "$@"; do echo "arg:$arg"; done
echo "self:$0"
ls -l "$0" | cut -c1-10
if [ "$1" = "fail" ]; then exit 3; fi
if [ "$1" = "die" ]; then kill -9 $$; fi
exit 0
"""


class Base(unittest.TestCase):
    def setUp(self):
        support.forbid_real_store(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.store = store.Store(os.path.join(self.base, "store"))
        self.store.ensure()
        self.root = os.path.join(self.base, "project")
        os.makedirs(os.path.join(self.root, "tools"))
        self.helper = os.path.join(self.root, "tools", "helper.sh")
        self.write(self.helper, HELPER)
        self.pin()

    def write(self, path, text):
        with open(path, "w") as handle:
            handle.write(text)

    def pin(self, name="commit", rel="tools/helper.sh", root=None):
        with open(os.path.join(root or self.root, rel), "rb") as handle:
            digest = pins.hash_bytes(handle.read())
        pins.set_pin(self.store, PROJECT, name, rel, digest, "owner")

    def run_helper(self, *args, name="commit", root=None, project=PROJECT):
        with tempfile.TemporaryFile() as out:
            code = launch.launch(self.store, project, name, root or self.root, list(args), stdout=out)
            out.seek(0)
            return code, out.read().decode()

    def run_dir(self):
        return os.path.join(self.store.root, "bin", "run")

    def nothing_left(self):
        path = self.run_dir()
        self.assertEqual(os.listdir(path) if os.path.isdir(path) else [], [])


class RunTest(Base):
    def test_a_helper_that_matches_its_pin_runs_with_its_arguments(self):
        code, output = self.run_helper("one", "two words", "--flag")
        self.assertEqual(code, 0)
        self.assertIn("count:3", output)
        for arg in ("arg:one", "arg:two words", "arg:--flag"):
            self.assertIn(arg, output)

    def test_arguments_are_passed_verbatim_with_no_shell(self):
        marker = os.path.join(self.base, "injected")
        tricky = ["a;touch %s" % marker, "$(touch %s)" % marker, "`touch %s`" % marker,
                  "x | y", "*", "~", "a\nb", "", "--", "-n"]
        code, output = self.run_helper(*tricky)
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(marker))
        self.assertIn("count:%d" % len(tricky), output)
        for arg in tricky[:7]:
            self.assertIn("arg:" + arg.split("\n")[0], output)

    def test_the_helpers_exit_code_is_returned(self):
        self.assertEqual(self.run_helper("fail")[0], 3)

    def test_a_helper_killed_by_a_signal_returns_128_plus_the_signal(self):
        self.assertEqual(self.run_helper("die")[0], 128 + 9)

    def test_the_helper_runs_from_a_private_copy_not_from_the_project(self):
        _, output = self.run_helper()
        line = next(l for l in output.splitlines() if l.startswith("self:"))[5:]
        self.assertTrue(line.startswith(os.path.join(self.store.root, "bin", "run") + os.sep), line)
        self.assertTrue(line.endswith("/commit"), line)
        self.assertNotEqual(line, self.helper)
        self.assertIn("-rwx------", output)

    def test_the_copy_is_removed_after_a_run_and_after_a_failure(self):
        self.run_helper()
        self.nothing_left()
        self.run_helper("fail")
        self.nothing_left()
        self.run_helper("die")
        self.nothing_left()

    def test_the_copy_is_removed_when_the_run_is_interrupted(self):
        with unittest.mock.patch.object(launch.subprocess, "run", side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                self.run_helper()
        self.nothing_left()

    def test_a_helper_without_the_execute_bit_in_the_project_still_runs(self):
        os.chmod(self.helper, 0o644)
        self.assertEqual(self.run_helper()[0], 0)

    def test_the_run_directories_are_private(self):
        modes = []
        real = launch.subprocess.run

        def spy(command, **kwargs):
            modes.append((stat.S_IMODE(os.stat(os.path.dirname(command[0])).st_mode),
                          stat.S_IMODE(os.stat(command[0]).st_mode),
                          stat.S_IMODE(os.stat(self.run_dir()).st_mode)))
            return real(command, **kwargs)

        with unittest.mock.patch.object(launch.subprocess, "run", spy):
            self.run_helper()
        self.assertEqual(modes, [(0o700, 0o700, 0o700)])


class RefusalTest(Base):
    def refused(self, pattern, *args, **kwargs):
        with unittest.mock.patch.object(launch.subprocess, "run",
                                        side_effect=AssertionError("the helper was run")):
            with self.assertRaisesRegex(launch.LaunchError, pattern):
                self.run_helper(*args, **kwargs)
        self.nothing_left()

    def test_a_helper_edited_after_pinning_is_not_run(self):
        marker = os.path.join(self.base, "ran")
        self.write(self.helper, HELPER + "touch %s\n" % marker)
        self.refused("has changed since it was pinned")
        self.assertFalse(os.path.exists(marker))

    def test_the_message_tells_the_owner_how_to_recover(self):
        self.write(self.helper, HELPER + "# edited\n")
        with self.assertRaisesRegex(launch.LaunchError, "pin it again"):
            self.run_helper()

    def test_a_one_byte_change_is_enough(self):
        self.write(self.helper, HELPER.replace("count", "Count"))
        self.refused("has changed")

    def test_an_edit_can_be_pinned_again_and_then_runs(self):
        self.write(self.helper, HELPER + "# edited\n")
        self.refused("has changed")
        self.pin()
        self.assertEqual(self.run_helper()[0], 0)

    def test_a_helper_replaced_between_the_hash_and_the_run_still_runs_the_verified_bytes(self):
        marker = os.path.join(self.base, "evil-ran")

        def swap():
            self.write(self.helper, "#!/bin/sh\ntouch %s\n" % marker)

        with unittest.mock.patch.object(launch, "_after_hash", swap):
            code, output = self.run_helper()
        self.assertEqual(code, 0)
        self.assertIn("count:0", output)
        self.assertFalse(os.path.exists(marker))
        with open(self.helper) as handle:
            self.assertIn("evil-ran", handle.read())

    def test_a_helper_replaced_by_a_symbolic_link_is_refused(self):
        other = os.path.join(self.base, "other.sh")
        self.write(other, HELPER)
        os.unlink(self.helper)
        os.symlink(other, self.helper)
        self.refused("cannot be read")

    def test_a_directory_on_the_way_replaced_by_a_symbolic_link_is_refused(self):
        moved = os.path.join(self.base, "moved-tools")
        shutil.move(os.path.join(self.root, "tools"), moved)
        os.symlink(moved, os.path.join(self.root, "tools"))
        self.refused("cannot be read")

    def test_a_fifo_or_directory_in_place_of_the_helper_is_refused(self):
        os.unlink(self.helper)
        os.mkfifo(self.helper)
        self.refused("cannot be read")
        os.unlink(self.helper)
        os.mkdir(self.helper)
        self.refused("cannot be read")

    def test_a_moved_or_removed_helper_is_refused(self):
        os.rename(self.helper, os.path.join(self.root, "tools", "renamed.sh"))
        self.refused("cannot be read")
        os.unlink(os.path.join(self.root, "tools", "renamed.sh"))
        self.refused("cannot be read")

    def test_a_missing_pin_refuses(self):
        self.refused("no pin named", name="other")

    def test_a_pin_for_another_project_does_not_count(self):
        self.refused("no pin named", project="b" * 64)

    def test_a_damaged_pins_file_refuses(self):
        with open(os.path.join(self.store.root, "projects", PROJECT, "pins"), "wb") as handle:
            handle.write(b"{ broken")
        self.refused("pins file")

    def test_a_pin_that_points_outside_the_root_cannot_be_used(self):
        path = os.path.join(self.store.root, "projects", PROJECT, "pins")
        with open(path) as handle:
            text = handle.read()
        with open(path, "w") as handle:
            handle.write(text.replace("tools/helper.sh", "../outside.sh"))
        self.refused("unsafe path|pins file")

    def test_a_root_that_is_a_symbolic_link_is_refused(self):
        link = os.path.join(self.base, "rootlink")
        os.symlink(self.root, link)
        self.refused("cannot be read", root=link)

    def test_a_missing_root_is_refused(self):
        self.refused("cannot be read", root=os.path.join(self.base, "nowhere"))

    def test_a_run_directory_that_is_a_symbolic_link_is_not_followed(self):
        outside = os.path.join(self.base, "outside")
        os.makedirs(outside)
        os.makedirs(os.path.join(self.store.root, "bin"), exist_ok=True)
        os.symlink(outside, self.run_dir())
        self.refused("cannot prepare")
        self.assertEqual(os.listdir(outside), [])

    def test_a_run_directory_open_to_others_is_refused(self):
        os.makedirs(self.run_dir(), mode=0o755)
        os.chmod(self.run_dir(), 0o755)
        with self.assertRaisesRegex(launch.LaunchError, "cannot prepare"):
            self.run_helper()

    def test_a_helper_that_cannot_be_executed_is_a_refusal_not_a_traceback(self):
        self.write(self.helper, "#!/nonexistent/interpreter\n")
        self.pin()
        with self.assertRaisesRegex(launch.LaunchError, "could not be run"):
            self.run_helper()
        self.nothing_left()

    def test_a_nul_byte_in_an_argument_is_a_refusal_not_a_traceback(self):
        err = io.StringIO()
        code = launch.run(self.store, PROJECT, "commit", self.root, ["bad\x00arg"], err)
        self.assertEqual(code, 1)
        self.assertIn("could not be run", err.getvalue())
        self.nothing_left()

    def test_bad_ids_and_names_are_refused_by_the_command(self):
        for project, name in (("short", "commit"), (PROJECT, "bad name"), (PROJECT, "../x")):
            with self.subTest(project=project, name=name):
                err = io.StringIO()
                self.assertEqual(launch.run(self.store, project, name, self.root, [], err), 1)
                self.assertIn("refused:", err.getvalue())


class CapturedTest(Base):
    """`launch_captured`: the helper's output is read here, bounded in size and in time."""

    def helper_text(self, text):
        self.write(self.helper, "#!/bin/sh\n" + text)
        self.pin()

    def captured(self, *args, limit=1000, timeout=10, **kwargs):
        return launch.launch_captured(self.store, PROJECT, "commit", self.root, list(args),
                                      limit=limit, timeout=timeout, **kwargs)

    def gone(self, pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        return False

    def test_output_the_exit_code_and_a_little_of_standard_error_come_back(self):
        self.helper_text('echo "problem: x"\necho oops >&2\nexit 4\n')
        got = self.captured()
        self.assertEqual((4, b"problem: x\n", b"oops\n", False, False), tuple(got))
        self.nothing_left()

    def test_the_working_directory_is_the_one_asked_for_and_input_is_closed(self):
        self.helper_text('pwd\ncat\necho done\n')
        got = self.captured(cwd=self.root)
        self.assertEqual((0, False, False), (got.code, got.over, got.timed_out))
        self.assertEqual([os.path.realpath(self.root), "done"], got.stdout.decode().split("\n")[:2])

    def test_output_at_the_limit_is_kept_and_one_byte_more_stops_the_helper(self):
        self.helper_text('printf %s 0123456789\n')
        self.assertEqual((b"0123456789", False), (self.captured(limit=10).stdout, self.captured(limit=10).over))
        got = self.captured(limit=9)
        self.assertTrue(got.over)
        self.assertEqual(b"012345678", got.stdout)

    def test_endless_output_is_stopped_at_the_limit(self):
        self.helper_text('while :; do echo aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; done\n')
        got = self.captured(limit=5000, timeout=20)
        self.assertTrue(got.over)
        self.assertLessEqual(len(got.stdout), 5000)
        self.assertNotEqual(0, got.code)
        self.nothing_left()

    def test_a_helper_that_ignores_a_closed_pipe_is_still_stopped(self):
        self.helper_text('trap "" PIPE\nwhile :; do echo aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 2>/dev/null; done\n')
        got = self.captured(limit=2000, timeout=20)
        self.assertTrue(got.over)
        self.nothing_left()

    def test_a_helper_that_runs_too_long_is_stopped_with_what_it_started(self):
        self.helper_text('sleep 60 &\necho $!\nwait\n')
        started = time.monotonic()
        got = self.captured(timeout=1)
        self.assertLess(time.monotonic() - started, 15)
        self.assertTrue(got.timed_out)
        child = int(got.stdout.split()[0])
        for _ in range(50):
            if self.gone(child):
                break
            time.sleep(0.1)
        self.assertTrue(self.gone(child))
        self.nothing_left()

    def test_a_helper_that_quits_leaving_a_child_holding_the_pipe_does_not_hang_and_leaves_nothing(self):
        self.helper_text('sleep 60 >&1 2>&2 &\necho $!\nexit 0\n')
        started = time.monotonic()
        got = self.captured(timeout=30)
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual((0, False), (got.code, got.timed_out))
        child = int(got.stdout.split()[0])
        for _ in range(50):
            if self.gone(child):
                break
            time.sleep(0.1)
        self.assertTrue(self.gone(child))
        self.nothing_left()

    def test_a_helper_killed_by_a_signal_returns_128_plus_the_signal(self):
        self.helper_text('kill -9 $$\n')
        self.assertEqual(137, self.captured().code)

    def test_standard_error_is_cut_to_what_is_kept(self):
        self.helper_text('head -c 100000 /dev/zero | tr "\\0" e >&2\n')
        self.assertEqual(launch.STDERR_KEPT, len(self.captured().stderr))

    def test_a_changed_helper_is_refused_and_does_not_run(self):
        self.write(self.helper, HELPER + "echo changed >> %s\n" % os.path.join(self.base, "ran"))
        with self.assertRaises(launch.LaunchError):
            self.captured()
        self.assertFalse(os.path.exists(os.path.join(self.base, "ran")))
        self.nothing_left()

    def test_a_missing_pin_is_refused(self):
        with self.assertRaises(launch.LaunchError):
            launch.launch_captured(self.store, PROJECT, "other", self.root, [], limit=10, timeout=1)

    def test_a_caller_kit_that_differs_from_the_pin_is_refused(self):
        with self.assertRaises(launch.LaunchError):
            self.captured(kit=1)

    def test_the_helper_cannot_be_started_without_an_interpreter_or_with_a_nul_argument(self):
        with self.assertRaises(launch.LaunchError):
            self.captured("a\x00b")
        self.nothing_left()


class Caller(Base):
    def test_the_caller_cannot_name_another_file(self):
        decoy = os.path.join(self.root, "tools", "decoy.sh")
        self.write(decoy, "#!/bin/sh\necho decoy\n")
        for args in (["tools/decoy.sh"], ["--root", self.root], ["../decoy.sh"], [decoy]):
            with self.subTest(args=args):
                code, output = self.run_helper(*args)
                self.assertNotIn("decoy\n", output.replace("arg:", ""))
                self.assertIn("count:%d" % len(args), output)

    def test_the_same_pin_works_from_two_clones_at_different_paths(self):
        clone = os.path.join(self.base, "elsewhere", "deeper", "clone")
        shutil.copytree(self.root, clone)
        self.assertEqual(self.run_helper(root=clone)[0], 0)
        self.assertEqual(self.run_helper()[0], 0)
        self.write(os.path.join(clone, "tools", "helper.sh"), HELPER + "# edited in one clone\n")
        with self.assertRaisesRegex(launch.LaunchError, "has changed"):
            self.run_helper(root=clone)
        self.assertEqual(self.run_helper()[0], 0)


class CommandLineTest(Base):
    def setUp(self):
        super().setUp()
        # The command finds its store from HOME, so the store lives where HOME says.
        self.home = os.path.join(self.base, "home")
        self.store = store.Store(os.path.join(self.home, ".config", "project-workbench"))
        self.store.ensure()
        self.pin()

    def command(self, *argv, project=PROJECT):
        env = dict(os.environ, HOME=self.home, PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE="1",
               PATH=support.clean_path())
        done = subprocess.run([sys.executable, "-B", "-m", "workbench", "launch", project] + list(argv),
                              env=env, cwd=self.base, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return done.returncode, done.stdout.decode(), done.stderr.decode()

    def test_launch_runs_the_pinned_helper_and_passes_arguments_after_the_double_dash(self):
        code, out, err = self.command("commit", "--root", self.root, "--", "one", "--two", "three")
        self.assertEqual((code, err), (0, ""), out)
        for expected in ("count:3", "arg:one", "arg:--two", "arg:three"):
            self.assertIn(expected, out)

    def test_the_exit_code_of_the_helper_is_the_exit_code_of_launch(self):
        self.assertEqual(self.command("commit", "--root", self.root, "--", "fail")[0], 3)

    def test_an_edited_helper_exits_1_with_a_reason_on_standard_error(self):
        self.write(self.helper, HELPER + "# edited\n")
        code, out, err = self.command("commit", "--root", self.root, "--")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("refused: the helper commit has changed since it was pinned", err)

    def test_no_pin_exits_1(self):
        code, _, err = self.command("nothing", "--root", self.root, "--")
        self.assertEqual(code, 1)
        self.assertIn("no pin named", err)

    def test_usage_errors_exit_2(self):
        for argv in ([], ["commit"], ["commit", "--root"], ["commit", "--root", ""]):
            with self.subTest(argv=argv):
                self.assertEqual(self.command(*argv)[0], 2)

    def test_launch_prints_nothing_of_its_own_on_success(self):
        code, out, err = self.command("commit", "--root", self.root, "--")
        self.assertEqual((code, err), (0, ""))
        self.assertNotIn("warning", out)


class WrapperTest(unittest.TestCase):
    EXPECTED = ("#!/bin/sh\n"
                "# Generated by project-workbench. It is rewritten whenever the guarded store is\n"
                "# initialized, so do not edit it.\n"
                "WORKBENCH_DIR='/opt/workbench'\n"
                "export WORKBENCH_DIR\n"
                "exec python3 -I -c 'import os, runpy, sys; sys.path.insert(0, os.environ[\"WORKBENCH_DIR\"]); "
                "runpy.run_module(\"workbench\", run_name=\"__main__\", alter_sys=True)' \"$@\"\n")

    def setUp(self):
        support.forbid_real_store(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.store = store.Store(os.path.join(self.base, "store"))
        self.store.ensure()
        self.wb = os.path.join(self.store.root, "bin", "wb")
        # support turned the PATH scan off; these tests are about it.
        finder = unittest.mock.patch.object(launch, "find_command", shutil.which)
        finder.start()
        self.addCleanup(finder.stop)

    def text(self):
        with open(self.wb) as handle:
            return handle.read()

    def test_the_wrapper_is_fixed_text_apart_from_one_path(self):
        launch.install_wrapper(self.store, "/opt/workbench")
        self.assertEqual(self.text(), self.EXPECTED)
        self.assertTrue(os.stat(self.wb).st_mode & stat.S_IXUSR)

    def test_a_second_initialization_changes_nothing(self):
        launch.install_wrapper(self.store, "/opt/workbench")
        before = os.stat(self.wb)
        self.assertEqual(launch.install_wrapper(self.store, "/opt/workbench"), [])
        after = os.stat(self.wb)
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))
        self.assertEqual(self.text(), self.EXPECTED)

    def test_a_moved_distribution_rewrites_it_and_a_damaged_wrapper_is_repaired(self):
        launch.install_wrapper(self.store, "/opt/workbench")
        launch.install_wrapper(self.store, "/elsewhere/workbench")
        self.assertIn("WORKBENCH_DIR='/elsewhere/workbench'", self.text())
        with open(self.wb, "w") as handle:
            handle.write("#!/bin/sh\necho tampered\n")
        launch.install_wrapper(self.store, "/elsewhere/workbench")
        self.assertIn("exec python3 -I -c", self.text())
        self.assertNotIn("tampered", self.text())

    def test_the_wrapper_runs_the_workbench(self):
        launch.install_wrapper(self.store, ROOT)
        home = os.path.join(self.base, "home")
        os.makedirs(home)
        env = dict(os.environ, HOME=home, PYTHONDONTWRITEBYTECODE="1")
        env.pop("PYTHONPATH", None)
        done = subprocess.run([self.wb, "verify", os.path.join(ROOT, "tests", "fixtures", "sample-package")],
                              env=env, cwd=self.base, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(b"sample/sample-notes", done.stdout)

    def test_the_wrapper_ignores_a_hostile_working_directory(self):
        # A project that ships its own `workbench` package, a `json.py` and a sitecustomize must
        # not run in place of the real ones when `wb` is used from inside it.
        launch.install_wrapper(self.store, ROOT)
        marker = os.path.join(self.base, "hostile-ran")
        hostile = os.path.join(self.base, "hostile-project")
        os.makedirs(os.path.join(hostile, "workbench"))
        code = "open(%r, 'a').write('ran')\nraise SystemExit(99)\n" % marker
        for rel in ("workbench/__init__.py", "workbench/__main__.py", "json.py", "hashlib.py",
                    "sitecustomize.py", "usercustomize.py"):
            with open(os.path.join(hostile, rel), "w") as handle:
                handle.write(code)
        home = os.path.join(self.base, "home")
        os.makedirs(home)
        env = dict(os.environ, HOME=home, PYTHONDONTWRITEBYTECODE="1", PATH=support.clean_path())
        env.pop("PYTHONPATH", None)
        done = subprocess.run([self.wb, "verify", os.path.join(ROOT, "tests", "fixtures", "sample-package")],
                              env=env, cwd=hostile, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertFalse(os.path.exists(marker), "code from the working directory ran")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(b"sample/sample-notes", done.stdout)

    def test_the_wrapper_ignores_a_pythonpath_set_by_the_caller(self):
        launch.install_wrapper(self.store, ROOT)
        marker = os.path.join(self.base, "path-ran")
        evil = os.path.join(self.base, "evil")
        os.makedirs(os.path.join(evil, "workbench"))
        with open(os.path.join(evil, "workbench", "__init__.py"), "w") as handle:
            handle.write("open(%r, 'a').write('ran')\n" % marker)
        home = os.path.join(self.base, "home")
        os.makedirs(home)
        env = dict(os.environ, HOME=home, PYTHONPATH=evil, PATH=support.clean_path())
        done = subprocess.run([self.wb, "verify", os.path.join(ROOT, "tests", "fixtures", "sample-package")],
                              env=env, cwd=self.base, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_a_workbench_directory_that_cannot_be_quoted_is_not_written(self):
        for bad in ("/opt/it's", "relative/path", "/opt/new\nline", "/opt/\x1b[0m", "", None):
            with self.subTest(bad=bad):
                warnings = launch.install_wrapper(self.store, bad)
                self.assertEqual(len(warnings), 1)
                self.assertIn("not written", warnings[0])
                self.assertFalse(os.path.exists(self.wb))

    def test_a_wrapper_that_is_a_symbolic_link_is_not_followed_or_replaced(self):
        target = os.path.join(self.base, "target")
        with open(target, "w") as handle:
            handle.write("keep")
        os.symlink(target, self.wb)
        warnings = launch.install_wrapper(self.store, "/opt/workbench")
        self.assertTrue(any("not written" in w for w in warnings))
        with open(target) as handle:
            self.assertEqual(handle.read(), "keep")

    def fake_wb(self, name):
        directory = os.path.join(self.base, name)
        os.makedirs(directory)
        path = os.path.join(directory, "wb")
        with open(path, "w") as handle:
            handle.write("#!/bin/sh\necho other wb\n")
        os.chmod(path, 0o755)
        return directory, path

    def test_a_different_wb_on_the_path_produces_a_warning_naming_it(self):
        directory, path = self.fake_wb("fakebin")
        with unittest.mock.patch.dict(os.environ, {"PATH": directory + os.pathsep + os.environ["PATH"]}):
            warnings = launch.install_wrapper(self.store, "/opt/workbench")
        self.assertEqual(len(warnings), 1)
        self.assertIn(path, warnings[0])
        self.assertIn(self.wb, warnings[0])

    def test_no_other_wb_gives_no_warning(self):
        empty = os.path.join(self.base, "emptybin")
        os.makedirs(empty)
        with unittest.mock.patch.dict(os.environ, {"PATH": empty}):
            self.assertEqual(launch.install_wrapper(self.store, "/opt/workbench"), [])

    def test_our_own_wrapper_on_the_path_gives_no_warning(self):
        with unittest.mock.patch.dict(os.environ, {
                "PATH": os.path.join(self.store.root, "bin") + os.pathsep + os.environ["PATH"]}):
            self.assertEqual(launch.install_wrapper(self.store, "/opt/workbench"), [])

    def test_the_warning_is_given_once_when_the_wrapper_is_written_not_on_every_command(self):
        directory, _ = self.fake_wb("fakebin")
        with unittest.mock.patch.dict(os.environ, {"PATH": directory + os.pathsep + os.environ["PATH"]}):
            self.assertEqual(len(launch.install_wrapper(self.store, "/opt/workbench")), 1)
            self.assertEqual(launch.install_wrapper(self.store, "/opt/workbench"), [])

    def test_a_command_writes_the_wrapper_and_prints_the_warning(self):
        directory, path = self.fake_wb("fakebin")
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch.dict(os.environ, {"PATH": directory + os.pathsep + os.environ["PATH"]}):
            code = cli.main(["verify", os.path.join(ROOT, "tests", "fixtures", "sample-package")],
                            out, err, store_root=self.store.root, distribution="/opt/workbench")
        self.assertEqual(code, 0)
        self.assertEqual(self.text(), self.EXPECTED)
        self.assertIn("warning: another command named `wb` is on your PATH at " + path, out.getvalue())

    def test_a_command_never_stops_because_of_the_wrapper(self):
        os.symlink(os.path.join(self.base, "x"), self.wb)
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["verify", os.path.join(ROOT, "tests", "fixtures", "sample-package")],
                        out, err, store_root=self.store.root, distribution="/opt/workbench")
        self.assertEqual(code, 0)
        self.assertIn("the `wb` launcher was not written", out.getvalue())


if __name__ == "__main__":
    unittest.main()

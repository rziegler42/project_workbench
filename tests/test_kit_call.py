"""The kit's `call.run_command`: another module's pinned command, started through `wb run`.

The `wb` here is a fake that records what it was given and acts by the command name it is asked to run, so
no test depends on a module, a pin or a store. That the real launcher refuses an unpinned or unprovided
command is shown in `test_run`."""

import json
import os
import sys
import tempfile
import time
import unittest
import unittest.mock

from workbench.wbkit import call

FAKE = """#!{python}
import json, os, subprocess, sys, time
argv = sys.argv[1:]
mode = argv[3] if argv[1:2] == ["--provides"] else argv[1]
with open({log!r}, "a") as handle:
    handle.write(json.dumps({{"argv": argv, "env": dict(os.environ), "cwd": os.getcwd(), "me": {me!r}}}) + "\\n")
if mode == "exit3":
    sys.stderr.write("refused: nope\\n")
    sys.exit(3)
if mode == "hang":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
    with open({pids!r}, "w") as handle:
        handle.write(str(child.pid))
    time.sleep(300)
if mode == "big":
    sys.stdout.buffer.write(b"x" * 5000000)
    sys.exit(0)
if mode == "noisy":
    sys.stderr.write("e" * 20000)
    sys.exit(0)
sys.stdout.buffer.write(sys.stdin.buffer.read())
"""


class Call(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.root = os.path.join(self.base, "project")
        self.outside = os.path.join(self.base, "outside")
        for folder in (self.root, os.path.join(self.root, "bin"), self.outside):
            os.makedirs(folder)
        self.log = os.path.join(self.base, "outside.log")
        self.inside_log = os.path.join(self.base, "inside.log")
        self.pids = os.path.join(self.base, "pids")
        self.fake(self.outside, self.log, "outside")
        self.path([self.outside])

    def fake(self, folder, log, me):
        script = os.path.join(folder, "wb")
        with open(script, "w") as handle:
            handle.write(FAKE.format(python=sys.executable, log=log, me=me, pids=self.pids))
        os.chmod(script, 0o755)

    def path(self, entries, **extra):
        patch = unittest.mock.patch.dict(os.environ, dict({"PATH": os.pathsep.join(entries)}, **extra))
        patch.start()
        self.addCleanup(patch.stop)

    def records(self, log=None):
        with open(log or self.log) as handle:
            return [json.loads(line) for line in handle]

    def run_it(self, command="echo", arguments=(), **kwargs):
        kwargs.setdefault("limit", 1 << 20)
        kwargs.setdefault("timeout", 20)
        return call.run_command(self.root, command, arguments, **kwargs)


class Runs(Call):
    def test_it_runs_wb_with_run_the_command_and_every_argument_literally(self):
        extra = ["ask", "--model", "a b", ";", "$HOME", "--", "-n", "", "--provides"]
        result = self.run_it("echo", extra)
        self.assertEqual((0, b"", b"", False, False), (result.code, result.stdout, result.stderr,
                                                       result.over, result.timed_out))
        self.assertEqual(["run", "echo"] + extra, self.records()[-1]["argv"])

    def test_the_capability_goes_before_the_command(self):
        self.run_it("echo", ["ask"], provides="model-bridge")
        self.assertEqual(["run", "--provides", "model-bridge", "echo", "ask"], self.records()[-1]["argv"])

    def test_it_starts_in_the_project_root_unless_told_otherwise(self):
        self.run_it()
        self.assertEqual(self.root, os.path.realpath(self.records()[-1]["cwd"]))
        sub = os.path.join(self.root, "docs")
        os.mkdir(sub)
        self.run_it(cwd=sub)
        self.assertEqual(sub, os.path.realpath(self.records()[-1]["cwd"]))

    def test_standard_input_reaches_the_command_and_its_output_comes_back(self):
        data = "prompt é\n".encode() * 5
        result = self.run_it("echo", ["ask"], stdin=data)
        self.assertEqual((0, data), (result.code, result.stdout))

    def test_a_large_input_and_a_large_output_do_not_deadlock(self):
        data = os.urandom(900000)
        result = self.run_it("echo", ["ask"], stdin=data, limit=2000000)
        self.assertEqual((0, data, False), (result.code, result.stdout, result.over))

    def test_the_exit_code_and_the_refusal_line_come_back_as_data(self):
        result = self.run_it("exit3")
        self.assertEqual((3, b"refused: nope\n"), (result.code, result.stderr))

    def test_a_command_that_never_reads_its_input_does_not_hang_the_caller(self):
        result = self.run_it("exit3", stdin=b"x" * 900000)
        self.assertEqual((3, False), (result.code, result.timed_out))


class Bounded(Call):
    def test_output_past_the_limit_is_cut_and_reported(self):
        result = self.run_it("big", limit=1000)
        self.assertEqual((True, 1000, False), (result.over, len(result.stdout), result.timed_out))

    def test_only_the_end_of_standard_error_is_kept(self):
        result = self.run_it("noisy")
        self.assertEqual((0, call.STDERR_KEPT), (result.code, len(result.stderr)))

    def test_a_timeout_stops_the_command_and_what_it_started(self):
        started = time.monotonic()
        result = self.run_it("hang", timeout=1)
        self.assertTrue(result.timed_out)
        self.assertLess(time.monotonic() - started, 15)
        with open(self.pids) as handle:
            child = int(handle.read())
        self.addCleanup(self.reap, child)
        for _ in range(50):
            try:
                os.kill(child, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            self.fail("the command's child is still running")

    @staticmethod
    def reap(pid):
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass


class Environment(Call):
    SECRETS = {"GIT_DIR": "/x", "GIT_CONFIG_COUNT": "1", "GITHUB_TOKEN": "t", "AWS_SECRET_ACCESS_KEY": "s",
               "LD_PRELOAD": "/x", "DYLD_INSERT_LIBRARIES": "/x", "PYTHONPATH": "/x", "WB_ANYTHING": "1",
               "OPENAI_API_KEY": "k"}

    def test_only_the_kept_variables_and_a_trusted_path_reach_the_command(self):
        self.path([self.outside, "relative", "", os.path.join(self.root, "bin")],
                  HOME="/home/x", LC_ALL="C", TZ="UTC", **self.SECRETS)
        self.run_it()
        env = self.records()[-1]["env"]
        for name in self.SECRETS:
            self.assertNotIn(name, env)
        self.assertEqual(self.outside, env["PATH"])
        self.assertEqual(("/home/x", "C", "UTC"), (env["HOME"], env["LC_ALL"], env["TZ"]))
        allowed = set(call.KEPT) | {"PATH", "__CF_USER_TEXT_ENCODING"}
        self.assertEqual([], [n for n in env if n not in allowed and not n.startswith("LC_")])

    def test_the_environment_is_built_from_the_list_and_nothing_else(self):
        self.path([self.outside], **self.SECRETS)
        env = call.environment(self.root)
        self.assertLessEqual(set(env), set(call.KEPT) | {"PATH"} | {n for n in env if n.startswith("LC_")})


class FindsWbOutsideTheProject(Call):
    def setUp(self):
        Call.setUp(self)
        self.fake(os.path.join(self.root, "bin"), self.inside_log, "inside")

    def test_a_wb_in_the_project_is_not_used_when_there_is_one_outside(self):
        link_dir = os.path.join(self.base, "links")
        os.mkdir(link_dir)
        os.symlink(os.path.join(self.root, "bin", "wb"), os.path.join(link_dir, "wb"))
        self.path([os.path.join(self.root, "bin"), "bin", "", link_dir, self.outside])
        self.run_it()
        self.assertEqual("outside", self.records()[-1]["me"])
        self.assertFalse(os.path.exists(self.inside_log))

    def test_with_none_outside_nothing_runs(self):
        link_dir = os.path.join(self.base, "links")
        os.mkdir(link_dir)
        os.symlink(os.path.join(self.root, "bin", "wb"), os.path.join(link_dir, "wb"))
        self.path([os.path.join(self.root, "bin"), "bin", "", ".", link_dir, os.path.join(self.base, "none")])
        with self.assertRaises(call.CallError) as caught:
            self.run_it()
        self.assertIn("not found", str(caught.exception))
        self.assertFalse(os.path.exists(self.inside_log))
        self.assertFalse(os.path.exists(self.log))

    def test_a_wb_in_a_repository_the_project_is_inside_is_not_used(self):
        outer = os.path.join(self.base, "outer")
        inner = os.path.join(outer, "inner")
        for folder in (os.path.join(outer, ".git"), os.path.join(outer, "bin"), inner):
            os.makedirs(folder)
        self.fake(os.path.join(outer, "bin"), self.inside_log, "outer")
        self.path([os.path.join(outer, "bin")])
        with self.assertRaises(call.CallError):
            call.run_command(inner, "echo", limit=1 << 20, timeout=20)
        self.assertFalse(os.path.exists(self.inside_log))
        self.path([os.path.join(outer, "bin"), self.outside])
        call.run_command(inner, "echo", limit=1 << 20, timeout=20)
        self.assertEqual("outside", self.records()[-1]["me"])

    def test_a_path_entry_spelled_in_another_case_does_not_get_past_the_check(self):
        self.fake(os.path.join(self.root, "bin"), self.inside_log, "inside")
        self.path([os.path.join(self.root, "bin").upper()])
        with self.assertRaises(call.CallError):
            self.run_it()
        self.assertFalse(os.path.exists(self.inside_log))

    def test_a_non_executable_wb_is_skipped(self):
        os.chmod(os.path.join(self.outside, "wb"), 0o644)
        with self.assertRaises(call.CallError):
            self.run_it()


class RefusesBadArguments(Call):
    def refuses(self, *args, **kwargs):
        with self.assertRaises(call.CallError):
            call.run_command(*args, **dict({"limit": 100, "timeout": 5}, **kwargs))
        self.assertFalse(os.path.exists(self.log))

    def test_a_command_name_that_is_not_a_plain_name(self):
        for bad in ("", "-x", "a b", "../x", "a/b", "x" * 65, "a\nb", 7, None):
            self.refuses(self.root, bad, ["ask"])

    def test_a_capability_that_is_not_a_plain_name(self):
        for bad in ("", "A", "a b", "-x", "x" * 65, 7):
            self.refuses(self.root, "echo", ["ask"], provides=bad)

    def test_arguments_that_cannot_be_passed_literally(self):
        self.refuses(self.root, "echo", ["a\0b"])
        self.refuses(self.root, "echo", [7])
        self.refuses(self.root, "echo", ["x" * (call.MAX_ARGUMENT + 1)])
        self.refuses(self.root, "echo", ["a"] * (call.MAX_ARGUMENTS + 1))
        self.refuses(self.root, "echo", "ask")

    def test_input_and_limits_that_are_not_usable(self):
        self.refuses(self.root, "echo", [], stdin="text")
        self.refuses(self.root, "echo", [], stdin=b"x" * (call.MAX_INPUT + 1))
        for limit in (0, -1, 1.5, True):
            self.refuses(self.root, "echo", [], limit=limit)
        for timeout in (0, -1, True, "5", 86401):
            self.refuses(self.root, "echo", [], timeout=timeout)

    def test_a_root_that_is_not_absolute(self):
        self.refuses("project", "echo", [])


class TheKitStaysStandardLibraryOnly(unittest.TestCase):
    def test_it_imports_nothing_of_the_workbench(self):
        import ast
        with open(call.__file__) as handle:
            tree = ast.parse(handle.read())
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(0, node.level, "a relative import")
                names.append(node.module)
        self.assertEqual([], [n for n in names if n.split(".")[0] in ("workbench", "wbkit")])


if __name__ == "__main__":
    unittest.main()

"""``wb run``: a pinned module command from anywhere in a project, through the command line.

The modules are synthetic (``support_project``). The helper records every start in a log, so a test
that expects a refusal can show that nothing ran."""

import io
import os
import re
import sys
import tempfile
import unittest
import unittest.mock

from tests import support_project, support_words
from tests.support_project import HELPER_PATH, tool
from workbench import cli, commands, rules

SCRIPT = (b"#!/bin/sh\n"
          b"echo \"n:$#\"\n"
          b"for a in \"$@\"; do echo \"a:$a\"; done\n"
          b"echo ran >> \"$WB_TEST_LOG\"\n"
          b"if [ \"$1\" = report ]; then exit 3; fi\n"
          b"exit 0\n")


class Run(support_project.Project):
    MODULES = {"h": (support_project.HARNESS, {}), "tool": tool(helper=SCRIPT)}

    def setUp(self):
        support_project.Project.setUp(self)
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.log = os.path.join(os.path.realpath(holder.name), "ran.log")
        patch = unittest.mock.patch.dict(os.environ, {"WB_TEST_LOG": self.log})
        patch.start()
        self.addCleanup(patch.stop)

    def go(self, *args, cwd=None):
        """`wb run <args>` from `cwd`: its exit code, standard output and error text."""
        err = io.StringIO()
        with tempfile.TemporaryFile() as out:
            code = commands.run(self.guarded, list(args), err, cwd=cwd or self.real, stdout=out)
            out.seek(0)
            return code, out.read().decode(), err.getvalue()

    def ran(self):
        return os.path.exists(self.log)

    def refused(self, *args, contains=None, **kwargs):
        code, out, err = self.go(*args, **kwargs)
        self.assertEqual((1, ""), (code, out))
        self.assertEqual(1, len(err.splitlines()), err)
        self.assertTrue(err.startswith("refused: "), err)
        if contains:
            self.assertIn(contains, err)
        self.assertFalse(self.ran())

    def pinned(self, **kwargs):
        self.ready()
        self.pin(**kwargs)


class Runs(Run):
    def test_it_runs_the_pinned_helper_with_the_first_argument(self):
        self.pinned()
        code, out, err = self.go("tool", "check")
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["n:1", "a:check"], out.splitlines())

    def test_from_a_subdirectory_it_finds_the_project_above(self):
        self.pinned()
        deep = os.path.join(self.real, "docs", "a")
        os.makedirs(deep)
        code, out, err = self.go("tool", "report", cwd=deep)
        self.assertEqual((3, ""), (code, err))
        self.assertEqual(["n:1", "a:report"], out.splitlines())

    def test_the_exit_code_of_the_helper_reaches_the_caller(self):
        self.pinned()
        self.assertEqual(3, self.go("tool", "report")[0])

    def test_arguments_after_the_first_reach_the_helper_unchanged(self):
        self.pinned()
        extra = ["--root", "x", "--", "-n", "", "a b", "--help", "$HOME", ";"]
        code, out, err = self.go("tool", "check", *extra)
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["n:%d" % (1 + len(extra)), "a:check"] + ["a:" + a for a in extra],
                         out.splitlines())

    def test_nothing_is_printed_on_success(self):
        self.pinned()
        err = io.StringIO()
        shown = io.StringIO()
        with tempfile.TemporaryFile() as out:
            with unittest.mock.patch.object(sys, "stdout", shown):
                commands.run(self.guarded, ["tool", "check"], err, cwd=self.real, stdout=out)
        self.assertEqual(("", ""), (shown.getvalue(), err.getvalue()))


class RunsThroughTheKitRunner(Run):
    """A python command runs through the kit runner with the pinned number, and the exec default
    runs the file as it is. The runner is the real one, so the helper must be a kit helper."""

    def test_a_python_command_is_started_with_the_kit_number(self):
        declared = {"tool": {"helper": HELPER_PATH, "runtime": "python", "kit": 1,
                             "arguments": ["check"]}}
        self.MODULES = {"h": (support_project.HARNESS, {}), "tool": tool(declared)}
        self.ready()
        self.pin(kit=1)
        done = unittest.mock.Mock(returncode=0)
        with unittest.mock.patch("subprocess.run", return_value=done) as spawned:
            code = commands.run(self.guarded, ["tool", "check"], io.StringIO(), cwd=self.real)
        self.assertEqual(0, code)
        argv = spawned.call_args.args[0]
        self.assertEqual("-I", argv[1])
        self.assertEqual("1", argv[3])
        self.assertEqual("check", argv[-1])


class Refused(Run):
    def test_a_changed_helper_is_refused_and_does_not_run(self):
        self.pinned()
        self.edit(self.installed(), lambda data: data + b"echo changed >> \"$WB_TEST_LOG\"\n")
        self.refused("tool", "check", contains="has changed since it was pinned")

    def test_an_unpinned_command_is_refused(self):
        self.ready()
        self.unpin("tool")
        self.refused("tool", "check", contains="not pinned")

    def test_an_unknown_command_is_refused(self):
        self.pinned()
        self.refused("nothing", "check", contains="no installed module declares")

    def test_an_argument_the_declaration_does_not_list_is_refused(self):
        self.pinned()
        self.refused("tool", "delete", contains="is not an argument")

    def test_a_missing_first_argument_is_refused(self):
        self.pinned()
        self.refused("tool", contains="needs one of")

    def test_outside_a_project_it_is_refused(self):
        self.pinned()
        with tempfile.TemporaryDirectory() as elsewhere:
            self.refused("tool", "check", cwd=os.path.realpath(elsewhere))

    def test_a_hostile_name_is_shown_cleaned(self):
        self.pinned()
        code, _, err = self.go("tool\x1b[31m", "check")
        self.assertEqual(1, code)
        self.assertNotIn("\x1b", err)
        self.assertEqual(1, err.count("\n"))


class Provides(Run):
    """``wb run --provides <capability> <command>``: the module that declares the command must provide the
    capability, and the check is made by the launcher's side, before anything runs."""

    def setUp(self):
        Run.setUp(self)
        fields, files = tool(helper=SCRIPT)
        fields["provides"] = ["p:bridge"]
        self.MODULES = {"h": (support_project.HARNESS, {}), "tool": (fields, files)}

    def test_a_command_of_a_module_that_provides_the_capability_runs(self):
        self.pinned()
        code, out, err = self.go("--provides", "p:bridge", "tool", "check", "x")
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["n:2", "a:check", "a:x"], out.splitlines())

    def test_a_module_that_does_not_provide_it_is_refused_and_nothing_runs(self):
        self.pinned()
        self.refused("--provides", "p:other", "tool", "check", contains="does not provide p:other")

    def test_a_capability_that_is_not_a_name_is_refused(self):
        self.pinned()
        for bad in ("P:Bridge", "a b", "x" * 65, "-x"):
            self.refused("--provides", bad, "tool", "check", contains="is not a capability name")

    def test_an_unknown_command_is_still_refused(self):
        self.pinned()
        self.refused("--provides", "p:bridge", "nothing", "check", contains="no installed module declares")

    def test_an_unpinned_command_is_still_refused(self):
        self.ready()
        self.unpin("tool")
        self.refused("--provides", "p:bridge", "tool", "check", contains="is not pinned")

    def test_the_option_is_only_read_before_the_command(self):
        self.pinned()
        code, out, err = self.go("tool", "check", "--provides", "p:other")
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["n:3", "a:check", "a:--provides", "a:p:other"], out.splitlines())

    def test_a_missing_command_or_capability_is_a_usage_error(self):
        self.ready()
        for tokens in (("--provides",), ("--provides", "p:bridge"), ("--provides", "", "tool"),
                       ("--provides", "p:bridge", "--help"), ("--provides", "p:bridge", "")):
            self.assertEqual((2, "", commands.USAGE), self.go(*tokens), tokens)


class Usage(Run):
    def setUp(self):
        Run.setUp(self)
        self.ready()

    def test_no_command_is_a_usage_error(self):
        code, out, err = self.go()
        self.assertEqual((2, "", commands.USAGE), (code, out, err))

    def test_an_option_in_place_of_the_command_is_a_usage_error(self):
        for token in ("--help", "-x", ""):
            self.assertEqual(2, self.go(token)[0], token)


class FromTheCommandLine(Run):
    def main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(list(argv), out, err, store_root=self.store_root)
        return code, out.getvalue(), err.getvalue()

    def test_no_command_prints_the_usage_and_exits_2(self):
        code, out, err = self.main("run")
        self.assertEqual((2, ""), (code, out))
        self.assertEqual(commands.USAGE, err)

    def test_an_unpinned_command_is_one_refused_line_with_exit_1(self):
        self.ready()
        self.unpin("tool")
        with unittest.mock.patch("os.getcwd", return_value=self.real):
            code, out, err = self.main("run", "tool", "check")
        self.assertEqual((1, ""), (code, out))
        self.assertEqual(1, len(err.splitlines()), err)
        self.assertTrue(err.startswith("refused: "), err)

    def test_the_usage_text_names_run(self):
        self.assertIn("workbench run [--provides <capability>] <command>", cli.USAGE)


class Classified(unittest.TestCase):
    def test_run_is_agent_safe_and_not_owner_run(self):
        self.assertIn("run", rules.AGENT_SAFE)
        self.assertNotIn("run", rules.OWNER_RUN)


class TheInstallerNamesNoModuleCommand(unittest.TestCase):
    """The installer knows no command by name. This is the check for the commands the modules declare;
    the whole boundary test is `test_boundary`."""

    def test_no_installer_source_names_a_module_command(self):
        root = os.path.dirname(os.path.abspath(cli.__file__))
        names = support_words.command_names()
        if not names:
            return  # a distribution with no module declares no command, and an empty pattern matches all
        pattern = re.compile("|".join(re.escape(name) + "(?!-module)" for name in names))
        named = []
        for folder, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in ("shipped_approvals", "__pycache__")]
            for name in files:
                if name.endswith(".py"):
                    path = os.path.join(folder, name)
                    with open(path, encoding="utf-8") as handle:
                        # `<command>-module` is the name of a plan, not of the command.
                        if pattern.search(handle.read()):
                            named.append(os.path.relpath(path, root))
        self.assertEqual([], named)


if __name__ == "__main__":
    unittest.main()

"""`wb code-work <subcommand>`: find the project, find the pin, launch the pinned helper.

Plan `2026-10-21-code-work-plans`, increment E. The project is the fixture of increment A, a real
install whose shipped helper is a shell script that echoes its arguments, so the tests see exactly
what reached the helper."""

import io
import json
import os
import tempfile
import unittest
import unittest.mock

from tests import test_codework_fixture as fixture
from workbench import cli, dispatch, harnessplan, pins

SCRIPT = (b"#!/bin/sh\n"
          b"echo \"n:$#\"\n"
          b"for a in \"$@\"; do echo \"a:$a\"; done\n"
          b"echo ran >> \"$WB_TEST_LOG\"\n"
          b"if [ \"$1\" = plans ]; then exit 3; fi\n"
          b"exit 0\n")


class Dispatched(fixture.Fixture):
    MODULES = dict(fixture.Fixture.MODULES, codework=fixture.codework(helper=SCRIPT))

    def setUp(self):
        fixture.Fixture.setUp(self)
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.log = os.path.join(os.path.realpath(holder.name), "ran.log")
        patch = unittest.mock.patch.dict(os.environ, {"WB_TEST_LOG": self.log})
        patch.start()
        self.addCleanup(patch.stop)

    def go(self, *args, cwd=None):
        """Run `wb code-work <args>` from `cwd`: its exit code, standard output and error text."""
        err = io.StringIO()
        with tempfile.TemporaryFile() as out:
            code = dispatch.run(self.guarded, list(args), err, cwd=cwd or self.place, stdout=out)
            out.seek(0)
            return code, out.read().decode(), err.getvalue()

    def ran(self):
        return os.path.exists(self.log)

    def installed(self):
        self.ready()
        self.pinned()

    def lines(self, out):
        return out.splitlines()


class Runs(Dispatched):
    def test_from_the_project_root_it_runs_the_pinned_helper_with_the_subcommand(self):
        self.installed()
        code, out, err = self.go("check")
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(["n:1", "a:check"], self.lines(out))

    def test_from_a_subdirectory_it_finds_the_project_above(self):
        self.installed()
        deep = os.path.join(self.place, "docs", "a", "b")
        os.makedirs(deep)
        code, out, err = self.go("report", cwd=deep)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(["n:1", "a:report"], self.lines(out))
        self.assertTrue(self.ran())

    def test_the_exit_code_of_the_helper_is_returned(self):
        self.installed()
        self.assertEqual(3, self.go("plans")[0])

    def test_arguments_after_the_subcommand_reach_the_helper_unchanged(self):
        self.installed()
        extra = ["--root", "x", "--", "-n", "", "a b", "--help", "$HOME", ";"]
        code, out, err = self.go("check", *extra)
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(["n:%d" % (len(extra) + 1), "a:check"] + ["a:" + a for a in extra],
                         self.lines(out))

    def test_it_writes_nothing_into_the_project(self):
        self.installed()
        before = self.snapshot()
        self.assertEqual(0, self.go("check")[0])
        after = self.snapshot()
        self.assertEqual(before, after)

    def snapshot(self):
        found = {}
        for base, dirs, files in os.walk(self.place):
            for name in dirs + files:
                full = os.path.join(base, name)
                info = os.lstat(full)
                found[os.path.relpath(full, self.place)] = (info.st_mode, info.st_size)
        return found


class Usage(Dispatched):
    def test_only_the_three_read_only_subcommands_are_accepted_and_nothing_is_run_otherwise(self):
        self.installed()
        for args in ([], ["commit"], ["remove", "x"], ["--help"], ["-h"], [""], ["Check"],
                     ["check\n"], ["--", "check"], ["checks"]):
            with self.subTest(args=args):
                code, out, err = self.go(*args)
                self.assertEqual((2, ""), (code, out))
                self.assertTrue(err.startswith("usage: wb code-work check|plans|report"), err)
        self.assertFalse(self.ran())

    def test_the_usage_error_does_not_look_for_a_project(self):
        with tempfile.TemporaryDirectory() as bare:
            with unittest.mock.patch.object(dispatch, "find_root", side_effect=AssertionError):
                code, out, err = self.go("bogus", cwd=os.path.realpath(bare))
        self.assertEqual((2, ""), (code, out))


class Refuses(Dispatched):
    def refused(self, contains, cwd=None, *args):
        code, out, err = self.go(*(args or ("check",)), cwd=cwd)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertFalse(self.ran())

    def test_outside_any_project(self):
        self.installed()
        with tempfile.TemporaryDirectory() as bare:
            self.refused("not inside a workbench project", os.path.realpath(bare))

    def test_with_no_pin_the_message_names_the_pin_and_the_owners_step(self):
        self.ready()
        code, out, err = self.go("check")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("code-work helper is not pinned", err)
        self.assertIn("owner", err)
        self.assertFalse(self.ran())

    def test_a_project_that_has_the_manifest_but_not_the_module_has_no_pin(self):
        """Another helper is pinned for the project, but none named `code-work`."""
        self.ready()
        pins.set_pin(self.guarded, self.project_id, "other", self.shipped(),
                     pins.hash_bytes(self.read(self.shipped())), "owner")
        self.refused("not pinned")

    def test_an_edited_helper_is_not_run(self):
        self.installed()
        self.edit(self.shipped(), lambda data: data + b"echo evil\n")
        self.refused("has changed since it was pinned")

    def test_a_pin_made_for_another_project_does_not_apply(self):
        self.ready()
        other = "f" * 64 if self.project_id != "f" * 64 else "e" * 64
        pins.set_pin(self.guarded, other, "code-work", self.shipped(),
                     pins.hash_bytes(self.read(self.shipped())), "owner")
        self.refused("not pinned")

    def test_a_forged_manifest_without_a_git_directory_is_not_a_project(self):
        self.installed()
        with tempfile.TemporaryDirectory() as holder:
            forged = os.path.realpath(holder)
            os.mkdir(os.path.join(forged, ".workbench"))
            with open(os.path.join(forged, ".workbench", "manifest.json"), "wb") as handle:
                handle.write(self.read(".workbench/manifest.json"))
            self.refused("not inside a workbench project", forged)

    def test_a_git_file_as_in_a_linked_worktree_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as holder:
            tree = os.path.realpath(holder)
            os.mkdir(os.path.join(tree, ".workbench"))
            with open(os.path.join(tree, ".workbench", "manifest.json"), "wb") as handle:
                handle.write(b"{}")
            with open(os.path.join(tree, ".git"), "w") as handle:
                handle.write("gitdir: elsewhere\n")
            self.refused("not inside a workbench project", tree)

    def test_a_symbolic_link_at_the_workbench_directory_is_not_followed(self):
        self.installed()
        with tempfile.TemporaryDirectory() as holder:
            tree = os.path.realpath(holder)
            os.mkdir(os.path.join(tree, ".git"))
            os.symlink(os.path.join(self.place, ".workbench"), os.path.join(tree, ".workbench"))
            self.refused("not inside a workbench project", tree)

    def test_a_symbolic_link_at_the_manifest_is_not_followed(self):
        self.installed()
        with tempfile.TemporaryDirectory() as holder:
            tree = os.path.realpath(holder)
            os.mkdir(os.path.join(tree, ".git"))
            os.mkdir(os.path.join(tree, ".workbench"))
            os.symlink(os.path.join(self.place, ".workbench", "manifest.json"),
                       os.path.join(tree, ".workbench", "manifest.json"))
            self.refused("not inside a workbench project", tree)

    def test_a_manifest_that_is_not_a_manifest_is_refused_with_a_reason(self):
        self.installed()
        with tempfile.TemporaryDirectory() as holder:
            tree = os.path.realpath(holder)
            os.mkdir(os.path.join(tree, ".git"))
            os.mkdir(os.path.join(tree, ".workbench"))
            with open(os.path.join(tree, ".workbench", "manifest.json"), "w") as handle:
                handle.write("{}")
            self.refused("manifest cannot be used", tree)

    def test_a_project_deeper_than_the_search_limit_is_not_searched_for_ever(self):
        self.installed()
        deep = self.place
        for _ in range(dispatch.MAX_DEPTH + 2):
            deep = os.path.join(deep, "d")
        os.makedirs(deep)
        self.refused("not inside a workbench project", deep)

    def test_an_escape_in_the_start_directory_is_not_printed_raw(self):
        self.installed()
        with tempfile.TemporaryDirectory() as holder:
            weird = os.path.join(os.path.realpath(holder), "x\x1b[31my")
            os.mkdir(weird)
            code, out, err = self.go("check", cwd=weird)
        self.assertEqual(1, code)
        self.assertIn("not inside a workbench project", err)
        self.assertIn("x", err)
        self.assertNotIn("\x1b", err)

    def test_a_working_directory_that_cannot_be_read_is_a_refusal_and_not_a_traceback(self):
        self.installed()
        err = io.StringIO()
        with unittest.mock.patch("os.getcwd", side_effect=FileNotFoundError(2, "gone")):
            code = dispatch.run(self.guarded, ["check"], err)
        self.assertEqual(1, code)
        self.assertTrue(err.getvalue().startswith("refused: the working directory cannot be read"))

    def test_the_limit_is_exact_64_levels_are_searched_and_65_are_not(self):
        self.installed()
        deep = self.place
        for _ in range(dispatch.MAX_DEPTH - 1):
            deep = os.path.join(deep, "d")
        os.makedirs(deep)
        self.assertEqual(0, self.go("check", cwd=deep)[0])
        deeper = os.path.join(deep, "d")
        os.mkdir(deeper)
        os.unlink(self.log)
        self.refused("not inside a workbench project", deeper)


class Command(Dispatched):
    """The `code-work` command as `cli.main` routes it. Only refusals are run here, because the
    helper of a successful run would write to the real standard output."""

    def main(self, *argv, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch("os.getcwd", lambda: cwd or self.place):
            code = cli.main(["code-work"] + list(argv), out, err, store_root=self.store_root)
        return code, out.getvalue(), err.getvalue()

    def test_it_is_routed_before_the_option_parser(self):
        self.ready()
        self.assertEqual(2, self.main()[0])
        code, out, err = self.main("bogus", "--select")
        self.assertEqual(2, code)
        with tempfile.TemporaryDirectory() as holder:
            fresh = os.path.join(os.path.realpath(holder), "never-made")
            self.assertEqual(2, cli.main(["code-work", "commit"], io.StringIO(), io.StringIO(),
                                         store_root=fresh))
            self.assertFalse(os.path.exists(fresh))  # a usage error does not open the store
        self.assertEqual(2, code)
        self.assertTrue(err.startswith("usage: wb code-work"), err)

    def test_with_no_pin_it_refuses_through_the_command_too(self):
        self.ready()
        code, out, err = self.main("check")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("not pinned", err)

    def test_the_usage_text_lists_it_as_read_only(self):
        self.assertIn("code-work check|plans|report", cli.USAGE)

    def test_it_is_not_among_the_commands_the_claude_rules_deny(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "packages", "workbench", "claude", "module.json")) as handle:
            layout = json.load(handle)["layout"]
        document = json.loads(harnessplan.render_permissions([], layout, "/Users/t/.config/x",
                                                             "/Users/t"))
        for rule in document["permissions"]["deny"] + document["permissions"]["ask"]:
            self.assertNotIn("code-work", rule)
            self.assertNotIn(rule, ("Bash(wb *)", "Bash(wb)"))


if __name__ == "__main__":
    unittest.main()

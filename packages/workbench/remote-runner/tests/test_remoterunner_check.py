"""The `remote-runner` module's check, and the module installed in a project (conformance checklist item 3 of
`docs/specs/remote-runner.md`). Plan `2026-10-24-remote-runner-module`, increment B.

The shipped approvals are stale until increment F of the plan, so the installs here run against a copy of the
package in a temporary distribution whose approvals `release_approvals` records in that copy."""

import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock

import support_remote
from support_remote import FILE, OLD_FILE, VALID
from tests import support_install
from workbench import cli, commands, firstparty, install, manifest, pins, sources

ROOT = support_install.ROOT
SELECT = ("claude", "remote-runner")


class Report(support_remote.Project):
    def test_a_project_with_no_file_and_no_old_file_has_nothing_to_report(self):
        self.assertEqual([], self.check.report(self.root))

    def test_a_good_file_has_nothing_to_report(self):
        self.write(FILE, VALID)
        self.assertEqual([], self.check.report(self.root))

    def test_a_refused_file_is_one_problem_with_the_reason_and_none_of_the_content(self):
        self.write(FILE, VALID + "\nSECRET-MARKER = 1\n")
        before = self.snapshot()
        lines = self.check.report(self.root)
        self.assertEqual(1, len(lines))
        self.assertTrue(lines[0].startswith("problem: .workbench/remote-runner.toml: "), lines)
        self.assertNotIn("SECRET-MARKER", lines[0])
        self.assertEqual(before, self.snapshot())

    def test_an_old_file_is_reported_as_the_old_path_and_is_neither_read_nor_changed(self):
        self.write(OLD_FILE, b"SECRET-MARKER \xff not toml")
        before = self.snapshot()
        lines = self.check.report(self.root)
        self.assertEqual(1, len(lines))
        self.assertTrue(lines[0].startswith("problem: .claude/remote-runner.toml: "), lines)
        self.assertIn(".workbench/remote-runner.toml", lines[0])
        self.assertNotIn("SECRET-MARKER", lines[0])
        self.assertEqual(before, self.snapshot())

    def test_a_refused_file_and_an_old_file_are_two_problems(self):
        self.write(FILE, "project = [")
        self.write(OLD_FILE, VALID)
        lines = self.check.report(self.root)
        self.assertEqual(2, len(lines))
        self.assertTrue(all(line.startswith("problem: ") for line in lines))

    def test_a_link_in_place_of_the_file_is_a_problem_not_a_crash(self):
        outside = os.path.join(self.base, "outside.toml")
        with open(outside, "w") as handle:
            handle.write(VALID)
        os.symlink(outside, os.path.join(self.root, *FILE.split("/")))
        lines = self.check.report(self.root)
        self.assertEqual(1, len(lines))
        self.assertTrue(lines[0].startswith("problem: .workbench/remote-runner.toml: "), lines)

    def test_a_link_in_place_of_the_old_folder_is_not_followed_and_not_a_crash(self):
        outside = os.path.join(self.base, "elsewhere")
        os.makedirs(outside)
        with open(os.path.join(outside, "remote-runner.toml"), "w") as handle:
            handle.write(VALID)
        os.symlink(outside, os.path.join(self.root, ".claude"))
        self.assertEqual([], self.check.report(self.root))

    def test_an_old_file_that_is_a_directory_or_a_link_is_still_the_old_path(self):
        os.makedirs(os.path.join(self.root, ".claude", "remote-runner.toml"))
        self.assertEqual(1, len(self.check.report(self.root)))

    def test_every_line_is_ascii_bounded_and_starts_with_problem(self):
        self.write(FILE, "project = [")
        self.write(OLD_FILE, VALID)
        for line in self.check.report(self.root):
            self.assertTrue(line.isascii() and line.isprintable() and len(line) <= 300, line)

    def test_main_prints_the_lines_and_exits_zero(self):
        self.write(FILE, "project = [")
        out = io.StringIO()
        with unittest.mock.patch("sys.stdout", out), unittest.mock.patch("os.getcwd", return_value=self.root):
            code = self.check.main()
        self.assertEqual(0, code)
        self.assertEqual(self.check.report(self.root), out.getvalue().splitlines())

    def test_a_folder_that_cannot_be_read_is_one_problem(self):
        lines = self.check.report(os.path.join(self.base, "missing"))
        self.assertEqual(1, len(lines))
        self.assertTrue(lines[0].startswith("problem: "), lines)


class Installed(support_install.InstallBase):
    """Install into an empty directory, as a released copy of the package, and run `wb run` and `wb check`."""

    def setUp(self):
        support_install.InstallBase.setUp(self)
        self.dist = os.path.join(self.root, "dist")
        shutil.copytree(os.path.join(ROOT, "packages"), os.path.join(self.dist, "packages"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(ROOT, "base"), os.path.join(self.dist, "base"))
        os.makedirs(os.path.join(self.dist, "workbench"))
        done = firstparty.release_approvals(self.dist)
        self.assertEqual(1, done.packages)
        self.package_path = os.path.join(self.dist, "packages", "workbench")
        self.home = os.path.join(self.root, "home")
        os.mkdir(self.home)

    def install(self, place, select=SELECT):
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(place, [(self.package_path, None)], list(select))
        code = install.run(self.guarded, command, support_install.Typist(out, support_install.correct),
                           out, err, distribution=self.dist, seed=support_install.SEED, home=self.home)
        return code, out.getvalue(), err.getvalue()

    def write(self, place, rel, data):
        full = os.path.join(place, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data.encode("utf-8") if isinstance(data, str) else data)

    def commit(self, place):
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        for args in (["add", "-A"], ["commit", "-q", "-m", "x"]):
            done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.test",
                                   "-c", "commit.gpgsign=false"] + args, cwd=place, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(0, done.returncode, done.stderr)

    def check(self, place):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["check", place], out, err, store_root=self.store_root, distribution=self.dist,
                        home=self.home)
        return code, out.getvalue(), err.getvalue()

    def run_profiles(self, place, *args):
        errors = io.StringIO()
        before = os.getcwd()
        self.addCleanup(os.chdir, before)
        os.chdir(place)
        with tempfile.TemporaryFile() as out:
            code = commands.run(self.guarded, ["remote-runner", *args], errors, cwd=place, stdout=out)
            out.seek(0)
            return code, out.read().decode(), errors.getvalue()

    @unittest.skipUnless(shutil.which("git"), "needs git")
    def test_an_install_pins_the_command_and_the_check_and_a_clean_project_passes_check(self):
        place = self.place()
        code, out, err = self.install(place)
        self.assertEqual(0, code, (out, err))
        held = pins.load(self.guarded, manifest.project_id(support_install.SEED))
        base = ".workbench/workbench/remote-runner/helper/"
        self.assertEqual((base + "remote-runner", "workbench install", 1),
                         (held["remote-runner"].path, held["remote-runner"].pinned_by, held["remote-runner"].kit))
        self.assertEqual((base + "remote-runner-check", "workbench install", 1),
                         (held["remote-runner-check"].path, held["remote-runner-check"].pinned_by,
                          held["remote-runner-check"].kit))
        self.commit(place)
        code, out, err = self.check(place)
        self.assertEqual((0, ""), (code, err), out)
        self.assertTrue(out.endswith("check found no problems\n"), out)

    @unittest.skipUnless(shutil.which("git"), "needs git")
    def test_wb_check_reports_a_refused_file_and_an_old_file_under_the_module_name(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        self.write(place, FILE, "project = [")
        self.write(place, OLD_FILE, VALID)
        self.commit(place)
        code, out, err = self.check(place)
        self.assertEqual(1, code)
        self.assertIn("problem: workbench/remote-runner: .workbench/remote-runner.toml: ", err)
        self.assertIn("problem: workbench/remote-runner: .claude/remote-runner.toml: ", err)

    @unittest.skipUnless(shutil.which("git"), "needs git")
    def test_wb_check_reports_nothing_for_a_project_without_the_module(self):
        place = self.place()
        self.assertEqual(0, self.install(place, select=("claude", "safe-git"))[0])
        self.write(place, FILE, "project = [")
        self.write(place, OLD_FILE, VALID)
        self.commit(place)
        code, out, err = self.check(place)
        self.assertNotIn("workbench/remote-runner", err)   # the installer's own stray-file warning is not the module's
        self.assertNotIn("workbench/remote-runner", out)
    def test_wb_run_prints_the_profiles_and_refuses_another_argument(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        self.write(place, FILE, VALID)
        code, shown, err = self.run_profiles(place, "profiles")
        self.assertEqual((0, ""), (code, err), shown)
        self.assertEqual(["fast", "full"], [p["name"] for p in json.loads(shown)["profiles"]])
        code, shown, err = self.run_profiles(place, "submit")
        self.assertEqual(1, code)
        self.assertIn("is not an argument of the command", err)

    def test_an_edited_helper_is_refused_and_prints_nothing(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        self.write(place, FILE, VALID)
        with open(os.path.join(place, ".workbench", "workbench", "remote-runner", "helper", "remote-runner"),
                  "ab") as handle:
            handle.write(b"\n# edited\n")
        code, shown, err = self.run_profiles(place, "profiles")
        self.assertEqual((1, ""), (code, shown))
        self.assertIn("has changed since it was pinned", err)


if __name__ == "__main__":
    unittest.main()

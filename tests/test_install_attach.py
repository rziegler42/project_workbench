"""``wb install`` attaches as its last step: the plan lists the harness files and the digest covers
them; they are written after the install's own marker is gone; a failure there leaves a finished
install and says how to finish it."""

import hashlib
import io
import json
import os
import subprocess
import unittest
import unittest.mock

from tests import support, test_install
from tests.test_preview import NOTES
from workbench import (__version__, attach, cli, fetch, harnessstage, install, localmanifest,
                       preview, projectfs, sources)

ROOT = test_install.ROOT
CLAUDE = os.path.join(ROOT, "packages", "workbench")
MARKER = test_install.MARKER


class Base(test_install.InstallBase):
    def setUp(self):
        test_install.InstallBase.setUp(self)
        self.home = os.path.join(self.root, "home")
        os.mkdir(self.home)

    def notes(self, fields=None, files=None):
        path = self.package(modules={"notes": (fields or NOTES[0], files or NOTES[1])})
        self.approve(path)
        return path

    def command(self, place, path):
        support.require_release(self)
        return sources.Command(place, [(path, None), (CLAUDE, None)], ["claude", "notes"])

    def install(self, place, path, reply=test_install.correct):
        out, err = io.StringIO(), io.StringIO()
        code = install.run(self.guarded, self.command(place, path),
                           test_install.Typist(out, reply), out, err, seed=test_install.SEED,
                           home=self.home)
        return code, out.getvalue(), err.getvalue()

    def preview(self, place, path):
        out, err = io.StringIO(), io.StringIO()
        code = preview.run(self.guarded, self.command(place, path), out, err,
                           seed=test_install.SEED, home=self.home)
        return code, out.getvalue(), err.getvalue()

    def lines(self, place, *parts):
        return self.read(place, *parts).decode("utf-8").splitlines()


class Preview(Base):
    def test_the_preview_lists_the_harness_files_the_exclude_lines_and_the_local_manifest(self):
        code, out, err = self.preview(self.place(), self.notes())
        self.assertEqual(0, code, err)
        self.assertNotIn("harness not attached", out)
        for line in ("harness: workbench/claude is attached after the install",
                     "  create CLAUDE.md [per-clone]", "  create .claude/settings.local.json",
                     "add to .git/info/exclude: /CLAUDE.md, /.claude/",
                     "  create .workbench/local/harness.json [per-clone] sha256 ",
                     "changes what the agent may do here"):
            self.assertIn(line, out)
        self.assertIn("preview only: nothing was written", out)

    def test_the_digest_covers_the_harness_files(self):
        """The rules name the home directory, so only the harness files differ between these."""
        path = self.notes()
        digests = []
        for name in ("one", "two"):
            home = os.path.join(self.root, "home-" + name)
            os.mkdir(home)
            out, err = io.StringIO(), io.StringIO()
            command = self.command(os.path.join(self.root, "same"), path)
            code = install.run(self.guarded, command, test_install.Typist(out, lambda text: "no"),
                               out, err, seed=test_install.SEED, home=home)
            self.assertEqual(1, code, err.getvalue())
            self.assertIn("cancelled: nothing was written", out.getvalue())
            digests.append(test_install.DIGEST.findall(out.getvalue())[-1])
        self.assertNotEqual(*digests)
        self.assertFalse(os.path.exists(os.path.join(self.root, "same")))

    def test_a_harness_file_that_collides_with_an_installed_file_is_refused_unwritten(self):
        path = self.notes({"writes": ["CLAUDE.md"]}, {"files/CLAUDE.md": b"mine\n"})
        place = self.place()
        code, out, err = self.install(place, path)
        self.assertEqual(1, code)
        self.assertIn("refused:", err)
        self.assertFalse(os.path.exists(place))

    def test_a_plan_whose_harness_part_changes_after_it_is_shown_is_refused(self):
        """Each part of the harness plan is in the digest: a file's bytes, an exclude line, the
        local manifest."""
        def file_bytes(staged):
            files = []
            for f in staged.files:
                if f.path == "CLAUDE.md":
                    data = b"@AGENTX.md\n"
                    f = f._replace(data=data, sha256=hashlib.sha256(data).hexdigest())
                files.append(f)
            return staged._replace(files=files)

        changes = {
            "a file": file_bytes,
            "an exclude line": lambda staged: staged._replace(exclude=staged.exclude + ["extra"]),
            "the local manifest": lambda staged: staged._replace(
                document=dict(staged.document, tree="0" * 64)),
        }
        for name, change in changes.items():
            with self.subTest(name):
                path = self.notes()
                place = self.place("proj-" + name.replace(" ", "-"))
                real = harnessstage.stage
                calls = []

                def changing(*args):
                    staged = real(*args)
                    calls.append(1)
                    return staged if len(calls) < 2 else change(staged)

                with unittest.mock.patch.object(harnessstage, "stage", changing):
                    code, out, err = self.install(place, path)
                self.assertEqual(1, code, err)
                self.assertIn("the plan changed while it was shown", err)
                self.assertFalse(os.path.exists(place))


    def test_an_unusable_exclude_file_in_an_existing_git_is_refused_before_anything_is_written(self):
        path = self.notes()
        place = self.place("proj", "git")
        info = os.path.join(place, ".git", "info")
        os.makedirs(info)
        os.symlink(os.path.join(self.root, "elsewhere"), os.path.join(info, "exclude"))
        for run in (self.preview, self.install):
            with self.subTest(run=run.__name__):
                code, out, err = run(place, path)
                self.assertEqual(1, code)
                self.assertIn("refused: .git/info/exclude", err)
        self.assertFalse(os.path.exists(os.path.join(place, ".workbench")))

    def test_a_case_variant_of_an_installed_path_is_refused(self):
        path = self.notes({"writes": ["claude.md"]}, {"files/claude.md": b"mine\n"})
        place = self.place()
        code, out, err = self.install(place, path)
        self.assertEqual(1, code)
        self.assertIn("refused:", err)
        self.assertFalse(os.path.exists(place))


class Attached(Base):
    def test_install_writes_the_harness_files_after_its_own_marker_is_gone(self):
        path = self.notes()
        place = self.place()
        original = projectfs.Writer.create_file
        seen = {}

        def watching(writer, rel, data, executable=False):
            seen[rel] = os.path.exists(os.path.join(place, MARKER))
            return original(writer, rel, data, executable)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", watching):
            code, out, err = self.install(place, path)
        self.assertEqual(0, code, (out, err))
        self.assertTrue(seen["docs/notes.md"])
        for rel in ("CLAUDE.md", ".claude/settings.local.json", localmanifest.PATH):
            self.assertFalse(seen[rel], rel)
        self.assertFalse(os.path.exists(os.path.join(place, MARKER)))
        self.assertIn("attached workbench/claude", out)
        self.assertIn("added 2 lines to .git/info/exclude: CLAUDE.md, .claude/", out)

    def test_the_files_are_those_attach_would_write_and_nothing_is_tracked_by_git(self):
        path = self.notes()
        place = self.place()
        code, out, err = self.install(place, path)
        self.assertEqual(0, code, (out, err))
        self.assertEqual(b"@AGENTS.md\n", self.read(place, "CLAUDE.md"))
        settings = json.loads(self.read(place, ".claude", "settings.local.json"))
        self.assertIn("Bash(wb install)", settings["permissions"]["deny"])
        self.assertEqual(["/CLAUDE.md", "/.claude/"],
                         self.lines(place, ".git", "info", "exclude"))
        document = localmanifest.parse(self.read(place, localmanifest.PATH))
        self.assertEqual("claude", document["harness"])
        self.assertEqual({"CLAUDE.md", ".claude/settings.local.json"},
                         {item["path"] for item in document["files"]})
        env = fetch.git_environment()
        env["HOME"] = self.home
        status = subprocess.run(
            ["git", "-C", place, "status", "--porcelain", "--untracked-files=all"], env=env,
            capture_output=True, text=True)
        self.assertEqual(0, status.returncode, status.stderr)
        self.assertNotIn("CLAUDE.md", status.stdout)
        self.assertNotIn(".claude", status.stdout)
        self.assertIn("AGENTS.md", status.stdout)
        tracked = subprocess.run(["git", "-C", place, "ls-files"], env=env, capture_output=True,
                                 text=True)
        self.assertEqual("", tracked.stdout)

    def test_the_local_manifest_records_the_source_the_version_and_the_pin(self):
        path = self.notes()
        place = self.place()
        self.assertEqual(0, self.install(place, path)[0])
        document = localmanifest.parse(self.read(place, localmanifest.PATH))
        self.assertEqual("local:workbench", document["source"])
        self.assertEqual(__version__, document["workbench"])
        self.assertEqual(64, len(document["tree"]))

    def test_the_rules_name_the_home_directory_given_through_the_command_line(self):
        support.require_release(self)
        path = self.notes()
        place = self.place()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["install", place, "--package", path, "--package", CLAUDE,
                         "--select", "claude", "notes"], out, err, store_root=self.store_root,
                        home=self.home, stdin=test_install.Typist(out, test_install.correct))
        self.assertEqual(0, code, (out.getvalue(), err.getvalue()))
        self.assertIn(os.path.realpath(self.home), self.read(
            place, ".claude", "settings.local.json").decode())

    def test_the_preview_command_shows_the_rules_for_the_home_directory_given(self):
        support.require_release(self)
        path = self.notes()
        shown = []
        for name in ("one", "two"):
            home = os.path.join(self.root, "home-" + name)
            os.mkdir(home)
            out, err = io.StringIO(), io.StringIO()
            code = cli.main(["preview", "install", os.path.join(self.root, "same"), "--package",
                             path, "--package", CLAUDE, "--select", "claude", "notes"], out, err,
                            store_root=self.store_root, home=home)
            self.assertEqual(0, code, err.getvalue())
            shown.append([line for line in out.getvalue().splitlines()
                          if ".claude/settings.local.json" in line][0])
        self.assertNotEqual(*shown)

    def test_the_committed_manifest_does_not_name_the_harness(self):
        path = self.notes()
        place = self.place()
        self.assertEqual(0, self.install(place, path)[0])
        self.assertNotIn(b"claude", self.read(place, ".workbench", "manifest.json"))


class Failure(Base):
    def failing(self, rel_prefix, error=OSError("disk full")):
        original = projectfs.Writer.create_file

        def create(writer, rel, data, executable=False):
            if rel.startswith(rel_prefix):
                raise error
            return original(writer, rel, data, executable)

        return unittest.mock.patch.object(projectfs.Writer, "create_file", create)

    def test_a_failed_attach_leaves_a_finished_install_and_names_attach(self):
        path = self.notes()
        place = self.place()
        with self.failing("CLAUDE.md"):
            code, out, err = self.install(place, path)
        self.assertEqual(3, code)
        self.assertIn("failed: disk full\n", err)
        self.assertIn("the install is complete", err)
        self.assertIn("`wb attach --harness workbench/claude`", err)
        self.assertNotIn("Traceback", out + err)
        self.assertFalse(os.path.exists(os.path.join(place, MARKER)))
        self.assertTrue(os.path.isfile(os.path.join(place, ".workbench", "manifest.json")))
        self.assertFalse(os.path.exists(os.path.join(place, localmanifest.PATH)))
        self.assertTrue(os.path.isfile(os.path.join(place, ".claude", "settings.local.json")))
        self.assertFalse(os.path.exists(os.path.join(place, "CLAUDE.md")))
        written, _, not_written = err.partition("\nwritten:\n")[2].partition("not written:\n")
        self.assertIn("  .claude/settings.local.json\n", written)
        self.assertNotIn("AGENTS.md", written)
        self.assertNotIn(".workbench/manifest.json", written)
        self.assertIn("  CLAUDE.md\n", not_written)

    def test_a_rerun_of_attach_finishes_it(self):
        path = self.notes()
        place = self.place()
        with self.failing("CLAUDE.md"):
            self.assertEqual(3, self.install(place, path)[0])
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["attach", place, "--harness", "workbench/claude", "--package", path,
                         "--package", CLAUDE], out, err, store_root=self.store_root,
                        home=self.home)
        self.assertEqual(0, code, (out.getvalue(), err.getvalue()))
        self.assertEqual(b"@AGENTS.md\n", self.read(place, "CLAUDE.md"))
        self.assertTrue(os.path.isfile(os.path.join(place, localmanifest.PATH)))
        self.assertIn("left 1 files as they were", out.getvalue())

    def test_an_interrupt_while_attaching_is_a_failure_after_a_finished_install(self):
        path = self.notes()
        place = self.place()
        with self.failing(".claude/", KeyboardInterrupt()):
            code, out, err = self.install(place, path)
        self.assertEqual(3, code)
        self.assertIn("failed: interrupted\n", err)
        self.assertIn("the install is complete", err)

    def test_a_failure_adding_the_exclude_lines_leaves_no_harness_file(self):
        path = self.notes()
        place = self.place()
        with unittest.mock.patch.object(projectfs.Writer, "add_exclude",
                                        side_effect=OSError("no exclude")):
            code, out, err = self.install(place, path)
        self.assertEqual(3, code)
        self.assertIn("the install is complete", err)
        self.assertFalse(os.path.exists(os.path.join(place, "CLAUDE.md")))
        self.assertFalse(os.path.exists(os.path.join(place, ".claude")))

    def test_the_unfinished_write_record_does_not_list_the_harness_files(self):
        path = self.notes()
        place = self.place()
        seen = []
        original = install.record_of

        def recording(plan):
            data = original(plan)
            seen.append(data)
            return data

        with unittest.mock.patch.object(install, "record_of", recording):
            self.assertEqual(0, self.install(place, path)[0])
        for name in (b"CLAUDE.md", b".claude", b"harness.json"):
            self.assertNotIn(name, seen[0])

    def test_attach_does_not_run_when_the_install_itself_failed(self):
        path = self.notes()
        place = self.place()
        with self.failing("docs/"), unittest.mock.patch.object(attach, "apply") as applied:
            code, out, err = self.install(place, path)
        self.assertEqual(3, code)
        applied.assert_not_called()
        self.assertTrue(os.path.isfile(os.path.join(place, MARKER)))


if __name__ == "__main__":
    unittest.main()

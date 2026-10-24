"""What `remote-runner fetch` and `fetch-overwrite` do with a fake `remote-runner` (conformance checklist items 10
to 14 of `docs/specs/remote-runner.md`). Plan `2026-10-24-remote-runner-module`, increment D."""

import ast
import io
import json
import os
import shutil
import unittest

import support_program
from support_program import JOB, conformance_problems
from tests import support_install
from workbench import firstparty, install, sources

ROOT = support_install.ROOT
HELPER = os.path.join(ROOT, "packages", "workbench", "remote-runner", "helper", "remote-runner")


class Fetch(support_program.Wrapped):
    def setUp(self):
        support_program.Wrapped.setUp(self)
        os.makedirs(os.path.join(self.root, "out", "deeper"))
        os.makedirs(os.path.join(self.root, "real"))
        os.symlink(os.path.join(self.root, "real"), os.path.join(self.root, "alias"))

    def argv(self):
        return [call["argv"] for call in self.calls()]

    def test_it_passes_the_job_and_the_relative_paths_and_nothing_more(self):
        cases = [
            (("fetch", JOB, "model.bin"), ["fetch", JOB, "model.bin"]),
            (("fetch", JOB, "a/b.bin", "c.txt"), ["fetch", JOB, "a/b.bin", "c.txt"]),
            (("fetch", JOB, "model.bin", "--dest", "out"), ["fetch", JOB, "model.bin", "--dest", "out"]),
            (("fetch", "--dest", "out/deeper", JOB, "m.bin"), ["fetch", JOB, "m.bin", "--dest", "out/deeper"]),
            (("fetch", JOB, "model.bin", "--as", "renamed.bin"), ["fetch", JOB, "model.bin", "--as", "renamed.bin"]),
            (("fetch", JOB, "m.bin", "--dest", self.root + "/out", "--as", "n.bin"),
             ["fetch", JOB, "m.bin", "--dest", "out", "--as", "n.bin"]),
            (("fetch", JOB) + tuple("f%d.txt" % i for i in range(16)),
             ["fetch", JOB] + ["f%d.txt" % i for i in range(16)]),
        ]
        for args, expected in cases:
            with self.subTest(args[:4]):
                self.assertEqual(0, self.document(*args)["exit"])
                self.assertEqual(expected, self.argv()[-1])
        self.assertTrue(all("--force" not in argv for argv in self.argv()))

    def refuse(self, *args):
        code, out, err = self.run_it(*args)
        self.assertEqual((1, ""), (code, out), args)
        self.assertTrue(err.startswith("refused: ") and err.count("\n") == 1, err)

    def test_every_refused_shape_starts_nothing_and_changes_nothing(self):
        with open(os.path.join(self.root, "exists.txt"), "w") as handle:
            handle.write("mine\n")
        os.symlink(os.path.join(self.base, "nowhere"), os.path.join(self.root, "dangling"))
        os.symlink(os.path.join(self.root, "real"), os.path.join(self.root, "out", "inner-link"))
        os.mkdir(os.path.join(self.root, "adir"))
        refused = {
            "no path": ("fetch", JOB),
            "no job": ("fetch",),
            "17 paths": ("fetch", JOB) + tuple("f%d.txt" % i for i in range(17)),
            "a job without the two dashes": ("fetch", "abc", "a.txt"),
            "an absolute path": ("fetch", JOB, "/etc/passwd"),
            "a path with ..": ("fetch", JOB, "a/../b"),
            "a path that is ..": ("fetch", JOB, ".."),
            "a path with an empty part": ("fetch", JOB, "a//b"),
            "a path that names .git": ("fetch", JOB, ".git/config"),
            "a path inside .git": ("fetch", JOB, "x/.git/config"),
            "a dotted name": ("fetch", JOB, ".env"),
            "a dotted part": ("fetch", JOB, "ok/.hidden/a"),
            "a path with a leading dash": ("fetch", JOB, "-rf"),
            "a path with a backslash": ("fetch", JOB, "a\\b"),
            "a path with a control character": ("fetch", JOB, "a\x07b"),
            "a path over 512 characters": ("fetch", JOB, "a" * 513),
            "the program's force option": ("fetch", JOB, "a.txt", "--force"),
            "a repeated dest": ("fetch", JOB, "a.txt", "--dest", "out", "--dest", "out"),
            "a dest without a value": ("fetch", JOB, "a.txt", "--dest"),
            "an absolute dest outside the project": ("fetch", JOB, "a.txt", "--dest", "/tmp"),
            "a dest above the project": ("fetch", JOB, "a.txt", "--dest", "../x"),
            "a dest with ..": ("fetch", JOB, "a.txt", "--dest", "out/../out"),
            "a dest that is a dot": ("fetch", JOB, "a.txt", "--dest", "."),
            "a dest that does not exist": ("fetch", JOB, "a.txt", "--dest", "missing"),
            "a dest that is a file": ("fetch", JOB, "a.txt", "--dest", "exists.txt"),
            "a dest that is a link": ("fetch", JOB, "a.txt", "--dest", "alias"),
            "a dest below a link": ("fetch", JOB, "a.txt", "--dest", "alias/x"),
            "a dest below a link inside it": ("fetch", JOB, "a.txt", "--dest", "out/inner-link"),
            "a dest that is .git": ("fetch", JOB, "a.txt", "--dest", ".git"),
            "a dest below .workbench": ("fetch", JOB, "a.txt", "--dest", ".workbench"),
            "a dest with a leading dash": ("fetch", JOB, "a.txt", "--dest", "-x"),
            "a target that exists": ("fetch", JOB, "exists.txt"),
            "a target that is a directory": ("fetch", JOB, "adir"),
            "a target that is a dangling link": ("fetch", JOB, "dangling"),
            "a target that is a link": ("fetch", JOB, "alias"),
            "a target below a link": ("fetch", JOB, "alias/new.txt"),
            "a target below a file": ("fetch", JOB, "exists.txt/new.txt"),
            "a target that exists below dest": ("fetch", JOB, "x.txt", "--dest", "out", "--as", "deeper"),
            "--as with two paths": ("fetch", JOB, "a.txt", "b.txt", "--as", "c.txt"),
            "--as with a slash": ("fetch", JOB, "a.txt", "--as", "x/y"),
            "--as with ..": ("fetch", JOB, "a.txt", "--as", ".."),
            "--as with a leading dot": ("fetch", JOB, "a.txt", "--as", ".x"),
            "--as with a leading dash": ("fetch", JOB, "a.txt", "--as", "-x"),
            "--as that is an existing file": ("fetch", JOB, "a.txt", "--as", "exists.txt"),
            "--as without a path": ("fetch", JOB, "--as", "x.txt"),
        }
        before = self.snapshot()
        for label, args in refused.items():
            with self.subTest(label):
                self.refuse(*args)
        self.assertEqual([], self.calls())
        self.assertEqual(before, self.snapshot())

    def test_a_target_that_does_not_yet_exist_below_an_existing_folder_is_allowed(self):
        self.assertEqual(0, self.document("fetch", JOB, "out/new/deeper/file.bin")["exit"])

    def test_the_programs_files_list_with_its_hashes_is_returned_unchanged_and_the_helper_writes_nothing(self):
        listing = json.dumps({"job": JOB, "files": [{"path": "m.bin", "bytes": 3, "sha256": "ab" * 32}]}) + "\n"
        self.control(stdout=listing)
        before = self.snapshot()
        document = self.document("fetch", JOB, "m.bin")
        self.assertEqual(listing, document["output"])
        self.assertEqual("fetch", document["command"])
        self.assertEqual(before, self.snapshot())

    def test_the_helper_reads_no_fetched_file_and_writes_no_file(self):
        with open(HELPER, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    names.add(func.id)
                elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    names.add(func.value.id + "." + func.attr)
        forbidden = {"open", "os.write", "os.rename", "os.replace", "os.remove", "os.unlink", "os.mkdir",
                     "os.makedirs", "os.symlink", "os.link", "os.chmod", "shutil.copy", "shutil.move"}
        self.assertEqual(set(), names & forbidden)

    def test_a_failing_fetch_is_reported_with_the_reason(self):
        self.control(stderr="refused: target exists\n", code=1)
        code, out, err = self.run_it("fetch", JOB, "m.bin")
        document = json.loads(out)
        self.assertEqual((1, 1, "refused: target exists"), (code, document["exit"], document["detail"]))


class Overwrite(support_program.Wrapped):
    def setUp(self):
        support_program.Wrapped.setUp(self)
        with open(os.path.join(self.root, "exists.txt"), "w") as handle:
            handle.write("mine\n")
        os.makedirs(os.path.join(self.root, "out"))
        os.mkdir(os.path.join(self.root, "adir"))
        os.symlink(os.path.join(self.root, "exists.txt"), os.path.join(self.root, "link"))

    def test_it_adds_force_and_may_replace_an_existing_regular_file(self):
        document = self.document("fetch-overwrite", JOB, "exists.txt")
        self.assertEqual("fetch-overwrite", document["command"])
        self.assertEqual(["fetch", JOB, "exists.txt", "--force"], self.calls()[0]["argv"])

    def test_it_keeps_the_options_and_puts_force_last(self):
        self.document("fetch-overwrite", JOB, "m.bin", "--dest", "out", "--as", "n.bin")
        self.assertEqual(["fetch", JOB, "m.bin", "--dest", "out", "--as", "n.bin", "--force"],
                         self.calls()[0]["argv"])

    def test_it_still_refuses_a_directory_a_link_a_bad_path_and_a_bad_dest(self):
        for args in (("adir",), ("link",), ("exists.txt/x",), ("/etc/passwd",), ("..",), (".env",), ("a.txt", "--force"),
                     ("a.txt", "--dest", "../x"), ("a.txt", "--dest", ".git"), ("a.txt", "b.txt", "--as", "c.txt")):
            with self.subTest(args):
                code, out, err = self.run_it("fetch-overwrite", JOB, *args)
                self.assertEqual((1, ""), (code, out))
                self.assertTrue(err.startswith("refused: "), err)
        self.assertEqual([], self.calls())

    def test_it_is_a_separate_argument_so_that_fetch_alone_is_never_given_force(self):
        self.document("fetch", JOB, "new.txt")
        self.assertNotIn("--force", self.calls()[0]["argv"])
        code, out, err = self.run_it("fetch", JOB, "exists.txt")
        self.assertEqual(1, code)
        self.assertEqual(1, len(self.calls()))


class Conformance(support_program.Wrapped):
    def conforming(self, mode):
        self.control(fetch=mode)
        scratch = os.path.join(self.base, "scratch-" + mode)
        os.makedirs(os.path.join(scratch, "project"))
        return conformance_problems(self, os.path.join(self.outside, "remote-runner"),
                                    os.path.join(scratch, "project"))

    def test_a_program_that_refuses_what_it_should_conforms(self):
        self.assertEqual([], self.conforming("conforming"))

    def test_a_program_that_overwrites_writes_through_a_link_or_takes_a_dotted_name_is_reported(self):
        problems = self.conforming("overwriting")
        self.assertEqual(3, len(problems), problems)
        self.assertIn("it overwrote an existing file without --force", problems)

    def test_the_wrappers_own_check_still_refuses_first_when_the_program_does_not_conform(self):
        self.control(fetch="overwriting")
        with open(os.path.join(self.root, "exists.txt"), "w") as handle:
            handle.write("mine\n")
        before = self.snapshot()
        code, out, err = self.run_it("fetch", JOB, "exists.txt")
        self.assertEqual((1, ""), (code, out))
        self.assertEqual([], self.calls())
        self.assertEqual(before, self.snapshot())

    def test_a_fetch_through_the_wrapper_places_a_new_file_and_nothing_else(self):
        self.control(fetch="conforming")
        document = self.document("fetch", JOB, "new/file.bin")
        self.assertEqual(0, document["exit"])
        self.assertEqual(["new/file.bin"], [f["path"] for f in json.loads(document["output"])["files"]])
        with open(os.path.join(self.root, "new", "file.bin")) as handle:
            self.assertEqual("fetched\n", handle.read())


class Installed(support_install.InstallBase):
    """The Claude settings rendered for an attached module."""

    def setUp(self):
        support_install.InstallBase.setUp(self)
        self.dist = os.path.join(self.root, "dist")
        shutil.copytree(os.path.join(ROOT, "packages"), os.path.join(self.dist, "packages"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(ROOT, "base"), os.path.join(self.dist, "base"))
        os.makedirs(os.path.join(self.dist, "workbench"))
        firstparty.release_approvals(self.dist)
        self.package_path = os.path.join(self.dist, "packages", "workbench")
        self.home = os.path.join(self.root, "home")
        os.mkdir(self.home)

    def test_the_declaration_lists_fetch_overwrite_as_owner_run(self):
        with open(os.path.join(ROOT, "packages", "workbench", "remote-runner", "module.json")) as handle:
            command = json.load(handle)["commands"]["remote-runner"]
        self.assertEqual(["fetch-overwrite"], command["owner"])
        self.assertIn("fetch", command["arguments"])
        self.assertIn("fetch-overwrite", command["arguments"])

    def test_the_rendered_claude_settings_deny_fetch_overwrite_and_not_the_others_and_allow_nothing(self):
        place = self.place()
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(place, [(self.package_path, None)], ["claude", "remote-runner"])
        code = install.run(self.guarded, command, support_install.Typist(out, support_install.correct), out, err,
                           distribution=self.dist, seed=support_install.SEED, home=self.home)
        self.assertEqual(0, code, (out.getvalue(), err.getvalue()))
        with open(os.path.join(place, ".claude", "settings.local.json"), encoding="utf-8") as handle:
            permissions = json.load(handle)["permissions"]
        deny = " ".join(permissions["deny"])
        self.assertIn("run remote-runner fetch-overwrite", deny)
        for argument in ("profiles", "recommend", "status", "artifacts", "submit"):
            self.assertNotIn("remote-runner %s" % argument, deny)
        self.assertNotRegex(deny, r"remote-runner fetch(?!-overwrite)")
        self.assertNotIn("remote-runner", " ".join(permissions.get("allow", [])))


if __name__ == "__main__":
    unittest.main()

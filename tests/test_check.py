import hashlib
import io
import json
import os
import subprocess
import unittest
import unittest.mock

from tests import support_harness
from tests.test_attach import Base
from workbench import check, cli, firstparty, gitindex, harnesses, localmanifest, sources

LOCAL = localmanifest.PATH
SETTINGS = ".fixture/settings.local.json"
HARNESS_PATHS = ["FIXTURE.md", ".fixture/agents/reviewer.md", ".fixture/commands/ship.md", SETTINGS,
                 ".fixture/skills/sample/SKILL.md"]


class Clone(Base):
    """A project installed as `install` writes it, in a real git repository with everything
    committed, so what git tracks is real."""

    def ready(self, **changes):
        package = Base.ready(self, **changes)
        os.unlink(os.path.join(self.place, ".git", "index"))
        self.git("init", "-q", "--template=")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "install")
        return package

    def git(self, *args, data=b""):
        """Run real git in the project, with nothing from the machine's configuration."""
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.test",
                               "-c", "commit.gpgsign=false", "-c", "gc.auto=0",
                               "-c", "maintenance.auto=false"] + list(args), cwd=self.place,
                              env=env, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(0, done.returncode, done.stderr)
        return done.stdout

    def check(self, *args, place=None):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["check", place or self.place] + list(args), out, err,
                        store_root=self.store_root, home=self.home, distribution=self.dist)
        return code, out.getvalue(), err.getvalue()

    def attached(self):
        self.ready()
        self.assertEqual(0, self.attach()[0])

    def write(self, rel, data):
        full = os.path.join(self.place, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data)

    def problems(self, err):
        return [line for line in err.splitlines() if line.startswith("problem: ")]


class Check(Clone):
    def test_a_clean_clone_has_no_problems_and_says_what_the_record_is(self):
        self.attached()
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)
        self.assertIn("harness: fixture attached in", out)
        self.assertIn("scratch record", out)
        self.assertTrue(out.endswith("check found no problems\n"), out)

    def test_a_clone_with_none_attached_is_valid_and_says_so(self):
        self.ready()
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)
        self.assertIn("harness: none attached in", out)
        self.assertNotIn("scratch record", out)

    def test_files_of_a_harness_beside_none_attached_warn_and_do_not_fail(self):
        self.ready()
        self.write(".fixture/settings.json", b"{}\n")
        code, out, err = self.check()
        self.assertEqual(0, code, err)
        self.assertIn("warning: .fixture belongs to the harness fixture, and no harness is attached",
                      err)
        self.assertEqual([], self.problems(err))

    def test_an_edited_generated_file_is_a_problem(self):
        self.attached()
        self.write(".fixture/commands/ship.md", b"edited\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(["problem: .fixture/commands/ship.md: differs from what attach wrote"],
                         self.problems(err))
        self.assertTrue(out.endswith("check found 1 problem\n"), out)

    def test_a_missing_generated_file_is_a_problem(self):
        self.attached()
        os.unlink(os.path.join(self.place, "FIXTURE.md"))
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(1, len(self.problems(err)), err)
        self.assertIn("problem: FIXTURE.md: missing", err)

    def test_an_extra_file_under_a_generated_directory_is_a_problem(self):
        self.attached()
        self.write(".fixture/skills/sample/notes.md", b"mine\n")
        self.write(".fixture/agents/extra.md", b"mine\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(["problem: .fixture/agents/extra.md: not a file attach wrote",
                          "problem: .fixture/skills/sample/notes.md: not a file attach wrote"],
                         sorted(self.problems(err)))

    def test_a_link_in_a_generated_directory_is_reported_and_not_followed(self):
        self.attached()
        secret = os.path.join(self.outside, "secret")
        with open(secret, "wb") as handle:
            handle.write(b"x")
        os.symlink(self.outside, os.path.join(self.place, ".fixture", "skills", "linked"))
        os.symlink(secret, os.path.join(self.place, ".fixture", "agents", "leak.md"))
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: .fixture/skills/linked: not a file attach wrote", err)
        self.assertIn("problem: .fixture/agents/leak.md: not a file attach wrote", err)
        self.assertNotIn("secret", err)

    def test_a_recorded_file_replaced_by_a_link_is_a_problem(self):
        self.attached()
        target = os.path.join(self.outside, "elsewhere")
        with open(target, "wb") as handle:
            handle.write(b"@AGENTS.md\n")
        full = os.path.join(self.place, "FIXTURE.md")
        os.unlink(full)
        os.symlink(target, full)
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: FIXTURE.md: cannot be read", err)

    def test_a_linked_harness_directory_is_a_problem(self):
        self.attached()
        agents = os.path.join(self.place, ".fixture", "agents")
        for name in os.listdir(agents):
            os.unlink(os.path.join(agents, name))
        os.rmdir(agents)
        os.symlink(self.outside, agents)
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn(".fixture/agents/reviewer.md: cannot be read", err)
        self.assertIn("problem: .fixture/agents: unreadable", err)

    def test_the_local_manifest_is_not_evidence(self):
        """A file edited together with the scratch record is not reported: no drift means the
        file matches the record, and the output says that is all it means."""
        self.attached()
        data = b"edited and recorded\n"
        self.write(".fixture/commands/ship.md", data)
        document = self.planned()
        for item in document["files"]:
            if item["path"] == ".fixture/commands/ship.md":
                item["hash"] = hashlib.sha256(data).hexdigest()
        with open(os.path.join(self.place, *LOCAL.split("/")), "wb") as handle:
            handle.write(localmanifest.serialize(document))
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)
        self.assertIn("not a file known to be safe", out)

    def test_a_damaged_local_manifest_is_a_problem(self):
        self.attached()
        self.write(LOCAL, b"{}\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: %s: " % LOCAL, err)

    def test_nothing_is_written_and_the_index_is_unchanged(self):
        self.attached()
        self.write(".fixture/agents/extra.md", b"mine\n")
        before = (self.content(), self.content(self.store_root))
        index = self.read(".git/index")
        self.check()
        self.assertEqual(before, (self.content(), self.content(self.store_root)))
        self.assertEqual(index, self.read(".git/index"))

    def test_a_target_that_is_not_a_project_is_refused(self):
        empty = os.path.join(self.root, "empty")
        os.mkdir(empty)
        code, out, err = self.check(place=empty)
        self.assertEqual((1, ""), (code, out))
        self.assertTrue(err.startswith("refused: the target is not an existing project"), err)

    def test_the_options_are_checked(self):
        for tokens in (["--bad"], ["one", "two"], ["--dir"], [""]):
            with self.subTest(tokens=tokens):
                out, err = io.StringIO(), io.StringIO()
                self.assertEqual(2, cli.main(["check"] + tokens, out, err,
                                             store_root=self.store_root))
        with self.assertRaises(sources.UsageError):
            check.parse(["--dir", "a", "--dir", "b"])

    def test_the_findings_are_bounded(self):
        self.attached()
        for number in range(check.LISTED + 5):
            self.write(".fixture/commands/x%d.md" % number, b"x\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(check.LISTED + 1, len(self.problems(err)))
        self.assertIn("problem: and 5 more", err)

    def test_other_entries_directly_under_the_harness_directory_warn(self):
        self.attached()
        self.write(".fixture/hooks/x.sh", b"#!/bin/sh\n")
        code, out, err = self.check()
        self.assertEqual(0, code, err)
        self.assertTrue(out.endswith("check found no problems\n"), out)
        self.assertIn("warning: .fixture/hooks: not written by attach", err)

    def test_hostile_names_are_cleaned_in_the_findings(self):
        self.attached()
        self.write(".fixture/agents/evil\x1b[2Jname.md", b"x\n")
        os.mkdir(os.path.join(self.place, ".fixture", "skills", "bi\u202edi"))
        self.write(".fixture/skills/bi\u202edi/f.md", b"x\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertNotIn("\x1b", err)
        self.assertNotIn("\u202e", err)
        for line in err.splitlines():
            self.assertTrue(line.startswith(("problem: ", "warning: ")), line)

    def test_the_scan_is_bounded_in_entries_and_depth(self):
        self.attached()
        with unittest.mock.patch.object(check, "MAX_ENTRIES", 3):
            for number in range(6):
                self.write(".fixture/commands/y%d.md" % number, b"x\n")
            code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("not all were looked at", err)
        deep = ".fixture/skills/sample" + "/d" * (check.MAX_DEPTH + 2) + "/f.md"
        self.write(deep, b"x\n")
        code, out, err = self.check()
        self.assertIn("nested too deeply", err)

    def test_a_recorded_path_below_a_linked_directory_is_unreadable(self):
        self.attached()
        sample = os.path.join(self.place, ".fixture", "skills", "sample")
        os.unlink(os.path.join(sample, "SKILL.md"))
        os.rmdir(sample)
        os.symlink(self.outside, sample)
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: .fixture/skills/sample/SKILL.md: cannot be read", err)

    def test_an_unknown_harness_name_is_valid_and_has_no_stray_scan(self):
        self.attached()
        document = self.planned()
        document["harness"] = "stranger"
        with open(os.path.join(self.place, *LOCAL.split("/")), "wb") as handle:
            handle.write(localmanifest.serialize(document))
        self.write(".fixture/agents/extra.md", b"x\n")
        code, out, err = self.check()
        self.assertIn("harness: stranger attached", out)
        self.assertIn("warning: stranger is not a harness this workbench knows, so its files were "
                      "not scanned", err)
        self.assertNotIn("extra.md: not a file", err)

    def test_files_of_another_known_harness_are_problems(self):
        support_harness.write_package(self.dist, support_harness.renamed(support_harness.SYNTHETIC),
                                      package="second", module="second")
        firstparty.release_approvals(self.dist)
        self.attached()
        self.write("SECOND.md", b"x\n")
        self.write(".second/notes.md", b"x\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(["problem: .second belongs to the harness second, not to the attached fixture",
                          "problem: SECOND.md belongs to the harness second, not to the attached fixture"],
                         sorted(self.problems(err)))

    def test_a_name_two_first_party_packages_declare_is_not_scanned(self):
        support_harness.write_package(self.dist, support_harness.renamed(support_harness.SYNTHETIC),
                                      package="copy", module=support_harness.MODULE)
        firstparty.release_approvals(self.dist)
        self.attached()
        self.write(".fixture/agents/extra.md", b"x\n")
        code, out, err = self.check()
        self.assertIn("warning: fixture is declared by more than one first-party package, so its "
                      "files were not scanned", err)
        self.assertNotIn("extra.md: not a file", err)

    def test_every_recorded_path_is_looked_at(self):
        self.attached()
        for path in HARNESS_PATHS:
            os.unlink(os.path.join(self.place, *path.split("/")))
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(len(HARNESS_PATHS), len(self.problems(err)), err)
        self.assertIn(SETTINGS, err)


class Tracked(Clone):
    """What git tracks: harness output and scratch, pointers into untracked content, the
    committed manifest, and no program run for any of it."""

    def entries(self):
        return json.loads(self.read(".workbench/manifest.json"))["files"]

    def first(self, owner_class):
        return next(item for item in self.entries() if item["class"] == owner_class)

    def force_add(self, *paths):
        self.git("add", "-f", "--", *paths)

    def test_a_clean_project_says_the_manifest_is_tracked(self):
        self.ready()
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)
        self.assertIn("manifest: tracked by git\n", out)

    def test_an_uncommitted_manifest_is_reported_and_is_not_a_problem(self):
        self.ready()
        self.git("rm", "-q", "--cached", ".workbench/manifest.json")
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)
        self.assertIn("manifest: not tracked by git, so it is not committed", out)

    def test_a_project_with_nothing_committed_warns_once_for_the_recorded_files(self):
        self.ready()
        os.unlink(os.path.join(self.place, ".git", "index"))
        code, out, err = self.check()
        self.assertEqual(0, code, err)
        self.assertIn("manifest: not tracked by git", out)
        self.assertEqual(1, [line.startswith("warning: ") and "not tracked by git yet" in line
                             for line in err.splitlines()].count(True), err)

    def test_tracked_harness_output_and_scratch_are_problems(self):
        self.attached()
        self.write(".debug/2026-10-21-x/README", b"x\n")
        self.force_add("FIXTURE.md", SETTINGS, ".debug/2026-10-21-x/README", LOCAL)
        code, out, err = self.check()
        self.assertEqual(1, code)
        found = sorted(self.problems(err))
        for path, what in (("FIXTURE.md", "output of the harness fixture"),
                           (SETTINGS, "output of the harness fixture"),
                           (LOCAL, "scratch"), (".debug/2026-10-21-x/README", "scratch")):
            self.assertIn("problem: %s: tracked by git, but it looks like %s" % (path, what), found)

    def test_paths_are_matched_without_case(self):
        tracked = gitindex.Tracked(frozenset({".Fixture/notes", ".DEBUG/x", "Fixture.md", "src/a"}),
                                   frozenset(), frozenset())
        self.assertEqual(
            ["%s: tracked by git, but it looks like %s" % item for item in
             ((".DEBUG/x", "scratch"), (".Fixture/notes", "output of the harness fixture"),
              ("Fixture.md", "output of the harness fixture"))],
            check._generated(tracked, harnesses.known(self.dist)))

    def test_documents_that_point_into_untracked_content_are_problems(self):
        self.ready()
        self.write("scratch.txt", b"x\n")
        self.write("build/out.md", b"x\n")
        self.write("docs/guide.md", (
            "[a](../scratch.txt) ![i](/build/out.md) [r][ref]\n\n[ref]: <../build/out.md>\n\n"
            "<a href=\"../scratch.txt#frag\">h</a>\n\n@../scratch.txt and (@docs/missing.md)\n"
            "[local](../.debug/notes.md) [away](../../elsewhere.md) @~/notes.md @/etc/passwd\n"
        ).encode())
        self.git("add", "docs/guide.md")
        code, out, err = self.check()
        self.assertEqual(1, code)
        found = self.problems(err)
        self.assertIn("problem: docs/guide.md: points to scratch.txt, which git does not track", found)
        self.assertIn("problem: docs/guide.md: points to build/out.md, which git does not track", found)
        self.assertIn("problem: docs/guide.md: points to .debug/notes.md, which git does not track",
                      found)
        self.assertIn("problem: docs/guide.md: points outside the project: ../../elsewhere.md", found)
        self.assertIn("problem: docs/guide.md: points outside the project: ~/notes.md", found)
        self.assertIn("problem: docs/guide.md: points outside the project: /etc/passwd", found)
        self.assertEqual(1, found.count(
            "problem: docs/guide.md: points to scratch.txt, which git does not track"))
        self.assertNotIn("missing.md", err)

    def test_what_the_rule_allows_is_not_flagged(self):
        self.ready()
        self.write("scratch.txt", b"x\n")
        self.write("docs/ok.md", (
            "See [the readme](../AGENTS.md#top) and [the web](https://example.test/x.md), "
            "[mail](mailto:a@b.test), [anchor](#here), [dir](../docs/), [gone](../none.md).\n"
            "Prose names `scratch.txt` and scratch.txt and .debug/x and /local/ and a@scratch.txt.\n"
            "```\n[a](../scratch.txt)\n@scratch.txt\n```\n~~~\n[b](../scratch.txt)\n~~~\n"
            "Inline `[c](../scratch.txt)` too.\n").encode())
        self.write("src/code.py", b"# [a](../scratch.txt)\nx = '@scratch.txt'\n")
        self.git("add", "docs/ok.md", "src/code.py")
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)

    def test_a_tracked_link_is_a_warning_and_is_not_followed(self):
        self.ready()
        secret = os.path.join(self.outside, "secret.md")
        with open(secret, "wb") as handle:
            handle.write(b"[a](../scratch.txt)\n")
        os.symlink(secret, os.path.join(self.place, "docs", "leak.md"))
        self.git("add", "docs/leak.md")
        code, out, err = self.check()
        self.assertEqual(0, code, err)
        self.assertIn("warning: docs/leak.md: a link that git tracks; where it points is not "
                      "checked", err)
        self.assertNotIn("secret", err)

    def test_a_module_owned_file_that_differs_is_a_problem_and_a_seeded_one_is_not(self):
        self.ready()
        owned = self.first("module-owned")["path"]
        seeded = self.first("seeded")["path"]
        self.write(owned, self.read(owned) + b"edited\n")
        self.write(seeded, self.read(seeded) + b"mine\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(["problem: %s: a module-owned file that differs from the manifest" % owned],
                         self.problems(err))

    def test_a_missing_module_owned_file_and_an_edited_block_are_problems(self):
        self.ready()
        owned = self.first("module-owned")["path"]
        block = self.first("slot block")
        os.unlink(os.path.join(self.place, *owned.split("/")))
        self.write(block["path"], self.read(block["path"]).replace(b"Rule A", b"Rule Z"))
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: %s: a module-owned file that is missing from the manifest" % owned,
                      err)
        self.assertIn("problem: %s: the block %s differs from the manifest"
                      % (block["path"], block["block"]), err)

    def test_an_edited_file_that_git_does_not_track_is_not_reported_as_committed(self):
        self.ready()
        owned = self.first("module-owned")["path"]
        self.git("rm", "-q", "--cached", owned)
        self.write(owned, b"edited\n")
        code, out, err = self.check()
        self.assertEqual(0, code, err)
        self.assertIn("not tracked by git yet", err)

    def test_a_damaged_manifest_is_a_problem(self):
        self.ready()
        self.write(".workbench/manifest.json", b"{}\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: .workbench/manifest.json: ", err)

    def test_nothing_in_the_repository_configuration_runs_and_the_index_is_unchanged(self):
        self.attached()
        marker = os.path.join(self.outside, "ran")
        program = os.path.join(self.outside, "program.sh")
        with open(program, "w") as handle:
            handle.write("#!/bin/sh\necho ran >> %s\n" % marker)
        os.chmod(program, 0o755)
        extra = os.path.join(self.outside, "extra.config")
        with open(extra, "w") as handle:
            handle.write("[core]\n\tfsmonitor = %s\n" % program)
        with open(os.path.join(self.place, ".git", "config"), "a") as handle:
            handle.write("[core]\n\tfsmonitor = %s\n\thooksPath = %s\n\tsshCommand = %s\n"
                         "\teditor = %s\n[include]\n\tpath = %s\n[filter \"x\"]\n\tclean = %s\n"
                         "\tsmudge = %s\n[diff]\n\texternal = %s\n"
                         % ((program,) * 4 + (extra,) + (program,) * 3))
        self.write(".gitattributes", b"* filter=x\n")
        index = self.read(".git/index")
        calls = []

        def forbidden(*args, **kwargs):
            calls.append(args)
            raise AssertionError("a program was started")

        with unittest.mock.patch.object(subprocess, "Popen", forbidden), \
                unittest.mock.patch.object(os, "system", forbidden), \
                unittest.mock.patch.object(os, "execv", forbidden), \
                unittest.mock.patch.object(os, "posix_spawn", forbidden):
            code, out, err = self.check()
        self.assertEqual([], calls)
        self.assertEqual(0, code, err)
        self.assertFalse(os.path.exists(marker))
        self.assertEqual(index, self.read(".git/index"))

    def test_a_large_index_is_read(self):
        self.ready()
        empty = self.git("hash-object", "-w", "--stdin").decode().strip()
        lines = "".join("100644 %s 0\tbig/n%06d.txt\n" % (empty, number) for number in range(150000))
        self.git("update-index", "--add", "--index-info", data=lines.encode())
        self.assertGreater(os.path.getsize(os.path.join(self.place, ".git", "index")), 4 << 20)
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)
        self.assertIn("manifest: tracked by git\n", out)

    def test_a_damaged_local_manifest_does_not_stop_the_git_checks(self):
        self.attached()
        self.write(LOCAL, b"{}\n")
        self.force_add("FIXTURE.md")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: %s: " % LOCAL, err)
        self.assertIn("problem: FIXTURE.md: tracked by git", err)
        self.assertIn("manifest: tracked by git\n", out)

    def test_a_tracked_document_that_cannot_be_read_is_reported(self):
        self.ready()
        entry = b"\0" * 24 + b"\x00\x00\x81\xa4" + b"\0" * 12 + b"\0" * 20
        body = b""
        for path in (b"../x.md", b"docs/a.md"):
            one = entry + len(path).to_bytes(2, "big") + path
            body += one + b"\0" * (-(len(one) + 1) % 8 + 1)
        data = b"DIRC" + (2).to_bytes(4, "big") + (2).to_bytes(4, "big") + body
        data += hashlib.sha1(data).digest()
        self.write(".git/index", data)
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: 1 tracked document could not be read, so it was not looked at", err)

    def test_an_index_that_is_a_link_is_a_problem_and_is_not_followed(self):
        self.ready()
        real = os.path.join(self.outside, "index")
        os.rename(os.path.join(self.place, ".git", "index"), real)
        os.symlink(real, os.path.join(self.place, ".git", "index"))
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: .git/index: it cannot be read", err)
        self.assertIn("manifest: not known", out)

    def test_a_damaged_index_is_a_problem_and_the_other_checks_still_run(self):
        self.attached()
        self.write(".git/index", b"DIRC" + b"\0" * 40)
        self.write(".fixture/agents/extra.md", b"x\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: .git/index: ", err)
        self.assertIn("problem: .fixture/agents/extra.md: not a file attach wrote", err)

    def test_an_index_over_the_limit_is_a_problem(self):
        self.ready()
        with unittest.mock.patch.object(gitindex, "LIMIT", 100):
            code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: .git/index: it cannot be read", err)

    def test_the_number_of_documents_and_references_looked_at_is_bounded(self):
        self.ready()
        self.write("scratch.txt", b"x\n")
        for number in range(4):
            self.write("docs/d%d.md" % number, b"[a](../scratch.txt)\n")
        self.git("add", "docs")
        with unittest.mock.patch.object(check, "MAX_DOCUMENTS", 2):
            code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("not all were looked at", err)
        with unittest.mock.patch.object(check, "MAX_LOOKUPS", 1):
            code, out, err = self.check()
        self.assertIn("not all were looked at", err)
        with unittest.mock.patch.object(check, "MAX_DOCUMENT_BYTES", 10):
            code, out, err = self.check()
        self.assertIn("not all were looked at", err)

    def test_documents_over_four_mebibytes_in_all_are_looked_at_in_full(self):
        self.ready()
        for number in range(3):
            self.write("docs/big%d.md" % number, b"x" * (1536 * 1024) + b"\n")
        self.git("add", "docs")
        code, out, err = self.check()
        self.assertNotIn("not all were looked at", err)
        self.assertEqual(0, code)

    def test_hostile_names_in_what_git_tracks_are_cleaned(self):
        self.ready()
        self.write("docs/x.md", "[a](../ev\x1b[2Jil‮.txt)\n".encode())
        self.write("ev\x1b[2Jil‮.txt", b"x\n")
        self.write(".debug/e\x1b[2Jv‮il", b"x\n")
        self.git("add", "-f", "-A")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertNotIn("\x1b", err)
        self.assertNotIn("‮", err)
        for line in err.splitlines():
            self.assertTrue(line.startswith(("problem: ", "warning: ")), line)


if __name__ == "__main__":
    unittest.main()

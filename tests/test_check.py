import hashlib
import io
import os
import unittest
import unittest.mock

from tests.test_attach import HARNESS_PATHS, LOCAL, SETTINGS, Base
from workbench import check, cli, localmanifest, sources


class Check(Base):
    def check(self, *args, place=None):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["check", place or self.place] + list(args), out, err,
                        store_root=self.store_root, home=self.home)
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

    def test_a_clean_clone_has_no_problems_and_says_what_the_record_is(self):
        self.attached()
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)
        self.assertIn("harness: claude attached in", out)
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
        self.write(".claude/settings.json", b"{}\n")
        code, out, err = self.check()
        self.assertEqual(0, code, err)
        self.assertIn("warning: .claude belongs to the harness claude, and no harness is attached",
                      err)
        self.assertEqual([], self.problems(err))

    def test_an_edited_generated_file_is_a_problem(self):
        self.attached()
        self.write(".claude/commands/ship.md", b"edited\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(["problem: .claude/commands/ship.md: differs from what attach wrote"],
                         self.problems(err))
        self.assertTrue(out.endswith("check found 1 problem\n"), out)

    def test_a_missing_generated_file_is_a_problem(self):
        self.attached()
        os.unlink(os.path.join(self.place, "CLAUDE.md"))
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(1, len(self.problems(err)), err)
        self.assertIn("problem: CLAUDE.md: missing", err)

    def test_an_extra_file_under_a_generated_directory_is_a_problem(self):
        self.attached()
        self.write(".claude/skills/sample/notes.md", b"mine\n")
        self.write(".claude/agents/extra.md", b"mine\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(["problem: .claude/agents/extra.md: not a file attach wrote",
                          "problem: .claude/skills/sample/notes.md: not a file attach wrote"],
                         sorted(self.problems(err)))

    def test_a_link_in_a_generated_directory_is_reported_and_not_followed(self):
        self.attached()
        secret = os.path.join(self.outside, "secret")
        with open(secret, "wb") as handle:
            handle.write(b"x")
        os.symlink(self.outside, os.path.join(self.place, ".claude", "skills", "linked"))
        os.symlink(secret, os.path.join(self.place, ".claude", "agents", "leak.md"))
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: .claude/skills/linked: not a file attach wrote", err)
        self.assertIn("problem: .claude/agents/leak.md: not a file attach wrote", err)
        self.assertNotIn("secret", err)

    def test_a_recorded_file_replaced_by_a_link_is_a_problem(self):
        self.attached()
        target = os.path.join(self.outside, "elsewhere")
        with open(target, "wb") as handle:
            handle.write(b"@AGENTS.md\n")
        full = os.path.join(self.place, "CLAUDE.md")
        os.unlink(full)
        os.symlink(target, full)
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: CLAUDE.md: cannot be read", err)

    def test_a_linked_harness_directory_is_a_problem(self):
        self.attached()
        agents = os.path.join(self.place, ".claude", "agents")
        for name in os.listdir(agents):
            os.unlink(os.path.join(agents, name))
        os.rmdir(agents)
        os.symlink(self.outside, agents)
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn(".claude/agents/reviewer.md: cannot be read", err)
        self.assertIn("problem: .claude/agents: unreadable", err)

    def test_files_of_another_harness_are_a_problem(self):
        self.attached()
        self.write("opencode.json", b"{}\n")
        os.mkdir(os.path.join(self.place, ".codex"))
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(["problem: .codex belongs to the harness codex, not to the attached claude",
                          "problem: opencode.json belongs to the harness opencode, not to the "
                          "attached claude"], sorted(self.problems(err)))

    def test_the_local_manifest_is_not_evidence(self):
        """A file edited together with the scratch record is not reported: no drift means the
        file matches the record, and the output says that is all it means."""
        self.attached()
        data = b"edited and recorded\n"
        self.write(".claude/commands/ship.md", data)
        document = self.planned()
        for item in document["files"]:
            if item["path"] == ".claude/commands/ship.md":
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
        self.write(".claude/agents/extra.md", b"mine\n")
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
            self.write(".claude/commands/x%d.md" % number, b"x\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(check.LISTED + 1, len(self.problems(err)))
        self.assertIn("problem: and 5 more", err)

    def test_other_entries_directly_under_the_harness_directory_warn(self):
        self.attached()
        self.write(".claude/hooks/x.sh", b"#!/bin/sh\n")
        self.write(".claude/settings.json", b"{}\n")
        code, out, err = self.check()
        self.assertEqual(0, code, err)
        self.assertTrue(out.endswith("check found no problems\n"), out)
        self.assertIn("warning: .claude/hooks: not written by attach", err)
        self.assertNotIn("settings.json", err)

    def test_hostile_names_are_cleaned_in_the_findings(self):
        self.attached()
        self.write(".claude/agents/evil\x1b[2Jname.md", b"x\n")
        os.mkdir(os.path.join(self.place, ".claude", "skills", "bi\u202edi"))
        self.write(".claude/skills/bi\u202edi/f.md", b"x\n")
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
                self.write(".claude/commands/y%d.md" % number, b"x\n")
            code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("not all were looked at", err)
        deep = ".claude/skills/sample" + "/d" * (check.MAX_DEPTH + 2) + "/f.md"
        self.write(deep, b"x\n")
        code, out, err = self.check()
        self.assertIn("nested too deeply", err)

    def test_a_recorded_path_below_a_linked_directory_is_unreadable(self):
        self.attached()
        sample = os.path.join(self.place, ".claude", "skills", "sample")
        os.unlink(os.path.join(sample, "SKILL.md"))
        os.rmdir(sample)
        os.symlink(self.outside, sample)
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: .claude/skills/sample/SKILL.md: cannot be read", err)

    def test_an_unknown_harness_name_is_valid_and_has_no_stray_scan(self):
        self.attached()
        document = self.planned()
        document["harness"] = "gemini"
        with open(os.path.join(self.place, *LOCAL.split("/")), "wb") as handle:
            handle.write(localmanifest.serialize(document))
        self.write(".claude/agents/extra.md", b"x\n")
        code, out, err = self.check()
        self.assertIn("harness: gemini attached", out)
        self.assertNotIn("extra.md: not a file", err)

    def test_every_recorded_path_is_looked_at(self):
        self.attached()
        for path in HARNESS_PATHS:
            os.unlink(os.path.join(self.place, *path.split("/")))
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(len(HARNESS_PATHS), len(self.problems(err)), err)
        self.assertIn(SETTINGS, err)


if __name__ == "__main__":
    unittest.main()

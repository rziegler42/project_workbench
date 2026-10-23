"""What is specific to the Claude Code harness, run against the real module.

The installer's tests use a synthetic harness for the mechanism; the paths, the settings file and the
files `wb check` expects to find are Claude's, so they are asserted here."""

import hashlib
import io
import json
import os
import subprocess
import unittest

from tests import support, support_install
from workbench import cli, layout, localmanifest, rules, verify

CLAUDE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = os.path.dirname(CLAUDE_DIR)
MODULE = os.path.join(CLAUDE_DIR, "module.json")
SETTINGS = ".claude/settings.local.json"
LOCAL = localmanifest.PATH
WRITTEN = ["CLAUDE.md", ".claude/agents/reviewer.md", ".claude/commands/ship.md", SETTINGS,
           ".claude/skills/sample/SKILL.md"]


def declared():
    with open(MODULE, encoding="utf-8") as handle:
        return json.load(handle)["layout"]


class Facts(unittest.TestCase):
    def test_the_layout_is_accepted(self):
        self.assertEqual([], layout.problems(declared()))

    def test_the_facts_are_the_roots_the_generated_directories_and_the_tolerated_file(self):
        self.assertEqual(layout.facts(declared()), {
            "roots": ("CLAUDE.md", ".claude"), "directories": (".claude",),
            "generated": (".claude/skills", ".claude/agents", ".claude/commands"),
            "tolerated": (".claude/settings.json",),
            "hook_targets": (("Edit", ("file_path",)), ("MultiEdit", ("file_path",)),
                             ("NotebookEdit", ("notebook_path",)), ("Write", ("file_path",)))})

    def test_the_tolerated_file_is_not_one_the_layout_writes(self):
        document = declared()
        self.assertNotEqual(document["local_settings"]["path"], document["tolerated"][0])
        self.assertTrue(document["tolerated"][0].startswith(".claude/"))


class Project(support_install.Base):
    """The project installed as `install` writes it, in a real git repository with everything
    committed, and the shipped Claude module to attach."""

    def ready(self, **changes):
        package = support_install.Base.ready(self, **changes)
        os.unlink(os.path.join(self.place, ".git", "index"))
        self.git("init", "-q", "--template=")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "install")
        return package

    def git(self, *args):
        """Real git in the project, with nothing from the machine's configuration."""
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.test",
                               "-c", "commit.gpgsign=false"] + list(args), cwd=self.place, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(0, done.returncode, done.stderr)
        return done.stdout

    def attach(self, *args, **kwargs):
        """Attach this module itself, from the running distribution."""
        support.require_release(self)
        kwargs.setdefault("harness", "workbench/claude")
        kwargs.setdefault("package", PACKAGE)
        kwargs.setdefault("dist", None)
        return support_install.Base.attach(self, *args, **kwargs)

    def warm(self, path):
        cli.main(["verify", path], io.StringIO(), io.StringIO(), store_root=self.store_root)

    def attached(self):
        self.ready()
        code, out, err = self.attach()
        self.assertEqual(0, code, err)

    def check(self):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["check", self.place], out, err, store_root=self.store_root, home=self.home)
        return code, out.getvalue(), err.getvalue()

    def write(self, rel, data):
        full = os.path.join(self.place, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data)

    def problems(self, err):
        return [line for line in err.splitlines() if line.startswith("problem: ")]


class Attached(Project):
    def test_it_writes_exactly_the_claude_files_and_excludes_them(self):
        self.ready()
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        document = self.planned()
        self.assertEqual(sorted(WRITTEN), [f["path"] for f in document["files"]])
        for item in document["files"]:
            self.assertEqual(item["hash"], hashlib.sha256(self.read(item["path"])).hexdigest())
        self.assertEqual(b"@AGENTS.md\n", self.read("CLAUDE.md"))
        self.assertEqual(b"/CLAUDE.md\n/.claude/\n", self.read(".git/info/exclude"))
        self.assertIn("note: Restart the Claude session to load the new settings.\n", out)

    def test_the_record_and_the_report_name_this_module(self):
        self.ready()
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertTrue(out.startswith("attached workbench/claude 0.1.0 in "), out)
        document = self.planned()
        self.assertEqual(("claude", "0.1.0", "local:workbench"),
                         (document["harness"], document["module_version"], document["source"]))
        verified = next(m for m in verify.verify_package(PACKAGE, first_party=True).modules if m.name == "claude")
        self.assertEqual(verified.tree_hash, document["tree"])

    def test_the_tolerated_file_is_not_written(self):
        self.ready()
        self.assertEqual(0, self.attach()[0])
        self.assertFalse(os.path.exists(os.path.join(self.place, ".claude", "settings.json")))

    def test_the_settings_deny_every_owner_run_command_and_the_store_and_never_allow(self):
        self.ready()
        self.assertEqual(0, self.attach()[0])
        permissions = json.loads(self.read(SETTINGS))["permissions"]
        self.assertEqual(["ask", "deny"], sorted(permissions))
        store = os.path.realpath(self.store_root).lstrip("/")
        for command in rules.OWNER_RUN:
            self.assertIn("Bash(wb %s)" % command, permissions["deny"])
            self.assertIn("Bash(wb %s *)" % command, permissions["deny"])
            self.assertIn("Bash(python3 -m workbench %s *)" % command, permissions["deny"])
        self.assertIn("Edit(//%s/**)" % store, permissions["deny"])
        self.assertIn("Bash(git push --force*)", permissions["ask"])

    def test_the_settings_deny_approving_a_plan_in_every_spelling_and_let_the_agent_read_its_status(self):
        self.ready()
        self.assertEqual(0, self.attach()[0])
        permissions = json.loads(self.read(SETTINGS))["permissions"]
        for spelling in rules.SPELLINGS:
            self.assertIn("Bash(%s approve-plan)" % spelling, permissions["deny"])
            self.assertIn("Bash(%s approve-plan *)" % spelling, permissions["deny"])
            for rule in permissions["deny"] + permissions["ask"]:
                self.assertFalse(rule.startswith("Bash(%s plan-status" % spelling), rule)


class Checked(Project):
    def test_a_clean_attach_has_no_problems(self):
        self.attached()
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)
        self.assertIn("harness: claude attached in", out)
        self.assertTrue(out.endswith("check found no problems\n"), out)

    def test_a_file_under_a_generated_directory_that_attach_did_not_write_is_a_problem(self):
        self.attached()
        self.write(".claude/skills/other/SKILL.md", b"mine\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertEqual(["problem: .claude/skills/other/SKILL.md: not a file attach wrote"],
                         self.problems(err))

    def test_an_unknown_entry_beside_the_tolerated_file_warns_and_the_tolerated_file_does_not(self):
        self.attached()
        self.write(".claude/hooks/x.sh", b"#!/bin/sh\n")
        self.write(".claude/settings.json", b"{}\n")
        code, out, err = self.check()
        self.assertEqual(0, code, err)
        self.assertTrue(out.endswith("check found no problems\n"), out)
        self.assertIn("warning: .claude/hooks: not written by attach", err)
        self.assertNotIn("settings.json", err)

    def test_a_tracked_claude_path_is_a_problem(self):
        self.attached()
        self.git("add", "-f", "--", "CLAUDE.md", SETTINGS)
        code, out, err = self.check()
        self.assertEqual(1, code)
        found = self.problems(err)
        for path in ("CLAUDE.md", SETTINGS):
            self.assertIn("problem: %s: tracked by git, but it looks like output of the harness "
                          "claude" % path, found)


if __name__ == "__main__":
    unittest.main()

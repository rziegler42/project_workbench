"""A confined agent's hook, rendered by attach: into the agent's own file, with a deny for that file, a note, and
the drift report of ``check``.

The project, its module, its agents and the harness layout are synthetic (``test_agent_gate.Guarded``); the installer
under test knows no module, agent or harness."""

import io
import json
import os
import unittest

from tests import test_agent_gate, test_check
from workbench import cli, localmanifest

CONFINED = ("checker", "writer", "runner")
AGENTS = ".fixture/agents/%s.md"
SETTINGS = ".fixture/settings.local.json"


class Attaches(test_agent_gate.Guarded):
    def attached(self):
        synth = os.path.join(self.gdist, "packages", "synthetic")
        code, out, err = self.attach(dist=self.gdist, package=synth)
        self.assertEqual(0, code, err)
        return out, err

    def read(self, rel):
        with open(os.path.join(self.place, *rel.split("/")), "rb") as handle:
            return handle.read()

    def denied(self):
        return json.loads(self.read(SETTINGS))["permissions"]["deny"]


class Rendered(Attaches):

    def test_each_confined_agents_file_carries_its_own_hook(self):
        self.attached()
        for name in CONFINED:
            text = self.read(AGENTS % name).decode()
            self.assertIn('    - matcher: "Bash|Edit|Write"\n', text)
            self.assertIn('          command: "wb agent-gate fixture %s || exit 2"\n' % name, text)
            self.assertIn("          timeout: 20\n---\n", text)

    def test_an_agent_without_limits_is_written_as_before(self):
        self.attached()
        self.assertEqual(b'---\nname: "plain"\ndescription: "Reads"\ntools: "Glob, Grep, Read"\n---\nRead.\n',
                         self.read(AGENTS % "plain"))

    def test_the_hook_is_not_in_the_settings_file_that_holds_the_edit_gate(self):
        self.attached()
        self.assertNotIn(b"agent-gate", self.read(SETTINGS))

    def test_the_deny_covers_each_confined_file_in_every_spelling_and_no_other(self):
        self.attached()
        deny = self.denied()
        for name in CONFINED:
            for rule in ("Edit(%s)", "Edit(**/%s)", "Edit(//%s)"):
                text = rule % ((AGENTS % name) if "//" not in rule else os.path.join(self.real, AGENTS % name).lstrip("/"))
                self.assertIn(text, deny)
        self.assertEqual([], [rule for rule in deny if "plain" in rule])

    def test_there_is_one_note_for_each_confined_agent_and_none_for_the_other(self):
        out, err = self.attached()
        notes = [line for line in out.splitlines() if "is confined by a hook" in line]
        self.assertEqual(sorted("note: agent/%s is confined by a hook in its own file." % n for n in CONFINED),
                         sorted(line.split(" The harness")[0] for line in notes))
        self.assertTrue(all("only in a folder it trusts" in line for line in notes))
        self.assertNotIn("agent/plain is confined", out + err)

    def test_the_same_input_renders_the_same_bytes_so_a_file_already_there_is_left(self):
        self.attached()
        before = self.content()
        os.unlink(os.path.join(self.place, *localmanifest.PATH.split("/")))
        synth = os.path.join(self.gdist, "packages", "synthetic")
        code, out, err = self.attach(dist=self.gdist, package=synth)
        self.assertEqual(0, code, err)
        self.assertEqual(before, self.content())
        self.assertNotIn("wrote ", out)
        self.assertIn("left 6 files", out)


class Checked(Attaches):
    git = test_check.Clone.git

    def attached(self):
        os.unlink(os.path.join(self.place, ".git", "index"))
        self.git("init", "-q", "--template=")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "install")
        return Attaches.attached(self)

    def test_check_reports_an_edited_confined_file(self):
        self.attached()
        path = os.path.join(self.place, *(AGENTS % "checker").split("/"))
        with open(path, "ab") as handle:
            handle.write(b"edited\n")
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["check", self.place], out, err, store_root=self.store_root, home=self.home,
                        distribution=self.gdist)
        self.assertEqual(1, code, err.getvalue())
        self.assertIn("problem: %s: differs from what attach wrote" % (AGENTS % "checker"), err.getvalue())

    def test_check_finds_nothing_after_a_clean_attach(self):
        self.attached()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["check", self.place], out, err, store_root=self.store_root, home=self.home,
                        distribution=self.gdist)
        self.assertEqual(0, code, err.getvalue())


class Skipped(test_agent_gate.Guarded):
    def test_a_harness_with_no_such_entries_installs_the_ordinary_agent_only(self):
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertFalse(os.path.exists(os.path.join(self.place, ".fixture", "agents", "checker.md")))
        self.assertTrue(os.path.exists(os.path.join(self.place, ".fixture", "agents", "plain.md")))
        self.assertIn("warning: skipped: agent/checker", err)


if __name__ == "__main__":
    unittest.main()

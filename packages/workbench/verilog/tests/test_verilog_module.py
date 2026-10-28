"""The real `verilog` module in `packages/workbench/`: its declaration, its file list and its neutral skills
(criteria 1 to 3 of plan `2026-10-28-verilog-module`). The package tree hash changes with this module, so the shipped
approvals are stale until increment C of that plan. The tests prove structure and scope; the skills' technical advice
is read, not run."""

import json
import os
import re
import unittest

from tests import support_install
from workbench import neutral, verify

ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "verilog")
NEUTRAL = os.path.join(MODULE, "harness", "neutral")
SKILLS = ("verilog-verilator-sim", "verilog-sby-formal")


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as handle:
        return handle.read()


def declaration():
    return json.loads(read(MODULE, "module.json"))


def skill_text(name):
    return read(NEUTRAL, "skills", name, "SKILL.md")


def reference_text(name):
    return read(NEUTRAL, "skills", name, "reference.md")


class Declaration(unittest.TestCase):
    def test_it_verifies_as_a_first_party_module(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=("verilog",), harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertIn("verilog", [m.name for m in result.modules])

    def test_it_provides_nothing_and_ships_no_program(self):
        document = declaration()
        self.assertEqual("module", document["type"])
        for field in ("provides", "requires", "helpers", "ships", "commands", "checks", "fills", "writes", "blocks",
                      "slots", "layout", "approval"):
            self.assertNotIn(field, document)

    def test_the_package_lists_it(self):
        self.assertIn("verilog", json.loads(read(PACKAGE, "package.json"))["modules"])

    def test_it_ships_exactly_the_two_skills(self):
        self.assertEqual(["verilog-sby-formal", "verilog-verilator-sim"], sorted(SKILLS))
        shipped = sorted(os.listdir(os.path.join(NEUTRAL, "skills")))
        self.assertEqual(sorted(SKILLS), shipped)

    def test_every_file_is_the_declaration_or_a_skill_file(self):
        expected = ["module.json"]
        for name in SKILLS:
            expected += ["harness/neutral/skills/%s/SKILL.md" % name,
                         "harness/neutral/skills/%s/reference.md" % name]
        found = []
        for base, dirs, files in os.walk(MODULE):
            if base == MODULE:
                dirs.remove("tests")  # the module's own tests are not part of what it installs
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                found.append(os.path.relpath(os.path.join(base, name), MODULE))
        self.assertEqual(sorted(expected), sorted(found))

    def test_the_reader_takes_each_skill_with_its_reference_file(self):
        files = {}
        for name in SKILLS:
            for leaf in ("SKILL.md", "reference.md"):
                path = "skills/%s/%s" % (name, leaf)
                with open(os.path.join(NEUTRAL, path), "rb") as handle:
                    files[path] = handle.read()
        items = neutral.read_items(files)
        self.assertEqual(sorted(SKILLS), sorted(item.name for item in items))
        for item in items:
            self.assertEqual(["reference.md"], [bundled.rel for bundled in item.files])


class Skills(unittest.TestCase):
    def test_each_has_its_name_and_a_one_line_description(self):
        for name in SKILLS:
            match = re.match(r"---\nname: %s\ndescription: ([^\n]+)\n---\n" % re.escape(name), skill_text(name))
            self.assertIsNotNone(match, name)
            self.assertGreater(len(match.group(1)), 40, name)
            self.assertLessEqual(len(match.group(1)), neutral.MAX_DESCRIPTION_CHARS, name)

    def test_each_begins_with_its_scope(self):
        for name in SKILLS:
            body = skill_text(name).split("\n---\n", 1)[1]
            opening = body.strip().split("\n\n")[1]  # the paragraph after the heading
            for phrase in ("plain Verilog-2001", "SystemVerilog", "out of scope", "stop and tell the owner"):
                self.assertIn(phrase, opening, "%s: %s" % (name, phrase))

    def test_the_formal_skill_ties_a_new_assume_to_a_written_source_and_the_owner(self):
        text = skill_text("verilog-sby-formal")
        for phrase in ("written source", "conditional task", "unweakened", "never as an unconditional pass",
                       "tell the owner"):
            self.assertIn(phrase, text, phrase)

    def test_each_points_to_its_reference_file(self):
        for name in SKILLS:
            self.assertIn("reference.md", skill_text(name), name)

    def test_the_text_names_no_vendor_harness_or_personal_path(self):
        for name in SKILLS:
            for text in (skill_text(name), reference_text(name)):
                lowered = text.lower()
                for word in ("claude", "codex", "anthropic", "openai", "~/", "/users/", "/home/", ".claude",
                             "superpowers", "global_config"):
                    self.assertNotIn(word, lowered, "%s: %s" % (name, word))

    def test_the_text_sends_the_reader_nowhere_outside_the_project(self):
        for name in SKILLS:
            for text in (skill_text(name), reference_text(name)):
                for word in ("http://", "https://", "curl ", "wget ", "pip install", "npm install", "apt install",
                             "apt-get", "brew install", "sudo "):
                    self.assertNotIn(word, text, "%s: %s" % (name, word))

    def test_the_text_does_not_tell_the_agent_to_install_a_program(self):
        for name in SKILLS:
            for text in (skill_text(name), reference_text(name)):
                self.assertIsNone(re.search(r"\binstall(ing)?\b", text, re.IGNORECASE), name)


if __name__ == "__main__":
    unittest.main()

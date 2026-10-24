"""The real `security-review` module in `packages/workbench/`: its declaration, its file list and its neutral skill
(criterion 1 of plan `2026-10-24-security-review-module`, increment B). The package tree hash changes with this module,
so the shipped approvals are stale until increment E of that plan."""

import json
import os
import re
import unittest

from tests import support_install
from workbench import verify

ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "security-review")
SKILL = os.path.join(MODULE, "harness", "neutral", "skills", "security-review", "SKILL.md")


def declaration():
    with open(os.path.join(MODULE, "module.json"), encoding="utf-8") as handle:
        return json.load(handle)


def skill_text():
    with open(SKILL, encoding="utf-8") as handle:
        return handle.read()


class Declaration(unittest.TestCase):
    def test_it_verifies_as_a_first_party_module(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=("security-review",), harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertIn("security-review", [m.name for m in result.modules])

    def test_it_provides_security_review_and_ships_no_program(self):
        document = declaration()
        self.assertEqual("module", document["type"])
        self.assertEqual(["security-review"], document["provides"])
        for field in ("requires", "helpers", "ships", "commands", "checks", "fills", "writes", "blocks", "slots",
                      "layout", "approval"):
            self.assertNotIn(field, document)

    def test_the_package_lists_it(self):
        with open(os.path.join(PACKAGE, "package.json"), encoding="utf-8") as handle:
            self.assertIn("security-review", json.load(handle)["modules"])

    def test_every_file_is_the_declaration_the_skill_or_the_agent(self):
        found = []
        for base, dirs, files in os.walk(MODULE):
            if base == MODULE:
                dirs.remove("tests")  # the module's own tests are not part of what it installs
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                found.append(os.path.relpath(os.path.join(base, name), MODULE))
        self.assertEqual(sorted(["module.json", "harness/neutral/skills/security-review/SKILL.md",
                                 "harness/neutral/agents/security-reviewer.md"]), sorted(found))


class Skill(unittest.TestCase):
    def test_it_has_the_name_and_a_one_line_description(self):
        match = re.match(r"---\nname: security-review\ndescription: ([^\n]+)\n---\n", skill_text())
        self.assertIsNotNone(match)
        self.assertGreater(len(match.group(1)), 40)

    def test_it_says_what_a_review_covers_and_how_it_reports(self):
        text = skill_text()
        for phrase in ("changed boundary", "attacker", "fake program", "copy", "data", "tested", "read only",
                       "found sound", "Critical", "Low", "residual risk", "does not fix"):
            self.assertIn(phrase, text, phrase)

    def test_it_names_no_vendor_harness_or_personal_path(self):
        text = skill_text().lower()
        for word in ("claude", "codex", "anthropic", "openai", "~/", "/users/", ".claude", "superpowers",
                     "workflow-reviewer"):
            self.assertNotIn(word, text, word)

    def test_it_sends_the_reader_nowhere_outside_the_project(self):
        text = skill_text()
        for word in ("http://", "https://", "curl ", "pip install", "npm install"):
            self.assertNotIn(word, text, word)


if __name__ == "__main__":
    unittest.main()

"""The real `freecad` module in `packages/workbench/`: its declaration, its file list and its neutral skills
(criteria 1 to 3 of plan `2026-10-28-freecad-module`). The package tree hash changes with this module, so the shipped
approvals are stale until the last increment of that plan. The tests prove structure and scope; the skills' technical
advice is checked by running FreeCAD 1.1.4 where the plan says so, and that is recorded in the plan, not tested here."""

import json
import os
import re
import shutil
import tempfile
import unittest

from tests import support_install
from workbench import neutral, verify

ROOT = support_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "freecad")
NEUTRAL = os.path.join(MODULE, "harness", "neutral")
SKILLS = ("freecad-python",)
BUNDLED = {}  # skill name -> files it ships below its folder besides SKILL.md and reference.md


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as handle:
        return handle.read()


def declaration():
    return json.loads(read(MODULE, "module.json"))


def skill_text(name):
    return read(NEUTRAL, "skills", name, "SKILL.md")


def reference_text(name):
    return read(NEUTRAL, "skills", name, "reference.md")


def description(name):
    match = re.match(r"---\nname: %s\ndescription: ([^\n]+)\n---\n" % re.escape(name), skill_text(name))
    return match.group(1) if match else None


class Declaration(unittest.TestCase):
    def test_it_verifies_as_a_first_party_module(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=("freecad",), harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertIn("freecad", [m.name for m in result.modules])

    def test_it_provides_nothing_and_ships_no_program(self):
        document = declaration()
        self.assertEqual("module", document["type"])
        for field in ("provides", "requires", "helpers", "ships", "commands", "checks", "fills", "writes", "blocks",
                      "slots", "layout", "approval"):
            self.assertNotIn(field, document)

    def test_the_package_lists_it(self):
        self.assertIn("freecad", json.loads(read(PACKAGE, "package.json"))["modules"])

    def test_it_ships_exactly_the_planned_skills(self):
        self.assertEqual(sorted(SKILLS), sorted(os.listdir(os.path.join(NEUTRAL, "skills"))))

    def test_every_file_is_the_declaration_or_a_skill_file(self):
        expected = ["module.json"]
        for name in SKILLS:
            expected += ["harness/neutral/skills/%s/%s" % (name, leaf)
                         for leaf in ("SKILL.md", "reference.md") + tuple(BUNDLED.get(name, ()))]
        found = []
        for base, dirs, files in os.walk(MODULE):
            if base == MODULE:
                dirs.remove("tests")  # the module's own tests are not part of what it installs
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for name in files:
                found.append(os.path.relpath(os.path.join(base, name), MODULE))
        self.assertEqual(sorted(expected), sorted(found))

    def test_the_reader_takes_each_skill_with_its_bundled_files(self):
        files = {}
        for name in SKILLS:
            for leaf in ("SKILL.md", "reference.md") + tuple(BUNDLED.get(name, ())):
                with open(os.path.join(NEUTRAL, "skills", name, leaf), "rb") as handle:
                    files["skills/%s/%s" % (name, leaf)] = handle.read()
        items = neutral.read_items(files)
        self.assertEqual(sorted(SKILLS), sorted(item.name for item in items))
        for item in items:
            self.assertEqual(sorted(("reference.md",) + tuple(BUNDLED.get(item.name, ()))),
                             sorted(bundled.rel for bundled in item.files))

    def test_a_script_bundled_in_a_skill_is_accepted_by_the_reader_and_the_verifier(self):
        """Choice 2 of the plan: the mesh script ships beside a SKILL.md as a plain file, not as a pinned helper."""
        with tempfile.TemporaryDirectory() as tmp:
            package = os.path.join(tmp, "pkg")
            os.makedirs(package)
            with open(os.path.join(package, "package.json"), "w", encoding="utf-8") as handle:
                json.dump({"name": "workbench", "version": "0.1.0", "contract": 1, "modules": ["freecad"]}, handle)
            shutil.copytree(MODULE, os.path.join(package, "freecad"), ignore=shutil.ignore_patterns("tests", "__pycache__"))
            scripts = os.path.join(package, "freecad", "harness", "neutral", "skills", SKILLS[0], "scripts")
            os.makedirs(scripts)
            with open(os.path.join(scripts, "probe.py"), "w", encoding="utf-8") as handle:
                handle.write("print('probe')\n")
            result = verify.verify_package(package, first_party=True, select=("freecad",), harness_required=False)
            self.assertTrue(result.accepted, [str(p) for p in result.problems])
            files = {}
            neutral_dir = os.path.join(package, "freecad", "harness", "neutral")
            for base, _dirs, names in os.walk(neutral_dir):
                for leaf in names:
                    path = os.path.join(base, leaf)
                    with open(path, "rb") as handle:
                        files[os.path.relpath(path, neutral_dir).replace(os.sep, "/")] = handle.read()
            item = [i for i in neutral.read_items(files) if i.name == SKILLS[0]][0]
            self.assertIn("scripts/probe.py", [bundled.rel for bundled in item.files])


class Skills(unittest.TestCase):
    def test_each_has_its_name_and_a_one_line_description(self):
        for name in SKILLS:
            text = description(name)
            self.assertIsNotNone(text, name)
            self.assertGreater(len(text), 40, name)
            self.assertLessEqual(len(text), neutral.MAX_DESCRIPTION_CHARS, name)
            self.assertTrue(text.startswith("Use when "), name)

    def test_the_descriptions_differ(self):
        texts = [description(name) for name in SKILLS]
        self.assertEqual(len(texts), len(set(texts)))

    def test_each_begins_with_its_scope(self):
        for name in SKILLS:
            body = skill_text(name).split("\n---\n", 1)[1]
            opening = body.strip().split("\n\n")[1]  # the paragraph after the heading
            for phrase in ("FreeCAD 1.1", "stop and tell the owner"):
                self.assertIn(phrase, opening, "%s: %s" % (name, phrase))

    def test_each_points_to_its_reference_file(self):
        for name in SKILLS:
            self.assertIn("reference.md", skill_text(name), name)

    def test_the_text_names_no_vendor_harness_or_personal_path(self):
        for name in SKILLS:
            for text in (skill_text(name), reference_text(name)):
                lowered = text.lower()
                for word in ("claude", "codex", "anthropic", "openai", "~/", "/users/", "/home/", ".claude",
                             "superpowers", "global_config", "/opt/"):
                    self.assertNotIn(word, lowered, "%s: %s" % (name, word))

    def test_the_text_sends_the_reader_nowhere_outside_the_project(self):
        for name in SKILLS:
            for text in (skill_text(name), reference_text(name)):
                for word in ("http://", "https://", "curl ", "wget ", "pip install", "npm install", "apt install",
                             "apt-get", "brew install", "sudo ", "download"):
                    self.assertNotIn(word, text.lower(), "%s: %s" % (name, word))

    def test_the_text_does_not_tell_the_agent_to_install_a_program(self):
        for name in SKILLS:
            for text in (skill_text(name), reference_text(name)):
                self.assertIsNone(re.search(r"\binstall(ing)?\b", text, re.IGNORECASE), name)


if __name__ == "__main__":
    unittest.main()

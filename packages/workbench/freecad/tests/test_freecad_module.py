"""The real `freecad` module in `packages/workbench/`: its declaration, its file list and its neutral skills
(criteria 1 to 3 of plan `2026-10-28-freecad-module`). The package tree hash changes with this module, so the shipped
approvals are stale until the last increment of that plan. The tests prove structure and scope; the skills' technical
advice is checked by running FreeCAD 1.1.4 where the plan says so, and that is recorded in the plan, not tested here."""

import ast
import hashlib
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
SKILLS = ("freecad-python", "freecad-part", "freecad-sketcher", "freecad-partdesign",
          "freecad-parameters", "freecad-mesh", "freecad-reverse-engineering",
          "freecad-image-to-model", "freecad-measure-and-inspection", "freecad-import-export",
          "freecad-assembly", "freecad-fem", "freecad-curves", "freecad-curved-shapes",
          "freecad-gui-and-workbenches", "freecad-macros", "freecad-mcp", "freecad-draft", "freecad-surface", "freecad-techdraw")
BUNDLED = {"freecad-reverse-engineering": ("scripts/mesh_report.py",)}  # files below a skill besides SKILL.md and reference.md
SCRIPT = os.path.join(NEUTRAL, "skills", "freecad-reverse-engineering", "scripts", "mesh_report.py")
# The sha-256 of the owner's script as read on 2026-10-28 (plan 2026-10-28-freecad-module, Assumptions).
SCRIPT_SHA256 = "4f7930f406d4ef099bedc5c577fb7cbbb539f2fdc28edb5929f3e9206f362667"
SCRIPT_IMPORTS = {"json", "os", "math", "sys", "FreeCAD", "Mesh", "numpy", "Part"}


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


class Script(unittest.TestCase):
    """The one script the module ships. It runs only under FreeCAD's own interpreter, so these tests read it as text."""

    def source(self):
        with open(SCRIPT, "rb") as handle:
            return handle.read()

    def test_it_is_byte_identical_to_the_script_that_was_read(self):
        self.assertEqual(SCRIPT_SHA256, hashlib.sha256(self.source()).hexdigest())

    def test_it_is_the_only_script_in_the_module(self):
        found = []
        for base, dirs, files in os.walk(MODULE):
            if base == MODULE:
                dirs.remove("tests")
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            found += [os.path.relpath(os.path.join(base, n), MODULE) for n in files if not n.endswith(".md") and n != "module.json"]
        self.assertEqual(["harness/neutral/skills/freecad-reverse-engineering/scripts/mesh_report.py"], found)

    def test_it_imports_only_what_it_needs(self):
        tree = ast.parse(self.source().decode("utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertEqual(set(), imported - SCRIPT_IMPORTS)

    def test_it_starts_no_program_and_uses_no_network_or_evaluation(self):
        text = self.source().decode("utf-8")
        for word in ("subprocess", "socket", "urllib", "ftplib", "shutil", "http", "os.system", "os.popen",
                     "exec(", "eval(", "__import__"):
            self.assertNotIn(word, text, word)

    def test_it_keeps_its_guard_on_the_json_target(self):
        text = self.source().decode("utf-8")
        for fragment in ("refusing --json target", "os.path.islink(target)", "os.path.abspath(path)", '!= ".json"'):
            self.assertIn(fragment, text, fragment)


class Corrections(unittest.TestCase):
    """What increment H-A of the plan added to earlier skills, after runs in FreeCAD 1.1.4 found it missing or wrong."""

    def test_part_says_a_boolean_returns_a_compound_that_has_no_centre_of_mass(self):
        lines = skill_text("freecad-part").splitlines()
        self.assertTrue(any("Compound" in line and "CenterOfMass" in line for line in lines))

    def test_part_has_a_mirror_and_an_array_section_in_its_reference(self):
        text = reference_text("freecad-part")
        for heading in ("## Mirror a shape", "## Arrays of a shape"):
            self.assertIn(heading, text)

    def test_part_warns_that_a_compound_of_overlapping_copies_is_not_merged(self):
        text = skill_text("freecad-part")
        self.assertIn("does not merge", text)

    def test_the_gmsh_row_of_the_removed_api_table_is_no_longer_marked_read(self):
        rows = [line for line in skill_text("freecad-python").splitlines() if "Gmsh" in line]
        self.assertEqual(1, len(rows))
        self.assertNotIn("(read)", rows[0])

if __name__ == "__main__":
    unittest.main()

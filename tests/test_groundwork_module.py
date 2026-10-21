"""The real `groundwork` module in `packages/workbench/`: its declaration, its READMEs, and an
install that creates the four document areas and nothing else.

The shipped approvals are stale between increment B and increment H of the groundwork-module plan,
so the installs here run against a copy of the package in a temporary distribution whose approvals
`release_approvals` records in that copy. The owner's real release is increment H."""

import io
import json
import os
import shutil
import unittest

from tests import test_install
from workbench import firstparty, install, manifest, sources, verify

ROOT = test_install.ROOT
PACKAGE = os.path.join(ROOT, "packages", "workbench")
MODULE = os.path.join(PACKAGE, "groundwork")
AREAS = ("specs", "roadmaps", "decisions", "references")
READMES = ["docs/%s/README.md" % area for area in AREAS]


def declaration():
    with open(os.path.join(MODULE, "module.json"), encoding="utf-8") as handle:
        return json.load(handle)


class Declaration(unittest.TestCase):
    def test_it_verifies_as_a_first_party_module(self):
        result = verify.verify_package(PACKAGE, first_party=True, select=["groundwork"],
                                       harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertIn("groundwork", [m.name for m in result.modules])

    def test_it_provides_the_four_capabilities_and_nothing_else_is_declared(self):
        document = declaration()
        self.assertEqual("module", document["type"])
        self.assertEqual(list(AREAS), document["provides"])
        self.assertEqual(sorted(READMES), document["writes"])
        for field in ("ships", "helpers", "requires", "blocks", "slots", "layout"):
            self.assertNotIn(field, document)

    def test_it_ships_no_code_and_every_file_is_a_readme_or_the_declaration(self):
        found = []
        for base, dirs, files in os.walk(MODULE):
            for name in files:
                found.append(os.path.relpath(os.path.join(base, name), MODULE))
                self.assertEqual(0, os.stat(os.path.join(base, name)).st_mode & 0o111, name)
        self.assertEqual(sorted(["module.json"] + ["files/" + rel for rel in READMES]),
                         sorted(found))

    def test_the_package_lists_it(self):
        with open(os.path.join(PACKAGE, "package.json"), encoding="utf-8") as handle:
            self.assertEqual(["claude", "groundwork"], json.load(handle)["modules"])

    def test_each_readme_says_what_the_area_is_for_how_it_is_named_and_its_status_values(self):
        words = {"specs": ("kebab-case", "Draft", "Current", "Superseded"),
                 "roadmaps": ("kebab-case", "<roadmap>#<id>"),
                 "decisions": ("YYYY-MM-DD-<topic>.md", "Proposed", "Accepted", "Rejected",
                               "Superseded", "owner"),
                 "references": ("index.json", "2 MB", "50 MB", ".workbench/local/refs/")}
        for area, expected in words.items():
            with open(os.path.join(MODULE, "files", "docs", area, "README.md"), encoding="utf-8") as h:
                text = h.read()
            self.assertTrue(text.startswith("# "), area)
            for word in expected:
                self.assertIn(word, text, (area, word))

    def test_no_readme_holds_a_template(self):
        for area in AREAS:
            with open(os.path.join(MODULE, "files", "docs", area, "README.md"), encoding="utf-8") as h:
                text = h.read()
            self.assertNotIn("<!--", text)
            self.assertNotIn("TODO", text)


class Install(test_install.InstallBase):
    """Install into an empty directory with the Claude module, as a released copy of the package."""

    def setUp(self):
        test_install.InstallBase.setUp(self)
        self.dist = os.path.join(self.root, "dist")
        shutil.copytree(os.path.join(ROOT, "packages"), os.path.join(self.dist, "packages"))
        shutil.copytree(os.path.join(ROOT, "base"), os.path.join(self.dist, "base"))
        os.makedirs(os.path.join(self.dist, "workbench"))
        done = firstparty.release_approvals(self.dist)
        self.assertEqual(1, done.packages)
        self.package_path = os.path.join(self.dist, "packages", "workbench")
        self.assertTrue(firstparty.is_first_party(self.package_path, self.dist))
        self.home = os.path.join(self.root, "home")
        os.mkdir(self.home)

    def install(self, place, select=("claude", "groundwork")):
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(place, [(self.package_path, None)], list(select))
        code = install.run(self.guarded, command, test_install.Typist(out, test_install.correct),
                           out, err, distribution=self.dist, seed=test_install.SEED,
                           home=self.home)
        return code, out.getvalue(), err.getvalue()

    def test_an_install_creates_the_four_readmes_and_no_other_file_in_the_areas(self):
        place = self.place()
        code, out, err = self.install(place)
        self.assertEqual(0, code, (out, err))
        for area in AREAS:
            folder = os.path.join(place, "docs", area)
            self.assertEqual(["README.md"], os.listdir(folder), area)
            with open(os.path.join(MODULE, "files", "docs", area, "README.md"), "rb") as handle:
                self.assertEqual(handle.read(), self.read(folder, "README.md"))
        self.assertEqual(sorted(["README.md"] + list(AREAS)), sorted(os.listdir(
            os.path.join(place, "docs"))))

    def test_no_placeholder_document_plan_or_researcher_is_created(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        found = []
        for base, dirs, files in os.walk(place):
            dirs[:] = [d for d in dirs if d not in (".git", ".workbench", ".claude")]
            found += [os.path.relpath(os.path.join(base, n), place) for n in files]
        self.assertEqual(sorted(READMES + ["AGENTS.md", "CLAUDE.md", "docs/README.md"]),
                         sorted(found))
        self.assertFalse(os.path.exists(os.path.join(place, "docs", "plans")))
        self.assertFalse(os.path.exists(os.path.join(place, ".claude", "agents")))

    def test_the_manifest_records_the_module_and_the_readmes_as_the_projects_own(self):
        place = self.place()
        self.assertEqual(0, self.install(place)[0])
        document = manifest.parse(self.read(place, ".workbench", "manifest.json"))
        names = {(p["name"], m["name"]) for p in document["packages"] for m in p["modules"]}
        self.assertEqual({("workbench", "groundwork")}, names)  # the harness is never committed
        classes = {f["path"]: f["class"] for f in document["files"]}
        for rel in READMES:
            self.assertEqual("seeded", classes[rel], rel)


if __name__ == "__main__":
    unittest.main()

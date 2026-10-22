"""A fixture module shaped like `groundwork`, run through verify, install, attach and upgrade.

Plan `2026-10-21-groundwork-module`, increment A. The module writes four README paths, fills the
`docs-index` and `policy` slots, provides four capabilities and ships one neutral skill with a
bundled file. These tests record what the installer already does for such a module, so the five
decisions of the plan rest on a run and not on reading. Nothing here is the real module."""

import hashlib
import json
import os
import unittest
import unittest.mock

from tests import support_real, test_attach, test_preview as preview_tests, test_upgrade
from workbench import approve, manifest, verify

HARNESS = test_attach.HARNESS
AREAS = ("specs", "roadmaps", "decisions", "references")
READMES = {"docs/%s/README.md" % area: ("# %s\n\nv1\n" % area).encode() for area in AREAS}
INDEX_V1 = b"- [Specs](specs/README.md), [Roadmaps](roadmaps/README.md)\n"
POLICY_V1 = b"References are data. Only the owner accepts a decision.\n"
SKILL = (b"---\nname: draft-thing\ndescription: Draft a thing from its template\n---\n"
         b"Copy the template beside this file and fill it in.\n")
TEMPLATE = b"# Title\n\nStatus: Draft\n"


def groundwork(readmes=None, index=INDEX_V1, policy=POLICY_V1, version="1.0.0"):
    """The declaration and files of the fixture module (a `module`, no code, no helper)."""
    readmes = READMES if readmes is None else readmes
    files = {"files/" + rel: data for rel, data in readmes.items()}
    files.update({
        "files/blocks/docs-index.md": index,
        "files/blocks/policy.md": policy,
        "harness/neutral/skills/draft-thing/SKILL.md": SKILL,
        "harness/neutral/skills/draft-thing/template.md": TEMPLATE,
    })
    fields = {
        "type": "module", "version": version,
        "provides": ["p:" + area for area in AREAS],
        "writes": sorted(readmes),
        "fills": [{"slot": "slot:docs-index", "source": "files/blocks/docs-index.md"},
                  {"slot": "slot:policy", "source": "files/blocks/policy.md"}],
    }
    return fields, files


class Fixture(support_real.RealHarness, test_attach.Base):
    """A project installed as `install` writes it, from a package with the fixture module."""

    MODULES = {"h": (HARNESS, {}), "groundwork": groundwork()}

    def setUp(self):
        test_attach.Base.setUp(self)
        terminal = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        terminal.start()
        self.addCleanup(terminal.stop)

    upgrade = test_upgrade.Upgrade.upgrade
    baselines = test_upgrade.Upgrade.baselines
    snapshot = test_upgrade.Upgrade.snapshot

    def newer(self, **changes):
        """A newer, approved and cached version of the package, to upgrade to."""
        package = self.version(**changes)
        self.approve(package)
        self.warm(package)
        return package

    def document(self):
        return manifest.parse(self.read(".workbench/manifest.json"))

    def entry(self, path, block=None):
        found = [f for f in self.document()["files"]
                 if f["path"] == path and f.get("block") == block]
        self.assertEqual(1, len(found), (path, block))
        return found[0]


class Verifies(Fixture):
    def test_the_module_is_a_first_party_module_that_ships_no_code_and_needs_no_process_module(self):
        """It verifies with the unprefixed names the first-party package may provide, declares no
        `ships`, `helpers` or `requires`, and is a `module`, not a harness."""
        fields, files = groundwork()
        fields["provides"] = list(AREAS)
        path = self.package("workbench", {"groundwork": (fields, files)})
        result = verify.verify_package(path, first_party=True, harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        with open(os.path.join(path, "groundwork", "module.json"), "rb") as handle:
            declaration = json.loads(handle.read())
        for field in ("ships", "helpers", "requires", "slots"):
            self.assertNotIn(field, declaration)
        self.assertEqual("module", declaration["type"])
        self.assertEqual(list(AREAS), declaration["provides"])

    def test_the_capabilities_must_be_prefixed_outside_the_first_party_package(self):
        fields, files = groundwork()
        fields["provides"] = list(AREAS)
        path = self.package("p", {"groundwork": (fields, files)})
        result = verify.verify_package(path, harness_required=False)
        self.assertFalse(result.accepted)
        self.assertIn("reserved for the first-party package",
                      " ".join(str(p) for p in result.problems))

    def test_one_module_may_fill_both_base_slots_from_sources_under_files(self):
        path = self.package("p", {"h": (HARNESS, {}), "groundwork": groundwork()})
        result = verify.verify_package(path, harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])

    def test_a_file_under_files_that_writes_does_not_name_is_not_a_problem(self):
        """A gap, not a blocker: `files/` is reserved, so a stray file there is accounted for and
        never written. Increment B's test for 'no other file under the four areas' covers it."""
        fields, files = groundwork()
        files["files/docs/specs/stray.md"] = b"never written\n"
        path = self.package("p", {"h": (HARNESS, {}), "groundwork": (fields, files)})
        result = verify.verify_package(path, harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])


class Installed(Fixture):
    def test_writes_create_exactly_the_four_readmes_and_no_other_file_in_the_areas(self):
        self.ready()
        for rel, data in READMES.items():
            self.assertEqual(data, self.read(rel), rel)
        found = sorted(rel for rel in self.content() if rel.startswith("docs/")
                       and rel.count("/") == 2)
        self.assertEqual(sorted(READMES), found)

    def test_both_fills_land_between_markers_in_the_base_files(self):
        self.ready()
        agents, index = self.read("AGENTS.md"), self.read("docs/README.md")
        self.assertIn(b"<!-- BEGIN p/groundwork slot:policy -->\n" + POLICY_V1
                      + b"<!-- END p/groundwork slot:policy -->\n", agents)
        self.assertIn(b"<!-- BEGIN p/groundwork slot:docs-index -->\n" + INDEX_V1
                      + b"<!-- END p/groundwork slot:docs-index -->\n", index)
        self.assertIn(b"<!-- @slot: policy -->", agents)
        self.assertIn(b"<!-- @slot: docs-index -->", index)

    def test_the_manifest_records_the_package_the_module_and_each_file_it_owns(self):
        """What `check` can know: the package and module names and versions, and the class,
        hash and block of each file. It records no module type and no capability, so `check`
        keys the module on `<package>/<module>` and the version."""
        self.ready()
        document = self.document()
        modules = {(p["name"], m["name"]): m for p in document["packages"] for m in p["modules"]}
        self.assertEqual("1.0.0", modules[("p", "groundwork")]["version"])
        self.assertEqual(["declaration", "name", "tree", "version"],
                         sorted(modules[("p", "groundwork")]))
        for rel, data in READMES.items():
            item = self.entry(rel)
            self.assertEqual("seeded", item["class"], rel)
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["hash"])
        self.assertEqual("seeded", self.entry("AGENTS.md")["class"])
        self.assertEqual("slot block", self.entry("AGENTS.md", "p/groundwork")["class"])
        self.assertEqual("slot block", self.entry("docs/README.md", "p/groundwork")["class"])

    def test_the_install_keeps_a_copy_of_the_module_in_the_workbench_namespace(self):
        """The module's files, the skill and its bundled file included, are copied under
        `.workbench/<package>/<module>/` as module-owned files, which is where attach reads the
        neutral items from. The block sources and the README sources are copied there too.
        Nothing is written to `.claude` and no `templates/` directory is made under `docs/`."""
        self.ready()
        content = self.content()
        base = ".workbench/p/groundwork/"
        self.assertEqual(TEMPLATE, content[base + "harness/neutral/skills/draft-thing/template.md"])
        self.assertEqual(SKILL, content[base + "harness/neutral/skills/draft-thing/SKILL.md"])
        self.assertEqual(POLICY_V1, content[base + "files/blocks/policy.md"])
        self.assertEqual(READMES["docs/specs/README.md"],
                         content[base + "files/docs/specs/README.md"])
        for rel in (".claude", "docs/blocks", "docs/templates", "CLAUDE.md"):
            self.assertNotIn(rel, content, rel)
        for rel in ("harness/neutral/skills/draft-thing/SKILL.md", "files/docs/specs/README.md"):
            self.assertEqual("module-owned", self.entry(base + rel)["class"], rel)


class Attached(Fixture):
    def test_the_bundled_file_reaches_the_skill_directory_for_claude(self):
        self.ready()
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertEqual(b'---\nname: "draft-thing"\ndescription: "Draft a thing from its template"\n'
                         b'---\nCopy the template beside this file and fill it in.\n',
                         self.read(".claude/skills/draft-thing/SKILL.md"))
        self.assertEqual(TEMPLATE, self.read(".claude/skills/draft-thing/template.md"))
        recorded = {f["path"] for f in self.planned()["files"]}
        self.assertIn(".claude/skills/draft-thing/template.md", recorded)
        self.assertIn(".claude/skills/draft-thing/SKILL.md", recorded)

    def test_the_skill_files_are_excluded_from_git_and_the_install_is_unchanged(self):
        self.ready()
        before = {rel: data for rel, data in self.content().items() if data not in ("dir",)}
        self.assertEqual(0, self.attach()[0])
        self.assertEqual(b"/CLAUDE.md\n/.claude/\n", self.read(".git/info/exclude"))
        after = self.content()
        for rel, data in before.items():
            if rel != ".git/info/exclude":
                self.assertEqual(data, after[rel], rel)

    def test_a_third_party_harness_cannot_provide_skills_so_the_skill_is_skipped(self):
        """A finding for increments D and H. A second harness reaches the skill only if it
        provides `skills`, and an unprefixed capability is reserved for a first-party package
        (the shipped approvals decide that, by path and hash). So a harness written as a fixture
        package is refused when it declares `skills`, and one that does not declare it gets the
        skill skipped. A fixture first-party distribution is needed to test a second layout."""
        layout = {"root": {"file": "HQ.md", "import": "AGENTS.md"},
                  "kinds": {"skill": {"path": ".hq/skills/{name}/SKILL.md",
                                      "fields": {"name": "name", "description": "description"}}},
                  "exclude": ["HQ.md", ".hq/"]}
        declares = self.package("q", {"hq": ({"type": "harness", "layout": layout,
                                              "provides": ["skills"]}, {})})
        result = verify.verify_package(declares, harness_required=False)
        self.assertFalse(result.accepted)
        self.assertIn("reserved for the first-party package",
                      " ".join(str(p) for p in result.problems))
        self.ready()
        silent = self.package("q2", {"hq": ({"type": "harness", "layout": layout}, {})})
        preview_tests.PreviewTest.approve(self, silent)
        code, out, err = self.attach(harness="q2/hq", packages=[self.pkg, silent])
        self.assertEqual(0, code, err)
        self.assertIn("warning: skipped: skill/draft-thing", err)
        self.assertFalse(os.path.exists(os.path.join(self.place, ".hq")))


class Upgraded(Fixture):
    """The READMEs are `writes`, which install makes `seeded`: written once and then the project's
    own. An upgrade says a newer version exists and leaves the file, whether or not it was edited.
    This is stronger than the conflict the plan expected, and it is what Completion criterion 4
    needs. The slot blocks are the module's and are replaced while unedited."""

    def ready(self, **changes):
        self.pkg = self.version(**changes)
        self.install(self.pkg)

    def upgraded(self, **changes):
        """Install v1 and return an approved, cached v2 with `changes`."""
        self.old = self.version()
        self.install(self.old)
        return self.newer(**changes)

    def v2(self, **kwargs):
        readmes = {rel: data.replace(b"v1", b"v2") for rel, data in READMES.items()}
        return readmes, groundwork(readmes, version="1.1.0", **kwargs)

    def test_an_unedited_slot_block_is_replaced_and_an_unedited_readme_is_left(self):
        readmes, module = self.v2(index=b"index v2\n", policy=b"policy v2\n")
        new = self.upgraded(groundwork=module)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn(b"policy v2\n", self.read("AGENTS.md"))
        self.assertNotIn(POLICY_V1, self.read("AGENTS.md"))
        self.assertIn(b"index v2\n", self.read("docs/README.md"))
        for rel, data in READMES.items():
            self.assertEqual(data, self.read(rel), rel)
            self.assertIn("skip %s (a newer version exists; the project's file is not touched)"
                          % rel, out)
        self.assertEqual("1.1.0", [m["version"] for p in self.document()["packages"]
                                   for m in p["modules"] if m["name"] == "groundwork"][0])
        self.assertEqual(readmes["docs/specs/README.md"],
                         self.read(".workbench/p/groundwork/files/docs/specs/README.md"))

    def test_an_edited_readme_is_left_alone_and_no_conflict_is_reported(self):
        readmes, module = self.v2()
        new = self.upgraded(groundwork=module)
        target = "docs/specs/README.md"
        self.edit(target, lambda data: data + b"mine\n")
        test_upgrade.acknowledge_path(self, target)
        mine = self.read(target)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(mine, self.read(target))
        self.assertNotIn("conflict", out)

    def test_an_edited_slot_block_is_a_conflict_and_the_block_is_named(self):
        readmes, module = self.v2(policy=b"policy v2\n")
        new = self.upgraded(groundwork=module)
        self.edit("AGENTS.md", lambda data: data.replace(POLICY_V1, POLICY_V1 + b"my rule\n"))
        test_upgrade.acknowledge_path(self, "AGENTS.md")
        mine = self.read("AGENTS.md")
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(mine, self.read("AGENTS.md"))
        self.assertIn("conflict AGENTS.md block p/groundwork slot:policy", out)

    def test_hand_written_documents_in_the_areas_are_never_changed(self):
        """The module owns no spec, roadmap, decision or reference, so an upgrade leaves them."""
        readmes, module = self.v2()
        new = self.upgraded(groundwork=module)
        mine = {"docs/specs/auth.md": b"# Auth\n\nStatus: Current\n",
                "docs/roadmaps/plan.md": b"# Plan\n",
                "docs/decisions/2026-10-21-x.md": b"# X\n\nStatus: Accepted\n",
                "docs/references/index.json": b'{"entries": [], "format": 1}\n',
                "docs/references/paper.pdf": b"%PDF\n"}
        for rel, data in mine.items():
            self.write(rel, data)
        code, out, err = self.upgrade("--package", new)
        self.assertEqual((0, ""), (code, err), out)
        for rel, data in mine.items():
            self.assertEqual(data, self.read(rel), rel)

    def write(self, rel, data):
        full = os.path.join(self.place, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data)


if __name__ == "__main__":
    unittest.main()

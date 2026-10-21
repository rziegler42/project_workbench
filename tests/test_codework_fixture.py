"""A fixture module shaped like `code-work`, run through verify, install, pin, launch and upgrade.

Plan `2026-10-21-code-work-plans`, increment A. The module is a `process` module that provides
`plans`, requires the three groundwork capabilities, writes one README, fills the `docs-index` and
`policy` slots and ships one helper file. These tests record what the installer already does for
such a module, so the five decisions of the plan rest on a run and not on reading. Nothing here is
the real module."""

import hashlib
import io
import os
import tempfile
import unittest
import unittest.mock

from tests import test_attach, test_groundwork_fixture as groundwork_fixture, test_upgrade
from workbench import approve, cli, declarations, launch, manifest, pins, request, verify

HARNESS = test_attach.HARNESS
README = b"# Plans\n\nv1\n"
INDEX_V1 = b"- [Plans](plans/README.md)\n"
POLICY_V1 = b"A plan needs the owner's explicit approval.\n"
HELPER_V1 = b"#!/bin/sh\necho helper-v1 \"$@\"\n"
HELPER_PATH = "helper/codework"
NEEDS = ["p:specs", "p:roadmaps", "p:decisions"]


def codework(helper=HELPER_V1, readme=README, index=INDEX_V1, policy=POLICY_V1, version="1.0.0",
             kind="process", provides=("p:plans",)):
    """The declaration and files of the fixture module."""
    files = {"files/docs/plans/README.md": readme, "files/blocks/docs-index.md": index,
             "files/blocks/policy.md": policy, HELPER_PATH: helper}
    fields = {
        "type": kind, "version": version, "provides": list(provides), "requires": list(NEEDS),
        "writes": ["docs/plans/README.md"], "ships": [HELPER_PATH],
        "fills": [{"slot": "slot:docs-index", "source": "files/blocks/docs-index.md"},
                  {"slot": "slot:policy", "source": "files/blocks/policy.md"}],
    }
    return fields, files


class Fixture(test_attach.Base):
    """A project installed as `install` writes it, from a package with the fixture modules."""

    MODULES = {"h": (HARNESS, {}), "groundwork": groundwork_fixture.groundwork(),
               "codework": codework()}

    def setUp(self):
        test_attach.Base.setUp(self)
        terminal = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        terminal.start()
        self.addCleanup(terminal.stop)

    upgrade = test_upgrade.Upgrade.upgrade
    baselines = test_upgrade.Upgrade.baselines
    snapshot = test_upgrade.Upgrade.snapshot

    def newer(self, **changes):
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

    def shipped(self):
        return ".workbench/p/codework/" + HELPER_PATH

    def pinned(self, data=None):
        """Pin the installed helper the way `wb pin` would: its path and the hash of its bytes."""
        data = self.read(self.shipped()) if data is None else data
        pins.set_pin(self.guarded, self.project_id, "code-work", self.shipped(),
                     pins.hash_bytes(data), "owner")

    def launched(self, *args):
        """Run the pinned helper as `launch` does: its exit code and the refusal text, if any."""
        with tempfile.TemporaryFile() as out:
            err = io.StringIO()
            try:
                code = launch.launch(self.guarded, self.project_id, "code-work", self.place,
                                     list(args), stdout=out)
            except launch.LaunchError as exc:
                err.write("refused: %s\n" % exc)
                code = 1
            return code, err.getvalue()


class Verifies(Fixture):
    def test_a_process_module_that_ships_a_helper_verifies_as_first_party(self):
        fields, files = codework()
        fields["provides"] = ["plans"]
        fields["requires"] = ["specs", "roadmaps", "decisions"]
        gw_fields, gw_files = groundwork_fixture.groundwork()
        gw_fields["provides"] = list(groundwork_fixture.AREAS)
        path = self.package("workbench", {"groundwork": (gw_fields, gw_files),
                                          "code-work": (fields, files)})
        result = verify.verify_package(path, first_party=True, harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        self.assertEqual(["code-work", "groundwork"], sorted(m.name for m in result.modules))

    def test_the_approval_request_lists_the_shipped_helper_as_code(self):
        path = self.version()
        hashes = [m for m in verify.verify_package(path, harness_required=False).modules
                  if m.name == "codework"][0]
        module = [m for m in declarations.load_package(path).modules if m.name == "codework"][0]
        text = request.render_module("p", module, hashes)
        self.assertIn(HELPER_PATH, text)
        self.assertIn("ships", text.lower())


class Installed(Fixture):
    def test_the_shipped_file_lands_in_the_module_namespace_as_a_module_owned_file(self):
        self.ready()
        self.assertEqual(HELPER_V1, self.read(self.shipped()))
        item = self.entry(self.shipped())
        self.assertEqual("module-owned", item["class"])
        self.assertEqual(hashlib.sha256(HELPER_V1).hexdigest(), item["hash"])

    def test_the_shipped_file_is_not_executable_and_the_launcher_does_not_need_it_to_be(self):
        """The file is written without an executable bit, because the launcher runs a private
        copy it makes executable itself."""
        self.ready()
        full = os.path.join(self.place, *self.shipped().split("/"))
        self.assertEqual(0, os.stat(full).st_mode & 0o111)

    def test_a_baseline_is_recorded_for_the_shipped_file(self):
        self.ready()
        self.assertEqual(hashlib.sha256(HELPER_V1).hexdigest(), self.baselines()[self.shipped()])

    def test_nothing_is_pinned_by_the_install(self):
        """A gap for increment F: `install` records no pin, so `wb code-work` would have none."""
        self.ready()
        self.assertEqual({}, pins.load(self.guarded, self.project_id))

    def test_the_policy_and_index_blocks_and_the_readme_are_written(self):
        self.ready()
        self.assertIn(b"<!-- BEGIN p/codework slot:policy -->\n" + POLICY_V1
                      + b"<!-- END p/codework slot:policy -->\n", self.read("AGENTS.md"))
        self.assertIn(b"<!-- BEGIN p/codework slot:docs-index -->\n" + INDEX_V1
                      + b"<!-- END p/codework slot:docs-index -->\n", self.read("docs/README.md"))
        self.assertEqual(README, self.read("docs/plans/README.md"))
        self.assertEqual("seeded", self.entry("docs/plans/README.md")["class"])
        found = sorted(rel for rel in self.content() if rel.startswith("docs/plans/"))
        self.assertEqual(["docs/plans/README.md"], found)

    def test_the_manifest_records_the_module_by_package_name_and_version_only(self):
        self.ready()
        modules = {(p["name"], m["name"]): m for p in self.document()["packages"]
                   for m in p["modules"]}
        self.assertEqual(["declaration", "name", "tree", "version"],
                         sorted(modules[("p", "codework")]))


class Refused(Fixture):
    def refused(self, package, contains):
        out, err = io.StringIO(), io.StringIO()
        before = self.content()
        code = cli.main(["preview", "install", self.place, "--package", package, "--select"]
                       + sorted(self.MODULES), out, err,
                        store_root=self.store_root, home=self.home)
        self.assertEqual(1, code, out.getvalue() + err.getvalue())
        self.assertIn(contains, err.getvalue())
        self.assertEqual(before, self.content())

    def test_without_a_provider_of_the_required_capabilities_the_install_stops(self):
        self.MODULES = {"h": (HARNESS, {}), "codework": codework()}
        package = self.version()
        self.approve(package)
        self.refused(package, "p:specs")

    def test_a_second_process_module_is_refused(self):
        other = codework(provides=("p:other",))
        other[0]["ships"] = []
        del other[1][HELPER_PATH]
        self.MODULES = dict(self.MODULES, second=other)
        package = self.version()
        self.approve(package)
        self.refused(package, "process")


class PinnedAndLaunched(Fixture):
    def test_the_launcher_runs_the_installed_file_once_it_is_pinned(self):
        self.ready()
        self.pinned()
        code, err = self.launched("check")
        self.assertEqual((0, ""), (code, err))

    def test_with_no_pin_the_launcher_refuses_and_runs_nothing(self):
        self.ready()
        code, err = self.launched("check")
        self.assertEqual(1, code)
        self.assertTrue(err.startswith("refused: "), err)

    def test_an_edited_helper_is_not_run_and_the_upgrade_refuses_until_it_is_acknowledged(self):
        self.ready()
        self.pinned()
        self.edit(self.shipped(), lambda data: data + b"echo evil\n")
        code, err = self.launched("check")
        self.assertEqual(1, code)
        self.assertIn("refused: ", err)
        newer = self.newer(codework=codework(version="1.1.0"))
        code, out, err = self.upgrade("--package", newer)
        self.assertEqual(1, code)
        self.assertIn(self.shipped(), err)


class Upgraded(Fixture):
    def test_an_unedited_helper_is_replaced_and_the_old_pin_then_refuses(self):
        """A gap for increment F: an upgrade writes the new helper but moves no pin, so the helper
        is not run until it is pinned again."""
        self.ready()
        self.pinned()
        newer = self.newer(codework=codework(helper=b"#!/bin/sh\necho helper-v2\n", version="1.1.0"))
        code, out, err = self.upgrade("--package", newer)
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn(b"helper-v2", self.read(self.shipped()))
        code, err = self.launched("check")
        self.assertEqual(1, code)
        self.assertIn("refused: ", err)

    def test_existing_plans_are_never_changed(self):
        self.ready()
        mine = {"docs/plans/2026-10-21-x.md": b"# X\n\nStatus: Approved\n"}
        for rel, data in mine.items():
            full = os.path.join(self.place, *rel.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as handle:
                handle.write(data)
        newer = self.newer(codework=codework(readme=b"# Plans\n\nv2\n", version="1.1.0"))
        code, out, err = self.upgrade("--package", newer)
        self.assertEqual((0, ""), (code, err), out)
        for rel, data in mine.items():
            self.assertEqual(data, self.read(rel), rel)


if __name__ == "__main__":
    unittest.main()

import hashlib
import io
import os
import unittest
import unittest.mock

from tests import test_preview as base_tests
from workbench import (acknowledgement, base, cli, fetch, installplan, manifest, preview, snapshot,
                       target, upgrade, verify)

HARNESS = base_tests.HARNESS
NOTES = base_tests.NOTES
NOTES2 = ({"writes": ["docs/notes.md"], "ships": ["scripts/run.sh"]},
          {"files/docs/notes.md": b"# Notes v2\n", "scripts/run.sh": b"#!/bin/sh\necho 2\n"})
FILL = lambda text: ({"fills": [{"slot": "slot:policy", "source": "policy.md"}]},
                     {"policy.md": text})
SCRIPT = ".workbench/p/notes/scripts/run.sh"
URL = "https://example.test/p.git"


class UpgradePreview(unittest.TestCase):
    """An installed project (written the way `install` writes it) and `wb preview upgrade`."""

    package = base_tests.PreviewTest.package
    approve = base_tests.PreviewTest.approve
    warm = base_tests.PreviewTest.warm
    tree = base_tests.PreviewTest.tree
    cache_copy = base_tests.PreviewTest.cache_copy
    MODULES = {"h": (HARNESS, {}), "notes": NOTES, "a": FILL(b"Rule A\n")}

    def setUp(self):
        base_tests.PreviewTest.setUp(self)
        self.place = os.path.join(self.root, "proj")

    def version(self, **changes):
        modules = dict(self.MODULES)
        modules.update(changes)
        return self.package("p", modules)

    def install(self, path, source="local:p", ref="", commit="", store_writes=True):
        """Write the project as install would, from the package at `path`."""
        self.approve(path)
        os.makedirs(os.path.join(self.place, ".git"))
        with open(os.path.join(self.place, ".git", "index"), "wb") as handle:
            handle.write(b"index")
        result = verify.verify_package(path, select=list(self.MODULES), harness_required=True,
                                       which=lambda name: "/bin/" + name)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        by_key = {(m.package, m.name): m for m in result.modules}
        modules = tuple(by_key[key] for key in result.order)
        snaps = {(m.package, m.name): snapshot.take(os.path.join(path, m.name), m)
                 for m in modules}
        packages = tuple(installplan.PackageSource(i.name, source, ref, commit, i.tree_hash)
                         for i in result.packages)
        with target.open_target(self.place, self.store_root) as held:
            plan = installplan.build(held, installplan.Selection(modules, packages), snaps,
                                     base.load_base(), "seed-1", "0.1.0")
            self.real = held.path
            for action in plan.actions:
                if action.kind == "create-file" and action.path != installplan.MARKER_PATH:
                    full = os.path.join(self.place, *action.path.split("/"))
                    os.makedirs(os.path.dirname(full), exist_ok=True)
                    with open(full, "wb") as handle:
                        handle.write(action.data)
        if store_writes:
            for rel, data in plan.store_writes:
                self.guarded.write(rel, data)
        self.project_id = plan.project_id
        self.warm(path)

    def preview(self, *args, place=None):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "upgrade", place or self.place] + list(args), out, err,
                        store_root=self.store_root)
        return code, out.getvalue(), err.getvalue()

    def refused(self, *args, contains, **kwargs):
        before = (self.tree(self.place), self.tree(self.store_root))
        code, out, err = self.preview(*args, **kwargs)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        for line in err.splitlines():
            self.assertTrue(line.startswith(("refused: ", "  ")), line)
            self.assertFalse(line.startswith("refused:  "), line)
        self.assertIn(contains, err)
        self.assertEqual(before, (self.tree(self.place), self.tree(self.store_root)))
        fetch.fetch.assert_not_called()
        return err

    def read(self, rel):
        with open(os.path.join(self.place, *rel.split("/")), "rb") as handle:
            return handle.read()

    def edit(self, rel, edit):
        data = edit(self.read(rel))
        with open(os.path.join(self.place, *rel.split("/")), "wb") as handle:
            handle.write(data)


class Preview(UpgradePreview):
    def test_a_newer_module_is_previewed_and_nothing_is_written(self):
        self.install(self.version())
        newer = self.version(notes=NOTES2)
        self.approve(newer)
        self.warm(newer)
        before = (self.tree(self.place), self.tree(self.store_root))
        code, out, err = self.preview("--package", newer)
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(out.startswith("target: %s\ncommand: upgrade\nstate: existing\n"
                                       % self.real), out)
        self.assertTrue(out.endswith("preview only: nothing was written\n"))
        self.assertIn("replace %s" % SCRIPT, out)
        self.assertIn("approved by the module record", out)
        self.assertNotIn("nothing to change", out)
        self.assertNotIn("digest:", out)
        self.assertEqual(before, (self.tree(self.place), self.tree(self.store_root)))
        with open(os.path.join(self.place, ".git", "index"), "rb") as handle:
            self.assertEqual(b"index", handle.read())
        fetch.fetch.assert_not_called()

    def test_the_same_modules_have_nothing_to_change(self):
        path = self.version()
        self.install(path)
        code, out, err = self.preview("--package", path)
        self.assertEqual((0, ""), (code, err))
        self.assertIn("nothing to change\npreview only: nothing was written\n", out)

    def test_a_conflict_is_shown_and_is_not_a_refusal(self):
        self.install(self.version())
        newer = self.version(notes=NOTES2)
        self.approve(newer)
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        self.acknowledge(SCRIPT)
        code, out, err = self.preview("--package", newer)
        self.assertEqual((0, ""), (code, err))
        self.assertIn("conflict %s [module-owned] (edited by the project)" % SCRIPT, out)

    def acknowledge(self, rel):
        """Stand in for `wb acknowledge`: make the baseline of `rel` what the file is now."""
        baselines = acknowledgement.read_baselines(self.guarded, self.project_id)
        baselines[rel] = hashlib.sha256(self.read(rel)).hexdigest()
        full = os.path.join(self.store_root, "projects", self.project_id, "baselines")
        with open(full, "wb") as handle:
            handle.write(installplan.json_store({"baselines": baselines, "format": 1}))

    def test_a_module_the_package_no_longer_declares_is_left_in_place(self):
        self.install(self.version())
        fewer = self.package("p", {"h": (HARNESS, {}), "notes": NOTES})
        self.approve(fewer)
        code, out, err = self.preview("--package", fewer)
        self.assertEqual((0, ""), (code, err))
        self.assertIn("skip AGENTS.md block p/a slot:policy [slot block] (left in place)", out)
        self.assertIn("skip .workbench/p/a/module.json [module-owned] (left in place)", out)
        self.assertNotIn("replace .workbench/p/a", out)

    def test_a_cached_download_is_used_without_a_package_argument(self):
        path = self.version()
        self.install(path, source=URL, ref="HEAD", commit="a" * 40)
        newer = self.version(notes=NOTES2)
        self.approve(newer)
        self.cache_copy(newer, URL)
        code, out, err = self.preview()
        self.assertEqual((0, ""), (code, err))
        self.assertIn("replace %s" % SCRIPT, out)
        fetch.fetch.assert_not_called()


class Refusals(UpgradePreview):
    def test_a_target_that_is_not_an_existing_project(self):
        empty = os.path.join(self.root, "empty")
        os.mkdir(empty)
        self.warm(self.version())
        err = self.refused(place=empty, contains="not an existing project")
        self.assertIn("use install", err)

    def test_a_project_this_machine_has_no_baselines_for(self):
        self.install(self.version(), store_writes=False)
        self.refused("--package", self.version(), contains="holds no acknowledgement baselines")

    def test_a_project_first_seen_somewhere_else(self):
        path = self.version()
        self.install(path)
        moved = installplan.json_store({"format": 1, "kind": "path", "value": "/elsewhere"})
        os.unlink(os.path.join(self.store_root, "projects", self.project_id, "seen"))
        self.guarded.write("projects/%s/seen" % self.project_id, moved)
        self.refused("--package", path, contains="first seen at /elsewhere")

    def test_an_edited_file_under_workbench_names_the_path_and_acknowledge(self):
        path = self.version()
        self.install(path)
        self.edit(SCRIPT, lambda data: data + b"# mine\n")
        err = self.refused("--package", path, contains="wb acknowledge")
        self.assertIn("changed %s" % SCRIPT, err)

    def test_a_hand_edited_manifest_is_refused_until_acknowledged(self):
        path = self.version()
        self.install(path)
        document = manifest.parse(self.read(".workbench/manifest.json"))
        document["workbench"] = "0.0.1"
        self.edit(".workbench/manifest.json", lambda data: manifest.serialize(document))
        err = self.refused("--package", path, contains="wb acknowledge")
        self.assertIn("changed .workbench/manifest.json", err)

    def test_a_file_added_under_workbench_is_refused(self):
        path = self.version()
        self.install(path)
        with open(os.path.join(self.place, ".workbench", "extra"), "wb") as handle:
            handle.write(b"x")
        self.refused("--package", path, contains="added .workbench/extra")

    def test_an_edited_file_the_upgrade_would_write_into_is_refused(self):
        self.install(self.version())
        newer = self.version(a=FILL(b"Rule A, changed\n"))
        self.approve(newer)
        self.edit("AGENTS.md", lambda data: data + b"mine\n")
        self.refused("--package", newer, contains="changed AGENTS.md")

    def test_a_local_package_must_be_given(self):
        self.install(self.version())
        self.refused(contains="give it with --package")

    def test_an_uncached_download_is_not_fetched(self):
        self.install(self.version(), source=URL, ref="HEAD", commit="a" * 40)
        self.refused(contains="has not been downloaded")

    def test_a_newer_module_that_is_not_approved(self):
        self.install(self.version())
        newer = self.version(notes=NOTES2)
        self.refused("--package", newer, contains="p/notes is not approved")

    def test_a_package_the_project_does_not_record(self):
        self.install(self.version())
        other = self.package("q", {"h": (HARNESS, {}), "x": NOTES})
        self.refused("--package", other, "--package", self.version(),
                     contains="not one this project records")

    def test_a_package_given_twice(self):
        path = self.version()
        self.install(path)
        self.refused("--package", path, "--package", self.version(),
                     contains="was given twice")

    def test_a_workbench_older_than_the_project(self):
        path = self.version()
        self.install(path)
        with target.open_target(self.place, self.store_root) as held:
            with self.assertRaises(preview.Refused) as caught:
                upgrade.prepare(self.guarded, held, [(path, None)], None, "0.0.1")
        self.assertIn("newer than 0.0.1", str(caught.exception))

    def test_a_file_that_changes_between_the_checks_is_caught_by_its_hash(self):
        path = self.version()
        self.install(path)
        newer = self.version(a=FILL(b"Rule A, changed\n"))
        self.approve(newer)
        self.edit("AGENTS.md", lambda data: data + b"mine\n")
        with unittest.mock.patch.object(acknowledgement, "differences", return_value=[]):
            err = self.refused("--package", newer, contains="AGENTS.md is not as last acknowledged")
        self.assertIn("wb acknowledge", err)

    def test_a_fifo_named_package_json_is_refused_not_opened(self):
        self.install(self.version())
        odd = os.path.join(self.root, "odd")
        os.mkdir(odd)
        os.mkfifo(os.path.join(odd, "package.json"))
        self.refused("--package", odd, contains="is not a regular file")

    def test_a_linked_package_json_is_refused(self):
        self.install(self.version())
        odd = os.path.join(self.root, "odd")
        os.mkdir(odd)
        os.symlink(os.path.join(self.version(), "package.json"), os.path.join(odd, "package.json"))
        self.refused("--package", odd, contains="no readable package.json")

    def test_select_is_a_usage_error_and_touches_nothing(self):
        bare = os.path.join(self.root, "bare")
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "upgrade", self.place, "--select", "h"], out, err,
                        store_root=bare)
        self.assertEqual(2, code)
        self.assertIn("preview upgrade", err.getvalue())
        self.assertFalse(os.path.exists(bare))


if __name__ == "__main__":
    unittest.main()

import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import unittest

import support
from workbench import approvals, cli, declarations, firstparty, hashing, store, verify
from workbench.wbkit import safefs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "sample-package")
NOW = "2026-10-20T08:00:00Z"


def listing(top):
    found = {}
    for base, dirs, files in os.walk(top):
        for name in dirs + files:
            full = os.path.join(base, name)
            info = os.lstat(full)
            digest = ""
            if stat.S_ISREG(info.st_mode):
                with open(full, "rb") as handle:
                    digest = hashlib.sha256(handle.read()).hexdigest()
            found[os.path.relpath(full, top)] = (stat.S_IMODE(info.st_mode), digest, info.st_mtime_ns)
    return found


class Base(unittest.TestCase):
    def setUp(self):
        support.forbid_real_store(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.dist = self.make_dist("dist")
        self.package = os.path.join(self.dist, "packages", "sample")
        self.shipped = os.path.join(self.dist, "workbench", "shipped_approvals")
        self.store = store.Store(os.path.join(self.base, "store"))
        self.store.ensure()

    def make_dist(self, name):
        dist = os.path.join(self.base, name)
        os.makedirs(os.path.join(dist, "workbench"))
        os.makedirs(os.path.join(dist, "packages"))
        target = os.path.join(dist, "packages", "sample")
        shutil.copytree(FIXTURE, target)
        # An unprefixed capability is allowed only for a first-party package.
        path = os.path.join(target, "sample-notes", "module.json")
        with open(path) as handle:
            document = json.load(handle)
        document["provides"] = ["plans"]
        with open(path, "w") as handle:
            json.dump(document, handle)
        return dist

    def release(self, dist=None):
        return firstparty.release_approvals(dist or self.dist)

    def module_hashes(self, name):
        result = verify.verify_package(self.package, first_party=True, harness_required=False)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        return next((m.declaration_hash, m.tree_hash) for m in result.modules if m.name == name)


class ReleaseTest(Base):
    def test_the_same_files_are_refused_as_third_party(self):
        result = verify.verify_package(self.package, first_party=False)
        self.assertFalse(result.accepted)

    def test_release_writes_a_record_per_module_and_per_package(self):
        done = self.release()
        self.assertEqual((done.packages, done.records, done.warnings), (1, 3, []))
        keys = os.listdir(os.path.join(self.shipped, "packages"))
        self.assertEqual(len(keys), 3)
        for key in keys:
            self.assertTrue(os.path.isfile(os.path.join(self.shipped, "packages", key, "approval.json")))

    def test_released_records_are_fixed_by_approver_and_time(self):
        self.release()
        tree = firstparty.shipped_tree(self.dist)
        decl, treeh = self.module_hashes("sample-notes")
        got = approvals.check_module(tree, "sample/sample-notes", decl, treeh)
        self.assertTrue(got.approved, got.reason)
        self.assertEqual((got.record.approver, got.record.time),
                         (firstparty.RELEASE_APPROVER, firstparty.RELEASE_TIME))

    def test_a_second_run_changes_nothing(self):
        self.release()
        before = listing(self.dist)
        done = self.release()
        self.assertEqual((done.records, done.warnings), (3, []))
        self.assertEqual(listing(self.dist), before)

    def test_two_distributions_with_the_same_packages_get_identical_records(self):
        other = self.make_dist("dist2")
        self.release()
        self.release(other)

        def records(dist):
            top = os.path.join(dist, "workbench", "shipped_approvals")
            return {rel: value[1] for rel, value in listing(top).items()}

        self.assertEqual(records(self.dist), records(other))
        self.assertTrue(records(self.dist))

    def test_no_packages_directory_writes_nothing(self):
        shutil.rmtree(os.path.join(self.dist, "packages"))
        done = self.release()
        self.assertEqual((done.packages, done.records, done.warnings), (0, 0, []))
        self.assertFalse(os.path.exists(self.shipped))

    def test_an_empty_packages_directory_writes_nothing(self):
        shutil.rmtree(self.package)
        done = self.release()
        self.assertEqual((done.packages, done.records), (0, 0))
        self.assertFalse(os.path.exists(self.shipped))

    def test_a_failing_module_stops_the_release_and_writes_nothing(self):
        second = os.path.join(self.dist, "packages", "other")
        shutil.copytree(FIXTURE, second)
        with open(os.path.join(second, "package.json"), "w") as handle:
            json.dump({"name": "other", "version": "1.0.0", "contract": 1,
                       "modules": ["sample-harness", "sample-notes"]}, handle)
        for module in ("sample-harness", "sample-notes"):
            path = os.path.join(second, module, "module.json")
            with open(path) as handle:
                text = handle.read().replace("sample:", "other:")
            with open(path, "w") as handle:
                handle.write(text)
        with open(os.path.join(second, "sample-notes", "stray.txt"), "w") as handle:
            handle.write("x")
        with self.assertRaises(firstparty.ReleaseError) as caught:
            self.release()
        self.assertIn("unaccounted-file", str(caught.exception))
        self.assertFalse(os.path.exists(self.shipped))

    def test_a_directory_whose_name_differs_from_the_package_is_refused(self):
        os.rename(self.package, os.path.join(self.dist, "packages", "renamed"))
        with self.assertRaisesRegex(firstparty.ReleaseError, "differ"):
            self.release()
        self.assertFalse(os.path.exists(self.shipped))

    def test_a_stray_file_in_packages_is_refused(self):
        with open(os.path.join(self.dist, "packages", "README"), "w") as handle:
            handle.write("x")
        with self.assertRaisesRegex(firstparty.ReleaseError, "not a package directory"):
            self.release()
        self.assertFalse(os.path.exists(self.shipped))

    def test_a_symbolic_link_as_a_package_is_refused(self):
        os.rename(self.package, os.path.join(self.base, "elsewhere"))
        os.symlink(os.path.join(self.base, "elsewhere"), self.package)
        with self.assertRaises(firstparty.ReleaseError):
            self.release()
        self.assertFalse(os.path.exists(self.shipped))

    def test_records_of_an_earlier_release_are_kept_and_reported(self):
        self.release()
        before = set(os.listdir(os.path.join(self.shipped, "packages")))
        with open(os.path.join(self.package, "sample-notes", "files", "docs", "notes.md"), "a") as handle:
            handle.write("changed\n")
        done = self.release()
        after = set(os.listdir(os.path.join(self.shipped, "packages")))
        self.assertTrue(before < after)
        self.assertEqual(len(done.warnings), 2)
        for warning in done.warnings:
            self.assertIn("remove it by hand", warning)


class IsFirstPartyTest(Base):
    def test_not_first_party_before_a_release(self):
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))

    def test_first_party_after_a_release(self):
        self.release()
        self.assertTrue(firstparty.is_first_party(self.package, self.dist))
        self.assertTrue(firstparty.is_first_party(self.package + "/", self.dist))

    def test_the_same_files_elsewhere_are_not_first_party(self):
        self.release()
        for place in ("copy", os.path.join("dist", "other", "sample"), os.path.join("dist", "sample"),
                      os.path.join("dist", "packages", "sample", "nested")):
            with self.subTest(place=place):
                target = os.path.join(self.base, place)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copytree(self.package, target)
                self.assertFalse(firstparty.is_first_party(target, self.dist))

    def test_a_package_with_a_first_party_name_but_another_directory_is_not(self):
        self.release()
        target = os.path.join(self.dist, "packages", "sample2")
        shutil.copytree(self.package, target)
        self.assertFalse(firstparty.is_first_party(target, self.dist))

    def test_a_symbolic_link_to_a_first_party_package_is_not_first_party(self):
        self.release()
        link = os.path.join(self.base, "link")
        os.symlink(self.package, link)
        self.assertFalse(firstparty.is_first_party(link, self.dist))
        inside = os.path.join(self.dist, "packages", "linked")
        os.symlink(self.package, inside)
        self.assertFalse(firstparty.is_first_party(inside, self.dist))

    def test_bad_paths_are_not_first_party(self):
        self.release()
        for path in (None, "", 5, "bad\0path", os.path.join(self.base, "missing")):
            with self.subTest(path=path):
                self.assertFalse(firstparty.is_first_party(path, self.dist))

    def test_a_damaged_shipped_record_makes_nobody_first_party(self):
        self.release()
        packages = os.path.join(self.shipped, "packages")
        for key in os.listdir(packages):
            with open(os.path.join(packages, key, "approval.json"), "wb") as handle:
                handle.write(b"{ broken")
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))

    def package_record_key(self):
        packages = os.path.join(self.shipped, "packages")
        for key in os.listdir(packages):
            with open(os.path.join(packages, key, "approval.json")) as handle:
                if json.load(handle)["kind"] == "package":
                    return key
        self.fail("no package record was shipped")

    def test_a_package_record_under_the_wrong_key_makes_nobody_first_party(self):
        self.release()
        self.assertTrue(firstparty.is_first_party(self.package, self.dist))
        packages = os.path.join(self.shipped, "packages")
        os.rename(os.path.join(packages, self.package_record_key()),
                  os.path.join(packages, "0" * 64))
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))

    def test_only_the_package_record_counts_not_the_module_records(self):
        self.release()
        packages = os.path.join(self.shipped, "packages")
        shutil.rmtree(os.path.join(packages, self.package_record_key()))
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))

    def test_a_missing_or_linked_shipped_directory_makes_nobody_first_party(self):
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))
        self.release()
        moved = os.path.join(self.base, "moved")
        os.rename(self.shipped, moved)
        os.symlink(moved, self.shipped)
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))

    def test_a_released_package_changed_since_is_no_longer_first_party(self):
        self.release()
        self.assertTrue(firstparty.is_first_party(self.package, self.dist))
        path = os.path.join(self.package, "sample-notes", "files", "docs", "notes.md")
        with open(path, "a") as handle:
            handle.write("changed\n")
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))

    def test_adding_an_unprefixed_capability_after_release_removes_the_right(self):
        self.release()
        path = os.path.join(self.package, "sample-notes", "module.json")
        with open(path) as handle:
            document = json.load(handle)
        document["provides"] = ["plans", "specs"]
        with open(path, "w") as handle:
            json.dump(document, handle)
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))
        self.assertFalse(verify.verify_package(
            self.package, first_party=firstparty.is_first_party(self.package, self.dist)).accepted)

    def test_a_declared_name_that_differs_from_the_directory_is_not_first_party(self):
        self.release()
        path = os.path.join(self.package, "package.json")
        with open(path) as handle:
            document = json.load(handle)
        document["name"] = "evil"
        with open(path, "w") as handle:
            json.dump(document, handle)
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))

    def test_a_trailing_slash_does_not_hide_a_symbolic_link(self):
        self.release()
        link = os.path.join(self.dist, "packages", "linked")
        os.symlink(self.package, link)
        for spelling in (link, link + "/", link + "//"):
            with self.subTest(spelling=spelling):
                self.assertFalse(firstparty.is_first_party(spelling, self.dist))


class CheckTest(Base):
    def setUp(self):
        super().setUp()
        self.release()
        self.decl, self.tree = self.module_hashes("sample-notes")

    def test_a_shipped_record_approves_a_first_party_module(self):
        got = firstparty.check_module(self.store, "sample/sample-notes", self.decl, self.tree,
                                      True, self.dist)
        self.assertTrue(got.check.approved, got.check.reason)
        self.assertEqual(got.source, "shipped")

    def test_the_same_hashes_are_not_approved_for_a_third_party_package(self):
        got = firstparty.check_module(self.store, "sample/sample-notes", self.decl, self.tree,
                                      False, self.dist)
        self.assertFalse(got.check.approved)
        self.assertIsNone(got.source)

    def test_another_subject_is_not_approved_by_a_shipped_record(self):
        got = firstparty.check_module(self.store, "evil/sample-notes", self.decl, self.tree,
                                      True, self.dist)
        self.assertFalse(got.check.approved)
        self.assertIn("shipped:", got.check.reason)

    def test_a_changed_module_has_no_shipped_approval(self):
        path = os.path.join(self.package, "sample-notes", "files", "docs", "notes.md")
        with open(path, "a") as handle:
            handle.write("changed\n")
        decl, tree = self.module_hashes("sample-notes")
        got = firstparty.check_module(self.store, "sample/sample-notes", decl, tree, True, self.dist)
        self.assertFalse(got.check.approved)
        self.assertNotEqual(tree, self.tree)

    def test_a_changed_module_can_still_be_approved_in_the_store(self):
        path = os.path.join(self.package, "sample-notes", "files", "docs", "notes.md")
        with open(path, "a") as handle:
            handle.write("changed\n")
        decl, tree = self.module_hashes("sample-notes")
        approvals.record_module(self.store, "sample/sample-notes", decl, tree, "owner", NOW)
        got = firstparty.check_module(self.store, "sample/sample-notes", decl, tree, True, self.dist)
        self.assertTrue(got.check.approved)
        self.assertEqual(got.source, "store")

    def test_a_store_approval_is_found_for_a_third_party_package(self):
        approvals.record_module(self.store, "other/m", self.decl, self.tree, "owner", NOW)
        got = firstparty.check_module(self.store, "other/m", self.decl, self.tree, False, self.dist)
        self.assertEqual((got.check.approved, got.source), (True, "store"))

    def test_a_package_record_is_shipped_and_checked_by_subject(self):
        with safefs.Root(self.package, "package") as root:
            decl = hashing.declaration_hash(declarations.parse_json(root.read_file("package.json")))
        tree = hashing.tree_hash(self.package, what="package")
        got = firstparty.check_package(self.store, "sample", decl, tree, True, self.dist)
        self.assertEqual((got.check.approved, got.source), (True, "shipped"))
        got = firstparty.check_package(self.store, "other", decl, tree, True, self.dist)
        self.assertFalse(got.check.approved)

    def test_checks_do_not_write_to_the_store_or_the_distribution(self):
        before_store, before_dist = listing(self.store.root), listing(self.dist)
        firstparty.check_module(self.store, "sample/sample-notes", self.decl, self.tree, True, self.dist)
        firstparty.check_module(self.store, "x/y", "0" * 64, "1" * 64, True, self.dist)
        self.assertEqual(listing(self.store.root), before_store)
        self.assertEqual(listing(self.dist), before_dist)

    def test_a_shipped_record_is_never_copied_into_the_store(self):
        firstparty.check_module(self.store, "sample/sample-notes", self.decl, self.tree, True, self.dist)
        self.assertEqual(os.listdir(os.path.join(self.store.root, "packages")), [])


class CliTest(Base):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(list(argv), out, err, store_root=self.store.root, distribution=self.dist)
        return code, out.getvalue(), err.getvalue()

    def test_verify_treats_a_released_package_as_first_party(self):
        code, _, err = self.run_cli("verify", self.package)
        self.assertEqual(code, 1, "unreleased: unprefixed capability is refused")
        self.assertIn("provides", err)
        self.assertEqual(self.run_cli("release-approvals")[0], 0)
        code, out, err = self.run_cli("verify", self.package)
        self.assertEqual((code, err), (0, ""), out)

    def test_the_same_files_outside_the_distribution_are_still_refused(self):
        self.assertEqual(self.run_cli("release-approvals")[0], 0)
        copy = os.path.join(self.base, "copy")
        shutil.copytree(self.package, copy)
        code, _, err = self.run_cli("verify", copy)
        self.assertEqual(code, 1)
        self.assertIn("provides", err)

    def test_release_approvals_reports_and_exits_0(self):
        code, out, err = self.run_cli("release-approvals")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("wrote 3 approvals for 1 first-party packages", out)

    def test_release_approvals_with_no_packages(self):
        shutil.rmtree(self.package)
        code, out, _ = self.run_cli("release-approvals")
        self.assertEqual((code, out), (0, "no first-party packages\n"))

    def test_release_approvals_refusal_exits_1_with_nothing_written(self):
        with open(os.path.join(self.package, "sample-notes", "stray.txt"), "w") as handle:
            handle.write("x")
        code, out, err = self.run_cli("release-approvals")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("refused: nothing was written", err)
        self.assertFalse(os.path.exists(self.shipped))

    def test_verify_refuses_a_released_package_once_it_changes(self):
        self.assertEqual(self.run_cli("release-approvals")[0], 0)
        self.assertEqual(self.run_cli("verify", self.package)[0], 0)
        with open(os.path.join(self.package, "sample-notes", "files", "docs", "notes.md"), "a") as handle:
            handle.write("changed\n")
        code, _, err = self.run_cli("verify", self.package)
        self.assertEqual(code, 1)
        self.assertIn("provides", err)

    def test_release_approvals_takes_no_arguments(self):
        self.assertEqual(self.run_cli("release-approvals", "extra")[0], 2)


if __name__ == "__main__":
    unittest.main()

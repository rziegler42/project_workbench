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


class PreviewTest(Base):
    """``wb preview release-approvals`` and the plan step that the write step takes (Increment B of
    ``2026-10-30-release-approvals-at-ask``)."""

    def preview(self, *extra, dist=None):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "release-approvals"] + list(extra), out, err,
                        store_root=os.path.join(self.base, "store"), distribution=dist or self.dist)
        return code, out.getvalue(), err.getvalue()

    def package_hashes(self):
        return firstparty._package_hashes(self.package, "sample")

    def test_the_preview_names_each_package_and_module_with_its_full_hashes_and_that_it_is_new(self):
        code, out, err = self.preview()
        self.assertEqual((0, ""), (code, err))
        decl, tree = self.package_hashes()
        self.assertIn("package sample declaration %s tree %s record new\n" % (decl, tree), out)
        mdecl, mtree = self.module_hashes("sample-notes")
        self.assertIn("module sample-notes declaration %s tree %s record new\n" % (mdecl, mtree), out)
        self.assertIn("approver: %s\n" % firstparty.RELEASE_APPROVER, out)
        self.assertIn("time: %s\n" % firstparty.RELEASE_TIME, out)
        self.assertIn("packages: 1\nmodules: 2\n", out)
        self.assertIn("not covered: ", out)

    def test_the_preview_says_recorded_for_a_record_that_a_release_wrote(self):
        self.release()
        _, out, _ = self.preview()
        self.assertNotIn("record new", out)
        self.assertEqual(3, out.count("record recorded"))

    def test_the_last_line_is_the_digest_of_the_text_before_it(self):
        _, out, _ = self.preview()
        text, last = out[:out.rindex("digest: ")], out[out.rindex("digest: "):]
        self.assertRegex(last, r"\Adigest: [0-9a-f]{32}\n\Z")
        self.assertEqual("digest: %s\n" % hashlib.sha256(text.encode("utf-8")).hexdigest()[:32], last)
        self.assertEqual(last[len("digest: "):-1], firstparty.digest_of(text))

    def test_the_preview_writes_nothing(self):
        before = listing(self.dist)
        self.preview()
        self.assertEqual(before, listing(self.dist))
        self.assertFalse(os.path.exists(self.shipped))
        self.release()
        before = listing(self.dist)
        self.preview()
        self.assertEqual(before, listing(self.dist))

    def test_the_digest_is_stable_and_changes_with_each_input(self):
        def digest(**given):
            plan = firstparty.plan_release(self.dist, **given)
            return firstparty.digest_of(firstparty.preview_text(plan))

        base = digest()
        self.assertEqual(base, digest())
        self.assertNotEqual(base, digest(approver="someone-else"))
        self.assertNotEqual(base, digest(time="2026-10-30T00:00:00Z"))
        stale = os.path.join(self.shipped, "packages", "0" * 64)
        os.makedirs(stale)
        with_stale = digest()
        self.assertNotEqual(base, with_stale)
        shutil.rmtree(stale)
        self.assertEqual(base, digest())
        # A change of one file of a module changes the tree hash and so the digest.
        with open(os.path.join(self.package, "sample-notes", "files", "docs", "notes.md"), "a") as handle:
            handle.write("changed\n")
        self.assertNotEqual(base, digest())

    def test_the_digest_covers_the_whole_hash_and_not_a_prefix(self):
        plan = firstparty.plan_release(self.dist)
        text = firstparty.preview_text(plan)
        for item in plan.packages:
            self.assertIn(item.declaration_hash, text)
            self.assertIn(item.tree_hash, text)
            for module in item.modules:
                self.assertIn(module.declaration_hash, text)
                self.assertIn(module.tree_hash, text)

    def test_a_refused_package_refuses_the_preview_and_prints_no_digest(self):
        with open(os.path.join(self.dist, "packages", "README"), "w") as handle:
            handle.write("x")
        code, out, err = self.preview()
        self.assertEqual(1, code)
        self.assertIn("not a package directory", err)
        self.assertNotIn("digest:", out)
        self.assertFalse(os.path.exists(self.shipped))

    def test_no_packages_gives_a_preview_of_nothing_with_a_digest(self):
        shutil.rmtree(os.path.join(self.dist, "packages"))
        code, out, _ = self.preview()
        self.assertEqual(0, code)
        self.assertIn("packages: 0\nmodules: 0\n", out)
        self.assertRegex(out, r"digest: [0-9a-f]{32}\n\Z")

    def test_an_argument_is_a_usage_error_and_prints_nothing_on_standard_output(self):
        code, out, err = self.preview("--digest", "0" * 32)
        self.assertEqual((2, ""), (code, out))
        self.assertIn("usage", err)

    def test_the_preview_does_not_create_the_guarded_store(self):
        missing = os.path.join(self.base, "no-store")
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "release-approvals"], out, err, store_root=missing, distribution=self.dist)
        self.assertEqual(0, code)
        self.assertFalse(os.path.lexists(missing))

    def test_a_stale_name_with_a_newline_cannot_forge_a_line_or_a_digest(self):
        # The safe walk of the shipped tree refuses such a name, so it never reaches the text; the preview says the stale
        # records are unreadable instead of printing none (security review of Increments B to D) ...
        forged = "x\ndigest: " + "0" * 32
        os.makedirs(os.path.join(self.shipped, "packages", forged))
        code, out, err = self.preview()
        self.assertEqual(0, code)
        self.assertEqual(1, out.count("digest: "), out)
        self.assertRegex(out, r"digest: [0-9a-f]{32}\n\Z")
        self.assertIn("stale records: unreadable\n", out)
        self.assertNotIn("stale records: 0", out)
        # The release goes on as before and writes the same records; it now says that stale records could not be listed.
        done = self.release()
        self.assertEqual((1, 3), (done.packages, done.records))
        self.assertEqual(1, len(done.warnings))
        self.assertIn("could not be listed", done.warnings[0])
        # ... and if one ever did, the text prints it through ``display.clean``.
        plan = firstparty.ReleasePlan((), "approver\nforged: 1", "time\x1b[2J", (forged,))
        text = firstparty.preview_text(plan)
        self.assertNotIn("\ndigest: ", text)
        self.assertNotIn("\nforged: 1", text)
        self.assertNotIn("\x1b", text)
        # the title, the two counts, the approver, the time, the stale count, the one stale key and the last line
        self.assertEqual(8, len(text.splitlines()))

    def test_a_damaged_record_does_not_refuse_the_preview_or_the_release_and_reads_as_new(self):
        self.release()
        keys = os.listdir(os.path.join(self.shipped, "packages"))
        damaged = os.path.join(self.shipped, "packages", sorted(keys)[0], "approval.json")
        with open(damaged, "w") as handle:
            handle.write("not json")
        code, out, err = self.preview()
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(1, out.count("record new"), out)
        self.assertEqual(2, out.count("record recorded"), out)
        before = len(os.listdir(os.path.join(self.shipped, "packages")))
        try:
            self.release()
        except firstparty.ReleaseError:
            pass  # what the write did with a damaged record before this plan; the plan step must not add a refusal of its own
        self.assertEqual(before, len(os.listdir(os.path.join(self.shipped, "packages"))))

    def test_the_release_is_the_plan_followed_by_the_write_and_a_second_run_changes_nothing(self):
        done = firstparty.write_release(firstparty.plan_release(self.dist), self.dist)
        self.assertEqual((1, 3, []), tuple(done))
        before = listing(self.dist)
        again = self.release()
        self.assertEqual((1, 3, []), tuple(again))
        self.assertEqual(before, listing(self.dist))

    def test_the_write_step_writes_the_plan_it_is_given_and_does_not_read_the_packages_again(self):
        plan = firstparty.plan_release(self.dist)
        decl, tree = self.package_hashes()
        with open(os.path.join(self.package, "sample-notes", "files", "docs", "notes.md"), "a") as handle:
            handle.write("changed after the plan\n")
        firstparty.write_release(plan, self.dist)
        shipped = firstparty.shipped_tree(self.dist)
        self.assertTrue(approvals.check_package(shipped, "sample", decl, tree).approved)
        # The package as it is now was not confirmed, so the records do not make it first-party.
        self.assertFalse(firstparty.is_first_party(self.package, self.dist))

    def test_the_stale_records_of_the_plan_are_those_the_write_reports(self):
        self.release()
        with open(os.path.join(self.package, "sample-notes", "files", "docs", "notes.md"), "a") as handle:
            handle.write("changed\n")
        plan = firstparty.plan_release(self.dist)
        self.assertEqual(2, len(plan.stale))
        self.assertTrue(all(len(key) == 64 for key in plan.stale))
        done = firstparty.write_release(plan, self.dist)
        self.assertEqual(sorted(key[:12] for key in plan.stale),
                         sorted(w.split()[2] for w in done.warnings))


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

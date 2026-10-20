import hashlib
import json
import os
import shutil
import stat
import tempfile
import unittest

import support
from workbench import approvals, firstparty, gate, store, verify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "sample-package")
NOW = "2026-10-20T08:00:00Z"
BOTH = ["sample-harness", "sample-notes"]


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


class Untouchable:
    """A store that fails the test if the gate asks it anything."""

    def kind(self, rel):
        raise AssertionError("the gate looked something up")

    read = kind


class Base(unittest.TestCase):
    def setUp(self):
        support.forbid_real_store(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.store = store.Store(os.path.join(self.base, "store"))
        self.store.ensure()
        self.path = os.path.join(self.base, "third")
        shutil.copytree(FIXTURE, self.path)
        self.rewrite_package(self.path, "third")

    def rewrite_package(self, path, name):
        for rel in ("package.json", "sample-harness/module.json", "sample-notes/module.json"):
            full = os.path.join(path, rel)
            with open(full) as handle:
                text = handle.read()
            text = text.replace('"name": "sample"', '"name": "%s"' % name).replace("sample:", name + ":")
            with open(full, "w") as handle:
                handle.write(text)

    def verified(self, select=BOTH, path=None):
        result = verify.verify_packages([path or self.path], select=select)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        return result

    def approve_modules(self, result, only=None):
        for module in result.modules:
            if only is None or module.name in only:
                approvals.record_module(self.store, "%s/%s" % (module.package, module.name),
                                        module.declaration_hash, module.tree_hash, "owner", NOW)

    def approve_package(self, result, modules=None):
        info = result.packages[0]
        listed = [(m.name, m.declaration_hash, m.tree_hash) for m in result.modules
                  if modules is None or m.name in modules]
        approvals.record_package(self.store, info.name, info.declaration_hash, info.tree_hash,
                                 listed, "owner", NOW)


class SelectionTest(Base):
    def test_every_module_with_its_own_record_is_approved(self):
        result = self.verified()
        self.approve_modules(result)
        got = gate.check_selection(self.store, result)
        self.assertTrue(got.approved, got)
        self.assertEqual([(m.name, m.via, m.source) for m in got.modules],
                         [("sample-harness", "module", "store"), ("sample-notes", "module", "store")])

    def test_modules_are_reported_in_install_order(self):
        result = self.verified(["sample-notes", "sample-harness"])
        self.approve_modules(result)
        got = gate.check_selection(self.store, result)
        self.assertEqual([m.name for m in got.modules], ["sample-harness", "sample-notes"])

    def test_a_package_record_covers_a_plain_module_but_not_the_harness(self):
        result = self.verified()
        self.approve_package(result)
        got = gate.check_selection(self.store, result)
        self.assertFalse(got.approved)
        harness, notes = got.modules
        self.assertFalse(harness.approved)
        self.assertIn("needs an approval of its own", harness.reason)
        self.assertEqual((notes.approved, notes.via), (True, "package"))

    def test_a_package_record_plus_the_harness_record_approves_the_selection(self):
        result = self.verified()
        self.approve_package(result)
        self.approve_modules(result, only=["sample-harness"])
        got = gate.check_selection(self.store, result)
        self.assertTrue(got.approved, got)
        self.assertEqual([m.via for m in got.modules], ["module", "package"])

    def test_a_process_module_also_needs_its_own_record(self):
        result = self.verified()
        process = result.modules[1]._replace(type="process")
        altered = result._replace(modules=(result.modules[0], process))
        self.approve_package(result)
        self.approve_modules(result, only=["sample-harness"])
        got = gate.check_selection(self.store, altered)
        self.assertFalse(got.approved)
        self.assertIn("process module needs an approval of its own", got.modules[1].reason)

    def test_only_the_exact_type_module_may_use_a_package_record(self):
        result = self.verified()
        self.approve_package(result)
        self.approve_modules(result, only=["sample-harness"])
        for odd in (None, "Harness", "harness ", "unknown", "", ["module"], 0, "MODULE", "module "):
            with self.subTest(type=odd):
                altered = result._replace(modules=(
                    result.modules[0], result.modules[1]._replace(type=odd)))
                got = gate.check_selection(self.store, altered)
                self.assertFalse(got.approved)
                self.assertFalse(got.modules[1].approved)
        good = gate.check_selection(self.store, result)
        self.assertTrue(good.approved)

    def test_one_unapproved_module_means_the_selection_is_not_approved(self):
        result = self.verified()
        self.approve_modules(result, only=["sample-harness"])
        got = gate.check_selection(self.store, result)
        self.assertFalse(got.approved)
        self.assertEqual([m.approved for m in got.modules], [True, False])
        self.assertIn("no approval is recorded", got.modules[1].reason)
        self.assertEqual(got.reason, "some modules are not approved")

    def test_an_empty_store_approves_nothing(self):
        got = gate.check_selection(self.store, self.verified())
        self.assertFalse(got.approved)
        self.assertEqual([m.approved for m in got.modules], [False, False])

    def test_a_changed_module_is_not_approved_and_the_others_still_are(self):
        result = self.verified()
        self.approve_modules(result)
        self.approve_package(result)
        with open(os.path.join(self.path, "sample-notes", "files", "docs", "notes.md"), "a") as handle:
            handle.write("changed\n")
        got = gate.check_selection(self.store, self.verified())
        self.assertFalse(got.approved)
        self.assertEqual([m.approved for m in got.modules], [True, False])

    def test_a_changed_declaration_is_not_approved(self):
        result = self.verified()
        self.approve_modules(result)
        path = os.path.join(self.path, "sample-notes", "module.json")
        with open(path) as handle:
            document = json.load(handle)
        document["description"] = "A different description."
        with open(path, "w") as handle:
            json.dump(document, handle)
        got = gate.check_selection(self.store, self.verified())
        self.assertEqual([m.approved for m in got.modules], [True, False])

    def test_a_package_record_that_lists_other_hashes_for_the_module_does_not_cover_it(self):
        result = self.verified()
        info = result.packages[0]
        wrong = [("sample-notes", "a" * 64, "b" * 64)]
        approvals.record_package(self.store, info.name, info.declaration_hash, info.tree_hash,
                                 wrong, "owner", NOW)
        self.approve_modules(result, only=["sample-harness"])
        got = gate.check_selection(self.store, result)
        self.assertFalse(got.approved)
        self.assertIn("does not list this module with these hashes", got.modules[1].reason)

    def test_a_package_record_with_no_modules_covers_nothing(self):
        result = self.verified()
        self.approve_package(result, modules=[])
        self.approve_modules(result, only=["sample-harness"])
        got = gate.check_selection(self.store, result)
        self.assertFalse(got.modules[1].approved)

    def test_a_package_record_for_a_changed_package_does_not_cover_its_modules(self):
        result = self.verified()
        self.approve_package(result)
        self.approve_modules(result, only=["sample-harness"])
        with open(os.path.join(self.path, "sample-notes", "files", "docs", "notes.md"), "a") as handle:
            handle.write("changed\n")
        got = gate.check_selection(self.store, self.verified())
        self.assertFalse(got.modules[1].approved)

    def test_approvals_for_another_package_with_the_same_bytes_do_not_count(self):
        result = self.verified()
        for module in result.modules:
            approvals.record_module(self.store, "other/%s" % module.name, module.declaration_hash,
                                    module.tree_hash, "owner", NOW)
        got = gate.check_selection(self.store, result)
        self.assertFalse(got.approved)
        self.assertIn("approved for other/", got.modules[0].reason)


class FailClosedTest(Base):
    def test_a_refused_verification_is_passed_through_and_nothing_is_looked_up(self):
        with open(os.path.join(self.path, "sample-notes", "stray.txt"), "w") as handle:
            handle.write("x")
        result = verify.verify_packages([self.path], select=BOTH)
        self.assertFalse(result.accepted)
        got = gate.check_selection(Untouchable(), result)
        self.assertEqual((got.approved, got.modules), (False, ()))
        self.assertIn("refused", got.reason)

    def test_an_empty_selection_is_not_approved(self):
        result = verify.verify_packages([self.path])
        self.assertTrue(result.accepted)
        got = gate.check_selection(Untouchable(), result)
        self.assertFalse(got.approved)
        self.assertIn("no modules were selected", got.reason)

    def test_a_module_the_result_does_not_describe_is_not_approved(self):
        result = self.verified()
        self.approve_modules(result)
        for altered in (result._replace(modules=result.modules[:1]),
                        result._replace(packages=())):
            with self.subTest(altered=len(altered.modules) + len(altered.packages)):
                got = gate.check_selection(self.store, altered)
                self.assertFalse(got.approved)
                self.assertIn("does not describe", got.modules[-1].reason)

    def test_malformed_results_are_not_approved_and_never_raise(self):
        result = self.verified()
        self.approve_modules(result)
        junk = [result._replace(order=(1,)), result._replace(order=5),
                result._replace(order=(("sample",),)), result._replace(order=(None,)),
                result._replace(packages=None), result._replace(modules=(None,)),
                result._replace(modules=None), result._replace(packages=(("t", "a", "b", False),)),
                result._replace(order=[["third", "sample-harness"], ["third", "sample-notes", 1]]),
                result._replace(modules=("ab", "cd"))]
        for item in junk:
            with self.subTest(item=item):
                got = gate.check_selection(self.store, item)
                self.assertFalse(got.approved)
        self.assertTrue(gate.check_selection(self.store, result).approved)

    def test_things_that_are_not_results_are_not_approved(self):
        for junk in (None, 5, "accepted", object()):
            with self.subTest(junk=junk):
                self.assertFalse(gate.check_selection(Untouchable(), junk).approved)

    def test_a_store_that_cannot_be_read_approves_nothing(self):
        result = self.verified()
        self.approve_modules(result)
        shutil.rmtree(os.path.join(self.store.root, "packages"))
        os.symlink(self.base, os.path.join(self.store.root, "packages"))
        got = gate.check_selection(self.store, result)
        self.assertFalse(got.approved)


class ReadOnlyTest(Base):
    def test_the_gate_never_writes_in_either_outcome(self):
        result = self.verified()
        self.approve_modules(result, only=["sample-harness"])
        before = listing(self.store.root)
        self.assertFalse(gate.check_selection(self.store, result).approved)
        unapproved = listing(self.store.root)
        self.approve_modules(result)
        mid = listing(self.store.root)
        self.assertTrue(gate.check_selection(self.store, result).approved)
        self.assertEqual(unapproved, before)
        self.assertEqual(listing(self.store.root), mid)
        self.assertNotEqual(before, mid)

    def test_the_gate_leaves_the_package_unchanged(self):
        result = self.verified()
        before = listing(self.path)
        gate.check_selection(self.store, result)
        self.assertEqual(listing(self.path), before)


class MixedTest(Base):
    def setUp(self):
        super().setUp()
        self.dist = os.path.join(self.base, "dist")
        os.makedirs(os.path.join(self.dist, "workbench"))
        os.makedirs(os.path.join(self.dist, "packages"))
        self.first = os.path.join(self.dist, "packages", "sample")
        shutil.copytree(FIXTURE, self.first)
        path = os.path.join(self.first, "sample-notes", "module.json")
        with open(path) as handle:
            document = json.load(handle)
        document["provides"] = ["plans"]
        with open(path, "w") as handle:
            json.dump(document, handle)
        # A third-party package with one plain module.
        self.third = os.path.join(self.base, "extra")
        os.makedirs(os.path.join(self.third, "extra"))
        with open(os.path.join(self.third, "package.json"), "w") as handle:
            json.dump({"name": "extra", "version": "1.0.0", "contract": 1,
                       "modules": ["extra"]}, handle)
        with open(os.path.join(self.third, "extra", "module.json"), "w") as handle:
            json.dump({"name": "extra", "version": "1.0.0", "description": "An extra module."}, handle)
        firstparty.release_approvals(self.dist)

    def select(self):
        flagged = [self.first] if firstparty.is_first_party(self.first, self.dist) else []
        result = verify.verify_packages(
            [self.first, self.third],
            select=["sample/sample-harness", "sample/sample-notes", "extra/extra"],
            first_party=flagged)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        return result

    def test_first_party_modules_are_approved_by_shipped_records_and_the_rest_need_the_store(self):
        result = self.select()
        got = gate.check_selection(self.store, result, self.dist)
        self.assertFalse(got.approved)
        by_name = {m.name: m for m in got.modules}
        self.assertEqual((by_name["sample-harness"].approved, by_name["sample-harness"].source),
                         (True, "shipped"))
        self.assertEqual((by_name["sample-notes"].approved, by_name["sample-notes"].source),
                         (True, "shipped"))
        self.assertFalse(by_name["extra"].approved)

    def test_a_store_approval_completes_the_mixed_selection(self):
        result = self.select()
        extra = next(m for m in result.modules if m.name == "extra")
        approvals.record_module(self.store, "extra/extra", extra.declaration_hash, extra.tree_hash,
                                "owner", NOW)
        got = gate.check_selection(self.store, result, self.dist)
        self.assertTrue(got.approved, got)
        self.assertEqual(sorted((m.name, m.source) for m in got.modules),
                         [("extra", "store"), ("sample-harness", "shipped"), ("sample-notes", "shipped")])

    def test_the_first_party_flag_is_taken_as_given_and_only_exact_bytes_match(self):
        # The gate does not recheck where a package lives. A byte-identical copy outside the
        # distribution, claimed first-party, matches the shipped records made for exactly
        # those bytes and that subject; claimed third-party it loses the shipped lookup.
        outside = os.path.join(self.base, "outside")
        shutil.copytree(self.first, outside)
        self.assertFalse(firstparty.is_first_party(outside, self.dist))
        result = verify.verify_packages([outside], select=BOTH, first_party=[outside])
        self.assertTrue(result.accepted)
        claimed = gate.check_selection(self.store, result, self.dist)
        self.assertEqual([(m.approved, m.source) for m in claimed.modules],
                         [(True, "shipped"), (True, "shipped")])
        denied = result._replace(packages=tuple(p._replace(first_party=False) for p in result.packages))
        got = gate.check_selection(self.store, denied, self.dist)
        self.assertFalse(got.approved)
        self.assertEqual([m.source for m in got.modules], [None, None])

    def test_changed_bytes_outside_the_distribution_never_match_a_shipped_record(self):
        outside = os.path.join(self.base, "outside")
        shutil.copytree(self.first, outside)
        with open(os.path.join(outside, "sample-notes", "files", "docs", "notes.md"), "a") as handle:
            handle.write("changed\n")
        result = verify.verify_packages([outside], select=BOTH, first_party=[outside])
        got = gate.check_selection(self.store, result, self.dist)
        self.assertEqual([m.approved for m in got.modules], [True, False])

    def test_a_first_party_package_changed_after_release_loses_its_shipped_approval(self):
        with open(os.path.join(self.first, "sample-notes", "files", "docs", "notes.md"), "a") as handle:
            handle.write("changed\n")
        self.assertFalse(firstparty.is_first_party(self.first, self.dist))
        result = verify.verify_packages([self.first], select=BOTH, first_party=[self.first])
        got = gate.check_selection(self.store, result, self.dist)
        by_name = {m.name: m for m in got.modules}
        self.assertTrue(by_name["sample-harness"].approved)
        self.assertFalse(by_name["sample-notes"].approved)


if __name__ == "__main__":
    unittest.main()

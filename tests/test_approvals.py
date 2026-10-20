import hashlib
import json
import os
import shutil
import stat
import tempfile
import unittest

import support
from workbench import approvals, store
from workbench.approvals import ApprovalError

A, B, C, D = "a" * 64, "b" * 64, "c" * 64, "d" * 64
NOW = "2026-10-20T08:00:00Z"
KEY_MODULE_AB = "f04f2164227adad514ca7d1f286d89757d1c4e3fbb99be352217c4c3e946584d"
KEY_PACKAGE_AB = "965f31f19cc0650d1368dd44b58dd934e1c534a05c56778c1eb520a08dfc2c2f"
COMMIT = "0123456789abcdef0123456789abcdef01234567"


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
        self.root = os.path.join(self.base, "store")
        self.store = store.Store(self.root)
        self.store.ensure()

    def module(self, decl=A, tree=B, subject="pkg/mod"):
        return approvals.record_module(self.store, subject, decl, tree, "owner", NOW)

    def package(self, decl=A, tree=B, modules=(("mod", C, D),), commit=None):
        return approvals.record_package(self.store, "pkg", decl, tree, list(modules), "owner",
                                        NOW, commit)

    def record_path(self, key):
        return os.path.join(self.root, "packages", key, "approval.json")

    def put(self, key, data, name="approval.json"):
        directory = os.path.join(self.root, "packages", key)
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, name), "wb") as handle:
            handle.write(data if isinstance(data, bytes) else json.dumps(data).encode())


class KeyAndFormatTest(unittest.TestCase):
    def test_keys_are_fixed_by_known_answers(self):
        self.assertEqual(approvals.record_key("module", A, B), KEY_MODULE_AB)
        self.assertEqual(approvals.record_key("package", A, B), KEY_PACKAGE_AB)

    def test_kind_and_each_hash_change_the_key(self):
        keys = {approvals.record_key("module", A, B), approvals.record_key("package", A, B),
                approvals.record_key("module", C, B), approvals.record_key("module", A, C),
                approvals.record_key("module", B, A)}
        self.assertEqual(len(keys), 5)

    def test_bad_key_input_is_refused(self):
        for kind, decl, tree in (("other", A, B), ("module", A.upper(), B), ("module", A, B[:-1]),
                                 ("module", None, B), ("module", A, 5), ("module", A + "0", B),
                                 ("module", "g" * 64, B)):
            with self.subTest(kind=kind, decl=decl, tree=tree):
                with self.assertRaises(ApprovalError):
                    approvals.record_key(kind, decl, tree)

    def test_serialization_is_fixed(self):
        record = approvals.Approval("module", "pkg/mod", A, B, "owner", NOW, "0.1.0", (), None)
        expected = ('{\n  "approver": "owner",\n  "declaration_hash": "%s",\n  "format": 1,\n'
                    '  "kind": "module",\n  "subject": "pkg/mod",\n  "time": "%s",\n'
                    '  "tree_hash": "%s",\n  "workbench_version": "0.1.0"\n}\n') % (A, NOW, B)
        self.assertEqual(approvals.serialize(record), expected.encode())

    def test_package_serialization_sorts_modules(self):
        record = approvals.Approval("package", "pkg", A, B, "owner", NOW, "0.1.0",
                                    (("a", C, D), ("b", D, C)), COMMIT)
        again = approvals.parse_record(approvals.serialize(record))
        self.assertEqual(again, record)


class WriteAndCheckTest(Base):
    def test_module_round_trip(self):
        written = self.module()
        got = approvals.check_module(self.store, "pkg/mod", A, B)
        self.assertTrue(got.approved, got.reason)
        self.assertEqual(got.record, written)
        self.assertEqual((got.record.subject, got.record.approver, got.record.time),
                         ("pkg/mod", "owner", NOW))
        self.assertTrue(os.path.isfile(self.record_path(KEY_MODULE_AB)))

    def test_package_round_trip_with_modules_and_commit(self):
        self.package(modules=[("zeta", D, C), ("mod", C, D)], commit=COMMIT)
        got = approvals.check_package(self.store, "pkg", A, B)
        self.assertTrue(got.approved, got.reason)
        self.assertEqual(got.record.modules, (("mod", C, D), ("zeta", D, C)))
        self.assertEqual(got.record.commit, COMMIT)

    def test_a_module_record_is_not_a_package_approval_and_the_reverse(self):
        self.module()
        self.assertFalse(approvals.check_package(self.store, "pkg", A, B).approved)
        self.package(decl=C, tree=D)
        self.assertFalse(approvals.check_module(self.store, "pkg/mod", C, D).approved)

    def test_a_changed_declaration_or_tree_hash_is_not_approved(self):
        self.module()
        for decl, tree in ((C, B), (A, C), (B, A)):
            with self.subTest(decl=decl[0], tree=tree[0]):
                got = approvals.check_module(self.store, "pkg/mod", decl, tree)
                self.assertFalse(got.approved)
                self.assertIn("no approval is recorded", got.reason)

    def test_the_same_bytes_under_another_subject_are_not_approved(self):
        self.module(subject="pkga/m")
        self.assertTrue(approvals.check_module(self.store, "pkga/m", A, B).approved)
        for subject in ("pkgb/m", "pkga/other", "pkga", "", "PKGA/m", "pkga/m "):
            with self.subTest(subject=subject):
                got = approvals.check_module(self.store, subject, A, B)
                self.assertFalse(got.approved)
                self.assertIn("approved for pkga/m", got.reason)

    def test_a_subject_that_is_not_text_is_not_approved(self):
        self.module()
        for subject in (None, 5, ["pkg/mod"], b"pkg/mod"):
            with self.subTest(subject=subject):
                got = approvals.check_module(self.store, subject, A, B)
                self.assertFalse(got.approved)
                self.assertIn("not text", got.reason)

    def test_recording_another_subject_for_the_same_hashes_is_refused(self):
        self.module(subject="pkga/m")
        with self.assertRaisesRegex(ApprovalError, "different record"):
            self.module(subject="pkgb/m")
        self.assertFalse(approvals.check_module(self.store, "pkgb/m", A, B).approved)

    def test_empty_store_approves_nothing(self):
        self.assertFalse(approvals.check_module(self.store, "pkg/mod", A, B).approved)

    def test_two_approvals_for_one_subject_are_independent(self):
        self.module(A, B)
        self.module(C, D)
        self.assertTrue(approvals.check_module(self.store, "pkg/mod", A, B).approved)
        self.assertTrue(approvals.check_module(self.store, "pkg/mod", C, D).approved)
        self.assertFalse(approvals.check_module(self.store, "pkg/mod", A, D).approved)

    def test_check_does_not_write(self):
        self.module()
        before = listing(self.root)
        approvals.check_module(self.store, "pkg/mod", A, B)
        approvals.check_module(self.store, "pkg/mod", C, D)
        self.assertEqual(listing(self.root), before)

    def test_approving_the_same_thing_again_keeps_the_first_record(self):
        first = self.module()
        again = approvals.record_module(self.store, "pkg/mod", A, B, "someone-else",
                                        "2027-01-01T00:00:00Z")
        self.assertEqual(again, first)
        self.assertEqual(approvals.check_module(self.store, "pkg/mod", A, B).record.approver, "owner")

    def test_a_record_that_binds_something_else_is_not_replaced(self):
        self.package(modules=[("mod", C, D)])
        with self.assertRaisesRegex(ApprovalError, "different record"):
            self.package(modules=[("mod", C, D), ("extra", D, C)])
        with self.assertRaisesRegex(ApprovalError, "different record"):
            approvals.record_package(self.store, "other", A, B, [("mod", C, D)], "owner", NOW)
        self.assertEqual(approvals.check_package(self.store, "pkg", A, B).record.commit, None)

    def test_the_commit_is_provenance_so_another_commit_keeps_the_first_record(self):
        first = self.package(modules=[("mod", C, D)], commit=COMMIT)
        again = self.package(modules=[("mod", C, D)], commit="b" * 40)
        self.assertEqual(again, first)
        self.assertEqual(approvals.check_package(self.store, "pkg", A, B).record.commit, COMMIT)

    def test_a_local_approval_is_kept_when_the_same_content_is_approved_from_a_commit(self):
        first = self.package(modules=[("mod", C, D)])
        again = self.package(modules=[("mod", C, D)], commit=COMMIT)
        self.assertEqual(again, first)
        self.assertIsNone(approvals.check_package(self.store, "pkg", A, B).record.commit)

    def test_a_damaged_record_is_not_replaced(self):
        self.module()
        with open(self.record_path(KEY_MODULE_AB), "wb") as handle:
            handle.write(b"{ broken")
        with self.assertRaisesRegex(ApprovalError, "not usable"):
            self.module()
        with open(self.record_path(KEY_MODULE_AB), "rb") as handle:
            self.assertEqual(handle.read(), b"{ broken")

    def test_writers_refuse_bad_input_and_write_nothing(self):
        before = listing(self.root)
        bad = [dict(subject="nope", decl=A, tree=B), dict(subject="a/b/c", decl=A, tree=B),
               dict(subject="Pkg/mod", decl=A, tree=B), dict(subject="pkg/mod", decl=A.upper(), tree=B),
               dict(subject="pkg/mod", decl=A, tree="x")]
        for args in bad:
            with self.subTest(args=args):
                with self.assertRaises(ApprovalError):
                    approvals.record_module(self.store, args["subject"], args["decl"],
                                            args["tree"], "owner", NOW)
        for approver in ("", "x" * 65, "line\nbreak", None):
            with self.assertRaises(ApprovalError):
                approvals.record_module(self.store, "pkg/mod", A, B, approver, NOW)
        for when in ("yesterday", "2026-13-01T00:00:00Z", "2026-10-20 08:00:00", 5, "", 0,
                     "\u0662\u0660\u0662\u0666-10-20T10:00:00Z"):
            with self.assertRaises(ApprovalError):
                approvals.record_module(self.store, "pkg/mod", A, B, "owner", when)
        for commit in ("abc", "G" * 40, COMMIT.upper(), 5):
            with self.assertRaises(ApprovalError):
                self.package(commit=commit)
        for modules in ("ab", None, 5, [("mod", C)], [("mod", C, D, A)], ["abc"], [None]):
            with self.subTest(modules=modules):
                with self.assertRaises(ApprovalError):
                    approvals.record_package(self.store, "pkg", A, B, modules, "owner", NOW)
        self.assertEqual(listing(self.root), before)


class FailClosedTest(Base):
    def setUp(self):
        super().setUp()
        self.module()
        with open(self.record_path(KEY_MODULE_AB), "rb") as handle:
            self.good = handle.read()

    def check(self):
        return approvals.check_module(self.store, "pkg/mod", A, B)

    def test_a_truncated_record_is_no_approval(self):
        for cut in (0, 1, len(self.good) // 2, len(self.good) - 2):
            with self.subTest(cut=cut):
                self.put(KEY_MODULE_AB, self.good[:cut])
                got = self.check()
                self.assertFalse(got.approved)
                self.assertIn("malformed", got.reason)

    def test_a_record_edited_to_carry_other_hashes_is_rejected(self):
        document = json.loads(self.good)
        document["declaration_hash"] = C
        self.put(KEY_MODULE_AB, document)
        got = self.check()
        self.assertFalse(got.approved)
        self.assertIn("different hashes", got.reason)

    def test_a_record_copied_under_another_key_is_rejected(self):
        other = approvals.record_key("module", C, D)
        self.put(other, self.good)
        got = approvals.check_module(self.store, "pkg/mod", C, D)
        self.assertFalse(got.approved)
        self.assertIn("different hashes", got.reason)

    def test_a_record_of_another_kind_in_the_place_is_rejected(self):
        self.package(decl=C, tree=D)
        key = approvals.record_key("package", C, D)
        with open(self.record_path(key), "rb") as handle:
            package_record = handle.read()
        self.put(KEY_MODULE_AB, package_record)
        got = self.check()
        self.assertFalse(got.approved)
        self.assertIn("is for a package, not a module", got.reason)

    def test_a_record_with_the_right_hashes_under_the_wrong_kind_is_rejected(self):
        document = json.loads(self.good)
        document["kind"] = "package"
        document["subject"] = "pkg"
        document["modules"] = []
        document["commit"] = None
        self.put(KEY_MODULE_AB, document)
        got = self.check()
        self.assertFalse(got.approved)
        self.assertIn("is for a package, not a module", got.reason)

    def test_the_wrong_file_name_is_no_approval(self):
        os.unlink(self.record_path(KEY_MODULE_AB))
        self.put(KEY_MODULE_AB, self.good, name="other.json")
        got = self.check()
        self.assertFalse(got.approved)
        self.assertIn("no record", got.reason)

    def test_a_symbolic_link_in_place_of_the_record_is_not_followed(self):
        target = os.path.join(self.base, "elsewhere.json")
        with open(target, "wb") as handle:
            handle.write(self.good)
        os.unlink(self.record_path(KEY_MODULE_AB))
        os.symlink(target, self.record_path(KEY_MODULE_AB))
        got = self.check()
        self.assertFalse(got.approved)
        self.assertIn("not a regular file", got.reason)

    def test_a_symbolic_link_in_place_of_the_directory_is_not_followed(self):
        directory = os.path.join(self.root, "packages", KEY_MODULE_AB)
        moved = os.path.join(self.base, "moved")
        shutil.move(directory, moved)
        os.symlink(moved, directory)
        got = self.check()
        self.assertFalse(got.approved)
        self.assertIn("not a directory", got.reason)

    def test_a_directory_or_fifo_in_place_of_the_record_is_no_approval(self):
        os.unlink(self.record_path(KEY_MODULE_AB))
        os.mkdir(self.record_path(KEY_MODULE_AB))
        got = self.check()
        self.assertFalse(got.approved)
        self.assertIn("not a regular file (dir)", got.reason)
        os.rmdir(self.record_path(KEY_MODULE_AB))
        os.mkfifo(self.record_path(KEY_MODULE_AB))
        got = self.check()
        self.assertFalse(got.approved)
        self.assertIn("not a regular file (other)", got.reason)

    def test_an_unreadable_record_is_no_approval(self):
        os.chmod(self.record_path(KEY_MODULE_AB), 0)
        self.addCleanup(os.chmod, self.record_path(KEY_MODULE_AB), 0o600)
        if os.access(self.record_path(KEY_MODULE_AB), os.R_OK):
            self.skipTest("this account can read a file with no permissions")
        got = self.check()
        self.assertFalse(got.approved)
        self.assertIn("cannot be read", got.reason)

    def test_an_oversize_record_is_no_approval(self):
        self.put(KEY_MODULE_AB, b" " * (2 * 1024 * 1024))
        self.assertFalse(self.check().approved)

    def test_bad_hash_arguments_are_no_approval_and_never_raise(self):
        for decl, tree in ((None, B), (A, None), (5, B), ("", ""), (A.upper(), B), (A, B + "0"),
                           ([A], B), (b"a" * 64, B)):
            with self.subTest(decl=decl, tree=tree):
                got = approvals.check_module(self.store, "pkg/mod", decl, tree)
                self.assertFalse(got.approved)
                self.assertTrue(got.reason)

    def test_an_unknown_kind_is_no_approval(self):
        self.assertFalse(approvals.check(self.store, "plan", "pkg", A, B).approved)

    def test_the_intact_record_is_still_approved(self):
        self.assertTrue(self.check().approved)


class ParseTest(unittest.TestCase):
    def base(self, **change):
        document = {"format": 1, "kind": "module", "subject": "pkg/mod", "declaration_hash": A,
                    "tree_hash": B, "approver": "owner", "time": NOW, "workbench_version": "0.1.0"}
        document.update(change)
        return document

    def package(self, **change):
        document = self.base(kind="package", subject="pkg", modules=[], commit=None)
        document.update(change)
        return document

    def parse(self, document):
        data = document if isinstance(document, bytes) else json.dumps(document).encode()
        return approvals.parse_record(data)

    def test_good_documents_parse(self):
        self.assertEqual(self.parse(self.base()).kind, "module")
        self.assertEqual(self.parse(self.package(commit=COMMIT, modules=[
            {"name": "m", "declaration_hash": C, "tree_hash": D}])).modules, (("m", C, D),))
        self.assertEqual(self.parse(self.package(commit="a" * 64)).commit, "a" * 64)

    def test_each_bad_module_document_is_refused(self):
        bad = [self.base(format=2), self.base(format=True), self.base(format="1"),
               self.base(kind="plan"), self.base(kind=None),
               self.base(subject="pkg"), self.base(subject="a/b/c"), self.base(subject="Pkg/mod"),
               self.base(subject=""), self.base(subject=5),
               self.base(declaration_hash=A.upper()), self.base(declaration_hash=A[:-1]),
               self.base(tree_hash=5), self.base(approver=""), self.base(approver="x" * 65),
               self.base(approver="a\nb"), self.base(time="2026-10-20"), self.base(time="x"),
               self.base(time="2026-02-30T00:00:00Z"), self.base(workbench_version=""),
               self.base(extra=1), self.base(modules=[]), self.base(commit=None)]
        for document in bad:
            with self.subTest(document=document):
                with self.assertRaises(ApprovalError):
                    self.parse(document)

    def test_missing_fields_are_refused(self):
        for field in ("format", "kind", "subject", "declaration_hash", "tree_hash", "approver",
                      "time", "workbench_version"):
            document = self.base()
            del document[field]
            with self.subTest(field=field):
                with self.assertRaises(ApprovalError):
                    self.parse(document)

    def test_each_bad_package_document_is_refused(self):
        entry = {"name": "m", "declaration_hash": C, "tree_hash": D}
        bad = [self.package(subject="pkg/mod"), self.package(modules="x"), self.package(modules=[1]),
               self.package(modules=[{"name": "m"}]),
               self.package(modules=[dict(entry, extra=1)]),
               self.package(modules=[dict(entry, name="M")]),
               self.package(modules=[dict(entry, tree_hash="z")]),
               self.package(modules=[entry, dict(entry)]),
               self.package(commit="abc"), self.package(commit=5), self.package(commit=COMMIT.upper())]
        document = self.package()
        del document["commit"]
        bad.append(document)
        document = self.package()
        del document["modules"]
        bad.append(document)
        for document in bad:
            with self.subTest(document=document):
                with self.assertRaises(ApprovalError):
                    self.parse(document)

    def test_a_time_written_with_non_ascii_digits_is_refused(self):
        with self.assertRaises(ApprovalError):
            self.parse(self.base(time="\u0662\u0660\u0662\u0666-10-20T10:00:00Z"))

    def test_undecodable_and_hostile_bytes_are_refused(self):
        for data in (b"", b"[]", b"null", b"\xff", b'{"format": 1, "format": 1}', b"{" * 100000,
                     b'{"format": NaN}', b'{"format": 1.0}', b'{"a": "\\ud800"}'):
            with self.subTest(data=data[:20]):
                with self.assertRaises(ApprovalError):
                    approvals.parse_record(data)

    def test_an_unknown_field_name_is_escaped_in_the_message(self):
        with self.assertRaises(ApprovalError) as caught:
            self.parse(self.base(**{"evil\x1b[31m": 1}))
        self.assertNotIn("\x1b", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

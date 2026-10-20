import os
import tempfile
import unittest

from workbench import hashing, safefs

DECLARATION_HASH = "17c8c6f7f948ee1c9b93b1bc35f6edc29cbaf3022bff7d076d1c4831dd8a44a2"
TREE_HASH = "197194d481cbcbef872feb29ff03a8febe57a5cfceeba57dc8fa2088771633fe"
TREE_HASH_NO_EXEC = "a81e64594c0e3caff4465c8fd72317e6cd7a319bac5ef7af43a9f0ba15c00261"

# The three below were computed by a separate script from bytes written out by hand,
# not by this package.
ESCAPES = {"k": 'a"b\\c\nd\x01\u00e9\u2028/'}
ESCAPES_BYTES = b'{"k":"a\\"b\\\\c\\nd\\u0001\xc3\xa9\xe2\x80\xa8/"}'
ESCAPES_HASH = "e126c6daeaf57954870e73729df8822a8e9ad30b449e5bd8763686b7e2829c57"
ORDER_BYTES = b'{"\xef\xbf\xbf":2,"\xf0\x90\x80\x80":1}'
ORDER_HASH = "0056eda596b63aaf104150e181dfd804c88761f267ce050f6bc04bf05d947511"
NUMBERS = {"z": [False, 0, True, 1], "a": {"c": 123456789012345678901234567890, "b": -5}}
NUMBERS_HASH = "7f89de0d4d0fbeb7cba5e6d15d0c92eb5a377c0d60c894ba3ae3a8e4623ac7a8"
ORDERED_TREE_HASH = "5a287cb56a46d73e4434c07a1be4e9e46c75526995f244100ee16e5d6b9aa0e8"
EMPTY_TREE_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def make_tree(base, executable=True):
    os.makedirs(os.path.join(base, "bin"))
    with open(os.path.join(base, "a.txt"), "wb") as handle:
        handle.write(b"hello\n")
    script = os.path.join(base, "bin", "run.sh")
    with open(script, "wb") as handle:
        handle.write(b"#!/bin/sh\n")
    os.chmod(script, 0o755 if executable else 0o644)
    return base


class DeclarationHashTest(unittest.TestCase):
    def test_known_answer(self):
        self.assertEqual(hashing.declaration_hash({"b": 1, "a": [True, None, "é"]}),
                         DECLARATION_HASH)

    def test_serialization_is_compact_sorted_utf8(self):
        self.assertEqual(hashing.canonical_bytes({"b": 1, "a": [True, None, "é"]}),
                         '{"a":[true,null,"é"],"b":1}'.encode("utf-8"))

    def test_field_order_does_not_change_it(self):
        one = {"name": "x", "nested": {"p": 1, "q": 2}, "list": [1, 2]}
        two = {"list": [1, 2], "nested": {"q": 2, "p": 1}, "name": "x"}
        self.assertEqual(hashing.declaration_hash(one), hashing.declaration_hash(two))

    def test_whitespace_in_the_source_does_not_matter(self):
        import json
        spaced = json.loads('{ "b" : 1 ,\n "a" : [ true , null , "é" ] }')
        self.assertEqual(hashing.declaration_hash(spaced), DECLARATION_HASH)

    def test_a_changed_value_changes_it(self):
        self.assertNotEqual(hashing.declaration_hash({"b": 2, "a": [True, None, "é"]}),
                            DECLARATION_HASH)

    def test_list_order_matters(self):
        self.assertNotEqual(hashing.declaration_hash({"a": [1, 2]}),
                            hashing.declaration_hash({"a": [2, 1]}))

    def test_string_escapes_are_fixed(self):
        self.assertEqual(hashing.canonical_bytes(ESCAPES), ESCAPES_BYTES)
        self.assertEqual(hashing.declaration_hash(ESCAPES), ESCAPES_HASH)

    def test_keys_sort_by_code_point(self):
        value = {"\U00010000": 1, "\uffff": 2}
        self.assertEqual(hashing.canonical_bytes(value), ORDER_BYTES)
        self.assertEqual(hashing.declaration_hash(value), ORDER_HASH)

    def test_numbers_nested_keys_and_booleans_are_fixed(self):
        self.assertEqual(hashing.declaration_hash(NUMBERS), NUMBERS_HASH)
        self.assertNotEqual(hashing.declaration_hash({"a": True}),
                            hashing.declaration_hash({"a": 1}))
        self.assertNotEqual(hashing.declaration_hash({"a": False}),
                            hashing.declaration_hash({"a": 0}))

    def test_a_lone_surrogate_is_a_refusal_not_a_crash(self):
        for bad in ({"a": "\ud800"}, {"\udc00": 1}, {"a": ["x", "\ud800"]}):
            with self.subTest(bad=bad):
                with self.assertRaises(hashing.HashError):
                    hashing.declaration_hash(bad)

    def test_unhashable_values_are_refused(self):
        for bad in ({"a": 1.5}, {"a": float("nan")}, {"a": (1, 2)}, {1: "x"}, {"a": b"x"}):
            with self.subTest(bad=bad):
                with self.assertRaises(hashing.HashError):
                    hashing.declaration_hash(bad)


class TreeHashTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.join(os.path.realpath(self.tmp.name), "module")

    def test_known_answer(self):
        make_tree(self.base)
        self.assertEqual(hashing.tree_hash(self.base), TREE_HASH)

    def test_records_sort_by_path_bytes(self):
        # "a.b" < "a/b" < "sp ace.txt" < "\u00e9.txt" bytewise, though not component-wise.
        for rel, data, mode in (("a.b", b"1", 0o644), ("a/b", b"2", 0o755),
                                ("\u00e9.txt", b"3", 0o644), ("sp ace.txt", b"4", 0o644)):
            full = os.path.join(self.base, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as handle:
                handle.write(data)
            os.chmod(full, mode)
        self.assertEqual(hashing.tree_hash(self.base), ORDERED_TREE_HASH)

    def test_an_empty_tree_hashes_like_nothing(self):
        os.makedirs(os.path.join(self.base, "only", "dirs"))
        self.assertEqual(hashing.tree_hash(self.base), EMPTY_TREE_HASH)

    def test_hash_tree_returns_kept_content_and_listings(self):
        make_tree(self.base)
        info = hashing.hash_tree(self.base, keep=lambda rel: rel == "a.txt")
        self.assertEqual(info.hash, TREE_HASH)
        self.assertEqual(info.files, ["a.txt", "bin/run.sh"])
        self.assertEqual(info.dirs, ["bin"])
        self.assertEqual(info.contents, {"a.txt": b"hello\n"})

    def test_a_changed_execute_bit_changes_it(self):
        make_tree(self.base, executable=False)
        self.assertEqual(hashing.tree_hash(self.base), TREE_HASH_NO_EXEC)
        self.assertNotEqual(TREE_HASH, TREE_HASH_NO_EXEC)

    def test_a_group_execute_bit_does_not(self):
        make_tree(self.base, executable=False)
        os.chmod(os.path.join(self.base, "bin", "run.sh"), 0o655)
        self.assertEqual(hashing.tree_hash(self.base), TREE_HASH_NO_EXEC)

    def test_deterministic_on_fresh_copies(self):
        first = hashing.tree_hash(make_tree(os.path.join(self.base, "one")))
        second = hashing.tree_hash(make_tree(os.path.join(self.base, "two")))
        self.assertEqual(first, second)
        self.assertEqual(first, TREE_HASH)

    def test_changed_content_changes_it(self):
        make_tree(self.base)
        with open(os.path.join(self.base, "a.txt"), "wb") as handle:
            handle.write(b"hellp\n")
        self.assertNotEqual(hashing.tree_hash(self.base), TREE_HASH)

    def test_a_renamed_file_changes_it(self):
        make_tree(self.base)
        os.rename(os.path.join(self.base, "a.txt"), os.path.join(self.base, "b.txt"))
        self.assertNotEqual(hashing.tree_hash(self.base), TREE_HASH)

    def test_an_empty_directory_does_not_count(self):
        make_tree(self.base)
        os.mkdir(os.path.join(self.base, "empty"))
        self.assertEqual(hashing.tree_hash(self.base), TREE_HASH)

    def test_symlink_is_refused_and_named(self):
        make_tree(self.base)
        os.symlink("a.txt", os.path.join(self.base, "bin", "link"))
        with self.assertRaises(hashing.HashError) as ctx:
            hashing.tree_hash(self.base)
        self.assertIn("bin/link", str(ctx.exception))
        self.assertIn("symbolic link", str(ctx.exception))

    def test_fifo_is_refused_and_named(self):
        make_tree(self.base)
        os.mkfifo(os.path.join(self.base, "pipe"))
        with self.assertRaises(hashing.HashError) as ctx:
            hashing.tree_hash(self.base)
        self.assertIn("pipe", str(ctx.exception))

    def test_a_symlink_root_is_refused(self):
        make_tree(self.base)
        link = os.path.join(os.path.dirname(self.base), "link")
        os.symlink(self.base, link)
        with self.assertRaises(safefs.SafeFsError):
            hashing.tree_hash(link)

    def test_a_forbidden_name_is_refused(self):
        make_tree(self.base)
        os.mkdir(os.path.join(self.base, ".git"))
        with self.assertRaises(safefs.SafeFsError):
            hashing.tree_hash(self.base)

    def test_no_path_based_file_access(self):
        import inspect
        source = inspect.getsource(hashing)
        for banned in ("open(", "os.walk", "os.scandir", "glob"):
            self.assertNotIn(banned, source.replace("safefs.Root(", ""))


if __name__ == "__main__":
    unittest.main()

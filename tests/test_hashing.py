import os
import tempfile
import unittest

from workbench import hashing, safefs

DECLARATION_HASH = "17c8c6f7f948ee1c9b93b1bc35f6edc29cbaf3022bff7d076d1c4831dd8a44a2"
TREE_HASH = "197194d481cbcbef872feb29ff03a8febe57a5cfceeba57dc8fa2088771633fe"
TREE_HASH_NO_EXEC = "a81e64594c0e3caff4465c8fd72317e6cd7a319bac5ef7af43a9f0ba15c00261"


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
        self.assertIn("symlink", str(ctx.exception))

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

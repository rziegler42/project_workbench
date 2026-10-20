import json
import os
import shutil
import tempfile
import unittest

from workbench import snapshot, verify

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sample-package")


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.path = os.path.join(os.path.realpath(holder.name), "pkg")
        shutil.copytree(FIXTURE, self.path)
        result = verify.verify_package(self.path, select=["sample-notes", "sample-harness"])
        self.assertTrue(result.accepted, result.problems)
        self.verified = {item.name: item for item in result.modules}

    def root(self, name="sample-notes"):
        return os.path.join(self.path, name)

    def test_take_returns_verified_bytes(self):
        for name, item in self.verified.items():
            taken = snapshot.take(self.root(name), item)
            self.assertEqual((item.package, name), (taken.package, taken.module))
            self.assertIn("module.json", taken.files)
            self.assertEqual(set(item.executable), set(taken.executable))
            for rel, data in taken.files.items():
                with open(os.path.join(self.root(name), *rel.split("/")), "rb") as handle:
                    self.assertEqual(handle.read(), data)

    def test_take_refuses_file_changed_after_verify(self):
        item = self.verified["sample-notes"]
        with open(os.path.join(self.root(), "module.json"), "ab") as handle:
            handle.write(b" ")
        with self.assertRaises(snapshot.SnapshotError) as caught:
            snapshot.take(self.root(), item)
        self.assertIn("sample-notes", str(caught.exception))

    def test_take_refuses_added_file(self):
        with open(os.path.join(self.root(), "extra.txt"), "w") as handle:
            handle.write("x")
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.take(self.root(), self.verified["sample-notes"])

    def test_take_refuses_changed_declaration(self):
        item = self.verified["sample-notes"]
        # Same tree hash, different declaration hash: the verified record lies about the
        # declaration, as a swapped record would.
        wrong = item._replace(declaration_hash="0" * 64)
        with self.assertRaises(snapshot.SnapshotError) as caught:
            snapshot.take(self.root(), wrong)
        self.assertIn("declaration", str(caught.exception))
        # A changed declaration also changes the tree.
        path = os.path.join(self.root(), "module.json")
        with open(path) as handle:
            declaration = json.load(handle)
        declaration["description"] = "changed"
        with open(path, "w") as handle:
            json.dump(declaration, handle)
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.take(self.root(), item)

    def test_take_refuses_link_and_special_file(self):
        item = self.verified["sample-notes"]
        link = os.path.join(self.root(), "link")
        os.symlink(os.path.join(self.root(), "module.json"), link)
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.take(self.root(), item)
        os.unlink(link)
        os.mkfifo(link)
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.take(self.root(), item)
        os.unlink(link)
        snapshot.take(self.root(), item)

    def test_take_refuses_a_missing_module(self):
        shutil.rmtree(self.root())
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.take(self.root(), self.verified["sample-notes"])


if __name__ == "__main__":
    unittest.main()

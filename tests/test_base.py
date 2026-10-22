import os
import shutil
import tempfile
import unittest

from tests import support_words
from workbench import base, firstparty, hashing


class BaseTest(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.dist = os.path.realpath(holder.name)
        shutil.copytree(os.path.join(firstparty.default_distribution(), "base"),
                        os.path.join(self.dist, "base"))

    def put(self, rel, data):
        path = os.path.join(self.dist, "base", *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def test_load_base_hashes_files(self):
        loaded = base.load_base(self.dist)
        self.assertEqual(["AGENTS.md", "docs/README.md"], sorted(loaded.files))
        self.assertEqual(hashing.tree_hash(os.path.join(self.dist, "base"), "the base"),
                         loaded.tree_hash)
        before = loaded.tree_hash
        self.put("AGENTS.md", loaded.files["AGENTS.md"] + b"more\n")
        self.assertNotEqual(before, base.load_base(self.dist).tree_hash)

    def test_the_shipped_base_loads(self):
        loaded = base.load_base()
        self.assertEqual(["AGENTS.md", "docs/README.md"], sorted(loaded.files))

    def test_base_refuses_link_and_special_files(self):
        path = os.path.join(self.dist, "base", "link.md")
        os.symlink(os.path.join(self.dist, "base", "AGENTS.md"), path)
        with self.assertRaises(base.BaseError):
            base.load_base(self.dist)
        os.unlink(path)
        os.mkfifo(path)
        with self.assertRaises(base.BaseError):
            base.load_base(self.dist)
        os.unlink(path)
        base.load_base(self.dist)

    def test_base_refuses_a_missing_directory_and_executables(self):
        shutil.rmtree(os.path.join(self.dist, "base"))
        with self.assertRaises(base.BaseError):
            base.load_base(self.dist)
        shutil.copytree(os.path.join(firstparty.default_distribution(), "base"),
                        os.path.join(self.dist, "base"))
        os.chmod(os.path.join(self.dist, "base", "AGENTS.md"), 0o755)
        with self.assertRaises(base.BaseError):
            base.load_base(self.dist)

    def test_base_refuses_a_path_the_validator_refuses(self):
        self.put(".git/config", b"x")
        with self.assertRaises(base.BaseError):
            base.load_base(self.dist)

    def test_base_contains_no_harness_file_name(self):
        loaded = base.load_base()
        for rel, data in loaded.files.items():
            text = (rel + "\n" + data.decode("utf-8")).lower()
            for name in support_words.harness_names() + ["gemini", "cursor", "copilot", ".agents"]:
                self.assertNotIn(name, text, "%s names %s" % (rel, name))

    def test_base_slot_markers_present_exactly_once(self):
        loaded = base.load_base()
        for slot, rel in base.SLOT_FILES.items():
            lines = loaded.files[rel].decode().split("\n")
            self.assertEqual(1, lines.count("<!-- @slot: %s -->" % slot))
        self.assertEqual(("docs-index", "policy"), base.BASE_SLOTS)

    def test_a_missing_or_repeated_marker_is_refused(self):
        self.put("AGENTS.md", b"# no marker\n")
        with self.assertRaises(base.BaseError):
            base.load_base(self.dist)
        self.put("AGENTS.md", b"<!-- @slot: policy -->\n<!-- @slot: policy -->\n")
        with self.assertRaises(base.BaseError):
            base.load_base(self.dist)


if __name__ == "__main__":
    unittest.main()

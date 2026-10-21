"""The maintainer directories, `tests/` and `tools/`: hashed and approved, never installed."""

import os
import shutil
import tempfile
import unittest

from workbench import modulefiles, snapshot, verify
from tests.test_install import InstallBase
from tests.test_modulefiles import Base
from tests.test_preview import NOTES

MAINTAINER = ("tests", "tools")


class VerifyTest(Base):
    def test_both_directories_are_accounted(self):
        self.put("sample-notes/tests/test_x.py")
        self.put("sample-notes/tools/build.py")
        self.assertEqual(self.check().problems, [])

    def test_a_change_in_either_changes_the_tree_hash(self):
        before = self.check().tree_hash
        for name, rel in (("tests", "tests/test_x.py"), ("tools", "tools/build.py")):
            with self.subTest(directory=name):
                self.put("sample-notes/" + rel, "one\n")
                added = self.check().tree_hash
                self.assertNotEqual(before, added)
                self.put("sample-notes/" + rel, "two\n")
                self.assertNotEqual(added, self.check().tree_hash)
                self.put("sample-notes/" + rel, "one\n")
                self.assertEqual(added, self.check().tree_hash)
                os.remove(os.path.join(self.path, "sample-notes", rel))
                self.assertEqual(before, self.check().tree_hash)

    def test_a_mode_change_changes_the_tree_hash(self):
        self.put("sample-notes/tools/build.py", mode=0o644)
        before = self.check().tree_hash
        os.chmod(os.path.join(self.path, "sample-notes", "tools", "build.py"), 0o755)
        self.assertNotEqual(before, self.check().tree_hash)

    def test_an_executable_there_is_not_listed_for_the_approval(self):
        self.put("sample-notes/tools/build.py", mode=0o755)
        self.put("sample-notes/scripts/check.sh", mode=0o755)
        self.assertEqual(self.check().executable, ("scripts/check.sh",))

    def test_an_unlisted_directory_is_still_refused(self):
        self.put("sample-notes/tests/test_x.py")
        self.put("sample-notes/docs/readme.md")
        result = self.refused("unaccounted-file")
        self.assertIn("docs/readme.md", str(result.problems[0]))

    def test_nested_files_are_accounted(self):
        self.put("sample-notes/tests/deep/er/test_x.py")
        self.put("sample-notes/tools/a/b/c.py")
        self.assertEqual(self.check().problems, [])

    def test_names_are_case_sensitive(self):
        for name in ("Tests", "TOOLS", "test", "tool"):
            with self.subTest(name=name):
                self.put("sample-notes/%s/x.py" % name)
                self.refused("unaccounted-file")
                shutil.rmtree(os.path.join(self.path, "sample-notes", name))

    def test_a_file_named_like_a_maintainer_directory_is_unaccounted(self):
        for name in MAINTAINER:
            with self.subTest(name=name):
                self.put("sample-notes/" + name)
                self.refused("unaccounted-file")
                os.remove(os.path.join(self.path, "sample-notes", name))

    def test_a_symbolic_link_inside_either_is_refused(self):
        for name in MAINTAINER:
            with self.subTest(name=name):
                folder = os.path.join(self.path, "sample-notes", name)
                os.makedirs(folder)
                os.symlink(os.path.join(self.path, "sample-notes", "module.json"),
                           os.path.join(folder, "link"))
                self.refused("files")
                shutil.rmtree(folder)

    def test_a_symbolic_link_as_either_is_refused(self):
        for name in MAINTAINER:
            with self.subTest(name=name):
                link = os.path.join(self.path, "sample-notes", name)
                os.symlink(os.path.join(self.path, "sample-notes", "scripts"), link)
                self.refused("files")
                os.remove(link)

    def test_an_empty_directory_is_ignored_like_any_other(self):
        before = self.check().tree_hash
        for name in MAINTAINER:
            os.makedirs(os.path.join(self.path, "sample-notes", name, "inner"))
        result = self.check()
        self.assertEqual(result.problems, [])
        self.assertEqual(before, result.tree_hash)

    def test_ships_cannot_name_a_maintainer_directory_or_a_file_in_one(self):
        self.put("sample-notes/tests/test_x.py")
        self.put("sample-notes/tools/build.py")
        for item in ("tests", "tools", "tests/test_x.py", "tools/build.py"):
            with self.subTest(item=item):
                self.edit_module(ships=["scripts/check.sh", item])
                result = self.refused("ships")
                self.assertIn(item, str(result.problems[0]))
                self.assertIn("maintainer", str(result.problems[0]))

    def test_a_fills_source_cannot_come_from_a_maintainer_directory(self):
        for name in MAINTAINER:
            with self.subTest(name=name):
                self.put("sample-notes/%s/a.md" % name)
                self.edit_module(fills=[{"slot": "slot:notes", "source": name + "/a.md"}])
                result = self.refused("fills")
                self.assertIn("maintainer", str(result.problems[0]))

    def test_the_reserved_names_are_the_documented_five(self):
        self.assertEqual(set(modulefiles.RESERVED_DIRS),
                         {"harness", "templates", "files", "tests", "tools"})


class KeptTest(unittest.TestCase):
    """The snapshot an install writes from holds no maintainer file, yet still proves the tree."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.path = os.path.join(os.path.realpath(holder.name), "pkg")
        shutil.copytree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures",
                                     "sample-package"), self.path)
        self.root = os.path.join(self.path, "sample-notes")
        for rel in ("tests/test_x.py", "tools/build.py", "tools/sub/more.py"):
            full = os.path.join(self.root, *rel.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w") as handle:
                handle.write("print(1)\n")
        os.chmod(os.path.join(self.root, "tools", "build.py"), 0o755)

    def verified(self):
        result = verify.verify_package(self.path, select=["sample-notes", "sample-harness"])
        self.assertTrue(result.accepted, result.problems)
        return {item.name: item for item in result.modules}["sample-notes"]

    def test_the_snapshot_holds_none_of_them(self):
        item = self.verified()
        taken = snapshot.take(self.root, item)
        self.assertIn("module.json", taken.files)
        self.assertFalse([rel for rel in taken.files if rel.split("/")[0] in MAINTAINER])
        self.assertFalse([rel for rel in taken.executable if rel.split("/")[0] in MAINTAINER])

    def test_a_changed_maintainer_file_still_fails_the_snapshot(self):
        item = self.verified()
        with open(os.path.join(self.root, "tests", "test_x.py"), "a") as handle:
            handle.write("# changed\n")
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.take(self.root, item)

    def test_an_added_maintainer_file_still_fails_the_snapshot(self):
        item = self.verified()
        with open(os.path.join(self.root, "tools", "new.py"), "w") as handle:
            handle.write("x\n")
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.take(self.root, item)


class InstallTest(InstallBase):
    def package_with(self, extra):
        fields, files = NOTES
        files = dict(files)
        files.update(extra)
        return self.package(modules={"h": ({"type": "harness", "layout": {}}, {}),
                                     "notes": (fields, files)})

    def installed(self, path, name):
        self.approve(path)
        place = self.place(name)
        code, out, err = self.run_install(place, path)
        self.assertEqual(0, code, (out, err))
        found = {}
        for base, dirs, files in os.walk(place):
            dirs[:] = [d for d in dirs if d != ".git"]
            for name in files:
                full = os.path.join(base, name)
                found[os.path.relpath(full, place)] = self.read(full)
        return found

    def test_an_install_writes_neither_directory(self):
        plain = self.installed(self.package_with({}), "plain")
        with_dirs = self.installed(self.package_with({
            "tests/test_x.py": b"import unittest\n",
            "tests/deep/test_y.py": b"y\n",
            "tools/build.py": b"#!/usr/bin/env python3\n",
        }), "with-dirs")
        self.assertFalse([rel for rel in with_dirs if "/tests/" in rel or "/tools/" in rel])
        self.assertEqual(sorted(plain), sorted(with_dirs))
        for rel in plain:
            if not rel.endswith("manifest.json"):
                self.assertEqual(plain[rel], with_dirs[rel], rel)


if __name__ == "__main__":
    unittest.main()

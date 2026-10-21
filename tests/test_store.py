import hashlib
import os
import stat
import tempfile
import unittest
import unittest.mock

import support
from workbench import store
from workbench.wbkit import safefs


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
            found[os.path.relpath(full, top)] = (stat.S_IMODE(info.st_mode), digest,
                                                  info.st_mtime_ns)
    return found


class StoreBase(unittest.TestCase):
    def setUp(self):
        support.forbid_real_store(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.root = os.path.join(self.base, ".config", "project-workbench")
        self.store = store.Store(self.root)


class EnsureTest(StoreBase):
    def test_creates_the_store_and_its_layout_with_private_modes(self):
        self.store.ensure()
        for rel in ("", "packages", "cache", "projects", "bin"):
            info = os.lstat(os.path.join(self.root, rel))
            self.assertTrue(stat.S_ISDIR(info.st_mode), rel)
            self.assertEqual(stat.S_IMODE(info.st_mode) & 0o077, 0, rel)
        self.assertEqual(sorted(os.listdir(self.root)), ["bin", "cache", "packages", "projects"])

    def test_a_second_call_changes_nothing(self):
        self.store.ensure()
        before = listing(self.base)
        self.store.ensure()
        self.assertEqual(listing(self.base), before)

    def test_missing_directory_inside_an_existing_store_is_made(self):
        self.store.ensure()
        os.rmdir(os.path.join(self.root, "cache"))
        self.store.ensure()
        self.assertTrue(os.path.isdir(os.path.join(self.root, "cache")))

    def test_existing_files_are_kept(self):
        self.store.ensure()
        self.store.write("settings", b"{}")
        self.store.ensure()
        self.assertEqual(self.store.read("settings"), b"{}")

    def test_a_store_open_to_group_or_other_is_refused_and_not_repaired(self):
        self.store.ensure()
        for mode in (0o750, 0o705, 0o755, 0o770):
            with self.subTest(mode=oct(mode)):
                os.chmod(self.root, mode)
                with self.assertRaisesRegex(store.StoreError, "open to other users"):
                    self.store.ensure()
                self.assertEqual(stat.S_IMODE(os.lstat(self.root).st_mode), mode)
        os.chmod(self.root, 0o700)

    def test_setgid_sticky_and_missing_owner_bits_are_refused(self):
        self.store.ensure()
        for mode in (0o2700, 0o1700, 0o500, 0o600):
            with self.subTest(mode=oct(mode)):
                os.chmod(self.root, mode)
                with self.assertRaisesRegex(store.StoreError, "unexpected mode"):
                    self.store.ensure()
        os.chmod(self.root, 0o700)
        self.store.ensure()

    def test_a_layout_directory_open_to_others_is_refused(self):
        self.store.ensure()
        path = os.path.join(self.root, "packages")
        os.chmod(path, 0o755)
        with self.assertRaisesRegex(store.StoreError, "packages"):
            self.store.ensure()

    def test_a_store_owned_by_another_user_is_refused(self):
        self.store.ensure()
        with unittest.mock.patch.object(store, "_current_uid", lambda: os.geteuid() + 1):
            with self.assertRaisesRegex(store.StoreError, "owned by another user"):
                self.store.ensure()

    def test_a_store_that_is_a_symbolic_link_is_refused(self):
        elsewhere = os.path.join(self.base, "elsewhere")
        os.makedirs(elsewhere, mode=0o700)
        os.makedirs(os.path.dirname(self.root))
        os.symlink(elsewhere, self.root)
        with self.assertRaises(safefs.SafeFsError):
            self.store.ensure()
        self.assertEqual(os.listdir(elsewhere), [])

    def test_a_layout_directory_that_is_a_symbolic_link_is_refused(self):
        self.store.ensure()
        elsewhere = os.path.join(self.base, "elsewhere")
        os.makedirs(elsewhere, mode=0o700)
        os.rmdir(os.path.join(self.root, "packages"))
        os.symlink(elsewhere, os.path.join(self.root, "packages"))
        with self.assertRaises(safefs.SafeFsError):
            self.store.ensure()
        self.assertEqual(os.listdir(elsewhere), [])

    def test_a_file_where_a_directory_belongs_is_refused(self):
        self.store.ensure()
        os.rmdir(os.path.join(self.root, "bin"))
        with open(os.path.join(self.root, "bin"), "w") as handle:
            handle.write("x")
        with self.assertRaises(safefs.SafeFsError):
            self.store.ensure()

    def test_a_file_in_place_of_the_store_is_refused(self):
        os.makedirs(os.path.dirname(self.root))
        with open(self.root, "w") as handle:
            handle.write("x")
        with self.assertRaises(safefs.SafeFsError):
            self.store.ensure()

    def test_ancestors_may_be_symbolic_links(self):
        dotfiles = os.path.join(self.base, "dotfiles")
        os.makedirs(dotfiles)
        os.symlink(dotfiles, os.path.join(self.base, ".config"))
        self.store.ensure()
        self.assertTrue(os.path.isdir(os.path.join(dotfiles, "project-workbench", "packages")))

    def test_a_relative_root_is_refused(self):
        with self.assertRaises(store.StoreError):
            store.Store("relative/store")
        with self.assertRaises(store.StoreError):
            store.Store(None)
        with self.assertRaises(store.StoreError):
            store.Store(self.base + "/with\0nul")


class DefaultRootTest(unittest.TestCase):
    def test_default_root_comes_from_home(self):
        with tempfile.TemporaryDirectory() as home:
            with unittest.mock.patch.dict(os.environ, {"HOME": home}):
                self.assertEqual(store.default_root(),
                                 os.path.join(home, ".config", "project-workbench"))

    def test_no_workbench_variable_moves_the_store(self):
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as other:
            env = {"HOME": home, "WORKBENCH_HOME": other, "WORKBENCH_STORE": other,
                   "XDG_CONFIG_HOME": other}
            with unittest.mock.patch.dict(os.environ, env):
                self.assertEqual(store.default_root(),
                                 os.path.join(home, ".config", "project-workbench"))

    def test_the_guard_fails_a_test_that_asks_for_the_real_location(self):
        class Probe(unittest.TestCase):
            def runTest(self):
                support.forbid_real_store(self)
                store.default_root()

        result = unittest.TestResult()
        Probe().run(result)
        self.assertEqual(len(result.failures) + len(result.errors), 1)


class ReadWriteTest(StoreBase):
    def setUp(self):
        super().setUp()
        self.store.ensure()

    def test_round_trip_and_nested_paths(self):
        self.store.write("packages/ab/record.json", b"data")
        self.assertEqual(self.store.read("packages/ab/record.json"), b"data")

    def test_paths_that_escape_are_refused(self):
        for rel in ("../outside", "/abs", "a/../b", "", ".git/config", "a\\b"):
            with self.subTest(rel=rel):
                with self.assertRaises(safefs.SafeFsError):
                    self.store.write(rel, b"x")
                with self.assertRaises(safefs.SafeFsError):
                    self.store.read(rel)
        self.assertEqual(os.listdir(self.base), [".config"])

    def test_a_symbolic_link_planted_inside_the_store_is_not_followed(self):
        outside = os.path.join(self.base, "outside")
        os.makedirs(outside)
        with open(os.path.join(outside, "secret"), "wb") as handle:
            handle.write(b"secret")
        os.symlink(outside, os.path.join(self.root, "packages", "link"))
        with self.assertRaises(safefs.SafeFsError):
            self.store.read("packages/link/secret")
        with self.assertRaises(safefs.SafeFsError):
            self.store.write("packages/link/new", b"x")
        self.assertEqual(os.listdir(outside), ["secret"])

    def test_a_symbolic_link_in_place_of_a_file_is_not_read_or_overwritten(self):
        target = os.path.join(self.base, "target")
        with open(target, "wb") as handle:
            handle.write(b"keep")
        os.symlink(target, os.path.join(self.root, "settings"))
        with self.assertRaises(safefs.SafeFsError):
            self.store.read("settings")
        with self.assertRaises(safefs.SafeFsError):
            self.store.write("settings", b"changed")
        with open(target, "rb") as handle:
            self.assertEqual(handle.read(), b"keep")

    def test_reading_a_missing_file_is_a_refusal_not_a_crash(self):
        with self.assertRaises(safefs.SafeFsError):
            self.store.read("settings")

    def test_write_replaces_atomically_and_leaves_no_temporary_file(self):
        self.store.write("settings", b"one")
        self.store.write("settings", b"two")
        self.assertEqual(self.store.read("settings"), b"two")
        self.assertEqual(sorted(os.listdir(self.root)),
                         ["bin", "cache", "packages", "projects", "settings"])


if __name__ == "__main__":
    unittest.main()

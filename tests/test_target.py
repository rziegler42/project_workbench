import os
import stat
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

from workbench import target
from workbench.target import TargetError, TargetUsage


class TargetTest(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)
        self.store = os.path.join(self.base, "store")
        os.mkdir(self.store)
        self.home = os.path.join(self.base, "home")
        os.mkdir(self.home)
        # Keep the account database's real home out of the way of these tests.
        patch = unittest.mock.patch.object(target, "_account_home", lambda: None)
        patch.start()
        self.addCleanup(patch.stop)

    def path(self, *parts):
        return os.path.join(self.base, *parts)

    def make(self, *parts):
        path = self.path(*parts)
        os.makedirs(path, exist_ok=True)
        return path

    def put(self, rel, data=b"x"):
        path = self.path(*rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def open(self, spelling):
        return target.open_target(spelling, self.store, home=self.home)

    def refused(self, spelling, *needles):
        before = sorted(os.listdir(self.base))
        with self.assertRaises(TargetError) as caught:
            self.open(spelling)
        for needle in needles:
            self.assertIn(needle, str(caught.exception))
        self.assertEqual(before, sorted(os.listdir(self.base)))
        return caught.exception

    def existing(self, name="proj"):
        self.make(name, ".git")
        self.put("%s/.workbench/manifest.json" % name)
        return self.path(name)


class ChooseTest(TargetTest):
    def test_choose_default_is_dot(self):
        self.assertEqual(".", target.choose(None, None))

    def test_choose_empty_is_usage_error(self):
        for pair in (("", None), (None, ""), ("a", "")):
            with self.assertRaises(TargetUsage):
                target.choose(*pair)

    def test_choose_differing_spellings_refused(self):
        self.make("one")
        self.make("two")
        with self.assertRaises(TargetUsage) as caught:
            target.choose(self.path("one"), self.path("two"))
        self.assertIn("different", str(caught.exception))

    def test_choose_same_directory_by_identity(self):
        self.make("one")
        os.symlink(self.path("one"), self.path("alias"))
        self.assertEqual(self.path("one/"), target.choose(self.path("one/"), self.path("one/.")))
        # A parent that is a link names the same directory by identity.
        os.symlink(self.base, self.path("up"))
        self.assertEqual(self.path("one"),
                         target.choose(self.path("one"), self.path("up", "one")))
        # Neither exists: the resolved path decides.
        self.assertEqual(self.path("none"), target.choose(self.path("none"), self.path("x", "..", "none")))

    def test_choose_a_link_and_its_destination_differ(self):
        self.make("one")
        os.symlink(self.path("one"), self.path("alias"))
        with self.assertRaises(TargetUsage):
            target.choose(self.path("one"), self.path("alias"))


class OpenTest(TargetTest):
    def test_final_symlink_refused_even_to_directory(self):
        self.make("real")
        os.symlink(self.path("real"), self.path("link"))
        self.refused(self.path("link"), "symbolic link", self.path("link"))
        self.refused(self.path("link") + "/", "symbolic link")
        os.symlink(self.path("nowhere"), self.path("dangling"))
        self.refused(self.path("dangling"), "symbolic link")

    def test_parent_symlink_is_resolved(self):
        self.make("real")
        os.symlink(self.path("real"), self.path("via"))
        with self.open(self.path("via", "new")) as held:
            self.assertEqual(self.path("real", "new"), held.path)
            self.assertEqual("new-missing", held.state)

    def test_refuses_root_home_store_inside_store_and_container_of_store(self):
        self.refused("/", "root")
        self.refused(self.home, "home directory")
        self.refused(self.store, "guarded store")
        inside = self.make("store", "deeper")
        self.refused(inside, "guarded store")
        self.refused(self.path("store", "newdir"), "guarded store")
        self.refused(self.base, "contains the guarded store")

    def test_a_subdirectory_of_home_is_fine(self):
        self.make("home", "proj")
        with self.open(self.path("home", "proj")) as held:
            self.assertEqual("new-empty", held.state)

    def test_home_from_account_database_also_refused(self):
        other = self.make("accounthome")
        with unittest.mock.patch.object(target, "_account_home", lambda: other):
            self.refused(other, "home directory")

    def test_state_missing_with_parent_is_new(self):
        with self.open(self.path("fresh")) as held:
            self.assertEqual(("new-missing", "fresh"), (held.state, held.name))
            self.assertEqual(os.stat(self.base).st_ino, os.fstat(held.fd).st_ino)
            self.assertFalse(held.has_incomplete_marker())
        self.assertFalse(os.path.exists(self.path("fresh")))

    def test_state_missing_parent_refused(self):
        self.refused(self.path("no", "such", "dir"), "parent")

    def test_state_empty_and_lone_git_are_new(self):
        self.make("empty")
        with self.open(self.path("empty")) as held:
            self.assertEqual("new-empty", held.state)
        self.make("lone", ".git")
        with self.open(self.path("lone")) as held:
            self.assertEqual("new-git", held.state)

    def test_other_content_and_files_are_refused(self):
        self.put("full/readme")
        self.refused(self.path("full"), "other content")
        self.put("afile")
        self.refused(self.path("afile"), "not a directory")
        self.make("both", ".git")
        self.put("both/readme")
        self.refused(self.path("both"), "other content")

    def test_git_file_or_link_refused(self):
        self.make("filegit")
        self.put("filegit/.git", b"gitdir: elsewhere")
        self.refused(self.path("filegit"), ".git is not a real directory")
        self.make("linkgit")
        self.make("elsewhere")
        os.symlink(self.path("elsewhere"), self.path("linkgit", ".git"))
        self.refused(self.path("linkgit"), ".git is not a real directory")

    def test_existing_needs_manifest_regular_file(self):
        with self.open(self.existing()) as held:
            self.assertEqual("existing", held.state)
        self.make("nomanifest", ".git", )
        self.make("nomanifest", ".workbench")
        self.refused(self.path("nomanifest"), "manifest.json")
        self.make("dirmanifest", ".git")
        self.make("dirmanifest", ".workbench", "manifest.json")
        self.refused(self.path("dirmanifest"), "manifest.json")
        self.make("linkmanifest", ".git")
        self.make("linkmanifest", ".workbench")
        self.put("real.json")
        os.symlink(self.path("real.json"), self.path("linkmanifest", ".workbench", "manifest.json"))
        self.refused(self.path("linkmanifest"), "manifest.json")

    def test_existing_without_its_own_git_is_refused(self):
        self.put("nogit/.workbench/manifest.json")
        self.refused(self.path("nogit"), "other content")

    def test_workbench_link_is_not_existing(self):
        self.make("linkwb", ".git")
        self.make("realwb")
        self.put("realwb/manifest.json")
        os.symlink(self.path("realwb"), self.path("linkwb", ".workbench"))
        self.refused(self.path("linkwb"), ".workbench is not a real directory")

    def test_local_link_is_not_existing(self):
        root = self.existing()
        self.make("elsewhere")
        os.symlink(self.path("elsewhere"), os.path.join(root, ".workbench", "local"))
        self.refused(root, ".workbench/local")

    def test_incomplete_marker_is_not_existing(self):
        root = self.existing()
        self.put("proj/.workbench/local/incomplete", b"")
        self.refused(root, "unfinished install")
        # Also a half-made target that has only the marker.
        self.put("half/.workbench/local/incomplete", b"")
        self.refused(self.path("half"), "unfinished install")

    def test_marker_is_seen_after_the_target_is_held(self):
        root = self.existing()
        with self.open(root) as held:
            self.assertFalse(held.has_incomplete_marker())
            self.put("proj/.workbench/local/incomplete", b"")
            self.assertTrue(held.has_incomplete_marker())

    def test_hostile_git_config_is_never_read(self):
        for case in ("lone", "full"):
            root = self.path(case)
            self.make(case, ".git")
            with open(os.path.join(root, ".git", "config"), "w") as handle:
                handle.write("[core]\n\tfsmonitor = touch %s\n" % self.path("pwned"))
            if case == "full":
                self.put("full/.workbench/manifest.json")
            opened = []
            watching = [True]

            def audit(event, args):
                if watching[0] and event == "open":
                    opened.append(str(args[0]))

            sys.addaudithook(audit)
            try:
                with unittest.mock.patch.object(subprocess, "Popen",
                                                side_effect=AssertionError("ran a program")):
                    with self.open(root) as held:
                        held.recheck()
                        held.has_incomplete_marker()
            finally:
                watching[0] = False
            self.assertFalse([name for name in opened if name.split("/")[-1] in (".git", "config")])
            self.assertFalse(os.path.exists(self.path("pwned")))

    def test_recheck_detects_swapped_directory(self):
        self.make("proj")
        with self.open(self.path("proj")) as held:
            held.recheck()
            os.rename(self.path("proj"), self.path("moved"))
            os.mkdir(self.path("proj"))
            with self.assertRaises(TargetError) as caught:
                held.recheck()
            self.assertIn("changed", str(caught.exception))

    def test_recheck_detects_a_missing_target_appearing(self):
        with self.open(self.path("later")) as held:
            held.recheck()
            os.mkdir(self.path("later"))
            with self.assertRaises(TargetError):
                held.recheck()

    def test_recheck_detects_swapped_parent_of_missing_target(self):
        os.mkdir(self.path("outer"))
        with self.open(self.path("outer", "later")) as held:
            os.rename(self.path("outer"), self.path("outer2"))
            os.mkdir(self.path("outer"))
            with self.assertRaises(TargetError):
                held.recheck()

    def test_closed_target_cannot_be_used(self):
        held = self.open(self.make("proj"))
        held.close()
        with self.assertRaises(TargetError):
            held.recheck()

    def test_case_variant_of_store_refused_on_case_insensitive_volume(self):
        if not os.path.exists(self.path("STORE")):
            self.skipTest("the volume is case-sensitive")
        self.refused(self.path("STORE"), "guarded store")


if __name__ == "__main__":
    unittest.main()

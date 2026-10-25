import os

from tests.test_target import TargetTest
from workbench import target
from workbench.target import TargetError


class AdoptableTest(TargetTest):
    """The adoptable state: a real `.git`, content besides it, and no `.workbench` of any kind."""

    def adoptable(self, name="repo"):
        self.make(name, ".git")
        self.put("%s/README.md" % name, b"hello\n")
        return self.path(name)

    def open_adopt(self, spelling):
        return target.open_target(spelling, self.store, home=self.home, adopt=True)

    def refused_adopt(self, spelling, *needles):
        before = sorted(os.listdir(self.base))
        with self.assertRaises(TargetError) as caught:
            self.open_adopt(spelling)
        for needle in needles:
            self.assertIn(needle, str(caught.exception))
        self.assertEqual(before, sorted(os.listdir(self.base)))
        return caught.exception

    def test_a_real_git_with_content_and_no_workbench_is_adoptable(self):
        place = self.adoptable()
        with self.open_adopt(place) as held:
            self.assertEqual("adoptable", held.state)
            self.assertEqual(place, held.path)

    def test_a_deeper_tree_of_content_is_adoptable(self):
        place = self.adoptable()
        self.put("repo/src/pkg/mod.py", b"x = 1\n")
        with self.open_adopt(place) as held:
            self.assertEqual("adoptable", held.state)

    def test_without_adopt_the_state_is_refused_and_names_adopt(self):
        place = self.adoptable()
        error = self.refused(place, "other content", "adopt")
        self.assertIn("wb adopt", str(error))

    def test_without_adopt_other_content_without_git_does_not_name_adopt(self):
        self.make("plain")
        self.put("plain/file.txt")
        error = self.refused(self.path("plain"), "other content")
        self.assertNotIn("adopt", str(error))

    def test_content_without_git_is_refused_and_adopt_does_not_make_one(self):
        self.make("nogit")
        self.put("nogit/file.txt")
        self.refused_adopt(self.path("nogit"), "adopt", ".git")
        self.assertEqual(["file.txt"], os.listdir(self.path("nogit")))

    def test_a_git_file_or_link_is_refused(self):
        self.make("worktree")
        self.put("worktree/.git", b"gitdir: /elsewhere\n")
        self.put("worktree/file.txt")
        self.refused_adopt(self.path("worktree"), ".git is not a real directory")
        self.make("linked")
        self.make("elsewhere")
        os.symlink(self.path("elsewhere"), self.path("linked", ".git"))
        self.put("linked/file.txt")
        self.refused_adopt(self.path("linked"), ".git is not a real directory")

    def test_any_workbench_entry_is_refused(self):
        for index, kind in enumerate(("file", "empty-dir", "link", "dir-without-manifest")):
            with self.subTest(kind=kind):
                name = "wb%d" % index
                place = self.adoptable(name)
                work = self.path(name, ".workbench")
                if kind == "file":
                    self.put("%s/.workbench" % name)
                elif kind == "empty-dir":
                    os.mkdir(work)
                elif kind == "link":
                    self.make("away%d" % index)
                    os.symlink(self.path("away%d" % index), work)
                else:
                    self.put("%s/.workbench/other.txt" % name)
                self.refused_adopt(place, "refused:")

    def test_a_workbench_without_git_is_refused(self):
        self.make("lone")
        self.put("lone/.workbench/manifest.json")
        self.put("lone/file.txt")
        self.refused_adopt(self.path("lone"), "refused:")

    def test_an_unfinished_marker_is_refused_not_adopted(self):
        place = self.adoptable()
        self.put("repo/.workbench/local/incomplete", b"")
        with self.assertRaises(target.UnfinishedMarker):
            self.open_adopt(place)

    def test_an_existing_project_is_returned_as_existing(self):
        place = self.existing()
        with self.open_adopt(place) as held:
            self.assertEqual("existing", held.state)

    def test_the_other_new_states_are_returned_unchanged(self):
        self.make("empty")
        self.make("lone", ".git")
        for name, state in (("empty", "new-empty"), ("lone", "new-git"), ("later", "new-missing")):
            with self.subTest(name=name):
                with self.open_adopt(self.path(name)) as held:
                    self.assertEqual(state, held.state)

    def test_the_refused_places_are_still_refused(self):
        self.assertRaises(TargetError, self.open_adopt, "/")
        self.assertRaises(TargetError, self.open_adopt, self.home)
        self.assertRaises(TargetError, self.open_adopt, self.store)
        self.assertRaises(TargetError, self.open_adopt, self.base)

    def test_a_symbolic_link_target_is_refused(self):
        place = self.adoptable()
        os.symlink(place, self.path("alias"))
        self.refused_adopt(self.path("alias"), "symbolic link")

    def test_a_target_that_is_not_adoptable_is_not_listed_as_a_state_install_accepts(self):
        self.assertIn("adoptable", target.STATES)
        self.assertNotIn("adoptable", ("new-missing", "new-empty", "new-git"))

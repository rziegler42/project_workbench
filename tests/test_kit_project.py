"""The kit's project finder and project ID (plan `2026-10-21-module-boundary-kit`, increment C).

The finder's cases are the ones `tests/test_dispatch.py` pins through `wb code-work`; here they run
against the kit directly, on plain directories."""

import hashlib
import json
import os
import re
import tempfile
import unittest

from tests import test_manifest
from workbench import manifest
from workbench.wbkit import project

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = "11111111-2222-4333-8444-555555555555"


class Tree(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.base = os.path.realpath(holder.name)

    def make(self, *parts, git=True, manifest_text=None):
        """A project directory under the base: `.git`, and `.workbench/manifest.json` holding the text."""
        here = os.path.join(self.base, *parts)
        os.makedirs(os.path.join(here, ".workbench"))
        if git:
            os.mkdir(os.path.join(here, ".git"))
        text = manifest_text if manifest_text is not None else json.dumps({"seed": SEED})
        with open(os.path.join(here, ".workbench", "manifest.json"), "w", encoding="utf-8") as handle:
            handle.write(text)
        return here


class FindRoot(Tree):
    def test_the_project_root_and_a_subdirectory_find_the_same_root(self):
        root = self.make("p")
        sub = os.path.join(root, "a", "b")
        os.makedirs(sub)
        self.assertEqual(root, project.find_root(root))
        self.assertEqual(root, project.find_root(sub))

    def test_the_nearest_project_wins(self):
        outer = self.make("p")
        inner = self.make("p", "q")
        self.assertEqual(inner, project.find_root(inner))
        self.assertNotEqual(outer, inner)

    def test_a_directory_with_no_project_above_it_is_refused(self):
        with self.assertRaises(project.ProjectError) as caught:
            project.find_root(self.base)
        self.assertIn("not inside a workbench project", str(caught.exception))

    def test_a_manifest_without_a_git_directory_is_not_a_project(self):
        root = self.make("p", git=False)
        with self.assertRaises(project.ProjectError):
            project.find_root(root)

    def test_a_git_file_as_in_a_linked_worktree_is_not_accepted(self):
        root = self.make("p", git=False)
        with open(os.path.join(root, ".git"), "w") as handle:
            handle.write("gitdir: elsewhere\n")
        with self.assertRaises(project.ProjectError):
            project.find_root(root)

    def test_a_link_at_the_workbench_directory_is_not_followed(self):
        real = self.make("real")
        tree = os.path.join(self.base, "linked")
        os.mkdir(tree)
        os.mkdir(os.path.join(tree, ".git"))
        os.symlink(os.path.join(real, ".workbench"), os.path.join(tree, ".workbench"))
        with self.assertRaises(project.ProjectError):
            project.find_root(tree)

    def test_a_link_at_the_manifest_is_not_followed(self):
        real = self.make("real")
        tree = os.path.join(self.base, "linked")
        os.makedirs(os.path.join(tree, ".workbench"))
        os.mkdir(os.path.join(tree, ".git"))
        os.symlink(os.path.join(real, ".workbench", "manifest.json"),
                   os.path.join(tree, ".workbench", "manifest.json"))
        with self.assertRaises(project.ProjectError):
            project.find_root(tree)

    def test_a_link_at_the_git_directory_is_not_followed(self):
        real = self.make("real")
        tree = os.path.join(self.base, "linked")
        os.makedirs(os.path.join(tree, ".workbench"))
        os.symlink(os.path.join(real, ".git"), os.path.join(tree, ".git"))
        with open(os.path.join(tree, ".workbench", "manifest.json"), "w") as handle:
            handle.write("{}")
        with self.assertRaises(project.ProjectError):
            project.find_root(tree)

    def test_the_limit_is_exact_64_levels_are_searched_and_65_are_not(self):
        self.assertEqual(64, project.MAX_DEPTH)
        root = self.make("p")
        deep = root
        for _ in range(project.MAX_DEPTH - 1):
            deep = os.path.join(deep, "d")
        os.makedirs(deep)
        self.assertEqual(root, project.find_root(deep))
        deeper = os.path.join(deep, "d")
        os.mkdir(deeper)
        with self.assertRaises(project.ProjectError):
            project.find_root(deeper)

    def test_an_escape_in_the_start_directory_is_not_printed_raw(self):
        weird = os.path.join(self.base, "x\x1b[31my")
        os.mkdir(weird)
        with self.assertRaises(project.ProjectError) as caught:
            project.find_root(weird)
        self.assertIn("x", str(caught.exception))
        self.assertNotIn("\x1b", str(caught.exception))


class ProjectId(unittest.TestCase):
    def test_the_id_is_the_sha256_of_the_seed_in_lowercase_hex(self):
        value = project.project_id(SEED)
        self.assertEqual(hashlib.sha256(SEED.encode()).hexdigest(), value)
        self.assertRegex(value, r"^[0-9a-f]{64}\Z")

    def test_a_seed_that_is_not_a_plain_token_is_refused(self):
        for seed in ("", None, 5, b"abc", "a b", "a/b", "é", "a\n", "x" * 129, "\x00", "\u0663", "\uff21"):
            with self.assertRaises(project.SeedError, msg=repr(seed)):
                project.project_id(seed)
        self.assertEqual(64, len(project.project_id("x" * 128)))

    def test_a_seed_error_is_a_project_error(self):
        self.assertTrue(issubclass(project.SeedError, project.ProjectError))

    def test_the_installer_gives_the_same_id_and_the_same_refusals(self):
        for seed in (SEED, "seed-2", "x" * 128, manifest.new_seed()):
            self.assertEqual(project.project_id(seed), manifest.project_id(seed))
        for seed in ("", None, "a b", "x" * 129):
            with self.assertRaises(manifest.ManifestError) as caught:
                manifest.project_id(seed)
            with self.assertRaises(project.SeedError) as kit:
                project.project_id(seed)
            self.assertEqual(str(kit.exception), str(caught.exception))

    def test_the_installer_does_not_derive_the_id_a_second_time(self):
        with open(os.path.join(ROOT, "workbench", "manifest.py"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn("hashlib", text)
        self.assertNotIn("sha256", text)
        self.assertIsNone(re.search(r"A-Za-z0-9\._-\]\{1,128\}", text))


class ReadId(Tree):
    def refused(self, root, contains="manifest cannot be used"):
        with self.assertRaises(project.ProjectError) as caught:
            project.read_id(root)
        self.assertIn(contains, str(caught.exception))
        return str(caught.exception)

    def test_it_reads_the_seed_and_derives_the_id(self):
        root = self.make("p")
        self.assertEqual(project.project_id(SEED), project.read_id(root))

    def test_it_agrees_with_the_installer_on_every_manifest_the_manifest_tests_build(self):
        document = test_manifest.document()
        other = dict(document, seed="seed-2")
        for built in (document, other):
            text = manifest.serialize(built).decode("ascii")
            root = self.make("p%s" % built["seed"], manifest_text=text)
            self.assertEqual(manifest.project_id(manifest.parse(text.encode())["seed"]),
                             project.read_id(root))

    def test_it_does_not_validate_anything_but_the_seed(self):
        root = self.make("p", manifest_text=json.dumps({"seed": SEED, "anything": [1, 2]}))
        self.assertEqual(project.project_id(SEED), project.read_id(root))

    def test_a_missing_manifest_is_refused(self):
        self.refused(os.path.join(self.base, "nothing"))

    def test_text_that_is_not_json_is_refused(self):
        for number, text in enumerate(("", "{", "not json", "\xff", "[" * 100000)):
            self.refused(self.make("p%d" % number, manifest_text=text))

    def test_bytes_that_are_not_utf8_are_refused(self):
        root = self.make("p")
        with open(os.path.join(root, ".workbench", "manifest.json"), "wb") as handle:
            handle.write(b'{"seed": "\xff"}')
        self.refused(root)

    def test_a_manifest_that_is_not_an_object_or_has_no_usable_seed_is_refused(self):
        for number, text in enumerate(("[]", "5", "null", "{}", '{"seed": 5}', '{"seed": ""}',
                                       '{"seed": "a b"}', '{"seed": null}',
                                       json.dumps({"seed": "x" * 129}))):
            self.refused(self.make("p%d" % number, manifest_text=text))

    def test_a_manifest_that_is_a_link_is_refused(self):
        real = self.make("real")
        tree = os.path.join(self.base, "linked")
        os.makedirs(os.path.join(tree, ".workbench"))
        os.symlink(os.path.join(real, ".workbench", "manifest.json"),
                   os.path.join(tree, ".workbench", "manifest.json"))
        self.refused(tree)

    def test_a_manifest_over_the_size_limit_is_refused(self):
        root = self.make("p", manifest_text='{"seed": "%s", "pad": "%s"}' % (SEED, "x" * (17 * 1024 * 1024)))
        self.refused(root)

    def test_an_escape_in_the_failure_text_is_not_passed_on_raw(self):
        root = self.make("p\x1b[31m")
        os.unlink(os.path.join(root, ".workbench", "manifest.json"))
        self.assertNotIn("\x1b", self.refused(root))


if __name__ == "__main__":
    unittest.main()

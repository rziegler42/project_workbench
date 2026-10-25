import hashlib
import io
import json
import os
import unittest

from tests.test_install import InstallBase
from tests.test_preview import HARNESS, NOTES
from workbench import cli
from workbench.wbkit import safefs

POLICY = ({"fills": [{"slot": "slot:policy", "source": "policy.md"}]},
          {"policy.md": b"Be careful.\n"})
SEED = "11111111-2222-4333-8444-555555555555"
OWN_AGENTS = b"# Our rules\n\nSECRET-HAND-WRITTEN-TEXT\n"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class AdoptPreviewBase(InstallBase):
    def setUp(self):
        InstallBase.setUp(self)
        safefs._hook = None
        self.addCleanup(setattr, safefs, "_hook", None)

    def repo(self, name="repo", files=None):
        """A directory with its own real .git and content."""
        place = os.path.join(self.root, name)
        os.makedirs(os.path.join(place, ".git"))
        with open(os.path.join(place, ".git", "index"), "wb") as handle:
            handle.write(b"index")
        for rel, data in (files if files is not None else {"README.md": b"hello\n"}).items():
            self.put(place, rel, data)
        return place

    def put(self, place, rel, data):
        full = os.path.join(place, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data)

    def modules(self, with_policy=False):
        found = {"h": (HARNESS, {}), "notes": NOTES}
        if with_policy:
            found["policy"] = POLICY
        return found

    def good_set(self, with_policy=False):
        path = self.package(modules=self.modules(with_policy))
        self.approve(path)
        return path

    def preview(self, place, path, command="adopt", select=("h", "notes")):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", command, place, "--package", path, "--select", *select],
                        out, err, store_root=self.store_root)
        return code, out.getvalue(), err.getvalue()

    def snapshot(self, place):
        found = self.tree(place)
        contents = {}
        for rel in found:
            full = os.path.join(place, rel)
            if os.path.isfile(full) and not os.path.islink(full):
                with open(full, "rb") as handle:
                    contents[rel] = handle.read()
        return found, contents


class AdoptPreviewTest(AdoptPreviewBase):
    def test_preview_plans_an_adoption_and_writes_nothing(self):
        path = self.good_set()
        place = self.repo(files={"README.md": b"hello\n", "AGENTS.md": OWN_AGENTS})
        cli.main(["verify", path], io.StringIO(), io.StringIO(), store_root=self.store_root)
        before = (self.snapshot(place), self.tree(self.store_root))
        code, out, err = self.preview(place, path)
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(out.startswith("target: " + place + "\n"))
        self.assertIn("command: adopt\n", out)
        self.assertIn("state: adoptable\n", out)
        self.assertTrue(out.endswith("preview only: nothing was written\n"))
        self.assertNotIn("digest:", out)
        self.assertEqual(before, (self.snapshot(place), self.tree(self.store_root)))

    def test_a_seeded_file_that_exists_is_kept_with_its_own_hash(self):
        path = self.good_set()
        place = self.repo(files={"README.md": b"hello\n", "AGENTS.md": OWN_AGENTS})
        code, out, err = self.preview(place, path)
        self.assertEqual(0, code, err)
        self.assertIn("keep-file AGENTS.md [seeded] - %d bytes sha256 %s"
                      % (len(OWN_AGENTS), sha(OWN_AGENTS)), out)
        self.assertIn("create-file docs/README.md [seeded]", out)
        self.assertIn("create-file docs/notes.md [seeded]", out)
        self.assertIn("create-file .workbench/manifest.json", out)

    def test_the_content_of_an_existing_file_is_never_printed(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        code, out, err = self.preview(place, path)
        self.assertEqual(0, code, err)
        self.assertNotIn("SECRET-HAND-WRITTEN-TEXT", out + err)

    def plan_for(self, place, path, select=("h", "notes")):
        from workbench import preview, target
        with target.open_target(place, self.store_root, adopt=True) as held:
            resolved = preview.resolve_all(self.guarded, [(path, None)])
            plan, _ = preview.prepare_adopt(self.guarded, held, resolved, list(select), None,
                                            SEED, "1.0.0")
        return plan

    def test_the_manifest_and_baselines_record_a_kept_file_at_its_own_hash(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        plan = self.plan_for(place, path)
        entry = next(e for e in plan.manifest["files"] if e["path"] == "AGENTS.md")
        self.assertEqual({"class": "seeded", "hash": sha(OWN_AGENTS), "path": "AGENTS.md"}, entry)
        baselines = json.loads(dict(plan.store_writes)["projects/%s/baselines" % plan.project_id])
        self.assertEqual(sha(OWN_AGENTS), baselines["baselines"]["AGENTS.md"])
        created = next(a for a in plan.actions if a.path == "docs/README.md")
        self.assertEqual(created.hash, baselines["baselines"]["docs/README.md"])
        self.assertNotIn(".workbench/local/incomplete", baselines["baselines"])
        self.assertEqual("adopt", plan.command)
        self.assertFalse(plan.git_init)
        self.assertIsNone(plan.harness)

    def test_the_manifest_has_no_block_entry_for_a_file_that_is_kept(self):
        path = self.good_set(with_policy=True)
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        plan = self.plan_for(place, path, select=("h", "notes", "policy"))
        self.assertEqual([], [e for e in plan.manifest["files"] if "block" in e])
        self.assertEqual((("AGENTS.md", "policy", "p/policy"),), plan.not_filled)

    def test_the_digest_covers_the_bytes_of_a_kept_file(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        first = self.plan_for(place, path)
        with open(os.path.join(place, "AGENTS.md"), "wb") as handle:
            handle.write(OWN_AGENTS + b"one more line\n")
        second = self.plan_for(place, path)
        self.assertNotEqual(first.digest, second.digest)

    def test_an_existing_real_directory_is_reused(self):
        path = self.good_set()
        place = self.repo(files={"docs/guide.md": b"guide\n"})
        code, out, err = self.preview(place, path)
        self.assertEqual(0, code, err)
        self.assertIn("reuse-dir docs\n", out)
        self.assertNotIn("create-dir docs\n", out)

    def test_a_block_for_an_existing_file_is_not_filled_and_says_how_to_get_it(self):
        path = self.good_set(with_policy=True)
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        code, out, err = self.preview(place, path, select=("h", "notes", "policy"))
        self.assertEqual(0, code, err)
        self.assertIn("not filled: AGENTS.md slot:policy from p/policy; wb upgrade offers it", out)
        self.assertIn("1 not filled", out)

    def test_a_block_for_a_file_adopt_creates_is_filled(self):
        path = self.good_set(with_policy=True)
        place = self.repo()
        code, out, err = self.preview(place, path, select=("h", "notes", "policy"))
        self.assertEqual(0, code, err)
        self.assertNotIn("not filled", out)
        self.assertIn("with blocks: p/policy slot:policy", out)

    def test_it_says_adopt_does_not_attach(self):
        path = self.good_set()
        code, out, err = self.preview(self.repo(), path)
        self.assertEqual(0, code, err)
        self.assertIn("wb attach", out)
        self.assertNotIn("is attached after the install", out)
        self.assertIn("git: the existing .git is used as it is", out)
        self.assertNotIn("creates an empty repository", out)

    def test_a_target_name_with_control_characters_is_escaped(self):
        path = self.good_set()
        place = self.repo(name="re\x1b[31mpo\npwn")
        code, out, err = self.preview(place, path)
        self.assertEqual(0, code, err)
        self.assertNotIn("\x1b", out + err)
        self.assertEqual(1, sum(1 for line in out.split("\n") if line.startswith("target:")))


class AdoptConflictTest(AdoptPreviewBase):
    def refused(self, place, path, *needles, select=("h", "notes")):
        before = self.snapshot(place)
        code, out, err = self.preview(place, path, select=select)
        self.assertEqual(1, code, out)
        self.assertEqual("", out)
        for needle in needles:
            self.assertIn(needle, err)
        self.assertEqual(before, self.snapshot(place))
        return err

    def test_a_file_where_a_directory_is_planned_is_refused(self):
        path = self.good_set()
        place = self.repo(files={"docs": b"not a directory\n"})
        self.refused(place, path, "docs", "refused:")

    def test_a_directory_where_a_file_is_planned_is_refused(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md/inner.txt": b"x"})
        self.refused(place, path, "AGENTS.md")

    def test_a_link_on_a_planned_file_is_refused(self):
        path = self.good_set()
        place = self.repo()
        outside = os.path.join(self.root, "outside.txt")
        with open(outside, "wb") as handle:
            handle.write(b"outside\n")
        os.symlink(outside, os.path.join(place, "AGENTS.md"))
        self.refused(place, path, "AGENTS.md", "link")

    def test_a_link_on_a_planned_directory_is_refused(self):
        path = self.good_set()
        place = self.repo()
        elsewhere = os.path.join(self.root, "elsewhere")
        os.mkdir(elsewhere)
        os.symlink(elsewhere, os.path.join(place, "docs"))
        self.refused(place, path, "docs", "link")
        self.assertEqual([], os.listdir(elsewhere))

    def test_a_dangling_link_is_refused(self):
        path = self.good_set()
        place = self.repo()
        os.symlink(os.path.join(self.root, "nowhere"), os.path.join(place, "AGENTS.md"))
        self.refused(place, path, "AGENTS.md", "link")

    def test_every_conflict_is_listed_at_once(self):
        path = self.good_set()
        place = self.repo(files={"docs": b"file\n", "AGENTS.md/inner.txt": b"x"})
        err = self.refused(place, path, "AGENTS.md", "docs")
        self.assertGreaterEqual(err.count("refused:"), 2)

    def test_a_kept_file_that_is_too_large_is_refused(self):
        path = self.good_set()
        place = self.repo()
        with open(os.path.join(place, "AGENTS.md"), "wb") as handle:
            handle.truncate(safefs.MAX_FILE_BYTES + 1)
        self.refused(place, path, "AGENTS.md", "too large")

    def test_a_kept_file_with_two_hard_links_is_refused(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        os.link(os.path.join(place, "AGENTS.md"), os.path.join(self.root, "other-name"))
        self.refused(place, path, "AGENTS.md", "hard link")

    def test_a_kept_path_that_is_a_fifo_is_refused_without_blocking(self):
        path = self.good_set()
        place = self.repo()
        os.mkfifo(os.path.join(place, "AGENTS.md"))
        self.refused(place, path, "AGENTS.md")

    def test_a_link_planted_between_the_listing_and_the_read_is_not_followed(self):
        path = self.good_set()
        place = self.repo(files={"AGENTS.md": OWN_AGENTS})
        outside = os.path.join(self.root, "outside.txt")
        with open(outside, "wb") as handle:
            handle.write(b"OUTSIDE-SECRET\n")
        target_file = os.path.join(place, "AGENTS.md")
        swapped = []

        def swap(stage, **info):
            if stage == "projectfs_walked" and info["rel"] == "AGENTS.md" and not swapped:
                swapped.append(True)
                os.unlink(target_file)
                os.symlink(outside, target_file)

        safefs._hook = swap
        code, out, err = self.preview(place, path)
        self.assertTrue(swapped)
        self.assertEqual(1, code, out)
        self.assertNotIn("OUTSIDE-SECRET", out + err)
        self.assertNotIn(sha(b"OUTSIDE-SECRET\n"), out + err)


class AdoptStatesTest(AdoptPreviewBase):
    def test_preview_adopt_refuses_a_new_project_and_names_install(self):
        path = self.good_set()
        for state in ("missing", "empty", "git"):
            with self.subTest(state=state):
                place = self.place("new-" + state, state)
                code, out, err = self.preview(place, path)
                self.assertEqual(1, code)
                self.assertIn("wb install", err)
                self.assertFalse(os.path.exists(os.path.join(place, ".workbench")))

    def test_preview_adopt_refuses_an_existing_project_and_names_upgrade(self):
        path = self.good_set()
        place = self.place("done", "missing")
        code, out, err = self.run_install(place, path)
        self.assertEqual(0, code, err)
        code, out, err = self.preview(place, path)
        self.assertEqual(1, code)
        self.assertIn("wb upgrade", err)

    def test_preview_adopt_refuses_content_without_git(self):
        path = self.good_set()
        place = os.path.join(self.root, "plain")
        os.makedirs(place)
        self.put(place, "file.txt", b"x")
        code, out, err = self.preview(place, path)
        self.assertEqual(1, code)
        self.assertIn(".git", err)
        self.assertEqual(["file.txt"], os.listdir(place))

    def test_preview_install_refuses_an_adoptable_directory_and_names_adopt(self):
        path = self.good_set()
        place = self.repo()
        code, out, err = self.preview(place, path, command="install")
        self.assertEqual(1, code)
        self.assertIn("wb adopt", err)

    def test_install_refuses_an_adoptable_directory_and_names_adopt(self):
        path = self.good_set()
        place = self.repo()
        code, out, err = self.run_install(place, path)
        self.assertNotEqual(0, code)
        self.assertIn("adopt", err)
        self.assertFalse(os.path.exists(os.path.join(place, ".workbench")))

    def test_preview_adopt_is_listed_in_the_usage_text(self):
        err = io.StringIO()
        self.assertEqual(2, cli.main(["preview", "nonsense"], io.StringIO(), err,
                                     store_root=self.store_root))
        self.assertIn("adopt", err.getvalue())


if __name__ == "__main__":
    unittest.main()

"""An adopted project works with the other commands: ``check``, ``acknowledge``, ``upgrade`` and
``attach`` behave on it as they do on one that ``install`` wrote, and none of them changes a file the
repository already had."""

import io
import os
import unittest
import unittest.mock

from tests.test_adopt_preview import OWN_AGENTS, SEED, sha
from tests.test_check import Clone
from tests.test_install import Typist, correct
from workbench import acknowledgement, approve, cli, install, manifest, sources

README = b"# The repository\n"
FIXTURE_MD = "FIXTURE.md"


class Adopted(Clone):
    """A repository with its own history, adopted with the synthetic package's modules."""

    def setUp(self):
        Clone.setUp(self)
        terminal = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        terminal.start()
        self.addCleanup(terminal.stop)

    def ready(self, **changes):
        """The repository exists and is committed; `adopt` has run; nothing is committed after it."""
        self.pkg = self.version(**changes)
        self.approve(self.pkg)
        self.warm(self.pkg)
        os.makedirs(self.place)
        self.git("init", "-q", "--template=")
        for rel, data in (("README.md", README), ("AGENTS.md", OWN_AGENTS)):
            with open(os.path.join(self.place, rel), "wb") as handle:
                handle.write(data)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "history")
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(self.place, [(self.pkg, None)], list(self.MODULES))
        self.assertEqual(0, install.run(self.guarded, command, Typist(out, correct), out, err,
                                        seed=SEED, home=self.home, distribution=self.dist,
                                        adopt=True), (out.getvalue(), err.getvalue()))
        self.project_id = manifest.project_id(SEED)
        return self.pkg

    def run_cli(self, *argv, answer=None):
        out, err = io.StringIO(), io.StringIO()

        class Ask(io.StringIO):
            def readline(this, *a):
                if answer is not None:
                    return answer + "\n"
                digest = [x for x in out.getvalue().splitlines() if x.startswith("digest: ")][-1]
                return digest[len("digest: "):][:12] + "\n"

        code = cli.main(list(argv), out, err, store_root=self.store_root, home=self.home,
                        distribution=self.dist, stdin=Ask(""))
        return code, out.getvalue(), err.getvalue()

    def kept(self):
        return {"README.md": README, "AGENTS.md": OWN_AGENTS}

    def assert_kept(self):
        for rel, data in self.kept().items():
            self.assertEqual(data, self.read(rel), rel)


class CheckTest(Adopted):
    def test_check_passes_on_an_adopted_project_with_nothing_attached(self):
        self.ready()
        code, out, err = self.check()
        self.assertEqual(0, code, (out, err))
        self.assertEqual([], self.problems(err))
        self.assert_kept()

    def test_check_passes_after_attach(self):
        self.ready()
        self.assertEqual(0, self.attach()[0])
        code, out, err = self.check()
        self.assertEqual(0, code, (out, err))
        self.assertEqual([], self.problems(err))
        self.assert_kept()


class AcknowledgeTest(Adopted):
    def test_an_unchanged_adopted_project_has_nothing_to_acknowledge(self):
        self.ready()
        code, out, err = self.run_cli("acknowledge", self.place)
        self.assertEqual((0, "nothing to acknowledge\n", ""), (code, out, err))

    def test_an_edit_to_a_kept_file_is_listed_and_accepted_at_its_new_hash(self):
        self.ready()
        mine = OWN_AGENTS + b"One more rule.\n"
        with open(os.path.join(self.place, "AGENTS.md"), "wb") as handle:
            handle.write(mine)
        code, out, err = self.run_cli("acknowledge", self.place)
        self.assertEqual(0, code, (out, err))
        self.assertIn("changed AGENTS.md\n", out)
        baselines = acknowledgement.read_baselines(self.guarded, self.project_id)
        self.assertEqual(sha(mine), baselines["AGENTS.md"])
        self.assertEqual(mine, self.read("AGENTS.md"))


class UpgradeTest(Adopted):
    def preview_upgrade(self):
        return self.run_cli("preview", "upgrade", self.place, "--package", self.pkg)

    def test_the_preview_skips_a_kept_seeded_file_and_offers_the_unfilled_block_as_an_append(self):
        self.ready()
        before = self.snapshot_files()
        code, out, err = self.preview_upgrade()
        self.assertEqual(0, code, (out, err))
        self.assertIn("  skip AGENTS.md [seeded]", out)
        self.assertIn("  append AGENTS.md block p/a slot:policy [slot block]", out)
        self.assertNotIn("replace README.md", out)
        self.assertEqual(before, self.snapshot_files())

    def test_applying_it_adds_the_block_after_the_owners_text_and_changes_no_other_file(self):
        self.ready()
        code, out, err = self.run_cli("upgrade", self.place, "--package", self.pkg)
        self.assertEqual(0, code, (out, err))
        agents = self.read("AGENTS.md")
        self.assertTrue(agents.startswith(OWN_AGENTS), agents)
        self.assertIn(b"Rule A\n", agents[len(OWN_AGENTS):])
        self.assertEqual(README, self.read("README.md"))
        self.assertEqual(0, self.check()[0])

    def test_a_second_upgrade_has_nothing_left_to_append(self):
        self.ready()
        self.assertEqual(0, self.run_cli("upgrade", self.place, "--package", self.pkg)[0])
        code, out, err = self.preview_upgrade()
        self.assertEqual(0, code, (out, err))
        self.assertNotIn("  append ", out)
        self.assertIn("nothing to change", out)

    def test_an_owner_edit_to_a_kept_file_blocks_the_upgrade_until_it_is_acknowledged(self):
        self.ready()
        mine = OWN_AGENTS + b"Edited later.\n"
        with open(os.path.join(self.place, "AGENTS.md"), "wb") as handle:
            handle.write(mine)
        code, out, err = self.run_cli("upgrade", self.place, "--package", self.pkg)
        self.assertEqual(1, code, (out, err))
        self.assertIn("acknowledge", err)
        self.assertEqual(mine, self.read("AGENTS.md"))

    def snapshot_files(self):
        return self.content(), self.content(self.store_root)


class AttachTest(Adopted):
    def test_attach_writes_the_harness_files_and_changes_no_kept_file(self):
        self.ready()
        code, out, err = self.attach()
        self.assertEqual(0, code, (out, err))
        self.assertEqual(b"@AGENTS.md\n", self.read(FIXTURE_MD))
        self.assert_kept()

    def test_a_harness_file_that_already_has_the_same_bytes_is_left_as_it_is(self):
        self.ready()
        self.write(FIXTURE_MD, b"@AGENTS.md\n")
        code, out, err = self.attach()
        self.assertEqual(0, code, (out, err))
        self.assertEqual(b"@AGENTS.md\n", self.read(FIXTURE_MD))
        self.assert_kept()

    def test_a_harness_file_with_other_content_is_refused_by_name_and_nothing_is_written(self):
        self.ready()
        self.write(FIXTURE_MD, b"my own notes\n")
        self.refuses(contains=FIXTURE_MD)
        self.assertEqual(b"my own notes\n", self.read(FIXTURE_MD))
        self.assert_kept()


if __name__ == "__main__":
    unittest.main()

"""``approve-plan`` at the ``ask`` and ``none`` levels, and the digest its preview prints.

Plan ``2026-10-26-command-permission-levels``, increment F (``docs/specs/command-permissions.md``, "The preview and the
digest"). The project, its process module and the synthetic harness are those of ``test_delegation``; the harness is
attached so that a rendering record exists. Nothing here runs in a terminal, so a run is the remote form."""

import io
import json
import os
import re
import shutil
import unittest
import unittest.mock

from tests import support_harness, test_delegation
from tests.test_delegation import PLAN, TEXT, cli_run
from workbench import levellog, levels, planapprovals, rendering, settings

DIGEST = re.compile(r"digest: ([0-9a-f]{32})\n")


class Ask(test_delegation.Delegated):
    SETTING = False

    def setUp(self):
        super().setUp()
        # The harness describes the command gate, so a key can be relaxed at all.
        shutil.rmtree(self.dist)
        self.dist = support_harness.distribution(
            os.path.join(self.root, "distribution"), layout=support_harness.gated_layout(),
            provides=support_harness.GATED_PROVIDES)
        # The project fixture says every stream is a terminal; these commands run with none.
        none = unittest.mock.patch.object(planapprovals.approve, "is_terminal", lambda stream: False)
        none.start()
        self.addCleanup(none.stop)
        # Attach verifies the packages again; the synthetic provider provides a reserved capability as a
        # first-party module may.
        from workbench import verify
        original = verify.verify_packages
        first = unittest.mock.patch.object(
            verify, "verify_packages",
            lambda paths, *a, **k: original(paths, *a, **dict(k, first_party=list(paths))))
        first.start()
        self.addCleanup(first.stop)

    def table(self, **table):
        self.guarded.write("settings", json.dumps({"version": 2, "checkpoints": {}, "floor": [], "levels": {
            key.replace("_", "-"): level for key, level in table.items()}}).encode())

    def attached(self, **table):
        self.table(**table)
        code, out, err = self.attach()
        self.assertEqual(0, code, err)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = cli_run(self, list(argv), out, err, None)
        return code, out.getvalue(), err.getvalue()

    def preview(self):
        code, out, err = self.run_cli("plan-status", PLAN, "--digest")
        self.assertEqual((0, ""), (code, err), out)
        return DIGEST.search(out).group(1), out

    def log_lines(self):
        if self.guarded.kind(levellog.LOG) != "file":
            return []
        return self.guarded.read(levellog.LOG).decode("ascii").splitlines()

    def refused(self, *argv, contains=""):
        before = (self.stored(), self.log_lines())
        code, out, err = self.run_cli(*argv)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertEqual(before, (self.stored(), self.log_lines()))
        return err


class Preview(Ask):
    def test_the_preview_prints_a_32_character_digest_and_what_it_covers(self):
        digest, out = self.preview()
        self.assertEqual(32, len(digest))
        self.assertIn(PLAN, out)
        self.assertIn("region hash", out)

    def test_the_digest_is_the_same_twice_and_changes_with_the_plan(self):
        first, _ = self.preview()
        self.assertEqual(first, self.preview()[0])
        self.put(PLAN, TEXT.replace(b"Do it.", b"Do more."))
        self.assertNotEqual(first, self.preview()[0])

    def test_a_status_edit_does_not_change_the_digest(self):
        first, _ = self.preview()
        self.put(PLAN, TEXT.replace(b"Proposed", b"In Progress"))
        self.assertEqual(first, self.preview()[0])

    def test_the_preview_writes_nothing(self):
        before = (self.stored(), self.log_lines())
        self.preview()
        self.assertEqual(before, (self.stored(), self.log_lines()))

    def test_plan_status_without_the_option_is_unchanged(self):
        code, out, err = self.run_cli("plan-status", PLAN)
        self.assertEqual((1, "not approved: %s\n" % PLAN, ""), (code, out, err))

    def test_the_options_are_checked(self):
        for argv in (("plan-status", PLAN, "--digests"), ("plan-status", PLAN, "--digest", "x"),
                     ("plan-status", "--digest", PLAN)):
            with self.subTest(argv=argv):
                self.assertEqual(2, self.run_cli(*argv)[0])


class AtAsk(Ask):
    def setUp(self):
        super().setUp()
        self.attached(approve_plan="ask")

    def with_digest(self, digest):
        return self.run_cli("approve-plan", PLAN, "--digest", digest)

    def test_a_matching_digest_approves_and_writes_the_record_a_terminal_would(self):
        digest, _ = self.preview()
        code, out, err = self.with_digest(digest)
        self.assertEqual((0, ""), (code, err), out)
        self.assertTrue(out.startswith("approved: %s (region " % PLAN), out)
        entry, = self.recorded()
        self.assertEqual((PLAN, None), (entry.plan, entry.delegate))
        self.assertEqual(self.resolve().declaration, entry.declaration_hash)
        self.assertEqual(0, self.status()[0])

    def resolve(self):
        from workbench import approvalcmd
        return approvalcmd.resolve(self.guarded, self.real)

    def test_it_leaves_an_attempt_and_a_done_outcome(self):
        digest, _ = self.preview()
        self.with_digest(digest)
        attempt, outcome = self.log_lines()
        fields = attempt.split("\t")
        self.assertEqual(["approve-plan", "ask", "digest:" + digest], fields[3:6])
        self.assertEqual(["O", fields[1]], outcome.split("\t", 4)[:2])
        self.assertEqual("done", outcome.split("\t", 4)[3])

    def test_a_second_approval_of_the_same_plan_writes_no_entry(self):
        digest, _ = self.preview()
        self.with_digest(digest)
        before = self.log_lines()
        code, out, err = self.with_digest(digest)
        self.assertEqual((0, ""), (code, err))
        self.assertTrue(out.startswith("already approved"), out)
        self.assertEqual(before, self.log_lines())

    def test_a_wrong_digest_is_refused_and_writes_nothing(self):
        digest, _ = self.preview()
        wrong = ("0" if digest[0] != "0" else "1") + digest[1:]
        self.refused("approve-plan", PLAN, "--digest", wrong, contains="digest")

    def test_a_plan_edited_after_the_preview_is_refused(self):
        digest, _ = self.preview()
        self.put(PLAN, TEXT.replace(b"Do it.", b"Do something else."))
        self.refused("approve-plan", PLAN, "--digest", digest, contains="digest")

    def test_no_digest_is_refused_as_terminal_only(self):
        self.refused("approve-plan", PLAN, contains="owner-run")

    def test_a_malformed_digest_is_a_usage_error(self):
        for value in ("", "x", "A" * 32, "0" * 31, "0" * 33, "0" * 12):
            with self.subTest(value=value):
                self.assertEqual(2, self.run_cli("approve-plan", PLAN, "--digest", value)[0])
        self.assertEqual(2, self.run_cli("approve-plan", PLAN, "--digest")[0])
        self.assertEqual(2, self.run_cli("approve-plan", "--digest", "0" * 32, PLAN)[0])

    def test_a_missing_rendered_rule_reads_as_block_and_is_refused(self):
        digest, _ = self.preview()
        os.unlink(os.path.join(self.store_root, *(rendering.RECORD % self.project_id).split("/")))
        self.refused("approve-plan", PLAN, "--digest", digest, contains="owner-run")

    def test_a_harness_file_edited_after_attach_is_refused(self):
        digest, _ = self.preview()
        with open(os.path.join(self.real, ".fixture", "settings.local.json"), "ab") as handle:
            handle.write(b" ")
        self.refused("approve-plan", PLAN, "--digest", digest, contains="owner-run")

    def test_an_unwritable_log_refuses_and_records_no_approval(self):
        digest, _ = self.preview()
        os.mkdir(os.path.join(self.store_root, levellog.LOG))
        self.refused("approve-plan", PLAN, "--digest", digest, contains="level log")
        self.assertEqual([], self.recorded())

    def test_a_failure_after_the_attempt_writes_a_refused_outcome(self):
        digest, _ = self.preview()
        with unittest.mock.patch.object(planapprovals, "add",
                                        side_effect=planapprovals.PlanApprovalError("cannot be written")):
            code, out, err = self.with_digest(digest)
        self.assertEqual((1, ""), (code, out))
        self.assertEqual("refused", self.log_lines()[1].split("\t", 4)[3])
        self.assertEqual([], self.recorded())

    def test_an_interrupt_exits_130_and_logs_a_refused_outcome(self):
        digest, _ = self.preview()
        with unittest.mock.patch.object(planapprovals, "add", side_effect=KeyboardInterrupt):
            code, out, err = self.with_digest(digest)
        self.assertEqual(130, code)
        self.assertEqual("refused", self.log_lines()[1].split("\t", 4)[3])
        self.assertEqual([], self.recorded())

    def test_the_digest_form_at_the_wrong_level_says_what_it_needs(self):
        digest, _ = self.preview()
        os.unlink(os.path.join(self.store_root, *(rendering.RECORD % self.project_id).split("/")))
        err = self.refused("approve-plan", PLAN, "--digest", digest, contains="owner-run")
        self.assertIn("level of approve-plan is ask", err)

    def test_an_outcome_that_cannot_be_written_exits_3_with_the_approval_recorded(self):
        digest, _ = self.preview()
        with unittest.mock.patch.object(levellog, "finish", side_effect=levellog.OutcomeError("level log is full")):
            code, out, err = self.with_digest(digest)
        self.assertEqual(3, code)
        self.assertIn("level log", err)
        self.assertEqual(1, len(self.recorded()))

    def test_the_plan_changing_while_the_approval_runs_is_refused(self):
        digest, _ = self.preview()
        self.control(region={"outputs": [json.dumps({"format": 1, "region_hash": "a" * 64, "unhashed": []}) + "\n",
                                         json.dumps({"format": 1, "region_hash": "b" * 64, "unhashed": []}) + "\n"]})
        self.refused("approve-plan", PLAN, "--digest", digest, contains="digest")

    def test_the_terminal_path_is_unchanged(self):
        digest, _ = self.preview()
        out, err = io.StringIO(), io.StringIO()
        stdin = io.StringIO(digest[:12] + "\n")
        with unittest.mock.patch.object(planapprovals.approve, "is_terminal", lambda stream: True):
            code = planapprovals.approve_plan(self.guarded, [PLAN], stdin, out, err, cwd=self.real)
        self.assertEqual(1, code, out.getvalue())  # the typed text is the region hash's first 12, not the digest's
        self.assertEqual([], self.recorded())


class AtBlockAndNone(Ask):
    def test_at_block_the_remote_forms_are_refused(self):
        self.attached()
        digest, _ = self.preview()
        self.refused("approve-plan", PLAN, "--digest", digest, contains="owner-run")
        self.refused("approve-plan", PLAN, contains="owner-run")

    def test_at_none_it_runs_with_no_digest_when_the_record_shows_no_rule(self):
        self.attached(approve_plan="none")
        code, out, err = self.run_cli("approve-plan", PLAN)
        self.assertEqual((0, ""), (code, err), out)
        attempt, outcome = self.log_lines()
        fields = attempt.split("\t")
        self.assertEqual(["approve-plan", "none", ""], fields[3:6])
        self.assertEqual("done", outcome.split("\t", 4)[3])
        self.assertEqual(0, self.status()[0])

    def test_at_none_a_digest_is_refused_as_an_unknown_argument(self):
        self.attached(approve_plan="none")
        digest, _ = self.preview()
        self.refused("approve-plan", PLAN, "--digest", digest, contains="unknown argument")

    def test_at_none_with_a_table_changed_since_attach_it_is_refused(self):
        self.attached()
        self.table(approve_plan="none")
        self.refused("approve-plan", PLAN, contains="owner-run")

    def test_at_none_without_a_rendering_record_it_is_refused(self):
        self.table(approve_plan="none")
        self.refused("approve-plan", PLAN, contains="owner-run")

    def test_at_none_an_unwritable_log_refuses(self):
        self.attached(approve_plan="none")
        os.mkdir(os.path.join(self.store_root, levellog.LOG))
        self.refused("approve-plan", PLAN, contains="level log")


class OfferedLevels(Ask):
    def test_approve_plan_offers_block_delegated_ask_and_none(self):
        self.assertEqual(("block", "delegated", "ask", "none"), levels.registry()["approve-plan"].offers)

    def test_no_other_owner_run_key_offers_ask_or_none(self):
        """An agent-safe key offers `none` (increment A of 2026-10-27-a-level-for-every-command); an owner-run key still
        offers `block` only until the increment that builds it."""
        agent = set(levels.agent_keys())
        for name, key in levels.registry(checkpoints=("a", "accept-decision")).items():
            if name != "approve-plan" and name not in agent:
                self.assertEqual(("block",), key.offers, name)

    def test_the_shipped_default_is_block_until_the_probe_is_recorded(self):
        self.assertEqual("block", levels.registry()["approve-plan"].default)

    def test_a_default_of_ask_reads_ask_only_after_an_attach_rendered_the_rule(self):
        with unittest.mock.patch.dict(levels._DEFAULTS, {"approve-plan": "ask"}):
            digest, _ = self.preview()
            # No attach yet: no record, so it reads block and the remote form is refused.
            self.refused("approve-plan", PLAN, "--digest", digest, contains="owner-run")
            self.assertEqual(0, self.attach()[0])
            digest, _ = self.preview()
            code, out, err = self.run_cli("approve-plan", PLAN, "--digest", digest)
            self.assertEqual((0, ""), (code, err), out)

    def test_a_version_1_settings_file_reads_the_default(self):
        self.guarded.write("settings", json.dumps({"version": 1, "checkpoints": {}, "floor": []}).encode())
        with unittest.mock.patch.dict(levels._DEFAULTS, {"approve-plan": "ask"}):
            table = rendering.table_of(self.guarded, ("approve-plan",), ())
        self.assertEqual("ask", table["approve-plan"])


class Delegation(Ask):
    SETTING = True

    def test_delegated_approval_is_unchanged_and_still_logged(self):
        code, out, err = self.delegate(PLAN)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(2, len(self.log_lines()))


if __name__ == "__main__":
    unittest.main()

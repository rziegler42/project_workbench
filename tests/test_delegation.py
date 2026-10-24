"""``delegate-approve-plan``: a plan approved by a delegate, and how that record is read.

Plan `2026-10-23-delegated-approval`, increment D. The project, its process module and its `peer-review` provider are
synthetic: both helpers print what a control file in the project tells them to, or the value a real one would compute
from the plan, and write each call they get to a log. The installer under test knows none of what a plan or a review
holds; it runs the declared, pinned commands, validates what they print and writes one record."""

import hashlib
import io
import json
import os
import selectors
import time
import unittest
import unittest.mock

from tests import support_project
from tests.support_project import HELPER_PATH, tool
from workbench import approvalcmd, cli, gate_hook, planapprovals, rules, settings, settingscmd, verify

PLAN = "docs/plans/a.md"
TEXT = b"# A plan\nStatus: Proposed\n\n## Goal\nDo it.\n\n## Result\nNone yet.\n"
REVIEW = "plan-0123456789abcdef"
WITHDRAWN = "delegated approval withdrawn: approve-plan is not delegate"

HELPER = b'''#!/usr/bin/env python3
import hashlib, json, os, sys, time
arg = sys.argv[1]
plan = sys.argv[2] if len(sys.argv) > 2 else None
with open("calls.log", "a") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
with open("calls.log") as log:
    seen = sum(1 for line in log if line.split(" ")[0] == arg)
control = json.load(open("control.json")) if os.path.exists("control.json") else {}
mine = control.get(arg, {})
data = open(plan, "rb").read() if plan else b""
if arg == "region":
    body = b"\\n".join(line for line in data.split(b"\\n") if not line.startswith(b"Status:"))
    payload = {"format": 1, "region_hash": hashlib.sha256(body).hexdigest(), "unhashed": ["Status"]}
elif arg == "delegable":
    payload = {"format": 1, "delegable": True, "reason": "one Risks section",
               "document_sha256": hashlib.sha256(data).hexdigest()}
else:
    payload = {"format": 1, "kind": "plan", "converged": True, "document_sha256": hashlib.sha256(data).hexdigest(),
               "rounds_used": 2, "bound": 3, "bridge": "bridge-one", "model": "model-one",
               "review": "plan-0123456789abcdef", "closed": False}
payload.update(mine.get("set", {}))
for key in mine.get("drop", []):
    payload.pop(key, None)
text = json.dumps(payload) + "\\n"
if "outputs" in mine and seen <= len(mine["outputs"]):
    text = mine["outputs"][seen - 1]
if "stdout" in mine:
    text = mine["stdout"]
if "edit" in mine:
    open(plan, "wb").write(mine["edit"].encode())
if mine.get("sleep"):
    time.sleep(mine["sleep"])
sys.stdout.write(text)
if mine.get("stderr"):
    sys.stderr.write(mine["stderr"])
raise SystemExit(mine.get("exit", 0))
'''

PROCESS = {"command": "region-of", "argument": "region", "delegable": "delegable"}
CONVERGENCE = {"command": "converge", "argument": "convergence"}


def process_module(**fields):
    module, files = tool({"region-of": {"helper": HELPER_PATH, "arguments": ["region", "delegable"]}}, helper=HELPER)
    module.update(type="process", approval=PROCESS, checkpoints=["approve-plan", "other-step"])
    module.update(fields)
    return module, files


def provider_module(**fields):
    module, files = tool({"converge": {"helper": HELPER_PATH, "arguments": ["convergence", "status"]}},
                         helper=HELPER + b"# the provider's own bytes\n")
    module.update(provides=["peer-review"], convergence=CONVERGENCE)
    module.update(fields)
    return module, files


def custom(test):
    """Mark a test that installs the modules it needs by calling `use`."""
    test.custom = True
    return test


class Delegated(support_project.Project):
    """A project with a process module and a provider, and the owner's setting at `delegate`."""

    MODULES = dict(support_project.Project.MODULES, tool=process_module(), review=provider_module())
    SETTING = True

    def setUp(self):
        support_project.Project.setUp(self)
        original = verify.verify_package
        # The synthetic provider provides the capability under its core name, as a first-party module may.
        first = unittest.mock.patch.object(
            verify, "verify_package", lambda *a, **k: original(*a, **dict(k, first_party=True)))
        first.start()
        self.addCleanup(first.stop)
        if not getattr(getattr(self, self._testMethodName), "custom", False):
            self.use()

    def use(self, **modules):
        self.MODULES = dict(type(self).MODULES, **modules)
        self.ready()
        self.put(PLAN, TEXT)
        if self.SETTING:
            self.setting({"approve-plan": "delegate"})

    def setting(self, checkpoints):
        self.guarded.write("settings", json.dumps({"checkpoints": checkpoints, "floor": [], "version": 1}).encode())

    def put(self, rel, data):
        full = os.path.join(self.real, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data if isinstance(data, bytes) else data.encode())

    def control(self, **arguments):
        self.put("control.json", json.dumps(arguments))

    def calls(self):
        path = os.path.join(self.real, "calls.log")
        if not os.path.exists(path):
            return []
        with open(path) as handle:
            return [line.split() for line in handle.read().splitlines()]

    def record_file(self):
        return "projects/%s/plan-approvals" % self.project_id

    def stored(self):
        return self.guarded.read(self.record_file()) if self.guarded.kind(self.record_file()) else None

    def recorded(self):
        return planapprovals.load(self.guarded, self.project_id)

    def delegate(self, *tokens, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        code = cli_run(self, ["delegate-approve-plan"] + list(tokens), out, err, cwd)
        return code, out.getvalue(), err.getvalue()

    def refuses(self, contains, *tokens):
        before = self.stored()
        code, out, err = self.delegate(*(tokens or (PLAN,)))
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: ") and err.count("\n") == 1, err)
        self.assertIn(contains, err)
        self.assertEqual(before, self.stored())
        return err

    def approved(self):
        code, out, err = self.delegate(PLAN)
        self.assertEqual((0, ""), (code, err), out)
        return out

    def status(self, plan=PLAN):
        out, err = io.StringIO(), io.StringIO()
        code = planapprovals.plan_status(self.guarded, [plan], out, err, cwd=self.real)
        return code, out.getvalue(), err.getvalue()


def cli_run(case, argv, out, err, cwd):
    """The command as the command line routes it, from `cwd` (the project root by default)."""
    previous = os.getcwd()
    os.chdir(cwd or case.real)
    try:
        return cli.main(argv, out, err, store_root=case.store_root, distribution=case.dist)
    finally:
        os.chdir(previous)


class Recorded(Delegated):
    def test_it_records_one_delegated_approval_and_says_so(self):
        code, out, err = self.delegate(PLAN)
        self.assertEqual((0, "approved: %s (delegated, 2 of 3 rounds)\n" % PLAN, ""), (code, out, err))
        entry, = self.recorded()
        self.assertEqual(PLAN, entry.plan)
        self.assertEqual(self.resolve().declaration, entry.declaration_hash)
        self.assertEqual(self.resolve().helper_sha256, entry.helper_sha256)
        review = self.convergence()
        self.assertEqual({"provider": "review", "provider_declaration_hash": review.declaration,
                          "provider_helper_sha256": review.helper_sha256, "bridge": "bridge-one",
                          "model": "model-one", "rounds_used": 2, "bound": 3, "review": REVIEW,
                          "document_sha256": hashlib.sha256(TEXT).hexdigest()}, entry.delegate)
        self.assertEqual(2, json.loads(self.stored())["format"])

    def resolve(self):
        return approvalcmd.resolve(self.guarded, self.real)

    def convergence(self):
        return approvalcmd.resolve_delegation(self.guarded, self.real)[1]

    def test_the_record_reads_as_approved_and_changed_after_any_hashed_edit(self):
        self.approved()
        self.assertEqual((0, "approved: %s\n" % PLAN, ""), self.status())
        self.put(PLAN, TEXT.replace(b"Proposed", b"Approved"))
        self.assertEqual(0, self.status()[0])
        self.put(PLAN, TEXT.replace(b"Do it", b"Do more"))
        self.assertEqual((1, "changed since approval: %s (the plan's region)\n" % PLAN, ""), self.status())

    def test_a_second_call_writes_nothing(self):
        self.approved()
        first = self.stored()
        code, out, err = self.delegate(PLAN)
        self.assertEqual((0, "already approved: %s\n" % PLAN, ""), (code, out, err))
        self.assertEqual(first, self.stored())

    def test_an_owner_entry_for_the_same_plan_is_kept_and_nothing_is_added(self):
        resolved = self.resolve()
        report = approvalcmd.region(self.guarded, resolved, PLAN)
        planapprovals.add(self.guarded, self.project_id, planapprovals.Approval(
            PLAN, report.region_hash, resolved.declaration, resolved.helper_sha256, "owner", "2026-10-23T00:00:00Z", "1"))
        first = self.stored()
        self.assertEqual((0, "already approved: %s\n" % PLAN, ""), self.delegate(PLAN))
        self.assertEqual(first, self.stored())

    def test_the_plan_is_named_from_any_directory_inside_the_project(self):
        below = os.path.join(self.real, "docs", "plans")
        code, out, err = self.delegate("a.md", cwd=below)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(PLAN, self.recorded()[0].plan)
        self.assertEqual(0, self.delegate(os.path.join(self.real, PLAN))[0])
        self.assertEqual(1, len(self.recorded()))

    def test_it_runs_the_region_command_the_delegability_and_the_convergence_in_that_order(self):
        self.approved()
        self.assertEqual([["region", PLAN], ["delegable", PLAN], ["convergence", PLAN], ["region", PLAN]],
                         self.calls())

    def test_an_entry_that_is_not_in_the_record_afterwards_is_refused(self):
        with unittest.mock.patch.object(planapprovals, "add", lambda *args: True):
            self.refuses("could not be read back")
        self.assertIsNone(self.stored())

    def test_the_provider_s_hashes_are_its_own(self):
        self.approved()
        entry, = self.recorded()
        self.assertNotEqual(self.resolve().helper_sha256, entry.delegate["provider_helper_sha256"])
        self.assertNotEqual(self.resolve().declaration, entry.delegate["provider_declaration_hash"])

    def test_a_status_edit_after_the_approval_does_not_withdraw_it(self):
        self.approved()
        self.put(PLAN, TEXT.replace(b"Proposed", b"In Progress"))
        self.assertEqual(0, self.status()[0])

    def test_a_model_that_is_not_known_is_recorded_as_null(self):
        self.control(convergence={"set": {"model": None}})
        self.approved()
        self.assertIsNone(self.recorded()[0].delegate["model"])

    def test_a_closed_review_counts(self):
        self.control(convergence={"set": {"closed": True}})
        self.approved()


class Setting(Delegated):
    def test_each_setting_but_delegate_refuses_before_any_command_runs(self):
        for label, value in (("stop", {"approve-plan": "stop"}), ("missing", {}), ("another name", {"other-step": "delegate"}),
                             ("not a string", {"approve-plan": True}), ("a spelling", {"approve-plan": "Delegate"})):
            with self.subTest(label):
                self.setting(value)
                self.refuses("approve-plan is not set to delegate")
                self.assertEqual([], self.calls())

    def test_a_damaged_or_absent_settings_file_refuses(self):
        self.guarded.write("settings", b"{ not json")
        self.refuses("approve-plan is not set to delegate")
        os.remove(os.path.join(self.store_root, "settings"))
        self.refuses("approve-plan is not set to delegate")

    def test_a_setting_from_the_project_is_not_the_owners(self):
        self.setting({})
        for rel in ("settings", ".workbench/settings", ".workbench/settings.json", "settings.json"):
            self.put(rel, json.dumps({"checkpoints": {"approve-plan": "delegate"}, "version": 1}))
        self.refuses("approve-plan is not set to delegate")

    @custom
    def test_a_module_that_does_not_declare_the_checkpoint_refuses(self):
        self.use(tool=process_module(checkpoints=["other-step"]))
        self.refuses("approve-plan is not set to delegate")

    def test_delegate_for_another_name_has_no_effect_and_is_reported_as_stop(self):
        self.setting({"approve-plan": "delegate", "other-step": "delegate"})
        out, err = io.StringIO(), io.StringIO()
        self.assertEqual(0, settingscmd.run(self.guarded, [], out, err, cwd=self.real))
        lines = out.getvalue().splitlines()
        self.assertIn("checkpoint approve-plan: delegate", lines)
        self.assertIn("checkpoint other-step: stop", lines)
        notes = [line for line in lines if line.startswith("settings: ")]
        self.assertEqual(1, len(notes), lines)
        self.assertIn("other-step", notes[0])

    def test_delegate_for_the_one_name_has_no_note(self):
        out, err = io.StringIO(), io.StringIO()
        settingscmd.run(self.guarded, [], out, err, cwd=self.real)
        self.assertFalse([line for line in out.getvalue().splitlines() if line.startswith("settings:")])

    def test_the_effective_rule_is_the_installers_and_ignores_the_module_s_other_names(self):
        self.setting({"approve-plan": "delegate", "other-step": "delegate"})
        loaded = settings.load(self.guarded)
        got = settings.effective(loaded, ["approve-plan", "other-step"], [])
        self.assertEqual({"approve-plan": "delegate", "other-step": "stop"}, got.checkpoints)


class Resolution(Delegated):
    @custom
    def test_no_process_module_refuses(self):
        self.use(tool=support_project.tool())
        self.refuses("no installed module declares an approval command")

    @custom
    def test_a_process_module_that_declares_no_delegability_refuses(self):
        self.use(tool=process_module(approval={"command": "region-of", "argument": "region"}))
        self.refuses("declares no delegability")
        self.assertEqual([], self.calls())

    def test_two_process_modules_refuse(self):
        real = approvalcmd.installed_modules

        def doubled(start):
            root, ident, found = real(start)
            return root, ident, found + [item._replace(package="q") for item in found if item.module.approval]
        with unittest.mock.patch.object(approvalcmd, "installed_modules", doubled):
            self.refuses("more than one installed module declares an approval command")
        self.assertEqual([], self.calls())

    @custom
    def test_no_provider_refuses(self):
        self.use(review=support_project.tool())
        self.refuses("no installed module provides peer-review with a convergence argument")
        self.assertEqual([], self.calls())

    @custom
    def test_a_provider_that_declares_no_convergence_is_not_one(self):
        module, files = provider_module()
        del module["convergence"]
        self.use(review=(module, files))
        self.refuses("no installed module provides peer-review with a convergence argument")

    @custom
    def test_two_providers_refuse(self):
        module, files = provider_module()
        module["commands"] = {"converge-two": module["commands"]["converge"]}
        module["convergence"] = {"command": "converge-two", "argument": "convergence"}
        self.use(second=(module, files))
        self.refuses("more than one installed module provides peer-review with a convergence argument")

    @custom
    def test_a_provider_without_convergence_beside_the_real_one_is_ignored(self):
        module, files = provider_module()
        del module["convergence"]
        module["commands"] = {"other": module["commands"]["converge"]}
        self.use(second=(module, files))
        self.approved()

    def test_a_process_helper_edited_since_its_pin_refuses_and_runs_nothing(self):
        self.edit(self.installed("tool"), lambda data: data + b"# edited\n")
        self.refuses("")
        self.assertEqual([], self.calls())

    def test_a_provider_helper_edited_since_its_pin_refuses(self):
        self.edit(self.installed("review"), lambda data: data + b"# edited\n")
        self.refuses("")
        self.assertEqual([["region", PLAN], ["delegable", PLAN]], self.calls()[:2])

    def test_a_provider_that_is_not_pinned_refuses(self):
        self.unpin("converge")
        self.refuses("not pinned")
        self.assertEqual([], self.calls())

    def test_a_process_module_that_is_not_pinned_refuses(self):
        self.unpin("region-of")
        self.refuses("not pinned")

    def test_a_declaration_changed_since_install_refuses(self):
        self.edit(".workbench/p/review/module.json", lambda data: data.replace(b'"version": "', b'"version": "9'))
        self.refuses("")

    def test_a_provider_changed_after_the_approval_does_not_change_the_reading(self):
        self.approved()
        self.edit(self.installed("review"), lambda data: data + b"# edited\n")
        self.assertEqual((0, "approved: %s\n" % PLAN, ""), self.status())
        self.edit(".workbench/p/review/module.json", lambda data: data + b"\n")
        self.assertEqual(0, self.status()[0])


DIGEST = hashlib.sha256(TEXT).hexdigest()
GOOD = '{"format": 1, "delegable": true, "reason": "x", "document_sha256": "%s"}' % DIGEST
BAD_DELEGABLE = {
    "not json": "nothing\n",
    "two lines": GOOD + "\n{}\n",
    "no newline": GOOD,
    "an extra field": GOOD[:-1] + ', "more": 1}\n',
    "a missing field": '{"format": 1, "delegable": true, "document_sha256": "%s"}\n' % DIGEST,
    "no document hash": '{"format": 1, "delegable": true, "reason": "x"}\n',
    "a document hash in capitals": GOOD.replace(DIGEST, DIGEST.upper()) + "\n",
    "a short document hash": GOOD.replace(DIGEST, DIGEST[:63]) + "\n",
    "a document hash that is not text": GOOD.replace('"%s"' % DIGEST, "1") + "\n",
    "format 2": GOOD.replace('"format": 1', '"format": 2') + "\n",
    "format as a boolean": GOOD.replace('"format": 1', '"format": true') + "\n",
    "a string for the answer": GOOD.replace("true", '"true"') + "\n",
    "a number for the answer": GOOD.replace("true", "1") + "\n",
    "a reason that is not text": GOOD.replace('"x"', "1") + "\n",
    "a reason of 201 characters": GOOD.replace('"x"', '"%s"' % ("x" * 201)) + "\n",
    "a reason with a control character": GOOD.replace('"x"', '"a\\u0001b"') + "\n",
    "a repeated key": GOOD.replace('"delegable": true,', '"delegable": true, "delegable": true,') + "\n",
    "an array": '[1]\n',
    "more than 1,024 bytes": GOOD[:-1] + " " * 1100 + "}\n",
}


class Delegability(Delegated):
    def test_each_unusable_answer_is_no_approval(self):
        for label, text in BAD_DELEGABLE.items():
            with self.subTest(label):
                self.control(delegable={"stdout": text})
                self.refuses("delegab")
                self.assertEqual([["region", PLAN], ["delegable", PLAN]], self.calls())
                os.remove(os.path.join(self.real, "calls.log"))

    def test_an_answer_about_other_bytes_is_refused_and_nothing_is_recorded(self):
        self.control(delegable={"set": {"document_sha256": hashlib.sha256(b"other").hexdigest()}})
        self.refuses("changed while the checks ran")
        self.assertEqual([["region", PLAN], ["delegable", PLAN]], self.calls())
        self.assertEqual([], self.recorded())

    def test_a_plan_that_is_not_delegable_is_refused_with_the_reason(self):
        self.control(delegable={"set": {"delegable": False, "reason": "the Risks section lists a hard stop"}})
        err = self.refuses("is not delegable")
        self.assertIn("the Risks section lists a hard stop", err)
        self.assertEqual([["region", PLAN], ["delegable", PLAN]], self.calls())

    def test_the_reason_is_shown_cleaned(self):
        self.control(delegable={"set": {"delegable": False, "reason": "bad text \u00e9"}})
        err = self.refuses("is not delegable")
        self.assertTrue(all(" " <= char <= "~" or char == "\n" for char in err), err)

    def test_a_reason_with_a_character_that_does_not_print_is_unusable(self):
        self.control(delegable={"set": {"delegable": False, "reason": "bad \u202e text"}})
        self.refuses("delegab")

    def test_a_failing_helper_is_no_approval(self):
        for label, control in (("a non-zero exit", {"exit": 3}), ("a refusal", {"exit": 1, "stderr": "refused: odd\n"}),
                               ("an exit with output", {"exit": 2})):
            with self.subTest(label):
                self.control(delegable=control)
                self.refuses("failed")

    def test_a_helper_that_does_not_finish_is_stopped(self):
        self.control(delegable={"sleep": 5})
        with unittest.mock.patch.object(approvalcmd, "TIMEOUT", 0.5):
            self.refuses("did not finish")


BAD_CONVERGENCE = {
    "not json": "x\n",
    "two lines": "{}\n{}\n",
    "an extra field": {"set": {"extra": 1}},
    "a missing field": {"drop": ["bridge"]},
    "a missing closed": {"drop": ["closed"]},
    "format 2": {"set": {"format": 2}},
    "another kind": {"set": {"kind": "spec"}},
    "converged as text": {"set": {"converged": "true"}},
    "converged as a number": {"set": {"converged": 1}},
    "closed as text": {"set": {"closed": "no"}},
    "uppercase hash": {"set": {"document_sha256": "A" * 64}},
    "a short hash": {"set": {"document_sha256": "a" * 63}},
    "rounds zero": {"set": {"rounds_used": 0}},
    "rounds six": {"set": {"rounds_used": 6}},
    "rounds true": {"set": {"rounds_used": True}},
    "rounds text": {"set": {"rounds_used": "2"}},
    "bound zero": {"set": {"bound": 0}},
    "bound six": {"set": {"bound": 6}},
    "bound true": {"set": {"bound": True}},
    "no bridge": {"set": {"bridge": ""}},
    "a bridge of 65 characters": {"set": {"bridge": "b" * 65}},
    "a bridge that is not text": {"set": {"bridge": 1}},
    "a model that is not text": {"set": {"model": 1}},
    "a model of 201 characters": {"set": {"model": "m" * 201}},
    "a model with a control character": {"set": {"model": "a\u0001b"}},
    "a malformed review": {"set": {"review": "plan-xyz"}},
    "a review of another kind": {"set": {"review": "spec-0123456789abcdef"}},
    "an uppercase review": {"set": {"review": "plan-0123456789ABCDEF"}},
    "a review that is not text": {"set": {"review": 1}},
}


class Convergence(Delegated):
    def convergence_calls(self):
        return [["region", PLAN], ["delegable", PLAN], ["convergence", PLAN]]

    def test_each_unusable_answer_is_no_approval(self):
        for label, control in BAD_CONVERGENCE.items():
            with self.subTest(label):
                self.control(convergence={"stdout": control} if isinstance(control, str) else control)
                self.refuses("convergence")
                self.assertEqual(self.convergence_calls(), self.calls())
                os.remove(os.path.join(self.real, "calls.log"))

    def test_more_than_4096_bytes_is_no_approval(self):
        good = json.dumps({"format": 1, "kind": "plan", "converged": True, "document_sha256": hashlib.sha256(TEXT).hexdigest(),
                           "rounds_used": 2, "bound": 3, "bridge": "bridge-one", "model": None, "review": REVIEW,
                           "closed": False})
        self.control(convergence={"stdout": good[:-1] + " " * 4200 + "}\n"})
        self.refuses("more than 4096 bytes")
        self.control(convergence={"stdout": good[:-1] + " " * 100 + "}\n"})
        self.approved()

    def test_a_review_that_has_not_converged_is_refused(self):
        self.control(convergence={"set": {"converged": False}})
        self.refuses("has not converged")
        self.assertEqual(self.convergence_calls(), self.calls())

    def test_a_review_of_other_bytes_is_refused_and_says_the_file_differs(self):
        self.control(convergence={"set": {"document_sha256": "0" * 64}})
        self.refuses("differs from the one that was reviewed")

    def test_a_review_of_the_plan_before_a_later_edit_is_refused(self):
        reviewed = hashlib.sha256(TEXT).hexdigest()
        self.put(PLAN, TEXT + b"\nA late line.\n")
        self.control(convergence={"set": {"document_sha256": reviewed}})
        self.refuses("differs from the one that was reviewed")

    def test_a_failing_provider_is_no_approval(self):
        for label, control in (("a non-zero exit", {"exit": 3}), ("a refusal", {"exit": 1, "stderr": "refused: unsealed\n"})):
            with self.subTest(label):
                self.control(convergence=control)
                err = self.refuses("failed")
        self.control(convergence={"exit": 1, "stderr": "refused: the review is not sealed\n"})
        self.assertIn("the review is not sealed", self.refuses("failed"))

    def test_a_provider_that_does_not_finish_is_stopped(self):
        self.control(convergence={"sleep": 5})
        with unittest.mock.patch.object(approvalcmd, "TIMEOUT", 0.5):
            self.refuses("did not finish")


    def test_an_answer_written_just_after_an_empty_wait_is_still_read(self):
        class Preempted(selectors.DefaultSelector):
            """A parent that a loaded machine stops after a wait that found nothing, until the provider has written
            its answer and exited."""

            def select(self, timeout=None):
                ready = super().select(timeout)
                if not ready:
                    time.sleep(1.0)
                return ready

        self.control(convergence={"sleep": 0.4})
        with unittest.mock.patch.object(selectors, "DefaultSelector", Preempted):
            self.approved()


class SameBytes(Delegated):
    def test_a_plan_that_changes_while_the_provider_runs_is_refused(self):
        self.control(convergence={"edit": TEXT.decode() + "\nChanged during the review.\n"})
        self.refuses("changed while")
        self.assertIn(["convergence", PLAN], self.calls())

    def test_a_status_edit_during_the_checks_is_a_change_of_the_file_too(self):
        self.control(convergence={"edit": TEXT.decode().replace("Proposed", "Approved")})
        self.refuses("changed while")

    def test_a_region_that_differs_between_the_two_runs_is_refused(self):
        first = '{"format": 1, "region_hash": "%s", "unhashed": []}\n' % ("a" * 64)
        second = '{"format": 1, "region_hash": "%s", "unhashed": []}\n' % ("b" * 64)
        self.control(region={"outputs": [first, second]})
        self.refuses("changed while")

    def test_a_process_helper_replaced_between_the_checks_is_refused(self):
        def swap(*args, **kwargs):
            self.edit(self.installed("tool"), lambda data: data + b"# swapped\n")
            return real(*args, **kwargs)
        real = approvalcmd.convergence
        with unittest.mock.patch.object(approvalcmd, "convergence", swap):
            self.refuses("")

    def test_a_symbolic_link_swapped_in_for_the_plan_is_refused(self):
        def swap(*args, **kwargs):
            full = os.path.join(self.real, *PLAN.split("/"))
            os.rename(full, full + ".moved")
            os.symlink(full + ".moved", full)
            return real(*args, **kwargs)
        real = approvalcmd.convergence
        with unittest.mock.patch.object(approvalcmd, "convergence", swap):
            self.refuses("")


class Plans(Delegated):
    def test_a_missing_plan_is_refused(self):
        self.refuses("cannot be used", "docs/plans/none.md")

    def test_a_link_is_refused_and_nothing_runs(self):
        os.symlink(os.path.join(self.real, PLAN), os.path.join(self.real, "docs", "plans", "link.md"))
        self.refuses("link", "docs/plans/link.md")
        self.assertEqual([], self.calls())

    def test_a_plan_outside_the_project_is_refused(self):
        outside = os.path.join(os.path.dirname(self.real), "x.md")
        with open(outside, "wb") as handle:
            handle.write(TEXT)
        self.refuses("not inside the project", outside)
        self.refuses("'..'", "../x.md")

    def test_an_oversize_plan_is_refused(self):
        self.put(PLAN, TEXT + b"x" * (1024 * 1024))
        self.refuses("too large")

    def test_a_directory_is_refused(self):
        os.makedirs(os.path.join(self.real, "docs", "plans", "dir.md"))
        self.refuses("not a regular file", "docs/plans/dir.md")

    def test_an_empty_path_is_refused(self):
        self.refuses("empty", "")


class Arguments(Delegated):
    def test_usage_errors_exit_2_and_write_nothing(self):
        for tokens in ([], [PLAN, PLAN], ["--help"], ["-x"], ["--", PLAN]):
            with self.subTest(tokens):
                code, out, err = self.delegate(*tokens)
                self.assertEqual((2, ""), (code, out))
                self.assertEqual("usage: wb delegate-approve-plan <plan>\n", err)
        self.assertIsNone(self.stored())
        self.assertEqual([], self.calls())

    def test_it_is_not_owner_run_and_is_agent_safe(self):
        self.assertNotIn("delegate-approve-plan", rules.OWNER_RUN)
        self.assertIn("delegate-approve-plan", rules.AGENT_SAFE)

    def test_it_needs_no_terminal(self):
        self.assertEqual(0, self.delegate(PLAN)[0])

    def test_outside_a_project_it_refuses(self):
        outside = os.path.dirname(self.real)
        code, out, err = self.delegate(PLAN, cwd=outside)
        self.assertEqual((1, ""), (code, out))
        self.assertTrue(err.startswith("refused: "), err)

    def test_it_edits_no_plan_and_commits_nothing(self):
        def plan_bytes():
            with open(os.path.join(self.real, *PLAN.split("/")), "rb") as handle:
                return handle.read()
        before = plan_bytes()
        self.approved()
        self.assertEqual(before, plan_bytes())
        self.assertFalse(os.path.exists(os.path.join(self.real, ".git", "COMMIT_EDITMSG")))


class Reading(Delegated):
    def test_a_delegated_entry_counts_only_while_the_setting_is_delegate(self):
        self.approved()
        for label, value in (("stop", {"approve-plan": "stop"}), ("missing", {}), ("another value", {"approve-plan": "x"})):
            with self.subTest(label):
                self.setting(value)
                self.assertEqual((1, "not approved: %s (%s)\n" % (PLAN, WITHDRAWN), ""), self.status())
        self.guarded.write("settings", b"{ damaged")
        self.assertEqual((1, "not approved: %s (%s)\n" % (PLAN, WITHDRAWN), ""), self.status())
        self.setting({"approve-plan": "delegate"})
        self.assertEqual((0, "approved: %s\n" % PLAN, ""), self.status())

    def test_an_absent_settings_file_withdraws_it(self):
        self.approved()
        os.remove(os.path.join(self.store_root, "settings"))
        self.assertEqual((1, "not approved: %s (%s)\n" % (PLAN, WITHDRAWN), ""), self.status())

    def test_an_owner_entry_is_not_affected_by_the_setting(self):
        resolved = approvalcmd.resolve(self.guarded, self.real)
        report = approvalcmd.region(self.guarded, resolved, PLAN)
        planapprovals.add(self.guarded, self.project_id, planapprovals.Approval(
            PLAN, report.region_hash, resolved.declaration, resolved.helper_sha256, "owner", "2026-10-23T00:00:00Z", "1"))
        for value in ({"approve-plan": "stop"}, {}, {"approve-plan": "delegate"}):
            self.setting(value)
            self.assertEqual((0, "approved: %s\n" % PLAN, ""), self.status())

    def test_an_edit_after_the_withdrawal_reads_not_approved_without_the_reason(self):
        self.approved()
        self.setting({})
        self.put(PLAN, TEXT.replace(b"Do it", b"Do more"))
        self.assertEqual((1, "not approved: %s\n" % PLAN, ""), self.status())

    def test_the_gate_reads_a_delegated_approval_like_an_owner_s(self):
        found = approvalcmd.resolve(self.guarded, self.real)
        self.approved()
        gate_hook._approved(self.guarded, found, [PLAN], deadline=time.monotonic() + 20)
        self.setting({})
        with self.assertRaises(gate_hook.Refusal) as caught:
            gate_hook._approved(self.guarded, approvalcmd.resolve(self.guarded, self.real), [PLAN],
                                time.monotonic() + 20)
        self.assertIn(WITHDRAWN, str(caught.exception))
        self.assertIn("wb approve-plan", str(caught.exception))

    def test_the_gate_refuses_a_changed_delegated_plan_like_any_other(self):
        self.approved()
        self.put(PLAN, TEXT.replace(b"Do it", b"Do more"))
        with self.assertRaises(gate_hook.Refusal) as caught:
            gate_hook._approved(self.guarded, approvalcmd.resolve(self.guarded, self.real), [PLAN],
                                time.monotonic() + 20)
        self.assertIn("changed since approval", str(caught.exception))


FORMAT_ONE = {"plan": PLAN, "region_hash": "a" * 64, "declaration_hash": "b" * 64, "helper_sha256": "c" * 64,
              "approver": "owner", "time": "2026-10-23T00:00:00Z", "workbench_version": "1"}
DELEGATE = {"provider": "review", "provider_declaration_hash": "d" * 64, "provider_helper_sha256": "e" * 64,
            "bridge": "bridge-one", "model": "model-one", "rounds_used": 2, "bound": 3, "review": REVIEW,
            "document_sha256": "f" * 64}


def document(format=2, entry=None, **changes):
    entry = dict(FORMAT_ONE if entry is None else entry, **changes)
    return json.dumps({"format": format, "approvals": [entry]}).encode()


class Format(Delegated):
    def refused(self, data):
        with self.assertRaises(planapprovals.PlanApprovalError):
            planapprovals.parse(data)

    def test_format_one_files_are_read(self):
        entry, = planapprovals.parse(document(format=1))
        self.assertEqual(PLAN, entry.plan)
        self.assertIsNone(entry.delegate)

    def test_a_format_one_file_is_rewritten_as_format_two_when_an_approval_is_added(self):
        self.guarded.write(self.record_file(), document(format=1))
        self.approved()
        stored = json.loads(self.stored())
        self.assertEqual(2, stored["format"])
        self.assertEqual(2, len(stored["approvals"]))
        self.assertNotIn("delegate", stored["approvals"][0])

    def test_format_two_reads_an_entry_with_a_delegate_and_one_without(self):
        self.assertIsNone(planapprovals.parse(document(2))[0].delegate)
        self.assertEqual(DELEGATE, planapprovals.parse(document(2, delegate=DELEGATE))[0].delegate)
        self.assertIsNone(planapprovals.parse(document(2, delegate=dict(DELEGATE, model=None)))[0].delegate["model"])

    def test_a_delegate_in_a_format_one_file_is_refused(self):
        self.refused(document(1, delegate=DELEGATE))

    def test_other_formats_are_refused(self):
        for value in (0, 3, True, "2", None, 2.0):
            with self.subTest(value):
                self.refused(json.dumps({"format": value, "approvals": []}).encode())

    def test_a_delegate_with_the_wrong_shape_is_refused(self):
        cases = {"a missing field": {k: v for k, v in DELEGATE.items() if k != "bridge"},
                 "an extra field": dict(DELEGATE, extra=1), "not an object": "x", "null": None, "a list": [],
                 "an uppercase hash": dict(DELEGATE, document_sha256="F" * 64),
                 "a short hash": dict(DELEGATE, provider_declaration_hash="d" * 63),
                 "rounds zero": dict(DELEGATE, rounds_used=0), "rounds six": dict(DELEGATE, rounds_used=6),
                 "rounds a boolean": dict(DELEGATE, rounds_used=True), "bound six": dict(DELEGATE, bound=6),
                 "bound text": dict(DELEGATE, bound="3"), "an empty provider": dict(DELEGATE, provider=""),
                 "a long provider": dict(DELEGATE, provider="p" * 65), "an empty bridge": dict(DELEGATE, bridge=""),
                 "a long bridge": dict(DELEGATE, bridge="b" * 65), "a model that is not text": dict(DELEGATE, model=1),
                 "a long model": dict(DELEGATE, model="m" * 201),
                 "a model with a control character": dict(DELEGATE, model="a\u0001b"),
                 "a bad review": dict(DELEGATE, review="plan-xyz"), "a review of another kind": dict(DELEGATE, review="spec-" + "0" * 16)}
        for label, delegate in cases.items():
            with self.subTest(label):
                self.refused(document(2, delegate=delegate))

    def test_a_tampered_or_truncated_file_is_no_approval(self):
        self.approved()
        good = self.stored()
        for label, data in (("truncated", good[:-20]), ("empty", b""), ("a changed hash", good.replace(b'"a', b'"A', 1)),
                            ("an extra key", good.replace(b'"format": 2', b'"format": 2, "x": 1'))):
            with self.subTest(label):
                self.guarded.write(self.record_file(), data)
                code, out, err = self.status()
                self.assertEqual((1, ""), (code, out))
                self.assertTrue(err.startswith("refused: "), err)
                self.assertEqual((1, ""), self.delegate(PLAN)[:2])

    def test_the_delegate_is_ordered_in_the_file_and_the_file_is_ascii(self):
        self.control(convergence={"set": {"model": "caf\u00e9"}})
        self.approved()
        self.stored().decode("ascii")


if __name__ == "__main__":
    unittest.main()

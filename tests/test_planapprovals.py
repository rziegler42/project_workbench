"""``planapprovals``: the record, the path rules, and the commands ``approve-plan`` and ``plan-status``.

The project and its process module are synthetic. The module's helper computes a hash of the plan without its
``Status:`` line and refuses a plan that has no status line or that is oversize or holds a duplicated
``## Result`` heading; the installer under test knows none of that and only runs it."""

import io
import json
import os
import unittest
import unittest.mock

from tests import support_project
from tests.support_project import HELPER_PATH, tool
from tests.test_approvalcmd import APPROVAL, Approval
from workbench import approvalcmd, approve, cli, hashing, manifest, planapprovals

PLAN = "docs/plans/a.md"
TEXT = b"# A plan\nStatus: Proposed\n\n## Goal\nDo it.\n\n## Result\nNone yet.\n"

HELPER = b'''#!/usr/bin/env python3
import hashlib, json, sys
argument, plan = sys.argv[1], sys.argv[2]
with open(plan, "rb") as handle:
    data = handle.read()
if len(data) > 100000:
    print("refused: the plan is oversize", file=sys.stderr)
    raise SystemExit(1)
lines = data.split(b"\\n")
if sum(1 for line in lines if line.startswith(b"## Result")) > 1:
    print("refused: a duplicated heading", file=sys.stderr)
    raise SystemExit(1)
if not any(line.startswith(b"Status:") for line in lines):
    print("refused: no status line", file=sys.stderr)
    raise SystemExit(1)
region = b"\\n".join(line for line in lines if not line.startswith(b"Status:"))
print(json.dumps({"format": 1, "region_hash": hashlib.sha256(region).hexdigest(), "unhashed": ["Status"]}))
'''


class Typed(io.StringIO):
    """Standard input that types `text`, after running `before` once, as a plan swapped while the owner reads."""

    def __init__(self, text, before=None):
        super().__init__(text)
        self.before = before

    def readline(self, size=-1):
        if self.before is not None:
            before, self.before = self.before, None
            before()
        return super().readline(size)


class Planned(Approval):
    def setUp(self):
        Approval.setUp(self)
        module, files = tool({"region-of": {"helper": HELPER_PATH, "arguments": ["region"]}}, helper=HELPER)
        module.update(type="process", approval=APPROVAL)
        self.MODULES = dict(self.MODULES, tool=(module, files))
        self.ready()
        self.put(PLAN, TEXT)

    def put(self, rel, data):
        full = os.path.join(self.real, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data)

    def record_file(self):
        return "projects/%s/plan-approvals" % self.project_id

    def recorded(self):
        return planapprovals.load(self.guarded, self.project_id)

    def stored(self):
        """The bytes of the record, or None when there is none."""
        return self.guarded.read(self.record_file()) if self.guarded.kind(self.record_file()) else None

    def status(self, *tokens, cwd=None):
        out, err = io.StringIO(), io.StringIO()
        code = planapprovals.plan_status(self.guarded, list(tokens), out, err, cwd=cwd or self.real)
        return code, out.getvalue(), err.getvalue()

    def approve_plan(self, *tokens, answer=None, cwd=None, before=None):
        """Run approve-plan, typing the right prefix unless `answer` is given."""
        if answer is None:
            plan = planapprovals.plan_path(self.real, cwd or self.real, tokens[0])
            answer = approvalcmd.region(self.guarded, self.resolve(), plan).region_hash[:12]
        out, err = io.StringIO(), io.StringIO()
        code = planapprovals.approve_plan(self.guarded, list(tokens), Typed(answer + "\n", before), out, err,
                                          cwd=cwd or self.real)
        return code, out.getvalue(), err.getvalue()

    def approved(self, plan=PLAN):
        code, out, err = self.approve_plan(plan)
        self.assertEqual((0, ""), (code, err), out)

    def nothing_written(self):
        self.assertIsNone(self.stored())


class Statuses(Planned):
    def test_a_plan_with_no_record_is_not_approved(self):
        self.assertEqual((1, "not approved: %s\n" % PLAN, ""), self.status(PLAN))
        self.nothing_written()

    def test_an_approved_plan_reads_back_as_approved(self):
        self.approved()
        self.assertEqual((0, "approved: %s\n" % PLAN, ""), self.status(PLAN))
        entry, = self.recorded()
        self.assertEqual(PLAN, entry.plan)
        self.assertEqual(self.resolve().declaration, entry.declaration_hash)
        self.assertEqual(self.resolve().helper_sha256, entry.helper_sha256)

    def test_a_status_edit_keeps_it_approved_and_any_other_edit_does_not(self):
        self.approved()
        self.put(PLAN, TEXT.replace(b"Proposed", b"Approved"))
        self.assertEqual(0, self.status(PLAN)[0])
        self.put(PLAN, TEXT.replace(b"None yet", b"Done"))      # a hashed edit here; the helper decides
        code, out, _ = self.status(PLAN)
        self.assertEqual(1, code)
        self.assertEqual("changed since approval: %s (the plan's region)\n" % PLAN, out)

    def test_a_status_line_alone_is_not_an_approval(self):
        self.put(PLAN, TEXT.replace(b"Proposed", b"Approved"))
        self.assertEqual((1, "not approved: %s\n" % PLAN, ""), self.status(PLAN))

    def test_the_same_text_at_another_path_is_not_approved(self):
        self.approved()
        self.put("docs/plans/b.md", TEXT)
        self.assertEqual((1, "not approved: docs/plans/b.md\n", ""), self.status("docs/plans/b.md"))

    def test_the_same_plan_named_two_ways_has_one_record(self):
        below = os.path.join(self.real, "docs", "plans")
        code, _, err = self.approve_plan("a.md", cwd=below)
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(0, self.approve_plan(PLAN)[0])
        self.assertEqual(0, self.approve_plan(os.path.join(self.real, PLAN))[0])
        self.assertEqual(1, len(self.recorded()))
        for name, cwd in ((PLAN, self.real), ("a.md", below), ("./a.md", below),
                          (os.path.join(self.real, PLAN), below)):
            with self.subTest(name):
                self.assertEqual((0, "approved: %s\n" % PLAN, ""), self.status(name, cwd=cwd))

    def test_a_changed_approval_adds_an_entry_and_keeps_the_old_one(self):
        self.approved()
        self.put(PLAN, TEXT.replace(b"Do it.", b"Do more."))
        self.assertEqual(1, self.status(PLAN)[0])
        code, out, _ = self.approve_plan(PLAN)
        self.assertEqual(0, code)
        self.assertIn("already has 1 earlier approval", out)
        self.assertEqual(2, len(self.recorded()))
        self.assertEqual(0, self.status(PLAN)[0])
        self.put(PLAN, TEXT)                                   # back to the first text: still approved
        self.assertEqual(0, self.status(PLAN)[0])

    def test_an_identical_approval_keeps_the_first_record(self):
        self.approved()
        before = self.stored()
        code, out, _ = self.approve_plan(PLAN)
        self.assertEqual(0, code)
        self.assertIn("already approved", out)
        self.assertEqual(before, self.stored())

    def test_an_edited_helper_after_approval_is_a_change(self):
        self.approved()
        new = HELPER + b"# edited\n"
        self.edit(self.installed("tool"), lambda data: new)
        self.pin("region-of", path=self.installed("tool"), data=new)
        code, out, _ = self.status(PLAN)
        self.assertEqual((1, "changed since approval: %s (the approval command's helper)\n" % PLAN), (code, out))

    def test_an_edited_declaration_after_approval_is_a_change(self):
        self.pin("region-of", path=self.installed("tool"))      # the owner's pin stands for the whole module
        self.approved()
        self.rewrite_declaration(lambda declaration: declaration.update(description="changed"))
        code, out, _ = self.status(PLAN)
        self.assertEqual(
            (1, "changed since approval: %s (the process module's declaration)\n" % PLAN), (code, out))

    def test_what_differs_names_each_difference(self):
        then = ("1" * 64, "2" * 64, "3" * 64)
        entry = planapprovals.Approval(PLAN, *then, "o", "t", "v")
        self.assertEqual(planapprovals.APPROVED, planapprovals.status([entry], PLAN, *then).state)
        for index, label in enumerate(("region", "declaration", "helper")):
            now = tuple("9" * 64 if i == index else then[i] for i in range(3))
            found = planapprovals.status([entry], PLAN, *now)
            with self.subTest(label):
                self.assertEqual(planapprovals.CHANGED, found.state)
                self.assertEqual(1, len(found.differs))
                self.assertIn(label, found.differs[0])
        found = planapprovals.status([entry], PLAN, *("9" * 64,) * 3)
        self.assertEqual(3, len(found.differs))
        self.assertEqual(planapprovals.NOT_APPROVED, planapprovals.status([entry], "docs/plans/z.md", *then).state)


class Cancelled(Planned):
    def test_a_wrong_or_empty_answer_records_nothing(self):
        for answer in ("", "no", "0" * 12, "a" * 11, self.region().region_hash[:11]):
            with self.subTest(answer):
                code, out, _ = self.approve_plan(PLAN, answer=answer)
                self.assertEqual(1, code)
                self.assertIn("cancelled", out)
                self.nothing_written()

    def test_a_longer_answer_that_starts_right_is_not_the_prefix(self):
        full = self.region().region_hash
        self.assertEqual(1, self.approve_plan(PLAN, answer=full)[0])
        self.nothing_written()

    def test_the_owner_sees_the_path_the_command_the_hashes_and_what_is_not_covered(self):
        _, out, _ = self.approve_plan(PLAN, answer="no")
        resolved = self.resolve()
        for text in (PLAN, "p/tool", resolved.declaration[:12], resolved.helper_sha256[:12], "Status",
                     self.region().region_hash, "type the first 12 characters"):
            self.assertIn(text, out)

    def test_without_a_terminal_nothing_is_run_or_written(self):
        with unittest.mock.patch.object(approve, "is_terminal", lambda stream: False), \
                unittest.mock.patch.object(approvalcmd.launch, "launch_captured",
                                           side_effect=AssertionError("ran")):
            code, out, err = self.approve_plan(PLAN, answer="x")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("owner-run", err)
        self.nothing_written()

    def test_an_interrupt_records_nothing(self):
        out, err = io.StringIO(), io.StringIO()

        class Interrupted(io.StringIO):
            def readline(self, size=-1):
                raise KeyboardInterrupt

        code = planapprovals.approve_plan(self.guarded, [PLAN], Interrupted(), out, err, cwd=self.real)
        self.assertEqual(130, code)
        self.nothing_written()

    def test_a_plan_swapped_between_the_two_runs_yields_no_record(self):
        swap = lambda: self.put(PLAN, TEXT.replace(b"Do it.", b"Do something else."))
        code, _, err = self.approve_plan(PLAN, before=swap)
        self.assertEqual(1, code)
        self.assertIn("changed while the approval was shown", err)
        self.nothing_written()

    def test_a_helper_edited_between_the_two_runs_yields_no_record(self):
        def edit():
            self.edit(self.installed("tool"), lambda data: data + b"# edited\n")
            self.pin("region-of", path=self.installed("tool"))
        code, _, err = self.approve_plan(PLAN, before=edit)
        self.assertEqual(1, code)
        self.assertIn("changed while", err)
        self.nothing_written()


class Refused(Planned):
    def both(self, *tokens, cwd=None, contains=""):
        """Both commands refuse with nothing written and nothing on standard output."""
        code, out, err = self.status(*tokens, cwd=cwd)
        self.assertEqual((1, ""), (code, out), err)
        self.assertIn("refused: ", err)
        self.assertIn(contains, err)
        code, out, err = self.approve_plan(*tokens, answer="x" * 12, cwd=cwd)
        self.assertEqual(1, code, out)
        self.assertIn(contains, err)
        self.nothing_written()

    def test_the_path_rules(self):
        os.makedirs(os.path.join(self.real, "docs", "dir.md"))
        os.symlink(os.path.join(self.real, PLAN), os.path.join(self.real, "docs", "plans", "link.md"))
        os.symlink(os.path.join(self.real, "docs", "plans"), os.path.join(self.real, "linked"))
        outside = os.path.join(self.outside, "o.md")
        with open(outside, "wb") as handle:
            handle.write(TEXT)
        os.symlink(self.outside, os.path.join(self.real, "docs", "away"))
        cases = {
            "an empty path": ("", "empty"),
            "a NUL": ("docs/plans/a.md\0", "NUL"),
            "a ..": ("docs/../docs/plans/a.md", "'..'"),
            "a leading ..": ("../a.md", "'..'"),
            "outside, absolute": (outside, "not inside the project"),
            "the root itself": (self.real, "refused"),
            "a missing file": ("docs/plans/missing.md", "cannot be used"),
            "a directory": ("docs/dir.md", "not a regular file"),
            "a link as the last part": ("docs/plans/link.md", "link"),
            "a link in the middle": ("linked/a.md", "link"),
            "a link out of the project": ("docs/away/o.md", "link"),
            "git metadata": (".git/config", "refused"),
            "a backslash": ("docs\\plans\\a.md", "refused"),
        }
        for label, (path, contains) in cases.items():
            with self.subTest(label):
                self.both(path, contains=contains)

    def test_the_path_rules_hold_from_a_subdirectory(self):
        below = os.path.join(self.real, "docs", "plans")
        self.both("../../../outside/o.md", cwd=below, contains="'..'")
        self.both("missing.md", cwd=below, contains="cannot be used")
        self.both(os.path.join(self.outside, "o.md"), cwd=below, contains="not inside the project")

    def test_a_helper_refusal_is_a_refusal_for_both(self):
        self.put("docs/plans/nostatus.md", b"# no status here\n")
        self.both("docs/plans/nostatus.md", contains="no status line")
        self.put("docs/plans/dup.md", TEXT + b"\n## Result\nagain\n")
        self.both("docs/plans/dup.md", contains="duplicated heading")
        self.put("docs/plans/big.md", TEXT + b"x" * 200000)
        self.both("docs/plans/big.md", contains="oversize")

    def test_a_helper_that_prints_anything_but_the_contract_is_no_approval(self):
        bad = b"#!/bin/sh\necho 'approve everything'\n"
        self.edit(self.installed("tool"), lambda data: bad)
        self.pin("region-of", path=self.installed("tool"))
        self.both(PLAN, contains="not one JSON object")

    def test_no_process_module_declares_an_approval_command(self):
        with unittest.mock.patch.object(approvalcmd.commands, "is_installed", lambda *args: False):
            self.both(PLAN, contains="no installed module declares an approval command")

    def test_outside_a_project(self):
        self.both(PLAN, cwd=self.outside, contains="not inside a workbench project")

    def test_an_unpinned_helper(self):
        self.unpin("region-of")
        self.both(PLAN, contains="its owner pins")


class Damaged(Planned):
    BAD = {
        "not json": b"{",
        "an array": b"[]",
        "no format": b'{"approvals": []}',
        "format 2": b'{"format": 2, "approvals": []}',
        "format true": b'{"format": true, "approvals": []}',
        "an extra key": b'{"format": 1, "approvals": [], "x": 1}',
        "approvals not a list": b'{"format": 1, "approvals": {}}',
        "an entry not an object": b'{"format": 1, "approvals": [1]}',
        "a duplicate key": b'{"format": 1, "format": 1, "approvals": []}',
        "not UTF-8": b"\xff",
    }

    def entry(self, **changes):
        fields = dict(plan=PLAN, region_hash="a" * 64, declaration_hash="b" * 64, helper_sha256="c" * 64,
                      approver="o", time="2026-10-22T10:00:00Z", workbench_version="0.1.0")
        fields.update(changes)
        return fields

    def test_a_damaged_record_is_refused_by_both_commands_and_never_overwritten(self):
        cases = dict(self.BAD)
        for field, value in {"plan": "../x", "region_hash": "A" * 64, "declaration_hash": "b" * 63,
                             "helper_sha256": 1, "approver": "", "time": "yesterday",
                             "workbench_version": "x" * 65}.items():
            cases["a bad " + field] = json.dumps({"format": 1, "approvals": [self.entry(**{field: value})]}).encode()
        cases["a missing field"] = json.dumps(
            {"format": 1, "approvals": [{k: v for k, v in self.entry().items() if k != "time"}]}).encode()
        cases["an extra field"] = json.dumps({"format": 1, "approvals": [dict(self.entry(), x=1)]}).encode()
        cases["too many entries"] = json.dumps(
            {"format": 1, "approvals": [self.entry()] * (planapprovals.MAX_ENTRIES + 1)}).encode()
        for label, data in cases.items():
            with self.subTest(label):
                self.guarded.write(self.record_file(), data)
                code, out, err = self.status(PLAN)
                self.assertEqual((1, ""), (code, out))
                self.assertIn("refused: ", err)
                code, out, err = self.approve_plan(PLAN, answer=self.region().region_hash[:12])
                self.assertEqual(1, code)
                self.assertIn("refused: ", err)
                self.assertEqual(data, self.stored())

    def test_a_record_that_is_a_directory_is_refused(self):
        os.makedirs(os.path.join(self.store_root, *self.record_file().split("/")))
        self.assertEqual(1, self.status(PLAN)[0])
        self.assertEqual(1, self.approve_plan(PLAN, answer="x")[0])

    def test_a_full_record_takes_no_more(self):
        entries = [planapprovals.Approval(PLAN, "%064x" % n, "b" * 64, "c" * 64, "o", "2026-10-22T10:00:00Z", "v")
                   for n in range(planapprovals.MAX_ENTRIES)]
        self.guarded.write(self.record_file(), planapprovals.serialize(entries))
        before = self.stored()
        code, _, err = self.approve_plan(PLAN)
        self.assertEqual(1, code)
        self.assertIn("already holds", err)
        self.assertEqual(before, self.stored())

    def test_the_record_round_trips(self):
        entry = planapprovals.Approval(PLAN, "a" * 64, "b" * 64, "c" * 64, "o", "2026-10-22T10:00:00Z", "0.1.0")
        self.assertEqual([entry], planapprovals.parse(planapprovals.serialize([entry])))


class FromTheCommandLine(Planned):
    def run_cli(self, *argv, stdin=None):
        out, err = io.StringIO(), io.StringIO()
        before = os.getcwd()
        os.chdir(self.real)
        self.addCleanup(os.chdir, before)
        code = cli.main(list(argv), out, err, store_root=self.store_root, stdin=stdin, distribution=self.dist)
        return code, out.getvalue(), err.getvalue()

    def test_plan_status_runs_from_the_command_line(self):
        self.assertEqual((1, "not approved: %s\n" % PLAN, ""), self.run_cli("plan-status", PLAN))
        self.approved()
        self.assertEqual((0, "approved: %s\n" % PLAN, ""), self.run_cli("plan-status", PLAN))

    def test_approve_plan_runs_from_the_command_line(self):
        typed = Typed(self.region().region_hash[:12] + "\n")
        code, out, err = self.run_cli("approve-plan", PLAN, stdin=typed)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(1, len(self.recorded()))

    def test_one_argument_and_no_option(self):
        for argv in (("plan-status",), ("plan-status", PLAN, PLAN), ("plan-status", "-x"), ("plan-status", "--root"),
                     ("plan-status", ""), ("approve-plan",), ("approve-plan", PLAN, PLAN), ("approve-plan", "-x"),
                     ("approve-plan", "--yes")):
            with self.subTest(argv):
                code, out, err = self.run_cli(*argv, stdin=Typed("\n"))
                self.assertEqual(2 if argv[-1] != "" else 1, code, err)
                self.assertEqual("", out)
                self.nothing_written()

    def test_a_plan_whose_name_starts_with_a_dash_is_named_with_a_directory(self):
        self.put("docs/plans/-odd.md", TEXT)
        self.assertEqual((1, "not approved: docs/plans/-odd.md\n", ""), self.run_cli("plan-status", "./docs/plans/-odd.md"))
        self.assertEqual(2, self.run_cli("plan-status", "-odd.md")[0])
        below = os.path.join(self.real, "docs", "plans")
        code, out, _ = self.status("./-odd.md", cwd=below)
        self.assertEqual((1, "not approved: docs/plans/-odd.md\n"), (code, out))

    def test_the_helper_is_never_given_an_option_through_the_plan_path(self):
        self.put("-r/x.md", TEXT)
        with unittest.mock.patch.object(approvalcmd.launch, "launch_captured", side_effect=AssertionError("ran")):
            code, out, err = self.status("./-r/x.md")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("option", err)

    def test_the_classification_lists_the_two_commands(self):
        from workbench import rules
        self.assertIn("approve-plan", rules.OWNER_RUN)
        self.assertIn("plan-status", rules.AGENT_SAFE)
        self.assertNotIn("plan-status", rules.OWNER_RUN)


if __name__ == "__main__":
    unittest.main()

"""``gate <harness>``: the edit gate that a harness's hook runs.

The project, its process module and its helper are synthetic: the helper lists the plans whose second line says
``Approved`` or ``In Progress`` and hashes a plan without that line, and the installer under test knows neither.
The table of tools the hook covers comes from a synthetic harness layout. A control file outside the project makes the
helper misbehave."""

import hashlib
import io
import json
import os
import time
import unittest
import unittest.mock

from tests import support_harness, support_project
from tests.support_project import HELPER_PATH, tool
from workbench import approvalcmd, cli, gate_hook, planapprovals, rules

TABLE = {"Edit": ("file_path",), "Write": ("file_path",), "MultiEdit": ("file_path",),
         "NotebookEdit": ("notebook_path",)}
APPROVAL = {"command": "listing", "argument": "region", "active": "active"}
PLAN = "docs/plans/a.md"
OTHER = "docs/plans/b.md"
TEXT = "# A plan\nStatus: Approved\n\n## Goal\nDo it.\n"

HELPER = '''#!/usr/bin/env python3
import hashlib, json, os, sys, time
LOG, CONTROL = %r, %r
args = sys.argv[1:]
with open(LOG, "a") as handle:
    handle.write(json.dumps(args) + "\\n")
try:
    with open(CONTROL) as handle:
        control = json.load(handle)
except OSError:
    control = {}
if control.get("sleep"):
    time.sleep(control["sleep"])
if control.get("exit"):
    print("it failed", file=sys.stderr)
    raise SystemExit(control["exit"])
if args[0] == "active":
    if "active" in control:
        sys.stdout.write(control["active"])
        raise SystemExit(0)
    plans = []
    for name in sorted(os.listdir("docs/plans")):
        with open("docs/plans/" + name) as handle:
            status = handle.read().split("\\n")[1]
        if status.split(": ")[1] in ("Approved", "In Progress"):
            plans.append("docs/plans/" + name)
    print(json.dumps({"format": 1, "plans": plans}))
else:
    with open(args[1], "rb") as handle:
        lines = handle.read().split(b"\\n")
    body = b"\\n".join(lines[:1] + lines[2:])
    print(json.dumps({"format": 1, "region_hash": hashlib.sha256(body).hexdigest(), "unhashed": ["Status"]}))
'''


def snapshot(top):
    found = {}
    for base, dirs, files in os.walk(top):
        for name in dirs:
            found[os.path.relpath(os.path.join(base, name), top)] = "dir"
        for name in files:
            full = os.path.join(base, name)
            with open(full, "rb") as handle:
                found[os.path.relpath(full, top)] = (hashlib.sha256(handle.read()).hexdigest(),
                                                     os.stat(full).st_mtime_ns)
    return found


class Gated(support_project.Project):
    INSTALL = True

    def setUp(self):
        support_project.Project.setUp(self)
        self.log = os.path.join(self.root, "helper.log")
        self.control = os.path.join(self.root, "control.json")
        if self.INSTALL:
            self.use()

    def use(self, approval=APPROVAL):
        module, files = tool({"listing": {"helper": HELPER_PATH, "arguments": ["region", "active"]}},
                             helper=(HELPER % (self.log, self.control)).encode())
        module.update(type="process", approval=approval)
        self.MODULES = dict(support_project.Project.MODULES, tool=(module, files))
        self.ready()
        self.resolved = approvalcmd.resolve(self.guarded, self.real)

    # --- the project
    def put(self, rel, text):
        full = os.path.join(self.real, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as handle:
            handle.write(text)

    def plan(self, rel=PLAN, status="Approved"):
        self.put(rel, TEXT.replace("Approved", status))

    def record(self, rel=PLAN):
        report = approvalcmd.region(self.guarded, self.resolved, rel)
        planapprovals.add(self.guarded, self.project_id, planapprovals.Approval(
            rel, report.region_hash, self.resolved.declaration, self.resolved.helper_sha256, "owner",
            "2026-10-22T00:00:00Z", "test"))

    def misbehave(self, **control):
        with open(self.control, "w") as handle:
            json.dump(control, handle)

    def helper_log_reset(self):
        if os.path.exists(self.log):
            os.remove(self.log)

    def helper_calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as handle:
            return [json.loads(line) for line in handle]

    # --- the call
    def path(self, rel):
        return os.path.join(self.real, *rel.split("/"))

    def payload(self, tool_name="Edit", cwd=None, **tool_input):
        return json.dumps({"hook_event_name": "PreToolUse", "cwd": cwd or self.real, "tool_name": tool_name,
                           "tool_input": tool_input})

    def gate(self, text, table=TABLE, deadline=gate_hook.DEADLINE, stdin=None):
        err = io.StringIO()
        code = gate_hook.run(stdin or io.StringIO(text), err, lambda: (self.guarded, table), deadline=deadline)
        return code, err.getvalue()

    def target(self, rel, tool_name="Edit", **kwargs):
        field = "notebook_path" if tool_name == "NotebookEdit" else "file_path"
        return self.gate(self.payload(tool_name, **{field: rel if rel.startswith("/") else self.path(rel)}),
                         **kwargs)

    def allowed(self, result):
        self.assertEqual((0, ""), result)

    def refused(self, result, contains=""):
        code, err = result
        self.assertEqual(2, code, err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertEqual(1, err.count("\n"), err)
        self.assertIn(contains, err)
        return err


class Decisions(Gated):
    def test_no_plan_under_way_allows_any_edit(self):
        self.plan(status="Proposed")
        self.allowed(self.target("src/x.py"))
        self.assertEqual([["active"]], self.helper_calls())

    def test_an_approved_plan_under_way_allows_an_edit(self):
        self.plan()
        self.record()
        self.allowed(self.target("src/x.py"))

    def test_an_unapproved_plan_under_way_refuses_an_edit_and_names_the_plan_and_the_command(self):
        self.plan()
        err = self.refused(self.target("src/x.py"), PLAN)
        self.assertIn("not approved", err)
        self.assertIn("wb approve-plan", err)

    def test_a_plan_changed_since_approval_refuses(self):
        self.plan()
        self.record()
        self.put(PLAN, TEXT + "More.\n")
        self.assertIn("changed since approval", self.refused(self.target("src/x.py"), PLAN))

    def test_a_status_edit_does_not_make_an_approval_stale(self):
        self.plan()
        self.record()
        self.plan(status="In Progress")
        self.allowed(self.target("src/x.py"))

    def test_the_plan_itself_may_be_written_even_when_it_is_not_approved(self):
        self.plan()
        self.allowed(self.target(PLAN))
        self.assertEqual([["active"]], self.helper_calls())

    def test_another_plan_is_not_the_plan_under_way(self):
        self.plan()
        self.plan(OTHER, status="Proposed")
        self.refused(self.target(OTHER), PLAN)

    def test_a_target_outside_the_root_passes(self):
        self.plan()
        self.allowed(self.target(os.path.join(self.outside, "x.py")))
        self.allowed(self.target("/etc/hosts"))
        self.allowed(self.target(os.path.join(os.path.dirname(self.real), "proj-sibling", "x")))

    def test_every_plan_under_way_must_be_approved_and_the_first_that_is_not_stops_the_check(self):
        self.plan()
        self.plan(OTHER)
        self.record(PLAN)
        self.helper_log_reset()
        self.refused(self.target("src/x.py"), OTHER)
        self.assertEqual([["active"], ["region", PLAN], ["region", OTHER]], self.helper_calls())
        self.record(OTHER)
        self.helper_log_reset()
        self.allowed(self.target("src/x.py"))
        self.assertEqual([["active"], ["region", PLAN], ["region", OTHER]], self.helper_calls())

    def test_the_first_plan_that_is_not_approved_ends_the_check(self):
        self.plan()
        self.plan(OTHER)
        self.record(OTHER)
        self.helper_log_reset()
        self.refused(self.target("src/x.py"), PLAN)
        self.assertEqual([["active"], ["region", PLAN]], self.helper_calls())

    def test_the_helper_is_run_with_the_declared_arguments_only(self):
        self.plan()
        self.record()
        self.helper_log_reset()
        self.allowed(self.target("src/x.py"))
        self.assertEqual([["active"], ["region", PLAN]], self.helper_calls())


class WithoutAnActiveCommand(Gated):
    INSTALL = False

    def test_a_module_that_declares_approval_without_active_is_allowed(self):
        self.use(approval={"command": "listing", "argument": "region"})
        self.plan()
        self.allowed(self.target("src/x.py"))
        self.assertEqual([], self.helper_calls())

    def test_a_project_with_no_process_module_is_allowed(self):
        self.ready()
        self.plan()
        self.allowed(self.target("src/x.py"))


class Tools(Gated):
    def setUp(self):
        Gated.setUp(self)
        self.plan()
        self.record()

    def test_each_tool_is_read_by_its_own_field(self):
        for name, field in (("Edit", "file_path"), ("Write", "file_path"), ("MultiEdit", "file_path"),
                            ("NotebookEdit", "notebook_path")):
            with self.subTest(name):
                self.allowed(self.gate(self.payload(name, **{field: self.path("src/x.py")})))
                self.refused(self.gate(self.payload(name)), "no %s" % field)
                self.refused(self.gate(self.payload(name, **{field: ""})), field)
                self.refused(self.gate(self.payload(name, **{field: 7})), field)
                self.refused(self.gate(self.payload(name, **{field: [self.path("x")]})), field)

    def test_the_other_tools_field_is_not_read(self):
        self.refused(self.gate(self.payload("NotebookEdit", file_path=self.path("src/x.py"))), "notebook_path")
        self.refused(self.gate(self.payload("Edit", notebook_path=self.path("src/x.py"))), "file_path")

    def test_a_tool_outside_the_table_is_refused_when_a_plan_is_under_way(self):
        self.refused(self.gate(self.payload("Bash", command="rm -r x")), "Bash")

    def test_a_tool_outside_the_table_is_allowed_when_no_plan_is_under_way(self):
        self.plan(status="Proposed")
        self.allowed(self.gate(self.payload("Bash", command="ls")))

    def test_a_call_with_several_targets_passes_only_when_every_target_does(self):
        table = {"Pair": ("one", "two")}
        self.plan(OTHER, status="Proposed")  # never under way
        self.plan(PLAN, status="Approved")
        self.put(PLAN, TEXT + "edited after approval\n")
        outside, inside = os.path.join(self.outside, "x"), self.path("src/x.py")
        self.allowed(self.gate(self.payload("Pair", one=outside, two=outside), table=table))
        self.refused(self.gate(self.payload("Pair", one=outside, two=inside), table=table), PLAN)
        self.refused(self.gate(self.payload("Pair", one=inside, two=outside), table=table), PLAN)
        self.refused(self.gate(self.payload("Pair", one=outside), table=table), "two")
        self.allowed(self.gate(self.payload("Pair", one=self.path(PLAN), two=outside), table=table))
        self.refused(self.gate(self.payload("Pair", one=self.path(PLAN), two=inside), table=table), PLAN)


class Placing(Gated):
    def setUp(self):
        Gated.setUp(self)
        self.plan()  # under way and not approved: every inside target is refused

    def test_a_relative_target_is_placed_against_the_working_directory(self):
        os.makedirs(os.path.join(self.real, "sub", "deep"))
        below = os.path.join(self.real, "sub")
        self.refused(self.gate(self.payload(file_path="x.py", cwd=below)), PLAN)
        self.refused(self.gate(self.payload(file_path="deep/x.py", cwd=below)), PLAN)
        self.refused(self.gate(self.payload(file_path="../x.py", cwd=below)), PLAN)
        self.allowed(self.gate(self.payload(file_path="../../x.py", cwd=below)))
        self.allowed(self.gate(self.payload(file_path=os.path.join(self.outside, "x"), cwd=below)))

    def test_dot_and_dot_dot_are_folded_lexically(self):
        self.allowed(self.target(self.real + "/docs/../../elsewhere/x"))
        self.refused(self.target(self.real + "/docs/../src/./x.py"), PLAN)
        self.refused(self.target(self.real + "//src///x.py"), PLAN)
        self.allowed(self.target(self.outside + "/../outside/x"))

    def test_a_path_that_climbs_out_and_back_in_is_inside(self):
        self.refused(self.target(self.real + "/../" + os.path.basename(self.real) + "/src/x.py"), PLAN)

    def test_the_root_itself_is_a_target_that_needs_approval(self):
        self.refused(self.target(self.real), PLAN)

    def test_case_and_unicode_variants_of_the_root_are_inside(self):
        self.refused(self.target(self.real.upper() + "/src/x.py"), PLAN)
        self.refused(self.target(self.real.swapcase() + "/src/x.py"), PLAN)

    def test_the_same_plan_spelled_in_another_case_is_refused_not_passed(self):
        self.refused(self.target("docs/plans/A.md"), "another way")
        self.refused(self.target("DOCS/plans/a.md"), "another way")

    def test_a_directory_named_like_a_prefix_of_the_root_is_outside(self):
        self.allowed(self.target(self.real + "-sibling/x"))

    def test_a_link_in_any_existing_component_of_an_inside_target_is_refused(self):
        os.makedirs(os.path.join(self.real, "real"))
        os.symlink(os.path.join(self.real, "real"), os.path.join(self.real, "inner"))
        os.symlink(self.outside, os.path.join(self.real, "out"))
        os.symlink(os.path.join(self.real, PLAN), os.path.join(self.real, "docs", "alias.md"))
        for rel in ("inner/x.py", "inner", "out/x.py", "out/deeper/x.py", "docs/alias.md"):
            with self.subTest(rel):
                self.refused(self.target(rel), "symbolic link")

    def test_a_target_spelled_through_an_alias_of_the_root_is_judged_where_it_lands(self):
        alias = os.path.join(self.outside, "alias")
        os.symlink(self.real, alias)
        os.symlink(os.path.join(self.real, "src"), os.path.join(self.outside, "src-alias"))
        for spelled in (alias + "/src/x.py", alias + "/x.py", alias, alias + "/new/dir/x.py",
                        alias + "/docs/../src/x.py", self.outside + "/src-alias/x.py"):
            with self.subTest(spelled):
                self.refused(self.target(spelled), PLAN)
        self.refused(self.gate(self.payload(file_path="../%s/alias/src/x.py" % os.path.basename(self.outside))), PLAN)

    def test_a_target_through_an_alias_that_lands_outside_or_on_the_plan_is_judged_there(self):
        os.symlink(self.outside, os.path.join(self.outside, "self"))
        self.allowed(self.target(self.outside + "/self/x"))
        alias = os.path.join(self.outside, "alias")
        os.symlink(self.real, alias)
        self.allowed(self.target(alias + "/docs/plans/a.md"))
        self.refused(self.target(alias + "/docs/plans/A.md"), "another way")

    def test_a_target_through_a_link_loop_is_refused(self):
        os.symlink(os.path.join(self.outside, "b"), os.path.join(self.outside, "a"))
        os.symlink(os.path.join(self.outside, "a"), os.path.join(self.outside, "b"))
        self.refused(self.target(self.outside + "/a/x"))

    def test_a_link_to_a_plan_is_not_the_plan(self):
        os.symlink(os.path.join(self.real, PLAN), os.path.join(self.real, "plan-link.md"))
        self.refused(self.target("plan-link.md"), "symbolic link")

    def test_a_dot_dot_after_a_link_is_refused(self):
        os.symlink(os.path.join(self.real, "docs"), os.path.join(self.real, "jump"))
        self.refused(self.target(self.real + "/jump/../src/x.py"), "'..'")
        os.symlink(os.path.join(self.real, "docs", "plans"), os.path.join(self.outside, "link-in"))
        self.refused(self.target(self.outside + "/link-in/../x"), "'..'")

    def test_a_component_that_does_not_exist_ends_the_link_check(self):
        self.refused(self.target("new/dir/never/x.py"), PLAN)

    def test_a_working_directory_that_is_not_plain_is_refused(self):
        for cwd in ("", "relative", self.real + "/", self.real + "/./docs", self.real + "/docs/..",
                    self.real + "//docs", "\0"):
            with self.subTest(cwd):
                self.refused(self.gate(self.payload(file_path="x", cwd=cwd)))

    def test_a_working_directory_outside_any_project_is_refused(self):
        self.refused(self.gate(self.payload(file_path="/x", cwd=self.outside)), "not inside a workbench project")

    def test_a_nul_and_an_overlong_path_are_refused(self):
        self.refused(self.target(self.real + "/src/x\0.py"), "NUL")
        self.refused(self.target(self.real + "/" + "a" * gate_hook.MAX_TARGET), "longer than")
        self.refused(self.target("x" * (gate_hook.MAX_TARGET + 1)), "longer than")

    def test_a_path_with_unusual_text_is_judged_not_trusted(self):
        for rel in ("src/-rf", "src/a b", "src/é.py", "src/é.py", "src/‮.py", "src/*", "src/$(x)"):
            with self.subTest(rel):
                self.refused(self.target(rel), PLAN)


class Hostile(Gated):
    def setUp(self):
        Gated.setUp(self)
        self.plan()
        self.record()

    def test_input_that_is_not_one_json_object_is_refused(self):
        for text in ("", "{", "[]", "null", '"x"', "7", '{"cwd": "/x"} {"cwd": "/x"}', '{"cwd": 1}garbage',
                     self.payload(file_path="/x") + "\n{}", '{"cwd": "%s", "cwd": "%s", "tool_name": "Edit", '
                     '"tool_input": {}}' % (self.real, self.real), "﻿" + self.payload(file_path="/x"),
                     '{"cwd": "%s", "tool_name": "Edit", "tool_input": {"file_path": "/x", "n": 1.5}}' % self.real,
                     '{"cwd": "%s", "tool_name": "Edit", "tool_input": {"file_path": "/x", "n": NaN}}' % self.real):
            with self.subTest(text[:40]):
                self.refused(self.gate(text))

    def test_the_fields_must_have_their_types(self):
        for cwd, name, given in ((7, "Edit", {}), (None, "Edit", {}), (self.real, 7, {}), (self.real, None, {}),
                                 (self.real, "Edit", []), (self.real, "Edit", "x"), (self.real, "Edit", None)):
            with self.subTest((cwd, name, given)):
                self.refused(self.gate(json.dumps({"cwd": cwd, "tool_name": name, "tool_input": given})))
        for missing in ("cwd", "tool_name", "tool_input"):
            document = {"cwd": self.real, "tool_name": "Edit", "tool_input": {"file_path": "/x"}}
            del document[missing]
            with self.subTest(missing):
                self.refused(self.gate(json.dumps(document)), missing if missing != "cwd" else "string cwd")

    def test_input_over_the_bound_is_refused_and_input_at_it_is_read(self):
        padding = {"content": "x" * (gate_hook.MAX_INPUT)}
        self.refused(self.gate(self.payload(file_path="/x", **padding)), "65536")
        head = self.payload(file_path=os.path.join(self.outside, "x"), content="")
        room = gate_hook.MAX_INPUT - len(head.encode())
        text = self.payload(file_path=os.path.join(self.outside, "x"), content="y" * room)
        self.assertEqual(gate_hook.MAX_INPUT, len(text.encode()))
        self.allowed(self.gate(text))
        self.refused(self.gate(text.replace('"y', '"yy', 1)), "65536")

    def test_input_nested_too_deeply_is_refused(self):
        text = '{"cwd": "%s", "tool_name": "Edit", "tool_input": {"file_path": "/x", "z": %s}}' % (
            self.real, "[" * 40 + "]" * 40)
        self.refused(self.gate(text))
        self.refused(self.gate('{"a":' * 5000 + "1" + "}" * 5000))

    def test_input_that_is_not_utf8_is_refused(self):
        class Bytes:
            buffer = io.BytesIO(b'{"cwd": "\xff"}')
        self.refused(self.gate("", stdin=Bytes()))

    def test_extra_fields_are_ignored(self):
        text = json.dumps({"cwd": self.real, "tool_name": "Edit", "session_id": "s", "permission_mode": "plan",
                           "tool_input": {"file_path": os.path.join(self.outside, "x"), "old_string": "a",
                                          "new_string": "b", "replace_all": False, "n": 3}})
        self.allowed(self.gate(text))

    def test_a_helper_that_fails_is_a_refusal(self):
        self.misbehave(exit=1)
        self.refused(self.target("src/x.py"), "failed")
        self.misbehave(exit=2)
        self.refused(self.target("src/x.py"), "failed")

    def test_a_helper_that_prints_something_else_is_a_refusal(self):
        paths = ["docs/plans/%s.md" % n for n in range(33)]
        for reply in ("", "\n", "{}\n", '{"format": 1, "plans": []}', '{"format": 1, "plans": []}\n{}\n',
                      '{"format": 1, "plans": [], "extra": 1}\n', '{"format": 2, "plans": []}\n',
                      '{"format": true, "plans": []}\n', '{"format": 1, "plans": "docs/plans/a.md"}\n',
                      json.dumps({"format": 1, "plans": paths}) + "\n",
                      '{"format": 1, "plans": ["docs/plans/a.md", "docs/plans/a.md"]}\n',
                      '{"format": 1, "plans": [7]}\n', '{"format": 1, "plans": [""]}\n',
                      '{"format": 1, "plans": ["../a.md"]}\n', '{"format": 1, "plans": ["/etc/passwd"]}\n',
                      '{"format": 1, "plans": ["-r.md"]}\n', '{"format": 1, "plans": ["a\\u0000b"]}\n',
                      '{"format": 1, "plans": ["%s"]}\n' % ("a" * 241), '{"format": 1, "plans": [1.5]}\n',
                      '[1]\n', 'null\n', "x" * 9000):
            self.misbehave(active=reply)
            with self.subTest(reply[:50]):
                self.refused(self.target("src/x.py"))
        self.misbehave(active='{"format": 1, "plans": []}\n')
        self.allowed(self.target("src/x.py"))

    def test_a_forged_listing_cannot_name_a_plan_that_is_a_link_or_missing(self):
        self.misbehave(active='{"format": 1, "plans": ["docs/plans/ghost.md"]}\n')
        self.refused(self.target("src/x.py"), "ghost.md")
        os.symlink(os.path.join(self.real, PLAN), os.path.join(self.real, "docs", "plans", "link.md"))
        self.misbehave(active='{"format": 1, "plans": ["docs/plans/link.md"]}\n')
        self.refused(self.target("src/x.py"), "link")

    def test_a_helper_that_hangs_is_stopped_at_the_deadline(self):
        self.misbehave(sleep=30)
        started = time.monotonic()
        self.refused(self.target("src/x.py", deadline=1.5), "")
        self.assertLess(time.monotonic() - started, 8)

    def test_input_that_never_ends_is_stopped_at_the_deadline(self):
        read, write = os.pipe()
        self.addCleanup(os.close, write)
        reader = os.fdopen(read, "rb")
        self.addCleanup(reader.close)
        started = time.monotonic()
        self.refused(self.gate("", stdin=reader, deadline=1.0), "within 1 seconds")
        self.assertLess(time.monotonic() - started, 5)

    def test_a_deadline_that_has_passed_before_the_helper_is_asked_is_a_refusal(self):
        with unittest.mock.patch.object(gate_hook.time, "monotonic", side_effect=[0.0, 100.0, 100.0, 100.0, 100.0]):
            self.refused(self.target("src/x.py"))

    def test_an_unexpected_failure_is_a_refusal_with_one_line(self):
        with unittest.mock.patch.object(approvalcmd, "installed_modules", side_effect=RuntimeError("boom")):
            err = self.refused(self.target("src/x.py"), "RuntimeError")
        self.assertNotIn("boom", err)

    def test_an_unpinned_helper_is_a_refusal(self):
        self.unpin()
        self.refused(self.target("src/x.py"), "not pinned")

    def test_a_declaration_changed_since_install_is_a_refusal(self):
        def change(data):
            document = json.loads(data)
            document["description"] = "changed after the install"
            return json.dumps(document).encode()

        self.edit(".workbench/p/tool/module.json", change)
        self.refused(self.target("src/x.py"), "changed since")

    def test_a_damaged_plan_record_is_a_refusal_and_is_not_overwritten(self):
        name = "projects/%s/plan-approvals" % self.project_id
        self.guarded.write(name, b"not json")
        self.refused(self.target("src/x.py"))
        self.assertEqual(b"not json", self.guarded.read(name))

    def test_a_refusal_prints_one_line_and_nothing_on_standard_output(self):
        self.misbehave(exit=1)
        out, err = io.StringIO(), io.StringIO()
        with unittest.mock.patch("sys.stdout", out):
            code = gate_hook.run(io.StringIO(self.payload(file_path=self.path("x"))), err,
                                 lambda: (self.guarded, TABLE))
        self.assertEqual((2, ""), (code, out.getvalue()))
        self.assertEqual(1, err.getvalue().count("\n"))


class Writes(Gated):
    def test_nothing_is_written_in_the_project_or_the_store_by_any_decision(self):
        self.plan()
        self.plan(OTHER, status="Proposed")
        self.record()
        cases = [self.payload(file_path=self.path("src/x.py")), self.payload(file_path=self.path(PLAN)),
                 self.payload(file_path="/elsewhere/x"), self.payload("Bash", command="x"), "{", ""]
        self.gate(cases[0])  # the launcher makes its private copy of the helper on the first run
        before = snapshot(self.real), snapshot(self.store_root)
        for text in cases:
            self.gate(text)
        self.assertEqual(before, (snapshot(self.real), snapshot(self.store_root)))

    def test_a_refusal_changes_nothing_either(self):
        self.plan()
        self.refused(self.target("src/x.py"))  # the launcher makes its private copy of the helper on the first run
        before = snapshot(self.real), snapshot(self.store_root)
        self.refused(self.target("src/x.py"))
        self.assertEqual(before, (snapshot(self.real), snapshot(self.store_root)))


class FromTheCommandLine(Gated):
    def setUp(self):
        Gated.setUp(self)
        layout = json.loads(json.dumps(support_harness.SYNTHETIC))
        layout["hooks"] = {"settings_key": "hooks", "targets": {name: list(fields) for name, fields in TABLE.items()}}
        self.gate_dist = support_harness.distribution(os.path.join(self.root, "gate-distribution"), layout)

    def cli(self, *argv, stdin="", distribution=None):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(list(argv), out, err, store_root=self.store_root, stdin=io.StringIO(stdin),
                        distribution=distribution or self.gate_dist)
        return code, out.getvalue(), err.getvalue()

    def test_it_allows_with_no_output(self):
        self.plan(status="Proposed")
        self.assertEqual((0, "", ""), self.cli("gate", support_harness.MODULE,
                                               stdin=self.payload(file_path=self.path("x"))))

    def test_it_refuses_with_exit_2_one_line_and_no_standard_output(self):
        self.plan()
        code, out, err = self.cli("gate", support_harness.MODULE, stdin=self.payload(file_path=self.path("x")))
        self.assertEqual((2, ""), (code, out))
        self.assertTrue(err.startswith("refused: "), err)
        self.assertEqual(1, err.count("\n"), err)

    def test_it_reads_the_table_from_the_harness_layout(self):
        self.plan()
        self.cli("gate", support_harness.MODULE, stdin="")  # warm the launcher for this distribution
        code, _, err = self.cli("gate", support_harness.MODULE, stdin=self.payload("Bash", command="x"))
        self.assertEqual(2, code)
        self.assertIn("Bash", err)

    def test_a_harness_with_no_hook_table_or_no_such_harness_is_refused(self):
        self.plan(status="Proposed")
        for name in (support_harness.MODULE, "nosuch"):
            with self.subTest(name):
                code, out, err = self.cli("gate", name, stdin=self.payload(file_path="/x"), distribution=self.dist)
                self.assertEqual((2, ""), (code, out))
                self.assertIn("not a known harness", err)

    def test_the_arguments(self):
        for argv in (("gate",), ("gate", "a", "b"), ("gate", ""), ("gate", "--help"), ("gate", "-x"), ("gate", "A"),
                     ("gate", "../x"), ("gate", "a b")):
            with self.subTest(argv):
                code, out, err = self.cli(*argv, stdin=self.payload(file_path="/x"))
                self.assertEqual((2, ""), (code, out))
                self.assertEqual(gate_hook.USAGE, err)

    def test_a_store_that_cannot_be_used_is_a_refusal_with_exit_2(self):
        broken = os.path.join(self.root, "not-a-store")
        with open(broken, "w") as handle:
            handle.write("x")
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["gate", support_harness.MODULE], out, err, store_root=broken,
                        stdin=io.StringIO(self.payload(file_path="/x")), distribution=self.gate_dist)
        self.assertEqual((2, ""), (code, out.getvalue()))
        self.assertEqual(1, err.getvalue().count("\n"))
        self.assertTrue(err.getvalue().startswith("refused: "))

    def test_a_store_without_settings_gains_only_the_seeded_file(self):
        self.plan(status="Proposed")
        self.cli("gate", support_harness.MODULE, stdin=self.payload(file_path="/x"))
        os.remove(os.path.join(self.store_root, "settings"))
        before, project = snapshot(self.store_root), snapshot(self.real)
        self.assertEqual(0, self.cli("gate", support_harness.MODULE, stdin=self.payload(file_path="/x"))[0])
        after = snapshot(self.store_root)
        self.assertEqual({"settings"}, set(after) - set(before))
        self.assertEqual(before, {key: after[key] for key in before})
        self.assertEqual(project, snapshot(self.real))

    def test_the_command_is_classified_as_read_only(self):
        self.assertIn("gate", rules.AGENT_SAFE)
        self.assertNotIn("gate", rules.OWNER_RUN)


if __name__ == "__main__":
    unittest.main()

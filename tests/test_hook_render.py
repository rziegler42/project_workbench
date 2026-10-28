"""The edit gate hook the installer renders into a harness's per-clone settings file.

The layout, the harness and the process module are synthetic: the installer names none of them. The rendered hook is
fixed by the layout (the event, the tools, the time limit and the blocking exit code) and by the harness's name."""

import hashlib
import io
import json
import os
import subprocess
import unittest
import unittest.mock

from tests import support_harness, support_project, test_gate_hook
from tests.support_project import HELPER_PATH, tool
from workbench import cli, harnessplan

TABLE = {"Edit": ["file_path"], "Write": ["file_path"], "MultiEdit": ["file_path"],
         "NotebookEdit": ["notebook_path"]}
HOOKS = {"settings_key": "hooks", "targets": TABLE, "event": "PreToolUse", "timeout": 20, "block_code": 2}
SETTINGS = support_harness.SYNTHETIC["local_settings"]["path"]
NAME = support_harness.MODULE
ROOT = "/work/project"


def hooked(**changes):
    document = json.loads(json.dumps(support_harness.SYNTHETIC))
    document["hooks"] = dict(HOOKS, **changes)
    return document


def render(document=None, name=NAME, **kwargs):
    kwargs.setdefault("root", ROOT)
    return json.loads(harnessplan.render_permissions(
        [], document or hooked(), "/store", "/home/u", hook_for=name, **kwargs))


class Rendered(unittest.TestCase):
    def test_the_entry_is_the_layouts_event_matcher_command_and_time_limit(self):
        self.assertEqual({"PreToolUse": [{
            "matcher": "Edit|MultiEdit|NotebookEdit|Write",
            "hooks": [{"type": "command", "command": "wb gate fixture || exit 2", "timeout": 20}]}]},
            render()["hooks"])

    def test_the_values_come_from_the_layout(self):
        entry = render(hooked(event="Before", timeout=7, block_code=9, targets={"Zed": ["a"], "Alpha": ["b"]}))
        self.assertEqual({"Before": [{"matcher": "Alpha|Zed", "hooks": [
            {"type": "command", "command": "wb gate fixture || exit 9", "timeout": 7}]}]}, entry["hooks"])

    def test_the_key_is_the_layouts_settings_key(self):
        document = render(hooked(settings_key="lifecycle"))
        self.assertIn("lifecycle", document)
        self.assertNotIn("hooks", document)

    def test_the_hook_and_the_rules_are_in_one_document(self):
        document = render()
        self.assertEqual(["ask", "deny"], sorted(document["permissions"]))
        self.assertIn("hooks", document)

    def test_it_is_the_same_bytes_every_time(self):
        first = harnessplan.render_permissions([], hooked(), "/store", "/home/u", hook_for=NAME, root=ROOT)
        second = harnessplan.render_permissions([], hooked(), "/store", "/home/u", hook_for=NAME, root=ROOT)
        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))

    def test_without_a_harness_name_nothing_changes(self):
        plain = harnessplan.render_permissions([], hooked(), "/store", "/home/u")
        self.assertNotIn(b"hooks", plain)
        self.assertEqual(plain, harnessplan.render_permissions([], hooked(), "/store", "/home/u", hook_for=None))

    def test_a_layout_without_a_whole_description_cannot_render_one(self):
        for changes in ({"event": None}, {"timeout": None}, {"block_code": None}, {"targets": None}):
            document = hooked()
            for key, value in changes.items():
                del document["hooks"][key]
            with self.subTest(changes), self.assertRaises(harnessplan.PlanError) as caught:
                harnessplan.render_permissions([], document, "/store", "/home/u", hook_for=NAME, root=ROOT)
            self.assertIn("hook", str(caught.exception))

    def test_a_layout_with_no_hooks_cannot_render_one(self):
        with self.assertRaises(harnessplan.PlanError):
            harnessplan.render_permissions([], support_harness.SYNTHETIC, "/store", "/home/u", hook_for=NAME,
                                           root=ROOT)

    def test_a_harness_name_the_gate_would_refuse_is_not_rendered(self):
        for name in ("", "A", "a b", "-a", "a;b", "a$(x)", "a|b", "a\nb", "x" * 65, "../x", "a'b"):
            with self.subTest(name), self.assertRaises(harnessplan.PlanError):
                render(name=name)

    def test_the_layout_that_is_refused_is_not_rendered(self):
        with self.assertRaises(harnessplan.PlanError):
            render(hooked(timeout=0))


AGENTS = (".fixture/agents/checker.md", ".fixture/agents/writer.md")


def protecting(protect=AGENTS, **kwargs):
    kwargs.setdefault("root", ROOT)
    return json.loads(harnessplan.render_permissions([], hooked(), "/store", "/home/u", protect=protect, **kwargs))


def only(document, text):
    return sorted(rule for rule in document["permissions"]["deny"] if text in rule)


class ProtectedAgents(unittest.TestCase):
    """The deny of the files that carry a confined agent's hook: the same three spellings as the settings file."""

    def test_each_file_is_denied_relative_from_any_directory_and_by_its_absolute_path(self):
        found = only(protecting(), "/agents/")
        wanted = []
        for path in AGENTS:
            wanted += ["Edit(%s)" % path, "Edit(**/%s)" % path, "Edit(/%s/%s)" % (ROOT, path)]
        self.assertEqual(sorted(wanted), found)

    def test_it_needs_no_edit_gate_hook(self):
        document = protecting()
        self.assertNotIn("hooks", document)
        self.assertEqual(6, len(only(document, "/agents/")))

    def test_with_the_edit_gate_hook_both_denies_are_there(self):
        document = protecting(hook_for=NAME)
        self.assertIn("hooks", document)
        self.assertIn("Edit(%s)" % SETTINGS, document["permissions"]["deny"])
        self.assertEqual(6, len(only(document, "/agents/")))

    def test_nothing_protected_leaves_the_bytes_as_they_were(self):
        before = harnessplan.render_permissions([], hooked(), "/store", "/home/u", hook_for=NAME, root=ROOT)
        after = harnessplan.render_permissions([], hooked(), "/store", "/home/u", hook_for=NAME, root=ROOT, protect=())
        self.assertEqual(before, after)

    def test_a_file_is_denied_whether_or_not_it_is_also_asked_about(self):
        document = protecting()
        self.assertEqual([], [rule for rule in document["permissions"]["ask"] if "/agents/" in rule])

    def test_without_a_root_it_cannot_be_rendered(self):
        with self.assertRaises(harnessplan.PlanError) as caught:
            harnessplan.render_permissions([], hooked(), "/store", "/home/u", protect=AGENTS)
        self.assertIn("project", str(caught.exception))

    def test_a_path_that_is_not_a_plain_relative_file_is_refused(self):
        for path in ("", "/abs/agent.md", "../x.md", ".fixture/../x.md", ".fixture//x.md", ".fixture/./x.md",
                     ".fixture/*.md", ".fixture/a(b).md", ".fixture/a\nb.md", "~/x.md", None, 7):
            with self.subTest(path), self.assertRaises(harnessplan.PlanError):
                protecting(protect=(path,))

    def test_it_is_the_same_bytes_every_time(self):
        first = harnessplan.render_permissions([], hooked(), "/store", "/home/u", root=ROOT, protect=AGENTS)
        second = harnessplan.render_permissions([], hooked(), "/store", "/home/u", root=ROOT, protect=tuple(reversed(AGENTS)))
        self.assertEqual(first, second)


class Protected(unittest.TestCase):
    """The deny of the settings file and the git exclude file: one separate hunk, so it can be dropped alone."""

    def test_the_hook_comes_with_a_deny_for_the_settings_file_and_the_exclude_file(self):
        deny = render()["permissions"]["deny"]
        for path in (SETTINGS, ".git/info/exclude"):
            self.assertIn("Edit(%s)" % path, deny)
            self.assertIn("Edit(**/%s)" % path, deny)

    def test_no_hook_no_such_deny(self):
        plain = json.loads(harnessplan.render_permissions([], hooked(), "/store", "/home/u"))
        self.assertEqual([], [rule for rule in plain["permissions"]["deny"] if "exclude" in rule or "settings" in rule])

    def test_a_root_without_a_hook_adds_nothing(self):
        plain = json.loads(harnessplan.render_permissions([], hooked(), "/store", "/home/u", root=ROOT))
        self.assertEqual([], [rule for rule in plain["permissions"]["deny"] if "exclude" in rule or "settings" in rule])

    def test_the_two_files_are_also_denied_by_their_absolute_path_in_the_project(self):
        deny = render()["permissions"]["deny"]
        for path in (SETTINGS, ".git/info/exclude"):
            self.assertIn("Edit(/%s/%s)" % (ROOT, path), deny)

    def test_the_deny_is_exactly_the_four_relative_and_the_two_absolute_patterns(self):
        deny = render()["permissions"]["deny"]
        found = sorted(rule for rule in deny if "exclude" in rule or "settings" in rule)
        wanted = sorted(["Edit(%s)" % SETTINGS, "Edit(**/%s)" % SETTINGS, "Edit(/%s/%s)" % (ROOT, SETTINGS),
                         "Edit(.git/info/exclude)", "Edit(**/.git/info/exclude)",
                         "Edit(/%s/.git/info/exclude)" % ROOT])
        self.assertEqual(wanted, found)

    def test_a_root_with_a_space_is_spelled_as_it_is(self):
        deny = render(root="/work/my project")["permissions"]["deny"]
        self.assertIn("Edit(//work/my project/%s)" % SETTINGS, deny)

    def test_a_root_that_cannot_be_a_rule_is_refused_and_named(self):
        for root in ("/work/a(b)", "/work/a*b", "/work/a'b", "/work/a\\b", "/work/a\nb", "/work/caf\u00e9",
                     "/work/a[b]", "/work/a:b"):
            with self.subTest(root), self.assertRaises(harnessplan.PlanError) as caught:
                render(root=root)
            self.assertIn("permission rule", str(caught.exception))

    def test_a_root_that_is_not_a_plain_absolute_path_is_refused(self):
        for root in ("", "/", "work", "./work", "/work/../x", "/work/./x", "/work//x", None, 7, b"/work"):
            with self.subTest(root), self.assertRaises(harnessplan.PlanError):
                render(root=root)

    def test_a_hook_cannot_be_rendered_without_a_root(self):
        with self.assertRaises(harnessplan.PlanError) as caught:
            harnessplan.render_permissions([], hooked(), "/store", "/home/u", hook_for=NAME)
        self.assertIn("project", str(caught.exception))

    def test_no_pattern_is_a_glob_built_from_the_root(self):
        for rule in render()["permissions"]["deny"]:
            if ROOT in rule:
                self.assertNotIn("*", rule)

    def test_the_deny_is_one_function_and_one_call(self):
        with open(harnessplan.__file__, encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual(1, text.count("def _protected("))
        self.assertEqual(2, text.count("_protected("))


def distribution(path, layout, provides):
    """A distribution whose synthetic harness module provides `provides`."""
    with unittest.mock.patch.object(support_harness, "PROVIDES", list(provides)):
        return support_harness.distribution(path, layout)


class Attached(test_gate_hook.Gated):
    """A project with a process module, in a real git repository, then the synthetic harness attached to it."""

    INSTALL = False

    def use(self, approval=test_gate_hook.APPROVAL, extra=None):
        """The project with the process module; `approval` None leaves the field out; `extra` adds modules."""
        module, files = tool({"listing": {"helper": HELPER_PATH, "arguments": ["region", "active"]}},
                             helper=(test_gate_hook.HELPER % (self.log, self.control)).encode())
        module["type"] = "process"
        if approval is not None:
            module["approval"] = approval
        self.MODULES = dict(support_project.Project.MODULES, tool=(module, files), **(extra or {}))
        self.ready()

    def setUp(self):
        test_gate_hook.Gated.setUp(self)
        self.hook_dist = distribution(os.path.join(self.root, "hook-distribution"), hooked(),
                                      support_harness.PROVIDES + ["hooks"])
        self.hook_package = os.path.join(self.hook_dist, "packages", support_harness.PACKAGE)

    def ready(self, **changes):
        package = test_gate_hook.Gated.ready(self, **changes)
        os.unlink(os.path.join(self.place, ".git", "index"))
        self.git("init", "-q", "--template=")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "install")
        return package

    def git(self, *args):
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.test",
                               "-c", "commit.gpgsign=false", "-c", "gc.auto=0", "-c", "maintenance.auto=false"]
                              + list(args), cwd=self.place, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(0, done.returncode, done.stderr)
        return done.stdout

    def attach_hooked(self, *args, **kwargs):
        kwargs.setdefault("dist", self.hook_dist)
        kwargs.setdefault("package", self.hook_package)
        return self.attach(*args, **kwargs)

    def settings(self):
        return json.loads(self.read(SETTINGS))

    def check(self, dist=None):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["check", self.place], out, err, store_root=self.store_root, home=self.home,
                        distribution=dist or self.hook_dist)
        return code, out.getvalue(), err.getvalue()

    def test_the_hook_and_the_rules_are_written_together(self):
        self.use()
        code, out, err = self.attach_hooked()
        self.assertEqual(0, code, err)
        document = self.settings()
        self.assertEqual("wb gate fixture || exit 2",
                         document["hooks"]["PreToolUse"][0]["hooks"][0]["command"])
        self.assertIn("deny", document["permissions"])

    def test_the_deny_names_the_two_files_by_the_real_path_of_the_project(self):
        self.use()
        self.assertEqual(0, self.attach_hooked()[0])
        deny = self.settings()["permissions"]["deny"]
        real = os.path.realpath(self.place)
        for path in (SETTINGS, ".git/info/exclude"):
            self.assertIn("Edit(/%s/%s)" % (real, path), deny)
            self.assertIn("Edit(%s)" % path, deny)

    def test_the_local_manifest_is_denied_in_the_three_spellings(self):
        self.use()
        self.assertEqual(0, self.attach_hooked()[0])
        deny = self.settings()["permissions"]["deny"]
        path = ".workbench/local/harness.json"
        for rule in ("Edit(%s)" % path, "Edit(**/%s)" % path, "Edit(/%s/%s)" % (os.path.realpath(self.place), path)):
            self.assertIn(rule, deny)

    def test_the_local_manifest_is_denied_without_a_hook_too(self):
        self.use(approval=None)
        self.assertEqual(0, self.attach_hooked()[0])
        deny = self.settings()["permissions"]["deny"]
        self.assertIn("Edit(.workbench/local/harness.json)", deny)
        self.assertEqual([], [rule for rule in deny if "exclude" in rule])

    def test_the_local_manifest_records_the_hash_of_the_file_with_the_hook(self):
        self.use()
        self.assertEqual(0, self.attach_hooked()[0])
        entry = next(f for f in self.planned()["files"] if f["path"] == SETTINGS)
        self.assertEqual(hashlib.sha256(self.read(SETTINGS)).hexdigest(), entry["hash"])

    def test_a_second_attach_is_byte_identical(self):
        self.use()
        self.assertEqual(0, self.attach_hooked()[0])
        first, before = self.read(SETTINGS), self.content()
        self.attach_hooked()
        self.assertEqual(first, self.read(SETTINGS))
        self.assertEqual(before, self.content())

    def test_a_hook_is_never_rendered_for_a_project_with_no_process_module_that_declares_approval(self):
        self.use(approval=None)
        self.assertEqual(0, self.attach_hooked()[0])
        self.assertNotIn("hooks", self.settings())
        self.assertEqual([], [rule for rule in self.settings()["permissions"]["deny"] if "exclude" in rule])

    def test_nor_for_an_approval_that_lists_no_plans_under_way(self):
        self.use(approval={"command": "listing", "argument": "region"})
        self.assertEqual(0, self.attach_hooked()[0])
        self.assertNotIn("hooks", self.settings())

    def test_a_layout_with_no_hook_renders_none_and_attach_says_so(self):
        self.use()
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertNotIn("hooks", self.settings())
        self.assertIn("warning: this harness renders no edit gate hook", err)

    def test_a_layout_that_describes_a_hook_but_a_module_that_does_not_provide_hooks_renders_none(self):
        self.use()
        dist = distribution(os.path.join(self.root, "quiet"), hooked(), support_harness.PROVIDES)
        code, out, err = self.attach(dist=dist, package=os.path.join(dist, "packages", support_harness.PACKAGE))
        self.assertEqual(0, code, err)
        self.assertNotIn("hooks", self.settings())
        self.assertIn("warning: this harness renders no edit gate hook", err)

    def test_a_module_that_provides_hooks_but_not_permissions_says_it_renders_no_hook(self):
        self.use()
        provides = [name for name in support_harness.PROVIDES if name != "permissions"] + ["hooks"]
        dist = distribution(os.path.join(self.root, "nopermissions"), hooked(), provides)
        code, out, err = self.attach(dist=dist, package=os.path.join(dist, "packages", support_harness.PACKAGE))
        self.assertEqual(0, code, err)
        self.assertIn("renders no edit gate hook", err)
        self.assertFalse(os.path.exists(os.path.join(self.place, *SETTINGS.split("/"))))

    def test_a_module_that_provides_hooks_needs_a_layout_that_describes_one(self):
        self.use()
        dist = distribution(os.path.join(self.root, "lying"), support_harness.SYNTHETIC,
                            support_harness.PROVIDES + ["hooks"])
        code, out, err = self.attach(dist=dist, package=os.path.join(dist, "packages", support_harness.PACKAGE))
        self.assertEqual(1, code)
        self.assertIn("hook", err)
        self.assertFalse(os.path.exists(os.path.join(self.place, *SETTINGS.split("/"))))

    def test_an_item_that_needs_hooks_is_still_skipped_when_the_harness_provides_them(self):
        """A hook has no neutral form, so providing the installer's own hook does not supply an item's."""
        hooked_skill = b"---\nname: hooked\ndescription: Needs hooks\nneeds: hooks\n---\nBody.\n"
        self.use(extra={"notes": ({}, {"harness/neutral/skills/hooked/SKILL.md": hooked_skill})})
        code, out, err = self.attach_hooked()
        self.assertEqual(0, code, err)
        self.assertFalse(os.path.exists(os.path.join(self.place, ".fixture", "skills", "hooked")))
        self.assertIn("needs hooks", err)

    def test_an_edited_hook_is_reported_by_check(self):
        self.use()
        self.assertEqual(0, self.attach_hooked()[0])
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)
        document = self.settings()
        document["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = "true"
        with open(os.path.join(self.place, *SETTINGS.split("/")), "w") as handle:
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: %s: differs from what attach wrote" % SETTINGS, err)


if __name__ == "__main__":
    unittest.main()

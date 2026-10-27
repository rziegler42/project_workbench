"""``wb preview rerender``: the plan of re-rendering an attached harness, read only.

Plan ``2026-10-27-rerender-attached-harness``, increment A (``docs/specs/harness-rerender.md``). The project, its process
module and the synthetic harness, which describes the command gate so that a key can be relaxed, are those of
``test_approve_levels``; the harness is attached with the table in force and the table is then changed."""

import io
import json
import os
import re
import unittest
import unittest.mock

from tests.test_approve_levels import Ask
from workbench import attach, cli, levels, rerender, rules

SETTINGS = ".fixture/settings.local.json"
LOCAL = ".workbench/local/harness.json"
DIGEST = re.compile(r"^digest: ([0-9a-f]{64})$", re.M)


class Base(Ask):
    def levels(self, **table):
        self.guarded.write("settings", json.dumps({"version": 2, "checkpoints": {}, "floor": [], "levels": {
            key.replace("_", " ") if key.startswith("wb_") else key: level for key, level in table.items()}}).encode())

    def snapshot(self):
        return (self.content(), self.content(self.store_root))

    def preview(self, *tokens, place=None, packages=None, dist=None):
        argv = ["preview", "rerender"] + ([place or self.place] if place != "" else [])
        for given in (packages if packages is not None else [self.pkg, self.synth]):
            argv += ["--package", given]
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(argv + list(tokens), out, err, store_root=self.store_root, home=self.home,
                        distribution=dist or self.dist)
        return code, out.getvalue(), err.getvalue()

    def shown(self, *tokens, **kwargs):
        before = self.snapshot()
        code, out, err = self.preview(*tokens, **kwargs)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(before, self.snapshot(), "a preview wrote something")
        return out

    def refuses(self, contains, *tokens, **kwargs):
        before = self.snapshot()
        code, out, err = self.preview(*tokens, **kwargs)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertEqual(before, self.snapshot(), "a refused preview wrote something")
        return err

    def live(self):
        with open(os.path.join(self.place, *SETTINGS.split("/")), "rb") as handle:
            return json.loads(handle.read())

    def edit_live(self, change):
        document = self.live()
        change(document)
        with open(os.path.join(self.place, *SETTINGS.split("/")), "wb") as handle:
            handle.write((json.dumps(document, indent=2, sort_keys=True) + "\n").encode())


class Plan(Base):
    def setUp(self):
        super().setUp()
        self.attached()

    def test_the_project_is_printed_first(self):
        out = self.shown()
        self.assertTrue(out.startswith("project: %s\n" % os.path.realpath(self.place)), out)

    def test_an_unchanged_table_says_nothing_changes_and_writes_nothing(self):
        out = self.shown()
        self.assertIn("nothing to change\n", out)
        self.assertNotIn("->", out)

    def test_a_key_moved_in_the_table_is_listed_with_its_old_and_new_rule(self):
        self.levels(wb_install="none")
        out = self.shown()
        self.assertIn("wb install: deny -> none\n", out)
        self.assertNotIn("nothing to change", out)

    def test_a_table_set_back_to_what_was_rendered_is_unchanged(self):
        self.levels(wb_install="none")
        self.assertNotIn("nothing to change", self.shown())
        self.levels(wb_install="block")
        self.assertIn("nothing to change\n", self.shown())

    def test_the_files_a_re_render_replaces_are_listed_with_their_hashes(self):
        self.levels(wb_install="none")
        out = self.shown()
        self.assertRegex(out, r"(?m)^  %s: [0-9a-f]{12} -> [0-9a-f]{12}$" % re.escape(SETTINGS))
        self.assertRegex(out, r"(?m)^  %s: [0-9a-f]{12} -> [0-9a-f]{12}$" % re.escape(LOCAL))
        self.assertRegex(out, r"(?m)^  rendering record \(guarded store\): [0-9a-f]{12} -> [0-9a-f]{12}$")

    def test_a_file_a_run_would_leave_as_it_is_is_marked(self):
        out = self.shown()
        for name in (SETTINGS, LOCAL):
            self.assertIn("  %s: left as it is\n" % name, out)

    def test_the_digest_is_stable_and_changes_with_the_table(self):
        first = DIGEST.search(self.shown()).group(1)
        self.assertEqual(first, DIGEST.search(self.shown()).group(1))
        self.levels(wb_install="none")
        self.assertNotEqual(first, DIGEST.search(self.shown()).group(1))

    def test_an_allow_rule_the_owner_added_is_kept_and_listed(self):
        self.edit_live(lambda doc: doc["permissions"].__setitem__("allow", ["Bash(ls)"]))
        out = self.shown()
        self.assertIn("kept: Bash(ls)\n", out)
        self.assertNotIn("nothing to change", out)

    def test_an_entry_the_new_file_will_not_have_is_listed_as_removed(self):
        self.edit_live(lambda doc: doc.__setitem__("extra", "x"))
        out = self.shown()
        self.assertIn('removed: extra = "x"\n', out)

    def test_the_digest_covers_the_kept_and_removed_entries(self):
        first = DIGEST.search(self.shown()).group(1)
        self.edit_live(lambda doc: doc["permissions"].__setitem__("allow", ["Bash(ls)"]))
        second = DIGEST.search(self.shown()).group(1)
        self.edit_live(lambda doc: doc.__setitem__("extra", "x"))
        third = DIGEST.search(self.shown()).group(1)
        self.assertEqual(3, len({first, second, third}))

    def test_the_inputs_the_staging_read_are_summarized(self):
        out = self.shown()
        self.assertRegex(out, r"(?m)^inputs: \d+ packages, \d+ modules, harness \S+ \S+$")

    def test_a_changed_staged_input_that_leaves_the_rendered_file_the_same_changes_the_digest(self):
        first = DIGEST.search(self.shown()).group(1)
        real = attach.stage

        def stage(*args, **kwargs):
            done = real(*args, **kwargs)
            return done._replace(inputs=done.inputs + (("module", "p", "m", "a" * 64, "d" * 64),))

        with unittest.mock.patch.object(attach, "stage", stage):
            out = self.shown()
        self.assertNotEqual(first, DIGEST.search(out).group(1))
        self.assertIn("nothing to change", out)

    def test_a_long_allow_rule_and_a_long_removed_entry_are_shown_whole(self):
        long_rule = "Bash(" + "x" * 400 + ")"
        self.edit_live(lambda doc: doc["permissions"].__setitem__("allow", [long_rule]))
        self.edit_live(lambda doc: doc.__setitem__("extra", "y" * 400))
        out = self.shown()
        self.assertIn("kept: %s\n" % long_rule, out)
        self.assertIn('removed: extra = "%s"\n' % ("y" * 400), out)

    def test_a_rule_other_than_deny_and_none_is_listed_with_its_old_and_new_rule(self):
        self.levels(**{"approve-plan": "ask"})
        code, out, err = self.preview()
        self.assertEqual(0, code, err)
        self.assertRegex(out, r"(?m)^  approve-plan: \w+ -> ask$")

    def test_a_non_string_allow_item_is_removed_not_kept(self):
        self.edit_live(lambda doc: doc["permissions"].__setitem__("allow", ["Bash(ls)", 7, {"a": 1}]))
        out = self.shown()
        self.assertIn("kept: Bash(ls)\n", out)
        self.assertEqual(["kept: Bash(ls)"], [line for line in out.splitlines() if line.startswith("kept:")])
        self.assertIn("removed: permissions.allow = 7\n", out)

    def test_an_allow_that_is_not_a_list_is_removed_and_nothing_is_kept(self):
        self.edit_live(lambda doc: doc["permissions"].__setitem__("allow", "Bash(ls)"))
        out = self.shown()
        self.assertNotIn("kept:", out)
        self.assertIn('removed: permissions.allow = "Bash(ls)"\n', out)

    def test_a_harness_changed_since_attach_is_noted_and_not_refused(self):
        original = rerender.harness_differs
        try:
            rerender.harness_differs = lambda recorded, document: True
            out = self.shown()
        finally:
            rerender.harness_differs = original
        self.assertIn("note: the harness module differs from the one recorded at attach", out)


class Refusals(Base):
    def test_a_clone_with_no_recorded_harness_is_refused_and_pointed_at_attach(self):
        self.refuses("wb attach")

    def test_a_target_that_is_not_a_project_is_refused(self):
        self.attached()
        self.refuses("not an existing project", place=self.outside)

    def test_two_spellings_of_one_directory_are_accepted(self):
        self.attached()
        before = self.snapshot()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "rerender", self.place, "--dir", self.place, "--package", self.pkg,
                         "--package", self.synth], out, err, store_root=self.store_root, home=self.home,
                        distribution=self.dist)
        self.assertEqual((0, ""), (code, err.getvalue()), out.getvalue())
        self.assertEqual(before, self.snapshot())

    def test_two_spellings_of_different_directories_are_a_usage_error(self):
        self.attached()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "rerender", self.place, "--dir", self.outside, "--package", self.pkg,
                         "--package", self.synth], out, err, store_root=self.store_root, home=self.home,
                        distribution=self.dist)
        self.assertEqual((2, ""), (code, out.getvalue()), err.getvalue())

    def test_an_unknown_option_is_a_usage_error(self):
        self.attached()
        self.assertEqual(2, self.preview("--harness", "x/y")[0])

    def test_a_missing_permissions_file_is_refused(self):
        self.attached()
        os.remove(os.path.join(self.place, *SETTINGS.split("/")))
        self.refuses(SETTINGS)

    def test_a_permissions_file_that_is_not_json_is_refused(self):
        self.attached()
        with open(os.path.join(self.place, *SETTINGS.split("/")), "wb") as handle:
            handle.write(b"not json\n")
        self.refuses("not valid")

    def test_a_permissions_file_that_is_not_an_object_is_refused(self):
        self.attached()
        with open(os.path.join(self.place, *SETTINGS.split("/")), "wb") as handle:
            handle.write(b"[1, 2]\n")
        self.refuses("must be an object")

    def test_a_permissions_file_that_is_too_deeply_nested_is_refused(self):
        self.attached()
        with open(os.path.join(self.place, *SETTINGS.split("/")), "wb") as handle:
            handle.write(b"[" * 200 + b"]" * 200)
        self.refuses("not valid")

    def test_the_default_target_is_the_working_directory(self):
        self.attached()
        before = self.snapshot()
        previous = os.getcwd()
        os.chdir(self.place)
        try:
            code, out, err = self.preview(place="")
        finally:
            os.chdir(previous)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(before, self.snapshot())

    def test_an_empty_target_is_a_usage_error(self):
        self.attached()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "rerender", ""], out, err, store_root=self.store_root, home=self.home,
                        distribution=self.dist)
        self.assertEqual(2, code, err.getvalue())

    def test_an_empty_dir_option_is_a_usage_error(self):
        self.attached()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["preview", "rerender", "--dir", ""], out, err, store_root=self.store_root, home=self.home,
                        distribution=self.dist)
        self.assertEqual(2, code, err.getvalue())

    def test_a_target_that_is_a_link_is_refused(self):
        self.attached()
        link = os.path.join(self.outside, "link")
        os.symlink(self.place, link)
        self.refuses("link", place=link)

    def test_unacknowledged_differences_are_refused(self):
        self.attached()
        installed = os.path.join(self.place, ".workbench")
        changed = None
        for base, dirs, files in os.walk(installed):
            dirs[:] = [name for name in dirs if name != "local"]
            for name in sorted(files):
                if name != "manifest.json":
                    changed = os.path.join(base, name)
                    break
            if changed:
                break
        self.assertIsNotNone(changed, "no installed file to change")
        with open(changed, "ab") as handle:
            handle.write(b"\n# changed by someone else\n")
        before = self.snapshot()
        code, out, err = self.preview()
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertEqual(before, self.snapshot())

    def test_a_harness_the_project_does_not_record_is_refused(self):
        self.attached()
        from workbench import localmanifest
        path = os.path.join(self.place, *localmanifest.PATH.split("/"))
        with open(path, "rb") as handle:
            data = handle.read()
        document = localmanifest.parse(data)
        document["harness"] = "nothere"
        with open(path, "wb") as handle:
            handle.write(localmanifest.serialize(document))
        self.refuses("nothere")

    def test_a_permissions_file_that_is_a_link_is_refused(self):
        self.attached()
        full = os.path.join(self.place, *SETTINGS.split("/"))
        os.remove(full)
        os.symlink(os.path.join(self.outside, "elsewhere"), full)
        self.refuses(SETTINGS)

    def test_the_harness_package_not_given_is_refused(self):
        self.attached()
        self.refuses("--package", packages=[self.pkg])


class Keys(unittest.TestCase):
    def test_the_preview_is_a_key_that_is_agent_safe_and_defaults_to_none(self):
        key = levels.registry()["wb preview rerender"]
        self.assertEqual((True, levels.NONE), (key.agent, key.default))
        self.assertIn(levels.BLOCK, key.offers)

    def test_the_preview_action_is_listed_with_the_others(self):
        self.assertIn("rerender", rules.PREVIEW_ACTIONS)


if __name__ == "__main__":
    unittest.main()

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
from workbench import attach, cli, levels, rendering, rerender, rules

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

    def test_a_shared_settings_file_that_moved_is_named_with_both_hashes_before_it_is_recorded(self):
        self.assertNotIn("shared settings file", self.shown())
        with open(os.path.join(self.place, ".fixture", "settings.json"), "wb") as handle:
            handle.write(b'{"changed": true}\n')
        out = self.shown()
        self.assertRegex(out, r"(?m)^note: the shared settings file \.fixture/settings\.json is not what the rendering "
                              r"record watched \((none|[0-9a-f]{12}) -> [0-9a-f]{12}\); this re-render does not write it")
        self.assertNotIn("nothing to change", out)

    def test_two_different_kept_rules_never_print_alike(self):
        rules_ = ["a\nb", "a\\nb", "a ", "a", "caf\u00e9", "\x1b[31mred"]
        self.edit_live(lambda doc: doc["permissions"].__setitem__("allow", rules_))
        lines = [line for line in self.shown().splitlines() if line.startswith("kept:")]
        self.assertEqual(len(rules_), len(set(lines)), lines)
        self.assertIn("kept: a", lines)
        for line in lines:
            self.assertTrue(line.isascii() and line.isprintable(), line)

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


class Ticks(io.StringIO):
    """The terminal's input: reads one answer, which is the typed digest unless the test gives another."""

    def __init__(self, out, answer=None, during=None):
        super().__init__("")
        self.out, self.answer, self.during = out, answer, during

    def readline(self, *args):
        if self.during:
            self.during()
        if self.answer is not None:
            return self.answer + "\n"
        return DIGEST.search(self.out.getvalue()).group(1)[:12] + "\n"


class Write(Base):
    """``wb rerender``: increment B. The table is changed after attach, so that a key set to ``none`` reads ``block`` until
    the harness is rendered again."""

    def setUp(self):
        super().setUp()
        self.attached()
        self.terminal(True)

    def terminal(self, on):
        from workbench import approve
        patch = unittest.mock.patch.object(approve, "is_terminal", lambda stream: on)
        patch.start()
        self.addCleanup(patch.stop)

    def level(self, key):
        table, root, ident = rendering.current_table(self.guarded, self.place)
        return rendering.effective_level(self.guarded, ident, root, table, key)

    def rerender(self, *tokens, answer=None, during=None, place=None, packages=None):
        argv = ["rerender"] + ([place or self.place] if place != "" else [])
        for given in (packages if packages is not None else [self.pkg, self.synth]):
            argv += ["--package", given]
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(argv + list(tokens), out, err, store_root=self.store_root, home=self.home,
                        distribution=self.dist, stdin=Ticks(out, answer, during))
        return code, out.getvalue(), err.getvalue()

    def loosened(self):
        self.levels(wb_install="none")
        self.assertEqual("block", self.level("wb install"))

    def stopped(self, expected_code, contains, **kwargs):
        """A run that writes nothing: the exit code, a ``refused:`` or ``cancelled:`` line, and every file as it was."""
        seen = [self.snapshot()]
        change = kwargs.pop("during", None)

        def during():
            # What the test itself changes while the plan is shown is not the command's write.
            change()
            seen[0] = self.snapshot()

        code, out, err = self.rerender(during=during if change else None, **kwargs)
        self.assertEqual(expected_code, code, out + err)
        self.assertIn(contains, out + err)
        self.assertEqual(seen[0], self.snapshot(), "a stopped run wrote something")
        return out, err

    def test_the_typed_digest_makes_the_key_read_none(self):
        self.loosened()
        code, out, err = self.rerender()
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual("none", self.level("wb install"))
        self.assertIn("wb install: deny -> none", out)
        self.assertIn("nothing was committed", out)
        self.assertIn("nothing to change", self.shown())

    def test_tightening_makes_a_relaxed_key_read_block_again(self):
        self.levels(wb_install="none")
        self.assertEqual(0, self.rerender()[0])
        self.assertEqual("none", self.level("wb install"))
        self.levels(wb_install="block")
        self.assertEqual("block", self.level("wb install"))
        out = self.rerender()[1]
        self.assertIn("wb install: none -> deny", out)
        self.assertEqual("block", self.level("wb install"))
        self.assertIn("nothing to change", self.shown())

    def test_a_wrong_digest_writes_nothing(self):
        self.loosened()
        self.stopped(1, "cancelled: nothing was written", answer="not the digest")
        self.assertEqual("block", self.level("wb install"))

    def test_an_empty_answer_writes_nothing(self):
        self.loosened()
        self.stopped(1, "cancelled: nothing was written", answer="")

    def test_a_run_without_a_terminal_is_refused_and_writes_nothing(self):
        self.loosened()
        self.terminal(False)
        self.stopped(1, "refused: ")
        self.assertEqual("block", self.level("wb install"))

    def test_one_terminal_is_not_enough(self):
        from workbench import approve
        self.loosened()
        patch = unittest.mock.patch.object(approve, "is_terminal", lambda stream: isinstance(stream, Ticks))
        patch.start()
        self.addCleanup(patch.stop)
        self.stopped(1, "refused: ")

    def test_no_level_lets_a_run_without_a_terminal_write(self):
        self.levels(wb_install="none", wb_rerender="none")
        self.terminal(False)
        before = self.snapshot()
        code, out, err = self.rerender()
        self.assertEqual(1, code, out)
        self.assertIn("refused: ", err)
        self.assertEqual(before, self.snapshot())

    def test_a_refused_run_without_a_terminal_reads_no_input(self):
        self.loosened()
        self.terminal(False)
        asked = []
        code, out, err = self.rerender(during=lambda: asked.append(1))
        self.assertEqual((1, []), (code, asked), err)

    def test_the_command_itself_refuses_without_a_terminal_whatever_called_it(self):
        self.loosened()
        self.terminal(False)
        before = self.snapshot()
        out, err = io.StringIO(), io.StringIO()
        code = rerender.run(self.guarded, rerender.parse([self.place, "--package", self.pkg, "--package", self.synth]),
                            Ticks(out), out, err, self.dist, home=self.home)
        self.assertEqual((1, ""), (code, out.getvalue()), err.getvalue())
        self.assertIn("refused: ", err.getvalue())
        self.assertEqual(before, self.snapshot())

    def test_the_cli_refuses_without_a_terminal_before_it_opens_the_store_or_the_target(self):
        self.loosened()
        self.terminal(False)
        with unittest.mock.patch.object(rerender, "run", side_effect=AssertionError("run was reached")):
            with unittest.mock.patch.object(cli, "_open_store", side_effect=AssertionError("store was opened")):
                code, out, err = self.rerender()
        self.assertEqual(1, code, out)
        self.assertIn("refused: ", err)

    def test_nothing_to_change_asks_nothing_and_writes_nothing(self):
        asked = []
        before = self.snapshot()
        code, out, err = self.rerender(during=lambda: asked.append(1))
        self.assertEqual((0, []), (code, asked), err)
        self.assertIn("nothing to change", out)
        self.assertEqual(before, self.snapshot())

    def test_the_prompt_names_the_characters_to_type(self):
        self.loosened()
        out = self.rerender()[1]
        self.assertIn("type the first 12 characters of the digest", out)
        self.assertLess(out.index("digest: "), out.index("type the first 12"))

    def test_the_allow_rules_survive_and_are_listed_before_the_prompt(self):
        self.edit_live(lambda doc: doc["permissions"].__setitem__("allow", ["Bash(ls)", "Bash(pwd)"]))
        self.levels(wb_install="none")
        code, out, err = self.rerender()
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(["Bash(ls)", "Bash(pwd)"], self.live()["permissions"]["allow"])
        self.assertLess(out.index("kept: Bash(ls)"), out.index("type the first 12"))
        self.assertEqual("none", self.level("wb install"))

    def test_an_entry_the_new_file_will_not_have_is_gone_after_the_run_and_was_listed(self):
        self.edit_live(lambda doc: doc.__setitem__("extra", "x"))
        code, out, err = self.rerender()
        self.assertEqual(0, code, err)
        self.assertIn('removed: extra = "x"', out)
        self.assertNotIn("extra", self.live())

    def test_a_table_changed_while_the_plan_was_shown_writes_nothing(self):
        self.loosened()
        self.stopped(1, "changed while it was shown", during=lambda: self.levels(wb_install="none", wb_pin="none"))
        self.assertEqual("block", self.level("wb install"))

    def test_the_permissions_file_changed_while_the_plan_was_shown_writes_nothing(self):
        self.loosened()
        self.stopped(1, "changed while it was shown", during=lambda: self.edit_live(
            lambda doc: doc["permissions"].__setitem__("allow", ["Bash(ls)"])))

    def test_the_shared_settings_file_changed_while_the_plan_was_shown_writes_nothing(self):
        self.loosened()

        def change():
            with open(os.path.join(self.place, ".fixture", "settings.json"), "wb") as handle:
                handle.write(b'{"changed": true}\n')

        self.stopped(1, "changed while it was shown", during=change)

    def test_the_local_manifest_changed_while_the_plan_was_shown_writes_nothing(self):
        self.loosened()

        def change():
            with open(os.path.join(self.place, *LOCAL.split("/")), "rb") as handle:
                text = handle.read()
            self.assertIn(b'"source": "', text)
            with open(os.path.join(self.place, *LOCAL.split("/")), "wb") as handle:
                handle.write(text.replace(b'"source": "', b'"source": "x', 1))

        self.stopped(1, "refused: ", during=change)

    def test_a_staged_input_changed_while_the_plan_was_shown_writes_nothing(self):
        self.loosened()
        real = attach.stage
        flag = []

        def stage(*args, **kwargs):
            done = real(*args, **kwargs)
            if flag:
                return done._replace(inputs=done.inputs + (("module", "p", "m", "a" * 64, "d" * 64),))
            return done

        with unittest.mock.patch.object(attach, "stage", stage):
            self.stopped(1, "changed while it was shown", during=lambda: flag.append(1))

    def test_a_target_that_changes_while_the_plan_was_shown_writes_nothing(self):
        self.loosened()
        moved = self.place + ".moved"

        def swap():
            os.rename(self.place, moved)
            os.mkdir(self.place)

        store = self.content(self.store_root)
        with open(os.path.join(self.place, *SETTINGS.split("/")), "rb") as handle:
            settings = handle.read()
        code, out, err = self.rerender(during=swap)
        self.assertEqual(1, code, out + err)
        self.assertIn("changed", err)
        self.assertEqual(store, self.content(self.store_root))
        with open(os.path.join(moved, *SETTINGS.split("/")), "rb") as handle:
            self.assertEqual(settings, handle.read())

    def test_a_live_file_replaced_between_the_plan_and_the_write_is_a_conflict_and_is_not_overwritten(self):
        from workbench import projectfs
        self.loosened()
        real = projectfs.Writer.replace_file
        edited = []

        def replace(writer, rel, expected, data, **kwargs):
            if rel == SETTINGS and not edited:
                edited.append(1)
                self.edit_live(lambda doc: doc.__setitem__("late", "y"))
            return real(writer, rel, expected, data, **kwargs)

        with unittest.mock.patch.object(projectfs.Writer, "replace_file", replace):
            code, out, err = self.rerender()
        self.assertEqual(1, code, out)
        self.assertIn("refused: ", err)
        self.assertIn("nothing was written", err)
        self.assertEqual("y", self.live()["late"])
        self.assertEqual("block", self.level("wb install"))

    def test_a_failure_after_the_permissions_file_is_replaced_leaves_every_relaxed_key_reading_block(self):
        from workbench import localmanifest
        self.levels(wb_install="none", wb_pin="none")
        with unittest.mock.patch.object(localmanifest, "replace", side_effect=OSError("forced")):
            code, out, err = self.rerender()
        self.assertEqual(3, code, out)
        self.assertIn("failed: forced", err)
        self.assertRegex(err, r"(?s)written:\n  %s\n.*not written:\n  %s\n  rendering record" % (
            re.escape(SETTINGS), re.escape(LOCAL)))
        for key in ("wb install", "wb pin"):
            self.assertEqual("block", self.level(key), key)

    def test_a_failure_after_the_manifest_is_replaced_leaves_every_relaxed_key_reading_block(self):
        self.levels(wb_install="none", wb_pin="none")
        with unittest.mock.patch.object(rendering, "write", side_effect=OSError("forced")):
            code, out, err = self.rerender()
        self.assertEqual(3, code, out)
        self.assertIn("failed: forced", err)
        self.assertRegex(err, r"(?s)written:\n  %s\n  %s\n.*not written:\n  rendering record" % (
            re.escape(SETTINGS), re.escape(LOCAL)))
        for key in ("wb install", "wb pin"):
            self.assertEqual("block", self.level(key), key)

    def test_an_interrupt_right_after_the_rename_is_reported_as_written(self):
        from workbench import projectfs
        self.loosened()
        real = projectfs.Writer.replace_file

        def replace(writer, rel, expected, data, **kwargs):
            real(writer, rel, expected, data, **kwargs)
            if rel == SETTINGS:
                raise KeyboardInterrupt

        with unittest.mock.patch.object(projectfs.Writer, "replace_file", replace):
            code, out, err = self.rerender()
        self.assertEqual(3, code, out)
        self.assertRegex(err, r"(?s)written:\n  %s\n.*not written:\n  %s\n" % (re.escape(SETTINGS), re.escape(LOCAL)))
        self.assertEqual("block", self.level("wb install"))

    def test_a_run_after_a_stopped_one_finishes_the_job(self):
        self.levels(wb_install="none")
        with unittest.mock.patch.object(rendering, "write", side_effect=OSError("forced")):
            self.assertEqual(3, self.rerender()[0])
        code, out, err = self.rerender()
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual("none", self.level("wb install"))
        self.assertIn("  %s: left as it is" % SETTINGS, out)

    def test_an_interrupt_while_asking_writes_nothing(self):
        self.loosened()

        def interrupt():
            raise KeyboardInterrupt

        self.stopped(130, "cancelled: nothing was written", during=interrupt)

    def test_an_interrupt_after_writing_began_exits_3(self):
        self.loosened()
        with unittest.mock.patch.object(rendering, "write", side_effect=KeyboardInterrupt):
            code, out, err = self.rerender()
        self.assertEqual(3, code, out)
        self.assertIn("failed: interrupted", err)
        self.assertEqual("block", self.level("wb install"))

    def test_a_clone_with_no_recorded_harness_is_refused_and_pointed_at_attach(self):
        os.unlink(os.path.join(self.place, *LOCAL.split("/")))
        self.stopped(1, "wb attach")

    def test_a_permissions_file_that_is_a_link_is_refused_with_nothing_written(self):
        self.loosened()
        path = os.path.join(self.place, *SETTINGS.split("/"))
        os.rename(path, path + ".real")
        os.symlink(path + ".real", path)
        self.stopped(1, "refused: ")

    def test_a_permissions_file_that_is_not_valid_is_refused_with_nothing_written(self):
        self.loosened()
        with open(os.path.join(self.place, *SETTINGS.split("/")), "wb") as handle:
            handle.write(b"{not json")
        self.stopped(1, "refused: ")

    def test_two_spellings_of_different_directories_are_a_usage_error_and_write_nothing(self):
        self.loosened()
        before = self.snapshot()
        code, out, err = self.rerender("--dir", self.place + "-other")
        self.assertEqual(2, code, out)
        self.assertEqual(before, self.snapshot())

    def test_the_target_is_printed_before_the_plan(self):
        self.loosened()
        out = self.rerender()[1]
        self.assertTrue(out.startswith("project: %s\n" % os.path.realpath(self.place)), out)

    def test_no_level_log_line_is_written(self):
        self.loosened()
        before = self.log_lines()
        self.assertEqual(0, self.rerender()[0])
        self.assertEqual(before, self.log_lines())

    def test_a_settings_entry_of_none_for_the_key_reads_block_and_still_asks(self):
        self.levels(wb_install="none", wb_rerender="none")
        self.assertEqual("block", self.level("wb rerender"))
        out = self.rerender(answer="no")[1]
        self.assertIn("type the first 12", out)


class Relaxed(Base):
    """A key already relaxed at attach and a table that does not change: the only reason to re-render is a live file that
    differs, as after "Yes, and don't ask again"."""
    terminal, level, rerender = Write.terminal, Write.level, Write.rerender

    def setUp(self):
        super().setUp()
        self.attached(**{"wb install": "none"})
        self.terminal(True)

    def test_a_stop_after_the_file_is_replaced_leaves_the_relaxed_key_reading_block(self):
        self.assertEqual("none", self.level("wb install"))
        self.edit_live(lambda doc: doc["permissions"].__setitem__("allow", ["Bash(ls)"]))
        self.assertEqual("block", self.level("wb install"))
        with unittest.mock.patch.object(rendering, "write", side_effect=OSError("forced")):
            code, out, err = self.rerender()
        self.assertEqual(3, code, out)
        self.assertIn("failed: forced", err)
        self.assertEqual("block", self.level("wb install"))
        self.assertEqual(["Bash(ls)"], self.live()["permissions"]["allow"])
        code, out, err = self.rerender()
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual("none", self.level("wb install"))
        self.assertEqual(["Bash(ls)"], self.live()["permissions"]["allow"])


class Pty(Base):
    """The command on real pseudo-terminals, with ``approve.is_terminal`` as it is in the product: the other tests say every
    stream is a terminal (or none is)."""

    def setUp(self):
        super().setUp()
        self.attached()
        from workbench import approve

        def real(stream):
            try:
                return os.isatty(stream.fileno())
            except (AttributeError, OSError, ValueError):
                return False

        patch = unittest.mock.patch.object(approve, "is_terminal", real)
        patch.start()
        self.addCleanup(patch.stop)

    def level(self, key):
        table, root, ident = rendering.current_table(self.guarded, self.place)
        return rendering.effective_level(self.guarded, ident, root, table, key)

    def drive(self, answer):
        """Run `wb rerender` with both streams on one pseudo-terminal and type `answer` (a function of the output so far)
        once the prompt is shown. Returns the exit code and the standard error."""
        import pty
        import select
        import threading
        import time
        master, slave = pty.openpty()
        seen = bytearray()

        def talk():
            while b"> " not in seen:
                ready, _, _ = select.select([master], [], [], 0.2)
                if ready:
                    try:
                        seen.extend(os.read(master, 4096))
                    except OSError:
                        return
            # The command discards what is typed before the prompt has been shown.
            time.sleep(0.3)
            os.write(master, (answer(seen.decode("utf-8", "replace")) + "\n").encode())

        thread = threading.Thread(target=talk, daemon=True)
        thread.start()
        err = io.StringIO()
        argv = ["rerender", self.place, "--package", self.pkg, "--package", self.synth]
        try:
            with open(slave, "r", closefd=False) as stdin, open(slave, "w", closefd=False) as out:
                code = cli.main(argv, out, err, store_root=self.store_root, home=self.home, distribution=self.dist,
                                stdin=stdin)
        finally:
            thread.join(10)
            os.close(master)
            os.close(slave)
        return code, err.getvalue()

    def test_the_digest_typed_at_a_real_terminal_makes_the_key_read_none(self):
        self.levels(wb_install="none")
        self.assertEqual("block", self.level("wb install"))
        code, err = self.drive(lambda shown: re.search(r"digest: ([0-9a-f]{64})", shown).group(1)[:12])
        self.assertEqual((0, ""), (code, err))
        self.assertEqual("none", self.level("wb install"))

    def test_anything_else_typed_at_a_real_terminal_writes_nothing(self):
        self.levels(wb_install="none")
        before = self.snapshot()
        code, err = self.drive(lambda shown: "no")
        self.assertEqual((1, ""), (code, err))
        self.assertEqual(before, self.snapshot())
        self.assertEqual("block", self.level("wb install"))

    def test_standard_input_that_is_not_a_terminal_is_refused_even_with_a_terminal_output(self):
        import pty
        self.levels(wb_install="none")
        master, slave = pty.openpty()
        before = self.snapshot()
        try:
            with open(slave, "w", closefd=False) as out:
                err = io.StringIO()
                code = cli.main(["rerender", self.place, "--package", self.pkg, "--package", self.synth], out, err,
                                store_root=self.store_root, home=self.home, distribution=self.dist,
                                stdin=io.StringIO("x\n"))
        finally:
            os.close(master)
            os.close(slave)
        self.assertEqual(1, code)
        self.assertIn("refused: ", err.getvalue())
        self.assertEqual(before, self.snapshot())


class Keys(unittest.TestCase):
    def test_the_write_is_an_owner_run_key_that_offers_block_only(self):
        key = levels.registry()["wb rerender"]
        self.assertEqual((levels.BLOCK, (levels.BLOCK,), False), (key.default, key.offers, key.agent))

    def test_the_write_is_an_owner_run_command(self):
        self.assertIn("rerender", rules.OWNER_RUN)
        self.assertNotIn("rerender", rules.AGENT_SAFE)

    def test_the_preview_is_a_key_that_is_agent_safe_and_defaults_to_none(self):
        key = levels.registry()["wb preview rerender"]
        self.assertEqual((True, levels.NONE), (key.agent, key.default))
        self.assertIn(levels.BLOCK, key.offers)

    def test_the_preview_action_is_listed_with_the_others(self):
        self.assertIn("rerender", rules.PREVIEW_ACTIONS)


if __name__ == "__main__":
    unittest.main()

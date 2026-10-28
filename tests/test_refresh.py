"""``wb preview rerender``: the state of every rendered file but the permissions file, read only.

Plan ``2026-10-28-refresh-rendered-harness``, increment A (``docs/specs/harness-refresh.md``). The project and the synthetic
harness are those of ``test_rerender``; the harness is attached and a source is then changed by replacing what the staging
returns, since the fixture's packages are verified against what the project records."""

import contextlib
import hashlib
import json
import os
import re
import unittest
import unittest.mock

from tests import test_attach, test_rerender
from tests.test_rerender import DIGEST, LOCAL, SETTINGS
from workbench import attach, harnessplan, localmanifest, projectfs, refresh, rendering, rerender, target

SKILL = ".fixture/skills/sample/SKILL.md"
AGENT = ".fixture/agents/reviewer.md"
COMMAND = ".fixture/commands/ship.md"
ROOT = "FIXTURE.md"
EXTRA = ".fixture/skills/extra/SKILL.md"
OLD_TEXT = b"Do the thing."
NEW_TEXT = b"A new skill.\n"


def chained(*changes):
    """One change to the staged files that applies each of `changes` in turn."""
    def change(files):
        for each in changes:
            files = each(files)
        return files
    return change


def planned(path, data):
    return harnessplan.Planned(path, data, harnessplan.FILE_MODE, hashlib.sha256(data).hexdigest(), "test")


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Base(test_rerender.Base):
    # The module with a skill, an agent and a command in its neutral tree, so the attached clone has rendered files.
    MODULES = dict(test_rerender.Base.MODULES, notes=test_attach.NOTES)

    def setUp(self):
        super().setUp()
        self.attached()

    def full(self, rel):
        return os.path.join(self.place, *rel.split("/"))

    def disk(self, rel):
        with open(self.full(rel), "rb") as handle:
            return handle.read()

    def put_disk(self, rel, data):
        os.makedirs(os.path.dirname(self.full(rel)), exist_ok=True)
        with open(self.full(rel), "wb") as handle:
            handle.write(data)

    def staged_as(self, change):
        """The staging with its files changed by `change`, a function from the list of ``Planned`` to a list."""
        real = attach.stage

        def stage(*args, **kwargs):
            done = real(*args, **kwargs)
            return done._replace(staged=done.staged._replace(files=sorted(change(list(done.staged.files)),
                                                                          key=lambda item: item.path.encode())))

        return unittest.mock.patch.object(attach, "stage", stage)

    def with_data(self, path, data):
        return lambda files: [planned(path, data) if item.path == path else item for item in files]

    def without(self, path):
        return lambda files: [item for item in files if item.path != path]

    def adding(self, path, data):
        return lambda files: files + [planned(path, data)]

    def newer(self, path):
        """A change that gives `path` other staged bytes than the rendered ones."""
        return self.with_data(path, self.disk(path) + b"More.\n")

    def out_of(self, change=None):
        with self.staged_as(change) if change else contextlib.nullcontext():
            return self.shown()

    def refused_with(self, contains, change=None):
        with self.staged_as(change) if change else contextlib.nullcontext():
            return self.refuses(contains)

    def build(self, change=None):
        command = rerender.parse([self.place, "--package", self.pkg, "--package", self.synth])
        with self.staged_as(change) if change else contextlib.nullcontext():
            with target.open_target(self.place, self.store_root) as held:
                return rerender.build(self.guarded, held, command, self.dist, home=self.home)

    def row(self, out, path):
        found = [line for line in out.splitlines() if line.startswith("  %s: " % path)]
        self.assertEqual(1, len(found), (path, out))
        return found[0]


class Current(Base):
    def test_a_clone_just_attached_has_every_file_current_and_nothing_to_change(self):
        out = self.shown()
        for path in (SKILL, AGENT, COMMAND, ROOT):
            self.assertEqual("  %s: left as it is" % path, self.row(out, path))
        self.assertIn("nothing to change\n", out)

    def test_a_difference_that_is_only_the_translation_is_not_stale(self):
        # The neutral source differs from the rendered file (the agent's `tools` line is translated); the staged file is
        # the translated one, so the comparison is of the renderer's output with the disk.
        self.assertIn(b"tools: read, search", test_attach.AGENT)
        self.assertNotIn(b"tools: read, search", self.disk(AGENT))
        self.assertIn("  %s: left as it is\n" % AGENT, self.shown())


class Stale(Base):
    def test_a_file_whose_source_moved_is_stale_with_old_and_new_hash(self):
        out = self.out_of(self.newer(SKILL))
        self.assertRegex(self.row(out, SKILL), r"^  %s: [0-9a-f]{12} -> [0-9a-f]{12} \(stale\)$" % re.escape(SKILL))
        self.assertNotIn("nothing to change", out)

    def test_the_changed_lines_are_shown(self):
        out = self.out_of(self.with_data(SKILL, self.disk(SKILL).replace(OLD_TEXT, b"Do it.")))
        self.assertIn("    -Do the thing.\n", out)
        self.assertIn("    +Do it.\n", out)

    def test_a_changed_line_that_is_not_plain_is_shown_as_its_json_string(self):
        out = self.out_of(self.with_data(SKILL, self.disk(SKILL).replace(OLD_TEXT, b"Do it \xc3\xa9\x01.")))
        self.assertIn('    +"Do it \\u00e9\\u0001."\n', out)

    def test_a_change_of_one_line_separator_for_another_is_shown(self):
        # Splitting on every separator made these two texts equal line by line, so a stale file showed no changed line.
        cases = (
            (b"a\x0bb\n", b"a\x0cb\n", (("-", "a\x0bb"), ("+", "a\x0cb"))),
            (b"a\rb\n", b"a\xe2\x80\xa8b\n", (("-", "a\rb"), ("+", "a\u2028b"))),
            (b"a\r\nb\n", b"a\nb\n", (("-", "a\r"), ("+", "a"))),
        )
        for old, new, expected in cases:
            self.assertEqual((expected, 0), refresh._changed(old, new), (old, new))

    def test_a_changed_final_newline_is_shown(self):
        lines, more = refresh._changed(b"a\nb", b"a\nb\n")
        self.assertEqual((("+", ""),), lines)

    def test_a_stale_file_still_lists_the_manifest_as_changing(self):
        out = self.out_of(self.newer(SKILL))
        self.assertRegex(self.row(out, LOCAL), r"[0-9a-f]{12} -> [0-9a-f]{12}$")

    def test_the_manifest_in_the_plan_takes_the_new_hash(self):
        data = self.disk(SKILL) + b"More.\n"
        plan = self.build(self.newer(SKILL))
        entry, = [item for item in plan.manifest["files"] if item["path"] == SKILL]
        self.assertEqual(sha(data), entry["hash"])
        self.assertEqual({SKILL: "stale"}, {row.path: row.state for row in plan.rows if row.state != "current"})


class Edited(Base):
    def test_a_file_the_owner_edited_refuses_the_run_and_is_named(self):
        self.put_disk(SKILL, b"edited by the owner\n")
        err = self.refused_with(SKILL)
        self.assertIn("edited", err)

    def test_one_edited_file_refuses_even_when_another_is_stale(self):
        self.put_disk(AGENT, b"edited\n")
        self.refused_with(AGENT, self.newer(SKILL))

    def test_an_edited_file_is_refused_even_if_it_equals_nothing_staged_or_recorded(self):
        self.put_disk(ROOT, b"@other\n")
        self.refused_with(ROOT)


class Missing(Base):
    def test_a_deleted_file_is_recreated_and_listed(self):
        os.remove(self.full(AGENT))
        out = self.shown()
        self.assertRegex(self.row(out, AGENT), r"^  %s: none -> [0-9a-f]{12} \(missing; recreated\)$" % re.escape(AGENT))
        self.assertNotIn("nothing to change", out)


class New(Base):
    def test_a_staged_file_the_manifest_does_not_list_is_new(self):
        out = self.out_of(self.adding(EXTRA, b"A new skill.\n"))
        self.assertRegex(self.row(out, EXTRA), r"^  %s: none -> [0-9a-f]{12} \(new\)$" % re.escape(EXTRA))

    def test_the_manifest_in_the_plan_lists_the_new_file_in_order(self):
        plan = self.build(self.adding(EXTRA, b"A new skill.\n"))
        paths = [item["path"] for item in plan.manifest["files"]]
        self.assertIn(EXTRA, paths)
        self.assertEqual(sorted(paths, key=lambda path: path.encode()), paths)

    def test_other_content_at_the_path_of_a_new_file_is_unrecorded_and_refused(self):
        self.put_disk(EXTRA, b"somebody else's file\n")
        err = self.refused_with(EXTRA, self.adding(EXTRA, b"A new skill.\n"))
        self.assertIn("unrecorded", err)

    def test_a_path_outside_the_exclude_lines_refuses_when_it_would_be_created(self):
        err = self.refused_with("docs/new.md", self.adding("docs/new.md", b"x\n"))
        self.assertIn("exclude", err)

    def test_a_missing_file_outside_the_exclude_lines_refuses_too(self):
        # A recorded file the layout no longer excludes would be written where git sees it.
        real = attach.stage

        def stage(*args, **kwargs):
            done = real(*args, **kwargs)
            return done._replace(staged=done.staged._replace(exclude=["FIXTURE.md"]))

        os.remove(self.full(AGENT))
        with unittest.mock.patch.object(attach, "stage", stage):
            err = self.refuses(AGENT)
        self.assertIn("exclude", err)


class Applied(Base):
    def test_a_file_already_holding_the_staged_bytes_while_the_manifest_records_another_is_applied(self):
        data = self.disk(SKILL) + b"More.\n"
        self.put_disk(SKILL, data)
        out = self.out_of(self.with_data(SKILL, data))
        self.assertRegex(self.row(out, SKILL), r"^  %s: left as it is \(applied\)$" % re.escape(SKILL))
        self.assertNotIn("nothing to change", out)

    def test_the_manifest_in_the_plan_takes_the_hash_of_an_applied_file(self):
        data = self.disk(SKILL) + b"More.\n"
        self.put_disk(SKILL, data)
        plan = self.build(self.with_data(SKILL, data))
        entry, = [item for item in plan.manifest["files"] if item["path"] == SKILL]
        self.assertEqual(sha(data), entry["hash"])

    def test_a_created_file_that_the_manifest_does_not_list_yet_is_applied(self):
        self.put_disk(EXTRA, b"A new skill.\n")
        out = self.out_of(self.adding(EXTRA, b"A new skill.\n"))
        self.assertIn("  %s: left as it is (applied)\n" % EXTRA, out)


class Orphaned(Base):
    def test_a_listed_file_the_sources_no_longer_ship_is_orphaned_and_present(self):
        out = self.out_of(self.without(COMMAND))
        self.assertRegex(self.row(out, COMMAND), r"^  %s: [0-9a-f]{12} -> none \(orphaned; no longer shipped, present\)$"
                         % re.escape(COMMAND))
        # An orphan is listed and never written, so it is no change.
        self.assertIn("nothing to change", out)

    def test_an_orphan_that_is_already_gone_says_so(self):
        os.remove(self.full(COMMAND))
        out = self.out_of(self.without(COMMAND))
        self.assertRegex(self.row(out, COMMAND), r"^  %s: none -> none \(orphaned; no longer shipped, already gone\)$"
                         % re.escape(COMMAND))

    def test_an_orphan_is_decided_before_an_edit_is(self):
        self.put_disk(COMMAND, b"edited\n")
        out = self.out_of(self.without(COMMAND))
        self.assertIn("orphaned", self.row(out, COMMAND))

    def test_an_orphan_keeps_its_manifest_entry_and_is_never_written(self):
        before = self.disk(COMMAND)
        plan = self.build(self.without(COMMAND))
        self.assertIn(COMMAND, [item["path"] for item in plan.manifest["files"]])
        self.assertEqual(before, self.disk(COMMAND))


class Links(Base):
    def link(self, rel, content):
        outside = os.path.join(self.outside, "elsewhere")
        with open(outside, "wb") as handle:
            handle.write(content)
        os.remove(self.full(rel))
        os.symlink(outside, self.full(rel))

    def test_a_link_with_the_staged_and_recorded_content_is_refused_when_nothing_else_changes(self):
        self.link(SKILL, self.disk(SKILL))
        err = self.refused_with(SKILL)
        self.assertIn("link", err.lower())

    def test_a_link_at_an_orphaned_path_is_refused(self):
        self.link(COMMAND, self.disk(COMMAND))
        self.refused_with(COMMAND, self.without(COMMAND))

    def test_a_link_in_a_directory_above_a_staged_path_is_refused(self):
        os.rename(self.full(".fixture/agents"), os.path.join(self.outside, "agents"))
        os.symlink(os.path.join(self.outside, "agents"), self.full(".fixture/agents"))
        self.refused_with(".fixture/agents")


class PermissionsFile(Base):
    def test_a_live_allow_rule_is_kept_and_never_an_edit_that_refuses(self):
        self.edit_live(lambda doc: doc["permissions"].__setitem__("allow", ["Bash(ls)"]))
        out = self.shown()
        self.assertIn("kept: Bash(ls)\n", out)
        self.assertNotIn("refused", out)

    def test_the_permissions_file_is_not_a_row_of_the_table(self):
        plan = self.build()
        self.assertNotIn(SETTINGS, [row.path for row in plan.rows])


class Digest(Base):
    def digest(self, change=None):
        return DIGEST.search(self.out_of(change)).group(1)

    def test_it_changes_with_the_staged_bytes_a_state_and_an_orphan(self):
        base = self.digest()
        stale = self.digest(self.newer(SKILL))
        other = self.digest(self.with_data(SKILL, self.disk(SKILL) + b"Other.\n"))
        orphan = self.digest(self.without(COMMAND))
        self.assertEqual(4, len({base, stale, other, orphan}))

    def test_it_changes_when_a_file_goes_missing(self):
        base = self.digest()
        os.remove(self.full(AGENT))
        self.assertNotEqual(base, self.digest())

    def test_it_is_stable_for_the_same_plan(self):
        self.assertEqual(self.digest(self.newer(SKILL)), self.digest(self.newer(SKILL)))


class Writes(Base):
    """``wb rerender`` writes the files (increment B). The table is loosened after attach where the test says so, so that the
    permissions file and the record change with the rendered files and a stop leaves a relaxed key reading ``block``."""
    terminal, level, rerender, stopped, loosened = (test_rerender.Write.terminal, test_rerender.Write.level,
                                                     test_rerender.Write.rerender, test_rerender.Write.stopped,
                                                     test_rerender.Write.loosened)

    def setUp(self):
        super().setUp()
        self.terminal(True)

    def run_with(self, change, **kwargs):
        with self.staged_as(change):
            return self.rerender(**kwargs)

    def mode(self, rel):
        return os.stat(self.full(rel)).st_mode & 0o777

    def listed(self):
        return {item["path"]: item["hash"] for item in json.loads(self.disk(LOCAL))["files"]}

    def agrees(self):
        """Every file the manifest lists is on disk with the hash the manifest records (what `wb check` asks)."""
        for path, recorded in self.listed().items():
            self.assertEqual(recorded, sha(self.disk(path)), path)

    def all_changed(self):
        return chained(self.newer(AGENT), self.adding(EXTRA, NEW_TEXT), self.newer(SKILL))

    def swap_for_link(self, rel):
        elsewhere = os.path.join(self.outside, "elsewhere")
        with open(elsewhere, "wb") as handle:
            handle.write(self.disk(rel))
        os.remove(self.full(rel))
        os.symlink(elsewhere, self.full(rel))

    def test_a_stale_file_is_replaced_and_the_preview_then_reads_it_current(self):
        change = self.newer(SKILL)
        data = self.disk(SKILL) + b"More.\n"
        mode = self.mode(SKILL)
        code, out, err = self.run_with(change)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(data, self.disk(SKILL))
        self.assertEqual(mode, self.mode(SKILL))
        self.assertIn("(stale)", out)
        self.agrees()
        with self.staged_as(change):
            after = self.shown()
        self.assertIn("  %s: left as it is\n" % SKILL, after)
        self.assertIn("nothing to change", after)

    def test_a_new_file_is_created_with_its_parent_directories_and_the_mode_attach_gives(self):
        self.assertFalse(os.path.exists(self.full(".fixture/skills/extra")))
        code, out, err = self.run_with(self.adding(EXTRA, NEW_TEXT))
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(NEW_TEXT, self.disk(EXTRA))
        self.assertEqual(self.mode(SKILL), self.mode(EXTRA))
        self.agrees()

    def test_a_missing_file_is_recreated_with_the_mode_attach_gave_it(self):
        was, mode = self.disk(AGENT), self.mode(AGENT)
        os.remove(self.full(AGENT))
        code, out, err = self.rerender()
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual((was, mode), (self.disk(AGENT), self.mode(AGENT)))
        self.assertIn("missing; recreated", out)
        self.agrees()

    def test_an_orphan_is_left_alone_and_keeps_its_manifest_entry(self):
        before, entry = self.disk(COMMAND), self.listed()[COMMAND]
        code, out, err = self.run_with(chained(self.without(COMMAND), self.newer(SKILL)))
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual((before, entry), (self.disk(COMMAND), self.listed()[COMMAND]))
        self.assertIn("orphaned", out)

    def test_an_applied_file_is_not_touched_and_only_its_hash_goes_into_the_manifest(self):
        data = self.disk(SKILL) + b"More.\n"
        self.put_disk(SKILL, data)
        info = os.stat(self.full(SKILL))
        code, out, err = self.run_with(self.with_data(SKILL, data))
        self.assertEqual((0, ""), (code, err), out)
        after = os.stat(self.full(SKILL))
        self.assertEqual((info.st_ino, info.st_mtime_ns), (after.st_ino, after.st_mtime_ns))
        self.assertEqual(sha(data), self.listed()[SKILL])

    def test_the_report_counts_the_files_by_what_was_done(self):
        os.remove(self.full(COMMAND))
        code, out, err = self.run_with(chained(self.newer(AGENT), self.adding(EXTRA, NEW_TEXT)))
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("files: 1 replaced, 1 created, 1 recreated\n", out)
        self.assertLess(out.index("files: "), out.index("nothing was committed"))

    def test_the_permissions_file_the_record_and_the_files_are_written_in_one_run(self):
        self.edit_live(lambda doc: doc["permissions"].__setitem__("allow", ["Bash(ls)"]))
        self.levels(wb_install="none")
        code, out, err = self.run_with(self.newer(SKILL))
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(["Bash(ls)"], self.live()["permissions"]["allow"])
        self.assertEqual("none", self.level("wb install"))
        self.agrees()

    def test_a_run_with_nothing_to_change_writes_nothing(self):
        change = self.newer(SKILL)
        self.assertEqual(0, self.run_with(change)[0])
        asked, before = [], self.snapshot()
        code, out, err = self.run_with(change, during=lambda: asked.append(1))
        self.assertEqual((0, []), (code, asked), err)
        self.assertIn("nothing to change", out)
        self.assertEqual(before, self.snapshot())

    def test_no_level_log_line_is_written(self):
        before = self.log_lines()
        self.assertEqual(0, self.run_with(self.newer(SKILL))[0])
        self.assertEqual(before, self.log_lines())

    def test_a_wrong_digest_writes_nothing(self):
        with self.staged_as(self.newer(SKILL)):
            self.stopped(1, "cancelled: nothing was written", answer="not the digest")

    def test_a_run_without_a_terminal_writes_nothing_and_asks_nothing(self):
        self.terminal(False)
        asked = []
        with self.staged_as(self.newer(SKILL)):
            self.stopped(1, "refused: ", during=lambda: asked.append(1))
        self.assertEqual([], asked)

    def test_an_edited_file_refuses_the_run_and_writes_nothing(self):
        self.put_disk(AGENT, b"edited by the owner\n")
        with self.staged_as(self.newer(SKILL)):
            self.stopped(1, AGENT)

    def test_nothing_is_written_before_the_confirmation(self):
        before, asked = self.snapshot(), []
        with self.staged_as(self.all_changed()):
            self.stopped(1, "cancelled", answer="no", during=lambda: asked.append(self.snapshot()))
        self.assertEqual([before], asked)

    # --- a change between the plan and the write ---

    def test_a_file_changed_while_the_plan_was_shown_writes_nothing(self):
        with self.staged_as(self.newer(SKILL)):
            self.stopped(1, "nothing was written", during=lambda: self.put_disk(SKILL, b"changed meanwhile\n"))

    def test_a_file_deleted_while_the_plan_was_shown_writes_nothing(self):
        with self.staged_as(self.newer(SKILL)):
            self.stopped(1, "nothing was written", during=lambda: os.remove(self.full(SKILL)))

    def test_a_file_swapped_for_a_link_while_the_plan_was_shown_writes_nothing(self):
        with self.staged_as(self.newer(SKILL)):
            self.stopped(1, "nothing was written", during=lambda: self.swap_for_link(SKILL))

    def late(self, change, tamper):
        """Run with `tamper` called after the plan was rebuilt and before the first write. The run must refuse and leave the
        tree as `tamper` left it."""
        real, seen = rerender._write, []

        def write(*args, **kwargs):
            tamper()
            seen.append(self.snapshot())
            return real(*args, **kwargs)

        with unittest.mock.patch.object(rerender, "_write", write):
            code, out, err = self.run_with(change)
        self.assertEqual(1, len(seen), out + err)
        self.assertEqual(1, code, out + err)
        self.assertIn("nothing was written", err)
        self.assertEqual(seen[0], self.snapshot(), "a refused run wrote something")
        return err

    def test_a_stale_file_changed_after_the_rebuild_is_found_by_the_re_read(self):
        err = self.late(self.newer(SKILL), lambda: self.put_disk(SKILL, b"changed late\n"))
        self.assertIn(SKILL, err)

    def test_a_stale_file_deleted_after_the_rebuild_is_found_by_the_re_read(self):
        self.late(self.newer(SKILL), lambda: os.remove(self.full(SKILL)))

    def test_a_stale_file_swapped_for_a_link_after_the_rebuild_is_found_by_the_re_read(self):
        self.late(self.newer(SKILL), lambda: self.swap_for_link(SKILL))

    def test_a_file_that_appeared_at_the_path_of_a_new_file_is_found_by_the_re_read(self):
        err = self.late(self.adding(EXTRA, NEW_TEXT), lambda: self.put_disk(EXTRA, b"somebody's file\n"))
        self.assertIn(EXTRA, err)

    def test_an_applied_file_changed_after_the_rebuild_is_found_by_the_re_read(self):
        data = self.disk(SKILL) + b"More.\n"
        self.put_disk(SKILL, data)
        self.late(self.with_data(SKILL, data), lambda: self.put_disk(SKILL, b"changed late\n"))

    def test_a_file_changed_after_the_first_replacement_stops_the_run_with_the_two_lists(self):
        self.loosened()
        real = projectfs.Writer.replace_file

        def replace(writer, rel, expected, data, **kwargs):
            real(writer, rel, expected, data, **kwargs)
            if rel == AGENT:
                self.put_disk(SKILL, b"changed after the first replacement\n")

        with unittest.mock.patch.object(projectfs.Writer, "replace_file", replace):
            code, out, err = self.run_with(chained(self.newer(AGENT), self.newer(SKILL)))
        self.assertEqual(3, code, out)
        self.assertIn("failed: ", err)
        self.assertRegex(err, r"(?s)written:\n  %s\n.*not written:\n  %s\n  %s\n  %s\n  rendering record" % (
            re.escape(AGENT), re.escape(SKILL), re.escape(SETTINGS), re.escape(LOCAL)))
        self.assertEqual(b"changed after the first replacement\n", self.disk(SKILL))
        self.assertEqual("block", self.level("wb install"))

    def test_an_applied_file_changed_after_the_first_replacement_stops_before_the_manifest_names_its_hash(self):
        data = self.disk(SKILL) + b"More.\n"
        self.put_disk(SKILL, data)
        real = projectfs.Writer.replace_file

        def replace(writer, rel, expected, data, **kwargs):
            real(writer, rel, expected, data, **kwargs)
            self.put_disk(SKILL, b"changed after the first replacement\n")

        with unittest.mock.patch.object(projectfs.Writer, "replace_file", replace):
            code, out, err = self.run_with(chained(self.newer(AGENT), self.with_data(SKILL, data)))
        self.assertEqual(3, code, out)
        self.assertRegex(err, r"(?s)written:\n  %s\n.*not written:\n  %s\n" % (re.escape(AGENT), re.escape(LOCAL)))
        self.assertNotEqual(sha(data), self.listed()[SKILL])

    # --- a stop partway, and the run that finishes it ---

    def fail_replacing(self, rel):
        real = projectfs.Writer.replace_file

        def replace(writer, path, expected, data, **kwargs):
            if path == rel:
                raise OSError("forced")
            return real(writer, path, expected, data, **kwargs)

        return unittest.mock.patch.object(projectfs.Writer, "replace_file", replace)

    def stops_then_finishes(self, patch, applied):
        change = self.all_changed()
        self.loosened()
        with patch:
            code, out, err = self.run_with(change)
        self.assertEqual(3, code, out + err)
        self.assertIn("failed: forced", err)
        self.assertEqual("block", self.level("wb install"))
        code, out, err = self.run_with(change)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual("none", self.level("wb install"))
        for path in applied:
            self.assertIn("  %s: left as it is (applied)\n" % path, out)
        self.agrees()
        with self.staged_as(change):
            self.assertIn("nothing to change", self.shown())

    def test_a_stop_after_some_files_leaves_the_keys_at_block_and_a_second_run_finishes(self):
        self.stops_then_finishes(self.fail_replacing(SKILL), (AGENT, EXTRA))

    def test_a_stop_after_the_permissions_file_leaves_the_keys_at_block_and_a_second_run_finishes(self):
        self.stops_then_finishes(unittest.mock.patch.object(localmanifest, "replace", side_effect=OSError("forced")),
                                 (AGENT, EXTRA, SKILL))

    def test_a_stop_after_the_manifest_leaves_the_keys_at_block_and_a_second_run_finishes(self):
        # The manifest was written before the stop, so the second run finds every file current and only the record to write.
        self.stops_then_finishes(unittest.mock.patch.object(rendering, "write", side_effect=OSError("forced")), ())

    def test_the_manifest_is_complete_when_the_record_is_written(self):
        self.loosened()
        seen = []
        real = rendering.write

        def write(*args, **kwargs):
            self.agrees()
            seen.append(1)
            return real(*args, **kwargs)

        with unittest.mock.patch.object(rendering, "write", write):
            self.assertEqual(0, self.run_with(self.all_changed())[0])
        self.assertEqual([1], seen)

    def test_an_interrupt_right_after_a_file_was_renamed_is_reported_as_written(self):
        real = projectfs.Writer.replace_file

        def replace(writer, rel, expected, data, **kwargs):
            real(writer, rel, expected, data, **kwargs)
            raise KeyboardInterrupt

        with unittest.mock.patch.object(projectfs.Writer, "replace_file", replace):
            code, out, err = self.run_with(self.newer(SKILL))
        self.assertEqual(3, code, out)
        self.assertRegex(err, r"(?s)written:\n  %s\n.*not written:\n  %s\n" % (re.escape(SKILL), re.escape(LOCAL)))

    def test_a_file_partly_written_when_the_create_failed_is_named_and_must_be_removed_before_the_next_run(self):
        change = self.adding(EXTRA, NEW_TEXT)

        def create(writer, rel, data, executable=False):
            self.put_disk(rel, data[:3])
            writer.written.append(rel)
            raise OSError("forced")

        with unittest.mock.patch.object(projectfs.Writer, "create_file", create):
            code, out, err = self.run_with(change)
        self.assertEqual(3, code, out)
        self.assertIn("failed: forced", err)
        self.assertIn("%s may be partly written" % EXTRA, err)
        with self.staged_as(change):
            self.assertIn("unrecorded", self.refuses(EXTRA))
        os.remove(self.full(EXTRA))
        self.assertEqual(0, self.run_with(change)[0])
        self.agrees()


class Nothing(Base):
    def test_the_preview_writes_nothing_in_any_state(self):
        os.remove(self.full(AGENT))
        # `shown` compares the project and the store before and after.
        self.out_of(self.adding(EXTRA, b"A new skill.\n"))


if __name__ == "__main__":
    unittest.main()

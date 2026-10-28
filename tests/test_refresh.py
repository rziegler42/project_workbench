"""``wb preview rerender``: the state of every rendered file but the permissions file, read only.

Plan ``2026-10-28-refresh-rendered-harness``, increment A (``docs/specs/harness-refresh.md``). The project and the synthetic
harness are those of ``test_rerender``; the harness is attached and a source is then changed by replacing what the staging
returns, since the fixture's packages are verified against what the project records."""

import contextlib
import hashlib
import os
import re
import unittest
import unittest.mock

from tests import test_attach, test_rerender
from tests.test_rerender import DIGEST, LOCAL, SETTINGS
from workbench import attach, harnessplan, rerender, target

SKILL = ".fixture/skills/sample/SKILL.md"
AGENT = ".fixture/agents/reviewer.md"
COMMAND = ".fixture/commands/ship.md"
ROOT = "FIXTURE.md"
EXTRA = ".fixture/skills/extra/SKILL.md"
OLD_TEXT = b"Do the thing."


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


class Interim(Base):
    """Until Increment B writes the files, `wb rerender` must not write a manifest that names hashes of files it did not
    write. This class is removed by that increment."""

    def test_rerender_refuses_a_plan_with_files_to_write_and_writes_nothing(self):
        from workbench import approve, cli
        import io
        os.remove(self.full(AGENT))
        patch = unittest.mock.patch.object(approve, "is_terminal", lambda stream: True)
        patch.start()
        self.addCleanup(patch.stop)
        before = self.snapshot()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["rerender", self.place, "--package", self.pkg, "--package", self.synth], out, err,
                        store_root=self.store_root, home=self.home, distribution=self.dist,
                        stdin=test_rerender.Ticks(out, None, None))
        self.assertEqual(1, code, out.getvalue() + err.getvalue())
        self.assertIn("not built", err.getvalue())
        self.assertEqual(before, self.snapshot())


class Nothing(Base):
    def test_the_preview_writes_nothing_in_any_state(self):
        os.remove(self.full(AGENT))
        # `shown` compares the project and the store before and after.
        self.out_of(self.adding(EXTRA, b"A new skill.\n"))


if __name__ == "__main__":
    unittest.main()

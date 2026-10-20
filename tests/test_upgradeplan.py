import copy
import hashlib
import os
import unittest

from tests import test_installed as fixture
from workbench import installed, installplan, manifest, upgradeplan
from workbench.upgradeplan import (APPEND, CONFLICT, CREATE, REPLACE, SKIP, UpgradeError)

SCRIPT = ".workbench/p/notes/scripts/run.sh"
NOTES2 = ({"writes": ["docs/notes.md"], "ships": ["scripts/run.sh"]},
          {"files/docs/notes.md": b"# Notes v2\n", "scripts/run.sh": b"#!/bin/sh\necho 2\n"})
EXTRA = ({"writes": ["docs/c.md"]}, {"files/docs/c.md": b"# C\n"})


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Upgrade(fixture.Fixture):
    """An installed project, and upgrades planned over it."""

    def modules(self, **changes):
        modules = dict(fixture.MODULES)
        modules.update(changes)
        return modules

    def baselines(self):
        return {a.path: a.hash for a in self.made.actions
                if a.kind == "create-file" and a.path != installplan.MARKER_PATH}

    def upgrade(self, modules=None, names=None, mode="upgrade", version="0.1.0", baselines=None):
        path = self.package("p", modules or fixture.MODULES)
        selection, snaps = self.select(path, names or fixture.NAMES)
        return upgradeplan.build(self.read(), self.writer(), baselines or self.baselines(),
                                 selection, snaps, self.base, version, mode)

    def rows(self, plan, kind=None):
        return {(r.path, r.block): r for r in plan.rows if kind is None or r.kind == kind}

    def kinds(self, plan):
        return {(r.path, r.block): r.kind for r in plan.rows}

    def apply(self, plan):
        for write in plan.writes:
            full = self.path(write.path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as handle:
                handle.write(write.data)

    def disk(self, rel):
        with open(self.path(rel), "rb") as handle:
            return handle.read()

    def entry(self, plan, path, block=None):
        found = [e for e in plan.document["files"]
                 if e["path"] == path and e.get("block") == block]
        self.assertEqual(1, len(found), (path, block))
        return found[0]


class Unchanged(Upgrade):
    def test_the_same_modules_change_nothing(self):
        plan = self.upgrade()
        self.assertEqual({SKIP}, {r.kind for r in plan.rows})
        self.assertEqual((), plan.writes)
        self.assertEqual(self.baselines(), plan.baselines)
        self.assertEqual(self.made.manifest, plan.document)

    def test_building_the_plan_writes_nothing(self):
        before = {}
        for where, _, names in os.walk(self.project):
            for name in names:
                full = os.path.join(where, name)
                before[full] = self.disk(os.path.relpath(full, self.project))
        self.upgrade(self.modules(notes=NOTES2, c=EXTRA), fixture.NAMES + ["c"])
        after = {}
        for where, _, names in os.walk(self.project):
            for name in names:
                full = os.path.join(where, name)
                after[full] = self.disk(os.path.relpath(full, self.project))
        self.assertEqual(before, after)

    def test_a_new_workbench_version_rewrites_only_the_manifest(self):
        plan = self.upgrade(version="0.2.0")
        self.assertEqual([".workbench/manifest.json"], upgradeplan.written_paths(plan))
        self.assertEqual("0.2.0", plan.document["workbench"])
        self.assertEqual(self.made.manifest["seed"], plan.document["seed"])
        old = self.baselines()
        changed = {p for p in plan.baselines if plan.baselines[p] != old.get(p)}
        self.assertEqual({".workbench/manifest.json"}, changed)
        self.assertEqual(sha(plan.manifest_bytes), plan.baselines[".workbench/manifest.json"])
        write = plan.writes[0]
        self.assertEqual(("replace", self.read().manifest_hash), (write.op, write.expected))

    def test_an_unknown_mode_is_refused(self):
        with self.assertRaises(UpgradeError):
            self.upgrade(mode="delete")


class ModuleOwned(Upgrade):
    def newer(self):
        return self.upgrade(self.modules(notes=NOTES2))

    def test_a_changed_file_that_is_as_installed_is_replaced(self):
        plan = self.newer()
        self.assertEqual(REPLACE, self.kinds(plan)[(SCRIPT, None)])
        write = [w for w in plan.writes if w.path == SCRIPT][0]
        self.assertEqual("replace", write.op)
        self.assertEqual(b"#!/bin/sh\necho 2\n", write.data)
        self.assertEqual(self.baselines()[SCRIPT], write.expected)
        self.assertEqual(sha(write.data), self.entry(plan, SCRIPT)["hash"])
        self.assertEqual(sha(write.data), plan.baselines[SCRIPT])

    def test_the_namespace_copy_of_the_whole_tree_is_replaced_file_by_file(self):
        replaced = {p for (p, b), r in self.rows(self.newer()).items() if r.kind == REPLACE}
        self.assertEqual({SCRIPT, ".workbench/p/notes/files/docs/notes.md",
                          ".workbench/manifest.json"}, replaced)

    def test_the_seeded_file_a_module_writes_is_never_touched(self):
        row = self.rows(self.newer())[("docs/notes.md", None)]
        self.assertEqual(SKIP, row.kind)
        self.assertIn("newer version", row.detail)
        self.assertNotIn("docs/notes.md", upgradeplan.written_paths(self.newer()))
        self.assertEqual(self.baselines()["docs/notes.md"],
                         self.newer().baselines["docs/notes.md"])

    def test_a_file_the_project_edited_is_a_conflict_and_keeps_its_entry(self):
        self.rewrite(SCRIPT, lambda data: data + b"# mine\n")
        plan = self.newer()
        row = self.rows(plan)[(SCRIPT, None)]
        self.assertEqual(CONFLICT, row.kind)
        self.assertIn("edited", row.detail)
        self.assertNotIn(SCRIPT, upgradeplan.written_paths(plan))
        self.assertEqual(self.entry_of(SCRIPT), self.entry(plan, SCRIPT))
        self.assertEqual(self.baselines()[SCRIPT], plan.baselines[SCRIPT])

    def entry_of(self, path, block=None):
        return [e for e in self.made.manifest["files"]
                if e["path"] == path and e.get("block") == block][0]

    def test_a_file_the_project_removed_is_a_conflict_and_is_not_restored(self):
        os.unlink(self.path(SCRIPT))
        plan = self.newer()
        row = self.rows(plan)[(SCRIPT, None)]
        self.assertEqual(CONFLICT, row.kind)
        self.assertIn("not restored", row.detail)
        self.assertNotIn(SCRIPT, upgradeplan.written_paths(plan))

    def test_a_removed_file_that_did_not_change_is_a_skip(self):
        os.unlink(self.path(SCRIPT))
        self.assertEqual(SKIP, self.kinds(self.upgrade())[(SCRIPT, None)])

    def test_a_link_in_the_way_is_a_conflict(self):
        os.unlink(self.path(SCRIPT))
        os.symlink("/etc/hostname", self.path(SCRIPT))
        plan = self.newer()
        self.assertEqual(CONFLICT, self.kinds(plan)[(SCRIPT, None)])
        self.assertNotIn(SCRIPT, upgradeplan.written_paths(plan))

    def test_add_never_replaces(self):
        with self.assertRaises(UpgradeError) as caught:
            self.upgrade(self.modules(notes=NOTES2), mode="add")
        self.assertIn("add never replaces", str(caught.exception))
        self.assertIn(".workbench/p/notes/", str(caught.exception))

    def test_add_with_nothing_to_replace_is_allowed(self):
        plan = self.upgrade(self.modules(c=EXTRA), fixture.NAMES + ["c"], mode="add")
        self.assertEqual("add", plan.mode)
        self.assertEqual(CREATE, self.kinds(plan)[("docs/c.md", None)])


class Hostile(Upgrade):
    def retag(self, path, **changes):
        document = copy.deepcopy(self.made.manifest)
        for item in document["files"]:
            if item["path"] == path and "block" not in item:
                item.update(changes)
        with open(self.path(".workbench/manifest.json"), "wb") as handle:
            handle.write(manifest.serialize(document))

    def test_a_class_the_declaration_does_not_give_is_a_conflict(self):
        self.retag(SCRIPT, **{"class": "seeded"})
        plan = self.upgrade(self.modules(notes=NOTES2))
        row = self.rows(plan)[(SCRIPT, None)]
        self.assertEqual(CONFLICT, row.kind)
        self.assertIn("seeded", row.detail)
        self.assertNotIn(SCRIPT, upgradeplan.written_paths(plan))

    def test_a_seeded_file_recorded_as_module_owned_is_not_replaced(self):
        agents = [e for e in self.made.manifest["files"]
                  if e["path"] == "AGENTS.md" and "block" not in e][0]
        self.retag("AGENTS.md", **{"class": "module-owned"})
        plan = self.upgrade()
        self.assertEqual(CONFLICT, self.kinds(plan)[("AGENTS.md", None)])
        self.assertNotIn("AGENTS.md", upgradeplan.written_paths(plan))
        self.assertEqual(agents["hash"], self.entry(plan, "AGENTS.md")["hash"])

    def test_a_new_block_into_a_file_recorded_as_module_owned_is_a_conflict(self):
        self.retag("AGENTS.md", **{"class": "module-owned"})
        plan = self.upgrade(self.modules(c=fixture.FILL(b"Rule C\n")), fixture.NAMES + ["c"])
        self.assertEqual(CONFLICT, self.kinds(plan)[("AGENTS.md", "p/c")])
        self.assertNotIn("AGENTS.md", upgradeplan.written_paths(plan))

    CHANGED_A = fixture.FILL(b"Rule A, changed\n")

    def test_a_changed_block_in_a_file_recorded_as_module_owned_is_not_written(self):
        self.retag("AGENTS.md", **{"class": "module-owned"})
        plan = self.upgrade(self.modules(a=self.CHANGED_A))
        self.assertEqual(CONFLICT, self.kinds(plan)[("AGENTS.md", "p/a")])
        self.assertNotIn("AGENTS.md", upgradeplan.written_paths(plan))

    def test_a_changed_block_in_a_file_the_manifest_does_not_record_is_not_written(self):
        document = copy.deepcopy(self.made.manifest)
        document["files"] = [e for e in document["files"]
                             if not (e["path"] == "AGENTS.md" and "block" not in e)]
        with open(self.path(".workbench/manifest.json"), "wb") as handle:
            handle.write(manifest.serialize(document))
        plan = self.upgrade(self.modules(a=self.CHANGED_A))
        row = self.rows(plan)[("AGENTS.md", "p/a")]
        self.assertEqual(CONFLICT, row.kind)
        self.assertIn("not recorded", row.detail)
        self.assertNotIn("AGENTS.md", upgradeplan.written_paths(plan))

    def test_a_changed_block_in_a_file_that_is_a_link_is_not_written(self):
        os.unlink(self.path("AGENTS.md"))
        os.symlink("/etc/hostname", self.path("AGENTS.md"))
        plan = self.upgrade(self.modules(a=self.CHANGED_A))
        self.assertEqual(CONFLICT, self.kinds(plan)[("AGENTS.md", "p/a")])
        self.assertNotIn("AGENTS.md", upgradeplan.written_paths(plan))

    def test_building_at_a_lower_version_than_the_manifest_records_is_refused(self):
        document = copy.deepcopy(self.made.manifest)
        document["workbench"] = "0.2.0"
        with open(self.path(".workbench/manifest.json"), "wb") as handle:
            handle.write(manifest.serialize(document))
        existing = installed.read(self.writer(), "0.2.0")
        path = self.package("p", fixture.MODULES)
        selection, snaps = self.select(path, fixture.NAMES)
        with self.assertRaises(UpgradeError) as caught:
            upgradeplan.build(existing, self.writer(), self.baselines(), selection, snaps,
                              self.base, "0.1.0", "upgrade")
        self.assertIn("newer", str(caught.exception))

    def test_a_fill_into_a_slot_the_base_does_not_have_is_refused(self):
        nowhere = ({"fills": [{"slot": "slot:nowhere", "source": "x.md"}]}, {"x.md": b"x\n"})
        with self.assertRaises(UpgradeError) as caught:
            self.upgrade(self.modules(c=nowhere), fixture.NAMES + ["c"])
        self.assertIn("nowhere", str(caught.exception))

    def add_entry(self, path, owner):
        document = copy.deepcopy(self.made.manifest)
        document["files"].append({"class": owner, "hash": "0" * 64, "path": path})
        document["files"].sort(key=lambda e: (e["path"].encode(), e.get("block", "")))
        with open(self.path(".workbench/manifest.json"), "wb") as handle:
            handle.write(manifest.serialize(document))

    def test_a_module_owned_entry_outside_the_namespace_is_a_conflict_never_written(self):
        self.add_entry("docs/plans/2026-01-01-x.md", "module-owned")
        plan = self.upgrade()
        self.assertEqual(CONFLICT, self.kinds(plan)[("docs/plans/2026-01-01-x.md", None)])
        self.assertNotIn("docs/plans/2026-01-01-x.md", upgradeplan.written_paths(plan))
        self.assertEqual("0" * 64, self.entry(plan, "docs/plans/2026-01-01-x.md")["hash"])

    def test_a_seeded_entry_with_no_counterpart_is_left_in_place(self):
        self.add_entry("docs/plans/2026-01-01-y.md", "seeded")
        row = self.rows(self.upgrade())[("docs/plans/2026-01-01-y.md", None)]
        self.assertEqual((SKIP, "left in place"), (row.kind, row.detail))

    def test_an_entry_in_another_slot_is_a_conflict(self):
        document = copy.deepcopy(self.made.manifest)
        for item in document["files"]:
            if item.get("block") == "p/a":
                item["slot"] = "other"
        with open(self.path(".workbench/manifest.json"), "wb") as handle:
            handle.write(manifest.serialize(document))
        plan = self.upgrade()
        self.assertEqual(CONFLICT, self.kinds(plan)[("AGENTS.md", "p/a")])

    def test_a_manifest_that_collides_in_case_with_a_new_path_is_refused(self):
        self.add_entry("DOCS/c.md", "seeded")
        with self.assertRaises(UpgradeError):
            self.upgrade(self.modules(c=EXTRA), fixture.NAMES + ["c"])


class NewFiles(Upgrade):
    def test_a_new_module_creates_its_files_and_is_recorded(self):
        plan = self.upgrade(self.modules(c=EXTRA), fixture.NAMES + ["c"])
        kinds = self.kinds(plan)
        self.assertEqual(CREATE, kinds[("docs/c.md", None)])
        self.assertEqual(CREATE, kinds[(".workbench/p/c/module.json", None)])
        creates = {w.path: w for w in plan.writes if w.op == "create"}
        self.assertEqual(b"# C\n", creates["docs/c.md"].data)
        self.assertIsNone(creates["docs/c.md"].expected)
        self.assertEqual("seeded", self.entry(plan, "docs/c.md")["class"])
        self.assertEqual(sha(b"# C\n"), plan.baselines["docs/c.md"])
        names = [m["name"] for p in plan.document["packages"] for m in p["modules"]]
        self.assertEqual(["a", "b", "c", "notes"], sorted(names))

    def test_a_path_that_exists_is_a_conflict_and_gets_no_entry(self):
        with open(self.path("docs/c.md"), "wb") as handle:
            handle.write(b"mine\n")
        plan = self.upgrade(self.modules(c=EXTRA), fixture.NAMES + ["c"])
        self.assertEqual(CONFLICT, self.kinds(plan)[("docs/c.md", None)])
        self.assertNotIn("docs/c.md", upgradeplan.written_paths(plan))
        self.assertNotIn("docs/c.md", [e["path"] for e in plan.document["files"]])
        self.assertNotIn("docs/c.md", plan.baselines)

    def test_a_directory_in_the_way_is_a_conflict(self):
        os.mkdir(self.path("docs/c.md"))
        plan = self.upgrade(self.modules(c=EXTRA), fixture.NAMES + ["c"])
        self.assertEqual(CONFLICT, self.kinds(plan)[("docs/c.md", None)])

    def test_a_link_at_a_parent_is_a_conflict(self):
        elsewhere = os.path.join(self.root, "elsewhere")
        os.mkdir(elsewhere)
        os.symlink(elsewhere, self.path(".workbench/p/c"))
        plan = self.upgrade(self.modules(c=EXTRA), fixture.NAMES + ["c"])
        self.assertEqual(CONFLICT, self.kinds(plan)[(".workbench/p/c/module.json", None)])
        self.assertEqual([], os.listdir(elsewhere))


class Blocks(Upgrade):
    C = fixture.FILL(b"Rule C\n")

    def with_c(self, **more):
        return self.upgrade(self.modules(c=self.C, **more), fixture.NAMES + ["c"] + list(more))

    def agents(self, plan):
        return [w for w in plan.writes if w.path == "AGENTS.md"][0]

    def test_a_new_block_goes_before_the_marker(self):
        plan = self.with_c()
        self.assertEqual(CREATE, self.kinds(plan)[("AGENTS.md", "p/c")])
        before = self.disk("AGENTS.md")
        write = self.agents(plan)
        self.assertEqual("replace", write.op)
        self.assertEqual(sha(before), write.expected)
        marker = b"<!-- @slot: policy -->\n"
        block = b"<!-- BEGIN p/c slot:policy -->\nRule C\n<!-- END p/c slot:policy -->\n"
        self.assertEqual(before.replace(marker, block + marker), write.data)
        self.assertEqual(sha(write.data), plan.baselines["AGENTS.md"])
        self.assertEqual(sha(block), self.entry(plan, "AGENTS.md", "p/c")["hash"])

    def test_the_file_entry_of_a_filled_seeded_file_is_unchanged(self):
        plan = self.with_c()
        self.assertEqual(self.entry_in_made("AGENTS.md"), self.entry(plan, "AGENTS.md"))

    def entry_in_made(self, path):
        return [e for e in self.made.manifest["files"]
                if e["path"] == path and "block" not in e][0]

    def test_one_write_covers_every_block_of_a_file(self):
        plan = self.with_c(d=fixture.FILL(b"Rule D\n"))
        self.assertEqual(1, [w.path for w in plan.writes].count("AGENTS.md"))
        data = self.agents(plan).data
        self.assertLess(data.index(b"Rule C"), data.index(b"Rule D"))
        self.assertEqual(CREATE, self.kinds(plan)[("AGENTS.md", "p/d")])

    def test_a_changed_block_is_replaced_and_nothing_else_moves(self):
        plan = self.upgrade(self.modules(a=fixture.FILL(b"Rule A, changed\n")))
        self.assertEqual(REPLACE, self.kinds(plan)[("AGENTS.md", "p/a")])
        before, after = self.disk("AGENTS.md"), self.agents(plan).data
        self.assertEqual(before.replace(b"Rule A\n", b"Rule A, changed\n"), after)

    def test_a_block_the_project_edited_is_a_conflict(self):
        self.rewrite("AGENTS.md", lambda data: data.replace(b"Rule A\n", b"Rule A mine\n"))
        plan = self.upgrade(self.modules(a=fixture.FILL(b"Rule A, changed\n")))
        self.assertEqual(CONFLICT, self.kinds(plan)[("AGENTS.md", "p/a")])
        self.assertNotIn("AGENTS.md", upgradeplan.written_paths(plan))

    def test_add_never_replaces_a_block(self):
        with self.assertRaises(UpgradeError):
            self.upgrade(self.modules(a=fixture.FILL(b"Rule A, changed\n")), mode="add")

    def remove_block(self, who):
        def edit(data):
            start = data.index(b"<!-- BEGIN %s " % who)
            end = data.index(b"<!-- END %s " % who)
            return data[:start] + data[data.index(b"\n", end) + 1:]
        self.rewrite("AGENTS.md", edit)

    def test_a_block_whose_markers_are_gone_is_skipped_and_stays_recorded(self):
        self.remove_block(b"p/a")
        plan = self.upgrade(self.modules(a=fixture.FILL(b"Rule A, changed\n")))
        row = self.rows(plan)[("AGENTS.md", "p/a")]
        self.assertEqual((SKIP, "slot gone"), (row.kind, row.detail))
        self.assertEqual(self.entry_in_made_block("p/a"), self.entry(plan, "AGENTS.md", "p/a"))
        self.assertNotIn("AGENTS.md", upgradeplan.written_paths(plan))

    def entry_in_made_block(self, who):
        return [e for e in self.made.manifest["files"] if e.get("block") == who][0]

    def test_a_block_the_project_removed_is_not_put_back_by_the_next_upgrade(self):
        self.remove_block(b"p/a")
        first = self.upgrade(self.modules(c=self.C), fixture.NAMES + ["c"])
        self.apply(first)
        second = self.upgrade(self.modules(c=self.C), fixture.NAMES + ["c"],
                              baselines=first.baselines)
        self.assertEqual("slot gone", self.rows(second)[("AGENTS.md", "p/a")].detail)
        self.assertEqual((), second.writes)
        self.assertNotIn(b"Rule A", self.disk("AGENTS.md"))

    def test_a_block_present_but_not_recorded_is_a_conflict(self):
        document = copy.deepcopy(self.made.manifest)
        document["files"] = [e for e in document["files"] if e.get("block") != "p/a"]
        with open(self.path(".workbench/manifest.json"), "wb") as handle:
            handle.write(manifest.serialize(document))
        plan = self.upgrade()
        row = self.rows(plan)[("AGENTS.md", "p/a")]
        self.assertEqual(CONFLICT, row.kind)
        self.assertIn("does not record", row.detail)

    def test_a_missing_slot_marker_appends_the_block_and_then_the_marker(self):
        self.rewrite("AGENTS.md", lambda data: data.replace(b"<!-- @slot: policy -->\n", b""))
        plan = self.with_c()
        row = self.rows(plan)[("AGENTS.md", "p/c")]
        self.assertEqual(APPEND, row.kind)
        before = self.disk("AGENTS.md")
        self.assertEqual(before + b"<!-- BEGIN p/c slot:policy -->\nRule C\n"
                         b"<!-- END p/c slot:policy -->\n<!-- @slot: policy -->\n",
                         self.agents(plan).data)

    def test_after_an_append_the_block_reads_as_installed(self):
        self.rewrite("AGENTS.md", lambda data: data.replace(b"<!-- @slot: policy -->\n", b""))
        modules, names = self.modules(c=self.C), fixture.NAMES + ["c"]
        first = self.upgrade(modules, names)
        self.apply(first)
        states = {(e.path, e.block): e.state for e in self.read().entries}
        self.assertEqual(installed.AS_INSTALLED, states[("AGENTS.md", "p/c")])
        self.assertEqual(installed.AS_INSTALLED, states[("AGENTS.md", None)])
        second = self.upgrade(modules, names, baselines=first.baselines)
        self.assertEqual((), second.writes)

    def test_two_blocks_into_a_slot_without_a_marker_append_then_insert(self):
        self.rewrite("AGENTS.md", lambda data: data.replace(b"<!-- @slot: policy -->\n", b""))
        plan = self.with_c(d=fixture.FILL(b"Rule D\n"))
        kinds = self.kinds(plan)
        self.assertEqual((APPEND, CREATE), (kinds[("AGENTS.md", "p/c")],
                                            kinds[("AGENTS.md", "p/d")]))
        data = self.agents(plan).data
        self.assertEqual(1, data.count(b"<!-- @slot: policy -->"))
        self.assertLess(data.index(b"Rule C"), data.index(b"Rule D"))

    def test_an_appended_file_without_a_final_line_feed_gets_one(self):
        self.rewrite("AGENTS.md", lambda data: data.replace(b"<!-- @slot: policy -->\n", b"")
                     .rstrip(b"\n"))
        data = self.agents(self.with_c()).data
        self.assertIn(b"\n<!-- BEGIN p/c slot:policy -->\n", data)

    def test_a_file_the_project_removed_gets_no_block(self):
        os.unlink(self.path("AGENTS.md"))
        plan = self.with_c()
        row = self.rows(plan)[("AGENTS.md", "p/c")]
        self.assertEqual(CONFLICT, row.kind)
        self.assertIn("not restored", row.detail)
        self.assertNotIn("AGENTS.md", upgradeplan.written_paths(plan))

    def test_a_link_in_place_of_the_file_gets_no_block(self):
        os.unlink(self.path("AGENTS.md"))
        os.symlink("/etc/hostname", self.path("AGENTS.md"))
        plan = self.with_c()
        self.assertEqual(CONFLICT, self.kinds(plan)[("AGENTS.md", "p/c")])
        self.assertNotIn("AGENTS.md", upgradeplan.written_paths(plan))

    def test_a_marker_twice_is_a_conflict(self):
        self.rewrite("AGENTS.md", lambda data: data + b"<!-- @slot: policy -->\n")
        plan = self.with_c()
        self.assertEqual(CONFLICT, self.kinds(plan)[("AGENTS.md", "p/c")])
        self.assertNotIn("AGENTS.md", upgradeplan.written_paths(plan))

    def test_a_malformed_marker_is_a_conflict(self):
        self.rewrite("AGENTS.md", lambda data: data + b"<!-- BEGIN broken -->\n")
        plan = self.with_c()
        self.assertEqual(CONFLICT, self.kinds(plan)[("AGENTS.md", "p/c")])

    def test_an_empty_fill_comes_out_as_the_declaration_gives_it(self):
        plan = self.upgrade(self.modules(e=fixture.FILL(b"")), fixture.NAMES + ["e"])
        self.assertEqual(CREATE, self.kinds(plan)[("AGENTS.md", "p/e")])
        block = b"<!-- BEGIN p/e slot:policy -->\n\n<!-- END p/e slot:policy -->\n"
        self.assertIn(block, self.agents(plan).data)
        self.assertEqual(sha(block), self.entry(plan, "AGENTS.md", "p/e")["hash"])

    def test_after_the_plan_is_applied_everything_reads_as_installed_and_a_second_is_empty(self):
        modules = self.modules(notes=NOTES2, c=self.C, a=fixture.FILL(b"Rule A, changed\n"))
        names = fixture.NAMES + ["c"]
        first = self.upgrade(modules, names)
        self.apply(first)
        states = {e.state for e in self.read().entries}
        self.assertEqual({installed.AS_INSTALLED}, states)
        second = self.upgrade(modules, names, baselines=first.baselines)
        self.assertEqual((), second.writes)
        self.assertEqual({SKIP}, {r.kind for r in second.rows})
        self.assertEqual(first.baselines, second.baselines)

    def test_a_module_not_in_the_selection_is_not_lost_from_the_manifest(self):
        plan = self.upgrade(names=["h", "notes", "a"])
        left = self.rows(plan)[("AGENTS.md", "p/b")]
        self.assertEqual((SKIP, "left in place"), (left.kind, left.detail))
        names = {m["name"] for p in plan.document["packages"] for m in p["modules"]}
        self.assertIn("b", names)
        self.assertEqual(self.entry_in_made_block("p/b"), self.entry(plan, "AGENTS.md", "p/b"))

    def test_a_module_removed_upstream_is_left_in_place_and_nothing_is_deleted(self):
        plan = self.upgrade(names=["h", "notes", "a"])
        left = {k for k, r in self.rows(plan).items() if r.detail == "left in place"}
        self.assertIn((".workbench/p/b/module.json", None), left)
        self.assertEqual((), plan.writes)


if __name__ == "__main__":
    unittest.main()

import hashlib
import io
import json
import os
import shutil
import subprocess
import types
import unittest
import unittest.mock

from tests import support
from tests import test_preview as preview_tests
from tests import test_upgrade_preview as base_tests
from tests.test_neutral import AGENT, COMMAND, SKILL
from workbench import (acknowledgement, attach, cli, harnessplan, installplan, localmanifest,
                       manifest, neutral, projectfs, rules, safefs, snapshot, sources)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUDE = os.path.join(ROOT, "packages", "workbench")
HARNESS = base_tests.HARNESS
FILL = base_tests.FILL
NOTES2 = base_tests.NOTES2
LOCAL = localmanifest.PATH
SETTINGS = ".claude/settings.local.json"
NEUTRAL_FILES = {"harness/neutral/skills/sample/SKILL.md": SKILL,
                 "harness/neutral/agents/reviewer.md": AGENT,
                 "harness/neutral/commands/ship.md": COMMAND}
NOTES = ({"writes": ["docs/notes.md"], "ships": ["scripts/run.sh"]},
         dict({"files/docs/notes.md": b"# Notes\n", "scripts/run.sh": b"#!/bin/sh\n"},
              **NEUTRAL_FILES))
HARNESS_PATHS = ["CLAUDE.md", ".claude/agents/reviewer.md", ".claude/commands/ship.md",
                 ".claude/settings.local.json", ".claude/skills/sample/SKILL.md"]


class Base(base_tests.UpgradePreview):
    """A project installed the way `install` writes it, with neutral items in one of its modules,
    and the first-party Claude module to attach."""

    MODULES = {"h": (HARNESS, {}), "notes": NOTES, "a": FILL(b"Rule A\n")}
    skip_approval = ()

    def setUp(self):
        base_tests.UpgradePreview.setUp(self)
        self.home = os.path.join(self.root, "home")
        os.mkdir(self.home)
        self.outside = os.path.join(self.root, "outside")
        os.mkdir(self.outside)

    def approve(self, path, only=None):
        names = [name for name in self.MODULES if name not in self.skip_approval]
        preview_tests.PreviewTest.approve(self, path, only=names)

    def ready(self, **changes):
        self.pkg = self.version(**changes)
        self.install(self.pkg)
        return self.pkg

    def attach(self, *args, harness="workbench/claude", package=CLAUDE, place=None, packages=None):
        if package == CLAUDE:
            support.require_release(self)
        argv = ["attach", place or self.place, "--harness", harness]
        for given in (packages if packages is not None else [self.pkg] + ([package] if package else [])):
            argv += ["--package", given]
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(argv + list(args), out, err, store_root=self.store_root, home=self.home)
        return code, out.getvalue(), err.getvalue()

    def content(self, top=None):
        """Every file under `top` (default the project) and every directory, with its bytes."""
        top = top or self.place
        found = {}
        for base, dirs, files in os.walk(top):
            for name in dirs:
                full = os.path.join(base, name)
                found[os.path.relpath(full, top)] = "link" if os.path.islink(full) else "dir"
            for name in files:
                full = os.path.join(base, name)
                if os.path.islink(full):
                    found[os.path.relpath(full, top)] = "link"
                else:
                    with open(full, "rb") as handle:
                        found[os.path.relpath(full, top)] = handle.read()
        return found

    def refuses(self, *args, contains, **kwargs):
        before = (self.content(), self.content(self.store_root), self.content(self.outside))
        code, out, err = self.attach(*args, **kwargs)
        self.assertEqual((1, ""), (code, out), err)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertIn(contains, err)
        self.assertEqual(before, (self.content(), self.content(self.store_root),
                                  self.content(self.outside)))
        self.assertFalse(os.path.exists(os.path.join(self.place, *LOCAL.split("/"))))
        return err

    def local(self):
        return localmanifest.read(projectfs.Writer(self.held()))

    def held(self):
        from workbench import target
        held = target.open_target(self.place, self.store_root)
        self.addCleanup(held.close)
        return held

    def planned(self):
        with open(os.path.join(self.place, *LOCAL.split("/")), "rb") as handle:
            return localmanifest.parse(handle.read())

    def acknowledge(self, rel):
        baselines = acknowledgement.read_baselines(self.guarded, self.project_id)
        baselines[rel] = hashlib.sha256(self.read(rel)).hexdigest()
        full = os.path.join(self.store_root, "projects", self.project_id, "baselines")
        with open(full, "wb") as handle:
            handle.write(installplan.json_store({"baselines": baselines, "format": 1}))


class Attached(Base):
    def test_the_harness_files_exclude_lines_and_local_manifest_are_written(self):
        self.ready()
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        for path in HARNESS_PATHS:
            self.assertTrue(os.path.isfile(os.path.join(self.place, *path.split("/"))), path)
        self.assertEqual(b"@AGENTS.md\n", self.read("CLAUDE.md"))
        self.assertEqual(b"/CLAUDE.md\n/.claude/\n", self.read(".git/info/exclude"))
        document = self.planned()
        self.assertEqual("claude", document["harness"])
        self.assertEqual("0.1.0", document["module_version"])
        self.assertEqual("local:workbench", document["source"])
        self.assertEqual(sorted(HARNESS_PATHS), [f["path"] for f in document["files"]])
        for item in document["files"]:
            self.assertEqual(item["hash"], hashlib.sha256(self.read(item["path"])).hexdigest())
        verified = base_tests.verify.verify_package(CLAUDE, first_party=True).modules[0]
        self.assertEqual(verified.tree_hash, document["tree"])

    def test_the_report_names_the_files_the_warning_and_the_note(self):
        self.ready()
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertTrue(out.startswith("attached workbench/claude 0.1.0 in %s\n" % self.real
                                       if hasattr(self, "real") else "attached workbench/claude"))
        self.assertIn("wrote 5 files:\n", out)
        self.assertIn("  .claude/settings.local.json\n", out)
        self.assertIn("added 2 lines to .git/info/exclude: CLAUDE.md, .claude/\n", out)
        self.assertIn("recorded .workbench/local/harness.json\nnothing was committed\n", out)
        self.assertIn("note: Restart the Claude session to load the new settings.\n", out)
        self.assertIn("warning: .claude/settings.local.json changes what the agent may do", err)
        self.assertNotIn("harness not attached", out + err)

    def test_the_settings_deny_the_owner_run_commands_and_the_store_and_never_allow(self):
        self.ready()
        self.assertEqual(0, self.attach()[0])
        document = json.loads(self.read(SETTINGS))
        self.assertEqual(["permissions"], list(document))
        permissions = document["permissions"]
        self.assertEqual(["ask", "deny"], sorted(permissions))
        store = os.path.realpath(self.store_root).lstrip("/")
        for command in rules.OWNER_RUN:
            self.assertIn("Bash(wb %s)" % command, permissions["deny"])
            self.assertIn("Bash(wb %s *)" % command, permissions["deny"])
            self.assertIn("Bash(python3 -m workbench %s *)" % command, permissions["deny"])
        self.assertIn("Edit(//%s/**)" % store, permissions["deny"])
        self.assertNotIn("Bash(wb preview *)", permissions["deny"])
        self.assertIn("Bash(git push --force*)", permissions["ask"])

    def test_nothing_committed_and_nothing_else_in_the_project_or_store_changes(self):
        self.ready()
        before = self.content()
        store = self.content(self.store_root)
        self.assertEqual(0, self.attach()[0])
        after = self.content()
        for path, data in before.items():
            if path in (".git", ".git/info"):
                continue
            self.assertEqual(data, after[path], path)
        added = sorted(set(after) - set(before))
        self.assertEqual(sorted(HARNESS_PATHS + [".claude", ".claude/agents", ".claude/commands",
                                                 ".claude/skills", ".claude/skills/sample",
                                                 ".git/info", ".git/info/exclude", ".workbench/local",
                                                 LOCAL]),
                         added)
        self.assertEqual(store, self.content(self.store_root))
        self.assertEqual(b"index", self.read(".git/index"))

    def test_the_exclude_lines_come_first_and_the_local_manifest_last(self):
        self.ready()
        order = []
        create, add = projectfs.Writer.create_file, projectfs.Writer.add_exclude
        write = localmanifest.write

        def create_file(writer, rel, data, executable=False):
            order.append(rel)
            return create(writer, rel, data, executable)

        def add_exclude(writer, entries):
            order.append("exclude")
            return add(writer, entries)

        def write_local(writer, document):
            order.append("manifest")
            return write(writer, document)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", create_file), \
                unittest.mock.patch.object(projectfs.Writer, "add_exclude", add_exclude), \
                unittest.mock.patch.object(localmanifest, "write", write_local):
            self.assertEqual(0, self.attach()[0])
        self.assertEqual("exclude", order[0])
        self.assertEqual(["manifest", LOCAL], order[-2:])
        self.assertEqual(sorted(HARNESS_PATHS), sorted(order[1:-2]))

    def test_it_is_not_terminal_gated(self):
        support.require_release(self)
        self.ready()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["attach", self.place, "--harness", "workbench/claude", "--package",
                         self.pkg, "--package", CLAUDE], out, err, store_root=self.store_root,
                        home=self.home, stdin=io.StringIO(""))
        self.assertEqual(0, code, err.getvalue())

    def test_the_dir_option_names_the_target(self):
        support.require_release(self)
        self.ready()
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["attach", "--dir", self.place, "--harness", "workbench/claude",
                         "--package", self.pkg, "--package", CLAUDE], out, err,
                        store_root=self.store_root, home=self.home)
        self.assertEqual(0, code, err.getvalue())

    def test_a_project_written_by_an_older_workbench_warns_and_continues(self):
        self.ready()
        document = manifest.parse(self.read(".workbench/manifest.json"))
        document["workbench"] = "0.0.1"
        self.edit(".workbench/manifest.json", lambda data: manifest.serialize(document))
        self.acknowledge(".workbench/manifest.json")
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertIn("warning: the project was written by workbench 0.0.1 and this is ", err)


class Overrides(Base):
    """Overrides and exclusions in a module's `harness/<harness>/` reach the written files."""

    def override_notes(self, extra):
        files = dict(NOTES[1])
        files.update(extra)
        return (NOTES[0], files)

    def test_an_override_replaces_one_item_and_is_reported(self):
        replacement = b"---\nname: sample\n---\nThe claude-specific skill.\n"
        self.pkg = self.version(notes=self.override_notes(
            {"harness/claude/skills/sample/SKILL.md": replacement}))
        self.install(self.pkg)
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertEqual(replacement, self.read(".claude/skills/sample/SKILL.md"))
        self.assertIn("overridden: skill/sample: replaced by the module's own files", out)
        self.assertIn(b"Reviews changes", self.read(".claude/agents/reviewer.md"))

    def test_an_exclusion_stops_one_item_and_the_reason_is_reported(self):
        manifest_text = json.dumps({"exclude": [{"item": "commands/ship",
                                                 "reason": "no ship on claude"}]}).encode()
        self.pkg = self.version(notes=self.override_notes(
            {"harness/claude/manifest.json": manifest_text}))
        self.install(self.pkg)
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertFalse(os.path.exists(os.path.join(self.place, ".claude", "commands", "ship.md")))
        self.assertIn("excluded: command/ship: no ship on claude", out)
        self.assertNotIn(".claude/commands/ship.md", [f["path"] for f in self.planned()["files"]])

    def test_an_override_for_another_harness_is_left_alone(self):
        self.pkg = self.version(notes=self.override_notes(
            {"harness/other/skills/sample/SKILL.md": b"---\nname: sample\n---\nOther.\n"}))
        self.install(self.pkg)
        self.assertEqual(0, self.attach()[0])
        self.assertIn(b"Do the thing.", self.read(".claude/skills/sample/SKILL.md"))

    def test_an_agent_override_without_a_tools_list_is_skipped_not_installed(self):
        bare = b"---\nname: reviewer\ndescription: Reviews\n---\nAll tools.\n"
        self.pkg = self.version(notes=self.override_notes(
            {"harness/claude/agents/reviewer.md": bare}))
        self.install(self.pkg)
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertFalse(os.path.exists(os.path.join(self.place, ".claude", "agents")))
        self.assertIn("warning: skipped: agent/reviewer", err)

    def test_an_item_that_needs_hooks_is_skipped_because_the_module_does_not_provide_them(self):
        hooked = (b"---\nname: hooked\ndescription: Needs hooks\nneeds: hooks\n---\nBody.\n")
        self.pkg = self.version(notes=self.override_notes(
            {"harness/neutral/skills/hooked/SKILL.md": hooked}))
        self.install(self.pkg)
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertFalse(os.path.exists(os.path.join(self.place, ".claude", "skills", "hooked")))
        self.assertIn("warning: skipped: skill/hooked: needs hooks, which this harness does not "
                      "provide", err)

    def test_a_harness_that_provides_no_permissions_warns_and_writes_no_settings(self):
        self.ready()
        other = self.package("q", {"hq": (HARNESS, {})})
        preview_tests.PreviewTest.approve(self, other)
        code, out, err = self.attach(harness="q/hq", packages=[self.pkg, other])
        self.assertEqual(0, code, err)
        self.assertIn("warning: this harness provides no permissions, so the hard stops and the "
                      "guarded store are enforced only by instruction", err)
        self.assertFalse(os.path.exists(os.path.join(self.place, ".claude")))
        document = self.planned()
        self.assertEqual(("hq", []), (document["harness"], document["files"]))
        self.assertNotIn("changes what the agent may do", err)

    def test_an_override_with_no_neutral_item_is_refused(self):
        self.pkg = self.version(notes=self.override_notes(
            {"harness/claude/skills/ghost/SKILL.md": b"---\nname: ghost\n---\nx\n"}))
        self.install(self.pkg)
        self.refuses(contains="skill/ghost")


class Inputs(unittest.TestCase):
    """`attach.inputs` reads the neutral tree, overrides and exclusions of every module."""

    @staticmethod
    def modules(**files):
        mods, snaps = [], {}
        for name, contents in files.items():
            package, _, module = name.partition(".")
            mods.append(types.SimpleNamespace(package=package, name=module))
            snaps[(package, module)] = snapshot.Snapshot(package, module, contents, frozenset())
        return mods, snaps

    def read(self, harness="claude", **files):
        mods, snaps = self.modules(**files)
        return attach.inputs(mods, snaps, harness)

    def refused(self, text, harness="claude", **files):
        with self.assertRaises(attach.Refused) as caught:
            self.read(harness, **files)
        self.assertIn(text, str(caught.exception))

    def test_the_trees_of_two_modules_are_joined(self):
        tree, overrides, excludes = self.read(**{
            "p.a": {"harness/neutral/skills/x/SKILL.md": b"x"},
            "p.b": {"harness/neutral/agents/y.md": b"y", "module.json": b"{}"}})
        self.assertEqual({"skills/x/SKILL.md": b"x", "agents/y.md": b"y"}, tree)
        self.assertEqual(({}, {}), (overrides, excludes))

    def test_one_path_in_two_modules_is_refused_naming_both(self):
        self.refused("p/a and p/b both supply harness/neutral/skills/x/SKILL.md", **{
            "p.a": {"harness/neutral/skills/x/SKILL.md": b"1"},
            "p.b": {"harness/neutral/skills/x/SKILL.md": b"2"}})

    def test_an_override_is_keyed_by_kind_and_name(self):
        _, overrides, _ = self.read(**{"p.a": {
            "harness/claude/skills/x/SKILL.md": b"s", "harness/claude/skills/x/ref/a.md": b"r",
            "harness/claude/agents/y.md": b"y", "harness/claude/commands/z.md": b"z"}})
        self.assertEqual({("skill", "x"): {"SKILL.md": b"s", "ref/a.md": b"r"},
                          ("agent", "y"): {"y.md": b"y"}, ("command", "z"): {"z.md": b"z"}},
                         overrides)

    def test_two_modules_overriding_one_item_are_refused(self):
        self.refused("p/a and p/b both override skill/x", **{
            "p.a": {"harness/claude/skills/x/SKILL.md": b"1"},
            "p.b": {"harness/claude/skills/x/SKILL.md": b"2"}})

    def test_a_misplaced_override_is_refused(self):
        for rel in ("harness/claude/tools/x.md", "harness/claude/skills/x.md",
                    "harness/claude/skills/x", "harness/claude/agents/y.txt",
                    "harness/claude/agents/dir/y.md", "harness/claude/skills/Bad/SKILL.md",
                    "harness/claude/agents/Bad.md"):
            with self.subTest(rel=rel), self.assertRaises(attach.Refused):
                self.read(**{"p.a": {rel: b"x"}})

    def test_exclusions_are_read_by_kind_and_name_and_the_first_reason_stays(self):
        first = json.dumps({"exclude": [{"item": "skills/x", "reason": "r1"}]}).encode()
        second = json.dumps({"exclude": [{"item": "skills/x", "reason": "r2"},
                                         {"item": "agents/y", "reason": "r3"}]}).encode()
        _, _, excludes = self.read(**{"p.a": {"harness/claude/manifest.json": first},
                                      "p.b": {"harness/claude/manifest.json": second}})
        self.assertEqual({("skill", "x"): "r1", ("agent", "y"): "r3"}, excludes)

    def test_a_bad_exclusion_manifest_is_refused(self):
        for text in (b"{", b"[]", b'{"exclude": {}}', b'{"exclude": [1]}',
                     b'{"exclude": [{"item": "skills/x"}]}',
                     b'{"exclude": [{"item": "tools/x", "reason": "r"}]}',
                     b'{"exclude": [{"item": "skills/", "reason": "r"}]}',
                     b'{"exclude": [{"item": 5, "reason": "r"}]}'):
            with self.subTest(text=text), self.assertRaises(attach.Refused):
                self.read(**{"p.a": {"harness/claude/manifest.json": text}})

    def test_files_that_are_not_harness_items_are_ignored(self):
        tree, overrides, excludes = self.read(**{"p.a": {
            "module.json": b"{}", "files/x": b"x", "harness/neutral": b"", "scripts/run.sh": b"#"}})
        self.assertEqual(({}, {}, {}), (tree, overrides, excludes))


class Refusals(Base):
    def test_a_clone_that_already_records_a_harness(self):
        self.ready()
        self.assertEqual(0, self.attach()[0])
        before = (self.content(), self.content(self.store_root))
        code, out, err = self.attach()
        self.assertEqual((1, ""), (code, out))
        self.assertIn("refused: this clone already records the harness claude", err)
        self.assertEqual(before, (self.content(), self.content(self.store_root)))

    def test_a_local_manifest_that_is_not_canonical_is_refused_not_ignored(self):
        self.ready()
        os.makedirs(os.path.join(self.place, ".workbench", "local"))
        with open(os.path.join(self.place, *LOCAL.split("/")), "wb") as handle:
            handle.write(b"{}")
        before = self.content()
        code, out, err = self.attach()
        self.assertEqual((1, ""), (code, out))
        self.assertIn("the local manifest cannot be used", err)
        self.assertEqual(before, self.content())

    def test_a_target_that_is_not_an_existing_project(self):
        self.ready()
        empty = os.path.join(self.root, "empty")
        os.mkdir(empty)
        err = self.refuses(place=empty, contains="not an existing project")
        self.assertIn("use install", err)

    def test_a_git_file_is_refused_and_named(self):
        self.ready()
        shutil.rmtree(os.path.join(self.place, ".git"))
        with open(os.path.join(self.place, ".git"), "w") as handle:
            handle.write("gitdir: ../elsewhere\n")
        self.refuses(contains=".git is not a real directory")

    def test_a_project_this_machine_has_no_baselines_for(self):
        self.pkg = self.version()
        self.install(self.pkg, store_writes=False)
        self.refuses(contains="holds no acknowledgement baselines")

    def test_a_project_changed_since_it_was_acknowledged(self):
        self.ready()
        self.edit(".workbench/p/notes/scripts/run.sh", lambda data: data + b"# mine\n")
        err = self.refuses(contains="wb acknowledge")
        self.assertIn("changed .workbench/p/notes/scripts/run.sh", err)

    def test_the_harness_package_is_not_given(self):
        self.ready()
        self.refuses(package=None, contains="the harness package workbench is not one this "
                                            "project records; give it with --package")

    def test_a_recorded_local_package_must_be_given(self):
        self.ready()
        self.refuses(packages=[CLAUDE], contains="give it with --package <directory>")

    def test_a_module_the_package_does_not_declare(self):
        self.ready()
        self.refuses(harness="workbench/ghost", contains="declares no module ghost")

    def test_a_module_that_is_not_a_harness(self):
        self.ready()
        self.refuses(harness="p/notes", contains="p/notes is recorded as an installed module")

    def test_a_package_module_that_is_not_a_harness(self):
        self.ready()
        other = self.package("q", {"m": ({}, {})})
        self.approve(other)
        self.refuses(harness="q/m", packages=[self.pkg, other], contains="harness")

    def test_a_recorded_module_that_is_not_approved(self):
        self.skip_approval = ("notes",)
        self.ready()
        self.refuses(contains="p/notes is not approved")

    def test_a_harness_that_is_not_approved(self):
        self.ready()
        other = self.package("q", {"hq": (HARNESS, {})})
        self.refuses(harness="q/hq", packages=[self.pkg, other], contains="q/hq is not approved")

    def test_a_package_that_differs_from_the_lock(self):
        self.ready()
        newer = self.version(notes=(NOTES[0], dict(NOTES[1], **{"scripts/run.sh": b"#!/bin/sh\necho 2\n"})))
        self.approve(newer)
        err = self.refuses(packages=[newer, CLAUDE], contains="not the one the lock records")
        self.assertIn("wb upgrade", err)

    def test_a_first_party_module_edited_after_release_is_third_party_and_refused(self):
        self.ready()
        copy = os.path.join(self.root, "edited")
        shutil.copytree(CLAUDE, os.path.join(copy, "workbench"))
        path = os.path.join(copy, "workbench", "claude", "module.json")
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
        document["description"] = "changed after approval"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        self.refuses(packages=[self.pkg, os.path.join(copy, "workbench")],
                     contains="unprefixed capability 'instructions' is reserved")

    def test_a_third_party_harness_edited_after_it_was_approved_is_not_approved(self):
        self.ready()
        other = self.package("q", {"hq": (HARNESS, {})})
        preview_tests.PreviewTest.approve(self, other)
        path = os.path.join(other, "hq", "module.json")
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
        document["description"] = "changed after approval"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
        self.refuses(harness="q/hq", packages=[self.pkg, other], contains="q/hq is not approved")

    def record(self, edit):
        """Rewrite the committed manifest the way a hostile or careless commit could, and
        acknowledge it, so only attach's own checks stand in the way."""
        document = manifest.parse(self.read(".workbench/manifest.json"))
        edit(document)
        self.edit(".workbench/manifest.json", lambda data: manifest.serialize(document))
        self.acknowledge(".workbench/manifest.json")

    def test_a_manifest_that_records_a_harness_does_not_make_another_module_the_harness(self):
        self.ready()
        result = base_tests.verify.verify_package(self.pkg, select=list(self.MODULES),
                                                  harness_required=True)
        recorded = next(m for m in result.modules if m.name == "h")

        def add_harness(document):
            document["packages"][0]["modules"].append(
                {"declaration": recorded.declaration_hash, "name": "h",
                 "tree": recorded.tree_hash, "version": recorded.version})
            document["packages"][0]["modules"].sort(key=lambda m: m["name"])

        self.record(add_harness)
        other = self.package("q", {"m": ({}, {})})
        preview_tests.PreviewTest.approve(self, other)
        self.refuses(harness="q/m", packages=[self.pkg, other], contains="q/m is not a harness module")

    def test_packages_that_changed_while_they_were_read_are_refused(self):
        self.ready()
        real = base_tests.verify.verify_packages

        def swapped(*args, **kwargs):
            result = real(*args, **kwargs)
            return result._replace(packages=list(reversed(result.packages)))

        with unittest.mock.patch.object(attach.verify, "verify_packages", swapped):
            self.refuses(contains="the packages changed while they were read")

    def test_a_package_changed_outside_every_recorded_module_differs_from_the_lock(self):
        self.ready()
        newer = self.version(h=({"type": "harness", "layout": {}, "description": "other"}, {}))
        self.approve(newer)
        self.refuses(packages=[newer, CLAUDE], contains="the package p is not the one the lock records")

    def test_a_module_hash_the_lock_does_not_match_is_refused_though_the_package_is_the_same(self):
        self.ready()

        def forge(document):
            for module in document["packages"][0]["modules"]:
                if module["name"] == "notes":
                    module["tree"] = "0" * 64

        self.record(forge)
        self.refuses(contains="the module p/notes is not the one the lock records")

    def test_the_package_is_not_cached_and_nothing_is_fetched(self):
        self.pkg = self.version()
        self.install(self.pkg, source="https://example.test/p.git", ref="HEAD", commit="a" * 40)
        self.refuses(packages=[CLAUDE], contains="has not been downloaded")
        base_tests.fetch.fetch.assert_not_called()

    def test_the_harness_must_be_two_names(self):
        self.ready()
        for bad in ("workbench", "workbench/", "/claude", "a/b/c", "Workbench/claude"):
            with self.subTest(harness=bad):
                out, err = io.StringIO(), io.StringIO()
                code = cli.main(["attach", self.place, "--harness", bad, "--package", CLAUDE],
                                out, err, store_root=self.store_root, home=self.home)
                self.assertEqual(2, code)
                self.assertIn("--harness takes <package>/<module>", err.getvalue())

    def test_a_home_directory_a_rule_cannot_name_refuses_everything(self):
        self.ready()
        self.home = os.path.join(self.root, "ho:me")
        os.mkdir(self.home)
        self.refuses(contains="cannot write the path")

    def test_a_home_that_is_unknown_refuses(self):
        support.require_release(self)
        self.ready()
        with unittest.mock.patch.object(attach, "default_home", lambda: None):
            out, err = io.StringIO(), io.StringIO()
            before = self.content()
            code = cli.main(["attach", self.place, "--harness", "workbench/claude", "--package",
                             self.pkg, "--package", CLAUDE], out, err, store_root=self.store_root)
        self.assertEqual(1, code)
        self.assertIn("the home directory is not known", err.getvalue())
        self.assertEqual(before, self.content())

    def test_a_local_manifest_that_would_be_too_large_refuses_before_any_write(self):
        self.ready()
        with unittest.mock.patch.object(localmanifest, "MAX_FILES", 2):
            self.refuses(contains="the local manifest cannot be written")


class Conflicts(Base):
    def setUp(self):
        Base.setUp(self)
        self.ready()

    def put(self, rel, data=b"mine\n"):
        full = os.path.join(self.place, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb") as handle:
            handle.write(data)

    def test_a_harness_file_with_other_content_is_a_conflict_and_nothing_is_written(self):
        self.put("CLAUDE.md", b"# my own\n")
        err = self.refuses(contains="CLAUDE.md: it exists with other content")
        self.assertEqual(b"# my own\n", self.read("CLAUDE.md"))
        self.assertFalse(os.path.exists(os.path.join(self.place, ".claude")))

    def test_every_conflict_is_listed_together(self):
        self.put("CLAUDE.md")
        self.put(".claude/agents/reviewer.md")
        err = self.refuses(contains="CLAUDE.md")
        self.assertIn(".claude/agents/reviewer.md", err)

    def test_an_existing_settings_file_is_not_merged_and_the_entries_are_printed(self):
        self.put(SETTINGS, b'{"permissions": {"allow": ["Bash(ls)"]}}\n')
        err = self.refuses(contains=".claude/settings.local.json: it exists with other content")
        self.assertEqual(b'{"permissions": {"allow": ["Bash(ls)"]}}\n', self.read(SETTINGS))
        self.assertIn("  the entries attach would have written to it:\n", err)
        self.assertIn('"Bash(wb install)"', err)
        self.assertIn("attach never edits a settings file it did not write", err)
        self.assertNotIn('"allow"', err.split("the entries attach would")[1])

    def test_a_link_at_claude_is_refused_and_nothing_is_written_through_it(self):
        os.symlink(self.outside, os.path.join(self.place, ".claude"))
        self.refuses(contains=".claude")
        self.assertEqual([], os.listdir(self.outside))

    def test_a_link_at_the_settings_file_is_refused_and_its_target_is_untouched(self):
        victim = os.path.join(self.outside, "victim")
        with open(victim, "wb") as handle:
            handle.write(b"keep\n")
        os.makedirs(os.path.join(self.place, ".claude"))
        os.symlink(victim, os.path.join(self.place, ".claude", "settings.local.json"))
        self.refuses(contains="settings.local.json")
        with open(victim, "rb") as handle:
            self.assertEqual(b"keep\n", handle.read())

    def test_a_dangling_link_is_not_created_through(self):
        os.symlink(os.path.join(self.outside, "new"), os.path.join(self.place, "CLAUDE.md"))
        self.refuses(contains="CLAUDE.md")
        self.assertEqual([], os.listdir(self.outside))

    def test_a_directory_where_a_file_goes_is_a_conflict(self):
        os.mkdir(os.path.join(self.place, "CLAUDE.md"))
        self.refuses(contains="CLAUDE.md")

    def test_a_file_where_a_directory_goes_is_a_conflict(self):
        self.put(".claude", b"a file\n")
        self.refuses(contains=".claude")

    def test_a_link_at_the_exclude_file_is_refused_before_any_file_is_written(self):
        os.mkdir(os.path.join(self.place, ".git", "info"))
        os.symlink(os.path.join(self.outside, "x"), os.path.join(self.place, ".git", "info",
                                                                 "exclude"))
        self.refuses(contains=".git/info/exclude")
        self.assertFalse(os.path.exists(os.path.join(self.place, ".claude")))
        self.assertEqual([], os.listdir(self.outside))

    def test_a_link_at_git_info_is_refused_before_any_file_is_written(self):
        os.symlink(self.outside, os.path.join(self.place, ".git", "info"))
        self.refuses(contains=".git/info/exclude")
        self.assertFalse(os.path.exists(os.path.join(self.place, "CLAUDE.md")))

    def test_the_owners_exclude_lines_are_kept(self):
        os.mkdir(os.path.join(self.place, ".git", "info"))
        with open(os.path.join(self.place, ".git", "info", "exclude"), "wb") as handle:
            handle.write(b"# mine\n*.log\n")
        self.assertEqual(0, self.attach()[0])
        self.assertEqual(b"# mine\n*.log\n/CLAUDE.md\n/.claude/\n", self.read(".git/info/exclude"))


class Rerun(Base):
    def setUp(self):
        Base.setUp(self)
        self.ready()

    def stop_at(self, number):
        """Make the `number`-th file creation fail."""
        original = projectfs.Writer.create_file
        calls = []

        def create_file(writer, rel, data, executable=False):
            calls.append(rel)
            if len(calls) == number:
                raise OSError("disk full")
            return original(writer, rel, data, executable)

        return unittest.mock.patch.object(projectfs.Writer, "create_file", create_file)

    def test_a_failure_part_way_exits_3_and_names_what_was_and_was_not_written(self):
        with self.stop_at(3):
            code, out, err = self.attach()
        self.assertEqual((3, ""), (code, out))
        self.assertIn("failed: disk full\n", err)
        self.assertIn("written:\n  .git/info/\n  .git/info/exclude\n  .claude/\n", err)
        self.assertIn("not written:\n", err)
        self.assertIn("that file may be incomplete: remove it yourself", err)
        self.assertIn("  .workbench/local/harness.json\n", err)
        self.assertIn("the project itself is complete", err)
        self.assertIn("`wb attach` again", err)
        self.assertFalse(os.path.exists(os.path.join(self.place, *LOCAL.split("/"))))
        self.assertEqual(b"/CLAUDE.md\n/.claude/\n", self.read(".git/info/exclude"))

    def test_a_failure_adding_the_exclude_lines_leaves_no_harness_file(self):
        with unittest.mock.patch.object(projectfs.Writer, "add_exclude",
                                        side_effect=OSError("no space")):
            code, out, err = self.attach()
        self.assertEqual(3, code)
        self.assertFalse(os.path.exists(os.path.join(self.place, "CLAUDE.md")))
        self.assertFalse(os.path.exists(os.path.join(self.place, ".claude")))
        self.assertEqual(0, self.attach()[0])

    def test_the_rerun_leaves_the_files_it_wrote_and_finishes(self):
        with self.stop_at(4):
            self.assertEqual(3, self.attach()[0])
        written = {path: self.read(path) for path in HARNESS_PATHS
                   if os.path.exists(os.path.join(self.place, *path.split("/")))}
        self.assertTrue(written)
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertIn("left %d files as they were" % len(written), out)
        for path, data in written.items():
            self.assertEqual(data, self.read(path))
        self.assertEqual(sorted(HARNESS_PATHS), [f["path"] for f in self.planned()["files"]])
        self.assertEqual(b"/CLAUDE.md\n/.claude/\n", self.read(".git/info/exclude"))

    def test_a_rerun_after_a_failed_manifest_write_adds_no_exclude_line_twice(self):
        with unittest.mock.patch.object(localmanifest, "write", side_effect=OSError("no space")):
            self.assertEqual(3, self.attach()[0])
        self.assertEqual(b"/CLAUDE.md\n/.claude/\n", self.read(".git/info/exclude"))
        code, out, err = self.attach()
        self.assertEqual(0, code, err)
        self.assertNotIn("added", out)
        self.assertEqual(b"/CLAUDE.md\n/.claude/\n", self.read(".git/info/exclude"))

    def test_a_file_edited_after_the_failure_is_a_conflict_not_overwritten(self):
        with self.stop_at(4):
            self.assertEqual(3, self.attach()[0])
        with open(os.path.join(self.place, "CLAUDE.md"), "wb") as handle:
            handle.write(b"edited\n")
        self.refuses(contains="CLAUDE.md: it exists with other content")
        self.assertEqual(b"edited\n", self.read("CLAUDE.md"))

    def test_a_target_that_changed_before_the_first_write_is_not_written(self):
        from workbench import target
        before = self.content()
        with unittest.mock.patch.object(target.Target, "recheck",
                                        side_effect=target.TargetError("refused: the target changed")):
            code, out, err = self.attach()
        self.assertEqual((3, ""), (code, out))
        self.assertIn("failed: refused: the target changed", err)
        self.assertEqual(before, self.content())

    def test_an_interrupt_while_writing_exits_3_and_leaves_a_clone_that_can_be_rerun(self):
        original = projectfs.Writer.create_file
        calls = []

        def create_file(writer, rel, data, executable=False):
            calls.append(rel)
            if len(calls) == 2:
                raise KeyboardInterrupt
            return original(writer, rel, data, executable)

        with unittest.mock.patch.object(projectfs.Writer, "create_file", create_file):
            code, out, err = self.attach()
        self.assertEqual(3, code)
        self.assertIn("failed: interrupted", err)
        self.assertEqual(0, self.attach()[0])


class Git(Base):
    """A real repository: nothing attach wrote is tracked, and every path is ignored."""

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_every_written_path_is_ignored_by_the_exclude_file_and_none_is_tracked(self):
        self.ready()
        shutil.rmtree(os.path.join(self.place, ".git"))
        env = {"PATH": os.environ.get("PATH", ""), "HOME": self.home,
               "XDG_CONFIG_HOME": os.path.join(self.home, "xdg"),
               "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

        def git(*args):
            done = subprocess.run(["git", "-c", "init.defaultBranch=main"] + list(args),
                                  cwd=self.place, env=env, capture_output=True, text=True)
            self.assertEqual(0, done.returncode, done.stderr)
            return done.stdout

        git("init", "-q")
        self.assertEqual(0, self.attach()[0])
        ignored = git("check-ignore", "-v", *HARNESS_PATHS)
        for path in HARNESS_PATHS:
            self.assertIn(path, ignored)
        self.assertIn(".git/info/exclude", ignored)
        git("add", "-A")
        self.assertEqual("", "\n".join(line for line in git("ls-files").splitlines()
                                       if line == "CLAUDE.md" or line.startswith(".claude/")))
        self.assertEqual("", "\n".join(line for line in git("status", "--porcelain",
                                                            "--untracked-files=all").splitlines()
                                       if "CLAUDE.md" in line or ".claude/" in line))


class Parse(unittest.TestCase):
    def parse(self, *tokens):
        return attach.parse(list(tokens))

    def test_a_full_command(self):
        command = self.parse("proj", "--harness", "workbench/claude", "--package", "a", "--ref",
                             "v1", "--package", "b")
        self.assertEqual(("proj", ("workbench", "claude"), [("a", "v1"), ("b", None)]),
                         (command.target, command.harness, command.packages))

    def test_the_target_defaults_to_the_current_directory_and_dir_works(self):
        self.assertEqual(".", self.parse("--harness", "w/c").target)
        self.assertEqual("x", self.parse("--dir", "x", "--harness", "w/c").target)

    def test_bad_usage(self):
        for tokens in ((), ("--harness",), ("--harness", "w/c", "--harness", "w/c"),
                       ("--harness", "w/c", "--ref", "v1"),
                       ("--harness", "w/c", "--package", "a", "--ref", "1", "--ref", "2"),
                       ("--harness", "w/c", "--dir", "a", "--dir", "b"),
                       ("--harness", "w/c", "a", "b"), ("--harness", "w/c", "--force"),
                       ("--harness", "w/c", ""), ("--harness", "w/c", "--dir", "a", "b"),
                       ("--harness", "w"), ("--harness", "w/c/d"), ("--harness", "W/c"),
                       ("--harness", "w/" + "c" * 65)):
            with self.subTest(tokens=tokens), self.assertRaises(sources.UsageError):
                self.parse(*tokens)


class Cli(Base):
    def test_attach_is_routed_and_has_a_usage_line(self):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["attach"], out, err, store_root=self.store_root)
        self.assertEqual(2, code)
        self.assertIn("python3 -m workbench attach [<target> | --dir <path>] --harness", err.getvalue())

    def test_attach_is_classified_as_owner_run_and_routed(self):
        self.assertIn("attach", rules.OWNER_RUN)
        self.assertEqual((), rules.NOT_YET_ROUTED)


class Paths(unittest.TestCase):
    def planned(self, path, data=b"x"):
        return harnessplan.Planned(path, data, 0o644, hashlib.sha256(data).hexdigest(), "t")

    def test_a_path_in_git_or_workbench_is_refused_in_any_case(self):
        for path in (".git/hooks/pre-commit", ".GIT/config", ".workbench/x", ".Workbench/local/y"):
            with self.subTest(path=path), self.assertRaises(attach.Refused):
                attach._check_paths([self.planned(path)])

    def test_two_paths_that_collide_are_refused(self):
        with self.assertRaises(attach.Refused):
            attach._check_paths([self.planned("a/B"), self.planned("a/b")])
        with self.assertRaises(attach.Refused):
            attach._check_paths([self.planned("a"), self.planned("a/b")])
        with self.assertRaises(attach.Refused):
            attach._check_paths([self.planned("a"), self.planned("a")])

    def test_too_many_bytes_are_refused(self):
        big = self.planned("big", b"x" * (attach.MAX_WRITE_BYTES + 1))
        with self.assertRaises(attach.Refused):
            attach._check_paths([big])

    def test_good_paths_pass(self):
        attach._check_paths([self.planned("CLAUDE.md"), self.planned(".claude/a/b.md")])


if __name__ == "__main__":
    unittest.main()

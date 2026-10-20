import json
import os
import shutil
import tempfile
import unittest

from workbench import declarations, hashing, modulefiles

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "sample-package")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(os.path.realpath(self.tmp.name), "pkg")
        shutil.copytree(FIXTURE, self.path)

    def put(self, rel, text="x\n", mode=None):
        full = os.path.join(self.path, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as handle:
            handle.write(text)
        if mode:
            os.chmod(full, mode)

    def edit_module(self, name="sample-notes", **changes):
        rel = name + "/module.json"
        with open(os.path.join(self.path, rel)) as handle:
            decl = json.load(handle)
        decl.update(changes)
        self.put(rel, json.dumps(decl))

    def check(self, name="sample-notes"):
        loaded = declarations.load_package(self.path)
        self.assertEqual(loaded.problems, [], [str(p) for p in loaded.problems])
        module = [m for m in loaded.modules if m.name == name][0]
        return modulefiles.verify_module(self.path, loaded.package.name, module)

    def refused(self, rule, name="sample-notes"):
        result = self.check(name)
        self.assertTrue(result.problems)
        self.assertEqual(result.problems[0].rule, rule, [str(p) for p in result.problems])
        self.assertEqual(result.problems[0].scope, "module")
        self.assertIsNone(result.tree_hash)
        self.assertIsNone(result.declaration_hash)
        return result


class AccountingTest(Base):
    def test_valid_fixture_returns_both_hashes(self):
        for name in ("sample-notes", "sample-harness"):
            result = self.check(name)
            self.assertEqual(result.problems, [])
            self.assertEqual(result.tree_hash, hashing.tree_hash(os.path.join(self.path, name)))
            self.assertEqual(len(result.declaration_hash), 64)

    def test_declaration_hash_is_of_the_declaration(self):
        with open(os.path.join(self.path, "sample-notes", "module.json")) as handle:
            decl = json.load(handle)
        self.assertEqual(self.check().declaration_hash, hashing.declaration_hash(decl))

    def test_unaccounted_file(self):
        self.put("sample-notes/stray.txt")
        result = self.refused("unaccounted-file")
        self.assertIn("stray.txt", str(result.problems[0]))

    def test_unaccounted_nested_file(self):
        self.put("sample-notes/docs/deep/stray.txt")
        self.refused("unaccounted-file")

    def test_reserved_directory_names_are_case_sensitive(self):
        self.put("sample-notes/Templates/x.txt")
        self.refused("unaccounted-file")

    def test_a_file_named_like_a_reserved_directory_is_unaccounted(self):
        for name in ("harness", "templates"):
            with self.subTest(name=name):
                self.put("sample-notes/" + name)
                self.refused("unaccounted-file")
                os.remove(os.path.join(self.path, "sample-notes", name))
        self.edit_module(writes=[])
        shutil.rmtree(os.path.join(self.path, "sample-notes", "files"))
        self.put("sample-notes/files")
        self.refused("unaccounted-file")

    def test_all_unaccounted_files_are_reported(self):
        self.put("sample-notes/a.txt")
        self.put("sample-notes/b.txt")
        self.assertEqual(len(self.check().problems), 2)

    def test_files_under_reserved_directories_are_accounted(self):
        self.put("sample-notes/templates/t.md")
        self.put("sample-notes/files/other/o.md")
        self.assertEqual(self.check().problems, [])

    def test_ships_directory_accounts_for_its_files(self):
        self.edit_module(ships=["scripts"])
        self.put("sample-notes/scripts/more/run.sh")
        self.assertEqual(self.check().problems, [])

    def test_ships_directory_must_hold_a_file(self):
        self.edit_module(ships=["scripts/check.sh", "empty"])
        os.mkdir(os.path.join(self.path, "sample-notes", "empty"))
        result = self.refused("ships")
        self.assertIn("empty directory", str(result.problems[0]))

    def test_ships_directory_holding_only_empty_directories_is_refused(self):
        self.edit_module(ships=["scripts/check.sh", "empty"])
        os.makedirs(os.path.join(self.path, "sample-notes", "empty", "inner"))
        self.refused("ships")

    def test_fills_source_is_accounted(self):
        self.edit_module(fills=[{"slot": "slot:notes", "source": "blocks/a.md"}])
        self.put("sample-notes/blocks/a.md")
        self.assertEqual(self.check().problems, [])

    def test_missing_fills_source(self):
        self.edit_module(fills=[{"slot": "slot:notes", "source": "blocks/a.md"}])
        self.refused("fills")

    def test_fills_source_that_is_a_directory(self):
        self.edit_module(fills=[{"slot": "slot:notes", "source": "blocks"}])
        self.put("sample-notes/blocks/a.md")
        self.assertTrue(any(p.rule == "fills" for p in self.check().problems))

    def test_missing_ships_item(self):
        self.edit_module(ships=["scripts/check.sh", "scripts/gone.sh"])
        self.refused("ships")

    def test_missing_writes_source(self):
        self.edit_module(writes=["docs/notes.md", "docs/other.md"])
        result = self.refused("writes")
        self.assertIn("files/docs/other.md", str(result.problems[0]))

    def test_writes_source_must_be_a_file(self):
        self.edit_module(writes=["docs"])
        self.refused("writes")

    def test_symlink_is_refused(self):
        os.symlink("../module.json", os.path.join(self.path, "sample-notes", "files", "link"))
        result = self.refused("files")
        self.assertIn("files/link", str(result.problems[0]))

    def test_symlink_to_a_directory_is_refused(self):
        os.symlink("files", os.path.join(self.path, "sample-notes", "dirlink"))
        self.refused("files")

    def test_fifo_is_refused(self):
        os.mkfifo(os.path.join(self.path, "sample-notes", "files", "pipe"))
        result = self.refused("files")
        self.assertIn("pipe", str(result.problems[0]))

    def test_module_directory_swapped_for_a_symlink(self):
        loaded = declarations.load_package(self.path)
        module = loaded.modules[1]
        shutil.move(os.path.join(self.path, "sample-notes"), os.path.join(self.path, "real"))
        os.symlink("real", os.path.join(self.path, "sample-notes"))
        result = modulefiles.verify_module(self.path, "sample", module)
        self.assertEqual(result.problems[0].rule, "files")

    def test_declaration_changed_after_parsing(self):
        loaded = declarations.load_package(self.path)
        module = loaded.modules[1]
        self.edit_module(version="9.9.9")
        result = modulefiles.verify_module(self.path, "sample", module)
        self.assertEqual(result.problems[0].rule, "module.json")
        self.assertIsNone(result.tree_hash)

    def test_hashes_change_with_content_and_execute_bit(self):
        first = self.check()
        self.put("sample-notes/scripts/check.sh", "#!/bin/sh\nexit 1\n")
        second = self.check()
        self.assertNotEqual(first.tree_hash, second.tree_hash)
        self.assertEqual(first.declaration_hash, second.declaration_hash)
        os.chmod(os.path.join(self.path, "sample-notes", "scripts", "check.sh"), 0o755)
        self.assertNotEqual(second.tree_hash, self.check().tree_hash)
        self.edit_module(description="Changed.")
        self.assertNotEqual(second.declaration_hash, self.check().declaration_hash)

    def test_two_runs_on_fresh_copies_agree(self):
        first = self.check()
        shutil.rmtree(self.path)
        shutil.copytree(FIXTURE, self.path)
        self.assertEqual(self.check(), first)

    def test_verification_writes_nothing(self):
        def listing():
            out = []
            for base, dirs, files in os.walk(self.path):
                out += [os.path.join(base, n) for n in dirs + files]
            return sorted(out)
        before = listing()
        self.check()
        self.assertEqual(listing(), before)


class HarnessLayoutTest(Base):
    def setUp(self):
        super().setUp()
        self.base = "sample-notes/harness"

    def test_neutral_only(self):
        self.put(self.base + "/neutral/skills/a/SKILL.md")
        self.put(self.base + "/neutral/commands/b.md")
        self.assertEqual(self.check().problems, [])

    def test_harness_directory_only(self):
        self.put(self.base + "/claude/skills/a.md")
        self.assertEqual(self.check().problems, [])

    def test_neither_neutral_nor_harness_directory(self):
        os.makedirs(os.path.join(self.path, self.base))
        self.refused("harness-layout")

    def test_file_directly_under_harness(self):
        self.put(self.base + "/neutral/skills/a.md")
        self.put(self.base + "/readme.md")
        self.refused("harness-layout")

    def test_item_needs_kind_and_name(self):
        self.put(self.base + "/neutral/loose.md")
        self.refused("harness-layout")

    def test_bad_item_names(self):
        self.put(self.base + "/neutral/skills/Bad Name.md")
        self.refused("harness-layout")

    def test_two_paths_for_one_item(self):
        self.put(self.base + "/neutral/skills/a.md")
        self.put(self.base + "/neutral/skills/a/SKILL.md")
        self.refused("harness-layout")

    def test_exclusion_of_an_existing_item_is_a_warning(self):
        self.put(self.base + "/neutral/skills/a.md")
        self.put(self.base + "/claude/manifest.json",
                 json.dumps({"exclude": [{"item": "skills/a", "reason": "not for claude"}]}))
        result = self.check()
        self.assertEqual(result.problems, [])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("skills/a", result.warnings[0])
        self.assertIn("not for claude", result.warnings[0])

    def test_exclusion_of_a_missing_item(self):
        self.put(self.base + "/neutral/skills/a.md")
        self.put(self.base + "/claude/manifest.json",
                 json.dumps({"exclude": [{"item": "skills/ghost", "reason": "r"}]}))
        self.refused("harness-layout")

    def test_exclusion_without_a_neutral_directory(self):
        self.put(self.base + "/claude/manifest.json",
                 json.dumps({"exclude": [{"item": "skills/a", "reason": "r"}]}))
        self.refused("harness-layout")

    def test_overridden_and_excluded(self):
        self.put(self.base + "/neutral/skills/a.md")
        self.put(self.base + "/claude/skills/a.md")
        self.put(self.base + "/claude/manifest.json",
                 json.dumps({"exclude": [{"item": "skills/a", "reason": "r"}]}))
        result = self.refused("harness-layout")
        self.assertIn("both overridden and excluded", str(result.problems[0]))

    def test_override_without_exclusion_is_fine(self):
        self.put(self.base + "/neutral/skills/a.md")
        self.put(self.base + "/claude/skills/a.md")
        self.assertEqual(self.check().problems, [])

    def test_exclusion_in_one_harness_does_not_block_override_in_another(self):
        self.put(self.base + "/neutral/skills/a.md")
        self.put(self.base + "/claude/manifest.json",
                 json.dumps({"exclude": [{"item": "skills/a", "reason": "r"}]}))
        self.put(self.base + "/codex/skills/a.md")
        self.assertEqual(self.check().problems, [])

    def test_exclusion_reason_must_be_printable_and_short(self):
        self.put(self.base + "/neutral/skills/a.md")
        for reason in ("\x1b[2J\x1b]0;pwn\x07hi", "two\nlines", "x" * 201):
            with self.subTest(reason=reason):
                self.put(self.base + "/claude/manifest.json",
                         json.dumps({"exclude": [{"item": "skills/a", "reason": reason}]}))
                self.refused("harness-layout")

    def test_bad_manifests(self):
        self.put(self.base + "/neutral/skills/a.md")
        for text in ('{"exclude": [{"item": "skills/a"}]}',
                     '{"exclude": [{"item": "skills/a", "reason": ""}]}',
                     '{"exclude": [{"item": "skills/a", "reason": "r", "x": 1}]}',
                     '{"exclude": "skills/a"}',
                     '{"other": 1}',
                     '{"exclude": [], "exclude": []}',
                     '[]',
                     '{"exclude": [{"item": "skills/a", "reason": "r"},'
                     ' {"item": "skills/a", "reason": "r"}]}'):
            with self.subTest(text=text):
                self.put(self.base + "/claude/manifest.json", text)
                self.assertTrue(self.check().problems)

    def test_a_manifest_in_neutral_is_an_item_not_a_manifest(self):
        self.put(self.base + "/neutral/manifest.json")
        self.refused("harness-layout")

    def test_module_without_harness_directory_has_no_layout_checks(self):
        self.assertEqual(self.check().warnings, [])


if __name__ == "__main__":
    unittest.main()

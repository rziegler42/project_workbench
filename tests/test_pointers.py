import time
import unittest

from workbench import pointers


def found(text):
    return pointers.references(text)


class References(unittest.TestCase):
    def test_links_definitions_attributes_and_imports_are_found(self):
        text = ("[a](x/a.md) ![b](<y y/b.png> \"t\") [c][r] <a href=\"h.md\"> <img src='i.png'>\n"
                "[r]: ../r.md \"title\"\n@AGENTS.md and (@docs/x) and\n@~/home.md\n")
        self.assertEqual(
            [("x/a.md", False), ("y y/b.png", False), ("h.md", False), ("i.png", False),
             ("../r.md", False), ("AGENTS.md", True), ("docs/x", True), ("~/home.md", True)],
            found(text))

    def test_code_and_plain_mentions_are_ignored(self):
        text = ("`[a](x.md)` and `@AGENTS.md`\n```md\n[b](y.md)\n@z.md\n```\n"
                "~~~\n[c](w.md)\n~~~\nUnclosed:\n```\n[d](v.md)\n")
        self.assertEqual([], found(text))
        self.assertEqual([], found("see docs/x.md, mail a@b.test, @slot: name, @owner, "
                                   "<!-- @slot: policy --> and v@1.2 plus @10.5"))

    def test_the_count_is_bounded(self):
        self.assertEqual(pointers.MAX_REFERENCES,
                         len(found("[a](b.md) " * (pointers.MAX_REFERENCES + 50))))

    def test_hostile_text_is_read_in_linear_time(self):
        for text in ("[" * 200000, "](" * 100000, "```\n" * 50000, "@" * 200000, "`" * 200000,
                     "~" * 200000, "[a]:" * 100000, "<a href=\"" * 50000, "``` " * 50000,
                     "\n```\n" + "`" * 200000, "~~~\n" + "~" * 200000, "@a" * 100000, "](<" * 100000, "[a]: <" * 100000, "[" + "a]: <" * 100000,
                     "<a href=\"" * 100000 + "x"):
            start = time.monotonic()
            found(text)
            self.assertLess(time.monotonic() - start, 2.0, text[:12])


class Targets(unittest.TestCase):
    def target(self, raw, document="docs/guide.md", is_import=False):
        return pointers.target_of(document, raw, is_import)

    def test_relative_and_root_paths_resolve_against_the_document_and_the_project(self):
        self.assertEqual("docs/a.md", self.target("a.md"))
        self.assertEqual("README.md", self.target("../README.md#top"))
        self.assertEqual("docs/a.md", self.target("./a.md?x=1"))
        self.assertEqual("docs/my file.md", self.target("my%20file.md"))
        self.assertEqual("src/a.md", self.target("/src/a.md"))
        self.assertEqual("AGENTS.md", self.target("../AGENTS.md", "docs/x.md"))
        self.assertEqual("a.md", self.target("a.md", "README.md"))

    def test_what_is_not_a_path_is_none(self):
        for raw in ("", "  ", "#top", "https://x.test/a", "mailto:a@b.test", "//host/x", "C:\\x",
                    "?q=1", "a\\b", "a\x00b", "a\nb", "x:y"):
            with self.subTest(raw=raw):
                self.assertIsNone(self.target(raw))

    def test_the_project_directory_itself_is_not_a_target(self):
        self.assertIsNone(self.target(".", "README.md"))
        self.assertEqual("docs", self.target(".", "docs/x.md"))

    def test_a_path_that_leaves_the_project_is_outside(self):
        for raw in ("../../x.md", "../..", "a/../../../x"):
            with self.subTest(raw=raw):
                self.assertEqual(pointers.OUTSIDE, self.target(raw))
        self.assertEqual(pointers.OUTSIDE, self.target("../x.md", "x.md"))

    def test_an_import_of_a_machine_path_is_outside(self):
        self.assertEqual(pointers.OUTSIDE, self.target("~/x.md", is_import=True))
        self.assertEqual(pointers.OUTSIDE, self.target("/etc/x", is_import=True))
        self.assertEqual("docs/~/x.md", self.target("~/x.md"))


if __name__ == "__main__":
    unittest.main()

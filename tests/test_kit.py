import ast
import os
import sys
import unittest

import workbench
from tests import support_words
from workbench import wbkit
from workbench.wbkit import display

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "workbench", "wbkit")

# `sys.stdlib_module_names` needs Python 3.10; older interpreters get this list, which is every
# module the kit uses and is extended deliberately with the kit.
KIT_STDLIB = ("collections", "errno", "hashlib", "json", "os", "re", "stat", "struct", "unicodedata")
# Ways to import or run code that a plain import statement does not show.
INDIRECT_MODULES = ("importlib", "runpy", "pkgutil", "imp", "zipimport")
INDIRECT_NAMES = ("__import__", "import_module", "exec", "eval", "compile", "run_path", "run_module")

# Names of things the kit must not know: the first-party modules and the harnesses.
FORBIDDEN_WORDS = tuple(support_words.module_names() + support_words.harness_names())


def kit_sources():
    found = []
    for directory, names, files in os.walk(KIT):
        names[:] = [n for n in names if n != "__pycache__"]
        found.extend(os.path.join(directory, f) for f in files if f.endswith(".py"))
    return sorted(found)


def parse(path):
    with open(path, encoding="utf-8") as handle:
        return ast.parse(handle.read(), path)


class Api(unittest.TestCase):
    def test_the_api_version_is_an_integer(self):
        self.assertIs(type(wbkit.API), int)
        self.assertGreaterEqual(wbkit.API, 1)

    def test_the_kit_is_a_directory_of_the_workbench(self):
        self.assertEqual(os.path.dirname(os.path.abspath(wbkit.__file__)), KIT)
        self.assertTrue(os.path.dirname(KIT).endswith(os.sep + "workbench"))
        self.assertTrue(kit_sources())


def violations(tree):
    """What in a parsed source breaks the kit's boundary: an import outside the standard library and the
    kit, and any way of importing or running code that a plain import statement does not show."""
    found = []
    stdlib = getattr(sys, "stdlib_module_names", None) or KIT_STDLIB
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports = [(0, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports = [(node.level, node.module or "")]
        else:
            imports = []
        for level, name in imports:
            top = name.split(".")[0]
            if level == 0 and top not in stdlib:
                found.append("imports %r, which is not the standard library" % name)
            elif level > 1:
                found.append("imports %r from outside the kit" % ("." * level + name))
            if level == 0 and top in INDIRECT_MODULES:
                found.append("imports %r, which runs or loads code" % name)
        if isinstance(node, ast.Name) and node.id in INDIRECT_NAMES:
            found.append("uses %r" % node.id)
        elif isinstance(node, ast.Attribute) and node.attr in INDIRECT_NAMES:
            found.append("uses %r" % node.attr)
    return found


class Boundary(unittest.TestCase):
    """The kit imports the standard library and itself, and knows no module or harness."""

    def test_the_kit_imports_only_the_standard_library_and_itself_and_runs_no_code_indirectly(self):
        for path in kit_sources():
            self.assertEqual(violations(parse(path)), [], os.path.relpath(path, ROOT))

    def test_the_boundary_check_catches_what_it_describes(self):
        for text in ("import requests\n", "from .. import x\n", "from ..x import y\n",
                     "from importlib import import_module as f\n", "import importlib.util\n",
                     "import runpy\n", "exec('x')\n", "__import__('x')\n", "eval('1')\n",
                     "compile('1', 'f', 'exec')\n", "import os\nos.__import__('x')\n"):
            self.assertTrue(violations(ast.parse(text)), text)
        for text in ("import os.path as p\nimport json\n", "from . import display\n",
                     "from .display import clean\n", "import unicodedata\n"):
            self.assertEqual(violations(ast.parse(text)), [], text)

    def test_the_kit_names_no_module_or_harness(self):
        words = set(FORBIDDEN_WORDS)
        for path in kit_sources():
            with open(path, encoding="utf-8") as handle:
                text = handle.read().lower()
            for word in sorted(words):
                self.assertNotIn(word, text, "%s names %r" % (os.path.relpath(path, ROOT), word))

    def test_the_old_location_is_gone(self):
        for name in ("display", "safefs"):
            self.assertFalse(os.path.exists(os.path.join(ROOT, "workbench", name + ".py")), name)
            self.assertFalse(hasattr(workbench, name), name)
            self.assertTrue(os.path.isfile(os.path.join(KIT, name + ".py")), name)


class Display(unittest.TestCase):
    """What `display` does, pinned before it moved into the kit."""

    def test_ordinary_text_is_kept_including_non_ascii(self):
        self.assertEqual(display.clean("plain text 123 - ok"), "plain text 123 - ok")
        self.assertEqual(display.clean("café 中文"), "café 中文")

    def test_other_values_are_shown_as_text(self):
        self.assertEqual(display.clean(5), "5")
        self.assertEqual(display.clean(None), "None")

    def test_control_characters_become_visible_escapes(self):
        self.assertEqual(display.clean("a\nb"), "a\\nb")
        self.assertEqual(display.clean("a\x1b[2Jb"), "a\\x1b[2Jb")
        self.assertEqual(display.clean("a\x00b"), "a\\x00b")
        self.assertEqual(display.clean("a\rb\tc"), "a\\rb\\tc")

    def test_invisible_and_steering_characters_become_escapes(self):
        for char, shown in (("​", "\\u200b"), ("‮", "\\u202e"), (" ", "\\xa0"),
                            ("́", "\\u0301"), ("ㅤ", "\\u3164"), ("﻿", "\\ufeff")):
            self.assertEqual(display.clean("a" + char + "b"), "a" + shown + "b", repr(char))

    def test_a_plain_space_is_kept(self):
        self.assertEqual(display.clean("a b"), "a b")

    def test_ascii_text_escapes_every_non_ascii_character(self):
        self.assertEqual(display.ascii_text("bin/rуn"), "bin/r\\u0443n")
        self.assertEqual(display.ascii_text("\U0001f600"), "\\U0001f600")
        self.assertEqual(display.ascii_text("plain ~ text"), "plain ~ text")
        self.assertEqual(display.ascii_text("a\nb"), "a\\nb")
        self.assertEqual(display.ascii_text(7), "7")

    def test_the_cleaned_text_has_no_line_break_or_escape_character(self):
        hostile = "a\nb\rc\x1bd‮e f g"
        for shown in (display.clean(hostile), display.ascii_text(hostile)):
            for char in "\n\r\x1b‮  ":
                self.assertNotIn(char, shown)


if __name__ == "__main__":
    unittest.main()

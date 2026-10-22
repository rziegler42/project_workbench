"""A module's tests may import the repository's `tests` package only for its shared support.

`tests/support.py` and `tests/support_*.py` are shared; every other file in `tests/` is the installer's
own test and may not be reached from a module's tests (module-boundary spec, "What the installer's own
tests may use"). The rule is read from the syntax tree, so it holds for code that never runs. It is static: it guards
against accidental coupling, and an `importlib` or `sys.path` trick is outside it.
"""

import ast
import glob
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def shared(name):
    return name == "support" or name.startswith("support_")


def offences(source):
    """The imports in `source` that reach into `tests` beyond its shared support, as text."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == "tests" and not (len(parts) == 2 and shared(parts[1])):
                    found.append("import " + alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            parts = (node.module or "").split(".")
            if parts[0] != "tests":
                continue
            if len(parts) == 1:
                found.extend("from tests import " + alias.name for alias in node.names
                             if not shared(alias.name))
            elif not (len(parts) == 2 and shared(parts[1])):
                found.append("from %s import ..." % node.module)
    return found


class Rule(unittest.TestCase):
    def test_the_shared_support_is_allowed(self):
        for source in ("from tests import support", "from tests import support_harness, support",
                       "from tests.support import forbid_real_store", "import tests.support_harness",
                       "from tests.support_harness import SYNTHETIC", "import os"):
            with self.subTest(source=source):
                self.assertEqual([], offences(source))

    def test_any_other_reach_into_tests_is_found(self):
        for source, text in (("from tests import test_layout", "from tests import test_layout"),
                             ("from tests.test_layout import SYNTHETIC", "from tests.test_layout import ..."),
                             ("import tests.test_layout", "import tests.test_layout"),
                             ("import tests", "import tests"),
                             ("from tests import support, test_neutral", "from tests import test_neutral"),
                             ("from tests.support.sub import x", "from tests.support.sub import ..."),
                             ("from tests.supports import x", "from tests.supports import ..."),
                             ("def f():\n    from tests.test_neutral import tree", "from tests.test_neutral import ...")):
            with self.subTest(source=source):
                self.assertEqual([text], offences(source))

    def test_the_support_name_must_be_exact(self):
        for name in ("supportive", "supports", "Support"):
            with self.subTest(name=name):
                self.assertEqual(1, len(offences("from tests import " + name)))


class Repository(unittest.TestCase):
    def test_no_module_test_reaches_into_the_installers_tests(self):
        files = glob.glob(os.path.join(ROOT, "packages", "*", "*", "tests", "**", "*.py"), recursive=True)
        for path in sorted(files):
            with self.subTest(path=os.path.relpath(path, ROOT)):
                with open(path, encoding="utf-8") as handle:
                    self.assertEqual([], offences(handle.read()))


if __name__ == "__main__":
    unittest.main()

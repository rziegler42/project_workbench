import unittest

import workbench
from workbench import __main__ as entry


class PackageTest(unittest.TestCase):
    def test_package_imports(self):
        self.assertTrue(workbench.__doc__)

    def test_main_without_command_is_a_usage_error(self):
        self.assertEqual(entry.main([]), 2)


if __name__ == "__main__":
    unittest.main()

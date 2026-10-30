"""The installer's names for the git identity (``2026-10-29-approvals-name-the-approver-by-git-identity``).

The reader and its grammar live in the kit and ``tests/test_wbkit_identity.py`` runs the whole of their tests. These check
that the installer's module is the kit's reader under the installer's names, and that the installer reads through it."""

import unittest

from workbench import approvals, identity
from workbench.wbkit import identity as kit

NAME = "Example Approver"
EMAIL = "12345+example@users.noreply.github.com"


class InstallerNames(unittest.TestCase):
    def test_the_names_are_the_kits(self):
        for name in ("Identity", "IdentityError", "account_home", "check", "parse", "read"):
            with self.subTest(name=name):
                self.assertIs(getattr(identity, name), getattr(kit, name))

    def test_the_grammar_is_the_same_through_both_names(self):
        found = identity.check(NAME, EMAIL)
        self.assertEqual(found, kit.check(NAME, EMAIL))
        self.assertEqual(found.text, "%s <%s>" % (NAME, EMAIL))
        self.assertEqual(identity.parse(found.text), found)

    def test_a_refusal_is_the_same_error_through_both_names(self):
        with self.assertRaises(kit.IdentityError):
            identity.check("", EMAIL)
        with self.assertRaises(identity.IdentityError):
            kit.parse("not an identity")

    def test_the_approvals_read_the_approver_through_this_module(self):
        self.assertIs(approvals.identity, identity)


if __name__ == "__main__":
    unittest.main()

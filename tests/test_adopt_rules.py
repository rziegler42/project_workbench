"""An agent may preview an adoption and never run one: the harness denies `adopt` as it denies `install`."""

import unittest

from workbench import rules


class AdoptRulesTest(unittest.TestCase):
    def test_adopt_is_an_owner_run_command_and_sits_beside_install(self):
        self.assertIn("adopt", rules.OWNER_RUN)
        self.assertNotIn("adopt", rules.AGENT_SAFE)
        self.assertEqual(rules.OWNER_RUN.index("install") + 1, rules.OWNER_RUN.index("adopt"))

    def test_adopt_is_denied_in_every_spelling_install_is_denied_in(self):
        every = rules.owner_run_patterns()
        for spelling in rules.SPELLINGS:
            for command in ("install", "adopt"):
                self.assertIn("%s %s" % (spelling, command), every)
                self.assertIn("%s %s *" % (spelling, command), every)

    def test_preview_adopt_is_not_denied(self):
        every = rules.owner_run_patterns()
        for spelling in rules.SPELLINGS:
            for text in every:
                self.assertFalse(text.startswith("%s preview" % spelling), text)


if __name__ == "__main__":
    unittest.main()

"""The command gate: ``wb gate-command <harness>``, the Bash hook that stops a command naming a relaxed command unless it
is exactly the simple command the ``ask`` rule can fire on.

Plan ``2026-10-26-command-permission-levels``, increment J (``docs/decisions/2026-10-26-ask-level-command-gate.md``, with the
clarification note). The judging is text only; the cases come from the security review of the design."""

import io
import json
import unittest

from workbench import command_gate

STORE_BIN = "/home/owner/.config/project-workbench/bin/wb"
APPROVE = "approve-plan"
DIGEST = "0123456789abcdef0123456789abcdef"
BS = "\\"


def judge(command, keys=(APPROVE,)):
    return command_gate.judge(command, keys, STORE_BIN)


class Allowed(unittest.TestCase):
    def test_the_exact_forms_the_ask_rule_matches(self):
        for command in ("wb approve-plan docs/plans/2026-10-26-a.md",
                        "wb approve-plan docs/plans/2026-10-26-a.md --digest " + DIGEST,
                        "%s approve-plan docs/plans/a.md --digest %s" % (STORE_BIN, DIGEST)):
            with self.subTest(command=command):
                self.assertIsNone(judge(command))

    def test_a_command_with_no_guarded_word_is_allowed(self):
        for command in ("wb check", "wb plan-status docs/plans/a.md --digest " + DIGEST, "git status",
                        "echo hello", "python3 -m unittest tests.test_levels", "ls docs/plans", ""):
            with self.subTest(command=command):
                self.assertIsNone(judge(command))

    def test_the_delegated_command_is_not_the_guarded_one(self):
        self.assertIsNone(judge("wb delegate-approve-plan docs/plans/a.md"))
        self.assertIsNone(judge("wb delegate-approve-plan docs/plans/a.md --nothing"))

    def test_nothing_is_guarded_when_no_key_is_relaxed(self):
        self.assertIsNone(judge("bash -c 'wb approve-plan x'", keys=()))


class BlockedWhenTheWordIsContiguous(unittest.TestCase):
    def test_wrappers_and_control_syntax(self):
        for command in (
                "bash -c 'wb approve-plan docs/plans/a.md --digest %s'" % DIGEST,
                "sh -c 'wb approve-plan x'", "env wb approve-plan x", "eval \"wb approve-plan x\"",
                "exec wb approve-plan x", "nohup wb approve-plan x", "time wb approve-plan x",
                "command wb approve-plan x", "echo x | xargs wb approve-plan", "find . -exec wb approve-plan x {} ;",
                "$(echo wb) approve-plan x", "`echo wb` approve-plan x", "wb approve-plan x && wb check",
                "wb check; wb approve-plan x", "wb approve-plan x | cat", "wb approve-plan x > out",
                "cat <<EOF\nwb approve-plan x\nEOF", "FOO=1 wb approve-plan x", "/usr/local/bin/wb approve-plan x",
                "python3 -I -m workbench approve-plan x", "PYTHONPATH=/p python3 -m workbench approve-plan x",
                "wb approve-plan x --digest %s extra" % DIGEST, "wb approve-plan x y", "wb  approve-plan x",
                "wb approve-plan docs/plans/a.md\nwb check"):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))

    def test_a_word_that_only_appears_in_text_is_blocked_too(self):
        for command in ("grep -r approve-plan docs", "git commit -m 'approve-plan the thing'", "echo approve-plan"):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))

    def test_folded_spellings(self):
        for command in ("wb APPROVE-PLAN x", "wb Approve-Plan x", "wb ａｐｐｒｏｖｅ-ｐｌａｎ x"):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))


class BlockedWhenTheWordIsSpliced(unittest.TestCase):
    def test_static_splices(self):
        for command in ('wb approve""-plan x', "wb appr'ove-p'lan x", "wb approve\\-plan x", 'wb "approve"-"plan" x',
                        "wb app\\rove-plan x", "wb a'p'p'r'o'v'e-plan x", "wb approve-p''lan x",
                        "wb approve_plan x", "wb approve.plan x", "wb approve plan x"):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))

    def test_ansi_c_quoting_with_the_letters_in_order(self):
        for command in ("wb $'approve\\x2dplan' x", "wb $'\\141pprove-plan' x", 'wb $"approve-plan" x'):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))

    def test_a_dollar_quote_without_the_letters_is_not_blocked(self):
        self.assertIsNone(judge("printf %s $'\\n'"))


class BlockedWhenAQuoteIsMispaired(unittest.TestCase):
    """A stray ``$'`` ahead of the real one must not hide a hex-escaped word (review finding F1)."""

    def test_a_dollar_quote_pairs_in_every_position(self):
        for command in (": '$'; wb $'\\x61pprove-plan' plan.md",
                        "echo \"$'\" ; wb $'\\x61pprove-plan' p",
                        "echo 'cost $'; wb $'\\x61pprove-plan' p",
                        "wb $'\\x61pprove-plan p",
                        "wb $'\\141pprove-plan' p $'",
                        "wb $'appr\\157ve-plan' p"):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))

    def test_decoding_starts_at_every_dollar_quote(self):
        views = command_gate.decoded_views("x '$'; wb $'\\x61pprove-plan' y")
        self.assertTrue(any("approve-plan" in view for view in views), views)


class BlockedWhenAPatternBreaksTheWord(unittest.TestCase):
    """Brace, glob and parameter forms that split the word (review finding F4)."""

    def test_forms_that_need_a_decoy_or_a_variable(self):
        for command in ("wb approve-pla? p", "wb approve-p*n p", "wb approve-p{l,}an p", "wb approve-[p]lan p",
                        "wb approve-${x}plan p", "wb approve-$1plan p", "wb $0approve-plan p"):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))

    def test_a_backtick_substitution_that_splits_the_word(self):
        for command in ("wb appro`printf ve`-plan x", "wb `echo approve`-plan x"):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))

    def test_the_letters_must_sit_close_together(self):
        """A long command that has the eleven letters scattered through it is not a spelling of the word (review round 2)."""
        long_message = ("git commit -m \"$(cat <<'EOF'\nRefactor the parser so that the settings are read once, keep the "
                        "plan list in order, and move the loader into a helper, with no new dependency.\nEOF\n)\"")
        self.assertIsNone(judge(long_message))
        self.assertIsNone(judge("find . -name '*.py' -exec grep -l 'approach plan' {} +"))
        self.assertIsNotNone(judge("a=appr b=oveplan; wb ${a}${b} x"))

    def test_a_star_that_stands_for_a_long_run_is_a_known_limit(self):
        self.assertIsNone(judge("wb appr* x"))

    def test_ordinary_commands_with_the_same_characters_pass(self):
        for command in ("ls docs/*.md", "grep -r foo docs/*.md", "echo ${HOME}", "python3 -m unittest -k 'test_*'",
                        "git log --format=%H -n 3"):
            with self.subTest(command=command):
                self.assertIsNone(judge(command))


class BlockedAfterTheReviewOfTheBuiltCode(unittest.TestCase):
    """Findings M1, M2, L2 and L4 of the review of the built code; every string was run through ``judge`` first."""

    def test_the_exemption_cannot_be_turned_into_the_word(self):
        for command in ("A=delegate-approve-plan; wb ${A#delegate-} docs/plans/x.md",
                        'A=delegate-approve-plan; wb "${A##*delegate-}" docs/plans/x.md'):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))

    def test_the_delegated_command_stays_allowed_without_a_pattern_character(self):
        self.assertIsNone(judge("wb delegate-approve-plan docs/plans/x.md"))
        self.assertIsNotNone(judge("wb delegate-approve-plan docs/plans/*.md"))

    def test_padding_inside_an_expansion_that_expands_to_nothing_does_not_hide_the_word(self):
        pad = "x" * 31
        for command in ("wb appr$(true %s)ove-plan docs/plans/x.md" % pad,
                        "wb appr`: %s`ove-plan docs/plans/x.md" % pad,
                        "wb appr${u:+%s}ove-plan docs/plans/x.md" % pad,
                        "wb $'\\x61pprove-p'\"$(true %s)\"$'\\x6c\\x61n' docs/plans/x.md" % pad):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))

    def test_an_expansion_around_a_long_ordinary_command_is_not_a_spelling(self):
        self.assertIsNone(judge("git commit -m \"$(cat <<'EOF'\nFix the parser\nEOF\n)\""))
        self.assertIsNone(judge("echo $(date) && ls ${HOME}"))

    def test_whitespace_around_the_exact_form_is_not_the_exact_form(self):
        """The rule sees the raw text; the gate must not allow what the rule would not match."""
        for command in ("\nwb approve-plan docs/plans/x.md\n", "\twb approve-plan docs/plans/x.md",
                        "wb approve-plan docs/plans/x.md ", " wb approve-plan docs/plans/x.md"):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))

    def test_a_command_full_of_dollar_quotes_is_refused_quickly(self):
        import time
        began = time.monotonic()
        self.assertIsNotNone(judge("$'a'" * 16000))
        self.assertLess(time.monotonic() - began, 2.0)
        self.assertIsNone(judge("echo " + "$'a' " * 10))


class WhatTheTextCannotSee(unittest.TestCase):
    """The stated limits of the decision. These pass the gate; the tests pin that they are known, not that they are fine."""

    def test_a_word_whose_letters_are_not_in_the_text_passes(self):
        for command in ("wb $(echo YXBwcm92ZS1wbGFu | base64 -d) x", "wb $(rev <<< nalp-evorppa) x"):
            with self.subTest(command=command):
                self.assertIsNone(judge(command))

    def test_variables_that_carry_the_letters_in_order_are_caught_by_the_pattern_rule(self):
        for command in ("a=approve b=plan; wb $a-$b x", "wb $(printf 'approve\\055plan') x"):
            with self.subTest(command=command):
                self.assertIsNotNone(judge(command))

    def test_a_variable_far_from_the_rest_of_the_word_passes(self):
        """The window is cosmetic against a variable (review S3); the decision accepts a word built at run time."""
        self.assertIsNone(judge("A=approve; : " + "x" * 40 + "; wb $A-plan docs/plans/x.md"))

    def test_a_script_file_passes_because_the_command_names_no_word(self):
        self.assertIsNone(judge("bash ./x.sh"))
        self.assertIsNone(judge("python3 x.py"))


class OtherKeys(unittest.TestCase):
    def test_a_module_command_key_guards_both_words_in_order(self):
        key = "wb run tool go"
        self.assertIsNotNone(judge("bash -c 'wb run tool go d 2'", keys=(key,)))
        self.assertIsNotNone(judge("echo tool then go", keys=(key,)))
        self.assertIsNone(judge("wb run tool status docs/plans/a.md", keys=(key,)))
        self.assertIsNone(judge("wb run tool go docs/plans/a.md 2", keys=(key,)))
        self.assertIsNone(judge("%s run tool go docs/plans/a.md 2 --digest %s" % (STORE_BIN, DIGEST),
                                keys=(key,)))

    def test_a_key_with_no_command_guards_nothing(self):
        self.assertIsNone(judge("echo accept-decision", keys=("accept-decision",)))


class SingleWordKeys(unittest.TestCase):
    """A key of the form ``wb <word>`` is read in command position (``2026-10-27-command-gate-command-position``)."""

    KEYS = ("wb install",)

    def judge(self, command, keys=KEYS):
        return judge(command, keys=keys)

    def test_the_word_alone_is_allowed(self):
        for command in ("npm install", "pip install requests", "git commit -m 'install deps'", "ls docs/install.md",
                        "grep -rn install docs", "echo install", "wb check", "git add docs/x.md"):
            with self.subTest(command=command):
                self.assertIsNone(self.judge(command))

    def test_the_exact_forms_and_the_preview_are_allowed(self):
        for command in ("wb install --dir x", "wb install --dir x --package a/b", "%s install --dir x" % STORE_BIN,
                        "wb preview install --dir x", "%s preview install --dir x" % STORE_BIN):
            with self.subTest(command=command):
                self.assertIsNone(self.judge(command))

    def test_the_launcher_and_the_word_are_blocked_in_every_wrapper_and_spelling(self):
        for command in ("python3 -m workbench install --dir x", "python3 -B -m workbench install", "bash -c 'wb install'",
                        "env wb install --dir x", "sh -c \"wb  install\"", "wb install --dir x; echo done",
                        "echo x && wb install", "wb install | cat", "eval 'wb install'", "xargs wb install",
                        "cd x && %s install" % STORE_BIN, "$(wb install --dir x)", "wb preview install; wb install",
                        "wb preview  install", "wb preview-install"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command))

    def test_spliced_and_expanded_spellings_of_the_pair_are_blocked(self):
        for command in ('w""b install', 'wb inst""all', "wb inst\\all", "wb $'\\x69nstall'", "w$'b' install",
                        "${X}wb install", "wb ins${Y}tall", "wb `echo`install", "W=w; ${W}b install", "wb $'install'",
                        "wb {install,x}", "wb inst*"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command))

    def test_a_command_full_of_dollar_quotes_is_still_refused(self):
        self.assertIsNotNone(self.judge("echo " + "$'a' " * 70))

    def test_the_preview_exemption_does_not_hide_the_pair(self):
        for command in ("wb preview install wb install", "wb install preview install ; wb install",
                        "bash -c 'wb preview install && wb install'", "bash -c 'wb install preview install'"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command))

    def test_the_word_before_the_launcher_is_blocked_too(self):
        # The word can reach the launcher as data: both are literal in the text, in either order.
        for command in ("echo install | xargs wb", "printf install | xargs wb", "xargs wb <<< install",
                        "for w in install; do wb $w; done", "set -- install; wb \"$@\"", "read a <<< install; wb $a",
                        "echo install; python3 -m workbench $1", "echo inst\"\"all | xargs wb", "echo $'install' | xargs wb",
                        "echo install | xargs %s" % STORE_BIN, "echo install | xargs python3 -m workbench"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command))

    def test_the_cost_of_that_is_a_compound_command_that_holds_both(self):
        self.assertIsNotNone(self.judge("npm install && wb check"))
        self.assertIsNone(self.judge("npm install"))
        self.assertIsNone(self.judge("wb check"))

    def test_a_real_call_whose_arguments_hold_the_preview_words_is_the_exact_form(self):
        # It is the command the ask rule matches, so it is allowed to reach the harness's prompt.
        self.assertIsNone(self.judge("wb install preview install"))
        self.assertIsNone(self.judge("wb install --dir preview install"))

    def test_the_launcher_alone_spliced_or_expanded_is_blocked(self):
        for command in ('python3 -m work""bench install', "python3 -m wor${K}kbench install", "w${E}b install",
                        "%s/b?n/wb install" % "~", "python3 -m w*bench install"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command))

    def test_a_preview_that_holds_an_expansion_or_a_glob_is_still_blocked(self):
        # The pattern rule reads the text as written (the decision accepts it): run such a preview with the path spelled out.
        self.assertIsNotNone(self.judge("wb preview install --dir $PWD"))
        self.assertIsNone(self.judge("wb preview install --dir /tmp/x"))

    def test_a_module_command_named_like_a_preview_is_still_read_as_its_words(self):
        key = "wb run preview install"
        self.assertIsNone(self.judge("wb run preview install x", keys=(key,)))
        self.assertIsNotNone(self.judge("bash -c 'wb run preview install x'", keys=(key,)))
        self.assertIsNotNone(self.judge("echo preview install", keys=(key,)))

    def test_two_words_guard_each_other_independently(self):
        keys = ("wb install", "wb add")
        self.assertIsNone(self.judge("git add docs/x.md && npm install", keys=keys))
        self.assertIsNotNone(self.judge("bash -c 'wb add x'", keys=keys))
        self.assertIsNotNone(self.judge("bash -c 'wb install'", keys=keys))
        self.assertIsNone(self.judge("wb add --dir x", keys=keys))

    def test_approve_plan_is_still_read_as_the_word_alone(self):
        self.assertIsNotNone(self.judge("echo approve-plan", keys=("approve-plan",)))
        self.assertIsNotNone(self.judge("grep approve-plan docs", keys=("approve-plan", "wb install")))
        self.assertIsNone(self.judge("npm install", keys=("approve-plan", "wb install")))

    def test_a_module_command_key_is_still_read_as_its_words(self):
        key = "wb run tool go"
        self.assertIsNotNone(self.judge("echo tool then go", keys=(key,)))
        self.assertIsNone(self.judge("echo tool", keys=(key,)))

    def test_the_first_tier_checkpoint_guards_the_acknowledge_command(self):
        key = "acknowledge-first-tier"
        self.assertEqual(["acknowledge"], command_gate.words(key))
        self.assertIsNone(self.judge("wb acknowledge --dir /x", keys=(key,)))
        self.assertIsNone(self.judge("%s acknowledge /x" % STORE_BIN, keys=(key,)))
        for command in ("bash -c 'wb acknowledge'", "python3 -m workbench acknowledge", "wb acknowledge; echo", 'w""b acknowledge',
                        "wb acknow\"\"ledge", "echo acknowledge | xargs wb"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command, keys=(key,)))
        self.assertIsNone(self.judge("echo acknowledge", keys=(key,)))
        self.assertIsNone(self.judge("wb run helper commit --subject 'acknowledge'", keys=(key,)))

    def test_the_launchers_and_the_preview_actions_are_those_of_the_rules(self):
        from workbench import rules
        self.assertEqual(sorted({spelling.split()[-1] for spelling in rules.SPELLINGS}),
                         sorted(command_gate.LAUNCHERS))
        self.assertEqual(tuple(rules.PREVIEW_ACTIONS), command_gate.PREVIEW_ACTIONS)

    def test_the_release_preview_is_not_the_owner_run_command(self):
        key = "wb release-approvals"
        self.assertIsNone(self.judge("wb preview release-approvals", keys=(key,)))
        self.assertIsNotNone(self.judge("bash -c 'wb release-approvals'", keys=(key,)))

    def test_the_release_preview_does_not_hide_a_release_in_the_same_command(self):
        key = "wb release-approvals"
        for command in ("wb preview release-approvals; wb release-approvals",
                        "wb preview release-approvals && wb release-approvals",
                        "wb preview release-approvals | wb release-approvals",
                        "wb release-approvals; wb preview release-approvals"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command, keys=(key,)))

    def test_every_owner_run_command_is_read_in_command_position(self):
        from workbench import rules
        for command in rules.OWNER_RUN:
            if command == "approve-plan":
                continue
            key = "wb " + command
            with self.subTest(key=key):
                self.assertIsNotNone(self.judge("bash -c '%s'" % key, keys=(key,)))
                self.assertIsNone(self.judge("echo %s" % command, keys=(key,)))


class LiteralRunCommands(unittest.TestCase):
    """A literal ``wb run <name> <arguments>`` names a word only as data, and a sibling command name is not its prefix key
    (``2026-10-27-command-gate-literal-arguments``)."""

    KEYS = ("wb add", "wb install", "wb pin")
    HEAD = "0123456789abcdef0123456789abcdef01234567"

    def judge(self, command, keys=KEYS):
        return judge(command, keys=keys)

    def commit(self, subject, paths="tests/test_add.py", head="wb"):
        return "%s run helper commit --expected-head %s --subject '%s' -- %s" % (head, self.HEAD, subject, paths)

    def test_a_commit_through_wb_run_is_allowed_whatever_words_it_holds(self):
        for command in (self.commit("Add tests"), self.commit("Fix padding"), self.commit("Install docs"),
                        self.commit("Add tests", "workbench/install.py"), self.commit("pin, mapping, shipping"),
                        self.commit("Add tests", head=STORE_BIN), self.commit("Add\nmore\r\ntests"),
                        self.commit("costs $5 and `x` and $(y)"), self.commit("a ; b | c && wb install"),
                        "wb run checker check --files workbench/install.py", "wb run helper commit",
                        "wb run helper commit --body 'install' --trailer 'Plan: a#B' -- a b c"):
            with self.subTest(command=command):
                self.assertIsNone(self.judge(command))

    def test_any_other_form_is_judged_as_before(self):
        for command in (
                'wb run x --subject "$(wb install)"', "wb run x 'a' ; wb install",
                'wb run x "install"', "wb run x install; wb install", "wb run x 'a'\nwb install",
                "wb run x 'a' > out; wb install", "wb run x $(wb install)", "wb run x `wb install`",
                "wb run x 'install'x", "wb run x 'ins''tall'", "wb run x 'a' && wb install", "wb run x 'install'\n",
                "wb run x 'install' \n", "wb run x " + BS + "'install", "wb run x 'it's install", "wb run x 'a' wb install 'b'; echo",
                "echo install | xargs wb run x", "bash -c 'wb run x install'", "wb run x 'install' | xargs wb"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command))

    def test_the_name_may_not_be_a_launcher_or_a_verb(self):
        for command in ("wb run wb install", "wb run workbench install", "wb run install x", "wb run add x",
                        "wb run python3 install", "wb run -m workbench install"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command))

    def test_a_name_that_is_not_a_name_is_not_exempt(self):
        for command in ("wb run  x install", "wb run x" + BS + "y install", "wb run " + "a" * 65 + " install", "wb run .x install",
                        "wb run x/y install", "wb run x\tinstall"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command))

    def test_a_lookalike_launcher_is_not_the_literal_form(self):
        for launcher in ("\uff57b", "W" + "B", "w\u200bb", "\u0077\u0062\u200d"):
            with self.subTest(launcher=launcher):
                self.assertIsNotNone(self.judge("%s run x 'install'" % launcher))

    def test_a_trailing_newline_is_not_the_literal_form(self):
        self.assertIsNotNone(self.judge(self.commit("Add tests") + "\n"))
        self.assertIsNotNone(self.judge(self.commit("Add tests") + "\nwb install"))

    def test_the_other_keys_are_not_exempted(self):
        # `wb run <command> <argument>` keys and approve-plan read their own words, as they did.
        key = "wb run vault init"
        self.assertIsNone(self.judge("wb run vault init x", keys=(key,)))
        self.assertIsNotNone(self.judge("wb run vault init 'x'", keys=(key,)))
        self.assertIsNotNone(self.judge("wb run helper commit --subject 'vault init'", keys=(key,)))
        self.assertIsNotNone(self.judge("wb run x 'approve-plan'", keys=("approve-plan",)))

    def test_the_exemption_does_not_lift_the_other_relaxed_keys(self):
        keys = ("wb install", "wb run vault init")
        self.assertIsNone(self.judge("wb run helper commit --subject 'install'", keys=keys))
        self.assertIsNone(self.judge("wb run vault init", keys=keys))  # the exact call the ask rule matches
        self.assertIsNotNone(self.judge("wb run helper commit --subject 'vault init'", keys=keys))

    def test_a_sibling_command_name_is_not_its_prefix_key(self):
        self.assertIsNone(self.judge("wb approve-plan docs/plans/a.md", keys=("wb approve",)))
        self.assertIsNone(self.judge("wb approve-plan docs/plans/a.md --digest " + DIGEST, keys=("wb approve",)))
        # With approve-plan relaxed too, the sibling is judged by its own key: only its exact forms pass.
        both = ("wb approve", "approve-plan")
        self.assertIsNone(self.judge("wb approve-plan docs/plans/a.md", keys=both))
        self.assertIsNotNone(self.judge("bash -c 'wb approve-plan docs/plans/a.md'", keys=both))

    def test_the_sibling_exemption_does_not_hide_the_word(self):
        keys = ("wb approve",)
        self.assertIsNone(self.judge("wb approve /x/pkg", keys=keys))
        for command in ("bash -c 'wb approve-plan x; wb approve y'",
                        'wb approve"-plan" x', "wb approve${X} y", "wb approv$'e' x", "echo approve | xargs wb",
                        "wb approve-plan x && wb approve y", "python3 -m workbench approve x"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command, keys=keys))

    def test_the_siblings_are_the_commands_of_the_rules_that_continue_the_word(self):
        from workbench import rules
        found = {key: [name for name in rules.OWNER_RUN + rules.AGENT_SAFE if name.startswith(key + "-")]
                 for key in ("approve", "install", "add", "pin", "upgrade")}
        self.assertEqual({"approve": ["approve-plan"], "install": [], "add": [], "pin": [], "upgrade": []}, found)
        self.assertEqual(("approve-plan",), tuple(command_gate.siblings("wb approve")))
        self.assertEqual((), tuple(command_gate.siblings("wb install")))
        self.assertEqual((), tuple(command_gate.siblings("approve-plan")))

    def test_an_exact_form_with_arguments_that_hold_the_word_is_still_allowed(self):
        self.assertIsNone(self.judge("wb install --dir /x --package a/install"))

    def test_the_message_for_a_key_at_none_does_not_name_an_ask_rule(self):
        reason = command_gate.judge("bash -c 'wb install'", ["wb install"], STORE_BIN, {"wb install": "none"})
        self.assertIsNotNone(reason)
        self.assertNotIn("ask rule", reason)
        self.assertIn("none", reason)
        self.assertIn("~", reason)
        asked = command_gate.judge("bash -c 'wb install'", ["wb install"], STORE_BIN, {"wb install": "ask"})
        self.assertIn("ask rule", asked)
        unknown = command_gate.judge("bash -c 'wb install'", ["wb install"], STORE_BIN)
        self.assertIn("ask rule", unknown)

    def test_the_provides_form_is_not_exempt_and_a_word_in_its_arguments_is(self):
        self.assertIsNotNone(self.judge("wb run --provides cap helper commit --subject 'install'"))
        self.assertIsNone(self.judge("wb run helper --provides install"))

    def test_an_option_with_the_quote_after_an_equals_sign_is_not_the_literal_form(self):
        self.assertIsNotNone(self.judge("wb run helper commit --subject='install'"))

    def test_a_store_path_with_regex_characters_is_matched_literally(self):
        odd = "/tmp/a b(c)+[x]/bin/wb"
        self.assertIsNone(command_gate.judge("%s run helper commit --subject 'install'" % odd, ["wb install"], odd))
        self.assertIsNotNone(command_gate.judge("/tmp/aXb(c)+[x]/bin/wb run helper 'install' ; wb install", ["wb install"], odd))
        self.assertIsNotNone(command_gate.judge("/tmp/a b(c)+x/bin/wb run helper 'install' | xargs wb", ["wb install"], odd))

    def test_a_very_long_command_is_judged_quickly(self):
        import time
        started = time.monotonic()
        long_run = "wb run helper " + " ".join("'a b c'" for _ in range(8000))
        self.assertIsNone(self.judge(long_run + " 'install'"))
        self.assertIsNotNone(self.judge(long_run + " 'install' ; wb install"))
        self.assertIsNotNone(self.judge(long_run + " 'install"))
        self.assertLess(time.monotonic() - started, 5)

    def test_the_word_built_from_the_sibling_name_stays_blocked_however_far_apart(self):
        keys = ("wb approve",)
        padding = " ".join("filler%d" % n for n in range(40))
        for command in ("A=approve-plan; wb ${A%-plan} x", "A=approve-plan; wb ${A/-plan} x", "A=approve-plan; wb ${A%%-*} x",
                        "A=approve-plan; echo %s; wb ${A%%-plan}" % padding, "echo approve-plan | xargs wb",
                        "python3 -m workbench ${A%-plan}; x=approve-plan"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command, keys=keys))
        self.assertIsNone(self.judge("python3 -m workbench approve-plan docs/plans/a.md", keys=keys))
        self.assertIsNone(self.judge("%s approve-plan docs/plans/a.md" % STORE_BIN, keys=keys))

    def test_a_decision_obfuscation_stays_blocked_with_the_exemption_in_place(self):
        for command in ('w""b install', 'wb inst""all', "wb $'\\x69nstall'", "w" + BS + "b install", "w" + BS + "\nb install",
                        "wb inst" + BS + "\nall", "echo install | xargs w" + BS + "\nb", "echo install | xargs wb",
                        "wb inst*", "${X}wb install", "W=w; ${W}b install"):
            with self.subTest(command=command):
                self.assertIsNotNone(self.judge(command))


class ModuleArgumentIsData(unittest.TestCase):
    """For a key ``wb run <command> <argument>``, a literal call of that command whose first argument is another plain token
    names the key's argument only as data (``2026-10-28-gate-reads-module-arguments``)."""

    ARGUMENTS = ("extend", "reset", "archive", "amend", "prune")
    DOC = "docs/plans/a.md"
    RE = "wb run vault"

    def key(self, argument):
        return "wb run vault " + argument

    def judge(self, command, argument, **more):
        return judge(command, keys=(self.key(argument),) + more.get("also", ()))

    def test_a_preview_and_other_arguments_of_the_command_are_allowed(self):
        for argument in self.ARGUMENTS:
            for command in ("%s preview %s %s 4" % (self.RE, argument, self.DOC),
                            "%s decide %s F1 applied --reason 'the %s bound'" % (self.RE, self.DOC, argument),
                            "%s status %s" % (self.RE, self.DOC),
                            "%s preview %s %s 4" % (STORE_BIN, argument, self.DOC)):
                with self.subTest(argument=argument, command=command):
                    if command.startswith(STORE_BIN):
                        command = command.replace(STORE_BIN, STORE_BIN + " run vault", 1)
                    self.assertIsNone(self.judge(command, argument))

    def test_the_exact_simple_form_of_the_argument_is_still_allowed(self):
        for argument in self.ARGUMENTS:
            for tail in ("", " 4", " 4 --digest " + DIGEST):
                with self.subTest(argument=argument, tail=tail):
                    self.assertIsNone(self.judge("%s %s %s%s" % (self.RE, argument, self.DOC, tail), argument))

    def test_a_first_argument_that_is_not_plain_is_still_searched(self):
        for argument in self.ARGUMENTS:
            hexa = "$'" + "".join("\\x%02x" % ord(char) for char in argument) + "'"
            for command in ("%s '%s' %s 4" % (self.RE, argument, self.DOC),
                            "%s %s''%s %s 4" % (self.RE, argument[:2], argument[2:], self.DOC),
                            '%s "preview" %s %s 4' % (self.RE, argument, self.DOC),
                            '%s "%s" %s 4' % (self.RE, argument, self.DOC),
                            "%s %s %s 4" % (self.RE, hexa, self.DOC),
                            "A=preview; %s $A %s %s 4" % (self.RE, argument, self.DOC),
                            "%s ${A} %s %s 4" % (self.RE, argument, self.DOC),
                            "%s pre* %s %s 4" % (self.RE, argument, self.DOC),
                            "%s %s %s 4" % (self.RE, argument.capitalize(), self.DOC),
                            "%s %s" % (self.RE, argument + BS + "\n" + self.DOC)):
                with self.subTest(argument=argument, command=command):
                    self.assertIsNotNone(self.judge(command, argument))

    def test_a_compound_or_multiline_command_is_still_searched(self):
        for argument in self.ARGUMENTS:
            for command in ("%s preview %s %s 4; %s %s %s 4" % (self.RE, argument, self.DOC, self.RE, argument, self.DOC),
                            "%s preview %s %s 4 && %s %s %s 4" % (self.RE, argument, self.DOC, self.RE, argument, self.DOC),
                            "%s preview %s %s 4\n%s %s %s 4" % (self.RE, argument, self.DOC, self.RE, argument, self.DOC),
                            "%s preview %s %s 4\n" % (self.RE, argument, self.DOC),
                            "%s\npreview %s %s 4" % (self.RE, argument, self.DOC),
                            "%s preview %s %s 4 | xargs" % (self.RE, argument, self.DOC),
                            "bash -c '%s preview %s %s 4'" % (self.RE, argument, self.DOC),
                            "%s preview %s $(echo %s)" % (self.RE, argument, self.DOC),
                            "%s preview %s `echo %s`" % (self.RE, argument, self.DOC),
                            "%s preview %s %s 4 > out" % (self.RE, argument, self.DOC),
                            "%s preview %s \"%s\" 4" % (self.RE, argument, self.DOC)):
                with self.subTest(argument=argument, command=command):
                    self.assertIsNotNone(self.judge(command, argument))

    def test_only_the_keys_own_command_is_freed(self):
        for argument in self.ARGUMENTS:
            for command in ("wb run helper commit --subject 'vault %s'" % argument,
                            "wb run --provides cap vault preview %s %s" % (argument, self.DOC),
                            "wb run vault-x preview vault %s" % argument):
                with self.subTest(argument=argument, command=command):
                    self.assertIsNotNone(self.judge(command, argument))

    def test_a_differently_named_command_is_judged_as_before(self):
        self.assertIsNone(self.judge("wb run other preview extend", "extend"))

    def test_the_freeing_is_decided_per_key(self):
        # `reset` is the first argument and the second key's own argument: not freed for that key, though freed for the first.
        command = "%s reset %s 'x'" % (self.RE, self.DOC)
        self.assertIsNone(self.judge(command, "extend"))
        self.assertIsNotNone(self.judge(command, "extend", also=(self.key("reset"),)))
        self.assertIsNone(self.judge("%s reset %s 4" % (self.RE, self.DOC), "extend", also=(self.key("reset"),)))
        self.assertIsNone(self.judge("%s preview reset %s" % (self.RE, self.DOC), "extend"))
        self.assertIsNone(self.judge("%s preview reset %s" % (self.RE, self.DOC), "reset", also=(self.key("extend"),)))

    def test_another_module_key_follows_the_same_rule(self):
        key = "wb run ledger init"
        self.assertIsNone(judge("wb run ledger init", keys=(key,)))
        self.assertIsNone(judge("wb run ledger search init", keys=(key,)))
        self.assertIsNotNone(judge("wb run ledger 'init'", keys=(key,)))
        self.assertIsNotNone(judge("wb run ledger search 'x'; wb run ledger init", keys=(key,)))

    def test_a_key_at_none_is_freed_the_same_way_and_its_block_does_not_name_an_ask_rule(self):
        key = self.key("extend")
        levels = {key: "none"}
        self.assertIsNone(command_gate.judge("%s preview extend %s 4" % (self.RE, self.DOC), [key], STORE_BIN, levels))
        reason = command_gate.judge("%s 'extend' %s 4" % (self.RE, self.DOC), [key], STORE_BIN, levels)
        self.assertIsNotNone(reason)
        self.assertNotIn("ask rule", reason)

    def test_a_first_token_that_only_looks_like_the_argument_is_freed_because_the_launcher_refuses_it(self):
        # The launcher compares the first argument exactly, so none of these runs the key's argument.
        for token in ("extend.", "-extend", "--", "-x", "=extend", "./extend", "extend=1", "extend,"):
            with self.subTest(token=token):
                self.assertIsNone(self.judge("%s %s %s 4" % (self.RE, token, self.DOC), "extend"))

    def test_a_very_long_literal_call_is_judged_quickly(self):
        import time
        started = time.monotonic()
        long_call = "%s preview extend %s %s" % (self.RE, self.DOC, " ".join("'a b c'" for _ in range(8000)))
        self.assertIsNone(self.judge(long_call, "extend"))
        self.assertIsNotNone(self.judge(long_call + " 'x", "extend"))
        self.assertLess(time.monotonic() - started, 5)

    def test_the_other_kinds_of_key_are_judged_as_before(self):
        self.assertIsNotNone(judge("wb run vault preview 'approve-plan'", keys=("approve-plan",)))
        self.assertIsNone(judge("wb run helper commit --subject 'install'", keys=("wb install",)))
        self.assertIsNotNone(judge("bash -c 'wb install'", keys=("wb install",)))


def run(payload, prepare=None):
    """The gate on `payload`; `prepare(cwd)` gives ``(tool, field, table, store bin path)``."""
    err = io.StringIO()
    text = payload if isinstance(payload, str) else json.dumps(payload)
    code = command_gate.run(io.StringIO(text), err, prepare or _prepare)
    return code, err.getvalue()


def _prepare(cwd):
    return "Bash", "command", {"approve-plan": "ask"}, STORE_BIN


class Constants(unittest.TestCase):
    def test_the_layouts_minimum_harness_timeout_follows_the_gates_deadline(self):
        from workbench import gate_hook, layout
        self.assertEqual(gate_hook.DEADLINE, layout.GATE_DEADLINE)


class Protocol(unittest.TestCase):
    def call(self, command, **extra):
        payload = {"cwd": "/tmp", "tool_name": "Bash", "tool_input": {"command": command}}
        payload.update(extra)
        return run(payload)

    def test_allow_prints_nothing_and_returns_0(self):
        self.assertEqual((0, ""), self.call("wb check"))
        self.assertEqual((0, ""), self.call("wb approve-plan docs/plans/a.md --digest " + DIGEST))

    def test_block_prints_one_refused_line_and_returns_2(self):
        code, err = self.call("bash -c 'wb approve-plan x'")
        self.assertEqual(2, code)
        self.assertTrue(err.startswith("refused: "), err)
        self.assertEqual(1, err.count("\n"), err)

    def test_every_malformed_input_is_a_block(self):
        for payload in ("", "not json", "[]", "null", json.dumps({"cwd": "/tmp"}),
                        json.dumps({"cwd": "/tmp", "tool_name": "Bash"}),
                        json.dumps({"cwd": "/tmp", "tool_name": "Bash", "tool_input": {}}),
                        json.dumps({"cwd": "/tmp", "tool_name": "Bash", "tool_input": {"command": 5}}),
                        json.dumps({"cwd": "/tmp", "tool_name": "Bash", "tool_input": {"command": None}}),
                        json.dumps({"cwd": 5, "tool_name": "Bash", "tool_input": {"command": "wb check"}}),
                        json.dumps({"cwd": "/tmp", "tool_name": "Write", "tool_input": {"command": "wb check"}})):
            with self.subTest(payload=payload[:40]):
                self.assertEqual(2, run(payload)[0])

    def test_an_oversize_command_is_a_block(self):
        code, err = self.call("echo " + "x" * (command_gate.MAX_COMMAND + 1))
        self.assertEqual(2, code)

    def test_the_tool_and_field_come_from_prepare_inside_the_guard(self):
        """Finding L3: the harness lookup runs under the deadline and the guard, so its failure is a block."""
        def broken(cwd):
            raise OSError("cannot hash the packages")
        payload = {"cwd": "/tmp", "tool_name": "Bash", "tool_input": {"command": "wb check"}}
        self.assertEqual(2, run(payload, broken)[0])
        self.assertEqual(2, run(payload, lambda cwd: ("Write", "command", {"approve-plan": "ask"}, STORE_BIN))[0])
        self.assertEqual(2, run(payload, lambda cwd: ("Bash", "cmd", {"approve-plan": "ask"}, STORE_BIN))[0])

    def test_a_failure_to_prepare_is_a_block(self):
        def broken(cwd):
            raise command_gate.gate_hook.Refusal("no project")
        payload = {"cwd": "/tmp", "tool_name": "Bash", "tool_input": {"command": "wb check"}}
        code, err = run(payload, broken)
        self.assertEqual(2, code)
        self.assertIn("no project", err)

    def test_a_crash_is_a_block(self):
        def crash(cwd):
            raise RuntimeError("boom")
        payload = {"cwd": "/tmp", "tool_name": "Bash", "tool_input": {"command": "wb check"}}
        self.assertEqual(2, run(payload, crash)[0])

    def test_no_relaxed_key_allows_everything(self):
        payload = {"cwd": "/tmp", "tool_name": "Bash", "tool_input": {"command": "bash -c 'wb approve-plan x'"}}
        self.assertEqual(0, run(payload, lambda cwd: ("Bash", "command", {"approve-plan": "block"}, STORE_BIN))[0])

    def test_relaxed_means_ask_or_none_in_the_table(self):
        payload = {"cwd": "/tmp", "tool_name": "Bash", "tool_input": {"command": "bash -c 'wb approve-plan x'"}}
        for level in ("ask", "none"):
            with self.subTest(level=level):
                self.assertEqual(2, run(payload, lambda cwd, level=level: (
                    "Bash", "command", {"approve-plan": level}, STORE_BIN))[0])


class AgentSafeCommandsTest(unittest.TestCase):
    """Increment C of plan 2026-10-27-a-level-for-every-command: the agent-safe keys never make the gate block a command."""

    COMMANDS = ("wb check", "wb verify docs", "wb settings", "wb launch p n --root r", "wb plan-status docs/plans/a.md",
                "wb preview install --dir x", "wb preview adopt --dir x", "wb run tool check")

    def test_no_agent_safe_command_is_blocked_when_no_key_is_relaxed(self):
        for command in self.COMMANDS:
            with self.subTest(command=command):
                self.assertIsNone(command_gate.judge(command, (), STORE_BIN))

    def test_no_agent_safe_command_is_blocked_by_a_relaxed_owner_run_key(self):
        for command in self.COMMANDS:
            with self.subTest(command=command):
                self.assertIsNone(command_gate.judge(command, ("wb pin",), STORE_BIN))
                self.assertIsNone(command_gate.judge(command, (APPROVE,), STORE_BIN))


if __name__ == "__main__":
    unittest.main()

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


def judge(command, keys=(APPROVE,)):
    return command_gate.judge(command, keys, STORE_BIN)


class Allowed(unittest.TestCase):
    def test_the_exact_forms_the_ask_rule_matches(self):
        for command in ("wb approve-plan docs/plans/2026-10-26-a.md",
                        "wb approve-plan docs/plans/2026-10-26-a.md --digest " + DIGEST,
                        "%s approve-plan docs/plans/a.md --digest %s" % (STORE_BIN, DIGEST),
                        "  wb approve-plan docs/plans/a.md --digest %s\n" % DIGEST):
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


def run(payload, prepare=None):
    """The gate on `payload`; `prepare(cwd)` gives ``(table, store bin path)``."""
    err = io.StringIO()
    text = payload if isinstance(payload, str) else json.dumps(payload)
    code = command_gate.run(io.StringIO(text), err, prepare or _prepare, "Bash", "command")
    return code, err.getvalue()


def _prepare(cwd):
    return {"approve-plan": "ask"}, STORE_BIN


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
        self.assertEqual(0, run(payload, lambda cwd: ({"approve-plan": "block"}, STORE_BIN))[0])

    def test_relaxed_means_ask_or_none_in_the_table(self):
        payload = {"cwd": "/tmp", "tool_name": "Bash", "tool_input": {"command": "bash -c 'wb approve-plan x'"}}
        for level in ("ask", "none"):
            with self.subTest(level=level):
                self.assertEqual(2, run(payload, lambda cwd, level=level: ({"approve-plan": level}, STORE_BIN))[0])


if __name__ == "__main__":
    unittest.main()

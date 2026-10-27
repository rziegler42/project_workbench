"""The grammar of a prompted command and its one parse (`docs/specs/action-review.md`, "The reviewed command is the
command that runs"). Plan `2026-10-26-action-review-engine`, increment C.

The unit tests state each accepted form and each refused character class. The property tests generate command text
over the grammar's alphabet and the quote forms: the engine and a reference reading of the grammar must agree on every
text, and for every accepted text the engine's words must equal the argument list `sh` and `zsh` pass to a program
that only prints its arguments. A missing shell skips its test with a reason."""

import io
import json
import os
import random
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

from tests import support_helpers

HELPER = None
BARE = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._/:=@%+,-"
SPECIAL = "\"\\$`*?[~{}#;&|<>()!^\n\t\r\0\x7f"
DECLARED = frozenset(("--flag", "--"))


def setUpModule():
    global HELPER
    HELPER = support_helpers.load("action-review")


def values(words):
    return [w.text for w in words]


class Accepted(unittest.TestCase):
    def test_a_single_bare_word(self):
        self.assertEqual(["wb"], values(HELPER.parse_words("wb")))

    def test_bare_words_of_the_whole_alphabet_each_separated_by_one_space(self):
        words = HELPER.parse_words("wb run safe-git commit a.b_c/d:e=f@g%h+i,j")
        self.assertEqual(["wb", "run", "safe-git", "commit", "a.b_c/d:e=f@g%h+i,j"], values(words))
        self.assertEqual([False] * 5, [w.quoted for w in words])

    def test_a_single_quoted_word_holds_every_other_character_literally(self):
        body = "a b \"\\$`*?[~{}#;&|<>()!^\t\r\u00e9 -x"
        words = HELPER.parse_words("wb 'x" + body + "'")
        self.assertEqual(["wb", "x" + body], values(words))
        self.assertTrue(words[1].quoted)

    def test_an_empty_quoted_word_is_an_empty_argument(self):
        self.assertEqual(["wb", ""], values(HELPER.parse_words("wb ''")))

    def test_a_declared_flag_and_the_separator_are_accepted_and_a_value_may_follow(self):
        words = HELPER.parse_words("wb --flag 'v w' -- p", DECLARED)
        self.assertEqual(["wb", "--flag", "v w", "--", "p"], values(words))

    def test_a_quoted_word_equal_to_a_bare_one_has_the_same_value(self):
        self.assertEqual(values(HELPER.parse_words("wb run")), values(HELPER.parse_words("'wb' 'run'")))

    def test_an_equals_sign_inside_a_later_word_is_an_ordinary_character(self):
        self.assertEqual(["wb", "a=b", "c=d"], values(HELPER.parse_words("wb a=b c=d")))

    def test_a_quoted_first_word_that_looks_like_an_assignment_is_a_command_name(self):
        self.assertEqual(["A=b", "wb"], values(HELPER.parse_words("'A=b' wb")))

    def test_the_longest_text_is_accepted(self):
        text = "wb " + "a" * (HELPER.MAX_TEXT - 3)
        self.assertEqual(HELPER.MAX_TEXT, len(text))
        self.assertEqual(2, len(HELPER.parse_words(text)))


class Refused(unittest.TestCase):
    def refused(self, text, declared=frozenset(), contains=None):
        with self.assertRaises(HELPER.Unreviewable) as caught:
            HELPER.parse_words(text, declared)
        if contains:
            self.assertIn(contains, str(caught.exception))

    def test_each_character_outside_the_grammar_is_refused_in_the_middle_of_a_word_and_alone(self):
        for char in SPECIAL:
            self.refused("wb a%sb" % char)
            self.refused("wb %s" % char)
            self.refused("wb a %s b" % char)

    def test_a_character_class_is_named_in_the_refusal(self):
        self.refused("wb a$b", contains="outside the grammar")

    def test_double_quotes_backslashes_backticks_and_expansions_are_refused_outside_single_quotes(self):
        for text in ('wb "a"', "wb a\\ b", "wb `a`", "wb $(a)", "wb ${a}", "wb $a"):
            self.refused(text)

    def test_a_newline_or_tab_between_words_is_refused(self):
        for text in ("wb\nrun", "wb\trun", "wb run\n", "wb run\t", "\nwb"):
            self.refused(text)

    def test_a_newline_or_a_nul_inside_single_quotes_is_refused(self):
        self.refused("wb 'a\nb'")
        self.refused("wb 'a\0b'")

    def test_a_lone_surrogate_that_cannot_be_encoded_is_refused(self):
        self.refused("wb '\udc80'")
        self.refused("wb \udc80")

    def test_an_environment_prefix_is_refused(self):
        for text in ("A=1 wb run", "_a1=x wb", "ab= wb", "A=1", "x+=1 wb", "a+= wb", "PATH+=:/tmp wb", "a.b=1 wb"):
            self.refused(text, contains="assignment")

    def test_a_bare_word_that_begins_with_an_equals_sign_is_refused(self):
        self.refused("wb =ls")
        self.refused("=ls")

    def test_a_leading_trailing_or_doubled_space_is_refused(self):
        for text in (" wb", "wb ", "wb  run", "wb run  x", " ", "  ", "wb   "):
            self.refused(text)

    def test_the_empty_text_and_a_non_string_are_refused(self):
        self.refused("")
        for value in (None, b"wb", 1, ["wb"]):
            self.refused(value)

    def test_a_text_over_the_limit_is_refused(self):
        self.refused("wb " + "a" * (HELPER.MAX_TEXT - 2), contains="longer than")

    def test_an_unterminated_quote_is_refused(self):
        self.refused("wb 'a")
        self.refused("wb '")

    def test_a_quote_beside_a_word_or_another_quote_is_refused(self):
        for text in ("wb 'a'b", "wb a'b'", "wb 'a''b'", "wb 'a'  'b'", "wb a'b", "wb ''''"):
            self.refused(text)

    def test_a_bare_word_beginning_with_a_dash_that_is_not_declared_is_refused(self):
        self.refused("wb -x", contains="not declared")
        self.refused("wb --flag", contains="not declared")
        self.refused("wb --", contains="not declared")
        self.refused("wb --other", DECLARED, contains="not declared")
        self.refused("wb -", DECLARED, contains="not declared")

    def test_a_flag_written_with_an_equals_sign_is_an_undeclared_word(self):
        self.refused("wb --flag=v", DECLARED, contains="not declared")

    def test_a_quoted_word_beginning_with_a_dash_is_refused_even_when_a_flag_of_that_spelling_is_declared(self):
        self.refused("wb '-x'")
        self.refused("wb '--flag'", DECLARED, contains="quoted")
        self.refused("wb '-'")
        self.refused("'-wb'")

    def test_the_declared_set_is_exact_and_whole_word(self):
        self.refused("wb --flagx", DECLARED)
        self.refused("wb --fla", DECLARED)


class Split(unittest.TestCase):
    def words(self, text):
        return HELPER.parse_words(text, DECLARED)

    def test_it_returns_the_words_after_the_spelling_and_the_subcommand(self):
        arguments = HELPER.split_command(self.words("wb run safe-git commit --flag 'a b' -- p"),
                                         ("wb", "run", "safe-git"), "commit")
        self.assertEqual(["--flag", "a b", "--", "p"], [w.text for w in arguments])

    def test_a_quoted_word_matches_the_spelling_by_its_value(self):
        arguments = HELPER.split_command(self.words("'wb' run 'safe-git' 'commit' x"), ("wb", "run", "safe-git"),
                                         "commit")
        self.assertEqual(["x"], [w.text for w in arguments])

    def test_it_matches_whole_words_only(self):
        spelling = ("wb", "run", "safe-git")
        for text in ("wb run safe-git commit2", "wb run safe-git2 commit", "wb run safe commit", "wb2 run safe-git commit",
                     "wb run safe-git Commit", "x wb run safe-git commit", "wb run safe-git", "wb run", "wb"):
            self.assertIsNone(HELPER.split_command(self.words(text), spelling, "commit"), text)

    def test_a_command_with_no_arguments_gives_an_empty_list(self):
        self.assertEqual([], HELPER.split_command(self.words("wb run safe-git commit"), ("wb", "run", "safe-git"),
                                                  "commit"))


class Review(unittest.TestCase):
    def call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = HELPER.main(list(argv), io.BytesIO(b""), out, err, os.getcwd())
        return code, out.getvalue(), err.getvalue()

    def test_text_outside_the_grammar_is_refused_as_unreviewable_with_nothing_on_standard_output(self):
        for text in ("wb run safe-git commit $(x)", "A=1 wb", "wb  run", ""):
            code, out, err = self.call("review", text)
            self.assertEqual((1, ""), (code, out), text)
            self.assertTrue(err.startswith("refused: unreviewable: "), (text, err))
            self.assertEqual(1, len(err.splitlines()), text)

    def test_log_row_comes_first_and_the_text_is_exactly_one_argument(self):
        code, out, err = self.call("review", "--log-row", "wb $x")
        self.assertEqual((1, ""), (code, out))
        self.assertTrue(err.startswith("refused: unreviewable: "), err)
        for argv in (("review",), ("review", "--log-row"), ("review", "a", "b"), ("review", "wb", "--log-row"),
                     ("review", "--other", "wb"), ("review", "--log-row", "--log-row", "wb"),
                     ("review", "--log-row", "wb", "x")):
            code, out, err = self.call(*argv)
            self.assertEqual((1, ""), (code, out), argv)
            self.assertTrue(err.startswith("refused: usage: action-review review"), (argv, err))

    def test_a_text_inside_the_grammar_is_still_refused_because_no_rule_is_loaded_yet(self):
        code, out, err = self.call("review", "wb run safe-git commit 'x y' a")
        self.assertEqual((1, ""), (code, out))
        self.assertIn("not built", err)


def reference_accepts(text, declared=DECLARED):
    """The grammar read independently of the engine: a regular expression and the stated extra rules."""
    if not isinstance(text, str) or not text or len(text) > 4096:
        return False
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    word = r"(?:[A-Za-z0-9._/:=@%%+,-]+|'[^'\n\0]*')"
    if not re.fullmatch(r"%s(?: %s)*" % (word, word), text):
        return False
    words = re.findall(word, text)
    if "=" in words[0] and not words[0].startswith("'"):
        return False
    for each in words:
        if each.startswith("'"):
            if each[1:2] == "-":
                return False
        elif each.startswith("="):
            return False
        elif each.startswith("-") and each not in declared:
            return False
    return True


def generated_text(rng):
    """A text built from the grammar's own parts, so most are accepted."""
    words = []
    for _ in range(rng.randint(1, 6)):
        kind = rng.random()
        if kind < 0.3:
            words.append(rng.choice(sorted(DECLARED)))
        elif kind < 0.65:
            head = rng.choice(BARE.replace("-", "").replace("=", ""))
            words.append(head + "".join(rng.choice(BARE) for _ in range(rng.randint(0, 8))))
        else:
            alphabet = BARE + SPECIAL.replace("\n", "").replace("\0", "") + " \u00e9\u00a0\u2028\x1b\x80\x83\x9f"
            body = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8)))
            words.append("'" + body.lstrip("-") + "'")
    first = words[0]
    if "=" in first or first.startswith("-"):
        words[0] = "wb"
    return " ".join(words)


def random_text(rng):
    """Text over the alphabet, the specials, space and the quote, most of it outside the grammar."""
    alphabet = BARE + SPECIAL + "  ''"
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))


class Property(unittest.TestCase):
    def test_the_engine_accepts_exactly_the_texts_the_reference_reading_accepts(self):
        rng = random.Random(20261026)
        accepted = 0
        texts = [generated_text(rng) for _ in range(3000)] + [random_text(rng) for _ in range(6000)]
        texts += ["wb " + c + d for c in BARE + SPECIAL + "' " for d in ("", "x", "'")]
        for text in texts:
            try:
                HELPER.parse_words(text, DECLARED)
                got = True
            except HELPER.Unreviewable:
                got = False
            self.assertEqual(reference_accepts(text), got, repr(text))
            accepted += got
        self.assertGreater(accepted, 1500)   # the run exercises both sides

    def test_every_character_alone_and_in_pairs_agrees_with_the_reference_reading(self):
        alphabet = BARE + SPECIAL + "' \u00e9"
        for first in alphabet:
            for second in alphabet:
                for text in (first + second, "wb " + first + second, "wb '" + first + second + "'"):
                    try:
                        HELPER.parse_words(text, DECLARED)
                        got = True
                    except HELPER.Unreviewable:
                        got = False
                    self.assertEqual(reference_accepts(text), got, repr(text))


class Shells(unittest.TestCase):
    """A fake `wb` that records its arguments is run by each shell with the generated text after it."""

    @classmethod
    def setUpClass(cls):
        holder = tempfile.TemporaryDirectory()
        cls.holder = holder
        cls.base = os.path.realpath(holder.name)
        cls.bin = os.path.join(cls.base, "bin")
        os.makedirs(cls.bin)
        cls.out = os.path.join(cls.base, "calls.jsonl")
        script = os.path.join(cls.bin, "wb")
        with open(script, "w") as handle:
            handle.write("#!%s -I\nimport json, os, sys\nwith open(os.environ['WB_OUT'], 'a', encoding='utf-8', "
                         "errors='surrogateescape') as out:\n    out.write(json.dumps(sys.argv[1:]) + '\\n')\n"
                         % sys.executable)
        os.chmod(script, stat.S_IRWXU)
        script = os.path.join(cls.bin, "wbenv")
        with open(script, "w") as handle:
            handle.write("#!%s -I\nimport json, os, sys\nwith open(os.environ['WB_ENV'], 'w', encoding='utf-8') as out:\n"
                         "    json.dump({'argv': sys.argv[1:], 'V': os.environ.get('V')}, out)\n" % sys.executable)
        os.chmod(script, stat.S_IRWXU)
        rng = random.Random(20261027)
        cls.texts = sorted({"wb " + generated_text(rng) for _ in range(400)})
        cls.texts = [t for t in cls.texts if reference_accepts(t)]

    @classmethod
    def tearDownClass(cls):
        cls.holder.cleanup()

    def run_shell(self, argv):
        if os.path.exists(self.out):
            os.remove(self.out)
        script = "\n".join(self.texts) + "\n"
        env = {"PATH": self.bin + os.pathsep + "/usr/bin:/bin", "WB_OUT": self.out, "HOME": self.base,
               "LC_ALL": "en_US.UTF-8", "LANG": "en_US.UTF-8"}
        done = subprocess.run(argv + [script], cwd=self.base, env=env, capture_output=True, timeout=120)
        self.assertEqual((0, b""), (done.returncode, done.stderr), argv)
        with open(self.out, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle]

    def agree(self, argv):
        calls = self.run_shell(argv)
        self.assertEqual(len(self.texts), len(calls))
        for text, got in zip(self.texts, calls):
            self.assertEqual(values(HELPER.parse_words(text, DECLARED))[1:], got, repr(text))

    def test_there_are_enough_accepted_texts(self):
        self.assertGreater(len(self.texts), 300)

    def test_sh_passes_the_arguments_the_engine_reads(self):
        self.agree(["/bin/sh", "-c"])

    def test_zsh_passes_the_arguments_the_engine_reads(self):
        zsh = shutil.which("zsh")
        if zsh is None:
            self.skipTest("zsh is not installed on this machine")
        self.agree([zsh, "-f", "-c"])

    def test_bash_passes_the_arguments_the_engine_reads(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash is not installed on this machine")
        self.agree([bash, "--noprofile", "--norc", "-c"])

    def shell_output(self, argv, script):
        """What `wbenv` recorded when the shell ran `script`: its arguments and the variable `V`."""
        record = os.path.join(self.base, "env.json")
        if os.path.exists(record):
            os.remove(record)
        env = {"PATH": self.bin + os.pathsep + "/usr/bin:/bin", "WB_ENV": record, "HOME": self.base}
        done = subprocess.run(argv + [script], cwd=self.base, env=env, capture_output=True, timeout=60)
        self.assertEqual((0, b""), (done.returncode, done.stderr), (argv, script))
        with open(record, encoding="utf-8") as handle:
            return json.load(handle)

    def shells(self):
        found = [("sh", ["/bin/sh", "-c"])]
        for name, flags in (("bash", ["--noprofile", "--norc", "-c"]), ("zsh", ["-f", "-c"])):
            path = shutil.which(name)
            if path:
                found.append((name, [path] + flags))
        return found

    def test_an_assignment_prefix_really_sets_the_environment_so_the_parser_refuses_it(self):
        for name, argv in self.shells():
            for first in ("V=1", "V+=1"):
                if name == "sh" and first == "V+=1":
                    continue   # the system sh in POSIX mode may not read the append form; it is refused anyway
                text = "%s wbenv x" % first
                self.assertIsNotNone(self.shell_output(argv, text)["V"], (name, text))
                with self.assertRaises(HELPER.Unreviewable):
                    HELPER.parse_words(text)

    def test_a_word_beginning_with_an_equals_sign_is_expanded_by_zsh_so_the_parser_refuses_it(self):
        zsh = shutil.which("zsh")
        if zsh is None:
            self.skipTest("zsh is not installed on this machine")
        got = self.shell_output([zsh, "-f", "-c"], "wbenv =wbenv")
        self.assertNotEqual(["=wbenv"], got["argv"])
        with self.assertRaises(HELPER.Unreviewable):
            HELPER.parse_words("wbenv =wbenv")


if __name__ == "__main__":
    unittest.main()

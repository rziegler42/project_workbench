"""The object `safe-git describe` prints: its fields, its caps and the rule that a value is left out whole
(plan `2026-10-25-safe-git-describe`, increment C; `docs/specs/safe-git.md`, "Caps and their sources").

The builder is tested on its own, with synthetic facts. The size of an object is the length of what the
helper prints: compact JSON with every non-ASCII character escaped, and the newline that ends the line."""

import io
import json
import unittest

from tests import support_helpers

H = support_helpers.load("safe-git")

CAP = 196608


def size(built):
    return len(H.render_description(built))


def pad(count):
    return "x" * count


def facts_of(built):
    return built["facts"]


class Fields(unittest.TestCase):
    def test_an_object_has_exactly_the_specified_fields(self):
        built = H.build_description("remove", [], [("name", "value")])
        self.assertEqual(["contract", "action", "ok", "truncated", "errors", "facts"], list(built))
        self.assertEqual((1, "remove", True, False, []), (built["contract"], built["action"], built["ok"],
                                                            built["truncated"], built["errors"]))
        self.assertEqual({"name": "value", "omitted": []}, built["facts"])

    def test_it_is_printed_as_one_compact_ascii_line(self):
        built = H.build_description("remove", [], [("name", "café 中 \U0001f600")])
        text = H.render_description(built)
        self.assertEqual(1, text.count("\n"))
        self.assertTrue(text.endswith("\n"))
        self.assertTrue(text.isascii())
        self.assertNotIn(": ", text)
        self.assertEqual("café 中 \U0001f600", json.loads(text)["facts"]["name"])

    def test_ok_is_true_only_when_there_is_no_error(self):
        self.assertTrue(H.build_description("remove", [], [])["ok"])
        built = H.build_description("remove", [("usage", "no path")], [])
        self.assertFalse(built["ok"])
        self.assertEqual([{"code": "usage", "message": "no path"}], built["errors"])

    def test_a_code_must_be_a_short_lower_case_word(self):
        for bad in ("", "Usage", "a-b", "a b", "x" * 65, "usage\n", None, 3):
            with self.subTest(code=bad):
                with self.assertRaises(ValueError):
                    H.build_description("remove", [(bad, "m")], [])
        H.build_description("remove", [("x" * 64, "m")], [])
        H.build_description("remove", [("a_9", "m")], [])

    def test_a_message_is_cleaned_and_cut_to_five_hundred_characters(self):
        built = H.build_description("remove", [("usage", "a\nb\x1b[31m‮" + pad(600))], [])
        message = built["errors"][0]["message"]
        self.assertEqual(500, len(message))
        self.assertTrue(message.isascii() and message.isprintable())

    def test_a_value_of_another_type_is_refused_by_the_builder(self):
        for bad in ({"a": 1}, 1.5, (1, 2), b"x", object(), [1], [None], [["a"]], [b"x"]):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    H.build_description("remove", [], [("name", bad)])

    def test_the_allowed_types_are_kept(self):
        facts = [("s", "text"), ("n", 7), ("t", True), ("f", False), ("z", None), ("a", ["x", "y"]), ("e", [])]
        got = H.build_description("remove", [], facts)["facts"]
        self.assertEqual({"s": "text", "n": 7, "t": True, "f": False, "z": None, "a": ["x", "y"], "e": [],
                          "omitted": []}, got)

    def test_a_fact_name_is_not_repeated_and_omitted_is_not_a_fact_of_the_caller(self):
        for facts in ([("a", 1), ("a", 2)], [("omitted", [])]):
            with self.subTest(facts=facts):
                with self.assertRaises(ValueError):
                    H.build_description("remove", [], facts)


class Numbers(unittest.TestCase):
    def test_a_whole_number_from_zero_to_two_to_the_53_minus_one_is_kept(self):
        for good in (0, 1, 2 ** 53 - 1):
            self.assertEqual(good, H.build_description("remove", [], [("n", good)])["facts"]["n"])

    def test_a_number_outside_that_range_is_refused_by_the_builder(self):
        for bad in (-1, 2 ** 53, 2 ** 64):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    H.build_description("remove", [], [("n", bad)])


class ValueCaps(unittest.TestCase):
    def test_a_string_of_32768_bytes_is_kept_and_one_byte_more_is_left_out(self):
        built = H.build_description("remove", [], [("s", pad(32768))])
        self.assertEqual(pad(32768), built["facts"]["s"])
        self.assertFalse(built["truncated"])
        built = H.build_description("remove", [], [("s", pad(32769)), ("after", 1)])
        self.assertEqual({"after": 1, "omitted": ["s"]}, built["facts"])
        self.assertTrue(built["truncated"])

    def test_the_cap_of_a_string_counts_bytes_and_not_characters(self):
        self.assertEqual(32768, len(H.build_description("remove", [], [("s", "é" * 16384)])["facts"]["s"]) * 2)
        self.assertEqual(["s"], H.build_description("remove", [], [("s", "é" * 16385)])["facts"]["omitted"])

    def test_the_diff_may_be_98304_bytes_and_no_more(self):
        built = H.build_description("commit", [], [("diff", pad(98304))])
        self.assertEqual(pad(98304), built["facts"]["diff"])
        built = H.build_description("commit", [], [("diff", pad(98305))])
        self.assertEqual(["diff"], built["facts"]["omitted"])
        self.assertTrue(built["truncated"])

    def test_the_diff_cap_is_measured_before_escaping(self):
        text = "\n" * 60000     # 120,000 bytes once each newline is escaped: over the cap, under the object's
        built = H.build_description("commit", [], [("diff", text)])
        self.assertEqual(text, built["facts"]["diff"])
        self.assertGreater(size(built), 98304)
        self.assertLessEqual(size(built), CAP)

    def test_only_the_diff_has_the_larger_string_cap(self):
        self.assertEqual(["other"], H.build_description("commit", [], [("other", pad(32769))])["facts"]["omitted"])

    def test_an_array_of_200_elements_is_kept_and_201_is_left_out(self):
        self.assertEqual(200, len(H.build_description("remove", [], [("a", ["p"] * 200)])["facts"]["a"]))
        built = H.build_description("remove", [], [("a", ["p"] * 201)])
        self.assertEqual({"omitted": ["a"]}, built["facts"])

    def test_an_element_of_1024_bytes_is_kept_and_1025_leaves_the_array_out(self):
        self.assertEqual([pad(1024)], H.build_description("remove", [], [("a", [pad(1024)])])["facts"]["a"])
        self.assertEqual(["a"], H.build_description("remove", [], [("a", ["p", pad(1025)])])["facts"]["omitted"])
        self.assertEqual(["a"], H.build_description("remove", [], [("a", ["é" * 513])])["facts"]["omitted"])

    def test_what_is_left_out_is_named_in_table_order_and_the_rest_is_still_tried(self):
        facts = [("first", pad(40000)), ("kept", 5), ("second", ["p"] * 300), ("last", pad(40000)), ("tail", True)]
        built = H.build_description("remove", [], facts)
        self.assertEqual({"kept": 5, "tail": True, "omitted": ["first", "second", "last"]}, built["facts"])
        self.assertTrue(built["truncated"])

    def test_a_caller_may_leave_a_fact_out_and_have_it_named(self):
        built = H.build_description("remove", [], [("total", H.OMIT), ("other", 1)])
        self.assertEqual({"other": 1, "omitted": ["total"]}, built["facts"])
        self.assertTrue(built["truncated"])


class ObjectCap(unittest.TestCase):
    """Seven strings, six of 30,000 bytes, that together fill the object."""

    def facts(self, extra=0):
        facts = [("s%d" % number, pad(30000)) for number in range(6)]
        base = size(H.build_description("remove", [], facts + [("s6", "")]))
        facts.append(("s6", pad(CAP - base + extra)))
        return facts

    def test_an_object_of_exactly_196608_bytes_is_kept_whole(self):
        built = H.build_description("remove", [], self.facts())
        self.assertEqual(CAP, size(built))
        self.assertFalse(built["truncated"])
        self.assertEqual([], built["facts"]["omitted"])

    def test_one_byte_more_leaves_out_the_value_that_crosses_the_cap(self):
        built = H.build_description("remove", [], self.facts(1))
        self.assertLessEqual(size(built), CAP)
        self.assertTrue(built["truncated"])
        self.assertEqual(["s6"], built["facts"]["omitted"])
        self.assertEqual(6, len([name for name in built["facts"] if name.startswith("s") and name != "s6"]))

    def test_naming_what_was_left_out_never_takes_the_object_past_the_cap(self):
        facts = self.facts() + [("later", pad(32769))]
        built = H.build_description("remove", [], facts)
        self.assertLessEqual(size(built), CAP)
        self.assertEqual(["s6", "later"], built["facts"]["omitted"])

    def test_a_value_is_never_cut(self):
        for built in (H.build_description("remove", [], self.facts(1)),
                      H.build_description("remove", [], self.facts() + [("later", pad(32769))])):
            for name, value in built["facts"].items():
                if name.startswith("s") and name != "omitted":
                    self.assertEqual(30000, len(value))


class Command(unittest.TestCase):
    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        code = H.main(list(argv), out, err, "/")
        return code, out.getvalue(), err.getvalue()

    def test_an_unknown_first_argument_exits_one_with_no_object(self):
        for argv in (["describe"], ["describe", "push "], ["describe", ""], ["describe", "Remove"],
                     ["describe", "--help"], ["describe", "remove "], ["describe", "push-check"]):
            with self.subTest(argv=argv):
                code, out, err = self.run_main(*argv)
                self.assertEqual((1, ""), (code, out))
                self.assertTrue(err.startswith("refused: "), err)
                self.assertEqual(1, len(err.splitlines()))

    def test_describe_is_a_command_of_the_helper(self):
        self.assertIn("describe", H.COMMANDS)


if __name__ == "__main__":
    unittest.main()

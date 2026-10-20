import ast
import unittest

from workbench import floor
from workbench.floor import FloorError, Stop

SPEC_BULLETS = (
    "force operations and rewriting history that has been pushed",
    "deleting uncommitted project files, or overwriting an existing or tracked file with fetched content",
    "publishing or deploying",
    "anything touching secrets",
    "installing dependencies",
)


class FloorTest(unittest.TestCase):
    def test_the_floor_is_the_five_entries_of_the_spec(self):
        self.assertEqual(tuple(stop.description for stop in floor.FLOOR), SPEC_BULLETS)
        ids = [stop.id for stop in floor.FLOOR]
        self.assertEqual(len(set(ids)), 5)

    def test_the_floor_cannot_be_changed_in_place(self):
        self.assertIsInstance(floor.FLOOR, tuple)
        with self.assertRaises(AttributeError):
            floor.FLOOR[0].id = "x"

    def test_without_additions_the_stops_are_the_floor(self):
        self.assertEqual(floor.effective_stops(), floor.FLOOR)
        self.assertEqual(floor.effective_stops([]), floor.FLOOR)

    def test_added_stops_follow_the_floor_sorted_by_id(self):
        extra = [Stop("start-a-print", "starting a print"), Stop("place-an-order", "placing an order")]
        got = floor.effective_stops(extra)
        self.assertEqual(got[:5], floor.FLOOR)
        self.assertEqual([stop.id for stop in got[5:]], ["place-an-order", "start-a-print"])

    def test_the_same_addition_twice_is_one_stop(self):
        stop = Stop("start-a-print", "starting a print")
        self.assertEqual(len(floor.effective_stops([stop, stop])), 6)

    def test_the_same_id_with_different_text_is_refused(self):
        with self.assertRaises(FloorError):
            floor.effective_stops([Stop("start-a-print", "one"), Stop("start-a-print", "two")])

    def test_any_removal_is_refused(self):
        for removal in (["publish-or-deploy"], ["touch-secrets", "start-a-print"], ["anything"]):
            with self.subTest(removal=removal):
                with self.assertRaisesRegex(FloorError, "cannot be removed"):
                    floor.effective_stops(removals=removal)
                with self.assertRaisesRegex(FloorError, "cannot be removed"):
                    floor.effective_stops([Stop("start-a-print", "starting a print")], removal)

    def test_removals_must_be_an_empty_list_or_tuple(self):
        for ok in ((), []):
            self.assertEqual(floor.effective_stops(removals=ok), floor.FLOOR)
        for bad in ("", "touch-secrets", None, 0, {}, set(), b"", iter(())):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(FloorError, "cannot be removed"):
                    floor.effective_stops(removals=bad)

    def test_a_subclass_of_stop_is_refused(self):
        class Shifty(Stop):
            __slots__ = ()
            shown = ["a"]

            @property
            def description(self):
                return "starting a print" if self.shown.pop() else ""

        with self.assertRaises(FloorError):
            floor.effective_stops([Shifty("start-a-print", "ignored")])

    def test_returned_stops_are_plain_stops(self):
        got = floor.effective_stops([Stop("start-a-print", "starting a print")])
        self.assertTrue(all(type(stop) is Stop for stop in got))

    def test_an_addition_that_repeats_a_floor_entry_is_refused(self):
        for stop_id in ("publish-or-deploy", "publishordeploy", "publish--or-deploy",
                        "touch-secrets", "install-dependencies"):
            with self.subTest(stop_id=stop_id):
                with self.assertRaises(FloorError):
                    floor.effective_stops([Stop(stop_id, "weaker wording")])

    def test_two_additions_that_differ_only_in_punctuation_are_refused(self):
        with self.assertRaises(FloorError):
            floor.effective_stops([Stop("start-print", "a"), Stop("startprint", "b")])

    def test_malformed_additions_are_refused(self):
        bad = [("not a stop", ), "touch-secrets", None, 5,
               Stop("Upper", "text"), Stop("", "text"), Stop("a" * 65, "text"),
               Stop("ok", ""), Stop("ok", "x" * 201), Stop("ok", "line\nbreak"),
               Stop("ok", "esc\x1b[31m"), Stop(5, "text"), Stop("ok", None),
               Stop("1abc", "text")]
        for item in bad:
            with self.subTest(item=item):
                with self.assertRaises(FloorError):
                    floor.effective_stops([item])

    def test_a_string_is_not_a_list_of_additions(self):
        for text in ("start-a-print", b"x"):
            with self.assertRaises(FloorError):
                floor.effective_stops(text)

    def test_the_floor_module_reads_no_file_and_knows_no_settings(self):
        with open(floor.__file__, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "." * node.level)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, ("open", "eval", "exec", "__import__"))
        self.assertEqual(imported, {"collections", "re"})


if __name__ == "__main__":
    unittest.main()

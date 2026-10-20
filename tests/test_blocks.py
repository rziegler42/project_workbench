import random
import unittest

from workbench import base, blocks, installplan

BEGIN = b"<!-- BEGIN p/m slot:policy -->\n"
END = b"<!-- END p/m slot:policy -->\n"
MARK = b"<!-- @slot: policy -->\n"
HEAD = b"# Title\n\ntext\n"
FILLED = HEAD + BEGIN + b"rule\n" + END + MARK + b"tail\n"


class Scan(unittest.TestCase):
    def test_file_without_markers(self):
        found = blocks.scan(b"# Title\n\nplain <!-- comment -->\n")
        self.assertEqual(([], []), (found.blocks, found.markers))

    def test_empty_file(self):
        self.assertEqual(([], []), tuple(blocks.scan(b"")))

    def test_a_filled_slot(self):
        found = blocks.scan(FILLED)
        (block,) = found.blocks
        self.assertEqual(("p/m", "policy"), (block.id, block.slot))
        self.assertEqual(BEGIN + b"rule\n" + END, block.text)
        self.assertEqual(b"rule\n", block.body)
        self.assertEqual(block.text, FILLED[block.start:block.end])
        (marker,) = found.markers
        self.assertEqual(("policy", MARK), (marker.slot, FILLED[marker.start:marker.end]))

    def test_marker_line_matches_the_base(self):
        self.assertEqual(base.marker("policy").encode() + b"\n", blocks.marker_line("policy"))

    def test_the_block_text_is_what_the_installer_hashes(self):
        files = installplan._Files()
        files.add("AGENTS.md", HEAD + MARK, "seeded", False, installplan.BASE_ORIGIN)
        out = []
        installplan._apply_fill(files, type("V", (), {"package": "p", "name": "m"})(),
                                "slot:policy", b"rule\n", out)
        self.assertEqual(files.items["AGENTS.md"]["data"], HEAD + BEGIN + b"rule\n" + END + MARK)
        (block,) = blocks.scan(files.items["AGENTS.md"]["data"]).blocks
        self.assertEqual(installplan._sha(block.text), out[0]["hash"])

    def test_crlf_markers_are_accepted(self):
        data = (b"a\r\n<!-- BEGIN p/m slot:policy -->\r\nx\r\n<!-- END p/m slot:policy -->\r\n"
                b"<!-- @slot: policy -->\r\n")
        found = blocks.scan(data)
        self.assertEqual(1, len(found.blocks))
        self.assertEqual(1, len(found.markers))

    def test_marker_on_the_last_line_without_a_line_feed(self):
        self.assertEqual(1, len(blocks.scan(b"a\n<!-- @slot: policy -->").markers))

    def test_two_blocks_in_one_slot(self):
        data = (BEGIN + b"a\n" + END + b"<!-- BEGIN q/n slot:policy -->\nb\n"
                b"<!-- END q/n slot:policy -->\n" + MARK)
        self.assertEqual(["p/m", "q/n"], [b.id for b in blocks.scan(data).blocks])

    def hostile(self, data):
        with self.assertRaises(blocks.BlockError, msg=data):
            blocks.scan(data)

    def test_hostile_shapes_are_refused(self):
        cases = [
            BEGIN + BEGIN + END,                               # nested BEGIN
            BEGIN + b"x\n" + END + BEGIN + b"x\n" + END,       # the same block twice
            END,                                               # END with no BEGIN
            b"x\n" + BEGIN + b"x\n",                           # BEGIN with no END
            BEGIN + b"x\n<!-- END q/m slot:policy -->\n",      # disagree on the ID
            BEGIN + b"x\n<!-- END p/m slot:other -->\n",       # disagree on the slot
            BEGIN + MARK + END,                                # slot marker inside a block
            b"<!-- BEGIN p/m slot:policy -->x\n",              # text after the marker
            b"<!-- BEGIN p/m slot:policy-->\n",                # no space
            b"<!-- BEGIN p slot:policy -->\n",                 # not package/module
            b"<!-- BEGIN p/m slot: -->\n",                     # empty slot
            b"<!-- BEGIN  p/m slot:policy -->\n",              # two spaces
            b"<!-- END p/m slot:policy --> \n",                # trailing space
            b"<!-- @slot:policy -->\n",                        # no space after the colon
            b"<!-- @slot: pol icy -->\n",
            b"<!-- @slot: ../x -->\n",
            b"<!-- BEGIN ../x/y slot:policy -->\n",
            b"<!-- BEGIN p/m slot:policy -->\r\r\n",
        ]
        for data in cases:
            self.hostile(data)

    def test_marker_lookalikes_not_at_line_start_are_text(self):
        data = b" <!-- BEGIN nonsense -->\n> <!-- END -->\ntext <!-- @slot: x -->\n"
        self.assertEqual(([], []), tuple(blocks.scan(data)))

    def test_not_bytes_is_refused(self):
        self.hostile("text")


class Edits(unittest.TestCase):
    def test_insert_goes_before_the_marker(self):
        out = blocks.insert(HEAD + MARK + b"tail\n", "p/m", "policy", b"rule\n")
        self.assertEqual(FILLED, out)

    def test_insert_adds_to_a_filled_slot_after_the_earlier_block(self):
        out = blocks.insert(FILLED, "q/n", "policy", b"more")
        self.assertEqual(HEAD + BEGIN + b"rule\n" + END
                         + b"<!-- BEGIN q/n slot:policy -->\nmore\n<!-- END q/n slot:policy -->\n"
                         + MARK + b"tail\n", out)

    def test_insert_equals_what_the_installer_builds(self):
        files = installplan._Files()
        files.add("AGENTS.md", HEAD + MARK, "seeded", False, installplan.BASE_ORIGIN)
        verified = type("V", (), {"package": "p", "name": "m"})()
        installplan._apply_fill(files, verified, "slot:policy", b"rule\n", [])
        self.assertEqual(files.items["AGENTS.md"]["data"],
                         blocks.insert(HEAD + MARK, "p/m", "policy", b"rule\n"))

    def test_insert_refuses(self):
        for data, filler, slot in ((HEAD, "p/m", "policy"),          # no marker
                                   (FILLED, "p/m", "policy"),        # already filled
                                   (MARK + MARK, "p/m", "policy"),   # ambiguous marker
                                   (MARK, "p/m", "other")):
            with self.subTest(data=data, slot=slot), self.assertRaises(blocks.BlockError):
                blocks.insert(data, filler, slot, b"x\n")

    def test_replace_changes_only_the_block(self):
        out = blocks.replace(FILLED, "p/m", "policy", b"new rule\n")
        self.assertEqual(HEAD + BEGIN + b"new rule\n" + END + MARK + b"tail\n", out)

    def test_replace_refuses_a_missing_block(self):
        for args in (("q/n", "policy"), ("p/m", "other")):
            with self.assertRaises(blocks.BlockError):
                blocks.replace(FILLED, *args, b"x\n")

    def test_append_adds_the_block_and_the_marker_at_the_end(self):
        out = blocks.append(HEAD, "p/m", "policy", b"rule\n")
        self.assertEqual(HEAD + BEGIN + b"rule\n" + END + MARK, out)

    def test_append_after_a_file_without_a_final_line_feed(self):
        out = blocks.append(b"text", "p/m", "policy", b"rule\n")
        self.assertEqual(b"text\n" + BEGIN + b"rule\n" + END + MARK, out)

    def test_append_to_an_empty_file(self):
        self.assertEqual(BEGIN + b"r\n" + END + MARK, blocks.append(b"", "p/m", "policy", b"r\n"))

    def test_the_result_of_append_is_an_ordinary_filled_slot(self):
        out = blocks.append(HEAD, "p/m", "policy", b"rule\n")
        self.assertEqual(blocks.PRESENT, blocks.slot_state(out, "policy", "p/m"))
        self.assertEqual(out[:-len(MARK)] + b"<!-- BEGIN q/n slot:policy -->\nx\n"
                         b"<!-- END q/n slot:policy -->\n" + MARK,
                         blocks.insert(out, "q/n", "policy", b"x\n"))

    def test_append_refuses_where_the_slot_has_a_marker_or_the_block_is_there(self):
        for data in (HEAD + MARK, FILLED):
            with self.assertRaises(blocks.BlockError):
                blocks.append(data, "p/m", "policy", b"x\n")

    def test_text_with_a_marker_line_is_refused(self):
        for text in (b"a\n<!-- @slot: x -->\n", b"<!-- BEGIN p/m slot:x -->\n", b"<!-- END a -->",
                     b"fine\r\n<!-- END p/m slot:x -->\r\n"):
            for edit in (lambda t: blocks.insert(HEAD + MARK, "p/m", "policy", t),
                         lambda t: blocks.replace(FILLED, "p/m", "policy", t),
                         lambda t: blocks.append(HEAD, "p/m", "policy", t)):
                with self.subTest(text=text), self.assertRaises(blocks.BlockError):
                    edit(text)

    def test_bad_names_are_refused(self):
        for filler, slot in (("p", "policy"), ("p/m", "po licy"), ("p/m", ""), ("../m/x", "s"),
                             ("p/m\n", "policy"), ("p/m", "policy\n")):
            with self.subTest(filler=filler, slot=slot), self.assertRaises(blocks.BlockError):
                blocks.insert(HEAD + MARK, filler, slot, b"x\n")

    def test_an_edit_of_a_damaged_file_is_refused(self):
        with self.assertRaises(blocks.BlockError):
            blocks.insert(BEGIN + MARK, "q/n", "policy", b"x\n")

    def test_bytes_outside_the_changed_span_are_identical(self):
        before = bytes(range(256)) * 3 + b"\n" + HEAD
        data = before + BEGIN + b"rule\n" + END + MARK + b"\xff\xfe tail"
        out = blocks.replace(data, "p/m", "policy", b"changed\n")
        self.assertTrue(out.startswith(before))
        self.assertTrue(out.endswith(MARK + b"\xff\xfe tail"))
        out = blocks.insert(data, "q/n", "policy", b"z\n")
        (old,) = blocks.scan(data).blocks
        self.assertEqual(data[:old.end], out[:old.end])
        self.assertEqual(MARK + b"\xff\xfe tail", out[-len(MARK + b"\xff\xfe tail"):])

    def test_crlf_text_outside_is_kept(self):
        data = b"a\r\n" + b"<!-- @slot: policy -->\r\nb\r\n"
        out = blocks.insert(data, "p/m", "policy", b"x\n")
        self.assertEqual(b"a\r\n" + BEGIN + b"x\n" + END + b"<!-- @slot: policy -->\r\nb\r\n", out)


class State(unittest.TestCase):
    def test_states(self):
        self.assertEqual(blocks.PRESENT, blocks.slot_state(FILLED, "policy", "p/m"))
        self.assertEqual(blocks.PRESENT, blocks.slot_state(FILLED, "policy", "p/m", True))
        self.assertEqual(blocks.OPEN, blocks.slot_state(HEAD + MARK, "policy", "p/m"))
        self.assertEqual(blocks.ABSENT, blocks.slot_state(HEAD, "policy", "p/m"))

    def test_a_file_with_no_markers_is_absent(self):
        self.assertEqual(blocks.ABSENT, blocks.slot_state(b"", "policy", "p/m"))

    def test_a_recorded_block_with_no_markers_is_gone(self):
        self.assertEqual(blocks.GONE, blocks.slot_state(HEAD, "policy", "p/m", True))
        self.assertEqual(blocks.GONE, blocks.slot_state(HEAD + MARK, "policy", "p/m", True))

    def test_another_filler_does_not_make_this_one_present(self):
        self.assertEqual(blocks.OPEN, blocks.slot_state(FILLED, "policy", "q/n"))

    def test_an_ambiguous_slot_is_refused(self):
        with self.assertRaises(blocks.BlockError):
            blocks.slot_state(MARK + MARK, "policy", "p/m")

    def test_a_damaged_file_is_refused(self):
        with self.assertRaises(blocks.BlockError):
            blocks.slot_state(BEGIN, "policy", "p/m")


class Fuzz(unittest.TestCase):
    """Random files of text lines and marker-like lines. A file is either refused or edited by
    changing only the span an edit owns."""

    PIECES = [b"text\n", b"\n", b"# heading\n", b"x\r\n", b"\xff\x00\n", BEGIN, END, MARK,
              b"<!-- BEGIN p/m slot:policy -->", b"<!-- END q/n slot:policy -->\n",
              b"<!-- @slot: other -->\n", b"<!-- BEGIN -->\n", b"<!-- @slot:\n", b"  <!-- END -->\n"]

    def test_edits_change_nothing_outside_their_span(self):
        rng = random.Random(20261020)
        edited = refused = 0
        for _ in range(8000):
            data = b"".join(rng.choice(self.PIECES) for _ in range(rng.randrange(0, 9)))
            try:
                found = blocks.scan(data)
            except blocks.BlockError:
                refused += 1
                for edit in (lambda: blocks.insert(data, "z/z", "policy", b"n\n"),
                             lambda: blocks.append(data, "z/z", "policy", b"n\n"),
                             lambda: blocks.replace(data, "p/m", "policy", b"n\n")):
                    with self.assertRaises(blocks.BlockError):
                        edit()
                continue
            try:
                out = blocks.insert(data, "z/z", "policy", b"n\n")
            except blocks.BlockError:
                out = None
            if out is not None:
                edited += 1
                at = next(m.start for m in found.markers if m.slot == "policy")
                new = b"<!-- BEGIN z/z slot:policy -->\nn\n<!-- END z/z slot:policy -->\n"
                self.assertEqual(data[:at] + new + data[at:], out)
                self.assertEqual(len(found.blocks) + 1, len(blocks.scan(out).blocks))
            try:
                out = blocks.append(data, "z/z", "policy", b"n\n")
            except blocks.BlockError:
                out = None
            if out is not None:
                self.assertTrue(out.startswith(data))
                self.assertEqual(len(found.blocks) + 1, len(blocks.scan(out).blocks))
            for block in found.blocks:
                out = blocks.replace(data, block.id, block.slot, b"r\n")
                self.assertEqual(data[:block.start], out[:block.start])
                self.assertEqual(data[block.end:], out[len(out) - (len(data) - block.end):])
        self.assertGreater(edited, 100)
        self.assertGreater(refused, 100)


if __name__ == "__main__":
    unittest.main()

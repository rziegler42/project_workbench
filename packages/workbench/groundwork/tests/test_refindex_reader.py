import copy
import json
import unittest

from tests import support_doccheck

refindex = support_doccheck.load("refcheck")
RefIndexError = refindex.RefIndexError

HASH = "a" * 64


def entry(name="docs/references/datasheet.pdf", **changes):
    value = {
        "file": name,
        "license": "CC-BY-4.0",
        "notes": "pin 3 is the enable",
        "retrieved": "2026-10-21",
        "sha256": HASH,
        "title": "Datasheet",
        "url": "https://example.com/datasheet.pdf",
        "version": "rev C",
    }
    value.update(changes)
    return value


def document(*entries, **changes):
    value = {"entries": list(entries) or [entry("docs/references/a.pdf"),
                                           entry("docs/references/b.pdf")],
             "format": 1}
    value.update(changes)
    return value


def refused(case, doc, field, area=refindex.AREA):
    with case.assertRaises(RefIndexError) as caught:
        refindex.serialize(doc, area)
    case.assertIn(field, str(caught.exception))
    return str(caught.exception)


def raw(doc):
    return json.dumps(doc, sort_keys=True).encode()


class Shape(unittest.TestCase):
    def test_the_canonical_bytes_are_stable_and_read_back(self):
        data = refindex.serialize(document())
        self.assertEqual(data, refindex.serialize(copy.deepcopy(document())))
        self.assertEqual(document(), refindex.parse(data))
        self.assertTrue(data.endswith(b"}\n"))
        data.decode("ascii")

    def test_the_layout_is_one_entry_per_line(self):
        lines = refindex.serialize(document()).decode().split("\n")
        self.assertEqual("{", lines[0])
        self.assertEqual('  "entries": [', lines[1])
        self.assertTrue(lines[2].startswith('    {"file": "docs/references/a.pdf"'))
        self.assertTrue(lines[2].endswith("},"))
        self.assertTrue(lines[3].endswith("}"))
        self.assertEqual(['  ],', '  "format": 1', '}', ''], lines[4:])

    def test_an_empty_index_is_valid_and_round_trips(self):
        data = refindex.serialize({"entries": [], "format": 1})
        self.assertEqual(b'{\n  "entries": [],\n  "format": 1\n}\n', data)
        self.assertEqual({"entries": [], "format": 1}, refindex.parse(data))

    def test_entries_must_be_sorted_by_file(self):
        doc = document(entry("docs/references/b.pdf"), entry("docs/references/a.pdf"))
        refused(self, doc, "not sorted")

    def test_a_file_may_not_repeat(self):
        refused(self, document(entry("docs/references/a.pdf"), entry("docs/references/a.pdf")),
                "repeat")

    def test_two_files_that_differ_only_in_case_are_refused(self):
        refused(self, document(entry("docs/references/A.pdf"), entry("docs/references/a.pdf")),
                "index")

    def test_a_file_may_not_also_be_a_directory(self):
        refused(self, document(entry("docs/references/a"), entry("docs/references/a/b.pdf")),
                "index")

    def test_the_untracked_index_is_read_with_its_own_area(self):
        doc = document(entry(".workbench/local/refs/a.pdf"))
        data = refindex.serialize(doc, refindex.LOCAL_AREA)
        self.assertEqual(doc, refindex.parse(data, refindex.LOCAL_AREA))
        refused(self, doc, "file")
        with self.assertRaises(RefIndexError):
            refindex.parse(data)


class Fields(unittest.TestCase):
    def test_every_hostile_file_is_refused_with_the_field_named(self):
        for name in ("/etc/passwd", "docs/references/../../x", "docs/references/../a.pdf",
                     "docs/references/.git/config", "docs/references/.GIT/config",
                     "docs/references/git~1/x", ".git/config", "docs/references",
                     "docs/references/", "docs/other/a.pdf", "a.pdf", "",
                     "docs/references//a.pdf", "docs/references/./a.pdf",
                     "docs/references/a\\b.pdf", "docs/references/c:a.pdf",
                     "docs/references/a\x1b[31m.pdf", "docs/references/a\nb.pdf",
                     "DOCS/REFERENCES/../x", ".workbench/local/refs/a.pdf",
                     "docs/references-extra/a.pdf", "docs/references" + "/x" * 400):
            with self.subTest(name=name):
                refused(self, document(entry(name)), "entry 0: file")

    def test_the_index_and_the_readme_are_not_references(self):
        for name in ("docs/references/index.json", "docs/references/README.md"):
            with self.subTest(name=name):
                message = refused(self, document(entry(name)), "entry 0: file")
                self.assertIn("not references", message)

    def test_a_name_that_differs_from_the_metadata_in_letter_case_is_a_reference(self):
        # The exemption is exact: such a file is a file of its own where letters are told apart,
        # so it is indexed like any other.
        for name in ("INDEX.JSON", "readme.md", "README.MD", "index.j\u017fon"):
            with self.subTest(name=name):
                doc = document(entry("docs/references/" + name))
                self.assertEqual(doc, refindex.parse(refindex.serialize(doc)))

    def test_an_area_that_only_folds_into_the_real_one_is_refused(self):
        for name in ("docs/REFERENCES/x.pdf", "Docs/references/x.pdf", "docs/referenceſ/x.pdf",
                     "docſ/references/x.pdf", "DOCS/REFERENCES/x.pdf"):
            with self.subTest(name=name):
                refused(self, document(entry(name)), "entry 0: file")

    def test_a_file_named_like_metadata_below_the_area_is_a_reference(self):
        doc = document(entry("docs/references/sub/index.json"))
        self.assertEqual(doc, refindex.parse(refindex.serialize(doc)))

    def test_a_hash_that_is_not_sixty_four_lowercase_hex_digits_is_refused(self):
        for value in ("", "a" * 63, "a" * 65, "A" * 64, "g" * 64, " " + "a" * 63, None, 5, ["a"],
                      "a" * 64 + "\n"):
            with self.subTest(value=value):
                refused(self, document(entry(sha256=value)), "entry 0: sha256")

    def test_a_field_of_the_wrong_type_is_refused(self):
        for field in ("title", "url", "license", "retrieved", "version", "notes", "file"):
            for value in (None, 5, True, ["x"], {"x": 1}):
                with self.subTest(field=field, value=value):
                    refused(self, document(entry(**{field: value})), "entry 0: " + field)

    def test_a_missing_or_extra_field_is_refused_and_the_extra_one_is_not_shown(self):
        short = entry()
        del short["notes"]
        refused(self, document(short), "entry 0: the fields")
        message = refused(self, document(entry(**{"\x1b[31mred": "x"})), "entry 0: the fields")
        self.assertNotIn("red", message)
        self.assertNotIn("\x1b", message)

    def test_an_entry_that_is_not_an_object_is_refused(self):
        for value in (None, "x", 5, [entry()], True):
            with self.subTest(value=value):
                refused(self, {"entries": [value], "format": 1}, "entry 0")

    def test_text_is_printable_and_bounded(self):
        for field, limit in refindex.LIMITS.items():
            with self.subTest(field=field):
                over = "https://e.com/" + "x" * limit if field == "url" else "x" * (limit + 1)
                refused(self, document(entry(**{field: over})), "entry 0: " + field)
                for bad in ("a\x1bb", "a\nb", "a\x00b", "a\x7fb", "a b", "a\x85b"):
                    if field == "url":
                        bad = "https://e.com/" + bad
                    refused(self, document(entry(**{field: bad})), "entry 0: " + field)

    def test_text_at_its_limit_is_accepted(self):
        doc = document(entry(title="t" * 300, license="l" * 128, version="v" * 128,
                             notes="n" * 2000, url="https://e.com/" + "u" * (2048 - 14)))
        self.assertEqual(doc, refindex.parse(refindex.serialize(doc)))

    def test_a_title_and_a_url_are_required_but_a_license_version_and_notes_are_not(self):
        refused(self, document(entry(title="")), "entry 0: title")
        refused(self, document(entry(url="")), "entry 0: url")
        doc = document(entry(license="", version="", notes=""))
        self.assertEqual(doc, refindex.parse(refindex.serialize(doc)))

    def test_a_url_is_an_http_or_https_address(self):
        for value in ("ftp://e.com/x", "file:///etc/passwd", "javascript:alert(1)", "e.com/x",
                      "https://", "https:///x", "https://e.com/a b", "HTTPS:e.com", "//e.com/x"):
            with self.subTest(value=value):
                refused(self, document(entry(url=value)), "entry 0: url")
        doc = document(entry(url="http://e.com/x?y=1#z"))
        self.assertEqual(doc, refindex.parse(refindex.serialize(doc)))

    def test_a_date_is_a_real_ascii_date(self):
        for value in ("", "2026-13-01", "2026-02-30", "26-10-21", "2026-1-21", "2026/10/21",
                      "2026-10-21T00:00", "٢٠٢٦-10-21", "2026-10-21\n"):
            with self.subTest(value=value):
                refused(self, document(entry(retrieved=value)), "entry 0: retrieved")

    def test_the_position_of_the_bad_entry_is_named(self):
        doc = document(entry("docs/references/a.pdf"), entry("docs/references/b.pdf"),
                       entry("docs/references/c.pdf", sha256="x"))
        refused(self, doc, "entry 2: sha256")

    def test_the_format_must_be_the_integer_one(self):
        for value in (0, 2, True, 1.0, "1", None):
            with self.subTest(value=value):
                refused(self, document(format=value), "format")

    def test_the_top_level_has_exactly_two_keys(self):
        doc = document()
        doc["extra"] = []
        refused(self, doc, "the index: the fields")
        refused(self, {"format": 1}, "the index: the fields")
        refused(self, {"entries": {}, "format": 1}, "entries")
        refused(self, [], "the index")


class Bounds(unittest.TestCase):
    def test_more_than_five_thousand_entries_are_refused(self):
        many = [entry("docs/references/f%05d.pdf" % n) for n in range(refindex.MAX_ENTRIES + 1)]
        refused(self, {"entries": many, "format": 1}, "more than 5000")

    def small(self, count):
        return [entry("docs/references/f%04d.pdf" % n, notes="", title="t", version="",
                      license="", url="https://e.com/x") for n in range(count)]

    def test_a_large_index_that_fits_the_bytes_is_read(self):
        doc = {"entries": self.small(3000), "format": 1}
        data = refindex.serialize(doc)
        self.assertLess(len(data), refindex.MAX_BYTES)
        self.assertEqual(doc, refindex.parse(data))

    def test_the_byte_bound_is_reached_before_the_entry_bound_for_the_smallest_entries(self):
        # An entry is at least about 230 bytes, so 5,000 of them are over a mebibyte. Both
        # bounds stand; the smaller one decides.
        with self.assertRaises(RefIndexError) as caught:
            refindex.serialize({"entries": self.small(refindex.MAX_ENTRIES), "format": 1})
        self.assertIn("larger than", str(caught.exception))

    def test_more_than_a_mebibyte_is_refused_before_it_is_parsed(self):
        with self.assertRaises(RefIndexError) as caught:
            refindex.parse(b" " * (refindex.MAX_BYTES + 1))
        self.assertIn("larger than", str(caught.exception))

    def test_an_index_whose_entries_exceed_the_byte_bound_is_refused(self):
        many = [entry("docs/references/f%04d.pdf" % n, notes="n" * 2000, title="t" * 300)
                for n in range(2000)]
        with self.assertRaises(RefIndexError) as caught:
            refindex.serialize({"entries": many, "format": 1})
        self.assertIn("larger than", str(caught.exception))

    def test_nesting_is_bounded(self):
        data = b'{"entries": ' + b"[" * 5000 + b"]" * 5000 + b', "format": 1}'
        with self.assertRaises(RefIndexError):
            refindex.parse(data)


class Parse(unittest.TestCase):
    def refuse(self, data, text=None):
        with self.assertRaises(RefIndexError) as caught:
            refindex.parse(data)
        if text:
            self.assertIn(text, str(caught.exception))

    def test_what_is_not_json_is_refused(self):
        for data in (b"", b"not json", b"[]", b"null", b'"x"', b"{", b"\xff\xfe{}",
                     b'{"entries": [], "format": 1} trailing', b"\xef\xbb\xbf{}"):
            with self.subTest(data=data):
                self.refuse(data)

    def test_a_non_bytes_value_is_refused(self):
        self.refuse("text", "not bytes")
        self.refuse(None, "not bytes")

    def test_a_duplicate_key_is_refused(self):
        self.refuse(b'{"entries": [], "format": 1, "format": 1}', "duplicate")
        good = refindex.serialize(document(entry("docs/references/a.pdf"))).decode()
        self.refuse(good.replace('"title"', '"url": "https://x.com/y", "title"', 1).encode(),
                    "duplicate")

    def test_nan_and_infinity_and_fractions_are_refused(self):
        for token in ("NaN", "Infinity", "-Infinity", "1.0", "1e2"):
            with self.subTest(token=token):
                self.refuse(('{"entries": [], "format": %s}' % token).encode())

    def test_a_non_canonical_layout_is_refused(self):
        data = refindex.serialize(document()).decode()
        self.refuse(data.replace("\n", "\r\n").encode(), "canonical")
        self.refuse(json.dumps(json.loads(data), indent=4).encode(), "canonical")
        self.refuse(data.rstrip("\n").encode(), "canonical")
        self.refuse(data.replace('"retrieved"', '"retrieved" ', 1).encode(), "canonical")
        self.refuse(raw(document()), "canonical")

    def test_a_hostile_character_is_refused_even_when_escaped(self):
        for text in ("\\u001b", "\\u0000", "\\u2028", "\\u0085", "\\ud800"):
            with self.subTest(text=text):
                good = refindex.serialize(document(entry("docs/references/a.pdf"))).decode()
                self.refuse(good.replace("Datasheet", "x" + text + "y").encode())

    def test_what_the_serializer_writes_is_ascii_even_for_unicode_text(self):
        doc = document(entry("docs/references/café.pdf", title="Café 中"))
        data = refindex.serialize(doc)
        data.decode("ascii")
        self.assertEqual(doc, refindex.parse(data))

    def test_a_refusal_never_repeats_a_hostile_value(self):
        for name in ("docs/references/\x1b[31mred\x1b[0m\n", "/\x1b]0;title\x07"):
            with self.assertRaises(RefIndexError) as caught:
                refindex.serialize(document(entry(name)))
            self.assertNotIn("\x1b", str(caught.exception))
            self.assertNotIn("red", str(caught.exception))
            self.assertNotIn("title", str(caught.exception))


if __name__ == "__main__":
    unittest.main()

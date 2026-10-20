import copy
import hashlib
import json
import unittest

from workbench import manifest
from workbench.manifest import ManifestError


def h(char):
    return char * 64


def document():
    return {
        "base": h("b"),
        "files": [
            {"class": "module-owned", "hash": h("3"), "path": ".workbench/.gitignore"},
            {"class": "seeded", "hash": h("1"), "path": "AGENTS.md"},
            {"block": "code/work", "class": "slot block", "hash": h("2"), "path": "AGENTS.md",
             "slot": "policy"},
        ],
        "packages": [{
            "commit": "a" * 40,
            "modules": [
                {"declaration": h("4"), "name": "alpha", "tree": h("5"), "version": "1.0"},
                {"declaration": h("6"), "name": "beta", "tree": h("7"), "version": "0.2"},
            ],
            "name": "pkg", "ref": "main", "source": "https://example.test/pkg", "tree": h("8"),
        }],
        "seed": "11111111-2222-4333-8444-555555555555",
        "version": 1,
        "workbench": "0.1.0",
    }


KNOWN = (
    '{\n'
    '  "base": "%s",\n'
    '  "files": [\n'
    '    {"class": "module-owned", "hash": "%s", "path": ".workbench/.gitignore"},\n'
    '    {"class": "seeded", "hash": "%s", "path": "AGENTS.md"},\n'
    '    {"block": "code/work", "class": "slot block", "hash": "%s", "path": "AGENTS.md", '
    '"slot": "policy"}\n'
    '  ],\n'
    '  "packages": [\n'
    '    {"commit": "%s", "modules": [{"declaration": "%s", "name": "alpha", "tree": "%s", '
    '"version": "1.0"}, {"declaration": "%s", "name": "beta", "tree": "%s", "version": "0.2"}], '
    '"name": "pkg", "ref": "main", "source": "https://example.test/pkg", "tree": "%s"}\n'
    '  ],\n'
    '  "seed": "11111111-2222-4333-8444-555555555555",\n'
    '  "version": 1,\n'
    '  "workbench": "0.1.0"\n'
    '}\n'
) % (h("b"), h("3"), h("1"), h("2"), "a" * 40, h("4"), h("5"), h("6"), h("7"), h("8"))

KNOWN_SHA256 = "10ec4a7f67d5a6c2d1830bdb64cebbf849329b37ed295fd4b29b5892132a1120"


class ManifestTest(unittest.TestCase):
    def test_known_answer_manifest_bytes(self):
        data = manifest.serialize(document())
        self.assertEqual(KNOWN.encode(), data)
        self.assertEqual(KNOWN_SHA256, hashlib.sha256(data).hexdigest())

    def test_one_entry_per_line(self):
        doc = document()
        doc["files"] += [{"class": "seeded", "hash": h("9"), "path": "docs/README.md"}]
        lines = manifest.serialize(doc).decode().split("\n")
        entries = [line for line in lines if line.startswith("    {")]
        self.assertEqual(4 + 1, len(entries))
        for line in entries:
            json.loads(line.rstrip(","))

    def test_empty_lists_are_written_on_one_line(self):
        doc = document()
        doc["files"], doc["packages"] = [], []
        text = manifest.serialize(doc).decode()
        self.assertIn('  "files": [],\n', text)
        self.assertIn('  "packages": [],\n', text)
        self.assertEqual(doc, manifest.parse(text.encode()))

    def test_serialize_refuses_unsorted_input(self):
        doc = document()
        doc["files"].reverse()
        with self.assertRaises(ManifestError):
            manifest.serialize(doc)
        doc = document()
        doc["packages"][0]["modules"].reverse()
        with self.assertRaises(ManifestError):
            manifest.serialize(doc)
        doc = document()
        doc["packages"].append(dict(doc["packages"][0], name="aaa"))
        with self.assertRaises(ManifestError):
            manifest.serialize(doc)

    def test_serialize_refuses_repeated_entries(self):
        doc = document()
        doc["files"].append(dict(doc["files"][-1]))
        with self.assertRaises(ManifestError):
            manifest.serialize(doc)

    def test_a_seeded_file_and_its_slot_blocks_share_a_path(self):
        manifest.serialize(document())

    def test_parse_round_trip(self):
        self.assertEqual(document(), manifest.parse(manifest.serialize(document())))

    def test_parse_refuses_noncanonical_bytes(self):
        data = manifest.serialize(document())
        for changed in (data.replace(b"\n", b"\r\n"), data.rstrip(b"\n"), data + b"\n",
                        data.replace(b"  ", b"\t", 1),
                        json.dumps(document(), sort_keys=True).encode() + b"\n",
                        data.replace(b'"seed": ', b'"seed":  ')):
            with self.assertRaises(ManifestError):
                manifest.parse(changed)

    def test_parse_refuses_duplicate_key_unknown_key_float_and_depth(self):
        data = manifest.serialize(document()).decode()
        bad = [
            data.replace('  "version": 1,', '  "version": 1,\n  "version": 1,'),
            data.replace('  "version": 1,', '  "extra": 1,\n  "version": 1,'),
            data.replace('"version": 1', '"version": 1.0'),
            data.replace('"version": 1', '"version": NaN'),
            data.replace('"version": 1', '"version": true'),
            data.replace('"version": 1', '"version": 2'),
            '[' * 100 + ']' * 100,
            "[]",
            "",
        ]
        for text in bad:
            with self.assertRaises(ManifestError, msg=text[:60]):
                manifest.parse(text.encode())
        with self.assertRaises(ManifestError):
            manifest.parse(b"\xff\xfe")
        with self.assertRaises(ManifestError):
            manifest.parse("text")

    def test_no_harness_or_timestamp_field_allowed(self):
        for key, value in (("harness", "claude"), ("time", "2026-01-01T00:00:00Z"),
                           ("created", 1), ("clone", "x")):
            doc = document()
            doc[key] = value
            with self.assertRaises(ManifestError, msg=key):
                manifest.serialize(doc)
            doc = document()
            doc["packages"][0][key] = value
            with self.assertRaises(ManifestError, msg=key):
                manifest.serialize(doc)
            doc = document()
            doc["files"][0][key] = value
            with self.assertRaises(ManifestError, msg=key):
                manifest.serialize(doc)

    def test_shape_refusals(self):
        def broken(change):
            doc = copy.deepcopy(document())
            change(doc)
            return doc

        cases = {
            "short hash": lambda d: d.update(base="abc"),
            "upper hash": lambda d: d.update(base="B" * 64),
            "bad seed": lambda d: d.update(seed="has space"),
            "bad version text": lambda d: d.update(workbench="a b"),
            "unknown class": lambda d: d["files"][1].update({"class": "weird"}),
            "block without slot class": lambda d: d["files"][1].update(slot="policy", block="a/b"),
            "slot block without block": lambda d: d["files"][2].pop("block"),
            "bad path": lambda d: d["files"][1].update(path="../x"),
            "git path": lambda d: d["files"][1].update(path=".git/config"),
            "bad block id": lambda d: d["files"][2].update(block="nocolon"),
            "bad package name": lambda d: d["packages"][0].update(name="Bad"),
            "bad commit": lambda d: d["packages"][0].update(commit="abc"),
            "control in source": lambda d: d["packages"][0].update(source="a\nb"),
            "bad module version": lambda d: d["packages"][0]["modules"][0].update(version="x"),
            "modules not a list": lambda d: d["packages"][0].update(modules={}),
            "files not a list": lambda d: d.update(files={}),
        }
        for name, change in cases.items():
            with self.assertRaises(ManifestError, msg=name):
                manifest.serialize(broken(change))

    def test_a_local_directory_package_has_no_commit(self):
        doc = document()
        doc["packages"][0].update(commit="", ref="")
        self.assertEqual(doc, manifest.parse(manifest.serialize(doc)))

    def test_non_ascii_is_escaped(self):
        doc = document()
        doc["files"].append({"class": "seeded", "hash": h("9"), "path": "docs/caf\u00e9.md"})
        data = manifest.serialize(doc)
        data.decode("ascii")
        self.assertIn(b"caf\\u00e9", data)
        self.assertEqual(doc, manifest.parse(data))

    def test_project_id_is_sha256_of_seed(self):
        seed = "11111111-2222-4333-8444-555555555555"
        self.assertEqual(hashlib.sha256(seed.encode()).hexdigest(), manifest.project_id(seed))
        self.assertEqual(64, len(manifest.project_id(seed)))
        with self.assertRaises(ManifestError):
            manifest.project_id("")
        with self.assertRaises(ManifestError):
            manifest.project_id(None)

    def test_project_id_is_accepted_by_the_store(self):
        from workbench import pins
        value = manifest.project_id(manifest.new_seed())
        self.assertEqual(value, pins.check_id(value))

    def test_two_seeds_give_different_ids(self):
        first, second = manifest.new_seed(), manifest.new_seed()
        self.assertNotEqual(first, second)
        self.assertNotEqual(manifest.project_id(first), manifest.project_id(second))

    def test_base_ignore(self):
        self.assertEqual(b"/local/\n", manifest.BASE_IGNORE)


if __name__ == "__main__":
    unittest.main()

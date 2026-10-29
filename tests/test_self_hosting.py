"""How this repository's hand-maintained files relate to what the installer would seed.

The installer cannot be run on this repository (a target must be new or empty), and a seeded file is the
owner's to change after install, so agreement is not equal bytes. This test installs the first-party modules
into a scratch directory with `preview`, which writes nothing, and requires every seeded path to have one
recorded disposition in `tests/fixtures/self_hosting_dispositions.json`: `identical`, `diverged` or `absent`.
It fails when the installer plans a seeded path or a slot block that has no record, or when a record no
longer holds. A change to a module's seeds therefore forces a decision about this repository."""

import hashlib
import io
import json
import os
import re
import tempfile
import unittest

from tests import support
from workbench import preview, sources, store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "tests", "fixtures", "self_hosting_dispositions.json")
SEEDED = re.compile(r"^  create-file (\S+) \[seeded\] - \d+ bytes sha256 ([0-9a-f]{64})(?: \(with blocks: (.*)\))?$")
DISPOSITIONS = ("identical", "diverged", "absent")
HOW = ("Record it in tests/fixtures/self_hosting_dispositions.json with a disposition "
       "(identical, diverged or absent) and, for diverged and absent, a reason.")


def load_records():
    with open(DATA, encoding="utf-8") as handle:
        return json.load(handle)


def installer_plan(modules):
    """The seeded paths the installer would write for `modules`: {path: (sha256, [block, ...])}."""
    with tempfile.TemporaryDirectory() as holder:
        holder = os.path.realpath(holder)
        guarded = store.Store(os.path.join(holder, "store"))
        guarded.ensure()
        out, err = io.StringIO(), io.StringIO()
        command = sources.Command(os.path.join(holder, "target"),
                                  [(os.path.join(ROOT, "packages", "workbench"), None)], list(modules))
        code = preview.run(guarded, command, out, err)
        if code != 0:
            raise AssertionError("the scratch preview was refused: " + err.getvalue())
    planned = {}
    for line in out.getvalue().splitlines():
        found = SEEDED.match(line)
        if found:
            blocks = [b.strip() for b in (found.group(3) or "").split(",") if b.strip()]
            planned[found.group(1)] = (found.group(2), blocks)
    return planned


def read(path):
    with open(os.path.join(ROOT, *path.split("/")), "rb") as handle:
        return handle.read()


def exists(path):
    return os.path.lexists(os.path.join(ROOT, *path.split("/")))


def problems_of(planned, records):
    """Every problem found, as lines; an empty list means the records match the plan and this repository."""
    problems = []
    by_path = {}
    for record in records:
        if record["path"] in by_path:
            problems.append("%s has more than one record. %s" % (record["path"], HOW))
        by_path[record["path"]] = record
    for path in sorted(planned):
        if path not in by_path:
            problems.append("the installer seeds %s and no disposition is recorded. %s" % (path, HOW))
    for path in sorted(by_path):
        record = by_path[path]
        if path not in planned:
            problems.append("%s is recorded but the installer no longer seeds it; remove the record" % path)
            continue
        disposition = record.get("disposition")
        if disposition not in DISPOSITIONS:
            problems.append("%s has the disposition %r; use one of %s" % (path, disposition, DISPOSITIONS))
            continue
        if disposition != "identical" and not record.get("reason"):
            problems.append("%s is %s and has no reason" % (path, disposition))
        seed_hash, blocks = planned[path]
        if sorted(record.get("blocks", [])) != sorted(blocks):
            problems.append("%s: the installer fills the slots %s and the record lists %s. %s"
                            % (path, sorted(blocks), sorted(record.get("blocks", [])), HOW))
        if disposition == "absent":
            if exists(path):
                problems.append("%s is recorded absent but exists here; record it diverged or identical" % path)
            continue
        if not exists(path):
            problems.append("%s is recorded %s but does not exist here" % (path, disposition))
            continue
        same = hashlib.sha256(read(path)).hexdigest() == seed_hash
        if disposition == "identical" and not same:
            problems.append("%s is recorded identical but differs from the seed; record it diverged" % path)
        if disposition == "diverged" and same:
            problems.append("%s is recorded diverged but now equals the seed; record it identical" % path)
    return problems


class Relation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        records = load_records()
        cls.modules = records["modules"]
        cls.records = records["seeded"]

    def setUp(self):
        support.forbid_real_store(self)
        support.require_release(self)

    def test_every_seeded_path_has_one_disposition_that_holds(self):
        planned = installer_plan(self.modules)
        self.assertTrue(planned, "the installer planned no seeded path")
        self.assertEqual([], problems_of(planned, self.records))

    def test_a_missing_record_an_invented_path_and_a_wrong_disposition_are_each_caught(self):
        planned = installer_plan(self.modules)
        records = list(self.records)
        removed = problems_of(planned, records[1:])
        self.assertTrue(any("no disposition is recorded" in line for line in removed), removed)
        invented = problems_of(planned, records + [{"path": "docs/invented/README.md",
                                                    "disposition": "absent", "reason": "x"}])
        self.assertTrue(any("no longer seeds it" in line for line in invented), invented)
        wrong = [dict(r, disposition="identical") if r["disposition"] == "diverged" else r for r in records]
        self.assertTrue(any("recorded identical but differs" in line for line in problems_of(planned, wrong)))
        absent = [dict(r, disposition="absent") if r["disposition"] == "diverged" else r for r in records]
        self.assertTrue(any("recorded absent but exists" in line for line in problems_of(planned, absent)))
        planned_new = dict(planned)
        planned_new["docs/new/README.md"] = ("0" * 64, [])
        self.assertTrue(any("docs/new/README.md" in line for line in problems_of(planned_new, records)))
        slots = [dict(r, blocks=[]) if r.get("blocks") else r for r in records]
        self.assertTrue(any("fills the slots" in line for line in problems_of(planned, slots)))

    def test_a_seed_equal_file_must_be_recorded_identical(self):
        planned = installer_plan(self.modules)
        diverged = sorted(r["path"] for r in self.records if r["disposition"] == "diverged")
        self.assertTrue(diverged, "no seeded path is recorded diverged")
        path = diverged[0]
        _, blocks = planned[path]
        stand_in = dict(planned)
        stand_in[path] = (hashlib.sha256(read(path)).hexdigest(), blocks)
        records = [dict(r) for r in self.records]
        self.assertTrue(any("now equals the seed" in line for line in problems_of(stand_in, records)))
        for record in records:
            if record["path"] == path:
                record["disposition"] = "identical"
        self.assertEqual([], [line for line in problems_of(stand_in, records) if path in line])


if __name__ == "__main__":
    unittest.main()

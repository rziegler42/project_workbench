import hashlib
import io
import os
import subprocess
import unittest
import unittest.mock

from tests.test_doccheck import Base, installed_document
from workbench import cli, gitindex, manifest, refcheck, refindex

PDF = b"%PDF-1.4 datasheet\n"
PNG = b"\x89PNG image bytes\n"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entry(name, data, **changes):
    value = {"file": "docs/references/" + name, "license": "CC-BY-4.0", "notes": "n",
             "retrieved": "2026-10-21", "sha256": sha(data), "title": "Title " + name,
             "url": "https://example.com/" + name, "version": "1"}
    value.update(changes)
    return value


def index_bytes(*entries):
    return refindex.serialize({"entries": sorted(entries, key=lambda e: e["file"]), "format": 1})


def tracked_of(*paths, links=()):
    return gitindex.Tracked(frozenset(paths) | frozenset(links), frozenset(), frozenset(links))


class Setup(Base):
    """A project with the module, some reference files on disk, and a tracked set made by hand."""

    def setUp(self):
        super().setUp()
        self.install()

    def reference(self, name, data):
        self.put("docs/references/" + name, data)

    def index(self, *entries):
        self.put(refindex.PATH, index_bytes(*entries))

    def run_check(self, *paths, links=()):
        tracked = tracked_of(refindex.PATH, *("docs/references/" + p for p in paths), links=links)
        problems, warnings = refcheck.examine(self.writer(), tracked)
        return problems, warnings

    def good(self):
        self.reference("a.pdf", PDF)
        self.reference("b.png", PNG)
        self.index(entry("a.pdf", PDF), entry("b.png", PNG))


class Presence(Setup):
    def test_a_project_without_the_module_gets_no_report(self):
        self.put(".workbench/manifest.json",
                 manifest.serialize(installed_document(module="other")))
        self.put(refindex.PATH, b"not json")
        self.assertEqual(([], []), refcheck.examine(self.writer(), tracked_of(refindex.PATH)))

    def test_the_module_with_no_references_gives_no_problem(self):
        self.assertEqual(([], []), refcheck.examine(self.writer(), tracked_of()))

    def test_the_readme_alone_is_not_a_reference(self):
        self.put("docs/references/README.md", "# References\n")
        tracked = tracked_of("docs/references/README.md")
        self.assertEqual(([], []), refcheck.examine(self.writer(), tracked))

    def test_an_empty_index_with_no_references_is_clean(self):
        self.index()
        self.assertEqual(([], []), self.run_check())

    def test_a_good_index_is_clean(self):
        self.good()
        self.assertEqual(([], []), self.run_check("a.pdf", "b.png"))

    def test_the_index_and_readme_need_no_entry_and_a_nested_index_does(self):
        self.good()
        self.put("docs/references/README.md", "# R\n")
        self.reference("sub/index.json", b"{}")
        problems, _ = self.run_check("a.pdf", "b.png", "README.md", "sub/index.json")
        self.assertEqual(1, len(problems), problems)
        self.assertIn("docs/references/sub/index.json: git tracks it, but the index has no entry",
                      problems[0])

    def test_the_names_are_matched_without_case_for_the_area_and_the_metadata(self):
        self.good()
        tracked = tracked_of("DOCS/References/Index.JSON", "docs/references/README.MD",
                             refindex.PATH, "docs/references/a.pdf", "docs/references/b.png")
        self.assertEqual(([], []), refcheck.examine(self.writer(), tracked))


class Lies(Setup):
    def test_an_entry_for_a_file_git_does_not_track_is_a_problem(self):
        self.good()
        problems, _ = self.run_check("a.pdf")
        self.assertEqual(["docs/references/b.png: the index has an entry for it, but git does "
                          "not track it"], problems)

    def test_an_entry_for_a_file_that_is_missing_is_a_problem(self):
        self.good()
        os.unlink(os.path.join(self.root, "docs", "references", "b.png"))
        problems, _ = self.run_check("a.pdf", "b.png")
        self.assertEqual(["docs/references/b.png: is missing"], problems)

    def test_a_hash_that_differs_is_a_problem(self):
        self.good()
        self.reference("a.pdf", PDF + b"changed")
        problems, _ = self.run_check("a.pdf", "b.png")
        self.assertEqual(["docs/references/a.pdf: its content differs from the hash in the index"],
                         problems)

    def test_a_tracked_file_with_no_entry_is_a_problem(self):
        self.good()
        self.reference("c.txt", b"x")
        problems, _ = self.run_check("a.pdf", "b.png", "c.txt")
        self.assertEqual(["docs/references/c.txt: git tracks it, but the index has no entry for "
                          "it"], problems)

    def test_a_file_replaced_by_a_link_is_a_problem_and_the_target_is_not_read(self):
        self.good()
        secret = os.path.join(self.outside, "target.pdf")
        with open(secret, "wb") as handle:
            handle.write(PDF)  # the same bytes: following the link would hide the swap
        os.unlink(os.path.join(self.root, "docs", "references", "a.pdf"))
        os.symlink(secret, os.path.join(self.root, "docs", "references", "a.pdf"))
        problems, _ = self.run_check("a.pdf", "b.png")
        self.assertEqual(["docs/references/a.pdf: is a link or not a regular file, so it was "
                          "not read"], problems)

    def test_a_link_that_git_tracks_in_place_of_a_file_is_a_problem(self):
        self.good()
        problems, _ = self.run_check("b.png", links=("docs/references/a.pdf",))
        self.assertEqual(["docs/references/a.pdf: git tracks a link in place of the file"],
                         problems)

    def test_a_link_at_the_folder_is_not_followed(self):
        self.reference("x", b"")
        os.unlink(os.path.join(self.root, "docs", "references", "x"))
        os.rmdir(os.path.join(self.root, "docs", "references"))
        os.makedirs(os.path.join(self.outside, "refs"))
        with open(os.path.join(self.outside, "refs", "a.pdf"), "wb") as handle:
            handle.write(PDF)
        with open(os.path.join(self.outside, "refs", "index.json"), "wb") as handle:
            handle.write(index_bytes(entry("a.pdf", PDF)))
        os.symlink(os.path.join(self.outside, "refs"), os.path.join(self.root, "docs", "references"))
        problems, _ = self.run_check("a.pdf")
        self.assertEqual(2, len(problems), problems)
        self.assertIn("index.json: cannot be read", problems[0])
        self.assertIn("was not compared with an index", problems[1])

    def test_a_directory_in_place_of_a_file_is_a_problem(self):
        self.good()
        os.unlink(os.path.join(self.root, "docs", "references", "b.png"))
        os.makedirs(os.path.join(self.root, "docs", "references", "b.png"))
        problems, _ = self.run_check("a.pdf", "b.png")
        self.assertEqual(1, len(problems), problems)
        self.assertIn("docs/references/b.png", problems[0])

    def test_the_index_missing_while_files_are_tracked_is_a_problem(self):
        self.reference("a.pdf", PDF)
        problems, _ = self.run_check("a.pdf")
        self.assertEqual(1, len(problems))
        self.assertIn("there is no index, but git tracks 1 reference file", problems[0])

    def test_an_index_git_does_not_track_is_a_problem(self):
        self.good()
        tracked = tracked_of("docs/references/a.pdf", "docs/references/b.png")
        problems, _ = refcheck.examine(self.writer(), tracked)
        self.assertEqual(2, len(problems), problems)
        self.assertIn("git does not track it", problems[0])
        self.assertIn("2 tracked reference files were not compared", problems[1])

    def test_an_index_that_is_a_link_is_not_followed(self):
        self.good()
        outside = os.path.join(self.outside, "index.json")
        with open(outside, "wb") as handle:
            handle.write(index_bytes())
        os.unlink(os.path.join(self.root, *refindex.PATH.split("/")))
        os.symlink(outside, os.path.join(self.root, *refindex.PATH.split("/")))
        problems, _ = self.run_check("a.pdf", "b.png")
        self.assertIn("cannot be read", problems[0])

    def test_a_note_or_title_naming_the_untracked_area_is_a_problem(self):
        for field in ("notes", "title"):
            with self.subTest(field=field):
                self.reference("a.pdf", PDF)
                self.index(entry("a.pdf", PDF, **{field: "see .Workbench/Local/refs/x.pdf"}))
                problems, _ = self.run_check("a.pdf")
                self.assertEqual(1, len(problems), problems)
                self.assertIn("its %s names a path into .workbench/local" % field, problems[0])

    def test_many_files_without_an_entry_are_listed_up_to_a_bound(self):
        self.index()
        names = ["f%03d.txt" % n for n in range(refcheck.MAX_LISTED + 7)]
        for name in names:
            self.reference(name, b"x")
        problems, _ = self.run_check(*names)
        self.assertEqual(refcheck.MAX_LISTED + 1, len(problems))
        self.assertEqual("7 more tracked reference files have no entry in the index", problems[-1])

    def test_a_tracked_name_with_an_escape_is_shown_escaped(self):
        self.index()
        name = "\x1b[31mred\x1b[0m.txt"
        self.reference(name, b"x")
        problems, _ = self.run_check(name)
        self.assertEqual(1, len(problems))
        self.assertNotIn("\x1b", problems[0])
        self.assertIn("\\x1b", problems[0])


class Hostile(Setup):
    def refuse(self, data):
        self.reference("a.pdf", PDF)
        self.put(refindex.PATH, data)
        problems, warnings = self.run_check("a.pdf")
        self.assertEqual([], warnings)
        self.assertEqual(2, len(problems), problems)
        self.assertTrue(problems[0].startswith("%s: " % refindex.PATH), problems)
        self.assertIn("1 tracked reference file was not compared", problems[1])
        for line in problems:
            self.assertNotIn("\x1b", line)
        return problems[0]

    def test_an_index_that_is_not_json_or_not_canonical_is_a_problem(self):
        for data in (b"not json", b"", b"[]", b'{"entries": [], "format": 1}',
                     b'{"entries": [], "format": 1, "format": 1}', b'{"entries": NaN}'):
            with self.subTest(data=data):
                self.refuse(data)

    def test_every_hostile_entry_file_is_refused_and_named(self):
        for name in ("/etc/passwd", "docs/references/../../x", ".git/config",
                     "docs/references/.git/x", "docs/other/a.pdf",
                     "docs/references/index.json", "docs/references/README.md",
                     "docs/references/\x1b[31m"):
            with self.subTest(name=name):
                good = index_bytes(entry("a.pdf", PDF)).decode()
                data = good.replace("docs/references/a.pdf", name.replace("\x1b", "\\u001b"))
                self.assertIn("entry 0: file", self.refuse(data.encode()))

    def test_a_bad_hash_and_a_wrong_type_are_refused(self):
        good = index_bytes(entry("a.pdf", PDF)).decode()
        self.assertIn("entry 0: sha256", self.refuse(good.replace(sha(PDF), "z" * 64).encode()))
        self.assertIn("entry 0: sha256", self.refuse(good.replace('"' + sha(PDF) + '"', "5").encode()))

    def test_a_huge_index_is_refused_before_it_is_parsed(self):
        self.assertIn("larger than", self.refuse(b" " * (refindex.MAX_BYTES + 1)))

    def test_an_entry_list_over_the_bound_is_refused(self):
        many = ",\n".join('    {"file": "docs/references/f%d"}' % n
                          for n in range(refindex.MAX_ENTRIES + 1))
        data = ('{\n  "entries": [\n%s\n  ],\n  "format": 1\n}\n' % many).encode()
        self.assertIn("more than", self.refuse(data))


class Limits(Setup):
    def test_a_file_over_the_size_limit_is_a_warning_and_not_a_problem(self):
        self.good()
        with unittest.mock.patch.object(refcheck, "FILE_WARN", 5):
            problems, warnings = self.run_check("a.pdf", "b.png")
        self.assertEqual([], problems)
        self.assertEqual(2, len(warnings), warnings)
        self.assertIn("over the 5", warnings[0])

    def test_the_folder_over_its_limit_is_a_warning(self):
        self.good()
        with unittest.mock.patch.object(refcheck, "FOLDER_WARN", 10):
            problems, warnings = self.run_check("a.pdf", "b.png")
        self.assertEqual([], problems)
        self.assertEqual(1, len(warnings), warnings)
        self.assertIn("the indexed references total", warnings[0])

    def test_an_entry_with_no_license_is_a_warning(self):
        self.reference("a.pdf", PDF)
        self.index(entry("a.pdf", PDF, license=""))
        problems, warnings = self.run_check("a.pdf")
        self.assertEqual([], problems)
        self.assertEqual(["docs/references/a.pdf: no license is recorded"], warnings)

    def test_reading_stops_at_the_byte_bound_and_says_so(self):
        self.good()
        with unittest.mock.patch.object(refcheck, "MAX_READ", len(PDF)):
            problems, _ = self.run_check("a.pdf", "b.png")
        self.assertEqual(1, len(problems), problems)
        self.assertIn("the rest were not looked at", problems[0])

    def test_a_file_too_large_to_read_is_a_problem_and_not_a_crash(self):
        big = b"x" * 5000
        self.reference("a.pdf", big)
        self.index(entry("a.pdf", big))
        with unittest.mock.patch("workbench.projectfs.safefs.MAX_FILE_BYTES", 3000):
            problems, _ = self.run_check("a.pdf")
        self.assertEqual(1, len(problems), problems)
        self.assertIn("a.pdf: cannot be read", problems[0])

    def test_nothing_is_written_or_changed(self):
        self.good()
        before = {}
        for name in ("a.pdf", "b.png", "index.json"):
            with open(os.path.join(self.root, "docs", "references", name), "rb") as handle:
                before[name] = handle.read()
        stamp = os.stat(os.path.join(self.root, refindex.PATH)).st_mtime_ns
        self.run_check("a.pdf", "b.png")
        for name, data in before.items():
            with open(os.path.join(self.root, "docs", "references", name), "rb") as handle:
                self.assertEqual(data, handle.read())
        self.assertEqual(stamp, os.stat(os.path.join(self.root, refindex.PATH)).st_mtime_ns)


class Command(Setup):
    """`wb check` end to end in a real git repository, with no harness attached."""

    def setUp(self):
        super().setUp()
        os.chmod(self.store, 0o700)
        self.git("init", "-q", "--template=")

    def git(self, *args):
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.test",
                               "-c", "commit.gpgsign=false"] + list(args), cwd=self.root, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(0, done.returncode, done.stderr)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "x")

    def check(self):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["check", self.root], out, err, store_root=self.store,
                        home=os.path.join(self.base, "nohome"))
        return code, out.getvalue(), err.getvalue()

    def test_a_clean_project_has_no_problems_and_the_git_index_is_untouched(self):
        self.good()
        self.commit()
        path = os.path.join(self.root, ".git", "index")
        with open(path, "rb") as handle:
            before = handle.read()
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)
        self.assertTrue(out.endswith("check found no problems\n"), out)
        with open(path, "rb") as handle:
            self.assertEqual(before, handle.read())

    def test_a_changed_file_an_untracked_entry_and_a_missing_entry_are_problems(self):
        self.good()
        self.reference("c.txt", b"x")
        self.commit()
        self.reference("a.pdf", PDF + b"x")
        self.git("rm", "-q", "--cached", "docs/references/b.png")
        code, out, err = self.check()
        self.assertEqual(1, code)
        lines = [line for line in err.splitlines() if line.startswith("problem: ")]
        self.assertEqual(3, len(lines), err)
        self.assertTrue(any("a.pdf: its content differs" in line for line in lines))
        self.assertTrue(any("b.png: the index has an entry for it, but git does not" in line
                            for line in lines))
        self.assertTrue(any("c.txt: git tracks it, but the index has no entry" in line
                            for line in lines))

    def test_a_tracked_document_with_a_path_into_the_untracked_area_is_a_problem(self):
        self.good()
        self.put("docs/specs/power.md",
                 "# P\n\nStatus: Current\n\nSee [the sheet](../../.workbench/local/refs/x.pdf).\n")
        self.commit()
        code, out, err = self.check()
        self.assertEqual(1, code)
        self.assertIn("problem: docs/specs/power.md: points to .workbench/local/refs/x.pdf, "
                      "which git does not track", err)

    def test_a_project_without_the_module_is_not_reported(self):
        self.put(".workbench/manifest.json",
                 manifest.serialize(installed_document(module="other")))
        self.reference("a.pdf", PDF)
        self.put(refindex.PATH, b"not json")
        self.commit()
        code, out, err = self.check()
        self.assertEqual((0, ""), (code, err), err)

    def test_no_program_the_repository_names_is_run(self):
        self.good()
        self.commit()
        marker = os.path.join(self.outside, "ran")
        program = os.path.join(self.outside, "hook.sh")
        with open(program, "w") as handle:
            handle.write("#!/bin/sh\necho ran >> %s\n" % marker)
        os.chmod(program, 0o755)
        with open(os.path.join(self.root, ".git", "config"), "a") as handle:
            handle.write("[core]\n\tfsmonitor = %s\n\thooksPath = %s\n" % (program, self.outside))
        code, out, err = self.check()
        self.assertEqual(0, code, err)
        self.assertFalse(os.path.exists(marker))


if __name__ == "__main__":
    unittest.main()

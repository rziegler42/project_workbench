"""The groundwork decision helper: ``preview`` and ``accept`` of a decision record.

Plan ``2026-10-29-accept-decision-at-ask``, Increment E (``docs/specs/command-permissions.md``, "Accepting a decision through
a command"). The helper is one file over the kit, loaded here by its path and run in process on a synthetic project with a
fixed git identity and a fixed date. How the launcher starts it, reads its result line and logs the run is tested with a
synthetic module in ``tests/test_checkpoint_command*.py``; the declaration is checked below."""

import datetime
import hashlib
import io
import json
import os
import re
import unittest
import unittest.mock

from tests import support_docs, support_helpers
from workbench.wbkit import identity, safefs

groundwork = support_helpers.load("groundwork")
doccheck = support_helpers.load("doccheck")

RECORD = "docs/decisions/2026-10-29-use-spi-flash.md"
PROPOSED = "# Use SPI flash\n\nStatus: Proposed\nDate: 2026-10-29\n\n## Context\n\nText.\n"
WHO = identity.check("Example Approver", "12345+example@users.noreply.github.com")
TODAY = datetime.date(2026, 10, 30)
ACCEPTED_LINE = "Status: Accepted by Example Approver <12345+example@users.noreply.github.com> on 2026-10-30"
DIGEST = re.compile(r"digest: ([0-9a-f]{32})\n\Z")
WRONG = "0" * 32


def sha(data):
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


class Base(support_docs.Base):
    SEED = "seed-one"

    def setUp(self):
        super().setUp()
        os.mkdir(os.path.join(self.root, ".git"))
        os.mkdir(os.path.join(self.root, ".workbench"))
        self.seed(self.SEED)
        self.put(RECORD, PROPOSED)
        for target, name, value in ((groundwork.identity, "read", lambda home=None: WHO),
                                    (groundwork, "today", lambda: TODAY)):
            patcher = unittest.mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.clear_hook)

    @staticmethod
    def clear_hook():
        safefs._hook = None

    def seed(self, seed):
        self.put(".workbench/manifest.json", json.dumps({"seed": seed}))

    def call(self, *argv, terminal=False, stdin="", cwd=None):
        out, err = io.StringIO(), io.StringIO()
        code = groundwork.main(list(argv), io.StringIO(stdin), out, err, cwd or self.root, terminal)
        return code, out.getvalue(), err.getvalue()

    def content(self, rel=RECORD):
        with open(os.path.join(self.root, *rel.split("/")), "rb") as handle:
            return handle.read()

    def tree(self):
        found = {}
        for base, dirs, files in os.walk(self.root):
            for name in files:
                full = os.path.join(base, name)
                if os.path.islink(full):
                    found[os.path.relpath(full, self.root)] = b"->"
                    continue
                with open(full, "rb") as handle:
                    found[os.path.relpath(full, self.root)] = handle.read()
        return found

    def digest(self, rel=RECORD):
        code, out, err = self.call("preview", rel)
        self.assertEqual((0, ""), (code, err), out)
        found = DIGEST.search(out)
        self.assertIsNotNone(found, out)
        return found.group(1)

    def last_line(self, out):
        return json.loads(out.rstrip("\n").split("\n")[-1])

    def expected(self, text=PROPOSED):
        return text.replace("Status: Proposed", ACCEPTED_LINE, 1).encode("utf-8")

    def refused(self, *argv, needle=None, **kwargs):
        before = self.tree()
        code, out, err = self.call(*argv, **kwargs)
        self.assertEqual(1, code, (out, err))
        self.assertTrue(err.startswith("refused: "), err)
        if needle:
            self.assertIn(needle, err)
        self.assertEqual(before, self.tree())
        return err


class Preview(Base):
    def test_it_prints_what_the_digest_binds_and_a_digest_and_writes_nothing(self):
        before = self.tree()
        code, out, err = self.call("preview", RECORD)
        self.assertEqual((0, ""), (code, err))
        lines = out.rstrip("\n").split("\n")
        self.assertRegex(lines[-1], r"\Adigest: [0-9a-f]{32}\Z")
        text = "\n".join(lines[:-1])
        for needle in ("groundwork accept", "project: " + sha(self.SEED), "record: " + RECORD,
                       "status line: Status: Proposed", "sha256: " + sha(PROPOSED),
                       "that you read the record", "the index row"):
            self.assertIn(needle, text)
        self.assertEqual(before, self.tree())

    def test_the_digest_is_the_first_32_characters_of_the_sha256_of_the_text(self):
        code, out, err = self.call("preview", RECORD)
        lines = out.rstrip("\n").split("\n")
        self.assertEqual(sha("\n".join(lines[:-1]))[:32], lines[-1].split(": ")[1])

    def test_it_is_the_same_on_a_second_run(self):
        self.assertEqual(self.digest(), self.digest())

    def test_another_project_another_record_another_content_and_another_status_line_are_another_digest(self):
        first = self.digest()
        self.put("docs/decisions/2026-10-29-other.md", PROPOSED)
        other_record = self.digest("docs/decisions/2026-10-29-other.md")
        self.put(RECORD, PROPOSED + "More.\n")
        other_content = self.digest()
        self.put(RECORD, PROPOSED.replace("Status: Proposed", "Status: Proposed. Drafted by Ann"))
        other_status = self.digest()
        self.put(RECORD, PROPOSED)
        self.seed("seed-two")
        other_project = self.digest()
        digests = [first, other_record, other_content, other_status, other_project]
        self.assertEqual(len(digests), len(set(digests)), digests)

    def test_two_records_whose_paths_share_their_first_200_characters_are_two_digests(self):
        long = "docs/decisions/" + "x" * 200
        first, second = long + "A.md", long + "B.md"
        self.put(first, PROPOSED)
        self.put(second, PROPOSED)
        self.assertNotEqual(self.digest(first), self.digest(second))
        self.refused("accept", second, "--digest", self.digest(first), needle="digest")

    def test_it_needs_no_identity(self):
        with unittest.mock.patch.object(groundwork.identity, "read", side_effect=identity.IdentityError("none")):
            self.assertEqual(0, self.call("preview", RECORD)[0])

    def test_it_previews_an_accepted_record_too(self):
        self.put(RECORD, PROPOSED.replace("Proposed", "Accepted"))
        self.assertEqual(0, self.call("preview", RECORD)[0])

    def test_it_refuses_what_accept_would_refuse_and_writes_nothing(self):
        self.put("docs/specs/x.md", PROPOSED)
        self.put("docs/decisions/sub/x.md", PROPOSED)
        for rel in ("docs/specs/x.md", "docs/decisions/sub/x.md", "docs/decisions/absent.md", "../x.md", "/abs.md",
                    "docs/decisions/x.txt", "docs/decisions/.md", ".git/config"):
            with self.subTest(rel=rel):
                self.refused("preview", rel)


class AcceptAtAsk(Base):
    def test_the_digest_of_the_preview_replaces_the_status_line_and_nothing_else(self):
        digest = self.digest()
        code, out, err = self.call("accept", RECORD, "--digest", digest)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(self.expected(), self.content())
        self.assertEqual({"format": 1, "record": RECORD, "sha256": sha(PROPOSED), "approver": WHO.text, "via": "ask"},
                         self.last_line(out))
        self.assertLessEqual(len(out.rstrip("\n").split("\n")[-1].encode()), groundwork.MAX_RESULT)
        self.assertEqual([RECORD.split("/")[-1]], os.listdir(os.path.join(self.root, "docs", "decisions")))

    def test_a_wrong_digest_a_digest_of_another_record_and_a_stale_digest_are_refused(self):
        self.put("docs/decisions/2026-10-29-other.md", PROPOSED + "x\n")
        other = self.digest("docs/decisions/2026-10-29-other.md")
        stale = self.digest()
        self.put(RECORD, PROPOSED + "edited after the preview\n")
        for digest in (WRONG, other, stale):
            with self.subTest(digest=digest):
                self.refused("accept", RECORD, "--digest", digest, needle="digest")

    def test_a_malformed_digest_is_a_usage_error(self):
        before = self.tree()
        for digest in ("", "abc", self.digest().upper(), self.digest() + "0", "g" * 32):
            with self.subTest(digest=digest):
                code, out, err = self.call("accept", RECORD, "--digest", digest)
                self.assertEqual(2, code, err)
        self.assertEqual(before, self.tree())

    def test_a_second_run_changes_nothing_and_reports_the_record_as_accepted(self):
        old = self.digest()
        self.assertEqual(0, self.call("accept", RECORD, "--digest", old)[0])
        done = self.content()
        self.refused("accept", RECORD, "--digest", old, needle="digest")
        new = self.digest()
        code, out, err = self.call("accept", RECORD, "--digest", new)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(done, self.content())
        self.assertIn("already accepted", out)
        self.assertEqual("ask", self.last_line(out)["via"])
        self.assertEqual(sha(done), self.last_line(out)["sha256"])

    def test_an_accepted_record_with_a_wrong_digest_is_refused_not_reported(self):
        self.put(RECORD, PROPOSED.replace("Proposed", "Accepted"))
        self.refused("accept", RECORD, "--digest", WRONG, needle="digest")


class AcceptAtNone(Base):
    def test_a_run_with_no_digest_and_no_terminal_is_recorded_with_the_route_none(self):
        code, out, err = self.call("accept", RECORD)
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(self.expected(), self.content())
        self.assertEqual({"format": 1, "record": RECORD, "sha256": sha(PROPOSED), "approver": WHO.text, "via": "none"},
                         self.last_line(out))

    def test_an_accepted_record_is_reported_and_not_changed(self):
        self.put(RECORD, PROPOSED.replace("Proposed", "Accepted"))
        before = self.tree()
        code, out, err = self.call("accept", RECORD)
        self.assertEqual((0, ""), (code, err))
        self.assertEqual(before, self.tree())
        self.assertEqual("none", self.last_line(out)["via"])


class AcceptAtATerminal(Base):
    def test_the_owner_types_the_first_twelve_characters_of_the_hash(self):
        code, out, err = self.call("accept", RECORD, terminal=True, stdin=sha(PROPOSED)[:12] + "\n")
        self.assertEqual((0, ""), (code, err), out)
        self.assertEqual(self.expected(), self.content())
        self.assertIn("sha256: " + sha(PROPOSED), out)
        self.assertNotIn("{", out)  # no result line: a terminal run reads no level and writes no entry

    def test_what_is_typed_must_match_and_nothing_else_is_accepted(self):
        for typed in ("", "\n", "0" * 12 + "\n", sha(PROPOSED)[:11] + "\n", "yes\n", sha(PROPOSED).upper()[:12] + "\n"):
            with self.subTest(typed=typed):
                self.refused("accept", RECORD, terminal=True, stdin=typed)

    def test_a_digest_given_at_a_terminal_is_checked_and_needs_no_typing(self):
        code, out, err = self.call("accept", RECORD, "--digest", self.digest(), terminal=True)
        self.assertEqual((0, ""), (code, err), out)
        self.assertNotIn("Type the first", out)
        self.assertNotIn("{", out)  # a terminal run reads no level, so it prints no result line
        self.assertEqual(self.expected(), self.content())

    def test_an_accepted_record_at_a_terminal_prints_no_result_line(self):
        self.put(RECORD, PROPOSED.replace("Proposed", "Accepted"))
        code, out, err = self.call("accept", RECORD, terminal=True, stdin=sha(PROPOSED.replace("Proposed", "Accepted"))[:12])
        self.assertEqual((0, ""), (code, err), out)
        self.assertIn("already accepted", out)
        self.assertNotIn("{", out)

    def test_a_wrong_digest_at_a_terminal_is_refused_even_if_the_hash_is_typed(self):
        self.refused("accept", RECORD, "--digest", WRONG, terminal=True, stdin=sha(PROPOSED)[:12] + "\n")


class Refusals(Base):
    def test_a_status_that_is_not_proposed_is_refused(self):
        for status in ("Rejected", "Superseded", "Draft", "proposed", ""):
            with self.subTest(status=status):
                self.put(RECORD, PROPOSED.replace("Proposed", status))
                self.refused("accept", RECORD, needle="not Proposed")

    def test_a_missing_or_repeated_status_line_is_refused(self):
        documents = {
            "none": "# T\n\nNo status.\n",
            "two": "# T\n\nStatus: Proposed\nStatus: Proposed\n",
            "in a fence": "# T\n\n```\nStatus: Proposed\n```\n",
            "quoted": "# T\n\n> Status: Proposed\n",
            "after a heading": "# T\n\n## Context\n\nStatus: Proposed\n",
            "indented four spaces": "# T\n\n    Status: Proposed\n",
            "past the header": "# T\n" + "x\n" * 45 + "Status: Proposed\n",
        }
        for name, text in documents.items():
            with self.subTest(name=name):
                self.put(RECORD, text)
                self.refused("accept", RECORD, needle="status line")
                self.assertEqual(1, self.call("preview", RECORD)[0])

    def test_a_path_that_is_not_a_record_under_docs_decisions_is_refused(self):
        self.put("docs/specs/x.md", PROPOSED)
        self.put("docs/decisions/sub/x.md", PROPOSED)
        self.put("docs/decisions/x.txt", PROPOSED)
        for rel in ("docs/specs/x.md", "docs/decisions/sub/x.md", "docs/decisions/x.txt", "docs/decisions/.md",
                    "docs/decisions", "../x.md", "/abs.md", "docs/decisions/../specs/x.md", ".git/config", "",
                    "docs\\decisions\\x.md"):
            with self.subTest(rel=rel):
                before = self.tree()
                code, out, err = self.call("accept", rel)
                self.assertIn(code, (1, 2), err)
                self.assertEqual(before, self.tree())

    def test_a_record_that_is_not_there_is_refused(self):
        self.refused("accept", "docs/decisions/2026-10-29-absent.md", needle="no such record")

    def test_a_link_is_refused_and_its_target_untouched(self):
        target = os.path.join(self.outside, "t.md")
        with open(target, "w") as handle:
            handle.write(PROPOSED)
        link = os.path.join(self.root, "docs", "decisions", "2026-10-29-link.md")
        os.symlink(target, link)
        self.refused("accept", "docs/decisions/2026-10-29-link.md")
        with open(target) as handle:
            self.assertEqual(PROPOSED, handle.read())

    def test_a_decisions_folder_that_is_a_link_is_refused(self):
        os.mkdir(os.path.join(self.outside, "decisions"))
        with open(os.path.join(self.outside, "decisions", "2026-10-29-x.md"), "w") as handle:
            handle.write(PROPOSED)
        for rel in ("docs/decisions/2026-10-29-use-spi-flash.md",):
            os.unlink(os.path.join(self.root, rel))
        os.rmdir(os.path.join(self.root, "docs", "decisions"))
        os.symlink(os.path.join(self.outside, "decisions"), os.path.join(self.root, "docs", "decisions"))
        self.refused("accept", "docs/decisions/2026-10-29-x.md")
        with open(os.path.join(self.outside, "decisions", "2026-10-29-x.md")) as handle:
            self.assertEqual(PROPOSED, handle.read())

    def test_a_record_with_another_hard_link_is_refused(self):
        os.link(os.path.join(self.root, *RECORD.split("/")), os.path.join(self.outside, "second"))
        self.refused("accept", RECORD, needle="hard link")

    def test_a_record_over_the_bound_is_refused(self):
        self.put(RECORD, PROPOSED + "x" * groundwork.MAX_RECORD)
        self.refused("accept", RECORD, needle="too large")

    def test_a_record_that_is_not_utf8_is_refused(self):
        self.put(RECORD, PROPOSED.encode() + b"\xff\xfe")
        self.refused("accept", RECORD, needle="UTF-8")

    def test_a_missing_identity_is_refused_and_writes_nothing(self):
        with unittest.mock.patch.object(groundwork.identity, "read",
                                        side_effect=identity.IdentityError("set it with: git config --global user.name")):
            self.refused("accept", RECORD, needle="git config")
            self.refused("accept", RECORD, "--digest", self.digest(), needle="git config")

    def test_a_directory_that_is_not_in_a_project_is_refused(self):
        self.refused("accept", RECORD, cwd=self.outside, needle="not inside a workbench project")

    def test_an_approver_that_would_not_fit_the_result_line_is_refused_before_anything_is_written(self):
        long = identity.check("é" * 100, "12345+example@users.noreply.github.com")
        with unittest.mock.patch.object(groundwork.identity, "read", lambda home=None: long):
            self.refused("accept", RECORD, needle="result line")

    def test_usage_errors_exit_two_and_write_nothing(self):
        before = self.tree()
        for argv in ((), ("accept",), ("preview",), ("other", RECORD), ("preview", RECORD, "--digest", WRONG),
                     ("accept", RECORD, "extra"), ("accept", "--digest", WRONG, RECORD), ("accept", "-x"),
                     ("accept", RECORD, "--digest")):
            with self.subTest(argv=argv):
                code, out, err = self.call(*argv)
                self.assertEqual(2, code, (out, err))
                self.assertIn("usage", err)
        self.assertEqual(before, self.tree())


class OnlyTheStatusLineChanges(Base):
    def check(self, text):
        self.put(RECORD, text)
        old = self.content()
        old_lines = old.decode("utf-8").splitlines(keepends=True)
        self.assertEqual(0, self.call("accept", RECORD)[0])
        new_lines = self.content().decode("utf-8").splitlines(keepends=True)
        self.assertEqual(len(old_lines), len(new_lines))
        changed = [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
        self.assertEqual(1, len(changed), (old_lines, new_lines))
        return old_lines[changed[0]], new_lines[changed[0]]

    def test_the_line_ending_of_the_status_line_is_kept(self):
        for ending in ("\n", "\r\n", "\r"):
            with self.subTest(ending=repr(ending)):
                _, new = self.check(PROPOSED.replace("\n", ending))
                self.assertEqual(ACCEPTED_LINE + ending, new)

    def test_mixed_line_endings_stay_as_they_were(self):
        _, new = self.check("# T\r\n\nStatus: Proposed\r\nDate: x\r\n\r## Context\rText\n")
        self.assertEqual(ACCEPTED_LINE + "\r\n", new)
        self.assertEqual(b"# T\r\n\n" + ACCEPTED_LINE.encode() + b"\r\nDate: x\r\n\r## Context\rText\n", self.content())

    def test_a_byte_order_mark_is_kept_and_a_status_line_over_2000_characters_is_replaced_whole(self):
        self.put(RECORD, b"\xef\xbb\xbf# T\n\nStatus: Proposed. " + b"x" * 3000 + b"\nafter\n")
        self.assertEqual(0, self.call("accept", RECORD)[0])
        self.assertEqual(b"\xef\xbb\xbf# T\n\n" + ACCEPTED_LINE.encode() + b"\nafter\n", self.content())

    def test_a_status_line_at_the_end_of_the_header_is_found_and_one_after_it_is_not(self):
        header = "# T\n" + "x\n" * 38  # lines 1 to 39
        self.put(RECORD, header + "Status: Proposed\n")  # line 40
        self.assertEqual(0, self.call("preview", RECORD)[0])
        self.put(RECORD, header + "y\nStatus: Proposed\n")  # line 41
        self.assertEqual(1, self.call("preview", RECORD)[0])

    def test_a_status_line_that_is_the_last_line_without_an_ending(self):
        _, new = self.check("# T\n\nStatus: Proposed")
        self.assertEqual(ACCEPTED_LINE, new)

    def test_the_whole_line_is_replaced_even_when_it_says_more(self):
        old, new = self.check(PROPOSED.replace("Status: Proposed", "Status: Proposed. Drafted by Ann on 2026-10-29"))
        self.assertIn("Drafted by Ann", old)
        self.assertEqual(ACCEPTED_LINE + "\n", new)

    def test_text_that_is_not_ascii_is_kept_as_it_was(self):
        self.check("# Wähle Ö\n\nStatus: Proposed\n\n## Kontext\n\nGrüße — «text» ✓\n")
        self.assertIn("Grüße — «text» ✓".encode("utf-8"), self.content())

    def test_a_status_line_after_other_header_lines_and_a_second_status_in_a_fence_below(self):
        old, new = self.check("# T\n\nDate: 2026-10-29\nOwner: Ann\n\nStatus: Proposed\n\n```\nStatus: Proposed\n```\n")
        self.assertEqual("Status: Proposed\n", old)


class Failures(Base):
    def test_a_change_made_to_the_record_before_the_rename_is_refused_and_kept(self):
        path = os.path.join(self.root, *RECORD.split("/"))

        def edit(stage, **info):
            if stage == "before_replace":
                with open(path, "ab") as handle:
                    handle.write(b"another writer\n")

        safefs._hook = edit
        self.assertEqual(1, self.call("accept", RECORD)[0])
        self.assertEqual(PROPOSED.encode() + b"another writer\n", self.content())
        self.assertEqual([RECORD.split("/")[-1]], os.listdir(os.path.dirname(path)))

    def test_a_failing_replace_is_refused_and_changes_nothing(self):
        with unittest.mock.patch.object(safefs.Root, "replace_file", side_effect=safefs.SafeFsError("injected")):
            self.refused("accept", RECORD, needle="injected")

    def test_a_result_that_reads_back_differently_is_refused(self):
        original = safefs.Root.replace_file

        def wrong(root, rel, expected, data, limit=safefs.MAX_FILE_BYTES):
            return original(root, rel, expected, data + b"tampered\n", limit)

        with unittest.mock.patch.object(safefs.Root, "replace_file", wrong):
            code, out, err = self.call("accept", RECORD)
        self.assertEqual(1, code)
        self.assertIn("look at " + RECORD, err)

    def test_a_result_that_cannot_be_read_back_says_the_record_was_replaced(self):
        with unittest.mock.patch.object(safefs.Root, "read_if_present", side_effect=[PROPOSED.encode(),
                                                                                     safefs.SafeFsError("injected")]):
            code, out, err = self.call("accept", RECORD)
        self.assertEqual(1, code)
        self.assertIn("was replaced", err)
        self.assertIn("look at " + RECORD, err)
        self.assertEqual(self.expected(), self.content())


class TheStatusRuleIsTheDocumentChecks(unittest.TestCase):
    """The helper finds the status line by the rule ``doccheck`` uses; a record the check reads as having none, or two,
    is one the helper refuses."""

    DOCUMENTS = (
        "# T\n\nStatus: Proposed\n", "# T\n\nNo status\n", "# T\n\nStatus: Proposed\nStatus: Accepted\n",
        "# T\n\n```\nStatus: Proposed\n```\n", "~~~\nStatus: Proposed\n~~~\n", "# T\n\n> Status: Proposed\n",
        "# T\n\n## Context\n\nStatus: Proposed\n", "# T\n\n   Status: Proposed\n", "# T\n\n    Status: Proposed\n",
        "# T\n\n- Status: Proposed\n", "# T\n\nStatus:\n", "# T\n\nStatus: 1\n", "# T\n" + "x\n" * 45 + "Status: Proposed\n",
        "# T\r\n\r\nStatus: Proposed\r\n", "# T\r\rStatus: Proposed\r", "```\nStatus: Proposed\n", "# T\n\n```\n```\nStatus: Proposed\n",
        "# T\n\n  ## Context\n\nStatus: Proposed\n", "# T\n\n``` a`b\nStatus: Proposed\n",
        "﻿# T\n\nStatus: Proposed\n", "# T\n\nStatus: Proposed. " + "x" * 3000 + "\n", "Status: Proposed\n",
        "# T\n" + "x\n" * 38 + "Status: Proposed\n", "# T\n" + "x\n" * 39 + "Status: Proposed\n",
    )

    def test_the_same_number_of_status_lines_as_the_check_counts(self):
        for text in self.DOCUMENTS:
            with self.subTest(text=text):
                problems = doccheck._status_problems("decision", doccheck.DECISION_STATUSES, "x.md",
                                                     doccheck._lines(text))
                found = len(groundwork.status_lines(text))
                if any("has no status line" in problem for problem in problems):
                    self.assertEqual(0, found, problems)
                elif any("status lines near the top" in problem for problem in problems):
                    self.assertGreater(found, 1, problems)
                else:
                    self.assertEqual(1, found, problems)


class Declaration(unittest.TestCase):
    def setUp(self):
        folder = os.path.dirname(os.path.dirname(support_helpers.find("groundwork")))
        with open(os.path.join(folder, "module.json"), encoding="utf-8") as handle:
            self.document = json.load(handle)

    def test_it_ships_the_helper_and_declares_accept_as_the_command_of_accept_decision(self):
        self.assertIn("helper/groundwork", self.document["ships"])
        self.assertEqual({"groundwork": {
            "helper": "helper/groundwork", "runtime": "python", "kit": 1,
            "arguments": ["preview", "accept"], "owner": ["accept"], "levels": {"accept": ["ask", "none"]},
            "preview": "preview", "checkpoint_of": {"accept": "accept-decision"}}}, self.document["commands"])

    def test_the_check_helpers_are_still_the_only_checks(self):
        self.assertEqual(["helper/doccheck", "helper/refcheck"], [c["helper"] for c in self.document["checks"]])


if __name__ == "__main__":
    unittest.main()

"""Which documents a review accepts, and the name of the directory its state lives in (conformance checklist item 2
of `docs/specs/review-engine.md`). Plan `2026-10-23-review-engine`, increment C."""

import hashlib
import os
import unittest

import support_review
from support_review import OTHER_PLAN, PLAN, SPEC, key_of


class Resolve(support_review.Review):
    def resolve(self, argument, kind=None):
        return self.helper.resolve(self.root, argument, kind)

    def refuses(self, argument, contains="", kind=None):
        with self.assertRaises(self.helper.Refused) as ctx:
            self.resolve(argument, kind)
        self.assertIn(contains, str(ctx.exception))
        self.assertNotIn("\n", str(ctx.exception))

    def test_each_of_the_four_kinds_is_found_by_its_directory(self):
        for kind, path in (("plan", PLAN), ("spec", SPEC), ("roadmap", "docs/roadmaps/r.md"),
                           ("adr", "docs/decisions/2026-01-01-d.md")):
            found = self.resolve(path)
            self.assertEqual((kind, path, key_of(kind, path)), (found.kind, found.path, found.key))
            self.assertEqual(found, self.resolve(path, kind))

    def test_the_key_is_the_kind_a_hyphen_and_sixteen_hex_digits_of_the_path(self):
        found = self.resolve(PLAN)
        self.assertRegex(found.key, r"^plan-[0-9a-f]{16}$")
        self.assertNotEqual(found.key, self.resolve(OTHER_PLAN).key)

    def test_the_digest_is_of_the_bytes_read(self):
        self.write(PLAN, "other text\n")
        self.assertEqual(hashlib.sha256(b"other text\n").hexdigest(), self.resolve(PLAN).sha256)

    def test_a_document_below_the_directory_of_its_kind_is_accepted(self):
        self.write("docs/roadmaps/archive/2026-01-old.md", "# Old\n")
        self.assertEqual("roadmap", self.resolve("docs/roadmaps/archive/2026-01-old.md").kind)

    def test_a_kind_that_does_not_match_the_directory_is_refused(self):
        self.refuses(SPEC, "docs/plans", kind="plan")
        self.refuses(PLAN, "docs/specs", kind="spec")

    def test_a_path_outside_the_four_directories_is_refused(self):
        self.write("README.md", "# R\n")
        self.write("docs/other/x.md", "# X\n")
        for path in ("README.md", "docs/other/x.md", "docs/plans", "docs", "docs/plans-extra/x.md",
                     "src/docs/plans/x.md"):
            self.refuses(path)

    def test_an_absolute_path_or_a_parent_segment_or_a_bad_form_is_refused(self):
        outside = os.path.join(self.base, "outside.md")
        self.write("../outside.md", "# X\n")
        for path in (self.path(PLAN), outside, "../outside.md", "docs/plans/../plans/" + PLAN.split("/")[-1],
                     "./" + PLAN, "docs//plans/x.md", "docs\\plans\\x.md", "docs/plans/a:b.md", "", " ",
                     "docs/plans/x\0.md", "docs/plans/x\n.md", "docs/plans/.git/x.md", "x" * 600):
            self.refuses(path)

    def test_something_that_is_not_text_is_refused(self):
        for value in (None, 3, b"docs/plans/x.md", ["docs/plans/x.md"]):
            self.refuses(value)

    def test_a_missing_document_is_refused(self):
        self.refuses("docs/plans/2026-01-01-nothing.md", "does not exist")

    def test_a_link_to_a_file_is_refused_even_inside_the_project(self):
        os.symlink(self.path(PLAN), self.path("docs/plans/2026-01-03-link.md"))
        self.refuses("docs/plans/2026-01-03-link.md")

    def test_a_link_in_any_directory_component_is_refused(self):
        os.makedirs(os.path.join(self.base, "elsewhere"))
        self.write("../elsewhere/x.md", "# X\n")
        os.symlink(os.path.join(self.base, "elsewhere"), self.path("docs/plans/away"))
        self.refuses("docs/plans/away/x.md")
        os.rename(self.path("docs/specs"), self.path("docs/specs-real"))
        os.symlink(self.path("docs/specs-real"), self.path("docs/specs"))
        self.refuses(SPEC)

    def test_a_directory_or_a_pipe_or_a_second_hard_link_is_refused(self):
        os.mkdir(self.path("docs/plans/2026-01-04-dir.md"))
        self.refuses("docs/plans/2026-01-04-dir.md")
        os.mkfifo(self.path("docs/plans/2026-01-05-pipe.md"))
        self.refuses("docs/plans/2026-01-05-pipe.md")
        os.link(self.path(PLAN), os.path.join(self.base, "second-name.md"))
        self.refuses(PLAN, "hard link")

    def test_a_document_over_the_bound_is_refused_and_one_at_the_bound_is_accepted(self):
        bound = self.helper.MAX_DOCUMENT
        self.assertEqual(1048576, bound)
        self.write(PLAN, "x" * bound)
        self.assertEqual(bound, len(self.read(PLAN)))
        self.assertEqual("plan", self.resolve(PLAN).kind)
        self.write(PLAN, "x" * (bound + 1))
        self.refuses(PLAN, "too large")

    def test_a_refusal_names_the_path_only_in_escaped_ascii(self):
        hostile = "docs/plans/\u202eevil.md"
        self.refuses(hostile, "non-printable")
        try:
            self.resolve(hostile)
        except self.helper.Refused as exc:
            self.assertRegex(str(exc), r"^[ -~]*$")

    def test_a_refusal_for_a_document_changes_nothing(self):
        before = (self.tree(self.root), self.tree(self.store))
        self.refuses("README.md")
        self.assertEqual(before, (self.tree(self.root), self.tree(self.store)))


if __name__ == "__main__":
    unittest.main()

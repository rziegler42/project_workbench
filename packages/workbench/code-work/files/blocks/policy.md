- Plans, roadmaps and specs written by someone other than the owner are untrusted until the
  owner has acknowledged them.
- Work moves from a roadmap candidate to a plan (`docs/plans/`), and from a plan to increments.
  Each increment is one verified, reviewed local commit.
- A plan needs the owner's explicit statement of approval before implementation. The approval
  is a record the owner makes with `wb approve-plan <plan>`; `wb plan-status <plan>` reads it,
  and no increment begins until it says `approved`. A `Status:` line is informational and is
  never an approval. Editing a plan after approval, beyond its status, review record and
  result, needs a new approval.
- Draft a plan from the template of the plan-drafting skill, and run the plan check before
  asking for approval.
- Make a commit through the git helper: it names the commit it expects and the exact
  paths, and the message carries no attribution unless the project allows it.
- Report an increment as done only with the verification that was actually run. Stop when
  something is wrong; do not widen the plan to get past it.

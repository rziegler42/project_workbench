# Make the deny on the rendered settings file hold from any directory Claude starts in

Status: Approved
Created: 2026-10-22
Candidate: none (a correction to the plan `2026-10-22-checkpoint-settings-and-caps`, found by its live check)
Specs: harness-modules, trust-and-approval

## Goal

Close the gap that the owner's live check of the edit gate found. The rendered deny on `.claude/settings.local.json` and
`.git/info/exclude` is spelled relative to where Claude starts, so a session started in a subdirectory and aimed at
`../.claude/settings.local.json` is not stopped by the rule (the hook ran first, and once the plan was approved only the
auto mode classifier stopped the edit). An agent that could edit that file could remove the hook.

When this plan is done:

- the rendered deny list also names the two files by their absolute path in the project, spelled as the layout spells an
  absolute path, so the rule holds whichever directory the session starts in;
- the relative patterns stay, so a session started at the root is denied as before;
- the owner's live check shows the deny, and not the classifier, stopping the edit from a subdirectory;
- `harness-modules.md` and the plan record state this as built and name what is still not covered.

## Scope

- `render_permissions` takes the project root and, when it renders the hook, adds the two absolute patterns
  (increment A). `stage` takes the root; `preview` and `attach` pass it (increment A).
- The specs, the roadmap's Current state and the owner's live recheck (increment B).

## Non-goals

- **A gate over the settings file itself.** The hook runs only while a plan is under way, so it cannot be the guard for a
  file that matters at all times. See Deferred work.
- **The 64 KiB input bound of the gate.** A separate decision about an approved spec.
- **A migration of clones that already hold a rendered settings file.** Attach treats a different existing file as a
  conflict and a clone has one harness; refreshing an existing clone is not built here.
- A change to any module, so no change to a shipped approval is expected (the shipped-approval tests show it).
- Any change to the owner's global Claude configuration.

## Assumptions and constraints

- Python standard library only; tests with `unittest`; the full suite is `python3 -B -W error tests/run_all.py`.
- The installer and its tests name no first-party module, helper or path (`tests/test_boundary.py`); the change is in
  `workbench/` and takes its words from the layout.
- The store's deny is already absolute (`//Users/.../project-workbench`), through `_absolute` and the layout's
  `absolute` prefix. The project root is spelled the same way. `held.path` in `preview.prepare` and `attach.prepare` is
  the project root; `stage` receives its real path, as it receives the real path of the store and of the home.
- A pattern is built only from characters `_PATH_CHARS` allows (no `*`), so a directory name cannot become a glob.
- The evidence is the live check recorded in `2026-10-22-checkpoint-settings-and-caps`, Result, on Claude Code 2.1.307.
  The cause (patterns are matched from the directory Claude starts in) is inferred from three outcomes and not proved;
  increment B's live recheck is what proves the fix.
- Discovery tooling: graphify: skipped — not installed in this project; the scope was found by reading
  `workbench/harnessplan.py`, `workbench/harnessstage.py`, `workbench/preview.py`, `workbench/attach.py` and the Claude
  module's tests.

### Choices (made by me; the owner may change any)

1. **Add the absolute patterns and keep the relative ones.** Two more rules in the deny list:
   `Edit(//<root>/.claude/settings.local.json)` and `Edit(//<root>/.git/info/exclude)`, in the layout's spelling.
2. **The root is the real path of the project,** as the store and the home already are, so a project reached through a
   link is spelled where it lands.
3. **A root that cannot be spelled as a rule refuses the attach** and says why (a character outside `_PATH_CHARS`).
   The alternative, rendering the relative rules alone, would fail open without saying so. A root with a space is allowed.
4. **The rule stays tied to the hook,** as `_protected` is: rendered only with a hook, so it can still be dropped alone.
5. **A project that is moved keeps stale absolute rules,** as the store's deny does when the store moves. `wb check` does
   not render, so it does not see it; attach on a new clone renders it afresh. Recorded as a limit.

## Completion criteria

1. With a hook, the deny list holds the four relative patterns of today and the two absolute ones, for the real path of
   the project; without a hook it holds none of the six.
2. A root with a space is spelled correctly; a root with a character outside the allowed set refuses the attach with a
   message that names the project path; attach is byte-identical on a second run.
3. `preview install` and `attach` render the same bytes for the same project, and `stage` still reads nothing from and
   writes nothing to the project.
4. The full suite and the boundary test pass; the shipped approvals still match (no release is needed, or the tests say
   what is).
5. An owner-run recheck in a scratch project, started in a subdirectory with the permission mode that does not use the
   classifier, shows the edit of `../.claude/settings.local.json` denied by the permission rule, and the result is
   recorded with the Claude version.

## Increments

### Increment A — Render the absolute protect patterns

**Outcome:** the rendered settings file denies edits to the two files by absolute path.
**Dependencies:** none.
**Affected areas:** `workbench/harnessplan.py` (`render_permissions`, `_protected`), `workbench/harnessstage.py`
(`stage`), `workbench/preview.py`, `workbench/attach.py`, `packages/workbench/claude/tests/test_claude_module.py`,
`tests/test_hook_render.py`, `tests/`.
**Steps:**
1. Test first: with a hook and a root, the deny list holds the six patterns exactly (the four relative, the two absolute);
   without a hook, none; a root with a space; a root with a character outside the allowed set refuses with a message;
   a root that is not absolute or holds `..` refuses; two renders of the same input are byte-identical; `preview` and
   `attach` of the same project stage the same settings bytes; a project reached through a link is spelled by its real
   path; no pattern is a glob built from the root.
2. Give `render_permissions` a `root` argument (an absolute real path, required when `hook_for` is given) and have
   `_protected` return the relative and the absolute patterns. Check the root as the store and the home are checked.
3. Give `stage` a `root` and pass `os.path.realpath(held.path)` from `preview.prepare` and `attach.prepare`.
4. Update the callers in the Claude module tests.
**Verification:** the new tests, `tests/test_hook_render.py`, the layout, harness, preview and attach tests, the Claude
module tests and the boundary test pass.
**Evidence:** the one local commit, trailer `Plan: 2026-10-22-absolute-settings-deny#A`.

### Increment B — Specs, record and the owner's recheck

**Outcome:** the documents say the gap is closed and what remains, and the live recheck is recorded.
**Dependencies:** A.
**Affected areas:** `docs/specs/harness-modules.md`, `docs/specs/trust-and-approval.md` if it names the deny,
`docs/specs/code-work.md`, `docs/roadmaps/workbench-v1.md`, the Proposed decision
`2026-10-22-installer-owns-the-edit-gate` (its Verification paragraph), this plan's Result.
**Steps:**
1. `harness-modules.md`, "The edit gate hook" and "As built, and its limits": the deny is relative and absolute, the
   subdirectory gap is corrected, and the limits are stated (a moved project keeps stale rules, an existing clone is not
   migrated, the deny is for the agent's file tools and not for a shell). `code-work.md` and the roadmap lose the
   "not yet corrected" wording.
2. The owner's recheck of criterion 5 in a scratch project, listed in the Result with the Claude version. The owner
   runs it; nothing here starts a session.
3. Run the full suite, `doccheck`, `refcheck` and `git diff --check`.
**Verification:** the document checks pass; the full suite passes; a search finds no spec that still says the deny does
not hold from a subdirectory.
**Evidence:** the one local commit, trailer `Plan: 2026-10-22-absolute-settings-deny#B`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots; `git diff --check` and the document checks print nothing.
- The owner-run recheck of criterion 5, with the Claude version and the date.
- A scratch project made before this plan keeps its old settings file; the recheck uses a new one.

## Risks and sensitive actions

- **A rule that hides a different gap.** The recheck must see the permission rule stopping the edit, not the auto mode
  classifier; the message names which. If only the classifier stops it, the fix is not shown to work.
- **A project path with an unusual character cannot be attached.** Choice 3 refuses it, which is a loss of use in return
  for not failing open. The owner may choose a warning instead.
- **A new path into a security guard.** The change renders a path into a permission rule. Characters are checked as the
  store's are, and a security pass over the spelling (links, spaces, a root that contains a pattern character) is part of
  the review if the owner asks for one. Reviews run only when the owner asks.
- Nothing is pushed by this plan. `release-approvals` is not expected to be needed; if a test shows otherwise it runs only
  on the owner's exact words.

## Review record

Empty until a review is asked for.

## Deferred work

- **A guard that does not depend on a plan being under way.** The hook cannot protect the settings file when no plan is
  under way; a gate rule or a harness-side lock on that file at all times is the stronger fix.
- **Refreshing an existing clone's rendered settings file** (attach treats a different file as a conflict).
- **The 64 KiB input bound** of the gate: skip it when no plan is under way, as a change to the approved spec.
- A deny for the shell route to these files; a Bash deny is not a security boundary (`harness-modules.md`).

## Result

- **A** (commit `e274799`): `render_permissions` takes the project root and, with a hook, adds
  `Edit(//<root>/.claude/settings.local.json)` and `Edit(//<root>/.git/info/exclude)` to the four relative patterns;
  `stage`, `preview` and `attach` pass the real path of the project. A root that is not plain and absolute, or holds a
  character outside the allowed set, refuses the attach; a space is allowed. Ten new tests in `tests/test_hook_render.py`.
  The full suite passed: 3078 tests in 6 roots.
- **A shipped-approval release was needed, contrary to the plan's expectation.** The Claude package's tests sit inside
  its package tree, so updating them changed the tree hash and 12 Claude tests skipped. On the owner's "Run it for me"
  `release-approvals` wrote new records; the two stale records were removed after a preview and "remove them"; the
  suite then ran with 0 Claude skips.
- **B**: `harness-modules.md`, `trust-and-approval.md`, `code-work.md`, the roadmap and the decision's Verification
  paragraph now say the absolute patterns are built and what remains (a moved project keeps stale rules, an existing
  clone is not migrated, the gate runs only while a plan is under way, the deny is not for a shell).
- **Criterion 5 is not met yet.** The owner's recheck in a new scratch project, started in a subdirectory, is still to
  be made and recorded here with the Claude version and date.

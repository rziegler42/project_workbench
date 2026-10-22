# The code-work module: the commit helper

Status: Approved
Created: 2026-10-22
Candidate: workbench-v1#code-work-commit
Specs: code-work, trust-and-approval, module-contract

## Goal

Give the `code-work` helper the two subcommands that change a repository, `commit` and `remove`, so an
agent commits through a bounded, local, reviewable path and no project depends on the owner's personal
`claude-workflow`. Today the helper only reads. The owner's private helper does these things, outside any
project, with its own tests; a project cannot ship it, a teammate cannot have it, and the project's first
commit (a repository with no commits) is a hand step recorded as a known gap in `AGENTS.md`.

When this plan is done:

- `wb run code-work commit` makes one local commit from exact file paths, after checking that HEAD is
  where the caller expected it to be, that nothing else is staged, that the message carries no tool
  attribution (unless the project says otherwise), and that the commit holds exactly the paths named;
- it can make the first commit of a repository that has none;
- `wb run code-work remove` previews and, with `--confirm`, deletes exact project paths, and refuses
  anything that is, holds or lies inside Git metadata;
- neither runs a program the repository chooses, neither pushes, and neither reads the environment or
  configuration of the repository to decide what to run;
- the shipped approvals are made again and the helper is pinned by the installer as before.

## Scope

- **The git runner** inside the helper: finds `git` on a PATH entry outside the repository, scrubs the
  environment it passes, and refuses a repository whose own configuration or hooks would make a commit run
  a program.
- **`commit`**: argument and message validation, the staging flow of the old helper, the checks after the
  commit, and the unborn-branch case.
- **The attribution setting**: a small committed file, default refuse.
- **`remove`**: preview, confirm, recursive.
- **Module wiring**: the command's `arguments`, the usage text, the README and the policy block where they
  describe commits, and tests through the launcher.
- **The security pass and the release** (`release-approvals`, run by the owner).
- **Spec, guide and roadmap edits** for what was built and decided, and one decision record.

## Non-goals

- `amend-message`, `context` and `project-id` of the old helper. The owner amends with git by hand.
- Updating the acknowledgement baselines (see Choice 2).
- Any push, tag, branch, merge, rebase or checkout, and any reset other than the unstage of the named
  paths after a failure before the commit (criterion 7). The helper runs only the git subcommands listed
  in criterion 7 and increment A.
- Plan approval, review, loop caps, the push checkpoint and compaction guidance (`code-work-approval`).
- Replacing the permission rule or the commit approver in the owner's `~/.claude`, which match
  `claude-workflow commit` today (`global-config-migration`).
- Moving the three read-only subcommands onto the kit. They keep their own readers; the new code uses the
  kit (Choice 1).

## Assumptions and constraints

- Python standard library only; tests with `unittest`; full suite `python3 -B -W error tests/run_all.py`
  (2421 tests in 4 roots today). Real git is used in tests; a test that needs it skips with a reason when
  `git` is not found.
- The helper is run by the launcher from a private copy, through the kit runner (`runtime: python`,
  `kit: 1`), and imports only the standard library and `wbkit`. It does not trust its working directory,
  `sys.path`, the environment or the repository's configuration.
- The repository is attacker-controlled input: its configuration, hooks, attributes, index, file names and
  links. A user's global and system Git configuration is the owner's and is trusted.
- The installer pins the helper on the digest the owner confirmed and binds the pin to the declaration
  (`2026-10-22-installer-pins-declared-helpers`). Changing the command's `arguments` changes the
  declaration; the pin follows at the next upgrade.
- Any file in the module tree, including its tests, makes the shipped approvals stale. Increments A to E
  leave them stale; F makes them again. The tests that need them skip, as before.
- The read-only subcommands run no program and keep that property. `commit` and `remove` are the
  exception, so criterion 5 of the earlier plan is restated for them in increment G.
- **Decided by me, for the owner to confirm or change before approval:**
  1. **The command moves onto the kit.** The helper was written before the kit existed, as one file that
     imports nothing; `groundwork`'s helpers moved onto it. Copying careful reading code into each helper is
     rejected in `2026-10-21-module-code-lives-in-modules` because it drifts. So the command is declared
     `runtime: python, kit: 1` and the new code uses `wbkit`: `safefs` for no-follow reads and path
     checks, `jsonstrict` for the attribution file, `display` for text it prints. The three read-only
     subcommands keep their own readers and are not touched; moving them is deferred. `remove` needs a
     descriptor-relative delete walk that `safefs` lacks. It lives in the helper and not in the kit,
     because a new kit function raises the kit API number and every helper's declaration with it.
     *Alternative:* stay standalone, one file with no kit coupling and the surface of the three read-only
     subcommands unchanged; rejected for the duplication, and because the plan's own `commit` would copy
     what the kit already has.
  2. **The helper does not write the acknowledgement baselines.** The roadmap outcome and a line of
     `trust-and-approval.md` say a deliberate change made through the commit helper updates the
     baselines of the files it changed. The helper is run by an agent with the owner's privileges, and a
     baseline is the owner's acceptance of a change made by someone else. If the helper wrote baselines,
     an agent could edit `AGENTS.md` or a file under `.workbench/`, commit it through the helper and have
     it accepted: the attack `2026-10-20-acknowledge-before-upgrade` exists to stop. So a change to a
     baselined path made and committed through the helper is listed by the next `wb acknowledge`, and the
     owner accepts it there. The spec line and the roadmap outcome are corrected in increment G.
     *Alternative:* write baselines only for paths outside the first tier; today every baselined path is
     in it, so the alternative would write nothing.
  3. **No `--allow-repo-programs`.** The old helper let the owner override the refusal on a repository
     that selects programs (hooks, a filter, `core.fsmonitor`). Through `wb run` the caller is an agent,
     so the override would be the agent's. A repository that selects programs is committed to by hand.
  4. **The attribution setting** is `.workbench/code-work.json`, `{"format": 1, "attribution": "refuse"}`
     or `"allow"`. Absent means refuse. Anything else, a file that is not strict JSON, and a link at that
     path refuse the commit and say why. A file added or edited under `.workbench/` is a difference
     that `wb acknowledge` lists, so a pulled edit that switches it to `allow` is seen before the
     owner accepts it. *Alternative:* a module block in `AGENTS.md`; rejected, the block is prose.
  5. **Output.** A success prints one JSON line on standard output (`committed`, `preview`, `removed`)
     with the same field names the old helper used, so the owner's tools can read both; a refusal prints
     `refused: <reason>` on standard error and exits 1, as the read-only subcommands do.
  6. **Unborn branch.** `--expected-head none` is accepted only when `git rev-parse --verify HEAD` fails
     and HEAD names an unborn branch; any other value is a 40-digit hex hash that must equal HEAD.
  7. **The expected-HEAD guarantee is detection, not atomicity.** Git has no compare-and-swap for
     `git commit` with an index; building the commit with `commit-tree` and `update-ref` would need a
     temporary index to honour `--leave-other-staged`. The helper compares HEAD with the expected hash
     before it stages, after it stages and immediately before it commits, and after the commit it requires
     the new commit's only parent to be the expected hash (none for the first commit). A concurrent
     writer that moves HEAD after the last check therefore produces a commit the helper reports as
     failed: exit 1, `refused: HEAD moved during the commit; the commit <hash> was made on <parent>`,
     nothing undone (a reset is not run, and no history is rewritten). The guarantee is that the helper
     never reports success for a commit whose parent is not the expected one. A second writer in the
     same repository is outside the threat model: the agent and the owner act in turn, and
     `index.lock` serialises Git's own writes.
  8. **`--leave-other-staged` stays.** It commits only the named paths and keeps other staged work
     staged, as the old helper did; without it a non-empty index is refused.
- **The contract ported, stated here so nothing tracked depends on an untracked file.** It comes from the
  owner's private `claude-workflow`, called "the old helper" below (a single script, not in any repository; 633 lines; read 2026-10-22;
  sha256 `7add9cfd6d6b0473c8084d69b9384ea0ed29c5234943a8a2a4fb56e26cdf5464`). The tests carry this contract;
  they do not read that file.
  - **Attribution patterns** (case-insensitive, matched on text that is first NFKC-normalised, stripped of
    Unicode category `Cf` characters, mapped through the confusable table below, with a folded
    continuation line (`\n` then spaces or tabs) joined by one space and `:` followed by a newline joined):
    `co-?authored-?by\s*:[^\n]*(claude|anthropic)`;
    `\b(assisted|generated|created|written|authored|reviewed|helped|made)[- ](with|by)\s+(?:the\s+|an?\s+)?(?:ai\s+)?(claude|anthropic)\b`;
    `(assisted|generated|created|written|authored|reviewed|helped)-?(with|by)\s*:[^\n]*(claude|anthropic)`;
    `noreply@anthropic\.com`;
    `(?<![A-Za-z0-9-])(?:www\.)?claude\.(ai|com)/(code|chat|share|claude-code|new|resume|login)\b`.
    Confusable table (to ASCII): U+0430 a, U+0435 e, U+043E o, U+0440 p, U+0441 c, U+0445 x, U+0443 y,
    U+0455 s, U+0456 i, U+0458 j, U+03BF o, U+03B1 a. The subject, the body and every trailer are checked.
  - **Repository settings that make a commit run a program**, from `git config --list -z` with the global
    file replaced by the null device and the system file ignored (so only the repository and what it
    includes is read): a key, lower-cased, that fully matches
    `.*\.(program|command|driver|cmd|clean|smudge|process|textconv|external|defaultkeycommand)` or
    `core\.(hookspath|fsmonitor|sshcommand)`, or `commit.gpgsign` with a true Git boolean (no value is true;
    an integer is true unless zero; only empty, `false`, `no`, `off` and `0` are false; anything unrecognised
    is true); a configuration that cannot be listed; and an executable file that does not end in `.sample`
    in the `hooks` directory of both `rev-parse --absolute-git-dir` and `--git-common-dir`. Only the names
    of findings are reported, never their values.
  - **Paths:** exact, repository-relative names; refused are an empty name, `.`, `..`, an absolute path, any
    of `*?[]`, a leading `:` or `-`, a directory, a name that does not exist and is not tracked, and (for
    `remove`) any component equal to `.git` in any case or any `.`/`..` component. Git runs with
    `GIT_LITERAL_PATHSPECS=1`.
  - **Staging semantics:** HEAD must equal the expected hash; a non-empty index is refused unless
    `--leave-other-staged`; a named path already staged is refused; `git diff --check` on the named paths
    first; `git add -- <paths>`; the staged set must equal the named set (less what was staged before);
    `git diff --cached --check`; the commit takes one `-m` per paragraph (subject, body, one paragraph of
    trailers joined by newlines) and, with `--leave-other-staged`, `--only -- <paths>`; afterwards the
    message must equal the paragraphs joined by a blank line, the commit's changed paths must equal the
    named set, and the index must be what it was before.
- Discovery: graphify — skipped, this project has no discovery tooling. The files read for this plan:
  the owner's `claude-workflow` (`commit`, `remove`, the path and Git-metadata checks; see the contract above), the helper in
  `packages/workbench/code-work/helper/code-work`, `module.json`, `launch.py`, `commands.py`, `code-work.md`,
  `trust-and-approval.md`, `workbench-v1.md` and the plan `2026-10-21-code-work-plans`.

## Completion criteria

1. In a repository with commits, `wb run code-work commit --expected-head <hash> --subject S -- <paths>`
   makes exactly one commit that holds exactly the named paths, with the message S plus an optional body
   and `Key: value` trailers, and prints the commit, the subject and the paths. HEAD that differs, a
   non-empty index (without `--leave-other-staged`), a path already staged, a directory, a glob, a
   `:`-prefixed or `-`-prefixed path, a path outside the repository, a path through a link, a path in a
   nested repository, a gitlink, and `.git` in any case each refuse and change nothing.
2. In a repository with no commits, `--expected-head none` makes the first commit the same way.
3. A message that carries tool attribution (the old helper's patterns, after Unicode normalisation) is
   refused, unless `.workbench/code-work.json` says `allow`. A subject with a newline, a NUL or a
   carriage return, a trailer that is not one `Key: value` line, and a body with a NUL are refused.
4. A repository whose configuration or hooks select a program (the old helper's shapes), a `git` found
   inside the repository, and a relative or empty PATH entry are refused or ignored as the old helper did.
   No `GIT_*` variable of the caller (`GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_CONFIG_*`,
   `GIT_EXEC_PATH`, `GIT_SSH_COMMAND`, `GIT_ASKPASS`, the editor and pager variables and the rest) is passed
   on; the helper sets the few it needs itself (increment A).
5. After the commit the helper checks that the message is the one asked for, that the commit's only parent
   is the expected HEAD (Choice 7), that it holds exactly the named paths, and that the rest of the index
   is as it was. A failure before the commit unstages the named paths and says so; a failure after it is
   reported with the commit hash and undoes nothing.
6. `remove` previews and, with `--confirm`, removes exact paths; it refuses `.git` in any case, a path
   that is, holds or lies inside Git metadata or a nested repository, the repository root, a path through
   a link, overlapping targets, a glob, and a directory without `--recursive`. It follows no link and
   removes nothing outside the subtrees it validated. The guarantee is confinement, not identity, and it
   has two parts. **Between the preview and the confirmation** (two runs, so no inode survives from one
   to the other): `--confirm` validates every target from scratch, and a target that was replaced in
   between is removed as what it now is if it passes every check, and refused if it does not. **During the
   walk:** each entry is removed relative to the descriptor of its already-checked parent, so a swap for a
   link removes the link and not what it points to, and a swap for a directory is refused by `rmdir`; an
   entry whose type changed since it was listed, a nested repository and a new `.git` entry stop the walk.
   The report lists what was removed and, if the walk stopped, what was not (exit 1).
7. The helper runs only these git subcommands: `rev-parse`, `diff`, `ls-files`, `add`, `commit`, `reset`
   (only `reset -q -- <the named paths>`, only before the commit and only while HEAD is the expected one), `show`, `diff-tree`, `config` (read) and `status`; a test with a recording `git`
   shows the arguments of every run and that no `push`, `fetch`, `checkout`, `switch`, `merge`, `rebase`,
   `tag` or `branch` appears on any path, including every failure path.
8. The read-only subcommands behave as before and still run no program.
9. An adversarial `security-reviewer` pass over the helper finds nothing Medium or higher unresolved, and a
   second pass has tried to bypass each fix.
10. The specs, the guide, the roadmap and `AGENTS.md` describe what was built, the decision record exists,
    and the full suite passes with `-W error`.

## Review focus

Inputs the specs imply that the tests must pin, most likely to bite first:

1. **A repository that runs code.** `core.fsmonitor`, `core.hooksPath`, `core.sshCommand`, `core.editor`,
   `core.pager`, `commit.gpgsign` with `gpg.program`, `diff.external`, a clean or smudge filter in
   `.gitattributes`, `include.path` and `includeIf` to a file with those keys, an executable
   `pre-commit` or `commit-msg` hook, `core.worktree`, `core.bare`, a `gitdir:` file, and
   `extensions.*`. The old helper refused most of these by the shapes in the contract; `core.editor`,
   `core.pager`, `core.worktree`, `core.bare`, `gitdir:` and `extensions.*` are made unreachable instead (every
   message is given with `-m`, `GIT_EDITOR=true` and `GIT_PAGER=cat` are set by the helper, and the root
   checks of increment A refuse the others). The tests run each with a script that writes a marker file and
   assert the marker never appears.
2. **A `git` the repository supplies.** A `git` in a relative PATH entry, an empty entry, `.`, a
   directory inside the repository, a symlink to one; and `PATH` without a git at all.
3. **The caller's environment.** Every Git variable that redirects the repository, the index, the object
   store, the config, the editor, the askpass or the exec path, set to a hostile value in the helper's
   environment.
4. **Paths.** `-x`, `:(glob)*`, `:!x`, `*`, a name with a newline or a tab or a leading space, a name with
   backslashes, `a/../b`, `./a`, `a//b`, a path through a link to a file outside, a link that is the
   file, a deleted tracked file, an untracked ignored file, a file in a submodule or gitlink, `.GIT/config`,
   `.git ` with a trailing space or dot on a case-folding filesystem, and 10,000 paths.
5. **Messages.** Attribution spelled with Cyrillic or Greek look-alikes, zero-width characters, fullwidth
   forms, split across a folded line, in a trailer, in the body and in the subject; a body that is only
   whitespace; a trailer with a newline; a subject of 100,000 characters.
6. **Races.** HEAD moves between the check and the commit (the helper must report failure and name the
   parent, never success: a recording `git` moves HEAD between its own calls); a path changes between
   `add` and `commit`; the index is replaced between the two checks; a file becomes a link after validation.
7. **State.** Unborn branch, detached HEAD, a merge in progress (`MERGE_HEAD`), a rebase in progress, a
   sparse checkout, a skip-worktree path, an assume-unchanged path, a shallow clone, a worktree whose
   `.git` is a file.
8. **Removal.** An entry swapped for a link, a directory or a file during the walk (a test hook between the
   listing and the unlink of each entry), a `.git` created inside the tree during the walk, a directory holding a nested repository at any depth, a separate git directory inside a
   subdirectory, a link to a directory, a directory that is also a mount point, two spellings of one
   file, a path whose parent is a link, a case-colliding pair, and `--recursive` on a file.
9. **Failure after staging.** `git commit` fails (a hook the owner trusts, a full disk): the named paths
   are unstaged, nothing else is touched, and the exit says so.
10. **The attribution file.** Absent, empty, not JSON, `format` 2, an unknown key, a duplicate key,
    `"attribution": "ALLOW"`, a link, a directory, 2 MiB.

## Increments

### Increment A — The git runner and the repository checks

**Outcome:** the helper can run `git` safely and refuses a repository that selects programs. No
subcommand uses it yet, so nothing changes for a project.
**Dependencies:** none.
**Affected areas:** `packages/workbench/code-work/helper/code-work`, `module.json` (`runtime`, `kit`),
`tests/test_codework_git.py` (new), `tests/support_git.py` (new: real repositories in a temporary directory,
a recording fake `git`).
**Steps:**
0. Declare the command `runtime: python, kit: 1` and import `wbkit` in the helper (Choice 1). The
   read-only subcommands are unchanged; their tests run as before, loaded as `groundwork`'s helper tests do.
   A test pins that the pin made by the installer records kit 1 and that `wb run` refuses a pin without it.
1. Failing tests first: the trusted-PATH search, the environment scrub, `GIT_NO_REPLACE_OBJECTS`, the
   repository root and boundary checks of the old helper (`git_root`, the `core.worktree` and separate
   git directory refusals), and `repo_program_findings` with each key shape and each hook.
2. Port `run`, `trusted_path_entries`, `trusted_which`, `git_root`, `head`, `names` and
   `repo_program_findings`. The environment is built from a short allowlist (`HOME`, `LANG`, `LC_*`,
   `TZ`, `TERM`, the scrubbed `PATH`) and `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_NOSYSTEM`,
   `GIT_TERMINAL_PROMPT=0`, `GIT_EDITOR=true`, `GIT_PAGER=cat`, `GIT_NO_REPLACE_OBJECTS=1` and (for
   `commit`) `GIT_LITERAL_PATHSPECS=1`, all set by the helper; no `GIT_*` variable of the caller is passed. Add the git-subcommand allowlist of
   criterion 7 inside `run`, so a bug cannot reach `push`.
3. A recording `git` in the tests proves the allowlist and the environment.
**Verification:** the new tests; the full suite; the read-only tests unchanged.
**Evidence:** commit with trailer `Plan: 2026-10-22-code-work-commit#A`.

### Increment B — `commit`

**Outcome:** `commit` works in a repository that has commits.
**Dependencies:** A.
**Affected areas:** the helper; `tests/test_codework_commit.py` (new).
**Steps:**
1. Failing tests first for criteria 1 and 3 and review focus 4, 5, 6 and 9, against real repositories.
2. Port `validate_subject`, `refuse_attribution` with its confusable map, `message_paragraphs`,
   `validate_paths` and the `commit` flow. Path validation uses `wbkit.safefs` and refuses a link at any
   component (the old helper's `resolve()` follows links and is replaced); a path is also
   compared with `git ls-files -s` for a gitlink mode, and a path under a directory that holds its own `.git`
   (a nested repository) is refused.
3. The three HEAD checks and the after-commit checks of criterion 5 (Choice 7). On any failure before the
   commit, run `git reset -q -- <named paths>` only if HEAD is still the expected one; after the commit,
   undo nothing.
4. Arguments are parsed by hand (`argparse` on untrusted `--` handling is avoided): `--expected-head`,
   `--subject`, `--body`, `--trailer` (repeatable), `--leave-other-staged`, then `--`, then the paths. An
   unknown option, a repeated singleton option and a missing `--` refuse.
**Verification:** the new tests; mutation checks (remove the HEAD check, the staged-set comparison, the
link refusal, the unstage-on-failure: a named test fails each time); the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-22-code-work-commit#B`.

### Increment C — The first commit and the attribution setting

**Outcome:** a repository with no commits can be committed to, and a project can allow attribution.
**Dependencies:** B.
**Affected areas:** the helper; `tests/test_codework_commit.py`.
**Steps:**
1. Failing tests first for criterion 2, review focus 7 and 10.
2. `--expected-head none` (Choice 6): verify the branch is unborn, stage with `git add`, commit, and check
   the result as in B. The check "the index is as before" is taken against an empty tree.
3. Read `.workbench/code-work.json` with `safefs` and `jsonstrict` (duplicate keys refused, bounded),
   `format` 1, one key. Apply Choice 4.
4. A merge, rebase, cherry-pick or revert in progress refuses (the `MERGE_HEAD`, `rebase-merge`,
   `rebase-apply`, `CHERRY_PICK_HEAD` and `REVERT_HEAD` entries of the git directory).
**Verification:** the new tests; the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-22-code-work-commit#C`.

### Increment D — `remove`

**Outcome:** `remove` previews and removes exact paths.
**Dependencies:** A.
**Affected areas:** the helper; `tests/test_codework_remove.py` (new).
**Steps:**
1. Failing tests first for criterion 6 and review focus 8.
2. Port `removal_targets`, the Git-metadata and nested-repository checks and `remove_paths`, replacing
   `Path.resolve()` with descriptor-relative walking (in the helper, Choice 1). During the walk (not between
   preview and confirm, which is criterion 6), a nested repository found, a `.git` entry that appears after
   validation, and an entry whose type changed since it was listed stop the walk with a partial report, and
   the walk is re-checked per directory: every parent is opened without following links, the
   target is `lstat`ed, a directory is walked with `os.scandir(fd)` and removed bottom-up with `unlink`
   and `rmdir` relative to its parent descriptor; nothing is followed. `--confirm` re-validates before it
   removes, and a target that changed between preview and removal refuses.
**Verification:** the new tests; mutation checks on the nested-repository, link and Git-metadata
refusals; the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-22-code-work-commit#D`.

### Increment E — Wiring through the module and the launcher

**Outcome:** `wb run code-work commit` and `remove` work in an installed project, with the pin made by
the installer.
**Dependencies:** B, C, D.
**Affected areas:** `module.json` (`arguments`), the helper's usage and `main`, the README for
`docs/plans/`, the policy block, `test_codework_module.py`.
**Steps:**
1. Failing end-to-end tests first: install the three modules with real git in the temporary project,
   `wb run code-work commit` makes a commit through the launcher, the first commit works, an edited
   helper is refused, and an upgrade of the module changes the declaration and moves the pin (the
   installer-made pin follows the new `arguments`).
2. Add `commit` and `remove` to the command's `arguments`; the helper's `main` dispatches by the first
   argument and passes the rest, and the read-only subcommands still take none.
3. The policy block and the README say a commit is made through the helper and carries no attribution
   by default, in behavior terms; a test pins the text.
**Verification:** the new tests; the full suite.
**Evidence:** commit with trailer `Plan: 2026-10-22-code-work-commit#E`.

### Increment F — Security pass and release

**Outcome:** the package is first-party again and the helper has been attacked.
**Dependencies:** A to E.
**Affected areas:** `workbench/shipped_approvals/`, tests.
**Steps:**
1. An adversarial `security-reviewer` pass over the whole of the helper's new code with every case of
   Review focus; fix, add a regression test for each, and have a second reviewer try to bypass each
   fix. It must also try `wb run code-work commit` from a repository whose `.git/config` includes a file
   outside the repository, and an agent that sets `--expected-head none` on a repository that has commits.
2. Ask the owner to run `release-approvals`, which makes the shipped approvals again. I run it only if
   the owner says "Run it for me", and remove the stale records only after a preview and the owner's
   approval.
**Verification:** the full suite, with the previously skipped module tests running.
**Evidence:** commit with trailer `Plan: 2026-10-22-code-work-commit#F`.

### Increment G — Documentation and decisions

**Outcome:** the specs, the guide, the roadmap and the decision record match what was built.
**Dependencies:** A to F.
**Affected areas:** `docs/specs/code-work.md`, `trust-and-approval.md` (the line that says the owner's
change through the commit helper updates the baseline), `docs/development.md`,
`docs/roadmaps/workbench-v1.md` (the outcome of `code-work-commit`), `AGENTS.md` (the Bootstrap gap),
`docs/decisions/` (one record, `Proposed`).
**Steps:**
1. Edit the documents; record every limit found. Remove the Bootstrap paragraph about the first commit.
   State that the read-only subcommands run no program and that `commit` and `remove` run only `git`.
2. Write `docs/decisions/2026-10-22-commit-helper-leaves-baselines-to-the-owner.md` (Choice 2, with the
   alternative of writing baselines and the attack it would allow) and mention the git runner's rules.
**Verification:** `git diff --check`; every claim matched to a test or a run.
**Evidence:** commit with trailer `Plan: 2026-10-22-code-work-commit#G`.

## Verification for the plan as a whole

- Full suite with `-W error` after every increment, recorded in the Result.
- Review of each increment before its commit. The process in `code-work.md` makes review mandatory and lets
  the owner be the reviewer when no provider is installed ("Review"); `code-work-approval` has not built
  the gate. Until it does, the owner asks for the review in session (a read-only `workflow-reviewer`, or a
  `security-reviewer` for A to D), and the Result of each increment records the verdict, or that the
  owner committed without a review. Increments A to D handle untrusted input, so the plan asks for the
  security reviewer there. A review of the whole plan follows the last increment.
- The security pass in increment F.
- A recorded hand run: in a scratch repository, make the first commit and a second through
  `wb run code-work commit`, then `remove` a file and a directory, and edit the helper to see the
  launch refuse. Needs the owner's allowance.

## Risks and sensitive actions

- **A helper that changes a repository, run by an agent.** The launcher is a pin check and not a sandbox.
  A flaw in `commit` can write the owner's history; one in `remove` can delete the owner's files. The
  security pass is mandatory and runs before the release.
- **Git runs repository-controlled programs unless stopped.** The refusal is by shape of configuration
  key and by the presence of hooks, which can miss a key a later Git adds. The environment allowlist and
  the subcommand allowlist limit the damage; the residual risk is recorded in the decision.
- **The approver and permission rules in `~/.claude` match `claude-workflow`, not `wb run code-work`.**
  Until `global-config-migration`, the owner keeps using the old helper for the project's own commits.
- **The kit coupling.** The command now depends on kit API 1: a kit change that raises the number needs this
  declaration updated and approved again, as for `groundwork` (`2026-10-21-module-code-lives-in-modules`).
- **Two readers of one rule.** The attribution patterns exist in the old helper and here. They can drift;
  a test pins the patterns, and the owner's global instruction does not depend on the helper.
- **The package tree hash changes**, so first-party approvals are stale between A and F.
- Actions that need the owner: `release-approvals`, any `approve`, accepting the decision, and the hand
  run.

## Review record

Round 1 of 3, 2026-10-22, requested by the owner: Codex (`gpt-5.6-luna`, medium effort, read-only).
Outcome `changes_needed`: three major findings, each evaluated as a review comment and accepted in part.
- **R1-F1 (the plan depends on the owner's untracked helper):** accepted. The contract is now written into
  the plan (attribution patterns and normalisation, the configuration-key shapes, the path rules, the
  staging semantics), with the private script cited by description, date and sha256 and not by path.
- **R1-F2 (the expected-HEAD check is not atomic):** accepted in part. Git cannot make `commit` with an
  index atomic without a temporary index, so the plan states Choice 7: the HEAD is compared three times,
  the commit's parent is checked afterwards, and a moved HEAD is reported as a failure naming the parent
  and undoes nothing. Atomicity is not claimed.
- **R1-F3 (a swap during the removal walk):** accepted in part. The guarantee is confinement to the validated
  subtrees and no followed link, not that each removed entry is the one previewed (two runs share no
  inode); the walk is per-directory descriptor-relative, stops with a partial report, and has swap tests.
Round 2 of 3, 2026-10-22, same reviewer and effort. Outcome `changes_needed`: three major findings.
- **R2-F1 (the plan forbids and requires a reset):** accepted. The non-goal now allows exactly the unstage of the
  named paths before the commit while HEAD is the expected one, and criterion 7 says so.
- **R2-F2 (two race policies for `remove`):** accepted. The criterion and Increment D now separate the two
  cases: a target replaced between the preview and the confirmation is revalidated from scratch and removed
  only if it passes; an entry that changes during the walk stops the walk.
- **R2-F3 (review is not a mandatory step):** accepted in part. The process makes review mandatory and lets the
  owner review when no provider is installed; the gate is `code-work-approval`'s. The plan now states that
  each increment is reviewed before its commit at the owner's request and that the Result records the
  verdict or the owner's choice to commit without one. It does not make the helper or the plan enforce it.
Before the commit the author re-read the plan for contradictions and fixed five wording points: the term "old helper"
defined, the environment rule in criterion 4 matched to increment A, the list of settings that are refused
versus made unreachable, the editor and pager variables the helper sets, and the nested-repository refusal in
increment B. No choice changed. Round 3 of the bound is unused.
The review did not approve the plan. The owner approved it in session on 2026-10-22, with the eight choices
in "Decided by me" as written.

## Deferred work

- `amend-message`, if the owner wants it in a project helper.
- Writing baselines for paths outside the first tier, when such paths have baselines.
- Carrying the approver and permission rules into the modules (`global-config-migration`).
- Plan approval, the delegation helper, review, caps and push (`code-work-approval`).

## Result

Not started.

# The code-work module: the commit helper

Status: Completed
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
The owner closed the review with `ask-codex archive` on 2026-10-22 (16:51 UTC) after the plan was completed:
2 of 3 rounds used, outcome "not converged" (three major findings in the last round, all accepted in part
above), 6 decisions applied, none rejected.

## Deferred work

- `amend-message`, if the owner wants it in a project helper.
- Writing baselines for paths outside the first tier, when such paths have baselines.
- Carrying the approver and permission rules into the modules (`global-config-migration`).
- Plan approval, the delegation helper, review, caps and push (`code-work-approval`).
- Keeping the attribution setting in the owner's config outside the repository, so an agent cannot write it
  (`global-config-migration`).

## Result

### Increment A — the git runner and the repository checks (2026-10-22)

The helper can run `git` safely and refuses a repository that selects programs. No subcommand uses it yet.

- **The command moved onto the kit** (`module.json`: `runtime: python`, `kit: 1`); the helper imports
  `wbkit.display` and nothing else new. A module test pins that the installer's pin records kit 1 and that
  `wb run` refuses a pin without it. The read-only subcommands are unchanged and still run no program.
- **The runner** (below the line `# --- running git ---` in the helper): `trusted_path_entries`,
  `trusted_which`, `git_environment`, `run`, `git_root`, `head`, `names`, `git_bool_is_true` and
  `repo_program_findings`, ported from the contract. `run` takes only the shapes in `git_shape_ok`, one per
  subcommand of criterion 7 (`rev-parse`, `diff`, `ls-files`, `add`, `commit`, `reset`, `show`, `diff-tree`,
  `config`, `status`); a global option before the subcommand, an unlisted subcommand, and the wrong shape of a
  listed one (a `commit` with `--amend`, a `reset` that is not `-q -- <paths>`, an `add` with no `--`, a
  `diff --ext-diff`) are refused before any program starts.
- **Tests:** `test_codework_git.py` (35, against real git) and `support_git.py` (real repositories, a
  recording `git`). Mutation checks: with the inside-the-repository PATH test, the `GIT_` scrub, the shape of
  `reset`, the hooks scan, the link refusal, the allowlist or the global-configuration exclusion removed, a
  named test fails each time. Existing tests changed: the helper is loaded through `support_helpers` (the kit
  must be importable), the import check allows `wbkit` and `subprocess`, the no-program text scan covers
  only the part above the line, and the lookalike-module test runs the helper through the runner. Full suite:
  2458 tests in 4 roots, passing with `-W error` (the 11 `claude` tests that need the shipped approvals are
  skipped: they are stale until increment F).
- **Departures from the plan's text, for the owner:**
  1. A repository whose `.git` is a file or a link is refused. The old helper allowed a `.git` file (a linked
     worktree or a submodule); here that is the redirect an attacker would write, so a linked worktree cannot
     be committed to through the helper until the owner says otherwise.
  2. The shapes are stricter than the plan's list of subcommands: each is allowed in one argument shape, and
     `GIT_LITERAL_PATHSPECS=1` is set for every run and not only for `commit`.
  3. `rev-parse --verify -q refs/heads/<name>` and `rev-parse HEAD^@` are allowed for the unborn-branch and
     parent checks of increments B and C; no `symbolic-ref` is needed.
- **Known limits, for the security pass:** git's output is read whole into memory, with no size bound (only a
  timeout of 120 seconds); a repository whose configuration names a program by a key the shape does not
  match is not found; `HOME` and `XDG_CONFIG_HOME` of the caller choose the global configuration that is
  trusted.
- **Review (security-reviewer, two rounds, 2026-10-22; round 1 found one High and two Low, round 2 found no
  bypass).** The reviewer ran real git against real repositories.
  - **High, fixed (F1):** a committed gitlink whose nested repository sets `core.fsmonitor` made `diff`,
    `status` and `commit` start that program, and `repo_program_findings` read only the top repository.
    It now lists the index and reports `submodule:<path>` for any mode-160000 entry (any stage, flagged or
    not; at most 5 names), so a commit is refused. A test shows the nested program does run when the
    finding is ignored, and that an untracked nested repository runs nothing and is not a finding.
  - **Low, fixed (F2):** the PATH boundary was the nearest `.git` ancestor, so an embedded repository made
    the outer one look outside. `run` now uses `outermost_boundary`; `git_root` keeps the nearest for its
    own check.
  - **Low, fixed (F3):** `diff` with two absolute paths switched git to `--no-index` and read outside the
    repository; every path-taking shape now rejects an empty, absolute or `..`-component path
    (`_paths_ok`), and the refusal message is truncated. Increment B's `validate_paths` still has to reject
    `.` (the whole tree), which the shape accepts.
  - **Mutation checks:** removing the gitlink scan, the outermost boundary, the path check or the message
    bound fails a named test each time.
  - **Recorded as limits:** (1) the gitlink check reads the index only, so one that exists in `HEAD` but not
    in the index is not seen; (2) an ancestor `.git` (a dotfiles repository in `$HOME`) makes every PATH
    entry under it untrusted, which fails closed; (3) a repository may select the owner's own programs by
    attributes (`filter=lfs`, `diff=pdf`) that the trusted global configuration defines (informational);
    (4) a gitlink added by a concurrent writer after the check is outside the threat model (Choice 7);
    (5) git's output is unbounded in memory; (6) `git_environment` does not set `GIT_CONFIG_GLOBAL` or
    `GIT_CONFIG_NOSYSTEM` for ordinary runs, unlike the plan's wording, because the owner's global
    configuration supplies the commit identity; only the configuration scan excludes it.
  - **Not covered:** the unit tests of the fixes, TOCTOU between the PATH search and the start, and the
    bind-mount and case-folding PATH cases beyond `samefile`.

### Increment B — `commit` (2026-10-22)

`code-work commit` makes one local commit of exactly the named files in a repository that has commits. The
module's `arguments` do not list it yet, so `wb run` does not pass it (increment E); the helper's `main`
dispatches it.

- **Code** (below `# --- commit ---` in the helper): `parse_commit` (hand-parsed: unknown option, repeated
  singleton, missing value, missing `--`, more than 2000 paths refuse), `validate_message`,
  `refuse_attribution` (the contract's patterns, after NFKC, `Cf` removal, case folding, the confusable
  table and folded-line joining; subject, body, each trailer and the whole), `validate_paths` (built on
  `wbkit.safefs.validate_relpath` and `Root.list_dir`: no link at any component, no directory, no
  nested repository, no glob or leading `-`, no duplicate or case-colliding pair, a missing path must be
  tracked, a path in a merge state is refused), `command_commit` and `verify_commit`.
- **Flow:** repository checks (A), HEAD against the expected hash before anything, before staging, after
  staging and just before the commit; the staged set must equal the named set plus what was staged
  before; `diff --check` before and after staging; `commit -m` per paragraph (`--only -- <paths>` with
  `--leave-other-staged`). Afterwards: the only parent is the expected hash, the message is the one asked
  for (as git cleans it), the commit holds exactly the named paths, and the rest of the index is as it was.
  A failure before the commit runs `reset -q -- <named paths>` only while HEAD is the expected one; a
  failure after it says `nothing was undone`.
- **Departures and additions, for the owner:**
  1. `--no-renames` joins the allowed `diff` flags and is used for the staged-set comparison. Without it, a
     delete plus an add that git reads as a rename never matched the named set (the likely reason the old
     helper refused such a commit).
  2. `validate_relpath` is stricter than the contract: it also refuses `:` and a backslash anywhere, a
     non-printable character (a tab, a newline) and a path over 512 characters.
  3. `--expected-head none` is refused until increment C; `-m` text that git would clean (trailing space,
     runs of blank lines) is compared after the same cleaning, not byte for byte.
  4. A moved HEAD is detected, not prevented (Choice 7): the test makes a `git` that moves HEAD just before
     the commit runs and the result is exit 1 naming the commit.
- **Tests:** `test_codework_commit.py` (46, real git; a `git` that moves HEAD at a chosen call; a recording
  `git` showing only the allowed subcommands on success and failure and one `reset -q -- a.txt`; hostile
  `GIT_*` variables not reaching git). Mutation checks: removing the first, third or parent HEAD check, the
  staged-set comparison, the link refusal, the unstage, the already-staged and non-empty-index refusals, the
  program scan, the attribution check or the nested-repository check fails a named test each time. Full
  suite: 2514 tests in 4 roots, passing with `-W error` (the 11 `claude` tests that need the shipped
  approvals are still skipped until F).
- **Not covered:** a file changed between `add` and `commit` (the commit takes the index as staged);
  skip-worktree, assume-unchanged and sparse-checkout paths; a security review (asked for separately).
- **Review (security-reviewer, round 1, 2026-10-22): no Critical or High; two Medium, three Low, one
  informational. All fixed except L3, with tests and mutation checks.**
  - **M1, fixed:** a merge in progress made the commit a two-parent merge before the post-check could report
    it. `refuse_operation_in_progress` now refuses before anything is staged when the git directory holds
    `MERGE_HEAD`, `REVERT_HEAD`, `CHERRY_PICK_HEAD`, `rebase-merge` or `rebase-apply` (this takes over the
    part of increment C that named those states).
  - **M2, fixed:** the attribution check read a few spellings the contract's patterns missed (non-hyphen
    dashes, runs of blanks or a newline between the words, punctuation before the name, combining and filler
    characters, more look-alike letters, other verbs, `Claude-Session:`, `noreply+x@anthropic.com`). The
    text is now folded further (every dash a hyphen, blanks collapsed, accents dropped) and the message is
    refused outright when it holds a combining mark no precomposed letter has or a word that mixes
    scripts. The patterns gained `drafted`, `powered`, `using`, `via`, `AI-assisted (Claude)`,
    `claude-session:` and `noreply…@anthropic.com`. This is broader than the contract and can refuse a
    message that only mentions a tool next to a verb ("written by Claude"); it is a guard against a mistake,
    not a boundary. A bare `claude.ai` is still allowed.
  - **L1, fixed:** the `co-authored-by:` patterns scanned to the end of the line from every occurrence
    (20 s for 100,000 characters); the gap is now bounded at 200 characters.
  - **L2, fixed:** a tracked name present on disk under another Unicode spelling (a link in NFD where the
    index holds NFC) skipped the link check. An absent-but-tracked path is now `lstat`ed and must be a plain
    file or nothing.
  - **L3, accepted and recorded:** a repository can select the owner's own global filter by attributes
    (limit 3 of increment A). Nothing in the repository's configuration runs.
  - **Informational, fixed:** `commit.cleanup=strip` in the repository dropped `#` lines and the
    post-check reported a failure after the commit. The helper now passes `--cleanup=whitespace`.
- **Review, round 2 (a bypass attempt on the fixes, 2026-10-22):** no way to give a commit a foreign parent
  and none to read outside the repository; a regex-cost stress of 28 inputs of 80 to 100 KB ran in 0.2 s or
  less; `_commit_shape` accepted nothing it should not. Findings, all fixed except as noted:
  - **Medium, fixed:** the attribution check still passed control characters, private-use and unassigned
    characters, U+2800 and U+1680 inside the name, Latin look-alikes the table lacked (`ɑ`, `ᴄ`, `ł`, `ƚ`),
    `Co-developed-by:`, `Signed-off-by:`, `Built with`, `Claude wrote`, `Claude Session:` and a session URL
    with a query, a port or an unlisted path (and a `。` for the dot). The message is now refused outright
    when it holds a control character other than newline or tab, a private-use or unassigned character,
    U+2800 or U+1680; the table and the patterns gained the rest; any `claude.ai` or `claude.com` followed by
    `/`, `:` or `?` and a character is attribution, a bare host is not.
  - **Low, fixed:** the mixed-script refusal rejected Japanese, Korean and Latin with Japanese
    (`APIを修正`) and a micro sign (`µs`). Han, Kana, Hangul and Bopomofo are one script now, and the test is
    Latin mixed with Cyrillic, Greek, Armenian, Coptic or Cherokee only.
  - **Low, fixed:** `sequencer` joins the states `refuse_operation_in_progress` refuses. A bisect in progress
    is not refused (it does not change the commit's parent).
  - **Recorded as limits:** the attribution filter is best-effort against an agent that deliberately
    obfuscates, not a boundary; a message in a script that uses combining marks (Hindi) is refused rather
    than read; a path through a case-variant or NFC-versus-NFD directory link passes the helper's own check
    and is stopped by `git add` ("beyond a symbolic link"), after which the paths are unstaged; case
    variants were tried on case-insensitive APFS only.

### Increment C — the first commit and the attribution setting (2026-10-22)

`code-work commit` now makes the first commit of a branch and reads the attribution setting. The module's
`arguments` still do not list `commit` (increment E).

- **`--expected-head none`:** `validate_expected` returns `None` for it. `tip` resolves HEAD with
  `rev-parse --verify HEAD`; when that fails, HEAD must be the plain text `ref: refs/heads/<name>` (read
  with `O_NOFOLLOW`, the name passing `_branch_ref`, so ASCII letters, digits and `. _ - /`), no loose file
  may hold that ref, and `rev-parse --verify -q <ref>` must exit 1 with no output. Anything else is refused,
  never taken for an unborn branch. Every HEAD check compares against `None` the same way; the
  after-commit check requires no parent and lists the commit with `diff-tree --root`. `reset -q --`
  unstages on an unborn branch too. No new git subcommand or shape.
- **Attribution setting:** `attribution_allowed` reads `.workbench/code-work.json` at the repository root
  with `safefs.read_if_present` (no link at any component, regular file, one hard link, 4096 bytes) and
  `jsonstrict.parse_object`. It must be exactly `{"format": 1, "attribution": "refuse"|"allow"}`; absent
  means refuse; anything else, a link, a directory, a pipe or a file in the way stops every commit with a
  reason. With `allow` the attribution check, including its refusal of odd characters, is skipped; every
  other check stays. The check now runs after the repository is found.
- **A fix found on the way:** git on macOS precomposes its arguments, so a message in decomposed form was
  stored in composed form and the after-commit message check reported a failure for a good commit. Both
  sides are compared in canonical (NFC) form. This was unreachable before, because the attribution check
  refused such messages.
- **Review focus 7 tested at commit level:** detached HEAD and a shallow clone commit normally; a linked
  work tree (`.git` is a file) is refused; assume-unchanged, skip-worktree and out-of-cone sparse paths are
  refused with nothing changed.
- **Tests:** 40 added to `test_codework_commit.py` (86 in all): the unborn flow (first commit, other
  staged work kept, a hash refused, `none` refused where a commit exists, odd and unreadable HEADs, a
  dangling and a packed ref, a non-ASCII branch, a moved HEAD at three points, a failed commit unstaged, the
  recording `git`), the odd states, and the setting (absent, refuse, allow, 24 malformed files, a link, a
  directory, a hard link, a pipe, a linked `.workbench`, the root versus the current directory). Full suite:
  2556 tests in 4 roots, passing with `-W error` (the 11 `claude` tests that need the shipped approvals are
  still skipped until F).
- **Mutation checks, each failing a named test:** treating every unreadable HEAD as unborn, the HEAD-file
  shape, the loose-ref check, the `diff-tree --root` flag, the parent comparison, allow ignored, absent
  read as allow, the format, key-set and value checks, the size limit, the read-error handler, the
  attribution-before-setting order, the NFC comparison.
- **Surviving mutants, recorded:** the `O_NOFOLLOW` open of HEAD and the quiet-exit test of
  `rev-parse --verify -q` are not pinned by a test, because git itself rejects the cases they guard (a HEAD
  link outside `.git`; a ref to a missing object, where `git commit` fails and the paths are unstaged).
  They stay as defence in depth.
- **Limits for the owner:** the setting is read from the work tree, so a process that can write there can
  switch it to `allow` before committing; it stops a mistake and is not a boundary, and a pulled edit shows
  in `wb acknowledge`. A legitimate unborn branch with a non-ASCII name is refused, with the reason. No
  security review of C has been asked for yet.
- **Review (security-reviewer, 2026-10-22): no Critical or High; one Medium for the owner, one Low fixed.** It
  found no way to get `none` accepted where the branch has a commit (a packed ref, a dangling ref, a
  directory at the ref, CRLF, an extra line and a link at HEAD were each tested), and no wrong-parent,
  wrong-path or wrong-message success; `--leave-other-staged` with `--only` on an initial commit commits
  only the named path; the setting file's duplicate keys by escape, `1.0`, `1e0`, a BOM, 4 KiB and larger,
  a linked `.workbench` or file, a hard link and a pipe were each refused with no read outside the
  repository.
  - **Low, fixed:** `_branch_ref` let through a branch name git rejects (`.x`, `a/.b`, `a.lock/b`): the
    helper staged, `git commit` failed, and the paths stayed staged because the unstage could not resolve
    HEAD. A name with a component that starts with `.` or ends with `.lock`, or holds `@{`, is now not a
    branch name for the helper. A regression test and a mutation check cover it.
  - **Medium, for the owner (not changed):** `attribution: allow` is read from the work tree, so a process
    that can write the file (an untracked file is enough) can turn the filter off and commit with
    attribution. This is the limit recorded above; Choice 4 approved reading the file with `safefs`. The
    reviewer's smallest fix is to take the setting from HEAD (`allow` counts only when the file is tracked
    and the work tree and index copies equal HEAD), which means the owner commits the setting, or to keep
    it in the owner's config outside the repository. Either changes Choice 4, so it waits for the owner.
    **Owner's decision (2026-10-22): keep Choice 4 as approved.** The filter is best-effort and not a
    boundary, so the file read from the work tree adds no way that an agent does not already have. A real
    boundary would be a setting in the owner's config outside the repository; that belongs to
    `global-config-migration` and is noted under Deferred work.

### Increment D — `remove` (2026-10-22)

`code-work remove [--recursive] [--confirm] -- <path>...` previews and removes exact paths. The module's
`arguments` still do not list it (increment E). No new git subcommand or shape: the only git run is
`rev-parse` through `git_root`, so a repository that selects a program (`core.fsmonitor`) may still have files
removed, and the test shows the program does not run.

- **Validation, from scratch on every run** (preview and `--confirm` share it): `safefs.validate_relpath`
  (so no empty, `.`, `..`, absolute, backslash, colon or non-printable name), no glob character, no leading
  `-`, no part spelled like Git metadata (`.git` in any case, with trailing dots or spaces, with invisible
  characters or compatibility forms, `git~N`), no overlap (compared by NFC and case-folded parts, either
  direction), every parent opened relative to the one before with `O_NOFOLLOW` on the repository's
  filesystem and not inside a nested repository, the target examined with `lstat`. A directory needs
  `--recursive` (a file does not mind it), may not be the repository root by identity or another filesystem,
  and its tree is scanned without following anything: a `.git` entry of any kind or spelling, a bare or
  separate git directory (HEAD, objects, refs), another filesystem, more than `MAX_REMOVE_ENTRIES` entries in
  all or in one directory, or more than `MAX_REMOVE_DEPTH` levels refuses everything.
- **The walk:** each target's parents are opened again; each entry is `lstat`ed, compared by type with how it
  was listed, and deleted with `unlink` or `rmdir` relative to its own parent's descriptor; a directory is
  opened with `O_NOFOLLOW`, compared by device and inode with the listing, listed, checked again for
  repository metadata and emptied bottom-up. A swap for a link removes the link or stops; a swap for a
  directory is refused by `unlink`; a new `.git` or any new entry makes `rmdir` fail and stops the walk,
  saying which. A stop prints `{"status":"stopped","reason","removed","stopped_in","not_removed"}` on
  standard output, `stopped: <reason>` on standard error and exits 1. Nothing is undone.
- **Output:** a preview is `{"status":"preview","targets":[{"path","kind"[,"entries"]}],"next_action"}`
  and a removal `{"status":"removed","targets":[...]}`; kinds are `file`, `directory`, `symlink`, `other`.
- **My calls, not in the approved choices:** the command line takes `--` before the paths like `commit`
  (the old helper did not); a name with `:` or a backslash cannot be removed (the kit's path rule); the hook
  `HOOK(stage, path)` is a module variable for tests only.
- **Tests:** 54 in `test_codework_remove.py` (real repositories; races use the hook at `entry`, `checked`,
  `listed`, `planning` and `scanning`; the preview-to-confirm swaps are separate runs). Full suite: 2611
  tests in 4 roots, passing with `-W error` (the same 11 `claude` tests skip until F).
- **Mutation checks, each failing a named test (39 variants):** the link-following parent open, the Git-name
  predicate and each of its four normalisations, the ancestor, scan and walk repository checks, the bare
  repository test, overlap (both directions, case, NFC), glob, leading dash, the Git-metadata part check,
  `--recursive`, the root identity, the device check at four places, both depth checks, both entry bounds, the
  type-change check, the walk's no-follow open, the identity checks at three places, links followed by the
  listing, preview that removes, no re-resolve of the parent, a stop that exits 0, validating only the first
  path, and the kit's path rule. Nine first survived (tests used paths that failed for another reason, or
  reached no hook); each got a test and was rerun.
- **Limits:** the confinement is by descriptor, not identity (criterion 6); two hard links to one file are
  two targets; a case-sensitive filesystem with `A` and `a` is treated as one (conservative). No security
  review of D is recorded below.
- **Review (security-reviewer, 2026-10-22): no Critical or High; one Medium and one Low, both fixed.** It
  found no way to delete outside the repository, the repository's own `.git` or the root, or to follow a
  link; unreadable directories at every level, FIFOs, odd and over-long names and a surrogate in an argument
  each fail closed with no escaping exception (tested).
  - **Medium, fixed:** a nested bare git directory whose `objects` or `refs` is a link (or whose `HEAD` is)
    was not recognised, because the test looked at file types, and was deleted. `_holds_repository` now
    needs only the names `HEAD`, `objects` and `refs`, whatever their type, or `HEAD` and `commondir` (a
    linked work tree's git directory). Tests on the target and below it, a test for `commondir`, and
    mutation checks cover it.
  - **Low, fixed:** each target listed and `lstat`ed every ancestor directory, so 2000 targets under a large
    directory took minutes. A directory is now listed once per phase (plan, removal), keyed by device and
    inode; a test counts the listings. The cost is that a `.git` created in an ancestor between two targets
    of the same phase is seen only in the next phase, which does not affect the target's own walk.
  - No second bypass round has been run on these two fixes.

### Increment E — wiring through the module and the launcher (2026-10-22)

- `module.json`: the arguments of `code-work` are now `check`, `plans`, `report`, `commit`, `remove`. The
  helper's `main` already dispatched `commit` and `remove` (increments B to D), so the helper changed only
  in its usage line, which now says `commit` and `remove` take options.
- The policy block gained one rule (a commit goes through the helper, names the commit it expects and the
  exact paths, and carries no attribution unless the project allows it), and the README of `docs/plans/`
  gained a short "Committing an increment" section. Both are in behavior terms and name no tool. The policy
  test that forbade the word "attribution" now forbids the other checkpoint words only, and a new test pins
  the rule's text; the block is 14 lines, at its limit.
- New tests in `test_codework_module.py` (red first, then green), all through `commands.run` in a project
  installed from a released copy: the declaration lists the five arguments; the first commit (`--expected-head
  none`) and a second commit work; a second `none` on a branch with a commit is refused and HEAD is unchanged;
  a message naming a tool is refused and nothing is committed; `remove` previews and then removes; a read
  command given an extra argument and an unlisted name are refused; an edited helper is refused for `commit`;
  an upgrade that adds an argument moves the installer-made pin's declaration and keeps its path and kit.
- Verification: `test_codework_module` and its neighbours (148 tests, OK); the full suite, 2623 tests in
  4 roots, OK.
- Limit: the helper's own standard error is not captured by `commands.run`, so the end-to-end tests assert
  exit codes and repository state for helper refusals; the refusal texts are covered in the helper tests.
- The shipped approvals for `code-work` stay stale until F.

### Increment F — security pass (2026-10-22; the release is not yet run)

Three read-only `security-reviewer` passes covered the git runner and repository checks, `commit`, and
`remove`, with the cases of Review focus, then three more rounds tried to bypass the fixes. All probes ran
in scratch repositories against real git; sentinel files outside the target were checked after each.

Fixed, each with a test that failed before the fix:

- **High.** `repo_program_findings` ran `core.fsmonitor` through its own `git ls-files`. Every run now sets
  `core.fsmonitor=false` through `GIT_CONFIG_COUNT`; an entry whose value is false is not a finding.
- **High.** A partial-clone configuration plus a missing object made `diff` and `commit` run
  `remote.*.uploadpack`. Every run sets `GIT_NO_LAZY_FETCH=1`, and the keys `uploadpack`, `receivepack`,
  `vcs`, `helper`, `promisor`, `partialclone`, `partialclonefilter`, `core.gitproxy` and `core.askpass`
  are findings.
- **High.** Auto-maintenance after a commit ran `gc.recentObjectsHook`. Every run sets `maintenance.auto=false`
  and `gc.auto=0`, and any key ending in `hook` is a finding.
- **High.** A hooks directory without read permission (mode 0311 or 0111) was skipped, though git runs a
  hook it names. It is now the finding `hooks:unreadable`.
- **Low.** `diff` shapes that read contents now require `--no-ext-diff` and `--no-textconv`, unless they only
  list names.
- **Medium.** Attribution evaded the check through look-alike letters: Latin small capitals and IPA letters
  (refused), letters with a stroke, hook or dot and boxed letters (folded to the base letter), a handful of
  single symbols (mapped), and words that mix scripts (refused, with Japanese, Chinese and Korean counted
  as one). The mixed-script rule now applies to every word, not only to words that hold Latin.
- **Low.** `remove` now enforces the entry bound during the delete walk too.

Not fixed, with the reason:

- **The attribution setting is read from the work tree** (decision 4). An agent that can write files can
  set it to `allow` itself, and reading it from `HEAD` only moves that, since the agent can commit the
  change. The guard prevents a mistake; it is not a control against a deliberate agent.
- **A look-alike list cannot be complete.** Visual substitutes of a letter by a digit or a capital I
  (`C1aude`, `CIaude`) and other characters not yet listed can still pass.
- **The caller's `HOME` and `PATH` are trusted** (plan assumption). A `git` in an absolute `PATH` entry
  outside the repository runs, and a `HOME` chosen by the caller selects the global configuration. The
  repository is the untrusted party.
- **An attribute in the repository can select a filter the owner's global configuration defines.**
- **The expected-HEAD guarantee is detection** (decision 7). A file staged by another process between the
  last check and the commit is committed and reported.
- **The check for a nested repository is not repeated per target** under one parent in `remove --confirm`.
  It needs a concurrent writer of the same user and affects only a path named by the owner.
- **Linux bind mounts** share a device number with the filesystem under them, so the mount guard of
  `remove` does not see them. Not reachable on macOS; untested.
- **Settings checked only by reading:** `GIT_CONFIG_COUNT` needs git 2.31 and `GIT_NO_LAZY_FETCH` needs 2.44;
  an older git ignores them and only the findings protect.
- **The last two fixes** (the script-mix rule and `hooks:unreadable`) have not had their own bypass round.
- Messages are not checked for control characters when the project allows attribution.

Verification: the full suite, 2638 tests in 4 roots, OK (13 more than before F plus the later fixes).
The shipped approvals for `code-work` are still stale, and F is not complete until the owner runs
`release-approvals` and the stale records are removed.

### Increment G — documentation and decisions (2026-10-22)

- `docs/specs/code-work.md`: the Commit section now states what `commit` and `remove` take and refuse, that
  the expected-HEAD guarantee is detection, the attribution setting and its limits, the git runner's rules,
  and that the read-only subcommands run no program while `commit` and `remove` run only `git` (this
  restates criterion 5 of `2026-10-21-code-work-plans` for the two that change a repository).
- `docs/specs/trust-and-approval.md`: the line that said a change through the commit helper updates the
  baseline now says it does not, and that `wb acknowledge` lists it.
- `docs/roadmaps/workbench-v1.md`: the outcome of `code-work-commit` no longer promises baseline updates.
- `AGENTS.md`: the Bootstrap paragraph about the first commit is removed.
- `docs/development.md`: two command rows and a section, "The code-work helper", with the recorded limits.
- `docs/decisions/2026-10-22-commit-helper-leaves-baselines-to-the-owner.md`, `Proposed`, and its row in
  the decisions index. Accepting it is the owner's act.
- Not run: the plan check on this repository (`wb run code-work check` needs a workbench project, and this
  repository is not one until `self-hosting`).

### Result of the plan

All seven increments are committed. Criterion 9 holds with one recorded exception the owner accepted:
the last two security fixes (the mixed-script rule and `hooks:unreadable`) had no bypass round of their own.
The specs, the guide, the roadmap and `AGENTS.md` describe what was built, the decision record exists, and
the full suite passed with `-W error` (2638 tests in 4 roots, OK) after increment F.

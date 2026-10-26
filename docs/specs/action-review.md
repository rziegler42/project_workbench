# action-review

Status: Draft. A design for the engine of roadmap candidate `action-review-engine`, written on 2026-10-25 from a
brainstorm in which the owner chose to skip the questions. The owner approved the design as written on 2026-10-25,
after settling the accuracy method, the false-decline bound, the name `describe`, and the fate of `safe-committer`
and `amend-message`. A call marked **(default)** was the author's and is approved with the design but was not
separately chosen; the owner may still change it. The approval is of the design only and approves no plan. The
`describe` interface is a decision record of its own, accepted by the owner on 2026-10-25
(`2026-10-25-describe-interface-for-action-review`). The status stays `Draft` because nothing in this spec is built.

Terms are defined in `terms.md`. The engine sits above the bridge of `model-bridge.md` and beside the engine of
`review-engine.md`. The decision behind it is `2026-10-22-model-calls-go-through-vendor-bridges` (decisions 3, 6, 7
and 8); the authority rules are in `trust-and-approval.md`.

## Purpose and reason

The owner's approver is a program in the user level (item `codex_approver.py` of `global-config-inventory.md`,
role USER). A hook calls it when a command that an `ask` rule prompted for is about to run. It collects facts
about the action, runs fixed checks, asks a model for a verdict against a rubric, logs the verdict and, for two
delegated rules, can allow the command.

It cannot be moved or removed in pieces. Its facts for a commit and a removal come from the global
`claude-workflow` program, loaded as a library (`load_helper`, `collect_commit`, `collect_remove`, read on
2026-10-25, not run). So the program cannot be removed (move M14) without silencing review of every commit, and
the module spellings were added only by a narrow patch that keeps that dependence (accepted option 1a of
`2026-10-25-approver-coverage-for-the-module-commands`). Decision 7 of the vendor-bridges record says facts come
from the module that owns the action and leaves the interface open until this engine is planned. This spec
proposes that interface and the engine around it.

## Goals

1. An engine, `action-review`, that takes facts about one action and returns a verdict with reasons as data,
   from a rubric, fixed checks and rules, calling a model only through a `model-bridge`.
2. A `describe` interface by which the module that owns an action reports the facts, read-only, before the action is
   made. No second copy of the owner's inspection code.
3. The approver's program can be replaced by a thin hook that asks the engine, so M1 stage 2 and M14 can happen
   and the global `claude-workflow` program can go.
4. The review is accurate against the owner's own judgment, not against the approver's verdicts. The owner reports
   that the approver gave many false declines (commands the owner would approve), so agreeing with it is not the
   target. Both errors are counted: a false decline (a safe action stopped) and a false approve (an unsafe action
   let through). A false approve is the worse one. Every kind of command the approver reviews is still reviewed.

## Non-goals and anti-goals

- The engine writes no `allow` rule, no setting and no hook entry, and its verdict authorizes nothing by itself
  (decision 6). A verdict that is missing, malformed, unavailable, timed out or not a verdict approves nothing.
- It is not a reviewer of documents (that is `review-engine`), and it names no vendor.
- It does not move the enforcement point. The hook stays in the owner's own configuration, outside a project's
  reach (`2026-10-24-project-guarantees-a-floor`). The agent does not write the user level.
- It does not widen delegation. Which actions a verdict may stand in for is the owner's personal setting and a
  code constant of the enforcement point, as `DELEGABLE` is today.
- Anti-goals: an engine that approves more than the approver does; a `describe` command that changes anything; facts
  trusted as instructions; a typo in a rule file that silently turns the review off for every command (the
  approver does this today, measured on 2026-10-25).

## The design

### The `describe` interface (default)

A module that owns an action ships a read-only subcommand `describe` beside the action. `wb run safe-git describe
commit <the arguments of commit>` takes exactly the arguments of the real command and prints one JSON object of
the facts that the real command would act on, running the same validation code the real command runs. It makes no
commit, stages nothing, writes nothing and runs no program the repository selects. `describe remove` does the same for
`remove`, extending the `remove` preview it has. `push-check` already has this shape for a push.

- The object has `contract` (a whole number), `action` (`commit`), `ok`, `truncated` (always present, a boolean),
  `errors` (the refusals the real command would give, as data, not as a failed run) and `facts` (a flat set of named
  values with a size cap). A module documents the names of its facts and its numeric caps in its own spec, and the
  engine's rules name them. A truncated object is incomplete and the verdict is a decline. The field rules and the
  behaviour at the cap are fixed by the accepted decision `2026-10-25-describe-interface-for-action-review`.
- A refusal is a fact: a commit the real helper would refuse is reported as `ok: false` with the reason, and the
  engine's check for it fails the verdict.
- The engine runs `describe` only through the launcher (`wb run`), the same rule decision 4 sets for bridges, and
  only for a command that an installed, pinned module declares as a `describe` provider. Its output is data.
- **Why this shape (default):** the real validation lives in one place and cannot drift; the call is free of side
  effects by construction; it needs no new capability of the launcher beyond running a pinned command. The
  alternative of a `--preview` flag on the action itself was rejected as default because a mistaken flag would run
  the action.

### The engine (default)

A module `action-review` providing the capability of that name (still a proposal), requiring `model-bridge`. One
command, `wb run action-review review`, takes the line of the command to be reviewed and, by that line, finds the
rule, runs the module's `describe`, applies the rule's checks, and only if the checks pass asks the bridge for a
verdict against the rubric. It prints one verdict object: `verdict` (`approve` or `decline`), `failed_checks` and
`reason`, the shape of today's verdict schema. It keeps a log of verdicts as hashes, not command text.

- **Rule properties fixed here; the schema is the first deliverable of the engine's plan.** A rule file has a
  `format` number, and a rule is keyed by one spelling and one subcommand, matched on whole tokens (never a text
  prefix). Two rules with the same key are both refused, and neither reviews anything. A rule that does not load, or
  is ambiguous, refuses only the commands of its own key. Each flag it declares has a type (value, multi, boolean),
  and positionals are declared as exactly one named group. The versioned JSON schema, its field types and bounds, the
  precedence rule and the tests for malformed and overlapping rules are written by the plan that builds the engine,
  before the engine, and reviewed with it.
- **Rules are data** (a JSON file per rule: the command spelling, the module and the action that `describe`
  reports on, the checks, the rubric section, the review questions). The module and the action are identifiers
  only: a rule holds no command text and no verb. The engine builds the launcher argument list itself, `wb run
  <module> describe <action> <the parsed arguments>`, with the fixed word `describe`. A rule format that can carry
  command text, an extra verb or a path to run is rejected, and a rule that names such a field does not load. **The checks are code in the module** and are fixed: a pure function of the facts.
  A rule can only name a check that exists. This keeps the owner's finding that a rule file is not a place to put
  logic.
- **Fail closed, and loudly.** A rule file that does not load makes `review` refuse that rule with a message the
  hook can show. It never disables the review of other commands. This is a change from the approver.
- **The prompt holds the facts and the rubric; the vendor can still read the project.** Content from a hostile
  repository (a diff, a message) is quoted as data and the rubric keeps the check that refuses text addressed to the
  reviewer (`no_reviewer_directed_text`). That is not an isolation boundary. The bridge starts the vendor program in
  the project, and `model-bridge.md` ("What the vendor program can read") says it can open any file there, including
  untracked scratch and the repository's own instruction files, so repository text can reach the model by that
  route as well. The spec therefore claims only this: the engine puts nothing sensitive in the project for the
  vendor to find (the labelled set is stored outside any project, see below), and it does not rely on the model
  ignoring what it reads. A bridge option for a scratch root with no project content would be a change to
  `model-bridge.md`, which the engine's plan may propose; none exists today.

### The reviewed command is the command that runs (default)

A review is useless if it examines something other than what executes. The engine takes the prompted command as the
raw text the harness is about to run, and as one canonical form from the hook to `describe`:

- **Accepted grammar (a restricted subset, so that every shell reads it alike).** The text is a sequence of words
  separated by exactly one space each, with no leading or trailing space. A word is either a bare word made only of
  `A-Z a-z 0-9 . _ / : = @ % + , -` (not beginning with `-` unless it is a flag the rule declares), or a single-quoted
  string: `'`, any characters except `'` and newline, `'`. Nothing else is accepted: no double quote, backslash,
  `$`, backtick, `*`, `?`, `[`, `~`, `{`, `#`, `;`, `&`, `|`, `<`, `>`, `(`, `)`, newline or tab outside a
  single-quoted string, and no environment prefix. Inside single quotes every character is literal in POSIX shells
  and in zsh, so the word means the same to all of them. A command that does not fit is unreviewable and approves
  nothing; the owner then sees the normal prompt. A commit message that needs a single quote is written without one
  or in a body file the helper takes, which the plan of `describe` may add.
- **The corpus is a test of a stated grammar.** The grammar above is exact, so the equivalence test is a property
  test over generated command text and not a sample: every accepted text parses to the same argument list in the
  engine and in `sh` and `zsh`, and every other text is refused.
- **One parse.** The rule's declared flags parse the arguments once. The result is an argument list, never a shell
  string, and `describe` receives that list through the launcher, with the fixed verb `describe`, so the facts are of
  the arguments the real command will receive.
- **Unknown means unreviewed.** A flag the rule does not declare, a repeated single-valued flag and a missing
  required flag refuse the review.
- **Tested.** A corpus of quoting, spacing, wrapper and shell-metacharacter forms shows that the argument list the
  engine reviews equals the argument list the real command parses from the same text, or that the review is refused.

### Settings and the bridge (default)

Decision 5 of `2026-10-22-model-calls-go-through-vendor-bridges` applies unchanged. The engine reads its own project
file, `.workbench/action-review.json`: a format number and the bridge, the model and the effort the project would
like. It is a request and never an authorization.

- The bridge must be an installed, pinned module that provides `model-bridge`. A name that is not is refused and no
  other vendor is tried.
- The owner's personal setting is authoritative: it may choose among the installed bridges and lower the effort, and
  where it and the project disagree the personal setting is used. A teammate with none gets the project's bridge if
  it is installed and approved, and otherwise a refusal.
- A pulled change to the file is a difference `wb acknowledge` lists, and at run time the file is accepted only if it
  names a bridge the owner already approved by installing it.
- The timeout the engine passes to the bridge is shorter than its own limit, as `model-bridge.md` requires.
- A missing or unreadable setting, or a bridge failure of any class, yields no approval.

### The enforcement point (default)

The owner's hook becomes a thin program: match the prompted command to a spelling, run `wb run action-review
review`, and turn the verdict into the hook's answer. What the hook allows without the owner (`DELEGABLE`, the
mode setting) stays a code constant there. The hook is the owner's to write and install; the agent prepares and
tests it on a scratch copy, as it did for the patch of option 1a.

### Accuracy and cutover (default)

The approver is not the standard, because the owner finds it wrongly declines. So the engine is judged against a
labelled set, not against the approver.

1. **Find where the approver goes wrong.** Its verdict log holds the rule, the verdict, the failed checks and a
   command hash, never command text. Counting declines by failed check shows which checks cause them. This needs
   no new data and is read-only. Plan 1 does it first, so that the engine is not built to repeat those checks.
2. **Build a labelled set.** A collector records, for each prompted command from now on, the `describe` output (the
   command text, the facts, the engine's verdict) in a local, untracked file, and the owner marks each one right
   or wrong. A new file is needed because the old log has no text to label. The facts can contain diffs, and a
   vendor program can open any file inside the project, so the file lives outside every project, in the owner's
   own data directory beside the verdict log, and is never tracked. The owner-side collector writes it; the agent
   does not. A project path for it would be readable by the vendor and is not allowed.
3. **Shadow.** The thin hook runs the engine beside the approver. The approver's answer still decides; the
   engine's is logged. Nothing the engine says takes effect.
4. **Measure.** The report gives false declines and false approves of both programs against the owner's labels. A
   disagreement is settled by the owner's label, not by assuming either is right.
5. **Cut over only when the owner says.** The engine replaces the approver when its false-approve count on the
   test set and the labelled set is zero and its false declines are below a bound the owner sets. The old program and `claude-workflow` stay
   installed until then (rule 6 of `global-config-inventory.md`).

The cost is the owner's time to label, and two model calls per prompted command during the shadow.

**Decided by the owner (2026-10-25):** both. The owner labels real commands, and the author also writes a small test
set of dangerous cases, which the owner reviews and corrects. The two answer different questions. Real commands
seldom include an unsafe one, so a count of zero false approves on them is weak evidence that the engine stops
unsafe actions. The test set covers the stops: a secret in a diff, a HEAD that does not match, a repository that
selects a program, a message addressed to the reviewer, a removal of Git metadata. The labels measure the
everyday false-decline rate. The cutover bound applies to both: no false approve on the test set or the labels,
and false declines on the labels under the owner's bound.

**The bound (the owner chose the author's recommendation, 2026-10-25).** At most 10% of the labelled real commands
are false declines, on at least 30 labelled commands, and strictly below the approver's rate on the same commands.
The 10% is provisional and the owner may tighten it once plan 1 has counted the approver's declines by failed check.
A false decline costs the owner a prompt (under `delegate` a decline falls back to the normal prompt); a false
approve is the harm, so it has no bound: any false approve on either set blocks cutover. The report groups false
declines by check, so a few fixable checks are not hidden in a count. The 10% and the 30 are the author's judgment,
not measured.

### What moves, and what does not

| today | after |
|---|---|
| collectors for commit and remove, via the global program | `safe-git describe commit`, `safe-git describe remove` |
| collector for a remote job | `remote-runner describe submit`, `describe fetch` of the module, which wraps the owner's global program (M16 and F-C6 apply) |
| collector for a push | `safe-git push-check`, plus facts of the outgoing commits that it does not yet give |
| the rubric, schema and rule files | ported into the engine as data, section by section |
| `ask-codex-archive` rule | none: the module's `archive` is owner-run and denied (M15) |
| `safe-committer` agent and the guard's `committer` mode | go with the program (decided by the owner, 2026-10-25): the agent and the mode are removed in the owner's step that removes `claude-workflow`; the guard program stays for its other modes. No module counterpart. |
| `claude-workflow amend-message` | lost with the program (the owner's decision is recorded under "Decisions on the two leftovers") |

## Proposed split into plans (default)

Each is a plan of its own, in this order. None exists, and the owner approves each.

1. **The interface, documented.** The `describe` decision is accepted. This plan settles what it left open: the
   form of a module's declaration in `module-contract.md`, the numeric caps and the fact names for `commit` and
   `remove` in `safe-git.md`, and the engine's contract completed in this spec. It also holds the
   read-only count of the approver's declines by failed check, so the rubric is written knowing where the approver
   goes wrong.
2. **`safe-git describe`** for `commit` and `remove`, with tests that the facts equal what the real command acts on and
   that the call changes nothing.
3. **The engine** with its checks, rules, rubric, log and bridge call, tested with a fake bridge. No hook.
4. **The shadow hook, the labelled set, the test set and the report**, prepared on a scratch copy; the owner installs
   the hook, labels the commands and reviews the test set. The test set is written in plan 3 with the checks.
5. **Cutover and M14**: the thin hook replaces the approver, the global `claude-workflow` program goes, and the
   paragraphs OP5 and OP7 are repointed. Facts for remote jobs follow M16.

## Decisions on the two leftovers

- **`safe-committer` and the guard's `committer` mode (F-A7): the owner chose the author's recommendation on
  2026-10-25.** They go with `claude-workflow`. The workbench's `commit-changes` skill has the main agent run
  `wb run safe-git commit` directly, and the helper enforces the limits. A confined commit agent for the module would
  need the agent gate's grammar extended, for a convenience. If the owner turns out to use the agent, a module
  version is planned later.
- **`claude-workflow amend-message`: lost with the program. The owner accepted the author's recommendation on
  2026-10-25 and said it can be added later if it is needed.** Read on 2026-10-25 (the
  installed program, read, not run): it rewrites the message of the HEAD commit only. It refuses when HEAD is not the
  expected hash, when anything is staged, and when HEAD is on a known remote branch unless `--allow-pushed` is
  passed. Evidence for losing it: (1) the plan `2026-10-22-code-work-commit` left it out on purpose ("the owner amends
  with git by hand"); (2) the module's `commit-changes` skill already says never to amend; (3) the approver has no
  rule for it (F-B4), so it has never been reviewed and no review is lost; (4) this repository's reflog holds no amend
  operation; (5) a new `describe` command, rule, checks and test cases would be built for a history-rewriting command
  that is otherwise refused by policy. Limits of that evidence: the reflog covers this repository only, and the
  owner's other repositories were not examined. A bad message is fixed by a new commit or by the owner's own `git
  commit --amend` in a terminal. When the program goes, its `ask` and `allow` entries for `amend-message` are dead and
  the owner removes them (rule 6 of `global-config-inventory.md`).

## Constraints and assumptions

- Standard library only, a helper per command, pinned by the installer (`module-boundary.md`).
- The engine runs a `describe` command and a bridge only through `wb run`, as decision 4 requires. A security review is
  owed because a helper starts another module's pinned command (decision 4, consequences).
- Assumes a hook can run `wb run` in good time. How long a review may take before the prompt is shown is open.
- The approver's rubric text is read and ported by the plan that builds the engine; this spec does not restate it.

## Open questions for the owner

- Is a separate `describe` subcommand the right shape, or should the interface be something else?
- Decided: you label real commands and review a test set, with the bound above. Open: whether 10% stays after
  plan 1's count.
- `safe-committer` (F-A7) and `amend-message`: decided, see "Decisions on the two leftovers".
- The capability name `action-review` is a proposal.

## Acceptance criteria

- For each action that stays a reviewable module action (commit, remove, a push through `push-check`, and later the
  remote actions), a module `describe` command prints an object that obeys the rules above, runs the real command's
  validation, and changes nothing (a test compares the repository before and after).
- The retired actions have no `describe` provider and no rule: `ask-codex archive`, `safe-committer` and
  `amend-message`. A test shows the engine refuses a command line that names one.
- A rule that carries command text, an extra verb or a path does not load, and the engine builds only `wb run <module>
  describe <action> ...`.
- A synthetic action with a fake module and a fake bridge gets a verdict only through `wb run`; a `describe` command or a
  bridge that is not installed, pinned and declared is refused and nothing runs.
- A missing, malformed, oversize or unavailable bridge reply, facts object or rule file yields no approval.
- Over generated command text, every text the stated grammar accepts parses to the same argument list in the engine
  and in `sh` and `zsh`, and every other text is refused.
- Two rules with one key, a malformed rule and a rule with an unknown field each refuse only their own key; other
  commands are still reviewed.
- Bridge selection: an absent setting, a bridge that is not installed, one that is not pinned, and a project request
  that the owner's setting overrides each behave as the settings section says, and no other vendor is tried.
- No file holding labelled data or command text lies inside a project tree.
- A corrupt rule file does not stop the review of any other command.
- Every check of today's approver for commit, remove and push has a named counterpart or a recorded reason it does
  not (the plan of the engine lists them).
- On the test set of dangerous cases (reviewed by the owner) and on the labelled set of the owner's real commands,
  the engine has no false approve; on the labelled set its false-decline count is below the owner's bound; and the
  report shows the approver's counts on the same sets for comparison.
- The count of the approver's declines by failed check exists before the engine's rubric is written.

## Evidence

- The approver's collectors were read on 2026-10-25 in the program the inventory records (baseline SHA-256
  `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`, then patched to
  `d8b3facdee46432d27547a07865abf024741929ae2d9191e1015ee8280bcd613`); `load_helper`, `collect_commit` and
  `collect_remove` call the global `claude-workflow` program as a library. Read, not run.
- The module sides were read in `safe-git.md` (`commit`, `remove`, `push-check`) and `model-bridge.md`.
- Not run: any `describe` command, any engine, any hook. The proposals are the author's.

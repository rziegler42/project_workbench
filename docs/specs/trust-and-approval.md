# Trust, approval and untrusted content

Status: Current. Approved by the owner on 2026-10-19. The guarded store, the personal settings, approval
records, first-party shipped approvals, the approval request and gate, the owner-run `approve` and `pin`
commands, the inert download and the launcher are built (`module-approvals`), and "Concrete formats" records what
the code does. Acknowledgement (the baseline check and `wb acknowledge`) is built (`ownership-and-upgrade`). The rendering into the Claude harness is built (`claude-harness`). Plan approval records (`2026-10-22-plan-approval-records`) are built. The `caps` setting, `wb settings` and the
edit gate (`2026-10-22-checkpoint-settings-and-caps`) are built. Delegation
and the opencode rendering are not built yet, and their record formats and setting names
remain proposals. The rules are the substance.

Terms are defined in `terms.md`. Places and manifests are defined in
`repository-boundary.md`. Declarations are defined in `module-contract.md`.

## Purpose and scope

This specification defines who or what may grant authority, how a grant is recorded
and checked, which actions always stop, and how text written by someone else is
treated. It exists so that an agent working unattended stays inside what its owner
actually authorized, even when the files it reads were written by a hostile party.

Non-goals:

- The list of checkpoints a particular way of working defines. Each process module
  specifies its own, using the framework here.
- The translation of rules into a particular harness's syntax.
- Defence against an attacker who already holds the owner's full privileges on the
  owner's machine, or against a compromised workbench installation.

## Threat model

Adversaries considered:

- a contributor who commits hostile text or files to a shared repository: roadmaps,
  specs, plans, decisions, manifests, scripts, `AGENTS.md`;
- the author of a third-party package;
- the author of a web page, datasheet, image or other reference the agent reads;
- an agent that has been steered by any of the above;
- a second reviewing AI that reads the same hostile text as the agent it reviews,
  and so may be steered the same way.

Assets protected: the owner's machine and accounts, the project's history and shared
remote, the owner's money (tokens, printing time, fabrication orders), and the
integrity of what the project records as decided.

## Principles

1. **Authority comes only from the owner's settings and from approvals the owner or
   an explicit delegate recorded.** Never from the text of a plan, spec, roadmap,
   decision, reference, manifest or module.
2. **Committed policy may tighten, never loosen.** Committed content can add stops;
   it cannot remove one, grant a permission, or widen a delegation.
3. **Fail closed.** A missing, unreadable or mismatched record means no approval. A
   reviewer that is unavailable, times out or says no means stop and report.
4. **Enforce mechanically where the harness can.** A rule an AI is merely asked to
   follow is advice. Where the harness provides `permissions`, hard stops are also
   rendered as local `deny` and `ask` rules, because a reviewing AI can be steered
   by the same text as the agent.
5. **Unattended work is bounded.** Every loop has a cap, and exceeding it stops the
   run with a report.
6. **Untrusted content is data.** Instructions inside it are ignored.

## The guarded store

The guarded store (`~/.config/project-workbench/`) holds everything whose forgery
would defeat the above: approvals, acknowledgement baselines, pinned hashes and the
owner's personal settings.

- The agent must not write the store. Each harness that provides `permissions`
  receives a local `deny` rule on writes to it. Where the harness has a sandbox,
  the store is outside the sandbox's writable set.
- The owner records an approval by running a command themselves, from a prompt the
  agent does not control (for example a harness's user-shell prefix). The agent's
  command permissions deny that command.
- Delegated approval is performed only by a small command of the installer
  (`wb delegate-approve-plan`; see "Delegated approval"), which the agent may call
  and which checks before it writes. That command and the launcher in "Pinned
  helpers" are components of the workbench itself: the installer installs them when
  it initializes the store. They are not shipped by any module.
- **Initialization.** Every workbench command first ensures the store exists,
  idempotently, and seeds the personal settings if they are missing, before any
  approval check runs. No command depends on an earlier "first run".
- The hard-stop floor is compiled into the installer. The seeded copy in the
  personal settings is additive, so a deleted or damaged settings file cannot
  remove the floor, and the floor does not depend on a file the agent could damage.
- The store is a mechanical barrier, not an operating-system one: it runs under the
  same user account. Its strength depends on the harness's deny rules and sandbox.
  Where a harness lacks `permissions`, the installer warns that the store and the
  hard stops are enforced only by instruction.

## Approvals

An approval is a record in the guarded store. Every approval has a kind, a subject,
the hash or hashes it binds to, the approver, and the time. A record is valid only
while the current hashes of its subject match.

### Package and module approval

- Subject: a module in a package. Binding: the module's declaration hash and its
  content tree hash, as defined in `module-contract.md`.
- Kept machine-wide, keyed by those hashes, so a module is approved once for all
  projects.
- Required before any of a package's files are written into a project or activated.
  The owner cannot judge a declaration without seeing it, so a package is first
  downloaded **inertly**: into a cache inside the guarded store, as data only, never
  executed and never written into a project. The approval request is then shown from
  that cached copy, and the tree hash it binds to is computed from it. Only after
  approval are the resolved commit and tree hash pinned and the files written.
- A module of type `harness` or `process` always needs an explicit approval.
- The approval request shows the declaration in plain terms: type, what it provides,
  requires and blocks, the paths it writes, every hook or executable it ships, and
  the helpers it expects, and each command it offers with its helper, how it starts and the
  first arguments it allows, and each check it offers with its helper, the kit API it runs through and
  the name its owner pins it under. A module that blocks a core capability is flagged high
  risk.
- First-party modules are approved by the same command, run at release time, and the
  records ship with the workbench. They are verified by the same verifier. Shipping
  with the workbench counts as explicit approval. The trust root for these records is
  the workbench's own distribution: they are read from the installed workbench, which
  is version-pinned, and are not copied into the guarded store.
- A changed declaration or changed content is a different subject and needs a new
  approval.

### Plan approval

- Subject: a plan in a project. Binding: a hash of the plan's hashed region.
- Kept per project, under the project ID.
- The sections that are excluded are named by the plan format of the process module
  in use (see `code-work.md`); this specification defines the rule and the process
  module defines the section names.
- The **hashed region** is the whole plan except its status line, its review record
  and its result. These are the parts the agent legitimately edits as work proceeds.
  Everything else, including scope, increments, verification and risks, is hashed.
  The text is normalized before hashing: line endings, trailing whitespace and the
  final newline.
- Editing the hashed region after approval invalidates the approval. A plan changed
  by a pull needs approving again.
- The agent acts on a plan only while its current hash matches a recorded approval.
  A `Status: Approved` line in a committed file is never an approval.
- The installer reads no plan and holds no list of section names. The process module declares a pinned command
  that computes the hashed region and reports its hash; the installer runs that command, records what it
  reports and compares it later ("Plan approval records", below; built by plan `2026-10-22-plan-approval-records`).

## Checkpoints, delegation and hard stops

### Checkpoint

A checkpoint is a named point at which authority is needed before the agent
continues. A way of working declares its checkpoints. Each checkpoint has one
setting in the personal settings, with two values:

- `stop`: the default. The agent halts and the owner decides.
- `delegate`: the verdict may be given by a second reviewer, subject to the rules
  below.

A new teammate with no settings gets `stop` for every checkpoint.

### Delegated approval

- A delegate may issue the verdict for a checkpoint only when the personal setting
  for that checkpoint is `delegate` and the `peer-review` capability is provided
  by an installed, approved module. The first-party provider is the module
  `review-engine` (`review-engine.md`). It stores findings, the reviewer's verdict
  and its own reading as data, and it records no approval and grants no authority;
  nothing in it asks for one. The delegated
  record is designed (plan `2026-10-23-delegated-approval`, decision
  `2026-10-23-delegated-plan-approval`, accepted) and not built; "Delegated plan
  approval records" below states it.
- A reviewer may always give findings without delegation. The verdict is the part
  that needs authority.
- For plan approval, the delegate's verdict requires that review converged with no
  blocking findings within the round cap. The helper records the delegate (provider
  and model), the number of rounds, and a pointer to the review record.
- The reviewer checks a plan against its roadmap candidate and its specs. Drift
  from either is a finding.
- A reviewer that is unavailable, times out, or returns no verdict yields no
  approval and the run stops.
- A plan whose risks section lists any hard-stop action is not delegable. This is
  defence in depth only: a hostile plan can omit the section, so the real control is
  that hard stops stop at the time of the action whatever the plan says.
- The installer's `delegate-approve-plan` command is the only writer of delegated
  approvals. It writes the same record as the owner's `approve-plan`, from facts that
  declared, pinned commands report; a module never writes a plan approval record.
  A module's other writes to the store, such as the review engine's seal key and
  marks, are not approvals and are unchanged.

### Hard stops and the floor

A hard stop is an irreversible or externally-effecting action. It always stops for
the owner. No setting, plan, review or delegate can lift it.

The **floor** is the set of hard stops that ship with the workbench and apply to
every project, including a project with no process module:

- force operations and rewriting history that has been pushed;
- deleting uncommitted project files, or overwriting an existing or tracked file with
  fetched content;
- publishing or deploying;
- anything touching secrets;
- installing dependencies.

Rules:

- The floor is compiled into the installer, and also seeded into the personal
  settings when the store is initialized (see "The guarded store"). The seeded copy
  is additive and the compiled floor always applies.
- A module may add hard stops (for example a way of working for physical fabrication
  adds starting a print and placing an order). Nothing, including committed project
  policy, may remove one.
- Each harness that provides `permissions` receives the floor and the added stops as
  local `deny` and `ask` rules at attach.
- Deleting inside the session's scratch directory or the system's temporary
  directory is not a hard stop. It is a personal permission, not project policy.

### Rendering rules

- The neutral rule list contains only `ask` and `deny`. It never contains `allow`.
  A convenience allowance is personal and lives in the owner's own configuration.
- A rule is rendered into local, uncommitted harness configuration only.
- A harness that provides `permissions` renders a `deny` for each owner-run command, so an
  agent cannot run it: `wb install`, `wb upgrade`, `wb add`, `wb attach`, `wb acknowledge`,
  `wb recover`, `wb approve`, `wb pin`, `wb release-approvals` and `wb approve-plan`, in the `wb` spelling and
  the four interpreter spellings of `-m workbench` (`rules.SPELLINGS`). The read-only `wb preview` is not denied. The commands
  are listed in `installer-interface.md`. A module command may also declare owner-run arguments
  (`module-boundary.md`, "Declaration schema"), and the harness renders a `deny` for each as well:
  `wb run <command> <argument>` bare, with more arguments and through `--provides`, in the same five spellings
  (`rules.command_owner_patterns`). They are restrictive only, they depend on the modules installed when the
  harness was attached (a module added later needs `wb attach` again), and they are the same best-effort match
  as the rest. A harness that provides no `permissions` enforces them by instruction only. *(Rendered by the Claude harness module, built by
  `claude-harness`; the opencode module is `opencode-harness`.)* The deny is best effort: it
  matches the command text the agent submits, not what a wrapper script runs. With the edit gate's hook the
  rendered rules also deny edits to the local settings file and `.git/info/exclude`, by relative and by absolute
  path; without a hook they do not (`harness-modules.md`, "As built, and its limits").

## Acknowledgement

Acknowledgement is the owner confirming they have seen a change they had not
reviewed. It protects against text changed by someone else.

- The guarded store keeps a baseline hash per file. Any difference from the baseline
  needs acknowledgement, shown as a diff. Authorship is not used, because a git
  author name can be forged.
- **First tier:** instruction-bearing and executable files: `AGENTS.md`, committed
  files under `.workbench/`, helper scripts, and continuous-integration
  configuration. The agent must not act on a changed file in this tier until it is
  acknowledged. The checkpoint is `stop` unless the owner has explicitly set it to
  `delegate`.
- **Second tier:** direction documents: roadmaps, specs, plans and decisions. They
  need acknowledgement before the agent drafts from or acts on a changed one. The
  checkpoint can be delegated like any other.
- References need no acknowledgement. They never carry authority.
- A change made and committed through the commit helper does not update a baseline. The helper
  runs with the owner's privileges at an agent's request, and a baseline is the owner's acceptance of a
  change someone else made, so the next `wb acknowledge` lists the change and the owner accepts it there
  (`2026-10-22-commit-helper-leaves-baselines-to-the-owner`).
- Approving an install or an upgrade preview updates the baselines for exactly the
  files in that preview, so the owner is not asked to acknowledge their own approved
  change.
- **Baselines file (built by `base-and-manifests`).** `projects/<id>/baselines` is strict JSON,
  `{"baselines": {"<path relative to the project root>": "<sha256 hex of the bytes>"}, "format": 1}`,
  with sorted keys. `install` writes it for the files it wrote. `upgrade`, `add` and
  `acknowledge` read it *(built by `ownership-and-upgrade`)*.
- **What a command checks before it acts on a project** *(built by `ownership-and-upgrade`; owner)*. The project must have
  `projects/<id>/baselines` and a `seen` record at the resolved target path on this machine, else
  it is treated as new here and the command refuses. It then compares the committed manifest,
  every file under `.workbench/` outside `local/` (a file added or removed counts) and every
  file the command would write into with the baselines, and refuses on any difference, naming
  the paths. A file the command writes into must equal its baseline, so a baseline update never
  accepts an unreviewed edit.
- **`wb acknowledge`** is the owner's way to accept the differences. It is owner-run and
  terminal-only. It lists each difference (path, baseline hash, current hash, reason) and a
  parsed summary of the manifest, asks for the first 12 characters of the digest of the list,
  and on a match replaces the baselines for exactly the listed paths. The store keeps hashes,
  not old bytes, so the listing is not a line diff. As built, the list covers the manifest, every
  file under `.workbench/` outside `local/` and every other path that has a baseline, so an
  edited seeded file that an upgrade would write a block into can be accepted too.
- Scratch under `.workbench/local/` is not covered. It grants no authority.

## Pinned helpers

A helper that the owner pre-allows, such as the commit helper, is protected from
silent replacement.

- A small workbench-owned launcher, installed by the installer in the guarded store
  (it is part of the workbench, not shipped by a module), verifies the helper's hash
  against a pin and only then runs it. The helper itself is a file of the module
  that supplies it. The installer never runs a module's code at install; the
  launcher runs a helper only when the agent or the owner invokes it.
- The owner's personal allowance targets the launcher, not the helper, because a
  harness's allowance matches a path and not a hash.
- A pulled edit to the helper changes its hash, so it loses its pre-approval until
  the change is acknowledged and the pin is updated.
- **The installer pins the helpers a confirmed plan declares.** A `commands` or `checks` helper of a
  module in an install, add or upgrade is pinned in the step the owner confirms with the digest
  (`workbench/pinplan.py`): the owner has just confirmed those exact bytes, so a separate `pin` for each
  adds friction and no information. The preview and the digest list every pin made, moved or replaced, and a
  replacement shows the pin it replaces and who made it; the pin records `workbench <command>` as its
  maker. A helper the plan does not write keeps the pin it has, so a pulled edit stays refused until
  `acknowledge`. An installer-made pin also records the hash of the `module.json` the owner confirmed
  (`declaration`); `wb run` and `wb check` refuse a pin whose declaration differs from the manifest's, so
  a pull that rewrites a declaration and its hash cannot widen what a pinned helper accepts. Only an
  upgrade of the module, with the digest typed, or an owner-run `pin` clears that refusal.
- **`acknowledge` moves only the pins the installer made.** When it accepts an edit to
  a helper whose pin records a declaration and holds the bytes last acknowledged, the pin moves to the bytes
  accepted and keeps its declaration; the move is listed in the digest. A pin the owner typed with `pin`
  records no declaration and is never moved: acknowledging an edit is not permission to run it.
- **One module's helper may run another's command, and only through the launcher.** A helper that calls a
  command of another installed module does so with the kit's `call.run_command`, which starts `wb run`
  (`module-boundary.md`, "A helper that runs another module's command"). The launcher applies the pin to the
  callee exactly as it does for the agent: installed, declared, pinned on the declared helper, bytes and
  declaration unchanged. The caller's approval is not the callee's, the callee's output is untrusted data to
  the caller, and the callee runs with the caller's privileges, because a pin is not a sandbox.
- The pin file, the launcher and the `wb` script are described under "Concrete formats".

## Concrete formats

Recorded from the code of `module-approvals`, which is where each item is implemented. Where the
prose above and this section differ in precision, this section is what the code enforces.

### The guarded store and the personal settings

- **Location.** `~/.config/project-workbench/`, found from the account's home directory. No
  workbench environment variable, option or file moves it, because a variable the agent can set in
  one command would let it point the workbench at a store it controls. `HOME` is honoured as for any
  program run by the same account. The code takes the root as an argument only so that tests use a
  temporary one.
- **Directories.** The store and its directories `packages/`, `cache/`, `projects/` and `bin/`
  (and `bin/run/`) are real directories, owned by the current user, with mode exactly `0700`. A
  symbolic link, another owner or any other mode (group or other access, setgid, sticky) is refused
  and named; nothing is repaired. Ancestors of the store may be symbolic links, because `~/.config` is
  often one. Every read and write is no-follow, descriptor-relative and atomic.
- **Initialization.** Every command makes sure the store exists, then seeds `settings` if it is
  missing, then makes sure `bin/wb` exists.
- **Settings.** The file `settings` is strict JSON:
  `{"checkpoints": {"<name>": "stop" | "delegate"}, "floor": ["<id>", ...], "version": 1}`. A
  checkpoint name is lowercase kebab-case, at most 64 characters; the names themselves are defined
  by a way of working. A checkpoint that is missing, malformed or not exactly `delegate` reads as
  `stop`. A damaged file, a wrong version, or a file that is not a regular file is reported on the
  command's output as a `settings:` note and is never overwritten; every checkpoint then stops. The
  `floor` list is a copy for the owner and for harnesses to read: nothing reads it to decide what
  applies.
- **The floor.** The five entries of "Hard stops and the floor" are compiled into the installer
  with the identifiers `force-or-rewrite-history`, `delete-or-overwrite-files`,
  `publish-or-deploy`, `touch-secrets` and `install-dependencies`. The one function that combines
  stops returns the floor followed by any additions and refuses any removal, any addition that
  repeats a floor entry (also under another spelling) and any malformed addition.

### Approval records

- **File and key.** A record is `packages/<key>/approval.json`. The key is the SHA-256, in
  lowercase hex, of `"<kind>\n<declaration hash>\n<tree hash>\n"`, so a record is found only by
  presenting the hashes it binds to.
- **Fields.** Strict JSON with exactly these fields and no others: `format` (1), `kind`
  (`module` or `package`), `subject`, `declaration_hash`, `tree_hash`, `approver` (printable text,
  at most 64 characters), `time` (UTC, `YYYY-MM-DDTHH:MM:SSZ`) and `workbench_version`. A package
  record also has `modules` (a list of `{name, declaration_hash, tree_hash}`, unique and sorted by
  name) and `commit` (`null` or a lowercase hex commit id).
- **What each kind binds.** A `module` record has the subject `<package>/<module>` and binds that
  module's declaration hash and tree hash. A `package` record has the subject `<package>` and binds
  the package declaration's hash and the tree hash of the whole package directory, and lists the
  modules it approved with both hashes each.
- **A check.** It returns approved only when the record exists as a regular file in a real
  directory, can be read, is well formed, and its kind, both hashes and its subject all equal what is
  presented. The subject is compared as well as the hashes, so byte-identical content approved as
  `a/m` is not approved as `b/m`. Anything else is no approval, with a reason. A check never raises.
- **Writing.** Approving the same thing again keeps the first record and its approver and time. A
  record that differs in subject or module list for the same hashes is not written, and a damaged
  record is never replaced. The `commit` is provenance and not part of what a record binds:
  identical content reached by another commit, or after a local approval, is the same approval and
  the first record, with its commit or absence of one, is kept.
- **Approver.** The account name from the operating system's user database, not from an
  environment variable. It is text and grants nothing.

### Plan approval records

*(Built by plan `2026-10-22-plan-approval-records`, at `format: 1`.)*

- **The region command.** A `process` module declares `approval: {"command", "argument"}` (`module-contract.md`).
  The installer resolves exactly one process module that declares it, from the committed manifest, and runs the
  command as `wb run` does: the module installed and approved, its declaration hash equal to the
  manifest's, the helper pinned for that command and its bytes unchanged (the tree hash is not compared at run
  time). It runs `<command> <argument> <plan>` with the
  plan's path relative to the project root, with standard input closed, and accepts, within 4,096 bytes of
  standard output, one JSON object and a newline and nothing else:
  `{"format": 1, "region_hash": "<64 lowercase hex>", "unhashed": ["<name>", ...]}`, with at most 16 names of at
  most 64 printable characters. Anything else, a non-zero exit, a timeout or a `refused:` line is no approval. The
  module's helper reads the plan (bounded, no link followed) and decides what is in the region; the output is
  data and is validated, never followed.
- **The record.** `projects/<id>/plan-approvals` in the guarded store, strict JSON,
  `{"format": 1, "approvals": [{"plan", "region_hash", "declaration_hash", "helper_sha256", "approver", "time",
  "workbench_version"}, ...]}` with at most 2,000 entries. `plan` is the path relative to the project root, and
  passes the path validator. `declaration_hash` is the process module's declaration hash and `helper_sha256` is the
  SHA-256 of the helper as pinned. The file is replaced whole and atomically. An approval that equals an entry in
  all four of plan, region hash, declaration hash and helper hash is not added again (the first record is kept);
  one that differs adds an entry, and the older entries stay as history. Reading fails closed.
- **The check.** For a plan the installer computes the four values now. If an entry equals all four, the plan is
  `approved`. If some entry names the same plan, the newest such entry says what differs and the plan is `changed
  since approval` (the region, the process declaration or the helper). Otherwise it is `not approved`. A project
  with no process module that declares `approval`, with more than one, or a command that cannot run, is a
  refusal and not a status.
- **`approve-plan <plan>`** (owner-run; terminal on both standard input and standard output). One argument and no
  option, run from anywhere inside the project, with the root and the ID found as `wb run` finds them. `<plan>` is
  read relative to the current directory (or absolute) and converted to a path relative to the root; it is
  refused if it is outside the root, empty, holds a NUL or a `..`, or has a link in any component, the last one
  included, or is not a regular file. It shows the root, the plan, the process module, the first 12 characters of
  the declaration and helper hashes, the `unhashed` names and the region hash, and says if an older entry for
  the plan exists. It records only when the first 12 characters of the region hash are typed back, after running
  the command again and finding the two reports equal. Exit codes: 0 recorded or already recorded, 1 refused or
  cancelled with nothing written, 2 usage error, 130 interrupted. The typed text is friction, not authentication;
  the barrier is the harness's deny rule.
- **`plan-status <plan>`** (read-only, agent-safe). The same argument and path rules. It writes nothing and prints
  one line on standard output, `approved: <plan>`, `changed since approval: <plan> (<what differs>)` or `not
  approved: <plan>`; a refusal prints a `refused:` line on standard error and nothing on standard output. Exit
  codes: 0 approved, 1 anything else, 2 usage error.
- **Limits.** The gate is a command and a rule. Nothing stops an agent that does not ask it. The helper is the
  authority on what the region is, as far as its owner-approved bytes go, and a helper that misreports it defeats
  the approval; the record binds the helper's hash so that an edit of it is a change.

### Delegated plan approval records

*(Designed by plan `2026-10-23-delegated-approval` and the decision `2026-10-23-delegated-plan-approval`, which the
owner accepted on 2026-10-23; nothing here is built yet.)*

- **The command.** `wb delegate-approve-plan <plan>` takes one argument and no option, runs from anywhere inside the
  project, and finds the root, the ID and the plan path as `approve-plan` does, with the same path rules. It is not
  owner-run: the agent may run it, and no harness denies it. It prints one line, `approved: <plan> (delegated, <n> of
  <bound> rounds)` or `already approved: <plan>`, or a `refused:` line on standard error and nothing on standard
  output. Exit codes: 0 recorded or already recorded, 1 refused with nothing written, 2 usage error.
- **What it checks, in this order, and stops at the first failure.**
  1. The effective value of the checkpoint `approve-plan` is `delegate` ("Checkpoint and cap settings", below). The
     value is read from the owner's personal settings in the guarded store and from nowhere else.
  2. Exactly one process module declares `approval` (as for `approve-plan`) and exactly one installed module provides
     `peer-review` and declares `convergence` ("Declaration" in `module-contract.md`). Each is installed, approved, has
     its declaration hash equal to the manifest's, and has its helper pinned and unchanged, as `wb run` requires. None
     or more than one is a refusal.
  3. The plan file is read once, with no link followed and within the bound the region reader uses, and its SHA-256
     is taken (`H1`).
  4. The region command runs as for `approve-plan` and reports the region hash.
  5. The process module's `delegable` argument runs; the plan must be delegable.
  6. The provider's `convergence` argument runs; the review must be of kind `plan`, converged, and its
     `document_sha256` must equal `H1`.
  7. The plan is read and hashed again and must equal `H1`, and the region command's report must equal the first. A
     difference is a refusal.
  8. One entry is written, then read back; it is not written if an entry equal in plan, region hash, declaration hash
     and helper hash exists, whoever made it.
- **The facts the commands report.** Each is run with standard input closed, as `region` is, with the plan's
  project-relative path as its last argument, and each answers with one JSON object and a newline and nothing else
  within its bound; a non-zero exit, a timeout, a `refused:` line, a second line or a field not listed is no approval.
  The output is data: validated, never followed.
  - `delegable` (the process module's argument named by `approval.delegable`, at most 1,024 bytes):
    `{"format": 1, "delegable": true | false, "reason": "<at most 200 printable characters>"}`.
  - `convergence` (the provider's argument, at most 4,096 bytes): `{"format": 1, "kind": "plan", "converged": true |
    false, "document_sha256": "<64 lowercase hex>", "rounds_used": <1 to 5>, "bound": <1 to 5>, "bridge": "<name of at
    most 64 characters>", "model": "<at most 200 printable characters>" | null, "review": "plan-<16 lowercase hex>",
    "closed": true | false}`. The provider reads its own sealed state and refuses with a `refused:` line when the
    review is missing, unsealed, rolled back or unreadable, has no round in its current window, or is not of a plan. `converged` is true only when the last
    round has no `blocker` or `major` finding, no meaningful finding of the window has no decision, the reviewer's
    verdict and the provider's reading both say no meaningful changes, and the rounds used do not exceed the bound.
    A rejected finding does not make a review converge, because the last round must itself be clean. A closed
    (archived) review counts.
- **The same-bytes rule and its order.** The review's `document_sha256` is the hash of the plan file as the reviewer
  read it, so the approval is only given while the file is byte-for-byte what was reviewed. The review record the agent
  writes after a review changes the file, so the agent asks for the delegated approval after the converging round and
  before it writes the record. If it asks later the command refuses, saying that the file differs from the reviewed
  one; the agent runs another round or the owner approves. The status line, the review record and the result can change
  after the approval without invalidating it, because the approval binds the region.
- **The record.** The `plan-approvals` file moves to `format: 2`. The reader accepts formats 1 and 2 and the writer
  writes 2; an older workbench refuses a format-2 file, which fails closed. An entry of either format has the fields of
  "Plan approval records". A format-2 entry may also have `delegate`, an object with exactly: `provider` (the module
  name), `provider_declaration_hash`, `provider_helper_sha256`, `bridge`, `model` (text or null), `rounds_used`,
  `bound`, `review` and `document_sha256`. An entry with `delegate` is a delegated approval; `approver` is still the
  account's name from the operating system and grants nothing. The four values that decide `approved` are unchanged, so
  `plan-status` and the edit gate read a delegated approval as they read an owner's, and a change of the region, the
  process declaration or the helper makes it `changed since approval` in the same way.
- **While the setting stands.** An entry with `delegate` counts only while the effective value of `approve-plan` is
  `delegate` when it is read. A setting that is `stop`, missing or damaged withdraws it: `plan-status` prints `not
  approved: <plan> (delegated approval withdrawn: approve-plan is not delegate)`, the gate refuses with that reason, and
  the owner's `approve-plan` is how to approve. An entry without `delegate` is never affected by the setting. The
  provider's hashes in the entry are provenance and are not checked when the entry is read.
- **Delegable.** A plan is delegable when it has exactly one Risks section and that section has no line that begins,
  after any list marker and emphasis, with `Hard stop:` (case-sensitive). A plan with no Risks section, more than one,
  or one that cannot be read is not delegable. The marker is a convention the process module documents. It is defence
  in depth only: a hostile plan can omit it, and the real control is that hard stops stop at the time of the action.
- **Limits.** A delegated approval is weaker than the owner's. A plan written to steer the reviewer can get a clean
  review, the reviewer and the author can share a blind spot, and the gate stops a mistaken agent and not a hostile
  one. The seal key and the rollback mark of the review sit in the guarded store under the harness's deny rule, which
  is a mistake guard. A review that was not sealed on this machine gives no delegated approval until the owner resets it.
  The model may be unknown (null). The record states the delegate; it does not say that the reviewer was good.
  A provider that is changed, replaced or removed after the approval does not withdraw it (an accepted risk, decision
  `2026-10-23-delegated-plan-approval`): what was approved is bound by the region and the process module's helper, and
  the owner turns delegation off or approves the plan again to withdraw it.

### Checkpoint and cap settings, and the edit gate

*(Built by plan `2026-10-22-checkpoint-settings-and-caps`. The names are in `code-work.md`; the declaration fields are
in `module-contract.md`; the decision that the installer owns the gate is
`docs/decisions/2026-10-22-installer-owns-the-edit-gate.md`, accepted.)*

- **What the module declares.** A process module declares `checkpoints`, `caps` and `approval.active`. The
  installer treats every name as opaque text and knows no plan: it never reads one.
- **The `caps` setting.** The personal settings gain an optional `caps`, `{"<name>": <integer>}`. `version` stays 1
  because the key is additive; a workbench that predates it reports the key as unknown and ignores it. A missing
  `caps` is empty.
- **Effective values.** A checkpoint is `delegate` only when the owner set exactly `delegate` for a name the
  module declares, and `stop` otherwise; `delegate` has no effect until `delegated-approval` reads it. *(Proposed, not
  built: once built, `delegate` takes effect for the checkpoint `approve-plan` only, which `delegate-approve-plan`
  reads. For any other name, `delegate` stays `stop`, and `wb settings` prints `stop` with a `settings:` note that
  delegation of that name has no effect.)* A cap is the
  owner's value when that is a JSON integer from 1 to the module's ceiling (a boolean, zero, a negative
  number or a larger number is not; a number with a fraction or an exponent makes the strict loader treat the
  whole file as damaged), and the module's default otherwise. A checkpoint or cap entry for a name the
  module does not declare is ignored. Each ignored or replaced value is reported as a `settings:` note. A damaged
  settings file gives every default, every checkpoint `stop`, and the existing damage note, and is not
  overwritten.
- **`wb settings`** (read-only, agent-safe; `installer-interface.md`). It resolves the one process module,
  reads its verified declaration, and prints the effective values and the notes.
- **The active command.** For a module that declares `approval.active`, the installer runs
  `<command> <active>` with no further argument, with standard input closed, as it runs the region command, and
  accepts within 8,192 bytes of standard output one JSON object and a newline and nothing else:
  `{"format": 1, "plans": ["<root-relative path>", ...]}` with at most 32 paths of at most 240 characters, each
  passing the path validator, none repeated. Anything else, a non-zero exit, a timeout or a `refused:` line is a
  failure of the helper. The output is data and is validated, never followed.
- **`wb gate <harness>`** (the edit gate; the hook's command, `wb gate claude` for the Claude harness). It reads one JSON object from standard input,
  at most 16 MiB (16,777,216 bytes; more is a refusal), and decides one tool call. While a plan is under way the
  object may be at most 65,536 bytes. It prints nothing and exits 0 to allow, and prints one `refused:`
  line on standard error and exits 2 to refuse. Every other outcome, a crash included, is a refusal. A total
  deadline of 10 seconds covers everything including the helper runs, and its expiry is a refusal. In order:
  1. The object must carry a string `cwd`, a string `tool_name` and an object `tool_input`. The project is found
     from `cwd` as `wb run` finds it; none is a refusal (the hook is only rendered into a project).
  2. A project with no installed process module that declares `approval.active` is allowed. More than one such
     module is a refusal.
  3. The `active` command is run. No plan under way is an allow. A failed command is a refusal.
  4. The targets are read from `tool_input` by the table the harness module's layout declares under
     `hooks.targets` (`harness-modules.md`, "The edit gate hook"); the installer holds no tool name. A `tool_name`
     outside the table, a missing or empty field, a field that is not a string, a NUL and a path of more than 4,096
     characters are refusals. Every target is placed and judged, and the call is allowed only when all of them pass.
  5. A target is placed by resolving a relative path against `cwd` and folding `.` and `..` lexically; a `..` that
     follows a symbolic link is a refusal. Containment in the root compares with case and Unicode variants folded,
     so a case-insensitive filesystem cannot turn an inside path into an outside one. A target that lies outside the
     root as spelled is followed through its links and judged where it lands, so an alias of the root is not a way
     out; a loop or a path that cannot be resolved is a refusal. A target outside the root passes. A target inside
     the root is refused when any component that exists is a symbolic link. A target that is exactly a plan under
     way passes, so that a plan's status, review record and result can still be written; the same plan spelled in
     another case is refused and not passed, which is stricter than a fold would be.
  6. Any other target passes only when every plan under way reads `approved` by "The check" above; the first plan
     that does not stops the check. The refusal names the plan, its state (`not approved` or `changed since
     approval`) and `wb approve-plan`.
- **Writes.** Nothing in the project and nothing in the store beyond the bootstrap that every command makes
  ("The guarded store and the personal settings", "Initialization"). The first tool call of a session may seed
  a missing `settings` file, as any other command would.
- **Limits.** The gate stops a mistaken agent and not a hostile one. A `Status:` line is informational and an agent
  can edit it; a shell command writes any file without passing a file-editing tool; a plan that no listed
  status marks as under way is not seen; and the hook runs only where the owner's local settings carry it.
  `Bash` and commit-time gates are deferred (`2026-10-22-checkpoint-settings-and-caps`, "Deferred work").
  Input of more than 65,536 bytes is refused only once the `active` command has reported a plan under way, so a
  `Write` of more than about 64 KiB is allowed when none is, and refused while one is. Input of more than 16 MiB is
  refused in every state, so the read is always bounded; a `Write` of that size is refused with the hook installed.
  A harness that renders no hook, or whose layout describes none, has no gate, and attach says so.
- **As built.** `delegate` has no effect: every checkpoint stops. There is no project-level setting that lowers a
  cap; `code-work.md` says a project may lower and not raise, and that waits for a generic project setting the
  installer can read ("Deferred work" of the plan). Only the Claude harness renders a hook.

### The `approve` command

`approve (<package> | --source <url> [--ref <ref>]) [--module <name>]` is run by the owner.

- It refuses unless standard input and output are both terminals, tested on the file descriptors.
  There is no `--yes` option.
- It verifies the package and refuses on any problem, recording nothing.
- It prints the request and asks the owner to type the first 12 characters of the tree hash shown:
  the package's, or with `--module` that module's. Anything else cancels.
- It verifies again just before writing and refuses a package that changed while it was shown.
- It writes a `module` record for each module and then the `package` record, or only the one
  `module` record with `--module`. A harness or process module is approved on its own record.
- With `--source` the package is first downloaded (see "Inert download"); the request, the typed
  hash and the records all come from the cached copy, and the package record stores the resolved
  commit as provenance. A copy that is declined or fails verification stays in the cache.
- The typed text guards against a mistake. It is not authentication: the characters are printed by
  `verify` and by the request, and a process that opens its own pseudo-terminal passes the terminal
  test. The barrier is the harness's deny rule for this command and for writes to the store.

### The request

For a module the request shows, in this order: a `HIGH RISK` line when it applies (a `harness` or
`process` module, or a module that blocks a core capability, which is an unprefixed name); the
identity and source; both hashes in full; a size line with a count of each kind of entry; and then
what it provides, requires (soft ones marked) and blocks (core capabilities marked), the slots it
owns and fills, the paths it writes, every item it ships (`[executable]` or `[code-bearing]`), any
other executable file in the module, the helpers it expects, and a harness module's layout, one line
per leaf. A package request lists every module and which need an explicit approval of their own.
Nothing a package controls is shortened, lists are shown one entry to a line, and every
package-supplied string is shown as ASCII with anything else as a visible escape. The text is
rendered from the verification result and not from a second read of the files.

### First-party packages

A package is first-party only when all of these hold: its directory is directly inside the
distribution's `packages/` directory and is not a symbolic link; its declared name equals its
directory name; and a shipped package record for that name matches the package's current
declaration hash and whole-package tree hash. Only a first-party package may provide an unprefixed
capability name. The shipped records are in `workbench/shipped_approvals/` in the same layout as the
store, are read in place and never copied into the store, and are made at release time by
`release-approvals`, which verifies every package under `packages/` as first-party, writes nothing if
any module fails, and uses a fixed approver and time so a second run changes nothing. Records of
earlier releases are left in place and reported, because nothing deletes them. A first-party
package changed since its release is third-party until it is released again, and its modules are
checked against the store. The shipped records count as approval because the distribution is the
trust root; the command needs no terminal because releases may run unattended, so what a release
changes in `workbench/shipped_approvals/` must be reviewed in its git diff.

### The approval gate

The gate takes the result of verifying a selection and approves it only when every module in the
install order is approved, reading only. A module is approved by its own `module` record; a module
whose type is exactly `module` can instead be approved by a `package` record that matches the
package's current hashes and lists the module with exactly its two hashes. Every other type needs a
record of its own. A refused verification, an empty selection and a malformed result are not
approved. The gate approves what the verifier hashed and not what an installer reads later, so an
installer must write from the verified bytes or verify and gate again from one snapshot, and must
set each package's first-party flag from the first-party rule above.

### Inert download

A package is brought into `cache/<id>/` as data only: the files under `package/` and a
`fetch.json` (source, ref, resolved commit, counts) beside them.

- **Sources.** An `https://` URL without credentials, an `ssh://` URL, a `file://` URL, or a local
  directory. Other transports, scp-style `host:path`, and anything starting with `-` or holding
  whitespace are refused. A ref is a branch, tag or commit name of letters, digits and `._/@+-`.
- **Nothing runs and nothing is checked out.** The ref is fetched into a private bare repository
  outside the store, created without hooks, with a scrubbed git environment, the user's and system's
  git configuration ignored, prompts off, only the file, https and ssh transports allowed, incoming
  objects checked, and no tags or submodules fetched. Files are read with `ls-tree` and `cat-file`.
- **The listing is checked before any content is read.** Every entry must be a regular file
  (a symbolic link or a submodule refuses the download), every path must pass the path validator,
  names that collide ignoring case are refused, and the limits are 2048 files, 16 MiB per file and
  64 MiB in total. Files get the default mode (0644 under the usual umask), or 0755 where git
  recorded the execute bit.
- **Resource limits.** Each git command runs in its own process group with capped output, a
  timeout and a limit on the size of any file it writes, and is killed with everything it started on
  an excess. A tree can share subtrees, so the listing is read incrementally.
- **Placement.** The files are written to a staging directory and moved into place with one rename;
  a failure leaves nothing in the cache. A cache directory is never reused. Nothing removes cache
  copies yet.
- **Limits.** This does not defend against a flaw in git's own handling of objects or in the
  network transport, and does not verify who runs the server; an `ssh` source uses the owner's ssh
  configuration; a process killed outright can leave a temporary or `.incoming-*` directory. Whatever
  reads a cached copy later must verify it again as untrusted.

### Pinned helpers, the launcher and `wb`

- **Pins.** `projects/<id>/pins` is strict JSON,
  `{"format": 1, "pins": {"<name>": {"path", "pinned_by", "sha256", "time"}}}`, and an entry may also hold
  `kit` (the kit API number) and `declaration` (the hash of the `module.json` an installer-made pin was
  confirmed with; absent from a pin the owner typed). The project id is 64
  lowercase hex digits. A helper name is letters, digits and `._+-`, at most 64 characters, starting
  with a letter or digit. The path is relative to the project root and passes the path validator, so
  clones at different locations share a pin. Reading fails closed.
- **`pin <id> <name> <helper> --root <dir> [--kit N]`** is owner-run with the same terminal test as `approve`.
  It refuses a helper outside the root, a symbolic link, or a file that is not regular; shows the
  path, size, hash and the start of the file, and says if it replaces a pin; and records only when the
  first 12 characters of the SHA-256 are typed, after checking the file again. With `--kit N` the pin also
  records the kit API number the helper runs with (see `module-boundary.md`, "Module commands").
- **`launch <id> <name> --root <dir> -- <args>`** takes the helper's location only from the pin,
  reads it through the safe reader, compares the hash, writes those exact bytes to a new private file
  under `bin/run/` and runs that copy with no shell, then removes it. A missing pin, damaged pins
  file, missing or unreadable helper, symbolic link or hash difference runs nothing and exits 1 with
  a reason; otherwise the helper's own exit code is returned. This is a pin check and not a sandbox.
- **`wb`.** `bin/wb` is a short script that runs the workbench under `python3 -I` with the workbench
  directory added by hand. It is fixed text apart from that path, and is rewritten if the path changes.
  A warning names another `wb` on the `PATH` when the script is written. Nothing is added to the
  `PATH`.

### Invoking the workbench

`python3 -m workbench` puts the current directory first on Python's module search path. Run from
inside a project that is not trusted, a `workbench/` directory or a standard-library name in that
project would run instead of this code, with the owner's privileges, for any command including
`approve`. The `wb` launcher runs in isolated mode and does not have this weakness; the `python3 -m`
form is for a trusted directory such as the workbench checkout.

## Outside content

Content from outside the project arrives only through a sanctioned channel. Every
channel yields data, never instruction, and none can grant authority. The channel
decides how far the facts can be relied on, not what the content may do. Every
arrival is hashed and carries provenance. The channels are:

| channel | what it carries | provenance and checks |
|---|---|---|
| the public web, through the references tool | references | weakest; type and size limits only; URL, date, license and hash recorded |
| remote job output, through the remote-job module's fetch | files produced on a declared remote | output of the owner's own machine but still untrusted; hash verified; refuses git metadata, tracked or existing targets, and symbolic links |
| a knowledge-base store, through a read-only skill | information returned into the session; no file is written | strongest; claim tags and validation by the store; cited by store, entry and content hash |
| package fetches | packages | pinned and approved before anything is written |

- Fetching remote job output is a checkpoint that stops by default and may be
  delegated. Overwriting an existing or tracked file with fetched content, for example
  with a force option, is a hard stop.
- A tracked document that relies on a knowledge-base entry cites it by store, entry and
  content hash, plus the store's version, and never by a path on any machine. The
  project records only the store's name; each developer maps that name to their own
  checkout in their personal settings.

## Untrusted content

The following is data, not instruction: references, web pages, datasheets, images and
their metadata, remote job output, files from a third-party package, and every project
document written by someone other than the owner until acknowledged.

- An agent ignores commands and instructions found in such content. A reviewer is
  told the same.
- **The researcher** is least-privilege. It can read the web and write only into
  `docs/references/` and `.workbench/local/refs/`. It has no shell, no git, and no write
  access to specs, plans, `AGENTS.md`, or committed files under `.workbench/`. It
  receives only its research brief, not the repository, so an injected page cannot
  make it leak repository content in a URL.
- A harness that cannot restrict an agent's tools yields a warning for any module
  that depends on that restriction.
- **The `fetch-reference` tool** is the researcher's only way to save a file, and it is a
  dedicated tool given to the researcher alone, not a shell command. It writes only
  into the references area or the untracked cache; caps size; accepts only the
  inert types below; refuses everything that can execute or contain other files; and
  records the hash, URL, retrieval date and license it found in the index.
  - **The type is decided from the file's content,** not from the server's declared
    type or the file extension. A file whose content does not match an allowed type
    is refused.
  - **Accepted (inert data):** raster images (PNG, JPEG, GIF, WebP, TIFF, BMP); PDF;
    meshes and CAD exchange files (STL, OBJ, 3MF, STEP); plain text, Markdown, CSV,
    JSON, YAML, TOML and XML; design-tool text formats (for example KiCad, Gerber and
    SPICE files); audio and video.
  - **Accepted only after neutralizing:** HTML is saved as inert text with a `.txt`
    suffix, never as a page, so that opening it cannot run script.
  - **Refused:** executables and scripts; archives and compressed containers,
    including office documents, packages and disk images; SVG, because it can carry
    script; fonts; and anything the content check cannot classify.
  - The list is closed. A type is added only by changing this specification.
- Photo metadata that reveals location is flagged and stripped from tracked copies.
  A fixed set of tools opens image files, to limit parser attacks. A reference whose
  license is unknown is kept untracked and cited by URL, date and hash.

## Loop caps

Every unattended loop has a cap, and exceeding it stops the run with a report:
review rounds (with a hard ceiling), retries of the same failure, and exchanges with a
second reviewer per checkpoint. The caps and their defaults are set by the way of
working in use, held as the `caps` setting and read with `wb settings` ("Checkpoint and cap settings, and the
edit gate"); there is no cap on increments inside an approved plan. A second identical failure stops and diagnoses
instead of retrying. No dollar ceiling is required.

## Residual risk

- A well-disguised plan can still steer the agent within the actions the owner has
  delegated. Hard stops, acknowledgement and the caps limit the damage.
- A harness without `permissions` leaves hard stops and the guarded store protected
  by instruction only.
- The guarded store shares the owner's account.
- A pin the owner types records no declaration and so stands for the whole module: a pull that rewrites the
  `module.json` and its manifest hash can widen the command's `arguments`, which are a filter and not a
  boundary (`module-boundary.md`). The helper must validate its own arguments. A pin made before the installer recorded
  declarations carries none and is updated at the next upgrade.
- The typed confirmation of `approve`, `pin` and the project write commands (`installer-interface.md`) is friction, not authentication, and a process that
  opens its own pseudo-terminal passes the terminal test. Only the harness deny rules stop an agent
  from running those commands.
- Shipped first-party approvals are trusted because the distribution is. Anything that can write the
  repository can add a package and release it.
- A hostile source can become the first pin for content that is identical to a legitimate commit. The
  pin is provenance and the content hash is what is approved, so this can only make a later re-fetch
  fail, not change what is installed.
- A downloaded copy stays in the cache with its hostile content until removed; nothing reads the cache
  without verifying it again.
- Running `python3 -m workbench` from an untrusted directory lets that directory's code run. Use the
  `wb` launcher there.
- A reviewer and an author can share a blind spot.

## Deferred

- **Running a command outside the agent.** The user-shell prefix is how the owner
  records an approval in Claude. Whether opencode has an equivalent is settled by
  `verify-opencode`; if it has none, the owner uses a separate terminal.
- **Image handling.** Which tools open image files, and how location metadata is
  stripped from tracked copies, are decided in the `researcher-fetch-tool` candidate.
- **Formats still proposals.** The formats in "Concrete formats" are fixed by the code at `format: 1`.
  The format of plan approvals is built ("Plan approval records"); the formats of
  delegated-approval records remain a proposal (the baselines format is built) until the way of working that
  uses them is built. The `caps` setting and the edit gate are built by plan `2026-10-22-checkpoint-settings-and-caps` ("Checkpoint and cap
  settings, and the edit gate"); the checkpoint names are in `code-work.md`.
- **Added hard stops.** A module may add hard stops, and the function that combines stops accepts
  additions, but a module declaration has no field to declare one and no module supplies any. The owner
  decides the field (a `module-contract` change) or defers it.
- **Cleaning up.** Nothing removes cache copies, shipped records of earlier releases, or leftover
  `bin/run/` directories of a launcher that was killed.

## Acceptance criteria

- With no personal settings, every checkpoint behaves as `stop`.
- *(Built by plan `2026-10-22-checkpoint-settings-and-caps`.)* With no `caps`, `wb settings` reports every default; a value that is not an
  integer from 1 to the ceiling is replaced by the default with a `settings:` note. `wb gate claude` refuses an
  edit while a plan under way is not approved, allows it otherwise, and refuses on any doubt.
- A module whose declaration or content differs from its approval is not installed,
  and nothing is written.
- A plan whose hashed region differs from the approved hash is not acted on. Changing
  only its status, review record or result leaves the approval valid.
- A committed `Status: Approved` line with no matching record in the guarded store is
  not an approval.
- With a harness that provides `permissions`, the floor appears as local deny or ask
  rules after attach, and a write to the guarded store is denied.
- A plan that omits its risks section still cannot cause a hard stop to be skipped.
- A change to `AGENTS.md` or a committed file under `.workbench/` by someone else
  stops the agent until the owner acknowledges it, unless the owner explicitly set
  that checkpoint to `delegate`.
- A pulled edit to a pinned helper is not run until the change is acknowledged.
- A helper that runs another module's command reaches it only through `wb run`: a command that is not
  installed, declared and pinned, or whose module lacks the capability asked for, is refused and nothing
  runs; a `wb` inside the project is never run; the caller's environment is not passed on.
- A reviewer that returns no verdict produces no approval.
- A plan with no record is `not approved` whatever its `Status:` line says; a record of
  an earlier region, process declaration or helper makes it `changed since approval`; a status, review-record or
  result edit leaves it `approved`; `approve-plan` writes nothing unless the command's two reports are equal and
  the typed prefix matches; the installer's text names no plan section.
- The neutral rule list is rejected if it contains an `allow` entry.
- A module that tries to remove a floor entry is refused.
- The researcher cannot run a shell command or write outside the references area;
  the `fetch-reference` tool rejects an executable, an archive, an SVG, an over-size
  file, and a file whose content does not match its declared type, and saves HTML only
  as inert text.
- Approving an upgrade preview does not require a separate acknowledgement of the
  files in that preview.

### Built and tested by `module-approvals`

- A record binds its kind, subject and both hashes: a changed declaration or content, or the same bytes
  under another subject, is not approved.
- `approve` and `pin` record only when standard input and output are terminals and the owner types the
  first 12 characters of the hash shown; piped input or output, a wrong answer, a package that fails
  verification and a package that changes while it is shown record nothing.
- A package approved from a source is bound by its content: a ref that later moves to different content
  is not approved, and the pinned commit's content still is.
- A download never checks anything out or runs anything, and refuses a symbolic link, a submodule, an
  unsafe path, a name collision, an oversize or over-numerous tree, and leaves nothing in the cache.
- Only an unchanged package in the distribution with a matching shipped record is first-party.
- The gate approves a selection only when every module has a matching record, and a package record
  never covers a `harness` or `process` module.
- A pinned helper whose bytes changed is not run until it is pinned again, and what runs is the bytes
  that were hashed.
- Through the `wb` launcher, code in the working directory does not take the place of the workbench.

# Trust, approval and untrusted content

Status: Current. Approved by the owner on 2026-10-19. The guarded store, the personal settings, approval
records, first-party shipped approvals, the approval request and gate, the owner-run `approve` and `pin`
commands, the inert download and the launcher are built (`module-approvals`), and "Concrete formats" records what
the code does. Plan approval, delegation, acknowledgement and the rendering into a harness are not built yet, and
their record formats and setting names remain proposals. The rules are the substance.

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
- Delegated approval is performed only by a small helper (see "Delegated
  approval"), which the agent may call and which checks before it writes. The
  helper and the launcher in "Pinned helpers" are components of the workbench
  itself: the installer installs them when it initializes the store. They are not
  shipped by any module.
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
  the helpers it expects. A module that blocks a core capability is flagged high
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
  by an installed, approved module.
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
- The helper is the only writer of delegated approvals. Its integrity is pinned (see
  "Pinned helpers").

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
  agent cannot run it: `wb install`, `wb upgrade`, `wb add`, `wb attach`, `wb approve`,
  `wb pin` and `wb release-approvals`. The read-only `wb preview` is not denied. The commands
  are listed in `installer-interface.md`. *(Required by that specification; not yet
  rendered by any harness module, which is for `claude-harness` and `opencode-harness`.)*

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
- A deliberate change the owner makes through the commit helper updates the baseline
  for the files changed.
- Approving an install or an upgrade preview updates the baselines for exactly the
  files in that preview, so the owner is not asked to acknowledge their own approved
  change.
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
  `{"format": 1, "pins": {"<name>": {"path", "pinned_by", "sha256", "time"}}}`. The project id is 64
  lowercase hex digits. A helper name is letters, digits and `._+-`, at most 64 characters, starting
  with a letter or digit. The path is relative to the project root and passes the path validator, so
  clones at different locations share a pin. Reading fails closed.
- **`pin <id> <name> <helper> --root <dir>`** is owner-run with the same terminal test as `approve`.
  It refuses a helper outside the root, a symbolic link, or a file that is not regular; shows the
  path, size, hash and the start of the file, and says if it replaces a pin; and records only when the
  first 12 characters of the SHA-256 are typed, after checking the file again.
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
working in use; there is no cap on increments inside an approved plan. A second identical failure stops and diagnoses
instead of retrying. No dollar ceiling is required.

## Residual risk

- A well-disguised plan can still steer the agent within the actions the owner has
  delegated. Hard stops, acknowledgement and the caps limit the damage.
- A harness without `permissions` leaves hard stops and the guarded store protected
  by instruction only.
- The guarded store shares the owner's account.
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
  The formats of plan approvals, acknowledgement baselines and delegated-approval records, and the
  setting names for checkpoints, remain proposals until the way of working that uses them is built.
- **Added hard stops.** A module may add hard stops, and the function that combines stops accepts
  additions, but a module declaration has no field to declare one and no module supplies any. The owner
  decides the field (a `module-contract` change) or defers it.
- **Cleaning up.** Nothing removes cache copies, shipped records of earlier releases, or leftover
  `bin/run/` directories of a launcher that was killed.

## Acceptance criteria

- With no personal settings, every checkpoint behaves as `stop`.
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
- A reviewer that returns no verdict produces no approval.
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

# Terms

Status: Current. Approved by the owner on 2026-10-19. The installer, the verifier, the first-party modules and the Claude harness
are built, and the definitions describe their behavior. Where a specification marks something as not built (a second harness, for
example), the term describes the intended behavior.

## Purpose and scope

This specification fixes the vocabulary used by every other specification and
decision in this repository, so that one word means one thing. It defines terms
only. Behavior, schemas and rules belong to the specifications that use them.

Non-goals: it does not define file formats, command-line interfaces or
algorithms, and it does not record decisions or their rationale.

## How to read this document

Each entry gives the term, what it means here, and what it is not, where a
confusion is likely. A term is written in backticks when it is a literal name,
path or field.

## The system

**workbench**
: The installer and orchestrator that creates and maintains projects, plus the
  first-party package it ships. Not a project, and not an AI tool.

**project**
: A user's repository that the workbench has set up. A project is installed from
  a chosen set of modules and is owned by its user afterwards.

**clone**
: One checkout of a project on one machine. Several clones of one project may use
  different harnesses.

**base**
: The content every project receives regardless of the modules chosen. It is not
  a module and has no type. It contains only what no module can supply, plus the
  empty slots that modules fill.

## Packaging

**package**
: A directory or repository that holds one or more modules and a package
  declaration. A package is the unit that is fetched, pinned and approved as a
  source. The workbench ships one first-party package. Anyone may publish another.

**module**
: A named unit of installable behavior inside a package. A module has a type,
  declares what it provides, requires and blocks, and ships files. A module's
  identity is `<package>/<module>`.

**type**
: A role the installer enforces a count on. The set of types is closed and owned
  by the installer. A module has exactly one type. The types are `harness`
  (exactly one per project), `process` (at most one per project) and `module`
  (any number, the default).

**module declaration**
: The data a module publishes about itself: its type, what it provides, requires
  and blocks, the paths it writes, and what it ships. Approval is recorded
  against the declaration together with the module's content.

**contract**
: The versioned definition of the declaration formats and the rules the installer
  applies to them. A package states which contract version it targets.

## Capabilities

**capability**
: A plain, case-sensitive string naming something a harness or module supplies,
  such as `skills` or `peer-review`. Capabilities share one namespace.
  Capability names are flat and coarse.

**provides / requires / blocks**
: The three lists in a module declaration. `provides` names what the module
  supplies. `requires` names what it needs, hard by default or marked soft.
  `blocks` names a capability the module cannot coexist with; any conflict stops
  the install and cannot be overridden.

**hard requirement / soft requirement**
: A hard requirement (the default) must be met or the install stops. A soft
  requirement is marked `soft`; when it is unmet the module installs and the
  feature that needs it is absent, with a message saying so.

**harness capability**
: One of `instructions`, `skills`, `agents`, `commands`, `hooks` and
  `permissions`. Only a module of type `harness` may provide one.

**helper**
: A tool expected on the machine's `PATH`. A module lists helpers separately
  from capabilities. The installer only checks that a helper exists and never runs
  it.

**shipped helper**
: A file a module lists in `ships` that runs at use time, through the launcher, after the owner has pinned
  it. It is not the same as a **helper**, a tool expected on `PATH`.

**kit**
: The small standard-library library, imported as `wbkit`, that the installer and Python helpers share
  for safe, bounded reading of project content and for reporting. It belongs to the workbench, not to any
  module, carries an integer API version, and is never pinned per project (`module-boundary.md`).

**runner**
: The fixed workbench file the launcher uses to start a Python helper: it loads the kit from beside
  itself, checks the kit version the module declared and runs the helper as `__main__`.

**module command**
: A pinned shipped helper that a module declares in `commands`, together with the first arguments it
  accepts. It is run with `wb run <command>`; the installer knows no command by name.

**module check**
: A pinned Python helper that a module declares in `checks`. `wb check` runs it and prints the `problem:`
  and `warning:` lines it reports.

**maintainer directory**
: The `tests/` or `tools/` directory of a module. It is hashed and approved with the module, never
  installed into a project and never run by the installer.

**slot**
: A named, empty extension point in a file. A module that owns a slot provides the
  capability `slot:<name>`. A module fills a slot with a block. In prose a slot is
  called "the `<name>` slot", and the capability form `slot:<name>` is written only
  where a capability is meant. `docs-index` is the slot in the base's docs README
  that modules fill with index entries. It is a slot, not a file.

**block**
: Content a module contributes into a slot, delimited by markers that name the
  module and the slot. A block belongs to the installer, not to the project's
  author, even though it sits inside the project's file. Not the level `block`.

## Harness

**harness**
: The AI agent runtime a clone uses, such as Claude or opencode. Where "harness"
  names the runtime, it is not a file or a module. The word is also the name of a
  module type and of the `harness/` directory in a module; the text writes "harness
  module" whenever the module is meant.

**harness module**
: The module of type `harness` that describes one harness: its directories, file
  formats, root file (or none), and the capabilities it provides. A project has
  exactly one harness module. A clone may have none attached.

**attach**
: Writing the files for one harness into one clone, from the project's pinned
  module set. Attach writes only per-clone output.

**harness files**
: The per-clone files a harness reads, such as a root instruction file and its
  skill, agent and command directories. Harness files are never committed.

**neutral**
: The reserved name for harness-agnostic module content, held in
  `harness/neutral/`. `neutral` is not a harness and no harness may use the name.

**override**
: A file under `harness/<name>/` that replaces, for that harness only, the
  translation of one neutral item. An item is matched by kind and name.

**exclude**
: An entry in a harness's optional manifest that stops one neutral item being
  installed for that harness, with a stated reason.

## State and storage

**committed**
: Tracked by git and shared by every clone. Also called *tracked*.

**untracked**
: Not tracked by git. It covers both scratch and per-clone harness files, and
  neither is shared between clones.

**tracked-pointer rule**
: Nothing committed in a document or workbench-managed file depends on untracked
  content. A tracked document cites an untracked reference by source URL, date and
  content hash, never by path.

**scratch**
: Untracked, agent-writable local state that grants no authority, held under
  `.workbench/local/`: debug output, the reference cache and index, and the local
  harness manifest (with the one exception its entry names).

**guarded store**
: The workbench's user-level store at `~/.config/project-workbench/`, outside any
  project, which the agent must not write. It holds approvals, acknowledgement
  baselines, pinned hashes and the owner's personal settings. It is not a
  harness's global configuration.

**project ID**
: A hash of a unique seed generated at install and stored in the committed
  manifest. It names a project's directory in the guarded store.

**manifest**
: A record the workbench keeps about a project. The committed manifest lists
  modules, versions, hashes and file ownership and never names a harness. The
  local manifest has its own entry under "Permissions and approval".

**lock**
: The part of the committed manifest that pins each package and module to an exact
  version and content hash.

**owner class**
: How a file the installer wrote is treated on upgrade: module-owned, seeded,
  a slot block, or living or historical content.

## Authority and process

**process module**
: A module of type `process` that supplies a way of working, such as `code-work`
  for programming. A project has at most one. "Process module" always means the type.

**way of working**
: The general idea that a process module implements: how work is planned, reviewed
  and recorded in a project. Not a type and not a module.

**groundwork**
: The module holding specs, roadmaps, decisions and references, shared by every
  process and usable without one.

**checkpoint**
: A named point at which the agent may need authority before continuing, such as
  approving a plan or pushing a shared branch. A checkpoint stops by default: its level is `block`. The approver may set it, in the
  personal settings, to `ask`, `delegated` or `none`, where its key offers that level; `delegated` takes effect where a command
  declares a gate.

**delegation**
: The approver letting the converged verdict of a second reviewer, supplied by a `peer-review` provider, stand for a checkpoint:
  the level `delegated`, written `delegate` in the checkpoint settings. Delegation is a personal setting held in the guarded
  store, never project policy.

**hard stop**
: An irreversible or externally-effecting action that always stops for the owner,
  whatever a plan or a reviewer says.

**floor**
: The set of hard stops that ship with the workbench and apply to every project.
  Modules may add to the floor; nothing may remove from it.

**approval**
: A record, in the guarded store, that the owner (or a delegate) accepted a
  specific plan or module. An approval binds to a content hash; a changed hash
  needs approving again. A status line written in a committed file is never an
  approval.

**acknowledgement**
: The owner confirming they have seen a change to a file they had not reviewed.

**peer review**
: Review performed by a reviewer other than the author, supplied by a module that
  provides the capability `peer-review`. It can give findings without being
  delegated the verdict. The capability is named `peer-review`; the section of a
  plan that records a review is named "Review record", so the two are never
  confused. The first-party provider is specified in `review-engine.md`.

**model bridge**
: A thin module for one vendor that provides the capability `model-bridge`. It takes a prompt
  and options, asks the vendor's program one read-only question and prints one JSON object. It holds no state and
  no policy; it is run only through the launcher (`model-bridge.md`).

**launcher**
: The small workbench component, run as `wb`, that the installer places in the guarded
  store. It checks a shipped helper's hash against a pin and only then runs it. It is not
  shipped by any module.

**delegation helper**
: The small workbench component that is the only writer of a delegated approval. It
  checks the owner's setting and the review evidence before it writes. It is not
  shipped by any module.

**inert download**
: Fetching a package into a cache in the guarded store as data only, so that its
  declaration can be shown for approval. Nothing is executed and nothing is written
  into a project.

**work record**
: A plan whose `Candidate:` line names a roadmap candidate and whose status is
  `Completed`. A candidate is complete when a work record refers to it.

## Permissions and approval

**owner**
: The person who decides at a checkpoint on a machine that holds the workbench's guarded store: who approves, accepts,
  acknowledges and sets levels. Read it with **approver**. It names a role at the moment of acting, not the author of a document
  and not a named individual.

**approver**
: The person who may approve a plan, accept a decision, acknowledge a change or set a level, defined by that capability and not by
  having written the document. A specification that says "the owner" at a checkpoint means the approver. A record of what happened
  names the person who acted by their git identity, `Name <email>`, in the form the accepted record
  `2026-10-29-approvals-name-the-approver-by-git-identity` sets, and, since 2026-10-29, the installer does this for every approval
  a person makes (plan approvals, module and package approvals, pins made with `pin`), read from the account's global git
  configuration (the shipped records and the pins an install, upgrade, add or acknowledge makes keep a role as their maker), together with
  `via`, the level the run was authorized under: `terminal`, `ask`, `none` or `delegated` (`trust-and-approval.md`, "The approver
  and how it was authorized"). That identity is an attribution and not authority.

**owner-run command**
: A command whose default level is `block`: by default only the owner runs it, and the harness denies it to an agent.
  The approver may set the level of its key to one the key offers (`command-permissions.md`, "Which levels a key offers"): `none`
  for an installer command (and `ask` for `wb release-approvals`, with the digest of its preview), `ask`, `delegated` or `none` for
  `approve-plan`, `ask` or `none` for `accept-decision`, and `ask` or `none` for a module command that declares `levels`. `delegated` exists only where a command declares a gate. An agent may then run the command at that level. A key that
  offers only `block`, such as `wb rerender`, stays with the owner. It does not mean that an agent can never run it.

**agent-safe command**
: A command an agent may run by default, because it only reads or runs a pinned helper that checks its own pin. One that has a key
  defaults to `none`, and the approver may set it to `block`. The hook entry points and the words that only dispatch (`wb run`,
  `wb preview`) have no key, and `wb delegate-approve-plan` reaches the key `approve-plan` (`command-permissions.md`, "`wb settings`").

**level**
: How a key is gated, from strictest to least strict. `block`: the agent never runs it, and the harness denies it where a command
  exists to deny. `ask`: the agent runs it after the approver confirms a harness prompt that carries the digest of a read-only
  preview. `delegated`: the agent runs it after a gate that the command declares has passed, such as a converged review. `none`:
  nothing stops it, and a run that changes something is logged. A key offers only some of these (`command-permissions.md`, "A level
  for every command"). Not the slot **block**.

**key**
: The name a level is set under: a declared checkpoint such as `approve-plan`, or a command in the `wb` spelling, such as
  `wb install` or `wb run <command> <argument>`.

**levels table**
: The `levels` object of the personal settings (version 2), which maps a key to a level. A key's level is its table entry, else its
  checkpoint reading (`stop` as `block`, `delegate` as `delegated`), else its shipped default.

**pin**
: The record, in the guarded store, of a shipped helper's path (relative to the project root) and its SHA-256. The launcher runs a
  helper only while its bytes still match the pin.

**rendering record**
: The record the installer writes in the guarded store at attach and at re-render: the hash of the permissions file it rendered,
  the digest of the levels table it rendered from, and for every key whether a `deny`, an `ask` or nothing was rendered. While it
  does not match, a relaxed key reads `block` (`command-permissions.md`, "Rendering").

**rerender**
: `wb rerender`. It renders an attached clone's harness files and permissions again from the installed modules and the current
  levels table, carries the live permissions file's `allow` rules into the new one and shows each in a preview. It is owner-run
  and needs a terminal at every level (`harness-rerender.md`).

**local manifest**
: The record, in scratch (`.workbench/local/harness.json`), of the attached harness and the hash of each rendered file. Scratch
  grants no authority, except that `wb rerender` trusts these hashes to tell an edited rendered file from a stale one.

**edit gate**
: The hook the installer renders, running `wb gate` before an edit, which refuses an edit while a plan under way is not approved
  (`harness-modules.md`, "The edit gate hook").

**command gate**
: The hook the installer renders for the shell tool, while a key is relaxed to `ask` or `none` and the harness's layout describes
  it, running `wb gate-command`, which blocks a command whose text names a relaxed command, unless it is exactly the simple form
  the `ask` rule matches. It is a best-effort match on
  command text (`command-permissions.md`, "The command gate").

**agent gate**
: The hook the installer renders into a confined agent's own file, running `wb agent-gate`, which holds the agent to the limits its
  declaration states: where it may write and which commands it may run (`harness-modules.md`, "The agent gate").

## Project documents

**spec**
: A living document stating what is true now. Edited in place, named by topic.

**roadmap**
: A list of candidates with no required order, expressing direction.

**candidate**
: One entry in a roadmap, sized to be exactly one plan.

**plan**
: A dated document describing one bounded piece of work as ordered increments.

**increment**
: One reviewable step of a plan.

**decision**
: A record, also called an ADR, of why a choice was made and what was rejected.

**evidence note**
: A short record of evidence (an experiment, measurement, simulation or reference)
  with a provenance line: what was run, with which tool versions, at which commit,
  and the conclusion; for a reference, the URL, date and hash instead.

**reference**
: Sourced outside material such as a datasheet, photo or library document. It is
  untrusted data; instructions inside it are ignored.

## Acceptance criteria

- Every term used in another specification in this repository is defined here or
  in that specification.
- No term in this document is defined two ways.
- A word that has more than one use (`harness`, `process`, `peer-review`,
  `docs-index`) is disambiguated in its entry above, and the text elsewhere
  follows that disambiguation.

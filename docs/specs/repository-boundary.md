# Repository boundary, manifests and upgrades

Status: Current. Approved by the owner on 2026-10-19; implementation has not started. File names and
marker syntax are proposals; the rules are the substance.

Terms are defined in `terms.md`. The declarations the installer reads are defined in
`module-contract.md`.

## Purpose and scope

This specification defines what the workbench puts where: what is committed, what
is per-clone, what is scratch and what is guarded; what the two manifests record;
what each installer operation does and refuses to do; and how an upgrade avoids
destroying work in progress or history.

Non-goals:

- How approvals are recorded and judged. That is the trust and approval
  specification. This one names the places approvals live and requires that they
  exist.
- The translation of neutral items into a harness's formats.
- The content of any module.
- Any commit or push. The installer never commits, pushes or publishes.

## Assumptions and constraints

- A project is a git repository. The installer assumes git, a POSIX shell and
  `python3` unless the project declares otherwise.
- The installer writes only inside the target project, plus the guarded store. It
  does not follow symbolic links when writing, and it scrubs `GIT_*` environment
  variables before running git.
- Several developers share one remote, and each may use a different harness. The
  committed repository must be sufficient and consistent for all of them.
- A rogue contributor may commit anything. Nothing the installer or an agent does
  may take authority from committed text.

## The four places

| place | where | tracked | who may write | holds |
|---|---|---|---|---|
| committed | the project tree | yes | the installer and the project's authors | modules' project files, `AGENTS.md`, docs, `.workbench/manifest.json`, `.workbench/<package>/<module>/` |
| per-clone harness files | the project tree, harness-specific paths | no, never | the installer (at attach) | a harness's root file, skills, agents, commands, local settings |
| scratch | `.workbench/local/` | no | the installer and the agent | the local manifest, debug output, the reference cache and untracked index |
| guarded store | `~/.config/project-workbench/` | outside the project | the owner only | approvals, acknowledgement baselines, pinned hashes, personal settings |

- Scratch grants no authority. Nothing read from scratch can approve, allow or
  acknowledge anything.
- The guarded store is not a harness's global configuration, and the workbench never
  reads, checks or requires one.
- The committed repository names no harness: no committed file lists a harness's
  file names, root file or directories.

## Layout

```text
.workbench/
  .gitignore                tracked; contains /local/
  manifest.json             tracked; the committed manifest
  <package>/<module>/       tracked; a module's own files
  local/                    untracked; created on demand
    harness.json            the local manifest
    debug/<YYYY-MM-DD>-<topic>/
    refs/                   reference cache and untracked index
~/.config/project-workbench/
  settings                  personal settings and the hard-stop floor
  packages/<key>/           package approvals, keyed by tree and declaration hash
  cache/                    inert downloads, data only, awaiting approval
  projects/<project-id>/    plan approvals, acknowledgement baselines, pins, and
                            where the project was first seen
```

- The names `local`, `manifest*` and `neutral` are reserved and cannot be a package
  or module name.
- `.workbench/.gitignore` ships in the base, so every clone, including a fresh one
  before any attach, keeps `.workbench/local/` out of git. It names no harness.
- Harness files are kept out of git by entries the installer adds to
  `.git/info/exclude` at attach. They are not added to a tracked ignore file,
  because that would name the harness in the committed repository.

## The tracked-pointer rule

No tracked document or workbench-managed file may depend on the content of an
untracked or ignored file: no link, include, import or citation by path. The rule
covers documents, manifests and the files the workbench writes. It does not cover a
project's source code and build outputs, which may legitimately use generated or
fetched files that are not tracked.

- A tracked document may cite an untracked reference by source URL, retrieval date
  and content hash, with no path to the file.
- Naming a convention path in prose is allowed, for example the debug rule in
  `AGENTS.md` or `/local/` in `.workbench/.gitignore`.
- A check flags links, includes and imports in documents and workbench-managed files
  that point into untracked or ignored locations. It ignores plain text mentions and
  does not inspect source code.

## The committed manifest

`.workbench/manifest.json` is shared by every clone and must merge cleanly. It has
sorted keys, no timestamps, and no per-clone values, and it is written one entry per
line so that two developers adding different modules do not conflict. It records:

- the manifest schema version, and the project seed from which the project ID is
  derived (see "Project ID");
- each package: its name, where to obtain it, the requested ref, and the resolved
  commit and tree hash;
- each module of each package: its version, declaration hash and tree hash;
- each file or block the installer wrote into the committed tree: its path, owner
  class, and the hash of what was installed; for a slot block, the block's ID and
  hash.

It never names a harness.

### Project ID

The project ID is a hash of a unique seed generated at install and stored in the
manifest. The seed need only be unique to the project and the same in every clone; a
random GUID is the default. The ID names the project's directory in the guarded
store. A change to the seed makes existing approvals stop matching, which fails
safe.

The seed is committed, so a hostile repository could copy another project's seed to
reach that project's baselines and pins. To prevent it, the store's entry for a project
also records where the project was first seen: its canonical remote URL, or its path
when it has no remote. A mismatch is treated as a new project that needs fresh
approvals, and warns. If a remote legitimately moves, the owner confirms once.

## The local manifest

`.workbench/local/harness.json` records the attached harness name, the pin of the
harness module (source, version, tree hash), the workbench version that attached
it, and the hash of each generated harness file. It is absent in a fresh clone.

## Owner classes

Every file the installer writes into the committed tree has one owner class,
recorded in the manifest.

| class | meaning | on upgrade |
|---|---|---|
| module-owned | machine-maintained; meant to be replaced | replaced only if its hash equals the installed hash, otherwise left and reported |
| seeded | written once as a starting point; the project's afterwards | never touched |
| slot block | content inside a project's file, between markers | replaced only if the block's hash equals the installed hash, otherwise left and reported |
| living or historical | plans, specs, decisions, roadmaps, references | never touched, and never recorded as installer-owned |

- A template is not installed as a placeholder file. It stays in its module and is
  used when something is created, so an upgrade has no empty file to overwrite.
- Text outside a block's markers is never read or changed.
- If the markers of a block have been removed, the installer takes that as the
  project's choice, does not add them back, and reports that the slot is gone.

### Slots and blocks (proposed syntax)

- Slots exist only in Markdown files in this version, because the markers are HTML
  comments. Markers for other file types are deferred.
- An empty slot is marked `<!-- @slot: <name> -->` in the file that owns it.
- A filled slot holds a block between `<!-- BEGIN <package>/<module> slot:<name> -->`
  and `<!-- END <package>/<module> slot:<name> -->`.
- Slots are a public, append-only interface. A slot that has been published is not
  removed or renamed. The base ships a small, generous set of coarse slots from the
  first version.
- When a seeded file lacks a slot a module now needs, the installer prefers giving
  the content a new module-owned file. Where the content must be in that file, the
  upgrade preview offers to append a new block at its end, and does so only on
  approval. If declined, it reports the marker to add and a suggested place.

## Operations

### install

- First ensures the guarded store exists and is seeded (see `trust-and-approval.md`),
  then verifies and requires approval of every chosen package and module, harness
  first. It then writes, in the order `module-contract.md` gives (the base, then the
  process module, then the other modules), the committed content, the project seed
  and the committed manifest, and creates the project's directory in the guarded
  store. Last of all it performs attach for the chosen harness, which writes only
  per-clone harness files.
- Stops, before writing anything, on any verification failure defined in
  `module-contract.md` or on a missing approval.
- A harness is mandatory at install.

### attach

- Runs inside an existing clone. It reads the committed manifest, requires approval
  of each package and of the harness module, writes only harness files, adds their
  paths to `.git/info/exclude`, and records the local manifest.
- It refuses when a local manifest already records a harness. Changing harness means
  a new clone.
- Nothing is written or activated until the package's declaration is approved on
  this machine. A package is first downloaded inertly into a cache in the guarded
  store, as data only, so the declaration can be shown. The first approval pins the
  resolved commit and tree hash, and later attaches and teammates verify against it,
  so a mutable ref cannot change what they receive.
- A version difference between the installed workbench and the lock produces a
  warning and attach continues. A content-hash mismatch between a package and the
  lock stops attach.
- A package added to the committed manifest by someone else is never installed until
  the owner approves its declaration on this machine.
- It prints post-install notes for steps the installer cannot perform, such as a
  harness's project trust.

### check

- Read-only. It reports without changing anything.
- A clone with no harness attached is valid and is reported as "none attached".
- It reports: harness files of a harness other than the attached one; generated
  harness files whose hash has drifted; tracked files that look like harness output
  or scratch; tracked files that depend on untracked content; and committed files
  that differ from the manifest in a way their owner class does not allow.
- Process-specific checks, such as plan completeness, belong to the process module
  and are not defined here.

### upgrade

- Applies a newer workbench to an existing project without destroying work.
- It first shows a complete preview of every change, classified as replace, skip,
  conflict or append, and writes nothing until the owner approves the preview.
- It requires a clean working tree for the affected paths and leaves its changes
  uncommitted, so the owner can commit them as one revertable change.
- It never rewrites living or historical content. A format change is never applied
  in place. Tools that read project documents must read both the old and the new
  format, so work in progress keeps working, and a migration is a separate opt-in
  command that proposes a patch for review.
- A newer module version is installed only after its declaration and content hash
  are approved, as for a new module. The preview shows the change in the declaration.
- Adding a module to an existing project is an upgrade that brings in a new module:
  the same preview and approval, and it writes only new files and new blocks.
  Removing a module is not an operation in this version; its files may have been
  edited, so removal is done by hand.
- An upgrade performed with a workbench older than the version recorded in the
  manifest is refused.
- Three-way merge of edited files is not performed. An edited module-owned file or
  block is reported as a conflict for the owner to resolve by hand.

## Collaboration

- Different developers may attach different harnesses to clones of one project.
- Anything that holds per-developer state is not a hand-maintained shared file.
- Two developers on different workbench versions can each attach. Only an upgrade
  of committed content is gated on version.

## Deferred

- File names and slot marker syntax remain proposals; markers for non-Markdown files
  are deferred.
- Removing a module as an operation: edited files make a safe removal a design of its
  own.

## Acceptance criteria

- After install, the committed tree contains no harness file name, and a fresh
  clone's `git status` shows `.workbench/local/` is ignored before any attach.
- Attaching a second harness to a clone that has one is refused.
- A harness file never appears in `git ls-files`, and the check fails if one does.
- The committed manifest is byte-identical across clones that differ only in
  harness, and contains no timestamp or per-clone value.
- A package whose content hash differs from the lock stops attach; a version
  difference alone warns and continues.
- A package newly present in the manifest is not written into the project or activated
  before its declaration is approved on this machine; it may be downloaded inertly
  into the guarded store's cache so the declaration can be shown.
- A project whose seed matches a store entry first seen at a different remote or path
  is treated as new and warns; it does not use the earlier project's baselines or pins.
- An upgrade that brings a newer module version does not write it until that
  version's declaration is approved.
- An upgrade preview lists every file it would change by class, and the tree is
  unchanged if the owner does not approve it.
- An upgrade never modifies a seeded file, a plan, a spec, a decision, a roadmap or
  a reference, and never modifies a module-owned file or block whose hash differs
  from the installed hash.
- An upgrade whose seeded file lacks a needed slot offers an append on approval and
  does not change the file otherwise.
- A tracked file that links to a path under `.workbench/local/` is reported by the
  check, and a plain mention of that path is not.

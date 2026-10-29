# Repository boundary, manifests and upgrades

Status: Current. Approved by the owner on 2026-10-19. The guarded store, with its approvals, cache, pins
and launcher, is built (`module-approvals`) and the layout below records it; attach and check are built
(`claude-harness`); upgrade and add are built (`ownership-and-upgrade`). `base-and-manifests` built the base, the committed
manifest, the seed, the baselines and `install` (the formats below are those it wrote); `claude-harness`
added the attach step.
File names and marker syntax are as built.

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
  reads, checks or requires one. This is to be amended: the accepted design
  `2026-10-24-installer-reads-global-settings-on-request` lets the installer's own code read a harness's global configuration,
  read-only, through an owner-run command that needs a terminal. That amendment and that command are pending and neither is built,
  so today the sentence holds as written.
- The committed repository names no harness: no committed file lists a harness's
  file names, root file or directories.

## Layout

```text
.workbench/
  .gitignore                tracked; contains /local/
  manifest.json             tracked; the committed manifest
  <package>/<module>/       tracked; a copy of the module's whole tree
  local/                    untracked; created on demand
    harness.json            the local manifest
    debug/<YYYY-MM-DD>-<topic>/
    refs/                   reference cache and untracked index
~/.config/project-workbench/
  settings                  personal settings and a copy of the hard-stop floor
  packages/<key>/approval.json
                            module and package approvals, keyed by kind and hashes
  cache/<id>/               an inert download: package/ (the files) and fetch.json
  projects/<project-id>/    one directory per project
    pins                    pinned helpers: path relative to the project root, SHA-256
    seen                    where the project was first seen (written by install)
    baselines               acknowledgement baselines, path to SHA-256 (written by install,
                            upgrade, add and acknowledge)
    plan-approvals          plan approvals: plan path, region hash, approver and time (written by
                            approve-plan and delegate-approve-plan; `trust-and-approval.md`)
  bin/wb                    the launcher script, fixed text apart from one path
  bin/run/<uuid>/<name>     a private copy of a pinned helper, only while it runs
```

- The store and its directories `packages/`, `cache/`, `projects/`, `bin/` and `bin/run/` are real
  directories owned by the current user with mode exactly `0700`; anything else is refused. The
  formats of the files in it are in `trust-and-approval.md`, "Concrete formats".
- The names `local`, `manifest*` and `neutral` are reserved and cannot be a package
  or module name.
- `.workbench/.gitignore` ships in the base, so every clone, including a fresh one
  before any attach, keeps `.workbench/local/` out of git. It names no harness. Its content is
  the single line `/local/` and a final newline.

### The base

The base is the content the workbench itself puts in every project before any module. It is part
of the workbench distribution, in `base/` at the distribution root, and is trusted as the
workbench code is (`trust-and-approval.md`, the distribution is the trust root); it is not a
module, has no type and has no approval record. Its tree hash and the workbench version are
recorded in the committed manifest. *(Built by `base-and-manifests`.)*

- `AGENTS.md`: the project's policy headings and the `policy` slot marker. Seeded.
- `README.md`: a stub for the project's purpose, how to start, how to test and where its documents are, with
  placeholders in angle brackets and links only to `AGENTS.md` and `docs/README.md`. It names no module and holds no
  slot marker. Seeded.
- `docs/README.md`: an index of the project's documents and the `docs-index` slot marker. Seeded.
- `.workbench/.gitignore`: generated, not stored. Module-owned.
- The base owns exactly two slots, `policy` (in `AGENTS.md`) and `docs-index` (in
  `docs/README.md`). They are always present and a module cannot own either: a slot has one
  owner.
- The base names no harness file and contains no executable.
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
- Naming a convention path in prose is allowed, for example the debug path
  `.workbench/local/debug/` or `/local/` in `.workbench/.gitignore`.
- A check flags links, includes and imports in documents and workbench-managed files
  that point into untracked or ignored locations. It ignores plain text mentions and
  does not inspect source code.

## The committed manifest

`.workbench/manifest.json` is shared by every clone and must merge cleanly. It has
sorted keys, no timestamps, and no per-clone values, and it is written one entry per
line so that two developers adding different modules do not conflict. It records:

- the manifest schema version, and the project seed from which the project ID is
  derived (see "Project ID");
- the base's tree hash and the version of the workbench that installed;
- each package: its name, where to obtain it, the requested ref, and the resolved
  commit and tree hash;
- each module of each package: its version, declaration hash and tree hash;
- each file or block the installer wrote into the committed tree: its path, owner
  class, and the hash of what was installed; for a slot block, the block's ID and
  hash.

It never names a harness.

**Format (built by `base-and-manifests`).** `.workbench/manifest.json` is UTF-8 JSON
with a final newline. Top-level keys are sorted: `base`, `files`, `packages`, `seed`, `version`,
`workbench`. `version` is the schema version, 1. `base` is the base's tree hash. `workbench` is
the installing workbench's version. `packages` is a list, one object per line, sorted by name,
each with `name`, `source`, `ref`, `commit` and `tree` and `modules` (sorted objects with
`name`, `version`, `declaration` and `tree`). `files` is a list, one object per line, sorted by
path, each with `class`, `hash`, `path`, and for a block `slot` and `block`. A harness module is
omitted, and a package that holds only the harness is omitted whole, because the manifest never
names a harness. A package source is recorded without any user name, password or query. A
serializer written for the purpose, not a library's formatting, produces the layout, so the
one-entry-per-line shape does not depend on a library, and a parser refuses anything else
(unsorted keys, a duplicate key, an unknown key, a wrong type).

### Project ID

The project ID is a hash of a unique seed generated at install and stored in the
manifest. It is the SHA-256 of the seed in lowercase hex, 64 digits, which also makes it safe as a
directory name; the store refuses any other form. The seed need only be unique to the project and the same in every clone; a
random GUID is the default. The ID names the project's directory in the guarded
store. A change to the seed makes existing approvals stop matching, which fails
safe.

The seed is committed, so a hostile repository could copy another project's seed to
reach that project's baselines and pins. To prevent it, the store's entry for a project
also records where the project was first seen: its canonical remote URL, or its path
when it has no remote. A mismatch is treated as a new project that needs fresh
approvals, and warns. If a remote legitimately moves, the owner confirms once.

**A local package directory** given to `install` is recorded in the manifest as the source
`local:<package name>` and with no ref or commit, so that no path of this machine is committed.
A source that is a URL is recorded without its credentials, query or fragment.

**The seed and the first-seen record.** The seed is a random UUID4 string. `install`
writes `projects/<id>/seen` as strict JSON, `{"format": 1, "kind": "path", "value": "<resolved
absolute path of the target>"}`. Reading a remote needs `.git/config`, which is hostile input,
so `install` records the path and no remote; a freshly initialized repository has no remote
anyway. When the target was an existing lone `.git`, `install` warns that no remote was
recorded. Recording and comparing a remote is settled by the candidate that first meets a
project in a second clone (at attach). `attach`, `upgrade` and `acknowledge` read `seen` and compare its path with
the project's resolved path, and refuse a project first seen at another path as a new one. No remote is compared.

**Baselines.** `install` writes `projects/<id>/baselines` as strict JSON,
`{"baselines": {"<path>": "<sha256 hex of the bytes written>"}, "format": 1}`, with sorted
keys, for exactly the files in the approved preview. Reading, comparing and acknowledging
were built by `ownership-and-upgrade`; `upgrade` and `add` replace the entries for exactly the
files they write and `acknowledge` for exactly the files it lists.

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
- **Classes at install.** The base's `AGENTS.md`, `README.md` and `docs/README.md` are `seeded`.
  `.workbench/.gitignore` is `module-owned`, as is each file under a module's namespace
  `.workbench/<package>/<module>/`. A file written from a module's `writes` is `seeded`. A
  filled block is a `slot block`. The declaration has no field to choose the class, and
  `ownership-and-upgrade` defers one: the fixed mapping stands, and a field can be added later
  without breaking it *(owner)*.
- **A kept seeded file** *(decision `2026-10-25-adopt-an-existing-repository-without-editing-it`)*. `adopt` finds a seeded path that already
  exists in the directory it adopts. It keeps the file and records it as `seeded` with the hash of the bytes there,
  not the hash of the seed, because the manifest records the bytes the installer last saw and "seeded with an entry is
  skip always" then means a later edit changes nothing. The file's slot blocks are not filled by `adopt` and have no
  entry; `upgrade` offers them.
- **This repository's own seeded files may differ from the installer's.** `install` cannot be run on a directory
  that has content, and a seeded file is the project's afterwards, so equal bytes are not the test of agreement.
  `tests/test_self_hosting.py` installs the first-party modules into a scratch directory, and
  `tests/fixtures/self_hosting_dispositions.json` records for each seeded path whether this repository's file is
  identical to the seed, diverged from it or absent; the test fails when a seeded path or slot has no record.
- **Classification on upgrade** *(built by `ownership-and-upgrade`)*. Each path of
  the desired state is compared with its manifest entry and the disk:
  no entry and absent is **create**; no entry and present is **conflict**; module-owned with
  the desired hash equal to the installed one is **skip**; module-owned and different, disk
  equal to installed, is **replace**, disk different is **conflict**; module-owned and absent is
  **conflict** (not restored); seeded with an entry is **skip** always; a slot block with no
  entry is **create** where its slot marker is present and **append** where it is not; a block
  with an entry, text equal to installed, is **replace** when the desired block differs and
  **skip** otherwise, and edited is **conflict**; a block whose markers are gone is **skip**,
  reported "slot gone"; an entry with no counterpart in the desired state is **skip**, reported
  "left in place". Nothing is ever deleted. An appended block is followed by its slot's marker
  line, so the slot is an ordinary filled slot afterwards. As built, a path's class comes from the
  declaration or the base and never from the manifest (a different class in the manifest is a
  conflict); every block edit needs its file recorded as seeded, present and readable; a seeded
  file keeps its recorded hash whatever blocks it receives; a module-owned manifest entry outside
  `.workbench/` is a conflict; and `add` plans only creates, appends and the manifest.
- **A module's namespace holds a copy of its whole tree** (declaration, templates, files and
  the rest), because a template stays in its module and is used when something is created. A
  harness module writes nothing committed.
- Text outside a block's markers is never read or changed.
- If the markers of a block have been removed, the installer takes that as the
  project's choice, does not add them back, and reports that the slot is gone.

### Slots and blocks

- Slots exist only in Markdown files in this version, because the markers are HTML
  comments. Markers for other file types are deferred.
- An empty slot is marked `<!-- @slot: <name> -->` in the file that owns it.
- A filled slot holds a block between `<!-- BEGIN <package>/<module> slot:<name> -->`
  and `<!-- END <package>/<module> slot:<name> -->`.
- **A filled slot keeps its marker.** The file holds, in install order, one BEGIN/END block
  per filler, then the `<!-- @slot: <name> -->` marker line, so a later module can add its
  block before the marker and the interface stays append-only. A fill source that contains a
  marker line of its own is refused. *(Built by `base-and-manifests`.)*
- Slots are a public, append-only interface. A slot that has been published is not
  removed or renamed. The base ships a small, generous set of coarse slots from the
  first version.
- When a seeded file lacks a slot a module now needs, the installer prefers giving
  the content a new module-owned file. Where the content must be in that file, the
  upgrade preview offers to append a new block at its end, and does so only on
  approval. If declined, it reports the marker to add and a suggested place.

## Operations

This section says what each operation does and refuses to do. How a command is invoked, how
its target is named and checked, its arguments and options, the preview and its approval,
the output and the exit codes are in [`installer-interface.md`](installer-interface.md) and
are not repeated here.

### install

- First ensures the guarded store exists and is seeded (see `trust-and-approval.md`),
  then verifies and requires approval of every chosen package and module, harness
  first. It then writes, in the order `module-contract.md` gives (the base, then the
  process module, then the other modules), the committed content, the project seed
  and the committed manifest, and creates the project's directory in the guarded
  store. Last of all it performs attach for the chosen harness, which writes only
  per-clone harness files.
- **`.git`.** A target that has no `.git` is given an empty one by `install` itself. Git is not
  run: `install` makes `.git` with `mkdir` (which refuses an existing path, a link included) and
  writes a fixed skeleton through descriptors it holds, so no program resolves a path inside
  the target. The skeleton is `HEAD` (`ref: refs/heads/main`), a `config` of four `[core]` keys
  and the empty `objects/` and `refs/` directories, and its hash is covered by the plan's
  digest. A target that already holds a lone `.git` is used as it is, and its configuration is
  never read or run.
- **The attach step (built by `claude-harness`).** The harness module is required, verified
  and approved as above, and `install` attaches as its last step. A harness module declares no
  `writes` or `fills`, because its files are per-clone and a committed file would name the
  harness.
- Stops, before writing anything, on any verification failure defined in
  `module-contract.md` or on a missing approval.
- A harness is mandatory at install.

### adopt *(decision `2026-10-25-adopt-an-existing-repository-without-editing-it`)*

- Installs the selected modules into a directory that has its own real `.git`, has content and has no `.workbench`.
  It does what `install` does for every path that does not exist, and it writes nothing into a path that does. It
  does not create `.git`, does not attach, and does not edit an existing file: no marker is added and no block is
  appended. The outcomes per path (create, keep, refuse, not filled), the order and the exit codes are in
  `installer-interface.md`.
- A kept seeded file is recorded in the manifest as `seeded` with the hash of the bytes there. A path a module owns,
  or one of the wrong type, refuses the whole command with every conflict listed.
- The result is an existing project for every other operation. The blocks that belong in a kept file are offered by
  `upgrade`; the harness is attached by `attach`.

### attach

- Runs inside an existing clone. It reads the committed manifest, requires approval
  of each package and of the harness module, writes only harness files, adds their
  paths to `.git/info/exclude`, and records the local manifest.
- It refuses when a local manifest already records a harness. Changing harness means
  a new clone.
- Nothing is written or activated until the package's declaration is approved on
  this machine. A package is first downloaded inertly into a cache in the guarded
  store, as data only, so the declaration can be shown. The approval binds the package's
  content by its declaration and tree hashes, and the first approval from a source also
  records the resolved commit as provenance; identical content reached by another commit is
  the same approval and the first record is kept. A teammate's `approve` fetches the recorded
  commit, and attach, which never fetches, reads the cache that filled and verifies the tree hash
  against the approval, so a mutable ref cannot change what they receive.
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
- It asks no git question: a path is replaced only when its hash equals the installed hash,
  and the project must be known on this machine with every difference from its baselines
  acknowledged (`wb acknowledge`) *(owner)*. It leaves its changes uncommitted, so the owner can
  commit them as one revertable change; on an install never committed there is nothing to
  revert to.
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
- *(Decision `2026-10-25-adopt-an-existing-repository-without-editing-it`.)* After `adopt`, every file that existed before is byte-identical, a kept
  seeded file is in the manifest at the hash of its own bytes, the tree contains no harness file, and nothing was
  committed. `check` passes on the adopted project, and `upgrade` classifies each kept seeded file **skip** and offers
  the blocks that were not filled.
- *(Decision `2026-10-25-adopt-an-existing-repository-without-editing-it`.)* `adopt` refuses a directory with no real `.git`, a `.git` that is a file
  or link, and any `.workbench` entry, and writes nothing.

# Ownership, slots and non-destructive upgrade

Status: In Progress
Created: 2026-10-20
Candidate: workbench-v1#ownership-and-upgrade
Specs: installer-interface, repository-boundary, trust-and-approval, module-contract

## Goal

Build `wb preview upgrade`, `wb upgrade`, `wb preview add`, `wb add` and `wb acknowledge`, so
an existing project can take a newer workbench or newer module versions, or a new module,
without losing work. The upgrade reads the project's manifest and files, classifies every
path as create, replace, skip, conflict or append by its owner class, shows the whole preview,
and writes nothing until the owner has typed the preview's digest in a terminal. It changes
only module-owned files and blocks that still equal what was installed, adds new files and new
blocks, appends a block only where the owner approves the append, and never touches a seeded
file, a plan, a spec, a decision, a roadmap or a reference. It commits nothing.

The manifest of an existing project is text anyone with write access to the repository can
edit. This plan makes the acknowledgement baselines the anchor that stops such an edit from
steering an upgrade: nothing the upgrade writes into is read as "installed" until its current
bytes equal what the owner last accepted, and `wb acknowledge` is the owner's way to accept a
change. When this plan is done, tests upgrade fixture projects through every classification,
and a hostile manifest, hostile markers, a swapped target and a changed package are each refused
with nothing written.

## Scope

- **Reading an existing project:** its manifest (strict reader, untrusted text), each manifest
  file's current state through no-follow descriptors, the older-workbench refusal, and the
  unfinished-install refusal that `target.py` already makes.
- **The baselines and first-seen record, read:** `projects/<id>/baselines` and `seen`, and a
  comparison of the project's manifest and files against the baselines.
- **Slot blocks in Markdown files:** a strict scanner for BEGIN/END blocks and markers, and pure
  functions that insert, replace and append a block and change no byte outside the markers.
- **A replace operation** in the project writer, and a read operation that returns the bytes and
  hash from the descriptor it will write through.
- **The upgrade plan:** classification of every path, the new manifest, the new baselines, the
  digest and the preview text. `add` uses the same plan with the rule that it writes only new
  files and new blocks.
- **The commands:** `wb preview upgrade`, `wb preview add` (read-only), `wb upgrade`, `wb add`
  and `wb acknowledge` (owner-run, terminal-only, typed digest).
- **Shared code with `install`:** the typed-digest prompt, the re-check and the failure report,
  moved out of `workbench/install.py` once.
- **Documents:** the specs, `docs/development.md`, the roadmap's current state (including its
  stale line about three decisions "awaiting the owner"; they are accepted) and decision records.

## Non-goals

- Format migrations, three-way merge and removing a module (deferred in the roadmap and specs).
  An upgrade never deletes a file.
- A declaration field that lets a module choose its files' owner class (Question 4: deferred).
- `attach`, `check`, the local manifest and any harness file. A harness module is still
  required, verified and gated at install only (My call 1).
- Running any git command. Whether a path is committed is not asked (Question 1).
- Contacting the network. `upgrade` and `add` read local packages and the cache `approve`
  filled; they never fetch (Question 6).
- Acknowledging a document's change for an agent's checkpoint (`code-work-module`). This plan
  builds the baseline read and the owner's acknowledge command, nothing that stops an agent.
- A second clone of a project. A project with no store entry on this machine, or a `seen`
  record at another path, is refused (Question 3); recording a remote is for `attach`.
- A machine-readable output form; Windows.

## Assumptions and constraints

- **Discovery:** skipped. This project provides no discovery tooling. The scope was checked
  directly against `workbench/installplan.py`, `install.py`, `preview.py`, `projectfs.py`,
  `manifest.py`, `target.py`, `store.py`, `sources.py` and `gate.py`; `installer-interface.md`
  ("Project commands", "The preview and approval", "Failure part-way"),
  `repository-boundary.md` ("Owner classes", "Slots and blocks", "upgrade"),
  `trust-and-approval.md` ("Acknowledgement"), `module-contract.md`; the roadmap candidate; and
  decision `2026-10-19-non-destructive-upgrades`.
- **Same stack:** Python 3, standard library only, `unittest`. Every read and write of the
  project goes through descriptor-relative, no-follow calls, as `projectfs.py` does now.
- **The interface spec is approved and is not reopened** except where a numbered question below
  names a gap or a contradiction. Approving this plan with those answers adopts them, and
  Increment A writes them into the specs; an answer the owner changes is written as changed.
- **The manifest is untrusted text.** The write set comes only from the approved declarations
  (a module's namespace, its `writes` and its slot `fills`) and the base. The manifest supplies
  only the installed hashes, the recorded package sources and refs, and the list of what was
  installed. A manifest entry outside the write set, in a living or historical place, or with a
  class the declaration does not give, is a conflict and is never a write.
- **The snapshot rule** of `install` holds: module bytes are read once, hashed, and written from
  memory; each replaced file's hash is checked on the descriptor held for the write.
- **The suite today** has 814 tests, all passing, and must still pass after every increment.
  Tests never touch the real store or the network.

### Points for the owner to settle at approval

Each has a recommended answer. Questions 1 and 2 block: they change what the specs say.

1. **A clean tree versus "refused until the owner commits" (blocking).** The interface spec says
   an upgrade requires a clean tree for the affected paths, decided "under the git rule, or by
   comparing file hashes with the manifest", and also says an upgrade straight after an
   uncommitted install is refused. Only git can say what is committed. A git question needs the
   private-`GIT_DIR` mechanism that the spec says must be tested against a hostile
   configuration; that is a large security build of its own. *Recommended:* decide by hashes
   alone. A path the upgrade would replace must equal the installed hash, which is the
   classification itself, so no separate clean-tree check and no git. Amend the spec: drop the
   "refused until committed" sentence and have the upgrade end by saying that nothing was
   committed and that committing first is what makes it one revertable change. The cost: an
   upgrade on an uncommitted install cannot be reverted by git.
2. **What acknowledging is (blocking).** The spec requires that a changed manifest, or a changed
   file under `.workbench/`, be acknowledged before a command acts on it, but no command
   acknowledges and nothing reads the baselines. Without the gate an attacker can edit the
   manifest so a hash matches the owner's edited file and the upgrade then "replaces" the
   owner's work. *Recommended:* a new owner-run, terminal-only `wb acknowledge [<target>]`. Every
   command that reads the manifest first compares these against `baselines` and refuses on any
   difference: the manifest, every baseline path the command would write into, and every file
   under `.workbench/` outside `local/` (a file added or removed is a difference). `wb
   acknowledge` lists each difference with its path, baseline hash, current hash and reason,
   prints a parsed summary of the manifest (packages, sources, refs, commits, module
   declaration hashes), asks for the typed digest of that list, and on a match replaces
   `baselines` for exactly the listed paths. The store keeps hashes and not old bytes, so the
   listing is a hash list and a summary, not a line diff; keeping old bytes is deferred. `add`
   and `upgrade` use the same gate, so an upgrade never re-baselines something the owner had not
   accepted.
3. **A project not known on this machine.** Nothing reads `seen` yet. *Recommended:* `upgrade`,
   `add` and `acknowledge` refuse when `projects/<id>/` has no baselines or `seen` records a
   path other than the resolved target, saying the project is treated as new here. A project
   moved on disk is therefore refused until `attach` (`claude-harness`) settles recording a
   remote or a move. Recorded as a known limit.
4. **The owner-class declaration field.** `repository-boundary.md` leaves it to this candidate.
   It changes the declaration schema, every declaration hash and every shipped approval, and no
   module needs it yet. *Recommended:* defer, with the fixed mapping of the interface spec
   (namespace files and `.workbench/.gitignore` module-owned, `writes` seeded, fills slot
   blocks), and say so in `repository-boundary.md`. A field can be added later without breaking
   the mapping.
5. **Is `add` in this plan?** The candidate boundary says "the upgrade and its preview only";
   the spec makes `add` an upgrade that brings in a module, and it needs no new machinery.
   *Recommended:* in, as the small Increment L, writing only new files and new blocks.
6. **Where newer content comes from.** The spec lets a write command fetch an approved source
   again. *Recommended:* it does not in this version. A package is resolved with
   `sources.resolve_cached`: from `--package <source> [--ref <ref>]` when given, else from the
   source and ref the manifest records, found in the cache that `approve --source` filled
   (the newest cached download of that source and ref), and a package recorded as
   `local:<name>` must be given with `--package <directory>`. The owner brings a new version in
   with `approve`, then upgrades. The manifest's source is used only to look up the cache, so a
   hostile manifest cannot make the workbench contact an address.
7. **Ordering of workbench versions.** *Recommended (my call):* versions are dotted decimal
   numbers compared numerically; an upgrade by a workbench lower than the version recorded in
   the manifest is refused, an equal or higher one proceeds, and a version of either side that
   is not dotted decimal is refused, naming it. The recorded version is read from the manifest,
   which is acknowledged first.

### My calls to confirm

Increment A states each in the specs.

1. **Harness in upgrade.** The manifest never names a harness and `attach` is not built, so
   `upgrade` and `add` verify the installed modules with the harness-required rule off. Counts
   of other types, conflicts, requirements, slot owners and order are checked as for an install.
   A harness module given as part of a package is ignored for writing, as at install.
2. **Every installed module is re-verified and gated.** An upgrade resolves every package in the
   manifest (Question 6), verifies and gates the whole set, and refuses if any module is not
   approved, even one whose files will not change. The manifest's module list is not trusted to
   shrink the set.
3. **Classification** of a path in the desired state, against its manifest entry and the disk:
   - no entry, absent on disk: **create**; no entry, present on disk: **conflict**;
   - module-owned, entry present, desired hash equals installed: **skip**;
   - module-owned, desired differs, disk equals installed: **replace**; disk differs: **conflict**;
   - module-owned, absent on disk: **conflict** (removed by the project; not restored);
   - seeded, entry present: **skip** always, with a note when a newer seed exists;
   - a slot block with no entry and its slot marker present: **create** (insert before the marker);
   - a slot block with no entry and no marker for that slot in its file: **append** (needs the
     file to be a base file with that slot; the block is appended with its marker line after it);
   - a slot block with an entry, both BEGIN/END present, text equal to installed: **replace**
     when the desired block differs, else **skip**; text edited: **conflict**;
   - a slot block with an entry whose markers are gone: **skip**, reported "slot gone";
   - an installed entry with no counterpart in the desired state (a module or file removed
     upstream): **skip**, reported "left in place"; nothing is deleted.
4. **Any file the upgrade writes into must equal its baseline** (Question 2). A seeded file
   such as `AGENTS.md` that gains a block must not carry an unacknowledged edit, because the
   preview's baseline update would otherwise accept it silently.
5. **Replace mechanism.** A temporary sibling is created exclusively with no-follow, filled and
   synced, the original is reopened no-follow on the held directory descriptor and its hash
   checked, and the sibling is renamed over it. Mode is 0644, or 0755 when the new content is
   executable, narrowed by the umask. The sibling is the only thing the writer may unlink
   besides the install marker, and only its own.
6. **Append form.** The appended text is the BEGIN/END block followed by the slot's marker
   line, at the end of the file after one newline, so the file becomes an ordinary filled slot.
7. **Module-owned manifest.** `.workbench/manifest.json` is rewritten whole, in the same
   plan, by the replace operation and is gated by its baseline.

## Completion criteria

- `wb preview upgrade`, `wb preview add`, `wb upgrade`, `wb add` and `wb acknowledge` exist and
  match `installer-interface.md` (as Increment A amends it) for every rule they reach; each
  reachable rule has a named passing test.
- A test upgrades a fixture project (installed by `wb install`, then acknowledged-clean)
  through each classification: create, replace, skip, conflict, append, "slot gone" and "left
  in place". For every file, the bytes outside the markers and every seeded file are
  byte-identical afterward, the manifest and baselines are exactly those the preview showed,
  nothing is committed and no file is deleted.
- With the preview not approved, the tree and the store are byte-for-byte unchanged (typed
  nothing, a wrong digest, no terminal, interrupt before writing).
- A hand-edited manifest, an edited `.workbench/` file, an added or removed `.workbench/` file
  and an edited seeded file that would receive a block are each refused with the paths named
  until `wb acknowledge`; a missing store entry and a `seen` at another path are refused.
- Hostile markers (duplicated, nested, unbalanced, an END before its BEGIN, a block id not in
  the declaration, markers inside a fill) and hostile paths (a manifest entry outside the write
  set, a living or historical path, a link at any component, a directory where a file is
  expected) are each refused or classified as a conflict, and never written.
- A package or file changed after the preview, a target swapped after the preview, and a file
  changed between the check and the write each refuse, and the swapped-file case writes nothing.
- A failure injected after the first write exits 3 and lists what was written and not; an
  upgrade is not left looking like a finished one without being reported.
- An upgrade by a lower workbench version is refused; an unapproved newer module is refused
  before any preview.
- `wb install`'s behavior and tests are unchanged by the shared-code extraction.
- `docs/development.md`, the specs and the roadmap record what was built; the decision
  records exist as `Proposed`.
- The full suite passes, `git diff --check` is clean, and an independent security review of
  Increments D, J, K and L has no unresolved finding when the owner asks for one.

## Increments

Fifteen increments or fewer keeps the plan reviewable. This plan has thirteen. If the owner
prefers two plans, the natural cut is after Increment I (everything read-only: the readers, the
plan, the digest and `preview upgrade`) and before `acknowledge`, `upgrade` and `add`, which
write.

### Increment A — Record the answers and settle the formats in the specs

Dependencies: the owner's answers to the questions above
Affected areas: `docs/specs/installer-interface.md`, `docs/specs/repository-boundary.md`,
`docs/specs/trust-and-approval.md`, `docs/specs/module-contract.md`, `docs/decisions/` and its
index

Outcome: the specs say what will be built, so the code is written against text. Documents only.

1. In `installer-interface.md`, write the owner's answers: no clean-tree check and no git (and
   delete the "refused until committed" sentence), the `acknowledge` command and its place in
   the command table, `upgrade` and `add` reading the cache only, the version ordering, and the
   harness rule of My call 1. Mark each built-or-proposed as that file does.
2. In `repository-boundary.md`, write the classification table of My call 3, the append form,
   the rule that no file is deleted, the "equals its baseline" rule, and that the owner-class
   field is deferred.
3. In `trust-and-approval.md`, write the acknowledgement scope (the manifest, baseline paths
   and unlisted files under `.workbench/`), the listing `acknowledge` shows, the `seen` check,
   and that nothing is stored but hashes.
4. In `module-contract.md`, change the slot-fill text only if the append form requires it.
5. Draft decision records, `Proposed`: *acknowledge-before-upgrade* (the baselines are the
   anchor against an edited manifest) and *upgrade-needs-no-git* (cleanliness is decided by
   hashes). Add both to the decisions index.

Verification: each rule the later increments build appears once in the specs; a search of the
four specs for "clean", "acknowledg", "baseline", "append" and "upgrade" finds no
contradiction; the records are `Proposed`; the specs cite no path under `.debug/`.

Evidence: the changed specs, the new records, and the search output.

### Increment B — Share the confirmation and failure code with `install`

Dependencies: A
Affected areas: new `workbench/confirm.py`, `workbench/install.py`, `tests/test_confirm.py`

Outcome: the code `upgrade`, `add` and `acknowledge` need is written once. No behavior changes.

1. Move out of `install.py` into `confirm.py`: the discard of typed-ahead input, the bounded
   read of the answer and its comparison with the first 12 characters of a digest, the
   `Progress` record, and the failure report that lists what was written and not written.
2. `install.py` calls them. Its output, exit codes and order stay exactly as they are.
3. Unit tests for the moved functions, and the existing install tests unchanged.

Verification: the full suite (814 plus the new tests) passes with `install` tests unmodified;
`git diff` of `install.py` shows moves and calls only.

Evidence: the passing suite and the diff.

### Increment C — Slot blocks: a strict scanner and exact edits

Dependencies: A
Affected areas: new `workbench/blocks.py`, `tests/test_blocks.py`

Outcome: pure functions over bytes that find the blocks of a Markdown file and edit them without
changing any byte outside the markers. No file is touched.

1. `scan(data)` returns the blocks (id, slot, byte span, text) and the slot markers (slot, line
   span). It raises `BlockError` for duplicated or nested BEGIN, an END with no BEGIN, a BEGIN
   with no END, a BEGIN and END that disagree, and a malformed marker; it accepts CRLF as the
   installer's blocks are written.
2. `insert(data, filler, slot, text)` puts a new block before the slot's marker;
   `replace(data, block_id, slot, text)` replaces one block's text; `append(data, filler, slot,
   text)` adds the block and the marker line at the end. Each refuses a text that holds a marker
   line, and returns the new bytes.
3. `slot_state(data, slot, block_id)` answers `present`, `gone` (markers removed) or `absent`.
4. Tests, byte for byte: for every edit the bytes outside the changed span are identical; a
   fuzz of random insertions of marker-like lines never changes bytes outside; each hostile
   shape above is refused; a file with no markers is `absent`; a recorded block with no markers
   is `gone`.

Verification: the new tests, then the full suite.

Evidence: the passing tests, including the byte-identity and hostile-shape ones.

### Increment D — The writer: read a file and replace a file

Dependencies: A
Affected areas: `workbench/projectfs.py`, `tests/test_projectfs.py`

Outcome: the writer can read a regular file and replace one whose hash is as expected, through
held descriptors, and can do nothing else new.

1. `Writer.read_file(rel)` walks one component at a time, no-follow, directory-only, opens the
   file no-follow and regular-only, and returns its bytes, hash and mode, bounded by
   `safefs.MAX_FILE_BYTES`. A link or a non-regular file at any component is a conflict.
2. `Writer.replace_file(rel, expected_hash, data, executable)` follows My call 5: sibling
   created exclusively, original reopened and its hash checked on the descriptor, sibling renamed
   over it. A hash difference, a link, or a non-regular file raises `WriteConflict`, removes the
   sibling it made, and changes nothing else. `written` records the path.
3. Update the module docstring: the writer replaces only through `replace_file` and unlinks only
   the marker and its own sibling.
4. Tests: a replace; a changed hash refuses; a link or directory planted at the file, a parent
   swapped for a link, and a sibling name already present each refuse and leave the victim
   untouched; the sibling is removed on every failure; modes under umask 0.

Verification: new tests, full suite; the `safefs._fire` hooks used by the existing tests drive a
swap between check and rename.

Evidence: the passing tests, with the swap cases named.

### Increment E — Read the baselines and the first-seen record, and compare

Dependencies: A, D
Affected areas: new `workbench/acknowledgement.py`, `tests/test_acknowledgement.py`

Outcome: the readers `docs/specs/repository-boundary.md` describes, and the comparison that
the gate in Question 2 uses. Read-only.

1. `read_baselines(guarded, project_id)` and `read_seen(guarded, project_id)` parse the strict
   formats that `install` writes and refuse anything else (wrong format number, unsorted or
   unknown keys, a non-hex hash, a path that is not a valid relative path).
2. `check_known(seen, resolved_path)` implements Question 3.
3. `differences(held_reader, baselines, manifest_entries)` hashes the manifest, each baseline
   path in scope, and a walk of `.workbench/` outside `local/`, with the writer's reader, and
   returns each difference as `changed`, `added` or `removed` with the two hashes. It never
   follows a link; a link or directory where a file is expected is a difference with that
   reason.
4. Tests: clean, each difference kind, a link in the walk, a hostile baselines file, a missing
   entry, `seen` at another path.

Verification: new tests, full suite.

Evidence: the passing tests.

### Increment F — Read an existing project

Dependencies: C, D, E
Affected areas: new `workbench/installed.py`, `tests/test_installed.py`

Outcome: one function turns an opened existing target into what is there now, without trusting
it.

1. `read(held, workbench_version)` reads and strictly parses `.workbench/manifest.json`, applies
   Question 7's version rule, and for each manifest file entry reads the current file with
   `read_file` and returns its state: `as-installed`, `edited`, `missing` or `unreadable`; for a
   slot block entry it uses `blocks.scan` and `slot_state`. A scan error is a state, not an
   exception, so a hostile file is reported as a conflict by name.
2. Manifest paths are validated by `safefs.check_tree_paths`; a bad path is refused.
3. Tests: a fresh install reads back all `as-installed`; one case per state; a hand-edited
   manifest still parses or is refused by the strict reader; a lower and an unparsable workbench
   version.

Verification: new tests, full suite.

Evidence: the passing tests.

### Increment G — The upgrade plan: classification, manifest and baselines

Dependencies: F
Affected areas: `workbench/installplan.py` (expose the desired state), new
`workbench/upgradeplan.py`, `tests/test_upgradeplan.py`

Outcome: a pure function from the existing project's state, the approved module snapshots and
the base to a plan of classified actions with the new manifest and the new baselines.

1. Split `installplan._assemble` so the desired files and blocks can be computed without a
   target; `installplan.build` is unchanged in output (its tests prove it).
2. `upgradeplan.build(installed, selection, snapshots, base, workbench_version, mode)` applies
   the table of My call 3. `mode` is `upgrade` or `add`; in `add` only create and append appear
   and a would-be replace is refused. Paths outside the write set, in a living or historical
   place, or claiming another class are conflicts.
3. It builds the new manifest document (kept entries, new entries, new hashes, workbench
   version, packages) and the new `baselines`: the old baselines with exactly the previewed paths
   updated. It refuses when the base's slot a block needs is missing and no append is possible.
4. Tests: one per classification; `add` refuses a replace; a manifest entry outside the write
   set; a module removed upstream is left in place; nothing in the plan deletes.

Verification: new tests, full suite; `installplan` tests unchanged.

Evidence: the passing tests.

### Increment H — The digest and the preview text

Dependencies: G
Affected areas: `workbench/upgradeplan.py`, `tests/test_upgradeplan.py`

Outcome: the injective digest and the text of `installer-interface.md` ("What a preview shows")
for an upgrade.

1. The digest covers the command and selection, the target's device and inode, the workbench
   version, every module's declaration and tree hash and its change, every path with class,
   action, mode, size, new hash and, for a replacement, the hash now, every new baseline, and
   the new manifest hash; as canonical JSON with explicit field names.
2. `render` prints the summary counts by action first, the high-risk flags, each module with
   its declaration change, each path with class and action, a conflict's reason, an append's
   block and place, hashes and never an existing file's content, and the guarded-store writes.
   Every package-supplied string goes through `display.ascii_text` with the backslash escaped.
3. Tests: two plans that differ in any one field differ in digest; names that would collide
   under a plain join do not; a hostile name is escaped; a declined append lists the marker to
   add.

Verification: new tests, full suite.

Evidence: the passing tests.

### Increment I — `wb preview upgrade`

Dependencies: G, H
Affected areas: `workbench/preview.py` or new `workbench/upgrade.py`, `workbench/cli.py`,
`tests/test_upgrade_preview.py`, `tests/test_cli.py`

Outcome: the read-only half. An agent can run it.

1. Arguments as `upgrade` in the spec: target, `--package <source> [--ref <ref>]` repeatable.
2. In order, refusing with `refused:` lines and nothing written: open and check the existing
   target; read the project (F); refuse an unknown project (Question 3) and any unacknowledged
   difference, naming the paths and saying to run `wb acknowledge` (Question 2); resolve every
   package from the cache or a local directory (Question 6); verify and gate the whole set
   (My calls 1 and 2); build the plan; print it and `preview only: nothing was written`.
3. Exit 0 when a preview was produced, 1 when the command would be refused. It contacts no
   network and writes nothing, not even a cache directory; the store and `.git/index` are
   byte-identical before and after.
4. Tests: each refusal above, a clean preview, `nothing to change`, no network (a recording
   fake for the fetch layer is never called), store and tree unchanged, and the usage text.

Verification: new tests, full suite.

Evidence: the passing tests and a sample preview captured for the Result.

### Increment J — `wb acknowledge`

Dependencies: E, B
Affected areas: new `workbench/acknowledge.py`, `workbench/cli.py`, `tests/test_acknowledge.py`

Outcome: the owner can accept a change to the manifest or to `.workbench/` and so unblock an
upgrade.

1. Owner-run and terminal-only, checked before anything is read, as `install` and `approve` do.
2. It lists the differences (E), prints the parsed manifest summary, shows the digest of that
   list, reads the typed answer as `install` does, and on a match replaces `baselines` for
   exactly the listed paths (atomic per file, through the store's writer). A path not listed is
   not touched; a wrong answer writes nothing.
3. It re-reads and re-checks after the answer and refuses if the differences changed.
4. With no differences it says `nothing to acknowledge` and exits 0.
5. Tests: a pty test with the real prompt (reusing `tests/support.drive_pty`), a wrong digest,
   typed-ahead input discarded, no terminal, a file that changes after the listing, and a
   baselines file left identical for unlisted paths.

Verification: new tests, full suite.

Evidence: the passing tests.

### Increment K — `wb upgrade`

Dependencies: B, D, I, J
Affected areas: `workbench/upgrade.py`, `workbench/cli.py`, `tests/test_upgrade.py`

Outcome: the owner-run write.

1. Terminal-only, refused with exit 1 otherwise. Runs the steps of Increment I, prints the plan
   with its digest, reads the typed answer (B).
2. After the answer: re-check the target identity and read the project again; rebuild the plan
   from the same packages with the same inputs and refuse if the digest differs; hold every
   file to be replaced and refuse if its hash is not the one in the plan.
3. Write in this order: directories; created files; block inserts, replaces and appends (each a
   `replace_file` of the whole file); the manifest last; then the store's `baselines`. The
   install marker `.workbench/local/incomplete` is created first and removed last, so a failure
   part-way is found by it and reported under the failure rule; exit 3 with the written and
   unwritten lists. Nothing is committed and nothing is deleted.
4. The final lines say how many paths were written, that nothing was committed, and that
   committing the result as one change makes it revertable; a skipped conflict or "slot gone"
   is listed with its reason.
5. Tests: every classification end to end; the not-approved cases of the completion criteria;
   a file edited between preview and write; a swapped target; a link planted after the marker;
   a failure injected after the first write (marker kept, exit 3, report); bytes outside
   markers byte-identical; an upgrade right after an uncommitted install still works.

Verification: new tests, full suite. The owner may then ask for a security review (Risks).

Evidence: the passing tests.

### Increment L — `wb add` and `wb preview add`

Dependencies: K
Affected areas: `workbench/upgrade.py`, `workbench/cli.py`, `tests/test_add.py`

Outcome: a module the project does not have is added with the same preview and approval.

1. Arguments: `--package <source> [--ref <ref>] --select <module> ...`. The new module is
   verified together with those already installed (My call 1), so counts, conflicts,
   requirements, slot owners and order are checked.
2. Plan `mode` is `add`: new files, new blocks and appends only. A module already installed is
   refused and the message says to use `upgrade`.
3. Tests: add a module with a fill; add one that fills a slot the base lacks (append); add a
   conflicting module (refused); add an installed module (refused); no network for the preview.

Verification: new tests, full suite.

Evidence: the passing tests.

### Increment M — Documents and the Result

Dependencies: K, L
Affected areas: `docs/development.md`, the four specs, `docs/roadmaps/workbench-v1.md`,
`docs/decisions/`, this plan's Result

Outcome: the documents describe what exists.

1. `docs/development.md`: rows for the five commands, a section on previewing and applying an
   upgrade, acknowledging, exit codes, and the limits.
2. Specs: change "proposed" to "built" for what is built and keep what is not as proposed.
3. Roadmap: add the current-state bullet for this candidate and correct the line saying three
   decisions "await the owner" (they were accepted on 2026-10-20).
4. Fill the plan's Result. Do not edit the approved plan text.

Verification: a search finds no stale "proposed" for a built command; the suite passes;
`git diff --check` is clean.

Evidence: the changed documents and the filled Result.

## Verification

- After every increment: `python3 -B -W error -m unittest discover -s tests`, and
  `git diff --check`.
- Hostile cases run through the real code path with a fake or planted file, never by reading
  alone: markers (Increment C), links and swaps (D, K), a hand-edited manifest and baselines
  (E, F, I, J).
- At the end: the criteria above, the full suite, and a hand run of `install`, an edit,
  `acknowledge`, `upgrade` on a fixture, recorded in the Result.

## Risks and sensitive actions

- This plan writes into a project the owner has edited and into the guarded store, and reads
  attacker-editable files. The sensitive increments are D (replace), J (store write), K and L.
  *Mitigation:* the write set comes from approved declarations only; every file replaced is
  hash-checked on the held descriptor; the baselines gate precedes any read of the manifest as
  "installed"; the digest is the owner's typed approval of exactly what is written.
- **The replace is not atomic with the check.** Between the hash check on the descriptor and the
  rename a same-account process can change the file. *Residual risk, accepted:* a process that
  can write the project can also write the file after the rename; the typed digest is friction,
  not authentication, as for `install`.
- **Read-modify-write on `baselines`.** Two commands running at once could lose an update.
  Accepted; the commands are owner-run.
- **Re-baselining.** Replacing `baselines` for the previewed paths is what accepts a change. The
  rule that every touched file must already equal its baseline keeps an upgrade from accepting an
  edit nobody reviewed.
- **Review focus** (inputs the specs imply that the tests above do not already pin, most likely
  first; each gets a test in the increment that owns the code):
  - a block text containing a marker line, or a filler id that repeats another's (C, G);
  - a `.workbench/` path that is a directory where a file is expected, or a file where a
    directory is (E, F);
  - a manifest path that differs only by case or Unicode form from a real path (F);
  - a module whose new version drops a file the project edited (G, "left in place");
  - an empty `baselines`, an empty manifest `files` list, or a manifest naming no packages (E, F);
  - CRLF files and a missing final newline around a block (C).
- A security review (`security-review` skill, with an adversarial reviewer in a scratch copy) of
  D, J, K and L is recommended before the plan is completed, at the owner's request; its fixes go
  into the increments they concern.
- Commits are made only with the owner's approval and only with `claude-workflow commit`. Nothing
  is pushed.

## Review record

None yet. An independent review of this plan happens only when the owner asks.

## Deferred work

- The owner-class declaration field (Question 4); keeping old bytes so `acknowledge` can show a
  line diff; markers for non-Markdown files; migration commands; removing a module; three-way
  merge; recording a remote or a moved project (`attach`); any git question (a private
  `GIT_DIR`); an upgrade that fetches (Question 6).

## Result

Not started.

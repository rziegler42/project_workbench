# Refreshing the rendered skills and agents of an attached clone

Status: Current
Updated: 2026-10-28

A design, approved by the owner on 2026-10-28 as it stands, the calls included. It was reviewed in three rounds with the
project's review bridge, which stopped at its bound; the fixes of the last round were not reviewed again. **(call)** marks a choice
the owner did not make themselves; the owner's own words are under "Intent". The owner chose to put this in a spec of its own and
not to revise [`harness-rerender.md`](harness-rerender.md), whose scope is the permissions file and the table. It is built by the
plan `2026-10-28-refresh-rendered-harness` (increments A to D); "As built" lists what the build settled and what remains open.
The text above "As built" is the design as approved, where it differs the built command is described under "As built".

## Intent

The owner found that a rendered skill in an attached clone can stay behind its source, and asked whether the fix belongs in
`upgrade` or `rerender`. Owner's words: "think about the issue updating stale skills", "what else would benefit from updating,
such as agents", "should we wrap this into an existing command, such as upgrade or rerender?".

## Scope

- The files `wb attach` renders from the installed modules' neutral items into the harness's own folders: skills, agents, the
  root file and the like. For the `claude` harness these are under `.claude/` and the files the layout names.
- How an owner learns that such a file is behind its source, and one owner-run command that brings them up to date.

## Non-goals

- No change of harness, and no change to a clone with no recorded harness (`attach` stays for that).
- No change to what `wb upgrade` writes. It updates what is installed under `.workbench` and the seeded documents.
- No agent-run refresh at any level: no new key, and no `ask` or `none` for it.
- No automatic refresh, hook or watcher. Nothing refreshes because a file changed.
- No deletion of a rendered file whose source is gone.
- No overwrite of a rendered file the owner or the harness edited since attach.

## Assumptions and constraints

Each is read in the code at commit `a7fb4c6` unless it says otherwise.

- **Rendering is a function of the packages.** `harnessstage.stage` turns the neutral items of the installed modules into the
  harness files and a local manifest that records a hash for each (`.workbench/local/harness.json`). `wb attach` writes them. It
  refuses a clone that already records a harness, so there is no command today that writes them a second time.
- **`wb rerender` already builds every file and keeps one.** `rerender.build` calls `attach.stage`, which stages the skills and
  agents too, and then takes only the permissions file from the result. When the harness module differs from the recorded one it
  says "only the permissions file is replaced, and the other harness files stay as attach wrote them" (`rerender.py`, around
  line 203). [`harness-rerender.md`](harness-rerender.md) states this scope and says a module change is not covered.
- **`wb upgrade` never writes `.claude/`.** Its writes are files under `.workbench`, the seeded documents, the manifest and the
  guarded store's baselines (`upgradeplan.py`).
- **`wb check` reports edited and missing files and does not report stale ones.** It compares each file's hash with the one the
  local manifest recorded (`check._drift`), which says a file was edited, and says nothing when the file is unchanged but its
  source has moved on.
- **Evidence.** Run on 2026-10-28 at commit `f81882c` with Python 3.15.0. After the owner ran `wb upgrade`, the installed
  `draft-plan` skill matched its package and the rendered `.claude/skills/draft-plan/SKILL.md` lacked the two lines the upgrade had
  delivered; `wb check` printed "check found no problems". The rendered `draft-decision` skill had been behind its source since
  before that, lacking the section for `accept-decision` at `none`. The rendered `reviewer` agent differed from its source only by
  translation (`tools: read, search` becomes `Glob, Grep, Read`), which is intended.
- The staging needs the packages the project records. A local source is given with `--package`, as for `upgrade`
  (`rerender.py` refuses without it).

## Behavior

**(call) One command, `wb rerender`.** It keeps its preview (`wb preview rerender`), its digest, its terminal-only rule and its
single owner-run key, `wb rerender`, which offers `block` only (decision `2026-10-27-rerender-is-terminal-only`). It renders the
permissions file as it does now and also the other staged files whose recorded hash is not the staged one. The plan, the digest
and the write are one: the owner confirms one digest for all of it. Reasons:

- The plan already holds the staged files, so no second staging, command or key is added.
- A skill or an agent is text the agent obeys. Refreshing one rewrites the agent's own instructions, so it keeps the strictest
  rule the project has: a terminal, a preview, and a digest the owner types back. Giving it a level of `ask` or `none` is
  refused for the same reason as the permissions file's, and more strongly.
- `upgrade` and `rerender` keep two meanings: what is installed, and what is rendered from it.

**(call) What the preview shows, per file.** Each staged file is one of:

The states below are for every staged file except the permissions file (see "The permissions file is outside the table"). They
are tried in this order, so a run that stopped halfway finishes when it is run again. First, every staged path and every path the
manifest lists is read without following a link; a link at any of them is refused, whatever its content, and so is a run in which
nothing would otherwise change. Then a manifest path that the staged files no longer have is "orphaned" whether or not its file is
on disk, and the rows for a staged path follow:

| State | Meaning | Action |
|---|---|---|
| current | the file on disk equals the staged hash and the manifest records it | listed as left as it is |
| applied | the file on disk equals the staged hash and the manifest records another (an earlier run stopped before the manifest was written) | left as it is; only the manifest's hash for it is written |
| stale | the file on disk equals the recorded hash and the staged hash differs | replaced; the old and new hash and the changed lines are shown |
| edited | the file on disk differs from the recorded hash and from the staged hash | refused: the command writes nothing at all until the owner resolves it |
| missing | the manifest lists the file, it is still staged, and it is gone | recreated from its source, and listed as recreated |
| new | the staged file is not in the manifest and nothing is at its path | created |
| unrecorded | the staged file is not in the manifest and a file with other content is at its path | refused, as for edited |
| orphaned | the manifest lists a path the staged files no longer have (checked before every row above) | listed as "no longer shipped", with its on-disk state (present, or already gone); never deleted, never recreated |

A staged file that is not in the manifest and whose content on disk equals the staged hash is "applied" too (an earlier run
created it and stopped before the manifest was written); it is not "unrecorded".

The owner resolves an edited file by moving it aside or deleting it, which makes it "missing" and so recreated from its
source. This command has no force option. **(call)** Refusing the whole run on one edited file keeps the plan the owner
confirmed identical to the plan written.

**(call) The comparison goes through the renderer.** The staged hash is of the translated file, with its frontmatter rewritten
by the harness layout. A comparison of the installed neutral file with the rendered one by bytes is wrong, because the two always
differ by translation.

**(call) Writes.** Each file is replaced with `Writer.replace_file(path, expected_hash, data)`, as `rerender` replaces the
permissions file, and the local manifest is written after the files and before the rendering record, so that a failure leaves
the clone with every relaxed key reading `block` and never looser (the order in `harness-rerender.md`, "Design").

**(call) What "nothing written" covers.** Immediately before the first write the command reads every file it will replace or
create again and compares each hash with the one the plan read, and it rebuilds the plan and compares its digest with the one
confirmed. Any difference, an edited, unrecorded or linked file included, refuses with nothing written. This is a check before the
first write and not a transaction. A file that changes after the first replacement fails that replacement; the command stops, exits
3 and lists what was written and what was not. Nothing is rolled back. Running it again finishes the job, because a file
already replaced equals its staged hash and reads as "applied", a created file likewise, and the manifest and the record are
written last.

**(call) `wb check` does not report staleness in this design.** Telling stale from current needs the staged hash, and staging needs
the harness module's layout and the packages (`attach.stage`, and `rerender` refuses without `--package` for a local source). The
harness module is not among the installed modules under `.workbench`, so `check` cannot translate the files on its own.
`wb preview rerender` is where staleness is seen. A later design could record in the local manifest a hash of each file's source,
so that `check` compares an installed item with that hash without staging; that is a change of the manifest's format and is not
decided here.

**(call) `wb upgrade` prints one line, and nothing else changes.** After an upgrade that wrote a module's harness items (a path
under a module's `harness/`), it says that the rendered copies may be behind and names `wb preview rerender`. It does not stage,
does not compare and does not render.

**The permissions file is outside the table.** The states above apply to the skills, agents, root file and other staged files,
and never to the permissions file. It keeps exactly the rules of [`harness-rerender.md`](harness-rerender.md): its planned bytes are
the rendered permissions plus the live file's validated `allow` rules, each shown in the preview and covered by the digest; the
file is replaced from the hash the plan read, and the resulting hash is the one recorded; the shared settings file is recorded and
not written. A live `allow` rule is therefore never an edit that refuses the run. A refresh that finds no change in the permissions
file writes nothing for it. The permissions file, the other files, the manifest and the record are one plan with one digest.

## Open questions

1. **Should `wb check` ever report staleness?** Only by a manifest that records each file's source hash (see Behavior). Whether
   that is worth a format change is left to the owner.
2. **A skill removed from a package.** The state "orphaned" lists it. Whether the owner then wants a command to remove rendered
   orphans is left out of this design.
3. **Does the root file count?** The rendered root file (`CLAUDE.md` for this harness) imports `AGENTS.md`. It is staged like the
   others and is covered by the table above. If the harness layout marks any rendered file as the owner's to edit, it needs a
   state of its own. Not checked.
4. **Does a refresh need its own security review?** The change decides which instructions the agent loads. **(call)** Yes, when it
   is built, and only when the owner asks for it.

## Acceptance criteria

1. With a package skill changed and `wb upgrade` run, `wb preview rerender` lists the rendered skill as stale. After
   `wb rerender` it lists it as current.
2. `wb preview rerender` shows every stale, applied, new, recreated and orphaned file with its old and new hash, writing `none` for
   a hash that does not exist (no old file for a new one, no staged file for an orphan), the changed lines of a stale file, and one
   digest, and writes nothing. A run with nothing to change and no table change says so.
3. `wb rerender` at a terminal, with the digest, replaces each stale file, creates each new file, writes the manifest, then the
   rendering record, and leaves an orphaned file alone.
4. A rendered file edited since attach, or an unrecorded file at a staged path, makes the whole run refuse with nothing written,
   and names the file. A missing one is recreated and listed as such.
5. A rendered file that is a link, even one whose content equals its staged and recorded hash and even when nothing else would
   change, is refused with nothing written, in the preview and in the write. So is a file that differs when the command re-reads
   every file before its first write. A change after the first replacement stops the run with exit 3 and the written and not-written lists.
6. A run without a terminal is refused at every level, and no level is offered for it.
7. A failure after one replacement leaves every relaxed key reading `block`, and a second run reads each replaced or created
   file as applied and finishes the job, including the manifest and the record. (As built, a stop after the manifest was written
   leaves the files reading `current` and not `applied`, because the manifest then records them; the second run finishes the record.)
8. `wb upgrade` writes nothing under `.claude/`.
9. The comparison tests use the real renderer, so a quoting or `tools:` translation does not count as stale.

## As built

Built by the plan `2026-10-28-refresh-rendered-harness`: A the states in the preview (`refresh.classify`), B the writes
(`refresh.recheck`, `refresh.write`, `rerender._write`), C the line of `wb upgrade`. What the build settled:

- **The write order.** The re-read of every stale, new, missing and applied file (a link or a changed hash refuses with nothing
  written), then the files (a stale one by `Writer.replace_file` with the hash the plan read, a new or missing one by
  `Writer.create_file`), then the permissions file, then the local manifest, then the record. The files go before the permissions
  file on purpose: a stop between leaves new instructions under the old permissions, never a looser key. Applied files are read
  again just before the manifest is written. The manifest keeps its fields; the hashes of the written and applied paths change and the entries of new paths are added.
- **The report.** A successful run prints one `files:` line (replaced, created, recreated, and recorded as applied; nonzero counts
  only) before "nothing was committed".
- **Failures.** A re-read that differs refuses with exit 1 and "nothing was written". A failure after a write is exit 3 with the
  written and not-written lists; the not-written list is every step of the write order not found done (the order is fixed, and the disk is read for the next step only). A new file is made whole or not at all
  (see "Limits as built"), so a failed create leaves nothing at its path. A second run finishes the job.
- **`wb upgrade`.** After "wrote N paths" it prints one line when a written path lies under `.workbench/<package>/<module>/harness/`:
  the rendered skills, agents or commands may be behind, and `wb preview rerender` shows which. It prints it for `wb add` as well,
  which shares the code. It stages and compares nothing, and it writes nothing under the harness's folders.
- **The root file is a rendered file like the others.** The owner-editable question (Open question 3) is answered by treating it
  so: an edit to it refuses the run, and the owner moves it aside to have it recreated.
- **`wb check`** still does not report staleness (Open question 1 stays open).

## Limits as built

Reviewed by a `reviewer` pass per increment and a security review of Increment B, asked for by the owner. Findings not applied,
for the owner to decide:

- **The edited-file test trusts the local manifest.** Whoever can write `.workbench/local/harness.json` can record an edited file's
  hash, and the file then reads stale and is replaced. The bytes written are always the staged ones, the preview shows the diff,
  and the owner types the digest. Since the plan `2026-10-28-protect-local-manifest` the rendered permissions deny the harness's
  write tool on the manifest (a clone has it after its next re-render), which closes the harness's tool and not a write by the
  shell. Corroborating the hash in the guarded store would close the rest and is not built. The deny also makes the
  rendered permissions need a plain project path, which they did not when there was nothing to protect: a project path with
  `(`, `)`, `#`, `'` or a non-ASCII character is refused by `wb attach` and `wb rerender`, as it already was with a hook.
- **A new file is written whole or not at all.** `Writer.create_file` (shared by install, adopt, add, upgrade and rerender) fills
  and syncs a sibling named `.workbench-<pid>-<hex>.tmp` in the same directory and links it to the final name, which fails when
  anything is there; the sibling is unlinked on every path out, and the path is listed as written only once the link is made. A
  failure before the link leaves nothing at the path. After the link the final name is read without following a link and must be
  a regular file with the device and inode of the file written and two links, or the create is a conflict, the path is not listed
  and what is there is left alone: the sibling is a plain file that whoever can write the directory could replace before the
  link. A swap after that check is not prevented. The other gap left is a crash between the link and the unlink: the finished
  file then has a second name, a later read refuses it by its final path (more than one hard link), and removing the sibling
  clears it. A filesystem without hard links fails the create and leaves nothing behind. The two-link condition assumes the
  filesystem reports link counts truthfully; one that does not would make every create a conflict, which is loud and not
  silent. It was tried on macOS (APFS) only.
- **A new file is checked against the clone's `.git/info/exclude` as well as the layout's exclude entries.** Both the preview
  and the run refuse a file they would create unless the entry that covers it has its line in that file (read without following
  a link, at most the file size limit; a CR at the end of a line is not part of it), or when the file cannot be read as a plain
  regular file; a missing file has no lines. A run with nothing to create does not read it. Nothing is written to `.git`.
- **The changed lines of a stale file are split on the newline only**, so a change of a carriage return, a vertical tab or another
  line separator shows as a changed line, written as its JSON string when it is not plain. A change of only the final newline
  shows as one added or removed empty line.
- A write that lands between `replace_file`'s comparison and its rename is overwritten without notice (as for the permissions file).
- The fixes of the third review round of this spec were not reviewed again.

## Governing decisions and references

- Decisions: [`2026-10-27-rerender-is-terminal-only`](../decisions/2026-10-27-rerender-is-terminal-only.md),
  [`2026-10-26-a-level-for-every-command`](../decisions/2026-10-26-a-level-for-every-command.md).
- Specs: [`harness-rerender.md`](harness-rerender.md), [`harness-modules.md`](harness-modules.md),
  [`repository-boundary.md`](repository-boundary.md), [`command-permissions.md`](command-permissions.md).

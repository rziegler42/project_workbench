# Re-rendering an attached harness

Status: Draft
Updated: 2026-10-27

A design, written with the owner's word to skip the questions, reviewed in four rounds with the project's review bridge, and
approved by the owner on 2026-10-27 as it stands, the calls included. Nothing in it is built, so the status stays `Draft` until
the plan `2026-10-27-rerender-attached-harness` builds it. **(call)** marks a choice the owner did not make themselves; the
owner's own words are under "Intent" and in the decisions recorded under "Open questions and decisions". The last edit, making
the command terminal-only, had no review round.

## Intent

The owner changes a level in the personal settings (`~/.config/project-workbench/settings`) and expects it to take effect.
It does not, in an attached clone, until the clone is attached again, and `wb attach` refuses a clone that already records
a harness. The gap is listed under "Not built" in [`command-permissions.md`](command-permissions.md). Owner's wording: a way to
re-render the harness to pick up a level change, at least when setting a key to `none`, and maybe others.

## What happens today

- Rendering is a function of the effective table (settings, checkpoints, module declarations). Attach writes the harness
  files and the rendering record, whose `table_digest` is of the table it rendered from.
- A key reads `ask` or `none` only while the record's digest equals the digest of the table now. After any table change,
  relaxed keys read `block`. Loosening therefore does nothing until a re-render, and it fails safe.
- Tightening an owner-run key is immediate (it reads `block`). Tightening an agent-safe key to `block` renders its `deny`
  only at the next attach, and the old rules stay until then.

## Goals

1. After the owner edits the settings, one owner-run command makes the attached clone's rendered rules and rendering record
   match the table, for both loosening and tightening, with no new clone.
2. The command shows what it will change before it changes anything, as `upgrade` does. At the default level `block` the owner
   confirms at a terminal, and the plan it printed is the plan it wrote. It runs only at a terminal: the owner is the one who
   sees the plan, including the `allow` rules it keeps.
3. `wb check` says when the rendering is out of date and names the command.
4. It re-renders the harness the clone already records. It never changes which harness.

## Non-goals and anti-goals

- No change of harness, and no change to a clone with no recorded harness (`attach` stays for that).
- No agent-run re-render by default. A re-render can relax every protection the owner's table allows, so it is an owner act.
- Not a hook that re-renders on a settings change, and no watcher. Nothing may re-render because a file changed.
- It must not relax a key beyond what the table says, and must not leave a clone in a state where `ask` or `none` reads
  more permissively than the files on disk render.
- It must not silently discard rules the owner or the harness added to the rendered files.

## Design

**(call) Name and shape.** A new installer command `wb rerender`, with `wb preview rerender` for the read-only plan. It is
preview, then owner-run with the preview digest typed at a terminal, like `wb upgrade`. Its key in the level table is
`wb rerender`, offering `block` only, default `block`. It has no `none`: see "Terminal only".

**(call) Binding the confirmation to the writes.** At a terminal the owner types the preview digest. Immediately before the
first write the command rebuilds the whole plan (settings, manifest, packages, the permissions file, retained rules) and compares its
digest with the one confirmed. On any difference it refuses and writes nothing.

**(call) Terminal only (the owner's decision, option a of review finding R4-F1).** `wb rerender` offers `block` only and always
needs a terminal. `none` would read the level through `rendering.effective_level`, which returns `block` whenever the record's
table digest or the permissions file's hash differs, and those are the two ordinary reasons to run a re-render (a changed table,
or an `allow` rule added by "Yes, and don't ask again"). It would refuse exactly when needed. A narrower recovery path would let
a non-terminal run keep and record, as trusted, `allow` rules nobody saw, so it was not chosen. This is a second exception to decision 3 of
`2026-10-26-a-level-for-every-command` (every key offers `block` and `none`), beside the owner-run arguments of module commands but
for a different reason. It is recorded in `2026-10-27-rerender-is-terminal-only`, which the owner accepted on 2026-10-27.
`command-permissions.md` lists it with the other exception when the command is built. The preview, `wb preview rerender`, is
unaffected. A run at a terminal writes no level-log entry, as for the other owner-run commands.

**(call) Keys.** The read-only plan, `wb preview rerender`, is its own agent-safe key and defaults to `none`, as the other preview
actions do; the owner may set it to `block`. It writes nothing. Only `wb rerender` governs writes, under its own owner-run
key. Both are registered as the registry requires for a routed subcommand.

**What the table changes (read in the code, `harnessstage.stage` and `rendering.effective_level`).** A level in the table is
rendered into one file only: the harness's permissions file (the per-clone settings file the layout names), through
`render_permissions` (the `deny`, `ask` and open patterns, and the command gate's hook). Every other staged file is the same for
any table. The gate also reads the rendering record and the local manifest's harness name, and watches the shared settings file
(it is hashed, not written). So a re-render replaces one file and the record, not the whole harness.

**(call) Source.** It stages as attach does, from the packages the local manifest records (a local source is given with
`--package`, as for `upgrade`) and the effective table now, and runs the same checks: no unacknowledged differences, packages
verified and approved on this machine, the recorded harness is still one this project records. It uses only the permissions
file from the result.

**(call) What it writes.** In this order: the permissions file, the local manifest's hash for it, then the record. The
permissions file is replaced with `Writer.replace_file(path, expected_hash, data)`, which writes a private sibling, reads the
original again and compares its hash, and renames it into place; it raises `WriteConflict` on any other hash, a link, or a file
that is gone. The expected hash is that of the file as the plan read it. The file as it stands may differ from the record's
`file_hash`, for example after "Yes, and don't ask again", which is why those keys read `block` until this runs.

- the live file's `allow` rules are carried into the new file, each listed in the preview and covered by the digest (the owner's
  decision, see below);
- anything else in the live file that the new file will not have is listed too, as a removal, so the owner sees it before the
  digest is confirmed. A file that is not valid, a link, or one that cannot be read refuses and writes nothing.

**(call) Order of writes.** A relaxed key holds only while the record, the permissions file and the shared settings file agree.
The record is written last, so until it is the old record names a hash the replaced file no longer has and every relaxed key
reads `block`: a failure at any step leaves the clone stricter than the table says and never looser. (Attach writes the record
first because it has no earlier record to disagree with; this is the reverse on purpose.) The local manifest's hash for the file
is written before the record so that `wb check` does not report drift once the record is current. Read from
`rendering.effective_level`: it consults only the record, the local manifest's harness name, the permissions file and the shared
settings file, so the order is sufficient. Whether `wb check` reads other manifest fields is for the plan to confirm.

**(call) Concurrent edits.** `replace_file` closes most of the gap: the hash is compared after the replacement is written and
immediately before the rename, in the held directory. An edit that lands between that comparison and the rename is not caught.
That window is listed under "Limits".

**(call) Plan output.** The preview lists, per key, the old and new rendered rule (`deny`, `ask`, `none`, `unruled`), the
files to replace, and the digest. A re-render that changes nothing says so and writes nothing.

**(call) `wb check`.** Reports `rendering: out of date; the settings table differs from the rendered one (wb rerender)` when
the record's digest differs from the table now. Informational, not a failure, since the stale state is already safe.

## Open questions and decisions

None.

Decided by the owner: "Yes, and don't ask again" writes `allow` rules into the per-clone settings file, and a re-render
records that file's new hash. A re-render keeps those rules, lists each one in the preview, and the digest the owner
confirms covers them.

Settled by the level system, not open: who may run the command is the owner's level for its key (decision
`2026-10-26-a-level-for-every-command`). It defaults to `block` because an agent cannot run it today, and offers `block` only (see "Terminal only"). My call:
it covers loosening and tightening both, since the owner asked for loosening and tightening an agent-safe key needs it.

## Acceptance criteria

1. With the table changed from `block` to `none` for a key, `wb preview rerender` shows the key moving and writes nothing;
   `wb rerender` at a terminal, with the digest, then makes the key read `none`.
2. With no change to the table, it writes nothing. Every `allow` rule in the settings file is listed in the preview and survives a
   re-render.
3. A permissions file that is a link, is not valid, or changes between the plan and the replacement is refused with nothing
   written. Anything the live file has that the new one will not is listed in the preview.
4. A failure after any file has been replaced and before the record is written leaves every relaxed key reading `block`.
5. A clone with no recorded harness is refused and pointed at `attach`.
6. A run without a terminal is refused at every level, and no level-log entry is written for a run at a terminal. The key offers
   `block` only.
7. If anything the plan reads changes between the preview and the write, the command refuses and writes nothing.
8. `wb check` reports an out-of-date rendering and stops reporting it after a re-render.

## Limits

- A write to the permissions file that lands between `replace_file`'s hash comparison and its rename is overwritten without
  notice. The command is owner-run; the window is small and is not closed here.
- A change to a module or a package is not a table change. This command re-renders for the table only; picking up a module
  change is `upgrade`'s work and is not covered here.

## Not decided

How the local manifest's hash for the permissions file is updated (whether `localmanifest` has a rewrite that does not need a
whole attach), how the preview shows the live file against the new one, how the owner-run key is wired into `levelrun`, and
the test plan. These are for the plan, after the owner approves the design.

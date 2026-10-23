# review-engine

Status: Draft. Written by plan `2026-10-23-review-engine` (increment A), before the module exists, so that the module is
built against this text. The state layer, `init`, `status`, the round, the decisions and owner commands, the setting and the skill are built
(increments C to F); "As built, and its limits" says what each is and where it is narrower than this text.
The capability name `peer-review` is the accepted one (`2026-10-19-mandatory-review-personal-delegation`).

Terms are in `terms.md`. The declaration is defined in `module-contract.md`; the launcher, the kit and the rule for a
helper that runs another module's command are in `module-boundary.md`; the contract of the bridge the engine calls is
`model-bridge.md`; the authority rules are in `trust-and-approval.md`. The decision behind it is
`2026-10-22-model-calls-go-through-vendor-bridges`, decisions 3 to 5.

## Purpose and scope

The **review engine** is a first-party module, `review-engine`, that asks a second model to review a plan, a spec, a roadmap or
a decision record, a bounded number of times, and keeps what came back. It provides the capability `peer-review`. It
gives findings and a recommendation and never a verdict: the verdict belongs to the owner until `delegated-approval`
builds the one rule that lets a delegate give it.

Non-goals:

- A vendor. The engine names no vendor and reaches a model only through a bridge (`model-bridge.md`).
- A verdict, an approval, a plan status or any change to a reviewed document. The engine is read-only towards the
  documents it reviews and writes only its own state.
- Reviewing code, a diff or an action. The four kinds are plan, spec, roadmap and ADR.
- Choosing the model for the owner: the project setting is a request and the owner's personal setting, which is not yet
  readable by a helper, will win when it can be (see "Limits").
- Listing a vendor's models. The engine cannot; a bridge could offer it later.

## Declaration

| field | value |
|---|---|
| name, type | `review-engine`, `module` |
| provides | `peer-review` |
| requires | `model-bridge` (hard) |
| ships | `helper/review-engine` and the neutral skill `peer-review` |
| commands | `review-engine`, with `helper` `helper/review-engine`, `runtime` `python`, `kit` 1 and the first `arguments` below |
| owner-run arguments | `amend`, `extend`, `reset`, `archive`, `prune` (see "Owner-run commands") |

The first arguments are `status`, `init`, `review-plan`, `review-spec`, `review-roadmap`, `review-adr`, `decide`,
`amend`, `extend`, `reset`, `archive` and `prune`. The engine is run as `wb run review-engine <argument> [...]`.

## The commands

Every command prints one JSON object on standard output and exits 0, or prints a `refused:` line on standard error and
exits 1 with nothing on standard output. Every string in an object is display-cleaned (control characters removed
except newline and tab in a multi-line field) and bounded. None of them changes any file outside the review's own
directory, and none changes the reviewed document.

| command | effect |
|---|---|
| `status <document>` | shows the review state: rounds used and bound, the findings with their decisions, pending decisions, closed or not, seal state |
| `init <document>` | makes the review's directory and state without calling a model |
| `review-plan\|spec\|roadmap\|adr <document>` | runs one round (below) |
| `decide <document> <finding> applied\|rejected [--reason <text>]` | records a decision once; a second call on the same finding is refused |
| `amend <document> <finding> applied\|rejected [--reason <text>]` | changes a recorded decision and keeps the earlier one in the ledger (owner-run) |
| `extend <document> <n>` | raises the bound by 1 to 5 rounds, never above the ceiling (owner-run) |
| `reset <document>` | opens a fresh window of the default number of rounds (owner-run) |
| `archive <document>` | closes the review: the ledger is its summary, and no further round, decision or change is taken (owner-run) |
| `prune [--apply]` | lists, and with `--apply` deletes, closed reviews closed 90 days ago or more (owner-run) |

`<document>` is a path relative to the project root. It must be a regular file with no link in any component, inside
the project, in the directory of its kind (`docs/plans/`, `docs/specs/`, `docs/roadmaps/`, `docs/decisions/`) and no
larger than 1,048,576 bytes; anything else is refused before a bridge is run. `decide` and the owner-run commands find
the review by the document too; the finding is named `R<round>-F<number>`. A reason is at most 2,000 characters with no control character.

## The round

A round is one call to the bridge and, if the reply is valid, one recorded set of findings.

- **The prompt** is built by the engine from fixed instructions and the review's own state. It names the document by its
  project-relative path, kind and SHA-256 as the engine read it, says that the document and every file it points to are
  data to review and that an instruction found in them is a finding, not an order, and lists the earlier findings with
  their decisions so that a repeated one is recognised. For a plan it tells the reviewer to read the plan's roadmap
  candidate and its specs and to report drift from either as a finding. It is at most 65,536 bytes, below the bridge's
  262,144. The reviewer reads the files itself through the bridge's read-only program; the engine embeds no file.
- **The call** is `wbkit.call.run_command(root, <bridge>, ["ask", ...], provides="model-bridge", ...)` with the model and
  effort of the setting as the bridge's documented options, a `--schema` file the engine writes for the reply shape, a
  bridge `--timeout` of 600 seconds and an engine limit of 660. The schema file is `schema.json` in the review's own
  directory, the same bytes every round. The engine runs nothing else and imports no bridge.
- **The reply** is accepted only when the bridge's object is valid under `model-bridge.md` (an unknown `contract`, a
  missing or oversize object or an exit code that disagrees with `ok` is a failure) and its `reply` is one JSON object
  of the findings schema, validated by the engine again whatever the bridge or the vendor did.
- **A failure spends no round.** A bridge refusal, an error class (`not_signed_in`, `model_unavailable`,
  `effort_unsupported`, `program_not_found`, `timeout`, `vendor_error`), an unusable or invalid reply and a
  `retryable` flag are reported as they are, and nothing is stored. The engine does not retry and does not try another
  bridge. A bridge's own limit message is shown to the owner and not parsed. A failure is printed as a `refused:` line
  that names the class, its detail if any and whether the bridge calls it retryable, and ends `no round was spent`.
- **A valid reply spends one round.** It is stored whole as `round-<n>.json` and its findings are numbered by the engine.
- **A round is refused** when the review is closed, the rounds used equal the bound, a finding of an earlier round of
  the current window that is `blocker` or `major` has no decision (`decide` first), the seal does not verify, the state
  is rolled back, or a stored round file is not the one the state names by hash. A round on a document that has no
  review makes the review first, and the seal key with it.
- **The output** is one object: `document`, `kind`, `key`, `seal`, `round`, `rounds_used`, `bound`, `verdict` (the
  reviewer's), `reading` (the engine's), `verdict_mismatch`, `summary`, `model`, `findings` (each with its `id`,
  `severity`, `location`, `problem` and `suggestion`), `meaningful` (the number of blocker and major findings),
  `pending` (the meaningful findings of the window with no decision) and `converged`.

### The findings schema

The reply object has exactly these fields; an unknown field, a wrong type or a value out of bounds fails the reply:

| field | type and bounds |
|---|---|
| `verdict` | `changes_needed` or `no_meaningful_changes`, the reviewer's recommendation |
| `summary` | string, at most 1,000 characters |
| `findings` | array of at most 100 objects |

A finding has `severity` (`blocker`, `major`, `minor` or `nit`), `location` (string, at most 500), `problem` (string, 1 to
4,000) and `suggestion` (string, at most 4,000). The engine, not the reply, numbers findings and sets their round.
`blocker` and `major` are **meaningful**.

**Converged** means the latest valid round has no meaningful finding and every meaningful finding of earlier rounds has
a decision. The reviewer's `verdict` is recorded beside the engine's own reading, and a disagreement is reported as
`verdict_mismatch`. Neither is an approval.

### Rounds, the bound and the ceiling

The default bound is 3 rounds. `extend` raises it, by 1 to 5 at a time, and never beyond a ceiling of 5 rounds in a
window. `reset` opens a new window with the default bound; the earlier rounds stay in the state. At the bound, a run
stops and reports what is still undecided, for the owner to decide. These numbers are the engine's own; the loop caps
that `code-work` declares are separate and are not read here.

## State

A review lives in its own directory in the project, `.workbench/workbench/review-engine/<key>/`, where `<key>` is the kind, a
hyphen and the first 16 hex digits of the SHA-256 of the document's project-relative path with its case and Unicode
form folded (so `Plan.md` and `plan.md`, one file on a case-insensitive disk, are one review; on a case-sensitive disk
two files that differ only so share a review). The directory is committed
with the project, so a clone and a teammate keep the history. It holds:

- `state.json`: strict JSON with exactly the fields `format` (1), `kind`, `path`, `window`, `rounds`, `decisions`,
  `closed`, `generation` and `seal`. The `window` is `{"first": <the number of the window's first round>, "bound": <1 to 5>}`, so the
  rounds used are the rounds from `first` on. A round is a record with exactly `n`, `file` (`round-<n>.json`), `sha256`
  (of that file), `document_sha256`, `at` (a UTC time), `bridge`, `requested` (`model` and `effort`, each or null),
  `model` (as the bridge reported it, cleaned, at most 200 characters, or null), `verdict` (the reviewer's), `reading`
  (the engine's: `changes_needed` if any finding is `blocker` or `major`), `mismatch`, `usage` (three counts or null; a
  count above 2,147,483,647 is stored as null) and `findings` (each with `id` and `severity`, numbered in order). Each
  decision records the finding, the choice (`applied` or `rejected`), the reason and its earlier values. `closed` is a
  UTC time or null; `generation` is a count that every save raises by one;
- `round-<n>.json`: the stored reply of round n, cleaned: `format`, `round`, `verdict`, `summary` and the findings
  with their `id`, `severity`, `location`, `problem` and `suggestion`;
- `schema.json`: the schema the reply is asked to follow, the same bytes in every round;
- `ledger.md`: a readable rendering of the above, regenerated on every change and never read back.

Every write is atomic (a temporary file in the same directory, flushed, then renamed) through the kit's no-follow file
layer, and a lock in the guarded store (below) stops two runs at once: the lock is the file `lock` beside the key, held
without waiting, and a run that cannot take it is refused.

A state read from the project is untrusted: it is parsed as strict JSON of at most 4,194,304 bytes, must have exactly the
fields above, must name the same kind and path as the review's directory, and every string in it must be at most 4,000
characters with no control character. A state that fails any of this is reported as not usable and is treated as
unsealed.

### The seal

The state is an agent-writable file in the project, so tampering is made visible:

- The helper keeps a random 32-byte key at `projects/<id>/review-engine/seal-key` in the guarded store, made on first use
  (by `init` or a round, never by `status`) with mode 0600 in directories of mode 0700. `<id>` is the project's recorded
  identity, read as the kit's `project` module reads it. A key that exists but is not 32 bytes, or is a link, is never
  replaced: the engine refuses and the owner removes it.
- `state.json` carries `seal`, the HMAC-SHA256 of the canonical JSON of every other field (sorted keys, no spaces,
  UTF-8). The state names each round file by SHA-256, so the seal covers the rounds too.
- A state whose seal does not verify, or that cannot be verified because there is no key (a fresh machine), is
  **unsealed**. An unsealed review can be read with `status` and can be `reset` by the owner, and runs no round, takes
  no `decide` and no `extend`.
- **Rollback.** A seal detects change, not replay: an older state is still validly sealed. So the helper also keeps, in
  the guarded store beside the key, a mark per review of the highest count of rounds, of decisions and the highest generation it has sealed, in
  `marks/<review key>`. A save writes the state first and the mark second, and the mark never goes down. A state below
  the mark in any of the three is **rolled back**; it is reported as such and treated like an unsealed one. The
  generation is what shows a replayed older state that has the same counts (it would otherwise reopen a closed review
  or undo a `reset`). A state file that is gone while the mark holds a round or a decision is also rolled back, not "no
  review". A mark that cannot be read is reported as unsealed. A machine that has not seen the later state has no mark, so a rollback there
  is not detected.
- The helper reaches the guarded store by the fixed path under the home directory, through the kit's no-follow layer,
  because the kit has no store accessor. That couples the helper to the store's `projects/<id>/` layout; a kit
  accessor would remove it and is a kit change with a new API number, deferred.
- These guard against a mistaken or careless agent and a casual edit. An agent that can read the key can forge a state,
  and the guarded store is a mechanical barrier under the owner's account (`trust-and-approval.md`). The harness
  denies the agent writes to the store; it does not make the store unreadable.

## The project setting

`.workbench/review.json` is project-owned configuration the engine reads and does not install (accepted record,
decision 5). It is strict JSON, at most 4,096 bytes, with:

| field | meaning |
|---|---|
| `format` | `1`, required |
| `bridge` | the name of the bridge command (for example the first-party `ask-codex`), required to run a round |
| `model` | optional; the bridge's `--model` value, with the bridge's own charset and length |
| `effort` | optional; `low`, `medium` or `high` |

It is a request and never an authorization. A round runs only if the named bridge is an installed module that provides
`model-bridge`, is pinned, and is unchanged since the pin; the launcher decides that and refuses otherwise, and the
engine then runs nothing and tries no other bridge. There is no default bridge: a missing or malformed file, or one
with no `bridge`, is a refusal that names the file, because the kit cannot list installed bridges and the engine will
not guess a vendor to send content to. The settings used are recorded in each round. A pulled commit that changes the
file is a difference `wb acknowledge` lists, and the next round records the changed request. `status` says when the
setting now differs from what the last round asked.

## Owner-run commands

`amend`, `extend`, `reset`, `archive` and `prune` change what a review allows or destroys what it recorded, so they are
the owner's. The declaration lists them as owner-run arguments, and the installer renders a `deny` rule for
`wb run review-engine <argument>` in each harness that provides `permissions`, as it does for the installer's own owner-run
commands. The rule names the first argument only, which is why `decide` (a once-only record) and `amend` (a change of
one) are separate arguments. The rule is restrictive and is a mistake guard, not a security boundary: a command spelling
it does not match runs. The agent's `decide` is allowed. This repository's owner may, by habit, run `decide` themselves;
nothing in the engine requires it.

## What leaves the machine

The bridge's vendor program reads the document and may read any file it can open (`model-bridge.md`, "What the vendor
program can read"). So:

- Installing a bridge is the owner's consent to send content to that vendor, and the engine adds none.
- The engine refuses a document outside the project, over its bound or in the wrong directory, and tells the agent, in
  its skill, to keep secrets out of any file a review may read.
- The engine writes no prompt and no reply anywhere but the review's own directory, which is in the project.

## Untrusted input

- A reviewed document is hostile input. The prompt marks it as data, and a reply is checked against the schema; nothing
  in a reply is run, followed or used as a path, and a finding's text is cleaned and bounded before it is stored.
- A bridge is untrusted. The engine trusts no claim of read-only behaviour and rechecks every field.
- The state files are untrusted on read: strict JSON, bounded, and checked against the seal and the mark before use.

## Conformance checklist

The module conforms when tests against a fake bridge, installed as a real pinned module in a temporary project, show:

1. The declaration is as above, and the installer renders a deny rule for each owner-run argument and none for the
   others.
2. A document outside the project, in the wrong directory, a link, a non-regular file or over the bound is refused and
   no bridge runs; a path with `..` or an absolute path is refused.
3. A round runs the bridge only through `run_command` with `provides` `model-bridge`; a bridge that is not installed,
   not pinned, not a `model-bridge` or edited since the pin is refused and nothing else runs.
4. A missing, malformed or bridge-less `.workbench/review.json` is refused naming the file; the model and effort reach
   the bridge only as its documented options.
5. A valid reply is stored with numbered findings; a reply that is not one object of the schema, has an unknown field, a
   wrong type, an oversize string, more than 100 findings or a bad severity is a failure and spends no round.
6. Each bridge error class is reported as it is and spends no round; the engine never retries.
7. A hostile reply (instruction text, control characters, markup, a path-like string, an oversize value) is stored only
   as cleaned, bounded text and changes nothing the engine does.
8. A pending meaningful finding blocks the next round; `decide` records once and refuses a second call and an unknown
   finding; `amend` changes it and keeps the earlier value in the ledger.
9. The bound of 3, `extend` by 1 to 5 up to the ceiling of 5, `reset` and `archive` behave as stated, and a closed review
   runs no round.
10. A state edited by hand, a state with a missing key, and a state restored to an older sealed copy are each refused for a
    round, a `decide` and an `extend`, are readable with `status`, and are named unsealed or rolled back.
11. `prune` without `--apply` changes nothing; with it, it deletes only closed reviews older than the retention that the
    engine created, never another path.
12. The reviewed document and every other project file are byte for byte the same before and after every case, and the
    only files written are the review's own directory and the guarded store's key, mark and lock.
13. Every case prints exactly one object that obeys the field rules, or a `refused:` line and nothing on standard output.

## Acceptance criteria

- The spec states the command surface, the schema, the bounds, the state and seal, the setting and the owner-run rule, and
  every item above can be tested against a fake bridge.
- A module built to it passes the checklist, with the installer's deny rules pinned by a drift test.
- Nothing here depends on a file outside the repository, and nothing in `workbench/` names this module.

## Limits and open questions

- The personal setting for bridge, model and effort (accepted record, decision 5) is not built: no helper can read the
  owner's personal settings. Until then the project file is the only source.
- The seal is tamper-evident for a careless agent, not a boundary against one that can read the key; a rollback is
  detected only where the mark exists.
- A committed state can conflict when two people review one document; the owner `reset`s the review.
- The helper builds the guarded-store path itself; a kit accessor would be a kit change.
- Whether `decide` should itself be owner-run is the owner's call; it is a change to one list.
- Whether the engine should refuse a bridge by vendor name is not decided; it refuses by the launcher's rules only.

## As built, and its limits

Built by plan `2026-10-23-review-engine`, increments C to F (the module `review-engine`, version 0.1.0):

- The declaration provides `peer-review`, requires `model-bridge` (hard) and declares the command `review-engine` with
  the twelve arguments of "The commands" and the `owner` list `amend`, `extend`, `reset`, `archive`, `prune`. It ships
  the neutral skill `peer-review`. The package has no shipped approval until the plan's last increment.
- Document resolution for the four kinds, the key and the directory name, the state file and its checks, the seal, the
  key and the mark in the guarded store, the lock, atomic writes and the ledger are built as stated above.
- `init <document>` makes an empty review (a window of 3 rounds) and prints its status; it refuses a review that
  already exists, including one whose state file is a link. `status <document>` prints one object with `document`,
  `kind`, `key`, `seal` (`ok`, `unsealed` or `rolled_back`) and `reason`, and, when the state could be used,
  `rounds_used`, `rounds_total`, `bound`, `ceiling`, `decisions_total` and `closed`. It refuses a document that has no
  review and never writes. The reasons are: there is no seal key on this machine; the seal key is not usable; the
  state is not usable; the seal does not match; the rollback mark is not usable; the state is older than the last one
  sealed here.
- Entries of `rounds` are checked field by field (numbered one after the other, hashes, time, bridge name, request,
  verdicts, usage and the numbering of their findings). Entries of `decisions` are checked only as bounded objects of
  clean strings, small whole numbers, lists, objects and null, until the increment that writes them.
- A state is refused when it would be larger than 4,194,304 bytes once written, so that it can always be read back.
- The round (increment D): `review-plan`, `review-spec`, `review-roadmap` and `review-adr` read `.workbench/review.json`
  (strict, at most 4,096 bytes, `format` 1, `bridge`, optional `model` and `effort`; a missing or bridge-less file is a
  refusal that names it, and no bridge is chosen), take the lock for the whole round, refuse a closed review, a full
  window, an undecided meaningful finding, an unsealed or rolled-back state and a stored round file that is missing,
  linked or not the one the state names, build the prompt, write `schema.json`, and run the bridge only through
  `wbkit.call.run_command` with `provides` `model-bridge`, `--timeout 600` and an engine limit of 660 seconds. The
  bridge's answer and the reply are validated again; a failure prints a `refused:` line and stores nothing but
  `schema.json`. Tested with the real launcher and the real first-party bridge against a fake vendor program; no real
  vendor, session or network call was used.
- The prompt names the document by path, kind and hash and never embeds it. Earlier findings are quoted in it, one line
  each, cut to 300 characters, with their decisions; when they do not fit in 65,536 bytes the oldest are left out and
  the prompt says so. A finding that was model output is therefore model input to the next round, which is why the
  prompt calls it data.
- The security pass over C and D (two read-only reviewers, with experiments on scratch copies) found no critical or
  high finding. Four findings were fixed: a deleted state file reset the round budget; a replayed older state with the
  same counts passed as sealed; the case or Unicode form of a path made a second review and defeated the bound; and a
  decision's choice was put into the next prompt without a bound. The rest are in the limits below.
- A second security pass, over E and F (two read-only reviewers; both stopped at a turn limit and were asked to finish,
  so some checks were not run: the real-launcher refusal tests, the launcher's handling of `--provides=` and `--`,
  multi-process races, case-insensitive disks), found no critical or high finding. Five were fixed (the ledger heading
  was unescaped; a damaged round file named a `reset` that does not help; one unreadable directory stopped `prune`; the
  generation at its largest gave no way out; `reset` of a replaced state said nothing of what it replaced), and the
  skill no longer treats a plan's say-so as the owner's request. A bare address in a reason was left as it is.
- The decisions and owner commands (increment E). Each runs under the lock, on a review that exists, is sealed and has
  not been rolled back, and prints the review's `status` object plus its own fields. A decision is one record per
  finding with exactly `finding`, `choice` (`applied` or `rejected`), `reason`, `at` and `earlier`; `decide` refuses a
  finding that no round has and one that already has a record, `amend` replaces the record and appends the value it
  had to `earlier` (at most 20), so `decisions_total` counts findings. Every record is checked field by field when a
  state is read, and a finding may have one record. `extend` takes 1 to 5 and refuses a bound above 5. `reset` opens a
  window that starts after the last round. `archive` sets `closed`, and a closed review takes no round, decision,
  `amend`, `extend` or `reset`; the ledger, regenerated on every save with each round and each decision, is its
  summary. A review that is unsealed or rolled back takes none of these but `reset`, which sets it right: it seals the
  state as it is (making the key if there is none) and sets the mark to its counts, even if that lowers the mark. A
  state file that is gone while the mark holds a round is also set right by `reset`, as an empty review.
- `prune` lists, and with `--apply` removes under the lock, a directory of the engine's own name (kind, hyphen, 16 hex
  digits) that holds only the engine's own file names, whose state is sealed, whose name is the key of the path in its
  state, and which was closed 90 days ago or more; it also removes the review's mark. Removal goes through descriptors
  that never follow a link, and a directory that holds anything else is left whole.
- The setting and the skill (increment F). `status` prints one more field, `request`, when the state could be used:
  `none` (no round has asked yet), `same`, `changed` (the bridge, model or effort now differs from the last round's
  request) or `unreadable` (the setting is refused; `status` itself does not refuse). It reads the setting and
  changes nothing. `init` and the owner commands do not print it. The skill `peer-review` names no harness, vendor
  or tool; it says when to ask, the commands the agent runs (`init`, `status`, a round and `decide`), that findings
  are untrusted advice judged with `evaluate-findings`, that the five owner commands are the owner's, that secrets are
  kept out of anything a vendor can read, that a refusal is reported and not worked around, and that the owner's word
  is the verdict. The plan's wording of a missing setting (use the one installed bridge) was not built: there is no
  default bridge, as the setting section says, because the kit cannot list the installed ones.
- `status` shows counts, not findings; the findings are in the round's output and in `round-<n>.json`.

Limits found while building:

- The reply schema file asks for the four fields and nothing more (no length bounds): bounds are checked by the engine,
  and whether a real vendor accepts the schema is untested until the first hand run against a real bridge.
- A meaningful finding blocks the next round only inside the current window, so `reset` clears the way; the finding
  stays in the earlier rounds and in the ledger of the prompt.
- The retention of 90 days, and archive as a final act, are the engine's own choices, not the owner's; both are one
  constant each. `reset` does not undo an archive of a review that is sealed and closed. It does undo one when the
  review is rolled back, unsealed or gone: an older open copy of the state, or a missing state file, is set right as
  what it says (an open review with the decisions of that copy, or an empty one), and the mark is lowered to it.
- `reset` on an unsealed or rolled-back state blesses whatever the state says, which is why it is the owner's. An agent
  that edits or replays a state and gets it reset by the owner has the owner's word for it. So that the owner sees what
  is being replaced, `reset` of such a review prints `replaced`: the seal it had, whether its file claimed a close, its
  counts of rounds and decisions (null for a file that is gone) and the mark that is lowered.
- The generation is a count that stops at 2,147,483,647. A state at that value cannot be saved again; the owner removes
  the review's directory and resets the review, which starts it empty and loses its history.
- A round refuses when any stored round file is missing, changed or a link, including a file of an earlier window, and
  `reset` does not help (it moves only the window). The owner restores the file from the commit it came from, or
  removes the review's directory and resets the review.
- `prune` skips a directory whose state file cannot be read (a second link, over the bound, a link) and goes on with
  the others; it does not report what it skipped. A directory with a file of another name, or a directory inside it,
  is left whole and is not listed.
- The ledger shows the document's path and a decision's reason with markup characters replaced by spaces, so a name
  such as `a_b.md` reads `a b.md` there. A bare web address in a reason is kept as text and a viewer may link it.
- The project's identity is read from the committed seed in `.workbench/manifest.json`, so a clone that copies the seed
  shares this project's key, marks and lock in the guarded store. It cannot forge a seal without the key, but it can
  raise a mark and so make the real review read as rolled back. The state is not compared with the current document: a
  review whose document changed since its last round still reads as `ok`.
- A deleted mark file reads as no mark, which is the documented limit of a mark that needs the guarded store.
- The document is hashed before the bridge call, which can last 11 minutes, and the vendor reads the path itself, so a
  swap of the file in between can show the reviewer other content than the hash names.
- A process that the bridge starts in a session of its own survives a timeout, because the engine ends the process
  group. `wbkit.call` also treats a `PATH` entry that does not exist yet as outside the project.
- The module is named `review-engine`, not `review`: the installer's boundary test refuses any module, command or helper
  name as a substring in `workbench/` and `tests/`, and `review` is an ordinary word there.
- A review's directory is inside the module's namespace, `.workbench/workbench/review-engine/`, beside the installed
  helper. Whether an upgrade or `wb check` leaves a file there alone is checked when the package is installed (the
  plan's last increment).

# review-engine

Status: Draft. Written by plan `2026-10-23-review-engine` (increment A), before the module exists, so that the module is
built against this text. Nothing here is built yet; "As built, and its limits" is filled by the plan's last increment.
The capability name `peer-review` is the accepted one (`2026-10-19-mandatory-review-personal-delegation`).

Terms are in `terms.md`. The declaration is defined in `module-contract.md`; the launcher, the kit and the rule for a
helper that runs another module's command are in `module-boundary.md`; the contract of the bridge the engine calls is
`model-bridge.md`; the authority rules are in `trust-and-approval.md`. The decision behind it is
`2026-10-22-model-calls-go-through-vendor-bridges`, decisions 3 to 5.

## Purpose and scope

The **review engine** is a first-party module, `review`, that asks a second model to review a plan, a spec, a roadmap or
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
| name, type | `review`, `module` |
| provides | `peer-review` |
| requires | `model-bridge` (hard) |
| ships | `helper/review` and the neutral skill `peer-review` |
| commands | `review`, with `helper` `helper/review`, `runtime` `python`, `kit` 1 and the first `arguments` below |
| owner-run arguments | `amend`, `extend`, `reset`, `archive`, `prune` (see "Owner-run commands") |

The first arguments are `status`, `init`, `review-plan`, `review-spec`, `review-roadmap`, `review-adr`, `decide`,
`amend`, `extend`, `reset`, `archive` and `prune`. The engine is run as `wb run review <argument> [...]`.

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
| `decide <finding> applied\|rejected [--reason <text>]` | records a decision once; a second call on the same finding is refused |
| `amend <finding> applied\|rejected [--reason <text>]` | changes a recorded decision and keeps the earlier one in the ledger (owner-run) |
| `extend <n>` | raises the bound by 1 to 5 rounds, never above the ceiling (owner-run) |
| `reset` | opens a fresh window of the default number of rounds (owner-run) |
| `archive` | writes the closed summary and refuses any further round (owner-run) |
| `prune [--apply]` | lists, and with `--apply` deletes, closed reviews older than the retention (owner-run) |

`<document>` is a path relative to the project root. It must be a regular file with no link in any component, inside
the project, in the directory of its kind (`docs/plans/`, `docs/specs/`, `docs/roadmaps/`, `docs/decisions/`) and no
larger than 1,048,576 bytes; anything else is refused before a bridge is run. `decide` and the owner-run commands find
the review by the document too; the finding is named `R<round>-F<number>`. A reason is at most 2,000 characters.

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
  bridge `--timeout` of 600 seconds and an engine limit of 660. The engine runs nothing else and imports no bridge.
- **The reply** is accepted only when the bridge's object is valid under `model-bridge.md` (an unknown `contract`, a
  missing or oversize object or an exit code that disagrees with `ok` is a failure) and its `reply` is one JSON object
  of the findings schema, validated by the engine again whatever the bridge or the vendor did.
- **A failure spends no round.** A bridge refusal, an error class (`not_signed_in`, `model_unavailable`,
  `effort_unsupported`, `program_not_found`, `timeout`, `vendor_error`), an unusable or invalid reply and a
  `retryable` flag are reported as they are, and nothing is stored. The engine does not retry and does not try another
  bridge. A bridge's own limit message is shown to the owner and not parsed.
- **A valid reply spends one round.** It is stored whole as `round-<n>.json` and its findings are numbered by the engine.
- **A round is refused** when the review is closed, the rounds used equal the bound, a finding of an earlier round
  that is `blocker` or `major` has no decision (`decide` first), the seal does not verify, or the state is rolled back.

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

A review lives in its own directory in the project, `.workbench/workbench/review/<key>/`, where `<key>` is the kind, a
hyphen and the first 16 hex digits of the SHA-256 of the document's project-relative path. The directory is committed
with the project, so a clone and a teammate keep the history. It holds:

- `state.json`: strict JSON with a format number, the kind and path, the settings used, the window and bound, the rounds
  (each with its file name and SHA-256, the document's SHA-256, the model reported, the verdict, the engine's reading
  and the usage counts), the decisions (each with the finding, the choice, the reason and its earlier values), the
  closed time, and the seal;
- `round-<n>.json`: the stored reply of round n;
- `ledger.md`: a readable rendering of the above, regenerated on every change and never read back.

Every write is atomic (a temporary file in the same directory, flushed, then renamed) through the kit's no-follow file
layer, and a lock in the guarded store (below) stops two runs at once.

### The seal

The state is an agent-writable file in the project, so tampering is made visible:

- The helper keeps a random 32-byte key at `projects/<id>/review/seal-key` in the guarded store, made on first use with
  mode 0600. `<id>` is the project's recorded identity, read as the kit's `project` module reads it.
- `state.json` carries `seal`, the HMAC-SHA256 of the canonical JSON of every other field (sorted keys, no spaces,
  UTF-8). The state names each round file by SHA-256, so the seal covers the rounds too.
- A state whose seal does not verify, or that cannot be verified because there is no key (a fresh machine), is
  **unsealed**. An unsealed review can be read with `status` and can be `reset` by the owner, and runs no round, takes
  no `decide` and no `extend`.
- **Rollback.** A seal detects change, not replay: an older state is still validly sealed. So the helper also keeps, in
  the guarded store beside the key, a mark per review of the highest count of rounds and of decisions it has sealed. A
  state below the mark in either count is **rolled back**; it is reported as such and treated like an unsealed one. A
  machine that has not seen the later state has no mark, so a rollback there is not detected.
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
file is a difference `wb acknowledge` lists, and the next round records the changed request.

## Owner-run commands

`amend`, `extend`, `reset`, `archive` and `prune` change what a review allows or destroys what it recorded, so they are
the owner's. The declaration lists them as owner-run arguments, and the installer renders a `deny` rule for
`wb run review <argument>` in each harness that provides `permissions`, as it does for the installer's own owner-run
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

Nothing is built.

# Module and package contract

Status: Current. Approved by the owner on 2026-10-19. The declaration verifier
(`installer-core-verifier`) implements this specification, and "Concrete schema" records
the field names, formats and limits it accepts. The rules are the substance of this
specification; where the table descriptions and "Concrete schema" differ in precision,
"Concrete schema" is the one the code enforces.

Terms are defined in `terms.md`. The fields `commands` and `checks` and the pin-name rule are specified by
`module-boundary.md` and added here on 2026-10-21; `commands` is built, and so are the `checks` field, the pin-name rule, the approval request's list of checks
and running a check with `wb check`. The maintainer directories `tests/` and
`tools/`, specified there too, are built.

## Purpose and scope

This specification defines what a package and a module declare about themselves,
and the rules the installer applies to those declarations before it writes
anything: types, capabilities, requirements, conflicts and verification. It is the
interface between the installer and everything it installs.

Non-goals:

- How files are written, upgraded or attached. That is the repository boundary and
  upgrade specification.
- How approval is recorded and how trust is judged. That is the trust and approval
  specification, which this one only feeds with the declaration and content hash.
- The translation mapping a harness module uses for neutral items.
- The content of any module (`groundwork`, `code-work` and so on).

## Assumptions and constraints

- The installer only copies files. It never executes anything a package or module
  ships at install, and it never evaluates its declaration as code. Declarations are data. The
  launcher and the delegation helper are components of the workbench itself, not
  module items; the installer installs them, and they run a module's helper only when
  invoked at use time, never at install. At use time a pinned helper runs through the launcher:
  by `wb launch`, and, for a declared command or check, by `wb run` and `wb check`
  (`module-boundary.md`).
- The installer treats every package the same way. A first-party package differs
  only in where it comes from and in carrying pre-generated approvals.
- All writes stay inside the project, and a module's own writes stay inside its
  own namespace (see "Writes").

## Package declaration

A package has one declaration file at its root, `package.json`.

| field | meaning |
|---|---|
| `name` | The package name. Lowercase kebab-case. |
| `version` | The package version: dotted integers such as `1.2.3`, compared numerically. |
| `contract` | The contract version the package targets, an integer. |
| `modules` | The names of the modules the package contains. |

The installer refuses a package whose `contract` is greater than the highest it
supports. Reserved names (`local`, `neutral`, and any name beginning `manifest`)
cannot be a package name or a module name.

## Module declaration

Each module has one declaration file, `module.json`, at the root of its directory.

| field | meaning |
|---|---|
| `name` | The module name, unique within its package. |
| `version` | The module version, in the same form as a package version. |
| `type` | One of the types below. Exactly one. |
| `description` | One line for people. |
| `provides` | Capabilities the module supplies. |
| `requires` | Capabilities it needs. Each entry is a name, optionally marked `soft`. |
| `blocks` | Capabilities it cannot coexist with. |
| `helpers` | Tools expected on `PATH`. |
| `slots` | Slots the module owns, by name. |
| `fills` | Blocks the module contributes: the slot, and the source file. |
| `writes` | The project paths the module writes, beyond its own namespace. |
| `ships` | Executable or code-bearing items it ships, such as hooks or helper scripts. |
| `commands` | Commands it offers, each a helper it ships and the first arguments it accepts, run with `wb run`. A command may also list `describes`, the actions its `describe` argument answers (`module-boundary.md`, "Declaration schema"; *built*). The installer pins the helper when the owner confirms the install; nothing in the name of the shipped file declares a command. A command may also list `owner`, the arguments only the owner runs, which a harness that provides `permissions` denies the agent (`module-boundary.md`, "Declaration schema"). *(built: verified, and run with `wb run`; `owner` built by plan `2026-10-23-review-engine`)* |
| `checks` | Pinned Python helpers it contributes to `wb check`. *(built: verified, listed in the approval request, and run by `wb check`)* |
| `approval` | Process modules only: the command of its own that computes the hashed region of a plan and, optionally, the argument that lists the plans under way. *(built by plans `2026-10-22-plan-approval-records` and `2026-10-22-checkpoint-settings-and-caps`)* |
| `checkpoints` | Process modules only: the names of the checkpoints it asks the owner about. *(built by plan `2026-10-22-checkpoint-settings-and-caps`)* |
| `caps` | Process modules only: the loop caps it enforces, each with a default and a ceiling. *(built by plan `2026-10-22-checkpoint-settings-and-caps`)* |
| `layout` | Harness modules only: the layout description (see `harness-modules.md`). It is part of the declaration and its hash. |

`provides`, `requires` and `blocks` are lists of capability names. A module that
provides nothing, requires nothing and blocks nothing is valid.

## Types and counts

The set of types is closed and owned by the installer. A module has exactly one.

| type | count per project |
|---|---|
| `harness` | exactly one |
| `process` | at most one |
| `module` | any number (the default) |

- A project must have a harness module at install. A clone may have none attached
  until a harness is attached.
- The installer stops when a project would have two harness modules or two process
  modules.
- Install order is: harness, then the base (which is not a module and has no type),
  then the process module, then every other module. Within a group, modules are
  ordered so that a module follows the modules it requires. A requirement on a module
  in a later group is allowed and does not change the order: every requirement is
  resolved before any file is written, so group order never decides whether one is met
  (a process module may require a capability that an ordinary module provides). Only a
  cycle in `requires`, within a group or across groups, is an error, and the message
  names the cycle. A slot fill counts as a soft requirement for ordering. The harness module is verified and approved first, but the per-clone
  harness files it describes are written last, by attach, after the committed content
  (see `repository-boundary.md`).

## Capabilities

A capability is a case-sensitive string with no spaces. All capabilities share one
namespace.

- **Core names.** Unprefixed names are reserved for the core contract. The harness
  capabilities are `instructions`, `skills`, `agents`, `commands`, `hooks` and
  `permissions`. Other core names are defined by the specifications that need them
  (for example `plans`, `specs`, `roadmaps`, `decisions`, `references`,
  `peer-review`, `security-review`, `discovery`). This specification names only the six harness
  capabilities; the full list of core names is the union of the capabilities that
  each specification defines.
- **Harness capabilities** may be provided only by a module of type `harness`.
  Other core names may be provided by any approved module.
- **Third-party names** are prefixed with their package, `<package>:<name>`.
  A package may not provide an unprefixed name unless it is the first-party package.
  A package is the first-party package only when its directory is directly inside the workbench
  distribution's `packages/` directory and is not a symbolic link, its declared name equals its
  directory name, and a shipped approval record for that package matches its current declaration
  hash and whole-package tree hash (`trust-and-approval.md`, "First-party packages"). A first-party
  package that has changed since its release is treated as third-party until it is released again.
- **Slots.** A slot is the capability `slot:<name>`. The module that owns the slot
  provides it. The base is not a module, so the slots the base owns are provided
  implicitly by the base and are always present. A module that fills a slot has a
  soft requirement on it. When several modules fill one slot, each contributes its
  own block, delimited by its own markers.
- **Sub-names.** A dotted refinement (`permissions.deny-read`) may be introduced
  later. A provider of the specific name satisfies a requirement for the general
  one. No sub-names are defined by this version.
- A new core name is added only when a module needs it, and only by changing a
  specification.

## Requirements

- A `requires` entry is **hard** unless marked `soft`. A hard requirement with no
  provider stops the install and names the capability and the modules that could
  supply it.
- A **soft** requirement with no provider produces a warning and the install
  continues.
- A requirement for a harness capability is always soft, whatever it is marked: a
  harness that lacks a capability yields a warning and the module's affected items
  are skipped, not an error.
- A slot fill is always soft.
- A cross-package need is satisfied by capability only. The installer never selects
  or fetches a package on its own; when nothing provides a hard requirement it tells
  the user to add a package that does.
- A **helper** is looked up on `PATH`. A missing helper is a warning. The installer
  never runs a helper.

## Conflicts

- A module's `blocks` names a capability. The module cannot be installed with any
  module that provides it. The check is symmetric: it applies whichever module is
  installed first.
- A module never conflicts with its own `provides`. A module that provides and
  blocks the same capability therefore allows exactly one provider, which is how an
  "at most one" rule is expressed beyond the closed types.
- Conflicts are checked after requirements are resolved and before any file is
  written. A conflict is a hard stop with no override, and the message names both
  modules.
- `blocks` is not restricted by name. An approval request flags a module that blocks
  a core capability as high risk.

## Writes

- A module writes only to its own namespace, `.workbench/<package>/<module>/`, to
  the slots it declares in `fills`, and to the paths it lists in `writes`.
- Paths in `writes` must be relative, must not leave the project, must not pass
  through a symbolic link, and must not name `.git`, the guarded store, or a path
  inside another module's namespace.
- A harness module additionally writes the per-clone harness files described by its
  own layout. Those paths are not committed.
- **A harness module declares no `writes` and no `fills`** *(built by `base-and-manifests`)*.
  Its files are per-clone, and a committed file would name the harness. A declaration that gives
  either is refused at install.
- **Base-owned slots** *(built by `base-and-manifests`)*: `policy`, in `AGENTS.md`, and
  `docs-index`, in `docs/README.md`. A fill of either needs no selected owner and gives no
  warning, and a module whose `slots` names one is refused, because a slot has one owner. A
  slot fill with no owner and not base-owned is still a warning.

## Verification before anything is written

The installer verifies a module before it writes any of the module's files:

1. The declaration parses, has valid field values, a valid type, and valid names.
2. The module's files match its declaration: every `fills` source and every item in
   `ships` exists, every `writes` entry has its source under `files/`, and no file
   exists in the module that its declaration does not account for. A file is
   accounted for when it is `module.json`, is under a reserved directory (`harness/`,
   `templates/`, `files/` or the maintainer directories `tests/` and `tools/`), or is
   named by `fills` or `ships`. A module that
   contains a symbolic link is refused, because the content hash cannot cover what a
   link points to. A mismatch stops the install.
3. The declaration hash and the module's content tree hash are computed. A
   declaration hash is taken over the declaration in a canonical form (fields sorted,
   no insignificant whitespace). The pair is what an approval binds to, and what the
   lock records.
4. Type counts, requirements and conflicts pass.

If any step fails for any module, nothing is written for any module.

## Module layout

A module directory contains `module.json` and any directories its declaration
names. The reserved directories are `harness/` (harness items), `templates/`
(documents created on demand, never installed as placeholders) and `files/` (the
sources copied to the paths in `writes`, at the same relative path). Two more are
**maintainer directories**: `tests/` (the module's own tests) and `tools/` (scripts for
its maintainers). Both are covered by the tree hash and the approval, neither is installed, and the
installer never runs either (`module-boundary.md`, "Module directories"). Where a module
supplies harness items it uses:

```text
<module>/
  module.json
  harness/
    neutral/        neutral items, translated for the attached harness (optional)
    <harness>/      per-item overrides for one harness (optional)
      manifest.json   optional; may list items to exclude, each with a reason
```

- At least one of `harness/neutral/` and a `harness/<harness>/` directory exists in
  a module that supplies harness items.
- An override matches a neutral item by kind and name. An override in
  `harness/<harness>/` replaces the translation of that one neutral item; other
  neutral items are still translated.
- An `exclude` entry must name an item that exists in `harness/neutral/`. An item
  that is both overridden and excluded is an error. Every exclusion is reported when
  the module is installed.
- The translation mapping itself is declared by the harness module and applied by
  the installer. It is specified separately.

## Concrete schema

This is what the verifier accepts. Anything else is refused. Every refusal names its
scope (the package, or one module of it) and the field or rule that failed.

**Files.** A declaration is read as bytes, never evaluated. It must be UTF-8 without a
byte-order mark, at most 1 MiB, and nested at most 32 levels. The top level is an
object. A duplicate key, an unknown field, NaN, Infinity and any number with a fraction
or exponent are refused, and so is a string that is not valid Unicode (a lone surrogate).
A module file is at most 16 MiB.

**Formats.**

| item | form |
|---|---|
| name (package, module, slot) | `^[a-z][a-z0-9-]*$`, at most 64 characters; `local`, `neutral` and anything beginning `manifest` are reserved |
| version | one to four dot-separated non-negative integers, no leading zeros, at most 64 characters, compared numerically |
| `contract` | an integer from 1 up to the highest supported (1) |
| capability | printable ASCII, no spaces, at most 64 characters, as `name` (core), `<package>:name` (third party) or `slot:name`; dotted sub-names are refused |
| `description` | one printable line, 1 to 200 characters |
| helper | a plain tool name: letters, digits and `._+-`, at most 64 characters |
| path (`writes`, `ships`, `fills` source) | relative, at most 512 characters, no empty, `.` or `..` segment, no backslash, colon or non-printable character, and no segment equal to `.git` after case folding and trimming trailing dots and spaces (nor `git~N`) |

**Package fields.** `name`, `version`, `contract` and `modules` are all required. Each
`modules` entry names a directory of the package that holds a `module.json`; no entry
is listed twice, and no directory holding a `module.json` is left unlisted.

**Module fields.** `name`, `version` and `description` are required. Optional:
`type` (default `module`), `provides`, `requires`, `blocks`, `helpers`, `slots`,
`fills`, `writes`, `ships` (default empty), `commands`, `checks`, `approval`, `checkpoints`, `caps` and `layout`. The list entry in `package.json`,
the directory name and `name` in `module.json` must be equal. No list holds a duplicate.

- `requires` entries are a capability, or `{"capability": "<capability>", "soft": true}`.
- `slots` lists the names of the slots the module owns. The module then provides
  `slot:<name>`, so `provides` may not list a `slot:` capability.
- `fills` entries are `{"slot": "slot:<name>", "source": "<path>"}`, one per slot.
- `layout` is required for a `harness` module and forbidden otherwise. It is an object
  whose keys come from `root`, `kinds`, `local_settings`, `hooks`, `exclude`,
  `tolerated` and `notes`; the values are checked by the harness specification, not here.
- `provides`: a harness capability only from a `harness` module; an unprefixed name only
  from the first-party package; a prefixed name's prefix equals the package name.
- `writes`: a path may enter `.workbench/` only under the module's own namespace
  `.workbench/<package>/<module>/`, and may not name the guarded store
  (`.config/project-workbench`). Case, Unicode normalization and trailing dots and
  spaces are folded before these checks. No two paths collide after folding or nest as
  file and directory.
- `ships`: each item is a file, or a directory that holds at least one file. An empty
  directory is refused because the content hash does not cover it.
- `commands` *(built)* and `checks` *(the field is built; `wb check` does not run it yet)*: the exact shapes,
  limits and refusals are in `module-boundary.md`, "Declaration schema". The verifier also requires a
  command's helper to be a regular file of the module. In short, each names a helper that is an item of `ships` (or a file below one),
  a Python helper declares the kit API number it needs in `kit`, and an unknown field is refused as
  everywhere else.
- `commands[].describes` *(built by plan `2026-10-25-safe-git-describe`; the verifier is its increment A)*: an optional list of at most 16 distinct strings, each `^[a-z][a-z0-9-]*$` and at most 32
  characters, naming the actions the command's `describe` argument answers. A non-empty list is refused unless `describe` is among
  the command's `arguments`, and `describe` may not be in `owner`. The form, the refusals, the engine's admission
  rule and the alternatives are in `module-boundary.md`, "Declaration schema". It is additive and covered by the
  declaration hash as written, so it needs no contract version change.
- `commands[].levels` and `commands[].preview` *(built by plan `2026-10-27-levels-for-the-review-workflow`, Increment C; decision
  `2026-10-27-owner-run-arguments-take-a-level`)*: both optional. `levels` is an object that maps an argument listed in `owner` to a
  non-empty list of different levels from `ask` and `none`, the levels that argument offers beyond `block` (`command-permissions.md`,
  "Which levels a key offers"). `delegated`, `block`, any other level, a key that is not an `owner` argument and an empty list are
  refused. `preview` names one of the command's `arguments` that is neither in `owner` nor `describe`; it is required exactly when some
  argument offers `ask`, and the argument it names is the read-only preview whose last line is `digest: <32 lowercase hex>`. Both are
  covered by the declaration hash as written, so a declaration without them hashes as before. A workbench that predates them refuses a
  package that has them, because it refuses an unknown field.

- `approval` *(built)*: an object with exactly the fields `command` (the key of one of this module's `commands`)
  and `argument` (one of that command's `arguments`), and refused on any module type but `process`. It names the
  pinned command the installer runs to learn a plan's hashed region (`trust-and-approval.md`, "Plan approval
  records"). An unknown field, a wrong type, a command the module does not declare or an argument the command
  does not list is refused, naming the module and the field.
- `approval.active` *(built by plan `2026-10-22-checkpoint-settings-and-caps`)*: an optional third field, one of the same command's `arguments`
  and not the same as `argument`. It names the argument that lists the plans under way, for the edit gate
  (`trust-and-approval.md`, "Checkpoint and cap settings, and the edit gate"). A module without it has no
  gate, no hook is rendered for its project, and `wb gate` allows every edit there.
- `approval.delegable` *(built by plan `2026-10-23-delegated-approval`, increment C)*: an optional field, one of the same
  command's `arguments`, different from `argument` and `active`. It names the argument that tells the installer whether
  a plan may be approved by a delegate (`trust-and-approval.md`, "Delegated plan approval records"). A module without it
  has no plan that is delegable.
- `convergence` *(built by plan `2026-10-23-delegated-approval`, increment B)*: an optional object on a module whose `provides` lists `peer-review`, with
  exactly the fields `command` (the key of one of its `commands`) and `argument` (one of that command's `arguments`). It
  names the argument that reports whether the last review of a plan converged. It is refused on a module that does not
  provide `peer-review`, with a command or argument the module does not declare, an unknown field or a wrong type,
  naming the module and the field. A provider without it gives findings only.
- `checkpoints` *(built)*: a list of at most 16 names, each lowercase kebab-case of at most 64 characters (the
  rule the personal settings already apply to a checkpoint name), none repeated. A process module only.
- `caps` *(built)*: a list of at most 16 objects with exactly the fields `name` (the same rule, none repeated),
  `default` and `ceiling`, both JSON integers, with `1 <= default <= ceiling <= 100`. A process module only.
- The three are optional, are part of the declaration and so of the declaration hash as written, and are
  refused with a wrong type, an unknown field, a repeated name or an out-of-range number, naming the module and
  the field. This contract has no version number of its own; the fields are additive, and a workbench that
  predates them refuses a module that declares them as an unknown field, so no bump is needed.

**Module files.** Every file is `module.json`, a file below `harness/`, `templates/`,
`files/`, `tests/` or `tools/` (exact case; a file of that name at the module root does not count), a
`fills` source, or an item of `ships` or a file below one. Empty directories are
ignored. A symbolic link, device, socket or FIFO anywhere in the module is refused. A
module with a `harness/` directory holds `harness/neutral/` or a `harness/<name>/`
directory and no file directly under `harness/`. `harness/<name>/manifest.json` may be
`{"exclude": [{"item": "<kind>/<name>", "reason": "<text>"}]}` with a printable
one-line reason of 1 to 200 characters. An item is `<kind>/<name>` read from the path
`<kind>/<name>` or `<kind>/<name>.md` below the harness directory; this reading is
provisional until the harness module specification fixes it.

**Hashes.** Both are SHA-256, as lowercase hex. The *declaration hash* is taken over the
declaration as written (defaults are not added), serialized as JSON with object keys
sorted at every level, separators `,` and `:`, non-ASCII characters left as themselves
and the result encoded as UTF-8. In a string only the quote, the backslash and the
control characters are escaped (`\n`, `\r`, `\t`, `\b`, `\f`, otherwise lowercase
`\u00xx`); `/` is not. Integers are plain decimal. Keys sort by code point, and no
Unicode normalization is applied. The *tree hash* is taken over one record per regular
file, `<hex SHA-256 of the content> <x or -> <path>` and a newline, where `x` means the
owner execute bit is set, with records sorted by the UTF-8 bytes of the path.
Directories do not contribute, so a tree of only empty directories hashes like an
empty one. Known-answer tests in `tests/` fix both.

**Set checks.** They run on a selection of modules, not on every module of a package.
A selected module is named `<module>`, or `<package>/<module>` where two packages
share a name. Pin names are one namespace: a command is pinned under its name and a
check under the last segment of its helper path, and a name given twice among the selected modules is
refused, naming both. The verifier enforces this for command names alone (rule `command-name`) and for any
name that a check uses, compared with case and Unicode variants folded (rule `pin-name`); inside one module
the same collision is refused as a `checks` error. A module is never its own provider. A `requires` entry for a `slot:` capability is hard
unless marked `soft`, like any other; only a slot fill is always soft. A slot has one
owner among the selected modules. A hard requirement with no provider
among the selected modules names the capability and the unselected modules that could
supply it. The result is all or nothing: if any package, module or set check fails the
result is a refusal and carries no hashes and no order.

## Deferred

- **Dotted sub-names** (`permissions.deny-read`): no module needs them yet.
- **Overloaded terms** (design-notes review item 12): the schema was written and no clash
  between terms was found in the code, so the item stays open only for the harness and
  trust specifications, which the verifier does not exercise.
- **Item naming** for harness modules: provisional, as stated under "Module files".
- **Added hard stops.** `trust-and-approval.md` lets a module add hard stops, but the module
  declaration has no field to declare one, so the verifier accepts none and no module supplies any.
  The code that combines stops accepts additions and refuses any removal. The owner decides the field
  and its format, or defers it.

## Acceptance criteria

- A package declaration with an unsupported `contract` version, or a reserved or
  malformed name, is refused with a message naming the problem.
- A project with two harness modules, or two process modules, is refused.
- A hard requirement with no provider stops the install; a soft requirement with no
  provider warns and installs.
- A requirement for a harness capability that the attached harness lacks warns and
  skips the affected items.
- A module whose `blocks` names a capability another selected module provides stops
  the install before any file is written, whichever was selected first.
- A module that provides and blocks the same capability is accepted alone and
  refused alongside a second provider.
- A module with a file its declaration does not account for, a declared path it
  does not contain, or a symbolic link, is refused.
- A module declaring a write outside its namespace that is not in `writes`, or a
  `writes` path that escapes the project, crosses a symbolic link, or names `.git`,
  is refused.
- A third-party package that provides an unprefixed core name, or a non-harness
  module that provides a harness capability, is refused.
- The declaration hash is identical for two declarations that differ only in field
  order or whitespace, and different for any change in meaning.
- When any module fails verification, no module's files are written.
- A module with a `tests/` or `tools/` directory verifies, the directory is counted in
  the tree hash, and a copy of the module in a project does not contain it. A `ships` item or a `fills`
  source at or below either is refused. A module that
  already shipped such a path is refused on its next verification, because those paths were never
  installed as maintainer files. An executable file there changes the tree hash but is not listed among
  the approval's executables, since nothing in it is installed.
- A `commands` entry with an unknown field, a helper that is not in
  `ships`, or a missing or misplaced `kit` is refused, naming the module and the field. The same holds for a `checks` entry
  (it has no `runtime` and no `arguments`), and for a pin name already used by another entry.
- A `commands` entry whose `describes` has an entry that is not a string, a duplicate or a
  malformed action, that is non-empty while `describe` is not in `arguments`, or that lists `describe` in `owner`, is refused, naming the
  module and the field.
- An `approval` field on a module that is not a `process` module, or naming a command or an
  argument the module does not declare, is refused, naming the module and the field.
- *(Built by plan `2026-10-22-checkpoint-settings-and-caps`.)* A process module's `checkpoints`, `caps` and `approval.active` verify; a repeated
  or malformed name, a default outside 1 to the ceiling, a ceiling over 100, more than 16 entries, an `active`
  argument the command does not list or equal to `argument`, and any of the three fields on another module type
  are refused; the declaration hash changes when any of them changes.

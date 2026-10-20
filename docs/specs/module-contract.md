# Module and package contract

Status: Current. Approved by the owner on 2026-10-19; implementation has not started. Field names are
proposals and are marked as such; the rules they carry are the substance of this
specification.

Terms are defined in `terms.md`.

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
  ships, and it never evaluates its declaration as code. Declarations are data. The
  launcher and the delegation helper are components of the workbench itself, not
  module items; the installer installs them, and they run a module's helper only when
  invoked at use time, never at install.
- The installer treats every package the same way. A first-party package differs
  only in where it comes from and in carrying pre-generated approvals.
- All writes stay inside the project, and a module's own writes stay inside its
  own namespace (see "Writes").

## Package declaration

A package has one declaration file at its root, `package.json`. Field names are
proposals.

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
Field names are proposals.

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
  ordered so that a module follows the modules it requires. A cycle in `requires`
  is an error. The harness module is verified and approved first, but the per-clone
  harness files it describes are written last, by attach, after the committed content
  (see `repository-boundary.md`).

## Capabilities

A capability is a case-sensitive string with no spaces. All capabilities share one
namespace.

- **Core names.** Unprefixed names are reserved for the core contract. The harness
  capabilities are `instructions`, `skills`, `agents`, `commands`, `hooks` and
  `permissions`. Other core names are defined by the specifications that need them
  (for example `plans`, `specs`, `roadmaps`, `decisions`, `references`,
  `peer-review`, `discovery`). This specification names only the six harness
  capabilities; the full list of core names is the union of the capabilities that
  each specification defines.
- **Harness capabilities** may be provided only by a module of type `harness`.
  Other core names may be provided by any approved module.
- **Third-party names** are prefixed with their package, `<package>:<name>`.
  A package may not provide an unprefixed name unless it is the first-party package.
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

## Verification before anything is written

The installer verifies a module before it writes any of the module's files:

1. The declaration parses, has valid field values, a valid type, and valid names.
2. The module's files match its declaration: every `fills` source and every item in
   `ships` exists, every `writes` entry has its source under `files/`, and no file
   exists in the module that its declaration does not account for. A file is
   accounted for when it is `module.json`, is under a reserved directory (`harness/`,
   `templates/` or `files/`), or is named by `fills` or `ships`. A module that
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
sources copied to the paths in `writes`, at the same relative path). Where a module
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

## Deferred

- **Field names** in `package.json` and `module.json` remain proposals until the
  schema is written by the `installer-core-verifier` candidate.
- **Dotted sub-names** (`permissions.deny-read`): no module needs them yet.
- **Overloaded terms** (design-notes review item 12): to be checked as the real
  schema is written.

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

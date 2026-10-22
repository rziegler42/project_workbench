# The installer reads a harness's paths from that harness module's layout

Status: Proposed
Date: 2026-10-21

## Context

The installer named the first harness's directories and its settings file in a table (`HARNESSES` in
`check.py`) and a literal allowlist (`SETTINGS_PATHS` in `layout.py`), and its tests attached the real
`claude` module. The decision `2026-10-21-module-code-lives-in-modules` puts module-specific code and
names in the module, and the module-boundary specification lists these two tables among what moves.

## Decision

- `wb check` takes the roots, the generated directories and the tolerated paths of a harness from the
  `layout` of that harness's module (`workbench/harnesses.py`, `layout.facts`). It knows only the harness
  modules of a first-party package in the running workbench's distribution. A harness recorded in a
  project's manifest that is not known gets one warning and no scan; a harness with no module (opencode,
  Codex) is not known.
- A layout may declare `tolerated`: at most 16 literal paths, each inside a directory the layout writes into,
  that the harness or the owner may keep there. `wb check` does not warn about them.
- The settings path is checked by a rule that names no harness: a safe, unreserved path of exactly two
  segments, a dot-directory and then a name ending `.json`, covered by the layout's `exclude`.
- The tool-name guards (`RULE_NAMES`, `TOOL_NAMES`, `INERT_TEMPLATE_NAMES`) stay in `layout.py` until
  the second harness module (`opencode-harness`).
- A boundary test derives its words from the `module.json` files under `packages/` and fails if the installer
  or its tests name a first-party module, helper, command, harness or harness path. The installer's tests
  attach a made-up harness module; the real `claude` module is tested in its own directory.

## Alternatives considered

- **Keep the settings literal** beside the tool-name guards. It would keep the property that the `deny` rules
  land in a file Claude reads, and put the literal on the boundary test's exception list. Rejected by the owner
  with Choice 3 of the plan.
- **Recognise third-party harnesses in `wb check`.** Rejected for now: the layout of a module that is not
  first-party has no shipped record to match, so it would be a new trust input.
- **Move the tool-name guards into the layout now.** Rejected: the layout would then say which of its own
  names are acceptable, and a generic form needs a second harness to design against.

## Consequences

- Nothing but the owner's approval of a module stops its layout from declaring a settings file the tool never
  reads, and so leaving its `deny` list inert. Exclusive creation and `exclude` coverage do not address it.
- A first-party harness module changed since release is not known to `check`, and `check` warns until the
  owner runs `release-approvals`.
- A name built at run time, split across lines or shorter than three characters escapes the boundary test.
- A root file and the file it imports must be plain Markdown names, so a layout cannot make attach write
  another tool's script or configuration file in the project root.
- The settings rule is a shape and not an allowlist: a layout can place its settings file in a directory
  another tool reads (`.github`, `.vscode`) and exclude that directory. Deferred to the plan that recognises
  a third-party harness.
- A package is hashed again after its layout is read. A change reverted between the two hashes is not caught;
  it needs write access to the distribution.

## Verification

The plan `2026-10-21-module-harness-paths`: increments A to D (facts, settings rule, known harnesses), E to
G (synthetic harness), I (boundary test, with its mutation results) and J (the run with `packages/` emptied
and the security pass).

## Related files and decisions

- `docs/specs/module-boundary.md`, `docs/specs/harness-modules.md`, `docs/specs/module-contract.md`
- `workbench/harnesses.py`, `workbench/layout.py`, `workbench/check.py`, `tests/test_boundary.py`
- [2026-10-21-module-code-lives-in-modules](2026-10-21-module-code-lives-in-modules.md)
- [2026-10-20-first-party-by-location-and-shipped-record](2026-10-20-first-party-by-location-and-shipped-record.md)

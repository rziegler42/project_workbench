# A skill name has one owner module; a practice that spans modules is split into skills

Status: Accepted (2026-10-24, by the owner; the rule is enforced by `tests/test_skill_names.py` and four ports follow it)
Date: 2026-10-23

## Context

The superpowers skills the owner uses are being ported into modules (plan `2026-10-23-port-superpowers`). A practice such as
test-first work, debugging or verification is general (every process shares it) and also has domain forms (a testbench for
HDL, a counterexample for a formal proof, a check of a CAD model). So one superpowers skill can belong in more than one
module.

A skill name is one path in a harness (`.claude/skills/<name>/SKILL.md`). The installer builds the neutral tree as the union
of every installed module's `harness/neutral/` and refuses a path two modules both supply
(`workbench/harnessstage.py`, `inputs`: "<a> and <b> both supply harness/neutral/..."). So two modules cannot ship a skill
of the same name, and a skill that is shipped by one module and wanted by another needs a way for the second to depend on
it. A skill and a command also share one name (`/name`), and an agent name is one file.

A capability is a property of a module, not of one skill (`module-contract.md`, "Capabilities"). A module `requires` a
capability by name; unprefixed names are core names, and a new one is added only by changing a specification.

## Decision

1. **A skill, agent or command name has exactly one owner module.** No two first-party packages ship the same name. A test
   reads every package's neutral tree and fails on a repeated name.
2. **A practice that spans modules is split into separate skills with separate names.** The general part goes to the module
   every process shares (`code-work` for the practices of the first ports). A domain form is a different skill, with a
   different name, in the domain's module. It does not copy the general skill's text; it says it extends the general skill
   and names it, and says that in its own domain its rules take precedence.
3. **A module whose skill extends another module's skill declares `requires`** on a capability that the owner module
   provides, as hard, so that an installation with one and not the other is refused. The capability is an existing core name
   where one fits (`plans` for `code-work`), and otherwise a new core name that the first such domain module's plan adds to
   a specification. Until a domain module exists, nothing is added.
4. **The owner of each ported skill is recorded** in `docs/specs/superpowers-ports.md`, and a test checks that every row
   marked built names an item its owner ships.

## Alternatives considered

- **The same skill name from two modules.** Refused by the installer today, and making it work (a merge, a precedence, a
  per-module path) is a change to the installer's mechanism and to what a name means. Rejected.
- **A copy of the general skill in every module, with distinct names and no link.** It installs, but the copies drift and an
  agent can load the wrong one. Rejected.
- **One module for all practices, required by every domain module.** It gives one owner, but forces a domain with no
  software practice (a CAD project) to take software wording, and puts the domain forms in a module that does not know the
  domain. Rejected. A module of its own for a practice every process shares is not ruled out if the inventory finds one;
  none has yet been found.
- **A capability per skill.** It would let a module require one skill exactly, but capabilities are module-level in the
  contract and every skill would add a core name. Rejected for now; revisited if a domain module needs finer dependence.

## Consequences

- A domain module can add its own form of a practice without touching `code-work`, and installs only where its general
  skill is installed.
- A name cannot be reused for a different purpose by another module; a clash is caught by the test before it reaches an
  install.
- The general skill's text must stay free of domain terms, so a domain form can extend it without contradicting it.
- No change to the installer or to the contract is made by this record. If the first domain module needs a new core name,
  that module's plan changes the specification.

## Verification

- `tests/test_skill_names.py`: no repeated name across the packages; the installer's refusal of one path from two modules,
  called directly; the inventory's built rows name items their owners ship.
- The inventory in `docs/specs/superpowers-ports.md` states each owner.

## Related files and decisions

- Plan `2026-10-23-port-superpowers`; spec `docs/specs/superpowers-ports.md`; `harness-modules.md` ("Neutral items");
  `module-contract.md` ("Capabilities", "Requirements").
- `2026-10-19-groundwork-shared-layer` (a shared layer owned by one module, used by others).

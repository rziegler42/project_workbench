# The installer pins the helpers a confirmed plan declares

Status: Accepted by the owner on 2026-10-22
Date: 2026-10-22

## Context

A module declares helpers as `commands` and `checks`. The launcher runs a helper only while its bytes match
a pin in the guarded store (`docs/specs/trust-and-approval.md`, "Pinned helpers"), and until now only the
owner's `pin` command made a pin, one helper at a time. When the owner types the digest of an install, add
or upgrade, the owner has confirmed exactly those bytes, so a separate `pin` adds friction and no
information, and it is one command per helper after every release and every accepted edit. A pin made at that step must still defeat a pull: a pulled commit can edit a helper, a
`module.json` and the manifest's hash of it together, but it cannot write the guarded store.

## Decision

- Install, add and upgrade pin every helper a `commands` or `checks` entry of a confirmed module declares.
  The pin follows the bytes of the confirmed plan, never the bytes found on disk later. The preview and
  the digest list each pin created, updated or replaced, and a replacement shows the pin it replaces. A
  helper the plan does not write keeps its pin.
- An installer-made pin records the hash of the `module.json` that was confirmed. `wb run` and `wb check`
  refuse when the manifest holds another declaration, so a pull that rewrites a declaration and its hash
  cannot widen the `arguments` of a pinned command. Only an upgrade with the digest typed, or an owner-run
  `pin`, clears the refusal.
- `acknowledge` moves a pin to the bytes it accepts only when the pin records a declaration and holds the
  bytes last acknowledged. A pin the owner typed records none, and is never moved.
- The rule is the same for first-party and other packages; it reads no module by name. No accepted
  decision said the owner pins a helper, so none is superseded.

## Alternatives considered

- **Print the `pin` lines and let the owner run them.** Nothing new in the installer, but an extra step
  after every release and acknowledged edit, with the same information the digest already carried.
- **A pin per helper by naming convention (a `helper/<module>` file pinned by its name).** Rejected: a new
  convention in place of a declaration, and not usable for checks.
- **Pin without recording the declaration.** Rejected after the security pass: a pull could widen a
  command's `arguments`.
- **Let `acknowledge` move every pin whose path it lists.** Rejected: acknowledging an edit would grant
  permission to run a helper the owner pinned deliberately for something else.

## Consequences

- An owner who types `pin` for a helper approves the whole module's handling of arguments, as before; the
  documentation says so (`docs/specs/trust-and-approval.md`, residual risk).
- A stop between the baselines write and the pins write leaves old pins; `wb recover` clears it and says
  to run `pin` for each replaced helper.
- Pins made before declarations were recorded carry none and are updated at the next upgrade.

## Verification

- `tests/test_pinplan.py`, `test_install_pins.py`, `test_upgrade_pins.py`, `test_acknowledge_pins.py`,
  `test_recover_pins.py`, `test_commands.py`, `test_checks.py`, `test_pins.py`.
- `packages/workbench/code-work/tests/test_codework_module.py`: the install, the refusal after an edit and
  the acknowledgement, with no typed pin.
- `packages/workbench/safe-git/tests/test_safegit_module.py`: the pin made by install for `safe-git`, an
  edited helper refused, and a pin that lets no other command run.
- Security pass, two rounds, in plan `2026-10-21-code-work-plans`, increment G.
- Accepted on 2026-10-22 on this evidence: two first-party modules now run through it, and the full suite
  runs 2658 tests in 5 roots, OK.

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/specs/module-boundary.md`, `docs/specs/installer-interface.md`
- `workbench/pinplan.py`, `workbench/pins.py`, `workbench/acknowledge.py`
- [2026-10-19-uniform-package-trust](2026-10-19-uniform-package-trust.md)
- [2026-10-20-acknowledge-before-upgrade](2026-10-20-acknowledge-before-upgrade.md)
- [2026-10-21-module-code-lives-in-modules](2026-10-21-module-code-lives-in-modules.md)

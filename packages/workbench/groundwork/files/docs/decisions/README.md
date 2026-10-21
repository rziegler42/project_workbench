# Decisions

A decision record states why a choice was made and what was rejected. It is durable
history, and it outranks the current code.

## Naming

One record per decision, named `YYYY-MM-DD-<topic>.md` with the creation date and a
lowercase kebab-case topic, for example `2026-01-15-use-spi-flash.md`. A record is never
renamed. Its file name without the extension is its ID.

## Status

The values are `Proposed`, `Accepted`, `Rejected` and `Superseded`. A superseded record
names its successor.

Accepting a decision is the owner's act. An agent writes a record as `Proposed` and asks.
Once accepted, a record is not rewritten: a correction or a change of mind is a new record
that supersedes it.

## Contents

Context, the decision, the alternatives considered and rejected, the consequences, and
evidence. Evidence carries a provenance line: what was run, with which tool versions, at
which commit, and the conclusion.

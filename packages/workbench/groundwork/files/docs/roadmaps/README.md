# Roadmaps

A roadmap lists candidates, each sized to be one unit of work, with no required order. It
expresses direction. It does not authorize work and does not change work in progress.

## Naming

A roadmap is named by its scope in lowercase kebab-case, with no number or date, for
example `first-release.md`. There may be several.

## Contents

A roadmap states its status, the date it was updated, its purpose, the current state, its
candidates, deferred work, and the decisions that bear on it.

A candidate has an ID, a title, the outcome wanted, dependency hints, a boundary and the
trigger for starting it. The ID is a short topic slug in lowercase kebab-case, fixed when
the candidate is created and unique within the roadmap. It is never reused, renumbered or
changed when the title is reworded. Refer to a candidate as `<roadmap>#<id>`, for example
`first-release#pick-a-board`. An abandoned candidate is marked dropped with a reason and
stays in the file.

Completion is never written into a roadmap. The file changes only when direction changes,
and changing direction needs the owner.

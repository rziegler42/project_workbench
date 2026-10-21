# The reference index is canonical JSON, and the index and README are not references

Status: Accepted
Date: 2026-10-21

## Context

The groundwork specification requires an index of the reference files in `docs/references/`
(tracked) and `.workbench/local/refs/` (untracked), and a check that compares the tracked index
with what git tracks. It left the file format open. The index is read by a check from content that
anyone who can commit may write, so it must be read strictly and bounded, and the check must be able
to say exactly what is wrong with it.

## Decision

- The tracked index is `docs/references/index.json` and the untracked one is
  `.workbench/local/refs/index.json`. Each is UTF-8 JSON, `{"entries": [...], "format": 1}`.
- Each entry has exactly `file`, `title`, `url`, `license`, `retrieved`, `version`, `sha256` and
  `notes`. `file` is a safe relative path from the project root under the index's own area.
  `retrieved` is a real `YYYY-MM-DD` date, `sha256` is 64 lowercase hex digits, `url` is an http
  or https address, and `license`, `version` and `notes` may be empty. Text is printable and
  bounded per field.
- The file is canonical: entries sorted by `file` (byte order), one entry per line, ASCII with
  escapes, and the reader accepts only the serializer's own output. Duplicate keys, NaN and
  fractions, unknown or missing fields, a repeated or case-colliding file, and non-printable text
  are refused. A refusal names the entry and the field and never repeats the value.
- The bounds are 1 MiB and 5,000 entries. The smallest entry is about 230 bytes, so the byte bound
  is reached first; both are kept.
- `index.json` and the area's `README.md` are metadata. Neither needs an entry, and an entry that
  names either is a problem.

## Alternatives considered

- **A Markdown table.** Easier to read and edit by hand. Rejected: a table has no exact grammar
  for a title or a note that contains a pipe or a newline, so the check could not tell a mistake
  from a value, and the hash would be one more cell to get wrong.
- **One file per reference** (a sidecar next to each file). Rejected: it doubles the files in the
  area, and a check for "a tracked file the index lacks" would have to find the sidecars first.
- **Free-form JSON that any writer may lay out.** Rejected: two writers would produce different
  bytes for the same content and conflict on merge; sorted, one-per-line entries merge cleanly.

## Consequences

- A hand edit must keep the canonical layout. `groundwork-research`, when it exists, writes the
  index with the same serializer. Until then a person edits it, and `wb check` says what to fix.
- A reference whose note needs a line break cannot hold one; the note is one line.
- The format is versioned by `format`. A change to it is a new decision.

## Verification

Tests of the plan `2026-10-21-groundwork-module` (increment E), `tests/test_refindex.py`: a
well-formed index round-trips, each hostile case in the plan's Review focus is refused with the
field named, the bounds hold, and a refusal does not repeat a hostile value.

## Related files and decisions

- `docs/specs/groundwork.md` ("Indexes")
- `workbench/refindex.py`
- [2026-10-19-tracked-pointer-rule](2026-10-19-tracked-pointer-rule.md)
- [2026-10-19-groundwork-shared-layer](2026-10-19-groundwork-shared-layer.md)

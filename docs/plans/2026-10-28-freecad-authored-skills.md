# The freecad module: authored skills

Status: In Progress
Created: 2026-10-28
Candidate: workbench-v1#cad-modules
Specs: module-contract

## Goal

Add three skills to the first-party module `freecad`: `freecad-draft`, `freecad-surface` and `freecad-techdraw`. The owner's
source text barely covers these workbenches, so the skills are authored here, and each claim a skill states as fact is
written only after it has been run in FreeCAD 1.1.4. This plan completes the candidate `cad-modules` together with the first
plan, `2026-10-28-freecad-module`.

When this plan is done:

- `packages/workbench/freecad/` ships twenty skills: the seventeen of the first plan and these three;
- each new skill has a `SKILL.md` and a `reference.md`, begins with its scope, and says which of its claims were run and
  which were only read;
- the Result lists, per skill, the commands run in FreeCAD, their output, and what could not be run.

## Scope

- `freecad-draft`: the Draft workbench's 2D objects (lines, circles, rectangles, polygons), move, rotate, scale and offset,
  arrays, and the snake_case API that replaced the camelCase names.
- `freecad-surface`: the Surface workbench's objects (filling, sections, curve networks, extending a surface) and how to
  check the result.
- `freecad-techdraw`: drawing pages, projected views, dimensions and annotations, and exporting a drawing.
- The module's tests and the shipped approvals.

## Non-goals

- Anything the first plan does. The module must exist with its seventeen skills first.
- CAM, BIM, OpenSCAD and Material skills; installing FreeCAD or an addon; a pinned helper, a command or a script.
- The owner's conventions (dropped on 2026-10-28), the wiki's text (it refuses automated access) and any copying of
  FreeCAD's source or documentation.
- Editing the roadmap, the inventory or the owner's global configuration.

## Assumptions and constraints

- The first plan, `2026-10-28-freecad-module`, has status `Completed` before increment A starts. If it is not, stop and tell
  the owner.
- The module's layout, text checks, limits and method (M1 to M6) are those of the first plan. Its tests are extended: the
  module ships exactly twenty skills, and the descriptions stay distinct.
- The only source on the owner's side is the Draft snippet and the deprecated-API rows in the source `SKILL.md`
  (sha-256 `8d4a357642fefcf6e9103d87b61cd4ef5d0cd70762e070dc7682d783abac61d8` on 2026-10-28). Nothing covers Surface or
  TechDraw, and the Draft snippet is short. The file is owner-local with no source URL, so it is identified by name, read
  date and hash, as in the first plan.
- FreeCAD 1.1.4 (revision 20260928) is extracted on this machine and runs headless with `freecadcmd`; each run is at the
  owner's word, from a scratch directory. Some TechDraw operations may need a display and cannot run headless; those are
  discovered by trying, and marked not run.
- FreeCAD's public source tree may be read for names and signatures. A file consulted is cited in the Result by URL,
  retrieval date and content hash; it is read by fetching it, which is a network read I make only with the owner's word.
  If it cannot be fetched, the skill rests on runs alone.
- Each increment makes the shipped approvals stale and the gates refuse until the owner runs `wb release-approvals`; the
  mitigation is the first plan's (stage in a scratch directory, copy in with one command).

### Choices (made by me; the owner may change any)

1. **A claim is kept only if it was run.** For each snippet the skill states as fact, I run it in 1.1.4 and record the
   command and output; a failing snippet is corrected or dropped. A statement that cannot be run (a display is needed, an
   external program is absent) is marked "read, not run" in the skill and listed as such in the Result.
2. **The skills are shorter than the others.** They cover what a script needs and what I could verify, not the whole
   workbench. A skill that would be mostly unverified is cut down to what was run.
3. **Three increments plus one.** One skill each, because each needs its own runs; then approvals and the record.
4. **The owner may supply material.** If the owner gives scripts or notes for any of the three, the skill is based on them
   first, and the Result says so.

## Completion criteria

1. The module ships exactly twenty skills, the new three each with `SKILL.md` and `reference.md`; the verifier accepts the
   module; `tests/test_skill_names.py` passes.
2. The same text checks as the first plan pass for the new skills: scope first, a missing-tool rule, no vendor or
   personal-path word, no URL, no install instruction, distinct descriptions of at most 300 characters.
3. Every snippet a new skill states as fact has a recorded run in FreeCAD 1.1.4; every other statement is marked read.
4. The shipped approvals are released by the owner; the full suite is green in all roots with no stale-approval skip; the
   document checks and `git diff --check` print nothing.
5. The Result names the commands run, the version, and what was not run.
6. The roadmap entry for `cad-modules` has been revised by the owner, through the owner's roadmap process, to match what the
   two plans built (no tool-neutral `cad` module; the mesh script as a bundled file, not a pinned helper; twenty skills
   in one `freecad` module). A note in the Result is not a substitute. Until the entry is revised, the plan stays `In
   Progress` and is not marked `Completed`.

## Increments

### Increment A — The Draft skill

**Outcome:** the module also ships `freecad-draft`.
**Dependencies:** the first plan, completed.
**Affected areas:** `packages/workbench/freecad/harness/neutral/skills/freecad-draft/`, the module's tests.
**Steps:**
1. Check the hashes of the source it reads (Assumptions); stop and tell the owner on a difference.
2. Test first: extend the module's tests with the name and the text checks; see them fail for the missing skill.
3. Write the skill and its reference in a scratch directory. Run each snippet in FreeCAD 1.1.4 (2D shapes, move, rotate,
   scale, offset, arrays, the snake_case names and the camelCase aliases) and keep only what ran. Copy the files in with
   one command and ask the owner to run `wb release-approvals`.
4. Run the module's tests, the package tests (`tests.test_package tests.test_skill_names tests.test_boundary`),
   `wb run code-work check` and `git diff --check`.
5. Record the increment in the Result and stop for the owner.
6. On the owner's word, make the one local commit with `wb run safe-git commit`, the exact paths and the trailer below.
**Verification:** the module's tests; the package tests; the recorded FreeCAD runs.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-authored-skills#A`.

### Increment B — The Surface skill

**Outcome:** the module also ships `freecad-surface`.
**Dependencies:** A.
**Affected areas:** `packages/workbench/freecad/harness/neutral/skills/freecad-surface/`, the module's tests.
**Steps:** the same six steps as increment A, for the Surface workbench: which objects exist in 1.1.4 (read from the
installed FreeCAD and its source tree), how a script creates a filling, a sections surface and a curve network, how to
extend a surface, and how to check validity and area of the result. Objects that fail headless are marked not run.
**Verification:** as A.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-authored-skills#B`.

### Increment C — The TechDraw skill

**Outcome:** the module also ships `freecad-techdraw`.
**Dependencies:** B.
**Affected areas:** `packages/workbench/freecad/harness/neutral/skills/freecad-techdraw/`, the module's tests.
**Steps:** the same six steps as increment A, for TechDraw: create a page from a template, add a projected view of a
part, add dimensions and annotations, and export the page. Which of these runs headless in 1.1.4 is found by trying; those
that need a display are marked not run. The `Drawing` to `TechDraw` change is a cross-reference to `freecad-python`.
**Verification:** as A.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-authored-skills#C`.

### Increment D — Approvals and record

**Outcome:** the shipped approvals match the final package tree and the plan records what was done.
**Dependencies:** A to C.
**Affected areas:** `workbench/shipped_approvals/` (by `release-approvals`), this plan's Result.
**Steps:**
1. The owner runs `wb release-approvals`, or asks me to run it. Remove stale records only after a preview and the owner's
   "remove them".
2. Run the full suite, `wb run code-work check`, `wb check` and `git diff --check`.
3. Ask the owner to revise the roadmap entry (I may draft it with the roadmap skill, as `Proposed` text for the owner). Do
   not edit the roadmap without the owner's word.
4. Fill the Result and set the plan `Completed` only when criterion 6 is met.
5. On the owner's word, make the one local commit with `wb run safe-git commit`, the exact paths and the trailer below.
**Verification:** `python3 -B -W error tests/run_all.py` green with no stale-approval skip; the document checks print nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-authored-skills#D`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` green in all roots; `wb check` and `wb run code-work check` report no problems;
  `git diff --check` prints nothing.
- `python3 -m workbench verify packages/workbench --select freecad` accepts the module with twenty skills.

## Risks and sensitive actions

- **Authored, not ported.** These skills come from my reading and from runs, not from the owner's practice. A run shows
  that a snippet works on 1.1.4 in a headless session, not that it is the best way. The skills say so.
- **Running FreeCAD** is the owner's decision each time; the runs use files I create in a scratch directory.
- **Network reads of FreeCAD's source tree** happen only with the owner's word and are cited by URL, date and hash.
- **Display-dependent features** (TechDraw rendering in particular) may not run headless and would stay unverified.
- **Size and context:** three more descriptions of up to 300 characters in every session.
- Gate lockout after each increment until the owner runs `wb release-approvals`.
- Nothing is committed or pushed without the owner's explicit word, and no dependency is installed.

## Review record

Independent review through the review engine (bridge `ask-codex`, model `gpt-5.6-terra`, effort medium), asked for by the
owner on 2026-10-28, two rounds of a bound of three. The reviewer's findings are untrusted input; each was judged on the
evidence. A review is not an approval.

- **Round 1** (changes needed, two major).
  - R1-F1, a Result note leaves the roadmap candidate inaccurate: **applied**. The written-acceptance route is removed;
    completion requires the owner to revise the roadmap entry.
  - R1-F2, no step makes the one commit each increment names as evidence: **applied**. Every increment now ends with a
    step that commits on the owner's word with the commit helper and the stated trailer.
- **Round 2** (no meaningful changes, converged).

Remaining disagreement: none.

## Deferred work

- CAM, BIM, OpenSCAD and Material skills.
- Revising the roadmap's `cad-modules` entry, which describes a tool-neutral module and one FreeCAD skill: the owner's call.

## Result

### Increment A

- **Read (2026-10-28):** the sha-256 of the owner's source `SKILL.md` matched the plan (`8d4a3576…`). Its Draft snippet and its
  deprecated-API rows were the only source; plan one has status `Completed`. FreeCAD's source tree was not fetched. The
  skill rests on the runs below and on `inspect.signature` of the installed `Draft` module.
- **Written:** `freecad-draft` (`SKILL.md` and `reference.md`), and its name in the module's tests (18 skills now).
- **Run against FreeCAD 1.1.4 (revision 20260928), headless with `freecadcmd`, at the owner's word, from a scratch directory,
  in memory only:** three probe runs (12, 11 and 7 blocks; one raised, because it read a property `Link` that does not
  exist, and was dropped), then the 19 blocks of the shipped `reference.md` (none raised, every printed value equals the
  comment in the file). Confirmed: the 2D objects and their shape types; `MakeFace`; extrusion to a solid (150.0) and
  `Draft.extrude`; `make_sketch`; `move`, `rotate` and `scale` in place and with `copy=True`, and on a list; `offset` and
  its side rule, the notice for a vector parallel to the first edge, and `AttributeError` before a recompute; the ortho, polar,
  circular and path arrays, `NumberX` changed and the base object's `Length` followed; `use_link=False`; clone and mirror; the
  signatures of 14 functions; that the camelCase names run are the same objects as the snake_case ones, while
  `makeArray` is another function that prints a notice.
- **Found, not in the source:** the source says "camelCase names are legacy aliases", but `makeArray` is a separate function
  with an older argument order; the source's offset note ("must be a recomputed 2D object") is right and the failure is an
  `AttributeError`; `offset` and `move` change the object unless `copy=True`; `offset` takes a vector whose component across
  the first edge picks the side; a circular array's number is its number of rings.
- **Not run, marked read in the skill:** `autoconstraints=True` of `make_sketch`, array properties other than `NumberX`, `Fuse`
  on touching copies, dimensions, text, labels, hatches, layers, working plane proxies, shape strings, `make_shape2dview`,
  `upgrade`, `downgrade` (one call returned a tuple and was not examined) and everything that needs the interface.
- **Verification as run:** test first, 23 tests with 2 failures and 8 errors; then the module tests, 23, OK; package tests,
  29, OK; the full suite, 5864 tests in 13 roots, OK; `wb run code-work check` (61 plans) and `wb check` found no problems;
  `git diff --check` printed nothing.
- **Gate:** the owner ran `wb release-approvals` once for this increment. Two records (`969bbb13…`, `abaaf2b7…`) are reported
  stale; none was removed. Increment D removes them after a preview.
- **Not done:** no independent review (only when the owner asks); no run in the GUI.

### Increment B

- **Read (2026-10-28):** there is no source on the owner's side for Surface. FreeCAD's source tree was not fetched. The
  skill rests on the runs below and on what the installed FreeCAD reports (`supportedTypes()` and each object's
  `PropertiesList` and enumerations).
- **Written:** `freecad-surface` (`SKILL.md` and `reference.md`), and its name in the module's tests (19 skills now).
- **Run against FreeCAD 1.1.4 (revision 20260928), headless with `freecadcmd`, at the owner's word, from a scratch directory,
  in memory only:** four probe runs (1, 9, 12 and 7 blocks; 3 blocks of the second raised on a null shape of a failed
  Filling or Coons and were rewritten to test the null shape instead), then the 10 blocks of the shipped `reference.md` (none
  raised). Two expected values in the file were guesses and were corrected to what printed (three edges gave area 100.0;
  extending by 0.5 and 0.1 gave 160.0 from x -1 to 15). Confirmed: the seven Surface types and their properties; that
  `Surface::CurveOnMesh` is not a document object type; `GeomFillSurface` with `Stretched` and `Curved` on flat and bent
  boundaries, edges from one wire or separate objects, in any order; `Coons` failing on straight edges and on an arc with
  two lines ("Curves are disjoint") and working on four arcs; `Filling` on a bent boundary, a circle failing as one edge and
  working as two half-arcs (area 78.54), a point constraint, `BoundaryOrder` `[1,1,1,1]` making the object `Invalid`, and
  `Tolerance3d` and `MaximumDegree`; `Sections` in order, reversed and out of order (area 158.77, valid); `Extend` with the
  symmetric flags on and off, on a plane and on a filled surface; `Sewing` of touching and separate planes; `Cut` of a face by
  a face, and failing with a solid or a shell; the checks (`isValid`, surface class, area, sampling, `optimalBoundingBox`,
  `distToShape` against the boundary).
- **Found:** the `BoundBox` of a surface overstates its height (ZMax 4.0 against a sampled 2.0); `isValid` does not catch
  sections in the wrong order or a boundary with a side missing; `Extend` values are fractions of the parameter range and the
  symmetric flags default to true.
- **Not run, marked read in the skill:** `FeatureBlendCurve` (its properties were listed, no curve was built), `BoundaryOrder` with
  boundary faces, `Filling` options other than those named, and the Surface commands and everything else that needs the interface.
- **Verification as run:** test first, 23 tests with 2 failures and 8 errors; then the module tests, 23, OK; package tests,
  29, OK; the full suite, 5864 tests in 13 roots, OK; `wb run code-work check` (61 plans) and `wb check` found no problems;
  `git diff --check` printed nothing.
- **Gate:** the owner ran `wb release-approvals` once for this increment. Four records (`969bbb13…`, `a0335de4…`, `abaaf2b7…`,
  `deadd047…`) are reported stale; none was removed. Increment D removes them after a preview.
- **Not done:** no independent review (only when the owner asks); no run in the GUI.

### Increment C

- **Read (2026-10-29):** there is no source on the owner's side for TechDraw. FreeCAD's source tree was not fetched. The
  skill rests on the runs below and on what the installed FreeCAD reports (`supportedTypes()`, each object's
  `PropertiesList` and enumerations, the module's names and its resource folder).
- **Written:** `freecad-techdraw` (`SKILL.md` and `reference.md`), and its name in the module's tests (20 skills now). The
  skill points to `freecad-python` for the `Drawing` to `TechDraw` change.
- **Run against FreeCAD 1.1.4 (revision 20260928), headless with `freecadcmd`, at the owner's word, from a scratch directory,
  in memory or a temporary folder:** two probe runs (3 and 10 blocks, none raised), then the 10 blocks of the shipped
  `reference.md` (none raised; every printed value matched the file). Confirmed: `import TechDraw` works and `import
  TechDrawGui` fails headless ("Cannot load Gui module in console application"); 46 TechDraw object types and the
  properties of the page, template, view, dimension, annotation, section, projection group and detail; the four template
  entries in the resource folder; a page from the A4 landscape template (297 by 210 mm, scale 1.0, first angle); a projected
  view of a box (4 visible edges, 0 hidden, 4 vertices); `TechDraw.project`, `projectEx`, `projectToSVG` and `projectToDXF`
  without a page; distance dimensions by edge (20.0, 20.0, 40.0, 40.0); an annotation; `writeDXFPage` and `writeDXFView`
  (4903 bytes each), `viewPartAsSvg` and `viewPartAsDxf`; saving a document with a page.
- **Found:** a view has no `getBoundingBox` or `getEdgeCount`; computing a page writes a copy of the template into FreeCAD's
  user cache folder, outside the project (the skill does not name the path); dimension edge numbers are the view's own.
- **Not run, marked read in the skill:** everything that needs `TechDrawGui` (interface export, printing), section, projection
  group and detail views, dimension types other than `Distance`, `References3D`, adding a view to the page after setting its
  source, and what each of the four shapes from `TechDraw.project` holds.
- **Verification as run:** test first, 23 tests with 2 failures and 8 errors; then the module tests, 23, OK; package tests,
  29, OK; the full suite, 5864 tests in 13 roots, OK; `wb run code-work check` (61 plans) and `wb check` found no problems;
  `git diff --check` printed nothing.
- **Gate:** the owner ran `wb release-approvals` once for this increment (13 approvals). Six records (`14a79110…`,
  `26acd5f3…`, `969bbb13…`, `a0335de4…`, `abaaf2b7…`, `deadd047…`) are reported stale; none was removed. Increment D removes
  them after a preview.
- **Not done:** no independent review (only when the owner asks); no run in the GUI.

### Increment D

- **Approvals:** the owner's release after Increment C (13 approvals) covers the final package tree; nothing under
  `packages/` changed afterwards. The preview of `wb run safe-git remove --recursive` listed six stale records (`14a79110…`,
  `26acd5f3…`, `969bbb13…`, `a0335de4…`, `abaaf2b7…`, `deadd047…`, one file each; two were tracked, four untracked) and, on the
  owner's "remove them", they were removed. The two records of the current release (`da4c0e05…`, `f5529bae…`) are new and
  are committed with this increment.
- **Verification as run:** the full suite, 5864 tests in 13 roots, OK, with no stale-approval skip; `wb run code-work check`
  (61 plans) and `wb check` found no problems; `git diff --check` printed nothing; `python3 -m workbench verify
  packages/workbench --select freecad --select claude` accepted the module.
- **Roadmap:** criterion 6 is not met. I drafted `Proposed` text for the `cad-modules` entry in chat for the owner; the roadmap
  was not edited. The plan stays `In Progress` until the owner revises the entry.
- **Not done:** no independent review (only when the owner asks); the plan is not `Completed`.

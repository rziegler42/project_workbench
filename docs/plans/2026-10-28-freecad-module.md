# The freecad module

Status: Proposed
Created: 2026-10-28
Candidate: none (first of two plans for `workbench-v1#cad-modules`; the second, `2026-10-28-freecad-authored-skills`, names the candidate, so it completes only when both are done)
Specs: module-contract

## Goal

Build the optional first-party module `freecad`. It holds seventeen neutral skills for scripting FreeCAD 1.1 from Python,
named by workbench or by task. Each is written in the workbench's words after a read of the owner's source text, and the
claims that FreeCAD 1.1.4 can check are checked by running it. One skill bundles the owner's mesh script as a file beside
its `SKILL.md`.

When this plan is done:

- `packages/workbench/freecad/` is a module that the verifier accepts, provides nothing, and ships no helper, command or
  check;
- it ships exactly these seventeen skills (below), each with valid front matter, a `reference.md`, and a description that
  names its own trigger;
- the skills are named by this module only (`tests/test_skill_names.py` passes);
- the Result records, for each skill, what was read, what was changed or dropped, what was added by the author, and what
  was run against FreeCAD 1.1.4 and what was not.

## Scope

The module `freecad`, its entry in `packages/workbench/package.json`, its tests, and these skills. "Source" is the owner's
`freecad-scripts` skill (its `SKILL.md`, ten reference files and one script; hashes under Assumptions).

| Skill | Covers | Built from |
|---|---|---|
| `freecad-python` | the Python environment, headless and GUI, the deprecated-API table, units, the document model, shorthand-to-API terms | `SKILL.md`, `scripting-fundamentals.md` |
| `freecad-part` | Part shapes, wires, faces, booleans, loft and sweep, topology | `geometry-and-shapes.md`, the Part parts of `SKILL.md` |
| `freecad-sketcher` | sketch constraints, sketch health, construction and external geometry | the Sketcher parts of `partdesign-and-parameters.md` and `geometry-and-shapes.md` |
| `freecad-partdesign` | PartDesign features, patterns, multi-body | `partdesign-and-parameters.md` |
| `freecad-parameters` | VarSet, Spreadsheet and expressions as ways to drive dimensions | the VarSet part of `partdesign-and-parameters.md`; the Spreadsheet part is the author's |
| `freecad-mesh` | Mesh and MeshPart: operations, conversion, triage and repair | the mesh parts of `geometry-and-shapes.md` and `mesh-reverse-engineering.md` |
| `freecad-reverse-engineering` | primitive fitting, parametric rebuild, deviation, and the bundled `scripts/mesh_report.py` | `mesh-reverse-engineering.md`, `scripts/mesh_report.py` |
| `freecad-image-to-model` | scale, measurement, build-and-compare against a photo, drawing or screenshot | `images-to-cad.md` |
| `freecad-measure-and-inspection` | Measure and Inspection, shape validity, closed solids, distances, "compare and report numbers" | the distance recipe, the deviation function, the validity checks |
| `freecad-import-export` | STEP, IGES, STL, OBJ, 3MF and other formats through the Import and Mesh modules | the export snippets in `SKILL.md`, `assembly-and-3mf.md`, mesh references |
| `freecad-assembly` | Assembly joints, mating parts, the reference format | `assembly-and-3mf.md` |
| `freecad-fem` | FEM analysis: solver, material, constraints, mesh, run | the FEM recipe in `workbenches-and-advanced.md` |
| `freecad-curves` | the Curves addon: two-rail sweeps, Gordon and ruled surfaces, joined splines | `curves-and-curved-shapes.md` |
| `freecad-curved-shapes` | the Curved Shapes addon: ribs between hull curves | `curves-and-curved-shapes.md` |
| `freecad-gui-and-workbenches` | commands, task panels, Pivy, FeaturePython objects, custom workbenches | `gui-and-interface.md`, `parametric-objects.md`, the workbench-authoring part of `workbenches-and-advanced.md` |
| `freecad-macros` | macro structure, the selection API, running macros, console output | the macro parts of `SKILL.md` and `workbenches-and-advanced.md` |
| `freecad-mcp` | driving FreeCAD through the `freecad-mcp` server: `execute_code`, `execute_code_headless`, GUI-thread limits | the MCP parts of `SKILL.md`; the server's tool names from its source at v0.1.28 |

## Non-goals

- Skills for Draft, Surface and TechDraw. The source barely covers them; they are authored and run in the second plan.
- Skills for CAM, BIM, OpenSCAD, Material, Points or Robot. A separate plan, if wanted. Point clouds are mentioned inside
  `freecad-reverse-engineering`.
- A base `cad` module, or a module for another vendor's CAD program. The owner decided on 2026-10-28 that each vendor
  gets its own module and that none is shared.
- The owner's conventions from the source (one object named `VarSet`, PascalCase `App::PropertyLength` names, no
  Spreadsheet unless asked, millimetres and 3MF as defaults, one Body per assembly part). The owner dropped them on
  2026-10-28. The techniques stay as options, and the choice is left to the project.
- A pinned helper, a `wb run` command or a launcher for the script (rejected, below), a wrapper that starts `freecadcmd`,
  or any code that starts a program.
- Installing FreeCAD, an addon, `uvx` or a FreeCAD MCP server, writing any MCP client or harness configuration, or telling
  the agent to do any of these. A skill whose tool is missing says so and stops.
- Editing the owner's global configuration, the global-config inventory (the owner is retiring that configuration, so no
  rows are added), or the roadmap.
- Removing the owner's personal `freecad-scripts` skill. That is the owner's.
- A claim that advice is correct beyond what was run. Structure is tested; advice is read unless a run is recorded.

## Assumptions and constraints

- Python 3.11 minimum, standard library only; tests use `unittest`; the full suite is `python3 -B -W error
  tests/run_all.py`. `tests/` names no first-party module (`tests/test_boundary.py`); the module's own tests may.
- The module's directory is `packages/workbench/freecad/`; skills live under `harness/neutral/skills/<name>/` as in
  `packages/workbench/verilog/`. A skill is `SKILL.md` with bundled files below it, at most 100, each at most 1 MiB, the
  item at most 256 KiB, and a description of at most 300 characters (`workbench/neutral.py`).
- No two first-party packages ship one skill name (`2026-10-23-one-owner-per-skill-name`). The owner's personal
  `freecad-scripts` is not used as a name here (the core skill is `freecad-python`), so the two never collide.
- The candidate's dependencies, `claude-harness` and `groundwork-module`, are complete.
- The source text is the owner's, in the owner's global configuration, and is not in this repository, so no tracked text
  cites a path to it. Hashes read on 2026-10-28 (sha-256): `SKILL.md`
  `8d4a357642fefcf6e9103d87b61cd4ef5d0cd70762e070dc7682d783abac61d8`; `assembly-and-3mf.md`
  `d7cfd2823281fc08d4d57b3dcdf2bbabac4d5a436a96d778372165760c9bacaa`; `curves-and-curved-shapes.md`
  `a3b7f547dbe7bc71acd1e431337b4475263619dd0e8c2e214768221493b7d08b`; `geometry-and-shapes.md`
  `f735be42da66970faaac47569b4e84641ef78d424ccac6e771023a5cbc72ae4c`; `gui-and-interface.md`
  `385a58f61994b445670bc5fb5cee2563ed3b93432e4b081bc81dda291182e667`; `images-to-cad.md`
  `a05a3961fa85b1019e3c8b974b4e3199d2dfb7cae4ddf6e7cfecf13ed543fb8a`; `mesh-reverse-engineering.md`
  `c6c0e6aec409ebcfc04acf16dc50c36faacc79523f98b7c1df3e0b9e4165439a`; `parametric-objects.md`
  `35dc4038e790465080000c79260bfafe9e748fc92e1a9edadb253aad2fd4c1ec`; `partdesign-and-parameters.md`
  `f8f717ad97998b2b6485fd4368829e8496cab05d0a1e2e433475774fab7196ec`; `scripting-fundamentals.md`
  `61466858ccea16a5191ac8d0de069952dd41a8cdb23b0f494fedd82244a1dc6d`; `workbenches-and-advanced.md`
  `20cb9c3a36e4e6b636554d9deb6e66874b00eb7df969726252f85628d80f2b7a`; `scripts/mesh_report.py`
  `4f7930f406d4ef099bedc5c577fb7cbbb539f2fdc28edb5929f3e9206f362667`. A different hash at the start of an increment
  means the source changed; the owner is told before it is used. These files are owner-local and have no source URL, so
  they are identified by name, read date and hash, as the global-config inventory identifies its items. Once copied into
  the module, `scripts/mesh_report.py` is a tracked file, and the byte-identity test compares it with the hash recorded
  here; the hash is the reproducible check, and the owner's file is not needed to run the tests.
- FreeCAD 1.1.4 (revision 20260928, from the project's AppImage, checksum verified against the release page's file) is
  extracted on this machine and runs headless with `freecadcmd`, with Python 3.11.14 and numpy 1.26.4. It is the owner's
  install, outside the repository; no tracked text names its path. It is the version the source says it was verified
  against. Each run of it is the owner's decision: I run it only when the owner has said so for that increment, from a
  scratch directory, and record the version and what was run.
- The Curves and Curved Shapes addons are not installed in that FreeCAD, so their skills cannot be run (Risks).
- The upstream server `freecad-mcp` (MIT, `https://github.com/neka-nat/freecad-mcp`) is read at v0.1.28, commit
  `8babe9927ce8e6e8fe7dd6ae2ffa2c93776e845a`, on 2026-10-28, from a clone the owner keeps. Of its files, `src/freecad_mcp/server.py`
  has sha-256 `80aba311dd4e88a6d5908d5b53b6b959733bacff65ecb128679352491a26f84f`. Increment H records the same URL, date and
  commit, and the sha-256 of every other file it reads, in the Result. No tracked text names the clone's path. The skill
  names the project and version but holds no URL (the module's tests ban URLs in skill text).
- The FreeCAD wiki refuses automated access, so no wiki page is read or cited. Which workbenches get a skill was chosen
  from two listings of FreeCAD's module directory, read on 2026-10-28: the project's source tree on GitHub
  (`https://github.com/FreeCAD/FreeCAD/tree/main/src/Mod`, read as a page listing, not as bytes, so it has no file hash; the
  sha-256 of its 31 names, sorted, one per line, is `362da27b86ad16bb9ccd1af5970940560658a2631afdbf0c61e2ea49e7c8b6af`) and the
  extracted 1.1.4's own module directory (sha-256 of its names, sorted, one per line,
  `4a16bcf60098d4b54465b7a832131da478bf3556a2636aa05b19a71b270702dc`). The two differ slightly (the branch is newer). No
  statement in a skill rests on either listing; each statement rests on a run in 1.1.4 or is marked read.
- Editing or adding to a module changes the package tree, so each increment makes the shipped approvals stale and the
  command and edit gates refuse until the owner runs `wb release-approvals` (as in plan `2026-10-28-verilog-module`).
  Staging new files in a scratch directory and copying them in with one command keeps this to one release per increment.
  The last increment releases the final tree. Four test lists of module names elsewhere in the repository (in the `claude`,
  `code-work` and `groundwork` tests) end at the last module and need `"freecad"` added in increment A; the previous plan
  missed this, and its Result records it.

### Choices (made by me; the owner may change any)

1. **Names.** The module is `freecad`. Skills are named by workbench (`freecad-part`, `freecad-mesh`) or, for a workflow
   across workbenches, by task (`freecad-image-to-model`), following the owner's wish on 2026-10-28 that workbench names
   be used. The core skill is `freecad-python`, not `freecad-scripts`: in this module every skill scripts FreeCAD, and
   the name would collide in meaning with `scripts/mesh_report.py`.
2. **The script ships as a bundled file, not as a helper.** A module command is a pinned helper run by the launcher either
   as `python3 -I` with the kit, which has no FreeCAD, or as a pinned executable; the script needs FreeCAD's interpreter
   (`freecadcmd`). Running it as a pinned helper would need a new wrapper that starts a second program on user-chosen paths.
   The owner accepted the bundled file on 2026-10-28. The bundled file is covered by the package tree hash and so by the
   owner's release of approvals, but it is not a pinned `wb run` command; the agent starts it through the ordinary command
   gate. Increment A confirms that the verifier accepts a bundled `.py` in a skill; if it refuses, the plan stops there and
   the owner decides.
3. **Skills carry what the tool does, not the owner's habits.** Advice states a technique and when it applies. A statement of
   the owner's preference is removed.
4. **The first-party text is not copied.** Every skill and reference is rewritten from a read of the source. FreeCAD's own
   source and documentation are not copied either; facts are checked by running.
5. **One skill may repeat a few lines of another.** A skill cannot cause another to load, so `freecad-sketcher` and
   `freecad-partdesign` each repeat the deprecated-API rows they need (`AttachmentSupport`, `body.newObject`); the full table
   lives in `freecad-python`.
6. **Distinct descriptions.** A skill is chosen by its description, at most 300 characters. The tests check each begins
   with "Use when", names its own subject, and is not the description of another skill; overlapping skills (Part and
   PartDesign, Mesh and ReverseEngineering) name which to use for what.
7. **Nine increments.** Skills are grouped by subject, with the script and the risky ones early (A: the verifier check;
   D: the bundled script), and approvals and the record last.

## Completion criteria

1. `packages/workbench/freecad/` passes the verifier (`python3 -m workbench verify packages/workbench --select freecad`),
   is listed in `package.json`, has type `module`, provides nothing, and ships no helper, command or check.
2. The module ships exactly the seventeen skills in Scope, each with `SKILL.md` and `reference.md`, the front matter valid,
   the description at most 300 characters and distinct; `freecad-reverse-engineering` also ships `scripts/mesh_report.py`,
   byte-identical to the source read, and no other skill ships a script.
3. No skill or reference names a vendor harness, a personal path, a harness-specific file or a URL, holds an instruction
   to read outside the project, or tells the agent to install or download a program; each states its scope first and what
   to do when its tool, workbench or addon is missing (stop and tell the owner).
4. The shipped approvals are released by the owner; the full suite is green in all roots with no stale-approval skip; the
   document checks and `git diff --check` print nothing.
5. The Result names, for each skill, what was read, changed or dropped, added by the author, run and not run, with the
   FreeCAD version and the commands run.

## Increments

Every skill increment follows the same method (M), so it is stated once:

- **M1.** Check the hashes of the sources it reads against Assumptions; stop and tell the owner on a difference.
- **M2.** Test first: extend the module's tests with the skill names and its text checks (below) and see them fail for
  the missing skill.
- **M3.** Write each skill and its `reference.md` in a scratch directory, then copy them into the module in one command and
  ask the owner to run `wb release-approvals`, because the gates refuse until then.
- **M4.** Run the module's tests, then `env PYTHONPATH=.:tests python3 -B -W error -m unittest tests.test_package
  tests.test_skill_names tests.test_boundary`, then `wb run code-work check` and `git diff --check`.
- **M5.** With the owner's word, run in FreeCAD 1.1.4 (`freecadcmd`, from a scratch directory) the snippets and
  deprecated-API rows the skill states as fact, and record each command and result; a claim not run is marked read in the
  skill and listed as not run in the Result. A snippet that fails is corrected or dropped, never kept.
- **M6.** Record the increment in the Result and stop for the owner. On the owner's word, make the one local commit with
  `wb run safe-git commit`, the exact paths and the increment's trailer; never push.

The text checks the module's tests apply to every skill: valid front matter and a one-line description of 40 to 300
characters beginning "Use when"; the opening paragraph after the heading states the scope and what to do when the tool is
missing; the skill points to its `reference.md`; no vendor, harness or personal-path word (`claude`, `codex`, `anthropic`,
`openai`, `~/`, `/users/`, `/home/`, `.claude`, `superpowers`, `global_config`, `/opt/`); no URL and no download or
installation words; no description shared with another skill; and the module ships exactly the skills the increments have
added so far, plus exactly one bundled script once D is done.

### Increment A — The module, the core skill and the verifier check

**Outcome:** the module exists, verifies and ships `freecad-python`; a bundled `.py` is known to be accepted or the plan has
stopped; the four module-name lists elsewhere include `freecad`.
**Dependencies:** none; the owner's source for this skill (Assumptions).
**Affected areas:** `packages/workbench/freecad/module.json`, `packages/workbench/freecad/harness/neutral/skills/freecad-python/`,
`packages/workbench/freecad/tests/`, `packages/workbench/package.json`, and the four lists of module names in the tests of
`claude`, `code-work` and `groundwork`.
**Steps:**
1. M1 for `SKILL.md` and `scripting-fundamentals.md`, `geometry-and-shapes.md` (for units and the document model).
2. Test first (M2), plus a test that builds a temporary copy of the module with a bundled `scripts/x.py` beside a
   `SKILL.md` and checks that the neutral reader and `verify.verify_package` accept it. See it fail for the missing module.
   If the verifier refuses the `.py`, stop and report; do not weaken the verifier.
3. Write `module.json` (type `module`, no `provides`), add `freecad` to `package.json`, and write the skill (M3): the
   environment, `freecadcmd` and `FreeCAD.GuiUp`, the deprecated-API table, units, the document model, the "compare and
   report numbers" rule, the shorthand-to-API terms, and the missing-tool rule. The owner's conventions are not carried.
4. Add `"freecad"` to the four lists of module names in the tests of the other modules, and run the full suite once.
5. M4, M5 for the table's rows, M6.
**Verification:** the module's tests; the package tests; the full suite; M5 (each table row run).
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-module#A`.

### Increment B — Part and Sketcher

**Outcome:** the module also ships `freecad-part` and `freecad-sketcher`.
**Dependencies:** A.
**Affected areas:** the two skill directories, the module's tests.
**Steps:** M1 to M6 for `geometry-and-shapes.md` (shape hierarchy, primitives, curves, wires and faces, operations, loft and
sweep, topology) and the Sketcher parts of `partdesign-and-parameters.md` and `geometry-and-shapes.md` (the constraints
reference, sketch health, construction and external geometry). `freecad-part` states when to prefer PartDesign
(`freecad-partdesign`); `freecad-sketcher` carries its deprecated-API rows.
**Verification:** as M4, M5.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-module#B`.

### Increment C — PartDesign and parameters

**Outcome:** the module also ships `freecad-partdesign` and `freecad-parameters`.
**Dependencies:** B.
**Affected areas:** the two skill directories, the module's tests.
**Steps:** M1 to M6 for `partdesign-and-parameters.md`. `freecad-partdesign` carries features, patterns, multi-body
modelling and common failures. `freecad-parameters` carries the VarSet technique from the source, a Spreadsheet section
written by me (create a sheet, set cells, alias a cell, bind a property by expression, recompute) and a neutral comparison
of the two; both additions are marked in the skill as the author's and are listed under "added by the author" in the Result.
The Spreadsheet snippets are run under M5 before they are kept.
**Verification:** as M4, M5.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-module#C`.

### Increment D — Mesh and reverse engineering, with the script

**Outcome:** the module also ships `freecad-mesh` and `freecad-reverse-engineering`, the latter with the bundled script,
byte-identical to the source.
**Dependencies:** A (the verifier check passed).
**Affected areas:** the two skill directories, `scripts/mesh_report.py`, the module's tests.
**Steps:**
1. M1 for `mesh-reverse-engineering.md`, the mesh parts of `geometry-and-shapes.md` and `scripts/mesh_report.py`.
2. Test first (M2), plus tests that the script is byte-identical to the hash in Assumptions, and a static check that it
   imports only `json`, `os`, `math`, `sys`, `FreeCAD`, `Mesh`, `numpy` and `Part`, names no `subprocess`, `socket`, `urllib`,
   `http`, `ftplib` or `shutil`, and keeps its `--json` guard (the strings that refuse the input file, a symlink and a
   non-`.json` target). See it fail.
3. Write the skills (M3). The script is copied unchanged and not rewritten; the skills say how it is run (`freecadcmd`
   from the skill's folder, with the arguments the script accepts) and that its claims about repair side effects are the
   author's measurements, read here. The path in the source's instructions is replaced by "the skill's folder".
4. M4; M5 with a small generated mesh (a cube and a cylinder written to STL in a scratch directory): the script's triage, the
   `--repair` option, the primitive fit and the deviation function are each run and the output recorded.
5. M6.
**Verification:** as M4, M5.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-module#D`.

### Increment E — Image, measurement and file formats

**Outcome:** the module also ships `freecad-image-to-model`, `freecad-measure-and-inspection` and `freecad-import-export`.
**Dependencies:** D.
**Affected areas:** the three skill directories, the module's tests.
**Steps:** M1 to M6 for `images-to-cad.md` (reworded where it names an assistant or an MCP tool), the distance and
validity recipes, and the export snippets (STEP, IGES, STL, OBJ, 3MF). `freecad-import-export` is the one place that names
the formats; the others point to it. The Inspection and Measure modules are described only where a run in 1.1.4 shows what
they do.
**Verification:** as M4, M5.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-module#E`.

### Increment F — Assembly and FEM

**Outcome:** the module also ships `freecad-assembly` and `freecad-fem`.
**Dependencies:** C.
**Affected areas:** the two skill directories, the module's tests.
**Steps:** M1 to M6 for `assembly-and-3mf.md` (joints, the reference format; the 3MF part is left to
`freecad-import-export`) and the FEM recipe. The FEM snippet is run in M5 only as far as the extracted FreeCAD allows; the
solver needs an external program that is not installed here, so the solver step is marked not run.
**Verification:** as M4, M5.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-module#F`.

### Increment G — The two addons

**Outcome:** the module also ships `freecad-curves` and `freecad-curved-shapes`.
**Dependencies:** C.
**Affected areas:** the two skill directories, the module's tests.
**Steps:** M1 to M4 and M6 for `curves-and-curved-shapes.md`, split by addon. Each skill states that the addon is not part of
FreeCAD, that its interface is unversioned, the tested version, and that a missing addon means stop and tell the owner. The
macOS addon paths are dropped. The addons are not installed in the extracted FreeCAD, so M5 cannot run: every claim is marked
read and the Result lists the skill as not run. The "prefer the core PartDesign pipe, loft and revolution" guidance
points to `freecad-partdesign`.
**Verification:** as M4 (no M5).
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-module#G`.

### Increment H — GUI, macros and the MCP server

**Outcome:** the module also ships `freecad-gui-and-workbenches`, `freecad-macros` and `freecad-mcp`.
**Dependencies:** A.
**Affected areas:** the three skill directories, the module's tests.
**Steps:** M1 to M6 for `gui-and-interface.md`, `parametric-objects.md`, the workbench-authoring and recipe parts of
`workbenches-and-advanced.md`, and the macro parts of `SKILL.md`. For `freecad-mcp`, read the server's tool names and
arguments at v0.1.28 and write only what they show; the skill states the version it was written against. GUI code is run in
M5 only under `freecadcmd`; whatever needs a display is marked not run.
**Verification:** as M4, M5.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-module#H`.

### Increment I — Approvals and record

**Outcome:** the shipped approvals match the final package tree and the plan records what was done.
**Dependencies:** A to H.
**Affected areas:** `workbench/shipped_approvals/` (by `release-approvals`), this plan's Result.
**Steps:**
1. The owner runs `wb release-approvals`, or asks me to run it. Remove stale records only after a preview and the owner's
   "remove them".
2. Run the full suite, `wb run code-work check`, `wb check` and `git diff --check`.
3. Fill the Result and set the plan `Completed`.
4. On the owner's word, make the one local commit with `wb run safe-git commit`, the exact paths and the trailer below.
**Verification:** `python3 -B -W error tests/run_all.py` is green with no stale-approval skip; the document checks print
nothing.
**Evidence:** the one local commit, trailer `Plan: 2026-10-28-freecad-module#I`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` green in all roots; `wb check` and `wb run code-work check` report no problems;
  `git diff --check` prints nothing.
- `python3 -m workbench verify packages/workbench --select freecad` accepts the module.
- `tests/test_skill_names.py` passes with seventeen new names.

## Risks and sensitive actions

- **Running FreeCAD.** M5 starts a program the owner extracted. Each run is at the owner's word, from a scratch directory,
  with files I generate there; it reads and writes nothing in the project. The script reads a mesh path it is given and
  writes only a `.json` file after refusing the input file, a symlink and a non-`.json` target. The owner declined a
  security review on 2026-10-28.
- **The bundled script is code that an agent may run.** It sits in the package tree, so its bytes are covered by the shipped
  approval, but it is not a pinned `wb run` command. The static test pins its hash and its imports. A later edit to the
  script changes the hash test and the package tree.
- **Advice that was not run.** The Curves and Curved Shapes skills, any step needing a display, the FEM solver and the
  MCP server's behaviour are read, not run. Each says so; the Result lists them.
- **Size and context.** Seventeen descriptions, each up to 300 characters, are always in context (about 5 KB). Skills with
  similar subjects must name which to use for what; the tests check that descriptions differ, not that the choice is right.
- **The owner's text and a third party's.** The skills are rewritten from the owner's text; FreeCAD (LGPL) and `freecad-mcp`
  (MIT) are read for facts and cited, not copied.
- **Gate lockout after each increment** until the owner runs `wb release-approvals`; the mitigation is in Assumptions.
- **Roadmap drift.** The roadmap's `cad-modules` text describes a tool-neutral `cad` module and a FreeCAD module with one
  skill, and it asks for the mesh script as a pinned and approved helper. This plan follows the owner's decisions of
  2026-10-28 instead (no `cad` module, a bundled script). The roadmap is not edited here, and this plan does not name the
  candidate. The companion plan, which does, requires the owner to revise the roadmap entry before it is marked
  `Completed`, so the candidate is not reported complete against an outcome it did not deliver.
- Nothing is committed or pushed without the owner's explicit word, and no dependency is installed.

## Review record

Independent review through the review engine (bridge `ask-codex`, model `gpt-5.6-terra`, effort medium), asked for by the
owner on 2026-10-28, three rounds of a bound of three. The reviewer's findings are untrusted input; each was judged on the
evidence. A review is not an approval.

- **Round 1** (changes needed, two major).
  - R1-F1, the plan drifts from the roadmap candidate: **applied**. The companion plan now requires the owner to revise
    the roadmap entry before it can complete, so the candidate cannot be reported complete against a different outcome.
  - R1-F2, no stable source URL for the owner-local sources: **applied** as a clarification. The sources have no URL;
    they are identified by name, date and hash, and the tracked copy of the script is checked against the recorded hash.
- **Round 2** (changes needed, one major).
  - R2-F1, incomplete provenance for the `freecad-mcp` server and the module listings: **applied**. URL, date, commit
    and file hash are recorded, the later increment must record the hashes of the other files it reads, and the plan says
    that the page listing has no file hash and that no skill statement rests on it.
- **Round 3** (no meaningful changes, converged). One minor note, that this section was empty, is addressed by this record.

Remaining disagreement: none. The roadmap entry still describes a different outcome; revising it is the owner's, and the
companion plan will not complete without it.

## Deferred work

- Draft, Surface and TechDraw skills: the second plan, `2026-10-28-freecad-authored-skills`.
- CAM, BIM, OpenSCAD and Material skills, and any `freecad-mcp` setup guidance: not planned.
- Revising the roadmap's `cad-modules` entry to match the owner's decisions: the owner's call, after both plans.
- Running the addon skills against installed addons, the FEM solver, and display-dependent GUI code: when FreeCAD with those
  is available.
- The owner's removal of the personal `freecad-scripts` skill and of its routing text, if any.

## Result

### Increment A

- **Read (2026-10-28):** the source `SKILL.md`, `scripting-fundamentals.md`; the three hashes matched the plan at the start.
  `geometry-and-shapes.md` was not needed for this skill (units and the document model are in `scripting-fundamentals.md`).
- **Rewritten, not copied.** `SKILL.md` has the run-headless-first rules, the document and recompute rule, units, the
  compare-and-report rule, the table of removed, renamed and deprecated APIs, the shorthand-to-API mapping and common
  mistakes. `reference.md` has the module layout, documents, vectors and placements, units, properties, the console and a
  script template. The owner's conventions are not carried. The MCP advice, the macro and GUI material and the generic
  API tutorial sections are left to later skills.
- **Dropped or changed:** every wiki link; the `PartDesign::Pad` "must be in a Body" row left the table of removed APIs
  (see below); the source's `getTypeOfProperty` note was wrong on 1.1.4 and is replaced.
- **Bundled-script check (the plan's stop condition):** a test builds a temporary package with a `scripts/probe.py` beside
  a `SKILL.md`; the neutral reader stages it and `wb verify` accepts it with no `ships` entry. So the bundled script of
  increment D is allowed.
- **Written:** `packages/workbench/freecad/` (`module.json`, the skill, `tests/test_freecad_module.py`, 14 tests),
  `"freecad"` in `packages/workbench/package.json`, and `"freecad"` in the four lists of module names in the tests of
  `claude`, `code-work` and `groundwork`.
- **Verification as run:**
  - Test first: 4 failures and 10 errors before the module existed.
  - Module tests, 14, OK; `tests.test_package tests.test_skill_names tests.test_boundary`, 29, OK; the full suite
    `python3 -B -W error tests/run_all.py`, 5855 tests in 13 roots, OK; `wb run code-work check` (61 plans) and `wb check`
    found no problems; `git diff --check` printed nothing.
- **Run against FreeCAD 1.1.4 (revision 20260928), headless with `freecadcmd`, at the owner's word, from a scratch
  directory** (Python 3.11.14, numpy 1.26.4): 23 checks, then a follow-up printing 17 lines. Matched the skill: `GuiUp` false and
  `ViewObject` `None` headless; arguments after `--` reach `sys.argv`; `PySide2` absent and `PySide`, `PySide6` present;
  `import FEM` fails and `Fem`, `ObjectsFem` import; `makeSolverCalculixCcxTools` absent and the two newer names present;
  `Drawing` and `importOBJ` absent and `TechDraw` present; `Mesh.export` to `.obj`; `sketch.Support` absent and
  `AttachmentSupport` set; `Constraint("Fixed")` raises `TypeError` while `Block` and a `Coincident` to the origin are
  accepted; the shorthand methods exist (volumes 1000, 1571, 4189); documents, objects, vectors, placements, units
  (`1 in` = 25.4 mm), properties and console calls behave as the reference shows.
- **Found wrong or too strong, corrected in the skill:**
  1. `import FreeCADGui` succeeds headless but has none of the GUI parts (no `Selection`, `Control`, main window); the
     skill had said it is "not usable".
  2. `Draft.makeArray` and the camelCase Draft names still exist in 1.1.4; they are deprecated, not removed. The table
     heading and two rows now say so.
  3. A `PartDesign::Pad` made with `doc.addObject` and given a profile recomputed to a valid 500 mm³ solid; the Body rule is
     a modelling convention (marked read), not an error the tool raises.
  4. In the source, `getTypeOfProperty` is said to return the type name; it returns the property flags (`[]` here).
     `getTypeIdOfProperty` returns `App::PropertyFloat`.
- **Not run, marked (read) in the skill:** `dialog.exec_()`, `getStandardButtons`, `ViewObject.DiffuseColor`, the icon path,
  `Std_Macro`, the Gmsh `mesh.Part` row, the statement that a modal dialog blocks the GUI thread, the other property
  statuses, and `FreeCADGui.SendMsgToActiveView` in the script template.
- **Added by the author:** none beyond rewording and the corrections above.
- **Gate:** the owner ran `wb release-approvals` twice for this increment (after the copy, and after the corrections).
  Six records are reported stale; none was removed. Increment I removes them after a preview.
- **Not done:** no independent review of the increment (only when the owner asks); no run in the GUI.

### Increment B

- **Read (2026-10-28):** the hashes of `SKILL.md`, `geometry-and-shapes.md` and `partdesign-and-parameters.md` matched the plan
  at the start. Read in full: `geometry-and-shapes.md`; from `partdesign-and-parameters.md`, the opening example, "Sketch
  health", "Sketcher beyond rectangles" and "Common failures".
- **Rewritten, not copied.** `freecad-part` covers the shape hierarchy, building from the bottom up, combining and
  finishing, reading a shape, and putting a shape in the document. `freecad-sketcher` covers attaching a sketch,
  geometry and constraints, sketch health, naming a constraint, and external geometry. The Mesh operations of
  `geometry-and-shapes.md` are left to `freecad-mesh`, and the constraints reference table is in the sketcher's reference.
- **Method:** every example in the two reference files is a self-contained block, and a runner extracted and ran each block
  in a fresh namespace in FreeCAD 1.1.4 (revision 20260928, headless, at the owner's word, from a scratch directory). The
  runs were made before the files were copied into the module, so the increment needed one release of approvals.
- **Verification as run:**
  - Test first: 2 failures and 8 errors before the skills existed.
  - Module tests, 14, OK; package tests, 29, OK; the full suite, 5855 tests in 13 roots, OK; `wb run code-work check` (61
    plans) and `wb check` found no problems; `git diff --check` printed nothing.
- **Run against FreeCAD 1.1.4:** 13 blocks, then two follow-up scripts and two added blocks, 15 blocks in the final run, none
  raising. Confirmed: the primitives, curves, wires, faces, solids, booleans, fillets, chamfers, thickness, offset,
  section, extrude, revolve, loft, `makePipeShell` and the topology readers (volumes and lengths checked against the
  geometry, for example a frustum loft of 408.4 and a revolve of 942.5); `Part.show` headless; a rectangle in a Body
  (8 degrees of freedom before dimensions, 0 and fully constrained after); conflicting constraints (`solve()` negative,
  `ConflictingConstraints` `[1, 2]`); a constraint driven by a VarSet property (40.0 then 55.0); the names that fail as
  constraint names (`h m s l t g in mm N V`) and the ones that do not (`width len w r`); a construction line, a tangent
  arc and line, a spline; external geometry from a sketch edge and a Body origin axis.
- **Found wrong or too strong in the source, corrected in the skills:**
  1. `Part.Face([outer, hole])` with two wires of the same direction gave an invalid face (`isValid()` False, area
     112.566, not 87.434). The hole wire must be reversed, or a face made from it cut from the outer face.
  2. `makePipe` returns an open `Shell` whose `Volume` equals its area (377.0); `makePipeShell(..., True, ...)` gives the
     solid (565.5).
  3. An edge of a Pad was accepted as external geometry (the source says it raised); the claim is dropped and the
     advice to prefer a sketch edge or an origin axis is marked read.
  4. An extra `Coincident` beside an end-point `Tangent` made `solve()` return `-2` and appeared in
     `RedundantConstraints`, which confirms the source's advice.
  5. The degrees of freedom of four coincident lines are 8, not the 4 first written in a comment.
- **Not run, marked read:** that edge names change when the model changes.
- **Added by the author:** none beyond rewording and the corrections above.
- **Gate:** the owner ran `wb release-approvals` once for this increment. Eight records are reported stale; none was
  removed. Increment I removes them after a preview.
- **Not done:** no independent review of the increment (only when the owner asks); no run in the GUI.

### Increment C

- **Read (2026-10-28):** the hash of `partdesign-and-parameters.md` matched the plan at the start. It was read in full.
- **Rewritten, not copied.** `freecad-partdesign` covers building inside a Body, the features that use a sketch (Pad,
  Pocket, Hole, Revolution, AdditivePipe, AdditiveLoft), datum planes, Fillet, Chamfer and Thickness, the patterns and
  MultiTransform, several Bodies, and checking the result. `freecad-parameters` covers VarSet and Spreadsheet as two
  ways to hold dimensions, binding them with expressions, derived values, and a bad expression. The sketch material of
  the same source file went to `freecad-sketcher` in increment B.
- **Dropped or changed:** the owner's conventions (the object named `VarSet`, PascalCase names, "VarSets preferred, a
  Spreadsheet only if asked"); the example names in the source's VarSet section are replaced by neutral ones; the
  "multi-body modelling" section no longer says "the user's models".
- **Method:** as in increment B. The examples of both reference files are self-contained blocks (with a shared
  "Helpers" prelude) that a runner extracted and ran in FreeCAD 1.1.4 (revision 20260928, headless, at the owner's
  word, from a scratch directory) before the files were copied into the module, so the increment needed one release.
- **Verification as run:**
  - Test first: 2 failures and 8 errors before the skills existed.
  - Module tests, 14, OK; package tests, 29, OK; the full suite, 5855 tests in 13 roots, OK; `wb run code-work check`
    (61 plans) and `wb check` found no problems; `git diff --check` printed nothing.
- **Run against FreeCAD 1.1.4:** 18 blocks, none raising. Confirmed with the volumes the geometry gives: a Pad (4000), Hole
  and Pocket (3874.34, 3803.65), Chamfer (3961.33), Thickness (1952.0), LinearPattern and MultiTransform (3905.75), PolarPattern
  (251.3), Mirrored (3748.67), Revolution (6283.2), straight and curved AdditivePipe (848.2, 394.8), AdditiveLoft (3665.2),
  a datum plane (5.0), SubShapeBinder and Boolean (2000.0, 3000.0); a failed feature (`['Touched', 'Invalid']`,
  `isValid()` false, "Wire is not closed" in the console); VarSet-driven and derived dimensions (6000.0, 9000.0, 5280.0);
  Spreadsheet cells, aliases and formulas driving a Pad and a sketch constraint (6000.0, 9000.0, 22.0 mm and 2640.0).
- **Settled by running:** a feature made with `doc.addObject` belongs to no Body (its parent group is `None`, it is not in
  the Body's group list and the Tip is unchanged), and when its profile sketch is inside a Body the recompute reports
  the links as out of scope. The source's "unlinked" is right. The increment A finding, that a loose Pad recomputed
  fine, holds only when its sketch is outside a Body too.
- **Found by running (not in the source):** `setExpression` accepts an expression that names a property which does not
  exist; the failure shows only at the recompute, as `['Touched', 'Invalid']` with a console message.
- **Added by the author:** the Spreadsheet section of `freecad-parameters` (create a sheet, set cells, alias a cell,
  formulas with a leading `=`, binding by expression) and the neutral comparison of a VarSet and a Spreadsheet. The
  snippets were run; the comparison is the author's judgement and is stated as such in the skill.
- **Not run, marked read:** that a sheet can import and export files (the two methods exist, which was checked, but they
  were not exercised), that a mirror plane that misses the part does nothing, that a binder cuts nothing by itself, and
  that face and edge names change when the model changes.
- **Gate:** the owner ran `wb release-approvals` once for this increment. Ten records are reported stale; none was removed.
  Increment I removes them after a preview.
- **Not done:** no independent review of the increment (only when the owner asks); no run in the GUI.

### Increment D

- **Read (2026-10-28):** the hashes of `mesh-reverse-engineering.md`, `geometry-and-shapes.md` and `scripts/mesh_report.py`
  matched the plan at the start. `mesh-reverse-engineering.md` was read in full, and the script was read in full when the
  plan was drafted.
- **Rewritten, not copied.** `freecad-mesh` covers loading, making and writing a mesh, the mesh and shape conversions, the
  operations, the health checks, the repair steps and the reading calls. `freecad-reverse-engineering` covers the script, the
  seven-step workflow, what to expect from fitting, repair, choosing features, and the report to the owner. The worked
  example of the source uses neutral names (`Dims`) and finds the script beside the skill (`<skill folder>/scripts`)
  where the source used a path under the owner's configuration. The wiki-style links and the owner's convention
  (a VarSet named `VarSet`) are not carried.
- **The script is copied, not rewritten.** `scripts/mesh_report.py` in `freecad-reverse-engineering` is byte-identical to
  the source (sha-256 `4f7930f406d4ef099bedc5c577fb7cbbb539f2fdc28edb5929f3e9206f362667`, checked by `cmp` and by a test).
  It is the only script in the module. Tests read it as text: the hash; that it imports only `json`, `os`, `math`, `sys`,
  `FreeCAD`, `Mesh`, `numpy` and `Part`; that it holds no `subprocess`, `socket`, `urllib`, `ftplib`, `shutil`, `http`,
  `os.system`, `os.popen`, `exec(`, `eval(` or `__import__`; and that its `--json` guard is present.
- **Written:** the two skill directories (a `SKILL.md` and a `reference.md` each), `scripts/mesh_report.py`, and the module's
  tests (19 in all, five of them new for the script).
- **Verification as run:**
  - Test first: 3 failures and 12 errors before the skills and the script existed.
  - Module tests, 19, OK; package tests, 29, OK; the full suite, 5860 tests in 13 roots, OK; `wb run code-work check` (61 plans)
    and `wb check` found no problems; `git diff --check` printed nothing.
- **Run against FreeCAD 1.1.4 (revision 20260928), headless, at the owner's word, from a scratch directory:** 15 example blocks
  (8 mesh, 7 reverse engineering; the mesh file was run twice after corrections), none raising. Confirmed: mesh read,
  write, make and health calls; meshing a cylinder (1564.9 against the shape's 1570.8); a `makeSolid` result is valid and
  faceted (164 planar faces for 164 facets); the repair sequence removing a duplicated facet and a stray triangle;
  `crossSections`, `getPlanarSegments`, `getCurvaturePerVertex`, `wireFromMesh`, `trimByPlane` and `projectShapeOnMesh`; the
  script's `triage`, `repair`, `fit_primitives` and `deviation` on a generated box with a boss and a hole (radii 4.0 and
  8.0, coverage 0.992, all grades good); the worked rebuild (volume 13005.31 equal to the source's, three fully
  constrained sketches, deviation 0.0 within tolerance 1.0, and 14136.28 after the boss radius became 10); and all
  seven `ReverseEngineering` function names, with `approxSurface` and `normalEstimation` documented.
- **The script from the command line**, on generated STL files: with `--repair --json report.json` it printed the JSON and wrote
  the same JSON to the file, removed a stray triangle (1025 to 1024 facets, then a closed solid) and fitted the three
  planes and the two cylinders; it refused `--json` aimed at the input file, at `out.txt`, at a symbolic link and with
  no path, and the input file's hash was the same afterwards.
- **Found wrong, too strong, or not stated in the source, corrected in the skills:**
  1. `unite`, `intersect` and `difference` return a new mesh and do not change the mesh they are called on. On two boxes with
     coincident faces they gave 1166.7, 541.7 and 333.3 (right: 1500, 500, 500) and open meshes.
  2. `removeComponents(n)` removes every component of fewer than `n` facets; `removeComponents(20)` removed a whole
     12-facet box. The script's default `min_component_facets` of 20 does the same to a coarse mesh.
  3. The script's `tiny_components` counts any component of 20 facets or fewer, so a very coarse part is reported as debris.
  4. `smooth()` collapsed a 12-facet cube to 95.4 from 1000.0, and shrank a finely meshed sphere by 2.6%.
  5. `getPlanarSegments(0.05, 30)` found no plane in a 12-facet cube because its minimum is in facets, and the volume of a
     mesh trimmed with `trimByPlane` is meaningless because the mesh is open.
  6. The built-in `getSegmentsOfType("Cylinder", 0.05, 30)` found no cylinder in the generated part; the source says it
     breaks a clean cylinder into fragments. Both say it is unreliable; the numbers differ, and the skill says what was seen.
- **Not run, marked read:** the owner's measurements on a real scan (`removeNeedles` removing about a quarter of the facets,
  `optimizeTopology` bringing back self-intersections, `fixSelfIntersections` leaving `isSolid()` false), that drifting
  cylinder radii mean the surface is not a cylinder, the table of features to choose from the fits, and the behaviour of
  `approxCurve`, `poissonReconstruction`, `regionGrowingSegmentation`, `sampleConsensus` and `featureSegmentation`.
- **Added by the author:** none beyond rewording and the corrections above.
- **Gate:** the owner ran `wb release-approvals` once for this increment. Twelve records are reported stale; none was
  removed. Increment I removes them after a preview.
- **Not done:** no independent review of the increment (only when the owner asks); no run in the GUI; a missing input file
  to the script printed no error line in what I looked at, which was not investigated.

### Increment E

- **Read (2026-10-28):** the hashes of `SKILL.md`, `images-to-cad.md`, `workbenches-and-advanced.md` and
  `assembly-and-3mf.md` matched the plan at the start. Read in full: `images-to-cad.md` and `assembly-and-3mf.md`; from
  `workbenches-and-advanced.md`, the "Common Recipes" part (the distance, colour and batch-export recipes); from `SKILL.md`,
  the export snippets and units.
- **Rewritten, not copied.** `freecad-image-to-model` covers the workflow, pixel measurement, a reference image plane,
  comparing with the image, and shapes that cannot be measured. `freecad-import-export` covers STEP, IGES, BREP, STL, OBJ
  and 3MF, 3MF for printing, exporting every solid, whole documents, and the `Import` module. The 3MF section follows
  `assembly-and-3mf.md`; the assembly material of that file is left to `freecad-assembly`. `freecad-measure-and-inspection`
  has little in the source (a distance recipe, the deviation function of the script, validity calls), so most of it was
  found by running; it says so. The wiki-style links, the sentence naming an assistant, the MCP tool names and the
  owner's conventions are not carried.
- **Written:** the three skill directories (a `SKILL.md` and a `reference.md` each) and the module's tests (19, with three
  more skills in the list).
- **Verification as run:**
  - Test first: 2 failures and 8 errors before the skills existed.
  - Module tests, 19, OK; package tests, 29, OK; the full suite, 5860 tests in 13 roots, OK; `wb run code-work check` (61 plans)
    and `wb check` found no problems; `git diff --check` printed nothing.
- **Run against FreeCAD 1.1.4 (revision 20260928), headless, at the owner's word, from a scratch directory, every file in a
  temporary folder removed afterwards:** 15 example blocks and one shared prelude in the final run of the final files, none
  raising, after one block was corrected and one added (the `Measure.Measurement` block, first explored with a separate
  script, then run as written). Confirmed: the pixel measurement of a synthetic image (a scale of 10.0
  px/mm, a part of 64.0 by 48.0 mm and a hole of 15.99 mm at (32.0, 24.0), against the true 64, 48 and 16); `PIL`, `numpy`
  and `scipy` importable; `Image::ImagePlane` made headless with `XSize` 90 and `YSize` 70; the overlap of two shifted
  outlines (0.8462); STEP, IGES and BREP export and read-back with equal volume (4492.04); STL, OBJ and 3MF export of a
  cylinder (500 facets, volume 6280.6); the 3MF XML holding `unit="millimeter"`; a controlled 3MF (280 facets, solid, no
  non-manifold edges, volume 6275.0 against 6283.2, a bounding box of 19.99 by 20 by 20); the export of every solid in a
  document; saving and reopening a document; the `Import` names and `Import.insert`; shape validity, an open shell,
  `distToShape` between shapes and from points, `isInside`, the comparison with computed values, and the
  `Measure.Measurement` calls with the values stated in the skill.
- **Found wrong, too strong, or not stated in the source, corrected in the skills:**
  1. The source says the default 3MF export of a 20 mm cylinder gives 124 facets and a controlled export 280. Here the
     default gave 500 (finer than the controlled 280, and closer to the true volume). The default comes from FreeCAD's own
     tessellation setting, so the skill tells the reader to mesh the shape with chosen deflections for a repeatable result.
  2. A Boolean (`cut`) returns a `Compound`, which has no `CenterOfMass`; take `.Solids[0]` first.
  3. The vertices of a mesh made from a shape lie on the shape, so a vertex-to-surface deviation reads 0.0 even though the
     mesh volume is 0.3% smaller. The same is true of the script's `deviation` function. The skill calls it a one-way
     measure, right for scan points against a rebuilt model and wrong for a tessellation.
  4. `Inspection` exposes no public Python names on 1.1.4 headless, and `Measure` exposes `MeasureBase` and `Measurement`.
     `Measurement.addReference3D` takes the object's name as a string and raises `TypeError` for the object.
  5. A point inside a solid has distance 0.0 against the solid but 10.0 against a compound of its faces, and 10.0 against a
     `Compound` that wraps the solid. The first version of the example used the wrapped form and was wrong.
  6. IGES and BREP files read back as a `Compound`, and STEP as a `Solid`.
- **Not run, marked read:** that OpenCV is not bundled, the orientation of an image plane and keeping it out of exports,
  the GUI `saveImage` route and capturing a model view for an overlap check, the printer resolution and wall advice,
  the `lineLineDistance` and `delta` calls, and the DXF functions of `Import`.
- **Added by the author:** none beyond rewording and the corrections above.
- **Seen outside this increment:** `freecad-part` (increment B) does not say that a Boolean returns a `Compound`
  without a `CenterOfMass`. It was not changed here; the owner decides whether to correct it in increment I.
- **Gate:** the owner ran `wb release-approvals` once for this increment. Fourteen records are reported stale; none was
  removed. Increment I removes them after a preview.
- **Not done:** no independent review of the increment (only when the owner asks); no run in the GUI.

### Increment F

- **Read (2026-10-28):** the hashes of `assembly-and-3mf.md` and `workbenches-and-advanced.md` matched the plan at the start.
  `assembly-and-3mf.md` was read in full (its 3MF part went to `freecad-import-export` in increment E), and from
  `workbenches-and-advanced.md` the FEM section.
- **Rewritten, not copied.** `freecad-assembly` covers the structure, the one correct reference form and the silent failure of a
  wrong one, choosing faces and vertices by geometry, and the flip, offset, Revolute and expression behaviour.
  `freecad-fem` covers building the analysis, the force units, generating the mesh, running CalculiX, reading the result, and
  checking it against a hand calculation. The owner's conventions (the object named `VarSet`) and the MCP tool names are
  not carried.
- **The solver could be run.** The plan expected the FEM solver step to be marked not run. The AppImage of FreeCAD 1.1.4 carries the
  CalculiX (`ccx`) and Gmsh programs in its `usr/bin`, and with that folder on `PATH` the whole analysis ran. FreeCAD wrote
  its own temporary files for the mesher and the solver under the system temporary folder; the solver's working folder
  was one the examples made and removed.
- **Written:** the two skill directories (a `SKILL.md` and a `reference.md` each) and the module's tests (19, with two more skills
  in the list).
- **Verification as run:**
  - Test first: 2 failures and 8 errors before the skills existed.
  - Module tests, 19, OK; package tests, 29, OK; the full suite, 5860 tests in 13 roots, OK; `wb run code-work check` (61 plans)
    and `wb check` found no problems; `git diff --check` printed nothing.
- **Run against FreeCAD 1.1.4 (revision 20260928), headless, at the owner's word, from a scratch directory:** assembly, 6 blocks and a
  shared prelude, none raising; FEM, 8 blocks and a shared prelude, none raising, after the force units were corrected;
  and a separate script that solved the same beam five times with different forces and element sizes. Two comments of the FEM
  file were reworded after its last run; its code is as run.
- **Found wrong, too strong, or not stated in the source, corrected in the skills:**
  1. `force.Force = 1000.0  # Newtons` is 1 N: a bare number is stored in kg*mm/s^2 (`1000.0 mm*kg/s^2`). `"1000 N"` and
     `Quantity(1000, "N")` are stored as `1000000.0 mm*kg/s^2`. With 1 N the tip deflection of the beam was 0.0012 mm; with
     1000 N it was about 1.15 mm on a 5 mm mesh. The source's recipe is described as verified end to end (one result
     object), and that was true, but its load is 1 N and the displacement it would print is a thousand times too small.
  2. Against beam theory (1.905 mm for a cantilever of 100 by 10 by 10 mm, 1000 N, 210000 MPa) the tip deflection was
     about 0.60, 0.84 and 0.94 of the theoretical value at element sizes 5, 2.5 and 1.5 mm (about 500, 3600 and 15300
     elements). Gmsh varied by about 1% between runs (3561, 3586 and 3593 elements at 2.5 mm).
  3. Joint creation works headless; the source reports that it was exercised only in the GUI.
  4. The source says a solve without a generated mesh fails with a missing node set; `check_prerequisites()` caught it first
     with "FEM mesh has neither volume nor shell or edge elements" and nothing ran.
  5. Confirmed from the source: a wrong reference form (`"Pad.Face5."`) is accepted, `solve()` returns 0, both joint
     placements are the identity and the block lands inside the base (z 0 to 10 instead of 10 to 20); a Revolute joint's
     `Angle` does not turn the part; a flip moves the part to the other side and a second flip restores it; `Offset2`
     moves the mate; and an expression on `Offset2.Base.x` follows a named value.
  6. `mesh.Part = obj` raises an `AttributeError` and `mesh.Shape` is the property; the table of removed APIs in
     `freecad-python` still marks that row as read.
- **Not run, marked read:** `ObjectsFem.makeSolverCalculiX` (the newer solver), posing a mechanism with an Angle joint, and
  parts in other documents.
- **Added by the author:** the comparison with beam theory and the mesh refinement table, which are results of the runs.
- **For increment I (the owner decides):** `freecad-part` should say that a Boolean returns a `Compound` without a
  `CenterOfMass` (found in increment E), and the Gmsh row of `freecad-python` can drop its "read" mark (found here).
- **Gate:** the owner ran `wb release-approvals` once for this increment. Sixteen records are reported stale; none was
  removed. Increment I removes them after a preview.
- **Not done:** no independent review of the increment (only when the owner asks); no run in the GUI.

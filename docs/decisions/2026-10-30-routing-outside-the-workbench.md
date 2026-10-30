# What routes an agent to a process in a repository the workbench is not attached to

Status: Accepted by Robert Ziegler <25854477+rziegler42@users.noreply.github.com> on 2026-10-30

## Context

Until the owner's user-level configuration was reset on 2026-10-29, an instruction file at the user level told every agent, in every
repository, which skill to use for which kind of work (brainstorming before new behaviour, planning, test first, debugging, review,
verification), kept two guards (no automatic worktree; no merge or cleanup without approval) and relied on a plugin that injected a
"look for a skill first" rule at the start of each session. The reset removed all three. The specs record what the file said, by role
and date (`docs/specs/global-config-inventory.md`, `docs/specs/superpowers-ports.md`); nothing in this record points at the owner's
copy of it.

In a repository the workbench is attached to, the process is carried by the project: the `policy` block of `AGENTS.md`, the skills of
`groundwork` and `code-work`, the compiled floor of denied and asked commands, and the plan and commit helpers. In a repository it is
not attached to, none of that exists. `2026-10-24-project-guarantees-a-floor` already says that a project guarantees a floor under any
global setup, and does not promise identical behaviour: so what the owner wants outside the workbench is not something the project
can supply, and is the owner's to settle. That record's second alternative, resetting the user level and supplying everything from the
project, was rejected as a working position; the owner has since reset the user level, so this record is where the question it left
open is picked up.

What was observed on 2026-10-30, by the owner, with no plugin (`docs/specs/superpowers-ports.md`, "The session-start test"; the
owner reported the harness version, Claude Code v2.1.314, once after all the runs, not per run): in a workbench project the request "I want to design a new feature" loaded `brainstorm`, while a request to
add a command and "build it" had not invoked it when the agent asked how to proceed, and the agent offered `draft-plan` as the
recommended option; in a folder that is not a project, the skill did not load for the "design" request. One run of each. This record
is about the last case and about what the user level should hold. Whether `brainstorm` should be forced for new behaviour inside a
workbench project is a separate question and is not decided here.

Constraints: the workbench writes nothing at the user level and the owner's user-level files are the owner's to edit; a skill the
workbench ships exists only in a project that installed the module; a user-level file is not versioned with any repository and is read
by one harness; `AGENTS.md` ranks below the owner's current instruction and above recalled context (`## Source of truth`), so a
user-level instruction that disagrees with a project's `AGENTS.md` has to be resolved by that order.

## Decision

Options 2 and 4 together, chosen by the owner on 2026-10-30:

- The workbench is attached, per repository, to each repository where the owner wants its process. What routes an agent to a process
  in a repository is that repository's own attached policy block, skills, floor and helpers, and nothing at the user level duplicates
  them.
- The user level keeps only the two guards of the former instruction file: no automatic worktree, and no merge or cleanup without
  approval. They are the owner's to write, as instruction text or as permission rules that ask before a merge and before the removal
  of a worktree or branch; the workbench writes nothing at the user level.
- There is no user-level routing file (option 3 is not taken) and the user level is not left empty (option 1 is not taken).

Not decided here: the exact wording or rules of the two guards and whether they are text or permission rules; whether `brainstorm`
should be forced for new behaviour inside a workbench project (the gap recorded in `docs/specs/superpowers-ports.md`); and which
repositories get the workbench.

## Alternatives considered

Options 2 and 4 are the decision above. Options 1 and 3 are rejected, each with its reason; all four are stated with what they cost.

1. **Nothing at the user level.** An agent in a repository without the workbench works as the harness does by default: no routing
   to a process, no plan approval, no helper commits. No compiled floor applies there (the floor is rendered only in a project that
   has the workbench), and what the harness does by default for a merge or the removal of a worktree is not stated in the specs.
   Cost: nothing to maintain; the old routing and its two guards are not there. It reaches no harness in particular.
   *Rejected:* it leaves the two guards to defaults the specs do not describe.
2. **Attach the workbench to the repository, per repository, where the owner wants the process.** The repository gets the policy
   block, the skills, the floor and the helpers, which the specs describe. Inside an attached project the runs of 2026-10-30 still
   found a gap (`brainstorm` had not been invoked for the build-wording request), so attaching does not by itself give the routing the
   old file gave. Cost: an owner-run adopt or install for each repository, files written into it, and a per-repository upgrade. The
   process then lives in versioned text, and it reaches the harnesses that the attached harness modules support.
3. **A short user-level instruction file** that states the process in prose for any repository (design before building, a plan the owner
   approves before implementation, verify before claiming done). Cost: the workbench's skills exist only in an attached project, so
   the file would describe the practice and could not rely on them; the owner maintains it by hand; it is read by every session,
   workbench projects included, so it must not contradict a project's `AGENTS.md`; it is not versioned or reviewed with any
   repository; and it reaches the one harness whose user-level file it is. *Rejected:* it could only describe the practice, would
   have to be kept in agreement with every project's `AGENTS.md`, and would rebuild the file the owner reset.
4. **Only the two guards at the user level**, as two lines of instruction or as permission rules that ask for a merge and for the
   removal of a worktree or branch. Cost: it gives no routing, so design-before-building is left to the agent; how a harness treats such
   a rule is not tested here; and either form reaches only the harness whose user-level file it is. It is a small amount of text or a
   few rules for the owner to keep, and either form is the owner's edit of their own user-level files.

Options 2 and 4 combine, and so do 2 and 3; option 1 excludes the others. The owner took 2 and 4.

## Consequences

Nothing in the workbench changes by this record: it writes no user-level file and builds nothing. What follows is the owner's work: to
attach the workbench to the repositories where the process is wanted, and to write the two guards at the user level. A repository
without the workbench keeps little or no routing, and its two guards rest on whatever the owner writes; the choice also leaves the
`brainstorm` gap inside an attached project open. The options differ in where the process lives. Options 1 and 4 leave a repository without the workbench with little or no routing; the one
run in a plain folder on 2026-10-30 is the only observation of that, and it is one request. Option 2 puts the process in the
repository's own versioned text, at the price of attaching each repository, and inside an attached project the routing was observed
to depend on the request. Option 3 puts text where it reaches every repository for one harness, at the price of wording that is not
versioned with any repository and that cannot rely on a skill. A choice that adds user-level text adds a second source of process
wording alongside a project's `AGENTS.md`, and the owner keeps the two in agreement; one that adds none leaves the project as the
only source.

A later record may supersede this one, and the choice may differ per repository.

## Evidence

Read on 2026-10-30 at commit `e6fb410`: `docs/specs/superpowers-ports.md` (the inventory of the plugin's skills, the differences found,
and the session-start test with the owner's runs), `docs/specs/global-config-inventory.md` (what the former instruction file carried,
by role, and the note that the reset ended that state), `docs/decisions/2026-10-24-project-guarantees-a-floor.md` and `AGENTS.md`
(`## Source of truth` and the policy block). The runs are the owner's, reported in their own words with the harness version
"Claude Code v2.1.314" given once after all of them; they were not repeated by the author. The choice was made by the owner on 2026-10-30 after the author recommended options 2 and 4
and gave the reasons recorded above; the recommendation is not evidence. Conclusion: in the one plain-folder run, `brainstorm` did not
load for one "design" request, which is what option 1 leaves; the observations do not show what option 3 or 4 would do, which is not
tested here, nor what the harness does by default for a merge.

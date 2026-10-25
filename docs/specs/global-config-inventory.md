# global-config-inventory

Status: Draft. Written by plan `2026-10-25-global-config-migration` (increment A). Parts B to D are not written yet; this
text covers the owner's user-level agents, hooks, skills and helper programs only. It is a record of what was read and
what is proposed, and it settles nothing.

Terms are defined in `terms.md`. The direction it serves is the roadmap candidate `workbench-v1#global-config-migration`;
the decision that frames it is `2026-10-24-project-guarantees-a-floor`.

## Scope

A line-by-line comparison of the owner's global Claude configuration against the specs and shipped modules, so that every
item has a recorded disposition and the later moves can be planned one item at a time. This part holds the
user-level agent definitions, hook programs, the approver's data files, skills and helper programs. The settings file and
the instruction file come in later parts of this spec.

Each item has one disposition:

| disposition | meaning |
|---|---|
| `move` | a workbench module already supplies it; the global copy can go once a test or recorded run shows a project behaves the same without it |
| `redesign` | the workbench supplies part of it, or supplies it in another shape; the item changes before or as it moves |
| `drop` | nothing needs it |
| `keep global` | it stays in the owner's configuration, because it is machine-level, personal, or has no workbench cover and none is planned |

A disposition is a proposal for the owner. No item is moved by this spec, and no durable choice in it is settled; a
choice among alternatives becomes a decision record only when the owner asks for one and accepts it.

## Non-goals

- Editing the user level. The agent does not write it (`2026-10-24-project-guarantees-a-floor`); every removal is the owner's,
  in a terminal.
- Moving any item, or changing the installer or a shipped module. A defect found here is recorded as a finding and planned
  separately.
- The settings file and the instruction file (later parts), and the owner's `allow` rules, which the workbench never writes.

## Provenance and what was not inspected

The global files are owner-local, untracked and have no source URL. They are identified here by role, item name, the date
they were read and their SHA-256 content hash. This spec writes no path to a global file (`AGENTS.md`: nothing tracked points
to anything untracked). Items inside a file are named by their own name.

Read on 2026-10-25 against this repository at `58a1903`, with the hashes taken at the start of the increment. The end hashes
are in "Hashes at the end".

**Read in full:** the five agent definitions, both hook programs (about 3,600 lines together), the four authored skills and their three
reference files, and the head of `opencode-workflow` (the first 60 lines).

**Read in part, with the reason:**

- The three helper programs `ask-codex` (1,697 lines), `claude-workflow` (633) and `remote-runner` (1,916) were hashed and
  compared by size and role with the shipped helpers, and not read line by line. The comparison that matters here is
  whether a workbench module supplies the same job, which the specs and the plans that built the modules record. A
  line-by-line diff of behaviour is the gating test of each move, not this inventory's.
- The approver's data directory: the configuration file and the eight rule files were listed with their identifiers and
  hashes, and the rubric was read by its headings only. The rubric is the approver's judgement text; its content belongs to
  the `action-review-engine` design, not to a disposition.
- The approver's logs were not read. They hold command digests and are runtime state (`Never mirror generated or private Claude
  state`).

**Not inspected:**

- The harness-synced skill bundle (228 files, 13 skills) is a payload the harness writes and refreshes; it is generated, not
  authored, and is not mirrored. Only its skill names and its manifest hash are recorded.
- Compiled bytecode under the hooks directory (generated).
- Third-party tools installed by `uv tool` or `pipx` (`graphify`, `mempalace` and their servers, `uv`, `uvx`, the numpy
  tools): they are programs the owner installed, not configuration. Their content was not read, and no program was run.
- Authentication data, session state, history, caches and plugin payloads. They are not configuration
  (the owner's rule: never mirror them).

## Items

### Agent definitions (5)

Each is a Markdown file with a frontmatter block. Source: owner-local, no URL; retrieved 2026-10-25.

| item | sha-256 | what it is | workbench cover | disposition and reason |
|---|---|---|---|---|
| `implementer` | `1d46f30839903fe0902a74401cff4f5ac498cebf4e17584e596bcf9e491fb912` | implements one approved slice; tools read, search, edit, write, shell; `skills:` names three plugin skills | no agent. `run-increment` runs the loop in the author's own context; "a fresh implementer per increment" is recorded as a gap and deferred (`superpowers-ports.md`; plan `2026-10-23-increment-loop-and-review-skills`) | `redesign`. Its `skills:` list breaks when the plugin goes; the workbench skills are `diagnose-failure`, `test-first` and `verify-before-claiming`. Whether a project gets an implementer agent is the owner's choice and has no candidate yet. Until then it stays global with its list repointed. |
| `safe-committer` | `38f6f93a63a4a2aeb53763efa364cb8b34904e2d39616ef9aa1ee124c6963c34` | makes one commit through the commit helper; runs under the guard's `committer` mode | `safe-git` and its skill `commit-changes` (the agent runs the helper itself). No agent | `keep global`. The workbench commits through `wb run safe-git commit`, and the agent's text and the guard's `committer` mode name the global helper. A workbench counterpart would be a confined agent whose pinned command is the module's, which the agent gate's grammar (`security-review.md`) does not yet describe. No candidate; see finding F-A7. |
| `security-reviewer` | `ea6589d56bd00a3a98a405b116d952366602a1e671378edd1b133480b3f5b896` | adversarial review with scratch experiments; `skills:` names `security-review` and a plugin skill; guard mode `security` | `security-review` module: skill `security-review` and confined agent `security-reviewer` (`security-review.md`) | `move`. Same name; a project agent wins over a global one, so the move changes no name. Gate: a recorded run in an attached project showing the rendered agent loads, its hook fires and the guard refuses a write outside scratch. Blocker: none, but the module has not been attached in a live project (`security-review.md` lists that as not shown), which the gate supplies. Residual: the guard runs only in a trusted folder (`security-review.md`, "Limits"). |
| `technical-researcher` | `efe23719bd92f179e69da250697f033962541bdd0fa004dd9ea7be1f450eca45` | web research without repository leakage; tools read, search, web; guard mode `research` | no module. `harness-modules.md` leaves "whether either harness can hand a specific tool to a specific agent" open (`researcher-fetch-tool`) | `keep global`. It needs a web tool narrowed per agent, which the workbench cannot yet declare. No candidate promotes it. |
| `workflow-reviewer` | `02d40c1d4fd3da3022956e70e84c816f647943ef89fd5350916736b34ee2d3da` | read-only final review; Bash to run the repository's checks; `skills:` names two plugin skills | `reviewer` agent (read and search only) and `request-review` (`code-work.md`) | `redesign`. The workbench reviewer covers the independent read; it cannot run a check, which this agent's Bash does. Repointing its `skills:` list is needed either way. Whether a project needs a reviewer that runs checks is the owner's choice; until then it stays global. |

### Hook programs (2) and the approver's data files (11)

| item | sha-256 | what it is | workbench cover | disposition and reason |
|---|---|---|---|---|
| `review_agent_guard.py` | `19330bb6c5c7fb557afd068e39f77cfc07cbcb5b35fd249a57ab3977aa1bd9c1` | a PreToolUse allowlist guard with five modes: `reviewer`, `security`, `research`, `committer`, `chunk`; fails closed | the installer's generic agent gate for a confined agent (`harness-modules.md`, "The agent gate"), which covers the `security-reviewer` shape (scratch writes, pinned commands). Nothing covers `research`, `committer` or `chunk` | `keep global`. Four global agents still call it. The `security` mode retires with `security-reviewer`'s move; the `reviewer` mode serves `workflow-reviewer` only. `chunk` serves an agent that is not among the five (F-A4). Modes leave it as the agents move, not before. |
| `codex_approver.py` | `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b` | a PermissionRequest hook that reviews prompts for the owner's helpers and `git push`, logs a verdict, can allow two delegated rules, and records outcomes | `action-review-engine` (roadmap, unbuilt). Decision `2026-10-22-model-calls-go-through-vendor-bridges` keeps the enforcement point in the owner's configuration and gives the engine only verdicts as data | `keep global`. Its rules and rubric are separate items below, each `redesign`, into `action-review-engine`. Blocker: that candidate has no plan. It is the approver the move order must never leave absent (F-A1). |
| approver configuration file | `8cbc91e2b03068d3a2373b33410841262091042bde2629bf4003de122a7c3dae` | mode `delegate`; delegates two rules (`claude-workflow-commit`, `ask-codex-archive`); notifications on | none | `keep global`. Machine-level and personal; a model and an effort setting. |
| approver rubric | `49e369d28ee425c66608dcd6540eb9aa945d6ca000a47e48f117ac1a2b172799` | the judgement text; eight rubric sections (commit, remove, push, four remote-runner kinds, ask-codex-archive) | `action-review-engine` (rubric and rules, unbuilt) | `redesign` into that module's rubric; read by headings only. |
| approver verdict schema | `ead8d9b7c80e962ad890685ef6c0c054bf10bb5b0796374c02cc59e336d3570a` | the reply schema Codex must return | same | `redesign` with the engine. |
| approver rule `ask-codex-archive` | `eb07890ec8de965b361ef95971d0d9023481ba4a8d558fecdd82f582aed07ae3` | matches `ask-codex archive` | `review-engine` owns `archive` as an owner-run command | `redesign`: the rule matches the global spelling only (F-A1). |
| approver rule `claude-workflow-commit` | `e7743892a3bb77c034153999478faf131b04446a294accbbb3e5558cc55407c1` | matches `claude-workflow commit`; delegated | `safe-git commit` | `redesign`: the rule matches the global spelling only (F-A1). |
| approver rule `claude-workflow-remove` | `f7822bfbca84da927bbe04564ff2589ce8df7bd7587fb7eed38b73f2b4ec84e9` | matches `claude-workflow remove` | `safe-git remove` | `redesign` (F-A1). |
| approver rule `git-push` | `11a01a007a99bd3e79fe4e9f3ac25da0c3706770478260ee9c1f0288a6f5f3cf` | matches plain `git push` | `push-changes` skill and `safe-git push-check` | `keep global`: it matches plain `git`, which a project also uses. |
| approver rule `remote-runner-cancel` | `3aadda4480c6a0991da3c03852d4e8dab010ca6d60456d74fa8a2f1873a444ed` | matches `remote-runner cancel` | `remote-runner` module | `redesign` (F-A1). |
| approver rule `remote-runner-fetch` | `3c5602e31475a15d98ccc43751c6005ce9f15efd3d821ed44b8beb2664c4a36d` | matches `remote-runner fetch` | `remote-runner` module | `redesign` (F-A1). |
| approver rule `remote-runner-prune` | `3ba149f5b1e9c381cf3194fdc4ffba2bbde333810d96f9cac9ea2d5c298fff37` | matches `remote-runner prune` | `remote-runner` module | `redesign` (F-A1). |
| approver rule `remote-runner-submit` | `a0e39556e80c35f51492d1798fb47ba302d60aa01f0fe72be5b730720e0431c4` | matches `remote-runner submit` | `remote-runner` module | `redesign` (F-A1). |

### Skills (4, and the synced bundle)

| item | sha-256 | what it is | workbench cover | disposition and reason |
|---|---|---|---|---|
| `architecture-decisions` | `a6ab399b23ae0c65549b9b1ab1429898e3e4e30b1df2631a24e4d400ef811e90` | how to propose, record, accept and supersede an ADR | `draft-decision` (groundwork), merged by plan `2026-10-24-architecture-decisions-merge`, which left "what happens to the personal one" to this candidate | `move`. The workbench skill carries the same rules: `Proposed` only, acceptance is the owner's act, a changed decision is a new record, an index and status search after a change. It differs in name, so both load today; the global one adds a default ADR template and a four-digit numbering default that the workbench replaces with dated names. Gate: a recorded run in an attached project where the agent drafts a record with only `draft-decision`. |
| `knowledge-base-authoring` | `82b070a06b9392a2f37249f2aee6dcfa93f82d2ee01ca0bc0b614187f8d62b50` | create and upgrade a knowledge-base store with the starter's installer | none. `knowledge-base-package` is unbuilt | `keep global`; it becomes a `redesign` when that candidate is built. It names the retired template's registration command and a specification in the retired global repository (F-A5). |
| `knowledge-base-authoring` reference: create and upgrade | `3904e625a85ad9d9bae23f0d0ce83a29b7f85fc58a05aae975bb2e4936b9a50f` | steps for a store create and upgrade | same | same disposition, same reason |
| `knowledge-base-authoring` reference: domain | `39ad12b0354ba2151cab19e564e747ffcd81c05c4a0b6edd57bce3f37852fb34` | steps to create a domain and set its charter | same | same disposition, same reason |
| `security-review` | `5eba555ed664db4319475d2dd69d8de5e9400a6b32e444758f1c6f0796ed795d` | focused security review recipe | module skill `security-review`; the module text keeps each recipe (boundary tracing, fake programs, path guards, edge values, fail-closed validation, no real secrets, regression test for a fix, an independent second look, findings with tested or read-only marks) in its own words | `move`. Same name; a personal skill replaces a project skill of the same name (observed 2026-10-24), so the project copy is shadowed until the global one goes. Gate: a recorded run showing the project skill loads once the global one is out of the way. |
| `verilog-verilator-sim` | `18ded3133fbbc1d8891bc15ebdc84b1c115e09202dcf0fb17a44436724bac452` | Verilator simulation verification practice | `verilog-module` (roadmap, unbuilt) | `move`, blocked on that candidate. The roadmap asks for a read of its content for accuracy before it moves. |
| `verilog-verilator-sim` reference | `d367e0031204321d44de74fefc534fbb64860ffaee2819c7cd3d7f75ec7f19db` | a worked testbench and sources | same | `move`, same blocker |
| harness-synced bundle: manifest | `cce72b7333a64a0f845f00e9eeaeb71b3427fa269cad4734a04ca67c21640599` | manifest of a bundle of 13 skills (`built-in-browser`, `chrome-browser`, `computer-use`, `deep-research`, `docs`, `docx`, `google-workspace`, `import-memory`, `morning`, `pdf`, `pptx`, `skill-creator`, `xlsx`) holding 228 files | none, and none planned: it is the harness's own payload | `keep global`. Generated and refreshed by the harness; not authored, not read, never mirrored. |

### Helper programs

| item | sha-256 | what it is | workbench cover | disposition and reason |
|---|---|---|---|---|
| `claude-workflow` | `7add9cfd6d6b0473c8084d69b9384ea0ed29c5234943a8a2a4fb56e26cdf5464` | the commit and removal helper (633 lines) | `safe-git` (`commit`, `remove`, `push-check`) | `move`. Gate: a recorded run of commit and an approved removal through `wb run safe-git` with the approver still reviewing them (F-A1). Blocker: the approver must match the new spelling first. |
| `ask-codex` | `68936f4723f228ab8108a980d3a65242365f34a1e93c809d44d08832a822d454` | the owner's Codex bridge and review runner (1,697 lines) | `ask-codex` bridge module and `review-engine` (plan `2026-10-23-review-engine`: "the owner's `ask-codex` once a recorded run shows a project gets the same review from the module") | `move`. Gate: that recorded run. The module is about a quarter of the size and covers a read-only question; the global program also runs the archive action the approver delegates. |
| `remote-runner` | `dc2d8485aafd140c66a6e883f3bd2d0b0b476c7ba38eb618e704771d14b4c209` | the remote job program (1,916 lines) | `remote-runner` module, which pins a helper and reads `.workbench/remote-runner.toml` | `move`, blocked: the program must read the new project-file path first (`remote-runner.md`, "What the program must change"; plan `2026-10-24-remote-runner-module`). The owner's `allow` rules and remote list are not moved. |
| `opencode-workflow` | `ab614146b52efc0e84429e27e4592eac17c68ae6a14d0db8bb69ee95e4120e09` | deterministic Git and Graphify operations for the opencode workflow (534 lines) | none; `opencode-harness` and `graphify-module` are unbuilt | `keep global`. Read in part (the first 60 lines). Revisit when either candidate is promoted. |
| `graphify`, `graphify-mcp` | not hashed: third-party installs | the code graph tool and its server | `graphify-module` unbuilt (`knowledge-tools.md`) | `keep global`. Machine-level installs; the module, when built, finds the program in a trusted `PATH` entry. |
| `mempalace`, `mempalace-mcp`, `mempalace-light-mcp` | not hashed: third-party installs | the memory search tool and its servers | `mempalace` module pins a helper that runs the owner's installed program (`mempalace.md`) | `keep global`. The module does not install or replace the program. |
| `uv`, `uvx` | not hashed: third-party installs | the Python tool manager | none | `keep global`. Machine-level. |

The numpy command-line tools and the harness binary also sit on the owner's `PATH`. They are not configuration and not
Claude-related; they are out of scope and not recorded further.

## What the building plans said they would let this work retire

Four earlier plans list the global items they replace. Quoted from the plans:

- `2026-10-23-review-engine`: "the owner's `ask-codex` once a recorded run shows a project gets the same review from the
  module". Used in the `ask-codex` row.
- `2026-10-24-remote-runner-module`: the paragraphs of the global instruction file about `remote-runner` profiles,
  provenance, snapshots, artifact fetching and pruning, and the use of the project file; they stay until the program reads
  the new path and a recorded run shows a project behaves the same. The owner's `allow` rules and remote list are not moved.
  The `remote-runner` row covers the program; the paragraphs are inventoried in the instruction-file part.
- `2026-10-23-compaction-guidance` and `2026-10-23-push-checkpoint`: the "Compact instructions" section and the push
  instruction of the global instruction file, none retired yet. Both are inventoried in the instruction-file part.

## Findings

Findings are for the owner to plan or dismiss. None changes a shipped module here.

- **F-A1: the approver would not review the workbench's commands.** It matches the raw text of a command against a fixed list
  of spellings of the global helpers and plain `git`. A command written `wb run safe-git commit` or `wb run remote-runner`
  matches no rule and is logged as unmatched, so moving a helper into a project removes the approver's review of that
  action unless the rules and the list of spellings change first. This fixes the order of the move list: the approver's
  coverage of a new spelling comes before the helper moves (`workbench-v1#global-config-migration`: "no hard stop,
  deny rule or approver is ever absent in between").
- **F-A2: stale pointers in the approver.** Its header cites a specification and an active-plan file by names this repository
  does not use (`docs/specs/` has no such spec; plans are dated files, not one fixed file).
- **F-A3: reviewer-facing paths.** The approver lists the paths whose commits need extra scrutiny (the reviewer prompts, a
  `second-opinion` skill, two agent files). The workbench's reviewer text lives under other names (`peer-review`,
  `reviewer`, `security-reviewer` skill files in modules), so a commit editing them is not recognised as reviewer-facing.
- **F-A4: a guard mode with no agent.** `chunk` exists for a `graphify-semantic` agent that is not among the five agent
  definitions. It is either left over or waits for a definition that is elsewhere.
- **F-A5: the knowledge-base skill depends on retired things.** It cites a specification in the retired global repository and
  the retired template's `--register` command.
- **F-A6: three agents name plugin skills** in their `skills:` lists (already recorded in `superpowers-ports.md`; confirmed
  against the current files: `implementer` three, `workflow-reviewer` two, `security-reviewer` one).
- **F-A7: the commit agent names the global helper.** `safe-committer` and the guard's `committer` mode accept only
  `claude-workflow commit`, never `wb run safe-git commit`.

## Hashes at the end

Re-hashed on 2026-10-25 when increment A finished: all 30 files listed in "Items" have the hash recorded there, so none
changed while the work ran, and this work wrote nothing at the user level. The harness-synced bundle's other 227 files
were not hashed.

## Acceptance criteria

1. Every file under the inspected global locations appears once in "Items", or in a named group (the synced bundle, the
   bytecode) with the reason it is a group.
2. Every item has one disposition from the table above and a reason.
3. The spec says what was read in full, in part, and not at all, and why.
4. The spec writes no path to a global file and no credential, host name or token.
5. Nothing under the user level was written by this work: the end hashes equal the start hashes, or each difference is
   reported as a change by something else.

## Governing decisions and references

- Decisions: `2026-10-24-project-guarantees-a-floor`, `2026-10-22-model-calls-go-through-vendor-bridges`,
  `2026-10-24-declared-agent-confinement`, `2026-10-23-one-owner-per-skill-name`.
- Specs: `superpowers-ports.md`, `security-review.md`, `safe-git.md`, `remote-runner.md`, `review-engine.md`,
  `harness-modules.md`, `knowledge-tools.md`.
- Plans: `2026-10-25-global-config-migration`, `2026-10-24-architecture-decisions-merge`,
  `2026-10-24-security-review-module`, `2026-10-23-review-engine`, `2026-10-24-remote-runner-module`.
- References: the owner's global files are owner-local with no source URL; each is cited above by role, name, retrieval date
  (2026-10-25) and content hash.

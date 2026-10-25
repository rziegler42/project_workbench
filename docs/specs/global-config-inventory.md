# global-config-inventory

Status: Draft. Written by plan `2026-10-25-global-config-migration` (increment A). Increment B added the user-level settings
file and increment C the user-level instruction file and the superpowers dependencies. Part D (the move list) is not
written yet. It is a record of what was read and what is proposed, and it settles nothing.

Terms are defined in `terms.md`. The direction it serves is the roadmap candidate `workbench-v1#global-config-migration`;
the decision that frames it is `2026-10-24-project-guarantees-a-floor`.

## Scope

A line-by-line comparison of the owner's global Claude configuration against the specs and shipped modules, so that every
item has a recorded disposition and the later moves can be planned one item at a time. This text holds the
user-level agent definitions, hook programs, the approver's data files, skills and helper programs (increment A) and the
user-level settings file (increment B), and the user-level instruction file with the superpowers dependencies (increment C).

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
- The owner's `allow` rules, which the workbench never writes.

## Provenance and what was not inspected

The global files are owner-local, untracked and have no source URL. They are identified here by role, item name, the date
they were read and their SHA-256 content hash. This spec writes no path to a global file (`AGENTS.md`: nothing tracked points
to anything untracked). Items inside a file are named by their own name.

Read on 2026-10-25 against this repository at `58a1903` (increment A; B and C ran at later commits of the same day), with the hashes taken at the start of the increment. The end hashes
are in "Hashes at the end".

**Read in full:** the five agent definitions, both hook programs (about 3,600 lines together), the four authored skills and their three
reference files, the settings file (634 lines), and the head of `opencode-workflow` (the first 60 lines).

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

## The user-level settings file

Identified by role: the owner's user-level settings file, owner-local, no URL, 34,228 bytes, SHA-256
`ec038970a30093e74dddbf690643a617b43e5eddf1bf59ad862f604085e9f315`, read in full on 2026-10-25 (the same
hash was taken at the start and at the end of increment B). It holds no credential, host name or token. The comparison is
with the project's rendered permission file for this repository (a per-clone, untracked file written by attach; read on the
same day), the specs `harness-modules.md`, `code-work.md` and `remote-runner.md`, and the decision
`2026-10-19-restrictive-only-permissions`.

The project's render has 58 `ask` entries and 281 `deny` entries (counted from the file read on 2026-10-25; the 2026-10-24
trial's 122 `deny` and 58 `ask` were a smaller throwaway project, and this one has more modules attached). It has no `allow` entry, one `PreToolUse` hook (the
edit gate) and no other setting.

### Top-level keys

| key | what it holds | disposition and reason |
|---|---|---|
| `permissions` | `allow` (46), `ask` (84), `deny` (18) and `defaultMode` | split: each entry has its own disposition below |
| `permissions.defaultMode` | `auto` | `keep global`: a machine-level choice. The 2026-10-24 trial found project `deny` and `ask` rules held under `auto` (`harness-modules.md`, "Evidence"), which is the floor. |
| `hooks` | three events, all running the approver (see "Hooks in the settings file") | `keep global`, with the approver |
| `enabledPlugins` | four plugins | split: each plugin has its own disposition under "Plugins" |
| `advisorModel`, `model`, `modelSettings` | model choice and effort | `keep global`: personal and machine-level; the workbench does not choose a model (`2026-10-24-project-guarantees-a-floor`) |
| `theme`, `agentPushNotifEnabled` | display and notification | `keep global`: personal |

### Permission entries

#### `allow` (46 entries)

Every `allow` entry is `keep global`: the workbench never writes `allow` (`2026-10-19-restrictive-only-permissions`), and what it allows is the owner's machine-level choice. Entries sharing a row have the same disposition and reason; each entry is listed.

| group | entries | disposition and reason |
|---|---|---|
| read of the user-level skills directory (1) | (one entry, named by the group) | `keep global`: read-only access the owner granted |
| read-only git (13) | `Bash(git status:*)`, `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(git show:*)`, `Bash(git rev-parse:*)`, `Bash(git check-ignore:*)`, `Bash(git ls-files:*)`, `Bash(git blame:*)`, `Bash(git describe:*)`, `Bash(git remote -v:*)`, `Bash(git for-each-ref:*)`, `Bash(git worktree list:*)`, `Bash(git branch --list:*)` | `keep global`: read-only git queries |
| raw `git add` and `git mv` (2) | `Bash(git add:*)`, `Bash(git mv:*)` | `keep global`: staging commands; the owner allows them, and the commit helper refuses a staged index |
| search (1) | `Bash(rg:*)` | `keep global`: read-only search |
| project check runners (14) | `Bash(make test:*)`, `Bash(make check:*)`, `Bash(make lint:*)`, `Bash(make build:*)`, `Bash(pytest:*)`, `Bash(python3 -m pytest:*)`, `Bash(npm test:*)`, `Bash(npm run test:*)`, `Bash(npm run lint:*)`, `Bash(npm run check:*)`, `Bash(npm run build:*)`, `Bash(cargo test:*)`, `Bash(cargo check:*)`, `Bash(go test:*)` | `keep global`: test and build runners the owner trusts |
| `claude-workflow` read subcommands (2) | `Bash(claude-workflow context:*)`, `Bash(claude-workflow project-id:*)` | `keep global`: read-only subcommands of a global helper |
| `ask-codex` review and status subcommands (8) | `Bash(ask-codex review-plan:*)`, `Bash(ask-codex review-spec:*)`, `Bash(ask-codex review-roadmap:*)`, `Bash(ask-codex review-adr:*)`, `Bash(ask-codex decide:*)`, `Bash(ask-codex status:*)`, `Bash(ask-codex models:*)`, `Bash(ask-codex init:*)` | `keep global`: subcommands of a global helper the agent may run |
| `remote-runner` read subcommands (5) | `Bash(remote-runner remotes:*)`, `Bash(remote-runner recommend:*)`, `Bash(remote-runner status:*)`, `Bash(remote-runner log:*)`, `Bash(remote-runner artifacts:*)` | `keep global`: read-only subcommands of a global helper |

#### `ask` (84 entries)

Each helper command below is listed in five spellings (bare name, the user bin path, the local bin path, `python3` + the user bin path, `python3 -B` + the user bin path); the five entries of a row have the same disposition and reason. The approver hook sees only a prompt that an `ask` rule raises (`codex_approver.py` header), so these entries are also what makes the approver look (F-B1).

| rule | entries | project supplies | disposition and reason |
|---|---|---|---|
| `ask-codex extend` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | a `deny` on the module's `review-engine` command of that name (owner-run) | `move`: gates the global program; the project's deny holds for the module, so the entry goes when the program does |
| `ask-codex reset` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | a `deny` on the module's `review-engine` command of that name (owner-run) | `move`: gates the global program; the project's deny holds for the module, so the entry goes when the program does |
| `ask-codex prune` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | a `deny` on the module's `review-engine` command of that name (owner-run) | `move`: gates the global program; the project's deny holds for the module, so the entry goes when the program does |
| `ask-codex archive` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | a `deny` on the module's `review-engine` command of that name (owner-run) | `move`: gates the global program; the project's deny holds for the module, so the entry goes when the program does |
| `claude-workflow commit` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | no `ask`: `wb run safe-git commit` and `remove` render none (F-B2) | `keep global`: gates the global helper and triggers the approver; stays until the module's commands are asked or the owner accepts the loss |
| `claude-workflow remove` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | no `ask`: `wb run safe-git commit` and `remove` render none (F-B2) | `keep global`: gates the global helper and triggers the approver; stays until the module's commands are asked or the owner accepts the loss |
| `claude-workflow amend-message` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | no `ask`: `wb run safe-git commit` and `remove` render none (F-B2) | `keep global`: gates the global helper and triggers the approver; stays until the module's commands are asked or the owner accepts the loss |
| `remote-runner submit` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | no `ask`: the module renders none for these (`remote-runner.md`, "The checkpoints"); only a `deny` on `fetch-overwrite` | `keep global`: gates the global program and triggers the approver; stays until the program reads the project file and the commands are asked |
| `remote-runner cancel` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | no `ask`: the module renders none for these (`remote-runner.md`, "The checkpoints"); only a `deny` on `fetch-overwrite` | `keep global`: gates the global program and triggers the approver; stays until the program reads the project file and the commands are asked |
| `remote-runner prune` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | no `ask`: the module renders none for these (`remote-runner.md`, "The checkpoints"); only a `deny` on `fetch-overwrite` | `keep global`: gates the global program and triggers the approver; stays until the program reads the project file and the commands are asked |
| `remote-runner fetch` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | no `ask`: the module renders none for these (`remote-runner.md`, "The checkpoints"); only a `deny` on `fetch-overwrite` | `keep global`: gates the global program and triggers the approver; stays until the program reads the project file and the commands are asked |
| `Bash(git commit:*)` | 1 | only `git commit --amend*` | `keep global`: the project does not ask for a plain raw commit; the owner's rule keeps raw commits prompted |
| `Bash(git push:*)` | 1 | `ask` on every `git push` and each force form | `move`: the floor renders it (`code-work.md`, "Push"); that the global approver hook also fires on the project's prompt is an inference (F-B1) |
| `Bash(git tag:*)` | 1 | none | `keep global`: no project rule for tags |
| `Bash(git switch:*)` | 1 | none | `keep global`: no project rule for switching |
| `Bash(git stash:*)` | 1 | only `git stash drop*` | `keep global`: the project asks for the destructive form only |
| `Bash(git branch -d:*)` | 1 | none | `keep global`: no project rule for branch deletion |
| `Bash(git branch -D:*)` | 1 | none | `keep global`: no project rule for branch deletion |
| `Bash(git branch --delete:*)` | 1 | none | `keep global`: no project rule for branch deletion |
| `Bash(gh:*)` | 1 | only `gh release create*` | `keep global`: broader than the project's rule |
| `Bash(ssh:*)` | 1 | none | `keep global`: remote access is machine-level; no project rule |
| `Bash(scp:*)` | 1 | none | `keep global`: remote access is machine-level; no project rule |
| `Bash(rsync:*)` | 1 | none | `keep global`: remote access is machine-level; no project rule |
| `Bash(pip install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(pip3 install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(python3 -m pip install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(npm install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(npm ci:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(cargo install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(cargo add:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(brew install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(apt install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(apt-get install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(go install:*)` | 1 | `go get*` only | `keep global`: the project's install list has no `go install` |
| `Bash(uv pip install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(uv add:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| `Bash(pipx install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the rendered rule was read, not run interactively |
| an `Edit` rule on the approver's data directory | 1 | none (it guards a global file) | `keep global`: the workbench never writes or guards the user level |
| an `Edit` rule on the approver hook program | 1 | none (it guards a global file) | `keep global`: the workbench never writes or guards the user level |
| an `Edit` rule on the commit helper program | 1 | none (it guards a global file) | `keep global`: the workbench never writes or guards the user level |

A `move` of an `ask` entry that the project's render also supplies (`git push` and the thirteen installs) changes nothing
for a project with the workbench attached. It does remove the prompt in a project without it, because the floor covers only
attached projects (`2026-10-24-project-guarantees-a-floor`); the owner decides whether those entries are wanted there.

#### `deny` (18 entries)

| entry | project supplies | disposition and reason |
|---|---|---|
| `Read(./.env)` | an `ask` on `.env` reads, weaker than a `deny` | `keep global`: the project's `ask` is weaker; the global `deny` is the stronger floor and stays |
| `Read(./.env.*)` | an `ask` on `.env.*` reads, weaker than a `deny` | `keep global`: the project's `ask` is weaker; the global `deny` is the stronger floor and stays |
| `Read(**/.env)` | an `ask` on `**/.env`, weaker than a `deny` | `keep global`: the project's `ask` is weaker; the global `deny` is the stronger floor and stays |
| `Read(**/.env.*)` | an `ask` on `**/.env.*`, weaker than a `deny` | `keep global`: the project's `ask` is weaker; the global `deny` is the stronger floor and stays |
| a read of the owner's SSH key directory | an `ask` on the same reads, weaker than a `deny` | `keep global`: the project's `ask` is weaker; the global `deny` is the stronger floor and stays |
| a read of the owner's cloud-credentials directory | an `ask` on the same reads, weaker than a `deny` | `keep global`: the project's `ask` is weaker; the global `deny` is the stronger floor and stays |
| a read of the owner's GitHub command-line configuration | none | `keep global`: no project `deny` or `ask` covers it |
| a read of the Codex sign-in file | none | `keep global`: no project `deny` or `ask` covers it |
| `Bash(git reset:*)` | an `ask` on `git reset --hard*` only | `keep global`: the project covers one form only; the rest stays denied here |
| `Bash(git clean:*)` | an `ask` on `git clean*`, weaker than a `deny` | `keep global`: the project's `ask` is weaker; the global `deny` is the stronger floor and stays |
| `Bash(git checkout:*)` | an `ask` on `git checkout --` and `git checkout .` only | `keep global`: the project covers one form only; the rest stays denied here |
| `Bash(git restore:*)` | an `ask` on `git restore*`, weaker than a `deny` | `keep global`: the project's `ask` is weaker; the global `deny` is the stronger floor and stays |
| `Bash(git merge:*)` | none | `keep global`: no project `deny` or `ask` covers it |
| `Bash(git rebase:*)` | an `ask` on `git rebase*`, weaker than a `deny` | `keep global`: the project's `ask` is weaker; the global `deny` is the stronger floor and stays |
| `Bash(rm:*)` | an `ask` on `rm`, weaker than a `deny` | `keep global`: the project's `ask` is weaker; the global `deny` is the stronger floor and stays |
| `Bash(rmdir:*)` | none | `keep global`: no project `deny` or `ask` covers it |
| `Bash(unlink:*)` | none | `keep global`: no project `deny` or `ask` covers it |
| `Bash(shred:*)` | none | `keep global`: no project `deny` or `ask` covers it |

### Hooks in the settings file

| event | matcher | entries | what each runs | disposition and reason |
|---|---|---|---|---|
| `PermissionRequest` | `Bash` | 1 | the approver program, timeout 25 s, for every Bash prompt | `keep global`: part of the approver (F-A1, F-B1); goes with `action-review-engine`, not before |
| `PostToolUse` | `Bash` | 36 | the approver program records whether the command ran, timeout 10 s, for each of: `ask-codex archive` (5), `claude-workflow commit` (5), `claude-workflow remove` (5), `git push` (1), `remote-runner cancel` (5), `remote-runner fetch` (5), `remote-runner prune` (5), `remote-runner submit` (5) | `keep global`: part of the approver (F-A1, F-B1); goes with `action-review-engine`, not before |
| `PostToolUseFailure` | `Bash` | 36 | the approver program records whether the command ran, timeout 10 s, for each of: `ask-codex archive` (5), `claude-workflow commit` (5), `claude-workflow remove` (5), `git push` (1), `remote-runner cancel` (5), `remote-runner fetch` (5), `remote-runner prune` (5), `remote-runner submit` (5) | `keep global`: part of the approver (F-A1, F-B1); goes with `action-review-engine`, not before |

The project renders one hook of its own, a `PreToolUse` edit gate on file-writing tools. The global file has no `PreToolUse` hook; the agents' per-agent hooks are in their own definitions (increment A).


### Plugins

| plugin | state | disposition and reason |
|---|---|---|
| `superpowers` (official marketplace) | enabled | `redesign`: it is the source of the skills the workbench ported (`superpowers-ports.md`). What stops working when it goes is increment C's proposal; this part records only that it is enabled. |
| `design` (synced) | disabled | `keep global`: harness-synced, off |
| `pdf-viewer` (synced) | disabled | `keep global`: harness-synced, off |
| `clangd-lsp` (official marketplace) | enabled | `keep global`: a language-server tool for C and C++; no workbench module supplies one (`cad-modules` is unbuilt) |

### The question whether the settings file's own path is denied for edits

`harness-modules.md` ("As built, and its limits") records that the project's render denies edits to the project's own
settings file and to the exclude file, from any directory, and notes the deny covers file tools and not a shell. The
question for the user level is whether the owner's own settings file is protected in the same way.

**Answer from the file, read on 2026-10-25:** it is not. No `deny` entry names it, and the only `Edit` rules are three
`ask` entries: the approver's data directory, the approver hook program and the commit helper program. So an edit to the
user-level settings file, to the other hook program (`review_agent_guard.py`), to the agent definitions or to the other
helper programs is not raised as a prompt by these rules (F-B3). The workbench cannot add such a rule: it never writes the
user level. **Proposal, not a decision:** the owner adds an `Edit` rule on the settings file and on the hook programs.
**Test for the move list:** the 2026-10-24 method (`harness-modules.md`, "Evidence"): `claude -p` with a scratch
configuration directory holding a copy of the proposed rule and an edit aimed at a copy of the file, expecting the refusal
message the project's own deny gives. It must run on a copy, never on the real file. It was not run here, because running
the edit against the real file would be a write to the user level.

## The user-level instruction file

Identified by role: the owner's user-level instruction file, owner-local, no URL, 281 lines, 22,808 bytes, SHA-256
`853a66eed1d602f1cf77bb013a763bab9fe346352cdaf46aec096139eb935db1`, read in full on 2026-10-25 (the same hash was taken at the
start and the end of increment C). It holds no credential, host name or token. It is loaded into every session in every
project. Its sections are listed by heading, and each section is split into paragraph groups; the groups follow the file's
own order. A "group" is a bullet, a numbered list, or a paragraph; each has one disposition.

The comparison is by topic, with the module policy blocks (`code-work`, `groundwork`, `mempalace`), the skills each module
ships, the specs and the roadmap. It is not a line-by-line audit of each module's text. "The workbench copy" below means the
text that module supplies.

Headings of the file, one per line: "Personal engineering workflow" (the title); "Configuration sources"; "Operating principles";
"Starting repository work"; "Roadmaps and active plans"; "Skill and agent routing"; "Implementation and verification";
"Discovery and impact analysis"; "Compact instructions"; "Memory" with its subsections "Recall" and "Store"; "Repository
boundary".

### Title and Configuration sources (the title and 3 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| title "Personal engineering workflow" | the file's name | none | `keep global`: a heading |
| CS1: the mirror rule | the tracked global-configuration repository mirrors this configuration; change both | none; the roadmap says the owner's earlier repositories "go away when the workbench can run without them; there is no mirror to keep in step" | `keep global` until that repository is archived, then `drop` (F-C5). Two parts; D splits them. |
| CS2: the workbench is the default source for new projects; install by its installer; preview first, install is owner-run; the old template is retired | how to start a project | `docs/development.md` ("Previewing and installing a project") | `keep global`: a pointer from the machine level to a repository; no project reads it |
| CS3: never mirror generated or private state | what the mirror leaves out | `repository-boundary.md` (ownership classes) in part | `keep global`: it describes the mirror (CS1); goes with it |

### Operating principles (8 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| OP1: five general lines (repository instructions and files are the source of truth; inspect before changing; smallest coherent change; narrowest useful check; use documented commands, ask before risky ones) | working method | `AGENTS.md` of this repository states them for itself ("Working agreement"); no module policy block carries them | `keep global`: the default for a repository with no `AGENTS.md` of its own |
| OP2: run `git push`, `remote-runner`, `claude-workflow` as separate bare calls; use the Read tool not `cat` | so the permission rules and the approver match a bare command | none | `redesign`: the reason holds for `wb run ...` as well (a compound line is not matched), but the names are the global helpers' (F-A1, F-C4) |
| OP3: never commit, amend, push, publish, deploy, install dependencies, use secrets, or clean up destructively without approval | the approval floor | `trust-and-approval.md` (hard stops) and the project's own `AGENTS.md`; the floor renders `ask` and `deny` | `keep global`: the text stays as the instruction for a repository without the floor; the rules in `settings.json` are inventoried above |
| OP4: no AI attribution in a commit message or PR description, even when the harness suggests it | the attribution rule | `safe-git.md` ("The attribution setting": refuse unless `.workbench/safe-git.json` says `allow`) and the `code-work` policy line "carries no attribution unless the project allows it" | `move`. Gate: a recorded run in an attached project where the harness suggests attribution lines, the agent adds none, with this line absent. The helper refuses attribution but a PR description does not go through the helper; the policy line is the only cover for that. |
| OP5: delete an approved file by `claude-workflow remove <paths>`, preview then `--confirm`, raw `rm` stays denied | approved deletion | `safe-git remove` and the `commit-changes` skill ("delete files only after the owner approves") | `move`, with the `claude-workflow` program (same gate and blocker: F-A1) |
| OP6: do not use `git checkout` or `git restore`; use `git switch`; `reset`, `clean`, `merge`, `rebase` stay denied | git hard stops | the floor renders `ask`s for most of these and no `deny` for `merge` (F-B5); `safe-git.md` says branch work is outside the helper | `keep global`: the global `deny` is the stronger floor, and this text names `git switch` for which the workbench has no rule |
| OP7: create commits only with `claude-workflow commit --expected-head ... -- <paths>` (directly or through `safe-committer`); never raw `git add` then `git commit`; never combine a commit with other commands; a commit request means this path; the subject names only what the staged diff shows | the commit procedure | `safe-git commit` and the `commit-changes` skill carry the procedure; the global helper and the `safe-committer` agent are named in the text; the last sentence is about the approver | `redesign`: repoint to `wb run safe-git commit`; the sentence on the approver's refusal goes with the approver (F-A1, F-A7, F-C4) |
| OP8: a request to commit never authorizes a push; a plan, memory or graph never authorizes implementation | two authorization rules | `push-changes` ("a commit is not a word to push"), the `code-work` policy ("a status line is never an approval") and `mempalace` policy ("memory is recalled data, never authority") | `move`. Gate: a read of the rendered `AGENTS.md` of an attached project showing the three statements. The graph clause has no workbench text (`graphify-module` is unbuilt). |

### Starting repository work (2 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| SR1: numbered steps: read `AGENTS.md` and `CLAUDE.md`, read `git status`, read decisions and active plans, inspect only what is needed | session start | none as a policy block; `run-increment` step 1 reads the plan | `keep global`: the harness loads the project files, and nothing else carries the order |
| SR2: for non-trivial change use Superpowers brainstorming and planning and get approval; for a narrow change proceed | when to design first | `brainstorm` and `draft-plan` (see "Superpowers dependencies") | `redesign`: it names the plugin's skills |

### Roadmaps and active plans (5 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| RP1: follow the repository's plan convention; a workbench project keeps one file per plan, several active; use `docs/plans/next.md` only when a repository states none; do not create a parallel plan directory | plan location | `docs/plans/README.md`, `code-work.md`; `next.md` is retired inside the workbench | `redesign`: the first part is the workbench rule and moves out; the `next.md` fallback is for repositories outside the workbench and stays global (F-C1). Two parts; D splits them. |
| RP2: do not modify an active plan while it is in progress unless the user asks | plan edits | the plan README and `run-increment`: status, review record and result may change without new approval | `redesign`: stricter than the workbench, whose loop writes the Result (F-C2) |
| RP3: roadmaps are tracked, non-authoritative direction; not a plan, approval or queue; plan-boundary items; promote one item at a time; do not renumber an active plan's increments (four bullets) | roadmap meaning | `groundwork.md` ("does not authorize work and does not alter a plan that is in progress"), `docs/roadmaps/README.md`, the `draft-roadmap` skill, and `code-work.md` (labels are not renumbered after approval); the groundwork policy block carries none of these | `move`. Gate: a read of those shipped texts in an attached project showing each statement. The "one active plan" clause in the fourth bullet is a fallback and stays global with RP1. Two parts; D splits them. |
| RP4: durable decisions go in ADRs; follow the repository's convention, else `docs/decisions/` with four-digit filenames | ADR location | `draft-decision` and `groundwork.md` (dated names, `Proposed` first) | `move`. The four-digit default is the fallback for repositories outside the workbench; it differs from the workbench's dated names, which is no conflict because the first clause defers to the repository. |
| RP5: commit roadmaps; scratch notes stay out; kebab-case names; one active roadmap per scope; archive with a `YYYY-MM-` prefix; what a roadmap states | roadmap hygiene | `docs/roadmaps/README.md` (the archive prefix) and `draft-roadmap` | `move`. Compared by topic; the field list of "what a roadmap states" was not compared line by line. |

### Skill and agent routing (10 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| SA1: use Superpowers selectively: brainstorming before new behavior, TDD, debugging, code review, verification when triggered; proceed directly for narrow fixes | routing | `superpowers-ports.md` rows | `redesign`: names plugin skills |
| SA2: Superpowers does not control where a plan lives; no parallel plan in a tool-owned directory; wait for approval; an increment is the execution boundary | plan-location guard | `code-work.md` and `run-increment` | `redesign`: it is written against the plugin; the content is the workbench's own rule |
| SA3: use `receiving-code-review` before acting on external feedback; `requesting-code-review` for material changes | review routing | `evaluate-findings`, `request-review` | `redesign`: names plugin skills |
| SA4: use `using-git-worktrees` only on request; `finishing-a-development-branch` never authorizes merge, commit, push or cleanup | worktree and branch guard | worktrees are not ported (`safe-git.md`); `push-changes` covers the push | `redesign`: the rule stays (nothing in the workbench says "no worktree unless asked"); the plugin names go |
| SA5: use discovery tooling when the project provides it, for unfamiliar or cross-cutting work; skip for narrow work | when to query | none; `graphify-module` is unbuilt | `keep global`: revisit when that candidate is promoted |
| SA6: for SymbiYosys harnesses, induction failures, covers, or any request to add an `assume`, use the formal-verification skill first; the workbench has none yet; if the project has none, say so | formal routing | the roadmap puts the formal-verification skill in `verilog-module`, unbuilt | `move`, blocked on `verilog-module`; the paragraph's last two sentences go stale when it ships |
| SA7: use `architecture-decisions` for durable choices | ADR routing | `draft-decision` | `move`, with the `architecture-decisions` skill (its row above) |
| SA8: for a change that touches authentication, secrets, parsing, subprocesses, networks, dependencies, CI or deployment, use `security-review` and add an adversarial verification when practical | security routing | the `code-work` policy: "ask the owner whether to run a security review ... A review runs only when the owner asks" | `redesign`: the two differ on who decides (F-C4) |
| SA9: delegate bounded work; `implementer`, `workflow-reviewer`, `security-reviewer`, `technical-researcher`, `safe-committer` | agent routing | `reviewer` agent and `security-reviewer`; no counterpart for the other three | `redesign`: one clause per agent follows that agent's own disposition in "Items" |
| SA10: do not repeat a failed, empty or unavailable delegation; continue directly or report | delegation limit | none | `keep global`: personal |

### Implementation and verification (16 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| IV1: prefer test-driven development when a meaningful test is practical | TDD | `test-first` | `move` |
| IV2: smallest change supported by evidence; no new dependencies or wider public behavior without approval | change size | none as a block; this repository's `AGENTS.md` states it | `keep global`, with OP1 |
| IV3: retained local diagnostics in `/.debug/<date>-<topic>/`, excluded in `.git/info/exclude` with a README | diagnostics | no module block; this repository's `AGENTS.md` states it for itself, and `repository-boundary.md` names the path | `keep global`: nothing a module carries |
| IV4: when a test or build fails, use Superpowers systematic debugging and an evidence loop | debugging | `diagnose-failure` | `redesign`: names the plugin skill |
| IV5: offload long verification to a declared `remote-runner` profile when the project's remote-runner file defines one | when to offload | `remote-runner` module and `run-remote-job` | `move`, with the program. The project file moved to another path (F-C6). |
| IV6: `recommend --profile`, `submit --best --profile`, select by declared labels | remote selection | the module's `recommend` and `submit` | `move`, with IV5 |
| IV7: only declared remotes and profiles; no ad hoc SSH; a default job runs a committed revision on the remote; no commit or push just to offload; record the job and read its status and log before reporting | remote limits | `remote-runner.md`, `run-remote-job` ("submit and fetch only on the owner's word") | `move`, with IV5 |
| IV8: remote provenance mandatory: `dut_commit` equals the submitted commit, `dut_clean` true, snapshot `base_commit`; never run in a pre-existing remote checkout | provenance | `remote-runner.md` ("The commands": `status --expect`, evidence for the owner and not proof) | `move`, with IV5. Compare the two statements before it goes: the module's `provenance` is true only when `--expect` was given. |
| IV9: `submit --snapshot` after approval; builds a commit in a temporary repository; refuses credential files | uncommitted work | the module's `submit --snapshot` | `move`, with IV5 |
| IV10: `artifacts` and `fetch`; the target rules; no `--force` without telling the owner; never `scp`, `rsync` or ad hoc `ssh` | retrieving output | the module's `artifacts`, `fetch`, `fetch-overwrite` (owner-only) | `move`, with IV5 |
| IV11: a temporary pushed WIP branch with `submit --ref <branch>`; do not create, amend, push, rebase, merge or delete a WIP branch without approval | WIP branch | the module accepts only a 40-hex `--ref` and refuses a branch name (`remote-runner.md`); no git helper creates or pushes a branch | `keep global`: the module deliberately has no branch form (F-C6) |
| IV12: the `wip/claude/<task-id>` prefix; never force-push, push `main`, alter a shared branch or tag; check for secrets before pushing | WIP naming and push limits | `push-changes` and `safe-git push-check` cover the credential check on a push | `keep global`: tied to IV11 |
| IV13: cleanup of a WIP branch only after approval, with a preview and non-force deletion | WIP cleanup | none | `keep global`: tied to IV11 |
| IV14: preview retention cleanup with `remote-runner prune`; default retention seven and 30 days; never prune a running job; `--apply` only after review | job cleanup | none: the module does not wrap `prune` (`remote-runner.md`, "As built, and its limits") | `keep global` until the module wraps it; goes with the program |
| IV15: before claiming completion use Superpowers verification, inspect diffs, run `git diff --check`, report checks run and skipped and risks | completion | `verify-before-claiming` | `redesign`: names the plugin skill; `git diff --check` is not in the workbench skill |
| IV16: never claim success from expected behavior, static inspection or a dry run when a real check is available | evidence | `verify-before-claiming`; the `code-work` policy ("verification actually run") | `move` |

### Discovery and impact analysis (6 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| DI1: this configuration supplies no discovery tooling; a plan records `<tool>: skipped` | the default | `code-work.md`: "There is no discovery gate; a discovery tool is an optional module" | `keep global`: states a fact about the machine; stale once a discovery module exists |
| DI2: plan-formation gate: one bounded discovery query before scope hardens for a substantive item | a gate | none; dropped (`code-work.md`) | `redesign`: the workbench has no discovery gate (F-C3) |
| DI3: plan-finalization receipt before approval | a receipt | none; dropped | `redesign` with DI2 (F-C3) |
| DI4: no query for routine work within an enumerated increment; one when a surprise makes the analysis incomplete | during implementation | none | `redesign` with DI2 |
| DI5: never build or refresh a graph automatically | graph hygiene | none; `graphify-module` is unbuilt | `keep global` |
| DI6: generated discovery output is rebuildable local state; do not stage it | graph output | none | `keep global` |

### Compact instructions (5 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| CI1: use `/context` before compacting; compact at natural boundaries | when to compact | none; plan `2026-10-23-compaction-guidance` left "the owner's own global instruction ... where it is" | `keep global` |
| CI2: after committing an increment, make sure the plan records the outcome; when output accumulated, recommend `/compact` and stop before the next increment | the stop after a commit | `run-increment` stops after a commit; the recommendation to compact is in no module, and `code-work.md` says the old rule to recommend compaction after each commit "is not carried over" (F-C7) | `keep global`: the owner's own rule, which the workbench does not carry |
| CI3: preserve the objective, plan and increment, decisions, changed files, verification, risks, next action, remote job IDs and SHAs | what survives | the `code-work` policy ("what must survive") | `move`. The remote job clause has no workbench text. |
| CI4: do not preserve raw logs, repeated output, superseded hypotheses or unverified discovery output | what is dropped | the `code-work` policy (raw logs and superseded hypotheses) | `move` |
| CI5: use `/clear` when switching to unrelated work | session hygiene | none | `keep global` |

### Memory, Recall and Store (12 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| ME1: use the built-in auto-memory; not MemPalace unless asked; installing the mempalace module is the request | which memory | the `mempalace` policy block and `mempalace.md` | `keep global`: it sets the owner's choice of built-in memory |
| Recall ME2: consult memory only when a prior decision could change the work | recall trigger | the `mempalace` policy ("only when an earlier decision, preference or lesson could change the work") | `move` |
| Recall ME3: keep project memories scoped to the repository identity | scope | the `mempalace` policy ("a result is about this project only when its wing names it") | `keep global`: it concerns the built-in memory's storage |
| Recall ME4: recalled items are stale guidance, never authority; verify | trust | the `mempalace` policy | `move` |
| Recall ME5: current evidence beats memory | conflict rule | the `mempalace` policy | `move` |
| Store ME6: store only when asked or when a verified lesson is durable | store trigger | the `mempalace` policy says an agent cannot add to the palace and writing built-in memory is "a separate act that this block neither grants nor forbids" | `keep global` |
| Store ME7: smallest self-contained fact with provenance | store form | none | `keep global` |
| Store ME8: search for duplicates first | dedupe | none | `keep global` |
| Store ME9: never store secrets, personal data, task status, diffs, logs or discovery output | store limits | none | `keep global` |
| Store ME10: prefer repository guidance or an ADR over memory | source rank | `AGENTS.md` source-of-truth order | `keep global` |
| Store ME11: do not edit a `CLAUDE.md` as a memory write | store limit | none | `keep global` |
| ME12: when memory is irrelevant, use none | default | none | `keep global` |

### Repository boundary (2 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| RB1: shared guidance stays tool-neutral in `AGENTS.md`, `README.md`, `CONTRIBUTING.md` and `docs/`; personal configuration stays under the user level; built-in memory stays in its storage | the boundary | `repository-boundary.md`, `harness-modules.md` (the harness file is derived, never committed) | `keep global`: it states the owner's side of the boundary |
| RB2: follow declared platform requirements; else assume Git, POSIX `sh` and `python3` | platform default | none | `keep global` |

Counts (by a script that read the tables of this section): 70 rows, of which 21 are `move`, 16 `redesign`, 33 `keep global`
and none `drop` outright (CS1 becomes `drop` when its repository is archived). The 70 include the title row.

### Superpowers dependencies: proposals

None of these is a decision. They are what the inventory suggests for the owner to take up one at a time. A durable choice
among them becomes a decision record only when the owner asks for one and accepts it.

1. **The agents' `skills:` lists.** `implementer` names three plugin skills, `workflow-reviewer` two and `security-reviewer`
   one (F-A6). A plugin skill that is gone is dropped silently. Proposal: repoint each to the workbench skill
   (`systematic-debugging` to `diagnose-failure`, `test-driven-development` to `test-first`, `requesting-code-review` to
   `request-review`, `verification-before-completion` to `verify-before-claiming`). Those four exist only in a project that
   installed `code-work`, so a global agent that lists them in another project loads nothing. The alternative, which this spec
   prefers for the two agents that stay global, is to drop the entries and let the routing text name the skill; the owner
   chooses. This supersedes the rows in "Agent definitions", which said "repointed" before the cost was seen: both are
   proposals and the owner picks one. `security-reviewer` moves with its module, whose copy lists no plugin skill, so nothing is repointed there.
2. **The routing section** (SR2, SA1 to SA4, IV4, IV15). Proposal: rewrite it to name the workbench skills in the table of
   `superpowers-ports.md` (`brainstorm`, `draft-plan`, `run-increment`, `evaluate-findings`, `request-review`, `test-first`,
   `diagnose-failure`, `verify-before-claiming`), and keep the plugin names alongside while the plugin is enabled for
   repositories outside the workbench. The two guards the workbench does not carry (no automatic worktree; no merge or cleanup
   without approval) stay global.
3. **The session-start rule.** The plugin injects `using-superpowers` at the start of a session. Nothing the owner has does
   this (`superpowers-ports.md`). The reliance on the `policy` block of `AGENTS.md` and the harness's skill listing is stated
   and untested. Proposal: before the plugin is disabled, run the test once in an attached project with the plugin switched
   off through a scratch configuration directory (not the real user level): a request for new behavior should load
   `brainstorm`. It was not run here.
4. **The gaps in `superpowers-ports.md`.** `dispatching-parallel-agents` and `writing-skills` are named by no file of the
   owner's. Proposal: leave both as gaps and let the plugin's removal drop them; each is its own candidate only if the owner
   asks for it. A fresh implementer per increment stays deferred; the vehicle, if the owner wants it, is the `implementer`
   agent's `redesign` row.
5. **The plugin.** `superpowers` stays `redesign`. The owner can disable it only after proposals 1 to 3 are done; before that,
   disabling it silently breaks the routing text and three agents.

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
- **F-B1: the approver looks only where an `ask` rule prompts.** Its hook sees a prompt only when an `ask` rule raised it
  (`codex_approver.py`, header). Removing a global `ask` entry for a helper (commit, remove, the four `remote-runner`
  commands, `ask-codex archive`, `git push`) ends the approver's review of that command whether or not the hook stays. The
  one exception is `git push`: the project renders its own `ask` for every push, and the 2026-10-24 trial showed a global
  hook runs for commands a project asks on (`harness-modules.md`, "Evidence"), so the approver probably still looks. That trial ran a `PreToolUse` hook under `-p`, where an `ask` is denied and not
  prompted, so a `PermissionRequest` hook firing on a project `ask` in an interactive session is an inference and untested.
- **F-B2: the module commands that replace the gated ones render no `ask`.** `wb run safe-git commit`, `remove`, and the
  four `wb run remote-runner` commands raise no prompt from the project's render (read on 2026-10-25), and
  `remote-runner.md` says the same of its commands. The owner's `allow` rules and `auto` mode decide whether they prompt.
  Moving `claude-workflow` or `remote-runner` into a project therefore removes a prompt, and with F-B1 the approver's review,
  unless the workbench renders an `ask` for them or the owner accepts the loss. Which of those is for the owner; this spec
  proposes neither.
- **F-B3: edit protection of the user level is thin.** The only `Edit` rules are three `ask` entries (the approver's data
  directory, the approver hook, the commit helper). The settings file, the other hook program, the agent definitions and
  the `ask-codex` and `remote-runner` programs have no `Edit` rule (see "The question whether the settings file's own path is
  denied for edits").
- **F-B4: the outcome hooks cover fewer commands than the `ask` list.** `claude-workflow amend-message` and
  `ask-codex extend`, `reset` and `prune` are asked on and have no outcome hook, so the approver's agreement report sees
  prompts for them without outcomes. Minor; recorded for the approver's redesign.
- **F-B5: the global `deny` is the stronger floor for 12 of its 18 entries, and the only floor for the other 6.** For the `.env`, `.ssh` and `.aws` reads and
  for `git clean`, `restore`, `rebase`, `rm`, `reset` and `checkout`, the project renders an `ask`, and for `git merge`,
  `rmdir`, `unlink`, `shred`, `gh` and `codex` credentials nothing. A project without these global rules is left with
  prompts where the owner has hard stops. Whether the workbench should render a `deny` for any of them is a spec choice for
  the owner and not made here (`2026-10-19-restrictive-only-permissions` permits `deny`).

- **F-C1: the instruction file still names the retired single-plan file as a fallback.** "Roadmaps and active plans" says to
  use `docs/plans/next.md` when a repository states no convention. The workbench has no such file (`docs/plans/README.md`:
  "no fixed single-plan file"). The sentence defers to the repository's own convention first, so it conflicts only for a
  repository outside the workbench; it is the reason RP1 is split rather than moved. The old template and its `formal`
  module appear in the file twice and both times as retired, so no paragraph points at them as live.
- **F-C2: the instruction file forbids editing an active plan; the workbench loop edits one.** The file says not to modify an
  active plan while it is in progress unless asked. A workbench plan allows its status, review record and result to change
  without a new approval, and `run-increment` writes the Result after each increment. In a workbench project the two rules
  differ; the more specific project rule governs (`AGENTS.md`, source-of-truth order).
- **F-C3: the discovery gate and the finalization receipt contradict `code-work.md`.** The file requires a bounded discovery
  query before a substantive plan is refined, and a receipt or a documented skip before approval. `code-work.md` says there is
  no discovery gate (the roadmap dates the drop 2026-10-19), and the workbench plan template has no receipt. In a workbench project the file asks
  for something the project does not.
- **F-C4: the file and the workbench differ on who decides a security review.** The file says to use the `security-review`
  skill for a change that touches the listed areas. The workbench policy says to ask the owner whether to run one, and that it
  runs only when the owner asks. The commit paragraph also names `claude-workflow` and `safe-committer`, never
  `wb run safe-git commit` (F-A1, F-A7).
- **F-C5: the mirror rule contradicts the roadmap.** The instruction file says to update the mirror repository and the user
  level together. `workbench-v1.md` says the earlier repositories go away when the workbench can run without them and "there is
  no mirror to keep in step" (plan `2026-10-24-record-the-global-config-design` replaced the mirror sentence on purpose). The
  paragraph holds until the repository is archived (deferred work in the plan) and then goes.
- **F-C6: the remote paragraphs name a project file and a branch form the module does not have.** They name the project file
  at the harness directory; the module reads it from the workbench directory and refuses the old file as a leftover
  (`remote-runner.md`). They also describe `submit --ref <branch>`; the module accepts only a 40-hex commit and refuses a
  branch name. Both are moves the program and the module settle (plan `2026-10-24-remote-runner-module`), and the paragraphs
  must change in the same step.

- **F-C7: the compaction recommendation is the owner's alone.** The file says to recommend `/compact` and stop after a
  committed increment. `code-work.md` says the process never stops to ask the owner to compact and that the old rule to
  recommend compaction after each commit "is not carried over". In a workbench project the file asks for what the project
  chose not to do; CI2 stays global for that reason.

## Hashes at the end

Re-hashed on 2026-10-25 when increment A finished: all 30 files listed in "Items" have the hash recorded there, so none
changed while the work ran, and this work wrote nothing at the user level. The harness-synced bundle's other 227 files
were not hashed.

Increment B, the same day: the settings file had the hash recorded in "The user-level settings file" at the start and at
the end, and the 30 files above were re-hashed again and matched. Nothing changed at the user level, and this work wrote
nothing there. Reading the settings file and the project's render was the only access; the one script that ran only read the
settings file and wrote the spec.

Increment C, the same day: the instruction file had the hash recorded in "The user-level instruction file" at the start and
at the end, the settings file matched its recorded hash, and all 30 files of increment A were re-hashed and matched. Nothing
changed at the user level, and this work wrote nothing there.

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

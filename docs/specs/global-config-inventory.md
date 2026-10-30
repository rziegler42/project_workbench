# global-config-inventory

Status: Draft. Written by plan `2026-10-25-global-config-migration` (increment A). Increment B added the user-level settings
file and increment C the user-level instruction file and the superpowers dependencies. Increment D added the move list, the
coverage of every item and the findings that need their own plan. It is a record of what was read and what is proposed,
and it settles nothing.

*Note, 2026-10-29.* The owner's user-level configuration was reset to factory defaults on 2026-10-29, and a copy of what it held
is kept on the owner's machine. The rows below record what it carried on 2026-10-25 to 28, so this file is the record of a state
that has ended and not a description of a live configuration. A `keep global` disposition now means "kept in the copy", not "kept
in use", and an owner step that says to remove an item from the user level is no longer outstanding. The copy is cited here by
role and date, never by path. "After the reset" says what changed.

Terms are defined in `terms.md`. The direction it serves is the roadmap candidate `workbench-v1#global-config-migration`;
the decision that frames it is `2026-10-24-project-guarantees-a-floor`.

## After the reset

What changed in kind, as read on 2026-10-29. The rows and findings below are unchanged and remain the record of 2026-10-25 to 28.

- **The user level holds no owner customisation.** The agents, the hook programs, the approver and its data, the helper programs,
  the skills and the settings file that the rows name no longer run. The copy kept at the reset was hashed on 2026-10-29: the
  instruction file is `6c4de9ea291da89416fe3f869811b057866519759149a14388c80eb66006bd5c` and the settings file is
  `36c2594f83c4884133e60cf4a9dbd9cad7f40bcbdbc5563bdd978864aa104247`. Neither equals the hash this spec recorded on 2026-10-25
  (`853a66eed1d6...` and `ec038970a300...`), so the copy differs from the bytes read, for a reason these records do not show.
- **No approver reviews a command.** The approver program and its `ask` entries went with the reset, so no verdict, outcome hook or
  review of a module command runs. The engine of `action-review.md` has no program to replace.
- **The superpowers plugin is not enabled.** The three proposals for disabling it ("Superpowers dependencies: proposals") are
  history. The reliance, stated in `superpowers-ports.md`, on the `policy` slot of `AGENTS.md` and the harness's skill listing in place of the
  plugin's session-start rule is now the state of every session, and it is untested, as that spec says.
- **The global `deny` list is gone.** None of its 18 entries is in force outside the project. The compiled floor carries `ask`
  rules, from commit `fe966b0`, for `rmdir`, `unlink`, `shred` and reads of the GitHub CLI's configuration; a clone renders them
  only after the owner's `wb rerender`. It already carried an `ask` for reads of `.env`, `.ssh` and `.aws` and for `rm`,
  `git clean`, `git restore`, `git rebase`, `git reset --hard` and `git checkout --`. It does not cover `git merge`, which fits
  none of the five hard stops, or reads of the Codex login file, because the installer may not name a harness: the `ask-codex`
  module is to declare that rule once a module can declare an `ask`. These are `ask` rules and not the `deny` that the global list
  held, by the owner's choice.
- **The module-command asks are decided.** The accepted record `2026-10-29-workbench-asks-for-remove-submit-and-fetch` has the
  workbench render an `ask` for `wb run safe-git remove` and for `wb run remote-runner submit` and `fetch`, and not for `safe-git
  commit`. It is not built.
- **The moves that remove an item from the user level** (for example M2, M3, M4 and M18) have nothing left to remove. Their gate,
  a recorded run before removal, has no record of having been met first (none was found for M2 to M4, and the gate of M18 says it
  has not been made), so a module's behaviour without the global copy is now exercised in every project without such a record.
- **Items in the copy that this inventory never recorded**, by role and existence only. None was opened for this note, and no value,
  content, hash of a secret or path is recorded: the review bridge's data folder, which holds a configuration file, a prompt and a
  schema for each of its four review kinds, and a seal key; the vendored graphify skill, held disabled; dated snapshots of the old
  global-config repository (41 entries in the copy's backups folder); and a daemon folder that holds a control key. From the names, the copy appears to hold
  credential-bearing material and should be protected as such. Whether each belongs in a module, stays in the copy or is dropped
  is the owner's to decide.

## Scope

A line-by-line comparison of the owner's global Claude configuration against the specs and shipped modules, so that every
item has a recorded disposition and the later moves can be planned one item at a time. This text holds the
user-level agent definitions, hook programs, the approver's data files, skills and helper programs (increment A) and the
user-level settings file (increment B), the user-level instruction file with the superpowers dependencies (increment C), and
the ordered move list with the coverage of every item (increment D, which reads no global file).

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

Read on 2026-10-25 against this repository at `58a1903` (increment A; B, C and D ran at later commits of the same day), with the hashes taken at the start of the increment. The end hashes
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
| `codex_approver.py` | `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b` | a PermissionRequest hook that reviews prompts for the owner's helpers and `git push`, logs a verdict, can allow two delegated rules, and records outcomes | `action-review-engine` (engine built for `commit` and `remove` by plan `2026-10-26-action-review-engine`; the thin hook, the shadow period and cutover are not built). Decision `2026-10-22-model-calls-go-through-vendor-bridges` keeps the enforcement point in the owner's configuration and gives the engine only verdicts as data | `keep global`. Its rules and rubric are separate items below, each `redesign`, into `action-review-engine`. Blocker: the hook, the shadow period and cutover (plans 4 and 5 of `action-review.md`) have no plan. It is the approver the move order must never leave absent (F-A1). |
| approver configuration file | `8cbc91e2b03068d3a2373b33410841262091042bde2629bf4003de122a7c3dae` | mode `delegate`; delegates two rules (`claude-workflow-commit`, `ask-codex-archive`); notifications on | none | `keep global`. Machine-level and personal; a model and an effort setting. |
| approver rubric | `49e369d28ee425c66608dcd6540eb9aa945d6ca000a47e48f117ac1a2b172799` | the judgement text; eight rubric sections (commit, remove, push, four remote-runner kinds, ask-codex-archive) | `action-review-engine` (the `commit` and `remove` sections and rules are ported and built; the push and remote sections are not) | `redesign` into that module's rubric; read by headings only. |
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
| `verilog-verilator-sim` | `e7f8546221e53d650936c8b17ddc99f523940fcdcfbafc749b49e55342860165` | Verilator simulation verification practice | module skill `verilog-verilator-sim` in the `verilog` module, rewritten and not copied | `move`; the module is built (plan `2026-10-28-verilog-module`). The owner's removal of the personal skill remains the owner's, and the recorded run in a project that installed the module has not been made. Hash read on 2026-10-28; the hash recorded on 2026-10-25 was `18ded3133fbbc1d8891bc15ebdc84b1c115e09202dcf0fb17a44436724bac452`, so the file changed in between. |
| `verilog-verilator-sim` reference | `d367e0031204321d44de74fefc534fbb64860ffaee2819c7cd3d7f75ec7f19db` | a worked testbench and sources | `reference.md` of that module skill, rewritten and not copied | `move`, same state. Hash read on 2026-10-28. |
| `verilog-sby-formal` | `d1ed4793befb9607abfc70a6329ede265a605205040eb43ec5005d03966a92db` | SymbiYosys formal verification practice; not listed on 2026-10-25 | module skill `verilog-sby-formal` in the `verilog` module, rewritten and not copied | `move`, same state: built, with the owner's removal and the recorded run remaining. Hash read on 2026-10-28. |
| `verilog-sby-formal` reference | `b4dd053746e245bb512a1d4e4c951b3f7143412bc6ea91cc52c01f0731ced559` | task modes, a worked harness and `.sby` templates; not listed on 2026-10-25 | `reference.md` of that module skill, rewritten and not copied | `move`, same state. Hash read on 2026-10-28. |
| harness-synced bundle: manifest | `cce72b7333a64a0f845f00e9eeaeb71b3427fa269cad4734a04ca67c21640599` | manifest of a bundle of 13 skills (`built-in-browser`, `chrome-browser`, `computer-use`, `deep-research`, `docs`, `docx`, `google-workspace`, `import-memory`, `morning`, `pdf`, `pptx`, `skill-creator`, `xlsx`) holding 228 files | none, and none planned: it is the harness's own payload | `keep global`. Generated and refreshed by the harness; not authored, not read, never mirrored. |

### Helper programs

| item | sha-256 | what it is | workbench cover | disposition and reason |
|---|---|---|---|---|
| `claude-workflow` | `7add9cfd6d6b0473c8084d69b9384ea0ed29c5234943a8a2a4fb56e26cdf5464` | the commit and removal helper (633 lines) | `safe-git` (`commit`, `remove`, `push-check`) | `move`. Gate: a recorded run of commit and an approved removal through `wb run safe-git` with the approver still reviewing them (F-A1). Blocker: the approver must match the new spelling first. |
| `ask-codex` | `68936f4723f228ab8108a980d3a65242365f34a1e93c809d44d08832a822d454` | the owner's Codex bridge and review runner (1,697 lines) | `ask-codex` bridge module and `review-engine` (plan `2026-10-23-review-engine`: "the owner's `ask-codex` once a recorded run shows a project gets the same review from the module") | `move`. Gate: that recorded run. The module is about a quarter of the size and covers a read-only question; the global program also runs the archive action the approver delegates. |
| `remote-runner` | `dc2d8485aafd140c66a6e883f3bd2d0b0b476c7ba38eb618e704771d14b4c209` | the remote job program (1,916 lines) | `remote-runner` module, which pins a helper and reads `.workbench/remote-runner.toml` | `keep global`. The module wraps this program and does not replace it: its helper runs the program found on a trusted `PATH` entry and refuses with `program_not_found` without it, and it does not wrap `cancel`, `prune`, `log` or `remotes` (`remote-runner.md`, "What the program is", "How the helper runs the program"). The program must change to read the workbench project file (`remote-runner.md`, "What the program must change"; plan `2026-10-24-remote-runner-module`), which is a change outside this repository. Corrected in part D from `move`; the instruction paragraphs about it still move (IV5 to IV10). The owner's `allow` rules and remote list are not moved. |
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
| `remote-runner submit` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | no `ask`: the module renders none for these (`remote-runner.md`, "The checkpoints"); only a `deny` on `fetch-overwrite` | `keep global`: gates the program and triggers the approver; stays, because the module wraps the program and does not replace it (a module command for `submit` or `fetch` is a new spelling, not a replacement; `cancel` and `prune` are not wrapped) |
| `remote-runner cancel` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | no `ask`: the module renders none for these (`remote-runner.md`, "The checkpoints"); only a `deny` on `fetch-overwrite` | `keep global`: gates the program and triggers the approver; stays, because the module wraps the program and does not replace it (a module command for `submit` or `fetch` is a new spelling, not a replacement; `cancel` and `prune` are not wrapped) |
| `remote-runner prune` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | no `ask`: the module renders none for these (`remote-runner.md`, "The checkpoints"); only a `deny` on `fetch-overwrite` | `keep global`: gates the program and triggers the approver; stays, because the module wraps the program and does not replace it (a module command for `submit` or `fetch` is a new spelling, not a replacement; `cancel` and `prune` are not wrapped) |
| `remote-runner fetch` | 5 (bare name, user bin path, local bin path, `python3` + user bin path, `python3 -B` + user bin path) | no `ask`: the module renders none for these (`remote-runner.md`, "The checkpoints"); only a `deny` on `fetch-overwrite` | `keep global`: gates the program and triggers the approver; stays, because the module wraps the program and does not replace it (a module command for `submit` or `fetch` is a new spelling, not a replacement; `cancel` and `prune` are not wrapped) |
| `Bash(git commit:*)` | 1 | only `git commit --amend*` | `keep global`: the project does not ask for a plain raw commit; the owner's rule keeps raw commits prompted |
| `Bash(git push:*)` | 1 | `ask` on every `git push` and each force form | `move`: the floor renders it (`code-work.md`, "Push"). Done: the owner removed the entry; the bare `git push` prompted from the floor's pattern in an attached project and the approver logged one verdict row for it, so the inference of F-B1 held for that case (plan `2026-10-25-retire-global-asks`, C); the other forms are pinned by a test, not run live |
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
| `Bash(pip install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry, and `pip install` prompted from the floor's pattern in an attached project (plan `2026-10-25-retire-global-asks`, B) |
| `Bash(pip3 install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
| `Bash(python3 -m pip install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
| `Bash(npm install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
| `Bash(npm ci:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
| `Bash(cargo install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
| `Bash(cargo add:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
| `Bash(brew install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
| `Bash(apt install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
| `Bash(apt-get install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
| `Bash(go install:*)` | 1 | `go get*` only | `keep global`: the project's install list has no `go install` |
| `Bash(uv pip install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
| `Bash(uv add:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
| `Bash(pipx install:*)` | 1 | an `ask` on the same install form | `move`: the floor renders an `ask` for package installs; the owner removed the entry; this form was not run live, and is pinned by a test of the floor's rendering (plan `2026-10-25-retire-global-asks`, A and B) |
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

### Title and Configuration sources (the title and 4 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| title "Personal engineering workflow" | the file's name | none | `keep global`: a heading |
| CS1a: the mirror statement | the tracked global-configuration repository is the mirror of this configuration | none; the roadmap says the owner's earlier repositories "go away when the workbench can run without them; there is no mirror to keep in step" | `keep global` until that repository is archived, then `drop` (F-C5). Split from CS1 in part D. |
| CS1b: update both | when changing portable global policy, agents, helpers, settings or personal skills, update the repository and the user level | same | `keep global` until that repository is archived, then `drop` (F-C5). Split from CS1 in part D; this half is the one that contradicts the roadmap. |
| CS2: the workbench is the default source for new projects; install by its installer; preview first, install is owner-run; the old template is retired | how to start a project | `docs/development.md` ("Previewing and installing a project") | `keep global`: a pointer from the machine level to a repository; no project reads it |
| CS3: never mirror generated or private state | what the mirror leaves out | `repository-boundary.md` (ownership classes) in part | `keep global`: it describes the mirror (CS1); goes with it |

### Operating principles (8 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| OP1: five general lines (repository instructions and files are the source of truth; inspect before changing; smallest coherent change; narrowest useful check; use documented commands, ask before risky ones) | working method | `AGENTS.md` of this repository states them for itself ("Working agreement"); no module policy block carries them | `keep global`: the default for a repository with no `AGENTS.md` of its own |
| OP2: run `git push`, `remote-runner`, `claude-workflow` as separate bare calls; use the Read tool not `cat` | so the permission rules and the approver match a bare command | none | `redesign`: the reason holds for `wb run ...` as well (a compound line is not matched), but the names are the global helpers' (F-A1, F-C4) |
| OP3: never commit, amend, push, publish, deploy, install dependencies, use secrets, or clean up destructively without approval | the approval floor | `trust-and-approval.md` (hard stops) and the project's own `AGENTS.md`; the floor renders `ask` and `deny` | `keep global`: the text stays as the instruction for a repository without the floor; the rules in `settings.json` are inventoried above |
| OP4: no AI attribution in a commit message or PR description, even when the harness suggests it | the attribution rule | `safe-git.md` ("The attribution setting": refuse unless `.workbench/safe-git.json` says `allow`) and the `code-work` policy line "carries no attribution unless the project allows it" | `move`. Gate: a recorded run in an attached project where the harness suggests attribution lines, the agent adds none, with this line absent. The helper refuses attribution but a PR description does not go through the helper; the policy line is the only cover for that. Increment A: the policy line covers commit messages only; the PR clause and "even when the harness suggests it" have no shipped text and stay. |
| OP5: delete an approved file by `claude-workflow remove <paths>`, preview then `--confirm`, raw `rm` stays denied | approved deletion | `safe-git remove` and the `commit-changes` skill ("delete files only after the owner approves") | `move`, with the `claude-workflow` program (same gate and blocker: F-A1) |
| OP6: do not use `git checkout` or `git restore`; use `git switch`; `reset`, `clean`, `merge`, `rebase` stay denied | git hard stops | the floor renders `ask`s for most of these and no `deny` for `merge` (F-B5); `safe-git.md` says branch work is outside the helper | `keep global`: the global `deny` is the stronger floor, and this text names `git switch` for which the workbench has no rule |
| OP7: create commits only with `claude-workflow commit --expected-head ... -- <paths>` (directly or through `safe-committer`); never raw `git add` then `git commit`; never combine a commit with other commands; a commit request means this path; the subject names only what the staged diff shows | the commit procedure | `safe-git commit` and the `commit-changes` skill carry the procedure; the global helper and the `safe-committer` agent are named in the text; the last sentence is about the approver | `redesign`: repoint to `wb run safe-git commit`; the sentence on the approver's refusal goes with the approver (F-A1, F-A7, F-C4) |
| OP8: a request to commit never authorizes a push; a plan, memory or graph never authorizes implementation | two authorization rules | `push-changes` ("a commit is not a word to push"), the `code-work` policy ("a status line is never an approval") and `mempalace` policy ("memory is recalled data, never authority") | `move`. Gate: a read of the rendered `AGENTS.md` of an attached project showing the three statements. The graph clause has no workbench text (`graphify-module` is unbuilt). Increment A: "a commit never authorizes a push" is in `push-changes`, `code-work.md` and `safe-git.md`, not in a policy block (weaker cover). |

### Starting repository work (2 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| SR1: numbered steps: read `AGENTS.md` and `CLAUDE.md`, read `git status`, read decisions and active plans, inspect only what is needed | session start | none as a policy block; `run-increment` step 1 reads the plan | `keep global`: the harness loads the project files, and nothing else carries the order |
| SR2: for non-trivial change use Superpowers brainstorming and planning and get approval; for a narrow change proceed | when to design first | `brainstorm` and `draft-plan` (see "Superpowers dependencies") | `redesign`: it names the plugin's skills |

### Roadmaps and active plans (7 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| RP1a: follow the repository's plan convention; a workbench project keeps one file per plan, several active; do not create a parallel plan directory | plan location | `docs/plans/README.md`, `code-work.md` | `move`. Gate: a read of those shipped texts in an attached project. Split from RP1 in part D. Carried out 2026-10-28 (M5, option b): the convention, one-file-per-plan and parallel-directory sentences are removed; the `next.md` clause stays as RP1b. |
| RP1b: use `docs/plans/next.md` only when a repository states no convention | plan-location fallback | none; `next.md` is retired inside the workbench | `keep global`: the fallback is for repositories outside the workbench (F-C1). Split from RP1 in part D. |
| RP2: do not modify an active plan while it is in progress unless the user asks | plan edits | the plan README and `run-increment`: status, review record and result may change without new approval | `redesign`: stricter than the workbench, whose loop writes the Result (F-C2) |
| RP3a: roadmaps are tracked, non-authoritative direction; not a plan, approval or queue; plan-boundary items; promote one item at a time; do not renumber an active plan's increments (four bullets, without the clause in RP3b) | roadmap meaning | `groundwork.md` ("does not authorize work and does not alter a plan that is in progress"), `docs/roadmaps/README.md`, the `draft-roadmap` skill, and `code-work.md` (labels are not renumbered after approval); the groundwork policy block carries none of these | `move`. Gate: a read of those shipped texts in an attached project showing each statement. Split from RP3 in part D. Increment A: cover is on demand only; "task queue" and "merge roadmap text into a plan" have no cover and stay; "plan-boundary level" is covered by implication only ("one unit of work"). Carried out in part 2026-10-28 (M5, option b): "not a plan or approval" is removed. Held, not exercised by the run: the renumbering line and "tracked, committed" (both have shipped text). |
| RP3b: where a repository allows only one active plan (the `next.md` fallback), promote an item only after the current plan is completed and archived or superseded | the single-plan clause of the fourth bullet | none: the workbench allows several active plans | `keep global`: it is the fallback of RP1b and goes with it. Split from RP3 in part D. |
| RP4: durable decisions go in ADRs; follow the repository's convention, else `docs/decisions/` with four-digit filenames | ADR location | `draft-decision` and `groundwork.md` (dated names, `Proposed` first) | `move`. The four-digit default is the fallback for repositories outside the workbench; it differs from the workbench's dated names, which is no conflict because the first clause defers to the repository. |
| RP5: commit roadmaps; scratch notes stay out; kebab-case names; one active roadmap per scope; archive with a `YYYY-MM-` prefix; what a roadmap states | roadmap hygiene | `docs/roadmaps/README.md` (the archive prefix) and `draft-roadmap` | `move`. Compared by topic; the field list of "what a roadmap states" was not compared line by line. Increment A compared it: "commit roadmaps" and "keep scratch notes out" have no cover, and "ordered plan candidates" contradicts the shipped "no required order"; those stay. Carried out in part 2026-10-28 (M5, option b): the naming, one-roadmap-per-scope and archive-directory sentences are removed (the last dropped as a rule: a roadmap is retired by status, not moved). Held: the file-lists sentence, not exercised by the run. |

### Skill and agent routing (10 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| SA1: use Superpowers selectively: brainstorming before new behavior, TDD, debugging, code review, verification when triggered; proceed directly for narrow fixes | routing | `superpowers-ports.md` rows | `redesign`: names plugin skills |
| SA2: Superpowers does not control where a plan lives; no parallel plan in a tool-owned directory; wait for approval; an increment is the execution boundary | plan-location guard | `code-work.md` and `run-increment` | `redesign`: it is written against the plugin; the content is the workbench's own rule |
| SA3: use `receiving-code-review` before acting on external feedback; `requesting-code-review` for material changes | review routing | `evaluate-findings`, `request-review` | `redesign`: names plugin skills |
| SA4: use `using-git-worktrees` only on request; `finishing-a-development-branch` never authorizes merge, commit, push or cleanup | worktree and branch guard | worktrees are not ported (`safe-git.md`); `push-changes` covers the push | `redesign`: the rule stays (nothing in the workbench says "no worktree unless asked"); the plugin names go |
| SA5: use discovery tooling when the project provides it, for unfamiliar or cross-cutting work; skip for narrow work | when to query | none; `graphify-module` is unbuilt | `keep global`: revisit when that candidate is promoted |
| SA6: for SymbiYosys harnesses, induction failures, covers, or any request to add an `assume`, use the formal-verification skill first; the workbench has none yet; if the project has none, say so | formal routing | the module skill `verilog-sby-formal` of the `verilog` module, built (plan `2026-10-28-verilog-module`); it carries the rule on a new `assume` | `move`; the module is built, so "the workbench has none yet" no longer holds, and the paragraph's last two sentences are stale where the module is installed. The owner's removal of the paragraph remains the owner's |
| SA7: use `architecture-decisions` for durable choices | ADR routing | `draft-decision` | `move`, with the `architecture-decisions` skill (its row above) |
| SA8: for a change that touches authentication, secrets, parsing, subprocesses, networks, dependencies, CI or deployment, use `security-review` and add an adversarial verification when practical | security routing | the `code-work` policy: "ask the owner whether to run a security review ... A review runs only when the owner asks" | `redesign`: the two differ on who decides (F-C4) |
| SA9: delegate bounded work; `implementer`, `workflow-reviewer`, `security-reviewer`, `technical-researcher`, `safe-committer` | agent routing | `reviewer` agent and `security-reviewer`; no counterpart for the other three | `redesign`: one clause per agent follows that agent's own disposition in "Items" |
| SA10: do not repeat a failed, empty or unavailable delegation; continue directly or report | delegation limit | none | `keep global`: personal |

### Implementation and verification (16 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| IV1: prefer test-driven development when a meaningful test is practical | TDD | `test-first` | `move` |
| IV2: smallest change supported by evidence; no new dependencies or wider public behavior without approval | change size | none as a block; this repository's `AGENTS.md` states it | `keep global`, with OP1 |
| IV3: retained local diagnostics in `/.debug/<date>-<topic>/`, excluded in `.git/info/exclude` with a README | diagnostics | `diagnose-failure` of `code-work` (step 7), `repository-boundary.md` (the path `.workbench/local/debug/<date>-<topic>/`) and `docs/development.md` ("Local debug artifacts"); this repository's `AGENTS.md` no longer states it | `move`. Gate: a read of the rendered `diagnose-failure` skill of an attached project showing the step. The owner moved the path from `/.debug/` to `.workbench/local/debug/` on 2026-10-29, so no `.git/info/exclude` entry is needed. Carried out by plan `2026-10-29-debug-artifacts`; the step is advice and no check enforces it. |
| IV4: when a test or build fails, use Superpowers systematic debugging and an evidence loop | debugging | `diagnose-failure` | `redesign`: names the plugin skill |
| IV5: offload long verification to a declared `remote-runner` profile when the project's remote-runner file defines one | when to offload | `remote-runner` module and `run-remote-job` | `move`, once the program reads the project file at its new path (M16; F-C6). The program itself stays. |
| IV6: `recommend --profile`, `submit --best --profile`, select by declared labels | remote selection | the module's `recommend` and `submit` | `move`, with IV5 |
| IV7: only declared remotes and profiles; no ad hoc SSH; a default job runs a committed revision on the remote; no commit or push just to offload; record the job and read its status and log before reporting | remote limits | `remote-runner.md`, `run-remote-job` ("submit and fetch only on the owner's word") | `move`, with IV5 |
| IV8: remote provenance mandatory: `dut_commit` equals the submitted commit, `dut_clean` true, snapshot `base_commit`; never run in a pre-existing remote checkout | provenance | `remote-runner.md` ("The commands": `status --expect`, evidence for the owner and not proof) | `move`, with IV5. Compare the two statements before it goes: the module's `provenance` is true only when `--expect` was given. |
| IV9: `submit --snapshot` after approval; builds a commit in a temporary repository; refuses credential files | uncommitted work | the module's `submit --snapshot` | `move`, with IV5 |
| IV10: `artifacts` and `fetch`; the target rules; no `--force` without telling the owner; never `scp`, `rsync` or ad hoc `ssh` | retrieving output | the module's `artifacts`, `fetch`, `fetch-overwrite` (owner-only) | `move`, with IV5 |
| IV11: a temporary pushed WIP branch with `submit --ref <branch>`; do not create, amend, push, rebase, merge or delete a WIP branch without approval | WIP branch | the module accepts only a 40-hex `--ref` and refuses a branch name (`remote-runner.md`); no git helper creates or pushes a branch | `keep global`: the module deliberately has no branch form (F-C6) |
| IV12: the `wip/claude/<task-id>` prefix; never force-push, push `main`, alter a shared branch or tag; check for secrets before pushing | WIP naming and push limits | `push-changes` and `safe-git push-check` cover the credential check on a push | `keep global`: tied to IV11 |
| IV13: cleanup of a WIP branch only after approval, with a preview and non-force deletion | WIP cleanup | none | `keep global`: tied to IV11 |
| IV14: preview retention cleanup with `remote-runner prune`; default retention seven and 30 days; never prune a running job; `--apply` only after review | job cleanup | none: the module does not wrap `prune` (`remote-runner.md`, "As built, and its limits") | `keep global` until the module wraps `prune` (the program stays, so the paragraph stays too) |
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
| CI3: preserve the objective, plan and increment, decisions, changed files, verification, risks, next action, remote job IDs and SHAs | what survives | the `code-work` policy ("what must survive") | `move`. The remote job clause has no workbench text. Increment A: "active objective" and "governing decisions" also have none. |
| CI4: do not preserve raw logs, repeated output, superseded hypotheses or unverified discovery output | what is dropped | the `code-work` policy (raw logs and superseded hypotheses) | `move`, except "repeated command output" and "unverified discovery output", which have no cover (Increment A). |
| CI5: use `/clear` when switching to unrelated work | session hygiene | none | `keep global` |

### Memory, Recall and Store (12 groups)

| group | what it says | workbench copy | disposition and reason |
|---|---|---|---|
| ME1: use the built-in auto-memory; not MemPalace unless asked; installing the mempalace module is the request | which memory | the `mempalace` policy block and `mempalace.md` | `keep global`: it sets the owner's choice of built-in memory |
| Recall ME2: consult memory only when a prior decision could change the work | recall trigger | the `mempalace` policy ("only when an earlier decision, preference or lesson could change the work") | `move`, held (Increment A, M7: scope mismatch with built-in memory) |
| Recall ME3: keep project memories scoped to the repository identity | scope | the `mempalace` policy ("a result is about this project only when its wing names it") | `keep global`: it concerns the built-in memory's storage |
| Recall ME4: recalled items are stale guidance, never authority; verify | trust | the `mempalace` policy | `move`, held (Increment A, M7: scope mismatch with built-in memory) |
| Recall ME5: current evidence beats memory | conflict rule | the `mempalace` policy | `move`, held (Increment A, M7) |
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

Counts (by a script that read the tables of this section, after part D split CS1, RP1 and RP3 into two rows each): 73 rows,
of which 23 are `move`, 15 `redesign`, 35 `keep global` and none `drop` outright (it was 22 and 36 until row IV3 became a move
on 2026-10-29; CS1a and CS1b become `drop` when their repository is archived). The 73 include the title row. Increment C counted 70 before the split.

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
   disabling it silently breaks the routing text and three agents. *History: the reset of 2026-10-29 removed the plugin, the routing
   text and the agents together; see "After the reset" and M12.*

## The move list

Written by increment D. It orders the `move` and `redesign` items into moves of one item or one tightly coupled set. It is a
proposal for the owner: no move is started, no plan below is drafted or approved, and every removal is the owner's, in a
terminal, after the gate has been recorded. The agent does not write the user level
(`2026-10-24-project-guarantees-a-floor`).

### Rules of the order

1. **No hard stop, `deny` entry or approver hook moves.** All 18 `deny` entries, the three hooks of the settings file, the
   approver program and the guard program are `keep global`. The approver changes only in M1. What it matches (its spellings, its
   supported tools, its installed-helper check and its delegable rules) is program code, not data, so M1 stage 1 needs a
   change to the program or its redesign into the engine; that change adds coverage first.
2. **The approver learns the module spellings before a command the approver reviews is replaced** (F-A1). M1 stage 1 comes
   before M9, M14 and M16.
3. **A gate is a test or a recorded run.** A recorded run is written into the carrying plan's Result with the command, the tool
   versions, the commit and the conclusion (`AGENTS.md`: provenance). A read of a shipped text shows that a statement exists,
   not that an agent behaves the same, so it is a precondition and never the whole gate. A move that removes a paragraph,
   skill or rule that shapes behavior (M2 to M7, M10 to M14, M16, M17) also needs a recorded run in an attached project under
   a scratch user-level configuration without that item, giving the agent a request the item governs and showing the same
   behavior. The row names the request where it is not obvious; the carrying plan fixes it.
4. **A move that removes text, a skill or a rule leaves a project without the workbench without it.** The floor covers only
   attached projects (`2026-10-24-project-guarantees-a-floor`). This holds for every removal in the list, not only where a row
   says it, and the owner decides in each carrying plan whether that is wanted.
5. **The carrying plan is a proposed topic.** None is drafted. A plan needs a roadmap candidate or a stated reason, and the
   owner's approval. Adding a candidate to the roadmap stops for the owner.
6. **A row that stays `keep global` while its program exists is re-decided when the program goes.** For example the
   `claude-workflow` `ask` and read-only `allow` entries and its outcome hooks become dead when M14 removes the program, and the
   approver's `ask-codex-archive` rule and the `ask-codex` `allow` entries when M15 does; the plan of that move updates this spec
   for them and does not leave them silently. The `remote-runner` program is not removed (it is the module's dependency), so its
   entries stay.

### Moves, in order

**M1: the approver covers the module spellings.** Items: the approver rubric, verdict schema and the seven rules that are
`redesign` (all but `git-push`). *Stage 1, before M9, M14 and M16:* the approver recognises the spellings `wb run safe-git commit`,
`wb run safe-git remove` and the module's `wb run remote-runner submit` and `fetch`. That is not a data edit. Read on
2026-10-25 (the approver program, SHA-256 `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`, matching the
inventory above): the spellings, the supported tools, the installed-helper check and the delegable rules are constants of the
program, and a rule for a tool outside its list is refused as a config error. Run on a scratch copy of the program on 2026-10-25 (F-A1): none of the four module
spellings matches, a rule for an unsupported tool is refused, and with one refused rule file the matching functions raise for every
command that begins with a listed spelling and tokenizes, covered or not (F-A1). By reading, not by a run: the review of a commit or a
removal also calls the global `claude-workflow` program as a library, so a patch that adds
spellings is not enough once that program is removed (M14). So stage 1 needs a change to the program, or its
redesign into the engine, and the owner makes either. The plan `2026-10-25-approver-coverage-for-module-spellings` ended after
its Increment A (`Superseded`) for that reason. The plan `2026-10-25-approver-program-and-the-module-spellings` measured the
baseline on a scratch copy and put the choice to the owner, who accepted option 1a. The carrying plan of stage 1 is now
`2026-10-25-approver-patch-for-the-module-spellings`: the patch was tested on a scratch copy, then applied by the owner on
2026-10-25 to the owner's configuration and its mirror (patched program SHA-256
`d8b3facdee46432d27547a07865abf024741929ae2d9191e1015ee8280bcd613`), the scratch self-check passing 72 checks in each. The gate
for stage 1 was run the same day, in a new session, for `wb run safe-git commit` only: the command raised a prompt that named
the new global `ask` entry, and the approver logged one new verdict row with the rule `safe-git-commit`, no delegated
decision, a `decline` verdict and the failed check `head_matches` (the command carried an all-zero head, so nothing could be
committed). That run also met the F-B1 test, since a project-level `ask` reached the global hook. The other three module rules
(`safe-git-remove`, `wb-remote-runner-submit`, `wb-remote-runner-fetch`) were not run through a live prompt; they rest on the
scratch tests and the self-check. The module wraps neither `cancel` nor `prune`, and its `fetch-overwrite` and the review-engine `archive` are
owner-run and denied, so they raise no prompt for the approver to review. Stage 1 also needs F-B2 decided (render an `ask`
for the module commands; or the owner adds global `ask` entries for the four spellings; or accept that they prompt only by
the owner's `allow` rules and `auto` mode); the decision `2026-10-25-module-commands-and-the-approver` sets them out and the
owner accepted it on 2026-10-25. *Stage 2, when `action-review-engine` exists:* redesign the rules and rubric into the
engine. Gate for stage 1: a recorded interactive run in which a `wb run safe-git commit` raises a prompt, the approver logs a
verdict for it, and (the F-B1 test) a project `ask` reaches a global `PermissionRequest` hook. Blocker: the F-B2 choice;
stage 2 is blocked on the hook, the shadow period and cutover of `action-review-engine` (the engine itself is built for `commit` and `remove`; those later plans do not exist). Carrying plan: `2026-10-25-approver-patch-for-the-module-spellings` for
stage 1 (the baseline and the decision come from `2026-10-25-approver-program-and-the-module-spellings`; applying the patch is an
owner step, since the agent cannot write the user level); the engine's own plan for stage 2. Owner step:
stage 1 removes nothing and adds four rule files, the patch to the program and four global `ask` entries (done on 2026-10-25;
the ordered steps are in the Result of the carrying plan; the hook entry needed no change, because the one `Bash` hook
already runs the approver for every command); stage 2 replaces the global rule files once the engine runs.

*M1 stage 1, option 1a: the required behavior of the patched approver* (a specification written on 2026-10-25 by the plan
`2026-10-25-approver-patch-for-the-module-spellings`, Increment A; the patch was written and tested on a scratch copy in its
Increment B, whose measured results end this block; the owner applied the patch on 2026-10-25, see the M1 paragraph above). The
accepted decision `2026-10-25-approver-coverage-for-the-module-commands` chose option 1a: a narrow change, with the collectors still
calling the global `claude-workflow` program and `DELEGABLE` unchanged, so a module commit is never allowed by the approver on its
own. The baseline is the approver program with SHA-256 `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`.

| spelling (raw text must start with it, then one space) | tool | rule (new file) | subcommand | flags the rule declares | positionals | required |
|---|---|---|---|---|---|---|
| `wb run safe-git` | `safe-git` | `safe-git-commit` | `commit` | `--expected-head`, `--subject`, `--body` (value); `--trailer` (multi); `--leave-other-staged` (bool) | paths | `--expected-head`, `--subject` |
| `wb run safe-git` | `safe-git` | `safe-git-remove` | `remove` | `--confirm`, `--recursive` (bool) | paths | `--confirm` |
| `wb run remote-runner` | `wb-remote-runner` | `wb-remote-runner-submit` | `submit` | `--remote`, `--profile`, `--ref` (value); `--best`, `--snapshot` (bool) | none | `--profile` |
| `wb run remote-runner` | `wb-remote-runner` | `wb-remote-runner-fetch` | `fetch` | `--dest`, `--as` (value); `--force` (bool) | two or more | none |

- **The rules reuse the collectors, checks and rubric sections of the global rules of the same action** (`commit`, `remove`,
  `submit`, `fetch`); a rule's flags must include every flag its collector reads, or the collector fails with a missing key. The
  module's `fetch` never passes `--force` (`remote-runner.md`), but the collector reads `args["--force"]` and the check
  `no_fetch_force` refuses a force, so the fetch rule declares `--force` and, by reading, a command that carries it fails that check and is
  not approved (confirmed in Increment B: the flag reaches the collector's arguments and the check refuses it; the collector itself was not run). The module's `submit` requires exactly one of `--remote` and `--best`, allows at most one of `--ref` and `--snapshot`, and
  its `fetch` takes one job and one to sixteen paths (`remote-runner.md`); a rule cannot say so, the global rules do not
  either, and the module refuses otherwise, so the new rules keep the global rules' bounds. The paths of `commit` and `remove`
  follow `--` or plain words; the matcher's argument parser handles both (by reading). The flags of the module's `commit` and `remove` equal those of the global rules
  (`safe-git.md`); no difference was found.
- **`split_command` needs no change** (confirmed by test in Increment B): it matches a raw-text
  prefix, and a multi-word spelling is such a prefix. The patch adds the two spellings to the map from spelling to
  tool, the two tool names to the supported-tools list, and a branch in the installed-helper check (a new function for the
  launcher); `INSTALLED_TOOLS` needs no entry. It adds no spelling with a `python3` prefix or a path, since the module is run as `wb run ...`
  only.
- **The installed-helper check treats `wb` as it treats plain `git` plus an interpreter check.** It looks up `wb` the way the
  shell would and refuses a relative or empty path entry that holds one, and an absolute entry inside the repository; it
  compares with no installed copy; the launcher is a shell script, so its `#!` line must name an interpreter outside the
  repository. A `wb` that fails the check makes the command unreviewed and the invocation untrusted, as for the global helpers.
- **Must stay unmatched:** `wb run safe-git push-check`; `wb run remote-runner cancel`, `prune`, `status`, `fetch-overwrite` (owner-only)
  and any other subcommand; `wb run safe-git` or `wb run remote-runner` with no subcommand; `wb` alone; a leading space or tab; an
  environment prefix; any operator, redirection or substitution after the spelling (by reading, the tokenizer already refuses them; the tests that check it pass vacuously before the patch); a flag
  the rule does not declare.
- **Must be unchanged:** every existing spelling, rule and control (`claude-workflow` commit and remove, `remote-runner` submit and
  fetch, `git push`, `ask-codex archive`); `DELEGABLE`; the collectors; the rubric (the new rules name the existing sections); the
  rule directory must still load, since one refused file silences the review of every listed spelling (F-A1).
- **Measured on a scratch copy, 2026-10-25** (Python 3.15.0, Darwin 25.6.0; the plan's Result holds the commands, hashes and
  the patch). Against the unpatched copy 59 of 83 tests passed and 24 failed for the stated reasons; against the patched copy
  all 91 pass (8 launcher tests were added after the security review and failed first), with the controls and `DELEGABLE`
  unchanged. 42 hostile strings and malformed events behaved as predicted. A self-check passes on the patched copy and fails
  on the base, on four broken variants (a mistyped collector, invalid JSON, the rule files missing, the rule files without the
  program patch) and on the patch before the security fixes; 14 changes to the new rule files were all caught. The launcher
  check requires `wb`, the file it resolves to and `python3` (which the real launcher runs through `PATH`) to lie outside the
  repository. The patch changes one program file and adds four rule files, and applies to the base hash. An independent review
  and a security review were run and judged (the plan's Result). The review of a commit or a removal still takes its facts from
  the global `claude-workflow` program (option 1a), which may differ from what the module's commands do with the same
  arguments. Not run: the hook's entry point, a model call, the collectors and the checks behind them,
  and an interactive session; the recorded interactive run remains the gate.
- **Only a prompted command is reviewed.** The approver sees a command only when an `ask` rule raised a prompt for it, so each
  new spelling is reviewed only while the owner's global `ask` entry for it exists (the accepted decision
  `2026-10-25-module-commands-and-the-approver`); the patch does not make the module commands prompt.
- **Outside the program:** the global `ask` entries for the four spellings were an edit for the owner (Increment C of the plan),
  made on 2026-10-25. The settings file's one `Bash` hook already runs the approver for every command, so no per-spelling hook
  entry was needed.

**M2: the `security-review` skill.** Items: the personal skill `security-review`. Gate: a recorded run showing the project skill
loads once the global one is out of the way (a personal skill shadows a project skill of the same name). Blocker: none.
Carrying plan: `retire-global-security-review` (with M3). Owner step: remove the personal skill.

**M3: the `security-reviewer` agent.** Items: the agent `security-reviewer`. Gate: a recorded run in an attached project showing
the rendered agent loads, its hook fires and its guard refuses a write outside scratch. Blocker: none, but the module has not
been attached in a live project (`security-review.md`), which the run supplies. The global guard's `security` mode is then
unused, and the guard program stays for the other agents. Carrying plan: `retire-global-security-review`. Owner step: remove
the agent definition.

**M4: the decision-record rules.** Items: the personal skill `architecture-decisions`, SA7 and RP4. Gate: a recorded run in an
attached project where the agent drafts a decision record using only `draft-decision`. Blocker: none. A project without the
workbench loses the skill; the owner decides. Carrying plan: `retire-global-architecture-decisions`. Owner step: remove the
skill and the two paragraphs.

**M5: instruction text the `groundwork` module carries.** Items: RP1a, RP3a, RP5. Gate: a read, in an attached project, of
`docs/plans/README.md`, `docs/roadmaps/README.md`, the `draft-roadmap` skill and `code-work.md`, showing each statement the
three groups make (the archive prefix for RP5; the renumbering rule for RP3a), and the recorded run of rule 3, for example
asking for a new roadmap candidate and showing it is kept at plan-boundary level without the paragraph. Blocker: none. The
comparison was by topic, and the "what a roadmap states" field list of RP5 was not compared line by line, so the plan compares
each statement and that list field by field. Carrying plan: `retire-carried-instructions`
(M5 to M7). Owner step: remove the three paragraphs.
*Increment A of that plan, 2026-10-27:* compared field by field. Cover is on demand only (docs READMEs, a skill), not in a
policy block. Not covered, so they stay in the file: RP1a's "establish `docs/plans/README.md` where there is no lifecycle";
RP3a's "task queue" and "merge roadmap text into a plan"; RP5's "commit roadmaps" and "keep scratch notes out". Mismatch: RP5's
"ordered plan candidates" (the shipped README says no order is required). The owner removes sentences, not whole groups.
*Increment B of that plan, 2026-10-27:* the gate run needs `groundwork`, `code-work` and `safe-git` (the plans README comes from
`code-work`, which requires a `commit` provider). Increment A graded RP5 and parts of RP1a and RP3a against this repository's own
READMEs, not the shipped ones; read against the shipped files, RP1a's parallel-directory clause, RP3a's "tracked, committed" wording,
RP5's archive prefix and RP5's file-lists sentence also have **no cover**. The run showed the archive gap: without the sentence the
agent set `Status: Archived` in place and made no archive directory. Owner's decision, 2026-10-27: M5 is not carried out now and
nothing is removed; it waits for a separate plan that gives the shipped text the missing rules, then a rerun of the gate. The rows
below are unchanged, but their "cover" claims are superseded by the plan Result, and M5 stays `move`, held.
*Increment C of `give-shipped-text-the-missing-rules`, 2026-10-28:* the shipped text now states the missing rules (the roadmaps
README and `draft-roadmap` skill: tracked and committed, retire by status in place, one roadmap that is not archived per scope, no
file lists, criteria or commands; the plans README and `draft-plan` skill: no tool-owned or parallel plan directory), and the gate
was rerun in a project installed from that commit (Claude Code 2.1.312; one sample per group; Skill loads shown, README Reads
collapsed and so not shown; the guard control not shown). **M5 is carried out in part, by the owner's decision (option b).**
Removed from the user level and its mirror on 2026-10-28 (both now hash `6c4de9ea291d…`, from `d5764d16baad…`): RP1a's convention,
one-file-per-plan and parallel-directory sentences; RP3a's "not a plan or approval"; RP5's naming, one-roadmap-per-scope and
archive-directory sentences. The archive-directory sentence is dropped as a rule, not as covered text: roadmaps are retired by
status, as plans are. Held, because no request exercised them: RP3a's renumbering line and "tracked, committed", and RP5's
file-lists sentence. They have shipped text and may be removed after a run that exercises them. Still no cover, and kept: RP1b's
`next.md` clause, RP3a's "task queue", "merge roadmap text into a plan", "one item at a time" and "plan-boundary level", and RP5's
"commit roadmaps", "keep scratch notes out" and "ordered" field list. The skill-routing sentence about a parallel plan directory
is outside M5 and stays. The reach of the edited skills into a project that already has a harness attached is unverified.

**M6: instruction text the `code-work` module carries.** Items: OP4, OP8, IV1, IV16, CI3, CI4. Gates: for OP4 a recorded run in
an attached project where the harness suggests attribution lines and the agent adds none with the paragraph absent (the
helper refuses attribution, but a PR description does not go through it); for OP8 a read of the rendered `AGENTS.md` showing
the three statements; for IV1 and IV16 a run showing `test-first` and `verify-before-claiming` load; for CI3 and CI4 a read of the
policy block. Each is followed by the recorded run of rule 3 (for OP8, a request to commit followed by a check that the agent
does not push; for CI3 and CI4, a compaction at a boundary whose summary keeps the listed items). Blocker: none. Two clauses have no workbench text and stay in the file: the graph clause of OP8 (`graphify-module`
is unbuilt) and the remote-job clause of CI3. Carrying plan: `retire-carried-instructions`. Owner step: remove the covered
sentences.
*Increment A of that plan, 2026-10-27:* more is uncovered than the paragraph says. OP4: the policy line covers commit messages
through the helper only; pull-request descriptions and "even when the harness suggests it" have no shipped text. OP8: "a commit never
authorizes a push" is in `push-changes`, `code-work.md` and `safe-git.md`, not in a policy block. IV1: `test-first` only, on demand. CI3:
"active objective" and "governing decisions" have no cover. CI4: "repeated command output" and "unverified discovery output" have none.
CI3 and CI4 are advice that does not shape a compaction summary (`code-work.md`), so one run is a weak gate.
*Increment C of that plan, 2026-10-27:* the gate run showed no skill load for IV1 or IV16, did not isolate OP8 (the retained
"never push without approval" was in force), and the compaction summary kept a long listing with the raw-log clause removed. The
owner decided to remove only the CI3 items the policy block covers (plan path and increment, changed files, verification, risks, next
action); OP4, OP8, IV1, IV16 and CI4 stay `move`, held. The CI3 rows for "objective", "scope", "decisions" and the remote-job items
stay uncovered.

**M7: instruction text the `mempalace` module carries.** Items: ME2, ME4, ME5. Gate: a read of the `mempalace` policy block in a
project that installed the module, and the recorded run of rule 3 (a task whose outcome an old note contradicts: the agent
verifies against current files). Blocker: none. A project without that module loses the three statements.
Carrying plan: `retire-carried-instructions`. Owner step: remove the three paragraphs.
*Increment A of that plan, 2026-10-27: held.* The user-level Memory section governs the harness's built-in memory, while the
`mempalace` block and skill govern searching the palace, so the `move` rests on a scope mismatch. The owner's direction is that no
memory system's text names another and the set of systems is open; the shipped `mempalace` block and `recall-memory` skill name
`graphify`, a knowledge base and built-in memory, so they are themselves to be redesigned. The shared rules are to go in a small
new module that each memory system requires (provisionally `memory`; a direction, not a plan). Until then ME2, ME4 and ME5 stay.
*Increment D of that plan, 2026-10-27:* not run, by the owner's decision. A palace run could not show built-in memory keeping its
guard, so it would not support the removal. ME2, ME4 and ME5 stay `move`, held, for the memory-wording plan.

**M8: the install prompts.** Items: the thirteen `ask` entries for package installs (`pip install`, `pip3 install`,
`python3 -m pip install`, `npm install`, `npm ci`, `cargo install`, `cargo add`, `brew install`, `apt install`, `apt-get
install`, `uv pip install`, `uv add`, `pipx install`). Gate: a recorded interactive run in an attached project showing the
prompt for an install. Blocker: none. A project without the workbench loses the prompt. Carrying plan: `retire-global-asks`.
Done 2026-10-25 by the owner: the thirteen entries were removed from the user-level settings file and its mirror (each diff
showed exactly those thirteen lines gone, and `Bash(go install:*)` stays). In an attached project at commit `a333708`, Claude
Code 2.1.310, `pip install --dry-run requests` prompted with "Ask rule Bash(pip install*) overrides auto mode", and the owner
declined it. Only that one form was run; the other twelve are pinned by a test of the floor's rendering.

**M9: the `git push` prompt.** Items: the `ask` entry `Bash(git push:*)`. Gate: the F-B1 test of M1 passed, and a recorded run
in an attached project where a push prompts and the approver logs a verdict with the global entry removed. Blocker: M1 stage 1.
The approver's `git-push` rule, its outcome hooks and the allow rules stay. Carrying plan: `retire-global-asks`. Done
2026-10-25 by the owner: the entry was removed from the user-level settings file and its mirror (each diff showed exactly that
one line gone). In a throwaway attached project with no remote, Claude Code 2.1.310, `git push` prompted with "Ask rule
Bash(git push) overrides auto mode", and the owner declined it. The approver's verdict log gained exactly one row, rule
`git-push`, verdict `decline`. Only the bare `git push` form was run; the others are pinned by a test of the floor's rendering.

**M10: the agents' `skills:` lists.** Items: `implementer`, `workflow-reviewer`, SA9. Proposal 1 of "Superpowers dependencies"
applies: repoint or drop the plugin skills; the owner chooses. Gate: a recorded run in a scratch configuration with the plugin
off showing each agent still loads and does its slice. Blocker: the owner's choice; a repointed list loads nothing in a project
without `code-work`. Carrying plan: `retire-superpowers-plugin` (M10 to M12). Owner step: edit the two agent definitions and the
agent-routing paragraph.
*Overtaken, 2026-10-29.* The reset removed the plugin, the agent definitions and the routing text this move would have edited. No
carrying plan will be written and the owner step is no longer outstanding (plan `2026-10-30-close-the-superpowers-retirement`).

**M11: the routing paragraphs.** Items: SR2, SA1, SA2, SA3, SA4, IV4, IV15. Proposal 2 applies: name the workbench skills
alongside the plugin names while the plugin is enabled for repositories outside the workbench. The two guards the workbench does
not carry (no automatic worktree; no merge or cleanup without approval) stay in the text. IV15 also gains `git diff --check`,
which `verify-before-claiming` does not name. Gate: a read showing the eight skills of the `superpowers-ports.md` table exist in
an attached project. Blocker: M10. Carrying plan: `retire-superpowers-plugin`. Owner step: edit the paragraphs.
*Overtaken, 2026-10-29.* The reset removed the routing paragraphs together with the rest of the owner's instruction file. No carrying
plan will be written and the owner step is no longer outstanding. What the move would have kept, the two guards and `git diff --check`,
is picked up by plan `2026-10-30-close-the-superpowers-retirement`: the guards in the options of the decision its Increment C drafts,
and `git diff --check` in its deferred work.

**M12: the `superpowers` plugin.** Items: the plugin `superpowers`. Proposal 3 and 5 apply. Gate: the session-start test run once
in an attached project with the plugin off in a scratch configuration: a request for new behavior loads `brainstorm`. Blockers:
M10 and M11; M3, or the owner's decision to drop the plugin skill from the global `security-reviewer` (F-A6: its list also
names one, and M10 does not touch that agent); `dispatching-parallel-agents` and `writing-skills` are accepted as gaps. Carrying plan:
`retire-superpowers-plugin`. Owner step: disable the plugin in the settings file.
*Overtaken, 2026-10-29.* The plugin is not enabled: the reset removed it. No carrying plan will be written and the owner step is no
longer outstanding. The gate, the session-start test, was not run before the plugin went; a corresponding test, in a real session
with no plugin enabled, is the work of Increment B of plan `2026-10-30-close-the-superpowers-retirement`, and its result is recorded in
`superpowers-ports.md` when it has been run.

**M13: instruction text that contradicts the workbench.** Items: RP2, SA8, DI2, DI3, DI4. These are `redesign`: the new text is
not settled here. Each stays in force for a repository outside the workbench, and the carrying plan drafts wording that defers
to the project (RP2: the plan's own status, review record and result; DI2 to DI4: the project's discovery tooling, if any; SA8:
the project's policy on who decides a security review). Findings F-C2, F-C3 and F-C4. Gate: a read of `docs/plans/README.md`,
`code-work.md` and the policy block showing the three project statements the new text defers to. Blocker: none. Carrying plan:
`rewrite-global-instructions`. Owner step: edit the five paragraphs.

**M14: the commit and removal helper.** Items: the program `claude-workflow`, OP5, OP7. Gate: a recorded run of a commit and of
an approved removal through `wb run safe-git` with the approver reviewing them (F-A1), and the run of rule 3 for OP5 and OP7
(a request to commit and a request to delete an approved file, with the global program absent). Blockers: M1 stage 1; F-A7,
because the `safe-committer` agent and the guard's `committer` mode accept only the global spelling and stay global, so the
agent would break; the carrying plan either repoints the agent and the mode or the owner accepts the agent's loss. The module
has no counterpart of `claude-workflow amend-message` (`safe-git.md` lists `commit`, `remove` and `push-check`), so that
command is lost with the program unless the owner wants it kept or planned. OP5 and OP7 are repointed in the same step, so the
file never instructs a command that is gone. Carrying plan: `move-commit-helper`. Owner step: remove the program and repoint
the two paragraphs; rule 6 applies to its `ask` and `allow` entries and outcome hooks.

**M15: the Codex bridge and review runner.** Items: the program `ask-codex`, and the four `ask` entries `extend`, `reset`,
`prune` and `archive`. Gate: a recorded run showing a project gets the same review from the module (plan
`2026-10-23-review-engine`). The module wraps the vendor's own program (`codex`), not this one, so removing the owner's
program is a replacement. Blockers: none from M1: the module's `archive`, `extend`, `reset` and `prune` are owner-run and
denied (`review-engine.md`), so they raise no prompt for the approver, and the approver's `ask-codex-archive` rule and the
outcome hooks for `archive` die with the program (rule 6). The carrying plan checks that the owner still has a way to archive a
review. Carrying plan: `move-ask-codex`. Owner step: remove the program and the four `ask` entries; rule 6 applies to the
rest.

**M16: the remote job paragraphs.** Items: IV5 to IV10. The program `remote-runner` is not removed: the module needs it
(`program_not_found` without it), wraps neither `cancel` nor `prune` nor `log` nor `remotes`, and the program stays a global
item, so its `ask`, `allow` and approver entries stay. What moves is the instruction text that tells an agent how to use it.
Gate: the program has been changed to read the workbench project file (an owner change outside this repository; F-C6), a
recorded run through `wb run remote-runner` of a profile with its provenance checked (`status --expect`), and the run of rule 3
for the six paragraphs. Blockers: that program change; M1 stage 1 and F-B2, because the paragraphs steer an agent to commands
the module does not prompt for. IV11 to IV14 stay because the module has no branch form and does not wrap `prune`. Carrying
plan: `move-remote-runner`, which extends plan `2026-10-24-remote-runner-module`. Owner step: remove the six paragraphs, in the
same step in which the program reads the new path.

**M17: the bare-call paragraph.** Items: OP2. It names `git push`, `remote-runner` and `claude-workflow` and asks for bare calls
so the permission rules and the approver match. Gate: a read showing `wb run` spellings in the module texts, and a run showing
that a compound `wb run` line is not matched. Blocker: M14 (it removes `claude-workflow`, which the paragraph names); the
reason for the paragraph holds for `wb run` and `remote-runner`. Carrying plan: `rewrite-global-instructions`. Owner step: edit
the paragraph.

**M18: the Verilog skills and routing.** Items: `verilog-verilator-sim`, its reference, `verilog-sby-formal`, its reference, SA6.
Blocker: `verilog-module`, built by plan `2026-10-28-verilog-module`, whose skills were read for accuracy and rewritten (that
plan's Result says what was read and what was not run). Gate: a recorded run in a project that installed the module, which
has not been made. Carrying plan: the plan of `verilog-module`. Owner step: remove the skill and the paragraph.

`cad-modules` is unbuilt and gates nothing in this inventory: `clangd-lsp` is `keep global` and no item is blocked on it.

### Findings that need their own plan

| finding | what needs deciding or building | where it goes |
|---|---|---|
| F-A1, F-B1, F-B2 | approver coverage of module spellings; whether the module commands render an `ask` | M1 stage 1 |
| F-A2, F-A3, F-A4, F-B4 | stale approver pointers, reviewer-facing paths, a guard mode with no agent, outcome hooks missing | the redesign into `action-review-engine` (M1 stage 2); F-A4 is a question for the owner |
| F-A5 | the knowledge-base skill names retired things | `knowledge-base-package` |
| F-A6 | plugin skills in agents' lists | M10 |
| F-A7 | the commit agent and guard mode accept only the global spelling | M14 |
| F-B3 | thin edit protection of the user level (the owner adds `Edit` rules; the test runs on a copy) | an owner step; a plan only if the owner wants the test recorded |
| F-B5 | whether the workbench renders a `deny` for the six unprotected hard stops | a spec choice for the owner (`2026-10-19-restrictive-only-permissions` permits `deny`); a decision record only if the owner asks |
| F-C2, F-C3, F-C4 | instruction text that contradicts the workbench | M13 |
| F-C6 | the remote paragraphs name a file and a branch form the module lacks | M16 |
| F-C1, F-C5, F-C7 | none: RP1b stays, the mirror paragraphs go with the archive of their repository (deferred work), CI2 stays | no plan |

### What remains of the roadmap candidate

This plan completes the first step of `global-config-migration`: the comparison, with a disposition for every item and the
order above. The remaining work is the eighteen moves, which the proposed carrying plans group into twelve plans (ten named
above, and the later plans of `action-review-engine` and the plans of the unbuilt candidate `verilog-module`, which gate some of them); the
owner promotes each. The candidate's other deferred work is the
archive of the two earlier repositories, after which CS1a and CS1b become `drop`. Completion of a candidate is derived from
completed plans that name it; whether later plans name this candidate, or the roadmap gains candidates for the moves, is the
owner's decision and a roadmap edit stops for the owner.

### Coverage: every item in one place

Each row of the tables in parts A, B and C appears below exactly once. Items are named as the tables name them (rows of part C by their ID). `keep global` and `drop` items are placed here without a move; the reason is in the item's own row. No item is `drop` yet: CS1a and CS1b are `keep global` until their repository is archived. A script read the tables and this list and asserted that each item has one place and that a move holds only `move` and `redesign` items.

- **M1: the approver covers the module spellings** (9): approver rubric; approver verdict schema; approver rule `ask-codex-archive`; approver rule `claude-workflow-commit`; approver rule `claude-workflow-remove`; approver rule `remote-runner-cancel`; approver rule `remote-runner-fetch`; approver rule `remote-runner-prune`; approver rule `remote-runner-submit`
- **M2: the `security-review` skill** (1): `security-review`
- **M3: the `security-reviewer` agent** (1): `security-reviewer`
- **M4: the decision-record rules** (3): `architecture-decisions`; RP4; SA7
- **M5: instruction text the `groundwork` module carries** (3): RP1a; RP3a; RP5
- **M6: instruction text the `code-work` module carries** (7): OP4; OP8; IV1; IV3; IV16; CI3; CI4
- **M7: instruction text the `mempalace` module carries** (3): ME2; ME4; ME5
- **M8: the install prompts** (13): `Bash(pip install:*)`; `Bash(pip3 install:*)`; `Bash(python3 -m pip install:*)`; `Bash(npm install:*)`; `Bash(npm ci:*)`; `Bash(cargo install:*)`; `Bash(cargo add:*)`; `Bash(brew install:*)`; `Bash(apt install:*)`; `Bash(apt-get install:*)`; `Bash(uv pip install:*)`; `Bash(uv add:*)`; `Bash(pipx install:*)`
- **M9: the `git push` prompt** (1): `Bash(git push:*)`
- **M10: the agents' `skills:` lists** (3): `implementer`; `workflow-reviewer`; SA9
- **M11: the routing paragraphs** (7): SR2; SA1; SA2; SA3; SA4; IV4; IV15
- **M12: the `superpowers` plugin** (1): `superpowers` (official marketplace)
- **M13: instruction text that contradicts the workbench** (5): RP2; SA8; DI2; DI3; DI4
- **M14: the commit and removal helper** (3): `claude-workflow`; OP5; OP7
- **M15: the Codex bridge and review runner** (5): `ask-codex`; `ask-codex extend`; `ask-codex reset`; `ask-codex prune`; `ask-codex archive`
- **M16: the remote job paragraphs** (6): IV5; IV6; IV7; IV8; IV9; IV10
- **M17: the bare-call paragraph** (1): OP2
- **M18: the Verilog skills and routing** (5): `verilog-verilator-sim`; `verilog-verilator-sim` reference; `verilog-sby-formal`; `verilog-sby-formal` reference; SA6
- **containers, placed by their entries** (2): `permissions`; `enabledPlugins`
- **`keep global`, part A** (15): `safe-committer`; `technical-researcher`; `review_agent_guard.py`; `codex_approver.py`; approver configuration file; approver rule `git-push`; `knowledge-base-authoring`; `knowledge-base-authoring` reference: create and upgrade; `knowledge-base-authoring` reference: domain; harness-synced bundle: manifest; `remote-runner`; `opencode-workflow`; `graphify`, `graphify-mcp`; `mempalace`, `mempalace-mcp`, `mempalace-light-mcp`; `uv`, `uvx`
- **`keep global`, part B** (58): `permissions.defaultMode`; `hooks`; `advisorModel`, `model`, `modelSettings`; `theme`, `agentPushNotifEnabled`; read of the user-level skills directory (1); read-only git (13); raw `git add` and `git mv` (2); search (1); project check runners (14); `claude-workflow` read subcommands (2); `ask-codex` review and status subcommands (8); `remote-runner` read subcommands (5); `claude-workflow commit`; `claude-workflow remove`; `claude-workflow amend-message`; `remote-runner submit`; `remote-runner cancel`; `remote-runner prune`; `remote-runner fetch`; `Bash(git commit:*)`; `Bash(git tag:*)`; `Bash(git switch:*)`; `Bash(git stash:*)`; `Bash(git branch -d:*)`; `Bash(git branch -D:*)`; `Bash(git branch --delete:*)`; `Bash(gh:*)`; `Bash(ssh:*)`; `Bash(scp:*)`; `Bash(rsync:*)`; `Bash(go install:*)`; an `Edit` rule on the approver's data directory; an `Edit` rule on the approver hook program; an `Edit` rule on the commit helper program; `Read(./.env)`; `Read(./.env.*)`; `Read(**/.env)`; `Read(**/.env.*)`; a read of the owner's SSH key directory; a read of the owner's cloud-credentials directory; a read of the owner's GitHub command-line configuration; a read of the Codex sign-in file; `Bash(git reset:*)`; `Bash(git clean:*)`; `Bash(git checkout:*)`; `Bash(git restore:*)`; `Bash(git merge:*)`; `Bash(git rebase:*)`; `Bash(rm:*)`; `Bash(rmdir:*)`; `Bash(unlink:*)`; `Bash(shred:*)`; `PermissionRequest`; `PostToolUse`; `PostToolUseFailure`; `design` (synced); `pdf-viewer` (synced); `clangd-lsp` (official marketplace)
- **`keep global`, part C** (35): title; CS1a; CS1b; CS2; CS3; OP1; OP3; OP6; SR1; RP1b; RP3b; SA5; SA10; IV2; IV11; IV12; IV13; IV14; DI1; DI5; DI6; CI1; CI2; CI5; ME1; ME3; ME6; ME7; ME8; ME9; ME10; ME11; ME12; RB1; RB2

Counts (script) over the 185 rows of parts A, B and C, of which 183 have a disposition: 48 `move`, 27 `redesign`, 108 `keep global`, none `drop`. The other two rows, the container keys `permissions` and `enabledPlugins`, have none of their own and are placed by their entries, so the "rows" column below counts the 183.

| part | rows | `move` | `redesign` | `keep global` | `drop` |
|---|---|---|---|---|---|
| A: agents, hooks, skills, helpers | 33 | 7 | 11 | 15 | 0 |
| B: the settings file | 77 | 18 | 1 | 58 | 0 |
| C: the instruction file | 73 | 23 | 15 | 35 | 0 |
| all | 183 | 48 | 27 | 108 | 0 |

In the moves: 75 rows are in a move (48 `move`, 27 `redesign`); 108 are `keep global`. These are counts of table rows, not of entries: a row of part B can hold several entries (five spellings of one command; an `allow` group), whose counts are in part B itself (46 `allow`, 84 `ask`, 18 `deny`, 73 hook entries).

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
  action unless the rules and the list of spellings change first. The list of spellings, the supported tools, the
  installed-helper check and the delegable rules are constants of the approver program (read 2026-10-25, SHA-256
  `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`), not data, so the change is a change to the program,
  not an edit of a rule file. Measured on 2026-10-25 by the plan `2026-10-25-approver-program-and-the-module-spellings` (Increment B),
  on a scratch copy of the program and of the rules, calling the matching functions only (no model call, no real run;
  Python 3.15.0, Darwin 25.6.0, repository commit `a31c426`): the control lines `claude-workflow commit`, `claude-workflow remove`,
  `remote-runner submit`, `remote-runner fetch` and `git push` each matched their rule; `wb run safe-git commit`, `wb run safe-git remove`,
  `wb run remote-runner submit`, `wb run remote-runner fetch` and `wb run safe-git push-check` matched nothing, because the raw text
  starts with no listed spelling, so the rules were never read. A rule file whose tool is `wb`, `safe-git` or `wb run safe-git`
  is refused ("rule tool is not supported"). So is a malformed file, a file missing a key and a file naming an unknown collector.
  In each case loading the rules raised for the whole directory, and every one of the five control lines then raised the same
  error instead of matching: with one bad rule file, the matching functions raise for every command that begins with a listed spelling and tokenizes, covered
  or not (a security review of 2026-10-25 measured `git status` and `git push` alike, and a bad, empty or missing `config.json`
  or a missing rules directory has the same effect; a line that fails to tokenize is not affected). By reading, not by a run, the
  hook's entry point swallows that error, so no verdict, no outcome row and no unmatched row is recorded and no decision is made,
  and the normal prompt is expected. The owner's mode is `delegate` (the configuration file read on 2026-10-25), so under such an
  error the delegated commit and archive no longer auto-allow and fall back to a prompt: a loss of convenience and of the log, not a
  bypass. Any change that adds a rule file for new spellings can disable the delegation and the log with one typo. A valid extra
  rule loaded and left all five controls matching. Not run: the entry point itself (it would reach a model), and the outcome hooks.
  What a patch would touch, by reading (line numbers of the program read on 2026-10-25): the spelling lists and the map from
  spelling to tool (lines 43 to 59), the supported tools (60), the installed-helper table (`INSTALLED_TOOLS`, 38 to 39), `split_command` (100), the check that a command runs the installed helper
  (`resolve_invocation`, from 449, which reads a spelling's last word as a path under the home directory), the collectors that
  call the global `claude-workflow` program as a library (`load_helper`, 387; `collect_commit`, 867; `collect_remove`, 947), and the
  rule files for the new spellings. `DELEGABLE` (77) stays as it is if commit is not delegated. The outcome hooks follow the
  matching (`process_outcome`, 2225; read, not run), but the settings file needs its own hook entries per spelling. This fixes the order of the move list: the approver's
  coverage of a new spelling comes before the helper moves (`workbench-v1#global-config-migration`: "no hard stop,
  deny rule or approver is ever absent in between").
- **F-A2: stale pointers in the approver.** Its header cites a specification and an active-plan file by names this repository
  does not use (`docs/specs/` has no such spec; plans are dated files, not one fixed file).
- **F-A3: reviewer-facing paths.** The approver lists the paths whose commits need extra scrutiny (the reviewer prompts, a
  `second-opinion` skill, two agent files). The workbench's reviewer text lives under other names (`peer-review`,
  `reviewer`, `security-reviewer` skill files in modules), so a commit editing them is not recognised as reviewer-facing.
- **F-A4: a guard mode with no agent.** `chunk` exists for a `graphify-semantic` agent that is not among the five agent
  definitions. It is either left over or waits for a definition that is elsewhere. *Status, 2026-10-29: the guard and its `chunk`
  mode went with the reset. Whether a definition of that agent survives in the copy was not checked.*
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
  prompted, so a `PermissionRequest` hook firing on a project `ask` in an interactive session was an inference and untested. On 2026-10-25 an interactive run covered one case: with the user-level entry gone, a bare `git push`
in a project with no remote raised the project's prompt and the approver logged one `git-push` verdict row (`decline`, from
failed remote checks); it says nothing about a push with a remote configured (plan `2026-10-25-retire-global-asks`, C).
- **F-B2: the module commands that replace the gated ones render no `ask`.** `wb run safe-git commit`, `remove`, and the
  `wb run remote-runner` commands `submit` and `fetch` (the module wraps no other asked command) raise no prompt from the
  project's render (read on 2026-10-25), and
  `remote-runner.md` says the same of its commands. The owner's `allow` rules and `auto` mode decide whether they prompt.
  Replacing `claude-workflow` by the module, or using the module's `submit` and `fetch` in place of the program's, therefore
  removes a prompt, and with F-B1 the approver's review, unless the workbench renders an `ask` for them or the owner accepts
  the loss. A third alternative, added by the plan `2026-10-25-approver-coverage-for-module-spellings` and not named in the
  first pass: the owner adds global `ask` entries for the four module spellings at the user level, which prompts and
  reaches the approver on the owner's machine only. Which of the three is for the owner; this spec proposes none. The choice is
  set out in the `Proposed` decision `2026-10-25-module-commands-and-the-approver`. *Status, 2026-10-29: decided. That decision was
  accepted on 2026-10-25 with the owner's global `ask` entries as the choice, and the reset removed them; the accepted record
  `2026-10-29-workbench-asks-for-remove-submit-and-fetch` replaces that choice for `safe-git remove` and `remote-runner submit`
  and `fetch`: the workbench renders an `ask` for those three, not for `safe-git commit`. Built 2026-10-29 by plan
  `2026-10-29-policy-and-module-asks` (increment B, the module `asks` field, then increment C, the declarations of `safe-git` and
  `remote-runner`): the rows above and this finding are the state of 2026-10-25 to 28, and a clone has the rule after
  `wb rerender`.*
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
  the owner and not made here (`2026-10-19-restrictive-only-permissions` permits `deny`). *Status, 2026-10-29: the premise is now
  acute and partly met. The global `deny` went with the reset, so for these six nothing outside the project covers them. The
  compiled floor, from commit `fe966b0`, renders an `ask` for `rmdir`, `unlink`, `shred` and the `gh` read, after the owner's
  `wb rerender`. `git merge` and the Codex login read are not covered (see "After the reset"). No `deny` was rendered: the owner
  chose `ask`.*

- **F-C1: the instruction file still names the retired single-plan file as a fallback.** "Roadmaps and active plans" says to
  use `docs/plans/next.md` when a repository states no convention. The workbench has no such file (`docs/plans/README.md`:
  "no fixed single-plan file"). The sentence defers to the repository's own convention first, so it conflicts only for a
  repository outside the workbench; it is the reason RP1 was split into RP1a (moves) and RP1b (stays). The old template and its `formal`
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

Increment D, the same day: it read no global file; the only access was hashing. At its start the instruction file, the
settings file and all 30 files of increment A had the recorded hashes. The end comparison is recorded in the plan's Result.

## Acceptance criteria

1. Every file under the inspected global locations appears once in "Items", or in a named group (the synced bundle, the
   bytecode) with the reason it is a group.
2. Every item has one disposition from the table above and a reason.
3. The spec says what was read in full, in part, and not at all, and why.
4. The spec writes no path to a global file and no credential, host name or token.
5. Nothing under the user level was written by this work: the end hashes equal the start hashes, or each difference is
   reported as a change by something else.
6. Every `move` and `redesign` item is in a move that names its gate, its blockers, its carrying plan and the owner's removal
   step, and every item of parts A to C is placed exactly once in "Coverage: every item in one place".

## Governing decisions and references

- Decisions: `2026-10-24-project-guarantees-a-floor`, `2026-10-22-model-calls-go-through-vendor-bridges`,
  `2026-10-24-declared-agent-confinement`, `2026-10-23-one-owner-per-skill-name`.
- Specs: `superpowers-ports.md`, `security-review.md`, `safe-git.md`, `remote-runner.md`, `review-engine.md`,
  `harness-modules.md`, `knowledge-tools.md`.
- Plans: `2026-10-25-global-config-migration`, `2026-10-24-architecture-decisions-merge`,
  `2026-10-24-security-review-module`, `2026-10-23-review-engine`, `2026-10-24-remote-runner-module`.
- References: the owner's global files are owner-local with no source URL; each is cited above by role, name, retrieval date
  (2026-10-25) and content hash.

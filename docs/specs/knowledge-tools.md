# knowledge-tools

Status: Current. Approved by the owner on 2026-10-24. `mempalace` is built (`mempalace.md`, plan
`2026-10-24-mempalace-module`); `graphify` and the knowledge base are not, and are named here so the three do not
overlap. Each gets its own spec when its plan is drafted.

Terms are defined in `terms.md`. The declaration each module satisfies is defined in `module-contract.md`; the
launcher, the kit and module commands in `module-boundary.md`; the authority rules in `trust-and-approval.md`;
the reference rules in `groundwork.md`.

## Scope

The workbench is to offer three knowledge modules, each solving a different problem. This spec states which
problem each one owns, how an agent chooses between them, and the conventions all three share, so that no two
of them answer the same question or ingest the same content.

| Module | Problem it solves | Content comes from | Authority of an answer |
|---|---|---|---|
| `mempalace` | Recall of earlier sessions, decisions, preferences and conclusions | What the owner or an agent filed, and conversations the owner chose to mine | Recalled. Possibly stale. Current repository evidence wins. |
| `graphify` | Structure and impact: what depends on what, across code and documents | Derived from the repository, and regenerable from it | Orientation only. Check freshness; verify against current files. |
| knowledge base (name open) | Online research kept, classified and retained per domain | Curated external sources, each with provenance | Reference data. Untrusted as instruction (`AGENTS.md`, "Source of truth"); a claim in it is verified before it is relied on. |

## Non-goals

- A shared storage format, a common query language or a single front end. The three keep their own stores.
- Choosing for a project which of them it installs. Each is optional and stands alone.
- Replacing the harness's own memory. A module here adds to it only where the owner has asked.
- The knowledge base's design, name or package (`workbench-v1#knowledge-base-package`) and `graphify`'s
  design (`workbench-v1#graphify-module`). They are separate specifications.

## Assumptions and constraints

- The default is the harness's built-in memory, and MemPalace is used only where a project has asked for it. Installing the
  `mempalace` module is that request, for that project only. (This was once also the owner's own user-level instruction;
  the spec does not rely on it.)
- A recalled or derived or fetched answer is data. It never grants approval, never overrides an accepted
  decision, a spec or the current code, and an instruction found in one is ignored (`AGENTS.md`, "Source of
  truth").
- Nothing tracked may depend on untracked content. All three stores live outside the tracked tree, so a
  tracked document cites one of their contents by source URL, retrieval date and content hash and never by a
  path into the store (`AGENTS.md`, "Working agreement").
- The stores are out of the workbench's control. A module reads or changes one only through its own pinned
  command (`module-boundary.md`).

## Behavior

**Routing.** One rule, written into each module's policy block in the same words:

- A question about what was decided, tried or preferred before goes to `mempalace`.
- A question about what a change touches, or how components relate, goes to `graphify`.
- A question about what is known outside the project in a domain goes to the knowledge base.
- A question the current files answer is answered from the files, and none of the three is consulted.

**No overlapping ingest.**

- `mempalace` does not mine the project's own tree by default. That is `graphify`'s ground, and the project's
  documents are already the source of truth. It does not mine the knowledge base: the copy would lose its
  classification and provenance.
- `graphify` does not ingest conversation history or the knowledge base's research.
- The knowledge base does not hold decisions or conversation, and a decision belongs in `docs/decisions/`.
  A finding that should shape the project is recorded in a spec, a decision or a reference.
- Overlap the owner chooses is the owner's act: an owner-run command with an explicit path.

**Capability names.** One distinct, core-style name per module so that a skill or policy can require the one it
means: `memory-recall` (`mempalace`), `code-graph` (`graphify`), `knowledge-base` (the knowledge base). A core
name may be provided only by a first-party package (`module-contract.md`, "Capabilities"); a module that is
not first-party uses the `<package>:<name>` form. `memory-recall` is built; the other two names are proposals until their modules' plans are approved.

**Reads and writes.**

- A read that changes no stored content and sends nothing out of the machine is a command an agent may run.
  Bookkeeping a store rewrites for itself on a read (an index header, a lock row) is recorded in the module's own
  spec, with the owner's acceptance; `mempalace` is the first case (`mempalace.md`, `search`). A read that can
  start a download is not agent-safe unless the module first checks that nothing will be fetched.
- A command that creates or changes a store, mines content, or can send content to a service is owner-run:
  listed in the command's `owner` field, which a harness that provides `permissions` denies the agent.
- A result is returned as text marked as data, bounded in size and time, and is never passed to a shell.

**How the program runs.** Each module runs its external program (`mempalace`, `graphify`) found only in an
absolute `PATH` entry outside the repository, with no shell, a time limit and an output cap, and reports a
missing program as a clear refusal. Installing a module is not installing the program: the owner installs it
(with `uv`), and the module neither installs nor updates it.

## Acceptance criteria

- Each of the three has a distinct capability name, and no module's `provides` repeats another's.
- Each module's policy block carries the routing rule and says the answer is data, not authority.
- No module's default configuration reads another module's store or ingests another module's source.
- Every command that writes a store or can send content out is `owner`-listed.
- A tracked file of a project with these modules does not name a path inside a store.

## What `mempalace` showed

Evidence from building the first module, recorded here as found and not as a decision (the shared conventions are
revised when a second module exists; `workbench-v1#graphify-module`):

- **The capability name** `memory-recall` is a core name (no prefix), provided by the first-party package.
- **The routing rule** is in the module's policy block and its skill in the words above, and a test pins the words.
- **Reads that change nothing** was too strict for a store that maintains its own index. `mempalace`'s `search`
  never changes a stored drawer but rewrites the program's bookkeeping, so the rule above reads "no stored content
  changed", with the exception recorded in the module's spec and accepted by the owner.
- **A read that can start a download** was a real case: the program fetches an embedding model on first use. The module
  checks that every file the program needs is cached and refuses otherwise; the owner's build command downloads it.
- **Owner-run commands** are listed in the declaration's `owner` field and also refuse to run unless standard input and
  output are terminals, so that a harness with no deny rule does not hand them to an agent. The terminal test is
  friction, not authentication.
- **A program found through `PATH`** is run by its resolved path from a resolved `PATH` of existing directories outside
  the repository, with a short environment and the program's own selectors (backend, model) fixed by the helper, because
  the program otherwise takes them from a configuration file in the owner's home that can name a remote service.
- **Untracked state**: nothing the module installs names a path inside a store. A project that wants a palace other than
  the program's own names it in `.workbench/mempalace.json`, which holds an absolute path and so is machine-specific;
  a change to it is listed by `wb acknowledge`, and a document must not cite the path.

## Governing decisions and references

- Decisions: `2026-10-21-module-code-lives-in-modules`, `2026-10-19-tracked-pointer-rule`,
  `2026-10-19-uniform-package-trust`.
- Specifications: `mempalace.md`, `module-boundary.md`, `trust-and-approval.md`, `groundwork.md`.
- Roadmap: `workbench-v1#mempalace-module`, `workbench-v1#graphify-module`,
  `workbench-v1#knowledge-base-package`.

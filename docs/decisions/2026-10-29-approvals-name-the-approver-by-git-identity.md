# Approvals name the approver by git identity and record how they were authorized

Status: Accepted by Robert Ziegler <25854477+rziegler42@users.noreply.github.com> on 2026-10-29
Date: 2026-10-29

## Context

Every approval record the workbench writes holds an `approver` text. It comes from `approve.approver_name()` in
`workbench/approve.py`: the operating-system account name of whoever ran the command, or the literal text `owner` when that lookup
fails. The writers are `approve`, `pin`, plan approval and delegated plan approval. The plan approvals file is shown in
`docs/specs/trust-and-approval.md`, "The record". The field is capped at 64 characters (`workbench/planapprovals.py`, `_text`).
Shipped records are written by `release-approvals` with the fixed approver `workbench-release`, so that a second release changes
nothing.

Three problems follow, and the owner raised them on 2026-10-29. The role word "owner" says nothing when the owner is also the author
of a document, and gets ambiguous when several people work on a repository. An account name is machine-local and is not
unique across machines. And a record gives no sign that an AI ran a command for the person, or that a review stood in for them:
a delegated record names the review but is not shown with the approver, and an `ask` or `none` run records only the account the agent
runs under, which is the person's.

No accepted decision defines the `approver` field; the specs do. This record is therefore a new decision and supersedes none.

## Decision

1. **One identifier for every approval:** the person's git identity in git's author form, `Name <email>`, for example
   `Example Approver <12345+example@users.noreply.github.com>`. It is an unverified attribution label: git does not check that a
   person owns an email, and two people could use one. The email is the part most likely to tell people apart, and a GitHub noreply
   address carries a permanent account number and keeps a personal address out of tracked files. Records are compared by the
   lowercase email, and the name is a label for readers.
2. **Where it is read from, exactly:** two runs, `git config --global --get user.name` and `git config --global --get user.email`,
   each given as an argument list with no shell, at the moment of approval. The working directory is the account's home directory
   from the account database and never the project. The environment is built from nothing: `HOME` set to that directory, a fixed
   `PATH`, `GIT_CONFIG_NOSYSTEM=1` and `LC_ALL=C`, and every `GIT_*` variable left out, including `GIT_CONFIG_GLOBAL`,
   `GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS` and `GIT_DIR`. `--global` reads only the account's own global files and, by git's
   documented default for a named file, follows no `include` directive. The project's own `.git/config` is never read, because a
   hostile clone can set it. A missing value makes the command refuse and say how to set it. The fallback to `owner` is removed.
3. **Separate fields, rendered as a sentence.** A record holds `approver` (`Name <email>`), `via` and, for a delegated approval, the
   existing `delegate` object (provider, bridge, model, rounds, review). `via` is one of `terminal`, `ask`, `delegated` or `none`, the
   level the run was authorized under. Commands and documents print it as, for example, "approved by Example Approver <email>
   delegated to codex (gpt-5.6-terra)". Hand-written status lines use the same identifier: "Accepted by Example Approver <email> on
   2026-10-29".
4. **The grammar and the limits.** The name is 1 to 100 characters after Unicode NFC normalization, with no control, format,
   surrogate, private-use or unassigned character, no line or paragraph separator, and neither `<` nor `>`. The email is 3 to 100
   characters, each a printable ASCII character from `!` to `~` other than `<` and `>`, with exactly one `@` and something on each
   side of it, so it holds no space, tab, line break or other control character. The stored text `Name <email>` is at most 210
   characters and is a single line of printable text. Records compare by the lowercased email and never by the name. An identity outside this grammar makes the
   command refuse, naming the value and the rule. The `approver` limit rises to 256 characters, each record format that holds it is
   raised one version, and entries written before the change are read as they are and stay as history.
5. **Shipped records keep `workbench-release`.** It is a role, not a person, and keeps a re-release deterministic.

## Alternatives considered

- **The git name alone.** Rejected: names are not unique, and two people can share one.
- **The operating-system account name, as today.** Rejected: it is machine-local and says nothing on another machine.
- **One free string with a suffix, such as "delegated to Codex".** Rejected by the owner in favour of fields: it needs a larger limit
  and a parser to tell the approver from the delegate.
- **An identity set once in the personal settings.** Not chosen: steadier for someone with several git identities, but it adds a
  setup step and a field. It can be added later if the global git identity proves unstable.
- **Read the project's git config.** Rejected: it is hostile input, and the installer already refuses to read it for other purposes.

## Consequences

- **Good:** an approval carries an attribution label that can usually be told apart from the author's, and shows whether it was typed
  at a terminal, confirmed at a prompt, delegated, or run with no gate.
- **Bad:** the email also appears in the guarded store and in tracked status lines. It is already in every commit's author and
  committer fields, so this adds little for the owner's noreply address; a contributor who commits with a personal address would
  add it to file content as well. Identity is self-declared in git, so this is an audit trail and not authority. Who may approve is
  a separate decision, not made here.
- **Limit:** the installer cannot tell which AI ran a command at `ask` or `none`; it records the level and the absence of a
  terminal. A named AI appears only for a delegated review, where the review record names the bridge and model.
- **Cost:** a code change in `workbench/` and its tests, an update to the record formats in `trust-and-approval.md`, and the
  convention in `terms.md` and the decisions and plans READMEs. The `workbench/` code is not under `packages/`, so no shipped
  approval is released for the code, but the README texts are module text and are.
- **Not decided:** a person with different identities on different machines, and a person who relocates the global git
  configuration with an environment variable: decision 2 ignores `GIT_CONFIG_GLOBAL`, so that person's identity is not read from the
  relocated file.

## Evidence

Read on 2026-10-29 at commit `5ee1ecce8efa83194f118748666a84fab4be6960`, workbench 0.1.0: `workbench/approve.py` (`approver_name`),
`workbench/planapprovals.py` (`_text`, the approval fields), `workbench/delegation.py` (the `delegate` object),
`workbench/firstparty.py` (`RELEASE_APPROVER`) and `docs/specs/trust-and-approval.md`; `git config --get` for the owner's name and
email on this machine, and the owner's direction in session on 2026-10-29. Not run: a refusal with no identity configured, since
the change is not built, and the invocation in decision 2. The claim that `git config --global` follows no `include` directive by
default is git's documented behaviour for a named file and was not tested here; the plan tests it.

## Clarification note, 2026-10-29 (approved by Robert Ziegler <25854477+rziegler42@users.noreply.github.com> on 2026-10-29; the body above is unchanged)

The security review of the identity reader (Increment A of `2026-10-29-approvals-name-the-approver`, commit `6f2e957`) ran the
grammar of decision 4 against a copy in a scratch directory (Python 3.15.0, Unicode 17, Apple Git 2.54.0, 2026-10-29) and found two
names that the grammar admits and that name nobody or are padded: a name made only of characters that print as nothing (U+3164,
U+115F, U+1160, U+FFA0, U+2800, U+17B4, U+17B5, U+034F, or combining marks alone), and a name with a space at either end. Decision 4
is clarified, and not otherwise changed, in two ways:

1. The name must hold at least one letter, number, punctuation mark or symbol that is not in that list of characters that print as
   nothing.
2. The name neither begins nor ends with a space or other blank (a `Zs` character).

The review also showed names that print as a second identity (lookalike angle brackets, a lookalike letter) and a run of up to 100
combining marks. They are not restricted: records compare by the lowercased ASCII email and never by the name, and a rule against
every lookalike would be long and still incomplete. The rest of the decision is unchanged, and the text above is not edited.

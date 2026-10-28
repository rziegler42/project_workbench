---
name: verilog-sby-formal
description: Use when writing, reviewing or debugging formal proofs for plain Verilog-2001 with SymbiYosys: sby tasks, harnesses, assert/assume/cover, induction failures, unreached covers, timeouts, or a request to raise depth or add an assume to make a proof pass. Not for SystemVerilog or simulation.
---

# Formal verification with SymbiYosys

This skill is for plain Verilog-2001 that Yosys accepts, in the design and in the harness. SystemVerilog is out of scope: if the design or the harness uses a SystemVerilog construct (assertion properties, interfaces, classes), stop and tell the owner instead of extending the advice to it, and do not bring in a second formal tool. A Verilator testbench or an intermittent simulation failure is a different skill (`verilog-verilator-sim`). The advice here is read from the owner's practice and has not been run in this project; each tool behaviour named below is a claim to check against the installed tool version before relying on it. Task modes, a worked harness, `.sby` templates and a deliberately broken fixture are in `reference.md`.

## Read the formal code with the formal frontend

Name the sources in the task's `[script]` with `read_verilog -formal`. A plain `read_verilog` rejects `assert`, `assume` and `cover` statements. It does accept `$past` and `$stable`, and the `(* anyseq *)` and `(* anyconst *)` attributes, but only the formal flow gives them meaning. Keep formal code in a separate harness file, or under `` `ifdef FORMAL `` with the define set in the script.

## Fix the proof boundary before writing a property

Read the design, the existing harnesses and tasks, and the document that defines the behaviour. State each property as a claim an observer could check: what is guaranteed, under which legitimate constraints on the environment, at which boundary.

Keep the harness apart from the production design. Code compiled under `FORMAL` inside the design needs an explicit owner and an explicit exclusion from synthesis. Reaching a design's state from a harness, by a new port or by checks inside the design under `FORMAL`, is such a change; prefer the checks inside when a new port would change an interface other code depends on. Use the smallest design and harness that own the behaviour. Do not begin the diagnosis of a failure with a whole-chip proof when one module can isolate it.

## Model the environment faithfully

Use `(* anyseq *)` for a value that may change every cycle and `(* anyconst *)` only for a value that must stay fixed across the whole trace. Constrain only real interface contracts: reset behaviour, protocol legality, fairness when it is essential and documented, and abstraction boundaries someone chose and wrote down.

`assume` restricts the world; `assert` checks the design. Never add an `assume` only to steer the design into a convenient state, opcode, occupancy or transition for a whole trace: it can remove legal counterexamples and make a proof pass for the wrong reason. If the space must be split, prove that the pieces together cover the original obligation, and state each piece as `selector -> property` at the point where a violation could happen.

### Adding an assume to make a proof pass or a cover reach

An `assume` on an interface input, such as excluding an opcode or an operand, needs a written source: a clause of the specification or a decision record. Without one, do not put it in the main task. Tell the owner, put it in a separately named conditional task, leave the unconditional task unweakened, and report any result under the conditional task as conditional, never as an unconditional pass. Raising the depth is the same kind of request: say so to the owner before doing it to make a result change.

### Starting state

Guard `$past` with a register that has an explicit initial value, or with a reset or initial-state condition. `$initstate` helps with initialisation; it does not replace an inductive invariant, because induction starts from an arbitrary state, not from time zero. Design registers with no initial value also start arbitrary, and the time-zero reset assumption is what defines them after the first clock edge.

## Write properties a solver can use

Prefer small, independent claims over one restatement of the design:

- safety and bounds: occupancy and range, mutual exclusion, no response without a request;
- stability under stall: a held request, address, data or control signal stays stable;
- exact-once lifecycle: admission, issue, completion and retirement neither repeat nor vanish;
- reset cleanup and cancellation;
- ordering and identity: a shadow transaction, token or small counter follows the real one;
- data correctness: compare with a value derived independently, never a copy of the design's own expression.

For a pipeline, queue, bus or controller, add ghost state that follows the unit of work: a count of outstanding work, a valid, identifier and data shadow, or a packet carried through the stages. That is often the missing inductive invariant, and it should be checked at every handoff. Prefer an invariant that explains an induction failure to a larger depth that merely gets past it.

For an instruction-set core, keep instruction meaning apart from microarchitecture behind a stable interface (inputs, outputs and a retirement signal), and generate one templated check per instruction from a shared script instead of copying the harness by hand.

Write immediate properties in procedural Verilog, usually inside `always @(posedge clk)`, with a comment beside each naming the contract it protects. Keep covers apart from safety assertions when their setup or depth differs. To limit a property to one mode or opcode, use an implication inside a shared block, such as `assert(sel_add -> (result == expected_sum));`: it is vacuously true outside its case and adds no constraint there.

## Choose and record the task

Use `bmc` to search for a counterexample to a bound, `prove` for induction, and `cover` for reachability and for finding vacuity (see `reference.md`). A bound that passes is not an unbounded proof. Record in the `.sby` file the mode, depth, timeout, engine, defines, top module, abstractions and the expected result (`expect pass` or `expect fail` in `[options]`). If a different solver is needed, record why, its arguments, the time taken and the outcome. Splitting a task for quicker feedback must not change the property, the depth or the assumptions.

## Diagnose from the evidence

When an assertion fails, read the trace and decide first whether it shows a defect in the design, a mistake in the harness or environment, a gap in initialisation, or a wrong property. Keep the counterexample until the finding is settled: running `sby -f` deletes the old task directory, so copy the trace out before the next run.

When a cover does not reach its goal, cover a step earlier in the intended lifecycle and work forward; an unreached cover leaves no trace to read. Do not repair a failed cover by strengthening the assumptions unless the resulting environment is justified on its own.

Keep `PASS`, `FAIL`, `TIMEOUT` and `UNKNOWN` apart. A timeout or an unknown is inconclusive: not a pass, and not automatically a design defect. Record the task, tool and engine, depth, timeout, time taken and the scope actually closed.

## Show that the proof means something

Every important safety proof needs a reachability witness: a cover of a useful path from start to completion, normally including a response and a return to an idle or reusable state, and of two or three transactions when throughput matters.

Keep at least one deliberately broken property or mutation as its own task with `expect fail` and a define that switches the break on (see `reference.md`). It shows that the task builds the intended harness, that the assumptions are not vacuous and that the diagnostics are usable.

Assumptions can also make a legal configuration unreachable while no assertion fails. Cover a state the assumptions should still allow, not only progress of the design; if that cover is not reached, the assumptions contradict each other.

Formal and simulation complement each other: simulation gives broad evidence of behaviour and timing, formal gives exhaustive claims about local safety, ordering and corner states.

## Follow the repository's own rules

If the repository keeps a property ledger, names an engine for each mode, asks for release or integration evidence, or lists dynamic checks to rerun after a change to the design for formal work, follow it (see `reference.md`). A passing task without the records the repository requires is not closure.

## Common mistakes

| Mistake | Instead |
|---|---|
| Raising the depth to make an induction step pass | Add the missing invariant or the reset and reachability anchor |
| An `assume` that pins the design to a convenient state | Assume only environment contracts, assert on the design, and ask the owner for a written source before any new assume on an input |
| `$past` with no initialised past-valid register | `reg f_past_valid = 1'b0;` and a time-zero reset assumption |
| Reporting TIMEOUT or UNKNOWN as a pass or as a bug | Report it as inconclusive with the depth, engine and time taken |
| A passing safety proof with no cover | Add a reachability cover so the proof is not vacuous |
| Two competing non-blocking assignments to one counter | Compute the next value once, in a `case` |
| A hierarchical reference such as `d.count` from the harness into a submodule | Yosys turns it into an undriven free wire. Reach the state through a port or check inside the design under `FORMAL`; start the harness with `` `default_nettype none `` and treat "implicitly declared" and "no driver" warnings as errors |

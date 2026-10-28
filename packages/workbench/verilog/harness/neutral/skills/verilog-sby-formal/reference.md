# Reference: SymbiYosys task modes, a harness and task files

Plain Verilog-2001 throughout. Nothing here has been run in this project; the advice is read from the owner's practice, so
check each tool behaviour against the version in use.

## Task modes

- `mode bmc`: a bounded search from reset for a counterexample. A bound that passes is not an unbounded proof.
- `mode prove`: k-induction. It runs a bounded base check and an induction step from an arbitrary state. A failing step
  usually means a missing invariant, a missing reset or reachability anchor, or an assertion that is too broad; it rarely
  calls for a larger depth.
- `mode cover`: reachability and vacuity. Cover leaving reset, a useful transaction completing, a return to idle,
  back-to-back work and the important exceptional paths.

A small control-only Boolean problem may suit a SAT or PDR engine. Use a bounded SMT engine for bit-vector BMC and an
engine that supports induction for `prove`. With more than one clock, add `multiclock on` to `[options]`.

## A harness for a responder

The design here is the responder: `i_req`, `i_addr` and `i_data` are inputs the harness assumes, `o_ready` and `o_ack` are
outputs it asserts. If the design is the requester, swap `assume` and `assert` in the stall block.

```verilog
`ifdef FORMAL
    // Anchor time zero. $past means nothing in the first cycle, and the
    // design must start in reset. The initial value is required: without it
    // the solver may pick f_past_valid = 1 at time zero.
    reg f_past_valid = 1'b0;
    always @(posedge i_clk)
        f_past_valid <= 1'b1;
    always @(*)
        if (!f_past_valid)
            assume(i_reset);

    // Ghost counter: requests accepted and not yet acknowledged.
    localparam MAX_OUTSTANDING = 8;
    reg [3:0] f_outstanding = 4'd0;
    wire f_accept = i_req && o_ready;

    // Reset has priority. An accept and an ack in the same cycle cancel, so
    // the next value is computed once rather than by two assignments.
    always @(posedge i_clk)
        if (i_reset)
            f_outstanding <= 4'd0;
        else
            case ({f_accept, o_ack})
            2'b10:   f_outstanding <= f_outstanding + 4'd1;
            2'b01:   f_outstanding <= f_outstanding - 4'd1;
            default: f_outstanding <= f_outstanding;
            endcase

    always @(posedge i_clk)
        if (!i_reset) begin
            // No acknowledgement for work that was never accepted.
            if (o_ack)
                assert(f_outstanding != 0);
            // Occupancy bound: the design must stop accepting when full.
            assert(f_outstanding <= MAX_OUTSTANDING);
            if (f_outstanding == MAX_OUTSTANDING)
                assert(!o_ready);
        end

    // Environment contract: a stalled request is held until it is accepted
    // or reset intervenes.
    always @(posedge i_clk)
        if (f_past_valid && !$past(i_reset)
                && $past(i_req && !o_ready)) begin
            assume(i_req);
            assume($stable(i_addr));
            assume($stable(i_data));
        end

    // Reachability witness: work is acknowledged, so the asserts above are
    // not passing on a design that never answers.
    always @(posedge i_clk)
        if (f_past_valid && !i_reset)
            cover(o_ack);
`endif
```

Keep the widths of the arithmetic, the meaning of a request and a response in the same cycle, reset priority and wrap
behaviour explicit in a real property. This is a starting point, not a protocol proof.

For `mode prove` the ghost counter must also be tied to the design's own state, together with any relation among the
design's other registers (for example that `o_ack` implies the design holds something). Otherwise induction starts from an
arbitrary design state that has nothing to do with the ghost and fails on the `o_ack` assertion. A `bmc` run from reset
passes without the coupling.

Reach that state through a port (an `o_count` output wired to a harness wire) or write the invariant inside the design under
`` `ifdef FORMAL ``. Do not write a hierarchical reference such as `d.count` from the harness: Yosys does not resolve it to
the instance's register. It warns that the identifier is implicitly declared and that the wire is used but has no driver,
then treats the name as a free wire the solver may set to anything, so the invariant fails on traces that cannot happen.
Treat those two warnings as errors.

The coupling for the harness above. The design gains `output [3:0] o_count`, driven by its internal counter; the harness
declares `wire [3:0] f_count;`, connects `.o_count(f_count)` and adds:

```verilog
`ifdef FORMAL
    // Tie the ghost counter to the design's real state so induction cannot
    // start from an unrelated arbitrary design state.
    always @(posedge i_clk)
        if (f_past_valid) begin
            assert(f_count == f_outstanding);
            // A relation among the design's own registers: an
            // acknowledgement implies something is outstanding.
            if (o_ack)
                assert(f_count != 0);
        end
`endif
```

With this added, `bmc`, `prove` (base and induction step) and `cover` are read to pass on a small responder; that has not
been run here.

Put `` `default_nettype none `` on the first line of the harness file, so a misspelt name or a hierarchical reference is a
parse error instead of a warning. Check that the harness declares every wire it uses, including the wires connected to
instance ports.

## A minimal `.sby` file

```
[tasks]
bmc
prove
cover

[options]
bmc: mode bmc
bmc: depth 30
prove: mode prove
prove: depth 20
cover: mode cover
cover: depth 40
timeout 300

[engines]
smtbmc yices

[script]
read_verilog -formal -DFORMAL dut.v harness.v
prep -top harness

[files]
dut.v
harness.v
```

Run a task with `sby -f dut.sby prove`. The `-f` option deletes the previous task directory, counterexample included: copy
out a trace you still need, or give the run its own directory with `-d`, before running again. The traces sit under the
task directory, in `engine_0/`: `trace.vcd` for a `bmc` counterexample, `trace_induct.vcd` for a failed induction step and
`trace0.vcd` for a reached cover, each with matching `*_tb.v` and `.yw` files. Use the repository's own engine in place of
`yices`, and record the depth, timeout and expected result for each task.

To prove a parameterised module in more than one configuration, add `-chparam NAME value` to the `hierarchy` line
(`hierarchy -check -top dut -chparam WIDTH 8`) and give each configuration its own task with a `script:`-tagged line,
instead of one task that only tries the default parameter values.

## A deliberately broken fixture

A separate task that must fail shows that the harness checks something. Guard a false assertion with a define, and give
that task `expect fail` and the define:

```verilog
`ifdef BREAK
    always @(posedge i_clk)
        if (f_past_valid && !i_reset)
            assert(f_outstanding == 0);   // false once anything is accepted
`endif
```

```
[tasks]
bmc
broken

[options]
bmc: mode bmc
bmc: depth 30
broken: mode bmc
broken: depth 30
broken: expect fail
timeout 300

[engines]
smtbmc yices

[script]
bmc: read_verilog -formal -DFORMAL dut.v harness.v
broken: read_verilog -formal -DFORMAL -DBREAK dut.v harness.v
prep -top harness

[files]
dut.v
harness.v
```

Running `sby -f dut.sby bmc broken` is read to report a pass for `bmc` and a failure for `broken`; the failure is the
expected outcome, and the counterexample is written under the `broken` task directory. Add `expect pass` (the default) or
`expect fail` to any task to record its expected result.

## Repository conventions

Follow each of these where the repository defines it, and skip the item otherwise.

- A property ledger or manifest: give each changed behaviour an entry with its owner, assumptions, task, proof style, scope
  and result. A passing task without the entry is not closure.
- A named solver engine for each mode: use it instead of running a matrix of solvers. Budget resources across parallel
  tasks, engines and solver threads together; do not maximise all three.
- Release or integration evidence requirements: keep them unchanged when fast focused tasks are split from long
  from-reset BMC and cover tasks.
- After a formal change to the design: rerun the affected simulation checks on the final design before reporting closure.

---
name: verilog-verilator-sim
description: Use when writing, reviewing or debugging a Verilator testbench for plain Verilog-2001: self-checking comparisons, intermittent failures, requests for a retry or longer timeout, golden fixtures, waveforms, races, Verilator warnings. Not for formal proofs or SystemVerilog.
---

# Simulation verification with Verilator

This skill is for plain Verilog-2001, in the design and in the testbench. SystemVerilog is out of scope: if the design or the testbench uses a SystemVerilog construct (classes, interfaces, assertions, `$fatal`, `$error`), stop and tell the owner instead of extending the advice to it. Formal proofs are a different skill (`verilog-sby-formal`). The advice here is read from the owner's practice and has not been run in this project; each tool behaviour named below is a claim to check against the installed tool version before relying on it. A worked testbench is in `reference.md`.

## Report the result in a line a script can read

Verilog-2001 has no way to set the process exit code from the testbench. Print one line that starts with `TEST PASSED` or `TEST FAILED`, and let the driver or the CI wrapper decide its exit status from that line. Do not rely on `$fatal` for a nonzero exit: it is not Verilog-2001.

## An intermittent failure is a real bug until shown otherwise

A Verilator run of one binary with the same seed and the same inputs gives the same result every time. If a check fails one run in twenty, something uncontrolled differs between runs. Look for an unseeded random call in the stimulus or the reference model, the build's policy for initial and unassigned values, evaluation-order sensitivity with several threads, or randomness inside the reference model.

1. Make every run-to-run setting visible (print it at start-up) and controllable (settable on the command line): the seed of the stimulus, the seed of the reference model and the seed of the simulator's own randomisation.
2. Replay one failing run with everything pinned. If it now fails every time, it is an ordinary bug: debug it as one. If it still comes and goes with everything pinned, the harness or the build has a defect, such as an ordering race or undefined behaviour. Find it; do not average it away.
3. Only with a reliable repeat, enrich the mismatch report (state of the design and of the model around the failing cycle). If that is not enough, use waveforms, and compare the design's trace with the model's rather than reading one alone.

Never add a retry, a skip marker, a looser threshold or a longer timeout to a check that asserts a correctness property (a comparison with a reference model, an occupancy bound, mutual exclusion) only because it fails now and then. First tell the owner that this may hide a real bug, and wait for a clear yes. Treat it like a request to regenerate a golden fixture or to loosen a checker that disagrees with the design: investigate and report before changing anything, not after.

| Excuse | Reality |
|---|---|
| "It is only flaky, add a retry" | A simulation is deterministic. A flaky result means an unpinned variable, and that variable is worth finding. |
| "There is no time to find the cause today" | Printing and pinning the seed takes one line and turns "sometimes" into "every time". That is the quick way. |
| "A retry changes neither the design nor the checker" | A retry that hides a failing correctness check ships the same bug as a rewritten fixture or a bent checker. |

## Design the comparison, not only the stimulus

Compare the design with a reference model derived independently, never with a restatement of the design's own expression. A model that repeats the design's fixed-width wrap or its conditional can share the design's bug and so cannot catch it. Prefer a different computation, for example an unbounded counter cut to the width, instead of a second copy of the wrapping logic. The formal skill states the same rule for an `assert`.

Write the registers of a model, like the registers of the design, with non-blocking assignments (`<=`) in clocked blocks: they stand for synchronous state and must read the old values. Use blocking assignments (`=`) only in a single-writer process for stimulus or bookkeeping, where no ordering hazard exists. Change stimulus away from the clock edge the design samples on, for example on the opposite edge, so the stimulus and the clocked block do not race.

## Coverage is evidence, not proof

Line and toggle coverage show that code ran and bits moved. They say nothing about a property across signals or over all reachable states, and a line counted as covered can hide a branch combination that was never tried. Treat full coverage as the health of the regression suite, not as a substitute for a proof. For an exhaustive claim about safety, ordering or a corner state, use `verilog-sby-formal`.

## Common mistakes

| Mistake | Instead |
|---|---|
| Using `$fatal` or `$error` in a Verilog-2001 project | Print the `TEST PASSED` or `TEST FAILED` line and let the wrapper set the exit status |
| A retry or skip on a correctness check because it is "flaky" | Pin and print the seed, reproduce it, and tell the owner before working around it |
| Letting the simulator's zero-fill of unset registers make a run pass | Run at least one regression with randomised initial values, so a reset bug cannot hide behind a lucky default |
| A reference model that recomputes the design's own wrap or conditional | Derive the expected value from the specification or a behavioural model |
| Blocking assignments in a clocked block that models register state | Use `<=`; keep `=` for single-writer stimulus and bookkeeping |
| Regenerating a golden fixture to match new output | Check the new output against the specification first; update the fixture only then |

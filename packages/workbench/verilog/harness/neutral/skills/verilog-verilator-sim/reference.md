# Reference: a self-checking testbench and Verilator pitfalls

Plain Verilog-2001 throughout. Nothing here has been run in this project; the advice is read from the owner's practice, so
check each tool behaviour against the version in use.

## A self-checking testbench

The design under test is a free-running counter of a given width with a synchronous reset. The reference model is a wider
counter that is cut to the width when compared, so it does not repeat the design's wrap logic. The check samples on the
falling clock edge, half a cycle after both sides have settled, so no same-time-step race has to be reasoned about. Reset
is released on a falling edge, not straight after the rising edge that ends the reset window: changing a signal at the
instant a clocked block also triggers is a race between the stimulus and that block.

```verilog
`timescale 1ns/1ps

module tb_counter;
    localparam WIDTH = 4;

    reg              clk;
    reg              rst;
    wire [WIDTH-1:0] dut_count;

    counter #(.WIDTH(WIDTH)) dut (.clk(clk), .rst(rst), .count(dut_count));

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    // Model: a wider counter, not a copy of the design's wrap arithmetic.
    // Non-blocking, because it stands for synchronous state.
    reg [31:0] model;
    always @(posedge clk)
        if (rst) model <= 32'd0;
        else     model <= model + 32'd1;

    integer errors;
    integer checked;
    always @(negedge clk)
        if (!rst) begin
            checked <= checked + 1;
            if (dut_count !== model[WIDTH-1:0]) begin
                $display("MISMATCH check=%0d expected=%0d got=%0d",
                         checked, model[WIDTH-1:0], dut_count);
                errors <= errors + 1;
            end
        end

    initial begin
        errors  = 0;
        checked = 0;
        rst     = 1'b1;
        repeat (2) @(posedge clk);
        @(negedge clk);           // release away from the active edge
        rst = 1'b0;
        repeat (40) @(posedge clk);
        @(negedge clk);           // let the last check settle
        if (errors == 0)
            $display("TEST PASSED: %0d checks, 0 mismatches", checked);
        else
            $display("TEST FAILED: %0d mismatches in %0d checks", errors, checked);
        $finish;                  // the exit status is always 0; the wrapper decides
    end
endmodule
```

The wrapper decides the result from the printed line, not from the simulator's exit status:

```sh
./sim_counter | tee run.log
grep -q '^TEST PASSED' run.log
```

For a larger design keep the model behavioural (a queue for a FIFO, arithmetic for an ALU) rather than a bit-exact copy of
the RTL. For a pipeline or a valid/ready bus, compare two queues, one of expected and one of observed values, each pushed
only when its valid signal fires, instead of comparing on every clock edge. Keep the same shape whatever the design: a
sentinel line and a watchdog timeout, so nobody needs a waveform viewer to learn whether it passed.

## Verilator pitfalls

Each point is read, not run.

- **Two-state simulation hides reset bugs.** Verilator has no X or Z. A register nobody initialised reads as 0, so a missing
  reset connection can pass by luck. Build at least one regression with randomised initial and unassigned values (the
  `--x-assign unique` and `--x-initial unique` options) so a reset gap shows as a mismatch.
- **`INITIALDLY`.** A non-blocking assignment in an `initial` block runs as a blocking one, because there is no delayed
  update queue there, which can differ from an event-driven simulator. Keep `<=` for clocked `always` blocks.
- **`UNOPTFLAT`.** Verilator fixes the evaluation order of combinational logic and cannot iterate to settle a real
  combinational loop. Treat the warning as a design defect to remove, not one to silence.
- **`===` and `!==` collapse to `==` and `!=`.** With no X or Z to tell apart, they cannot detect a floating bus or an
  uninitialised condition the way a four-state simulator can. A four-state simulator still earns its place for tri-state
  buses.
- **Speed settings trade against reset bugs.** The tool's "fast" settings for the same options skip the randomisation and so
  can hide a reset bug again; use them for speed only after a randomised run has passed.

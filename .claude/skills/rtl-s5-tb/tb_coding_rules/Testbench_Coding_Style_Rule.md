# Testbench Coding Style Rule

## 1. Scope

This document is the testbench coding-style rule converted from the `tb_check_item` sheet in the provided `RTL_Coding_Style_Rule(1).xlsx`.

The scope is a **direct, self-checking simulation testbench** written in **Verilog-2005 (IEEE 1364-2005)**: the testbench top `tb/tb_<module>.v`, its component modules `tb/tb_<module>_<role>.v` (section 3.2), and one test-case file `tc/<ID>.v` per top-level VPLAN Item (included as `sim/run_test.v`). SystemVerilog-only constructs (`logic`, `bit`, `string`, `always_ff`, `always_comb`, `always_latch`, `typedef`, `enum`, `struct`, `interface`/`modport`, `package`, `class`, `foreach`, queues, dynamic arrays, `mailbox`, SV casts, `$fatal`, SVA) shall **NOT** be used. The rules below do not introduce UVM, coverage, constrained-random or assertion-based verification.

This style applies when the project's optional S4/S5 direct-test flow is used. It does not make S4/S5 mandatory for every module.

## 2. Comment

| Category | Rule |
|---|---|
| Notation | Only use `//`. Do **NOT** use `/* */`. |
| Comment sentence | Comments must be written in English only; do not use other languages including Vietnamese. |

## 3. Format

| Category | Rule |
|---|---|
| Header | Use a meaningful header to describe the testbench/module. |
| Indentation | Use **2 spaces** for indentation instead of TAB. |
| Coding style | Do not omit `begin/end` pairs for statement blocks. |
| Coding style | Do not use one unnecessarily large `always` block for unrelated stimulus/checking behavior. Separate independent behavior when it improves readability. |

### 3.1 Mandatory Section Order (testbench top)

The testbench top `tb/tb_<module>.v` contains these nine sections, in this order, each opened by a visible header comment (`// ====…` / `// 1. Declaration` / `// ====…`). Keep all nine headers even in a small testbench; leave a section empty instead of writing meaningless code. Component files (section 3.2) do not use the nine sections.

| # | Section | Content |
|---|---|---|
| 1 | Declaration | `CLK_PERIOD`, `RESET_CYCLES`, `TIMEOUT_NS`, `CHK_DLY`, `MAX_WAIT` (handshake limit, when the DUT has one), log columns `TIME_W`/`CLK_W`/`TAG_W`/`VAL_W`, register addresses; every `wire` between the DUT and the components, each commented with its single driver (`// u_drv`); every variable used by the sequence tasks. |
| 2 | DUT Instance | `u_dut`, connected by name. |
| 3 | Clock Generation | Clock/reset generator instance `u_clk_rst` (`clk`, `rst_n`, global rising-edge count `clk_cnt`). |
| 4 | Init Reset | `reset_dut`: driver to idle now, reset applied per specification through `u_clk_rst`, `u_chk.sync`. Resets the DUT and the model (the model follows `rst_n`); never clears the result counters or `clk_cnt`. |
| 5 | Golden Reference Model | Model instance `u_model`. |
| 6 | Checker | Observation and result path: monitor `u_mon`, checker `u_chk`, logger `u_log`. |
| 7 | Helper Functions | Presentation helpers shared by the log (e.g. `reg_name(addr)`, `field_names(addr, mask)` from the register map); no checking logic. Empty when not needed. |
| 8 | Tasks | Stimulus path: driver instance `u_drv`; **sequence tasks** for the test cases – stimulus only, each ending with `u_chk.sync` (e.g. `apb_write`, `apb_read`, `set_dbg_mode(v)`, `wait_cycles(n)`); `init_test(id, objective)` (`u_log.init`, `[TEST]` context lines, plusargs) and `end_test` (`u_log.summary`, `$finish`). |
| 9 | Main Program Body | `` `include "run_test.v" `` (sequence of the selected Item) and the global timeout (`u_log.error_msg($time, "TIMEOUT", …)`, `end_test`). |

### 3.2 Testbench Components and Connections

The environment is built from Verilog-2005 modules with real ports, one file each, flat in `tb/`, named `tb_<module>_<role>` (prefix avoids name clashes between DUTs and with RTL modules) and listed in `sim/tb.f` before the testbench top.

| Role | Instance | Receives | Drives / produces | Logs (through `u_log`) |
|---|---|---|---|---|
| Test sequence / controller | `initial` block of `tc/<ID>.v` | – | calls the sequence tasks of the top (stimulus only), `reset_dut`, `u_log.item/sub1/sub2/goal` | branch headers, `[GOAL]` |
| Clock/reset generator | `u_clk_rst` (`tb_<m>_clk_rst`) | – | `clk`, `rst_n`, `clk_cnt` (only driver) | `[RESET]` at assert and at release |
| Protocol driver (e.g. APB master) | `u_drv` (`tb_<m>_drv`) | `clk`, `clk_cnt`, DUT handshake outputs the protocol needs | every DUT input except clock/reset (only driver) | inputs outside the bus when applied: `[DRIVE] <sig>: old -> new` (real changes only), `[WAIT] n cycles`, `[TIMEOUT]` |
| Monitor | `u_mon` (`tb_<m>_mon`) | `clk_cnt`, every DUT pin: inputs as really applied, outputs | samples `s_*`, `s_vld`, sample time `s_time`, transfer status (`s_done`, `s_wait`, `s_setup`) | `[OBSERVE] <output>: old -> new` for outputs whose edges matter (e.g. an interrupt) |
| Golden reference model | `u_model` (`tb_<m>_model`) | `clk`, `rst_n`, monitor **input** samples | expected values `exp_*`; at most a short rule name for the note of a FAIL line (e.g. `err_text`) | nothing |
| Checker | `u_chk` (`tb_<m>_chk`) | `exp_*` from the model, output samples, sample time and transfer status from the monitor | PASS/FAIL decision, `tb_<m>.u_log.check` | one line per transfer at its completion (`APB WRITE`/`APB READ`), `[WATCH]` on a deviation, `[CHECK]` on a checkpoint; a FAIL carries its short context as a note on the same line |
| Logger / result collector | `u_log` (`tb_<m>_log`) | `clk_cnt`; header, info, check and error calls with the event time | consistent formatting of every line; owns `pass_count`/`fail_count` | prefix, `[SUMMARY]`, `Test_result` |
| DUT | `u_dut` | inputs from `u_drv`, `u_clk_rst` | outputs to `u_mon` (handshake also to `u_drv`) | – |

- Pin-level data flows through ports and `wire`s only: sequence → driver → DUT → monitor → model/checker → logger. Every `wire` has exactly one driving port. No component assigns a signal driven by another one, reads DUT internals or uses `force`/`deposit`.
- Transaction-level calls use tasks through the instance names of the top (sequence task → `u_drv.apb_write(...)` + `u_chk.sync`, `u_chk` → `u_model.err_text`, every component → `tb_<m>.u_log.info/check/error_msg` and `tb_<m>.u_log.fmt_*`); one call direction per pair, documented in the component header.
- Each operation is told once, on one line, by the component that knows its outcome: a bus transfer by the checker at its completion (address, data, strobe and result together), an input outside the bus by the driver when applied, a reset by the clock/reset generator. The model computes silently (no explanation lines). Never log an operation that has not happened (e.g. "write applied" for a request or a rejected transfer).
- Timing per cycle: `posedge` – DUT and model update, `clk_cnt` + 1; `posedge + #1` – driver/reset changes; `negedge` – monitor samples (the X→0 initialization of `clk` at time 0 is not an edge); `negedge + CHK_DLY` – checker compares and logs with the **sample time** `s_time` (a line shows when the stimulus was applied or the output was sampled, never when it was printed). Every sequence task of the top ends with `u_chk.sync` (returns after the checker processed its last sample), so a branch header printed after a sequence task, or before the first stimulus, precedes every check of that branch.
- Every variable has one owning process; a handshake between two processes uses a request/ack counter pair (one owner each).
- Each component has a header comment (role, ports received/driven, timing, callers, ownership). Do not add empty or pass-through components: a role the DUT does not need is left out (e.g. no clock/reset generator for a purely combinational DUT); an independent second protocol gets its own driver/monitor; a few simple sideband inputs stay in the main driver.

## 4. Naming

| Category | Rule |
|---|---|
| Name length | Prefer short, meaningful names. Avoid unnecessarily long or cryptic names. The previous 2–20 character range is a guideline, not a hard restriction. |
| Character type | Use lowercase for module names, port names, and variable names. |
| Character type | Use uppercase for parameters and `define` symbols. |
| Polarity | Append `_n` to active-low signals. |
| Others | Do not append version or revision information to a module name. |
| Others | Use meaningful instance names that identify the instance's role or function. Numeric suffixes may be used for repeated instances. For a single DUT, names such as `u_dut` are acceptable. |
| Others | Use meaningful and appropriate English names for readability. |

## 5. Module Connection

| Category | Rule |
|---|---|
| Port connection | Connect ports **by name only**. Do not use positional port connection. |

## 6. Test Data and Timing

### 6.1 Delay Usage

- Use a parameter to describe reusable clock/testbench timing values.
- Do **NOT** scatter hard-coded delay numbers throughout the testbench.
- Small one-off timing controls may use literals when they are directly tied to the test scenario and do not create repeated magic numbers.

Example:

```verilog
parameter CLK_PERIOD = 20;

initial begin
  clk = 1'b0;
end

always #(CLK_PERIOD / 2) clk = ~clk;
```

The default clock period is **20 ns** (`` `timescale 1ns/1ps ``, `CLK_PERIOD = 20`). If the DUT specification requires another period, use the specification value for that testbench.

### 6.2 Racing Problem

Every DUT input driven as part of normal stimulus sequencing is driven **one time unit after the rising clock edge**:

```verilog
@(posedge clk);
#1;
din = 8'hA5;
```

- Do **NOT** drive stimulus on the falling edge, exactly at the rising edge, or just before the rising edge. Do not replace `#1` with another delay.
- Do not make the clock rise at simulation time `0`.
- Sample/check DUT outputs after `@(posedge clk); #1;` as well (registered outputs show the value updated at that edge). Check a combinational output while the inputs producing it are still applied, before the next rising edge.
- Reset follows the DUT specification: an asynchronous reset may be asserted immediately; its release, and any synchronous reset, use `@(posedge clk); #1;`.
- Internal testbench bookkeeping (model state, counters, case names) is not stimulus and does not need this timing.

The `#1` belongs to the testbench only. The DUT itself must not be modified with simulation delays just to hide a testbench race.

## 7. Test Cases

The direct testbench should cover **all major specified functional behaviors** and the important boundary/exception cases that are relevant to the design.

This normally includes:

- Basic operations.
- Important boundary/corner cases.
- Relevant illegal or exceptional input combinations when the specification defines their behavior.

The objective is sufficient functional confidence for the project's scope, **not exhaustive functional coverage**.

Do not invent large numbers of corner cases that are unrelated to the specification just to make the testbench look comprehensive.

## 8. Self-Checking and Log Format

### 8.1 Expected Values: Golden Model Only

- **Every expected value used to decide PASS/FAIL is computed by an independent, hand-written golden model derived from the specification.** Test cases never pass an expected value; the checker has no task taking an expected literal (no `u_chk.expect_rdata(name, 32'h…)`). A number of the VPLAN `Pass condition` is never a substitute expected value.
- The VPLAN still decides the functions to test, the Item/Sub item grouping and the stimulus scenario (Test sequence). Dropping VPLAN literal checks never drops a test case or reduces scope: every leaf is implemented and every quantity its Pass condition names is still observed (through a transaction, the per-sample watch or a checkpoint) – only the source of the expected value changes.
- The Pass condition is used to review the model while the testbench is written: compare the `expected` values of the log with the VPLAN numbers. On a difference, check the specification: a wrong model is fixed; a wrong VPLAN is reported (stage S4), never copied into the testbench.
- When a check is required at a specific moment, the test case only requests the checkpoint – the quantity/transaction and the moment (e.g. a register read, `wait_cycles(n)` followed by `u_chk.checkpoint("…")`); the checker takes the matching expected value from the model at that sample.
- Reset values, register masks, formulas and latencies may appear in the model when the specification states them (cite the source in the model header).
- The model never reads a DUT output or DUT internal state as expected value and does not copy the RTL; it is written from the specification text (register map, formulas, behavior). It is updated by clock, reset and the stimulus **actually applied** (monitor input samples), and it distinguishes a request from an accepted transaction (a write takes effect when the model predicts the transfer completes and is accepted per specification, not when the driver issues it).
- If the specification defines a handshake latency, the model predicts the handshake itself and the checker checks the DUT handshake separately (timing, wait cycles). If the latency is open, the real handshake may tell the model only *when* a transaction happens; its validity per protocol (phase, `MAX_WAIT` limit → `[TIMEOUT]`) is still checked separately. The model never follows a DUT error and still passes.
- A wrong value read from the DUT is never loaded back into the model to hide the deviation; later checks keep comparing with the model prediction.
- Missing information in the specification that is needed for an expected value is reported (propose an OPEN for S1); VPLAN numbers are not used instead.
- Compare with `===`/`!==`; X/Z is a FAIL.

### 8.2 Checks and Counters

| Line | When | Expected (model) | Actual (DUT through the monitor) | Counted |
|---|---|---|---|---|
| `[<PROTO> WRITE <REG>] addr data strb OK\|SLVERR` | transfer completion sample, response as the model predicts | error flag and wait cycles | observed error flag and wait cycles | no – `OK` only says the transfer completed without error response; it is not a data check |
| `[<PROTO> WRITE <REG>] addr data strb expected: <e> actual: <a> FAIL` | same, response differs | `OK`/`SLVERR` or `N wait` | observed | one FAIL |
| `[<PROTO> READ <REG>] addr expected: <e> actual: <a> PASS\|FAIL` | completion of a read | register value (and response) | read data (and response) | one |
| `[WATCH] <output> (<bus situation>) expected: <e> actual: <a> FAIL` | first mismatching sample of an output outside a completion | `exp_*` | `s_*` | one FAIL per mismatch episode; closed by `[WATCH END]` (not counted) |
| `[CHECK] <output> <what> expected: <e> actual: <a> PASS\|FAIL` | `u_chk.checkpoint("<what>")` at a moment the test case names | `exp_*` of that output | `s_*` | one |

- Every sample is compared, nothing is printed while it matches. The first mismatch of an output prints its FAIL line at once (sample time, bus situation, expected, actual); further mismatches of that output are only counted and closed by one `[WATCH END]` line ("N mismatching sample(s) clk=a..b, matches the model again", not counted). A mismatch of another output, or of the same output after it matched again, prints its own FAIL. No deviation inside a wait is skipped.
- `pass_count`/`fail_count` belong to the logger only: `u_log.init` (once per Item, in `init_test`), `u_log.check` (exactly one counter per line ending in `PASS`/`FAIL`), `u_log.error_msg` (non-comparison failure: `TIMEOUT`, `PROTOCOL ERROR`, `LOG ERROR`). **PASS = number of lines ending in `PASS`; FAIL = number of lines ending in `FAIL` + error lines.** Event lines (`APB WRITE … OK`, `DRIVE`, `RESET`, `WAIT`, `OBSERVE`, `WATCH END`) are never counted. A DUT reset between branches never clears the counters.

### 8.3 One Test-Case File per Item

- Each **top-level VPLAN Item** is one test-case file `tc/<ID>.v`, `<ID>` = the Item ID `TC_<MODULE>_<NNN>` (e.g. `tc/TC_ACC_UNIT_001.v`). The ID is the execution ID used for the file name, `make -C sim all TESTNAME=<ID>` (no `+TEST`), `sim/pat.list` and `sim/log/<ID>.log`. Sub items never get their own file; they are traced by the path `<ID> › <Item> › <Sub item 1> › <Sub item 2>` (equal leaf names under different parents are told apart by the parent).
- One `initial` block (the single control flow): `init_test("<ID>", "<objective>")`, `u_log.item("<Item>")` (+ `u_log.goal`), the branch groups, `end_test`. `init_test`/`end_test` run once for the whole Item.
- Each Sub item 1 and Sub item 2 is a named block `begin : <snake_case_name> … end`, in VPLAN order, siblings consecutive. Its first statement is its header (`u_log.sub1(...)`/`u_log.sub2(...)`), then one short `u_log.goal(...)`, before any time-consuming statement; it contains only the stimulus of that branch. The first `reset_dut` comes after the headers of the first leaf. A reset between branches calls `reset_dut` again (DUT/model only).
- Test cases describe **stimulus only**, following the VPLAN Test sequence: sequence tasks of the top, `reset_dut`, logger headers and goals. Literals in a test case are stimulus (address, data, strobe, cycle counts) and descriptive text – never an expected value. An input outside the bus is changed at the next drive point after the previous operation (`set_dbg_mode(v)`); no wait or observation is inserted that the scenario does not need. Drivers, monitors, model, checker and utilities stay in the testbench environment; test cases declare no variables.

### 8.4 Log Format (read by `check_sim_log.py` and `sim/report.csh`)

The log is short: one line per operation that acts on the DUT and one per meaningful check, so the stimulus and the first wrong checkpoint are visible at a glance, and the branch headers tell which function of the specification is tested. The model is not explained in the log; a FAIL adds only the direct information needed to understand the deviation.

```text
[TEST] <ID>: <objective>
[TEST] <DUT, public ports, specification paths>
[TEST] Time: <t unit, clk = rising edges since time 0 never reset, drive / sample points>
[TEST] Checks: <expected source, what is compared every sample, meaning of OK>
[ITEM] <Item>
  [SUBITEM1] <Sub item 1>
    [GOAL] <one short objective>
    [SUBITEM2] <Sub item 2>
<prefix> [<TAG>] <text>                                             event, not counted
<prefix> [<TAG>] <text> expected: <e> actual: <a> PASS|FAIL [(<note>)]   check, counted once
<prefix> [TIMEOUT|PROTOCOL ERROR|LOG ERROR] <text>                   counted as FAIL
[SUMMARY] PASS=<n> FAIL=<n>
Test_result: PASSED|FAILED

<prefix> = [t=<ns> ns clk=<n>]
```

- **Context** `[TEST]`: a few lines printed once by `init_test`: test ID and objective, DUT and scope (public ports only), specification paths, the time/clock convention (described here once, not on every line) and the expected-value source.
- **Prefix** `[t=<ns> ns clk=<n>]`: simulation time of the event and `clk_cnt`, the number of rising edges since time 0 – initialized once at the start of the simulation, +1 at every rising edge, never reset (not by a DUT reset, `init_test`, a branch change or a new scenario). Every component uses this one source. The time is when the stimulus was applied (`posedge + 1`) or the output sampled (falling edge), not when the line was printed. No phase or transaction ID in the prefix.
- **Branch headers**: Item → Sub item 1 → Sub item 2 → lines of that leaf. `[ITEM]` once at the start; `[SUBITEM1]` once at the start of its group, its `[SUBITEM2]` consecutive below; parent names are never repeated on later lines. One- and two-level branches print only the levels that exist. A new parent clears the child context; `sub1` without an Item or `sub2` without a Sub item 1 prints `[LOG ERROR] …` and counts a failure. Names are the exact English VPLAN cell text (never the ID, never translated); `check_sim_log.py --items <vplan>` prints them. Header indentation (0/2/4 spaces) is for reading only. `[GOAL]`: one short line per branch, never repeated.
- **Minimum lines per operation**:

| Operation | Line | Emitted by |
|---|---|---|
| Bus write | `[APB WRITE TCR] addr: 0x000 data: 0x00000103 strb: 0b0011 OK` – one line at the completion sample (setup was driven 2 rising edges earlier with one wait state, stated once in `[TEST] Time`); a wait-state or response deviation turns it into a FAIL line whose note gives the wait cycles and setup `clk`, or the error condition of the model | `u_chk` |
| Bus read | `[APB READ TDR0] addr: 0x004 expected: 3 counts actual: 3 counts PASS` – captured data and verdict on one line, at the completion sample | `u_chk` |
| Input outside the bus | `[DRIVE] dbg_mode: 0 -> 1` when it really changes, at the time applied | `u_drv` |
| Reset | `[RESET] sys_rst_n = 0 (asserted for N rising edges)` / `[RESET] sys_rst_n = 1 (released)` | `u_clk_rst` |
| Wait that matters to the scenario | `[WAIT] 8 cycles, bus idle (clk=a..b)` – one line, never one per cycle | `u_drv` |
| Output edge that matters (e.g. interrupt) | `[OBSERVE] tim_int: 0 -> 1` | `u_mon` |

- Never split one transfer into request / setup / access / completion lines, never print a read response and then a check repeating the same data, never print model explanations (history, formulas, state updates), repeated PASS per cycle, a separate diagnosis line or a speculative cause.
- In an integration testbench, internal signals of a sub-module (e.g. `cnt_en`, `div_cnt`) never appear as measured values; their effect is checked through public outputs (e.g. TDR reads) against the model.
- `Test_result`: `PASSED` when FAIL = 0 and PASS > 0, otherwise `FAILED`; printed right after `[SUMMARY]` (read by `sim/report.csh`); no other line contains `Test_result`.

### 8.5 Radix by Meaning

| Quantity | Format | Logger function |
|---|---|---|
| Address, raw register data, configuration, mask, value whose bit/field position matters | hex with `0x`, full width | `fmt_hex(v, w)` |
| Byte strobe, control bit group whose single bits matter | binary with `0b` | `fmt_bin(v, w)` |
| Count, cycle count, length, quantity, arithmetic operand/result | decimal with unit (`5 counts`, `4 cycle(s)`) | `fmt_cnt(v, w)` / `fmt_dec(v, w)` / `fmt_sdec(v, w)` |
| Single control bit | `0`/`1` with its name | `fmt_bit(v)` |

- Raw transaction lines keep `addr`/`data` in hex to match the register map; a functional check presents its value by meaning (a counter read, TDR included: `expected: 256 counts actual: 256 counts`; a configuration register: `expected: 0x00000203 actual: 0x00000203`). A count is not printed in both hex and decimal unless that helps the diagnosis; the reader never converts hex to decimal.
- Expected and actual of one check share radix, unit and signedness; signed values show their sign per specification, unsigned counts never print as negative; full width is kept, 64-bit counters included (never through a 32-bit `integer`).
- An actual value with X/Z is a FAIL and is shown in raw hex/binary (`X/Z 0x0000000x`), never as a plausible decimal number.
- Hex digits are upper-case (`0x01C`); `x`/`z` stay lower-case.
- Radix changes only the text, never the width or the comparison. Values are not all passed through one fixed hex print function.

### 8.6 Context of a FAIL

A check line already carries the function (tag and branch), the time and clock, expected (model) and actual (DUT); the operations before it are the lines above. A deviation stays **one line**: when expected/actual alone do not tell what went wrong, the checker adds a short note in parentheses after `FAIL` – no separate diagnosis line.

| FAIL | Note | Example |
| --- | --- | --- |
| Count read (TDR) | none – decimal expected/actual already show the difference | `expected:   3 counts actual:   6 counts FAIL` |
| Register read (hex) | fields that differ | `expected: 0x00000003 actual: 0x00000001 FAIL (differ: HALT_ACK)` |
| Write response | wait cycles vs. model and setup `clk`, or the error condition of the model | `expected: SLVERR actual: OK FAIL (tim_pslverr 0, model: TCR error condition 1, DIV_VAL > 8)` |
| Watch | bus situation of the sample, in the text before `expected:` | `[WATCH] tim_pready (access cycle 2 of APB WRITE TCR, setup clk=3) expected: 1 actual: 0 FAIL` |
| X/Z | none – actual is shown raw | `actual: X/Z 0x0000000x FAIL` |

- No model history, no long analysis, no suspected cause: top-level outputs alone never establish which internal module or signal is broken. The FAIL line under its branch header is the first deviation; no `[FIRST FAIL]` repetition is needed. A timeout is a separate `[TIMEOUT]` line (with the setup `clk`).

### 8.7 Column Alignment

- Prefix fields right-aligned: `t=` in `TIME_W` (default 8), `clk=` in `CLK_W` (default 6).
- `[<TAG>]` left-aligned, padded to `TAG_W` (default 17); on read lines `<e>` and `<a>` right-aligned in `VAL_W` (default 10). A longer tag or value is never truncated, only that line shifts.
- Parameters in section 1, passed to the logger. Every line is printed by the logger (`info`, `check`, `error_msg`), using the Verilog-2005 helper functions `prefix`, `str_len`, `pad_left`, `pad_right`. Do not use field widths such as `%-40s` or `%8d` (SystemVerilog extension).
- Headers, `[GOAL]`, `[TEST]`, `[SUMMARY]` and `Test_result` are not padded.

Example (excerpt of a real run, `references/example_timer_top/log/TC_TIMER_TOP_012.log`):

```text
[ITEM] cnt_halt_chk
  [SUBITEM1] Halt in debug mode
    [GOAL] DIV_VAL 1 (1 step / 2 cycles): dbg_mode = 1 alone does not halt; HALT_REQ = 1 halts (TDR0 and divider phase held); HALT_REQ = 0 resumes
[t=       0 ns clk=     0] [RESET]           sys_rst_n = 0 (asserted for 2 rising edges)
[t=      31 ns clk=     2] [RESET]           sys_rst_n = 1 (released)
[t=     100 ns clk=     5] [APB WRITE TCR]   addr: 0x000 data: 0x00000103 strb: 0b0011 OK
[t=     160 ns clk=     8] [APB READ TDR0]   addr: 0x004 expected:   1 counts actual:   1 counts PASS
[t=     171 ns clk=     9] [DRIVE]           dbg_mode: 0 -> 1
[t=     240 ns clk=    12] [APB WRITE THCSR] addr: 0x01C data: 0x00000001 strb: 0b0001 OK
[t=     300 ns clk=    15] [APB READ THCSR]  addr: 0x01C expected: 0x00000003 actual: 0x00000003 PASS
[t=     360 ns clk=    18] [APB READ TDR0]   addr: 0x004 expected:   3 counts actual:   3 counts PASS
[t=     371 ns clk=    19] [WAIT]            8 cycles, bus idle (clk=19..26)
[t=     580 ns clk=    29] [APB READ TDR0]   addr: 0x004 expected:   3 counts actual:   3 counts PASS
[t=     640 ns clk=    32] [APB WRITE THCSR] addr: 0x01C data: 0x00000000 strb: 0b0001 OK
[t=     700 ns clk=    35] [APB READ THCSR]  addr: 0x01C expected: 0x00000000 actual: 0x00000000 PASS
[t=     760 ns clk=    38] [APB READ TDR0]   addr: 0x004 expected:   6 counts actual:   6 counts PASS
```

Same branch with a deliberately mutated scratch copy of `cnt_ctrl` (halt ignored; the unmodified RTL passes):

```text
[t=     300 ns clk=    15] [APB READ THCSR]  addr: 0x01C expected: 0x00000003 actual: 0x00000003 PASS
[t=     360 ns clk=    18] [APB READ TDR0]   addr: 0x004 expected:   3 counts actual:   6 counts FAIL
```

## 9. Signal Assignment Ownership

Every driven testbench signal has a single clear owner: DUT inputs belong to the driver, `clk`/`rst_n` to the clock/reset generator, samples to the monitor, expected values to the model, `pass_count`/`fail_count` to the logger.

Avoid assigning the same variable from multiple `always`/`initial` statements; a handshake between two processes uses a request/ack counter pair, one owner each.

## 10. Direct-Test Testbench Checklist

- [ ] Testbench top `tb/tb_<module>.v`, components `tb/tb_<module>_<role>.v` and test cases `tc/<ID>.v` are pure Verilog-2005 (no SystemVerilog constructs); `tb/` and `tc/` hold HDL only; components are listed in `sim/tb.f`.
- [ ] The nine sections are present in the testbench top, in the mandatory order with visible headers.
- [ ] Driver, monitor, model, checker, logger and clock/reset generator are modules connected by named ports/wires (no empty or pass-through component); every wire has one driver; no DUT internal signal is read, forced or deposited.
- [ ] Every expected value comes from the golden model (spec-based, independent, no DUT output, no DUT internal state, no copied RTL); test cases pass no expected value and the checker has no expected-literal task; VPLAN numbers only review the model.
- [ ] The DUT handshake is checked against the model or the protocol separately; the model is never re-synchronized from a DUT value.
- [ ] Comments use `//` only.
- [ ] Comments are written in English.
- [ ] Header describes the testbench clearly.
- [ ] Indentation uses 2 spaces.
- [ ] `begin/end` pairs are not omitted for statement blocks.
- [ ] No unnecessarily large `always` block is used.
- [ ] Names are short, meaningful, and consistent with project rules.
- [ ] Instance names are meaningful rather than being forced into a fixed numeric pattern.
- [ ] DUT ports are connected by name.
- [ ] Reusable delays are parameterized; default `CLK_PERIOD = 20` unless the specification says otherwise.
- [ ] Every DUT input is driven by the driver with `@(posedge clk); #1;` (no falling-edge or at-edge stimulus); the monitor samples at the falling edge, the checker compares at falling edge + `CHK_DLY` and logs with the sample time; every sequence task ends with `u_chk.sync`.
- [ ] Clock does not rise at simulation time 0.
- [ ] Only the logger updates `pass_count`/`fail_count` and prints lines; PASS = lines ending in `PASS`, FAIL = lines ending in `FAIL` + error lines; event lines (`… OK`, `DRIVE`, `RESET`, `WAIT`, `OBSERVE`, `WATCH END`) are never counted; `[SUMMARY] PASS=<n> FAIL=<n>` and `Test_result: PASSED|FAILED` are printed at the end; a reset between branches keeps the counters.
- [ ] The log is short: a few `[TEST]` lines, one short `[GOAL]` per branch, prefix `[t=<ns> ns clk=<n>]` with `clk` counted from time 0 and never reset, one line per transfer / input change / reset / meaningful wait, no model explanation, no repeated PASS per cycle; the first FAIL appears at once, on one line, with expected, actual, time, clock and – when needed – a short note in parentheses.
- [ ] Values use the radix of their meaning (hex for addresses/raw data/configuration, binary for strobes, decimal with unit for counts/cycles); expected and actual share radix, unit and signedness; X/Z shown raw.
- [ ] Each top-level VPLAN Item is one test-case file `tc/<ID>.v` with one `initial` block, named blocks per branch in VPLAN order, and `[ITEM]`/`[SUBITEM1]`/`[SUBITEM2]` headers printed once per branch; every check belongs to a leaf.
- [ ] Test cases cover all major specified behaviors and important boundary/exception cases.
- [ ] Driven testbench signals have clear procedural ownership.

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
| 1 | Declaration | `CLK_PERIOD`, `RESET_CYCLES`, `TIMEOUT_NS`, `CHK_DLY`, `TIME_W`/`NAME_W`/`VAL_W`; every `wire` between the DUT and the components, each commented with its single driver (`// u_drv`); every variable used by the test cases. |
| 2 | DUT Instance | `u_dut`, connected by name. |
| 3 | Clock Generation | Clock/reset generator instance `u_clk_rst`. |
| 4 | Init Reset | `reset_dut`: driver to idle now, reset applied per specification through `u_clk_rst`. Resets the DUT and the model (the model follows `rst_n`); never clears the result counters. |
| 5 | Golden Reference Model | Model instance `u_model`. |
| 6 | Checker | Observation and result path: monitor `u_mon`, checker `u_chk`, logger `u_log`. |
| 7 | Helper Functions | Small functions of the top actually needed (usually empty). |
| 8 | Tasks | Stimulus path: driver instance `u_drv`; sequence tasks shared by several test cases; `init_test` (`u_log.init`, checker enable, plusargs) and `end_test` (`u_log.summary`, `$finish`). |
| 9 | Main Program Body | `` `include "run_test.v" `` (sequence of the selected Item) and the global timeout (`u_log.error_msg("[TIMEOUT] …")`, `end_test`). |

### 3.2 Testbench Components and Connections

The environment is built from Verilog-2005 modules with real ports, one file each, flat in `tb/`, named `tb_<module>_<role>` (prefix avoids name clashes between DUTs and with RTL modules) and listed in `sim/tb.f` before the testbench top.

| Role | Instance | Receives | Drives / produces |
|---|---|---|---|
| Test sequence / controller | `initial` block of `tc/<ID>.v` | – | calls tasks of `u_drv`, `u_clk_rst`, `u_chk` (`expect_*`), `u_log` (branch headers) |
| Clock/reset generator | `u_clk_rst` (`tb_<m>_clk_rst`) | – | `clk`, `rst_n` (only driver) |
| Protocol driver (e.g. APB master) | `u_drv` (`tb_<m>_drv`) | `clk`, DUT handshake outputs the protocol needs | every DUT input except clock/reset (only driver) |
| Monitor | `u_mon` (`tb_<m>_mon`) | every DUT pin: inputs as really applied, outputs | samples `s_*`, `s_vld`; completed transactions when useful |
| Golden reference model | `u_model` (`tb_<m>_model`) | `clk`, `rst_n`, monitor **input** samples | expected values `exp_*` |
| Checker | `u_chk` (`tb_<m>_chk`) | `exp_*` from the model, output samples from the monitor | results to `tb_<m>.u_log.result` |
| Logger / result collector | `u_log` (`tb_<m>_log`) | header and result calls | the log; owns `pass_count`/`fail_count` |
| DUT | `u_dut` | inputs from `u_drv`, `u_clk_rst` | outputs to `u_mon` (handshake also to `u_drv`) |

- Pin-level data flows through ports and `wire`s only: sequence → driver → DUT → monitor → model/checker → logger. Every `wire` has exactly one driving port. No component assigns a signal driven by another one or reads DUT internals.
- Transaction-level calls use tasks through the instance names of the top (`u_drv.apb_write(...)`, `u_chk.expect_rdata(...)`, `tb_<m>.u_log.result(...)`); one call direction per pair, documented in the component header.
- The model computes expected values independently from the specification/VPLAN, using clock, reset and the DUT inputs sampled by the monitor. It never takes a DUT output as expected value and does not copy the RTL structure. A DUT handshake whose latency the specification leaves open may only tell the model *when* a transaction happens, never its expected value; say so in the model header.
- Timing per cycle: `posedge` – DUT and model update; `posedge + #1` – driver/reset changes, branch headers; `negedge` – monitor samples (the X→0 initialization of `clk` at time 0 is not an edge); `negedge + CHK_DLY` – checker compares, then `expect_*` returns. Branch headers are printed only at `posedge + #1` or right after `expect_*` returns, so every check belongs to the open branch.
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

- Expected values come from the golden reference model or from the VPLAN pass condition, both derived from the specification. Never derive the expected value from a DUT output.
- Two kinds of checks, both through the checker and the logger: **automatic** (every valid monitor sample, model `exp_*` vs DUT output) and **VPLAN** (`u_chk.expect_<x>(name, value)`: the numeric Pass-condition value of the leaf vs the next monitor sample). Compare with `===`/`!==`; X/Z is a FAIL.
- `pass_count`/`fail_count` belong to the logger only: `u_log.init` (once per Item, in `init_test`), `u_log.result` (exactly one counter per comparison), `u_log.error_msg` (non-comparison failure: timeout, header misuse). A DUT reset between branches never clears them.

### 8.1 One Test-Case File per Item

- Each **top-level VPLAN Item** is one test-case file `tc/<ID>.v`, `<ID>` = the Item ID `TC_<MODULE>_<NNN>` (e.g. `tc/TC_ACC_UNIT_001.v`). The ID is the execution ID used for the file name, `make -C sim all TESTNAME=<ID>` (no `+TEST`), `sim/pat.list` and `sim/log/<ID>.log`. Sub items never get their own file; they are traced by the path `<ID> › <Item> › <Sub item 1> › <Sub item 2>` (equal leaf names under different parents are told apart by the parent).
- One `initial` block (the single control flow): `init_test`, `u_log.item("<Item>")`, the branch groups, `end_test`. `init_test`/`end_test` run once for the whole Item.
- Each Sub item 1 and Sub item 2 is a named block `begin : <snake_case_name> … end`, in VPLAN order, siblings consecutive. Its first statement is its header (`u_log.sub1(...)`/`u_log.sub2(...)`), before any time-consuming statement; it contains only the stimulus and checks of that branch. The first `reset_dut` comes after the headers of the first leaf. A reset between branches calls `reset_dut` again (DUT/model only).
- Test cases describe scenarios: driver/reset tasks, `u_chk.expect_*` with VPLAN values, logger headers. Drivers, monitors, model, checker and utilities stay in the testbench environment; test cases declare no variables.

### 8.2 Log Format (read by `check_sim_log.py` and `sim/report.csh`)

```text
[ITEM] <Item>
  [SUBITEM1] <Sub item 1>
    [SUBITEM2] <Sub item 2>
[<time>] <case> PASS | expected: <exp> | actual: <act>
[<time>] <case> FAIL | expected: <exp> | actual: <act>
[SUMMARY] PASS=<n> FAIL=<n>
Test_result: PASSED|FAILED
```

Fields:

- Branch headers: Item → Sub item 1 → Sub item 2 → check lines of that leaf. `[ITEM]` once at the start; `[SUBITEM1]` once at the start of its group, its `[SUBITEM2]` consecutive below; parent names are never repeated before each check. One- and two-level branches print only the levels that exist. A new parent clears the child context (`item` clears Sub item 1, `sub1` clears Sub item 2); `sub1` without an Item or `sub2` without a Sub item 1 prints `[LOG ERROR] …` and counts a failure. Names are the exact English VPLAN cell text (never the ID, never translated); `check_sim_log.py --items <vplan>` prints them. Header indentation (0/2/4 spaces) is for reading only; check lines are not indented.
- Every check line follows the header of its own leaf, including automatic per-cycle checks and checks during reset/setup.
- `<time>`: current simulation time (`$time`, ns), right-aligned in `TIME_W` digits inside the brackets.
- `<case>`: a short name without spaces describing the important input characteristics of the case (e.g. `addr_0_wdata_A5A5A5A5`, `valid_1_ready_0`); never a generic name like `CASE_001` or `TEST_01`.
- `PASS`/`FAIL`: checker result; `expected`: model value (automatic check) or VPLAN value (VPLAN check); `actual`: DUT value from the monitor (printed with `%h`, right-aligned in `VAL_W` digits).
- Keep the exact separator `| expected: ... | actual: ...`.
- **Column alignment:** every case line of a log is aligned in columns, whatever the case-name length or value width:
  - `<time>` right-aligned in `TIME_W` digits (default 8);
  - `<case>` left-aligned, padded with spaces to `NAME_W` characters (default 40; choose it ≥ the longest case name of the testbench – a longer name is never truncated, only that line shifts);
  - `<exp>` and `<act>` right-aligned in `VAL_W` digits (= the `%h` digits of the widest compared signal).
  - `TIME_W`, `NAME_W`, `VAL_W` are parameters in section 1, passed to the logger. Every check line is printed by one logger task `result`, using the Verilog-2005 helper functions `str_len`, `pad_left`, `pad_right` of the logger. Do not use field widths such as `%-40s` or `%8d` (SystemVerilog extension).
  - `[SUMMARY]`, `Test_result` and the branch headers are not padded.
- `Test_result`: `PASSED` when FAIL = 0 and PASS > 0, otherwise `FAILED`; printed right after `[SUMMARY]` (read by `sim/report.csh`).

Example:

```text
[ITEM] Register access
  [SUBITEM1] DATA Register 0
    [SUBITEM2] Reset value check
[      61] rd_addr_0                                PASS | expected: 00000000 | actual: 00000000
    [SUBITEM2] Read/write access
[     141] addr_0_wdata_A5A5A5A5                    PASS | expected: a5a5a5a5 | actual: a5a5a5a5
  [SUBITEM1] DATA Register 1
    [SUBITEM2] Reset value check
[     221] rd_addr_8                                FAIL | expected: ffffffff | actual: 0000000x
[SUMMARY] PASS=2 FAIL=1
Test_result: FAILED
```

## 9. Signal Assignment Ownership

Every driven testbench signal has a single clear owner: DUT inputs belong to the driver, `clk`/`rst_n` to the clock/reset generator, samples to the monitor, expected values to the model, `pass_count`/`fail_count` to the logger.

Avoid assigning the same variable from multiple `always`/`initial` statements; a handshake between two processes uses a request/ack counter pair, one owner each.

## 10. Direct-Test Testbench Checklist

- [ ] Testbench top `tb/tb_<module>.v`, components `tb/tb_<module>_<role>.v` and test cases `tc/<ID>.v` are pure Verilog-2005 (no SystemVerilog constructs); `tb/` and `tc/` hold HDL only; components are listed in `sim/tb.f`.
- [ ] The nine sections are present in the testbench top, in the mandatory order with visible headers.
- [ ] Driver, monitor, model, checker, logger and clock/reset generator are modules connected by named ports/wires (no empty or pass-through component); every wire has one driver.
- [ ] The model uses only clock, reset and monitor input samples; the checker compares model/VPLAN expected values with monitor samples and reports to the logger.
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
- [ ] Every DUT input is driven by the driver with `@(posedge clk); #1;` (no falling-edge or at-edge stimulus); the monitor samples at the falling edge, the checker compares at falling edge + `CHK_DLY`.
- [ ] Clock does not rise at simulation time 0.
- [ ] Expected values come from an independent golden reference model.
- [ ] Only the logger updates `pass_count`/`fail_count` and prints check lines; `[SUMMARY] PASS=<n> FAIL=<n>` and `Test_result: PASSED|FAILED` are printed at the end; a reset between branches keeps the counters.
- [ ] Each top-level VPLAN Item is one test-case file `tc/<ID>.v` with one `initial` block, named blocks per branch in VPLAN order, and `[ITEM]`/`[SUBITEM1]`/`[SUBITEM2]` headers printed once per branch; every check belongs to a leaf.
- [ ] Case names describe the important input characteristics (no generic `CASE_001`).
- [ ] Test cases cover all major specified behaviors and important boundary/exception cases.
- [ ] Driven testbench signals have clear procedural ownership.

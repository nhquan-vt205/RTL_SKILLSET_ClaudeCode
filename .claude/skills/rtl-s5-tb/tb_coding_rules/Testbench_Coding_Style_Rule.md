# Testbench Coding Style Rule

## 1. Scope

This document is the testbench coding-style rule converted from the `tb_check_item` sheet in the provided `RTL_Coding_Style_Rule(1).xlsx`.

The scope is a **direct, self-checking simulation testbench** written in **Verilog-2005 (IEEE 1364-2005)**, file `tb/<module>/tb_<module>.v`. SystemVerilog-only constructs (`logic`, `bit`, `string`, `always_ff`, `always_comb`, `always_latch`, `typedef`, `enum`, `struct`, `interface`/`modport`, `package`, `class`, `foreach`, queues, dynamic arrays, `mailbox`, SV casts, `$fatal`, SVA) shall **NOT** be used. The rules below do not introduce UVM, coverage, constrained-random or assertion-based verification.

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

### 3.1 Mandatory Section Order

Every testbench file contains these nine sections, in this order, each opened by a visible header comment (`// ====…` / `// 1. Declaration` / `// ====…`). Keep all nine headers even in a small testbench; leave a section empty instead of writing meaningless code.

| # | Section | Content |
|---|---|---|
| 1 | Declaration | `CLK_PERIOD` and other TB parameters, DUT signals, golden-model state, `pass_count`/`fail_count`, test-selection and case-name variables. |
| 2 | DUT Instance | `u_dut`, connected by name. |
| 3 | Clock Generation | `initial clk = 1'b0;` + `always #(CLK_PERIOD / 2) clk = ~clk;` |
| 4 | Init Reset | Reset task: all DUT inputs to idle, reset applied per specification, golden model reset. |
| 5 | Golden Reference Model | Reference state and tasks/functions computing expected values from the specification/VPLAN. |
| 6 | Checker | Compare task(s): update PASS/FAIL counters and print the standard log line. |
| 7 | Helper Functions | Small functions actually needed (e.g. `+TEST` selection). |
| 8 | Tasks | Protocol/driver tasks, then one test-case task per VPLAN item. |
| 9 | Main Program Body | Main `initial` (counters, plusargs, reset, test cases, summary, `$finish`) and the global timeout. |

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

- Expected values come from the golden reference model, derived from the specification/VPLAN. Never derive the expected value from a DUT output.
- Keep `integer pass_count;` and `integer fail_count;`, initialized to 0. Each checker comparison increments exactly one of them, so PASS + FAIL = number of comparisons.
- Each VPLAN item is one test-case task in section 8, named after its VPLAN ID (e.g. `tc_acc_unit_001`). Do not create separate testbench files per item. VPLAN IDs are used for task names, `+TEST=<ID>` selection and reporting.
- Log format (read by `check_sim_log.py`):

```text
-- <item name> test --
[<time>] <case> PASS | expected: <exp> | actual: <act>
[<time>] <case> FAIL | expected: <exp> | actual: <act>
[SUMMARY] PASS=<n> FAIL=<n>
```

Fields:

- `<item name>`: a concise, human-readable VPLAN item name that still distinguishes the item (not replaced by the VPLAN ID). Use the most specific VPLAN field and add a parent field only when needed to tell items apart (e.g. `DATA Register 0 / Reset value check`, not `Register access / DATA Register 0 / Reset value check`). `check_sim_log.py --items <vplan>` lists the expected headers.
- `<time>`: current simulation time (`$time`, ns).
- `<case>`: a short name without spaces describing the important input characteristics of the case (e.g. `addr_0_wdata_A5A5A5A5`, `valid_1_ready_0`); never a generic name like `CASE_001` or `TEST_01`.
- `PASS`/`FAIL`: checker result; `expected`: golden-model value; `actual`: DUT value (printed with `%h`).
- Keep the exact separator `| expected: ... | actual: ...`.

Example:

```text
-- APB write test --
[61] addr_0_wdata_A5A5A5A5 PASS | expected: A5A5A5A5 | actual: A5A5A5A5
-- handshake test --
[181] valid_1_ready_0 FAIL | expected: 0 | actual: 1
[SUMMARY] PASS=1 FAIL=1
```

## 9. Signal Assignment Ownership

Prefer a single clear procedural owner for each driven testbench signal.

Avoid assigning the same variable from multiple `always`/`initial` statements unless the ownership and scheduling are intentional and unambiguous.

## 10. Direct-Test Testbench Checklist

- [ ] Testbench is pure Verilog-2005 in `tb/<module>/tb_<module>.v` (no SystemVerilog constructs).
- [ ] The nine sections are present in the mandatory order with visible headers.
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
- [ ] Every DUT input is driven with `@(posedge clk); #1;` (no falling-edge or at-edge stimulus).
- [ ] Clock does not rise at simulation time 0.
- [ ] Expected values come from an independent golden reference model.
- [ ] The checker updates `pass_count`/`fail_count` and prints the standard log line; `[SUMMARY] PASS=<n> FAIL=<n>` is printed at the end.
- [ ] Each VPLAN item prints `-- <item name> test --` (human-readable VPLAN item name) and is implemented as one test-case task.
- [ ] Case names describe the important input characteristics (no generic `CASE_001`).
- [ ] Test cases cover all major specified behaviors and important boundary/exception cases.
- [ ] Driven testbench signals have clear procedural ownership.

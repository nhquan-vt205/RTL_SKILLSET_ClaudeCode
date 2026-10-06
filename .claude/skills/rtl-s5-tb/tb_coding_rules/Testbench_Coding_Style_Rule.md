# Testbench Coding Style Rule

## 1. Scope

This document is the testbench coding-style rule converted from the `tb_check_item` sheet in the provided `RTL_Coding_Style_Rule(1).xlsx`.

The scope is a **direct simulation testbench**. The rules below do not introduce UVM, coverage, or assertion-based verification.

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

```systemverilog
parameter CLK_PERIOD = 10;

always #(CLK_PERIOD/2) clk = ~clk;
```

### 6.2 Racing Problem

- Do not intentionally change stimulus at the same simulation event as the clock rising edge.
- Do not make the clock rise at simulation time `0`.
- Schedule stimulus so DUT/testbench race conditions do not determine the test result.

The DUT itself must not be modified with simulation delays just to hide a testbench race.

## 7. Test Cases

The direct testbench should cover **all major specified functional behaviors** and the important boundary/exception cases that are relevant to the design.

This normally includes:

- Basic operations.
- Important boundary/corner cases.
- Relevant illegal or exceptional input combinations when the specification defines their behavior.

The objective is sufficient functional confidence for the project's scope, **not exhaustive functional coverage**.

Do not invent large numbers of corner cases that are unrelated to the specification just to make the testbench look comprehensive.

## 8. Signal Assignment Ownership

Prefer a single clear procedural owner for each driven testbench signal.

Avoid assigning the same variable from multiple `always`/`initial` statements unless the ownership and scheduling are intentional and unambiguous.

## 9. Direct-Test Testbench Checklist

- [ ] Comments use `//` only.
- [ ] Comments are written in English.
- [ ] Header describes the testbench clearly.
- [ ] Indentation uses 2 spaces.
- [ ] `begin/end` pairs are not omitted for statement blocks.
- [ ] No unnecessarily large `always` block is used.
- [ ] Names are short, meaningful, and consistent with project rules.
- [ ] Instance names are meaningful rather than being forced into a fixed numeric pattern.
- [ ] DUT ports are connected by name.
- [ ] Reusable delays are parameterized.
- [ ] Stimulus does not intentionally change at the same clock rising event.
- [ ] Clock does not rise at simulation time 0.
- [ ] Test cases cover all major specified behaviors and important boundary/exception cases.
- [ ] Driven testbench signals have clear procedural ownership.

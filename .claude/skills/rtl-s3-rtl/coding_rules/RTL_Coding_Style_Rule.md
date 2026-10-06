# RTL Coding Style Rule

## 1. Scope

This document is the RTL coding-style rule converted from the provided `RTL_Coding_Style_Rule(1).xlsx`.

The scope is RTL module implementation in **Verilog-2005 (IEEE 1364-2005)**, files `rtl/<module>.v`. SystemVerilog-only constructs (`logic`, `always_ff`, `always_comb`, `always_latch`, `typedef`, `enum`, `struct`, `interface`/`modport`, `package`, `class`, `unique`/`priority case`, `inside`, `foreach`, `'0`/`'1` literals, SV casts, SVA) shall **NOT** be used in RTL. The rules are organized by category so they can be used directly as a code-review checklist.

These rules define **coding style and implementation quality**. They do not replace the RTL skill flow or make optional verification stages mandatory.

## 2. Rule Summary

### 2.1 Logic Correctness

| Category | Rule |
|---|---|
| RTL – Document match | RTL must implement the specified behavior and architecture. It does not need to reproduce the design document or diagram literally, and reasonable helper signals/implementation details are allowed. |
| Correctness confirmation by simulation | When S4/S5 verification is performed, the simulation shall complete without unexpected errors. Simulation is not a mandatory S1–S3 gate unless the project explicitly requires it. |

### 2.2 Comment

| Category | Rule |
|---|---|
| Notation | Only use `//`. Do **NOT** use `/* */`. |
| Comment sentence | Comments must be written in English only; do not use other languages including Vietnamese. |
| Comment for register-type variables | Clarify the intended role of important state/register variables when it improves readability. Do not add comments merely to satisfy traceability requirements. |

### 2.3 Format

| Category | Rule |
|---|---|
| Header & Revision | Use a meaningful header to describe the module. |
| Header & Revision | Use meaningful revision information when module changes need to be recorded. Do not maintain a separate history artifact just for coding style. |
| Indentation | Use **2 spaces** for indentation instead of TAB. |
| Blank line | Use blank lines to improve readability. |
| Begin-end pair | Do not omit `begin/end` pairs when a conditional or sequential construct contains a statement block. |
| Bit-stream declaration | Use `_` to improve readability of literal values. Example: `8'b01101100` → `8'b01_10_11_00`. |

### 2.4 Naming

| Category | Rule |
|---|---|
| Name length | Prefer short, meaningful names. Avoid unnecessarily long or cryptic names. The previous 2–20 character range is a guideline, not a hard restriction. |
| Character type | Use lowercase for module names, port names, and variable names. |
| Character type | Use uppercase for parameters and `define` symbols. |
| Polarity | Append `_n` to active-low signals. |
| Others | Do not append version or revision information to a module name. |
| Others | Use meaningful instance names that identify the instance's role or function. Numeric suffixes may be used for repeated instances. For a single DUT, names such as `u_dut` are acceptable. |
| Others | Name module `INPUT`/`OUTPUT` ports exactly as specified in the specification. |
| Others | Use meaningful and appropriate English names for readability. |

### 2.5 Declaration

| Category | Rule |
|---|---|
| Declaration line | Use one declaration per line. |
| Declaration type | Use `wire` for signals driven by `assign`, sub-module outputs, and internal nets. Use `reg` for every signal assigned inside an `always` block (registers `_q` and next values `_d`). An output assigned in an `always` block is declared `output reg`. Do **NOT** use `logic`. |
| Declaration organization | Organize declarations so clock/reset, inputs, outputs, state/registers, and combinational/internal signals are easy to identify. |
| Initial value | Do not assign an initial value in synthesizable RTL declarations unless the target technology/project explicitly requires and supports it. |
| Assignment | Do **NOT** use net-declaration assignment unless it significantly improves readability and is compatible with the target flow. |
| Vector signal | Use `[n:0]` declaration style. Do not use `[0:n]`. |
| Explicit declaration | Declare **ALL** used variables. Do not omit declarations. |
| Declaration order | Prefer: **clock/reset → input → output → state/register → internal combinational signal**. Keep the order consistent within the project. |

### 2.6 Module Connection

| Category | Rule |
|---|---|
| Port connection | Connect ports **by name only**. Do not use positional port connection. |

### 2.7 Always Statement

#### Sequential / FF Logic

| Rule |
|---|
| Write only the relevant clock and reset edge signals in the sensitivity list when using an event-control style `always` block. |
| Use the reset polarity specified by the design. Do not assume positive- or negative-active reset unless the project/specification defines it. |
| Use only non-blocking assignment `<=` for sequential state updates. |
| Do **NOT** add simulation delay to synthesizable sequential RTL. Race conditions must be handled by the testbench/simulation scheduling, not by adding delay to the DUT. |
| Write sequential logic as `always @(posedge clk ...)` (with `or negedge rst_n` for asynchronous active-low reset). Do **NOT** use `always_ff`. |
| Keep the clock declaration/order consistent with project style; do not add ordering rules that depend on tool-specific behavior. |

#### Combinational Logic

| Rule |
|---|
| Write combinational logic as `always @(*)` or continuous `assign`. Do **NOT** use `always_comb`. Assign a default value at the top of each `always @(*)` block (e.g. `count_d = count_q;`). |
| Assign values to all LHS variables on all possible paths to avoid inferred latches. |
| Use only blocking assignment `=` for combinational procedural logic. |
| Do **NOT** add delay. |
| Do **NOT** create one unnecessarily large `always` block for many unrelated signals; separate logic into blocks when that improves readability. |
| Do **NOT** create a timing loop. Timing loops are prohibited for normal synthesizable RTL. |

#### Common

| Rule |
|---|
| Do **NOT** mix sequential and combinational logic in the same procedural block. Separate them. |
| Avoid driving the same variable from multiple procedural blocks. Prefer a single clear owner for each signal/state variable. |
| Do **NOT** mix synchronous and asynchronous control semantics in one block unless the design explicitly requires them and the coding style is clear. |

### 2.8 If / Case Statement

#### If Statement

| Rule |
|---|
| Avoid deeply nested `if` statements. Prefer no more than two levels when practical; refactor deeper nesting when it improves readability. |

#### Case Statement

| Rule |
|---|
| Use `if` or `case` based on readability and the structure of the decision logic. |
| Do **NOT** use `casex`. |
| List similar cases with comma-separated case items when appropriate. |
| Do not use `default` as a substitute for normal functional paths. |
| Include a `default` case when required to define safe behavior for unexpected/non-normal states or values. |

### 2.9 Other

| Category | Rule |
|---|---|
| State machine & other control signal | Keep state-machine behavior and control priority consistent with the specified architecture. Do not impose a generic priority scheme unless the specification defines it. |
| State machine encoding | Encode states with `localparam` (e.g. `localparam STATE_IDLE = 2'b00;`) and hold the state in `reg state_q` with next state `reg state_d`: one register block plus one `always @(*)` next-state block with a `default` branch to a safe state. Do **NOT** use `typedef enum`. |
| Data structure | Do **NOT** use `typedef struct`. Use separate signals/vectors per field (e.g. `item_valid`, `item_data`). |
| Bit-width matching | Avoid unintended truncation, extension, or signedness conversion. Explicitly size/cast signals when needed. Exact LHS/RHS width equality is not required in every legal Verilog expression. |
| X-Value | Do not intentionally introduce reachable X/Z values in synthesizable functional RTL. |
| Parameter/Define usage | Use `parameter` only for values the specification defines as configurable, and then use it for every related width. If the specification fixes a width or count, write it explicitly (`reg [7:0] count_q;`); do **NOT** create new parameters just to make code generic. |
| Parameter/Define usage | Use `localparam` for state encoding and named architectural constants (address, fixed threshold) where it improves readability. |
| Parameter/Define usage | Do **NOT** build complex macros, generic frameworks, or functions that only save a few lines. Use `generate` only when the architecture really contains repeated identical structures. |

## 3. RTL Review Checklist

Before submitting an RTL module, verify:

- [ ] RTL implements the specified behavior and architecture.
- [ ] If S4/S5 verification is performed, simulation completes without unexpected errors.
- [ ] Header and revision information are meaningful.
- [ ] Comments use `//` and English only.
- [ ] Indentation uses 2 spaces.
- [ ] `begin/end` pairs are explicit for statement blocks.
- [ ] Naming and active-low polarity follow the project rules; instance names are meaningful.
- [ ] All signals are explicitly declared and organized consistently.
- [ ] Vector declarations use `[n:0]`.
- [ ] Module connections use named ports only.
- [ ] Sequential logic uses the specified clock/reset and non-blocking assignments.
- [ ] RTL is pure Verilog-2005 (`wire`/`reg`, no `logic`/`always_ff`/`always_comb`/`typedef`/`enum`/`struct`).
- [ ] Sequential logic uses `always @(posedge ...)`; combinational logic uses `always @(*)` or `assign`.
- [ ] Sequential and combinational logic are not mixed in one procedural block.
- [ ] No unintended latch, timing loop, or intentional reachable X/Z behavior is introduced.
- [ ] `case`/`if` structures are appropriate and not unnecessarily deep.
- [ ] No unintended width/signedness conversion is present.
- [ ] Parameters exist only where the specification requires configurability; FSM states use `localparam`.

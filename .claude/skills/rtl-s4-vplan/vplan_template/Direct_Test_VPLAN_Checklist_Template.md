# Direct Test VPLAN Checklist Template

## 1. Purpose

This template is derived from the provided `register_checklist.xlsx`.

It is intentionally reduced to the columns required for a **direct simulation test**:

| Column | Purpose |
|---|---|
| ID | Unique test-item identifier. |
| Item | Main feature/function being verified. |
| Sub item 1 | First-level functional grouping. |
| Sub item 2 | Specific test/check. |
| Test sequence | Stimulus and checking sequence performed by the direct testbench. |
| Pass condition | Objective condition used to decide PASS/FAIL. |

The following are intentionally excluded from this direct-test template:

- UVM-specific fields.
- Coverage fields.
- Formal assertion fields.
- Test planning dates.
- PIC/owner fields that are not required to execute the direct test.

## 2. Direct Test VPLAN – Illustrative Example

> **Important:** The table below is an example format based on a register-block test. It is **not a universal test requirement** and must be replaced/adapted to the actual DUT specification.
>
> For a very small DUT, the VPLAN may contain only the few test items needed to demonstrate its major specified behaviors.

| ID | Item | Sub item 1 | Sub item 2 | Test sequence | Pass condition |
|---:|---|---|---|---|---|
| 1 | Register access | DATA Register 0 | Reset value check | After reset is released, read DATA register 0 at offset `0x0`. | Read value = `32'h0000_0000` |
| 2 | Register access | DATA Register 0 | R/W access | 1. Write `0000_0000` and read back. 2. Write `FFFF_FFFF` and read back. 3. Write `5555_5555` and read back. 4. Write `AAAA_AAAA` and read back. | Read value is the same as the written value. |
| 3 | Register access | DATA Register 1 | Reset value check | After reset is released, read DATA register 1 at offset `0x8`. | Read value = `32'hFFFF_FFFF` |
| 4 | Register access | DATA Register 1 | R/W access | 1. Write `0000_0000` and read back. 2. Write `FFFF_FFFF` and read back. 3. Write `5555_5555` and read back. 4. Write `AAAA_AAAA` and read back. | Read value is the same as the written value. |
| 5 | Register access | Status Register 0 | Reset value check | After reset is released, read Status register 0 at offset `0x4`. | Read value = `32'h0000_0000` |
| 6 | Register access | Status Register 0 | R/W access | 1. Write `0000_0000` to DATA0 and read status. 2. Write `FFFF_FFFF` to DATA0 and read status. 3. Write `5555_5555` to DATA0 and read status. 4. Write `AAAA_AAAA` to DATA0 and read status. | Read value is always equal to DATA0 register. |
| 7 | Register access | Status Register 1 | Reset value check | After reset is released, read Status register 1 at offset `0xC`. | Read value = `32'hFFFF_FFFF` |
| 8 | Register access | Status Register 1 | R/W access | 1. Write `0000_0000` to DATA1 and read status. 2. Write `FFFF_FFFF` to DATA1 and read status. 3. Write `5555_5555` to DATA1 and read status. 4. Write `AAAA_AAAA` to DATA1 and read status. | Read value is always equal to DATA1 register. |
| 9 | Reserved access | — | Reserved address behavior | 1. Write `0xFFFF_FFFF` to `0x10` (first reserved address) and read back. 2. Write `0xFFFF_FFFF` to `0x50` (random middle reserved address) and read back. 3. Write `0xFFFF_FFFF` to `0x3FC` (last reserved address) and read back. | Read-back value is always `0`. |
| 10 | One-hot check | — | Pattern relationship check | 1. Write `0x5555_5555` to DATA0. 2. Write `0xAAAA_AAAA` to DATA1. 3. Read DATA0, DATA1, SR0, and SR1 and compare. | DATA0 = `0x5555_5555`; DATA1 = `0xAAAA_AAAA`; SR0 = DATA0; SR1 = DATA1. |
| 11 | Timing check | Write | Single Write | Use the specified 3-cycle write sequence: cycle 1 `wr_en=0`, cycle 2 `wr_en=1` with `wdata=D1` and address `0x0`, cycle 3 `wr_en=0`. Read back DATA0. | Read data = `D1`. |
| 12 | Timing check | Write | Continuous write | Use the specified 4-cycle sequence: cycle 1 idle; cycle 2 write DATA0=`D1`; cycle 3 write DATA1=`D2`; cycle 4 idle. Read back DATA0 and DATA1. | DATA0 = `D1`; DATA1 = `D2`. |
| 13 | Timing check | Read | Single Read | DATA0 is non-zero. Cycle 1 `rd_en=0`, address `0`; cycle 2 `rd_en=1`, address `0`; cycle 3 `rd_en=0`. Check `rdata` at cycle 2. | `rdata` = DATA0 value. |
| 14 | Timing check | Read | Continuous read | DATA0 and DATA1 have different values. Cycle 1 `rd_en=0`, address `0x0`; cycle 2 `rd_en=1`, address `0x8`; cycle 3 `rd_en=1`, address `0x0`; cycle 4 `rd_en=0`. Check `rdata` at cycles 2 and 3. | Cycle 2 `rdata` = DATA1 value; cycle 3 `rdata` = DATA0 value. |

## 3. Blank Direct-Test Item Template

Use the following row format when adding new direct tests:

```text
| ID | Item | Sub item 1 | Sub item 2 | Test sequence | Pass condition |
|---:|---|---|---|---|---|
| XX | Feature name | Group | Specific check | Stimulus and checking sequence | Expected result |
```

## 4. Direct Test Design Rule

Each test item should be:

1. Independently executable by the direct testbench where practical.
2. Deterministic with an objective PASS/FAIL condition.
3. Traceable to a functional requirement or design behavior when useful. Formal REQ IDs are not mandatory for very small designs.
4. Sufficiently concrete that another engineer can reproduce the test without interpretation.
5. Written in English in every checklist cell (item, sub items, test sequence, pass condition), with a short, distinguishable item name – S5 prints the item name in the simulation log.

The direct-test VPLAN should cover the DUT's **major specified functional behaviors** and important boundary/exception cases relevant to the project scope.

Do not interpret this template as requiring every listed register/timing/pattern test for every DUT. Replace the illustrative example with DUT-specific items.

Avoid adding UVM components, coverage targets, or formal assertions to this checklist unless the project explicitly asks for them.

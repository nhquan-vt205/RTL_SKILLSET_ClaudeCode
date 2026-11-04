# Direct Test VPLAN Checklist Template

## 1. Purpose

This template is derived from the provided `register_checklist.xlsx`.

It is intentionally reduced to the columns required for a **direct simulation test**:

| Column | Purpose |
|---|---|
| ID | Execution ID `TC_<MODULE>_<NNN>` of a top-level Item. One ID per Item, merged over every row of the Item. Used for `tc/<ID>.v`, `make TESTNAME=<ID>`, `sim/pat.list` and `sim/log/<ID>.log`. |
| Item | Broadest functional group of the DUT. One Item = one test-case file. |
| Sub item 1 | Functional branch inside the Item. |
| Sub item 2 | Deepest check branch inside the Sub item 1. |
| Test sequence | Stimulus and checking sequence of the leaf branch, performed by the direct testbench. |
| Pass condition | Objective expected values used to decide PASS/FAIL of the leaf branch. |

The following are intentionally excluded from this direct-test template:

- UVM-specific fields.
- Coverage fields.
- Formal assertion fields.
- Test planning dates.
- PIC/owner fields that are not required to execute the direct test.

## 2. Hierarchy Rules

The checklist is a tree: **Item → Sub item 1 → Sub item 2**. Every row of the table is one **leaf branch** and carries its own Test sequence and Pass condition.

1. **Item** is the broadest functional group; **Sub item 1** is a more detailed functional branch inside the Item; **Sub item 2** is the deepest check branch inside the Sub item 1. One Item contains one or more Sub item 1; one Sub item 1 may contain one or more Sub item 2.
2. Group by the **real function of the DUT** (register access, counting, interrupt, error response, timing, reset …), not by the number of test cases or by existing file names.
3. Use only the levels a branch needs:
   - one level: fill Item, leave Sub item 1 and Sub item 2 empty;
   - two levels: fill Item and Sub item 1, leave Sub item 2 empty;
   - three levels: fill all three.
4. Content is always left-aligned: never an Item → empty Sub item 1 → filled Sub item 2.
5. A node is either a leaf (has Test sequence and Pass condition) or a group (has children), never both. If one branch of an Item needs a Sub item 1, every row of that Item has a Sub item 1.
6. Do not create meaningless intermediate levels such as `General`, `Basic` or `Other` just to fill the table.
7. A leaf may contain several stimuli and checks; do not turn every input value into a branch (four write/read-back patterns are one leaf `Read/write access`, not four leaves).
8. Siblings with the same parent are one consecutive cluster. The parent name is written **once**; its cell is merged vertically over all rows of its children: the Item cell (and the ID cell) over every row of the Item, the Sub item 1 cell over the rows of its Sub item 2.
9. Item names are unique in the VPLAN; sibling names are unique under their parent. The same leaf name under different parents is allowed and is distinguished by its full parent path.
10. Leaf identity (traceability, reports) is the hierarchical path `<ID> › <Item> › <Sub item 1> › <Sub item 2>`, e.g. `TC_REG_BLK_001 › Register access › DATA Register 1 › Reset value check`. `check_sim_log.py --items <vplan>` prints the tree.

### 2.1 Merged Cells per File Format

| Format | Merged parent cell | Level that does not exist |
|---|---|---|
| `.md` | HTML `<table>` with `rowspan` on the ID, Item and Sub item 1 cells (Markdown pipe tables cannot merge cells and are not used for the checklist). | Empty cell `<td></td>`. |
| `.xlsx` | Real merged cells (vertical merge). | Empty unmerged cell. |
| `.docx` | Real vertically merged cells. | Empty unmerged cell. |
| `.csv` | CSV cannot merge: an **empty** ID, Item or Sub item 1 cell **inherits** the value of the row above (same parent). A new Item writes its ID and Item; a new Sub item 1 writes its name. | `—` (em dash). Sub item 2 is never empty: a two-level leaf writes `—`. |

In every format `—` also means "level does not exist". In a `.md` checklist, cell content is plain HTML: use `<code>…</code>` instead of backticks, `<br>` for line breaks, and `&lt;` `&gt;` `&amp;` for `<` `>` `&`; keep the table free of blank lines. Do not use `colspan`/horizontal merges in the checklist.

## 3. Direct Test VPLAN – Illustrative Example

> **Important:** The table below is an example format based on a register-block test (`reg_blk`). It is **not a universal test requirement** and must be replaced/adapted to the actual DUT specification.
>
> For a very small DUT, the VPLAN may contain only the few Items needed to demonstrate its major specified behaviors.

Three levels: `Register access`. Two levels: `Timing check`. One level: `Reserved address behavior`, `Pattern relationship check`. `Reset value check` appears under four different parents.

<table>
<thead>
<tr><th>ID</th><th>Item</th><th>Sub item 1</th><th>Sub item 2</th><th>Test sequence</th><th>Pass condition</th></tr>
</thead>
<tbody>
<tr><td rowspan="8">TC_REG_BLK_001</td><td rowspan="8">Register access</td><td rowspan="2">DATA Register 0</td><td>Reset value check</td><td>After reset is released, read DATA0 at offset <code>0x0</code>.</td><td>Read value = <code>32'h0000_0000</code>.</td></tr>
<tr><td>Read/write access</td><td>1. Write <code>32'h0000_0000</code> and read back. 2. Write <code>32'hFFFF_FFFF</code> and read back. 3. Write <code>32'h5555_5555</code> and read back. 4. Write <code>32'hAAAA_AAAA</code> and read back.</td><td>Each read value equals the value just written.</td></tr>
<tr><td rowspan="2">DATA Register 1</td><td>Reset value check</td><td>After reset is released, read DATA1 at offset <code>0x8</code>.</td><td>Read value = <code>32'hFFFF_FFFF</code>.</td></tr>
<tr><td>Read/write access</td><td>1. Write <code>32'h0000_0000</code> and read back. 2. Write <code>32'hFFFF_FFFF</code> and read back. 3. Write <code>32'h5555_5555</code> and read back. 4. Write <code>32'hAAAA_AAAA</code> and read back.</td><td>Each read value equals the value just written.</td></tr>
<tr><td rowspan="2">Status Register 0</td><td>Reset value check</td><td>After reset is released, read SR0 at offset <code>0x4</code>.</td><td>Read value = <code>32'h0000_0000</code>.</td></tr>
<tr><td>DATA0 mirror</td><td>1. Write <code>32'h0000_0000</code> to DATA0 and read SR0. 2. Write <code>32'hFFFF_FFFF</code> to DATA0 and read SR0. 3. Write <code>32'h5555_5555</code> to DATA0 and read SR0. 4. Write <code>32'hAAAA_AAAA</code> to DATA0 and read SR0.</td><td>Each SR0 read value equals the DATA0 value just written.</td></tr>
<tr><td rowspan="2">Status Register 1</td><td>Reset value check</td><td>After reset is released, read SR1 at offset <code>0xC</code>.</td><td>Read value = <code>32'hFFFF_FFFF</code>.</td></tr>
<tr><td>DATA1 mirror</td><td>1. Write <code>32'h0000_0000</code> to DATA1 and read SR1. 2. Write <code>32'hFFFF_FFFF</code> to DATA1 and read SR1. 3. Write <code>32'h5555_5555</code> to DATA1 and read SR1. 4. Write <code>32'hAAAA_AAAA</code> to DATA1 and read SR1.</td><td>Each SR1 read value equals the DATA1 value just written.</td></tr>
<tr><td>TC_REG_BLK_002</td><td>Reserved address behavior</td><td></td><td></td><td>1. Write <code>32'hFFFF_FFFF</code> to <code>0x10</code> (first reserved address) and read back. 2. Write <code>32'hFFFF_FFFF</code> to <code>0x50</code> (middle reserved address) and read back. 3. Write <code>32'hFFFF_FFFF</code> to <code>0x3FC</code> (last reserved address) and read back.</td><td>Every read-back value = <code>32'h0000_0000</code>.</td></tr>
<tr><td>TC_REG_BLK_003</td><td>Pattern relationship check</td><td></td><td></td><td>1. Write <code>32'h5555_5555</code> to DATA0. 2. Write <code>32'hAAAA_AAAA</code> to DATA1. 3. Read DATA0, DATA1, SR0 and SR1.</td><td>DATA0 = <code>32'h5555_5555</code>; DATA1 = <code>32'hAAAA_AAAA</code>; SR0 = DATA0; SR1 = DATA1.</td></tr>
<tr><td rowspan="4">TC_REG_BLK_004</td><td rowspan="4">Timing check</td><td>Single write</td><td></td><td>Cycle 1 <code>wr_en=0</code>; cycle 2 <code>wr_en=1</code>, <code>wdata=D1</code>, address <code>0x0</code>; cycle 3 <code>wr_en=0</code>. Read back DATA0.</td><td>Read value = <code>D1</code>.</td></tr>
<tr><td>Continuous write</td><td></td><td>Cycle 1 idle; cycle 2 write DATA0 = <code>D1</code>; cycle 3 write DATA1 = <code>D2</code>; cycle 4 idle. Read back DATA0 and DATA1.</td><td>DATA0 = <code>D1</code>; DATA1 = <code>D2</code>.</td></tr>
<tr><td>Single read</td><td></td><td>DATA0 is non-zero. Cycle 1 <code>rd_en=0</code>, address <code>0x0</code>; cycle 2 <code>rd_en=1</code>, address <code>0x0</code>; cycle 3 <code>rd_en=0</code>. Check <code>rdata</code> in cycle 2.</td><td><code>rdata</code> = DATA0 value.</td></tr>
<tr><td>Continuous read</td><td></td><td>DATA0 and DATA1 differ. Cycle 1 <code>rd_en=0</code>, address <code>0x0</code>; cycle 2 <code>rd_en=1</code>, address <code>0x8</code>; cycle 3 <code>rd_en=1</code>, address <code>0x0</code>; cycle 4 <code>rd_en=0</code>. Check <code>rdata</code> in cycles 2 and 3.</td><td>Cycle 2 <code>rdata</code> = DATA1 value; cycle 3 <code>rdata</code> = DATA0 value.</td></tr>
</tbody>
</table>

Rendered tree:

```text
TC_REG_BLK_001  Register access
                  DATA Register 0      Reset value check | Read/write access
                  DATA Register 1      Reset value check | Read/write access
                  Status Register 0    Reset value check | DATA0 mirror
                  Status Register 1    Reset value check | DATA1 mirror
TC_REG_BLK_002  Reserved address behavior
TC_REG_BLK_003  Pattern relationship check
TC_REG_BLK_004  Timing check
                  Single write | Continuous write | Single read | Continuous read
```

The same checklist as `.csv` (empty = inherited from the row above, `—` = level does not exist; Test sequence/Pass condition shortened here):

```text
ID,Item,Sub item 1,Sub item 2,Test sequence,Pass condition
TC_REG_BLK_001,Register access,DATA Register 0,Reset value check,Read DATA0 at 0x0 after reset.,Read value = 32'h0000_0000.
,,,Read/write access,Write and read back 4 patterns.,Each read value equals the value just written.
,,DATA Register 1,Reset value check,Read DATA1 at 0x8 after reset.,Read value = 32'hFFFF_FFFF.
,,,Read/write access,Write and read back 4 patterns.,Each read value equals the value just written.
TC_REG_BLK_002,Reserved address behavior,—,—,Write/read 0x10 0x50 0x3FC.,Every read-back value = 0.
TC_REG_BLK_004,Timing check,Single write,—,3-cycle write then read DATA0.,Read value = D1.
,,Continuous write,—,4-cycle write then read DATA0 and DATA1.,DATA0 = D1; DATA1 = D2.
```

## 4. Function Coverage

After the checklist, a table `Function → branch` maps each specified function to the Item ID or leaf path that checks it. It is a separate table (different columns) and is not a test list.

| Function (spec section) | Branch |
|---|---|
| Register reset values | TC_REG_BLK_001 › * › Reset value check |
| Status register mirrors DATA register | TC_REG_BLK_001 › Status Register 0 › DATA0 mirror, TC_REG_BLK_001 › Status Register 1 › DATA1 mirror |
| Reserved addresses read as zero | TC_REG_BLK_002 |

## 5. Blank Direct-Test Templates

Markdown (`.md`), one Item with two Sub item 1, the first with two Sub item 2:

```html
<table>
<thead>
<tr><th>ID</th><th>Item</th><th>Sub item 1</th><th>Sub item 2</th><th>Test sequence</th><th>Pass condition</th></tr>
</thead>
<tbody>
<tr><td rowspan="3">TC_M_001</td><td rowspan="3">Feature</td><td rowspan="2">Branch A</td><td>Check A1</td><td>Stimulus and checking sequence</td><td>Expected values</td></tr>
<tr><td>Check A2</td><td>Stimulus and checking sequence</td><td>Expected values</td></tr>
<tr><td>Branch B</td><td></td><td>Stimulus and checking sequence</td><td>Expected values</td></tr>
<tr><td>TC_M_002</td><td>Single-level feature</td><td></td><td></td><td>Stimulus and checking sequence</td><td>Expected values</td></tr>
</tbody>
</table>
```

Rowspan of an Item (and of its ID) = number of leaf rows of the Item; rowspan of a Sub item 1 = number of its Sub item 2 rows. A covered cell is not written again in the following rows.

## 6. Direct Test Design Rule

Each Item should be:

1. Executable as one direct test-case file `tc/<ID>.v` that runs every leaf branch of the Item, cluster by cluster in table order.
2. Deterministic with an objective PASS/FAIL condition on every leaf.
3. Traceable to a functional requirement or design behavior when useful. Formal REQ IDs are not mandatory for very small designs.
4. Sufficiently concrete that another engineer can reproduce every leaf without interpretation: stimulus, expected values (numbers) and pass condition.
5. Written in English in every checklist cell (Item, Sub items, Test sequence, Pass condition), with short, distinguishable branch names – S5 prints them as `[ITEM]`, `[SUBITEM1]`, `[SUBITEM2]` headers in the simulation log.

The direct-test VPLAN should cover the DUT's **major specified functional behaviors** and important boundary/exception cases relevant to the project scope.

Do not interpret this template as requiring every listed register/timing/pattern test for every DUT. Replace the illustrative example with DUT-specific Items.

Avoid adding UVM components, coverage targets, or formal assertions to this checklist unless the project explicitly asks for them.

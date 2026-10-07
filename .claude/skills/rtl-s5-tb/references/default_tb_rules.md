# Rule testbench mặc định (chỉ dùng cho chỗ tb_coding_rules/ không nói tới)

Mục tiêu: testbench direct, tự kiểm, mô phỏng tất định, đọc được ở mức sinh viên. Không UVM, class, interface, package, SVA, coverage, random, framework scoreboard.

## 1. Ngôn ngữ và file

- **Verilog-2005 (IEEE 1364-2005)**, file `tb/<m>/tb_<m>.v`, module top `tb_<m>`. Phải là cú pháp Verilog-2005 thật – không phải đổi đuôi một file SystemVerilog.
- Dùng: `reg`, `wire`, `integer`, `parameter`, `localparam`, `always`, `initial`, `task`, `function`, `if`, `case`, `for`, `while`, `repeat`, `$display`, `$write`, `$sformat`, `$value$plusargs`, `$test$plusargs`, `$finish`, `$dumpfile`, `$dumpvars`.
- **Cấm** (SystemVerilog): `logic`, `bit`, `byte`, `int`, `string`, `always_ff`, `always_comb`, `always_latch`, `typedef`, `enum`, `struct`, `union`, `interface`/`modport`, `package`/`import`, `class`, `virtual`, `foreach`, queue, mảng động, `mailbox`, `assert`/`property` (SVA), cast `type'(...)`, literal `'0`/`'1`, `$fatal`, khai báo biến trong `for` (`for (int i …)`).
- Chuỗi (tên item, tên case, ID test): `reg [8*N-1:0]`; ghép chuỗi động bằng `$sformat(case_name, "addr_%0h_wdata_%h", addr, wdata);`; in bằng `%0s`.
- `` `timescale 1ns/1ps `` đầu file.
- Comment, tên task/function/tín hiệu, chuỗi in và log chỉ dùng tiếng Anh.

## 2. Cấu trúc file – bắt buộc, đúng thứ tự

Mỗi phần mở bằng header như sau, giữ đủ 9 header kể cả khi TB nhỏ:

```verilog
// ============================================================
// 1. Declaration
// ============================================================
```

| # | Header | Nội dung |
| --- | --- | --- |
| 1 | `Declaration` | `parameter CLK_PERIOD = 20;` (và hằng TB: số chu kỳ reset, timeout); mọi `reg`/`wire` nối DUT; trạng thái golden model; `integer pass_count; integer fail_count;`; biến chọn test, tên case, biến vòng lặp. Khai báo hết ở đây trước khi dùng. |
| 2 | `DUT Instance` | `<m> u_dut (.port(net), ...);` nối theo tên, `#(.P(v))` nếu DUT có parameter. |
| 3 | `Clock Generation` | `initial begin clk = 1'b0; end` + `always #(CLK_PERIOD / 2) clk = ~clk;` |
| 4 | `Init Reset` | `task reset_dut`: đưa mọi input DUT về giá trị nghỉ, áp/nhả reset theo spec (mục 4), reset golden model. |
| 5 | `Golden Reference Model` | Mô hình tham chiếu tính giá trị mong đợi từ spec/vplan: thanh ghi/mảng tham chiếu + `task`/`function` cập nhật/tính (`ref_reset`, `ref_write`, `ref_step`…). |
| 6 | `Checker` | `task check_<tên>` so actual với expected, tăng `pass_count`/`fail_count`, in một dòng log (mục 6). |
| 7 | `Helper Functions` | `function` nhỏ thực sự dùng (vd. chọn test theo `+TEST`). Không cần thì để header trống. |
| 8 | `Tasks` | Task lái giao thức/bus (`apb_write`, `drive_cycle`) rồi các task test case `tc_<id>`, theo thứ tự vplan. |
| 9 | `Main Program Body` | `initial` chính (khởi tạo bộ đếm, đọc plusarg, `reset_dut` + `tc_<id>` cho từng item, in `[SUMMARY]`, `$finish`) và `initial` timeout toàn cục. |

Không viết code vô nghĩa để lấp một phần: phần không cần (thường là 7) chỉ giữ header. Golden model/checker giữ đơn giản theo độ phức tạp DUT.

## 3. Clock

- Mặc định **20 ns**: `parameter CLK_PERIOD = 20;`. Spec của DUT quy định chu kỳ/tần số khác → dùng giá trị của spec cho TB đó.
- `clk` khởi tạo 0 trong `initial`, đảo bằng `always #(CLK_PERIOD / 2)` → cạnh lên đầu tiên ở `CLK_PERIOD/2`, không có cạnh lên ở thời điểm 0.

## 4. Thời điểm lái stimulus và lấy mẫu

**Luật bắt buộc – lái input DUT: chờ cạnh lên, trễ đúng `#1`, rồi gán.**

```verilog
@(posedge clk);
#1;
din = 8'hA5;
```

- Áp dụng cho mọi lần lái input DUT trong chuỗi stimulus (kể cả trả input về giá trị nghỉ, và reset khi reset là input đồng bộ). Không lái ở `negedge`, không lái đúng tại `posedge`, không lái ngay trước `posedge`, không thay `#1` bằng trễ khác.
- `#1` chỉ thuộc testbench. Không bao giờ thêm trễ vào RTL, không sửa RTL để hợp với TB.
- Biến nội bộ của TB (golden model, bộ đếm, tên case) không cần theo luật này.
- Lấy mẫu/kiểm output cũng sau `@(posedge clk); #1;`: output từ thanh ghi đã cập nhật ở cạnh vừa qua. Output tổ hợp phụ thuộc input → kiểm khi input tạo ra nó còn giữ nguyên, sau khi lái và trước cạnh lên kế tiếp.

## 5. Reset

- Theo spec của DUT (cực tính, đồng bộ/không đồng bộ). Không sửa hành vi reset của RTL.
- `reset_dut` khởi tạo rõ: mọi input DUT về giá trị nghỉ, reset tích cực, golden model về trạng thái sau reset; giữ reset 5 chu kỳ (`RESET_CYCLES`), rồi nhả.
- Reset **không đồng bộ**: tích cực ngay khi gọi `reset_dut` (giữ ngữ nghĩa async), nhả bằng `@(posedge clk); #1;`.
- Reset **đồng bộ**: cả tích cực và nhả đều theo `@(posedge clk); #1;`.
- `initial` chính gọi `reset_dut` trước mỗi test case phụ thuộc trạng thái reset.

## 6. Self-check: golden model → checker → bộ đếm → log

- Giá trị mong đợi lấy từ golden model (spec, vplan, công thức, mô hình trạng thái), cập nhật song song với stimulus – **không** bao giờ lấy từ output DUT (`expected = dut_out;` là sai).
- `pass_count`, `fail_count` (`integer`) gán 0 đầu `initial` chính. Mỗi lần checker so sánh = một case: PASS → `pass_count = pass_count + 1;`, FAIL → `fail_count = fail_count + 1;`. PASS + FAIL = số lần checker được gọi.
- So bằng `===`/`!==` (bắt được X/Z). Checker có width đúng tín hiệu so sánh (một task cho mỗi width cần so, thường 1–2).

### Định dạng log (chuẩn, `check_sim_log.py` đọc)

```text
-- <item name> test --
[<time>] <case> PASS | expected: <exp> | actual: <act>
[<time>] <case> FAIL | expected: <exp> | actual: <act>
[SUMMARY] PASS=<n> FAIL=<n>
```

Ví dụ:

```text
-- APB write test --
[61] addr_0_wdata_A5A5A5A5 PASS | expected: A5A5A5A5 | actual: A5A5A5A5
[101] addr_4_wdata_00000000 PASS | expected: 00000000 | actual: 00000000
-- APB read unwritten register test --
[141] addr_0_unwritten PASS | expected: DEADBEEF | actual: DEADBEEF
-- handshake test --
[181] valid_1_ready_0 FAIL | expected: 0 | actual: 1
[SUMMARY] PASS=3 FAIL=1
```

- `-- <item name> test --`: in ở đầu task của mỗi item vplan. `<item name>` là **tên tiếng Anh ngắn, đọc được, lấy từ vplan** (không thay bằng ID, không dịch): vplan mặc định – phần tên sau ID ở heading `### TC_<M>_001 – <tên>`; template bảng có cột `ID` – cột cụ thể nhất (thường `Sub item 2`), chỉ thêm cột phía trước (`Sub item 1`, rồi `Item`, nối bằng ` / `) khi cần để phân biệt với item khác, bỏ ô trống/`—` (vd. `-- DATA Register 0 / Reset value check test --`, `-- Single Write test --`). Lấy đúng danh sách header bằng `python3 .claude/skills/rtl-s5-tb/scripts/check_sim_log.py --items doc/vplan/<m>_vplan.<ext>`; checker dùng tên này để map về ID vplan. Chỉ ghi ID thay tên khi item trong vplan không có tên hoặc tên trùng với item khác. Mọi case in sau header thuộc item đó.
- `[<time>]`: thời gian mô phỏng hiện tại, `$time` theo ns, in `%0d`.
- `<case>`: tên ngắn, không khoảng trắng, mô tả **đặc điểm input quan trọng** của case – `addr_0_wdata_A5A5A5A5`, `valid_1_ready_0`, `clr_1_en_1_pulse_1`; nhiều input quan trọng thì ghép đủ vào tên. Không dùng tên vô nghĩa kiểu `CASE_001`, `TEST_01`. Ghép động bằng `$sformat`.
- `PASS`/`FAIL`: quyết định của checker. `expected`: giá trị golden model. `actual`: giá trị DUT. In bằng `%h` (bus ra đủ chữ số hex theo width, 1 bit ra `0`/`1`), không thêm tiền tố.
- Dấu phân cách giữ nguyên `| expected: ... | actual: ...`.
- `[SUMMARY] PASS=<pass_count> FAIL=<fail_count>` in một lần cuối mô phỏng.
- ID vplan vẫn dùng cho máy: tên task `tc_<id>`, chọn test `+TEST=<ID>`, báo cáo.

```verilog
$display("[%0d] %0s PASS | expected: %h | actual: %h", $time, name, exp, act);
```

## 7. Chọn test, timeout, waveform

- `+TEST=<ID>` chạy riêng một item; không có hoặc `ALL` → chạy tất cả theo thứ tự vplan. Đọc bằng `$value$plusargs("TEST=%s", test_sel)` vào `reg [8*32-1:0]`.
- Timeout toàn cục (vd. 100× số chu kỳ ước lượng) trong `initial` riêng ở phần 9: in `[TIMEOUT] ...`, in `[SUMMARY]`, `$finish`.
- `+DUMP` bật `$dumpfile("tb_<m>.vcd"); $dumpvars(0, tb_<m>);` – chỉ để debug.

## 8. Khung mẫu (DUT `pulse_cnt` 3 bit: `clr_i` → 0, `en_i & pulse_i` → +1)

```verilog
// tb_pulse_cnt - self-checking direct testbench for pulse_cnt
// Vplan: doc/vplan/pulse_cnt_vplan.md
`timescale 1ns/1ps

module tb_pulse_cnt;

  // ============================================================
  // 1. Declaration
  // ============================================================
  parameter CLK_PERIOD   = 20;
  parameter RESET_CYCLES = 5;
  parameter TIMEOUT_NS   = 100000;

  reg            clk;
  reg            rst_n;
  reg            en;
  reg            pulse;
  reg            clr;
  wire [2:0]     count;

  reg  [2:0]     ref_count;
  integer        pass_count;
  integer        fail_count;
  reg  [8*32-1:0] test_sel;

  // ============================================================
  // 2. DUT Instance
  // ============================================================
  pulse_cnt u_dut (
    .clk_i   (clk),
    .rst_n_i (rst_n),
    .en_i    (en),
    .pulse_i (pulse),
    .clr_i   (clr),
    .count_o (count)
  );

  // ============================================================
  // 3. Clock Generation
  // ============================================================
  initial begin
    clk = 1'b0;
  end

  always #(CLK_PERIOD / 2) clk = ~clk;

  // ============================================================
  // 4. Init Reset
  // ============================================================
  // Idle inputs, assert async reset now, release at posedge + #1
  task reset_dut;
    begin
      en    = 1'b0;
      pulse = 1'b0;
      clr   = 1'b0;
      rst_n = 1'b0;
      ref_reset;
      repeat (RESET_CYCLES) @(posedge clk);
      #1;
      rst_n = 1'b1;
    end
  endtask

  // ============================================================
  // 5. Golden Reference Model
  // ============================================================
  task ref_reset;
    begin
      ref_count = 3'd0;
    end
  endtask

  // One clock of the specified behavior
  task ref_step;
    input r_en;
    input r_pulse;
    input r_clr;
    begin
      if (r_clr) begin
        ref_count = 3'd0;
      end
      else if (r_en && r_pulse) begin
        ref_count = ref_count + 3'd1;
      end
    end
  endtask

  // ============================================================
  // 6. Checker
  // ============================================================
  task check_count;
    input [8*48-1:0] name;
    input [2:0]      exp;
    input [2:0]      act;
    begin
      if (act === exp) begin
        pass_count = pass_count + 1;
        $display("[%0d] %0s PASS | expected: %h | actual: %h", $time, name, exp, act);
      end
      else begin
        fail_count = fail_count + 1;
        $display("[%0d] %0s FAIL | expected: %h | actual: %h", $time, name, exp, act);
      end
    end
  endtask

  // ============================================================
  // 7. Helper Functions
  // ============================================================
  // 1 when this test is selected by +TEST=<ID> (ALL or absent = all)
  function run_test;
    input [8*32-1:0] id;
    begin
      run_test = (test_sel == "ALL") || (test_sel == id);
    end
  endfunction

  // ============================================================
  // 8. Tasks
  // ============================================================
  // Drive one cycle at posedge + #1, return inputs to idle, update model
  task drive_cycle;
    input d_en;
    input d_pulse;
    input d_clr;
    begin
      @(posedge clk);
      #1;
      en    = d_en;
      pulse = d_pulse;
      clr   = d_clr;
      @(posedge clk);
      #1;
      ref_step(d_en, d_pulse, d_clr);
      en    = 1'b0;
      pulse = 1'b0;
      clr   = 1'b0;
    end
  endtask

  // TC_PULSE_CNT_002 (count enable): count only when en_i and pulse_i are 1
  task tc_pulse_cnt_002;
    begin
      $display("-- count enable test --");
      drive_cycle(1'b1, 1'b1, 1'b0);
      check_count("en_1_pulse_1", ref_count, count);
      drive_cycle(1'b0, 1'b1, 1'b0);
      check_count("en_0_pulse_1_hold", ref_count, count);
    end
  endtask

  // ============================================================
  // 9. Main Program Body
  // ============================================================
  initial begin
    pass_count = 0;
    fail_count = 0;
    if (!$value$plusargs("TEST=%s", test_sel)) begin
      test_sel = "ALL";
    end
    if ($test$plusargs("DUMP")) begin
      $dumpfile("tb_pulse_cnt.vcd");
      $dumpvars(0, tb_pulse_cnt);
    end

    if (run_test("TC_PULSE_CNT_002")) begin
      reset_dut;
      tc_pulse_cnt_002;
    end

    $display("[SUMMARY] PASS=%0d FAIL=%0d", pass_count, fail_count);
    $finish;
  end

  initial begin
    #(TIMEOUT_NS);
    $display("[TIMEOUT] simulation exceeded %0d ns", TIMEOUT_NS);
    $display("[SUMMARY] PASS=%0d FAIL=%0d", pass_count, fail_count);
    $finish;
  end

endmodule
```

Vplan có item `### TC_PULSE_CNT_002 – count enable`; log tương ứng:

```text
-- count enable test --
[131] en_1_pulse_1 PASS | expected: 1 | actual: 1
[171] en_0_pulse_1_hold PASS | expected: 1 | actual: 1
[SUMMARY] PASS=2 FAIL=0
```

## 9. `sim/<m>/run.sh` mặc định

Filelist `sim/<m>/<m>.f`: RTL cả cây (`rtl/*.v`) rồi `tb/<m>/tb_<m>.v`, mỗi dòng một file, đường dẫn tính từ gốc project. Không đưa testbench `.sv` cũ (nếu còn) vào filelist.

```bash
#!/usr/bin/env bash
# Usage: sim/<m>/run.sh [TEST_ID|ALL] [+DUMP]   (run from the project root)
set -e
M=<m>; T=${1:-ALL}; mkdir -p sim/$M/logs
if command -v iverilog >/dev/null; then
  iverilog -g2005 -o sim/$M/tb_$M.vvp -f sim/$M/$M.f
  vvp sim/$M/tb_$M.vvp +TEST=$T $2 | tee sim/$M/logs/run.log
elif command -v verilator >/dev/null; then
  verilator --binary --timing -Wno-fatal -Wno-TIMESCALEMOD -Wno-WIDTH --top-module tb_$M -f sim/$M/$M.f --Mdir sim/$M/obj_dir -o tb_$M
  sim/$M/obj_dir/tb_$M +TEST=$T $2 | tee sim/$M/logs/run.log
else
  echo "No simulator found (iverilog/verilator)"; exit 2
fi
```

Icarus chạy ở `-g2005` (cùng chế độ lint RTL của S3): TB lẫn RTL đều phải là Verilog-2005; lỗi parse nghĩa là còn construct SV → sửa TB. Simulator là lựa chọn độc lập với ngôn ngữ: Verilator lint/mô phỏng **cùng** file `tb_<m>.v` Verilog-2005 (lint kiểu 2005: `verilator --lint-only --timing --default-language 1364-2005 ...`); không bao giờ chuyển TB sang SystemVerilog để chạy Verilator. RTL module con cũ còn `.sv` (project trước khi S3 đổi sang `.v`) → báo trong báo cáo, không tự viết lại RTL.

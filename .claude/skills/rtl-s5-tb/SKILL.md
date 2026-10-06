---
name: rtl-s5-tb
description: Stage 5 của RTL flow (tùy chọn, nhẹ) – viết testbench self-checking Verilog-2005 (tb/<m>/tb_<m>.v) hiện thực đúng các direct test trong vplan của MỘT module (leaf hoặc cả cây con ở mức tích hợp) theo cấu trúc 9 phần cố định (golden model, checker, bộ đếm PASS/FAIL, log chuẩn), clock mặc định 20 ns, lái stimulus tại posedge + #1, tạo filelist + script chạy, mô phỏng bằng Icarus Verilog/Verilator nếu có. Theo rule testbench của người dùng trong tb_coding_rules/ nếu có. Dùng khi người dùng gọi /rtl-s5-tb <module> hoặc yêu cầu viết testbench theo vplan.
argument-hint: "<tên_module> [tên_module ...]"
disable-model-invocation: true
---

# Stage 5 – Testbench theo vplan

Module: `$ARGUMENTS`

Stage này **tùy chọn**, chỉ chạy khi người dùng cần mô phỏng.

Testbench tự kiểm: stimulus → DUT → golden reference model → checker → bộ đếm PASS/FAIL → log chuẩn → `[SUMMARY]`. Không chỉ `$display` để xem waveform bằng mắt. Không UVM, class, interface, package, random, coverage, SVA/assertion, framework scoreboard.

## Phạm vi

- Chỉ đúng module(s) được nêu tên; không nhận "all".
- Hiện thực **đúng và đủ** các test trong `doc/vplan/<m>_vplan.*`; test cần thêm → đề xuất trong báo cáo để cập nhật vplan.
- Không sửa RTL, spec, diagram, vplan. Đầu ra chỉ trong `tb/<m>/` và `sim/<m>/`.

## Bước 0 – Gate

```bash
python3 .claude/skills/rtl-s5-tb/scripts/check_preconditions.py --stage 5 --module <m>
```

Cần spec PASS, bảng port, RTL của module **và mọi module con** (để mô phỏng được), vplan. Mã thoát ≠ 0 → bỏ qua module đó, báo `[THIẾU]`. Test trong vplan còn `TBD` ở stimulus/mong đợi → bỏ qua test đó, liệt kê trong báo cáo.

## Bước 1 – Rule

Đọc `tb_coding_rules/` (trừ README.md) nếu có; chỗ không nói tới hoặc thư mục trống → `references/default_tb_rules.md`.

## Bước 2 – Viết testbench

Đọc vplan, RTL (port, parameter), spec (handshake, reset, chu kỳ clock, latency). Chi tiết và khung mẫu: `references/default_tb_rules.md`. Luật bắt buộc:

- **Ngôn ngữ:** Verilog-2005 (IEEE 1364-2005), một file `tb/<m>/tb_<m>.v`, module `tb_<m>`. Không construct SystemVerilog nào (`logic`, `bit`, `string`, `always_ff`, `typedef`, `enum`, `struct`, `interface`, `package`, `class`, `foreach`, queue, `$fatal`, SVA…).
- **Cấu trúc 9 phần, đúng thứ tự**, mỗi phần có header comment, giữ đủ header kể cả khi TB nhỏ (phần không cần thì để trống, không viết code giả): `1. Declaration` → `2. DUT Instance` → `3. Clock Generation` → `4. Init Reset` → `5. Golden Reference Model` → `6. Checker` → `7. Helper Functions` → `8. Tasks` → `9. Main Program Body`.
- **Clock:** `` `timescale 1ns/1ps ``, `parameter CLK_PERIOD = 20;` (20 ns mặc định; spec quy định chu kỳ khác thì theo spec), `clk = 1'b0` trong `initial` + `always #(CLK_PERIOD / 2) clk = ~clk;`.
- **Stimulus:** mọi lần lái input DUT là `@(posedge clk); #1;` rồi gán. Không lái ở negedge, không lái đúng tại posedge. `#1` chỉ có trong TB, không bao giờ trong RTL.
- **Reset:** theo spec – reset async tích cực ngay, nhả tại `posedge + #1`; reset đồng bộ lái như stimulus. `reset_dut` (phần 4) khởi tạo mọi input DUT và golden model; gọi trước mỗi test case phụ thuộc trạng thái reset.
- **Một kiến trúc TB cho cả module:** mỗi item vplan → một task trong phần 8, tên truy được về ID vplan (`tc_acc_unit_001`, hoặc `tc_003_rw_access` khi vplan dùng ID số); comment đầu task chép ID, tên và mục tiêu từ vplan. Không tách file TB theo item. ID vplan dùng cho tên task, `+TEST=<ID>` và báo cáo.
- **Self-check:** golden model tính expected độc lập từ spec/vplan (không bao giờ lấy từ output DUT); checker so sánh, tăng `pass_count`/`fail_count` (`integer`), PASS + FAIL = số lần checker so sánh.
- **Log chuẩn** (`check_sim_log.py` đọc): đầu mỗi item `-- <item name> test --` với `<item name>` là tên ngắn, đọc được, phân biệt được của item lấy từ vplan (không thay bằng ID; danh sách đúng: `check_sim_log.py --items <vplan>`); mỗi case `[<time>] <case> PASS | expected: <exp> | actual: <act>` hoặc `... FAIL | ...`, `<time>` = `$time`, `<case>` ngắn mô tả đặc điểm input quan trọng (`addr_0_wdata_A5A5A5A5`, `valid_1_ready_0` – không `CASE_001`), expected = golden model, actual = DUT; cuối cùng `[SUMMARY] PASS=<n> FAIL=<n>`. Chi tiết ở mục 6 của `default_tb_rules.md`.
- Timeout toàn cục (in `[TIMEOUT]`, `[SUMMARY]`, `$finish`); driver tuân thủ giao thức handshake; chạy riêng một item bằng `+TEST=<ID>`.
- DUT có module con (phạm vi tích hợp): instance module cha, stimulus qua port của nó, kiểm output/status cuối; filelist gồm RTL cả cây.

## Bước 3 – Script và chạy

Tạo `sim/<m>/<m>.f` (RTL cả cây + `tb/<m>/tb_<m>.v`) và `sim/<m>/run.sh` (hoặc theo rule) – mẫu ở mục 9 của `default_tb_rules.md`. Chạy nếu có simulator (ưu tiên Icarus `iverilog -g2005`, rồi Verilator – dùng cùng file `.v` Verilog-2005, không chuyển sang SystemVerilog), log vào `sim/<m>/logs/run.log`, rồi:

```bash
python3 .claude/skills/rtl-s5-tb/scripts/check_sim_log.py sim/<m>/logs/run.log doc/vplan/<m>_vplan.<ext>
```

Script map header `-- <item name> test --` về ID vplan theo tên item, rồi kiểm: item vplan chưa chạy/không có case, case FAIL, dòng case sai định dạng, case trước mọi header, header không có trong vplan, `[SUMMARY]` thiếu/trùng/lệch số dòng PASS/FAIL, `[TIMEOUT]`/fatal. Vplan dùng ID khác `TC_…` mà không phải bảng có cột `ID` → thêm `--id-re '<regex>'`.

Test FAIL → phân loại:
- Lỗi testbench (stimulus/chu kỳ kiểm sai so với vplan, golden model sai so với spec) → sửa TB, chạy lại.
- Lỗi RTL hoặc vplan → **không sửa**; báo test ID, triệu chứng, nghi ngờ ở file/dòng nào, cần sửa ở S3 hay S4.

Không có simulator → không phải lỗi thiết kế; ghi "chưa chạy mô phỏng" và lệnh chạy.

## Đầu ra

```
tb/<m>/tb_<m>.v          # Verilog-2005
sim/<m>/<m>.f
sim/<m>/run.sh
sim/<m>/logs/run.log     # nếu đã chạy – log tạm, bị .gitignore, không phải tài liệu cần giữ
```

Còn `tb/<m>/tb_<m>.sv` cũ (testbench SystemVerilog từ trước khi S5 đổi sang Verilog-2005) → **không tự xóa**, không đưa vào filelist; nêu trong báo cáo là file legacy để người dùng quyết định.

## Báo cáo cuối (chỉ trong chat)

File · ngôn ngữ TB (Verilog-2005) · file `.sv` legacy còn lại (nếu có) · số item hiện thực / tổng vplan · kết quả theo ID (số case PASS/FAIL, `[SUMMARY]`) · test bỏ qua vì TBD · lỗi nghi ở RTL/vplan kèm đề xuất · lệnh chạy lại.

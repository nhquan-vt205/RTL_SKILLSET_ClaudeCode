---
name: rtl-s3-rtl
description: Stage 3 của RTL flow – viết RTL Verilog-2005 (rtl/<m>.v) đơn giản, tổng hợp được, nhìn vào thấy phần cứng, compile/lint sạch cho MỘT module được chỉ định, giữ đúng state, datapath, control và hành vi của spec và diagram stage 2 (L2 viết trực tiếp reg + always + always @(*) + assign, L1 dùng mảng bộ nhớ/generate khi kiến trúc cần, L0 instance module con và nối dây), theo coding rule của người dùng nếu có. Dùng khi người dùng gọi /rtl-s3-rtl <module> hoặc yêu cầu implement RTL cho một module.
argument-hint: "<tên_module> [tên_module ...]"
disable-model-invocation: true
---

# Stage 3 – RTL Verilog-2005 cho từng module

Module cần implement: `$ARGUMENTS`

Mục tiêu: RTL **Verilog-2005, đúng chức năng trong spec, đơn giản, dễ đọc, compile/lint sạch, tổng hợp được**; nhìn vào thấy kiến trúc của diagram và phần cứng (thanh ghi → logic tổ hợp → mux/số học/so sánh → thanh ghi → output). Không tối ưu timing/diện tích.

## Phạm vi

- Chỉ implement đúng module(s) được nêu tên; không nhận "all".
- Module có module con: viết instance theo bảng port của con. Con chưa có RTL → vẫn instance, liệt kê trong báo cáo; **không tự viết module con**.
- Không sửa `doc/spec/`, `doc/diagram/`. Đầu ra chỉ trong `rtl/`, cộng việc bỏ comment dòng `../rtl/<m>.v` trong `sim/rtl.f` để kiểm compile. Không tạo file báo cáo, traceability hay testbench.

## Bước 0 – Gate

```bash
python3 .claude/skills/rtl-s3-rtl/scripts/check_preconditions.py --stage 3 --module <m>
```

Cần: spec đã PASS, bảng port của module, diagram `doc/diagram/<m>/<m>.svg`. `<m>_notes.md` không bắt buộc – có thì đọc. Diagram đầu vào chỉ là `<m>.svg`; góc nhìn scope `<m>_<part>.svg` không đọc; file định dạng cũ (`.mmd`, `.html`) không còn được nhận – chạy lại `/rtl-s2-diagram <m>`. Mã thoát ≠ 0 → bỏ qua module đó, báo các dòng `[THIẾU]` và lệnh cần chạy trước. Dòng `[INFO]` cho biết file cần đọc, level và module con chưa có RTL.

**Nhánh git** (mục "Nhánh git" của `CLAUDE.md`): sau gate, so nhánh hiện tại với nhánh `<b>` của `<m>` (cột `Branch` của `spec_status.md`; chế độ đơn `<m>`). Khác nhau → báo nhánh đúng và lệnh (`git checkout <b>`, hoặc `git checkout -b <b> main` nếu chưa có), chỉ chuyển khi người dùng đồng ý; không chạy S3 của module con trên `main`. Commit/push đầu ra chỉ khi người dùng yêu cầu; báo cáo cuối gợi ý lệnh commit và `git push -u origin <b>`.

## Bước 1 – Coding rule

Đọc mọi file trong `.claude/skills/rtl-s3-rtl/coding_rules/` (trừ README.md) nếu có – rule người dùng là luật cao nhất. Chỗ rule không nói tới (hoặc thư mục trống) dùng `references/default_rtl_rules.md`.

**Ngôn ngữ RTL mặc định: Verilog-2005 (IEEE 1364-2005), đuôi `.v`** – đây là luật, không phải gợi ý. Không dùng construct SystemVerilog (`logic`, `always_ff`, `always_comb`, `typedef`/`enum`/`struct`, `interface`, `package`, `unique case`, `inside`, `'0`, SVA…) – danh sách đủ trong `default_rtl_rules.md`. Chỉ đổi ngôn ngữ khi coding rule người dùng quy định rõ; ghi ngôn ngữ đã dùng trong báo cáo.

**Parameter:** spec nói cấu hình được → `parameter`; spec cố định → width/hằng viết thẳng (`reg [7:0] count_q;`). Không tự tạo parameter mới. `localparam` cho mã trạng thái FSM và hằng có tên.

## Bước 2 – Đọc thiết kế

Đọc các file gate in ra: spec (chức năng, hành vi, reset, thanh ghi, FSM, định dạng số), bảng port (tên, hướng, width, thứ tự), diagram (`<m>.svg`: bản vẽ cho thanh ghi, MUX, cổng, khối, instance, kết nối; `<desc id="model">` cho phương trình chính xác từng khối – phần gom thành cloud/khối `blk_` chỉ có hành vi trong model, vẫn viết trong module này), notes nếu có, tài liệu tách riêng nếu có (parameter, register map, FSM), bảng port của module con.

## Bước 3 – Viết code

**Quy tắc chính:** RTL phản ánh đúng state, datapath, control và hành vi của spec/diagram. Diagram là mô hình kiến trúc, không phải danh sách đối tượng code – không cần ánh xạ 1:1.

| Được (implementation detail) | Không được (đổi kiến trúc/chức năng) |
| --- | --- |
| Thêm tín hiệu trung gian (`count_d`, `count_en`, `wrap`) | Thêm pipeline, tầng thanh ghi, bộ đệm không có trong spec/diagram |
| Một khối diagram → nhiều câu lệnh; nhiều khối → một `always @(*)` | Thêm chức năng, chế độ, port không có trong spec |
| Helper logic tổ hợp, `localparam`, `function` nhỏ (khi thật sự giúp đọc) | Đổi latency, đổi hành vi reset, bỏ thanh ghi trạng thái của kiến trúc |
| Tách/gộp biểu thức để code rõ hoặc tổng hợp đúng | Đổi giao thức handshake |

Theo level:

| Level | Cách viết |
| --- | --- |
| **L2** | `reg` + `always` + `always @(*)` + `assign`. Thanh ghi trạng thái của diagram thành `reg ..._q` (khối `always @(posedge clk_i ...)`), logic next-value (mux/cộng/so sánh của diagram) thành `always @(*)` tính `_d` hoặc `assign`, output bằng `assign`. Thứ tự trong file: port → khai báo `wire`/`reg` nội bộ → thanh ghi → logic next-value → output; module đơn giản được gộp bớt khối. Tên tín hiệu đủ rõ để đối chiếu từng khối diagram; không nén code chỉ để ít dòng. |
| **L1** | `wire`/`reg`, mảng bộ nhớ Verilog (`reg [7:0] mem_q [0:15]`), `generate for` khi kiến trúc là nhiều bản sao giống nhau, `localparam`. Không `typedef`/`struct`/`enum`: trường dữ liệu thành vector riêng, FSM bằng `localparam` + `reg`. Theo "hiện thực RTL dự kiến" trong notes nếu có (diễn đạt lại bằng Verilog-2005 nếu notes viết kiểu SV). |
| **L0** | Một instance cho mỗi khối `u_` (khối mảng ghi `x N` → `generate for` N bản sao, cắt bit theo model), nối theo tên (`.port(net)`) theo port map trong model, net nội bộ khai báo `wire` đúng tên trong model/notes; glue logic bằng `assign`. |

Chung:
- Port list giống hệt bảng port (tên, hướng, width, thứ tự), kiểu ANSI Verilog-2005; output gán trong `always` là `output reg`.
- FSM: `localparam STATE_*` cho mã trạng thái + `reg` `state_q` / `state_d` + khối thanh ghi + khối `always @(*)` có `default` về trạng thái an toàn (mẫu trong `default_rtl_rules.md`).
- Header ngắn: tên module, 1–2 câu chức năng, đường dẫn spec/diagram.
- Code, tên định danh và comment chỉ dùng tiếng Anh. Comment ngắn theo kiến trúc khi giúp đọc (`// Accumulator state`). Không bắt buộc comment node id kiểu `// [reg_acc]` (trừ khi coding rule yêu cầu).
- Chỗ áp giả định `OPEN-xxx` → comment `// OPEN-xxx: <assumption>`.

Spec/diagram sai hoặc thiếu đến mức không viết được đúng chức năng (width không đủ, enable mơ hồ, FSM thiếu chuyển, diagram mâu thuẫn bảng port) → **dừng module đó**, không tự sửa thiết kế. Báo: file, vị trí, vấn đề, cần sửa ở S1 hay S2.

## Bước 4 – Kiểm tra (bắt buộc trước khi báo xong)

1. **Port list:**
   ```bash
   python3 .claude/skills/rtl-s3-rtl/scripts/check_ports.py rtl/<m>.v <file bảng port gate in ra>
   ```
2. **Compile/lint qua `sim/`** – không tự gõ lệnh simulator; đọc rồi dùng môi trường mô phỏng chung:
   - Đọc `sim/Makefile` và `sim/rtl.f`. Thiếu `sim/Makefile` → chép các file chưa có từ `.claude/skills/rtl-s5-tb/references/sim_env/` (không ghi đè file đã có); Makefile có sẵn mà chưa có target `lint` → báo, đề xuất chép target từ mẫu, ghi "chưa lint".
   - `sim/rtl.f`: S1 đã ghi sẵn `// ../rtl/<m>.v` → bỏ comment dòng đó (thành `../rtl/<m>.v`). Chưa có dòng nào của `<m>` → thêm, sau mọi module con và trước module cha. Không sửa dòng của module khác; dòng chứa `//` là comment, không được biên dịch.
   - Chạy (cần QuestaSim, `vlog` trong PATH):
     ```bash
     make -C sim lint TOP=<m>      # vlog -lint mọi file trong rtl.f (thư viện lint_work mới) + vopt cây <m>; log: sim/log/lint.log
     make -C sim lint              # khi còn module con chưa có RTL: chỉ compile, không elaborate
     ```
   - Lỗi → `make` dừng và in lại mọi dòng `** Error` (file, dòng) trong khối `ERRORS` ở cuối; log đầy đủ ở `sim/log/lint.log`.
   - Mục tiêu 0 error, không còn warning nghiêm trọng; warning còn lại phải giải thích được. File `.v` được biên dịch ở chế độ Verilog (không `-sv`): lỗi cú pháp do construct SV → sửa code, không chuyển sang SV. Lỗi ở file của module khác trong `rtl.f` → báo, không sửa. Module con cũ còn `.sv` → báo, không tự viết lại. Không có QuestaSim → ghi "chưa lint" và lệnh trên.
3. **Tự rà lỗi thật:**
   - Verilog-2005 thuần: không còn construct SV nào (`logic`, `always_ff`, `always_comb`, `typedef`, `enum`, `struct`, `'0`…); tín hiệu gán trong `always` là `reg`, gán bằng `assign` là `wire`.
   - Không latch (mọi nhánh gán đủ, `case` có `default`); reset đúng spec.
   - Không parameter nào mà spec không yêu cầu cấu hình.
   - Width: không cắt/mở rộng ngầm; phép có dấu khai báo `signed`.
   - FSM: đủ chuyển trạng thái, trạng thái lạ về trạng thái an toàn.
   - Kiến trúc: RTL có đủ các thanh ghi trạng thái và khối/instance quan trọng của diagram không, và không thêm kiến trúc mới?
   - Chức năng: duyệt nhanh từng hành vi trong spec, chỉ ra đoạn code thực hiện nó.

Lỗi lint/port do code của chính stage này → sửa rồi chạy lại đến khi sạch. Không cần synthesis, timing, formal, coverage, CDC tool.

## Đầu ra

`rtl/<m>.v` (Verilog-2005; cấu trúc thư mục khác chỉ khi coding rule quy định) và dòng của nó trong `sim/rtl.f` (đã bỏ comment). Một module một file. Làm lại module mà còn `rtl/<m>.sv` cũ do S3 tạo trước đây → xóa file `.sv` đó để không có hai bản.

## Báo cáo cuối (chỉ trong chat)

File đã tạo · ngôn ngữ (Verilog-2005) · level · kết quả check_ports và `make -C sim lint` (warning còn lại và lý do) · OPEN đã áp giả định · module con còn thiếu RTL · lệnh tiếp theo: module con còn thiếu, hoặc module cha; thiết kế xong ở đây – `/rtl-s4-vplan <m>` chỉ khi cần kiểm thử.

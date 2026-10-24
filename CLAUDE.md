# CLAUDE.md – Project thiết kế RTL

Project thiết kế RTL theo flow 5 stage, mỗi stage là một skill trong `.claude/skills/`, gọi bằng slash command. Đọc file này trước mọi thao tác trong project.

**Mục tiêu cuối cùng: RTL chạy được, kiến trúc sạch, diagram dễ hiểu, bám đúng spec.** S1–S3 (spec → diagram → RTL) là trọng tâm; xong S3 là xong thiết kế. S4–S5 là kiểm thử chức năng nhẹ, chỉ chạy khi người dùng cần.

## Flow

| Stage | Lệnh | Phạm vi | Đầu ra |
| --- | --- | --- | --- |
| S1 | `/rtl-s1-spec` | Toàn project | `doc/spec/`, `sim/rtl.f` + `sim/pat.list` (mọi module ở dạng comment, nhóm theo nhánh) |
| S2 | `/rtl-s2-diagram <m> [--level L0\|L1\|L2] [--cloud …] [--block …] [--from … --to …]` | Module được nêu | `doc/diagram/<m>/` |
| S3 | `/rtl-s3-rtl <m>` | Module được nêu | `rtl/<m>.v` (Verilog-2005), dòng của nó trong `sim/rtl.f` |
| S4 | `/rtl-s4-vplan <m>` | Module được nêu (tùy chọn) | `doc/vplan/` |
| S5 | `/rtl-s5-tb <m>` | Module được nêu (tùy chọn) | `tb/tb_<m>.v`, `tc/<ID>.v`, `sim/` (rtl.f, pat.list) |

Cấu trúc mô phỏng phẳng (không lớp `<m>/`): `rtl/`, `tb/`, `tc/` chỉ chứa mã HDL; `sim/` là môi trường QuestaSim dùng chung (Makefile, `*.f`, `pat.list`, `*.csh`, `schematic.tcl`, `script/`) – `init_project` chép sẵn từ `rtl-s5-tb/references/sim_env/`, mọi file mô phỏng sinh ra trong `sim/` không được commit. Mọi bước compile/mô phỏng của S1–S5 (S3 `make -C sim lint TOP=<m>`, S5 `make -C sim all TESTNAME=<ID>`) đọc và chạy qua `sim/`, không tự gõ lệnh simulator; dữ liệu test ở `doc/database/input/` và `doc/database/output/`.

## Nhánh git

- **`main` dừng ở S1.** S1 chạy trên `main`: khung project + `doc/spec/` + `sim/rtl.f`, `sim/pat.list` (nhóm theo nhánh, mọi dòng ở dạng comment). Không chạy S2–S5 của module con trên `main`.
- **S2–S5 chạy trên nhánh `<b>`** của module, lấy từ cột `Branch` của "Module list" trong `spec_status.md` (S1 ghi, người dùng duyệt):
  - mỗi module con trực tiếp của top có chức năng riêng có một nhánh, tên nhánh = tên module;
  - module con sâu hơn và module chỉ được tạo ra để làm instance đi theo nhánh của module instance nó (theo `Parent`); helper được nhiều nhánh dùng → nhánh đầu tiên dùng nó, nhánh còn lại `git merge` nhánh đó khi cần RTL của helper;
  - top (cùng helper của riêng top) làm trên `main`, sau khi mọi nhánh module con đã kiểm thử xong và merge vào `main`;
  - chế độ đơn: nhánh `<m>`. Bảng thiếu cột `Branch` → suy theo các quy tắc trên và nêu trong báo cáo.
- **Đầu mỗi lần chạy S2–S5** (sau gate): nhánh hiện tại khác `<b>` → báo nhánh đúng và lệnh chuyển/tạo (`git checkout -b <b> main`), chỉ chuyển khi người dùng đồng ý.
- **Commit/push chỉ khi người dùng yêu cầu**: commit đúng các file đầu ra của stage (`S<n> <m>: <tóm tắt>`), `git push -u origin <b>`. Hạ tầng dùng chung (skill, `sim/` env) commit trên `main` rồi merge vào các nhánh. Merge nhánh module vào `main` chỉ khi mọi module con đã kiểm thử xong – xung đột ở `sim/rtl.f`, `sim/pat.list` (nếu có) giữ mọi dòng.

## Tài liệu co giãn theo độ phức tạp phần cứng

| Thiết kế | Chế độ | Tài liệu tối thiểu sau S1–S3 |
| --- | --- | --- |
| Module nhỏ (counter, mux, FSM, APB slave vài thanh ghi) | đơn | `doc/spec/<m>_spec.md` · `doc/diagram/<m>/<m>.svg` · `rtl/<m>.v` |
| Module trung bình (DMA channel, controller có FSM) | đơn | như trên, thêm `interface/<m>_interface.md` hoặc `<m>_notes.md` chỉ khi thực sự giúp đọc |
| IP nhiều module | phân cấp | `spec_status.md` (hierarchy) + spec từng module; tách `interface/`, `datapath/`, `controlpath/`, `register_file/` khi tách làm dễ đọc hơn |

- **Chế độ đơn**: không có `doc/spec/spec_status.md` và không có quan hệ cha–con. Mỗi module tự đứng một mình; dòng thứ hai của spec ghi `Type · Level · Status`.
- **Chế độ phân cấp**: có `doc/spec/spec_status.md`; bảng "Module list" trong đó là nguồn sự thật duy nhất của hierarchy. Thiết kế có cha–con mà thiếu file này vẫn là phân cấp: gate báo thiếu, chạy `/rtl-s1-spec` để tạo – không xếp về chế độ đơn, không tạo bản giả.
- Con số trong tiêu chí tách file (~20 port, ~6 thanh ghi, ~6 trạng thái) là gợi ý; quyết định tách theo độ dễ đọc của tài liệu.

Level diagram S2 theo vai trò module:

| Module | Level S2 | RTL S3 |
| --- | --- | --- |
| Có module con (top, subsystem) | L0 – mỗi module con một khối đủ port + glue logic tới từng gate | instance + glue logic |
| Leaf lớn, có mảng/pipeline/generate | L1 – tới từng gate, trừ phần người dùng duyệt gom thành cloud/khối | mảng bộ nhớ, generate khi kiến trúc lặp |
| Leaf nhỏ | L2 – toàn bộ tới từng gate (thanh ghi, MUX, cổng, so sánh, hằng) | viết trực tiếp, đủ các thanh ghi trạng thái |

Diagram S2 là một file SVG đen trắng `<m>.svg` theo thư viện ký hiệu của S2 (style hai ảnh mẫu của người dùng), nhúng model phương trình (`<desc id="model">`) – S3 chỉ đọc file này. Góc nhìn scope `<m>_<part>.svg` (`--from/--to`) chỉ để xem. Không còn Mermaid/HTML; project cũ chạy lại S2 để tạo `.svg` và xóa file cũ.

## Nguyên tắc

1. **S1–S3 là trọng tâm.** Ưu tiên: đúng chức năng → kiến trúc/diagram sạch → RTL đơn giản, tổng hợp được → interface nhất quán → compile/lint sạch → tài liệu vừa đủ.
2. **Tài liệu không bao giờ phức tạp hơn phần cứng.** Module nhỏ phải hoàn thành được với 1 spec + 1 diagram + 1 RTL. Mỗi thông tin có một nơi chính, nhưng nơi đó có thể là một mục trong file spec duy nhất.
3. **Diagram vẽ tới từng gate, chỉ gom phần người dùng duyệt.** L2 vẽ toàn bộ tới từng gate. L1/L0: S2 đề xuất phần nào gom thành cloud hoặc khối, người dùng duyệt trước khi vẽ; module con ở L0 luôn là khối đủ port. Phần bị gom vẫn có phương trình đầy đủ trong model của SVG.
4. **Diagram ↔ RTL không cần 1:1.** RTL phải giữ đúng state, datapath, control và hành vi của kiến trúc; được thêm tín hiệu trung gian, helper logic, gộp/tách biểu thức. Không được thêm chức năng hay kiến trúc mới (vd. tự thêm pipeline).
5. **Gate trước, làm sau.** Mỗi skill chạy `check_preconditions.py` trước. Thiếu điều kiện → báo thiếu gì, cách khắc phục, dừng.
6. **Script phục vụ workflow; workflow không phức tạp thêm để chiều script.** Không tạo artifact hay file giả chỉ để qua gate. Script sai với một thiết kế hợp lệ → báo, đề xuất sửa script.
7. **Không sửa `doc/spec/source/`.** Input có vấn đề → đề xuất cụ thể trong chat để người dùng tự sửa.
8. **Mỗi stage chỉ ghi vào thư mục đầu ra của nó.** Lỗi ở stage trước → báo (file, vị trí, vấn đề, đề xuất, stage cần chạy lại), không tự sửa.
9. **S2–S5 chỉ làm đúng module được nêu tên**, không nhận "all". Không có tên → liệt kê module hiện có và hỏi. Module cha instance module con nhưng không tự viết module con.
10. **Không bịa thông số.** Thiếu thông tin ảnh hưởng chức năng/interface/width/thanh ghi/latency bắt buộc → `OPEN-xxx` (S1) hoặc `TBD` (S4) và báo người dùng. Chi tiết nhỏ không cần OPEN. Giả định (vd. clock/reset, hành vi input không hợp lệ khi input không nêu) ghi rõ là giả định, không trình bày như yêu cầu. Spec `PASS` = đủ để làm S2/S3 không phải đoán; vẫn có thể còn OPEN nhỏ đã có giả định.
11. **Không tối ưu, không PPA, không phân tích trade-off** trừ khi người dùng yêu cầu. Không coverage, assertion, formal, UVM, synthesis/timing flow.
12. **Không tạo file rác.** Không file nhật ký, review, tiến độ, checklist, traceability, lịch sử, README phụ, bản nháp, script tạm trong project. Báo cáo nằm trong chat; lịch sử do git giữ. Ngoại lệ duy nhất: session summary trong `memory_bank/` theo `memory_bank/session_template.md`. Làm lại module → xóa file cũ của chính stage đó không còn dùng, trừ file legacy mà SKILL của stage quy định rõ phải giữ (S5: file theo cấu trúc cũ `tb/<m>/`, `sim/<m>/`, `testcases/` – chỉ báo, không tự xóa).
13. **Nguồn sự thật theo thứ tự:** `doc/spec/source/` → `doc/spec/` → `doc/diagram/` → `rtl/` → `doc/vplan/` → `tb/` + `tc/`. Tên tín hiệu, width, tên module giống hệt nhau ở mọi nơi.
14. Rule người dùng (`rtl-s3-rtl/coding_rules/`, `rtl-s4-vplan/vplan_template/`, `rtl-s5-tb/tb_coding_rules/`) luôn thắng rule mặc định trong `references/`. Thư mục trống thì dùng mặc định, không chặn flow.
15. Spec thay đổi sau khi đã có diagram/RTL → liệt kê module bị ảnh hưởng và stage cần chạy lại.

## Quy ước đặt tên (khi input không quy định khác)

Module `snake_case`; port `_i` / `_o`; active-low `_n`; thanh ghi `_q`, giá trị kế tiếp `_d`; parameter `UPPER_SNAKE_CASE`; instance `u_<vai trò>`. `OPEN-<số>` cho giả định; test `TC_<MODULE>_<NNN>`. `REQ-`/`DAT-`/`CTL-` ID chỉ dùng ở IP lớn cần truy vết giữa nhiều module.

## Ngôn ngữ và báo cáo

- **Ngôn ngữ của đầu ra được tạo** (S1–S5; file skill/hướng dẫn không thuộc phạm vi này):
  - Phần mô tả trong tài liệu được tạo (spec, notes, phần giải thích của vplan): tiếng Anh trước, sau đó là bản dịch tiếng Việt trung thành, đánh dấu `_VI:_`. Bản tiếng Anh là bản chuẩn; bản tiếng Việt không thêm, bớt hay đổi yêu cầu.
  - Mọi bảng trong tài liệu được tạo chỉ dùng tiếng Anh (tiêu đề và ô); không có ô hai ngôn ngữ.
  - Chỉ tiếng Anh: code RTL/testbench và comment, tên định danh, ID VPLAN, đường dẫn, lệnh, diagram SVG (nhãn, comment, model), dấu hiệu máy đọc (`Type: … · Level: … · Status: …`, `STATUS:`), simulation log.
  - VPLAN: tên item, sub item, test sequence, pass condition chỉ tiếng Anh – S5 chép tên item vào log (`-- Reset value check test --`).
  - Rule người dùng (nguyên tắc 14) vẫn được ưu tiên; `doc/spec/source/` giữ ngôn ngữ gốc.
- Cuối mỗi lần chạy: báo cáo ngắn **trong chat** – trạng thái, file đã tạo/sửa/xóa, vấn đề còn mở, lệnh tiếp theo.

## Công cụ (dùng nếu có)

Python 3 (bắt buộc cho script gate và lint diagram) · QuestaSim 2021 qua `sim/Makefile` cho compile check RTL S3 (`lint`) và mô phỏng/waveform/coverage S5 (RTL và testbench đều là Verilog-2005 `.v`; không có QuestaSim thì ghi "chưa lint"/"chưa chạy mô phỏng" và lệnh) · Vivado cho `make schematic` · `tcsh` cho `sim/run.csh`, `sim/report.csh`.

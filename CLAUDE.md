# CLAUDE.md – Project thiết kế RTL

Project thiết kế RTL theo flow 5 stage, mỗi stage là một skill trong `.claude/skills/`, gọi bằng slash command. Đọc file này trước mọi thao tác trong project.

**Mục tiêu cuối cùng: RTL chạy được, kiến trúc sạch, diagram dễ hiểu, bám đúng spec.** S1–S3 (spec → diagram → RTL) là trọng tâm; xong S3 là xong thiết kế. S4–S5 là kiểm thử chức năng nhẹ, chỉ chạy khi người dùng cần.

## Flow

| Stage | Lệnh | Phạm vi | Đầu ra |
| --- | --- | --- | --- |
| S1 | `/rtl-s1-spec` | Toàn project | `doc/spec/` |
| S2 | `/rtl-s2-diagram <m> [--level L0\|L1\|L2] [--format mermaid\|html\|both]` | Module được nêu | `doc/diagram/<m>/` |
| S3 | `/rtl-s3-rtl <m>` | Module được nêu | `rtl/<m>.v` (Verilog-2005) |
| S4 | `/rtl-s4-vplan <m>` | Module được nêu (tùy chọn) | `doc/vplan/` |
| S5 | `/rtl-s5-tb <m>` | Module được nêu (tùy chọn) | `tb/<m>/tb_<m>.v`, `sim/<m>/` |

## Tài liệu co giãn theo độ phức tạp phần cứng

| Thiết kế | Chế độ | Tài liệu tối thiểu sau S1–S3 |
| --- | --- | --- |
| Module nhỏ (counter, mux, FSM, APB slave vài thanh ghi) | đơn | `doc/spec/<m>_spec.md` · `doc/diagram/<m>/<m>.mmd` · `rtl/<m>.v` |
| Module trung bình (DMA channel, controller có FSM) | đơn | như trên, thêm `interface/<m>_interface.md` hoặc `<m>_notes.md` chỉ khi thực sự giúp đọc |
| IP nhiều module | phân cấp | `spec_status.md` (hierarchy) + spec từng module; tách `interface/`, `datapath/`, `controlpath/`, `register_file/` khi tách làm dễ đọc hơn |

- **Chế độ đơn**: không có `doc/spec/spec_status.md` và không có quan hệ cha–con. Mỗi module tự đứng một mình; dòng đầu spec ghi `Loại · Level · Trạng thái`.
- **Chế độ phân cấp**: có `doc/spec/spec_status.md`; bảng "Danh sách module" trong đó là nguồn sự thật duy nhất của hierarchy. Thiết kế có cha–con mà thiếu file này vẫn là phân cấp: gate báo thiếu, chạy `/rtl-s1-spec` để tạo – không xếp về chế độ đơn, không tạo bản giả.
- Con số trong tiêu chí tách file (~20 port, ~6 thanh ghi, ~6 trạng thái) là gợi ý; quyết định tách theo độ dễ đọc của tài liệu.

Level diagram S2 theo vai trò module:

| Module | Level S2 | RTL S3 |
| --- | --- | --- |
| Có module con (top, subsystem) | L0 – khối + nối dây | instance + glue logic |
| Leaf lớn, có mảng/pipeline/generate | L1 – vi kiến trúc | mảng bộ nhớ, generate khi kiến trúc lặp |
| Leaf nhỏ | L2 – phác thảo hướng RTL: thanh ghi + logic chính | viết trực tiếp, đủ các thanh ghi trạng thái |

Định dạng S2 (`--format`, mặc định `mermaid`): L0/L1 và L2 không phải leaf chỉ Mermaid; một module leaf L2 được `mermaid` / `html` / `both`. `<m>.mmd` là diagram chính thức – S3 chỉ đọc `.mmd`. `<m>.html` là RTL schematic chi tiết để xem (render từ cùng mô hình kiến trúc + lớp chi tiết RTL của từng khối), không phải dependency của S3–S5.

## Nguyên tắc

1. **S1–S3 là trọng tâm.** Ưu tiên: đúng chức năng → kiến trúc/diagram sạch → RTL đơn giản, tổng hợp được → interface nhất quán → compile/lint sạch → tài liệu vừa đủ.
2. **Tài liệu không bao giờ phức tạp hơn phần cứng.** Module nhỏ phải hoàn thành được với 1 spec + 1 diagram + 1 RTL. Mỗi thông tin có một nơi chính, nhưng nơi đó có thể là một mục trong file spec duy nhất.
3. **Diagram là mô hình kiến trúc, không phải sơ đồ cổng.** Không vẽ từng AND/OR/inverter/hằng/comparator nhỏ trừ khi nó quan trọng về kiến trúc. 15 node sạch hơn 50 node rối. (Áp cho `.mmd`; `<m>.html` của leaf L2 cố ý là RTL schematic mức primitive – mục 8 `diagram_conventions.md` của S2.)
4. **Diagram ↔ RTL không cần 1:1.** RTL phải giữ đúng state, datapath, control và hành vi của kiến trúc; được thêm tín hiệu trung gian, helper logic, gộp/tách biểu thức. Không được thêm chức năng hay kiến trúc mới (vd. tự thêm pipeline).
5. **Gate trước, làm sau.** Mỗi skill chạy `check_preconditions.py` trước. Thiếu điều kiện → báo thiếu gì, cách khắc phục, dừng.
6. **Script phục vụ workflow; workflow không phức tạp thêm để chiều script.** Không tạo artifact hay file giả chỉ để qua gate. Script sai với một thiết kế hợp lệ → báo, đề xuất sửa script.
7. **Không sửa `doc/spec/source/`.** Input có vấn đề → đề xuất cụ thể trong chat để người dùng tự sửa.
8. **Mỗi stage chỉ ghi vào thư mục đầu ra của nó.** Lỗi ở stage trước → báo (file, vị trí, vấn đề, đề xuất, stage cần chạy lại), không tự sửa.
9. **S2–S5 chỉ làm đúng module được nêu tên**, không nhận "all". Không có tên → liệt kê module hiện có và hỏi. Module cha instance module con nhưng không tự viết module con.
10. **Không bịa thông số.** Thiếu thông tin ảnh hưởng chức năng/interface/width/thanh ghi/latency bắt buộc → `OPEN-xxx` (S1) hoặc `TBD` (S4) và báo người dùng. Chi tiết nhỏ không cần OPEN. Giả định (vd. clock/reset, hành vi input không hợp lệ khi input không nêu) ghi rõ là giả định, không trình bày như yêu cầu. Spec `PASS` = đủ để làm S2/S3 không phải đoán; vẫn có thể còn OPEN nhỏ đã có giả định.
11. **Không tối ưu, không PPA, không phân tích trade-off** trừ khi người dùng yêu cầu. Không coverage, assertion, formal, UVM, synthesis/timing flow.
12. **Không tạo file rác.** Không file nhật ký, review, tiến độ, checklist, traceability, lịch sử, README phụ, bản nháp, script tạm trong project. Báo cáo nằm trong chat; lịch sử do git giữ. Làm lại module → xóa file cũ của chính stage đó không còn dùng, trừ file legacy mà SKILL của stage quy định rõ phải giữ (S5: giữ `tb_<m>.sv` cũ, chỉ báo – không tự xóa).
13. **Nguồn sự thật theo thứ tự:** `doc/spec/source/` → `doc/spec/` → `doc/diagram/` → `rtl/` → `doc/vplan/` → `tb/`. Tên tín hiệu, width, tên module giống hệt nhau ở mọi nơi.
14. Rule người dùng (`rtl-s3-rtl/coding_rules/`, `rtl-s4-vplan/vplan_template/`, `rtl-s5-tb/tb_coding_rules/`) luôn thắng rule mặc định trong `references/`. Thư mục trống thì dùng mặc định, không chặn flow.
15. Spec thay đổi sau khi đã có diagram/RTL → liệt kê module bị ảnh hưởng và stage cần chạy lại.

## Quy ước đặt tên (khi input không quy định khác)

Module `snake_case`; port `_i` / `_o`; active-low `_n`; thanh ghi `_q`, giá trị kế tiếp `_d`; parameter `UPPER_SNAKE_CASE`; instance `u_<vai trò>`. `OPEN-<số>` cho giả định; test `TC_<MODULE>_<NNN>`. `REQ-`/`DAT-`/`CTL-` ID chỉ dùng ở IP lớn cần truy vết giữa nhiều module.

## Ngôn ngữ và báo cáo

- Tài liệu tiếng Việt; tên tín hiệu, module, code giữ tiếng Anh.
- Cuối mỗi lần chạy: báo cáo ngắn **trong chat** – trạng thái, file đã tạo/sửa/xóa, vấn đề còn mở, lệnh tiếp theo.

## Công cụ (dùng nếu có)

Python 3 (bắt buộc cho script gate) · Node.js + `npm install --prefix .claude/skills/rtl-s2-diagram/scripts` để parse Mermaid bằng thư viện thật · `verilator` / `iverilog` cho lint và mô phỏng (RTL S3 lint ở chế độ Verilog-2005: `iverilog -g2005`, `verilator --default-language 1364-2005`; testbench S5 cũng là Verilog-2005 `.v`, mô phỏng bằng `iverilog -g2005`).

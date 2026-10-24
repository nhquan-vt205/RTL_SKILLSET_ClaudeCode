---
name: rtl-s2-diagram
description: Stage 2 của RTL flow – vẽ sơ đồ logic SVG đen trắng (<m>.svg; MUX, register/FF, gate, ellipse operator, cloud, bus bundle, khối submodule, bộ nhớ theo thư viện ký hiệu của người dùng) cho MỘT module được chỉ định, mức chi tiết theo level – L2 leaf nhỏ vẽ tới từng gate, L1 leaf lớn vẽ tới từng gate trừ phần người dùng duyệt gom thành cloud/khối, L0 vẽ mỗi module con thành khối đủ port + glue logic tới từng gate. SVG nhúng model phương trình để S3 đọc. Tùy chọn góc nhìn phụ theo scope --from/--to. Dùng khi người dùng gọi /rtl-s2-diagram <module> hoặc yêu cầu vẽ sơ đồ logic, sơ đồ khối cho một module.
argument-hint: "<tên_module> [tên_module ...] [--level L0|L1|L2] [--cloud <phần,...>] [--block <phần,...>] [--from <tín hiệu,...> --to <tín hiệu,...> [--part <tên>]]"
disable-model-invocation: true
---

# Stage 2 – Sơ đồ logic SVG

Tham số: `$ARGUMENTS` – một hoặc nhiều tên module; tùy chọn `--level L0|L1|L2` (áp cho mọi module trong lệnh); `--cloud`/`--block` (tên các phần được gom, bỏ qua bước hỏi duyệt); `--from ... --to ... [--part ...]` (góc nhìn scope, chỉ cho **một** module).

Diagram là **sơ đồ logic đủ để viết RTL**, theo style hai ảnh mẫu của người dùng: đen trắng, MUX hình thang, FF chữ nhật + tam giác clock + bubble reset, gate AND/OR/XOR + bubble đảo, ellipse operator, cloud, bus bundle, junction dot. Mức chi tiết co giãn theo level: module nhỏ vẽ tới từng gate; module lớn chỉ gom những phần **người dùng đã duyệt**. Ưu tiên: **đúng phần cứng → dễ đọc → rõ luồng tín hiệu**.

Ngôn ngữ đầu ra: `.svg` (nhãn, comment, model) chỉ dùng tiếng Anh ASCII. `<m>_notes.md` (nếu có): phần mô tả tiếng Anh trước + bản dịch `_VI:_`, bảng chỉ tiếng Anh.

## Phạm vi

- Chỉ làm đúng module(s) được nêu tên; không nhận "all", không tiện tay vẽ module cha/con. Không có tên → liệt kê module hiện có (gate in ra) kèm level đề xuất và hỏi.
- Không sửa `doc/spec/`. Spec thiếu/sai → dừng module đó, báo file + mục + vấn đề + đề xuất.
- Đầu ra chỉ trong `doc/diagram/<m>/`. Khi vẽ lại, xóa file cũ của module không còn dùng: notes không còn cần, góc nhìn `<m>_<part>.svg` không còn khớp, và mọi file định dạng cũ (`*.mmd`, `<m>.html`, `_ff_notes.md`) – S3 chỉ đọc `.svg`.

## Bước 0 – Gate

```bash
python3 .claude/skills/rtl-s2-diagram/scripts/check_preconditions.py --stage 2 --module <m> [<m2> ...] [--level Lx]
```

Gọi một lần với **mọi module của lệnh**, kèm đúng `--level` người dùng đưa; mỗi module có một khối kết quả riêng. Khối nào `KHÔNG ĐỦ ĐIỀU KIỆN` → bỏ qua module đó, báo các dòng `[THIẾU]` và cách khắc phục. Mã thoát 2 (gọi sai) → dừng cả lệnh, báo nguyên văn lỗi. Dòng `[INFO]` cho biết chế độ (đơn/phân cấp), file spec và bảng port cần đọc, level đề xuất, file định dạng cũ cần xóa. Lệnh có `--from/--to` mà nêu nhiều module → dừng, đề nghị gọi riêng từng module.

**Nhánh git** (mục "Nhánh git" của `CLAUDE.md`): sau gate, chuyển sang nhánh `feat/<b>` của `<m>` (lệnh nhiều module mà khác nhánh → gọi riêng từng nhánh) (cột `Branch` của `spec_status.md`; chế độ đơn `feat/<m>`), tạo từ `main` nếu chưa có. Hoàn thành stage → commit đúng các file đầu ra của S2 và `git push -u origin feat/<b>`; không merge, không push `main`.

## Bước 1 – Chọn level

Ưu tiên: `--level` → level trong spec/`spec_status.md` → mặc định (có module con → L0, leaf → L2). Được lệch đề xuất nếu đọc spec thấy rõ không hợp (vd. leaf "nhỏ" có mảng 64 thanh ghi và nhiều khối điều khiển → L1); nêu lý do trong báo cáo.

| Level | Dùng cho | Mức chi tiết (mục 2 của `diagram_conventions.md`) |
| --- | --- | --- |
| **L0** – khối / hierarchy | top, subsystem: có module con | mỗi module con là một khối `u_` vẽ đủ port (trừ clk/rst); glue logic tới từng gate; người dùng có thể duyệt gom thêm phần glue thành cloud |
| **L1** – leaf lớn | pipeline, mảng thanh ghi/bộ nhớ, DMA engine, controller lớn; block có module con **và** nhiều logic riêng | tới từng gate, trừ các phần người dùng duyệt gom thành `cloud_` hoặc khối `blk_`; module con (nếu có) là khối `u_` |
| **L2** – leaf nhỏ | counter, FSM, FIFO nhỏ, APB slave ít thanh ghi | toàn bộ tới từng gate: mỗi thanh ghi, MUX, cổng, so sánh, phép toán, hằng |

## Bước 2 – Đọc spec

Đọc file spec và bảng port mà gate in ra (`[OK] spec:`, `[OK] bảng port:`), cùng các tài liệu tách riêng nếu gate liệt kê (parameter, register map, FSM). L0/L1 có instance: đọc thêm bảng port của module con. Ghi lại tên field trong register map (để ghi vào ô register).

Kiểm tra chức năng trước khi vẽ: mọi output được tạo từ đâu, mọi thanh ghi cập nhật khi nào và reset về gì, mọi enable/select có nguồn. Spec không đủ để xác định (width trung gian, điều kiện enable, chuyển FSM) → dừng, báo lỗi spec; không đoán.

Latency: chỉ kiểm khi spec **yêu cầu** latency/throughput cụ thể – đếm tầng thanh ghi trên đường dữ liệu và so với spec.

## Bước 3 – Đề xuất trừu tượng hóa (L1, L0) – chờ người dùng duyệt

- L2: bỏ qua bước này (vẽ tới từng gate).
- L1/L0 có `--cloud`/`--block`: dùng đúng lựa chọn đó; phần không nêu tên vẽ tới từng gate.
- L1/L0 không có `--cloud`/`--block`: chia logic thành các phần theo chức năng, trình bày bảng `Part | Signals in → out | Proposal (gate/cloud/blk) | Reason` (mẫu ở mục 2 của `diagram_conventions.md`) và **dừng, chờ người dùng duyệt hoặc sửa**. Không vẽ trước khi có câu trả lời. Module con ở L0 luôn là khối `u_`, không cần hỏi.

Khối `blk_` trong leaf chỉ là cách vẽ – S3 vẫn viết phần đó trong cùng module.

## Bước 4 – Vẽ `<m>.svg`

Theo `references/diagram_conventions.md` (khung file, ký hiệu, dây/nhãn/bố cục, model) và ví dụ cùng level (`example_l0_dma_top.svg`, `example_l1_sync_fifo.svg`, `example_l2_acc_unit.svg`). Ký hiệu chép đúng hình học trong `references/symbol_library.svg` / mục 3 – không tự chế ký hiệu; phần tử chưa có ký hiệu → hỏi người dùng mô tả.

- Header comment (`module`, `stage : 2 - diagram Lx`, `source`, `param` nếu có) – gate S3 đọc level từ đây.
- Mọi port trong bảng port có nhãn (bus chuẩn gom `prefix_*` được; clk không vẽ; reset ghi dưới bubble).
- Ô register ghi tên field theo spec, không có thì tên `_q` trong spec, kèm `[msb:lsb]` khi nhiều bit; FF không có tên trong spec để trống.
- Khối `u_`/`blk_`/`mem_`: nhãn giữa khối, tên port ghi trên dây sát cạnh khung, ngoài khung.
- `<desc id="model">`: phương trình từng nhóm `reg_`/`fsm_`/`mem_`/`cloud_`/`blk_`/`u_` (và `mux_`/`op_` khi giúp đọc) – phần bị gom viết đủ, kể cả thanh ghi bên trong. Bản vẽ và model phải khớp.
- Một file `<m>.svg` cho toàn module. Không có định dạng xem phụ (không HTML, không PNG).

Viết SVG xong, tự rà bố cục từ toạ độ: mỗi dây nối đúng chân ở cả hai đầu, junction dot ở mọi điểm rẽ, không chữ đè dây/khối, dây song song cách ≥ 20px.

## Bước 5 – Góc nhìn scope (chỉ khi có `--from/--to`)

Ngoài `<m>.svg` (vẽ hoặc giữ nguyên nếu đã có và vẫn khớp spec), xuất `<m>_<part>.svg` chỉ chứa logic từ các tín hiệu `--from` tới các tín hiệu `--to` – mục 6 của `diagram_conventions.md`. Tên tín hiệu không có trong spec hoặc scope mơ hồ → hỏi lại trước khi vẽ. Góc nhìn chỉ để xem; S3 đọc `<m>.svg`.

## Bước 6 – Ghi chú thiết kế (chỉ khi cần)

Mặc định **không tạo** `<m>_notes.md`. Tạo khi diagram + model + spec chưa đủ để viết RTL không phải đoán, thường là L1 phức tạp hoặc L0 lớn: cấu trúc hiện thực cần chốt (mảng bộ nhớ, pipeline, generate, mã hóa trạng thái), net nội bộ của L0 nhiều instance. Mẫu ở mục 7 của `references/diagram_conventions.md`.

## Bước 7 – Lint

```bash
python3 .claude/skills/rtl-s2-diagram/scripts/lint_svg.py doc/diagram/<m>/*.svg --interface <file bảng port gate in ra>
```

Sửa đến khi `KẾT QUẢ: OK`. Lint kiểm: XML, header/level, đen trắng, phần tử cấm, tiếng Anh, tiền tố id, model khớp nhóm, luật level, tên port không nằm trong khối, phủ port. Lint **không** kiểm bố cục – đó là việc tự rà ở Bước 4. Cảnh báo "nhiều primitive" → đề xuất người dùng gom thêm hoặc dùng góc nhìn scope, không tự gom.

## Đầu ra

```
doc/diagram/<m>/
├── <m>.svg          # diagram chính thức; header ghi level, <desc id="model"> cho S3
├── <m>_<part>.svg   # chỉ khi có --from/--to: góc nhìn scope, S3 không đọc
└── <m>_notes.md     # chỉ khi cần (Bước 6)
```

Không tạo README, PNG hay file phụ khác.

## Báo cáo cuối (chỉ trong chat)

Module · level (và lý do nếu khác đề xuất) · phần đã gom (cloud/khối) theo duyệt của người dùng · các thanh ghi/khối/instance chính · tên tín hiệu trung gian tự đặt · latency so với spec (chỉ khi spec yêu cầu) · file đã tạo/xóa · kết quả lint · lệnh tiếp theo `/rtl-s3-rtl <m>`.

---
name: rtl-s2-diagram
description: Stage 2 của RTL flow – vẽ diagram kiến trúc Mermaid (.mmd, mở được trên mermaid.live) cho MỘT module được chỉ định, ở level phù hợp – L0 sơ đồ khối/nối dây cho top và subsystem, L1 vi kiến trúc cho leaf lớn, L2 phác thảo hướng RTL (thanh ghi + logic chính) cho leaf nhỏ. Mặc định chỉ một file <m>.mmd; file ghi chú chỉ khi kiến trúc phức tạp. Riêng một module leaf L2 có thể xuất thêm (hoặc chỉ) <m>.html – RTL schematic chi tiết (DFF, MUX, comparator, cổng, phép toán, hằng, dây, feedback, clock/reset) để xem trên browser; artifact xem tùy chọn, S3 chỉ dùng .mmd. Dùng khi người dùng gọi /rtl-s2-diagram <module> hoặc yêu cầu vẽ sơ đồ khối, sơ đồ vi kiến trúc cho một module.
argument-hint: "<tên_module> [tên_module ...] [--level L0|L1|L2] [--format mermaid|html|both]"
disable-model-invocation: true
---

# Stage 2 – Diagram kiến trúc

Tham số: `$ARGUMENTS` – một hoặc nhiều tên module, tùy chọn `--level L0|L1|L2` (áp cho mọi module trong lệnh), tùy chọn `--format mermaid|html|both` (mặc định `mermaid` – hành vi như trước).

Diagram là **mô hình kiến trúc đủ để viết RTL**, không phải sơ đồ cổng và không phải AST của RTL. Nó cho thấy: ranh giới module, thanh ghi/trạng thái, datapath chính, khối điều khiển, đường dữ liệu lớn. Ưu tiên: **dễ đọc → rõ kiến trúc → rõ luồng tín hiệu**, trước mọi sự đầy đủ chi tiết. Diagram 15 node sạch tốt hơn 50 node trông như netlist.

Ngôn ngữ đầu ra: `.mmd` (nhãn node/cạnh, comment `%%`) và `<m>.html` chỉ dùng tiếng Anh – không đưa tiếng Việt vào nhãn, tên tín hiệu, tên module. `<m>_notes.md` (nếu có): phần mô tả tiếng Anh trước + bản dịch `_VI:_`, bảng chỉ tiếng Anh.

## Phạm vi

- Chỉ làm đúng module(s) được nêu tên; không nhận "all", không tiện tay vẽ module cha/con. Không có tên → liệt kê module hiện có (gate in ra) kèm level đề xuất và hỏi.
- Không sửa `doc/spec/`. Spec thiếu/sai → dừng module đó, báo file + mục + vấn đề + đề xuất.
- Đầu ra chỉ trong `doc/diagram/<m>/`. Khi vẽ lại, xóa file cũ của module không còn dùng (part cũ, notes không còn cần, `_ff_notes.md` bản cũ, `<m>.html` không còn khớp `.mmd` mới).

## Bước 0 – Gate

```bash
python3 .claude/skills/rtl-s2-diagram/scripts/check_preconditions.py --stage 2 --module <m> [<m2> ...] [--level Lx] [--format F]
```

Gọi một lần với **mọi module của lệnh**, kèm đúng `--level`/`--format` người dùng đưa; mỗi module có một khối kết quả riêng. Khối nào `KHÔNG ĐỦ ĐIỀU KIỆN` → bỏ qua module đó, báo các dòng `[THIẾU]` và cách khắc phục. Mã thoát 2 (gọi sai, vd. `--format html|both` với nhiều module) → dừng cả lệnh, báo nguyên văn lỗi. Dòng `[INFO]` cho biết chế độ (đơn/phân cấp), file spec và bảng port cần đọc, level đề xuất, định dạng.

## Bước 1 – Chọn level và định dạng

Ưu tiên: `--level` → level trong spec/`spec_status.md` → mặc định (có module con → L0, leaf → L2). Được lệch đề xuất nếu đọc spec thấy rõ không hợp (vd. leaf "nhỏ" có mảng 64 thanh ghi → L1); nêu lý do trong báo cáo.

| Level | Dùng cho | Thể hiện |
| --- | --- | --- |
| **L0** – khối / hierarchy | top, subsystem: có module con, logic riêng chủ yếu là nối dây | instance module con, interface chính, kết nối data/control chính, ít glue logic. Không vẽ mọi tín hiệu nội bộ. |
| **L1** – vi kiến trúc | leaf lớn, pipeline, mảng thanh ghi/bộ nhớ, mảng PE/MAC, DMA engine, controller lớn | nhóm thanh ghi, bộ nhớ, khối tổ hợp chức năng (`Address generation`, `MAC`, `Handshake`, `Decode`), tầng pipeline, FSM, MUX chọn dữ liệu chính, cấu trúc lặp |
| **L2** – phác thảo hướng RTL | leaf nhỏ: counter, FSM, FIFO nhỏ, APB slave ít thanh ghi | các thanh ghi (`state_q`, `count_q`, `data_q`), khối next-state / next-value, MUX hoặc phép toán chính. **Không** vẽ từng AND/OR/inverter/hằng/comparator nhỏ. |

Định dạng (`--format`):

| Module | `mermaid` (mặc định) | `html` | `both` |
| --- | --- | --- | --- |
| L0, L1 | `<m>.mmd` | không | không |
| L2 leaf | `<m>.mmd` | `<m>.html` | `<m>.mmd` + `<m>.html` |
| L2 không phải leaf (có module con, hoặc `Type` là `top`/`block`) | `<m>.mmd` | không | không |

- `html`/`both` chỉ khi lệnh có **đúng một module**, module là **leaf** theo hierarchy (gate kiểm: không có module con, `Type` không phải `top`/`block`) và level **L2**. Gate báo `[THIẾU]` hoặc mã thoát 2 → dừng, báo lỗi; **không tự chuyển sang Mermaid**.
- Với `html`/`both`, level phải giữ L2: đọc spec thấy cần lệch sang L1 → dừng, báo lý do, đề nghị gọi lại với `--format mermaid`.
- `<m>.mmd` luôn là diagram chính thức (S3 chỉ đọc nó) – mô hình khối, trả lời "module gồm những khối nào". `<m>.html` là **RTL schematic chi tiết** để người thiết kế xem – trả lời "các khối phần cứng nối với nhau thế nào" ở mức DFF/MUX/comparator/cổng/phép toán/hằng; không phải dependency của stage nào.
- Mỗi định dạng chỉ ghi file của nó: `mermaid` chỉ ghi `.mmd` (`.html` cũ không còn khớp thì xóa, mục Phạm vi), `html` chỉ ghi `.html` (không đụng `.mmd` đã có), `both` ghi cả hai.

## Bước 2 – Đọc spec

Đọc file spec và bảng port mà gate in ra (`[OK] spec:`, `[OK] bảng port:`), cùng các tài liệu tách riêng nếu gate liệt kê (parameter, register map, FSM). L0/L1 có instance: đọc thêm bảng port của module con.

## Bước 3 – Vẽ mô hình kiến trúc (Mermaid)

Mô hình kiến trúc là đồ thị node/cạnh theo quy ước Mermaid của S2. **`.mmd` và `.html` đều sinh từ đúng một mô hình này**: `.mmd` là chính mô hình, `.html` do `render_html.py` render từ nó cộng lớp chi tiết RTL của từng khối (Bước 6) – không vẽ tay HTML. `--format html` mà gate báo đã có `<m>.mmd` → không vẽ lại, bỏ qua Bước 3–5, sang Bước 6 render từ file đó.

Theo `references/diagram_conventions.md` và ví dụ cùng level (`example_l0_dma_top.mmd`, `example_l1_sync_fifo.mmd`, `example_l2_acc_unit.mmd`).

- Mọi port trong bảng port có mặt (gom bus thành một node `prefix_*` được).
- Mỗi thanh ghi/nhóm thanh ghi mang trạng thái có node riêng, nhãn có tên `_q` và width. Logic tổ hợp gom thành khối theo chức năng; chỉ tách phép toán/MUX thành node riêng khi nó là điểm chính của kiến trúc.
- Nhãn khối ghi hành vi ngắn gọn (phương trình chính) để S3 viết được code; chi tiết dài để trong spec hoặc notes.
- Dữ liệu nét liền có nhãn `tên [width]`; điều khiển nét đứt.
- Mặc định **một file `<m>.mmd`**. Chỉ chia (`<m>_<phần>.mmd`) khi một hình thực sự không đọc được hoặc có phần độc lập rõ ràng; số file tối thiểu. Phần cần chi tiết riêng mà đủ lớn thì nên là module con ở S1. (`html`/`both` luôn một file `<m>.mmd`.)

Kiểm tra chức năng trước khi vẽ xong: mọi output được tạo từ đâu, mọi thanh ghi cập nhật khi nào, mọi enable/select có nguồn. Spec không đủ để xác định điều đó (width trung gian, điều kiện enable, chuyển FSM) → dừng, báo lỗi spec; không đoán.

Latency: chỉ kiểm khi spec **yêu cầu** latency/throughput cụ thể – đếm tầng thanh ghi trên đường dữ liệu và so với spec. Spec không yêu cầu → không phân tích latency.

## Bước 4 – Ghi chú thiết kế (chỉ khi cần)

Mặc định **không tạo** `<m>_notes.md`. Tạo khi diagram + spec chưa đủ để viết RTL không phải đoán, thường là L1 phức tạp hoặc L0 lớn:

- nhiều cấu trúc hiện thực cần chốt (mảng bộ nhớ, pipeline, generate, mã hóa trạng thái);
- quy ước nối dây/net nội bộ của L0 nhiều instance;
- phương trình dài không vừa nhãn node.

Mẫu ở mục 7 của `references/diagram_conventions.md`. Notes bổ sung cho diagram, không chép lại spec và không cần liệt kê từng node.

## Bước 5 – Lint

```bash
python3 .claude/skills/rtl-s2-diagram/scripts/lint_mermaid.py doc/diagram/<m>/*.mmd --interface <file bảng port gate in ra> --parse
```

Sửa đến khi `KẾT QUẢ: OK`. Cảnh báo "nhiều node" → cân nhắc gom logic nhỏ vào khối. `--parse` cần Node.js + `npm install --prefix .claude/skills/rtl-s2-diagram/scripts`; không có thì script tự bỏ qua – ghi "chưa parse bằng Mermaid" trong báo cáo.

`--format html` không ghi `.mmd` → bỏ bước này; `render_html.py` tự lint mô hình bằng cùng luật (kể cả phủ port khi có `--interface`).

## Bước 6 – HTML RTL schematic (chỉ `--format html|both`)

Mô hình khối (Bước 3) cố ý gom AND/comparator/hằng vào nhãn; HTML cần mức chi tiết RTL nên có thêm **lớp chi tiết RTL**: phương trình kiểu Verilog-2005 cho từng khối của mô hình (`[blk_x]`, `[mux_x]`, `[reg_x]`...) – cú pháp, luật và ví dụ ở mục 8 của `references/diagram_conventions.md`. Viết từ spec + mô hình khối, đúng phần cứng RTL sẽ có: thanh ghi chỉ trong `reg_`/`fsm_`, mọi dây giữa hai khối phải là một cạnh của mô hình. Lớp chi tiết chỉ đưa qua stdin, không lưu file trong project; script nhúng nó vào HTML.

Render bằng script – không tự viết HTML/SVG, không nhúng Mermaid:

```bash
# both, hoặc html khi đã có <m>.mmd: mô hình từ chính file .mmd (không ghi lại .mmd), lớp chi tiết qua stdin
python3 .claude/skills/rtl-s2-diagram/scripts/render_html.py doc/diagram/<m>/<m>.mmd --detail - --interface <file bảng port> <<'SCH'
[blk_dec]
addr_hit = paddr_i == 10'h000;
...
SCH

# html khi chưa có .mmd: mô hình (đúng nội dung Bước 3), dòng '%% schematic', rồi lớp chi tiết – chỉ ghi doc/diagram/<m>/<m>.html
python3 .claude/skills/rtl-s2-diagram/scripts/render_html.py - --interface <file bảng port> <<'SCH'
%% module : <m>
%% stage  : 2 - diagram L2 (RTL-oriented sketch)
...
%% schematic
[blk_dec]
...
SCH

# kiểm metadata, file tự chứa, lớp chi tiết khớp mô hình, (khi có .mmd) cùng mô hình với .mmd
python3 .claude/skills/rtl-s2-diagram/scripts/render_html.py --check doc/diagram/<m>/<m>.html [--mmd doc/diagram/<m>/<m>.mmd] [--interface <file bảng port>]
```

Script từ chối: mô hình không phải L2, có instance `u_`/`gen_`, lỗi lint; lớp chi tiết thiếu/sai cú pháp, có khối của mô hình chưa có phương trình, `<=` ngoài `reg_`/`fsm_`, tín hiệu không nguồn, output chưa gán, dây giữa hai khối không có cạnh tương ứng trong mô hình (hoặc cạnh của mô hình không có tín hiệu nào). Sửa lớp chi tiết; nếu lỗi cho thấy mô hình khối thiếu/sai thì sửa mô hình (với `both`, sửa `.mmd` rồi lint lại; với `html` khi đã có `.mmd` thì không đụng `.mmd` – dừng, báo lỗi mô hình, đề nghị `--format both`) – không sửa HTML, không thêm phần cứng để qua kiểm tra. `[CẢNH BÁO] không xác định width` → khai báo `wire [..] x;` trong lớp chi tiết.

Kết quả: một file HTML tự chứa (HTML + CSS + SVG inline + JS nhỏ, không CDN/npm/server), mở trực tiếp bằng Chrome/Edge – RTL schematic trái → phải: port ngoài khung module, DFF có D/Q/▷/RST, MUX hình thang có select, comparator, cổng logic, phép toán, hằng gắn tại chân, bus ghi width, điều khiển nét đứt, feedback vòng phía trên, clock/reset thành rail phía dưới; zoom/pan/vừa khung, rê lên phần tử để sáng khối mô hình tương ứng. Metadata máy đọc trên thẻ `<html data-module data-stage="2" data-level="L2" data-format="html">`.

## Đầu ra

```
doc/diagram/<m>/
├── <m>.mmd          # diagram chính thức (mermaid, both); header ghi level (gate S3 đọc)
├── <m>.html         # chỉ --format html|both, leaf L2: RTL schematic chi tiết để xem, S3 bỏ qua
└── <m>_notes.md     # chỉ khi cần (Bước 4)
```

Không tạo README hay file phụ khác. Chỉ có `<m>.html` (đã chạy `--format html`) thì S3 dừng vì thiếu `.mmd` – đúng thiết kế; chạy `/rtl-s2-diagram <m>` hoặc `--format both` trước S3.

## Báo cáo cuối (chỉ trong chat)

Module · level (và lý do nếu khác đề xuất) · định dạng · các thanh ghi/khối/instance chính · (HTML) số primitive theo loại mà render in ra · latency so với spec (chỉ khi spec yêu cầu) · file đã tạo/xóa · kết quả lint/parse/render/check · lệnh tiếp theo `/rtl-s3-rtl <m>` (chỉ có `.html` thì tạo `.mmd` trước).

# RTL Design Skill Set cho Claude Code

Bộ 5 skill dẫn Claude Code từ tài liệu nguồn đến **RTL chạy được, kiến trúc sạch, diagram dễ hiểu** – từ counter 3 bit đến IP nhiều cấp. Trọng tâm là thiết kế (S1–S3); kiểm thử (S4–S5) là phần nhẹ, tùy chọn.

```
S1 spec ──► S2 diagram ──► S3 RTL ══► XONG THIẾT KẾ  ┄┄►  S4 vplan ──► S5 testbench
(toàn bộ)   (từng module)  (từng module)                   (tùy chọn, từng module)
```

## 1. Thiết kế nhỏ → tài liệu nhỏ, thiết kế lớn → tài liệu chi tiết

Tài liệu co giãn theo độ phức tạp phần cứng, không theo template:

| Thiết kế | Ví dụ | File sau S1–S3 |
| --- | --- | --- |
| Module nhỏ | counter, mux, FSM, APB slave vài thanh ghi | `doc/spec/<m>_spec.md` · `doc/diagram/<m>/<m>.mmd` · `rtl/<m>.v` |
| Module trung bình | DMA channel, controller | như trên + `interface/<m>_interface.md` / `<m>_notes.md` nếu thực sự cần |
| IP nhiều module | accelerator: control, DMA, SRAM IF, regs, engine | `spec_status.md` (hierarchy) + spec từng module + `interface/`, `datapath/`, `controlpath/`, `register_file/` khi tách giúp dễ đọc |

Level diagram theo vai trò module:

| Module | S2 vẽ | S3 viết |
| --- | --- | --- |
| Có module con (IP top, subsystem) | **L0** sơ đồ khối, nối dây | instance + glue |
| Leaf lớn / cấu trúc lặp (DMA channel, mảng MAC, buffer) | **L1** vi kiến trúc | mảng bộ nhớ, generate khi kiến trúc lặp |
| Leaf nhỏ (counter, FSM, FIFO nhỏ, APB slave) | **L2** phác thảo hướng RTL: thanh ghi + logic chính | viết trực tiếp |

Diagram là mô hình kiến trúc, không phải sơ đồ cổng; RTL giữ đúng kiến trúc và hành vi nhưng không cần ánh xạ 1:1 từng node.

## 2. Nội dung gói

```text
.
├── CLAUDE.md                     # quy tắc project, Claude Code tự nạp
├── README.md
├── .claude/skills/
│   ├── rtl-s1-spec/              # S1: input → spec (đơn hoặc phân cấp)
│   │   ├── references/process.md, input_criteria.md
│   │   └── scripts/check_preconditions.py, check_interface.py
│   ├── rtl-s2-diagram/           # S2: diagram Mermaid L0/L1/L2 (+ HTML RTL schematic tùy chọn cho leaf L2)
│   │   ├── references/diagram_conventions.md, example_l0/l1/l2_*.mmd
│   │   └── scripts/check_preconditions.py, lint_mermaid.py, render_html.py, mermaid_parse.mjs, package.json
│   ├── rtl-s3-rtl/               # S3: RTL
│   │   ├── coding_rules/         # (tùy chọn) coding rule RTL của bạn
│   │   ├── references/default_rtl_rules.md
│   │   └── scripts/check_preconditions.py, check_ports.py
│   ├── rtl-s4-vplan/             # S4 (tùy chọn): vplan direct test
│   │   ├── vplan_template/       # (tùy chọn) template vplan của bạn
│   │   ├── references/test_selection.md
│   │   └── scripts/check_preconditions.py
│   └── rtl-s5-tb/                # S5 (tùy chọn): testbench self-checking
│       ├── tb_coding_rules/      # (tùy chọn) rule testbench của bạn
│       ├── references/default_tb_rules.md
│       └── scripts/check_preconditions.py, check_sim_log.py
├── doc/{spec/source, diagram, vplan}/     # thư mục con khác của doc/spec/ do S1 tạo khi cần
└── rtl/  sim/  tb/
```

`.claude` là thư mục ẩn – bật "hiện file ẩn" nếu không thấy.

## 3. Cài đặt

1. Giải nén vào thư mục gốc project. Đã có `CLAUDE.md` riêng thì gộp nội dung.
2. Đặt tài liệu nguồn (requirements, kiến trúc thô, giải thuật, công thức – định dạng nào cũng được) vào `doc/spec/source/`.
3. (Tùy chọn) đặt coding rule / template của bạn vào `coding_rules/`, `vplan_template/`, `tb_coding_rules/`. Để trống thì skill dùng rule mặc định.
4. (Tùy chọn) để S2 parse Mermaid bằng đúng thư viện của mermaid.live: `npm install --prefix .claude/skills/rtl-s2-diagram/scripts`.

Công cụ: Python 3 (bắt buộc), Node.js, `iverilog` và/hoặc `verilator` (miễn phí, đủ cho cả flow).

## 4. Sử dụng

| Lệnh | Việc |
| --- | --- |
| `/rtl-s1-spec` | Đọc `doc/spec/source/`. Input chưa đủ → báo lỗi + đề xuất sửa trong chat, không ghi file. Đủ → spec tối thiểu (module nhỏ: một file) + trạng thái PASS/FAIL. |
| `/rtl-s1-spec --recheck` | Chỉ đánh giá input. |
| `/rtl-s2-diagram <m> [--level Lx] [--format mermaid\|html\|both]` | Diagram kiến trúc của module, mặc định một file `<m>.mmd` (mở trên https://mermaid.live). `--format html\|both` chỉ cho **một** module leaf L2: thêm/chỉ `<m>.html` – RTL schematic chi tiết (DFF, MUX, comparator, cổng, phép toán, hằng, feedback, clock/reset), SVG tự chứa, mở thẳng bằng Chrome/Edge. `.mmd` vẫn là diagram chính thức cho S3. |
| `/rtl-s3-rtl <m>` | RTL Verilog-2005 (`rtl/<m>.v`) theo spec + diagram, compile/lint sạch. |
| `/rtl-s4-vplan <m>` | (tùy chọn) Vplan direct test tối thiểu. |
| `/rtl-s5-tb <m>` | (tùy chọn) Testbench self-checking Verilog-2005 (`tb/<m>/tb_<m>.v`: 9 phần cố định, golden model + checker + bộ đếm PASS/FAIL, clock 20 ns, stimulus tại `posedge` + `#1`) + script chạy, mô phỏng nếu có simulator. |

Thiết kế nhiều cấp: S2→S3 cho các leaf trước, rồi block, cuối cùng top. Có thể nêu nhiều module trong một lệnh; không có lệnh "all" – chủ ý để bạn duyệt từng module.

## 5. Tài liệu được tạo

Chỉ tài liệu thiết kế; đánh giá input, kết quả kiểm tra và báo cáo nằm trong chat.

```text
Luôn có (mỗi module)
  doc/spec/<m>_spec.md                    chế độ đơn – chức năng, port, thanh ghi, hành vi, reset
    hoặc doc/spec/architecture/<m>_spec.md   chế độ phân cấp
  doc/diagram/<m>/<m>.mmd
  rtl/<m>.v                               Verilog-2005

Chỉ khi cần
  doc/spec/spec_status.md                 IP nhiều module: hierarchy + trạng thái + OPEN
  doc/spec/interface/<m>_interface.md, 00_parameters.md
  doc/spec/register_file/register_map.md
  doc/spec/datapath/…, controlpath/…
  doc/diagram/<m>/<m>_notes.md, <m>_<phần>.mmd
  doc/diagram/<m>/<m>.html                RTL schematic xem tùy chọn (leaf L2, --format html|both); S3 bỏ qua

Tùy chọn (S4–S5)
  doc/vplan/<m>_vplan.*
  tb/<m>/tb_<m>.v, sim/<m>/<m>.f, run.sh
```

## 6. Gate của từng stage

| Stage | Cần có trước |
| --- | --- |
| S1 | ≥ 1 file trong `doc/spec/source/`; input không có BLOCKER (`input_criteria.md`) |
| S2 | Spec PASS (dòng `Status` trong spec, hoặc `spec_status.md` nếu phân cấp) · spec + bảng port của module (và bảng port module con) |
| S3 | Điều kiện S2 · `doc/diagram/<m>/*.mmd` (chỉ Mermaid; chỉ có `<m>.html` thì vẫn dừng) |
| S4 | Spec PASS · spec + bảng port · `rtl/<m>.v` (gate vẫn nhận `.sv` cũ) |
| S5 | Điều kiện S4 · RTL của mọi module con · `doc/vplan/<m>_vplan.*` |

Chạy thử gate: `python3 .claude/skills/rtl-s3-rtl/scripts/check_preconditions.py --stage 3 --module <m>`

## 7. Script kiểm tra

Script phục vụ workflow – không bao giờ cần tạo file giả để qua gate.

| Script | Việc |
| --- | --- |
| `check_preconditions.py` | Gate từng stage; tự nhận chế độ đơn/phân cấp; in file spec, bảng port, level, module con |
| `check_interface.py` | Bảng port: hướng, width, hậu tố; ở chế độ phân cấp thêm port treo, sai hướng cha–con/anh em, lệch width, input nhiều nguồn |
| `lint_mermaid.py` | Cú pháp an toàn, đủ port (hỗ trợ gom bus `prefix_*`), width trên thanh ghi/port, cảnh báo diagram quá chi tiết; `--parse` parse bằng Mermaid thật |
| `render_html.py` | Render HTML RTL schematic (inline SVG, không phụ thuộc ngoài) từ mô hình khối `.mmd` + lớp chi tiết RTL (phương trình từng khối, qua stdin) – chỉ leaf L2; kiểm lớp chi tiết khớp mô hình (không thêm thanh ghi, cùng kết nối); `--check` kiểm metadata và cùng mô hình với `.mmd` |
| `check_ports.py` | Port list RTL so với bảng port (tính width từ parameter, kể cả `$clog2`) |
| `check_sim_log.py` | Log S5 (`-- <item name> test --`, `[<time>] <case> PASS\|FAIL \| expected: … \| actual: …`, `[SUMMARY]`): map tên item về ID vplan; mọi item vplan có case và đều PASS, `[SUMMARY]` khớp số dòng PASS/FAIL, không TIMEOUT |

## 8. Lưu ý

- Viết cho **Claude Code** (project skills). `disable-model-invocation: true` để stage chỉ chạy khi bạn gõ lệnh.
- Tải lên claude.ai (Settings → Skills): xóa hai dòng `argument-hint` và `disable-model-invocation` trong mỗi `SKILL.md`.
- Project cũ vẫn chạy: `architecture/` + `interface/` + `spec_status.md` là chế độ phân cấp; `<m>_notes.md` / `<m>_ff_notes.md` cũ vẫn được đọc nếu có, nhưng không còn bắt buộc.

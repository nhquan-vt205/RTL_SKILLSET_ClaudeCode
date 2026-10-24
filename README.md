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
| Module nhỏ | counter, mux, FSM, APB slave vài thanh ghi | `doc/spec/<m>_spec.md` · `doc/diagram/<m>/<m>.svg` · `rtl/<m>.v` |
| Module trung bình | DMA channel, controller | như trên + `interface/<m>_interface.md` / `<m>_notes.md` nếu thực sự cần |
| IP nhiều module | accelerator: control, DMA, SRAM IF, regs, engine | `spec_status.md` (hierarchy) + spec từng module + `interface/`, `datapath/`, `controlpath/`, `register_file/` khi tách giúp dễ đọc |

Level diagram theo vai trò module:

| Module | S2 vẽ | S3 viết |
| --- | --- | --- |
| Có module con (IP top, subsystem) | **L0** mỗi module con một khối đủ port + glue logic tới từng gate | instance + glue |
| Leaf lớn / cấu trúc lặp (DMA channel, mảng MAC, buffer) | **L1** tới từng gate, trừ phần bạn duyệt gom thành cloud/khối | mảng bộ nhớ, generate khi kiến trúc lặp |
| Leaf nhỏ (counter, FSM, FIFO nhỏ, APB slave) | **L2** toàn bộ tới từng gate | viết trực tiếp |

Diagram là sơ đồ logic SVG đen trắng (MUX, register/FF, gate, ellipse operator, cloud, bus bundle, khối submodule, bộ nhớ) theo thư viện ký hiệu của S2; với L1/L0, S2 đề xuất phần nào gom thành cloud/khối và chờ bạn duyệt. RTL giữ đúng phần cứng và hành vi nhưng không cần ánh xạ 1:1 từng ký hiệu.

## 2. Nội dung gói

```text
.
├── CLAUDE.md                     # quy tắc project, Claude Code tự nạp
├── README.md
├── .claude/skills/
│   ├── rtl-s1-spec/              # S1: input → spec (đơn hoặc phân cấp)
│   │   ├── references/process.md, input_criteria.md
│   │   └── scripts/check_preconditions.py, check_interface.py
│   ├── rtl-s2-diagram/           # S2: sơ đồ logic SVG L0/L1/L2 (+ góc nhìn scope --from/--to)
│   │   ├── references/diagram_conventions.md, symbol_library.svg, example_l0/l1/l2_*.svg
│   │   └── scripts/check_preconditions.py, lint_svg.py
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
│       ├── references/sim_env/   # mẫu sim/: Makefile, compile.f, rtl.f, tb.f, pat.list, run.csh, report.csh, schematic.tcl
│       └── scripts/check_preconditions.py, check_sim_log.py
├── memory_bank/session_template.md   # mẫu session summary để khôi phục ngữ cảnh (protocol trong ~/.claude/CLAUDE.md)
├── init_project                  # tạo project mới từ khung này (mục 3)
├── doc/{spec/source, diagram, vplan}/     # thư mục con khác của doc/spec/ do S1 tạo khi cần
└── rtl/  sim/  tb/
```

`.claude` là thư mục ẩn – bật "hiện file ẩn" nếu không thấy.

## 3. Cài đặt

1. Tạo project mới bằng `init_project` (cài một lần: `ln -s <đường dẫn repo>/init_project ~/.local/bin/init_project`):
   ```bash
   mkdir My_IP && cd My_IP && init_project      # tên project = tên thư mục; --no-git, --force, -h
   ```
   Script chép bản **đã commit** của repo này, tạo `rtl/ tb/ tc/ sim/ sim/script/ doc/{spec/source,diagram,vplan,database/input,database/output}/`, chép môi trường mô phỏng từ `rtl-s5-tb/references/sim_env/` vào `sim/` (`sim/rtl.f`, `sim/pat.list` do S1–S5 điền), chép `memory_bank/session_template.md`, tạo `README.md` và commit đầu. Project có sẵn: chép thư mục `.claude/` và gộp `CLAUDE.md`.
2. Đặt tài liệu nguồn (requirements, kiến trúc thô, giải thuật, công thức – định dạng nào cũng được) vào `doc/spec/source/`.
3. (Tùy chọn) đặt coding rule / template của bạn vào `coding_rules/`, `vplan_template/`, `tb_coding_rules/`. Để trống thì skill dùng rule mặc định.

Công cụ: Python 3 (bắt buộc). Compile check RTL ở S3 (`make -C sim lint`) và mô phỏng S5 đều chạy qua `sim/Makefile`, cần QuestaSim; `make schematic` cần Vivado; `run.csh`/`report.csh` cần `tcsh`.

## 4. Sử dụng

| Lệnh | Việc |
| --- | --- |
| `/rtl-s1-spec` | Đọc `doc/spec/source/`. Input chưa đủ → báo lỗi + đề xuất sửa trong chat, không ghi file. Đủ → spec tối thiểu (module nhỏ: một file) + trạng thái PASS/FAIL; PASS → ghi mọi module ở dạng comment vào `sim/rtl.f`, `sim/pat.list` (nhóm theo nhánh git). |
| `/rtl-s1-spec --recheck` | Chỉ đánh giá input. |
| `/rtl-s2-diagram <m> [--level Lx] [--cloud …] [--block …]` | Sơ đồ logic của module: một file `<m>.svg` đen trắng (mở bằng Chrome/Edge, chèn được vào Word/PPT), nhúng model phương trình cho S3. L1/L0: đề xuất phần gom thành cloud/khối và chờ bạn duyệt (`--cloud`/`--block` để chỉ định sẵn). |
| `/rtl-s2-diagram <m> --from a,b --to x,y [--part p]` | Thêm góc nhìn `<m>_<part>.svg` chỉ chứa logic từ tín hiệu `a,b` tới `x,y` (S3 không đọc). |
| `/rtl-s3-rtl <m>` | RTL Verilog-2005 (`rtl/<m>.v`) theo spec + diagram, bỏ comment dòng của nó trong `sim/rtl.f`, compile/lint sạch qua `make -C sim lint TOP=<m>`. |
| `/rtl-s4-vplan <m>` | (tùy chọn) Vplan direct test tối thiểu. |
| `/rtl-s5-tb <m>` | (tùy chọn) Testbench self-checking Verilog-2005 (`tb/tb_<m>.v`: 9 phần cố định, golden model + checker + bộ đếm PASS/FAIL, clock 20 ns, stimulus tại `posedge` + `#1`; mỗi item vplan một file `tc/<ID>.v`) + cập nhật `sim/rtl.f`, `sim/pat.list`, mô phỏng bằng QuestaSim (`make -C sim all TESTNAME=<ID>`) nếu có. |

Thiết kế nhiều cấp: S2→S3 cho các leaf trước, rồi block, cuối cùng top. Có thể nêu nhiều module trong một lệnh; không có lệnh "all" – chủ ý để bạn duyệt từng module.

Nhánh git: `main` dừng ở S1. Từ S2, mỗi module con trực tiếp của top có chức năng riêng làm trên nhánh `feat/<m>` (module con của nó và module chỉ để làm instance đi cùng nhánh; top đi `feat/<top>` sau khi các nhánh con đã merge); skill tự chuyển nhánh, commit đầu ra của stage và `git push -u origin feat/<m>`, bạn tự mở PR/merge vào `main`. Nhánh của từng module ghi ở cột `Branch` của `spec_status.md`.

## 5. Tài liệu được tạo

Chỉ tài liệu thiết kế; đánh giá input, kết quả kiểm tra và báo cáo nằm trong chat.

```text
Luôn có (mỗi module)
  doc/spec/<m>_spec.md                    chế độ đơn – chức năng, port, thanh ghi, hành vi, reset
    hoặc doc/spec/architecture/<m>_spec.md   chế độ phân cấp
  doc/diagram/<m>/<m>.svg
  rtl/<m>.v                               Verilog-2005 (+ dòng ../rtl/<m>.v trong sim/rtl.f)

Chỉ khi cần
  doc/spec/spec_status.md                 IP nhiều module: hierarchy + trạng thái + OPEN
  doc/spec/interface/<m>_interface.md, 00_parameters.md
  doc/spec/register_file/register_map.md
  doc/spec/datapath/…, controlpath/…
  doc/diagram/<m>/<m>_notes.md
  doc/diagram/<m>/<m>_<part>.svg          góc nhìn scope (--from/--to); S3 bỏ qua

Tùy chọn (S4–S5)
  doc/vplan/<m>_vplan.*
  tb/tb_<m>.v, tc/<ID>.v, sim/rtl.f, sim/pat.list
```

## 6. Gate của từng stage

| Stage | Cần có trước |
| --- | --- |
| S1 | ≥ 1 file trong `doc/spec/source/`; input không có BLOCKER (`input_criteria.md`) |
| S2 | Spec PASS (dòng `Status` trong spec, hoặc `spec_status.md` nếu phân cấp) · spec + bảng port của module (và bảng port module con) |
| S3 | Điều kiện S2 · `doc/diagram/<m>/<m>.svg` (`.mmd`/`.html` cũ không còn được nhận – chạy lại S2) |
| S4 | Spec PASS · spec + bảng port · `rtl/<m>.v` (gate vẫn nhận `.sv` cũ) |
| S5 | Điều kiện S4 · RTL của mọi module con · `doc/vplan/<m>_vplan.*` |

Chạy thử gate: `python3 .claude/skills/rtl-s3-rtl/scripts/check_preconditions.py --stage 3 --module <m>`

## 7. Script kiểm tra

Script phục vụ workflow – không bao giờ cần tạo file giả để qua gate.

| Script | Việc |
| --- | --- |
| `check_preconditions.py` | Gate từng stage; tự nhận chế độ đơn/phân cấp; in file spec, bảng port, level, module con |
| `check_interface.py` | Bảng port: hướng, width, hậu tố; ở chế độ phân cấp thêm port treo, sai hướng cha–con/anh em, lệch width, input nhiều nguồn |
| `lint_svg.py` | Diagram SVG: XML, header/level, chỉ đen trắng, không phần tử cấm, chữ tiếng Anh, tiền tố id, model khớp nhóm, luật theo level, tên port không nằm trong khối, đủ port (hỗ trợ gom bus `prefix_*`); không kiểm bố cục |
| `check_ports.py` | Port list RTL so với bảng port (tính width từ parameter, kể cả `$clog2`) |
| `check_sim_log.py` | Log S5, một hay nhiều file `sim/log/<ID>.log` (`-- <item name> test --`, `[<time>] <case> PASS\|FAIL \| expected: … \| actual: …`, `[SUMMARY]`, `Test_result`): map tên item về ID vplan; mọi item vplan có case và đều PASS, `[SUMMARY]`/`Test_result` khớp từng log, không TIMEOUT |

## 8. Lưu ý

- Viết cho **Claude Code** (project skills). `disable-model-invocation: true` để stage chỉ chạy khi bạn gõ lệnh.
- Tải lên claude.ai (Settings → Skills): xóa hai dòng `argument-hint` và `disable-model-invocation` trong mỗi `SKILL.md`.
- Project cũ vẫn chạy: `architecture/` + `interface/` + `spec_status.md` là chế độ phân cấp; `<m>_notes.md` / `<m>_ff_notes.md` cũ vẫn được đọc nếu có, nhưng không còn bắt buộc.

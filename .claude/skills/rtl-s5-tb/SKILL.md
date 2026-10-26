---
name: rtl-s5-tb
description: Stage 5 của RTL flow (tùy chọn, nhẹ) – viết testbench self-checking Verilog-2005 (tb/tb_<m>.v + mỗi item vplan một file tc/<ID>.v) hiện thực đúng các direct test trong vplan của MỘT module (leaf hoặc cả cây con ở mức tích hợp) theo cấu trúc 9 phần cố định (golden model, checker, bộ đếm PASS/FAIL, log chuẩn), clock mặc định 20 ns, lái stimulus tại posedge + #1, cập nhật môi trường mô phỏng dùng chung sim/ (Makefile QuestaSim, rtl.f, pat.list), mô phỏng bằng QuestaSim nếu có. Theo rule testbench của người dùng trong tb_coding_rules/ nếu có. Dùng khi người dùng gọi /rtl-s5-tb <module> hoặc yêu cầu viết testbench theo vplan.
argument-hint: "<tên_module> [tên_module ...]"
disable-model-invocation: true
---

# Stage 5 – Testbench theo vplan

Module: `$ARGUMENTS`

Stage này **tùy chọn**, chỉ chạy khi người dùng cần mô phỏng.

Testbench tự kiểm: stimulus → DUT → golden reference model → checker → bộ đếm PASS/FAIL → log chuẩn → `[SUMMARY]` + `Test_result`. Không chỉ `$display` để xem waveform bằng mắt. Không UVM, class, interface, package, random, SVA/assertion, framework scoreboard. (Target coverage có sẵn trong `sim/Makefile` là của người dùng; S5 không viết gì cho coverage.)

## Cấu trúc thư mục (phẳng, không lớp `<m>/`)

```
rtl/        <m>.v ...                 # chỉ mã HDL (S3)
tb/         tb_<m>.v                  # chỉ mã HDL: hạ tầng TB dùng chung cho mọi test của <m>
tc/         <ID>.v                    # chỉ mã HDL: chuỗi test của một item vplan
sim/        Makefile compile.f rtl.f tb.f pat.list run.csh report.csh schematic.tcl cov_excl.tcl
            exclude.do                # exclusion coverage của người dùng (make cov_gui) – S5 không sửa
            script/                   # script sinh dữ liệu test (nếu có), vd. <m>_gen_vectors.py
            log/<ID>.log              # log từng test – sinh ra, bị .gitignore
doc/database/input/   <m>_*.txt       # dữ liệu đưa vào DUT (TB đọc file)
doc/database/output/  <m>_*.txt       # dữ liệu tham chiếu để so kết quả
```

`rtl/`, `tb/`, `tc/` chỉ chứa mã HDL – không dữ liệu, script, log. Mọi thứ Makefile/simulator sinh ra trong `sim/` (`work/`, `log/`, `*.wlf`, `*.ucdb`, `coverage/`, `run_test.v`…) không phải đầu ra cần giữ.

## Phạm vi

- Chỉ đúng module(s) được nêu tên; không nhận "all".
- Hiện thực **đúng và đủ** các test trong `doc/vplan/<m>_vplan.*`; test cần thêm → đề xuất trong báo cáo để cập nhật vplan.
- Không sửa RTL, spec, diagram, vplan. Đầu ra chỉ: `tb/tb_<m>.v`, `tc/<ID>.v` của module, `sim/` (mục Bước 3), `sim/script/<m>_*` và `doc/database/{input,output}/<m>_*` khi TB dùng file dữ liệu.

## Bước 0 – Gate

```bash
python3 .claude/skills/rtl-s5-tb/scripts/check_preconditions.py --stage 5 --module <m>
```

Cần spec PASS, bảng port, RTL của module **và mọi module con** (để mô phỏng được), vplan. Mã thoát ≠ 0 → bỏ qua module đó, báo `[THIẾU]`. Test trong vplan còn `TBD` ở stimulus/mong đợi → bỏ qua test đó, liệt kê trong báo cáo.

**Nhánh git** (mục "Nhánh git" của `CLAUDE.md`): sau gate, so nhánh hiện tại với nhánh `<b>` của `<m>` (cột `Branch` của `spec_status.md`; chế độ đơn `<m>`). Khác nhau → báo nhánh đúng và lệnh (`git checkout <b>`, hoặc `git checkout -b <b> main` nếu chưa có), chỉ chuyển khi người dùng đồng ý; không chạy S5 của module con trên `main`. Commit/push đầu ra chỉ khi người dùng yêu cầu; báo cáo cuối gợi ý lệnh commit và `git push -u origin <b>`.

## Bước 1 – Rule

Đọc `tb_coding_rules/` (trừ README.md) nếu có; chỗ không nói tới hoặc thư mục trống → `references/default_tb_rules.md`.

## Bước 2 – Viết testbench và testcase

Đọc vplan, RTL (port, parameter), spec (handshake, reset, chu kỳ clock, latency). Chi tiết và khung mẫu: `references/default_tb_rules.md`. Luật bắt buộc:

- **Ngôn ngữ:** Verilog-2005 (IEEE 1364-2005): `tb/tb_<m>.v` (module `tb_<m>`) và `tc/<ID>.v`. Không construct SystemVerilog nào (`logic`, `bit`, `string`, `always_ff`, `typedef`, `enum`, `struct`, `interface`, `package`, `class`, `foreach`, queue, `$fatal`, SVA…). Comment, tên task và log chỉ dùng tiếng Anh.
- **TB: cấu trúc 9 phần, đúng thứ tự**, mỗi phần có header comment, giữ đủ header kể cả khi TB nhỏ (phần không cần thì để trống, không viết code giả): `1. Declaration` → `2. DUT Instance` → `3. Clock Generation` → `4. Init Reset` → `5. Golden Reference Model` → `6. Checker` → `7. Helper Functions` → `8. Tasks` → `9. Main Program Body`.
- **Phần 8** chứa task lái giao thức/driver dùng chung và hai task bắt buộc: `init_test` (gán 0 `pass_count`/`fail_count`, đọc plusarg như `+IN`/`+OUT`) và `end_test` (in `[SUMMARY]`, in `Test_result: PASSED` khi FAIL = 0 và PASS > 0, ngược lại `Test_result: FAILED`, rồi `$finish`).
- **Phần 9** chỉ gồm `` `include "run_test.v" `` (testcase được `make build` chép vào `sim/run_test.v`) và `initial` timeout toàn cục (in `[TIMEOUT]`, tăng `fail_count`, gọi `end_test`).
- **Mỗi item vplan → một file `tc/<ID>.v`**, tên file đúng ID vplan dạng `TC_<M>_<NNN>` (Makefile suy ra module từ tên này). File có header comment chép ID, tên, mục tiêu từ vplan, và đúng một khối `initial begin init_test; reset_dut; $display("-- <item name> test --"); <stimulus + check>; end_test; end`, thụt 2 khoảng trắng (được include bên trong module TB). Không chọn test bằng `+TEST`; test được chọn bằng `make TESTNAME=<ID>`.
- **Clock:** `` `timescale 1ns/1ps ``, `parameter CLK_PERIOD = 20;` (20 ns mặc định; spec quy định chu kỳ khác thì theo spec), `clk = 1'b0` trong `initial` + `always #(CLK_PERIOD / 2) clk = ~clk;`.
- **Stimulus:** mọi lần lái input DUT là `@(posedge clk); #1;` rồi gán. Không lái ở negedge, không lái đúng tại posedge. `#1` chỉ có trong TB, không bao giờ trong RTL.
- **Reset:** theo spec – reset async tích cực ngay, nhả tại `posedge + #1`; reset đồng bộ lái như stimulus. `reset_dut` (phần 4) khởi tạo mọi input DUT và golden model; mỗi testcase gọi sau `init_test`.
- **Self-check:** golden model tính expected độc lập từ spec/vplan (không bao giờ lấy từ output DUT); checker so sánh, tăng `pass_count`/`fail_count` (`integer`), PASS + FAIL = số lần checker so sánh.
- **Log chuẩn** (`check_sim_log.py` và `sim/report.csh` đọc): đầu item `-- <item name> test --` với `<item name>` là tên tiếng Anh ngắn, đọc được, phân biệt được của item lấy từ vplan (không thay bằng ID, không dịch; danh sách đúng: `check_sim_log.py --items <vplan>`); mỗi case `[<time>] <case> PASS | expected: <exp> | actual: <act>` hoặc `... FAIL | ...`, `<time>` = `$time`, `<case>` ngắn mô tả đặc điểm input quan trọng (`addr_0_wdata_A5A5A5A5`, `valid_1_ready_0` – không `CASE_001`), expected = golden model, actual = DUT; cuối cùng `[SUMMARY] PASS=<n> FAIL=<n>` rồi `Test_result: PASSED|FAILED`. Chi tiết ở mục 6 của `default_tb_rules.md`.
- **Dữ liệu từ file** (chỉ khi vplan/spec dùng vector ngoài): input ở `doc/database/input/<m>_<tên>.txt`, tham chiếu ở `doc/database/output/<m>_<tên>.txt`; TB đọc qua `+IN=`/`+OUT=`, mặc định là đường dẫn tương đối từ `sim/` (`../doc/database/input/...`). Script sinh dữ liệu đặt ở `sim/script/<m>_gen_vectors.py` (`make gen_data`).
- DUT có module con (phạm vi tích hợp): instance module cha, stimulus qua port của nó, kiểm output/status cuối.

## Bước 3 – Môi trường `sim/` và chạy

`sim/` dùng chung cho mọi module; mẫu ở `references/sim_env/` (`init_project` đã chép sẵn khi tạo project). Trước khi chạy, đọc `sim/Makefile`, `compile.f`, `tb.f`, `rtl.f`, `pat.list` để dùng đúng target và biến của bản đang có; mọi lần biên dịch/mô phỏng đều đi qua `sim/Makefile`, không tự gõ lệnh simulator.


- `Makefile`, `compile.f`, `tb.f`, `run.csh`, `report.csh`, `schematic.tcl`, `cov_excl.tcl` chưa có → chép từ `references/sim_env/`. Đã có → **không ghi đè** (có thể là bản người dùng đã chỉnh); khác mẫu thì nêu trong báo cáo.
- `rtl.f`, `pat.list` chưa có → chép mẫu (chỉ có dòng comment `//`) rồi thêm như dưới.
- `rtl.f`: mọi file trong `rtl/`, module con trước module cha, đường dẫn `../rtl/<file>.v`, mỗi dòng một file (S1 ghi sẵn ở dạng comment, S3 bỏ comment khi viết RTL). Dòng của cây `<m>` còn comment → bỏ comment; chưa có → thêm. Không sửa dòng của module khác.
- `pat.list`: ID các testcase của `<m>` (mỗi dòng một ID, không comment, theo thứ tự vplan), thêm vào cuối nhóm `// --- <b> ---` của `<m>` (S1 ghi sẵn dòng mở đầu nhóm; không sửa dòng mở đầu và dòng trống giữa các nhóm); giữ dòng của module khác; dòng chứa `//` là comment (cũng bỏ qua trong `rtl.f`).

Makefile suy ra `MODULE` từ `TESTNAME` (`TC_<M>_<NNN>` → `<m>` chữ thường), `TB_NAME = tb_<m>`; `tb.f` dùng `${TB_NAME}`. Chạy nếu có QuestaSim (`vsim` trong PATH), từng testcase một (không cần `csh`):

```bash
for t in <ID_1> <ID_2> ...; do make -C sim all TESTNAME=$t; done
python3 .claude/skills/rtl-s5-tb/scripts/check_sim_log.py sim/log/<ID_1>.log sim/log/<ID_2>.log ... doc/vplan/<m>_vplan.<ext>
```

`check_sim_log.py` nhận một hay nhiều log, bỏ tiền tố `# ` của transcript Questa, map header `-- <item name> test --` về ID vplan theo tên item, rồi kiểm: item vplan chưa chạy/không có case, case FAIL, dòng case sai định dạng, case trước mọi header, header không có trong vplan/trùng giữa các log, `[SUMMARY]` thiếu/trùng/lệch số dòng PASS/FAIL và `Test_result` thiếu/sai trong từng log, `[TIMEOUT]`/fatal. Vplan dùng ID khác `TC_…` mà không phải bảng có cột `ID` → thêm `--id-re '<regex>'`.

`make` dừng ở `build`/`run` (lỗi biên dịch hoặc dựng thiết kế) → đọc khối `ERRORS` cuối output hoặc `sim/log/<ID>.log` (đủ file, dòng của từng lỗi); lỗi trong `tb/`, `tc/` → sửa, lỗi trong `rtl/` → phân loại như dưới.

Test FAIL → phân loại:
- Lỗi testbench (stimulus/chu kỳ kiểm sai so với vplan, golden model sai so với spec) → sửa TB/testcase, chạy lại.
- Lỗi RTL hoặc vplan → **không sửa**; báo test ID, triệu chứng, nghi ngờ ở file/dòng nào, cần sửa ở S3 hay S4.

Không có QuestaSim → không phải lỗi thiết kế; không thay bằng simulator khác ngoài `sim/`; ghi "chưa chạy mô phỏng" và lệnh chạy.

## Đầu ra

```
tb/tb_<m>.v                          # Verilog-2005, hạ tầng TB
tc/<ID>.v                            # một file mỗi item vplan
sim/rtl.f, sim/pat.list              # cập nhật cho <m>
sim/Makefile, compile.f, tb.f, run.csh, report.csh, schematic.tcl, cov_excl.tcl   # chỉ khi chưa có (chép mẫu)
sim/script/<m>_gen_vectors.py, doc/database/{input,output}/<m>_*.txt # chỉ khi TB dùng file dữ liệu
sim/log/<ID>.log                     # nếu đã chạy – sinh ra, bị .gitignore
```

File theo cấu trúc cũ (`tb/<m>/tb_<m>.v|.sv`, `sim/<m>/…`, `testcases/<ID>.v`) → **không tự xóa**, không đưa vào filelist; nêu trong báo cáo là file legacy để người dùng quyết định.

## Báo cáo cuối (chỉ trong chat)

File · ngôn ngữ TB (Verilog-2005) · file legacy còn lại (nếu có) · file `sim/` dùng chung khác mẫu (nếu có) · số item hiện thực / tổng vplan · kết quả theo ID (số case PASS/FAIL, `[SUMMARY]`, `Test_result`) · test bỏ qua vì TBD · lỗi nghi ở RTL/vplan kèm đề xuất · lệnh chạy lại (`make -C sim all TESTNAME=<ID>`, `cd sim && ./run.csh && ./report.csh`).

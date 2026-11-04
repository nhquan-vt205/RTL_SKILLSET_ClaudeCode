---
name: rtl-s5-tb
description: Stage 5 của RTL flow (tùy chọn, nhẹ) – viết testbench self-checking Verilog-2005 cho MỘT module (leaf hoặc cả cây con ở mức tích hợp) gồm TB top tb/tb_<m>.v (cấu trúc 9 phần) và các component tb/tb_<m>_<role>.v nối bằng port thật (clock/reset generator, driver, monitor, golden model, checker, logger), mỗi Item cấp cao nhất của vplan một file tc/<ID>.v chạy mọi Sub item 1/Sub item 2 của Item, log phân cấp [ITEM]/[SUBITEM1]/[SUBITEM2] + dòng check căn cột + [SUMMARY]/Test_result, clock mặc định 20 ns, stimulus tại posedge + #1, cập nhật môi trường mô phỏng dùng chung sim/ (Makefile QuestaSim, rtl.f, tb.f, pat.list), mô phỏng bằng QuestaSim nếu có. Theo rule testbench của người dùng trong tb_coding_rules/ nếu có. Dùng khi người dùng gọi /rtl-s5-tb <module> hoặc yêu cầu viết testbench theo vplan.
argument-hint: "<tên_module> [tên_module ...]"
disable-model-invocation: true
---

# Stage 5 – Testbench theo vplan

Module: `$ARGUMENTS`

Stage này **tùy chọn**, chỉ chạy khi người dùng cần mô phỏng.

Testbench tự kiểm, gồm các component có kết nối thật: sequence (tc) → driver → DUT → monitor → golden reference model + checker → logger (bộ đếm PASS/FAIL) → log phân cấp → `[SUMMARY]` + `Test_result`. Không chỉ `$display` để xem waveform bằng mắt. Không UVM, class, SystemVerilog interface/package, random, SVA/assertion, framework scoreboard. (Target coverage có sẵn trong `sim/Makefile` là của người dùng; S5 không viết gì cho coverage.)

## Cấu trúc thư mục (phẳng, không lớp `<m>/`)

```
rtl/        <m>.v ...                 # chỉ mã HDL (S3)
tb/         tb_<m>.v                  # chỉ mã HDL: TB top (9 phần) – nối DUT với component
            tb_<m>_<role>.v           # chỉ mã HDL: component (clk_rst, drv, mon, model, chk, log …)
tc/         <ID>.v                    # chỉ mã HDL: kịch bản của một Item cấp cao nhất của vplan
sim/        Makefile compile.f rtl.f tb.f pat.list run.csh report.csh schematic.tcl cov_excl.tcl
            exclude.do                # exclusion coverage của người dùng (make cov_gui) – S5 không sửa
            script/                   # script sinh dữ liệu test (nếu có), vd. <m>_gen_vectors.py
            log/<ID>.log              # log từng Item – sinh ra, bị .gitignore
doc/database/input/   <m>_*.txt       # dữ liệu đưa vào DUT (TB đọc file)
doc/database/output/  <m>_*.txt       # dữ liệu tham chiếu để so kết quả
```

`rtl/`, `tb/`, `tc/` chỉ chứa mã HDL – không dữ liệu, script, log. Mọi thứ Makefile/simulator sinh ra trong `sim/` (`work/`, `log/`, `*.wlf`, `*.ucdb`, `coverage/`, `run_test.v`…) không phải đầu ra cần giữ.

## Phạm vi

- Chỉ đúng module(s) được nêu tên; không nhận "all".
- Hiện thực **đúng và đủ** mọi nhánh lá của mọi Item trong `doc/vplan/<m>_vplan.*`; test cần thêm → đề xuất trong báo cáo để cập nhật vplan.
- Không sửa RTL, spec, diagram, vplan. Đầu ra chỉ: `tb/tb_<m>.v`, `tb/tb_<m>_*.v`, `tc/<ID>.v` của module, `sim/` (mục Bước 3), `sim/script/<m>_*` và `doc/database/{input,output}/<m>_*` khi TB dùng file dữ liệu.

## Bước 0 – Gate

```bash
python3 .claude/skills/rtl-s5-tb/scripts/check_preconditions.py --stage 5 --module <m>
python3 .claude/skills/rtl-s5-tb/scripts/check_sim_log.py --items doc/vplan/<m>_vplan.<ext>
```

Gate cần spec PASS, bảng port, RTL của module **và mọi module con** (để mô phỏng được), vplan. Mã thoát ≠ 0 → bỏ qua module đó, báo `[THIẾU]`. `--items` đọc bảng checklist (ô gộp) và in cây Item → Sub item 1 → Sub item 2 cùng các header log mong đợi; mã thoát ≠ 0 (bảng sai cấu trúc, hoặc vplan định dạng cũ – bảng pipe phẳng) → dừng, báo lỗi của từng hàng và đề xuất chạy lại `/rtl-s4-vplan <m>`. Nhánh lá còn `TBD` ở stimulus/mong đợi → bỏ qua nhánh đó, liệt kê trong báo cáo (Item vẫn chạy các nhánh còn lại; parser sẽ báo nhánh thiếu).

**Nhánh git** (mục "Nhánh git" của `CLAUDE.md`): sau gate, so nhánh hiện tại với nhánh `<b>` của `<m>` (cột `Branch` của `spec_status.md`; chế độ đơn `<m>`). Khác nhau → báo nhánh đúng và lệnh (`git checkout <b>`, hoặc `git checkout -b <b> main` nếu chưa có), chỉ chuyển khi người dùng đồng ý; không chạy S5 của module con trên `main`. Commit/push đầu ra chỉ khi người dùng yêu cầu; báo cáo cuối gợi ý lệnh commit và `git push -u origin <b>`.

## Bước 1 – Rule

Đọc `tb_coding_rules/` (trừ README.md) nếu có; chỗ không nói tới hoặc thư mục trống → `references/default_tb_rules.md` (kiến trúc component, timing, log, khung mẫu `pulse_cnt` đã chạy thật).

## Bước 2 – Viết môi trường TB và testcase

Đọc vplan, RTL (port, parameter), spec (handshake, reset, chu kỳ clock, latency). Chi tiết và khung mẫu: `references/default_tb_rules.md`. Luật bắt buộc:

- **Ngôn ngữ:** Verilog-2005 (IEEE 1364-2005) cho mọi file `tb/`, `tc/`. Không construct SystemVerilog nào (`logic`, `bit`, `string`, `always_ff`, `typedef`, `enum`, `struct`, `interface`, `package`, `class`, `foreach`, queue, `$fatal`, SVA…). Comment, tên task và log chỉ dùng tiếng Anh. Port nối theo tên.
- **Component** (module riêng, file `tb/tb_<m>_<role>.v`, tên không trùng module RTL): clock/reset generator `u_clk_rst` (lái `clk`, `rst_n`), driver `u_drv` (lái mọi input DUT khác, task giao thức – vd. APB master), monitor `u_mon` (lấy mẫu mọi chân DUT ở `negedge`, xuất `s_*`, `s_vld`), golden reference model `u_model` (nhận clock, reset, mẫu **input** của monitor; xuất `exp_*`; viết theo spec, không lấy output DUT, không chép RTL), checker `u_chk` (so `exp_*`/giá trị VPLAN với mẫu output của monitor ở `negedge + CHK_DLY`, gửi kết quả cho logger), logger `u_log` (header nhánh, dòng check căn cột, sở hữu `pass_count`/`fail_count`, `[SUMMARY]`, `Test_result`). Dữ liệu mức chân đi qua `wire` khai báo ở phần 1 của TB top, mỗi `wire` một nguồn lái; lời gọi mức giao dịch là task qua tên instance. Không thêm component rỗng/chuyển tiếp; vai trò DUT không cần thì bỏ, giao thức độc lập thứ hai thì có driver/monitor riêng. Mỗi component có header comment (vai trò, port, timing, ai gọi, ai sở hữu biến).
- **TB top: cấu trúc 9 phần, đúng thứ tự**, mỗi phần có header comment, giữ đủ header kể cả khi TB nhỏ: `1. Declaration` (parameter, `wire` nối, biến testcase dùng) → `2. DUT Instance` → `3. Clock Generation` (`u_clk_rst`) → `4. Init Reset` (`reset_dut`: driver nghỉ, reset qua `u_clk_rst`; reset DUT/model, không xóa bộ đếm) → `5. Golden Reference Model` (`u_model`) → `6. Checker` (`u_mon`, `u_chk`, `u_log`) → `7. Helper Functions` → `8. Tasks` (`u_drv`, task sequence dùng chung, `init_test`, `end_test`) → `9. Main Program Body` (`` `include "run_test.v" `` + `initial` timeout toàn cục: `u_log.error_msg("[TIMEOUT] …")`, `end_test`).
- **`init_test`** (một lần mỗi Item): `u_log.init` (bộ đếm = 0), bật checker, đọc plusarg như `+IN`/`+OUT`. **`end_test`**: `u_log.summary` (`[SUMMARY]`, `Test_result: PASSED` khi FAIL = 0 và PASS > 0, ngược lại `FAILED`), rồi `$finish`.
- **Mỗi Item cấp cao nhất → một file `tc/<ID>.v`**, `<ID>` = ID của Item dạng `TC_<M>_<NNN>` (Makefile suy ra module từ tên này) – ID thực thi cho tên file, `TESTNAME`, `pat.list`, log. Không tạo file cho từng dòng hay từng Sub item. File có header comment (ID, Item, mục tiêu, cây nhánh con) và đúng một khối `initial` thụt 2 khoảng trắng: `init_test; u_log.item("<Item>");` → mỗi Sub item 1/Sub item 2 là một khối có tên `begin : <name>` theo đúng cây và thứ tự vplan, lệnh đầu là header `u_log.sub1(...)`/`u_log.sub2(...)` → `end_test;`. `reset_dut` đầu tiên nằm sau header của nhánh lá đầu tiên; reset giữa các nhánh gọi lại `reset_dut` (chỉ DUT/model, bộ đếm của Item giữ nguyên). Tc chỉ mô tả kịch bản (task driver/reset, `u_chk.expect_*` với giá trị VPLAN, header); không khai báo biến. Không chọn test bằng `+TEST`; test được chọn bằng `make TESTNAME=<ID>`.
- **Clock:** `` `timescale 1ns/1ps ``, `parameter CLK_PERIOD = 20;` (20 ns mặc định; spec quy định chu kỳ khác thì theo spec) truyền vào `u_clk_rst`: `clk = 1'b0` trong `initial` + `always #(CLK_PERIOD / 2) clk = ~clk;`.
- **Stimulus:** mọi lần lái input DUT (trong task của driver) là `@(posedge clk); #1;` rồi gán. Không lái ở negedge, không lái đúng tại posedge. `#1` chỉ có trong TB, không bao giờ trong RTL.
- **Reset:** theo spec – reset async tích cực ngay, nhả tại `posedge + #1`; reset đồng bộ lái như stimulus.
- **Self-check:** check tự động mỗi mẫu monitor (model vs DUT) và check theo VPLAN (`expect_*`, giá trị số của Pass condition vs mẫu monitor kế tiếp); expected không bao giờ lấy từ output DUT; so bằng `===` (bắt X/Z); timeout toàn cục. Chỉ logger tăng `pass_count`/`fail_count` (`integer`): PASS + FAIL = số dòng check (+ số `error_msg`).
- **Log chuẩn** (`check_sim_log.py` và `sim/report.csh` đọc), thứ tự Item → Sub item 1 → Sub item 2 → dòng check:
  - `[ITEM] <Item>` một lần ở đầu log; `  [SUBITEM1] <Sub item 1>` một lần khi bắt đầu nhóm; `    [SUBITEM2] <Sub item 2>` khi bắt đầu lá – chỉ các cấp có trong vplan, tên đúng nguyên văn ô vplan (danh sách: `check_sim_log.py --items <vplan>`); không in lại tên cha trước mỗi check; đổi cha thì xóa context con.
  - Mỗi check `[<time>] <case> PASS | expected: <exp> | actual: <act>` hoặc `... FAIL | ...` nằm sau header của đúng nhánh lá của nó – kể cả check tự động theo chu kỳ và check trong reset/setup (header chỉ in tại `posedge + #1` hoặc ngay sau khi `expect_*` trả về). `<time>` = `$time`, `<case>` ngắn mô tả đặc điểm input quan trọng (`addr_0_wdata_A5A5A5A5`, `valid_1_ready_0` – không `CASE_001`), expected = model hoặc giá trị VPLAN, actual = DUT qua monitor.
  - **Mọi dòng check thẳng cột** (`<time>` căn phải `TIME_W`, `<case>` căn trái `NAME_W`, `<exp>`/`<act>` căn phải `VAL_W`, in qua task `result` của logger + hàm `pad_left`/`pad_right` Verilog-2005 – không `%-40s`/`%8d`); cuối cùng `[SUMMARY] PASS=<n> FAIL=<n>` rồi `Test_result: PASSED|FAILED`. Chi tiết ở mục 7 của `default_tb_rules.md`.
- **Dữ liệu từ file** (chỉ khi vplan/spec dùng vector ngoài): input ở `doc/database/input/<m>_<tên>.txt`, tham chiếu ở `doc/database/output/<m>_<tên>.txt`; TB đọc qua `+IN=`/`+OUT=`, mặc định là đường dẫn tương đối từ `sim/` (`../doc/database/input/...`). Script sinh dữ liệu đặt ở `sim/script/<m>_gen_vectors.py` (`make gen_data`).
- DUT có module con (phạm vi tích hợp): instance module cha, stimulus qua port của nó, monitor/checker trên port của nó.

## Bước 3 – Môi trường `sim/` và chạy

`sim/` dùng chung cho mọi module; mẫu ở `references/sim_env/` (`init_project` đã chép sẵn khi tạo project). Trước khi chạy, đọc `sim/Makefile`, `compile.f`, `tb.f`, `rtl.f`, `pat.list` để dùng đúng target và biến của bản đang có; mọi lần biên dịch/mô phỏng đều đi qua `sim/Makefile`, không tự gõ lệnh simulator.

- `Makefile`, `compile.f`, `run.csh`, `report.csh`, `schematic.tcl`, `cov_excl.tcl` chưa có → chép từ `references/sim_env/`. Đã có → **không ghi đè** (có thể là bản người dùng đã chỉnh); khác mẫu thì nêu trong báo cáo.
- `rtl.f`, `tb.f`, `pat.list` chưa có → chép mẫu rồi thêm như dưới.
- `rtl.f`: mọi file trong `rtl/`, module con trước module cha, đường dẫn `../rtl/<file>.v`, mỗi dòng một file (S1 ghi sẵn ở dạng comment, S3 bỏ comment khi viết RTL). Dòng của cây `<m>` còn comment → bỏ comment; chưa có → thêm. Không sửa dòng của module khác.
- `tb.f`: nhóm `// --- <b> ---` của `<m>` (chưa có → thêm, cách nhóm khác một dòng trống, đặt trước dòng cuối `../tb/${TB_NAME}.v`) liệt kê mọi file component `../tb/tb_<m>_<role>.v` của `<m>`, mỗi dòng một file (thứ tự: clk_rst, driver, monitor, model, checker, logger). Giữ dòng cuối `../tb/${TB_NAME}.v`; không sửa nhóm của module khác. `tb.f` cũ chỉ có dòng `../tb/${TB_NAME}.v` vẫn hợp lệ – chỉ thêm nhóm. Component của mọi nhóm đều được biên dịch mỗi lần build.
- `pat.list`: ID các Item của `<m>` (mỗi dòng một ID, không comment, theo thứ tự vplan), thêm vào cuối nhóm `// --- <b> ---` của `<m>` (S1 ghi sẵn dòng mở đầu nhóm; không sửa dòng mở đầu và dòng trống giữa các nhóm); dòng chứa `//` là comment (cũng bỏ qua trong `rtl.f`, `tb.f`). **Mặc định theo nhánh** (mục "Nhánh git" của `CLAUDE.md`): chỉ ID của nhóm nhánh hiện tại để mở – trên nhánh module là nhóm `<b>`, trên `main` là nhóm của top; ID của mọi nhóm khác (vd. có được sau khi merge) comment bằng tiền tố `//` (`//TC_<M>_<NNN>`), giữ nguyên dòng, không xóa. Regression `./run.csh` vì vậy chỉ chạy test của nhánh; người dùng tự mở comment khi muốn chạy thêm. Làm lại module mà ID Item đổi → bỏ ID cũ của `<m>` không còn file `tc/`.

Makefile suy ra `MODULE` từ `TESTNAME` (`TC_<M>_<NNN>` → `<m>` chữ thường), `TB_NAME = tb_<m>`; `tb.f` dùng `${TB_NAME}`. Chạy nếu có QuestaSim (`vsim` trong PATH), từng Item một (không cần `csh`):

```bash
for t in <ID_1> <ID_2> ...; do make -C sim all TESTNAME=$t; done
python3 .claude/skills/rtl-s5-tb/scripts/check_sim_log.py sim/log/<ID_1>.log sim/log/<ID_2>.log ... doc/vplan/<m>_vplan.<ext>
```

`check_sim_log.py` đọc bảng checklist của vplan (`.md` bảng HTML rowspan, `.csv` ô trống = kế thừa và `—` = cấp không tồn tại, `.xlsx`/`.docx` ô gộp thật; bảng khác như "Function coverage" bị bỏ qua), dựng cây Item → Sub item 1 → Sub item 2, đọc một hay nhiều log (bỏ tiền tố `# `), rồi kiểm: Item chưa chạy (`--partial` để chỉ kiểm Item có log), nhánh lá thiếu hoặc không có check, nhánh thừa, sai cha, sai thứ tự cấp (`[SUBITEM2]` không có `[SUBITEM1]`, check ngoài nhánh lá hoặc trước `[ITEM]`), nhánh in lại/sai thứ tự vplan, check FAIL, dòng check sai định dạng, `<ID>.log` in Item khác, nhiều `[ITEM]` trong một log, Item trùng giữa các log, `[SUMMARY]` thiếu/trùng/lệch số dòng PASS/FAIL và `Test_result` thiếu/sai trong từng log, `[TIMEOUT]`/`[LOG ERROR]`/fatal. ID khác dạng `TC_…` → `--id-re '<regex>'`.

`make` dừng ở `build`/`run` (lỗi biên dịch hoặc dựng thiết kế) → đọc khối `ERRORS` cuối output hoặc `sim/log/<ID>.log` (đủ file, dòng của từng lỗi); lỗi trong `tb/`, `tc/` → sửa, lỗi trong `rtl/` → phân loại như dưới.

Check FAIL → phân loại:
- Lỗi testbench (stimulus/chu kỳ kiểm sai so với vplan, model sai so với spec, race giữa component) → sửa TB/testcase, chạy lại.
- Lỗi RTL hoặc vplan → **không sửa**; báo ID và đường dẫn nhánh (`<ID> › <Sub item 1> › <Sub item 2>`), triệu chứng, nghi ngờ ở file/dòng nào, cần sửa ở S3 hay S4.

Không có QuestaSim → không phải lỗi thiết kế; không thay bằng simulator khác ngoài `sim/`; ghi "chưa chạy mô phỏng" và lệnh chạy.

## Đầu ra

```
tb/tb_<m>.v                          # Verilog-2005, TB top 9 phần
tb/tb_<m>_<role>.v                   # Verilog-2005, component của môi trường
tc/<ID>.v                            # một file mỗi Item cấp cao nhất của vplan
sim/rtl.f, sim/tb.f, sim/pat.list    # cập nhật cho <m>
sim/Makefile, compile.f, run.csh, report.csh, schematic.tcl, cov_excl.tcl   # chỉ khi chưa có (chép mẫu)
sim/script/<m>_gen_vectors.py, doc/database/{input,output}/<m>_*.txt # chỉ khi TB dùng file dữ liệu
sim/log/<ID>.log                     # nếu đã chạy – sinh ra, bị .gitignore
```

Làm lại module theo cấu trúc mới → xóa `tc/` của `<m>` không còn là Item trong vplan (vd. file theo từng dòng của vplan phẳng cũ) và component cũ không còn dùng. File theo cấu trúc thư mục cũ (`tb/<m>/tb_<m>.v|.sv`, `sim/<m>/…`, `testcases/<ID>.v`) → **không tự xóa**, không đưa vào filelist; nêu trong báo cáo là file legacy để người dùng quyết định.

## Báo cáo cuối (chỉ trong chat)

File · ngôn ngữ TB (Verilog-2005) · component và kết nối (instance → instance) · file legacy còn lại (nếu có) · file `sim/` dùng chung khác mẫu (nếu có) · số Item/nhánh lá hiện thực / tổng vplan · kết quả theo ID (số check PASS/FAIL theo nhánh, `[SUMMARY]`, `Test_result`) · nhánh bỏ qua vì TBD · lỗi nghi ở RTL/vplan kèm đề xuất · lệnh chạy lại (`make -C sim all TESTNAME=<ID>`, `cd sim && ./run.csh && ./report.csh`).

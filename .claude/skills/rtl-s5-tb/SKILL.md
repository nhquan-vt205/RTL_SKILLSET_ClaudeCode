---
name: rtl-s5-tb
description: Stage 5 của RTL flow (tùy chọn, nhẹ) – viết testbench self-checking Verilog-2005 cho MỘT module (leaf hoặc cả cây con ở mức tích hợp) gồm TB top tb/tb_<m>.v (cấu trúc 9 phần) và các component tb/tb_<m>_<role>.v nối bằng port thật (clock/reset generator, driver, monitor, golden model, checker, logger), mọi expected chỉ do golden model theo spec tính (vplan chỉ quyết định kịch bản stimulus), mỗi Item cấp cao nhất của vplan một file tc/<ID>.v chạy mọi Sub item 1/Sub item 2 của Item, log ngắn, cô đọng (vài dòng [TEST], [ITEM]/[SUBITEM1]/[SUBITEM2] + một [GOAL] ngắn, prefix [t=<ns> ns clk=<n>] với clk đếm từ đầu mô phỏng không reset, mỗi giao dịch/input/reset một dòng, check gộp expected/actual/PASS|FAIL trên cùng dòng, chỉ in sai lệch của watch, mỗi sai lệch đúng một dòng FAIL kèm chú thích ngắn khi cần, không diễn giải model, radix theo ý nghĩa, [SUMMARY]/Test_result), clock mặc định 20 ns, stimulus tại posedge + #1, cập nhật môi trường mô phỏng dùng chung sim/ (Makefile QuestaSim, rtl.f, tb.f, pat.list), mô phỏng bằng QuestaSim nếu có. Theo rule testbench của người dùng trong tb_coding_rules/ nếu có. Dùng khi người dùng gọi /rtl-s5-tb <module> hoặc yêu cầu viết testbench theo vplan.
argument-hint: "<tên_module> [tên_module ...]"
disable-model-invocation: true
---

# Stage 5 – Testbench theo vplan

Module: `$ARGUMENTS`

Stage này **tùy chọn**, chỉ chạy khi người dùng cần mô phỏng.

Testbench tự kiểm, gồm các component có kết nối thật: sequence (tc, chỉ stimulus) → driver → DUT → monitor → golden reference model + checker → logger (bộ đếm PASS/FAIL) → log phân cấp → `[SUMMARY]` + `Test_result`. **Mọi expected dùng để kết luận PASS/FAIL do golden model tự viết theo spec tính**; vplan quyết định chức năng, phân nhóm và kịch bản stimulus. Log ngắn, cô đọng: đọc cùng spec là thấy ngay đang kiểm chức năng gì, TB đã tác động gì lên DUT và khi nào, checkpoint nào sai đầu tiên; model tính đầy đủ bên trong nhưng không in diễn giải. Không chỉ `$display` để xem waveform bằng mắt. Không UVM, class, SystemVerilog interface/package, random, SVA/assertion, framework scoreboard. (Target coverage có sẵn trong `sim/Makefile` là của người dùng; S5 không viết gì cho coverage.)

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

Gate cần spec PASS, bảng port, RTL của module **và mọi module con** (để mô phỏng được), vplan. Mã thoát ≠ 0 → bỏ qua module đó, báo `[THIẾU]`. `--items` đọc bảng checklist (ô gộp) và in cây Item → Sub item 1 → Sub item 2 cùng các header log mong đợi; mã thoát ≠ 0 (bảng sai cấu trúc, hoặc vplan định dạng cũ – bảng pipe phẳng) → dừng, báo lỗi của từng hàng và đề xuất chạy lại `/rtl-s4-vplan <m>`. Nhánh lá còn `TBD` ở Test sequence → bỏ qua nhánh đó, liệt kê trong báo cáo (Item vẫn chạy các nhánh còn lại; parser sẽ báo nhánh thiếu). `TBD` chỉ ở Pass condition → vẫn hiện thực nếu spec đủ để model tính expected (nêu trong báo cáo); spec không đủ → bỏ qua nhánh, báo thông tin spec còn thiếu (không tự chọn số).

**Nhánh git** (mục "Nhánh git" của `CLAUDE.md`): sau gate, so nhánh hiện tại với nhánh `<b>` của `<m>` (cột `Branch` của `spec_status.md`; chế độ đơn `<m>`). Khác nhau → báo nhánh đúng và lệnh (`git checkout <b>`, hoặc `git checkout -b <b> main` nếu chưa có), chỉ chuyển khi người dùng đồng ý; không chạy S5 của module con trên `main`. Commit/push đầu ra chỉ khi người dùng yêu cầu; báo cáo cuối gợi ý lệnh commit và `git push -u origin <b>`.

## Bước 1 – Rule

Đọc `tb_coding_rules/` (trừ README.md) nếu có; chỗ không nói tới hoặc thư mục trống → `references/default_tb_rules.md` (kiến trúc component, nguồn expected, timing, log, radix, chẩn đoán). Khung mẫu đã chạy thật: `references/example_timer_top/` (`tb/`, `tc/`, `log/` – `cnt_ctrl` kiểm qua `timer_top`, log PASS và log FAIL); đọc các file đó khi viết component.

## Bước 2 – Viết môi trường TB và testcase

Đọc vplan (chức năng, nhánh, Test sequence), RTL (chỉ port, parameter – không lấy hành vi từ RTL), spec (register map, handshake, reset, chu kỳ clock, latency – nguồn của model). Chi tiết và khung mẫu: `references/default_tb_rules.md`. Luật bắt buộc:

- **Ngôn ngữ:** Verilog-2005 (IEEE 1364-2005) cho mọi file `tb/`, `tc/`. Không construct SystemVerilog nào (`logic`, `bit`, `string`, `always_ff`, `typedef`, `enum`, `struct`, `interface`, `package`, `class`, `foreach`, queue, `$fatal`, SVA…). Comment, tên task và log chỉ dùng tiếng Anh. Port nối theo tên.
- **Component** (module riêng, file `tb/tb_<m>_<role>.v`, tên không trùng module RTL): clock/reset generator `u_clk_rst` (lái `clk`, `rst_n` và `clk_cnt` = số cạnh lên từ đầu mô phỏng, khởi tạo một lần, không bao giờ reset; log `[RESET]` lúc assert/release), driver `u_drv` (lái mọi input DUT khác, task giao thức – vd. APB master; không log từng pha bus; log `[DRIVE] <sig>: cũ -> mới` khi input ngoài bus thật sự đổi, `[WAIT] n cycles` khi chờ có nghĩa với kịch bản, `[TIMEOUT]` khi handshake quá `MAX_WAIT`), monitor `u_mon` (lấy mẫu mọi chân DUT ở `negedge`, xuất `s_*`, `s_vld`, thời điểm mẫu `s_time`, trạng thái giao dịch quan sát `s_done`/`s_wait`/`s_setup`; log `[OBSERVE]` khi output có cạnh quan trọng đổi, vd. ngắt), golden reference model `u_model` (nhận clock, reset, mẫu **input** của monitor; xuất `exp_*`; không in gì – tối đa một hàm trả tên quy tắc cho chú thích của dòng FAIL, vd. `err_text`; viết theo spec, không đọc output hay trạng thái nội bộ DUT, không chép RTL), checker `u_chk` (so `exp_*` với mẫu output ở `negedge + CHK_DLY`, log với thời điểm mẫu: mỗi giao dịch một dòng lúc hoàn tất, watch mọi mẫu khác và chỉ in khi lệch, checkpoint; `sync`), logger `u_log` (prefix `[t=<ns> ns clk=<n>]`, hàm định dạng `fmt_hex/fmt_bin/fmt_dec/fmt_cnt/fmt_sdec/fmt_bit`, căn cột, sở hữu `pass_count`/`fail_count`, `[SUMMARY]`, `Test_result`). Mỗi thao tác được log đúng một dòng, bởi component biết kết quả của nó; không log thao tác chưa xảy ra. Dữ liệu mức chân đi qua `wire` khai báo ở phần 1 của TB top, mỗi `wire` một nguồn lái; lời gọi mức giao dịch là task qua tên instance. Không `force`/`deposit`, không đọc tín hiệu nội bộ DUT. Không thêm component rỗng/chuyển tiếp; vai trò DUT không cần thì bỏ, giao thức độc lập thứ hai thì có driver/monitor riêng. Mỗi component có header comment (vai trò, port, timing, log, ai gọi, ai sở hữu biến).
- **TB top: cấu trúc 9 phần, đúng thứ tự**, mỗi phần có header comment, giữ đủ header kể cả khi TB nhỏ: `1. Declaration` (parameter, cột log, `wire` nối, biến task sequence dùng) → `2. DUT Instance` → `3. Clock Generation` (`u_clk_rst`) → `4. Init Reset` (`reset_dut`: driver nghỉ, reset qua `u_clk_rst`, `u_chk.sync`; reset DUT/model, không xóa bộ đếm PASS/FAIL hay `clk_cnt`) → `5. Golden Reference Model` (`u_model`) → `6. Checker` (`u_mon`, `u_chk`, `u_log`) → `7. Helper Functions` (hàm trình bày log theo register map: tên thanh ghi, field của mask) → `8. Tasks` (`u_drv`, task sequence chỉ stimulus và kết thúc bằng `u_chk.sync`, `init_test`, `end_test`) → `9. Main Program Body` (`` `include "run_test.v" `` + `initial` timeout toàn cục: `u_log.error_msg($time, "TIMEOUT", …)`, `end_test`).
- **`init_test(id, objective)`** (một lần mỗi Item): `u_log.init` (bộ đếm = 0), vài dòng bối cảnh `[TEST]` (ID và mục tiêu; DUT, phạm vi port công khai, spec; quy ước thời gian/clock mô tả một lần: `t` theo ns, `clk` = số cạnh lên từ đầu mô phỏng không reset, điểm lái/điểm lấy mẫu, dòng APB in lúc hoàn tất; nguồn expected và nghĩa của `OK`), đọc plusarg như `+IN`/`+OUT`. **`end_test`**: `u_log.summary` (`[SUMMARY]`, `Test_result: PASSED` khi FAIL = 0 và PASS > 0, ngược lại `FAILED`), rồi `$finish`.
- **Mỗi Item cấp cao nhất → một file `tc/<ID>.v`**, `<ID>` = ID của Item dạng `TC_<M>_<NNN>` (Makefile suy ra module từ tên này) – ID thực thi cho tên file, `TESTNAME`, `pat.list`, log. Không tạo file cho từng dòng hay từng Sub item. File có header comment (ID, Item, mục tiêu, cây nhánh con) và đúng một khối `initial` thụt 2 khoảng trắng: `init_test("<ID>", "<objective>"); u_log.item("<Item>");` → mỗi Sub item 1/Sub item 2 là một khối có tên `begin : <name>` theo đúng cây và thứ tự vplan, lệnh đầu là header `u_log.sub1(...)`/`u_log.sub2(...)` rồi một dòng `u_log.goal(...)` ngắn → `end_test;`. `reset_dut` đầu tiên nằm sau header của nhánh lá đầu tiên; reset giữa các nhánh gọi lại `reset_dut` (chỉ DUT/model, bộ đếm của Item giữ nguyên). **Tc chỉ mô tả stimulus** theo Test sequence của vplan (task sequence của TB top – vd. `apb_write`, `apb_read`, `set_dbg_mode(v)`, `wait_cycles(n)` –, `reset_dut`, header/goal, `u_chk.checkpoint("<what>")` khi cần một check ở đúng thời điểm vplan nêu; input ngoài bus đổi ở điểm lái hợp lệ gần nhất sau thao tác trước, không chèn chờ/quan sát thừa); literal trong tc chỉ là stimulus và chữ mô tả – không expected nào; không khai báo biến. Không chọn test bằng `+TEST`; test được chọn bằng `make TESTNAME=<ID>`.
- **Clock:** `` `timescale 1ns/1ps ``, `parameter CLK_PERIOD = 20;` (20 ns mặc định; spec quy định chu kỳ khác thì theo spec) truyền vào `u_clk_rst`: `clk = 1'b0` trong `initial` + `always #(CLK_PERIOD / 2) clk = ~clk;`.
- **Stimulus:** mọi lần lái input DUT (trong task của driver) là `@(posedge clk); #1;` rồi gán. Không lái ở negedge, không lái đúng tại posedge. `#1` chỉ có trong TB, không bao giờ trong RTL.
- **Reset:** theo spec – reset async tích cực ngay, nhả tại `posedge + #1`; reset đồng bộ lái như stimulus.
- **Expected chỉ từ golden model** (mục 2.2 của `default_tb_rules.md`): không truyền expected literal từ tc vào checker, không task kiểu `expect_rdata(name, 32'h…)`; số trong Pass condition không bao giờ là expected thay thế – chỉ dùng để soát model khi viết TB (lệch → đối chiếu spec: sửa model, hoặc báo vplan sai). Bỏ check literal không làm bỏ nhánh hay giảm phạm vi: mọi nhánh lá vẫn hiện thực, mọi đại lượng Pass condition nêu vẫn được quan sát. Hằng số reset, mask, công thức, latency có căn cứ spec được phép trong model. Model cập nhật theo stimulus thực tế đã áp (mẫu monitor), phân biệt request với giao dịch đã chấp nhận; handshake của DUT được kiểm riêng với model/giao thức (không để model đi theo lỗi DUT); không nạp lại giá trị DUT đọc sai vào model. Spec thiếu thông tin → báo thiếu, không lấy số vplan.
- **Self-check (đủ, nhưng in ít):** mỗi giao dịch hoàn tất được kiểm đáp ứng (cờ lỗi + số wait cycle, so với model) và – với lệnh đọc – dữ liệu; watch mọi output ở mọi mẫu khác nhưng chỉ in khi lệch (FAIL đầu tiên của một output in ngay; lặp lại chỉ đếm và đóng bằng một dòng `[WATCH END]` (không đếm) khi khớp lại; output khác hoặc lệch mới sau khi đã khớp lại vẫn in FAIL riêng; không bỏ sót sai lệch giữa khoảng chờ); checkpoint khi tc yêu cầu. So bằng `===` (X/Z là FAIL); giới hạn chờ handshake và timeout toàn cục. Chỉ logger tăng `pass_count`/`fail_count` (`integer`): **PASS = số dòng kết thúc bằng `PASS`, FAIL = số dòng kết thúc bằng `FAIL` + số dòng lỗi** (`TIMEOUT`/`PROTOCOL ERROR`/`LOG ERROR`); dòng sự kiện (`APB WRITE … OK`, `DRIVE`, `RESET`, `WAIT`, `OBSERVE`, `WATCH END`) không bao giờ được đếm. `OK` ở dòng ghi chỉ nói transfer hoàn tất không báo lỗi – không phải bằng chứng thanh ghi lưu đúng, không phải một data-check PASS.
- **Log chuẩn** (`check_sim_log.py` và `sim/report.csh` đọc; chi tiết mục 7 của `default_tb_rules.md`), tiếng Anh:
  - Bối cảnh `[TEST] …` đầu log; `[ITEM] <Item>` một lần; `  [SUBITEM1] <Sub item 1>` một lần khi bắt đầu nhóm; `    [SUBITEM2] <Sub item 2>` khi bắt đầu lá – chỉ các cấp có trong vplan, tên đúng nguyên văn ô vplan (danh sách: `check_sim_log.py --items <vplan>`); một `[GOAL]` ngắn ngay dưới header; không in lại tên cha, mục tiêu hay mô tả dài trên các dòng sau; đổi cha thì xóa context con.
  - Prefix `[t=<ns> ns clk=<n>]`: thời điểm stimulus thật sự áp (`posedge + 1`) hoặc output thật sự được lấy mẫu (`negedge`), không phải lúc logger in; `clk` lấy từ `clk_cnt` dùng chung. Không pha, không transaction ID. Số dòng tối thiểu cho mỗi thao tác: ghi bus một dòng lúc hoàn tất `[APB WRITE <REG>] addr: 0x… data: 0x… strb: 0b… OK` (không tách REQUEST/SETUP/ACCESS/COMPLETE; wait state hay response bất thường → dòng FAIL, chú thích nêu số wait và `clk` của pha setup hoặc điều kiện lỗi model dự đoán); đọc bus một dòng gộp dữ liệu và kết quả `[APB READ <REG>] addr: 0x… expected: … actual: … PASS|FAIL`; input ngoài bus `[DRIVE] dbg_mode: 0 -> 1`; reset `[RESET]` lúc assert và release; chờ `[WAIT] 8 cycles …` chỉ khi cần hiểu kịch bản. Không dòng `MODEL`, không diễn giải lịch sử đếm/công thức/cập nhật state, không PASS lặp theo chu kỳ.
  - Dòng check `<prefix> [<TAG>] <text> expected: <e> actual: <a> PASS|FAIL [(<note>)]` nằm sau header của đúng nhánh lá của nó (mọi task sequence kết thúc bằng `u_chk.sync`). Một sai lệch luôn chỉ **một dòng**: khi expected/actual chưa đủ, thêm chú thích ngắn trong ngoặc sau `FAIL` – thanh ghi hex: field khác `(differ: HALT_ACK)`; đáp ứng ghi: số wait so với model và `clk` setup, hoặc điều kiện lỗi model dự đoán; watch: tình trạng bus ngay sau tên output `[WATCH] tim_pready (access cycle 2 of APB WRITE TCR, setup clk=3) expected: 1 actual: 0 FAIL`; số đếm và X/Z: không cần chú thích. Không dòng chẩn đoán riêng, không phân tích dài, không phỏng đoán nguyên nhân. Prefix, tag (`TAG_W`) và expected/actual của dòng đọc (`VAL_W`) căn cột bằng `pad_left`/`pad_right` Verilog-2005 – không `%-40s`/`%8d`.
  - **Radix theo ý nghĩa**: hex `0x` cho địa chỉ, dữ liệu thô, cấu hình, mask; binary `0b` cho strobe/nhóm bit; decimal kèm đơn vị cho số đếm, số chu kỳ, độ dài, kết quả số học (TDR là thanh ghi nhưng khi kiểm chức năng đếm in decimal `3 counts`; không in cả hex lẫn decimal cho cùng số đếm nếu không giúp chẩn đoán; hex viết hoa `0x01C`); bit đơn 0/1. Expected và actual cùng radix, đơn vị, signed/unsigned; giữ đủ độ rộng (kể cả 64-bit); X/Z → FAIL và in raw hex/binary. Radix không đổi phép so.
  - Cuối log: `[SUMMARY] PASS=<n> FAIL=<n>`, `Test_result: PASSED|FAILED` (không lặp lại lỗi đầu tiên bằng `[FIRST FAIL]`: dòng FAIL đầu tiên đã hiện rõ dưới header nhánh của nó).
- **Dữ liệu từ file** (chỉ khi vplan/spec dùng vector ngoài): input ở `doc/database/input/<m>_<tên>.txt`, tham chiếu ở `doc/database/output/<m>_<tên>.txt`; TB đọc qua `+IN=`/`+OUT=`, mặc định là đường dẫn tương đối từ `sim/` (`../doc/database/input/...`). Script sinh dữ liệu đặt ở `sim/script/<m>_gen_vectors.py` (`make gen_data`).
- DUT có module con (phạm vi tích hợp, vd. chức năng `cnt_ctrl` kiểm qua `timer_top`): instance module cha, stimulus chỉ qua port công khai của nó (cấu hình thanh ghi qua bus để tạo điều kiện cho module con), monitor/checker trên port của nó; không `force`/`deposit`/lái trực tiếp tín hiệu nội bộ module con; tín hiệu nội bộ (vd. `cnt_en`, `div_cnt`) chỉ tồn tại trong model, không bao giờ in như giá trị đo được; hành vi của chúng được kiểm qua output công khai (vd. đọc TDR) so với model. Chọn checkpoint đủ phân biệt (vd. halt: THCSR kiểm cơ chế yêu cầu/xác nhận, TDR đọc trong halt hai lần cách nhau một khoảng giữ và một lần sau khi nhả để phân biệt "đã dừng", "vẫn đếm", "đã đếm tiếp"; không mặc định giá trị lúc halt bằng lần đọc trước). Mẫu: `references/example_timer_top/`. Mẫu: `references/example_timer_top/`.

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

`check_sim_log.py` đọc bảng checklist của vplan (`.md` bảng HTML rowspan, `.csv` ô trống = kế thừa và `—` = cấp không tồn tại, `.xlsx`/`.docx` ô gộp thật; bảng khác như "Function coverage" bị bỏ qua), dựng cây Item → Sub item 1 → Sub item 2, đọc một hay nhiều log (bỏ tiền tố `# `), chỉ đếm dòng có prefix kết thúc bằng `PASS`/`FAIL` kèm `expected: … actual: …` (dòng sự kiện `… OK`/DRIVE/RESET/WAIT/OBSERVE/WATCH END không bao giờ được đếm; chú thích `(…)` sau `FAIL` được chấp nhận) và dòng lỗi `[TIMEOUT]`/`[PROTOCOL ERROR]`/`[LOG ERROR]`, rồi kiểm: Item chưa chạy (`--partial` để chỉ kiểm Item có log), nhánh lá thiếu hoặc không có check, nhánh thừa, sai cha, sai thứ tự cấp (`[SUBITEM2]` không có `[SUBITEM1]`, check ngoài nhánh lá hoặc trước `[ITEM]`), nhánh in lại/sai thứ tự vplan, check FAIL, lỗi trong nhánh, dòng check sai định dạng (kết thúc bằng PASS/FAIL mà thiếu `expected:`/`actual:` hoặc thiếu prefix; định dạng cũ `[<time>] <case> PASS|FAIL`, `[t=… c=… <phase> txn=…]`, `[CHECK …] PASS | expected:`), `clk` giảm (bộ đếm clock bị reset), `<ID>.log` in Item khác, nhiều `[ITEM]` trong một log, Item trùng giữa các log, `[SUMMARY]` thiếu/trùng/lệch (PASS = dòng PASS, FAIL = dòng FAIL + dòng lỗi), `Test_result` thiếu/sai trong từng log, fatal. ID khác dạng `TC_…` → `--id-re '<regex>'`.

`make` dừng ở `build`/`run` (lỗi biên dịch hoặc dựng thiết kế) → đọc khối `ERRORS` cuối output hoặc `sim/log/<ID>.log` (đủ file, dòng của từng lỗi); lỗi trong `tb/`, `tc/` → sửa, lỗi trong `rtl/` → phân loại như dưới.

Check FAIL → đọc dòng FAIL đầu tiên (nhánh, `t`, `clk`, expected, actual, chú thích) và các dòng thao tác ngay trước nó; cần hiểu sâu hơn thì xem waveform hoặc tạm thêm `$display` khi gỡ lỗi (không để lại trong TB), rồi phân loại:
- Lỗi testbench (stimulus sai so với Test sequence của vplan, model sai so với spec, race giữa component) → sửa TB/testcase, chạy lại. Không sửa model bằng cách chép giá trị DUT hay số vplan; model chỉ sửa theo spec.
- Lỗi RTL hoặc vplan → **không sửa**; báo ID và đường dẫn nhánh (`<ID> › <Sub item 1> › <Sub item 2>`), triệu chứng, nghi ngờ ở file/dòng nào, cần sửa ở S3 hay S4.

Không có QuestaSim → không phải lỗi thiết kế; không thay bằng simulator khác ngoài `sim/`; ghi "chưa chạy mô phỏng" và lệnh chạy.

Soát model (khi đã chạy): so các giá trị `expected` của log với số trong Pass condition của vplan; khác → đối chiếu spec, nêu trong báo cáo (model sai đã sửa, hoặc vplan sai cần S4).

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

File · ngôn ngữ TB (Verilog-2005) · component và kết nối (instance → instance) · nguồn expected (model, các quy tắc spec đã mô hình hóa) · file legacy còn lại (nếu có) · file `sim/` dùng chung khác mẫu (nếu có) · số Item/nhánh lá hiện thực / tổng vplan · kết quả theo ID (số check PASS/FAIL theo nhánh, FAIL đầu tiên, `[SUMMARY]`, `Test_result`) · chênh lệch model ↔ Pass condition của vplan (nếu có) · thông tin spec còn thiếu cho model · nhánh bỏ qua vì TBD · lỗi nghi ở RTL/vplan kèm bằng chứng từ log và đề xuất · lệnh chạy lại (`make -C sim all TESTNAME=<ID>`, `cd sim && ./run.csh && ./report.csh`).

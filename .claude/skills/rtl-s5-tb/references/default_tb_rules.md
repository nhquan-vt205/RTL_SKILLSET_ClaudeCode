# Rule testbench mặc định (chỉ dùng cho chỗ tb_coding_rules/ không nói tới)

Mục tiêu: testbench direct, tự kiểm, mô phỏng tất định, đọc được ở mức sinh viên, gồm các component có kết nối thật. Không UVM, class, SystemVerilog interface/package, SVA, coverage, random, framework scoreboard.

## 1. Ngôn ngữ và file

- **Verilog-2005 (IEEE 1364-2005)**. Ba loại file, đều chỉ là mã HDL, đặt phẳng:
  - `tb/tb_<m>.v`, module top `tb_<m>`: nối DUT với các component, task dùng chung, cấu trúc 9 phần (mục 3).
  - `tb/tb_<m>_<role>.v`, module `tb_<m>_<role>`: một component của môi trường (mục 2). Tiền tố `tb_<m>_` tránh trùng tên giữa các DUT và với module RTL; không đặt tên trùng một module trong `rtl/`.
  - `tc/<ID>.v`, một file mỗi **Item cấp cao nhất** của vplan (`<ID>` = ID Item `TC_<M>_<NNN>`): kịch bản của mọi nhánh con của Item, được `make build` chép thành `sim/run_test.v` và include vào phần 9 của TB top (mục 8).
- Phải là cú pháp Verilog-2005 thật – không phải đổi đuôi một file SystemVerilog.
- Dùng: `reg`, `wire`, `integer`, `parameter`, `localparam`, `module`/port ANSI, `always`, `initial`, `task`, `function`, `if`, `case`, `for`, `while`, `repeat`, `wait`, khối có tên `begin : <name>`, `$display`, `$write`, `$sformat`, `$value$plusargs`, `$test$plusargs`, `$fopen`/`$fgets`/`$sscanf` (khi đọc file dữ liệu), `$finish`, `` `include ``, gọi task theo tên phân cấp (`u_drv.cycle(...)`).
- **Cấm** (SystemVerilog): `logic`, `bit`, `byte`, `int`, `string`, `always_ff`, `always_comb`, `always_latch`, `typedef`, `enum`, `struct`, `union`, `interface`/`modport`, `package`/`import`, `class`, `virtual`, `foreach`, queue, mảng động, `mailbox`, `assert`/`property` (SVA), cast `type'(...)`, literal `'0`/`'1`, `$fatal`, khai báo biến trong `for` (`for (int i …)`).
- Chuỗi (tên nhánh, tên case): `reg [8*64-1:0]` (≤ 64 ký tự; tên vplan dài hơn → tăng độ rộng thống nhất ở mọi nơi); ghép chuỗi động bằng `$sformat(case_name, "addr_%0h_wdata_%h", addr, wdata);`; in bằng `%0s`.
- `` `timescale 1ns/1ps `` đầu mỗi file `tb/`.
- Comment, tên task/function/tín hiệu, chuỗi in và log chỉ dùng tiếng Anh.
- Danh sách biên dịch: `sim/tb.f` liệt kê mọi file component theo nhóm nhánh (`// --- <b> ---`, như `rtl.f`), component trước, dòng cuối `../tb/${TB_NAME}.v` (mục 11).

## 2. Kiến trúc môi trường: component và kết nối

Luồng dữ liệu:

```text
tc/<ID>.v (sequence) ──task──> u_drv ──wire──> u_dut ──wire──> u_mon
       │                                 ^                        │ samples s_* (inputs + outputs)
       │                  u_clk_rst ─clk/rst_n─┴──> u_model <─────┤ inputs only
       │                                               │ exp_*    │ outputs (actual)
       └──task (headers)──> u_log <──task result── u_chk <────────┘
```

| Vai trò | Instance | Module | Nhận | Lái / tạo ra |
| --- | --- | --- | --- | --- |
| Test sequence / controller | (khối `initial` của tc) | `tc/<ID>.v` | – | gọi task của `u_drv`, `u_clk_rst`, `u_chk` (`expect_*`), `u_log` (header) |
| Clock/reset generator | `u_clk_rst` | `tb_<m>_clk_rst` | – | `clk`, `rst_n` (driver duy nhất) |
| Protocol driver | `u_drv` | `tb_<m>_drv` | `clk`, output handshake của DUT nếu giao thức cần (vd. `pready`) | mọi input DUT trừ clock/reset (driver duy nhất) |
| Monitor | `u_mon` | `tb_<m>_mon` | mọi chân DUT (input đã thực sự áp + output) | mẫu `s_*`, `s_vld`; giao dịch đã hoàn tất nếu cần (vd. `rd_data` cuối một lần đọc APB) |
| Golden reference model | `u_model` | `tb_<m>_model` | `clk`, `rst_n`, mẫu **input** của monitor | `exp_*` |
| Checker | `u_chk` | `tb_<m>_chk` | `exp_*` (model), mẫu output `s_*` (monitor) | gọi `u_log.result` |
| Logger / result collector | `u_log` | `tb_<m>_log` | lời gọi `item`/`sub1`/`sub2`/`result`/`error_msg` | log; sở hữu `pass_count`, `fail_count` |
| DUT | `u_dut` | `<m>` | input từ `u_drv`, `u_clk_rst` | output → `u_mon` (và handshake → `u_drv`) |

Luật kết nối:

- **Dữ liệu mức chân đi qua port/wire thật** khai báo ở phần 1 của TB top: driver → DUT, DUT → monitor, monitor → model, model + monitor → checker. Mỗi `wire` có đúng một nguồn lái (một output port); ghi nguồn bằng comment cạnh khai báo (`// u_drv`). Không component nào gán lên tín hiệu do component khác lái; không đọc tín hiệu nội bộ của DUT.
- **Lời gọi mức giao dịch dùng task qua tên instance của TB top**: sequence → `u_drv.<task>`, `u_clk_rst.<task>`, `u_chk.expect_*`, `u_log.item/sub1/sub2`; checker → `tb_<m>.u_log.result`. Mỗi cặp chỉ một chiều gọi; ghi trong header của component.
- **Model độc lập**: tính expected từ spec/vplan với clock, reset và input DUT mà monitor đã lấy mẫu. Không nhận output DUT, không chép cấu trúc RTL (viết theo câu chữ của spec: công thức, bảng trạng thái, mô hình thanh ghi). Nếu thời điểm một giao dịch chỉ biết qua handshake do DUT trả về và spec không định nghĩa độ trễ, model chỉ dùng tín hiệu đó để biết *khi nào*, không bao giờ làm giá trị expected; ghi lý do trong header model.
- **Sở hữu biến**: mỗi `reg` có một process sở hữu rõ ràng; cờ handshake giữa hai process dùng cặp bộ đếm request/ack (mỗi process sở hữu một bộ đếm), không để hai process cùng gán một biến.
- Component nhỏ, chỉ chứa đúng vai trò của nó; không cần cấu trúc 9 phần. Mỗi file có header comment: tên, vai trò, port nhận/lái, timing, ai gọi task nào, biến nào thuộc ai.
- Mặc định mỗi vai trò một module. Không tạo module rỗng hay chỉ chuyển tiếp tín hiệu để đủ số: vai trò không có ở DUT thì bỏ (vd. DUT tổ hợp không clock/reset → không có `u_clk_rst`, monitor lấy mẫu theo một strobe do sequence tạo, ghi rõ trong header TB). DUT có nhiều giao thức độc lập (vd. APB + bus dữ liệu) → một driver/monitor cho mỗi giao thức (`tb_<m>_apb_drv`, `tb_<m>_apb_mon`…); vài input sideband đơn giản (vd. `dbg_mode`) do driver chính lái.

### 2.1 Timing trong một chu kỳ

| Thời điểm | Việc |
| --- | --- |
| `posedge` | DUT và model cập nhật trạng thái (model dùng mẫu input của chu kỳ vừa kết thúc ở cạnh này) |
| `posedge + #1` | driver đổi input DUT; `u_clk_rst` nhả reset; sequence in header nhánh |
| `negedge` | monitor lấy mẫu mọi chân DUT (`s_vld = 1` từ cạnh xuống thật đầu tiên – lần `clk` X→0 ở thời điểm 0 không phải cạnh) |
| `negedge + CHK_DLY` | checker so: check tự động (model vs DUT), rồi check VPLAN đang chờ; sau đó `expect_*` trả về |

- `CHK_DLY = 1` (parameter) < nửa chu kỳ: lúc đó mẫu monitor và output tổ hợp của model đã ổn định, stimulus chưa đổi. Không có race giữa model và checker.
- Reset bất đồng bộ được phép tích cực giữa chu kỳ (`u_clk_rst.assert_reset`, thường ngay sau `posedge + #1`), không đúng tại `negedge`…`negedge + CHK_DLY`.
- Header nhánh chỉ in tại `posedge + #1` (sau một task driver/reset) hoặc ngay sau khi `expect_*` trả về – không bao giờ trong khoảng checker đang so – để mọi check, kể cả check tự động, thuộc đúng nhánh đang mở.

## 3. TB top `tb/tb_<m>.v` – cấu trúc 9 phần, đúng thứ tự

Mỗi phần mở bằng header như sau, giữ đủ 9 header kể cả khi TB nhỏ:

```verilog
// ============================================================
// 1. Declaration
// ============================================================
```

| # | Header | Nội dung |
| --- | --- | --- |
| 1 | `Declaration` | `parameter CLK_PERIOD = 20;`, `RESET_CYCLES`, `TIMEOUT_NS`, `CHK_DLY`, `TIME_W`/`NAME_W`/`VAL_W`; mọi `wire` nối DUT và component (comment nguồn lái); biến các testcase dùng. Khai báo hết ở đây – file testcase không khai báo biến. |
| 2 | `DUT Instance` | `<m> u_dut (.port(net), ...);` nối theo tên, `#(.P(v))` nếu DUT có parameter. |
| 3 | `Clock Generation` | Instance `u_clk_rst` (clock/reset generator). |
| 4 | `Init Reset` | `task reset_dut`: driver về giá trị nghỉ ngay (`u_drv.drive_idle`), `u_clk_rst.apply_reset(RESET_CYCLES)`. Reset DUT và model (model theo `rst_n`); **không** đụng bộ đếm của logger. |
| 5 | `Golden Reference Model` | Instance `u_model`. |
| 6 | `Checker` | Đường quan sát → kết quả: instance `u_mon`, `u_chk`, `u_log`. |
| 7 | `Helper Functions` | `function` nhỏ của TB top thực sự dùng (thường trống; hàm căn cột ở trong logger). |
| 8 | `Tasks` | Đường stimulus: instance `u_drv`; task sequence dùng chung cho nhiều testcase (gọi task driver, vd. `cfg_timer`); `init_test` (`u_log.init`, bật checker, đọc plusarg) và `end_test` (`u_log.summary`, `$finish`). |
| 9 | `Main Program Body` | `` `include "run_test.v" `` (kịch bản của Item đang chạy) và `initial` timeout toàn cục (`u_log.error_msg("[TIMEOUT] …")`, `end_test`). |

Không viết code vô nghĩa để lấp một phần: phần không cần (thường là 7) chỉ giữ header.

## 4. Clock

- Mặc định **20 ns**: `parameter CLK_PERIOD = 20;`, truyền vào `u_clk_rst`. Spec của DUT quy định chu kỳ/tần số khác → dùng giá trị của spec cho TB đó.
- Trong `tb_<m>_clk_rst`: `clk_o` khởi tạo 0 trong `initial`, đảo bằng `always #(CLK_PERIOD / 2)` → cạnh lên đầu tiên ở `CLK_PERIOD/2`, không có cạnh lên ở thời điểm 0.

## 5. Thời điểm lái stimulus và lấy mẫu

**Luật bắt buộc – lái input DUT: chờ cạnh lên, trễ đúng `#1`, rồi gán** (trong task của driver):

```verilog
@(posedge clk_i);
#1;
din_o = 8'hA5;
```

- Áp dụng cho mọi lần lái input DUT trong chuỗi stimulus (kể cả trả input về giá trị nghỉ, và reset khi reset là input đồng bộ). Không lái ở `negedge`, không lái đúng tại `posedge`, không lái ngay trước `posedge`, không thay `#1` bằng trễ khác.
- `#1` chỉ thuộc testbench. Không bao giờ thêm trễ vào RTL, không sửa RTL để hợp với TB.
- Biến nội bộ của TB (model, bộ đếm, tên case) không cần theo luật này.
- Lấy mẫu output: monitor ở `negedge` (mục 2.1) – output thanh ghi đã cập nhật ở cạnh lên trước đó, output tổ hợp ứng với input đang giữ. Driver cần handshake (vd. `pready`) thì cũng đọc ở `negedge` trước khi quyết định chu kỳ tiếp theo.

## 6. Reset

- Theo spec của DUT (cực tính, đồng bộ/không đồng bộ). Không sửa hành vi reset của RTL.
- `reset_dut` khởi tạo rõ: mọi input DUT về giá trị nghỉ, reset tích cực, giữ `RESET_CYCLES` (mặc định 5) chu kỳ, rồi nhả. Model về trạng thái reset theo `rst_n` (reset bất đồng bộ: `always @(posedge clk_i or negedge rst_n_i)`).
- Reset **không đồng bộ**: tích cực ngay khi gọi (giữ ngữ nghĩa async), nhả bằng `@(posedge clk); #1;`.
- Reset **đồng bộ**: cả tích cực và nhả đều theo `@(posedge clk); #1;`.
- Testcase gọi `reset_dut` sau khi đã in header tới nhánh lá đầu tiên, để các check trong lúc reset thuộc nhánh đó. Reset giữa các nhánh con: gọi lại `reset_dut` (chỉ DUT/model); `init_test` (xóa bộ đếm) chỉ chạy một lần mỗi Item.

## 7. Self-check: model → checker → logger

- Hai loại check, cả hai đi qua checker → `u_log.result`:
  - **tự động**: mỗi mẫu hợp lệ của monitor, `exp_*` của model so với output DUT (`s_*`), khi checker đang bật (`u_chk.enable`). Tên case ghép từ input đã lấy mẫu (`rst_n_1_en_1_pulse_1_clr_0`).
  - **theo VPLAN**: `u_chk.expect_<x>(name, value)` – giá trị số trong Pass condition của nhánh lá so với mẫu monitor kế tiếp; task trả về sau khi đã so.
- Expected không bao giờ lấy từ output DUT (`expected = dut_out;` là sai).
- So bằng `===`/`!==`: X/Z ở actual hoặc expected là FAIL.
- `pass_count`, `fail_count` (`integer`) chỉ do logger sở hữu: `u_log.init` gán 0 (một lần mỗi Item, trong `init_test`), `u_log.result` tăng đúng một bộ đếm mỗi lần so, `u_log.error_msg` tăng `fail_count` cho lỗi không phải phép so (timeout, lỗi gọi header). PASS + FAIL = số dòng check + số `error_msg`.

### Định dạng log (chuẩn, `check_sim_log.py` và `sim/report.csh` đọc)

```text
[ITEM] <Item>
  [SUBITEM1] <Sub item 1>
    [SUBITEM2] <Sub item 2>
[<time>] <case> PASS | expected: <exp> | actual: <act>
[<time>] <case> FAIL | expected: <exp> | actual: <act>
[SUMMARY] PASS=<n> FAIL=<n>
Test_result: PASSED|FAILED
```

- Thứ tự: Item → Sub item 1 → Sub item 2 → các dòng check của nhánh lá đó. `[ITEM]` in một lần ở đầu log; `[SUBITEM1]` một lần khi bắt đầu nhóm, các `[SUBITEM2]` cùng cha nằm liên tiếp bên dưới; không in lại tên cha trước mỗi check.
- Nhánh một hoặc hai cấp chỉ in các cấp thực sự tồn tại (Item một cấp: `[ITEM]` rồi các dòng check).
- Đổi cha thì context con cũ bị xóa (logger: `item` xóa Sub item 1, `sub1` xóa Sub item 2); gọi `sub1` khi chưa có Item hay `sub2` khi chưa có Sub item 1 → logger in `[LOG ERROR] …` và tăng `fail_count`.
- Tên in đúng nguyên văn ô vplan (tiếng Anh, không dịch, không thay bằng ID). Danh sách đúng: `python3 .claude/skills/rtl-s5-tb/scripts/check_sim_log.py --items doc/vplan/<m>_vplan.<ext>`. Thụt lề header 0/2/4 khoảng trắng chỉ để đọc; dòng check không thụt lề.
- Mọi check nằm sau header của nhánh lá của nó – kể cả check tự động mỗi chu kỳ và check trong lúc reset/setup. Check nằm ở Item/Sub item 1 còn nhánh con, hoặc trước `[ITEM]`, là lỗi.
- Mỗi testcase chạy thành một log riêng `sim/log/<ID>.log` (transcript QuestaSim, mỗi dòng có tiền tố `# `).

### Căn cột

Mọi dòng check trong một log thẳng cột, dù tên case hay width giá trị khác nhau:

| Cột | Căn | Độ rộng (parameter của logger, truyền từ phần 1) |
| --- | --- | --- |
| `<time>` trong `[ ]` | phải | `TIME_W` chữ số (mặc định 8, đủ tới 99 999 999 ns) |
| `<case>` | trái, đệm khoảng trắng | `NAME_W` ký tự (mặc định 40; chọn ≥ tên case dài nhất của TB) |
| `PASS` / `FAIL` | – | 4 ký tự (cố định) |
| `<exp>`, `<act>` | phải | `VAL_W` chữ số hex = số chữ số `%h` của tín hiệu rộng nhất được so (vd. 64 bit → 16) |

- Hiện thực trong logger: task `result` và 3 hàm `str_len`, `pad_left`, `pad_right` (chuỗi `reg [8*64-1:0]`) – Verilog-2005 thuần, không dùng `%-40s`/`%8d` (độ rộng trường là mở rộng SystemVerilog).
- Checker tạo chuỗi giá trị bằng `$sformat(s, "%h", v)` (đủ chữ số theo width) rồi gọi `u_log.result`; không component nào tự `$display` dòng check.
- Tên case dài hơn `NAME_W` không bị cắt, chỉ dòng đó lệch – tăng `NAME_W` thay vì rút tên.
- Header `[ITEM]`/`[SUBITEM1]`/`[SUBITEM2]`, `[SUMMARY]`, `Test_result` không đệm cột.

Các trường:

- `[<time>]`: thời gian mô phỏng hiện tại, `$time` theo ns, căn phải `TIME_W` chữ số (`[      61]`).
- `<case>`: tên ngắn, không khoảng trắng, mô tả **đặc điểm input quan trọng** của case – `addr_0_wdata_A5A5A5A5`, `valid_1_ready_0`, `clr_1_en_1_pulse_1`. Không dùng tên vô nghĩa kiểu `CASE_001`, `TEST_01`. Ghép động bằng `$sformat`.
- `PASS`/`FAIL`: quyết định của checker. `expected`: model (check tự động) hoặc giá trị VPLAN (check theo VPLAN). `actual`: DUT qua monitor. In bằng `%h`, căn phải `VAL_W` chữ số.
- Dấu phân cách giữ nguyên `| expected: ... | actual: ...`.
- `[SUMMARY] PASS=<pass_count> FAIL=<fail_count>` in một lần cuối mô phỏng (`u_log.summary` trong `end_test`).
- `Test_result: PASSED` khi FAIL = 0 và PASS > 0, ngược lại `Test_result: FAILED`; in ngay sau `[SUMMARY]`. `sim/report.csh` lấy từ thứ ba của dòng này làm kết quả.

## 8. Testcase: một file mỗi Item

- `tc/<ID>.v` với `<ID>` = ID Item `TC_<M>_<NNN>` – ID thực thi dùng cho tên file, `make TESTNAME=<ID>`, `sim/pat.list`, `sim/log/<ID>.log`. Không tạo file riêng cho Sub item 1/Sub item 2 hay từng dòng vplan. Nhánh con truy vết bằng đường dẫn `<ID> › <Item> › <Sub item 1> › <Sub item 2>` (cùng tên lá dưới cha khác nhau được phân biệt bằng cha).
- Header comment: ID, tên Item, mục tiêu, cây nhánh con của Item theo vplan.
- Đúng **một** khối `initial` (luồng điều phối chính), thụt 2 khoảng trắng (nằm bên trong module TB): `init_test` → `u_log.item("<Item>")` → các nhóm nhánh → `end_test`. `init_test` và `end_test` chạy một lần cho cả Item.
- Mỗi Sub item 1 / Sub item 2 là một khối có tên `begin : <snake_case_name> ... end` theo cây vplan, theo đúng thứ tự vplan, mỗi cụm cùng cha liên tiếp. Lệnh đầu tiên của khối là header của nó (`u_log.sub1(...)`/`u_log.sub2(...)`), trước mọi lệnh tốn thời gian; khối chỉ chứa stimulus và check của nhánh đó.
- Kịch bản chỉ mô tả stimulus và giá trị VPLAN: gọi task của driver, clock/reset generator, `u_chk.expect_*`, header logger. Driver, monitor, model, checker và tiện ích nằm trong môi trường TB (`tb/`); không khai báo biến, không viết lại model/checker trong tc.
- Không chọn test bằng `+TEST`; test được chọn bằng `make TESTNAME=<ID>`.

## 9. Chọn test, timeout, waveform, dữ liệu file

- Chọn test bằng file: `make -C sim all TESTNAME=<ID>` chép `tc/<ID>.v` thành `sim/run_test.v`, biên dịch (`compile.f` → `rtl.f`, `tb.f`), chạy. Chạy cả danh sách: `cd sim && ./run.csh` (đọc `pat.list`), tổng hợp: `./report.csh`.
- Timeout toàn cục (vd. 100× số chu kỳ ước lượng) trong `initial` riêng ở phần 9: `u_log.error_msg("[TIMEOUT] ...")` rồi `end_test`.
- Waveform: `make run` ghi mọi tín hiệu (`log -r /*`) vào `sim/vsim.wlf`; `make wave` mở trong QuestaSim. TB không cần `$dumpfile`/`$dumpvars`.
- Dữ liệu từ file (khi vplan/spec dùng vector ngoài): input `doc/database/input/<m>_<tên>.txt`, tham chiếu `doc/database/output/<m>_<tên>.txt`. `init_test` đọc `+IN=`/`+OUT=`; mặc định là đường dẫn tương đối từ `sim/` (`"../doc/database/input/<m>_<tên>.txt"`), biến chuỗi `reg [8*256-1:0]`. Driver đọc vector input, model hoặc checker đọc vector tham chiếu. Đổi cặp file: `make all TESTNAME=<ID> DATA_IN=<file> DATA_OUT=<file>`. Script sinh dữ liệu: `sim/script/<m>_gen_vectors.py` (`make gen_data`). Không đặt dữ liệu hay script trong `tb/`, `tc/`.

## 10. Khung mẫu (DUT `pulse_cnt` 3 bit: `clr_i` → 0, `en_i & pulse_i` → +1)

Đã biên dịch và chạy qua `sim/Makefile` mẫu với QuestaSim 2021 (`Errors: 0, Warnings: 0`, 3 Item `PASSED`, `check_sim_log.py` `TẤT CẢ PASS`).

Vplan (`doc/vplan/pulse_cnt_vplan.md`, cây theo `--items`):

```text
TC_PULSE_CNT_001  [ITEM] Counting
                    [SUBITEM1] Enable control   [SUBITEM2] Count step | Hold value check
                    [SUBITEM1] Clear control    [SUBITEM2] Clear to zero | Clear priority | Hold value check
TC_PULSE_CNT_002  [ITEM] Boundary
                    [SUBITEM1] Wrap from max | Clear at max
TC_PULSE_CNT_003  [ITEM] Reset during counting
```

`sim/tb.f`:

```text
// Testbench file list, paths relative to sim/. Lines containing // are comments.
// Component modules tb/tb_<m>_<role>.v of every testbench, grouped by branch
// like rtl.f ("// --- <b> ---" + one file per line, S5 adds them), then the
// testbench top of the selected test (TB_NAME is exported by the Makefile).
// Example:
// --- my_module ---
// ../tb/tb_my_module_drv.v

// --- pulse_cnt ---
../tb/tb_pulse_cnt_clk_rst.v
../tb/tb_pulse_cnt_drv.v
../tb/tb_pulse_cnt_mon.v
../tb/tb_pulse_cnt_model.v
../tb/tb_pulse_cnt_chk.v
../tb/tb_pulse_cnt_log.v

../tb/${TB_NAME}.v
```

`tb/tb_pulse_cnt.v`:

```verilog
// ============================================================================
// Testbench : tb_pulse_cnt - self-checking direct testbench of pulse_cnt
// Vplan     : doc/vplan/pulse_cnt_vplan.md
// Test cases: tc/TC_PULSE_CNT_<NNN>.v, one per VPLAN Item, copied to
//             sim/run_test.v by "make build" and included in section 9
// Components (tb/, listed in sim/tb.f before this file):
//   u_clk_rst tb_pulse_cnt_clk_rst clock/reset generator -> clk, rst_n
//   u_drv     tb_pulse_cnt_drv     driver                -> en, pulse, clr
//   u_mon     tb_pulse_cnt_mon     monitor               -> s_* samples
//   u_model   tb_pulse_cnt_model   golden reference model-> exp_count
//   u_chk     tb_pulse_cnt_chk     checker               -> u_log.result
//   u_log     tb_pulse_cnt_log     logger, owns pass_count / fail_count
// Dataflow  : tc -> u_drv -> u_dut -> u_mon -> u_model -> u_chk -> u_log
//                                     u_mon --------------> u_chk
// ============================================================================
`timescale 1ns/1ps

module tb_pulse_cnt;

  // ============================================================
  // 1. Declaration
  // ============================================================
  parameter CLK_PERIOD   = 20;
  parameter RESET_CYCLES = 5;
  parameter TIMEOUT_NS   = 100000;
  // Checker sample point: falling edge + CHK_DLY
  parameter CHK_DLY      = 1;
  // Log columns: time digits, case-name width, value digits (widest %h)
  parameter TIME_W       = 8;
  parameter NAME_W       = 40;
  parameter VAL_W        = 1;

  wire            clk;         // u_clk_rst
  wire            rst_n;       // u_clk_rst
  wire            en;          // u_drv
  wire            pulse;       // u_drv
  wire            clr;         // u_drv
  wire [2:0]      count;       // u_dut
  wire            s_rst_n;     // u_mon
  wire            s_en;        // u_mon
  wire            s_pulse;     // u_mon
  wire            s_clr;       // u_mon
  wire [2:0]      s_count;     // u_mon
  wire            s_vld;       // u_mon
  wire [2:0]      exp_count;   // u_model
  reg  [8*64-1:0] msg;

  // ============================================================
  // 2. DUT Instance
  // ============================================================
  pulse_cnt u_dut (
    .clk_i   (clk),
    .rst_n_i (rst_n),
    .en_i    (en),
    .pulse_i (pulse),
    .clr_i   (clr),
    .count_o (count)
  );

  // ============================================================
  // 3. Clock Generation
  // ============================================================
  tb_pulse_cnt_clk_rst #(
    .CLK_PERIOD (CLK_PERIOD)
  ) u_clk_rst (
    .clk_o   (clk),
    .rst_n_o (rst_n)
  );

  // ============================================================
  // 4. Init Reset
  // ============================================================
  // DUT and model reset (model follows rst_n); log counters are kept
  task reset_dut;
    begin
      u_drv.drive_idle;
      u_clk_rst.apply_reset(RESET_CYCLES);
    end
  endtask

  // ============================================================
  // 5. Golden Reference Model
  // ============================================================
  tb_pulse_cnt_model u_model (
    .clk_i       (clk),
    .rst_n_i     (rst_n),
    .s_en_i      (s_en),
    .s_pulse_i   (s_pulse),
    .s_clr_i     (s_clr),
    .exp_count_o (exp_count)
  );

  // ============================================================
  // 6. Checker
  // ============================================================
  // Monitor -> checker (with model) -> logger
  tb_pulse_cnt_mon u_mon (
    .clk_i     (clk),
    .rst_n_i   (rst_n),
    .en_i      (en),
    .pulse_i   (pulse),
    .clr_i     (clr),
    .count_i   (count),
    .s_rst_n_o (s_rst_n),
    .s_en_o    (s_en),
    .s_pulse_o (s_pulse),
    .s_clr_o   (s_clr),
    .s_count_o (s_count),
    .s_vld_o   (s_vld)
  );

  tb_pulse_cnt_chk #(
    .CHK_DLY (CHK_DLY)
  ) u_chk (
    .clk_i       (clk),
    .s_rst_n_i   (s_rst_n),
    .s_en_i      (s_en),
    .s_pulse_i   (s_pulse),
    .s_clr_i     (s_clr),
    .s_count_i   (s_count),
    .s_vld_i     (s_vld),
    .exp_count_i (exp_count)
  );

  tb_pulse_cnt_log #(
    .TIME_W (TIME_W),
    .NAME_W (NAME_W),
    .VAL_W  (VAL_W)
  ) u_log ();

  // ============================================================
  // 7. Helper Functions
  // ============================================================

  // ============================================================
  // 8. Tasks
  // ============================================================
  // Stimulus driver, called by the test case
  tb_pulse_cnt_drv u_drv (
    .clk_i   (clk),
    .en_o    (en),
    .pulse_o (pulse),
    .clr_o   (clr)
  );

  // Once per Item, before its first header
  task init_test;
    begin
      u_log.init;
      u_chk.enable(1'b1);
    end
  endtask

  // Once per Item: summary, Test_result, end of simulation
  task end_test;
    begin
      u_log.summary;
      $finish;
    end
  endtask

  // ============================================================
  // 9. Main Program Body
  // ============================================================
  // Test sequence of the selected Item (tc/<ID>.v)
`include "run_test.v"

  initial begin
    #(TIMEOUT_NS);
    $sformat(msg, "[TIMEOUT] simulation exceeded %0d ns", TIMEOUT_NS);
    u_log.error_msg(msg);
    end_test;
  end

endmodule
```

`tb/tb_pulse_cnt_clk_rst.v`:

```verilog
// ============================================================================
// Component : tb_pulse_cnt_clk_rst - clock/reset generator of tb_pulse_cnt
// Drives    : clk_o, rst_n_o (only driver of both nets)
// Timing    : first rising edge at CLK_PERIOD / 2; rst_n_o is the active-low
//             asynchronous reset of the spec: asserted immediately, released
//             at posedge + #1
// Called by : tb_pulse_cnt (reset_dut) and the test case
// ============================================================================
`timescale 1ns/1ps

module tb_pulse_cnt_clk_rst #(
  parameter CLK_PERIOD = 20
) (
  output reg clk_o,
  output reg rst_n_o
);

  initial begin
    clk_o   = 1'b0;
    rst_n_o = 1'b0;
  end

  always #(CLK_PERIOD / 2) clk_o = ~clk_o;

  // Asynchronous assertion, effective now
  task assert_reset;
    begin
      rst_n_o = 1'b0;
    end
  endtask

  // Release at the next posedge + #1
  task release_reset;
    begin
      @(posedge clk_o);
      #1;
      rst_n_o = 1'b1;
    end
  endtask

  // Assert now, hold n rising edges, release at posedge + #1
  task apply_reset;
    input integer n;
    begin
      rst_n_o = 1'b0;
      repeat (n) begin
        @(posedge clk_o);
      end
      #1;
      rst_n_o = 1'b1;
    end
  endtask

endmodule
```

`tb/tb_pulse_cnt_drv.v`:

```verilog
// ============================================================================
// Component : tb_pulse_cnt_drv - stimulus driver of tb_pulse_cnt
// Drives    : en_o, pulse_o, clr_o -> DUT inputs (only driver of these nets)
// Timing    : every change at posedge + #1; values hold until the next call
// Called by : the test case (sequence) and reset_dut
// ============================================================================
`timescale 1ns/1ps

module tb_pulse_cnt_drv (
  input  wire clk_i,
  output reg  en_o,
  output reg  pulse_o,
  output reg  clr_o
);

  // Idle values without waiting for an edge (reset only)
  task drive_idle;
    begin
      en_o    = 1'b0;
      pulse_o = 1'b0;
      clr_o   = 1'b0;
    end
  endtask

  // Inputs of one clock cycle, applied at posedge + #1
  task cycle;
    input d_en;
    input d_pulse;
    input d_clr;
    begin
      @(posedge clk_i);
      #1;
      en_o    = d_en;
      pulse_o = d_pulse;
      clr_o   = d_clr;
    end
  endtask

  // n idle cycles
  task idle;
    input integer n;
    integer k;
    begin
      for (k = 0; k < n; k = k + 1) begin
        cycle(1'b0, 1'b0, 1'b0);
      end
    end
  endtask

endmodule
```

`tb/tb_pulse_cnt_mon.v`:

```verilog
// ============================================================================
// Component : tb_pulse_cnt_mon - monitor of tb_pulse_cnt
// Observes  : every DUT pin (inputs as really applied, outputs as produced)
// Drives    : s_*_o samples -> u_model (inputs), u_chk (inputs and outputs)
// Timing    : samples at every falling edge, half a cycle after the stimulus
//             of posedge + #1 and after the outputs have settled; the X->0
//             initialization of clk at time 0 is not an edge (s_vld_o = 0)
// ============================================================================
`timescale 1ns/1ps

module tb_pulse_cnt_mon (
  input  wire       clk_i,
  input  wire       rst_n_i,
  input  wire       en_i,
  input  wire       pulse_i,
  input  wire       clr_i,
  input  wire [2:0] count_i,
  output reg        s_rst_n_o,
  output reg        s_en_o,
  output reg        s_pulse_o,
  output reg        s_clr_o,
  output reg  [2:0] s_count_o,
  output reg        s_vld_o
);

  initial begin
    s_vld_o = 1'b0;
  end

  always @(negedge clk_i) begin
    if ($time > 0) begin
      s_vld_o   <= 1'b1;
      s_rst_n_o <= rst_n_i;
      s_en_o    <= en_i;
      s_pulse_o <= pulse_i;
      s_clr_o   <= clr_i;
      s_count_o <= count_i;
    end
  end

endmodule
```

`tb/tb_pulse_cnt_model.v`:

```verilog
// ============================================================================
// Component : tb_pulse_cnt_model - golden reference model of pulse_cnt
// Inputs    : clk, asynchronous reset, DUT inputs as sampled by u_mon
//             (never a DUT output)
// Drives    : exp_count_o -> u_chk
// Behavior  : from the spec: reset -> 0; clr_i = 1 -> 0 (priority);
//             en_i = 1 and pulse_i = 1 -> count + 1 modulo 8. The state
//             moves at the rising edge with the inputs the monitor sampled
//             in the cycle that ends at that edge.
// ============================================================================
`timescale 1ns/1ps

module tb_pulse_cnt_model (
  input  wire       clk_i,
  input  wire       rst_n_i,
  input  wire       s_en_i,
  input  wire       s_pulse_i,
  input  wire       s_clr_i,
  output reg  [2:0] exp_count_o
);

  integer next_val;

  always @(posedge clk_i or negedge rst_n_i) begin
    if (!rst_n_i) begin
      exp_count_o <= 3'd0;
    end
    else begin
      next_val = exp_count_o;
      if (s_clr_i) begin
        next_val = 0;
      end
      else if (s_en_i && s_pulse_i) begin
        next_val = (next_val + 1) % 8;
      end
      exp_count_o <= next_val;
    end
  end

endmodule
```

`tb/tb_pulse_cnt_chk.v`:

```verilog
// ============================================================================
// Component : tb_pulse_cnt_chk - checker of tb_pulse_cnt
// Inputs    : expected value from u_model, actual value and sampled inputs
//             from u_mon
// Results   : every comparison goes to tb_pulse_cnt.u_log.result
// Timing    : compares each valid monitor sample at falling edge + CHK_DLY
//             (sample and model output stable; stimulus only changes at
//             posedge + #1)
//   - automatic check: every cycle while enabled (model vs DUT)
//   - directed check : expect_count compares a VPLAN value with the next
//                      sample and returns after the comparison
// Ownership : auto_en (enable), dir_req/dir_name/dir_exp (expect_count),
//             dir_ack (compare process)
// ============================================================================
`timescale 1ns/1ps

module tb_pulse_cnt_chk #(
  parameter CHK_DLY = 1
) (
  input  wire       clk_i,
  input  wire       s_rst_n_i,
  input  wire       s_en_i,
  input  wire       s_pulse_i,
  input  wire       s_clr_i,
  input  wire [2:0] s_count_i,
  input  wire       s_vld_i,
  input  wire [2:0] exp_count_i
);

  reg             auto_en;
  integer         dir_req;
  integer         dir_ack;
  reg  [2:0]      dir_exp;
  reg  [8*64-1:0] dir_name;
  reg  [8*64-1:0] auto_name;
  reg  [8*64-1:0] exp_s;
  reg  [8*64-1:0] act_s;

  initial begin
    auto_en = 1'b0;
    dir_req = 0;
    dir_ack = 0;
  end

  // Turn the automatic per-cycle check on or off
  task enable;
    input on;
    begin
      auto_en = on;
    end
  endtask

  // Directed check of a VPLAN value against the next monitor sample
  task expect_count;
    input [8*64-1:0] name;
    input [2:0]      exp;
    begin
      dir_name = name;
      dir_exp  = exp;
      dir_req  = dir_req + 1;
      wait (dir_ack == dir_req);
    end
  endtask

  // === comparison: X/Z in actual or expected is a FAIL
  task compare;
    input [8*64-1:0] name;
    input [2:0]      exp;
    input [2:0]      act;
    begin
      $sformat(exp_s, "%h", exp);
      $sformat(act_s, "%h", act);
      tb_pulse_cnt.u_log.result(name, (act === exp), exp_s, act_s);
    end
  endtask

  always @(negedge clk_i) begin
    #(CHK_DLY);
    if (auto_en && s_vld_i) begin
      $sformat(auto_name, "rst_n_%b_en_%b_pulse_%b_clr_%b",
               s_rst_n_i, s_en_i, s_pulse_i, s_clr_i);
      compare(auto_name, exp_count_i, s_count_i);
    end
    if (s_vld_i && dir_ack != dir_req) begin
      compare(dir_name, dir_exp, s_count_i);
      dir_ack = dir_req;
    end
  end

endmodule
```

`tb/tb_pulse_cnt_log.v`:

```verilog
// ============================================================================
// Component : tb_pulse_cnt_log - logger / result collector of tb_pulse_cnt
// Owns      : pass_count, fail_count (only this module changes them)
// Called by : test case (item / sub1 / sub2 headers), u_chk (result),
//             tb_pulse_cnt (init, error_msg, summary)
// Log       : [ITEM] / [SUBITEM1] / [SUBITEM2] headers, aligned check lines,
//             [SUMMARY] and Test_result (check_sim_log.py, sim/report.csh)
// ============================================================================
`timescale 1ns/1ps

module tb_pulse_cnt_log #(
  parameter TIME_W = 8,
  parameter NAME_W = 40,
  parameter VAL_W  = 1
);

  integer         pass_count;
  integer         fail_count;
  reg  [8*64-1:0] cur_item;
  reg  [8*64-1:0] cur_sub1;

  // Once per Item (init_test); a DUT reset does not call it
  task init;
    begin
      pass_count = 0;
      fail_count = 0;
      cur_item   = 0;
      cur_sub1   = 0;
    end
  endtask

  // Branch headers; a new parent clears the context of its children
  task item;
    input [8*64-1:0] name;
    begin
      cur_item = name;
      cur_sub1 = 0;
      $display("[ITEM] %0s", name);
    end
  endtask

  task sub1;
    input [8*64-1:0] name;
    begin
      if (cur_item == 0) begin
        error_msg("[LOG ERROR] [SUBITEM1] without [ITEM]");
      end
      cur_sub1 = name;
      $display("  [SUBITEM1] %0s", name);
    end
  endtask

  task sub2;
    input [8*64-1:0] name;
    begin
      if (cur_sub1 == 0) begin
        error_msg("[LOG ERROR] [SUBITEM2] without [SUBITEM1]");
      end
      $display("    [SUBITEM2] %0s", name);
    end
  endtask

  // One aligned check line: [time] case PASS|FAIL | expected: exp | actual: act
  task result;
    input [8*64-1:0] name;
    input            pass;
    input [8*64-1:0] exp_str;
    input [8*64-1:0] act_str;
    reg   [8*64-1:0] t_str;
    begin
      if (pass) begin
        pass_count = pass_count + 1;
      end
      else begin
        fail_count = fail_count + 1;
      end
      $sformat(t_str, "%0d", $time);
      $display("[%0s] %0s %0s | expected: %0s | actual: %0s",
               pad_left(t_str, TIME_W), pad_right(name, NAME_W),
               pass ? "PASS" : "FAIL",
               pad_left(exp_str, VAL_W), pad_left(act_str, VAL_W));
    end
  endtask

  // Failure without a comparison (timeout, logging error)
  task error_msg;
    input [8*64-1:0] msg;
    begin
      fail_count = fail_count + 1;
      $display("%0s", msg);
    end
  endtask

  // Summary and overall result (read by sim/report.csh)
  task summary;
    begin
      $display("[SUMMARY] PASS=%0d FAIL=%0d", pass_count, fail_count);
      if (fail_count == 0 && pass_count > 0) begin
        $display("Test_result: PASSED");
      end
      else begin
        $display("Test_result: FAILED");
      end
    end
  endtask

  // Number of characters of a string held in reg [8*64-1:0]
  function integer str_len;
    input [8*64-1:0] s;
    integer          k;
    begin
      str_len = 0;
      for (k = 0; k < 64; k = k + 1) begin
        if (s[8*k +: 8] != 8'h0) begin
          str_len = k + 1;
        end
      end
    end
  endfunction

  // s right-aligned in a field of w characters
  function [8*64-1:0] pad_left;
    input [8*64-1:0] s;
    input integer    w;
    integer          k;
    begin
      pad_left = s;
      for (k = str_len(s); k < w; k = k + 1) begin
        pad_left[8*k +: 8] = " ";
      end
    end
  endfunction

  // s left-aligned in a field of w characters
  function [8*64-1:0] pad_right;
    input [8*64-1:0] s;
    input integer    w;
    integer          k;
    begin
      pad_right = s;
      for (k = str_len(s); k < w; k = k + 1) begin
        pad_right = {pad_right[8*63-1:0], 8'h20};
      end
    end
  endfunction

endmodule
```

`tc/TC_PULSE_CNT_001.v` (Item ba cấp; `Hold value check` dưới hai cha khác nhau):

```verilog
// ============================================================================
// TC_PULSE_CNT_001 - Counting
// Objective: count enable, hold and clear behavior (VPLAN Item "Counting")
//   Enable control > Count step, Hold value check
//   Clear control  > Clear to zero, Clear priority, Hold value check
// Copied to sim/run_test.v and included inside tb_pulse_cnt.
// ============================================================================
  initial begin
    init_test;
    u_log.item("Counting");
    begin : enable_control
      u_log.sub1("Enable control");
      begin : count_step
        u_log.sub2("Count step");
        reset_dut;
        u_drv.cycle(1'b1, 1'b1, 1'b0);
        u_drv.cycle(1'b1, 1'b1, 1'b0);
        u_drv.cycle(1'b1, 1'b1, 1'b0);
        u_drv.idle(1);
        u_chk.expect_count("after_3_pulses", 3'd3);
      end
      begin : hold_value_check
        u_log.sub2("Hold value check");
        u_drv.cycle(1'b0, 1'b1, 1'b0);
        u_drv.cycle(1'b1, 1'b0, 1'b0);
        u_drv.idle(1);
        u_chk.expect_count("en_0_or_pulse_0_hold_3", 3'd3);
      end
    end
    begin : clear_control
      u_log.sub1("Clear control");
      begin : clear_to_zero
        u_log.sub2("Clear to zero");
        u_drv.cycle(1'b0, 1'b0, 1'b1);
        u_drv.idle(1);
        u_chk.expect_count("clr_1_from_3", 3'd0);
      end
      begin : clear_priority
        u_log.sub2("Clear priority");
        u_drv.cycle(1'b1, 1'b1, 1'b0);
        u_drv.cycle(1'b1, 1'b1, 1'b1);
        u_drv.idle(1);
        u_chk.expect_count("clr_1_en_1_pulse_1", 3'd0);
      end
      begin : hold_value_check
        u_log.sub2("Hold value check");
        u_drv.idle(2);
        u_chk.expect_count("idle_after_clear", 3'd0);
      end
    end
    end_test;
  end
```

`tc/TC_PULSE_CNT_002.v` (Item hai cấp; reset DUT/model giữa hai nhánh, bộ đếm giữ nguyên):

```verilog
// ============================================================================
// TC_PULSE_CNT_002 - Boundary
// Objective: wrap from 7 to 0 and clear at the maximum value
//   Wrap from max, Clear at max (two levels)
// Copied to sim/run_test.v and included inside tb_pulse_cnt.
// ============================================================================
  initial begin
    init_test;
    u_log.item("Boundary");
    begin : wrap_from_max
      u_log.sub1("Wrap from max");
      reset_dut;
      repeat (7) begin
        u_drv.cycle(1'b1, 1'b1, 1'b0);
      end
      u_drv.idle(1);
      u_chk.expect_count("after_7_pulses", 3'd7);
      u_drv.cycle(1'b1, 1'b1, 1'b0);
      u_drv.idle(1);
      u_chk.expect_count("pulse_at_7_wraps", 3'd0);
    end
    begin : clear_at_max
      u_log.sub1("Clear at max");
      reset_dut;
      repeat (7) begin
        u_drv.cycle(1'b1, 1'b1, 1'b0);
      end
      u_drv.cycle(1'b1, 1'b1, 1'b1);
      u_drv.idle(1);
      u_chk.expect_count("clr_1_at_7", 3'd0);
    end
    end_test;
  end
```

`tc/TC_PULSE_CNT_003.v` (Item một cấp; reset bất đồng bộ giữa lúc đếm):

```verilog
// ============================================================================
// TC_PULSE_CNT_003 - Reset during counting
// Objective: asynchronous reset clears the count while counting (one level)
// Copied to sim/run_test.v and included inside tb_pulse_cnt.
// ============================================================================
  initial begin
    init_test;
    u_log.item("Reset during counting");
    reset_dut;
    u_drv.cycle(1'b1, 1'b1, 1'b0);
    u_drv.cycle(1'b1, 1'b1, 1'b0);
    u_clk_rst.assert_reset;
    u_chk.expect_count("rst_n_0_en_1_pulse_1", 3'd0);
    u_clk_rst.release_reset;
    u_drv.idle(1);
    u_chk.expect_count("first_pulse_after_release", 3'd1);
    end_test;
  end
```

`sim/log/TC_PULSE_CNT_001.log` (bỏ tiền tố `# ` và các dòng của QuestaSim):

```text
[ITEM] Counting
  [SUBITEM1] Enable control
    [SUBITEM2] Count step
[      21] rst_n_0_en_0_pulse_0_clr_0               PASS | expected: 0 | actual: 0
[      41] rst_n_0_en_0_pulse_0_clr_0               PASS | expected: 0 | actual: 0
[      61] rst_n_0_en_0_pulse_0_clr_0               PASS | expected: 0 | actual: 0
[      81] rst_n_0_en_0_pulse_0_clr_0               PASS | expected: 0 | actual: 0
[     101] rst_n_1_en_0_pulse_0_clr_0               PASS | expected: 0 | actual: 0
[     121] rst_n_1_en_1_pulse_1_clr_0               PASS | expected: 0 | actual: 0
[     141] rst_n_1_en_1_pulse_1_clr_0               PASS | expected: 1 | actual: 1
[     161] rst_n_1_en_1_pulse_1_clr_0               PASS | expected: 2 | actual: 2
[     181] rst_n_1_en_0_pulse_0_clr_0               PASS | expected: 3 | actual: 3
[     181] after_3_pulses                           PASS | expected: 3 | actual: 3
    [SUBITEM2] Hold value check
[     201] rst_n_1_en_0_pulse_1_clr_0               PASS | expected: 3 | actual: 3
[     221] rst_n_1_en_1_pulse_0_clr_0               PASS | expected: 3 | actual: 3
[     241] rst_n_1_en_0_pulse_0_clr_0               PASS | expected: 3 | actual: 3
[     241] en_0_or_pulse_0_hold_3                   PASS | expected: 3 | actual: 3
  [SUBITEM1] Clear control
    [SUBITEM2] Clear to zero
[     261] rst_n_1_en_0_pulse_0_clr_1               PASS | expected: 3 | actual: 3
[     281] rst_n_1_en_0_pulse_0_clr_0               PASS | expected: 0 | actual: 0
[     281] clr_1_from_3                             PASS | expected: 0 | actual: 0
    [SUBITEM2] Clear priority
[     301] rst_n_1_en_1_pulse_1_clr_0               PASS | expected: 0 | actual: 0
[     321] rst_n_1_en_1_pulse_1_clr_1               PASS | expected: 1 | actual: 1
[     341] rst_n_1_en_0_pulse_0_clr_0               PASS | expected: 0 | actual: 0
[     341] clr_1_en_1_pulse_1                       PASS | expected: 0 | actual: 0
    [SUBITEM2] Hold value check
[     361] rst_n_1_en_0_pulse_0_clr_0               PASS | expected: 0 | actual: 0
[     381] rst_n_1_en_0_pulse_0_clr_0               PASS | expected: 0 | actual: 0
[     381] idle_after_clear                         PASS | expected: 0 | actual: 0
[SUMMARY] PASS=24 FAIL=0
Test_result: PASSED
```

## 11. Môi trường `sim/` (dùng chung cho mọi module)

Mẫu ở `references/sim_env/` (`init_project` chép sẵn vào `sim/` khi tạo project); S5 chép file nào chưa có trong `sim/`, không ghi đè bản đã có; `rtl.f`, `tb.f`, `pat.list` được S5 cập nhật dòng của module.

| File | Nội dung |
| --- | --- |
| `Makefile` | QuestaSim 2021: `build`, `run`, `all`/`all_wave`/`all_cov` (luôn `clean_sim` trước), `wave`, `build_cov`, `run_cov` (chỉ lưu `<ID>.ucdb`, không report riêng từng test), `gen_cov`/`gen_html` (dựng lại `IP.ucdb` từ đầu chỉ từ `<ID>.ucdb` của các test trong `pat.list`, không gộp `IP.ucdb` cũ, rồi áp `exclude.do` lên `IP.ucdb`), `cov_gui` (GUI coverage trên `IP.ucdb`, exclusion sửa trong GUI được ghi lại vào `exclude.do` khi thoát), `clean_sim` (file tạm của một lần chạy, giữ `*.ucdb`, `coverage/`), `clean` (xóa hết, kể cả coverage), `lint` (compile `rtl.f` không cần TB, `TOP=<m>` elaborate cây `<m>` – dùng ở S3), `help`; Vivado: `schematic` (`SCH=<instance>`, `PART=<device>`); `gen_data`. `vlog`/`vsim` lỗi → `make` dừng, in lại mọi dòng `** Error`/`** Fatal` (file, dòng) trong khối `ERRORS` ở cuối, và ghi log lỗi vào `log/<ID>.log` (không để log PASS cũ). `TESTNAME` mặc định = dòng đầu `pat.list`; `MODULE` suy ra từ `TESTNAME` (`TC_<M>_<NNN>` → `<m>`), `TB_NAME = tb_<m>`. |
| `compile.f` | `-timescale 1ns/1ps`, `+incdir+.`, `-f rtl.f`, `-f tb.f`. |
| `rtl.f` | Mọi file `rtl/*.v`, module con trước module cha, dạng `../rtl/<file>.v`. Dòng chứa `//` là comment. S1 ghi sẵn mọi module ở dạng comment, nhóm theo nhánh (`// --- <b> ---`, cách nhau một dòng trống); S3 bỏ comment `rtl/<m>.v` khi viết RTL; S5 bỏ comment/thêm file còn thiếu của cây `<m>`. |
| `tb.f` | File component `../tb/tb_<m>_<role>.v` của mọi testbench, nhóm theo nhánh (`// --- <b> ---`, S5 thêm nhóm của `<m>`; thứ tự trong nhóm: clk_rst, driver, monitor, model, checker, logger), rồi dòng cuối `../tb/${TB_NAME}.v` (QuestaSim thay biến môi trường do Makefile export). Mọi component được biên dịch mỗi lần build (như `rtl.f`); chỉ TB top của test đang chạy được include `run_test.v`. TB cũ không có component không cần dòng nào. |
| `pat.list` | ID Item, mỗi dòng một ID; dòng chứa `//` bị bỏ qua. S1 ghi sẵn dòng mở đầu `// --- <b> ---` của mọi nhóm nhánh; S5 thêm ID Item của `<m>` vào nhóm của nó. |
| `run.csh` / `report.csh` | Chạy hết `pat.list` (`./run.csh`; `./run.csh cov` chạy `make clean` một lần trước để regression coverage bắt đầu từ đầu) / bảng PAT_NAME – RUN_DATE – RESULT từ `log/<ID>.log` (`End time`, `Test_result`; log không có `Test_result` – build/load lỗi – là `ERROR`). Cần `tcsh`. |
| `schematic.tcl` | Vivado: đọc `rtl.f`, `synth_design -rtl -top <m>`, mở schematic. |
| `cov_excl.tcl` | Tcl cho `merge_cov`/`cov_gui`: `excl_load` (áp `exclude.do`), `excl_save` (ghi mọi exclusion hiện có kèm comment vào `exclude.do`, đường dẫn tương đối), `excl_autosave` (gọi `excl_save` khi vsim thoát). |
| `exclude.do` | Không có trong mẫu: do `make cov_gui` sinh ra từ exclusion của người dùng (lệnh `coverage exclude … -comment …`), được commit. Chỉ áp lên `IP.ucdb` tổng – mục tiêu coverage là của DUT trên `IP.ucdb`, không phải từng test; coverage của testbench không quan tâm, không exclude. S5 không tạo/sửa file này. |

Đầu ra mô phỏng (`work/`, `lint_work/`, `log/`, `*.log`, `*.wlf`, `vsim.dbg`, `modelsim.ini`, `*.ucdb`, `coverage/`, `covhtmlreport/`, `run_test.v`, `.Xil/`) là file sinh ra, không phải tài liệu cần giữ; `make clean` xóa phần lớn.

Mọi lần biên dịch/mô phỏng (S3 `lint`, S5 `all`/`all_cov`/`run.csh`) đều chạy qua `sim/Makefile`; skill đọc `sim/` trước và không tự gõ lệnh simulator. Không có QuestaSim → không chạy, báo lệnh. File `.v` biên dịch ở chế độ Verilog: lỗi cú pháp do construct SV → sửa TB, không chuyển TB sang SystemVerilog. RTL module con cũ còn `.sv` → báo trong báo cáo, không tự viết lại RTL.

# Rule testbench mặc định (chỉ dùng cho chỗ tb_coding_rules/ không nói tới)

Mục tiêu: testbench direct, tự kiểm, mô phỏng tất định, đọc được ở mức sinh viên, gồm các component có kết nối thật. **Mọi expected dùng để kết luận PASS/FAIL do golden model tính.** Log ngắn, cô đọng: đọc cùng spec là thấy ngay đang kiểm chức năng gì, TB đã tác động gì lên DUT và khi nào, checkpoint nào sai đầu tiên (mục 7); model tính mọi expected bên trong nhưng không in diễn giải. Không UVM, class, SystemVerilog interface/package, SVA, coverage, random, framework scoreboard.

## 1. Ngôn ngữ và file

- **Verilog-2005 (IEEE 1364-2005)**. Ba loại file, đều chỉ là mã HDL, đặt phẳng:
  - `tb/tb_<m>.v`, module top `tb_<m>`: nối DUT với các component, helper trình bày log, task sequence dùng chung, cấu trúc 9 phần (mục 3).
  - `tb/tb_<m>_<role>.v`, module `tb_<m>_<role>`: một component của môi trường (mục 2). Tiền tố `tb_<m>_` tránh trùng tên giữa các DUT và với module RTL; không đặt tên trùng một module trong `rtl/`.
  - `tc/<ID>.v`, một file mỗi **Item cấp cao nhất** của vplan (`<ID>` = ID Item `TC_<M>_<NNN>`): kịch bản stimulus của mọi nhánh con của Item, được `make build` chép thành `sim/run_test.v` và include vào phần 9 của TB top (mục 8).
- Phải là cú pháp Verilog-2005 thật – không phải đổi đuôi một file SystemVerilog.
- Dùng: `reg`, `wire`, `integer`, `time`, `parameter`, `localparam`, `module`/port ANSI, `always`, `initial`, `task`, `function`, `if`, `case`, `for`, `while`, `repeat`, `wait`, khối có tên `begin : <name>`, `$display`, `$sformat`, `$value$plusargs`, `$test$plusargs`, `$fopen`/`$fgets`/`$sscanf` (khi đọc file dữ liệu), `$finish`, `` `include ``, gọi task/function theo tên phân cấp (`u_drv.apb_write(...)`, `tb_<m>.u_log.fmt_hex(...)`).
- **Cấm** (SystemVerilog): `logic`, `bit`, `byte`, `int`, `string`, `always_ff`, `always_comb`, `always_latch`, `typedef`, `enum`, `struct`, `union`, `interface`/`modport`, `package`/`import`, `class`, `virtual`, `foreach`, queue, mảng động, `mailbox`, `assert`/`property` (SVA), cast `type'(...)`, literal `'0`/`'1`, `$fatal`, `++`/`+=`, khai báo biến trong `for` (`for (int i …)`). `event` là từ khóa – không đặt tên task là `event`.
- Chuỗi: tên nhánh/tag `reg [8*64-1:0]`, giá trị đã định dạng `reg [8*80-1:0]`, nội dung một dòng log `reg [8*200-1:0]` (dài hơn → tăng độ rộng thống nhất ở mọi nơi); ghép bằng `$sformat`; in bằng `%0s`.
- `` `timescale 1ns/1ps `` đầu mỗi file `tb/`.
- Comment, tên task/function/tín hiệu, chuỗi in và log chỉ dùng tiếng Anh.
- Danh sách biên dịch: `sim/tb.f` liệt kê mọi file component theo nhóm nhánh (`// --- <b> ---`, như `rtl.f`), component trước, dòng cuối `../tb/${TB_NAME}.v` (mục 11).

## 2. Kiến trúc môi trường: component và kết nối

Luồng dữ liệu:

```text
tc/<ID>.v ──task (stimulus only)──> TB top sequence tasks ──> u_drv ──wire──> u_dut ──wire──> u_mon
                                          │ u_chk.sync                   ^                        │ s_*, s_time,
                                          │            u_clk_rst ─clk/rst_n/clk_cnt                │ s_done, s_wait, s_setup
                                          │                              └──> u_model <────────────┤ inputs only
                                          │                                     │ exp_*            │ outputs (actual)
       tc ──task (headers, goal)──> u_log <──check/info── u_chk <───────────────┴──────────────────┘
                                      ^
                                      └──info── u_clk_rst ([RESET]), u_drv ([DRIVE], [WAIT], [TIMEOUT]), u_mon ([OBSERVE])
```

| Vai trò | Instance | Module | Nhận | Lái / tạo ra | Log (qua `u_log`) |
| --- | --- | --- | --- | --- | --- |
| Test sequence / controller | (khối `initial` của tc) | `tc/<ID>.v` | – | gọi task sequence của TB top (chỉ stimulus), `reset_dut`, `u_log.item/sub1/sub2/goal` | header nhánh, một `[GOAL]` ngắn |
| Clock/reset generator | `u_clk_rst` | `tb_<m>_clk_rst` | – | `clk`, `rst_n`, `clk_cnt` (số cạnh lên từ đầu mô phỏng, không bao giờ reset; driver duy nhất) | `[RESET]` lúc assert và lúc release |
| Protocol driver | `u_drv` | `tb_<m>_drv` | `clk`, `clk_cnt`, handshake DUT nếu giao thức cần (vd. `pready`) | mọi input DUT trừ clock/reset | input ngoài bus khi thật sự đổi `[DRIVE] <sig>: cũ -> mới`, `[WAIT] n cycles` (khi chờ có nghĩa với kịch bản), `[TIMEOUT]`; không log từng pha bus |
| Monitor | `u_mon` | `tb_<m>_mon` | `clk_cnt`, mọi chân DUT (input đã thực sự áp + output) | mẫu `s_*`, `s_vld`, thời điểm mẫu `s_time`; trạng thái giao dịch quan sát được (`s_done`, `s_wait`, `s_setup` = `clk` của pha setup) | `[OBSERVE] <output>: cũ -> mới` cho output có cạnh quan trọng (vd. ngắt) |
| Golden reference model | `u_model` | `tb_<m>_model` | `clk`, `rst_n`, mẫu **input** của monitor | `exp_*`; tối đa một hàm trả tên quy tắc cho chú thích của dòng FAIL (vd. `err_text`) | không in gì |
| Checker | `u_chk` | `tb_<m>_chk` | `exp_*` (model), mẫu output, `s_time` và trạng thái giao dịch (monitor) | quyết định PASS/FAIL, gọi `u_log.check` | mỗi giao dịch một dòng lúc hoàn tất, `[WATCH]` khi lệch, `[CHECK]` theo checkpoint; FAIL mang ngữ cảnh ngắn ngay trên cùng dòng |
| Logger / result collector | `u_log` | `tb_<m>_log` | `clk_cnt` | định dạng thống nhất, sở hữu `pass_count`/`fail_count` | mọi dòng, `[SUMMARY]`, `Test_result` |
| DUT | `u_dut` | `<m>` | input từ `u_drv`, `u_clk_rst` | output → `u_mon` (và handshake → `u_drv`) | – |

Luật kết nối:

- **Dữ liệu mức chân đi qua port/wire thật** khai báo ở phần 1 của TB top: driver → DUT, DUT → monitor, monitor → model, model + monitor → checker. Mỗi `wire` có đúng một nguồn lái (một output port); ghi nguồn bằng comment cạnh khai báo (`// u_drv`). Không component nào gán lên tín hiệu do component khác lái; không đọc tín hiệu nội bộ của DUT, không `force`/`deposit`.
- **Lời gọi mức giao dịch dùng task qua tên instance của TB top**: sequence → task sequence của TB top → `u_drv.<task>` + `u_chk.sync`; `u_chk` → `u_model.err_text`; mọi component → `tb_<m>.u_log.info/check/error_msg` và hàm định dạng `tb_<m>.u_log.fmt_*`. Mỗi cặp chỉ một chiều gọi; ghi trong header của component.
- **Mỗi thao tác được kể đúng một dòng, bởi component biết kết quả của nó**: giao dịch bus do checker kể lúc hoàn tất (addr, data, strb và kết quả trên cùng dòng), input ngoài bus do driver kể lúc áp, reset do `u_clk_rst`. Model tính âm thầm (không dòng diễn giải). Không log một thao tác chưa thực sự xảy ra (vd. "write applied" khi mới phát request hoặc transfer bị từ chối).
- **Sở hữu biến**: mỗi `reg` có một process sở hữu rõ ràng; cờ handshake giữa hai process dùng cặp bộ đếm request/ack (mỗi process sở hữu một bộ đếm, vd. `sync_req`/`sync_ack`), không để hai process cùng gán một biến.
- Component nhỏ, chỉ chứa đúng vai trò của nó; không cần cấu trúc 9 phần. Mỗi file có header comment: tên, vai trò, port nhận/lái, timing, log nào, ai gọi task nào, biến nào thuộc ai.
- Mặc định mỗi vai trò một module. Không tạo module rỗng hay chỉ chuyển tiếp tín hiệu để đủ số: vai trò không có ở DUT thì bỏ (vd. DUT tổ hợp không clock/reset → không có `u_clk_rst`, monitor lấy mẫu theo một strobe do sequence tạo, ghi rõ trong header TB). DUT có nhiều giao thức độc lập (vd. APB + bus dữ liệu) → một driver/monitor cho mỗi giao thức (`tb_<m>_apb_drv`, `tb_<m>_apb_mon`…); vài input sideband đơn giản (vd. `dbg_mode`) do driver chính lái.

### 2.1 Timing trong một chu kỳ và bộ đếm clock

`clk_cnt` (do `u_clk_rst` lái) = số cạnh lên của clock kể từ thời điểm 0: khởi tạo 0 một lần ở đầu mô phỏng, +1 ở mỗi cạnh lên (gán nonblocking: process cùng thức dậy ở cạnh đó vẫn đọc giá trị cũ), **không bao giờ reset** – không bởi reset DUT, `init_test`, đổi Item/Sub item hay kịch bản mới. Đây không phải số chu kỳ kể từ khi bật counter. Mọi component dùng chung nguồn này.

| Thời điểm | Việc |
| --- | --- |
| `posedge` | DUT và model cập nhật trạng thái (model dùng mẫu input của chu kỳ vừa kết thúc ở cạnh này); `clk_cnt` + 1 |
| `posedge + #1` | driver đổi input DUT (log `[DRIVE]`/`[WAIT]` với thời điểm này); `u_clk_rst` nhả reset |
| `negedge` | monitor lấy mẫu mọi chân DUT, ghi `s_time = $time` (`s_vld = 1` từ cạnh xuống thật đầu tiên – lần `clk` X→0 ở thời điểm 0 không phải cạnh) |
| `negedge + CHK_DLY` | checker so với model và log **với thời điểm mẫu `s_time`** (không phải lúc in); sau đó `u_chk.sync` trả về |

- `CHK_DLY = 1` (parameter) < nửa chu kỳ: lúc đó mẫu monitor và output tổ hợp của model đã ổn định, stimulus chưa đổi. Không có race giữa model và checker. Giữa `negedge` và lúc in không có cạnh lên, nên `clk` của dòng bằng `clk` lúc lấy mẫu.
- Reset bất đồng bộ được phép tích cực giữa chu kỳ (thường ngay sau `negedge + CHK_DLY` hoặc `posedge + #1`), không đúng tại `negedge`…`negedge + CHK_DLY`.
- **Mọi task sequence của TB top kết thúc bằng `u_chk.sync`** (trả về sau khi checker đã xử lý mẫu cuối của task). Vì vậy header nhánh in ngay sau một task sequence, hoặc trước stimulus đầu tiên, luôn đứng trước mọi check của nhánh đó.
- Mỗi task chiếm trọn các chu kỳ của nó và trả về ở `negedge` của chu kỳ cuối; task kế tiếp lái ở `posedge + #1` ngay sau đó (giao dịch nối tiếp không có chu kỳ nghỉ chen vào). Một input ngoài bus (`set_dbg_mode(v)`) đổi ở điểm lái hợp lệ gần nhất sau thao tác trước, bus nghỉ trong chu kỳ đó.

### 2.2 Nguồn expected: chỉ golden model

- **Mọi expected dùng để kết luận PASS/FAIL do model tự viết, độc lập, theo spec tính ra.** Testcase không truyền giá trị expected nào; checker không có task nhận expected literal (không `expect_rdata(name, 32'h…)`, không `expect_count(…, 3'd3)`). Giá trị trong `Pass condition` của vplan không bao giờ là expected thay thế.
- **Vplan quyết định chức năng cần test, phân nhóm Item/Sub item và kịch bản stimulus** (Test sequence: thanh ghi, data, strobe, số chu kỳ chờ, thời điểm đổi input). Bỏ cơ chế so literal VPLAN không làm bỏ testcase hay giảm phạm vi: mọi nhánh lá vẫn được hiện thực, mọi đại lượng `Pass condition` nêu vẫn được quan sát (qua giao dịch, watch từng mẫu hoặc checkpoint) – chỉ expected đổi nguồn.
- **Pass condition dùng để soát model** khi viết TB: so `expected` trong log với số của vplan. Khác nhau → đối chiếu spec: model sai → sửa model; vplan sai → báo (S4), không chép số vplan vào TB để "cho qua".
- Cần kiểm một thời điểm cụ thể → testcase chỉ **yêu cầu checkpoint** (đại lượng/giao dịch và thời điểm, vd. một lần đọc thanh ghi, hoặc `wait_cycles(n)` rồi `u_chk.checkpoint("<what>")` cho output không thuộc giao dịch); checker lấy expected tương ứng từ model tại đúng mẫu đó.
- Hằng số reset, mask thanh ghi, công thức, latency… được phép có trong model khi có căn cứ ở spec (ghi nguồn trong header model).
- **Model không đọc output DUT, không đọc trạng thái nội bộ DUT, không chép RTL** (viết theo câu chữ của spec: bảng thanh ghi, công thức, mô tả hành vi). Model cập nhật theo clock/reset và stimulus **thực tế đã áp** (mẫu input của monitor), không theo lời gọi task.
- **Phân biệt request với giao dịch đã được chấp nhận**: model áp một lệnh ghi khi chính model dự đoán giao dịch hoàn tất và được chấp nhận theo spec (vd. chu kỳ access cuối, không lỗi) – không phải lúc driver phát request.
- **Handshake**: nếu spec định nghĩa latency (vd. APB một wait state), model tự dự đoán handshake (`exp_pready`) và checker kiểm handshake thật của DUT riêng (timing, số wait cycle) – DUT trả handshake sai thì FAIL ở đúng chu kỳ đó. Nếu spec không định nghĩa latency, model chỉ dùng handshake thật để biết *khi nào*, và checker vẫn kiểm riêng tính hợp lệ của handshake theo giao thức (đúng pha, có giới hạn chờ `MAX_WAIT` → `[TIMEOUT]`); ghi lý do trong header model. Không để model "đi theo" lỗi DUT rồi vẫn PASS.
- **Không đồng bộ lại model từ DUT**: giá trị DUT đọc sai không bao giờ được nạp lại vào model để che sai lệch – model giữ dự đoán của nó, các check sau tiếp tục so với dự đoán đó.
- Spec thiếu thông tin để tính một expected → báo thiếu (đề xuất OPEN cho S1), không lấy số trong vplan để lấp; nhánh đó ghi rõ trong báo cáo.
- So bằng `===`/`!==`: X/Z ở actual hoặc expected là FAIL.

## 3. TB top `tb/tb_<m>.v` – cấu trúc 9 phần, đúng thứ tự

Mỗi phần mở bằng header như sau, giữ đủ 9 header kể cả khi TB nhỏ:

```verilog
// ============================================================
// 1. Declaration
// ============================================================
```

| # | Header | Nội dung |
| --- | --- | --- |
| 1 | `Declaration` | `parameter CLK_PERIOD = 20;`, `RESET_CYCLES`, `TIMEOUT_NS`, `CHK_DLY`, `MAX_WAIT` (nếu có handshake), cột log `TIME_W`/`CLK_W`/`TAG_W`/`VAL_W`; địa chỉ thanh ghi; mọi `wire` nối DUT và component (comment nguồn lái); biến các task sequence dùng. Khai báo hết ở đây – file testcase không khai báo biến. |
| 2 | `DUT Instance` | `<m> u_dut (.port(net), ...);` nối theo tên, `#(.P(v))` nếu DUT có parameter. |
| 3 | `Clock Generation` | Instance `u_clk_rst` (clock/reset generator, cả `clk_cnt`). |
| 4 | `Init Reset` | `task reset_dut`: driver về giá trị nghỉ ngay (`u_drv.drive_idle`), `u_clk_rst.apply_reset(RESET_CYCLES)`, `u_chk.sync`. Reset DUT và model (model theo `rst_n`); **không** đụng bộ đếm của logger hay `clk_cnt`. Output trong lúc reset vẫn được watch so với model. |
| 5 | `Golden Reference Model` | Instance `u_model`. |
| 6 | `Checker` | Đường quan sát → kết quả: instance `u_mon`, `u_chk`, `u_log`. |
| 7 | `Helper Functions` | Hàm **trình bày** dùng chung cho log (vd. `reg_name(addr)`, `field_names(addr, mask)` theo register map) – không chứa logic kiểm. Trống nếu DUT không cần. |
| 8 | `Tasks` | Đường stimulus: instance `u_drv`; **task sequence** cho testcase (chỉ stimulus, kết thúc bằng `u_chk.sync`: vd. `apb_write`, `apb_read`, `set_dbg_mode(v)`, `wait_cycles(n)`); `init_test(id, objective)` (`u_log.init`, các dòng `[TEST]`, plusarg) và `end_test` (`u_log.summary`, `$finish`). |
| 9 | `Main Program Body` | `` `include "run_test.v" `` (kịch bản của Item đang chạy) và `initial` timeout toàn cục (`u_log.error_msg($time, "TIMEOUT", …)`, `end_test`). |

Không viết code vô nghĩa để lấp một phần: phần không cần chỉ giữ header.

## 4. Clock

- Mặc định **20 ns**: `parameter CLK_PERIOD = 20;`, truyền vào `u_clk_rst` (và dùng cho dòng `[TEST] Time`). Spec của DUT quy định chu kỳ/tần số khác → dùng giá trị của spec cho TB đó.
- Trong `tb_<m>_clk_rst`: `clk_o` khởi tạo 0 trong `initial`, đảo bằng `always #(CLK_PERIOD / 2)` → cạnh lên đầu tiên ở `CLK_PERIOD/2`, không có cạnh lên ở thời điểm 0; `clk_cnt_o <= clk_cnt_o + 1` ở mỗi cạnh lên (khởi tạo 0 một lần, không bao giờ reset).

## 5. Thời điểm lái stimulus và lấy mẫu

**Luật bắt buộc – lái input DUT: chờ cạnh lên, trễ đúng `#1`, rồi gán** (trong task của driver):

```verilog
@(posedge clk_i);
#1;
din_o = 8'hA5;
```

- Áp dụng cho mọi lần lái input DUT trong chuỗi stimulus (kể cả trả input về giá trị nghỉ, và reset khi reset là input đồng bộ). Không lái ở `negedge`, không lái đúng tại `posedge`, không lái ngay trước `posedge`, không thay `#1` bằng trễ khác.
- `#1` chỉ thuộc testbench. Không bao giờ thêm trễ vào RTL, không sửa RTL để hợp với TB.
- Biến nội bộ của TB (model, bộ đếm, chuỗi log) không cần theo luật này.
- Lấy mẫu output: monitor ở `negedge` (mục 2.1) – output thanh ghi đã cập nhật ở cạnh lên trước đó, output tổ hợp ứng với input đang giữ. Driver cần handshake (vd. `pready`) thì cũng đọc ở `negedge` trước khi quyết định chu kỳ tiếp theo.
- Task giao dịch kết thúc ở `negedge` của chu kỳ cuối; lần gọi kế tiếp bắt đầu ở chu kỳ sau (back-to-back). Task không phải giao dịch (chờ, đổi sideband) đưa bus về nghỉ trong chu kỳ của nó.

## 6. Reset

- Theo spec của DUT (cực tính, đồng bộ/không đồng bộ). Không sửa hành vi reset của RTL.
- `reset_dut` khởi tạo rõ: mọi input DUT về giá trị nghỉ, reset tích cực, giữ `RESET_CYCLES` (mặc định 5; spec nêu khác thì theo spec) chu kỳ, rồi nhả. Model về trạng thái reset theo `rst_n` (reset bất đồng bộ: `always @(posedge clk_i or negedge rst_n_i)`). Output trong lúc reset vẫn được watch so với model ở mọi mẫu (chỉ in khi lệch).
- Reset **không đồng bộ**: tích cực ngay khi gọi (giữ ngữ nghĩa async), nhả bằng `@(posedge clk); #1;`. Log `[RESET] sys_rst_n = 0 (asserted for N rising edges)` lúc tích cực và `[RESET] sys_rst_n = 1 (released)` lúc nhả. `clk_cnt` không bị reset.
- Reset **đồng bộ**: cả tích cực và nhả đều theo `@(posedge clk); #1;`.
- Testcase gọi `reset_dut` sau khi đã in header (và `[GOAL]`) tới nhánh lá đầu tiên, để các check trong lúc reset thuộc nhánh đó. Reset giữa các nhánh con: gọi lại `reset_dut` (chỉ DUT/model); `init_test` (xóa bộ đếm) chỉ chạy một lần mỗi Item.

## 7. Self-check và log

Mục tiêu: log **ngắn, cô đọng**, bắt đúng mốc – mỗi thao tác tác động DUT một dòng, mỗi kết quả kiểm có ý nghĩa một dòng – để người đọc thấy ngay stimulus và checkpoint sai đầu tiên, rồi khoanh vùng lỗi theo spec. Kiểm tra vẫn chạy đầy đủ (mọi mẫu, mọi giao dịch); chỉ phần in được giảm. Model tính mọi expected bên trong, không in diễn giải.

### 7.1 Các loại check (đều so với model, đều in qua logger)

| Dòng | Khi nào | Expected (model) | Actual (DUT qua monitor) | Đếm |
| --- | --- | --- | --- | --- |
| `[<PROTO> WRITE <REG>] addr data strb OK\|SLVERR` | mẫu hoàn tất giao dịch ghi, đáp ứng đúng như model dự đoán | cờ lỗi, số wait cycle | cờ lỗi, số wait cycle quan sát | không – `OK` chỉ nói transfer hoàn tất không báo lỗi; không phải bằng chứng thanh ghi lưu đúng, không phải data-check |
| `[<PROTO> WRITE <REG>] addr data strb expected: <e> actual: <a> FAIL` | như trên, đáp ứng lệch (`OK`/`SLVERR` hoặc `N wait`) | – | – | 1 FAIL |
| `[<PROTO> READ <REG>] addr expected: <e> actual: <a> PASS\|FAIL` | mẫu hoàn tất giao dịch đọc: dữ liệu + đáp ứng trên một dòng | giá trị thanh ghi theo model | dữ liệu đọc | 1 |
| `[WATCH] <output> (<tình trạng bus>) expected: <e> actual: <a> FAIL` | mẫu lệch đầu tiên của một output ngoài mẫu hoàn tất (mọi output, mọi mẫu, kể cả lúc reset và lúc chờ) | `exp_*` | `s_*` | 1 FAIL mỗi đợt lệch; đóng bằng `[WATCH END]` (không đếm) |
| `[CHECK] <output> <what> expected: <e> actual: <a> PASS\|FAIL` | `u_chk.checkpoint("<what>")` ngay sau một task sequence | `exp_*` của output đó | `s_*` | 1 |

- **Watch không bỏ sót, không làm ngập log**: mọi mẫu đều được so; khớp thì không in gì; lệch lần đầu của một output → in ngay một dòng FAIL (thời điểm mẫu, tình trạng bus, expected, actual); các mẫu lệch tiếp theo của output đó chỉ đếm và được đóng bằng một dòng `[WATCH END]` (không đếm) khi khớp lại ("tim_pready: 3 mismatching sample(s) clk=a..b, matches the model again"). Lệch ở output khác, hoặc lệch mới sau khi đã khớp lại, in FAIL riêng. Không in PASS lặp theo chu kỳ.
- `pass_count`, `fail_count` (`integer`) chỉ do logger sở hữu: `u_log.init` gán 0 (một lần mỗi Item, trong `init_test`), `u_log.check` tăng đúng một bộ đếm mỗi dòng kết thúc bằng `PASS`/`FAIL`, `u_log.error_msg` tăng `fail_count` cho lỗi không phải phép so (`TIMEOUT`, `PROTOCOL ERROR`, `LOG ERROR`). **PASS = số dòng kết thúc bằng `PASS`; FAIL = số dòng kết thúc bằng `FAIL` + số dòng lỗi.** Dòng sự kiện (`APB WRITE … OK`, `DRIVE`, `RESET`, `WAIT`, `OBSERVE`, `WATCH END`) không bao giờ được đếm. Ý nghĩa này kiểm chứng được bằng cách đếm dòng (parser làm vậy).

### 7.2 Định dạng log (chuẩn, `check_sim_log.py` và `sim/report.csh` đọc)

```text
[TEST] <ID>: <objective>                                             bối cảnh, vài dòng đầu log
[TEST] DUT …, spec …
[TEST] Time: t in ns; clk = rising edges since time 0, never reset; drive / sample points; APB line at completion
[TEST] Checks: expected from the golden model; every sample compared, only deviations printed; meaning of OK
[ITEM] <Item>
  [SUBITEM1] <Sub item 1>
    [GOAL] <one short objective>
    [SUBITEM2] <Sub item 2>
<prefix> [<TAG>] <text>                                              dòng sự kiện (không đếm)
<prefix> [<TAG>] <text> expected: <e> actual: <a> PASS|FAIL [(<note>)]   dòng check (đếm 1)
<prefix> [TIMEOUT|PROTOCOL ERROR|LOG ERROR] <text>                   lỗi không phải phép so (đếm FAIL)
[SUMMARY] PASS=<n> FAIL=<n>
Test_result: PASSED|FAILED

<prefix> = [t=<ns> ns clk=<n>]   vd. [t=     360 ns clk=    18]
```

- **Bối cảnh `[TEST]`** (từ `init_test`, mỗi log tự đủ dùng, vài dòng): ID và mục tiêu; DUT, phạm vi (chỉ port công khai), đường dẫn spec; quy ước thời gian/clock (mô tả một lần ở đây, không lặp trên từng dòng); nguồn expected và nghĩa của `OK`.
- **Prefix** `[t=<ns> ns clk=<n>]`: thời điểm stimulus thật sự được áp (`posedge + 1`) hoặc output thật sự được lấy mẫu (`negedge`) – không phải lúc logger xử lý; `clk` = `clk_cnt` tại thời điểm đó (mục 2.1). Không pha, không transaction ID.
- **Header nhánh**: thứ tự Item → Sub item 1 → Sub item 2 → dòng của nhánh lá đó. `[ITEM]` một lần ở đầu; `[SUBITEM1]` một lần khi bắt đầu nhóm, các `[SUBITEM2]` cùng cha liên tiếp bên dưới; không in lại tên cha, mục tiêu hay mô tả dài trên các dòng sau. Nhánh một/hai cấp chỉ in các cấp thực sự tồn tại. Đổi cha thì context con bị xóa; gọi `sub1` khi chưa có Item hay `sub2` khi chưa có Sub item 1 → `[LOG ERROR]`. Tên in đúng nguyên văn ô vplan (tiếng Anh, không dịch, không thay bằng ID; danh sách: `check_sim_log.py --items <vplan>`). Thụt lề 0/2/4 chỉ để đọc. **`[GOAL]`**: một dòng ngắn dưới header (`u_log.goal`), bằng lời của spec.
- **Số dòng tối thiểu cho mỗi thao tác** (tag gợi ý, chọn theo giao thức nhưng ngắn và nhất quán):

| Thao tác | Dòng | Phát bởi |
| --- | --- | --- |
| Ghi bus | `[APB WRITE TCR]   addr: 0x000 data: 0x00000103 strb: 0b0011 OK` – một dòng ở mẫu hoàn tất; thời điểm setup = `clk - 2` khi đúng một wait state (nêu một lần ở `[TEST] Time`); wait state/đáp ứng bất thường → dòng FAIL, chú thích nêu số wait và `clk` setup hoặc điều kiện lỗi của model | `u_chk` |
| Đọc bus | `[APB READ TDR0]   addr: 0x004 expected:   3 counts actual:   3 counts PASS` – dữ liệu capture và kết quả trên một dòng, thời điểm = lúc lấy mẫu response | `u_chk` |
| Input ngoài bus | `[DRIVE]           dbg_mode: 0 -> 1` – chỉ khi thật sự đổi, thời điểm áp | `u_drv` |
| Reset | `[RESET]           sys_rst_n = 0 (asserted for 2 rising edges)` / `sys_rst_n = 1 (released)` | `u_clk_rst` |
| Chờ có nghĩa với kịch bản | `[WAIT]            8 cycles, bus idle (clk=19..26)` – một dòng, không log từng chu kỳ | `u_drv` |
| Output có cạnh quan trọng | `[OBSERVE]         tim_int: 0 -> 1` | `u_mon` |

- **Không in**: REQUEST / SETUP / ACCESS / COMPLETE tách dòng cho cùng một transfer; READ RESPONSE rồi CHECK lặp cùng dữ liệu; dòng `MODEL`, lịch sử đếm, công thức, các bước cập nhật trạng thái, suy luận dài; PASS lặp theo chu kỳ; dòng chẩn đoán riêng; phỏng đoán nguyên nhân.
- Với DUT cha (phạm vi tích hợp), tín hiệu nội bộ của module con (vd. `cnt_en`, `div_cnt`) chỉ tồn tại trong model, không bao giờ in như giá trị đo được; hành vi của chúng được kiểm qua output công khai (vd. đọc TDR) so với model.
- `Test_result: PASSED` khi FAIL = 0 và PASS > 0, ngược lại `FAILED`; in ngay sau `[SUMMARY]` (`sim/report.csh` lấy từ thứ ba của dòng này). Không dòng nào khác chứa chữ `Test_result`. Không cần `[FIRST FAIL]`: dòng FAIL đầu tiên đã hiện rõ dưới header nhánh của nó.
- Mỗi testcase chạy thành một log riêng `sim/log/<ID>.log` (transcript QuestaSim, mỗi dòng có tiền tố `# `).

### 7.3 Radix theo ý nghĩa dữ liệu

| Đại lượng | Định dạng | Hàm logger |
| --- | --- | --- |
| Địa chỉ, dữ liệu thanh ghi thô, cấu hình, mask, giá trị cần thấy vị trí bit/field | hex, tiền tố `0x`, đủ độ rộng, chữ số hoa (`0x01C`, `0x00000203`) | `fmt_hex(v, w)` |
| Byte strobe, nhóm bit điều khiển cần thấy từng bit | binary, tiền tố `0b` (`0b0011`) | `fmt_bin(v, w)` |
| Số đếm, số chu kỳ, độ dài, số lượng, toán hạng/kết quả số học | decimal, kèm đơn vị (`5 counts`, `8 cycles`) | `fmt_cnt(v, w)` / `fmt_dec(v, w)` / `fmt_sdec(v, w)` (có dấu) |
| Tín hiệu điều khiển một bit | `0`/`1` kèm tên (`dbg_mode: 0 -> 1`) | `fmt_bit(v)` |

- Dòng giao dịch ghi `addr`/`data` bằng hex để đối chiếu register map; dòng **kiểm chức năng** trình bày theo ý nghĩa: TDR là thanh ghi nhưng khi kiểm chức năng đếm in decimal (`expected: 5 counts actual: 5 counts`); thanh ghi cấu hình/trạng thái in hex (`expected: 0x00000003 actual: 0x00000003`). Không in cả hex lẫn decimal cho cùng một số đếm nếu không giúp chẩn đoán; không bắt người đọc tự đổi hex sang decimal.
- Expected và actual của cùng một check cùng radix, đơn vị và cách hiểu signed/unsigned; số có dấu in đúng dấu theo spec (`fmt_sdec`), số đếm unsigned không bao giờ in âm.
- Giữ đủ độ rộng, kể cả counter 64-bit (`fmt_*` nhận `[63:0]` + độ rộng; không qua `integer` 32-bit).
- Actual có X/Z → FAIL, và in raw (`X/Z 0x0000000x`) khi decimal không biểu diễn được, không bao giờ một số decimal có vẻ hợp lệ.
- Radix chỉ đổi cách trình bày, không đổi độ rộng hay phép so (`===` trên giá trị gốc). Không chuyển mọi giá trị qua một hàm in hex cố định.

### 7.4 Ngữ cảnh của một FAIL

Dòng check đã mang chức năng (tag + nhánh), thời điểm và `clk`, expected (model), actual (DUT); thao tác dẫn tới nằm ở các dòng ngay trên. Một sai lệch luôn chỉ **một dòng**: khi expected/actual chưa đủ để thấy sai gì, checker thêm chú thích ngắn trong ngoặc sau `FAIL` – không có dòng chẩn đoán riêng.

| FAIL | Chú thích | Ví dụ |
| --- | --- | --- |
| Đọc số đếm (TDR) | không – expected/actual decimal đã cho thấy chênh lệch | `expected:   3 counts actual:   6 counts FAIL` |
| Đọc thanh ghi (hex) | field khác nhau | `expected: 0x00000003 actual: 0x00000001 FAIL (differ: HALT_ACK)` |
| Đáp ứng lệnh ghi | số wait so với model và `clk` setup, hoặc điều kiện lỗi model dự đoán | `expected: SLVERR actual: OK FAIL (tim_pslverr 0, model: TCR error condition 1, DIV_VAL > 8)` |
| Watch | tình trạng bus của mẫu, đặt trong text trước `expected:` | `[WATCH] tim_pready (access cycle 2 of APB WRITE TCR, setup clk=3) expected: 1 actual: 0 FAIL` |
| X/Z | không – actual in raw | `actual: X/Z 0x0000000x FAIL` |

- Không in lịch sử model, phân tích dài hay nguyên nhân phỏng đoán; output top không bao giờ đủ để khẳng định module/tín hiệu nội bộ nào hỏng. Timeout là dòng `[TIMEOUT]` riêng (có `clk` của pha setup).
- Cần hiểu sâu hơn một FAIL → xem waveform (`make wave`) hoặc tạm thêm `$display` khi gỡ lỗi, không để lại trong TB.

### 7.5 Căn cột

| Cột | Căn | Độ rộng (parameter của logger, truyền từ phần 1) |
| --- | --- | --- |
| `t=` trong prefix | phải | `TIME_W` (mặc định 8) |
| `clk=` | phải | `CLK_W` (mặc định 6) |
| `[<TAG>]` | trái, đệm khoảng trắng | `TAG_W` (mặc định 17, ≥ tag dài nhất thường gặp, vd. `[APB WRITE THCSR]`; tag dài hơn không bị cắt, chỉ dòng đó lệch) |
| `<e>`, `<a>` của dòng đọc | phải | `VAL_W` (mặc định 10, vd. `0x00000203`, `  3 counts`); dòng watch/checkpoint không đệm |

- Hiện thực trong logger: hàm `prefix`, `str_len`, `pad_left`, `pad_right` (chuỗi `reg [8*80-1:0]`) – Verilog-2005 thuần, không `%-40s`/`%8d` (độ rộng trường là mở rộng SystemVerilog). Mọi dòng chỉ in qua logger (`info`, `check`, `error_msg`); không component nào tự `$display`.
- Header, `[GOAL]`, `[TEST]`, `[SUMMARY]`, `Test_result` không đệm cột.

## 8. Testcase: một file mỗi Item

- `tc/<ID>.v` với `<ID>` = ID Item `TC_<M>_<NNN>` – ID thực thi dùng cho tên file, `make TESTNAME=<ID>`, `sim/pat.list`, `sim/log/<ID>.log`. Không tạo file riêng cho Sub item 1/Sub item 2 hay từng dòng vplan. Nhánh con truy vết bằng đường dẫn `<ID> › <Item> › <Sub item 1> › <Sub item 2>` (cùng tên lá dưới cha khác nhau được phân biệt bằng cha).
- Header comment: ID, tên Item, mục tiêu, cây nhánh con của Item theo vplan, ghi chú "no expected value here".
- Đúng **một** khối `initial` (luồng điều phối chính), thụt 2 khoảng trắng (nằm bên trong module TB): `init_test("<ID>", "<objective>")` → `u_log.item("<Item>")` (+ `u_log.goal`) → các nhóm nhánh → `end_test`. `init_test` và `end_test` chạy một lần cho cả Item.
- Mỗi Sub item 1 / Sub item 2 là một khối có tên `begin : <name> ... end` theo cây vplan, theo đúng thứ tự vplan, mỗi cụm cùng cha liên tiếp. Lệnh đầu tiên của khối là header của nó (`u_log.sub1(...)`/`u_log.sub2(...)`), tiếp theo là một dòng `u_log.goal(...)` ngắn, trước mọi lệnh tốn thời gian; khối chỉ chứa stimulus của nhánh đó.
- Kịch bản **chỉ mô tả stimulus** theo Test sequence của vplan: gọi task sequence của TB top (`apb_write(addr, data, strb)`, `apb_read(addr)`, `set_dbg_mode(v)`, `wait_cycles(n)`, `u_chk.checkpoint("<what>")` khi cần), `reset_dut`, header/goal của logger. Input ngoài bus đổi ở điểm lái hợp lệ gần nhất sau thao tác trước; không chèn chờ/quan sát mà kịch bản không cần. Literal trong tc chỉ là stimulus (địa chỉ, data, strobe, số chu kỳ) và chữ mô tả – **không giá trị expected nào**. Không khai báo biến, không viết lại model/checker trong tc.
- Không chọn test bằng `+TEST`; test được chọn bằng `make TESTNAME=<ID>`.

## 9. Chọn test, timeout, waveform, dữ liệu file

- Chọn test bằng file: `make -C sim all TESTNAME=<ID>` chép `tc/<ID>.v` thành `sim/run_test.v`, biên dịch (`compile.f` → `rtl.f`, `tb.f`), chạy. Chạy cả danh sách: `cd sim && ./run.csh` (đọc `pat.list`), tổng hợp: `./report.csh`.
- Timeout toàn cục (vd. 100× số chu kỳ ước lượng) trong `initial` riêng ở phần 9: `u_log.error_msg($time, "TIMEOUT", "simulation exceeded … ns")` rồi `end_test`. Handshake có giới hạn chờ riêng trong driver (`MAX_WAIT` → `[TIMEOUT]` nêu giao dịch và `clk` setup, giao dịch bị bỏ, bus về nghỉ).
- Waveform: `make run` ghi mọi tín hiệu (`log -r /*`) vào `sim/vsim.wlf`; `make wave` mở trong QuestaSim. TB không cần `$dumpfile`/`$dumpvars`.
- Dữ liệu từ file (khi vplan/spec dùng vector ngoài): input `doc/database/input/<m>_<tên>.txt`, tham chiếu `doc/database/output/<m>_<tên>.txt`. `init_test` đọc `+IN=`/`+OUT=`; mặc định là đường dẫn tương đối từ `sim/` (`"../doc/database/input/<m>_<tên>.txt"`), biến chuỗi `reg [8*256-1:0]`. Driver đọc vector input; vector tham chiếu chỉ được dùng khi nó là đầu ra của một model tham chiếu độc lập (vd. script Python viết theo spec, `sim/script/<m>_gen_vectors.py`), được model hoặc checker đọc như một phần của golden model – ghi nguồn trong header. Đổi cặp file: `make all TESTNAME=<ID> DATA_IN=<file> DATA_OUT=<file>`. Script sinh dữ liệu: `make gen_data`. Không đặt dữ liệu hay script trong `tb/`, `tc/`.

## 10. Khung mẫu đã chạy thật: `cnt_ctrl` kiểm qua `timer_top`

Thư mục `references/example_timer_top/` (đọc trực tiếp các file khi viết TB mới):

```text
tb/tb_timer_top.v           TB top 9 phần: helper trình bày (reg_name, field_names), task sequence
                            (apb_write, apb_read, set_dbg_mode, wait_cycles), init_test, end_test
tb/tb_timer_top_clk_rst.v   clk, rst_n, clk_cnt (không reset); [RESET]
tb/tb_timer_top_drv.v       APB master + dbg_mode; [DRIVE], [WAIT], [TIMEOUT]; MAX_WAIT
tb/tb_timer_top_mon.v       mẫu negedge, s_time, s_done / s_wait / s_setup; [OBSERVE] tim_int
tb/tb_timer_top_model.v     model từ spec, không in gì; err_text cho chú thích FAIL
tb/tb_timer_top_chk.v       một dòng mỗi giao dịch, watch (chỉ in khi lệch, WATCH END), checkpoint, sync
tb/tb_timer_top_log.v       prefix [t= ns clk=], info / check / error_msg / goal / banner,
                            fmt_hex / fmt_bin / fmt_dec / fmt_cnt / fmt_sdec / fmt_bit
tc/TC_TIMER_TOP_006.v       cnt_ctrl_chk: Timer enable, Divider setting, TDR write while counting
tc/TC_TIMER_TOP_012.v       cnt_halt_chk: halt / resume theo HALT_REQ và theo dbg_mode, TDR write while halted
log/TC_TIMER_TOP_006.log    log PASS thật (62 dòng, PASS=22 FAIL=0)
log/TC_TIMER_TOP_012.log    log PASS thật (48 dòng, PASS=14 FAIL=0)
log/TC_TIMER_TOP_012_mutant_halt_ignored.log   log FAIL thật, RTL cố ý gây lỗi (xem 10.3)
```

Kiểm chứng (2026-11-05): QuestaSim 2021 qua `sim/Makefile` (`make all TESTNAME=<ID>`) trên một bản sao scratch của project (rtl/ thật của Timer_IP, `sim/` env, `tb.f` chỉ gồm các file trên): biên dịch `Errors: 0, Warnings: 0`; `check_sim_log.py … doc/vplan/timer_top_vplan.md --partial` → `TẤT CẢ PASS`; `report.csh` → PASSED (mutant: FAILED). File log chỉ giữ phần TB in (bỏ tiền tố `# ` và dòng của QuestaSim).

Hai nhánh đầu của `TC_TIMER_TOP_012` là **kịch bản minh họa của skill** cho halt/resume (thao tác và checkpoint rõ ràng), khác Test sequence của `doc/vplan/timer_top_vplan.md` và đổi `dbg_mode` khi TIM_EN = 1 – ngoài giả định môi trường OPEN-001 (`dbg_mode` đồng bộ, lái ở `posedge + #1`; hành vi vẫn xác định bởi `halted = dbg_mode & HALT_REQ` của spec). TB của project vẫn theo Test sequence của vplan.

DUT nhỏ không có bus: giữ nguyên vai trò; driver log `[DRIVE] <sig>: cũ -> mới` mỗi lần đổi input, checker dùng watch + `checkpoint` (không có dòng giao dịch).

### 10.1 Testcase: chỉ stimulus, checkpoint đủ phân biệt

```verilog
    begin : halt_in_debug_mode
      u_log.sub1("Halt in debug mode");
      u_log.goal("DIV_VAL 1 (1 step / 2 cycles): dbg_mode = 1 alone does not halt; HALT_REQ = 1 halts (TDR0 and divider phase held); HALT_REQ = 0 resumes");
      reset_dut;
      apb_write(ADDR_TCR,   32'h0000_0103, 4'b0011);     // DIV_VAL = 1, DIV_EN = 1, TIM_EN = 1
      apb_read(ADDR_TDR0);                               // counting
      set_dbg_mode(1'b1);                                // HALT_REQ = 0: no halt yet
      apb_write(ADDR_THCSR, 32'h0000_0001, 4'b0001);     // HALT_REQ = 1: halt starts
      apb_read(ADDR_THCSR);                              // HALT_REQ, HALT_ACK
      apb_read(ADDR_TDR0);                               // held
      wait_cycles(8);
      apb_read(ADDR_TDR0);                               // still held
      apb_write(ADDR_THCSR, 32'h0000_0000, 4'b0001);     // HALT_REQ = 0: resume
      apb_read(ADDR_THCSR);
      apb_read(ADDR_TDR0);                               // counting again, same divider phase
    end
```

- THCSR kiểm cơ chế yêu cầu/xác nhận halt (HALT_REQ, HALT_ACK); TDR0 kiểm hành vi đếm thực tế. Mọi giá trị TDR0 (trước halt, trong halt, sau resume) so với model.
- Hai lần đọc TDR0 trong halt cách nhau một khoảng giữ (`wait_cycles(8)`) phân biệt "đã dừng" với "vẫn đếm"; lần đọc sau resume phân biệt "đã đếm tiếp" với "vẫn dừng". Không mặc định TDR0 lúc halt bằng lần đọc trước: lần đọc trước = 1 count (clk 8), giá trị bị giữ = 3 counts vì các chu kỳ của lệnh đọc, của lần đổi `dbg_mode` và của lệnh ghi THCSR vẫn đếm.
- `set_dbg_mode` trước lệnh ghi HALT_REQ làm số chu kỳ chạy trước halt lẻ (7: clk 6..12), nên halt giữ divider ở vị trí 1 của 2; sau resume bước đầu tiên đến sau 1 chu kỳ: 6 counts ở clk 38 (divider bị đặt lại khi halt thì chỉ 5) – checkpoint này kiểm cả việc giữ pha divider.
- Nhánh `Halt without debug mode` làm ngược lại: HALT_REQ = 1 trước (không halt), `dbg_mode` 0 → 1 halt, `dbg_mode` 1 → 0 nhả trong khi HALT_REQ vẫn 1 (THCSR = `0x00000001`, TDR0 đếm tiếp). Hai nhánh cùng phủ bốn tổ hợp `dbg_mode`/HALT_REQ mà không thêm thao tác thừa.

Task sequence của TB top (phần 8) – stimulus rồi đồng bộ với checker, không expected:

```verilog
  task set_dbg_mode;
    input v;
    begin
      u_drv.set_dbg_mode(v);   // posedge + #1 of the next cycle, [DRIVE] only on a real change
      u_chk.sync;
    end
  endtask
```

Checker ở mẫu hoàn tất của lệnh đọc (trích `tb_timer_top_chk.v`): expected từ `exp_*`, dữ liệu và đáp ứng trên một dòng, thời điểm là lúc lấy mẫu:

```verilog
        if (is_cnt) begin                       // TDR0 / TDR1: a count -> decimal
          es = tb_timer_top.u_log.fmt_cnt(exp_prdata_i, 32);
          as = tb_timer_top.u_log.fmt_cnt(s_prdata_i, 32);
        end
        else begin                              // configuration / status -> hex
          es = tb_timer_top.u_log.fmt_hex(exp_prdata_i, 32);
          as = tb_timer_top.u_log.fmt_hex(s_prdata_i, 32);
        end
        dat_ok = (s_prdata_i === exp_prdata_i);
        tb_timer_top.u_log.check(s_time_i, tag, txt, dat_ok && rsp_ok, es, as, tb_timer_top.VAL_W);
```

### 10.2 Log PASS (`TC_TIMER_TOP_012 › Halt in debug mode`)

```text
[TEST] Time: t in ns; clk = sys_clk rising edges since time 0 (20 ns period, never reset); inputs applied at rising edge + 1 ns, outputs sampled at the falling edge; APB line at completion, setup at clk - 2
[TEST] Checks: expected from the golden model tb_timer_top_model; outputs compared at every falling edge, only deviations printed; APB WRITE ... OK = no error response (not a data check)
[ITEM] cnt_halt_chk
  [SUBITEM1] Halt in debug mode
    [GOAL] DIV_VAL 1 (1 step / 2 cycles): dbg_mode = 1 alone does not halt; HALT_REQ = 1 halts (TDR0 and divider phase held); HALT_REQ = 0 resumes
[t=       0 ns clk=     0] [RESET]           sys_rst_n = 0 (asserted for 2 rising edges)
[t=      31 ns clk=     2] [RESET]           sys_rst_n = 1 (released)
[t=     100 ns clk=     5] [APB WRITE TCR]   addr: 0x000 data: 0x00000103 strb: 0b0011 OK
[t=     160 ns clk=     8] [APB READ TDR0]   addr: 0x004 expected:   1 counts actual:   1 counts PASS
[t=     171 ns clk=     9] [DRIVE]           dbg_mode: 0 -> 1
[t=     240 ns clk=    12] [APB WRITE THCSR] addr: 0x01C data: 0x00000001 strb: 0b0001 OK
[t=     300 ns clk=    15] [APB READ THCSR]  addr: 0x01C expected: 0x00000003 actual: 0x00000003 PASS
[t=     360 ns clk=    18] [APB READ TDR0]   addr: 0x004 expected:   3 counts actual:   3 counts PASS
[t=     371 ns clk=    19] [WAIT]            8 cycles, bus idle (clk=19..26)
[t=     580 ns clk=    29] [APB READ TDR0]   addr: 0x004 expected:   3 counts actual:   3 counts PASS
[t=     640 ns clk=    32] [APB WRITE THCSR] addr: 0x01C data: 0x00000000 strb: 0b0001 OK
[t=     700 ns clk=    35] [APB READ THCSR]  addr: 0x01C expected: 0x00000000 actual: 0x00000000 PASS
[t=     760 ns clk=    38] [APB READ TDR0]   addr: 0x004 expected:   6 counts actual:   6 counts PASS
  [SUBITEM1] Halt without debug mode
    [GOAL] DIV_EN 0 (1 step / cycle): HALT_REQ = 1 then dbg_mode = 1 halts; dbg_mode = 0 with HALT_REQ = 1 kept: HALT_ACK 0, counting resumes
[t=     761 ns clk=    38] [DRIVE]           dbg_mode: 1 -> 0
[t=     761 ns clk=    38] [RESET]           sys_rst_n = 0 (asserted for 2 rising edges)
[t=     791 ns clk=    40] [RESET]           sys_rst_n = 1 (released)
```

`clk` tiếp tục tăng qua reset DUT (38 → 40 → …). Divider 2^8 (`TC_TIMER_TOP_006 › Divider setting`, phần C) – một dòng cho 253 chu kỳ chờ, mọi mẫu vẫn được watch:

```text
[t=    1680 ns clk=    84] [APB WRITE TCR]   addr: 0x000 data: 0x00000803 strb: 0b0011 OK
[t=    1691 ns clk=    85] [WAIT]            253 cycles, bus idle (clk=85..337)
[t=    6800 ns clk=   340] [APB READ TDR0]   addr: 0x004 expected:   0 counts actual:   0 counts PASS
[t=    6860 ns clk=   343] [APB READ TDR0]   addr: 0x004 expected:   1 counts actual:   1 counts PASS
```

### 10.3 Log FAIL (mutant: halt không chặn đếm)

Cùng TB, bản sao `cnt_ctrl.v` trong scratch bị sửa để halt không còn chặn đếm (`div_cnt_run = div_cnt_wrap`, `cnt_en = tim_en & div_tick`; `halt_ack` giữ đúng) – chỉ để minh họa, không phải lỗi của project:

```text
[t=     240 ns clk=    12] [APB WRITE THCSR] addr: 0x01C data: 0x00000001 strb: 0b0001 OK
[t=     300 ns clk=    15] [APB READ THCSR]  addr: 0x01C expected: 0x00000003 actual: 0x00000003 PASS
[t=     360 ns clk=    18] [APB READ TDR0]   addr: 0x004 expected:   3 counts actual:   6 counts FAIL
[t=     371 ns clk=    19] [WAIT]            8 cycles, bus idle (clk=19..26)
[t=     580 ns clk=    29] [APB READ TDR0]   addr: 0x004 expected:   3 counts actual:  11 counts FAIL
...
[SUMMARY] PASS=7 FAIL=7
Test_result: FAILED
```

Đọc được ngay: thao tác kích thích (cấu hình, `dbg_mode` 0 → 1 ở clk 9, HALT_REQ = 1 hoàn tất ở clk 12), cơ chế halt đúng (THCSR PASS), checkpoint sai đầu tiên (TDR0 trong halt ở clk 18: 6 thay vì 3) và lần đọc sau một khoảng giữ cho thấy counter vẫn đếm (11). Model không bị nạp lại từ DUT: các lần đọc sau tiếp tục so với dự đoán của model.

Hai mutant khác cho các dạng còn lại – `tim_pready` không lên cho lệnh ghi (watch + timeout), và HALT_ACK luôn 0 (đọc thanh ghi, chú thích field):

```text
[t=     100 ns clk=     5] [WATCH]           tim_pready (access cycle 2 of APB WRITE TCR, setup clk=3) expected: 1 actual: 0 FAIL
[t=     120 ns clk=     6] [WATCH END]       tim_pready: 1 mismatching sample(s) clk=5..5, matches the model again
[t=     240 ns clk=    12] [TIMEOUT]         APB WRITE TCR: no tim_pready = 1 in 9 access cycles (setup clk=3); transfer abandoned, bus idle

[t=     300 ns clk=    15] [APB READ THCSR]  addr: 0x01C expected: 0x00000003 actual: 0x00000001 FAIL (differ: HALT_ACK)
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

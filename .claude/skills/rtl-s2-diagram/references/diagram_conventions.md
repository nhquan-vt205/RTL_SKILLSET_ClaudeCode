# Quy ước diagram SVG (stage 2, mọi level)

Mục lục: 1. Khung file · 2. Mức chi tiết theo level · 3. Bộ ký hiệu · 4. Dây, nhãn, bố cục · 5. Model `<desc>` · 6. Góc nhìn scope (`--from/--to`) · 7. Mẫu `<m>_notes.md` (tùy chọn)

Mục tiêu: nhìn diagram hiểu phần cứng và viết được RTL. Style là **sơ đồ logic đen trắng** theo hai ảnh mẫu của người dùng (MUX hình thang, FF chữ nhật + tam giác clock + bubble reset, gate AND/OR + bubble đảo, ellipse operator, cloud, bus bundle, junction dot). Thư viện ký hiệu: `symbol_library.svg` (mở bằng Chrome/Edge). Ví dụ đã qua lint: `example_l0_dma_top.svg`, `example_l1_sync_fifo.svg`, `example_l2_acc_unit.svg`.

## 1. Khung file

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="W" height="H" viewBox="0 0 W H"
     font-family="Calibri, Arial, sans-serif" font-size="13">
  <!-- module : <m> -->
  <!-- stage  : 2 - diagram L0 | L1 | L2 -->           <- gate S1/S3 đọc level từ dòng này
  <!-- source : <spec file used> -->
  <!-- param  : <parameter values used for widths> -->  (nếu có)
  <!-- scope  : from <a, b> to <x, y> -->               (chỉ file góc nhìn <m>_<part>.svg, mục 6)
  <desc id="model"><![CDATA[
  ... phương trình từng khối, mục 5 ...
  ]]></desc>
  <style>
    .w{fill:none;stroke:#000;stroke-width:1.5}
    .s{fill:#fff;stroke:#000;stroke-width:1.5}
    .dot{fill:#000}
    text{fill:#000}
  </style>
  <rect width="100%" height="100%" fill="#fff"/>
  ... ký hiệu (<g id="reg_x">...</g>), dây, nhãn – theo thứ tự luồng dữ liệu ...
</svg>
```

- **Chỉ đen trắng**: nét `#000`, nền và fill `#fff`, chữ `#000`. Không màu, gradient, bóng, mũi tên, tiêu đề, legend, khung module.
- Chỉ dùng `g path line rect circle ellipse text`. Không `<use>`/`<symbol>`/`<image>`/`<script>`/marker: mỗi ký hiệu chép thẳng hình từ mục 3, để file mở được bằng browser và chèn được vào Word/PPT/Inkscape.
- Mọi chữ, comment và model chỉ dùng tiếng Anh ASCII (`>=`, `!=`, `x`; không `≥ ≠ ×`).
- Canvas vừa nội dung, lề ~30px. Dịch cả sơ đồ thì bọc trong `<g transform="translate(dx,dy)">` (lint hiểu `translate`).

Mỗi ký hiệu là một nhóm `<g id="<tiền tố><tên>">` chứa hình và chữ bên trong của ký hiệu đó. Dây, junction dot, nhãn dây và tên port nằm ngoài nhóm.

| Tiền tố | Phần tử | Mục `[id]` trong model |
| --- | --- | --- |
| `reg_` | thanh ghi / FF (`fsm_` cho thanh ghi trạng thái FSM) | bắt buộc |
| `mem_` | bộ nhớ, mảng thanh ghi | bắt buộc |
| `mux_` | MUX 2:1, MUX N:1 | nên có |
| `gate_` | AND, OR, XOR, NAND, NOR, XNOR, NOT | tùy chọn |
| `op_` | ellipse operator (so sánh, số học) | nên có |
| `bus_` | bus bundle / bus split | tùy chọn |
| `cloud_` | logic gom thành cloud (người dùng đã duyệt) | bắt buộc |
| `blk_` | khối gom trong leaf (người dùng đã duyệt) | bắt buộc |
| `u_` | instance module con (L0, L1) | bắt buộc (port map) |

## 2. Mức chi tiết theo level

Level vẫn chọn như cũ (SKILL.md Bước 1); level quyết định phần nào **được phép** trừu tượng hóa. Phần không được trừu tượng hóa thì vẽ tới từng gate: mỗi thanh ghi một ô FF, mỗi enable/select một MUX, mỗi AND/OR/NOT/so sánh/phép toán một ký hiệu, hằng ghi tại đầu dây. Mảng bộ nhớ/thanh ghi luôn vẽ bằng ký hiệu `mem_` (mọi level).

| Level | Vẽ tới từng gate | Được trừu tượng hóa |
| --- | --- | --- |
| **L2** – leaf nhỏ | toàn bộ module | không (`cloud_`/`blk_` chỉ khi người dùng yêu cầu rõ; không có `u_`) |
| **L1** – leaf lớn (hoặc block có module con và nhiều logic riêng) | mọi phần còn lại | phần người dùng duyệt → `cloud_` hoặc `blk_`; module con (nếu có) → `u_` |
| **L0** – có module con | glue logic | mỗi module con → `u_` (đủ port trừ clk/rst); phần glue người dùng duyệt → `cloud_` |

**Đề xuất trừu tượng hóa (L1, L0) – người dùng duyệt trước khi vẽ.** Lệnh không có `--cloud`/`--block` → sau khi đọc spec, chia logic của module thành các phần theo chức năng và trình bày trong chat:

| Part | Signals in → out | Proposal | Reason |
| --- | --- | --- | --- |
| `ctrl` | `wr_valid_i, rd_ready_i` → `wr_en, rd_en, wr_ready_o, rd_valid_o` | `blk` | handshake + flags + counter, ~25 gates |
| `wptr` | `wr_en` → `wr_ptr_q[3:0]` | `gate` | small, shows the pointer register |

Proposal là `gate`, `cloud` (logic tổ hợp/điều khiển chỉ cần biết vào–ra) hoặc `blk` (phần có cấu trúc rõ, cần thấy đủ tín hiệu vào–ra trên khung). **Dừng và chờ người dùng duyệt/sửa**; chỉ vẽ sau khi có câu trả lời. Có `--cloud a,b --block c` (tên phần) → dùng đúng lựa chọn đó, không hỏi; phần không nêu tên vẽ tới từng gate. Thanh ghi nằm trong phần bị gom không vẽ ô FF riêng nhưng phải có trong model của khối đó (mục 5).

`blk_` trong leaf **chỉ là cách vẽ**: S3 vẫn viết phần đó trong cùng module, không tạo module mới. Phần cần thành module thật → báo người dùng tách ở S1.

Lint cảnh báo khi quá ~60 primitive (`mux_`/`gate_`/`op_`/`reg_`): đề xuất người dùng gom thêm hoặc dùng góc nhìn scope (mục 6), không tự gom.

## 3. Bộ ký hiệu

Toạ độ là hình gốc tại (0,0), đặt bằng `<g id="..." transform="translate(x,y)">` hoặc cộng thẳng toạ độ. Tất cả: hình `class="s"` (fill trắng), nét `class="w"`, stroke 1.5. Hình mẫu trực quan: `symbol_library.svg` (id `sym_*`).

| Ký hiệu | Hình gốc | Chân nối / quy cách |
| --- | --- | --- |
| **AND** | `<path class="s" d="M0,0 H30 A25,25 0 0 1 30,50 H0 Z"/>` | 2 input tại (0,15), (0,35); output (55,25). n input: cao `h` (input cách đều ≥ 20px), `M0,0 H30 A(h/2),(h/2) 0 0 1 30,h H0 Z`, output (30+h/2, h/2). |
| **OR** | `<path class="s" d="M0,0 Q40,0 70,25 Q40,50 0,50 Q14,25 0,0 Z"/>` | output (70,25). Dây input chạm lưng cong: x = 28·(y/h)·(1−y/h) (h=50: y=15/35 → x≈5.9). Cao h: `M0,0 Q40,0 70,h/2 Q40,h 0,h Q14,h/2 0,0 Z`. |
| **XOR** | `<path class="s" d="M8,0 Q48,0 78,25 Q48,50 8,50 Q22,25 8,0 Z"/>` + `<path class="w" d="M0,0 Q14,25 0,50"/>` | input chạm cung sau (x≈5.9 tại y=15/35), output (78,25). |
| **NAND / NOR / XNOR** | AND / OR / XOR + bubble ở output | bubble `<circle class="s" r="4"/>` tâm cách mũi 4px: NAND (59,25) → output (63,25); NOR (74,25) → (78,25); XNOR (82,25) → (86,25). |
| **Bubble đảo input** | `<circle class="s" cx="-4" cy="yin" r="4"/>` | sát cạnh input của cổng; dây dừng ở x=−8. Đây là cách mặc định để vẽ NOT (như `~div_en`, `~pwrite` trong mẫu). |
| **NOT đứng riêng** | `<path class="s" d="M0,0 L30,15 L0,30 Z"/>` + bubble (34,15) r4 | input (0,15), output (38,15). Chỉ dùng khi không có cổng phía sau để gắn bubble (vd. `wr_ready_o = ~full`). |
| **MUX 2:1** | `<path class="s" d="M0,0 L30,15 L30,55 L0,70 Z"/>` | input `0` tại (0,24), `1` tại (0,54), nhãn `<text x="5" y="28">0</text>` và `<text x="5" y="58">1</text>` bên trong; output (30,35); select vào cạnh dưới tại (15,62.5) (hoặc cạnh trên (15,7.5)). Enable/hold: input `0` = feedback Q. |
| **MUX N:1** | rộng w, cao h, xiên s=2w/3: `M0,0 Lw,s Lw,h−s L0,h Z` (mẫu: `M0,0 L60,40 L60,160 L0,200 Z`) | input cạnh trái cách đều ≥ 40px, nhãn case bên trong sát cạnh trái (`0x0`, `0x4`, `......`); output (w, h/2); select cạnh dưới tại (w/2, h−s/2). |
| **Register / FF 1 bit** | `<rect class="s" x="0" y="0" width="70" height="110"/>` + clock `<path class="w" d="M0,80 L14,90 L0,100"/>` + reset `<circle class="s" cx="35" cy="115" r="5"/>` | D (0,55), Q (70,55); tên reset port dưới bubble `<text x="35" y="137" text-anchor="middle">`. Không nhãn D/Q, không dây clk. |
| **Register n bit** | thêm `<rect class="s" x="6" y="-6" width="70" height="110"/>` vẽ **trước** rect chính | Q ra từ (76,55). |
| **Tên trong ô register** | chữ căn giữa ô | Spec có register map → tên field theo spec (`TIM_EN`); không có → tên thanh ghi `_q` trong spec (`count_q`). n bit: dòng 1 tên (y=50), dòng 2 `[msb:lsb]` (y=66); 1 bit: một dòng (y=59). FF không có tên trong spec → để trống. Tên dài → nới rộng ô. |
| **FF không reset / reset đồng bộ** | không vẽ bubble | Reset đồng bộ: MUX trước D chọn giá trị reset (select = tín hiệu reset), như `cnt_rst` trong mẫu. |
| **Bộ nhớ / mảng thanh ghi** | rect (rộng ≥ 150), tam giác clock ở góc dưới-trái khi ghi đồng bộ, bubble reset chỉ khi spec có reset | nhãn giữa khối: dòng 1 tên (`mem_q`), dòng 2 kích thước `A x bitwidth` (mảng 2 chiều `A x bitwidth x B`), dòng 3 `start - end` nếu spec có địa chỉ (`0x000 - 0x03C`). Chân port chạm cạnh khung: `WE`, `WA[..]`, `WD[..]`, `RA[..]`, `RD[..]` (hoặc tên theo spec). |
| **Khối submodule** (`u_`, `blk_`) | rect, kích thước tự nới cho vừa nhãn và số chân | nhãn giữa khối: `u_` 2 dòng `u_eng` / `dma_engine`; `blk_` 1 dòng tên chức năng (`addr_gen`). Mỗi port là một dây chạm cạnh khung (input trái, output phải; được dùng cạnh trên/dưới để tránh dây vòng). `u_` vẽ đủ port của module con **trừ clk/rst**. |
| **Mảng instance** (`generate`) | khối `u_` thêm `<rect class="s" x="6" y="-6" .../>` cùng kích thước, vẽ **trước** khung chính (như register n bit) | nhãn giữa khối 3 dòng: `u_lane` / `mac_lane` / `x 4` (số bản sao). Chân port như khối submodule; dây ra cạnh phải bắt đầu từ khung sau (x+6). Port là bus gộp của mọi bản sao; cách cắt bit cho từng bản sao ghi trong model. |
| **Ellipse operator** | `<ellipse class="s" rx="26..55" ry="16..22"/>` + chữ căn giữa | `== ?`, `>= ?`, `+1`, `+`, `!=0`, `=0`, `sext`. Input chạm viền: x = cx − rx·√(1 − (dy/ry)²). Toán tử 1 ngôi đặt nối tiếp trên dây. |
| **Cloud** | `<path class="s" d="M20,60 a18,18 0 0 1 -2,-34 a22,22 0 0 1 38,-14 a22,22 0 0 1 40,2 a20,20 0 0 1 22,30 a18,18 0 0 1 -18,28 a22,22 0 0 1 -38,4 a22,22 0 0 1 -42,-16 Z"/>` | ~122×88; phóng to bằng `scale()`. **Không ghi chữ bên trong.** Vẽ cloud sau các dây vào/ra để fill trắng che đầu dây (dây kéo vào trong viền vài px). Dây vào/ra có nhãn. |
| **Bus bundle** (concat) | `<rect class="s" width="25" height="h"/>` | nhãn vector phía trên (`TCR[31:0]`); field vào cạnh trái với nhãn `[i]`/`[m:l]` hoặc hằng; vector ra giữa cạnh phải. |
| **Bus split** | như bus bundle, đảo chiều | vector vào giữa cạnh trái; từng bit/field ra cạnh phải, nhãn `[i]`/`[m:l]`. |
| **Junction dot** | `<circle class="dot" r="4"/>` | tại mọi điểm rẽ nhánh (kể cả góc chữ T). Hai dây cắt nhau **không** có dot = không nối; hạn chế cắt nhau. |
| **Hằng số** | chỉ là chữ ở đầu dây | `<text text-anchor="end">32'h0</text>` cách đầu dây 5px. |

Phần tử chưa có ký hiệu ở đây (latch, tri-state, clock gate...) → hỏi người dùng mô tả, không tự chế.

## 4. Dây, nhãn, bố cục

- Dây `class="w"`, chỉ ngang/dọc, không mũi tên. Bus dùng cùng nét, phân biệt bằng nhãn `[msb:lsb]`.
- Font Calibri/Arial 13px, chữ đen. Tên tín hiệu, width, hằng, offset lấy đúng theo spec và bảng port.
- **Port của module**: dây có nhãn ở mép – input bên trái (nhãn `text-anchor="end"` ngay trước đầu dây), output bên phải (nhãn trên dây, sát đầu phải). Ghi width khi > 1 bit (`din_i[15:0]`). Bus chuẩn được gom một dây nhãn `prefix_*` (`s_apb_*`). **Không vẽ dây clk** (tam giác clock trên FF là đủ); tên reset port ghi dưới bubble.
- **Port của khối** (`u_`, `blk_`, `mem_`): tên port ghi **trên dây, sát cạnh khung, ở ngoài khung** – không bao giờ ghi bên trong khối. Dây vào cạnh trái: `<text x="edge−4" y="wire−4" text-anchor="end">`; dây ra cạnh phải: `x="edge+4" y="wire−4"`; dây dọc ở cạnh trên/dưới: chữ đặt cạnh dây, sát mép khung. Hai khối nối nhau: ghi tên port ở cả hai đầu, dây đủ dài để hai nhãn không chạm nhau. Tên net trong RTL ghi trong model (mục 5).
- Tín hiệu nội bộ: nhãn đặt trên dây gần nguồn (`int_set`, `acc_q[39:0]`), không đè lên dot hay dây khác.
- Luồng trái → phải: input → logic điều kiện → MUX → register → logic output/read mux → output. Feedback (Q → input `0` của MUX, Q → phép toán) đi vòng **phía trên** với junction dot tại điểm rẽ. Logic tạo select đặt phía trên hoặc dưới MUX nó điều khiển; dây select vào cạnh trên/dưới MUX.
- Khoảng cách ≥ 20px giữa dây song song; không chữ đè dây/khối, không khối chồng nhau; tránh dây cắt nhau bằng cách đổi thứ tự hàng hoặc đưa chân sang cạnh trên/dưới.
- Lint không kiểm bố cục: trước khi báo xong, rà lại toạ độ để chắc mọi dây nối đúng chân ở cả hai đầu, nhãn không chồng.

## 5. Model `<desc id="model">`

Model là phần **S3 đọc** để biết chính xác hành vi, nhất là phần bị gom (cloud, khối). Bản vẽ và model phải khớp nhau.

```text
// comment; dòng trước mục đầu tiên: ghi chú clock/reset, gán output trực tiếp
acc_o = acc_q;
[reg_acc]                                  // = id của nhóm <g id="reg_acc">
acc_q <= acc_d @(rst=40'h0);               // '<=' thanh ghi; @(rst=<giá trị reset>) khi có reset
[mux_clr]
acc_d = clr_i ? 40'h0 : acc_hold;          // '=' logic tổ hợp
[mem_buf]
reg [7:0] mem_q [0:15];                    // khai báo mảng
mem_q[wr_ptr_q] <= wr_data_i @(en=wr_en);  // ghi đồng bộ có enable
rd_data_o = mem_q[rd_ptr_q];
[blk_ctrl]                                 // phần bị gom: viết đủ, kể cả thanh ghi ẩn bên trong
count_q <= count_d @(rst=5'd0);
[u_eng]
dma_engine u_eng (.start_i(start_pulse), .busy_o(busy), .m_mem_*(m_mem_*));   // clk/rst ngầm hiểu
[u_lane]                                   // mảng instance: generate, ghi cách cắt bit từng bản sao
for (i = 0; i < 4; i = i + 1) mac_lane u_lane (.a_i(a[8*i +: 8]), .p_o(p[16*i +: 16]));
```

- Cú pháp kiểu Verilog-2005; `@(rst=...)`, `@(en=...)` là chú thích thanh ghi. `.s_apb_*(s_apb_*)` = nối bus theo tên cùng hậu tố.
- Mỗi `[id]` ứng với đúng một `<g id>`; nhóm `reg_`/`fsm_`/`mem_`/`cloud_`/`blk_`/`u_` bắt buộc có mục. Thêm mục cho `mux_`/`op_` khi giúp S3 đọc tên tín hiệu trung gian.
- Model không thêm phần cứng ngoài bản vẽ (trừ bên trong `cloud_`/`blk_`), không bịa tín hiệu ngoài spec; tín hiệu trung gian tự đặt tên theo kiểu `*_d`, `*_en`, `*_sel` và báo lại.

## 6. Góc nhìn scope (`--from/--to`)

`/rtl-s2-diagram <m> --from a,b --to x,y [--part <tên>]` → `doc/diagram/<m>/<m>_<part>.svg` (`<part>` mặc định = tín hiệu `--to` đầu tiên), header thêm `<!-- scope : from a, b to x, y -->`.

- Input của scope (`--from`) là dây nhãn ở mép trái, không vẽ ngược về nguồn; output (`--to`) là dây nhãn ở mép phải, không vẽ tiếp phía sau.
- Vẽ toàn bộ và chỉ logic nằm trên đường từ input tới output. Tín hiệu phụ cần thiết nhưng không thuộc input đã nêu (reset, địa chỉ, hằng) là dây nhãn ngắn, không mở rộng nguồn.
- Mức chi tiết và quy trình đề xuất/duyệt như mục 2, theo level của module.
- Tên tín hiệu không có trong spec hoặc scope mơ hồ → hỏi lại trước khi vẽ.
- Là góc nhìn phụ: không thay `<m>.svg`, S3 không đọc, lint không kiểm phủ port.

## 7. Mẫu `<m>_notes.md` (tùy chọn – chỉ khi SKILL.md Bước 4 cần)

Chỉ ghi điều diagram, model và spec chưa nói rõ; không liệt kê lại từng ký hiệu, không cột ID truy vết. Dòng đầu ghi level. Phần mô tả tiếng Anh trước + bản dịch `_VI:_`; bảng chỉ tiếng Anh.

```markdown
# <m> – Design notes / Ghi chú thiết kế
Level: L1 · Diagram: <m>.svg

## Implementation / Hiện thực
| Block | Planned RTL implementation | Notes |
| --- | --- | --- |
| `mem_buf` | `reg [DATA_W-1:0] mem_q [0:DEPTH-1]`, no reset | written when `wr_en` |
| `fsm_ctl` | `state_q` + `localparam` STATE_IDLE/RUN/DONE | state transitions: see the spec Behavior section |
| `u_lane` (x 4) | `generate for` (`genvar i`) + `mac_lane` | 4 lanes |

## Internal nets (L0 with many instances) / Net nội bộ
| Net | Width | Source (inst.port) | Destination (inst.port) |
| --- | --- | --- | --- |
| `start_pulse` | 1 | `u_regs.start_o` | `u_eng.start_i` |
```

Bus chuẩn có thể ghi một dòng cho cả nhóm (`m_mem_*`, nối theo tên cùng hậu tố).

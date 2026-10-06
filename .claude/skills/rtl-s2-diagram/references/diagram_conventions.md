# Quy ước diagram Mermaid (stage 2, mọi level)

Mục lục: 1. Khung file · 2. Ký hiệu phần tử · 3. Cạnh · 4. Bố cục sạch · 5. Cú pháp an toàn · 6. Style · 7. Mẫu `<m>_notes.md` (tùy chọn) · 8. HTML schematic (leaf L2, tùy chọn)

Mục tiêu: nhìn diagram hiểu kiến trúc và viết được RTL; dán vào https://mermaid.live là render (Mermaid v11, `flowchart`). Ví dụ đã parse thành công: `example_l0_dma_top.mmd`, `example_l1_sync_fifo.mmd`, `example_l2_acc_unit.mmd`.

Diagram là mô hình kiến trúc, không phải netlist: một khối diagram có thể thành nhiều câu lệnh RTL, nhiều tín hiệu RTL có thể nằm trong một khối.

## 1. Khung file

```text
%% module : <m>
%% stage  : 2 - diagram L0 | L1 | L2      <- gate S3 đọc level từ dòng này
%% nguon  : <file spec đã dùng>
%% param  : <giá trị parameter dùng để ghi width>   (nếu có)
%% mo tren: https://mermaid.live
flowchart LR
  %% ===== INPUT PORTS =====      ngoài subgraph, bên trái
  %% ===== OUTPUT PORTS =====     ngoài subgraph, bên phải
  subgraph M_<m>["<m>"]
    direction LR
    ... phần tử bên trong, khai báo theo thứ tự dòng dữ liệu ...
  end
  %% ===== DATA =====             cạnh nét liền
  %% ===== CONTROL =====          cạnh nét đứt
  %% ===== STYLE =====            classDef + class
```

Comment `%%` chỉ dùng ASCII không dấu. Nhãn trong nháy kép được dùng tiếng Việt có dấu.

## 2. Ký hiệu phần tử

| Phần tử | Level | Tiền tố id | Cú pháp | Nhãn | class |
| --- | --- | --- | --- | --- | --- |
| Input port | mọi | `pi_` | `pi_din>"din_i [15:0]"]` | tên + `[msb:0]` | `port` |
| Output port | mọi | `po_` | `po_acc(["acc_o [39:0]"])` | tên + `[msb:0]` | `port` |
| Nhóm bus | mọi | `pi_`/`po_` | `pi_apb>"s_apb_* : APB4, ADDR 12, DATA 32"]` | `prefix_*` + giao thức | `port` |
| Instance module con | L0, L1 | `u_` | `u_eng[["u_eng : dma_engine"]]` | `instance : module` | `inst` |
| Mảng instance (generate) | L0, L1 | `gen_` | `gen_lane[["gen_lane × 4 : mac_lane"]]` | số bản sao | `inst` |
| Thanh ghi / nhóm thanh ghi / mảng | mọi | `reg_` | `reg_cnt["count_q [2:0]<br/>rst = 0"]` | tên `_q`, width/kích thước, reset nếu có | `reg` |
| FSM (thanh ghi trạng thái + next-state) | mọi | `fsm_` | `fsm_ctl["FSM state_q<br/>IDLE → RUN → DONE"]` | tên thanh ghi, trạng thái chính | `reg` |
| Bộ nhớ (SRAM/RF macro) | L1, L2 | `mem_` | `mem_buf[("SRAM 256x16")]` | kích thước | `reg` |
| Khối logic tổ hợp | mọi | `blk_` | `blk_nxt["NEXT COUNT<br/>clr: 0 ; en: +1"]` | chức năng + phương trình chính | `blk` |
| MUX chọn dữ liệu chính | L1, L2 | `mux_` | `mux_sel[/"MUX sel=mode_q<br/>0: a ; 1: b"\]` | select, các ngõ | `mux` |
| Phép toán là điểm chính kiến trúc | L1, L2 | `op_` | `op_mul(("×"))` | phép toán | `arith` |
| Glue logic nhỏ ở mức tích hợp | L0 | `glue_` | `glue_irq["irq_o = irq_raw AND irq_en"]` | phương trình | `logic` |
| Ghi chú | mọi | `n_` | `n_clkrst["..."]` | | `note` |

`ff_` vẫn được chấp nhận như `reg_` (diagram cũ).

**Gom, đừng tách.** Các thứ sau nằm trong nhãn của khối `blk_`/`reg_`, không thành node riêng: cổng AND/OR/NOT, hằng số, comparator nhỏ, mở rộng dấu, cắt bit, tín hiệu tạm, enable của thanh ghi. Tách thành node riêng chỉ khi nó định hình kiến trúc (bộ nhân dùng chung, MUX chọn nguồn dữ liệu, bộ so sánh quyết định luồng).

Clock/reset: vẽ `clk_i`, `rst_n_i` như port, nối nét đứt tới **một** node `n_clkrst`, không kéo dây tới từng thanh ghi. Thanh ghi dùng clock/reset khác ghi rõ trong nhãn.

## 3. Cạnh

| Loại | Cú pháp | Nhãn |
| --- | --- | --- |
| Dữ liệu | `a -->|"sum [39:0]"| b` | tên tín hiệu + width |
| Điều khiển (select, enable, clear, start, done) | `a -.->|"sel"| b` | tên hoặc vai trò tại đích |
| Bus nhóm | `a -->|"m_mem_*"| b` | tên nhóm |

Một nguồn tới nhiều đích → nhiều cạnh từ cùng node; không tạo node fan-out. Ở L0, nhãn cạnh dùng đúng tên net sẽ dùng trong RTL.

## 4. Bố cục sạch

- `flowchart LR`; input bên trái, output bên phải; dữ liệu đi trái → phải.
- Khai báo node theo thứ tự dòng dữ liệu – Mermaid xếp node theo thứ tự xuất hiện, nên khai báo đúng thứ tự giảm đường chéo.
- Nhãn ngắn: tối đa 3 dòng `<br/>`.
- Gom tín hiệu điều khiển cùng nguồn–đích vào một cạnh (`"wr_en, rd_en"`) thay vì nhiều cạnh song song.
- L1 pipeline: mỗi tầng một `subgraph S1["Tầng 1"]` lồng trong subgraph module.
- Nhiều clock domain: mỗi domain một subgraph, điểm CDC là node riêng.
- Diagram quá ~30–40 node thường là dấu hiệu đang vẽ quá chi tiết → gom trước khi nghĩ tới chia file.

## 5. Cú pháp an toàn (đã kiểm với parser Mermaid 11)

- Mọi nhãn node và nhãn cạnh đặt trong nháy kép `"..."`. Trong nhãn không dùng `"` (thay `#quot;`) và không dùng `|` (dùng `;`).
- Xuống dòng: `<br/>`. So sánh/toán tử dùng `≥ ≤ ≠ × −` thay vì `>= <= * -`.
- id node: chữ, số, `_`; không trùng từ khóa (`end`, `subgraph`, `class`, `style`, `graph`, `flowchart`, `click`, `direction`); không bắt đầu bằng `o` hoặc `x`. Các tiền tố ở mục 2 đã tránh được.
- Hình: MUX `[/"..."\]` · lục giác `{{"..."}}` · tròn `(("..."))` · stadium `(["..."])` · cờ `>"..."]` · subroutine `[["..."]]` · cylinder `[("...")]`.
- Mỗi `subgraph` có `end` riêng một dòng. Không dùng cú pháp `@{ shape: ... }`.

## 6. Style (copy nguyên khối, xóa class không dùng)

```text
  classDef port fill:#e8eaf6,stroke:#3949ab,color:#1a237e
  classDef reg fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#3e2723
  classDef blk fill:#e3f2fd,stroke:#1565c0,color:#0d47a1
  classDef mux fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20
  classDef arith fill:#e3f2fd,stroke:#1565c0,color:#0d47a1
  classDef logic fill:#f5f5f5,stroke:#616161,color:#212121
  classDef inst fill:#ede7f6,stroke:#5e35b1,stroke-width:2px,color:#311b92
  classDef note fill:#fffde7,stroke:#f9a825,stroke-dasharray:4 3,color:#5d4037
```

## 7. Mẫu `<m>_notes.md` (tùy chọn – chỉ khi SKILL.md Bước 4 cần)

Chỉ ghi điều diagram và spec chưa nói rõ; không liệt kê lại từng node, không cột ID truy vết. Dòng đầu ghi level.

```markdown
# <m> – Ghi chú thiết kế
Level: L1 · Diagram: <m>.mmd

## Hiện thực
| Khối | Hiện thực RTL dự kiến | Ghi chú |
| --- | --- | --- |
| `reg_mem` | `reg [DATA_W-1:0] mem_q [0:DEPTH-1]`, không reset | ghi khi `wr_en` |
| `fsm_ctl` | `state_q` + `localparam` STATE_IDLE/RUN/DONE | chuyển trạng thái: xem spec mục Hành vi |
| `gen_lane` | `generate for` (`genvar i`) + `mac_lane` | 4 lane |

## Net nội bộ (L0 nhiều instance)
| Net | Width | Nguồn (inst.port) | Đích (inst.port) |
| --- | --- | --- | --- |
| `start_pulse` | 1 | `u_regs.start_o` | `u_eng.start_i` |
```

Bus chuẩn có thể ghi một dòng cho cả nhóm (`m_mem_*`, nối theo tên cùng hậu tố).

## 8. HTML schematic (leaf L2, tùy chọn)

Hai định dạng, hai vai trò – cùng một mô hình kiến trúc:

| | `<m>.mmd` (Mermaid) | `<m>.html` (RTL schematic) |
| --- | --- | --- |
| Trả lời | "Module gồm những khối nào?" | "Các khối phần cứng nối với nhau thế nào?" |
| Mức | khối kiến trúc (mục 1–6, gom logic nhỏ) | primitive RTL: DFF, MUX, comparator, AND/OR/XOR/NOT, + − × <<, hằng, port, dây |
| Vai trò | diagram chính thức, S3 đọc | bản xem trực quan cho người thiết kế, không stage nào đọc |

`scripts/render_html.py` nhận **mô hình khối** (chính `<m>.mmd`, hoặc stdin) + **lớp chi tiết RTL** bên dưới, dịch thành netlist primitive, đối chiếu với mô hình khối, rồi tự layout. Quy tắc Mermaid ở mục 1–6 không đổi; lớp chi tiết không ghi vào `.mmd`.

### 8.1 Lớp chi tiết RTL

Phương trình kiểu Verilog-2005, nhóm theo node của mô hình. Viết từ spec + mô hình khối, đúng như RTL sẽ hiện thực – không thêm, không bớt phần cứng.

```text
localparam IDLE = 2'd0, RUN = 2'd1;      // tùy chọn: tên hằng hiện trên schematic
wire [31:0] data_d;                      // tùy chọn: width khi không suy ra được
reg  [7:0]  mem_q [0:15];                // bộ nhớ (chỉ trong khối mem_)

[blk_dec]                                // = id node trong mô hình
addr_hit = paddr_i == 10'h000;           // '=' : logic tổ hợp
wr_hit   = psel_i & penable_i & pwrite_i & addr_hit;
[mux_wd]
data_d   = wr_hit ? pwdata_i : data_q;   // ?: → MUX 2:1, case → MUX N:1
[reg_data]
data_q  <= data_d @(rst=32'h0);          // '<=' : thanh ghi; @(rst=, en=, clk=, reset=)
data_o   = data_q;                       // gán thẳng tên/hằng/cắt bit = nối dây, không sinh phần tử
[mux_rd]
prdata_o = case (paddr_i)
             10'h000: data_q;
             10'h004: {24'h0, status_i};
             default: 32'hDEADBEEF;
           endcase;
```

- Toán tử: `== != < <= > >=` · `& && | || ^ ~^ ~ !` · rút gọn `&x |x ^x` · `+ - * / % << >> <<< >>>` · `?:` · `case (s) K: e; …; default: e; endcase` · `{a, b}` · `{n{a}}` · `x[i]`, `x[m:l]` · `mem_q[addr]` · `( )`. Comment `//`, `/* */`.
- Thanh ghi: `@(rst=<giá trị reset>)` khi thanh ghi có reset (thiếu → vẽ không chân RST); `@(en=<biểu thức>)` khi spec mô tả clock-enable (vẽ chân EN); enable dạng giữ giá trị viết `x_d = en ? d : x_q` (vẽ MUX feedback). Clock/reset mặc định là input port duy nhất có tên chứa `clk`/`rst` (hoặc `clock`/`reset`); nhiều hơn một → ghi `clk=`/`reset=`.
- Width lấy theo thứ tự: khai báo trong lớp chi tiết → bảng port (`--interface`) → nhãn `tên [m:l]` trong mô hình → suy ra từ biểu thức.

Kiểm tra bắt buộc (sai → không ghi HTML):

| Luật | Ý nghĩa |
| --- | --- |
| mỗi khối bên trong của mô hình có ít nhất một phương trình | HTML không bỏ sót khối |
| `<=` chỉ trong `reg_`/`ff_`/`fsm_`, ghi bộ nhớ chỉ trong `mem_` | không bịa thanh ghi/bộ nhớ |
| `reg_`/`fsm_` có DFF, `mux_` có MUX, `op_` có phép toán/so sánh | khối giữ đúng vai trò |
| tín hiệu đi từ khối A sang khối B ⇔ mô hình có cạnh A → B | cùng kết nối với `.mmd` (clock/reset ra khỏi phép so) |
| mọi tín hiệu có nguồn, mọi output được gán, không gán hai lần | netlist đầy đủ |

### 8.2 Ánh xạ sang schematic

| Lớp chi tiết | Phần tử vẽ |
| --- | --- |
| `q <= d` | DFF: chân D, Q, ▷ clock, RST (vòng tròn khi active-low), EN nếu có; tên `q` ở trên, `[w] rst=…` ở dưới |
| `s ? a : b`, `case` | hình thang MUX, nhãn từng ngõ (`0`/`1`, giá trị case), select vào cạnh dưới |
| `== != < <= > >=` | khối comparator ghi toán tử (A/B khi không giao hoán) |
| `+ − × ÷ << >>`, `x[sel]` | vòng tròn phép toán |
| `& \| ^ ~` (2+ ngõ gộp thành một cổng) | ký hiệu cổng AND/OR/XOR/NOT chuẩn, bubble cho NAND/NOR/XNOR |
| hằng, `localparam` | hộp nhỏ gắn ngay tại chân dùng nó (`10'h000`, `LOCK`) |
| `{a, b}`, `{n{a}}` | thanh concat |
| `mem_q[a] <= d`, `mem_q[a]` | khối MEM: WA, WD, WE, RA/RD, ▷ |
| port | mũi tên ngũ giác ngoài khung module, tên + `[m:0]` |

Dây: dữ liệu nét liền, bus (width > 1) nét đậm, điều khiển (1 bit chỉ đi vào select/enable/điều kiện) nét đứt, clock/reset nét gạch-chấm – phân biệt được khi in trắng đen. Nhãn `tên[m:0]` đặt ngay sau chân nguồn; cắt bit (`[15]`) và tên tín hiệu feedback đặt trước chân đích; chấm tròn tại điểm rẽ nhánh.

### 8.3 Layout

Phân lớp trái → phải theo đường dài nhất từ input (port vào cột trái, port ra cột phải, node được kéo về sát nơi dùng); cạnh ra từ Q của thanh ghi/bộ nhớ tạo vòng thì thành **feedback**, đi lên lane phía trên rồi vòng về; clock/reset là **rail** phía dưới, rẽ lên từng chân ▷/RST. Thứ tự trong cột: barycenter theo vị trí chân, giữ phương án ít giao cắt nhất; tọa độ y căn chân thẳng hàng rồi nắn các dây lệch vài px. Dây chỉ ngang/dọc, đi trong kênh giữa hai cột, mỗi net một track dọc, track xếp theo số giao cắt ít nhất. HTML tự chứa (HTML + CSS + SVG inline + JS nhỏ): zoom (lăn chuột, nút), kéo để di chuyển, vừa khung, rê lên phần tử để làm sáng các phần tử cùng khối mô hình, nhấp dây để tô cả net. Mô hình khối và lớp chi tiết được nhúng (`<script type="application/json" id="arch-model">`) để `render_html.py --check … --mmd …` kiểm lại.

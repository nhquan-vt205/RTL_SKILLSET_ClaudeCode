# Quy trình viết spec (stage 1)

Mục lục: 1. Nguồn chính · 2. Hierarchy · 3. Khi nào tách file · 4. Spec chế độ đơn · 5. Spec chế độ phân cấp · 6. File tách tùy chọn · 7. Kiểm tra

Nguyên tắc: **viết vừa đủ để bước sau không phải đoán.** Độ dài tỉ lệ với thiết kế. Mục không áp dụng thì bỏ hẳn, không ghi "N/A" cho đủ khung. Một file rõ ràng tốt hơn nhiều file rời rạc.

Ngôn ngữ của file spec được tạo (`CLAUDE.md`): phần mô tả tiếng Anh trước, rồi bản dịch tiếng Việt đánh dấu `_VI:_`; tiêu đề mô tả có thể song ngữ (`## Function / Chức năng`). Mọi bảng chỉ tiếng Anh. Tên định danh, địa chỉ, ID, code, công thức và dấu hiệu máy đọc (`Type: … · Level: … · Status: …`, `STATUS:`, `## Module list`, cột `Port name`) giữ tiếng Anh, không dịch.

## 1. Nguồn chính

Mỗi thông tin có **một nơi chính**; nơi khác tham chiếu, không chép lại. Nơi chính có thể là một mục trong file spec duy nhất.

| Thông tin | Nơi chính (module nhỏ) | Nơi chính (khi đã tách file) |
| --- | --- | --- |
| Hierarchy | – (một module) | `spec_status.md` |
| Chức năng, cấu trúc, hành vi, reset | `<m>_spec.md` | `architecture/<m>_spec.md` |
| Port, parameter | mục Interface trong spec | `interface/<m>_interface.md`, `interface/00_parameters.md` |
| Thanh ghi phần mềm | mục Thanh ghi trong spec | `register_file/register_map.md` |
| Luồng dữ liệu / điều khiển, FSM | mục Hành vi trong spec | `datapath/`, `controlpath/` |

## 2. Hierarchy

### 2.1 Chia / gộp / giữ

| Quyết định | Khi nào |
| --- | --- |
| Giữ | Khối có 1 chức năng rõ, interface gọn – mặc định |
| Chia | > 1 chức năng độc lập; nhiều clock domain; control phức tạp trộn với datapath lớn đến mức khó đọc; phần tái sử dụng (FIFO, sync, regfile) |
| Gộp | Hai khối luôn đi cùng nhau và nối bằng rất nhiều tín hiệu; khối chỉ vài cổng logic |

Không chia để tăng số module. Thiết kế nhỏ: một module duy nhất.

### 2.2 Loại và level

- **Loại:** `top` (gốc có module con), `block` (có module con), `leaf` (không có module con). Module đơn là `leaf`.
- **Level** (đề xuất cho S2): `L0` cho module có module con mà logic riêng chỉ là nối dây/glue; `L2` cho leaf nhỏ mà diagram thanh ghi + logic chính còn đọc được trên một màn hình; `L1` cho leaf lớn hoặc có mảng/pipeline/generate, và cho block có nhiều logic riêng.
- Level gán theo từng module, không theo cấp cây: leaf nhỏ trong IP lớn vẫn là L2.

## 3. Khi nào tách file

Mặc định **không tách**. Tạo file riêng chỉ khi điều kiện tương ứng đúng:

| File | Tạo khi |
| --- | --- |
| `spec_status.md` | Có từ 2 module trở lên hoặc có quan hệ cha–con |
| `architecture/<m>_spec.md` | Chế độ phân cấp (thay cho `doc/spec/<m>_spec.md`) |
| `interface/<m>_interface.md` | Interface lớn khó đọc trong spec (vd. nhiều bus, cỡ ~20 port trở lên) hoặc module khác cần tham chiếu riêng |
| `interface/00_parameters.md` | Nhiều parameter dùng chung giữa các module, hoặc chuỗi suy width từ công thức phức tạp |
| `register_file/register_map.md` | Có thanh ghi phần mềm **và** register map đủ lớn để làm spec khó đọc (vd. cỡ ~6 thanh ghi trở lên, nhiều nhóm thanh ghi) hoặc nhiều module dùng |
| `datapath/00_datapath_overview.md` | Nhiều luồng dữ liệu đi qua nhiều module |
| `controlpath/00_control_overview.md` | Trình tự điều khiển giữa nhiều module cần mô tả theo chu kỳ |
| `controlpath/<m>_fsm.md` | FSM/điều khiển phức tạp (vd. cỡ ~6 trạng thái trở lên, nhiều pha) làm spec module khó đọc |

Không thỏa → viết thành một mục trong spec của module. Không tạo file chỉ để giữ metadata, truy vết, hay vì template có mục đó.

**Các con số trên là gợi ý về độ phức tạp, không phải ngưỡng bắt buộc.** Câu hỏi quyết định là: tài liệu hiện tại có còn dễ đọc không? Module 24 port nhưng datapath đơn giản, ít thanh ghi vẫn có thể giữ một file spec; module 10–12 port nhưng điều khiển nhiều pha, nhiều nhóm thanh ghi có thể tách dù chưa chạm con số nào. Không dùng điểm số hay công thức để quyết định.

`spec_status.md` ghi hierarchy, nó không quyết định project có phân cấp hay không: thiết kế có quan hệ cha–con là phân cấp dù file này chưa tồn tại – khi đó tạo nó với hierarchy thật.

```text
doc/spec/
├── source/                 # INPUT – chỉ đọc
├── <m>_spec.md             # chế độ đơn: tất cả trong một file
│
├── spec_status.md          # chế độ phân cấp: hierarchy + trạng thái + OPEN
├── architecture/<m>_spec.md
└── interface/ register_file/ datapath/ controlpath/   # chỉ khi cần (bảng trên)
```

Quy ước tên (input có quy ước riêng thì input thắng, ghi lại trong spec):

| Đối tượng | Quy ước | Ví dụ |
| --- | --- | --- |
| Module | `snake_case` | `fft_bfly` |
| Port in / out | `_i` / `_o` | `din_valid_i`, `result_o` |
| Thanh ghi / giá trị kế tiếp | `_q` / `_d` | `acc_q`, `acc_d` |
| Active-low | `_n` | `rst_n_i` |
| Handshake | `<bus>_valid`, `<bus>_ready`, `<bus>_data` | `pix_valid_i` |
| Bus chuẩn | tiền tố + chuẩn | `s_apb_*`, `m_axi_*` |
| Parameter, tên thanh ghi | `UPPER_SNAKE_CASE` | `DATA_W`, `CTRL.START` |
| Giả định | `OPEN-<số>` | `OPEN-001` |
| Truy vết (chỉ IP lớn) | `REQ-<nhóm>-<số>` | `REQ-FUNC-003` |

## 4. Spec chế độ đơn – `doc/spec/<m>_spec.md`

Một file chứa mọi thứ S2/S3 cần. Ví dụ đủ cho một counter:

```markdown
# pulse_cnt – Specification / Đặc tả
Type: leaf · Level: L2 · Status: PASS

## Function / Chức năng
Counts `pulse_i` pulses while `en_i` = 1, as a 3-bit wrap-around counter; `clr_i` clears it to 0 (priority over counting).

_VI:_ Đếm số xung `pulse_i` khi `en_i` = 1, đếm 3 bit wrap-around; `clr_i` xóa về 0 (ưu tiên hơn đếm).

## Interface
Clock `clk_i` rising edge · Reset `rst_n_i` async active-low

_VI:_ Clock `clk_i` sườn lên · Reset `rst_n_i` async active-low

| Port name | Direction | Width | Description |
| --- | --- | --- | --- |
| `clk_i` | in | 1 | Clock |
| `rst_n_i` | in | 1 | Async active-low reset |
| `en_i` | in | 1 | Count enable |
| `pulse_i` | in | 1 | Pulse to count, synchronous to `clk_i` |
| `clr_i` | in | 1 | Counter clear |
| `count_o` | out | 3 | Count value |

## Behavior / Hành vi
- On each rising edge: `clr_i` → 0; otherwise `en_i & pulse_i` → `count + 1` (7 → 0); otherwise hold.
  - _VI:_ Mỗi sườn lên: `clr_i` → 0; ngược lại `en_i & pulse_i` → `count + 1` (7 → 0); ngược lại giữ.
- `count_o` comes directly from the register (no extra latency).
  - _VI:_ `count_o` lấy trực tiếp từ thanh ghi (không latency thêm).

## Reset
`count` = 0.
```

Các mục thường có, chỉ viết mục áp dụng: **Chức năng** · **Tham số** (bảng `| Parameter | Default | Meaning |`) · **Interface** · **Thanh ghi** (nếu có bus cấu hình, bảng mục 6.1) · **Cấu trúc** (chỉ khi không hiển nhiên: thanh ghi chính, bộ nhớ, FSM, ánh xạ công thức → phần cứng, định dạng số) · **Hành vi** (theo chu kỳ, FSM dạng bảng chuyển nếu có, latency nếu spec yêu cầu, xử lý input không hợp lệ – xem C9 trong `input_criteria.md`) · **Reset** · **OPEN** (bảng `| ID | Description | Interim assumption |`, chỉ khi có; giả định về clock/reset hay input không hợp lệ nằm ở đây).

Dòng thứ hai `Type: … · Level: … · Status: PASS|FAIL` là bắt buộc – gate S2–S5 đọc dòng này.

### Bảng port

| Cột | Bắt buộc | Ghi chú |
| --- | --- | --- |
| `Port name` | có | script nhận diện bảng port bằng cột này |
| `Direction` | có | `in` / `out` / `inout` |
| `Width` | có | số (`8`) hoặc parameter kèm giá trị mặc định trong ngoặc: `DATA_W (8)` |
| `Description` | có | định dạng số (signed, Qm.n) nếu là dữ liệu số học |
| `Type` | chế độ phân cấp | `DATA` · `CTRL` · `STATUS` · `CLK/RST` |
| `Connects to` | chế độ phân cấp, trừ port của top | xem mục 5.2 |

Bus chuẩn (APB, AXI…) có thể ghi một dòng đại diện `s_apb_*` + chuẩn + độ rộng, liệt kê riêng tín hiệu ngoài chuẩn.

## 5. Spec chế độ phân cấp

### 5.1 `architecture/<m>_spec.md`

```markdown
# <m> – Specification / Đặc tả
Type: leaf | block | top · Parent: <parent | –> · Level: L0 | L1 | L2

## Function / Chức năng
## Interface        → bảng port (mục 4) hoặc tham chiếu interface/<m>_interface.md
## Structure / Cấu trúc
  leaf:      thanh ghi/mảng chính, bộ nhớ, FSM, ánh xạ công thức → phần cứng, định dạng số
  block/top: bảng | Instance | Module | Role |, glue logic nếu có
## Behavior / Hành vi   theo chu kỳ, latency (nếu input yêu cầu), back-pressure, lỗi, reset
```

**Spec top** thêm ở đầu `## Project overview / Tổng quan dự án`: chức năng IP, clock/reset (điểm CDC nếu có), sơ đồ khối Mermaid các module con trực tiếp (`flowchart LR`, mũi tên = có kết nối, nhãn = tên bus ngắn, tiếng Anh), 2–5 dòng lý do phân rã. Bảng REQ (`| REQ ID | Description | Implemented by |`) chỉ khi input có nhiều yêu cầu cần truy vết. Không chép lại cây hierarchy (đã có trong `spec_status.md`).

### 5.2 Cột `Connects to`

Script `check_interface.py` đọc cột này để kiểm nối dây giữa các module:

- `module.port`, nhiều đích cách bằng dấu phẩy. Port của top nối ra ngoài: `external`.
- Con nối thẳng lên port của cha: `<parent>.port` (cùng hướng). Nối với anh em: `<sibling>.port` (ngược hướng).
- Input của con lái bởi glue logic trong cha: `<parent> (glue: <expression>)`. Nhiều instance cùng module: `mac_lane[i].din_i`.

## 6. File tách tùy chọn

Chỉ khi thỏa bảng mục 3. Nội dung giống hệt khi viết thành mục trong spec.

### 6.1 Thanh ghi

Đầu mục/file: bus, base address, độ rộng, hành vi địa chỉ không tồn tại. Rồi:

```markdown
| Offset | Name | Bit | Field | Access | Reset | Description |
| --- | --- | --- | --- | --- | --- | --- |
| 0x00 | CTRL | 0 | EN | RW | 0 | Module enable |
```

### 6.2 Parameter dùng chung – `interface/00_parameters.md`

Bảng parameter + bảng width suy từ công thức `| Variable | Format | Width | Derived from | Rounding / saturation |`. Quy tắc: cộng N+N → N+1; nhân N×M → N+M; tích lũy K phần tử → +⌈log2 K⌉.

### 6.3 Datapath / control path

- `datapath/00_datapath_overview.md`: mỗi luồng – chuỗi khối, width, định dạng, biến đổi; latency nếu spec yêu cầu. Gắn `DAT-xxx` chỉ khi cần tham chiếu chéo.
- `controlpath/00_control_overview.md`: tín hiệu điều khiển giữa module (nguồn, đích, mức/xung, tác dụng) và các kịch bản chính theo chu kỳ. Gắn `CTL-xxx` chỉ khi cần tham chiếu chéo.
- `controlpath/<m>_fsm.md`: bảng trạng thái, bảng chuyển `| From | To | Condition |`, trạng thái sau reset. Sơ đồ `stateDiagram-v2` (nhãn tiếng Anh) nếu giúp đọc.

## 7. Kiểm tra trước khi PASS

| # | Kiểm tra | Đạt khi |
| --- | --- | --- |
| 1 | `check_interface.py` | 0 lỗi |
| 2 | Đủ để thiết kế | Mỗi output được xác định từ input/thanh ghi nào, khi nào; reset của mọi trạng thái rõ |
| 3 | Width | Width nhất quán giữa các nơi và đúng công thức; phép số học có định dạng số |
| 4 | FSM / điều khiển | Mỗi FSM không có trạng thái chết; mỗi enable/select quan trọng có điều kiện rõ |
| 5 | Hierarchy (phân cấp) | Mỗi module trong bảng có spec + bảng port; module có con liệt kê đủ con |
| 6 | Yêu cầu bắt buộc | Latency/throughput mà input yêu cầu (nếu có) đạt được với kiến trúc đã chọn |
| 7 | OPEN | Mỗi OPEN có giả định tạm cụ thể; không OPEN nào để chức năng, interface, register map, width, latency bắt buộc hay kiến trúc ở trạng thái phải đoán. OPEN nhỏ mà đổi giả định chỉ là sửa cục bộ vẫn cho phép PASS |
| 8 | Clock/reset, input không hợp lệ | Lấy từ input hoặc convention có sẵn của project; không có thì ghi rõ là giả định (mục OPEN), không viết như yêu cầu của input |
| 9 | Ngôn ngữ | Phần mô tả tiếng Anh trước + bản dịch tiếng Việt trung thành; mọi bảng chỉ tiếng Anh; tên định danh và dấu hiệu máy đọc không dịch |

Kết quả kiểm tra báo trong chat, không ghi bảng kiểm tra vào file.

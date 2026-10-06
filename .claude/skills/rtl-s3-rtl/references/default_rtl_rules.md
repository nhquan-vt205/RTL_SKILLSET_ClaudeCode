# Rule RTL mặc định (chỉ dùng cho chỗ coding_rules/ không nói tới)

File trong `coding_rules/` luôn thắng. Mục tiêu của các rule dưới: code đọc được, **nhìn vào thấy phần cứng** (thanh ghi → logic tổ hợp → mux/số học/so sánh → thanh ghi → output), tổng hợp được, chạy được trên công cụ miễn phí (Icarus Verilog ≥ 11 với `-g2005`, Verilator ≥ 5 với `--default-language 1364-2005`).

## Ngôn ngữ và file

- **Verilog-2005 (IEEE 1364-2005)**, đuôi `.v`, một module một file, tên file = tên module, đặt trong `rtl/`.
- Construct dùng: `wire`, `reg`, `always @(posedge ...)`, `always @(*)`, `assign`, `localparam`, `parameter` (chỉ khi spec yêu cầu cấu hình), mảng bộ nhớ `reg [7:0] mem_q [0:15]`, `generate for` với `genvar`, `function` nhỏ, `$clog2` (chỉ trong biểu thức hằng của parameter).
- **Cấm** (là SystemVerilog, parser Verilog-2005 không hiểu): `logic`, `bit`, `always_ff`, `always_comb`, `always_latch`, `typedef`, `enum`, `struct`, `union`, `interface`/`modport`, `package`/`import`, `class`, `virtual`, `unique`/`priority case`, `inside`, `foreach`, mảng động/queue/mailbox, cast `type'(...)` / `W'(...)`, literal `'0`/`'1`, assignment pattern `'{...}`, `assert`/`property` (SVA), port kiểu mảng.
- `` `default_nettype none `` đầu file, `` `default_nettype wire `` cuối file.

## Khai báo

- Port kiểu ANSI (Verilog-2001/2005), mỗi port một dòng, comment ngắn cuối dòng; thứ tự như bảng port.
- `wire` cho tín hiệu gán bằng `assign`, output module con, net nội bộ. `reg` cho mọi tín hiệu gán trong `always` (thanh ghi `_q` và cả giá trị kế tiếp `_d`). Output gán trong `always` khai báo `output reg [..]`; output gán bằng `assign` khai báo `output [..]` (`output wire`).
- Tín hiệu trung gian (`_d`, enable, cờ) khai báo tự do khi giúp code rõ – không cần có node tương ứng trong diagram.
- Hằng số đủ width (`8'd0`, `{W{1'b0}}`), không dùng `0` trơn cho bus khác 32 bit.
- Phép có dấu: khai báo `signed`, mở rộng dấu tường minh (`{{8{x[15]}}, x}` hoặc `$signed`).

## Parameter và hằng

- **Spec nói cấu hình được** (vd. "DATA_WIDTH configurable", bảng parameter) → `parameter`, và mọi width liên quan viết theo parameter.
- **Spec cố định** (counter 8 bit, ngưỡng 16 bit, 4 thanh ghi) → width/hằng viết thẳng: `reg [7:0] count_q;`. Không tự tạo `parameter` chỉ để code "generic" hay "tái sử dụng".
- `localparam` cho mã trạng thái FSM, địa chỉ thanh ghi, ngưỡng cố định, hằng kiến trúc có tên – dùng khi đặt tên làm code dễ đọc hơn, không lạm dụng.

## Tuần tự và tổ hợp

- Thanh ghi: `always @(posedge clk_i or negedge rst_n_i)` (reset async active-low; theo spec nếu khác – reset đồng bộ chỉ có `posedge clk_i`). Chỉ `<=` trong khối tuần tự, chỉ `=` trong khối tổ hợp. Không `#delay`.
- Nhóm thanh ghi cùng enable/reset được viết chung một khối; mảng dữ liệu không cần reset (bộ nhớ) viết khối riêng không reset.
- Tổ hợp: `always @(*)` hoặc `assign`; gán mặc định ở đầu `always @(*)` (`count_d = count_q;`) để tránh latch. `case` luôn có `default`.
- Mẫu ưu tiên cho thanh ghi có logic next-value (nhìn thấy thanh ghi + mux/cộng):

  ```verilog
  always @(*) begin
    acc_d = acc_q;
    if (clr_i) begin
      acc_d = 8'd0;
    end
    else if (en_i) begin
      acc_d = acc_q + data_i;
    end
  end

  always @(posedge clk_i or negedge rst_n_i) begin
    if (!rst_n_i) begin
      acc_q <= 8'd0;
    end
    else begin
      acc_q <= acc_d;
    end
  end

  assign acc_o = acc_q;
  ```

  Logic rất đơn giản (một enable, một biểu thức) có thể viết thẳng trong khối tuần tự; không bắt buộc tách `_d` khi không giúp đọc.

## FSM

`localparam` cho mã trạng thái + `reg` thanh ghi trạng thái + khối `always @(*)` tính trạng thái kế tiếp (và output nếu là Moore/Mealy tổ hợp). Trạng thái không hợp lệ về trạng thái an toàn (thường IDLE).

```verilog
localparam STATE_IDLE = 2'b00;
localparam STATE_RUN  = 2'b01;
localparam STATE_DONE = 2'b10;

reg [1:0] state_q;
reg [1:0] state_d;

always @(posedge clk_i or negedge rst_n_i) begin
  if (!rst_n_i) begin
    state_q <= STATE_IDLE;
  end
  else begin
    state_q <= state_d;
  end
end

always @(*) begin
  state_d = state_q;
  case (state_q)
    STATE_IDLE: begin
      if (start_i) begin
        state_d = STATE_RUN;
      end
    end
    STATE_RUN: begin
      if (last) begin
        state_d = STATE_DONE;
      end
    end
    STATE_DONE: begin
      state_d = STATE_IDLE;
    end
    default: begin
      state_d = STATE_IDLE;
    end
  endcase
end
```

## Dữ liệu nhiều trường

Không có `struct`: mỗi trường là một tín hiệu/vector riêng (`item_valid`, `item_data`), hoặc một vector ghép có `localparam` chỉ vị trí bit khi kiến trúc thật sự là một bus gộp.

## Generate và function

- `generate for` (khối có nhãn, vd. `gen_lane`) chỉ khi kiến trúc thật sự là nhiều bản sao giống nhau (mảng instance, lane). Không dùng generate chỉ vì code có thể parameter hóa.
- `function` chỉ khi logic nhỏ, được dùng lại nhiều chỗ và không che kiến trúc; module L2 nhỏ ưu tiên biểu thức hoặc khối `always @(*)` rõ ràng.

## Hierarchy

- Instance đặt tên `u_<vai trò>`, nối theo tên `.port(net)`; không nối theo vị trí. Net nội bộ nối giữa các instance khai báo `wire`.
- Parameter override bằng `#(.NAME(value))` – chỉ khi module con có parameter.
- Mảng instance dùng `generate for`, khối generate có nhãn.

## Giữ RTL đơn giản

Không tự parameter hóa mọi width, không tạo framework generic, macro phức tạp, function chỉ để bớt vài dòng, hay biểu thức dài gộp nhiều logic khác nhau. Không tối ưu code chỉ để ít dòng hơn. Ưu tiên: ít abstraction + thanh ghi rõ + logic tổ hợp rõ = dễ hình dung phần cứng. Đây vẫn là RTL tổng hợp được, không phải gate-level.

## Không dùng trong RTL

`initial`, `#delay`, `$display`/`$finish`, latch có chủ đích, clock gating, tri-state, nhiều clock trong một khối – trừ khi spec yêu cầu.

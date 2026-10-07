# Chọn direct test và định dạng vplan mặc định

Nguyên tắc: bộ test nhỏ nhất phủ **mọi chức năng chính → biên quan trọng → tương tác quan trọng**. Đây là đủ dùng về chức năng, không phải chỉ số coverage. Không cần mọi trạng thái FSM xuất hiện trong một test riêng nếu các kịch bản chức năng đã đi qua nó.

## Theo quy mô

| Quy mô | Test nên có | Thường khoảng |
| --- | --- | --- |
| Leaf nhỏ (counter, FIFO, APB slave) | reset; mỗi chức năng chính; biên (0, max, tràn/đầy/rỗng, đúng ngưỡng); handshake nếu có valid/ready; lỗi nếu spec mô tả | 3–8 test |
| Block vừa (DMA, buffer controller) | reset; một thao tác cơ bản; nhiều thao tác liên tiếp; biên địa chỉ/độ dài; stall/back-pressure nếu có; lỗi chính | 5–12 test |
| Top / IP | cấu hình qua bus; một phép tính/thao tác hoàn chỉnh end-to-end; di chuyển dữ liệu giữa các khối; start/busy/done/idle; vài biên quan trọng; lỗi/chức năng đặc biệt spec nhấn mạnh | 5–15 test |

Không tạo test chỉ để tăng số lượng.

## Theo đặc điểm module

| Có gì | Kiểm gì | Kết quả mong đợi lấy từ |
| --- | --- | --- |
| Reset | Output và thanh ghi trạng thái sau reset; reset giữa chừng hoạt động | Spec mục Hành vi, register map |
| Phép số học | Giá trị điển hình; 0; max dương; min âm; tổ hợp gây tràn/bão hòa | Công thức + định dạng số |
| valid/ready | valid khi ready=0 (dữ liệu giữ nguyên); back-to-back | Quy tắc handshake trong spec |
| Register slave | Đọc giá trị reset; ghi–đọc lại RW; RO không ghi được; W1C/W1P đúng hành vi | Bảng thanh ghi trong spec (hoặc `register_map.md` nếu tách) |
| FSM | Kịch bản bình thường từ IDLE về IDLE; hủy/lỗi giữa chừng nếu spec có | Mục Hành vi/FSM của spec |
| Parameter | Chạy ở cấu hình mặc định, ghi rõ cấu hình | Tham số trong spec |

Phép tính phức tạp (lọc, nhân ma trận…): tính kết quả mong đợi bằng script Python ngắn chạy tại chỗ hoặc golden model trong `doc/spec/source/`, rồi ghi giá trị số vào vplan. Không lưu script đó thành file của project.

## Viết kết quả mong đợi

Kết quả mong đợi thuộc checklist nên viết bằng tiếng Anh:

- Theo chu kỳ: "cycle 3 after `start_i`=1: `done_o`=1 for exactly 1 cycle, `result_o`=0x01F4".
- Kèm phép tính ngắn: `acc = 3 × 0x7FFF = 0x17FFD`.

## Định dạng mặc định (khi vplan_template/ trống)

Heading `### TC_<M>_NNN – <short name>` và các dòng trường của test là checklist → chỉ tiếng Anh (S5 lấy tên sau ID làm `-- <short name> test --`). Đoạn mô tả tùy chọn (mục đích, phạm vi, lý do chức năng chưa phủ): tiếng Anh trước + bản dịch `_VI:_`. Bảng chỉ tiếng Anh.

```markdown
# <m> – Vplan
DUT: `<m>` · Scope: leaf | integration (<submodules>) · Configuration: DATA_W=16, ...

## Tests
### TC_<M>_001 – <short name>
- Objective: ... · Function: <spec section> (REQ-xxx if the spec has them)
- Initial condition: after reset
- Stimulus: c0: ...; c1: ...
- Expected: c3: `result_o` = 0x... (= calculation)
- PASS when: every expected value matches

## Function coverage
| Function | Test |
| --- | --- |
```

Đúng: `### TC_PULSE_CNT_001 – Reset value check` → log S5 `-- Reset value check test --`. Sai: `### TC_PULSE_CNT_001 – Kiểm tra giá trị reset`.

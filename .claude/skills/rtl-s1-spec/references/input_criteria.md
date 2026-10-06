# Tiêu chí đánh giá input (stage 1)

Input đạt khi một kỹ sư khác viết được spec mà không phải hỏi lại điều gì ảnh hưởng tới **chức năng, interface hay bit width**. Hiệu năng, PPA, công nghệ không phải mục tiêu của flow này nên chỉ là MINOR.

- **BLOCKER** – không chốt được chức năng / interface / bit width / register map → dừng, không ghi file.
- **MINOR** – có giả định hợp lý → đi tiếp. Ghi `OPEN-xxx` + giả định tạm chỉ khi giả định ảnh hưởng chức năng, interface, width, hành vi thanh ghi hoặc latency bắt buộc; giả định mặc định vô hại (vd. C8, C10) chỉ nêu trong báo cáo chat. Giả định luôn được ghi là giả định – không trình bày như yêu cầu từ input.

Mức chi tiết co giãn theo quy mô: một counter chỉ cần vài câu mô tả hành vi + danh sách port; một IP cần mô tả từng khối chức năng.

| # | Tiêu chí | Nếu thiếu | Giả định mặc định khi MINOR |
| --- | --- | --- | --- |
| C1 | Mọi file input đọc được | BLOCKER | |
| C2 | Chức năng end-to-end: làm gì, vào gì, ra gì | BLOCKER | |
| C3 | Giao tiếp ngoài: port hoặc giao thức bus + width | BLOCKER | |
| C4 | Clock & reset | MINOR | Theo convention đã có của project (`CLAUDE.md`, spec module khác) nếu có. Không có → `OPEN-xxx` với giả định tạm: 1 clock `clk_i`, reset `rst_n_i` async active-low. OPEN này không chặn PASS |
| C5 | Giải thuật / hành vi: các bước, thứ tự, điều kiện dừng | BLOCKER | |
| C6 | Định dạng số mỗi biến (signed/unsigned, Qm.n hoặc dải), làm tròn/bão hòa | BLOCKER nếu có phép số học; MINOR nếu chỉ thiếu làm tròn | truncate, wrap-around |
| C7 | Thanh ghi phần mềm (nếu có bus cấu hình) | BLOCKER nếu có bus mà không mô tả; MINOR nếu chỉ thiếu offset | offset tăng dần theo thứ tự liệt kê, căn 4 byte |
| C8 | Hiệu năng (throughput, latency) | MINOR – BLOCKER chỉ khi input nhắc tới mà không có số | kiến trúc đơn giản nhất, không pipeline thêm |
| C9 | Hành vi lỗi / input không hợp lệ | MINOR | Không mặc định cứng là "bỏ qua". Input nêu → theo input; giao thức/kiến trúc đã ngụ ý rõ → dùng cách đó; còn mơ hồ mà ảnh hưởng hành vi nhìn thấy từ ngoài (FIFO ghi khi đầy, đọc địa chỉ không tồn tại, DMA length = 0…) → `OPEN-xxx` + giả định ghi trong spec. Chỉ chi tiết nội bộ, không nhìn thấy từ ngoài mới dùng giả định im lặng |
| C10 | Kiến trúc thô / danh sách khối | MINOR | Claude đề xuất phân rã |
| C11 | Mâu thuẫn giữa các file hoặc trong một file (width, tên, số liệu) | BLOCKER | |

## Cách viết đề xuất sửa (trong chat)

Mỗi lỗi đủ để người dùng mở file sửa ngay:

> **[BLOCKER C6]** `algo.md`, mục 3 "Tích lũy": biến `acc` không có định dạng số.
> Đề xuất thêm dưới công thức:
> ```
> - x[n]: signed Q1.15 (16 bit)
> - acc: signed, tích lũy <N> tích → <...> bit; đầu ra bão hòa về Q1.15
> ```

# Coding rule RTL của bạn (tùy chọn)

Đặt file coding style RTL vào thư mục này (.md, .txt, .pdf, .docx, file .v mẫu…). Stage 3 đọc mọi file ở đây trừ README.md; rule ở đây luôn thắng.

Thư mục trống → stage 3 vẫn chạy, dùng `../references/default_rtl_rules.md` (Verilog-2005, đuôi `.v`, kiểm bằng Icarus `-g2005` / Verilator chế độ 1364-2005).

Nên ghi rõ: header, đặt tên, kiểu reset, cách viết FSM, cấu trúc thư mục `rtl/`.

Rule ở đây không nêu ngôn ngữ → RTL là Verilog-2005. Chỉ ghi rõ ngôn ngữ khác ở đây khi thật sự muốn đổi.

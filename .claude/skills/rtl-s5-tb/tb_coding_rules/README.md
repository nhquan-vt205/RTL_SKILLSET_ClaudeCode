# Coding rule testbench của bạn (tùy chọn)

Đặt file rule testbench vào đây (ngôn ngữ, simulator, cấu trúc TB, định dạng log, script chạy…). Rule ở đây luôn thắng.

Thư mục trống → stage 5 dùng `../references/default_tb_rules.md` (Verilog-2005: TB top `tb_<m>.v` 9 phần + component `tb_<m>_<role>.v` nối bằng port, mỗi Item vplan một `tc/<ID>.v`, clock 20 ns, stimulus tại `posedge` + `#1`, log phân cấp `[ITEM]`/`[SUBITEM1]`/`[SUBITEM2]` + `[<time>] <case> PASS|FAIL | expected: … | actual: …` căn thẳng cột + `[SUMMARY]`).

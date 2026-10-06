# Coding rule testbench của bạn (tùy chọn)

Đặt file rule testbench vào đây (ngôn ngữ, simulator, cấu trúc TB, định dạng log, script chạy…). Rule ở đây luôn thắng.

Thư mục trống → stage 5 dùng `../references/default_tb_rules.md` (Verilog-2005 `tb_<m>.v`, clock 20 ns, stimulus tại `posedge` + `#1`, cấu trúc 9 phần, log `[<time>] <case> PASS|FAIL | expected: … | actual: …` + `[SUMMARY]`).

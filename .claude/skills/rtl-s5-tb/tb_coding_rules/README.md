# Coding rule testbench của bạn (tùy chọn)

Đặt file rule testbench vào đây (ngôn ngữ, simulator, cấu trúc TB, định dạng log, script chạy…). Rule ở đây luôn thắng.

Thư mục trống → stage 5 dùng `../references/default_tb_rules.md` (Verilog-2005: TB top `tb_<m>.v` 9 phần + component `tb_<m>_<role>.v` nối bằng port, mỗi Item vplan một `tc/<ID>.v`, clock 20 ns, stimulus tại `posedge` + `#1`, expected chỉ từ golden model, log ngắn: `[ITEM]`/`[SUBITEM1]`/`[SUBITEM2]` + một `[GOAL]`, prefix `[t=… ns clk=…]` (clk đếm từ đầu mô phỏng, không reset), mỗi thao tác một dòng (`[APB WRITE <REG>] … OK`, `[DRIVE]`, `[RESET]`, `[WAIT]`), dòng check `[APB READ <REG>] … expected: … actual: … PASS|FAIL` căn thẳng cột, chỉ in sai lệch của watch, mỗi sai lệch một dòng FAIL kèm chú thích `(…)` ngắn khi cần, `[SUMMARY]`/`Test_result`).

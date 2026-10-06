# Rule testbench mặc định (chỉ dùng cho chỗ tb_coding_rules/ không nói tới)

## Cấu trúc
- `tb/<m>/tb_<m>.sv`, module top `tb_<m>`, SystemVerilog chạy được trên Icarus (`-g2012`) và Verilator (`--binary --timing`).
- Thứ tự: parameter → tín hiệu → sinh clock → instance DUT `u_dut` (nối theo tên) → task tiện ích (`reset`, `expect_eq`) → task test `tc_<id>()` → `initial` chính.
- `initial` chính: đọc `+TEST=<ID>` (không có hoặc `ALL` thì chạy tất cả theo thứ tự vplan), reset trước mỗi test, in `[SUMMARY]`, `$finish`.

## Clock, reset, thời gian
- `` `timescale 1ns/1ps ``; chu kỳ theo tần số trong spec, mặc định 10 ns.
- Lái input ở cạnh xuống, lấy mẫu output ở cạnh lên – tránh race.
- Reset giữ 5 chu kỳ, nhả đồng bộ clock.
- Timeout toàn cục (vd. 100× số chu kỳ ước lượng): in `[TIMEOUT]` rồi `$fatal`.

## Kiểm tra
- `task expect_eq(input string name, input logic [63:0] got, exp)` tăng bộ đếm lỗi, in hex.
- Mỗi test một dòng `[TEST] <ID> PASS` / `[TEST] <ID> FAIL: ...`; cuối `[SUMMARY] PASS=<n> FAIL=<n>`.
- Phép tính mong đợi phức tạp có thể tính bằng function SV nhỏ trong TB; không xây reference model framework.

## Waveform (chỉ để debug, không bắt buộc)
- `+DUMP` bật `$dumpfile("tb_<m>.vcd"); $dumpvars(0, tb_<m>);`.

## `sim/<m>/run.sh` mặc định
```bash
#!/usr/bin/env bash
# Dùng: sim/<m>/run.sh [TEST_ID|ALL] [+DUMP]   (chạy từ gốc project)
set -e
M=<m>; T=${1:-ALL}; mkdir -p sim/$M/logs
if command -v iverilog >/dev/null; then
  iverilog -g2012 -o sim/$M/tb_$M.vvp -f sim/$M/$M.f
  vvp sim/$M/tb_$M.vvp +TEST=$T $2 | tee sim/$M/logs/run.log
elif command -v verilator >/dev/null; then
  verilator --binary --timing -Wno-fatal -Wno-TIMESCALEMOD -Wno-WIDTH --top-module tb_$M -f sim/$M/$M.f --Mdir sim/$M/obj_dir -o tb_$M
  sim/$M/obj_dir/tb_$M +TEST=$T $2 | tee sim/$M/logs/run.log
else
  echo "Không có simulator (iverilog/verilator)"; exit 2
fi
```

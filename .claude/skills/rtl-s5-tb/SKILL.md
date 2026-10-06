---
name: rtl-s5-tb
description: Stage 5 của RTL flow (tùy chọn, nhẹ) – viết testbench self-checking hiện thực đúng các direct test trong vplan của MỘT module (leaf hoặc cả cây con ở mức tích hợp), tạo filelist + script chạy, mô phỏng bằng Icarus Verilog/Verilator nếu có. Theo rule testbench của người dùng trong tb_coding_rules/ nếu có. Dùng khi người dùng gọi /rtl-s5-tb <module> hoặc yêu cầu viết testbench theo vplan.
argument-hint: "<tên_module> [tên_module ...]"
disable-model-invocation: true
---

# Stage 5 – Testbench theo vplan

Module: `$ARGUMENTS`

Stage này **tùy chọn**, chỉ chạy khi người dùng cần mô phỏng.

Testbench tự kiểm: stimulus → DUT → so giá trị thực với mong đợi → in PASS/FAIL. Không chỉ `$display` để xem waveform bằng mắt. Không UVM, random, coverage, assertion framework.

## Phạm vi

- Chỉ đúng module(s) được nêu tên; không nhận "all".
- Hiện thực **đúng và đủ** các test trong `doc/vplan/<m>_vplan.*`; test cần thêm → đề xuất trong báo cáo để cập nhật vplan.
- Không sửa RTL, spec, diagram, vplan. Đầu ra chỉ trong `tb/<m>/` và `sim/<m>/`.

## Bước 0 – Gate

```bash
python3 .claude/skills/rtl-s5-tb/scripts/check_preconditions.py --stage 5 --module <m>
```

Cần spec PASS, bảng port, RTL của module **và mọi module con** (để mô phỏng được), vplan. Mã thoát ≠ 0 → bỏ qua module đó, báo `[THIẾU]`. Test trong vplan còn `TBD` ở stimulus/mong đợi → bỏ qua test đó, liệt kê trong báo cáo.

## Bước 1 – Rule

Đọc `tb_coding_rules/` (trừ README.md) nếu có; chỗ không nói tới hoặc thư mục trống → `references/default_tb_rules.md`.

## Bước 2 – Viết testbench

Đọc vplan, RTL (port, parameter), spec (handshake, reset, latency).

- Mỗi test ID → một task chứa ID trong tên (`tc_acc_unit_001`), comment đầu task chép mục tiêu từ vplan.
- So sánh tại đúng chu kỳ; log mỗi test đúng một dòng `[TEST] <ID> PASS` hoặc `[TEST] <ID> FAIL: <tín hiệu> exp=<..> got=<..> @<t>`, cuối cùng `[SUMMARY] PASS=<n> FAIL=<n>` (trừ khi rule quy định khác).
- Timeout toàn cục; driver tuân thủ giao thức handshake; chạy riêng một test bằng `+TEST=<ID>`.
- DUT có module con (phạm vi tích hợp): instance module cha, stimulus qua port của nó, kiểm output/status cuối; filelist gồm RTL cả cây.

## Bước 3 – Script và chạy

Tạo `sim/<m>/<m>.f` (RTL cả cây + TB) và `sim/<m>/run.sh` (hoặc theo rule). Chạy nếu có simulator (ưu tiên Icarus, rồi Verilator), log vào `sim/<m>/logs/run.log`, rồi:

```bash
python3 .claude/skills/rtl-s5-tb/scripts/check_sim_log.py sim/<m>/logs/run.log doc/vplan/<m>_vplan.<ext>
```

Test FAIL → phân loại:
- Lỗi testbench (stimulus/chu kỳ kiểm sai so với vplan) → sửa TB, chạy lại.
- Lỗi RTL hoặc vplan → **không sửa**; báo test ID, triệu chứng, nghi ngờ ở file/dòng nào, cần sửa ở S3 hay S4.

Không có simulator → không phải lỗi thiết kế; ghi "chưa chạy mô phỏng" và lệnh chạy.

## Đầu ra

```
tb/<m>/tb_<m>.sv
sim/<m>/<m>.f
sim/<m>/run.sh
sim/<m>/logs/run.log     # nếu đã chạy – log tạm, bị .gitignore, không phải tài liệu cần giữ
```

## Báo cáo cuối (chỉ trong chat)

File · số test hiện thực / tổng vplan · kết quả theo ID · test bỏ qua vì TBD · lỗi nghi ở RTL/vplan kèm đề xuất · lệnh chạy lại.

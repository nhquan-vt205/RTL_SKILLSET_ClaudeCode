---
name: rtl-s4-vplan
description: Stage 4 của RTL flow (tùy chọn, nhẹ) – lập vplan gồm số ít direct test đủ chứng minh các chức năng chính của MỘT module chạy đúng theo spec; với module có module con thì test theo kịch bản tích hợp. Theo template người dùng trong vplan_template/ nếu có, không thì dùng định dạng mặc định. Dùng khi người dùng gọi /rtl-s4-vplan <module> hoặc yêu cầu viết vplan/test plan cho một module.
argument-hint: "<tên_module> [tên_module ...]"
disable-model-invocation: true
---

# Stage 4 – Vplan direct test

Module: `$ARGUMENTS`

Stage này **tùy chọn**: thiết kế đã xong ở S3; module nhỏ có thể dừng ở đó nếu người dùng không cần test plan.

Vplan trả lời một câu: **thiết kế có làm đúng các chức năng chính trong spec không?** Không chứng minh vét cạn. Không UVM, constrained-random, coverage (functional/code), assertion, formal, scoreboard framework – trừ khi template người dùng yêu cầu.

## Phạm vi

- Chỉ đúng module(s) được nêu tên; không nhận "all".
- Không sửa spec, diagram, RTL. Đầu ra: một file `doc/vplan/<m>_vplan.<đuôi>`.

## Bước 0 – Gate

```bash
python3 .claude/skills/rtl-s4-vplan/scripts/check_preconditions.py --stage 4 --module <m>
```

Cần spec PASS, bảng port, `rtl/<m>.sv|.v`. Mã thoát ≠ 0 → bỏ qua module đó, báo `[THIẾU]`. Dòng `[INFO] phạm vi tích hợp` nghĩa là DUT gồm cả module con → test theo kịch bản tích hợp.

## Bước 1 – Định dạng

Có file trong `vplan_template/` (trừ README.md) → theo đúng template: định dạng (.md/.xlsx/.docx/.csv), cột, quy ước ID; .xlsx/.docx giữ nguyên sheet/style, chỉ điền dữ liệu; nhiều template → hỏi dùng cái nào. Thư mục trống → định dạng Markdown mặc định trong `references/test_selection.md`.

## Bước 2 – Chọn test

Theo `references/test_selection.md` – số test tỉ lệ với số chức năng, không với số trạng thái:

- **Leaf:** reset, mỗi chức năng chính 1 test, vài giá trị biên, handshake/lỗi nếu spec có.
- **Block / top (có module con):** cấu hình → chạy một thao tác hoàn chỉnh → kiểm output/status; thêm vài thao tác liên tiếp, biên quan trọng, lỗi chính. Không cần test lại từng module con.

Mỗi test có: ID (`TC_<MODULE>_<NNN>` nếu template không quy định), mục tiêu, chức năng trong spec được kiểm (kèm REQ-ID nếu spec có), stimulus theo chu kỳ, **kết quả mong đợi bằng số** (tính từ công thức/latency, ghi phép tính), tiêu chí PASS. Không đủ thông tin để tính → `TBD – <thiếu gì>`, không đoán.

Cuối vplan: bảng `Chức năng → test ID`; chức năng chính nào chưa có test thì nêu lý do.

## Báo cáo cuối (chỉ trong chat)

File · số test theo nhóm · chức năng chưa phủ · trường TBD · lệnh tiếp theo `/rtl-s5-tb <m>`.

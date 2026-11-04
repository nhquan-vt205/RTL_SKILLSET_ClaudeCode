---
name: rtl-s4-vplan
description: Stage 4 của RTL flow (tùy chọn, nhẹ) – lập vplan direct test đủ chứng minh các chức năng chính của MỘT module chạy đúng theo spec, dạng cây Item → Sub item 1 → Sub item 2 theo chức năng thật của DUT (ô cha gộp dọc; mỗi Item cấp cao nhất là một testcase S5); với module có module con thì test theo kịch bản tích hợp. Theo template người dùng trong vplan_template/ nếu có, không thì dùng định dạng mặc định. Dùng khi người dùng gọi /rtl-s4-vplan <module> hoặc yêu cầu viết vplan/test plan cho một module.
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

**Nhánh git** (mục "Nhánh git" của `CLAUDE.md`): sau gate, so nhánh hiện tại với nhánh `<b>` của `<m>` (cột `Branch` của `spec_status.md`; chế độ đơn `<m>`). Khác nhau → báo nhánh đúng và lệnh (`git checkout <b>`, hoặc `git checkout -b <b> main` nếu chưa có), chỉ chuyển khi người dùng đồng ý; không chạy S4 của module con trên `main`. Commit/push đầu ra chỉ khi người dùng yêu cầu; báo cáo cuối gợi ý lệnh commit và `git push -u origin <b>`.

## Bước 1 – Định dạng

Có file trong `vplan_template/` (trừ README.md) → theo đúng template: định dạng (.md/.xlsx/.docx/.csv), cột, quy ước ID, cách gộp ô; .xlsx/.docx giữ nguyên sheet/style, chỉ điền dữ liệu và gộp ô thật; nhiều template → hỏi dùng cái nào. Thư mục trống → định dạng Markdown mặc định trong `references/test_selection.md`. Không tự đổi định dạng của vplan đã có sang định dạng khác.

**Bảng checklist phân cấp** (luật chi tiết: template, mục "Hierarchy Rules"; định dạng mặc định dùng cùng luật):

- Cột `ID | Item | Sub item 1 | Sub item 2 | Test sequence | Pass condition`. Mỗi dòng là một **nhánh lá** với stimulus, giá trị mong đợi và pass condition riêng.
- Item = nhóm chức năng bao quát nhất; Sub item 1 = nhánh chức năng chi tiết hơn trong Item; Sub item 2 = nhánh kiểm tra sâu nhất trong Sub item 1. Phân nhóm theo chức năng thật của DUT, không theo số testcase hay tên file hiện có.
- Chỉ dùng số cấp nhánh cần (1, 2 hoặc 3), nội dung dồn trái; không tạo cấp trung gian vô nghĩa (`General`, `Basic`, `Other`); một lá có thể chứa nhiều stimulus/check, không biến từng giá trị input thành một nhánh. Một nút hoặc là lá hoặc là nhóm.
- Nhánh cùng cha là cụm liên tiếp; tên cha viết một lần, ô gộp dọc qua mọi dòng con: ô ID và Item qua mọi dòng của Item, ô Sub item 1 qua các dòng Sub item 2 của nó. `.md`: bảng HTML `rowspan` (bảng pipe Markdown không gộp được ô, không dùng cho checklist); `.xlsx`/`.docx`: merge cell thật; `.csv`: ô trống ở ID/Item/Sub item 1 = kế thừa dòng trên, cấp không tồn tại ghi `—`.
- **ID** `TC_<MODULE>_<NNN>` (nếu template không quy định khác) là ID thực thi của **Item cấp cao nhất**: một ID mỗi Item, đánh số tăng dần theo thứ tự Item; S5 dùng cho `tc/<ID>.v`, `TESTNAME`, `pat.list`, log. Nhánh con truy vết bằng đường dẫn `<ID> › <Item> › <Sub item 1> › <Sub item 2>`: tên Item duy nhất trong vplan, tên anh em duy nhất dưới cùng cha; cùng tên lá dưới cha khác nhau được phép.
- Kiểm bảng sau khi viết: `python3 .claude/skills/rtl-s5-tb/scripts/check_sim_log.py --items doc/vplan/<m>_vplan.<ext>` phải in đúng cây dự định và mã thoát 0 (báo lỗi cấu trúc theo hàng: lặp tên cha, sai dồn trái, lá lẫn nhóm, ô gộp vượt ranh giới, thiếu Test sequence/Pass condition).

**Ngôn ngữ của vplan:** checklist chỉ dùng tiếng Anh – mọi tiêu đề và ô bảng: tên item, sub item, test sequence, pass condition. Không dịch nội dung ô sang tiếng Việt, không viết ô hai ngôn ngữ (`Truy cập thanh ghi / Register access` sai; `Register access` đúng). ID VPLAN giữ nguyên. Phần mô tả ngoài checklist: tiếng Anh trước, rồi bản dịch `_VI:_`. Lý do: S5 in nguyên văn tên nhánh vào header log (`[ITEM] Register access`, `  [SUBITEM1] DATA Register 0`, `    [SUBITEM2] Reset value check`).

## Bước 2 – Chọn test

Theo `references/test_selection.md` – số nhánh lá tỉ lệ với số chức năng, không với số trạng thái; Item gom các nhánh theo chức năng:

- **Leaf:** reset, mỗi chức năng chính một nhánh, vài giá trị biên, handshake/lỗi nếu spec có.
- **Block / top (có module con):** cấu hình → chạy một thao tác hoàn chỉnh → kiểm output/status; thêm vài thao tác liên tiếp, biên quan trọng, lỗi chính. Không cần test lại từng module con.

Mỗi Item có: ID, tên ngắn tiếng Anh phân biệt được, chức năng trong spec được kiểm (kèm REQ-ID nếu spec có). Mỗi nhánh lá có: tên ngắn tiếng Anh, stimulus theo chu kỳ, **kết quả mong đợi bằng số** (tính từ công thức/latency, ghi phép tính), tiêu chí PASS – giữ đủ các hành vi và giá trị mong đợi đã xác nhận. Không đủ thông tin để tính → `TBD – <what is missing>` ở nhánh đó, không đoán.

Cuối vplan: bảng `Function → branch` (tiếng Anh, cột khác bảng checklist) – ID Item hoặc đường dẫn nhánh lá kiểm chức năng; chức năng chính nào chưa có nhánh thì nêu lý do.

Làm lại vplan cũ dạng bảng phẳng (một dòng một ID, lặp tên cha): gom lại theo chức năng thành cây, đánh lại ID theo Item, liệt kê ánh xạ ID cũ → `<ID mới> › <nhánh>` trong báo cáo (S5 phải chạy lại cho module).

## Báo cáo cuối (chỉ trong chat)

File · cây Item (số Item, số nhánh lá mỗi Item, kết quả `check_sim_log.py --items`) · chức năng chưa phủ · nhánh TBD · lệnh tiếp theo `/rtl-s5-tb <m>`.

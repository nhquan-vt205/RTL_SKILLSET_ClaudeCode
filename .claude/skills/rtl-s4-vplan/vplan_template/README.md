# Template vplan của bạn (tùy chọn)

Đặt một file template (.md, .xlsx, .docx hoặc .csv) vào đây; vplan sinh ra dùng cùng định dạng, cột và quy ước ID. Nhiều template → Claude hỏi dùng cái nào.

Thư mục trống → stage 4 dùng định dạng Markdown mặc định trong `../references/test_selection.md`.

Dù dùng template nào:

- Checklist là cây Item → Sub item 1 → Sub item 2 theo chức năng của DUT; mỗi dòng là một nhánh lá; ô cha gộp dọc (`.md`: bảng HTML `rowspan`; `.xlsx`/`.docx`: merge cell thật; `.csv`: ô trống = kế thừa dòng trên, `—` = cấp không tồn tại). Mỗi Item cấp cao nhất có một ID `TC_<MODULE>_<NNN>` = một testcase S5.
- Template phải giữ 6 cột `ID | Item | Sub item 1 | Sub item 2 | Test sequence | Pass condition` để `check_sim_log.py` của S5 đọc được (`--items <vplan>` in cây).
- Nội dung checklist được tạo (item, sub item, test sequence, pass condition) chỉ dùng tiếng Anh.

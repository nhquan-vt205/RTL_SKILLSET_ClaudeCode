# Chọn direct test và định dạng vplan mặc định

Nguyên tắc: bộ nhánh lá nhỏ nhất phủ **mọi chức năng chính → biên quan trọng → tương tác quan trọng**, gom thành cây Item → Sub item 1 → Sub item 2 theo chức năng thật của DUT (luật cây: template `vplan_template/Direct_Test_VPLAN_Checklist_Template.md`, mục "Hierarchy Rules"). Đây là đủ dùng về chức năng, không phải chỉ số coverage. Không cần mọi trạng thái FSM xuất hiện trong một nhánh riêng nếu các kịch bản chức năng đã đi qua nó.

- **Item** = nhóm chức năng bao quát (truy cập thanh ghi, đếm, ngắt, phản hồi lỗi, timing, reset…) = một testcase S5 `tc/<ID>.v`.
- **Sub item 1 / Sub item 2** = nhánh chức năng chi tiết hơn / nhánh kiểm sâu nhất; chỉ thêm cấp khi chức năng thực sự tách nhánh. Một lá có thể chứa nhiều stimulus và check (vd. 4 mẫu ghi–đọc lại là một lá).

## Theo quy mô

| Quy mô | Nhánh lá nên có | Thường khoảng |
| --- | --- | --- |
| Leaf nhỏ (counter, FIFO, APB slave) | reset; mỗi chức năng chính; biên (0, max, tràn/đầy/rỗng, đúng ngưỡng); handshake nếu có valid/ready; lỗi nếu spec mô tả | 2–5 Item, 3–10 nhánh lá |
| Block vừa (DMA, buffer controller) | reset; một thao tác cơ bản; nhiều thao tác liên tiếp; biên địa chỉ/độ dài; stall/back-pressure nếu có; lỗi chính | 3–7 Item, 5–15 nhánh lá |
| Top / IP | cấu hình qua bus; một phép tính/thao tác hoàn chỉnh end-to-end; di chuyển dữ liệu giữa các khối; start/busy/done/idle; vài biên quan trọng; lỗi/chức năng đặc biệt spec nhấn mạnh | 4–8 Item, 8–20 nhánh lá |

Không tạo nhánh hay cấp chỉ để tăng số lượng; không tách Item theo số testcase muốn có.

## Theo đặc điểm module

| Có gì | Kiểm gì | Kết quả mong đợi lấy từ |
| --- | --- | --- |
| Reset | Output và thanh ghi trạng thái sau reset; reset giữa chừng hoạt động | Spec mục Hành vi, register map |
| Phép số học | Giá trị điển hình; 0; max dương; min âm; tổ hợp gây tràn/bão hòa | Công thức + định dạng số |
| valid/ready | valid khi ready=0 (dữ liệu giữ nguyên); back-to-back | Quy tắc handshake trong spec |
| Register slave | Đọc giá trị reset; ghi–đọc lại RW; RO không ghi được; W1C/W1P đúng hành vi | Bảng thanh ghi trong spec (hoặc `register_map.md` nếu tách) |
| FSM | Kịch bản bình thường từ IDLE về IDLE; hủy/lỗi giữa chừng nếu spec có | Mục Hành vi/FSM của spec |
| Parameter | Chạy ở cấu hình mặc định, ghi rõ cấu hình | Tham số trong spec |

Phép tính phức tạp (lọc, nhân ma trận…): tính kết quả mong đợi bằng script Python ngắn chạy tại chỗ hoặc golden model trong `doc/spec/source/`, rồi ghi giá trị số vào vplan. Không lưu script đó thành file của project.

## Viết kết quả mong đợi

Kết quả mong đợi thuộc checklist nên viết bằng tiếng Anh:

- Theo chu kỳ: "cycle 3 after `start_i`=1: `done_o`=1 for exactly 1 cycle, `result_o`=0x01F4".
- Kèm phép tính ngắn: `acc = 3 × 0x7FFF = 0x17FFD`.

## Định dạng mặc định (khi vplan_template/ trống)

Một file `doc/vplan/<m>_vplan.md`: dòng thông tin, đoạn mô tả tùy chọn, bảng checklist **HTML** (bảng pipe Markdown không gộp được ô) theo đúng cột và luật cây của template, rồi bảng `Function coverage`. Checklist và mọi bảng chỉ tiếng Anh (S5 in nguyên văn tên nhánh vào log: `[ITEM] Counting`, `  [SUBITEM1] Enable control`, `    [SUBITEM2] Count step`). Đoạn mô tả (mục đích, phạm vi, ký hiệu, lý do chức năng chưa phủ): tiếng Anh trước + bản dịch `_VI:_`.

```markdown
# <m> – Direct Test VPLAN
DUT: `<m>` · Scope: leaf | integration (<submodules>) · Configuration: DATA_W=16, ...

## Checklist

<table>
<thead>
<tr><th>ID</th><th>Item</th><th>Sub item 1</th><th>Sub item 2</th><th>Test sequence</th><th>Pass condition</th></tr>
</thead>
<tbody>
<tr><td rowspan="3">TC_PULSE_CNT_001</td><td rowspan="3">Counting</td><td rowspan="2">Enable control</td><td>Count step</td><td>After reset: 3 cycles <code>en_i</code>=1, <code>pulse_i</code>=1, then idle 1.</td><td><code>count_o</code> = 3 (= 0 + 3).</td></tr>
<tr><td>Hold value check</td><td>...</td><td>...</td></tr>
<tr><td>Clear control</td><td></td><td>...</td><td>...</td></tr>
<tr><td>TC_PULSE_CNT_002</td><td>Reset during counting</td><td></td><td></td><td>...</td><td>...</td></tr>
</tbody>
</table>

## Function coverage
| Function (spec section) | Branch |
| --- | --- |
| Count enable | TC_PULSE_CNT_001 › Enable control |
```

- Trong ô HTML: ghi ID thật (`TC_PULSE_CNT_001`; chuỗi dạng `<M>` bị hiểu là thẻ HTML), `<code>…</code>` thay backtick, `<br>` xuống dòng, `&lt;` `&gt;` `&amp;`; không để dòng trống trong bảng; không `colspan`.
- `rowspan` của Item (và ID) = số dòng lá của Item; `rowspan` của Sub item 1 = số dòng Sub item 2 của nó; cấp không tồn tại = ô trống `<td></td>`.
- Kiểm: `python3 .claude/skills/rtl-s5-tb/scripts/check_sim_log.py --items doc/vplan/<m>_vplan.md` in cây và mã thoát 0.

Đúng: Item `Register access` › Sub item 1 `DATA Register 0` › Sub item 2 `Reset value check` → log S5 `[ITEM] Register access` / `  [SUBITEM1] DATA Register 0` / `    [SUBITEM2] Reset value check`. Sai: lặp `Register access` ở mỗi dòng không gộp ô; tên tiếng Việt `Kiểm tra giá trị reset`; cấp lấp chỗ `General`.

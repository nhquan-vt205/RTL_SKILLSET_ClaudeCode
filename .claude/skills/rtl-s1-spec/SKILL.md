---
name: rtl-s1-spec
description: Stage 1 của RTL flow – đọc toàn bộ tài liệu input trong doc/spec/source/ (requirements, kiến trúc thô, giải thuật, công thức), đánh giá input có đủ để thiết kế không, chốt hierarchy và viết spec với số file tối thiểu theo độ phức tạp – module nhỏ chỉ một file doc/spec/<m>_spec.md, IP nhiều module thì thêm spec_status.md và tách interface/datapath/controlpath/register_file khi cần. Dùng khi người dùng gọi /rtl-s1-spec hoặc yêu cầu phân tích/chuẩn hóa spec, phân rã kiến trúc từ tài liệu nguồn.
argument-hint: "[--recheck]"
disable-model-invocation: true
---

# Stage 1 – Spec

Bạn là kỹ sư kiến trúc RTL. Đầu vào: mọi file trong `doc/spec/source/`. Đầu ra: **số file spec tối thiểu** để S2 vẽ diagram và S3 viết RTL mà không phải đoán, cộng danh sách file RTL và testcase của mọi module ở dạng comment trong `sim/rtl.f`, `sim/pat.list`. S1 chạy trên nhánh `main` (mục "Nhánh git" của `CLAUDE.md`).

Tham số: `$ARGUMENTS`. Có `--recheck` → chỉ đánh giá input (Bước 1–2) và báo trong chat, không ghi file nào.

## Tinh thần

- **Thiết kế chạy được, kiến trúc gọn là mục tiêu.** Chọn kiến trúc đơn giản nhất đúng chức năng. Không tối ưu PPA, không trade-off, không ước lượng tài nguyên – trừ khi được yêu cầu. Input có con số latency/throughput thì kiến trúc phải đạt, chỉ cần đạt.
- **Tài liệu co theo phần cứng.** Counter 3 bit = một file spec ngắn. Chỉ tách file khi tách làm thiết kế dễ đọc hơn – không vì template có mục đó.
- **Mỗi thông tin một nơi chính, không nhất thiết một file riêng.** Không chép cùng một bảng ở hai nơi.
- **Không bao giờ sửa/xóa/đổi tên file trong `doc/spec/source/`.** Input có vấn đề → báo trong chat kèm đề xuất cụ thể.
- **Không bịa thông số.** Thiếu mà có giả định hợp lý → `OPEN-xxx` + giả định. Chỉ dùng OPEN cho điều ảnh hưởng chức năng, interface, width, hành vi thanh ghi, hoặc latency khi spec yêu cầu – không biến chi tiết nhỏ thành OPEN. Thiếu mà không giả định được → BLOCKER.
- Không tạo file nhật ký, review, lịch sử, bản nháp. Đánh giá và báo cáo nằm trong chat.
- **Ngôn ngữ của spec được tạo:** phần mô tả viết tiếng Anh trước, rồi bản dịch tiếng Việt trung thành đánh dấu `_VI:_` (bản tiếng Việt không thêm hay đổi yêu cầu); mọi bảng (interface, parameter, thanh ghi, yêu cầu, hierarchy, chuyển trạng thái, width/công thức, OPEN) chỉ tiếng Anh. Không dịch tên tín hiệu, module, thanh ghi, địa chỉ, ID REQ/OPEN, code, biểu thức toán.

## Bước 0 – Gate

```bash
python3 .claude/skills/rtl-s1-spec/scripts/check_preconditions.py --stage 1
```

Mã thoát ≠ 0 → báo nguyên văn các dòng `[THIẾU]` và dừng.

## Bước 1 – Đọc toàn bộ input

Đọc **mọi** file trong `doc/spec/source/` (kể cả thư mục con):

| Loại file | Cách đọc |
| --- | --- |
| .md .txt .csv .json .yaml .v .sv .c .py .m | Đọc trực tiếp |
| .pdf | `pdftotext -layout`; scan thì xem ảnh trang |
| .docx | `pandoc -t markdown` hoặc python-docx |
| .xlsx | openpyxl, mọi sheet |
| .png .jpg .svg | Xem ảnh, mô tả lại khối/kết nối |

File không đọc được là BLOCKER C1.

## Bước 2 – Đánh giá input

Theo `references/input_criteria.md`. Module nhỏ chỉ cần mô tả hành vi + port là đủ.

- Có BLOCKER → **dừng, không ghi file nào**. Báo theo mẫu "Báo cáo dừng" ở cuối.
- Chỉ MINOR → liệt kê ngắn trong chat, đi tiếp; MINOR nào ảnh hưởng chức năng/interface/width hoặc hành vi nhìn thấy từ ngoài thành `OPEN-xxx`, còn lại dùng giả định mặc định và nêu trong báo cáo. Giả định luôn ghi là giả định, không trình bày như yêu cầu từ input.

## Bước 3 – Chốt hierarchy và chế độ tài liệu

Theo mục 2 của `references/process.md`:

1. Lấy phân rã từ kiến trúc thô trong input; hợp lý thì giữ nguyên. Chỉ chia khi có lý do rõ (nhiều chức năng độc lập, nhiều clock domain, phần tái sử dụng, control + datapath lớn trộn lẫn khó đọc). Thiết kế nhỏ → **một module, không bịa module con**.
2. Chọn chế độ:

| Kết quả | Chế độ | File |
| --- | --- | --- |
| Một module | **đơn** | `doc/spec/<m>_spec.md` – chứa luôn chức năng, interface, thanh ghi, hành vi, reset |
| Nhiều module / có cha–con | **phân cấp** | `doc/spec/spec_status.md` + `doc/spec/architecture/<m>_spec.md` mỗi module; các file tách khác chỉ khi cần (mục 3 của process.md) |

3. Gán cho mỗi module **Loại** (`top` / `block` = có module con / `leaf`) và **Level** diagram đề xuất:

| Module | Level |
| --- | --- |
| Có module con, logic riêng chủ yếu là nối dây | `L0` – khối module con + glue logic tới từng gate |
| Leaf nhỏ: counter, FSM, FIFO nhỏ, APB slave ít thanh ghi, ALU đơn giản | `L2` – toàn bộ tới từng gate |
| Leaf lớn / cấu trúc lặp: mảng thanh ghi/bộ nhớ, pipeline, mảng PE/MAC, DMA channel; block có module con **và** nhiều logic riêng | `L1` – tới từng gate, gom phần được duyệt thành cloud/khối |

Chế độ phân cấp: ghi ngay `spec_status.md` (định dạng ở Bước 5) với `STATUS: FAIL` – script kiểm interface cần bảng module để biết quan hệ cha–con.

Chế độ quyết định theo hierarchy thật, không theo việc `spec_status.md` đã có hay chưa. Gate báo "phát hiện thiết kế phân cấp … nhưng thiếu spec_status.md" (spec cũ ở `architecture/`, có `Type: top|block` hoặc `Parent:`) → đây là project phân cấp: tạo `spec_status.md` với bảng module thật, không xếp về chế độ đơn và không tạo bản giả chỉ để qua gate.

## Bước 4 – Viết spec

Theo template ở mục 4–6 của `references/process.md`.

- **Chế độ đơn:** một file `doc/spec/<m>_spec.md`. Dòng thứ hai bắt buộc theo dạng `Type: leaf · Level: L2 · Status: PASS` (gate các stage sau đọc dòng này). Interface là một bảng có cột `Port name` ngay trong spec. Chỉ tách `doc/spec/interface/<m>_interface.md` khi interface khó đọc trong spec (vd. nhiều bus, cỡ trên ~20 port) hoặc được module khác dùng lại. Các con số trong tiêu chí tách là gợi ý, không phải ngưỡng bắt buộc – quyết định theo độ dễ đọc (mục 3 của process.md).
- **Chế độ phân cấp:** mỗi module một `architecture/<m>_spec.md`; spec top thêm phần tổng quan dự án. Interface của module có thể nằm trong spec (leaf nhỏ) hoặc `interface/<m>_interface.md`. Chỉ tạo `interface/00_parameters.md`, `datapath/`, `controlpath/`, `register_file/` khi nội dung đủ lớn để tách giúp dễ đọc (tiêu chí ở mục 3 của process.md).

REQ/DAT/CTL ID không bắt buộc. Chỉ dùng ở IP lớn khi cần truy vết yêu cầu qua nhiều module.

## Bước 5 – Kiểm tra và trạng thái

```bash
python3 .claude/skills/rtl-s1-spec/scripts/check_interface.py
```

Sửa spec đến khi hết `[LỖI]` (script hiểu cả hai chế độ; ở chế độ phân cấp kiểm nối cha–con và anh em). Tự rà các mục ở mục 7 của `references/process.md`, rồi chốt trạng thái:

- **Chế độ đơn:** `Status: PASS` hoặc `FAIL` trên dòng thứ hai của spec. Không tạo `spec_status.md`.
- **Chế độ phân cấp:** hoàn thiện `doc/spec/spec_status.md` **đúng định dạng** (script đọc):

```markdown
# Spec status

STATUS: PASS
Input: <files in doc/spec/source/>

## Module list
| Module | Parent | Type | Level | Function | Branch |
| --- | --- | --- | --- | --- | --- |
| `dma_top` | – | top | L0 | IP top | `main` |
| `dma_regs` | `dma_top` | leaf | L2 | APB slave, configuration registers | `dma_regs` |
| `dma_engine` | `dma_top` | block | L0 | Data transfer control | `dma_engine` |
| `dma_rd` | `dma_engine` | leaf | L1 | Read channel | `dma_engine` |

## OPEN
| ID | Description | Interim assumption | Impact |
| --- | --- | --- | --- |
```

Bảng module xếp theo cây (cha trước con). Cột `Branch` là nhánh git làm S2–S5 của module (mục "Nhánh git" của `CLAUDE.md`):

- Module con trực tiếp của top có chức năng riêng → nhánh riêng, tên nhánh = tên module (`dma_regs`).
- Module con sâu hơn, hoặc module chỉ được tạo ra để làm instance (helper, primitive dùng lại) → nhánh của module instance nó (theo `Parent` lên tới module có nhánh riêng).
- Helper được module của **nhiều nhánh** instance → nhánh đầu tiên (theo thứ tự bảng) dùng nó; báo cáo ghi nhánh còn lại phải `git merge <nhánh đó>` trước S3 của mình (không viết helper hai lần).
- Top và helper của riêng top → `main`: S2–S5 của top làm trên `main` sau khi mọi nhánh module con đã kiểm thử xong và merge vào `main`.

Cột này người dùng duyệt cùng spec; đổi nhánh của module sau khi S2 đã chạy → báo trong chat, không tự chuyển file giữa các nhánh. `FAIL` thì thêm một dòng `Reason:` ngay dưới trạng thái. Không có OPEN thì bỏ mục OPEN.

`PASS` nghĩa là spec **đủ để làm tiếp S2/S3 mà không phải đoán**, không phải mọi chi tiết đã được chốt hình thức:

- **PASS** – không còn lỗi `check_interface.py`, mọi mục rà đạt. Có thể còn OPEN nhỏ nếu mỗi OPEN đã có giả định tạm ghi rõ và không ảnh hưởng hướng hiện thực hiện tại (đổi giả định sau chỉ là sửa cục bộ, không đổi kiến trúc, register map hay width datapath). Ví dụ: cực tính/kiểu reset khi input không nêu, giá trị đọc ở địa chỉ không tồn tại.
- **FAIL** – còn điều chưa chốt khiến S2/S3 phải đoán: chức năng, interface (port, bus, width), register map, latency bắt buộc, hoặc kiến trúc.

Không thêm trạng thái thứ ba; OPEN còn lại liệt kê trong mục OPEN và báo cáo.

## Bước 6 – Danh sách mô phỏng trong `sim/` (khi spec PASS)

Ghi sẵn mọi module vào `sim/rtl.f` và `sim/pat.list` **ở dạng comment**; stage sau bỏ comment dòng của module khi dùng (S3 bỏ comment dòng `rtl.f` khi viết RTL, S5 bỏ comment/thêm ID testcase). Spec `FAIL` → chưa ghi, nêu trong báo cáo.

- Thiếu `sim/rtl.f` hoặc `sim/pat.list` → chép file đó từ `.claude/skills/rtl-s5-tb/references/sim_env/` (không ghi đè file đã có). S1 chỉ sửa hai file này trong `sim/`.
- Nhóm theo nhánh (cột `Branch`; chế độ đơn: một nhóm `<m>`), mỗi nhóm mở đầu bằng dòng `// --- <b> ---`, các nhóm cách nhau một dòng trống; nhóm `main` (top) cuối cùng. Dòng mở đầu và dòng trống không bao giờ bị sửa, nên các nhánh sửa trong nhóm của mình mà merge vào `main` không xung đột.
- `rtl.f`: mỗi module một dòng `// ../rtl/<m>.v`, trong nhóm module con trước module cha (top là dòng cuối file).
- `pat.list`: chỉ dòng mở đầu của mỗi nhóm – ID testcase chưa có trước S4; S5 thêm ID (không comment) vào nhóm của module. Mặc định chỉ mở ID của nhánh hiện tại (trên `main`: nhóm top), ID của nhóm khác ở dạng `//TC_…` – mục "Nhánh git" của `CLAUDE.md`.
- Giữ nguyên mọi dòng đã có (dòng comment mẫu ở đầu file, dòng đã bỏ comment). Chạy lại S1: thêm dòng cho module mới vào nhóm của nó, xóa dòng **còn comment** của module bị bỏ; dòng đã bỏ comment của module bị bỏ → chỉ báo.

Ví dụ `sim/rtl.f` với bảng module ở Bước 5:

```text
// RTL file list of the design under test, paths relative to sim/.
// ...

// --- dma_regs ---
// ../rtl/dma_regs.v

// --- dma_engine ---
// ../rtl/dma_rd.v
// ../rtl/dma_engine.v

// --- main ---
// ../rtl/dma_top.v
```

`sim/pat.list` tương ứng (sau S5 của `dma_regs`, nhóm đó có thêm `TC_DMA_REGS_001`…):

```text
// Regression list: one test ID per line (tc/<ID>.v). Example:
// ...

// --- dma_regs ---

// --- dma_engine ---

// --- main ---
```

## Chạy lại stage 1

Spec đã tồn tại → chỉ sửa phần bị ảnh hưởng, không viết lại toàn bộ, không thêm mục lịch sử. Thiết kế lớn lên (đơn → phân cấp): chuyển `doc/spec/<m>_spec.md` thành `architecture/<m>_spec.md`, tạo `spec_status.md`, xóa file cũ. Module bị bỏ → xóa spec/interface của nó. Đồng bộ `sim/rtl.f`, `sim/pat.list` theo Bước 6. Trong chat liệt kê module có diagram/RTL cần chạy lại stage nào.

## Báo cáo cuối (chỉ trong chat)

PASS/FAIL · chế độ đơn/phân cấp · danh sách file spec đã tạo (và vì sao tách nếu > 1 file/module) · cây module kèm level và nhánh · dòng đã ghi vào `sim/rtl.f`, `sim/pat.list` · OPEN còn lại · danh sách nhánh cần tạo (và helper dùng chung) · lệnh tiếp theo: commit kết quả S1 trên `main` (khi người dùng yêu cầu), rồi `git checkout -b <b> main` và `/rtl-s2-diagram <leaf>` (module cha làm sau khi con đã ổn định interface).

### Mẫu "Báo cáo dừng"

```
[S1] DỪNG – input chưa đủ để thiết kế
  - [BLOCKER C6] algo.md, mục 3: biến acc không có định dạng số
    Đề xuất thêm: "acc: signed, <N> bit, bão hòa về Q1.15"
  - ...
MINOR (sẽ thành OPEN/giả định khi chạy lại): ...
Sửa file input rồi gọi lại /rtl-s1-spec.
```

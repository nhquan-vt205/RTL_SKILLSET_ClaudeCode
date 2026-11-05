#!/usr/bin/env python3
"""
Đối chiếu log mô phỏng phân cấp của testbench S5 với cây Item → Sub item 1 → Sub item 2 của vplan.

Dùng:
  python3 check_sim_log.py <log> [<log> ...] <vplan> [--id-re REGEX] [--partial]
  python3 check_sim_log.py --items <vplan> [--id-re REGEX]
Mỗi Item cấp cao nhất chạy thành một log riêng sim/log/<ID>.log (`make -C sim all TESTNAME=<ID>`);
truyền mọi log của module, vd. sim/log/TC_<M>_*.log. Tiền tố "# " của transcript QuestaSim được bỏ qua.
--partial: chỉ kiểm các Item có trong log (không báo Item chưa chạy).
--items  : in cây Item thực thi → các dòng header log mong đợi rồi thoát.

Vplan – bảng checklist có đúng 6 cột ID | Item | Sub item 1 | Sub item 2 | Test sequence | Pass condition
(bảng khác, vd. "Function coverage", bị bỏ qua). Mỗi dòng là một nhánh lá. Ô gộp = kế thừa cha:
  .md/.html  bảng HTML <table>, ô cha gộp dọc bằng rowspan; ô trống <td></td> = cấp không tồn tại.
             Bảng pipe Markdown không gộp ô được → định dạng cũ, chạy lại S4.
  .csv       không gộp ô: ô trống ở ID/Item/Sub item 1 = kế thừa dòng trên (cùng cha);
             cấp không tồn tại ghi "—" (hoặc "-"); Sub item 2 không bao giờ để trống.
  .xlsx      ô gộp thật (merge cell); ô trống không gộp = cấp không tồn tại.
  .docx      ô gộp dọc thật (vMerge); ô trống không gộp = cấp không tồn tại.
  "—" luôn = cấp không tồn tại. Đọc bằng thư viện chuẩn (không cần openpyxl/python-docx).
Quy tắc cây: ID gộp đúng theo Item; nội dung dồn trái (không có Item → trống Sub item 1 → có
Sub item 2); một nút hoặc là lá (có Test sequence + Pass condition) hoặc là nhóm, không cả hai; tên
Item duy nhất, tên anh em dưới cùng cha duy nhất (cụm cùng cha liên tiếp, không lặp tên cha).

Log (default_tb_rules.md mục 7):
  [TEST] <context>                                              bối cảnh đầu log (không đếm)
  [ITEM] <Item>                                                 một lần ở đầu log
    [SUBITEM1] <Sub item 1>                                     khi bắt đầu nhóm (nếu cấp tồn tại)
      [SUBITEM2] <Sub item 2>                                   khi bắt đầu lá (nếu cấp tồn tại)
  <prefix> [<TAG>] <text>                                       dòng sự kiện (APB WRITE … OK|SLVERR, DRIVE,
                                                                RESET, WAIT, OBSERVE, WATCH END …) – không đếm
  <prefix> [<TAG>] <text> expected: <e> actual: <a> PASS|FAIL [(<note>)]
                                                                dòng check (APB READ, WATCH, CHECK, APB WRITE
                                                                lệch response …): đếm đúng 1, thuộc nhánh lá
                                                                đang mở; verdict là từ cuối dòng, sau nó chỉ
                                                                có thể có một chú thích ngắn trong ngoặc
  <prefix> [TIMEOUT|PROTOCOL ERROR|LOG ERROR] <text>            lỗi không phải phép so (đếm vào FAIL)
  [SUMMARY] PASS=<n> FAIL=<n>                                   PASS = số dòng check PASS; FAIL = số dòng
                                                                check FAIL + số dòng lỗi (lỗi lặp của một
                                                                watch đã gộp vào một dòng FAIL)
  Test_result: PASSED|FAILED
  <prefix> = [t=<ns> ns clk=<số cạnh lên từ đầu mô phỏng>]
Thụt lề header chỉ để đọc; thẻ [ITEM]/[SUBITEM1]/[SUBITEM2] quyết định cấp. [FIRST FAIL] (nếu có) bị bỏ qua.

Kiểm: bảng vplan sai cấu trúc · Item chưa chạy · nhánh lá thiếu / không có check · nhánh thừa · sai cha
· sai thứ tự cấp (SUBITEM2 không có SUBITEM1, check ngoài nhánh lá) · nhánh in lại / sai thứ tự vplan
· check FAIL · dòng check sai định dạng (PASS|FAIL cuối dòng mà thiếu 'expected: … actual: …', thiếu tiền
tố) · định dạng cũ ('[<time>] <case> PASS|FAIL', '[t=… c=… <phase> txn=…]', '[CHECK …] PASS | expected:')
· clk giảm dần (bộ đếm clock bị reset) · log <ID>.log in Item khác · nhiều [ITEM] trong một log · Item
trùng giữa các log · thiếu/trùng/lệch [SUMMARY], Test_result sai · [TIMEOUT]/[PROTOCOL ERROR]/
[LOG ERROR]/$fatal/FATAL.
Mã thoát 0 = mọi nhánh lá của mọi Item cần kiểm đều PASS và log nhất quán; 1 = có vấn đề; 2 = lỗi dùng.
"""
import argparse
import csv
import html.parser
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

DEFAULT_ID_RE = r"TC_[A-Z0-9_]+_\d{3}"
COLS = ["id", "item", "sub item 1", "sub item 2", "test sequence", "pass condition"]
LEVEL_TAG = {1: "ITEM", 2: "SUBITEM1", 3: "SUBITEM2"}
NONE_MARK = {"-", "–", "—"}
FILLER = {"general", "basic", "other", "others", "misc", "common", "default"}

HEADER = re.compile(r"^(?P<ind>\s*)\[(?P<tag>ITEM|SUBITEM1|SUBITEM2)\]\s+(?P<name>.+?)\s*$")
PREFIX = r"\[t=\s*(?P<t>\d+) ns clk=\s*(?P<c>\d+)\]"
LINE = re.compile(r"^" + PREFIX + r"\s+\[(?P<tag>[^\]]+)\]\s*(?P<body>.*?)\s*$")
VERDICT = re.compile(r"\b(PASS|FAIL)(\s+\(.*\))?$")
CHECK_BODY = re.compile(r"^(?P<text>.*?)\s*expected:\s*(?P<exp>.*?)\s+actual:\s*(?P<act>.*?)\s+(?P<res>PASS|FAIL)"
                        r"(?:\s+\((?P<note>.*)\))?$")
ERROR_KINDS = {"TIMEOUT", "PROTOCOL ERROR", "LOG ERROR"}
ERROR_TAG = re.compile(r"\[(?P<kind>TIMEOUT|PROTOCOL ERROR|LOG ERROR)\]")
OLD_PREFIX = re.compile(r"\[t=\s*\d+ ns c=\s*\d+ \S+\s+txn=")
OLD_CHECK = re.compile(r"\[CHECK [^\]]+\]\s+(PASS|FAIL) \| expected:")
OLD_CASE = re.compile(r"^\s*\[\s*\d+\]\s+\S+\s+(PASS|FAIL)\b")
SUMMARY = re.compile(r"\[SUMMARY\]\s+PASS=(\d+)\s+FAIL=(\d+)")
RESULT = re.compile(r"^Test_result:\s*(\S+)")
QUESTA_PREFIX = re.compile(r"^#( |$)")


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[`*]", "", s)).strip().lower()


def text1(s):
    """Tên một dòng: bỏ markup, gộp khoảng trắng."""
    return re.sub(r"\s+", " ", re.sub(r"[`*]", "", s)).strip()


class VplanError(Exception):
    pass


# ----------------------------------------------------------------------------------------------
# Đọc bảng: mỗi bảng = list hàng, mỗi hàng = list ô (text, inherited)
# ----------------------------------------------------------------------------------------------
class _HtmlTables(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._stack = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._stack.append([])
        elif not self._stack:
            return
        elif tag == "tr":
            self._stack[-1].append([])
        elif tag in ("td", "th") and self._stack[-1]:
            self._stack[-1][-1].append({"text": "", "rowspan": int(a.get("rowspan") or 1),
                                        "colspan": int(a.get("colspan") or 1)})
        elif tag == "br":
            self._cell_add("\n")

    def handle_endtag(self, tag):
        if tag == "table" and self._stack:
            self.tables.append(self._stack.pop())

    def handle_data(self, data):
        self._cell_add(data)

    def _cell_add(self, s):
        if self._stack and self._stack[-1] and self._stack[-1][-1]:
            self._stack[-1][-1][-1]["text"] += s


def _expand_spans(rows):
    """Hàng có rowspan/colspan → lưới (text, inherited); ô bị rowspan phủ = inherited."""
    grid, pending = [], {}            # pending[col] = [text, remaining_rows]
    for r, cells in enumerate(rows):
        out, col, it = [], 0, iter(cells)
        while True:
            if col in pending:
                text, left = pending[col]
                out.append((text, True))
                pending[col][1] -= 1
                if pending[col][1] == 0:
                    del pending[col]
                col += 1
                continue
            c = next(it, None)
            if c is None:
                if any(k >= col for k in pending):
                    out.append(("", False))
                    col += 1
                    continue
                break
            if c["colspan"] > 1:
                raise VplanError(f"hàng {r + 1}: colspan không dùng trong checklist "
                                 f"(cấp không tồn tại để ô trống)")
            out.append((c["text"], False))
            if c["rowspan"] > 1:
                pending[col] = [c["text"], c["rowspan"] - 1]
            col += 1
        grid.append(out)
    return grid


def tables_md(p):
    text = p.read_text(encoding="utf-8", errors="replace")
    keep, fence = [], False
    for line in text.splitlines():          # bỏ khối ``` (ví dụ/mẫu trong vplan)
        if line.strip().startswith("```"):
            fence = not fence
        elif not fence:
            keep.append(line)
    body = "\n".join(keep)
    hp = _HtmlTables()
    hp.feed(body)
    tables = [_expand_spans(t) for t in hp.tables]
    pipes, cur = [], None                   # bảng pipe (chỉ để báo định dạng cũ)
    for line in keep:
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cur is None:
                cur = []
                pipes.append(cur)
            cur.append([(c, False) for c in cells])
        else:
            cur = None
    return tables, pipes


def tables_csv(p):
    rows = list(csv.reader(p.read_text(encoding="utf-8-sig", errors="replace").splitlines()))
    return [[[(c, None) for c in r] for r in rows]], []     # None = luật CSV (ô trống kế thừa)


def _col_index(ref):
    letters = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1, int(ref[len(letters):]) - 1


def tables_xlsx(p):
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    z = zipfile.ZipFile(p)
    names = set(z.namelist())
    shared = []
    if "xl/sharedStrings.xml" in names:
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(ns + "si"):
            shared.append("".join(t.text or "" for t in si.iter(ns + "t")))
    sheets = []
    try:
        rels = {r.get("Id"): r.get("Target") for r in
                ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
        for s in ET.fromstring(z.read("xl/workbook.xml")).iter(ns + "sheet"):
            t = rels[s.get(rel)].lstrip("/")
            sheets.append(t if t.startswith("xl/") else "xl/" + t)
    except KeyError:
        sheets = sorted(n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
    tables = []
    for sh in sheets:
        root = ET.fromstring(z.read(sh))
        cells = {}
        for c in root.iter(ns + "c"):
            col, row = _col_index(c.get("r"))
            t, v = c.get("t"), c.find(ns + "v")
            if t == "s":
                val = shared[int(v.text)] if v is not None else ""
            elif t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(ns + "t"))
            else:
                val = v.text if v is not None and v.text else ""
            cells[(row, col)] = val
        inh = set()
        for m in root.iter(ns + "mergeCell"):
            a, b = m.get("ref").split(":")
            c0, r0 = _col_index(a)
            c1, r1 = _col_index(b)
            if c1 != c0:
                raise VplanError(f"{sh}: ô gộp ngang {m.get('ref')} không dùng trong checklist")
            for r in range(r0 + 1, r1 + 1):
                cells[(r, c0)] = cells.get((r0, c0), "")
                inh.add((r, c0))
        if not cells:
            continue
        nr = max(r for r, _ in cells) + 1
        nc = max(c for _, c in cells) + 1
        tables.append([[(cells.get((r, c), ""), (r, c) in inh) for c in range(nc)] for r in range(nr)])
    return tables, []


def tables_docx(p):
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    root = ET.fromstring(zipfile.ZipFile(p).read("word/document.xml"))
    tables = []
    for tbl in root.iter(w + "tbl"):
        grid = []
        for tr in tbl.findall(w + "tr"):
            row = []
            for tc in tr.findall(w + "tc"):
                pr = tc.find(w + "tcPr")
                span = pr.find(w + "gridSpan") if pr is not None else None
                if span is not None and int(span.get(w + "val", "1")) > 1:
                    raise VplanError("docx: ô gộp ngang (gridSpan) không dùng trong checklist")
                vm = pr.find(w + "vMerge") if pr is not None else None
                inherited = vm is not None and vm.get(w + "val", "continue") == "continue"
                text = "\n".join("".join(t.text or "" for t in para.iter(w + "t"))
                                 for para in tc.findall(w + "p"))
                if inherited and grid and len(grid[-1]) > len(row):
                    text = grid[-1][len(row)][0]
                row.append((text, inherited))
            grid.append(row)
        tables.append(grid)
    return tables, []


READERS = {".md": tables_md, ".html": tables_md, ".htm": tables_md,
           ".csv": tables_csv, ".xlsx": tables_xlsx, ".docx": tables_docx}


# ----------------------------------------------------------------------------------------------
# Cây vplan
# ----------------------------------------------------------------------------------------------
class Node:
    def __init__(self, name, level, parent=None, tid=None, row=0):
        self.name, self.level, self.parent, self.tid, self.row = name, level, parent, tid, row
        self.children, self.leaf = [], False
        self.cases, self.errors, self.visits = [], [], 0

    @property
    def item(self):
        n = self
        while n.parent is not None:
            n = n.parent
        return n

    def path(self, with_item=True):
        parts, n = [], self
        while n is not None:
            parts.append(n.name)
            n = n.parent
        parts.reverse()
        return " › ".join(parts if with_item else parts[1:]) or self.name

    def child(self, name):
        return next((c for c in self.children if norm(c.name) == norm(name)), None)

    def leaves(self):
        if self.leaf:
            return [self]
        return [x for c in self.children for x in c.leaves()]


def _is_header(row):
    return [norm(c[0]) for c in row[:6]] == COLS


def find_checklist(tables, pipes):
    hits = []
    for t in tables:
        for i, r in enumerate(t):
            if _is_header(r):
                hits.append(t[i + 1:])
                break
    if not hits:
        if any(_is_header(r) for t in pipes for r in t[:1]):
            raise VplanError("checklist là bảng pipe Markdown (định dạng cũ, không gộp ô) – chạy lại "
                             "/rtl-s4-vplan <m> để tạo bảng HTML rowspan")
        raise VplanError("không tìm thấy bảng checklist với 6 cột: ID | Item | Sub item 1 | Sub item 2 | "
                         "Test sequence | Pass condition")
    if len(hits) > 1:
        raise VplanError(f"có {len(hits)} bảng checklist – vplan chỉ có một bảng checklist")
    return hits[0]


def build_tree(rows, id_re, csv_mode):
    rx = re.compile(id_re)
    items, errs, warns = [], [], []
    by_id = {}
    prev = {"item": None, "s1": None}
    hint = " (CSV: ô trống = kế thừa dòng trên, cấp không tồn tại ghi —)" if csv_mode else ""

    for n, raw in enumerate(rows, 1):
        if not any(c[0].strip() for c in raw):
            if csv_mode:
                break                                   # CSV: dòng trống = hết bảng
            continue
        cells = (raw + [("", False)] * 6)[:6]
        if csv_mode:                                    # luật CSV → (text, inherited)
            conv = []
            for k, (t, _) in enumerate(cells):
                s = t.strip()
                conv.append(("", True) if (s == "" and k < 4) else (t, False))
            cells = conv
        (tid, tid_inh), (it, it_inh), (s1, s1_inh), (s2, s2_inh) = \
            [(text1(c[0]), c[1]) for c in cells[:4]]
        seq, seq_inh = cells[4][0].strip(), cells[4][1]
        pas, pas_inh = cells[5][0].strip(), cells[5][1]
        where = f"hàng {n}"
        tid, it, s1, s2 = ["" if v in NONE_MARK else v for v in (tid, it, s1, s2)]

        # Item + ID
        if it_inh:
            item = prev["item"]
            if item is None:
                errs.append(f"{where}: Item kế thừa nhưng không có dòng trên{hint}")
                continue
            if not tid_inh:
                errs.append(f"{where}: ô ID phải gộp cùng Item '{item.name}' ({item.tid})")
        else:
            if tid_inh:
                errs.append(f"{where}: ô ID gộp vượt ranh giới Item '{it}'")
            if not it:
                errs.append(f"{where}: thiếu Item (nội dung phải dồn về bên trái){hint}")
                continue
            if not rx.fullmatch(tid):
                errs.append(f"{where}: ID '{tid}' của Item '{it}' không khớp --id-re {id_re}")
            if tid in by_id:
                errs.append(f"{where}: ID {tid} trùng với Item '{by_id[tid].name}'")
            if any(norm(x.name) == norm(it) for x in items):
                errs.append(f"{where}: Item '{it}' xuất hiện lần nữa – gom mọi nhánh của Item thành một cụm "
                            f"liên tiếp, gộp ô Item, không lặp tên")
            item = Node(it, 1, tid=tid, row=n)
            items.append(item)
            by_id.setdefault(tid, item)
            prev["s1"] = None
        prev["item"] = item

        # Sub item 1
        new_s1 = False
        if s1_inh:
            node1 = prev["s1"]
            if it_inh is False or node1 is None:
                errs.append(f"{where}: Sub item 1 kế thừa nhưng cha đã đổi hoặc dòng trên không có "
                            f"Sub item 1{hint}")
                continue
        elif s1:
            if item.leaf:
                errs.append(f"{where}: Item '{item.name}' vừa là nhánh lá (dòng {item.row}) vừa có Sub item 1")
                continue
            if item.child(s1):
                errs.append(f"{where}: Sub item 1 '{s1}' lặp dưới Item '{item.name}' – gom thành một cụm, "
                            f"gộp ô, không lặp tên cha")
                continue
            node1 = Node(s1, 2, item, row=n)
            item.children.append(node1)
            new_s1 = True
            if norm(s1) in FILLER:
                warns.append(f"{where}: Sub item 1 '{s1}' là cấp trung gian vô nghĩa – bỏ cấp này")
        else:
            node1 = None
        prev["s1"] = node1

        # Sub item 2 (luôn là lá, không gộp)
        if s2_inh:
            errs.append(f"{where}: Sub item 2 không được gộp/kế thừa – mỗi dòng là một nhánh lá"
                        + (" (CSV: nhánh hai cấp ghi — ở Sub item 2)" if csv_mode else ""))
            continue
        if s2 and node1 is None:
            errs.append(f"{where}: có Sub item 2 '{s2}' nhưng không có Sub item 1 (dồn nội dung về bên trái)")
            continue
        if s2:
            if node1.leaf:
                errs.append(f"{where}: Sub item 1 '{node1.name}' vừa là nhánh lá (dòng {node1.row}) "
                            f"vừa có Sub item 2")
                continue
            if node1.child(s2):
                errs.append(f"{where}: Sub item 2 '{s2}' lặp dưới '{node1.path()}'")
                continue
            leaf = Node(s2, 3, node1, row=n)
            node1.children.append(leaf)
            if norm(s2) in FILLER:
                warns.append(f"{where}: Sub item 2 '{s2}' là tên vô nghĩa")
        else:
            leaf = node1 if node1 is not None else item
            fresh = new_s1 if node1 is not None else not it_inh
            if not fresh:
                errs.append(f"{where}: dòng không tạo nhánh lá mới (nhánh '{leaf.path()}' đã có ở dòng "
                            f"{leaf.row})")
                continue
            if leaf.children:
                errs.append(f"{where}: '{leaf.path()}' vừa có nhánh con vừa là nhánh lá")
                continue
        leaf.leaf = True
        leaf.row = n
        if seq_inh or pas_inh:
            errs.append(f"{where}: Test sequence/Pass condition không được gộp – mỗi lá có stimulus và "
                        f"tiêu chí riêng")
        if not seq or seq in NONE_MARK or not pas or pas in NONE_MARK:
            errs.append(f"{where}: nhánh lá '{leaf.path()}' thiếu Test sequence hoặc Pass condition")

    for it in items:
        for n1 in it.children:
            if not n1.leaf and not n1.children:
                errs.append(f"'{n1.path()}' không có nhánh lá")
    if not items and not errs:
        errs.append("bảng checklist không có dòng nào")
    return items, errs, warns


def load_vplan(path, id_re):
    p = Path(path)
    reader = READERS.get(p.suffix.lower())
    if reader is None:
        raise VplanError(f"định dạng {p.suffix} không hỗ trợ (.md/.html, .csv, .xlsx, .docx)")
    tables, pipes = reader(p)
    rows = find_checklist(tables, pipes)
    return build_tree(rows, id_re, p.suffix.lower() == ".csv")


# ----------------------------------------------------------------------------------------------
# Log
# ----------------------------------------------------------------------------------------------
def all_nodes(items):
    for it in items:
        yield it
        for n1 in it.children:
            yield n1
            yield from n1.children


def check_logs(logs, items, id_re, problems):
    rx = re.compile(id_re)
    item_by_name = {norm(i.name): i for i in items}
    run, n_pass, n_fail = {}, 0, 0
    for log in logs:
        lname = Path(log).name
        try:
            lines = Path(log).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as e:
            problems.append(f"{lname}: không đọc được log ({e.strerror})")
            continue
        item = n1 = cur = None
        bad_ctx = False                         # đang ở nhánh không hợp lệ (đã báo)
        last_idx = {}                           # id(parent) → chỉ số anh em mở gần nhất
        l_pass = l_fail = l_err = 0
        last_clk = -1
        summaries, verdicts = [], []

        def enter(node, parent, at):
            k = parent.children.index(node)
            if node.visits:
                problems.append(f"{at}: nhánh '{node.path()}' in lại lần nữa – các check của một nhánh "
                                f"phải nằm liên tiếp")
            elif k < last_idx.get(id(parent), -1):
                problems.append(f"{at}: nhánh '{node.path()}' sai thứ tự vplan (in sau nhánh anh em "
                                f"'{parent.children[last_idx[id(parent)]].name}', vplan xếp trước)")
            last_idx[id(parent)] = max(k, last_idx.get(id(parent), -1))
            node.visits += 1

        def misplaced(name, level, parent):
            others = [x for x in all_nodes(items) if x.level == level and norm(x.name) == norm(name)
                      and x.parent is not parent]
            if others:
                return (f"sai cha: '{name}' thuộc {' / '.join(repr(o.parent.path()) for o in others)}, "
                        f"không thuộc '{parent.path()}'")
            return f"nhánh thừa: '{name}' không có dưới '{parent.path()}' trong vplan"

        for n, raw in enumerate(lines, 1):
            s = QUESTA_PREFIX.sub("", raw.rstrip())
            at = f"{lname}:L{n}"
            m = HEADER.match(s)
            if m:
                tag, name = m.group("tag"), text1(m.group("name"))
                if tag == "ITEM":
                    if item is not None:
                        problems.append(f"{at}: log có thêm [ITEM] '{name}' – mỗi tc/<ID>.v là đúng một Item")
                    node = item_by_name.get(norm(name))
                    if node is None:
                        problems.append(f"{at}: Item thừa: '{name}' không có trong vplan")
                        item, n1, cur, bad_ctx = None, None, None, True
                        continue
                    stem = Path(log).stem
                    if rx.fullmatch(stem) and stem != node.tid:
                        problems.append(f"{at}: log {lname} in Item '{node.name}' của {node.tid}")
                    if id(node) in run:
                        problems.append(f"{at}: Item '{node.name}' đã chạy trong {run[id(node)]}")
                    run[id(node)] = lname
                    item, n1, cur, bad_ctx = node, None, node, False
                    continue
                if item is None:
                    if not bad_ctx:
                        problems.append(f"{at}: [{tag}] '{name}' nằm trước [ITEM] (sai thứ tự cấp)")
                    cur = None
                    continue
                if tag == "SUBITEM1":
                    n1 = None
                    node = item.child(name)
                    if not item.children:
                        problems.append(f"{at}: Item '{item.name}' không có Sub item 1 trong vplan "
                                        f"nhưng log in [SUBITEM1] '{name}'")
                    elif node is None:
                        problems.append(f"{at}: {misplaced(name, 2, item)}")
                    if node is None:
                        cur, bad_ctx = None, True
                        continue
                    enter(node, item, at)
                    n1, cur, bad_ctx = node, node, False
                    continue
                # SUBITEM2
                if n1 is None:
                    if not bad_ctx:
                        problems.append(f"{at}: [SUBITEM2] '{name}' không có [SUBITEM1] đang mở trong "
                                        f"'{item.name}' (sai thứ tự cấp)")
                    cur, bad_ctx = None, True
                    continue
                node = n1.child(name)
                if node is None:
                    if not n1.children:
                        problems.append(f"{at}: '{n1.path()}' không có Sub item 2 trong vplan nhưng log in "
                                        f"[SUBITEM2] '{name}'")
                    else:
                        problems.append(f"{at}: {misplaced(name, 3, n1)}")
                    cur, bad_ctx = None, True
                    continue
                enter(node, n1, at)
                cur, bad_ctx = node, False
                continue

            # Định dạng cũ (S5 phiên trước): báo một lần mỗi dòng, không đếm
            if OLD_PREFIX.search(s) or OLD_CHECK.search(s) or OLD_CASE.match(s):
                problems.append(f"{at}: dòng định dạng cũ – S5 mới in '[t=<ns> ns clk=<n>] [<TAG>] … "
                                f"expected: <e> actual: <a> PASS|FAIL', chạy lại /rtl-s5-tb: {s.strip()[:100]}")
                continue
            m = LINE.match(s)
            if m:
                c = int(m.group("c"))
                if c < last_clk:
                    problems.append(f"{at}: clk={c} nhỏ hơn clk={last_clk} của dòng trước – bộ đếm clock "
                                    f"phải tăng xuyên suốt, không reset")
                last_clk = max(last_clk, c)
                tag, body = m.group("tag").strip(), m.group("body")
                if tag in ERROR_KINDS:
                    # Lỗi không phải phép so: đếm vào FAIL của [SUMMARY]
                    l_err += 1
                    if cur is not None and cur.leaf:
                        cur.errors.append((at, s.strip()))
                    problems.append(f"{at}: mô phỏng báo lỗi: {s.strip()[:120]}")
                    continue
                if not VERDICT.search(body):
                    continue                    # dòng sự kiện: không bao giờ đếm
                k = CHECK_BODY.match(body)
                if not k:
                    problems.append(f"{at}: dòng kết thúc bằng PASS/FAIL nhưng thiếu 'expected: <e> actual: "
                                    f"<a>' – không phải dòng check hợp lệ: {s.strip()[:120]}")
                    continue
                if k.group("res") == "PASS":
                    l_pass += 1
                else:
                    l_fail += 1
                rec = {"t": m.group("t"), "c": m.group("c"), "case": f"[{tag}] {k.group('text')}".strip(),
                       "res": k.group("res"), "exp": k.group("exp"), "act": k.group("act"),
                       "note": k.group("note") or ""}
                if cur is None:
                    if not bad_ctx:
                        problems.append(f"{at}: check '{rec['case']}' nằm trước [ITEM]")
                elif not cur.leaf:
                    problems.append(f"{at}: check '{rec['case']}' nằm ở '{cur.path()}' – chưa phải nhánh "
                                    f"lá (thiếu [{LEVEL_TAG[cur.level + 1]}])")
                else:
                    cur.cases.append((at, rec))
                continue
            if ERROR_TAG.search(s):
                l_err += 1
                if cur is not None and cur.leaf:
                    cur.errors.append((at, s.strip()))
                problems.append(f"{at}: dòng lỗi thiếu tiền tố '[t=<ns> ns clk=<n>]': {s.strip()[:100]}")
                continue
            st = s.strip()
            if VERDICT.search(st) and not st.startswith("Test_result") and not SUMMARY.search(st):
                problems.append(f"{at}: dòng mang PASS/FAIL không có tiền tố '[t=<ns> ns clk=<n>] [<TAG>]': "
                                f"{st[:100]}")
                continue
            m = SUMMARY.search(s)
            if m:
                summaries.append((int(m.group(1)), int(m.group(2))))
            m = RESULT.match(s.strip())
            if m:
                verdicts.append(m.group(1))
            if re.search(r"\$fatal|FATAL|\*\* Fatal", s):
                problems.append(f"{at}: mô phỏng dừng bất thường: {s.strip()[:120]}")

        n_pass += l_pass
        n_fail += l_fail + l_err
        if not any(r == lname for r in run.values()) and not bad_ctx:
            problems.append(f"{lname}: không có dòng [ITEM] <Item>")
        if not summaries:
            problems.append(f"{lname}: thiếu dòng [SUMMARY] PASS=<n> FAIL=<n>")
        else:
            sp, sf = summaries[-1]
            if (sp, sf) != (l_pass, l_fail + l_err):
                problems.append(f"{lname}: [SUMMARY] PASS={sp} FAIL={sf} lệch với log (dòng check PASS="
                                f"{l_pass}, dòng check FAIL={l_fail} + dòng lỗi={l_err})")
            if len(summaries) > 1:
                problems.append(f"{lname}: có {len(summaries)} dòng [SUMMARY]")
        want = "PASSED" if l_fail + l_err == 0 and l_pass > 0 else "FAILED"
        if len(verdicts) != 1:
            problems.append(f"{lname}: cần đúng một dòng 'Test_result: PASSED|FAILED' (có {len(verdicts)})")
        elif verdicts[0] != want:
            problems.append(f"{lname}: Test_result: {verdicts[0]} nhưng số check cho kết quả {want}")
    return run, n_pass, n_fail


def print_items(items, path, warns):
    leaves = sum(len(i.leaves()) for i in items)
    print(f"Vplan: {path} · {len(items)} Item, {leaves} nhánh lá")
    for it in items:
        print(f"\n{it.tid}  → tc/{it.tid}.v · make -C sim all TESTNAME={it.tid}")
        print(f"    [ITEM] {it.name}")
        for n1 in it.children:
            print(f"      [SUBITEM1] {n1.name}")
            for n2 in n1.children:
                print(f"        [SUBITEM2] {n2.name}")
    for w in warns:
        print("  [CẢNH BÁO] " + w)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", metavar="<log> [<log> ...] <vplan> | --items <vplan>")
    ap.add_argument("--id-re", default=DEFAULT_ID_RE)
    ap.add_argument("--items", action="store_true", help="in cây Item → header log mong đợi rồi thoát")
    ap.add_argument("--partial", action="store_true", help="chỉ kiểm các Item có trong log")
    a = ap.parse_args()
    if (len(a.files) != 1) if a.items else (len(a.files) < 2):
        ap.error("cần <log> [<log> ...] <vplan>, hoặc --items <vplan>")
    logs, vplan = a.files[:-1], a.files[-1]

    try:
        items, verrs, warns = load_vplan(vplan, a.id_re)
    except (VplanError, OSError, zipfile.BadZipFile, ET.ParseError) as e:
        print(f"[VPLAN] {vplan}: {e}")
        print("KẾT QUẢ: CÓ VẤN ĐỀ")
        sys.exit(1)
    if verrs:
        for e in verrs:
            print(f"  [VPLAN] {e}")
        for w in warns:
            print("  [CẢNH BÁO] " + w)
        print(f"KẾT QUẢ: CÓ VẤN ĐỀ (bảng checklist của {vplan} sai cấu trúc)")
        sys.exit(1)
    if a.items:
        print_items(items, vplan, warns)
        sys.exit(0)

    problems = []
    run, n_pass, n_fail = check_logs(logs, items, a.id_re, problems)
    todo = [i for i in items if id(i) in run or not a.partial]
    print(f"Vplan: {len(items)} Item, {sum(len(i.leaves()) for i in items)} nhánh lá · Log: {len(logs)} file, "
          f"{len(run)} Item chạy, {n_pass} check PASS, {n_fail} FAIL (check FAIL + dòng lỗi)")

    bad = 0
    for it in todo:
        if id(it) not in run:
            print(f"  {it.tid:<20} {it.name[:44]:<44} KHÔNG CHẠY (không có log/[ITEM] '{it.name}')")
            bad += 1
            continue
        rows, fails = [], 0
        for lf in it.leaves():
            nf = sum(1 for _, r in lf.cases if r["res"] == "FAIL")
            if not lf.visits and lf is not it:
                st = "THIẾU (nhánh không chạy)"
            elif not lf.cases:
                st = "KHÔNG CÓ CHECK"
            elif nf or lf.errors:
                st = f"FAIL ({nf}/{len(lf.cases)} check" + (f", {len(lf.errors)} lỗi)" if lf.errors else ")")
            else:
                st = f"PASS ({len(lf.cases)} check)"
            fails += not st.startswith("PASS")
            rows.append((lf, st))
        bad += fails
        print(f"  {it.tid:<20} {it.name[:44]:<44} " + (f"PASS ({len(rows)} nhánh lá)" if not fails
                                                     else f"CÓ VẤN ĐỀ ({fails}/{len(rows)} nhánh lá)"))
        for lf, st in rows:
            if lf is not it:
                print(f"      {lf.path(with_item=False)[:58]:<58} {st}")
            for at, r in lf.cases:
                if r["res"] == "FAIL":
                    note = f" ({r['note']})" if r["note"] else ""
                    print(f"          {at} [t={r['t']} ns clk={r['c']}] {r['case']}: expected {r['exp']} "
                          f"· actual {r['act']}{note}")
            for at, line in lf.errors:
                print(f"          {at} {line[:110]}")
    for w in warns:
        print("  [CẢNH BÁO] " + w)
    for p in problems:
        print("  [VẤN ĐỀ] " + p)
    ok = bad == 0 and not problems
    print("KẾT QUẢ:", "TẤT CẢ PASS" if ok else "CÓ VẤN ĐỀ")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

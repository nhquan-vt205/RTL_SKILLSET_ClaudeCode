#!/usr/bin/env python3
"""
Render HTML schematic RTL (inline SVG, không phụ thuộc gì ngoài) cho diagram L2 của MỘT module leaf.

Đầu vào gồm hai lớp của CÙNG một mô hình kiến trúc:
  1. Mô hình khối  – đồ thị node/cạnh Mermaid theo references/diagram_conventions.md (chính là <m>.mmd).
  2. Lớp chi tiết RTL – các phương trình kiểu Verilog-2005 gắn vào từng node của mô hình ([blk_x], [reg_x]...),
     mô tả bên trong khối gồm thanh ghi, MUX, comparator, cổng, phép toán, hằng nào (mục 8 của
     diagram_conventions.md).
Script dịch lớp chi tiết thành netlist primitive (DFF, MUX, CMP, AND/OR/XOR/NOT, +/−/×/<<, hằng, concat,
bộ nhớ, port), đối chiếu với mô hình khối (không thêm thanh ghi ngoài khối reg_/fsm_, mọi dây đi giữa hai
khối phải là một cạnh của mô hình và ngược lại), rồi tự layout schematic trái → phải, dây vuông góc,
feedback vòng phía trên, clock/reset thành rail phía dưới. Không vẽ tay HTML, không nhúng Mermaid.

Dùng (chạy từ thư mục gốc project):
  python3 render_html.py doc/diagram/<m>/<m>.mmd --detail - [--interface <file bảng port>] <<'SCH'
      ... lớp chi tiết ...
  SCH
      → doc/diagram/<m>/<m>.html (--format both, hoặc html khi đã có .mmd); .mmd không bị ghi
  python3 render_html.py - [--out doc/diagram/<m>/<m>.html] [--interface ...] <<'SCH'
      ... mô hình khối theo diagram_conventions.md ...
  %% schematic
      ... lớp chi tiết ...
  SCH
      → chỉ ghi .html, mô hình + chi tiết đọc từ stdin (--format html khi chưa có .mmd)
  python3 render_html.py --check doc/diagram/<m>/<m>.html [--mmd doc/diagram/<m>/<m>.mmd]
      → kiểm metadata, file tự chứa, lớp chi tiết vẫn khớp mô hình, (nếu có --mmd) cùng mô hình với .mmd

Mô hình khối được lint bằng lint_mermaid.lint (cùng luật với .mmd). Từ chối nếu không phải L2, có instance
module con (u_/gen_), hoặc lớp chi tiết sai/không khớp mô hình. HTML chỉ để xem; S3 chỉ đọc .mmd.
Mã thoát 0 = OK, 1 = lỗi.
"""
import argparse
import html
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True  # không để __pycache__ trong skill
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lint_mermaid import iface_ports, lint  # noqa: E402

# ---------------------------------------------------------------- mô hình khối (Mermaid)

KINDS = (("pi_", "in"), ("po_", "out"), ("reg_", "reg"), ("ff_", "reg"), ("fsm_", "fsm"), ("mem_", "mem"),
         ("mux_", "mux"), ("op_", "op"), ("blk_", "logic"), ("glue_", "logic"), ("u_", "inst"),
         ("gen_", "inst"), ("n_", "note"))
OPEN = r"\[/|\[\\|\(\[|\(\(|\{\{|\[\[|\[\(|\[|\(|>|\{"
CLOSE = r"\\\]|/\]|\]\)|\)\)|\}\}|\]\]|\)\]|\]|\)|\}"
NODE_DEF = re.compile(rf'([A-Za-z_]\w*)\s*(?:{OPEN})\s*"(.*)"\s*(?:{CLOSE})$')
EDGE_OP = re.compile(r"\s*(-\.->|==>|-->|-\.-|---)\s*(?:\|([^|]*)\|)?\s*")
SKIP = ("flowchart", "graph", "classdef", "class ", "style", "linkstyle", "direction", "click", "subgraph")
SCH_MARK = re.compile(r"^\s*%%\s*=*\s*schematic\b.*$", re.I | re.M)


def kind_of(nid):
    return next((k for p, k in KINDS if nid.startswith(p)), "logic")


def unescape(s):
    s = s.replace("#quot;", '"')
    return html.unescape(re.sub(r"#(\d+);", lambda m: chr(int(m.group(1))), s))


def parse_model(text):
    """Mô hình khối: {module, level, source, param, nodes[{id,kind,label}], edges[{src,dst,type,label}]}."""
    meta, nodes, edges, sub = {}, {}, [], ""

    def node(seg):
        seg = seg.strip()
        m = NODE_DEF.match(seg)
        nid = m.group(1) if m else seg
        if not re.fullmatch(r"[A-Za-z_]\w*", nid):
            return None
        if nid not in nodes:
            nodes[nid] = {"id": nid, "kind": kind_of(nid), "label": nid}
        if m:
            nodes[nid]["label"] = unescape(m.group(2))
        return nid

    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("%%"):
            m = re.match(r"%%\s*(module|stage|source|nguon|param)\s*:\s*(.*)$", s, re.I)
            if m:
                meta.setdefault(m.group(1).lower(), m.group(2).strip())
            continue
        low = s.lower()
        if low.startswith("subgraph") and not sub:
            m = re.match(r"subgraph\s+M_([A-Za-z_]\w*)", s)
            sub = m.group(1) if m else ""
        if not s or low == "end" or low.startswith(SKIP):
            continue
        quoted = []
        prot = re.sub(r'"[^"]*"', lambda m: quoted.append(m.group(0)) or f"\0{len(quoted) - 1}\0", s)
        restore = lambda t: re.sub(r"\0(\d+)\0", lambda m: quoted[int(m.group(1))], t)  # noqa: E731
        parts = EDGE_OP.split(prot)
        groups = [[node(restore(x)) for x in parts[0].split("&")]]
        for i in range(1, len(parts), 3):
            op, lab = parts[i], parts[i + 1]
            dst = [node(restore(x)) for x in parts[i + 2].split("&")]
            label = unescape(restore(lab).strip().strip('"')) if lab else ""
            for a in groups[-1]:
                for b in dst:
                    if a and b:
                        edges.append({"src": a, "dst": b, "label": label,
                                      "type": "control" if op.startswith("-.") else "data"})
            groups.append(dst)
    lv = re.search(r"\bL([012])\b", meta.get("stage", ""))
    return {"module": meta.get("module", sub).split()[0] if meta.get("module", sub) else "",
            "level": f"L{lv.group(1)}" if lv else "", "source": meta.get("source", meta.get("nguon", "")),
            "param": meta.get("param", ""), "nodes": list(nodes.values()), "edges": edges}


def same_architecture(a, b):
    key = lambda m: ({n["id"]: (n["kind"], n["label"]) for n in m["nodes"]},  # noqa: E731
                     sorted((e["src"], e["dst"], e["type"], e["label"]) for e in m["edges"]),
                     m["module"], m["level"])
    return key(a) == key(b)


def lines_of(label):
    return [x.strip() for x in re.split(r"<br\s*/?>", label) if x.strip()] or [""]


def iface_table(md):
    """Bảng port → {tên: (hướng, width)}; width 'PARAM (8)' → 8, không đọc được → 0."""
    out, header = {}, None
    for line in md.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = [re.sub(r"[`*]", "", c).strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            if any(c.lower().startswith(("port name", "tên port")) for c in cells):
                header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        col = lambda *names: next((i for i, h in enumerate(header) if h.startswith(names)), None)  # noqa: E731
        i_n, i_d, i_w = col("port name", "tên port"), col("direction", "hướng", "dir"), col("width", "độ rộng")
        name = cells[i_n] if i_n is not None and i_n < len(cells) else ""
        if not re.fullmatch(r"[A-Za-z_]\w*", name):
            continue
        d = cells[i_d].lower() if i_d is not None and i_d < len(cells) else ""
        w = cells[i_w] if i_w is not None and i_w < len(cells) else ""
        m = re.search(r"\((\d+)\)", w) or re.fullmatch(r"\s*(\d+)\s*", w)
        out[name] = ("out" if d.startswith("out") else "in", int(m.group(1)) if m else 0)
    return out


# ---------------------------------------------------------------- lớp chi tiết RTL: tokenizer + parser

class DetailError(Exception):
    pass


TOKEN = re.compile(r"""
 (?P<ws>\s+)
|(?P<num>(?:\d+\s*)?'[sS]?[bBoOdDhH]\s*[0-9a-fA-FxXzZ_?]+|\d[\d_]*)
|(?P<id>[A-Za-z_][\w$]*)
|(?P<op><<<|>>>|===|!==|==|!=|<=|>=|&&|\|\||<<|>>|~&|~\||~\^|\^~|[-+*/%<>!~&|^?:;,()\[\]{}=@])
""", re.X)
BIN_PREC = {"||": 1, "&&": 2, "|": 3, "^": 4, "~^": 4, "^~": 4, "&": 5, "==": 6, "!=": 6, "===": 6, "!==": 6,
            "<": 7, "<=": 7, ">": 7, ">=": 7, "<<": 8, ">>": 8, "<<<": 8, ">>>": 8, "+": 9, "-": 9,
            "*": 10, "/": 10, "%": 10}
GATE_OF = {"&": "and", "&&": "and", "|": "or", "||": "or", "^": "xor", "~^": "xnor", "^~": "xnor"}
CMP_OPS = {"==", "!=", "===", "!==", "<", "<=", ">", ">="}
SYM = {"==": "==", "===": "==", "!=": "!=", "!==": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">=",
       "+": "+", "-": "−", "*": "×", "/": "÷", "%": "%", "<<": "<<", ">>": ">>", "<<<": "<<<", ">>>": ">>>"}
COMMUTATIVE = {"==", "===", "!=", "!==", "+", "*"}


def tokenize(text):
    text = re.sub(r"^\s*%%.*$", "", text, flags=re.M)
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    toks, i, line = [], 0, 1
    while i < len(text):
        m = TOKEN.match(text, i)
        if not m:
            raise DetailError(f"dòng {line}: ký tự không hợp lệ {text[i]!r}")
        if m.lastgroup == "ws":
            line += m.group().count("\n")
        else:
            toks.append((m.lastgroup, m.group(), line))
        i = m.end()
    return toks


class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else ("eof", "", self.t[-1][2] if self.t else 0)

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def accept(self, v):
        k, val, _ = self.peek()
        if k != "eof" and val == v:
            self.i += 1
            return True
        return False

    def expect(self, v):
        if not self.accept(v):
            self.fail(f"cần '{v}'")

    def fail(self, msg):
        _, v, ln = self.peek()
        raise DetailError(f"dòng {ln}: {msg}, gặp {v!r}" if v else f"dòng {ln}: {msg}, gặp hết input")

    def ident(self):
        k, v, _ = self.peek()
        if k != "id":
            self.fail("cần tên tín hiệu")
        self.i += 1
        return v

    def text(self, a, b):
        s = " ".join(v for _, v, _ in self.t[a:b])
        s = re.sub(r"\s+([;,)\]])", r"\1", s)
        return re.sub(r"([(\[])\s+", r"\1", s)

    def range_opt(self):
        if self.peek()[1] != "[":
            return None
        self.next()
        hi = self.expr()
        self.expect(":")
        lo = self.expr()
        self.expect("]")
        return hi, lo

    def program(self):
        stmts, group = [], None
        while self.peek()[0] != "eof":
            start = self.i
            k, v, ln = self.peek()
            if v == "[":
                self.next()
                group = self.ident()
                self.expect("]")
                continue
            if v in ("localparam", "parameter"):
                self.next()
                self.range_opt()
                while True:
                    name = self.ident()
                    self.expect("=")
                    stmts.append({"k": "param", "name": name, "e": self.expr(), "line": ln})
                    if not self.accept(","):
                        break
                self.expect(";")
                continue
            if v in ("wire", "reg", "input", "output"):
                self.next()
                self.accept("signed")
                rng = self.range_opt()
                while True:
                    name = self.ident()
                    stmts.append({"k": "decl", "dir": v, "name": name, "rng": rng, "arr": self.range_opt(),
                                  "line": ln})
                    if not self.accept(","):
                        break
                self.expect(";")
                continue
            if group is None:
                self.fail("câu lệnh nằm ngoài khối – mở đầu bằng [<id node của mô hình>]")
            self.accept("assign")
            name, idx = self.ident(), None
            if self.accept("["):
                idx = self.expr()
                if self.peek()[1] == ":":
                    self.fail("không gán từng phần bit – gộp bằng {...} ở vế phải")
                self.expect("]")
            if self.accept("<="):
                kind = "seq"
            elif self.accept("="):
                kind = "comb"
            else:
                self.fail("cần '=' (tổ hợp) hoặc '<=' (thanh ghi)")
            e, attrs = self.expr(), {}
            if self.accept("@"):
                self.expect("(")
                while not self.accept(")"):
                    key = self.ident()
                    attrs[key] = self.expr() if self.accept("=") else None
                    self.accept(",")
            self.expect(";")
            stmts.append({"k": kind, "lhs": name, "idx": idx, "e": e, "attrs": attrs, "g": group, "line": ln,
                          "text": self.text(start, self.i)})
        return stmts

    def expr(self):
        c = self.binary(1)
        if self.accept("?"):
            a = self.expr()
            self.expect(":")
            return ("tern", c, a, self.expr())
        return c

    def binary(self, minp):
        lhs = self.unary()
        while True:
            k, v, _ = self.peek()
            p = BIN_PREC.get(v) if k == "op" else None
            if p is None or p < minp:
                return lhs
            self.next()
            lhs = ("bin", v, lhs, self.binary(p + 1))

    def unary(self):
        k, v, _ = self.peek()
        if k == "op" and v in ("!", "~", "-", "+", "&", "|", "^", "~&", "~|", "~^", "^~"):
            self.next()
            a = self.unary()
            return a if v == "+" else ("un", v, a)
        return self.primary()

    def primary(self):
        k, v, _ = self.next()
        if k == "num":
            return ("num", v.replace(" ", ""))
        if k == "id":
            if v == "case":
                return self.case_expr()
            if self.accept("["):
                hi, lo = self.expr(), None
                if self.accept(":"):
                    lo = self.expr()
                self.expect("]")
                return ("sel", v, hi, lo)
            return ("id", v)
        if v == "(":
            e = self.expr()
            self.expect(")")
            return e
        if v == "{":
            first = self.expr()
            if self.accept("{"):
                items = [self.expr()]
                while self.accept(","):
                    items.append(self.expr())
                self.expect("}")
                self.expect("}")
                return ("rep", first, items)
            items = [first]
            while self.accept(","):
                items.append(self.expr())
            self.expect("}")
            return ("cat", items)
        self.i -= 1
        self.fail("biểu thức không hợp lệ")

    def case_expr(self):
        self.expect("(")
        sel = self.expr()
        self.expect(")")
        items = []
        while not self.accept("endcase"):
            if self.peek()[0] == "eof":
                self.fail("thiếu endcase")
            if self.accept("default"):
                self.accept(":")
                labels = None
            else:
                labels = [self.expr()]
                while self.accept(","):
                    labels.append(self.expr())
                self.expect(":")
            e = self.expr()
            self.expect(";")
            items.append((labels, e))
        return ("case", sel, items)


def etext(e):
    k = e[0]
    if k in ("id", "num"):
        return e[1]
    if k == "sel":
        return f"{e[1]}[{etext(e[2])}" + (f":{etext(e[3])}" if e[3] else "") + "]"
    if k == "un":
        return e[1] + etext(e[2])
    if k == "bin":
        return f"{etext(e[2])} {e[1]} {etext(e[3])}"
    if k == "tern":
        return f"{etext(e[1])} ? {etext(e[2])} : {etext(e[3])}"
    if k == "cat":
        return "{" + ", ".join(map(etext, e[1])) + "}"
    if k == "rep":
        return "{" + etext(e[1]) + "{" + ", ".join(map(etext, e[2])) + "}}"
    return f"case ({etext(e[1])})"


def num_val(txt):
    t = txt.replace("_", "")
    m = re.fullmatch(r"(\d*)'[sS]?([bBoOdDhH])([0-9a-fA-FxXzZ?]+)", t)
    if m:
        base = {"b": 2, "o": 8, "d": 10, "h": 16}[m.group(2).lower()]
        try:
            v = int(m.group(3), base)
        except ValueError:
            v = None
        return (int(m.group(1)) if m.group(1) else 0), v
    return 0, int(t)


def ceval(e, env):
    """Giá trị hằng của biểu thức (localparam/param/số), None nếu không phải hằng."""
    k = e[0]
    if k == "num":
        return num_val(e[1])[1]
    if k == "id":
        return env.get(e[1])
    if k == "un":
        a = ceval(e[2], env)
        return None if a is None else {"-": -a, "~": ~a, "!": int(not a)}.get(e[1])
    if k == "bin":
        a, b = ceval(e[2], env), ceval(e[3], env)
        if a is None or b is None:
            return None
        ops = {"+": a + b, "-": a - b, "*": a * b, "<<": a << b if b >= 0 else None,
               ">>": a >> b if b >= 0 else None, "/": a // b if b else None, "%": a % b if b else None}
        return ops.get(e[1])
    if k == "tern":
        c = ceval(e[1], env)
        return None if c is None else ceval(e[2] if c else e[3], env)
    return None


# ---------------------------------------------------------------- lớp chi tiết → netlist primitive

class Netlist:
    def __init__(self):
        self.nodes, self.nets, self.cnt = {}, [], Counter()

    def net(self, name=None):
        self.nets.append({"id": len(self.nets), "name": name, "w": 0, "drv": None, "sinks": []})
        return len(self.nets) - 1

    def node(self, t, g, **kw):
        self.cnt[t] += 1
        nid = f"{t}{self.cnt[t]}"
        self.nodes[nid] = {"id": nid, "t": t, "g": g, "ins": [], "roles": [], "ann": [], "via": [], "outs": [],
                           **kw}
        return nid

    def connect(self, nid, src, role):
        net, ann, via = src
        n = self.nodes[nid]
        n["ins"].append(net)
        n["roles"].append(role)
        n["ann"].append(ann)
        n["via"].append(list(via))
        self.nets[net]["sinks"].append((nid, len(n["ins"]) - 1))

    def drive(self, nid, net):
        if self.nets[net]["drv"] is not None:
            raise DetailError(f"tín hiệu {self.nets[net]['name']} có hai nguồn")
        n = self.nodes[nid]
        self.nets[net]["drv"] = (nid, len(n["outs"]))
        n["outs"].append(net)


CLK_RE = re.compile(r"clk|clock", re.I)
RST_RE = re.compile(r"rst|reset", re.I)


def build_netlist(model, detail, iface=None):
    """Lớp chi tiết + mô hình khối → (netlist, lỗi, cảnh báo). Netlist None khi lỗi cú pháp."""
    errs, warns = [], []
    try:
        stmts = Parser(tokenize(detail)).program()
    except DetailError as ex:
        return None, [f"lớp chi tiết: {ex}"], []
    if not any(s["k"] in ("comb", "seq") for s in stmts):
        return None, ["lớp chi tiết trống – cần phương trình cho từng khối của mô hình"], []
    mnode = {n["id"]: n for n in model["nodes"]}
    iface = iface or {}
    nl = Netlist()

    # hằng: param của mô hình (%% param : A = 8, B = 4) và localparam của lớp chi tiết
    env = {k: int(v) for k, v in re.findall(r"([A-Za-z_]\w*)\s*=\s*(\d+)", model.get("param", ""))}
    lparam = {}
    for s in stmts:
        if s["k"] == "param":
            v = ceval(s["e"], env)
            if v is None:
                errs.append(f"dòng {s['line']}: localparam {s['name']} không tính được giá trị")
                continue
            env[s["name"]] = v
            lparam[s["name"]] = (etext(s["e"]), num_val(s["e"][1])[0] if s["e"][0] == "num" else 0)

    # width: khai báo trong lớp chi tiết > bảng port > nhãn mô hình
    widths, wsrc, mems = {}, {}, {}

    def setw(name, w, src):
        if not w:
            return
        if name in widths and widths[name] != w:
            warns.append(f"width {name}: {widths[name]} ({wsrc[name]}) khác {w} ({src})")
            return
        widths.setdefault(name, w)
        wsrc.setdefault(name, src)

    def rng_w(r, line):
        if r is None:
            return 1
        hi, lo = ceval(r[0], env), ceval(r[1], env)
        if hi is None or lo is None:
            errs.append(f"dòng {line}: không tính được khoảng bit (khai báo localparam/param trước)")
            return 0
        return abs(hi - lo) + 1

    for s in stmts:
        if s["k"] == "decl":
            w = rng_w(s["rng"], s["line"])
            if s["arr"]:
                mems[s["name"]] = {"w": w, "depth": rng_w(s["arr"], s["line"]), "node": None}
            else:
                setw(s["name"], w, "khai báo")
    for name, (_, w) in iface.items():
        setw(name, w, "bảng port")
    for text in [n["label"] for n in model["nodes"]] + [e["label"] for e in model["edges"]]:
        for nm, a, b in re.findall(r"([A-Za-z_]\w*)\s*\[(\d+):(\d+)\]", text):
            setw(nm, abs(int(a) - int(b)) + 1, "nhãn mô hình")

    # port của mô hình: node riêng (addr_i [9:0]) hoặc nhóm bus (s_apb_*)
    pnames, pgroups = {"in": {}, "out": {}}, {"in": {}, "out": {}}
    for n in model["nodes"]:
        if n["kind"] not in ("in", "out"):
            continue
        head = re.sub(r"\[[^\]]*\]", " ", lines_of(n["label"])[0].split(":")[0])
        for tok in re.findall(r"[A-Za-z_]\w*\*?", head):
            (pgroups if tok.endswith("*") else pnames)[n["kind"]][tok.rstrip("*")] = n["id"]

    def port_of(name):
        for d in ("in", "out"):
            if name in pnames[d]:
                return d, pnames[d][name]
        want = iface[name][0] if name in iface else ("out" if name.endswith("_o") else "in")
        for d in (want, "out" if want == "in" else "in"):
            for pre, nid in pgroups[d].items():
                if name.startswith(pre):
                    return d, nid
        return None, None

    assigns = [s for s in stmts if s["k"] in ("comb", "seq")]
    bad = False
    for s in assigns:
        g = mnode.get(s["g"])
        if g is None:
            errs.append(f"dòng {s['line']}: [{s['g']}] không phải node của mô hình")
            bad = True
        elif g["kind"] in ("in", "out", "note", "inst"):
            errs.append(f"dòng {s['line']}: [{s['g']}] là {g['kind']} – phương trình chỉ gắn vào khối bên trong")
            bad = True
    if bad:
        return None, errs, warns

    alias, named, seen = {}, {}, set()
    for s in assigns:
        lhs = s["lhs"]
        if s["idx"] is not None:
            if lhs not in mems:
                errs.append(f"dòng {s['line']}: chỉ bộ nhớ (reg [..] {lhs} [0:N]) mới gán theo chỉ số")
            elif s["k"] != "seq":
                errs.append(f"dòng {s['line']}: ghi bộ nhớ {lhs} phải là '<='")
            continue
        if lhs in mems or lhs in seen:
            errs.append(f"dòng {s['line']}: {lhs} được gán hai lần" if lhs in seen else
                        f"dòng {s['line']}: {lhs} là bộ nhớ – ghi theo chỉ số {lhs}[addr] <= ...")
            continue
        seen.add(lhs)
        if port_of(lhs)[0] == "in":
            errs.append(f"dòng {s['line']}: không gán vào input port {lhs}")
            continue
        e = s["e"]
        is_alias = s["k"] == "comb" and (e[0] in ("id", "num") or (
            e[0] == "sel" and e[1] not in mems and ceval(e[2], env) is not None
            and (e[3] is None or ceval(e[3], env) is not None)))
        if is_alias:
            alias[lhs] = s
        else:
            named[lhs] = nl.net(lhs)

    # input port: node theo thứ tự mô hình (kể cả port chưa dùng, để thấy đủ interface)
    def in_port(name):
        if name not in named:
            nid = nl.node("in", port_of(name)[1], name=name)
            named[name] = nl.net(name)
            nl.drive(nid, named[name])
        return named[name]
    for name in pnames["in"]:
        in_port(name)

    def mk(t, s, ins, out, roles=None, **kw):
        nid = nl.node(t, s["g"], stmt=s["text"], **kw)
        for i, src in enumerate(ins):
            nl.connect(nid, src, roles[i] if roles else f"I{i}")
        o = out if out is not None else nl.net()
        nl.drive(nid, o)
        return o, "", []

    def const(s, label, value, out=None):
        w, v = num_val(value) if re.match(r"\d|'", value) else (0, None)
        o = mk("const", s, [], out, label=label, value=value)
        nl.nets[o[0]]["w"] = w or (lparam.get(label, ("", 0))[1])
        return o

    def flatten(e, g):
        if e[0] == "bin" and GATE_OF.get(e[1]) == g:
            return flatten(e[2], g) + flatten(e[3], g)
        return [e]

    def mem_node(name, g):
        m = mems[name]
        if m["node"] is None:
            m["node"] = nl.node("mem", g, name=name, mw=m["w"], depth=m["depth"], stmt="", reads=0)
        elif g and nl.nodes[m["node"]]["g"] is None:
            nl.nodes[m["node"]]["g"] = g
        return m["node"]

    clocks = [n for n in list(pnames["in"]) + [k for k, v in iface.items() if v[0] == "in"] if CLK_RE.search(n)]
    resets = [n for n in list(pnames["in"]) + [k for k, v in iface.items() if v[0] == "in"] if RST_RE.search(n)]
    clocks, resets = list(dict.fromkeys(clocks)), list(dict.fromkeys(resets))

    def build(e, s, out=None, stack=()):
        k = e[0]
        if k == "id":
            nm = e[1]
            if nm in alias:
                if nm in stack:
                    raise DetailError(f"vòng gán bí danh qua {nm}")
                a = alias[nm]
                net, ann, via = build(a["e"], a, out, stack + (nm,))
                return net, ann, [a["g"]] + via
            if nm in lparam or (nm in env and nm not in named):
                return const(s, nm, lparam[nm][0] if nm in lparam else str(env[nm]), out)
            if nm in mems:
                raise DetailError(f"dòng {s['line']}: đọc bộ nhớ {nm} cần chỉ số {nm}[addr]")
            if nm in named:
                return named[nm], "", []
            d, _ = port_of(nm)
            if d == "in":
                return in_port(nm), "", []
            raise DetailError(f"dòng {s['line']}: {nm} không có nguồn (chưa gán trong lớp chi tiết, "
                              "không phải input port của mô hình)")
        if k == "num":
            return const(s, e[1], e[1], out)
        if k == "sel":
            base = e[1]
            if base in mems:
                m = mem_node(base, None)
                r = nl.nodes[m]["reads"]
                nl.nodes[m]["reads"] += 1
                nl.connect(m, build(e[2], s), f"RA{r}")
                o = out if out is not None else nl.net()
                nl.drive(m, o)
                return o, "", []
            hi = ceval(e[2], env)
            lo = ceval(e[3], env) if e[3] is not None else None
            if hi is None or (e[3] is not None and lo is None):
                return mk("arith", s, [build(("id", base), s), build(e[2], s)], out, ["A", "B"], op="[]", sym="[ ]")
            net, _, via = build(("id", base), s, None, stack)
            return net, (f"[{hi}:{lo}]" if e[3] is not None else f"[{hi}]"), via
        if k == "un":
            op, a = e[1], build(e[2], s)
            if op in ("~", "!"):
                return mk("gate", s, [a], out, op="not", logical=op == "!")
            if op == "-":
                return mk("arith", s, [a], out, ["A"], op="neg", sym="−")
            red = {"&": "and", "|": "or", "^": "xor", "~&": "nand", "~|": "nor", "~^": "xnor", "^~": "xnor"}[op]
            return mk("gate", s, [a], out, op=red, red=op)
        if k == "bin":
            op = e[1]
            if op in GATE_OF:
                items = flatten(e, GATE_OF[op])
                return mk("gate", s, [build(x, s) for x in items], out, op=GATE_OF[op],
                          logical=op in ("&&", "||"))
            kind = "cmp" if op in CMP_OPS else "arith"
            return mk(kind, s, [build(e[2], s), build(e[3], s)], out, ["A", "B"], op=op, sym=SYM.get(op, op))
        if k == "tern":
            return mk("mux", s, [build(e[3], s), build(e[2], s), build(e[1], s)], out, ["0", "1", "S"],
                      keys=["0", "1"], sel=etext(e[1]))
        if k == "case":
            keys, ins = [], []
            for labels, ex in e[2]:
                keys.append("default" if labels is None else ",".join(etext(x) for x in labels))
                ins.append(build(ex, s))
            return mk("mux", s, ins + [build(e[1], s)], out, keys + ["S"], keys=keys, sel=etext(e[1]))
        if k == "cat":
            return mk("concat", s, [build(x, s) for x in e[1]], out, label="{ }", rep=1)
        n = ceval(e[1], env)
        if n is None:
            raise DetailError(f"dòng {s['line']}: số lần lặp {{n{{...}}}} phải là hằng")
        return mk("concat", s, [build(x, s) for x in e[2]], out, label=f"{{{n}{{}}}}", rep=n)

    def pick(kind, attr, s, lst):
        if attr in s["attrs"]:
            a = s["attrs"][attr]
            if not a or a[0] != "id":
                raise DetailError(f"dòng {s['line']}: @({attr}=...) phải là tên input port")
            return a[1]
        if len(lst) != 1:
            raise DetailError(f"dòng {s['line']}: {'không có' if not lst else 'nhiều'} port {kind} "
                              f"({', '.join(lst) or '–'}) – ghi rõ @({attr}=<port>)")
        return lst[0]

    for s in assigns:
        try:
            g, kind = s["g"], mnode[s["g"]]["kind"]
            if s["k"] == "seq" and s["idx"] is not None:
                if s["lhs"] not in mems:
                    continue
                if kind != "mem":
                    raise DetailError(f"dòng {s['line']}: ghi bộ nhớ chỉ nằm trong khối mem_ (đang ở [{g}])")
                m = mem_node(s["lhs"], g)
                nl.nodes[m]["stmt"] += s["text"] + " "
                nl.connect(m, build(s["idx"], s), "WA")
                nl.connect(m, build(s["e"], s), "WD")
                if "en" in s["attrs"]:
                    nl.connect(m, build(s["attrs"]["en"], s), "WE")
                nl.connect(m, (in_port(pick("clock", "clk", s, clocks)), "", []), "CLK")
            elif s["k"] == "seq":
                if kind not in ("reg", "fsm"):
                    raise DetailError(f"dòng {s['line']}: thanh ghi {s['lhs']} ('<=') chỉ được nằm trong khối "
                                      f"reg_/fsm_ của mô hình – [{g}] là khối {kind}, mô hình không có thanh ghi ở đó")
                a = s["attrs"]
                rst = etext(a["rst"]) if "rst" in a and a["rst"] is not None else None
                nid = nl.node("dff", g, name=s["lhs"], rst=rst, stmt=s["text"])
                nl.connect(nid, build(s["e"], s), "D")
                if "en" in a:
                    nl.connect(nid, build(a["en"], s), "EN")
                nl.connect(nid, (in_port(pick("clock", "clk", s, clocks)), "", []), "CLK")
                if rst is not None:
                    rp = pick("reset", "reset", s, resets)
                    nl.nodes[nid]["rst_low"] = bool(re.search(r"(_n|n_i|_ni|_b)$", rp))
                    nl.connect(nid, (in_port(rp), "", []), "RST")
                nl.drive(nid, named[s["lhs"]])
            elif s["lhs"] in named:
                build(s["e"], s, named[s["lhs"]])
        except DetailError as ex:
            errs.append(str(ex))
        except RecursionError:
            errs.append(f"dòng {s['line']}: biểu thức lồng quá sâu")

    # output port: theo thứ tự mô hình, cộng các port thuộc nhóm bus được gán trong lớp chi tiết
    outs = list(pnames["out"]) + [k for k, v in iface.items() if v[0] == "out" and port_of(k)[0] == "out"]
    outs += [x for x in list(alias) + list(named) if port_of(x)[0] == "out"]
    for name in dict.fromkeys(outs):
        try:
            if name not in alias and name not in named:
                raise DetailError(f"output {name} chưa được gán trong lớp chi tiết")
            src = build(("id", name), {"g": port_of(name)[1], "line": "?", "text": ""})
            nid = nl.node("out", port_of(name)[1], name=name, pw=widths.get(name, 0))
            nl.connect(nid, src, "I")
        except DetailError as ex:
            errs.append(str(ex))
    for s in assigns:
        if s["k"] == "seq" and s["idx"] is not None and s["lhs"] in mems and mems[s["lhs"]]["node"] is None:
            errs.append(f"bộ nhớ {s['lhs']} không có node")
    for m, v in mems.items():
        if v["node"] and nl.nodes[v["node"]]["g"] is None:
            errs.append(f"bộ nhớ {m} được đọc nhưng không có phép ghi trong khối mem_")
    for net in nl.nets:
        if net["drv"] is None and net["sinks"]:
            errs.append(f"{net['name'] or 'tín hiệu'} không có nguồn")
        elif net["name"] and not net["sinks"] and net["drv"] and nl.nodes[net["drv"][0]]["t"] != "in" \
                and port_of(net["name"])[0] != "out":
            warns.append(f"{net['name']} được gán nhưng không dùng")
    unused_in = [n["name"] for n in nl.nodes.values() if n["t"] == "in" and not nl.nets[n["outs"][0]]["sinks"]]
    if unused_in:
        warns.append(f"input không dùng trong lớp chi tiết: {', '.join(unused_in)}")

    # clock/reset: net chỉ đi vào chân CLK/RST → rail
    rails = set()
    for net in nl.nets:
        if net["drv"] and nl.nodes[net["drv"][0]]["t"] == "in" and net["sinks"] and \
                all(nl.nodes[v]["roles"][i] in ("CLK", "RST") for v, i in net["sinks"]):
            rails.add(net["id"])

    # đối chiếu với mô hình khối
    content = defaultdict(Counter)
    for n in nl.nodes.values():
        content[n["g"]][n["t"]] += 1
    groups_used = {s["g"] for s in assigns}
    for n in model["nodes"]:
        k = n["kind"]
        if k in ("in", "out", "note", "inst"):
            continue
        if n["id"] not in groups_used:
            errs.append(f"khối {n['id']} của mô hình chưa có phương trình nào trong lớp chi tiết")
            continue
        need = {"reg": ("dff",), "fsm": ("dff",), "mem": ("mem",), "mux": ("mux",), "op": ("arith", "cmp")}.get(k)
        if need and not any(content[n["id"]][t] for t in need):
            errs.append(f"khối {n['id']} ({k}) cần có {'/'.join(need)} trong lớp chi tiết")
    rail_ports = {nl.nodes[nl.nets[r]["drv"][0]]["g"] for r in rails}
    mpairs = {}
    for e in model["edges"]:
        if mnode[e["src"]]["kind"] == "note" or mnode[e["dst"]]["kind"] == "note" or e["src"] == e["dst"]:
            continue
        if e["src"] in rail_ports and mnode[e["src"]]["kind"] == "in":
            continue
        mpairs.setdefault((e["src"], e["dst"]), e)
    pairs = defaultdict(set)
    for net in nl.nets:
        if net["drv"] is None or net["id"] in rails:
            continue
        a = nl.nodes[net["drv"][0]]["g"]
        for v, i in net["sinks"]:
            if nl.nodes[v]["roles"][i] in ("CLK", "RST"):
                continue
            path = [a] + list(reversed(nl.nodes[v]["via"][i])) + [nl.nodes[v]["g"]]
            for x, y in zip(path, path[1:]):
                if x != y:
                    pairs[(x, y)].add(net["name"] or "?")
    for (x, y), sigs in pairs.items():
        if (x, y) not in mpairs:
            errs.append(f"lớp chi tiết nối {x} → {y} ({', '.join(sorted(sigs))}) nhưng mô hình không có cạnh "
                        f"{x} → {y} – sửa lớp chi tiết, hoặc sửa mô hình nếu mô hình thiếu")
    for (x, y), e in mpairs.items():
        if (x, y) not in pairs:
            errs.append(f"mô hình có cạnh {x} → {y} \"{e['label']}\" nhưng lớp chi tiết không có tín hiệu nào "
                        f"đi từ {x} sang {y}")

    # width
    for net in nl.nets:
        if net["name"] in widths:
            net["w"] = widths[net["name"]]
    infer_widths(nl, mems)
    for net in nl.nets:
        nm = net["name"]
        if nm and nm in widths and net["w"] != widths[nm]:
            warns.append(f"width {nm}: {net['w']} khác {widths[nm]}")
    unknown = sorted({n["name"] for n in nl.nets if not n["w"] and n["name"] and n["sinks"]})
    if unknown:
        warns.append(f"không xác định width: {', '.join(unknown)} – khai báo wire/reg [..] trong lớp chi tiết")

    classify(nl, rails, model, mpairs)
    nl.rails = rails
    nl.groups = {s["g"] for s in assigns}
    return nl, errs, warns


def ann_w(ann):
    """Width của bit/part-select gắn tại chân ('[15]' → 1, '[7:4]' → 4), 0 nếu không có."""
    m = re.fullmatch(r"\[(-?\d+)(?::(-?\d+))?\]", ann or "")
    return (abs(int(m.group(1)) - int(m.group(2))) + 1 if m.group(2) else 1) if m else 0


def infer_widths(nl, mems):
    N, nets = nl.nodes, nl.nets
    flex = lambda x: N[nets[x]["drv"][0]]["t"] == "const" and not nets[x]["w"] if nets[x]["drv"] else False  # noqa
    for _ in range(60):
        changed = False
        for n in N.values():
            t, ins = n["t"], n["ins"]
            iw = [ann_w(n["ann"][i]) or nets[x]["w"] for i, x in enumerate(ins)]
            ok = lambda idx: idx and all(iw[i] or flex(ins[i]) for i in idx) and any(iw[i] for i in idx)  # noqa
            mx = lambda idx: max(iw[i] for i in idx)  # noqa: E731
            w = 0
            data = [i for i, r in enumerate(n["roles"]) if r not in ("S", "EN", "CLK", "RST")]
            if t == "cmp" or (t == "gate" and (n.get("logical") or n.get("red"))):
                w = 1
            elif t == "gate" and ok(data):
                w = mx(data)
            elif t == "arith":
                if n["op"] == "[]":
                    w = 1
                elif n["op"] in ("<<", ">>", "<<<", ">>>", "neg"):
                    w = iw[0]
                elif ok(data):
                    w = mx(data)
            elif t == "mux" and ok(data):
                w = mx(data)
            elif t == "concat" and all(iw[i] for i in range(len(ins)) if not flex(ins[i])) and any(iw):
                w = sum(iw) * n.get("rep", 1)
            elif t == "dff":
                w = iw[0]
                q = nets[n["outs"][0]]["w"] if n["outs"] else 0
                d = ins[0]
                if q and not iw[0] and nets[d]["drv"] and N[nets[d]["drv"][0]]["t"] != "const":
                    nets[d]["w"], changed = q, True
            elif t == "mem":
                w = n["mw"]
            for o in n["outs"]:
                if w and not nets[o]["w"]:
                    nets[o]["w"], changed = w, True
        if not changed:
            break


def classify(nl, rails, model, mpairs):
    """Loại net: clk (rail clock/reset), ctrl (1 bit chỉ đi vào select/enable/điều kiện), data."""
    N, nets = nl.nodes, nl.nets
    cls = {}
    for net in nets:
        cls[net["id"]] = "clk" if net["id"] in rails else ("ctrl" if net["w"] == 1 else "data")
    etype = {k: e["type"] for k, e in mpairs.items()}
    for _ in range(40):
        changed = False
        for net in nets:
            if cls[net["id"]] != "ctrl":
                continue
            for v, i in net["sinks"]:
                n, role = N[v], N[v]["roles"][i]
                if role in ("S", "EN", "WE", "CLK", "RST"):
                    continue
                if n["t"] in ("gate", "cmp"):
                    if n["outs"] and cls[n["outs"][0]] == "ctrl":
                        continue
                elif n["t"] == "out":
                    a = N[net["drv"][0]]["g"] if net["drv"] else None
                    if etype.get((a, n["g"])) == "control":
                        continue
                cls[net["id"]], changed = "data", True
                break
        if not changed:
            break
    for net in nets:
        net["cls"] = cls[net["id"]]


# ---------------------------------------------------------------- hình học primitive

FS, CW = 11, 6.6          # font chính (monospace) và bề rộng ký tự
SCW = 5.8                 # ký tự nhỏ (nhãn chân, hằng)
PG = 20                   # khoảng cách chân chuẩn
GAP, DGAP = 26, 10        # khe giữa node trong một cột / quanh node ảo
TRACK, CH_PAD = 9, 10     # khoảng giữa track dọc trong kênh / lề kênh
LANE0, LANE_P = 24, 12    # lane feedback phía trên
RAIL0, RAIL_P = 30, 26   # rail clock/reset phía dưới


def tw(s, cw=CW):
    return len(unicodedata.normalize("NFC", str(s))) * cw


def wtxt(w):
    return f"[{w - 1}:0]" if w and w > 1 else ""


def gate_back(base, h, y):
    t = y / h if h else 0.5
    return {"and": 0.0, "or": 16 * t * (1 - t), "xor": 5 + 16 * t * (1 - t)}.get(base, 0.0)


def geom(n, nets):
    t, k = n["t"], len(n["ins"])
    pin = lambda dy, *pts: {"dy": dy, "pts": [(0, dy), *pts]}  # noqa: E731
    if t in ("in", "out"):
        w = nets[n["outs"][0]]["w"] if t == "in" else n.get("pw") or ann_w(n["ann"][0]) or nets[n["ins"][0]]["w"]
        n["text"] = n["name"] + wtxt(w)
        g = {"w": tw(n["text"]) + 24, "h": 20}
        g.update({"S": [], "O": [10]} if t == "in" else {"S": [pin(10)], "O": []})
        return g
    if t == "dummy":
        return {"w": 0, "h": 0, "S": [pin(0)], "O": [0]}
    if t == "dff":
        T, BW = 16, 56
        bh = PG * k + 8
        w = nets[n["outs"][0]]["w"] if n["outs"] else 0
        n["cap"] = " ".join(x for x in (wtxt(w), f"rst={n['rst']}" if n.get("rst") else "") if x)
        W = max(BW + 8, tw(n["name"]) + 6, tw(n["cap"], SCW) + 6)
        bx = (W - BW) / 2
        S = [pin(T + 14 + PG * i, (bx - (5 if r == "RST" and n.get("rst_low") else 0), T + 14 + PG * i))
             for i, r in enumerate(n["roles"])]
        return {"w": W, "h": T + bh + 16, "S": S, "O": [T + 14], "bx": bx, "bw": BW, "T": T, "bh": bh}
    if t == "mux":
        keys = n["keys"]
        m = len(keys)
        bw = max(28, max(tw(x, SCW) for x in keys) + 16)
        H, T = PG * m + 12, 4
        s = min(12, H / 4)
        S = [pin(T + 16 + PG * i) for i in range(m)]
        sy = T + H + 12
        S.append(pin(sy, (bw / 2, sy), (bw / 2, T + H - s / 2)))
        return {"w": bw, "h": T + H + 16, "S": S, "O": [T + H / 2], "T": T, "H": H, "s": s}
    if t == "cmp":
        return {"w": 40, "h": 40, "S": [pin(10), pin(30)], "O": [20]}
    if t == "arith":
        d = max(40, tw(n["sym"], 8.4) + 18)
        r = d / 2
        dys = [r - 10, r + 10] if k == 2 else [r]
        return {"w": d, "h": d, "S": [pin(y, (r - math.sqrt(r * r - (y - r) ** 2), y)) for y in dys], "O": [r]}
    if t == "gate":
        op = n["op"]
        if op == "not":
            return {"w": 30, "h": 22, "S": [pin(11)], "O": [11]}
        base = {"nand": "and", "nor": "or", "xnor": "xor"}.get(op, op)
        h = max(28, 16 * k + 8)
        bub = op in ("nand", "nor", "xnor")
        bw = max(36, h / 2 + 16) + (5 if base == "xor" else 0)
        dys = [h / 2 + (i - (k - 1) / 2) * 16 for i in range(k)]
        S = [pin(y, (gate_back(base, h, y), y)) if base != "and" else pin(y) for y in dys]
        return {"w": bw + (6 if bub else 0), "h": h, "S": S, "O": [h / 2], "base": base, "bw": bw, "bub": bub}
    if t == "concat":
        T = 14
        h = 16 * k + 8
        return {"w": 10, "h": T + h, "S": [pin(T + 12 + 16 * i) for i in range(k)], "O": [T + h / 2], "T": T}
    if t == "mem":
        order = sorted(range(k), key=lambda i: ({"WA": 0, "WD": 1, "WE": 2, "CLK": 9}.get(n["roles"][i], 5),
                                                n["roles"][i]))
        T, BW = 16, 84
        rows = {i: r for r, i in enumerate(order)}
        S = [None] * k
        for i in range(k):
            S[i] = pin(T + 14 + PG * rows[i])
        O = []
        reads = [i for i in order if n["roles"][i].startswith("RA")]
        for j in range(len(n["outs"])):
            O.append(T + 14 + PG * rows[reads[j]] if j < len(reads) else T + 14)
        n["cap"] = f"{wtxt(n['mw']) or '[0:0]'} × {n['depth']}"
        W = max(BW, tw(n["name"]) + 6)
        return {"w": W, "h": T + PG * k + 8 + 16, "S": S, "O": O, "T": T, "bh": PG * k + 8, "order": order}
    raise ValueError(t)


# ---------------------------------------------------------------- layout

def pava(target):
    """Hồi quy đẳng trương: z không giảm, gần target nhất (bình phương tối thiểu)."""
    blocks = []
    for t in target:
        blocks.append([t, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            s, c = blocks.pop()
            blocks[-1][0] += s
            blocks[-1][1] += c
    out = []
    for s, c in blocks:
        out += [s / c] * c
    return out


def permutable(n):
    return (n["t"] == "gate" and not n.get("red") and len(n["ins"]) > 1) or \
           (n["t"] in ("cmp", "arith") and n.get("op") in COMMUTATIVE)


def layout(nl):
    N, nets, rails = nl.nodes, nl.nets, nl.rails
    G = {}
    railport = {}
    for nid, n in N.items():
        if n["t"] == "const":
            continue
        if n["t"] == "in" and nets[n["outs"][0]]["id"] in rails:
            railport[nets[n["outs"][0]]["id"]] = nid
        G[nid] = dict(geom(n, nets), t=n["t"])
        G[nid]["slot"] = list(range(len(n["ins"])))
    pinconst = {}
    for nid, n in N.items():
        if n["t"] == "const":
            for v, i in nets[n["outs"][0]]["sinks"]:
                pinconst[(v, i)] = nid
    E = []
    for net in nets:
        if net["id"] in rails or net["drv"] is None or net["drv"][0] not in G:
            continue
        u, sp = net["drv"]
        for v, i in net["sinks"]:
            E.append({"i": len(E), "src": u, "sp": sp, "dst": v, "dp": i, "net": net["id"]})

    # cắt vòng: ưu tiên cắt cạnh ra từ phần tử tuần tự (Q → logic) làm feedback
    seq = {"dff", "mem"}
    adj = defaultdict(set)

    def reaches(a, b):
        seen, todo = set(), [a]
        while todo:
            x = todo.pop()
            if x == b:
                return True
            if x not in seen:
                seen.add(x)
                todo += adj[x]
        return False
    fb = set()
    for e in sorted(E, key=lambda e: (G[e["src"]]["t"] in seq, e["i"])):
        if e["src"] == e["dst"] or reaches(e["dst"], e["src"]):
            fb.add(e["i"])
        else:
            adj[e["src"]].add(e["dst"])
    preds = defaultdict(set)
    for u, vs in adj.items():
        for v in vs:
            preds[v].add(u)

    rank = {}
    inner = [v for v in G if G[v]["t"] not in ("in", "out") and v not in railport.values()]

    def rk(v):
        if v not in rank:
            if G[v]["t"] == "in":
                rank[v] = 0
            else:
                rank[v] = 1 + max([rk(u) for u in preds[v] if G[u]["t"] != "out"], default=0)
        return rank[v]
    for v in inner:
        rk(v)
    LO = max([rank[v] for v in inner], default=0) + 1
    for v in G:
        if G[v]["t"] == "in":
            rank[v] = 0
        elif G[v]["t"] == "out":
            rank[v] = LO
    topo = sorted(inner, key=lambda v: rank[v])
    for v in reversed(topo):           # kéo node về phải, sát nơi dùng
        succ = [rank[w] for w in adj[v]]
        if succ:
            rank[v] = max(rank[v], min(succ) - 1)
    layer = dict(rank)
    fb = {i for i in fb if layer[E[i]["dst"]] <= layer[E[i]["src"]]}

    # node ảo cho cạnh dài, dùng chung theo (net, layer)
    links, dummy, seen_l = [], {}, set()
    for e in E:
        if e["i"] in fb:
            continue
        prev = (e["src"], e["sp"])
        for lv in range(layer[e["src"]] + 1, layer[e["dst"]]):
            key = (e["net"], lv)
            if key not in dummy:
                did = f"~d{len(dummy)}"
                dummy[key] = did
                G[did] = dict(geom({"t": "dummy", "ins": [None]}, nets), t="dummy", slot=[0])
                layer[did] = lv
            did = dummy[key]
            if (prev, did) not in seen_l:
                seen_l.add((prev, did))
                links.append({"src": prev[0], "sp": prev[1], "dst": did, "dp": 0, "net": e["net"]})
            prev = (did, 0)
        links.append({"src": prev[0], "sp": prev[1], "dst": e["dst"], "dp": e["dp"], "net": e["net"]})
    fbl = [{"src": E[i]["src"], "sp": E[i]["sp"], "dst": E[i]["dst"], "dp": E[i]["dp"], "net": E[i]["net"],
            "fb": True} for i in sorted(fb)]
    ins_of, outs_of = defaultdict(list), defaultdict(list)
    for lk in links:
        ins_of[lk["dst"]].append(lk)
        outs_of[lk["src"]].append(lk)

    # thứ tự trong layer: barycenter theo chân, giữ thứ tự ít giao cắt nhất
    L = [[] for _ in range(LO + 1)]
    for v in G:
        if v in layer and v not in railport.values():
            L[layer[v]].append(v)
    pos = {}
    for lay in L:
        pos.update({v: i for i, v in enumerate(lay)})

    def fo(v, sp):
        g = G[v]
        return pos[v] + (g["O"][sp] / (g["h"] + 1) if g["h"] else 0) * 0.8

    def fi(v, dp):
        g = G[v]
        if permutable(N.get(v, {"t": "dummy", "ins": []})):
            return pos[v] + 0.4
        return pos[v] + (g["S"][g["slot"][dp]]["dy"] / (g["h"] + 1) if g["h"] else 0) * 0.8

    def crossings():
        c = 0
        for lv in range(LO):
            ls = [(fo(lk["src"], lk["sp"]), fi(lk["dst"], lk["dp"])) for v in L[lv] for lk in outs_of[v]]
            for i in range(len(ls)):
                for j in range(i + 1, len(ls)):
                    if (ls[i][0] - ls[j][0]) * (ls[i][1] - ls[j][1]) < 0:
                        c += 1
        return c
    best, bestc = [list(x) for x in L], crossings()
    for it in range(16):
        rng = range(1, LO + 1) if it % 2 == 0 else range(LO - 1, -1, -1)
        for lv in rng:
            bc = {}
            for v in L[lv]:
                nb = [fo(lk["src"], lk["sp"]) for lk in ins_of[v]] if it % 2 == 0 else \
                     [fi(lk["dst"], lk["dp"]) for lk in outs_of[v]]
                bc[v] = sum(nb) / len(nb) if nb else pos[v]
            L[lv].sort(key=lambda v: (bc[v], pos[v]))
            pos.update({v: i for i, v in enumerate(L[lv])})
        c = crossings()
        if c < bestc:
            best, bestc = [list(x) for x in L], c
    L = best
    for lay in L:
        pos.update({v: i for i, v in enumerate(lay)})

    # tọa độ y: căn chân thẳng hàng (lặp tiến/lùi, PAVA giữ thứ tự và khe)
    y = {}
    for lay in L:
        acc = 0
        for v in lay:
            y[v] = acc
            acc += G[v]["h"] + GAP

    def py_out(v, sp):
        return y[v] + G[v]["O"][sp]

    def py_in(v, dp):
        return y[v] + G[v]["S"][G[v]["slot"][dp]]["dy"]

    src_of = {}
    for lk in links + fbl:
        src_of[(lk["dst"], lk["dp"])] = lk

    def assign_perm():
        for v, g in G.items():
            n = N.get(v)
            if not n or not permutable(n):
                continue
            k = len(n["ins"])

            def key(i):
                lk = src_of.get((v, i))
                if lk is None:
                    return 1e9 + i
                return py_out(lk["src"], lk["sp"]) if not lk.get("fb") else -1e9 + i
            order = sorted(range(k), key=key)
            for s, i in enumerate(order):
                g["slot"][i] = s

    def weight(lk):
        n = N.get(lk["dst"])
        if n is None:
            return 2.0
        role = n["roles"][lk["dp"]]
        return 0.6 if role in ("S", "EN", "WE") else 2.0

    def gap(a, b):
        return DGAP if "dummy" in (G[a]["t"], G[b]["t"]) else GAP

    def place(lay, want):
        if not lay:
            return
        off = [0.0]
        for a, b in zip(lay, lay[1:]):
            off.append(off[-1] + G[a]["h"] + gap(a, b))
        z = pava([want[v] - o for v, o in zip(lay, off)])
        for v, zz, o in zip(lay, z, off):
            y[v] = zz + o

    for it in range(24):
        assign_perm()
        if it % 2 == 0:
            for lv in range(1, LO + 1):
                want = {}
                for v in L[lv]:
                    d = [(py_out(lk["src"], lk["sp"]) - G[v]["S"][G[v]["slot"][lk["dp"]]]["dy"], weight(lk))
                         for lk in ins_of[v]]
                    want[v] = sum(a * w for a, w in d) / sum(w for _, w in d) if d else y[v]
                place(L[lv], want)
        else:
            for lv in range(LO - 1, -1, -1):
                want = {}
                for v in L[lv]:
                    d = [(py_in(lk["dst"], lk["dp"]) - G[v]["O"][lk["sp"]], weight(lk)) for lk in outs_of[v]]
                    want[v] = sum(a * w for a, w in d) / sum(w for _, w in d) if d else y[v]
                place(L[lv], want)
    assign_perm()

    # nắn thẳng: dây lệch vài px → dịch node cho thẳng nếu không chạm node kề
    for lv in list(range(1, LO + 1)) + [0] + list(range(1, LO + 1)):
        lay = L[lv]
        for i, v in enumerate(lay):
            if lv == 0:
                cand = [py_in(lk["dst"], lk["dp"]) - G[v]["O"][lk["sp"]] for lk in outs_of[v]]
            else:
                cand = [py_out(lk["src"], lk["sp"]) - G[v]["S"][G[v]["slot"][lk["dp"]]]["dy"] for lk in ins_of[v]]
            cand = [c for c in cand if 0.5 < abs(c - y[v]) < 16]
            if not cand:
                continue
            ny = min(cand, key=lambda c: abs(c - y[v]))
            lo_ok = i == 0 or ny >= y[lay[i - 1]] + G[lay[i - 1]]["h"] + gap(lay[i - 1], v) - 0.5
            hi_ok = i == len(lay) - 1 or ny + G[v]["h"] + gap(v, lay[i + 1]) <= y[lay[i + 1]] + 0.5
            if lo_ok and hi_ok:
                y[v] = ny
    top = min([y[v] for v in y] + [0])
    for v in y:
        y[v] -= top
    bottom = max([y[v] + G[v]["h"] for v in y] + [0])

    # feedback lane phía trên, rail clock/reset phía dưới
    fb_nets = list(dict.fromkeys(lk["net"] for lk in fbl))
    span = {k: max(layer[lk["src"]] for lk in fbl if lk["net"] == k)
            - min(layer[lk["dst"]] for lk in fbl if lk["net"] == k) for k in fb_nets}
    fb_nets.sort(key=lambda k: span[k])
    lane = {k: -LANE0 - i * LANE_P for i, k in enumerate(fb_nets)}
    rail_order = sorted(rails, key=lambda r: (0 if CLK_RE.search(nets[r]["name"]) else 1, r))
    rail_y = {r: bottom + RAIL0 + i * RAIL_P for i, r in enumerate(rail_order)}
    for r, v in railport.items():
        y[v] = rail_y[r] - G[v]["O"][0]
        layer[v] = 0

    # nhóm định tuyến theo kênh (kênh c nằm giữa cột c và c+1)
    ch = [dict() for _ in range(LO)]

    def grp(c, key, src, sp, net):
        return ch[c].setdefault(key, {"net": net, "src": src, "sp": sp, "d": [], "lane": None})
    for lk in links:
        grp(layer[lk["src"]], ("n", lk["src"], lk["sp"]), lk["src"], lk["sp"], lk["net"])["d"].append(lk)
    for lk in fbl:
        g = grp(layer[lk["src"]], ("n", lk["src"], lk["sp"]), lk["src"], lk["sp"], lk["net"])
        g["lane"] = lane[lk["net"]]
        c = layer[lk["dst"]] - 1
        g2 = grp(c, ("fb", lk["net"], c), None, None, lk["net"])
        g2["lane"] = lane[lk["net"]]
        g2["d"].append(lk)
    for r in rails:
        for v, i in nets[r]["sinks"]:
            c = layer[v] - 1
            g = grp(c, ("rail", r, c), None, None, r)
            g["lane"] = rail_y[r]
            g["d"].append({"src": None, "sp": None, "dst": v, "dp": i, "net": r, "rail": True})
    def inside(v, g):
        return v is not None and g["lo"] - 0.5 <= v <= g["hi"] + 0.5

    def cross(a, b):
        """Số giao cắt khi track của a nằm bên trái track của b."""
        return inside(b["sy"], a) + sum(inside(v, b) for v in a["ys"])

    ntr = []
    for c, groups in enumerate(ch):
        order = []
        for g in groups.values():
            g["ys"] = [py_in(lk["dst"], lk["dp"]) for lk in g["d"]]
            g["sy"] = py_out(g["src"], g["sp"]) if g["src"] is not None else None
            ys = g["ys"] + [v for v in (g["sy"], g["lane"]) if v is not None]
            g["lo"], g["hi"], g["t"] = min(ys), max(ys), None
        for g in sorted((g for g in groups.values() if g["hi"] - g["lo"] > 0.5 or g["lane"] is not None
                         or len(g["d"]) > 1), key=lambda g: (g["lo"], g["hi"])):
            best_i = min(range(len(order) + 1), key=lambda i: sum(cross(o, g) for o in order[:i])
                         + sum(cross(g, o) for o in order[i:]))
            order.insert(best_i, g)
        for t, g in enumerate(order):
            g["t"] = t
        ntr.append(len(order))

    # cột và kênh: chỗ cho nhãn net ở đầu nguồn, track dọc, nhãn/hằng ở đầu đích
    colw = [max([G[v]["w"] for v in lay] + [16 if lv in (0, LO) else 24]) for lv, lay in enumerate(L)]
    colw[0] = max([colw[0]] + [G[v]["w"] for v in railport.values()])

    def xoff(v, lv):
        t = G[v]["t"]
        return colw[lv] - G[v]["w"] if t == "in" else 0 if t == "out" else (colw[lv] - G[v]["w"]) / 2

    def src_label(g):
        if g["src"] is None or G[g["src"]]["t"] in ("dummy", "in"):
            return ""
        net = nets[g["net"]]
        if net["name"] and all(N[v]["t"] == "out" and N[v]["name"] == net["name"] for v, _ in net["sinks"]):
            return ""
        return (net["name"] or "") + wtxt(net["w"]) if (net["name"] or net["w"] > 1) else ""

    def sink_label(lk):
        if G[lk["dst"]]["t"] == "dummy" or lk.get("rail"):
            return ""
        n = N[lk["dst"]]
        ann = n["ann"][lk["dp"]]
        if lk.get("fb"):
            net = nets[lk["net"]]
            return (net["name"] or "") + (ann or wtxt(net["w"]))
        return ann

    srcw, sinkw = [0.0] * LO, [0.0] * LO
    for c, groups in enumerate(ch):
        for g in groups.values():
            lab = src_label(g)
            if lab:
                gapx = colw[c] - xoff(g["src"], c) - G[g["src"]]["w"]
                srcw[c] = max(srcw[c], tw(lab, SCW) + 10 - gapx)
            g["label"] = lab
            for lk in g["d"]:
                lab2 = sink_label(lk)
                lk["label"] = lab2
                if lab2:
                    sinkw[c] = max(sinkw[c], tw(lab2, SCW) + 12 - xoff(lk["dst"], c + 1))
    for (v, i), cn in pinconst.items():
        if v in G and layer.get(v, 0) >= 1:
            c = layer[v] - 1
            sinkw[c] = max(sinkw[c], tw(N[cn]["label"], SCW) + 10 + 14 - xoff(v, layer[v]))
    chw = [max(36, srcw[c] + CH_PAD + ntr[c] * TRACK + CH_PAD + sinkw[c]) for c in range(LO)]
    x, colx, chx = 0, [], []
    for lv in range(LO + 1):
        colx.append(x)
        x += colw[lv]
        if lv < LO:
            chx.append(x)
            x += chw[lv]
    for v in G:
        if v in layer:
            G[v]["x"] = colx[layer[v]] + xoff(v, layer[v])
            G[v]["y"] = y[v]
    return {"G": G, "L": L, "layer": layer, "links": links, "fbl": fbl, "ch": ch, "chx": chx, "colx": colx,
            "colw": colw, "srcw": srcw, "chw": chw, "lane": lane, "rail_y": rail_y, "railport": railport,
            "pinconst": pinconst, "width": x, "LO": LO, "bottom": bottom}


# ---------------------------------------------------------------- SVG

def esc(s):
    return html.escape(str(s), quote=True)


def text(x, y, s, cls="", anchor="start"):
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}">{esc(s)}</text>'


def f1(v):
    return f"{v:.1f}"


def svg_of(model, nl, lay):
    N, nets, G = nl.nodes, nl.nets, lay["G"]
    ch, chx, colx, colw, LO = lay["ch"], lay["chx"], lay["colx"], lay["colw"], lay["LO"]
    lanes = list(lay["lane"].values())
    rails = list(lay["rail_y"].values())
    top = min(lanes + [0]) - 40
    bot = max(rails + [lay["bottom"]]) + 18
    ox, oy = 16, -top + 16
    X = lambda v: v + ox  # noqa: E731
    Y = lambda v: v + oy  # noqa: E731
    out = []

    # khung module: cổng ở ngoài, logic ở trong
    bx0 = chx[0] + 4 if LO > 0 else 0
    bx1 = max(colx[LO] - 4, bx0 + 120)
    out.append(f'<rect class="mod" x="{f1(X(bx0))}" y="{f1(Y(top))}" width="{f1(bx1 - bx0)}" '
               f'height="{f1(bot - top)}" rx="4"/>')
    out.append(text(X(bx0) + 10, Y(top) + 17, model["module"], "modname"))

    segs, dots, labels = defaultdict(list), defaultdict(list), []

    def entry(v, dp):
        g = G[v]
        if g["t"] == "dummy":
            return [(G[v]["x"], G[v]["y"])]
        s = g["S"][g["slot"][dp]]
        return [(g["x"] + px, g["y"] + py) for px, py in s["pts"]]

    def path_to(x0, pts, arrow):
        d = f"M{f1(X(x0))},{f1(Y(pts[0][1]))} H{f1(X(pts[0][0]))}" + "".join(
            f" L{f1(X(px))},{f1(Y(py))}" for px, py in pts[1:])
        return d, arrow

    lane_x = defaultdict(list)
    for c, groups in enumerate(ch):
        tx0 = chx[c] + lay["srcw"][c] + CH_PAD
        for g in groups.values():
            k = g["net"]
            xt = tx0 + g["t"] * TRACK if g["t"] is not None else None
            src = None
            if g["src"] is not None:
                s = G[g["src"]]
                sx = s["x"] + s["w"] if s["t"] != "dummy" else colx[c] + colw[c]
                src = (sx, s["y"] + s["O"][g["sp"]])
                if g.get("label"):
                    labels.append((src[0] + 4, src[1] - 4, g["label"], k, "start"))
            ends = []
            for lk in g["d"]:
                pts = entry(lk["dst"], lk["dp"])
                if G[lk["dst"]]["t"] == "dummy":
                    pts = [(colx[c + 1], pts[0][1])]
                ends.append((pts, lk))
                if lk.get("label"):
                    labels.append((pts[0][0] - 6, pts[0][1] - 4, lk["label"], k, "end"))
            arrow = lambda lk: G[lk["dst"]]["t"] != "dummy"  # noqa: E731
            if xt is None:
                for pts, lk in ends:
                    segs[k].append(path_to(src[0], pts, arrow(lk)))
                continue
            if src:
                segs[k].append((f"M{f1(X(src[0]))},{f1(Y(src[1]))} H{f1(X(xt))}", False))
            segs[k].append((f"M{f1(X(xt))},{f1(Y(g['lo']))} V{f1(Y(g['hi']))}", False))
            for pts, lk in ends:
                segs[k].append(path_to(xt, pts, arrow(lk)))
            if g["lane"] is not None:
                lane_x[(k, g["lane"])].append(xt)
            # chấm nối: điểm trên track có ≥ 3 nhánh
            pts_y = [p[0][1] for p, _ in ends] + ([src[1]] if src else [])
            for py in sorted(set(round(p, 1) for p in pts_y + ([g["lane"]] if g["lane"] is not None else []))):
                hor = sum(1 for p in pts_y if abs(p - py) < 0.5)
                deg = hor + (py > g["lo"] + 0.5) + (py < g["hi"] - 0.5)
                if g["lane"] is not None and abs(py - g["lane"]) < 0.5:
                    deg += 1
                if deg >= 3:
                    dots[k].append((xt, py))
    # đoạn xuyên cột của node ảo
    for v, g in G.items():
        if g["t"] == "dummy":
            lv = lay["layer"][v]
            k = next(lk["net"] for lk in lay["links"] if lk["src"] == v)
            segs[k].append((f"M{f1(X(colx[lv]))},{f1(Y(g['y']))} H{f1(X(colx[lv] + colw[lv]))}", False))
    # lane feedback / rail clock-reset
    for (k, ly), xs in lane_x.items():
        if k in lay["rail_y"]:
            p = G[lay["railport"][k]]
            x0 = p["x"] + p["w"]
            xs = sorted(xs)
            segs[k].append((f"M{f1(X(x0))},{f1(Y(ly))} H{f1(X(xs[-1]))}", False))
            for xx in xs[:-1]:
                dots[k].append((xx, ly))
        elif len(xs) >= 2:
            xs = sorted(xs)
            segs[k].append((f"M{f1(X(xs[0]))},{f1(Y(ly))} H{f1(X(xs[-1]))}", False))
            for xx in xs[1:-1]:
                dots[k].append((xx, ly))
    # hằng gắn tại chân
    consts = []
    for (v, i), cn in lay["pinconst"].items():
        if v not in G or "x" not in G[v]:
            continue
        pts = entry(v, i)
        lab = N[cn]["label"]
        w = tw(lab, SCW) + 8
        x1 = pts[0][0] - 12
        k = N[cn]["outs"][0]
        segs[k].append(path_to(x1, pts, True))
        consts.append((x1 - w, pts[0][1] - 8, w, lab, N[cn]))

    for k, ss in segs.items():
        net = nets[k]
        cls = {"clk": "clkn", "ctrl": "ctrl", "data": "data"}[net["cls"]] + (" bus" if net["w"] > 1 else "")
        name = (net["name"] or "") + wtxt(net["w"]) or "(internal net)"
        out.append(f'<g class="net {cls}" data-net="{k}"><title>{esc(name)}</title>')
        for d, arrow in ss:
            out.append(f'<path class="hit" d="{d}"/><path class="w" d="{d}"'
                       + (' marker-end="url(#arr)"' if arrow else "") + "/>")
        for xx, yy in dots[k]:
            out.append(f'<circle class="dot" cx="{f1(X(xx))}" cy="{f1(Y(yy))}" r="3"/>')
        out.append("</g>")

    for v, g in G.items():
        if g["t"] == "dummy" or "x" not in g:
            continue
        out.append(node_svg(N[v], g, X(g["x"]), Y(g["y"])))
    for x0, y0, w, lab, n in consts:
        tip = f"{n['label']} = {n['value']}" if n["label"] != n["value"] else n["label"]
        out.append(f'<g class="node t-const" data-g="{esc(n["g"])}"><title>{esc(n["g"])} · constant {esc(tip)}'
                   f'</title><rect class="shape" x="{f1(X(x0))}" y="{f1(Y(y0))}" width="{f1(w)}" height="16" '
                   f'rx="2"/>{text(X(x0) + w / 2, Y(y0) + 11.5, lab, "cst", "middle")}</g>')
    for xx, yy, s, k, anchor in labels:
        cls = {"clk": "lbl clkl", "ctrl": "lbl ctrl", "data": "lbl"}[nets[k]["cls"]]
        out.append(f'<g data-net="{k}">' + text(X(xx), Y(yy), s, cls, anchor) + "</g>")
    W, H = X(lay["width"]) + 16, Y(bot) + 16
    defs = ('<defs><marker id="arr" viewBox="0 0 8 8" refX="7.6" refY="4" markerWidth="7" markerHeight="7" '
            'markerUnits="userSpaceOnUse" orient="auto"><path d="M0,0.6 L8,4 L0,7.4 z" class="arrow"/></marker></defs>')
    return W, H, (f'<svg id="sch" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
                  f'data-w="{W:.0f}" data-h="{H:.0f}" role="img" '
                  f'aria-label="RTL schematic {esc(model["module"])}">' + defs + "".join(out) + "</svg>")


def node_svg(n, g, x, y):
    t, w, h = n["t"], g["w"], g["h"]
    tip = f"{n['g']} · {n.get('stmt') or n.get('name', '')}".strip()
    o = [f'<g class="node t-{t}" data-g="{esc(n["g"])}"><title>{esc(tip)}</title>']
    P = lambda *pts: " ".join(f"{f1(a)},{f1(b)}" for a, b in pts)  # noqa: E731
    if t in ("in", "out"):
        if t == "in":
            o.append(f'<path class="shape" d="M{P((x, y))} H{f1(x + w - 9)} L{P((x + w, y + h / 2))} '
                     f'L{P((x + w - 9, y + h))} H{f1(x)} Z"/>')
        else:
            o.append(f'<path class="shape" d="M{P((x, y))} H{f1(x + w - 9)} L{P((x + w, y + h / 2))} '
                     f'L{P((x + w - 9, y + h))} H{f1(x)} L{P((x + 7, y + h / 2))} Z"/>')
        o.append(text(x + (12 if t == "out" else 6), y + h / 2 + 4, n["text"], "pname"))
    elif t == "dff":
        bx, bw, T, bh = x + g["bx"], g["bw"], g["T"], g["bh"]
        o.append(f'<rect class="shape" x="{f1(bx)}" y="{f1(y + T)}" width="{bw}" height="{bh}"/>')
        o.append(text(x + w / 2, y + T - 4, n["name"], "rname", "middle"))
        for i, r in enumerate(n["roles"]):
            py = y + g["S"][i]["dy"]
            if r == "CLK":
                o.append(f'<path class="clkpin" d="M{P((bx, py - 5), (bx + 8, py), (bx, py + 5))}"/>')
            else:
                o.append(text(bx + 4, py + 3.5, r, "pin"))
                if r == "RST" and n.get("rst_low"):
                    o.append(f'<circle class="bub" cx="{f1(bx - 2.5)}" cy="{f1(py)}" r="2.5"/>')
        o.append(text(bx + bw - 4, y + g["O"][0] + 3.5, "Q", "pin", "end"))
        if g["bx"] + bw < w:
            o.append(f'<path class="stub" d="M{P((bx + bw, y + g["O"][0]))} H{f1(x + w)}"/>')
        if n["cap"]:
            o.append(text(x + w / 2, y + T + bh + 12, n["cap"], "cap", "middle"))
    elif t == "mux":
        T, H, s = g["T"], g["H"], g["s"]
        o.append(f'<path class="shape" d="M{P((x, y + T), (x + w, y + T + s), (x + w, y + T + H - s), (x, y + T + H))} Z"/>')
        for i, key in enumerate(n["keys"]):
            o.append(text(x + 4, y + g["S"][i]["dy"] + 3.5, key if len(key) <= 12 else key[:11] + "…", "pin"))
    elif t == "cmp":
        o.append(f'<rect class="shape" x="{f1(x)}" y="{f1(y)}" width="{w}" height="{h}" rx="3"/>')
        o.append(text(x + w / 2, y + h / 2 + 5, n["sym"], "opsym", "middle"))
        if n["op"] not in COMMUTATIVE:
            o.append(text(x + 3, y + 13, "A", "pinsm"))
            o.append(text(x + 3, y + 33, "B", "pinsm"))
    elif t == "arith":
        o.append(f'<circle class="shape" cx="{f1(x + w / 2)}" cy="{f1(y + h / 2)}" r="{f1(w / 2)}"/>')
        o.append(text(x + w / 2, y + h / 2 + 5, n["sym"], "opsym", "middle"))
    elif t == "gate":
        o.append(gate_svg(n, g, x, y))
    elif t == "concat":
        T = g["T"]
        o.append(f'<rect class="shape bar" x="{f1(x)}" y="{f1(y + T)}" width="{w}" height="{f1(h - T)}"/>')
        o.append(text(x + w / 2, y + T - 3, n["label"], "pinsm", "middle"))
    elif t == "mem":
        T, bh = g["T"], g["bh"]
        o.append(f'<rect class="shape back" x="{f1(x + 4)}" y="{f1(y + T - 4)}" width="{f1(w)}" height="{bh}"/>')
        o.append(f'<rect class="shape" x="{f1(x)}" y="{f1(y + T)}" width="{f1(w)}" height="{bh}"/>')
        o.append(text(x + w / 2, y + T - 6, n["name"], "rname", "middle"))
        for i, r in enumerate(n["roles"]):
            py = y + g["S"][i]["dy"]
            if r == "CLK":
                o.append(f'<path class="clkpin" d="M{P((x, py - 5), (x + 8, py), (x, py + 5))}"/>')
            else:
                o.append(text(x + 4, py + 3.5, r, "pin"))
        for j, dy in enumerate(g["O"]):
            o.append(text(x + w - 4, y + dy + 3.5, f"RD{j}" if len(g["O"]) > 1 else "RD", "pin", "end"))
        o.append(text(x + w / 2, y + T + bh + 12, n["cap"], "cap", "middle"))
    return "".join(o) + "</g>"


def gate_svg(n, g, x, y):
    h = g["h"]
    if n["op"] == "not":
        w = g["w"]
        return (f'<path class="shape" d="M{f1(x)},{f1(y)} L{f1(x + w - 6)},{f1(y + h / 2)} L{f1(x)},{f1(y + h)} Z"/>'
                f'<circle class="shape bub" cx="{f1(x + w - 3)}" cy="{f1(y + h / 2)}" r="3"/>')
    base, bw = g["base"], g["bw"]
    o = []
    if base == "and":
        r = h / 2
        o.append(f'<path class="shape" d="M{f1(x)},{f1(y)} H{f1(x + bw - r)} A{f1(r)},{f1(r)} 0 0 1 '
                 f'{f1(x + bw - r)},{f1(y + h)} H{f1(x)} Z"/>')
    else:
        x0 = x + (5 if base == "xor" else 0)
        bw0 = bw - (5 if base == "xor" else 0)
        o.append(f'<path class="shape" d="M{f1(x0)},{f1(y)} Q{f1(x0 + bw0 * 0.62)},{f1(y)} {f1(x0 + bw0)},'
                 f'{f1(y + h / 2)} Q{f1(x0 + bw0 * 0.62)},{f1(y + h)} {f1(x0)},{f1(y + h)} Q{f1(x0 + 8)},'
                 f'{f1(y + h / 2)} {f1(x0)},{f1(y)} Z"/>')
        if base == "xor":
            o.append(f'<path class="arc" d="M{f1(x)},{f1(y + h)} Q{f1(x + 8)},{f1(y + h / 2)} {f1(x)},{f1(y)}"/>')
    if g["bub"]:
        o.append(f'<circle class="shape bub" cx="{f1(x + bw + 3)}" cy="{f1(y + h / 2)}" r="3"/>')
    if n.get("red"):
        o.append(text(x + bw * 0.42, y + h / 2 + 4, n["red"], "pinsm", "middle"))
    return "".join(o)


# ---------------------------------------------------------------- HTML

CSS = """
:root{--bg:#f3f4f6;--paper:#fff;--fg:#1b1f24;--muted:#57606a;--line:#d0d7de;--mod:#fbfbfc;--modl:#8c959f;
--wire:#1d3f73;--ctrl:#a14a00;--clk:#6f42c1;--hi:#d1242f;--fill:#fff;--stroke:#24292f;--reg:#fff4e6;
--regl:#9a3412;--mux:#eef7ee;--muxl:#1f6f2b;--cmp:#eef4ff;--cmpl:#1f4fa0;--op:#f5f0ff;--opl:#5a32a3;
--cst:#f6f8fa;--port:#eef0f8;--portl:#3b4a8c}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0d1117;--paper:#161b22;--fg:#e6edf3;
--muted:#9da7b3;--line:#30363d;--mod:#11161d;--modl:#57606a;--wire:#79b8ff;--ctrl:#f0a35e;--clk:#c3a6ff;
--hi:#ff7b72;--fill:#0d1117;--stroke:#c9d1d9;--reg:#2b1d10;--regl:#f0a35e;--mux:#10261a;--muxl:#56d364;
--cmp:#0f2140;--cmpl:#79c0ff;--op:#21183a;--opl:#bc8cff;--cst:#161b22;--port:#1a2040;--portl:#8c9eff}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
header{padding:12px 16px 8px;border-bottom:1px solid var(--line);background:var(--paper)}
h1{margin:0;font-size:18px;font-family:Consolas,"DejaVu Sans Mono",monospace}
.meta{color:var(--muted);font-size:12.5px;margin-top:3px}
.bar{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;padding:8px 16px;font-size:12.5px;color:var(--muted)}
.bar button{font:inherit;padding:2px 9px;border:1px solid var(--line);background:var(--paper);color:var(--fg);
border-radius:4px;cursor:pointer}
.lg{display:inline-flex;align-items:center;gap:5px}
.chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 8px;font-size:12px}
.chip{border:1px solid var(--line);border-radius:10px;padding:1px 8px;background:var(--paper);cursor:default;
font-family:Consolas,monospace}
.chip.on{border-color:var(--hi);color:var(--hi)}
#view{margin:0 16px 12px;background:var(--paper);border:1px solid var(--line);border-radius:6px;height:76vh;
overflow:hidden;cursor:grab;touch-action:none}
#view.drag{cursor:grabbing}
#sch{display:block;width:100%;height:100%;font-family:Consolas,"DejaVu Sans Mono","Courier New",monospace}
.mod{fill:var(--mod);stroke:var(--modl);stroke-width:1;stroke-dasharray:6 4}
.modname{font-size:13px;font-weight:700;fill:var(--muted)}
.net .w{fill:none;stroke:var(--wire);stroke-width:1.2}
.net.bus .w{stroke-width:2.6}
.net.ctrl .w{stroke:var(--ctrl);stroke-dasharray:5 3}
.net.clkn .w{stroke:var(--clk);stroke-dasharray:9 3 2 3}
.net .hit{fill:none;stroke:transparent;stroke-width:8}
.net .dot{fill:var(--wire)}.net.ctrl .dot{fill:var(--ctrl)}.net.clkn .dot{fill:var(--clk)}
.net:hover .w,.net.on .w{stroke:var(--hi);stroke-width:2.6}.net:hover .dot,.net.on .dot{fill:var(--hi)}
.arrow{fill:var(--muted)}
.lbl{font-size:9.5px;fill:var(--wire);paint-order:stroke;stroke:var(--paper);stroke-width:3px}
.lbl.ctrl{fill:var(--ctrl)}.lbl.clkl{fill:var(--clk)}
.node .shape{fill:var(--fill);stroke:var(--stroke);stroke-width:1.4}
.node.dim{opacity:.22}
.t-dff .shape{fill:var(--reg);stroke:var(--regl);stroke-width:2.2}
.t-mem .shape{fill:var(--reg);stroke:var(--regl);stroke-width:2}
.t-mux .shape{fill:var(--mux);stroke:var(--muxl);stroke-width:1.8}
.t-cmp .shape{fill:var(--cmp);stroke:var(--cmpl);stroke-width:1.6}
.t-arith .shape{fill:var(--op);stroke:var(--opl);stroke-width:1.6}
.t-const .shape{fill:var(--cst);stroke:var(--muted);stroke-width:1}
.t-in .shape,.t-out .shape{fill:var(--port);stroke:var(--portl)}
.shape.bar{fill:var(--stroke)}
.bub{fill:var(--fill);stroke:var(--stroke);stroke-width:1.3}
.arc{fill:none;stroke:var(--stroke);stroke-width:1.4}
.stub{fill:none;stroke:var(--wire);stroke-width:1.2}
.clkpin{fill:none;stroke:var(--regl);stroke-width:1.3}
.pname{font-size:11px;fill:var(--fg)}
.rname{font-size:11px;font-weight:700;fill:var(--fg)}
.cap{font-size:9.5px;fill:var(--muted)}
.pin{font-size:9.5px;fill:var(--muted)}.pinsm{font-size:8.5px;fill:var(--muted)}
.opsym{font-size:15px;font-weight:700;fill:var(--fg)}
.cst{font-size:9.5px;fill:var(--fg)}
.info{margin:0 16px 20px;font-size:13px}
.info table{border-collapse:collapse;margin:6px 0 12px;font-size:12.5px}
.info td,.info th{border:1px solid var(--line);padding:3px 8px;text-align:left;vertical-align:top}
.info code,.info pre{font-family:Consolas,monospace}
.info pre{background:var(--paper);border:1px solid var(--line);border-radius:4px;padding:8px;overflow:auto}
@media print{.bar,.chips{display:none}#view{height:auto;border:0;overflow:visible}#sch{height:auto}}
"""

JS = """
(function(){var s=document.getElementById('sch'),v=document.getElementById('view'),
W=+s.dataset.w,H=+s.dataset.h,vb=[0,0,W,H];
function ap(){s.setAttribute('viewBox',vb.join(' '));document.getElementById('zv').textContent=
Math.round(v.clientWidth/vb[2]*100)+'%';}
function fit(){var r=v.getBoundingClientRect(),k=Math.max(W/r.width,H/r.height),w=r.width*k,h=r.height*k;
vb=[(W-w)/2,(H-h)/2,w,h];ap();}
function one(){var r=v.getBoundingClientRect();vb=[0,0,r.width,r.height];ap();}
function zoom(f,px,py){var r=v.getBoundingClientRect(),cx=vb[0]+(px-r.left)/r.width*vb[2],
cy=vb[1]+(py-r.top)/r.height*vb[3];vb=[cx-(cx-vb[0])*f,cy-(cy-vb[1])*f,vb[2]*f,vb[3]*f];ap();}
function mid(f){var r=v.getBoundingClientRect();zoom(f,r.left+r.width/2,r.top+r.height/2);}
document.getElementById('zi').onclick=function(){mid(0.8)};
document.getElementById('zo').onclick=function(){mid(1.25)};
document.getElementById('z1').onclick=one;document.getElementById('zf').onclick=fit;
v.addEventListener('wheel',function(e){e.preventDefault();zoom(e.deltaY>0?1.15:1/1.15,e.clientX,e.clientY)},
{passive:false});
var d=null;v.addEventListener('pointerdown',function(e){d=[e.clientX,e.clientY,vb[0],vb[1]];
v.classList.add('drag');});
window.addEventListener('pointermove',function(e){if(!d)return;var r=v.getBoundingClientRect();
vb[0]=d[2]-(e.clientX-d[0])*vb[2]/r.width;vb[1]=d[3]-(e.clientY-d[1])*vb[3]/r.height;ap();});
window.addEventListener('pointerup',function(){d=null;v.classList.remove('drag');});
function hl(g){[].forEach.call(s.querySelectorAll('.node'),function(n){
n.classList.toggle('dim',!!g&&n.getAttribute('data-g')!==g)});
[].forEach.call(document.querySelectorAll('.chip'),function(c){c.classList.toggle('on',c.dataset.g===g)});}
s.addEventListener('mouseover',function(e){var n=e.target.closest('.node');hl(n?n.getAttribute('data-g'):null)});
s.addEventListener('mouseleave',function(){hl(null)});
[].forEach.call(document.querySelectorAll('.chip'),function(c){c.onmouseenter=function(){hl(c.dataset.g)};
c.onmouseleave=function(){hl(null)}});
s.addEventListener('click',function(e){var g=e.target.closest('.net');
[].forEach.call(s.querySelectorAll('.net.on'),function(n){if(n!==g)n.classList.remove('on')});
if(g)g.classList.toggle('on')});
window.addEventListener('resize',fit);fit();})();
"""

LEGEND = (
    '<span class="lg"><svg width="26" height="10"><path d="M0,5H26" stroke="var(--wire)" stroke-width="1.2"/></svg>'
    '1-bit data</span>'
    '<span class="lg"><svg width="26" height="10"><path d="M0,5H26" stroke="var(--wire)" stroke-width="2.6"/></svg>'
    'bus</span>'
    '<span class="lg"><svg width="26" height="10"><path d="M0,5H26" stroke="var(--ctrl)" stroke-width="1.2" '
    'stroke-dasharray="5 3"/></svg>control</span>'
    '<span class="lg"><svg width="26" height="10"><path d="M0,5H26" stroke="var(--clk)" stroke-width="1.2" '
    'stroke-dasharray="9 3 2 3"/></svg>clock/reset</span>'
    '<span class="lg"><svg width="12" height="10"><circle cx="6" cy="5" r="3" fill="var(--wire)"/></svg>'
    'junction</span>')


def html_of(model, nl, detail, origin):
    lay = layout(nl)
    W, H, svg = svg_of(model, nl, lay)
    m = model["module"]
    blob = json.dumps(dict(model, detail=detail), ensure_ascii=False, indent=1).replace("</", "<\\/")
    cnt = Counter(n["t"] for n in nl.nodes.values())
    names = {"dff": "DFF", "mux": "MUX", "cmp": "CMP", "gate": "gate", "arith": "arith", "const": "const",
             "concat": "concat", "mem": "MEM"}
    summary = " · ".join(f"{cnt[k]} {v}" for k, v in names.items() if cnt[k])
    per = defaultdict(Counter)
    for n in nl.nodes.values():
        if n["t"] not in ("in", "out"):
            per[n["g"]][names.get(n["t"], n["t"])] += 1
    inner = [n for n in model["nodes"] if n["kind"] not in ("in", "out", "note")]
    chips = "".join(f'<span class="chip" data-g="{esc(n["id"])}" title="{esc(" / ".join(lines_of(n["label"])))}">'
                    f'{esc(n["id"])}</span>' for n in inner)
    rows = "".join(f"<tr><td><code>{esc(n['id'])}</code></td><td>{esc(' / '.join(lines_of(n['label'])))}</td>"
                   f"<td>{esc(', '.join(f'{c} {k}' for k, c in per[n['id']].items()) or '–')}</td></tr>"
                   for n in inner)
    notes = "".join(f"<li>{esc(' / '.join(lines_of(n['label'])))}</li>" for n in model["nodes"]
                    if n["kind"] == "note")
    src = f" · source: {esc(model['source'])}" if model["source"] else ""
    par = f" · param: {esc(model['param'])}" if model["param"] else ""
    return f"""<!DOCTYPE html>
<html lang="en" data-module="{esc(m)}" data-stage="2" data-level="{esc(model['level'])}" data-format="html">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="rtl-s2-diagram/scripts/render_html.py">
<title>{esc(m)} RTL schematic</title>
<style>{CSS}</style>
</head>
<body>
<header>
<h1>{esc(m)}</h1>
<div class="meta">S2 · {esc(model['level'])} · RTL schematic (HTML) · {summary}<br>model: {esc(origin)}{src}{par}
· viewing aid – the official diagram for S3 is <code>{esc(m)}.mmd</code></div>
</header>
<div class="bar"><button id="zo" title="Zoom out">−</button><span id="zv">100%</span>
<button id="zi" title="Zoom in">+</button><button id="z1">1:1</button><button id="zf">Fit</button>
{LEGEND}<span>· wheel: zoom · drag: pan · hover element: highlight model block · click wire: highlight net</span></div>
<div class="chips">Model blocks: {chips}</div>
<div id="view">{svg}</div>
<div class="info">
<details><summary>Model blocks ↔ schematic elements ({len(inner)} blocks, {len(model['edges'])} edges)</summary>
<table><tr><th>Block (.mmd)</th><th>Label</th><th>Schematic elements</th></tr>{rows}</table>
{f"<ul>{notes}</ul>" if notes else ""}
</details>
<details><summary>RTL detail layer</summary><pre>{esc(detail.strip())}</pre></details>
</div>
<script type="application/json" id="arch-model">{blob}</script>
<script>{JS}</script>
</body>
</html>
"""


# ---------------------------------------------------------------- CLI

def split_stdin(text):
    m = SCH_MARK.search(text)
    return (text[:m.start()], text[m.end():]) if m else (text, "")


def check_html(path: Path, mmd, iface):
    errs = []
    if not path.is_file():
        return [f"không có file {path}"]
    s = path.read_text(encoding="utf-8")
    tag = re.search(r"<html\b([^>]*)>", s)
    attrs = dict(re.findall(r'data-(\w+)="([^"]*)"', tag.group(1))) if tag else {}
    for k, want in (("stage", "2"), ("level", "L2"), ("format", "html")):
        if attrs.get(k) != want:
            errs.append(f"metadata data-{k} = {attrs.get(k)!r}, cần {want!r}")
    if not attrs.get("module"):
        errs.append("thiếu metadata data-module")
    elif path.stem != attrs["module"]:
        errs.append(f"tên file {path.name} không khớp data-module={attrs['module']}")
    if "<svg" not in s:
        errs.append("không có SVG schematic")
    if re.search(r'(?:src|href)\s*=\s*"(?:https?:)?//|@import|<link\b', s):
        errs.append("có tài nguyên ngoài (src/href http, @import, <link>) – file phải tự chứa")
    m = re.search(r'<script type="application/json" id="arch-model">(.*?)</script>', s, re.S)
    try:
        model = json.loads(m.group(1).replace("<\\/", "</")) if m else None
    except ValueError:
        model = None
    if model is None:
        return errs + ["thiếu/hỏng mô hình kiến trúc nhúng (#arch-model)"]
    if not model.get("detail"):
        errs.append("HTML không có lớp chi tiết RTL – render lại bằng render_html.py bản mới")
    else:
        _, e2, _ = build_netlist(model, model["detail"], iface)
        errs += [f"lớp chi tiết: {e}" for e in e2]
    if mmd:
        other = parse_model(Path(mmd).read_text(encoding="utf-8"))
        if not same_architecture(model, other):
            errs.append(f"mô hình trong HTML khác {mmd} – render lại từ .mmd")
    return errs


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("model", nargs="?", help="<m>.mmd hoặc - (stdin: mô hình, dòng '%%%% schematic', lớp chi tiết)")
    ap.add_argument("--detail", help="lớp chi tiết RTL: - (stdin) hoặc file – bắt buộc khi mô hình là file .mmd")
    ap.add_argument("--out")
    ap.add_argument("--interface")
    ap.add_argument("--check", metavar="HTML")
    ap.add_argument("--mmd")
    a = ap.parse_args()
    iface = iface_table(Path(a.interface)) if a.interface else None

    if a.check:
        errs = check_html(Path(a.check), a.mmd, iface)
        print(f"== {a.check}")
        for e in errs:
            print("[LỖI]      " + e)
        if not errs:
            print("[OK]       lớp chi tiết khớp mô hình khối")
            if a.mmd:
                print(f"[OK]       cùng mô hình kiến trúc với {a.mmd}")
        print("KẾT QUẢ:", "OK" if not errs else f"{len(errs)} lỗi")
        sys.exit(1 if errs else 0)
    if not a.model:
        ap.error("cần file mô hình (.mmd) hoặc - (stdin), hoặc --check <html>")
    if a.model == "-" and a.detail == "-":
        ap.error("mô hình đã đọc từ stdin – đặt lớp chi tiết sau dòng '%% schematic' trong cùng stdin")

    stdin = sys.stdin.buffer.read().decode("utf-8") if "-" in (a.model, a.detail) else ""
    if a.model == "-":
        text, detail = split_stdin(stdin)
    else:
        text = Path(a.model).read_text(encoding="utf-8")
        detail = stdin if a.detail == "-" else Path(a.detail).read_text(encoding="utf-8") if a.detail else ""
        detail = split_stdin(detail)[1] if SCH_MARK.search(detail) else detail
    origin = "stdin (no .mmd yet)" if a.model == "-" else Path(a.model).as_posix()
    model = parse_model(text)
    m = model["module"]
    errs, warns = lint(text.splitlines(), iface_ports(Path(a.interface)) if a.interface else None)
    if not m:
        errs.append("thiếu header '%% module : <m>'")
    if model["level"] != "L2":
        errs.append(f"HTML schematic chỉ dùng cho L2 (mô hình ghi level {model['level'] or 'không rõ'}) "
                    "– dùng --format mermaid")
    inst = [n["id"] for n in model["nodes"] if n["kind"] == "inst"]
    if inst:
        errs.append(f"mô hình có instance module con ({', '.join(inst)}) – HTML chỉ dùng cho module leaf")
    out = Path(a.out) if a.out else (Path("doc/diagram") / m / f"{m}.html" if a.model == "-"
                                     else Path(a.model).with_name(f"{m}.html"))
    if m and out.name != f"{m}.html":
        errs.append(f"file ra phải tên {m}.html (đang là {out.name})")
    if out.suffix != ".html":
        errs.append("file ra phải là .html (không ghi đè .mmd)")
    nl = None
    if not detail.strip():
        errs.append("thiếu lớp chi tiết RTL – .mmd: --detail - kèm heredoc; stdin: sau dòng '%% schematic' "
                    "(mục 8 của diagram_conventions.md)")
    elif not errs:
        nl, e2, w2 = build_netlist(model, detail, iface)
        errs += e2
        warns += w2
    print(f"== render HTML – {m or '?'} ({origin})")
    for w in warns:
        print("[CẢNH BÁO] " + w)
    for e in errs:
        print("[LỖI]      " + e)
    if errs:
        print(f"KẾT QUẢ: {len(errs)} lỗi – không ghi HTML")
        sys.exit(1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_of(model, nl, detail, origin), encoding="utf-8", newline="\n")
    cnt = Counter(n["t"] for n in nl.nodes.values())
    print(f"[OK]       {out.as_posix()} – " + ", ".join(f"{k}:{v}" for k, v in sorted(cnt.items())))
    print("KẾT QUẢ: OK")


if __name__ == "__main__":
    main()

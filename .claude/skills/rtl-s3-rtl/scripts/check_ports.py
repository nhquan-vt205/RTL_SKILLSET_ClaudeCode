#!/usr/bin/env python3
"""
So sánh port list của file RTL Verilog-2005 (khai báo kiểu ANSI) với bảng port (cột "Port name", bản cũ "Tên port") trong spec.

Dùng: python3 check_ports.py rtl/<m>.v <file bảng port>
  <file bảng port>: doc/spec/<m>_spec.md, architecture/<m>_spec.md hoặc interface/<m>_interface.md
  (gate stage 3 in đường dẫn này ở dòng "[OK] bảng port:").
Width trong bảng: số (8) hoặc "PARAM (8)".
Kiểm: thiếu/thừa port, sai hướng, sai width (tính width bằng parameter mặc định của module
nếu biểu thức đơn giản), sai thứ tự (cảnh báo).
Mã thoát 0 = khớp, 1 = có lỗi.
"""
import math
import re
import sys
from pathlib import Path


def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def params_of(src):
    p = {}
    for m in re.finditer(r"\b(?:parameter|localparam)\b[^;=]*?\b([A-Za-z_]\w*)\s*=", src):
        i, depth, val = m.end(), 0, ""
        while i < len(src):
            c = src[i]
            if c == "(":
                depth += 1
            elif c == ")":
                if depth == 0:
                    break
                depth -= 1
            elif c in ",;\n" and depth == 0:
                break
            val += c
            i += 1
        p[m.group(1)] = val.strip()
    return p


def ev(expr, params, depth=0):
    if depth > 10:
        return None
    e = expr.strip()
    e = re.sub(r"\$clog2\s*\(", "_clog2(", e)
    for _ in range(10):
        prev = e
        for k in sorted(params, key=len, reverse=True):
            e = re.sub(rf"\b{k}\b", f"({params[k]})", e)
        if e == prev:
            break
    e = re.sub(r"\$clog2\s*\(", "_clog2(", e)
    if re.search(r"[A-Za-z_]\w*", re.sub(r"_clog2", "", e)):
        return None
    try:
        return int(eval(e, {"__builtins__": {}}, {"_clog2": lambda x: max(0, math.ceil(math.log2(x)))}))
    except Exception:
        return None


def rtl_ports(path):
    src = strip_comments(Path(path).read_text(encoding="utf-8"))
    m = re.search(r"\bmodule\s+(\w+)\s*(#\s*\((.*?)\)\s*)?\((.*?)\)\s*;", src, re.S)
    if not m:
        sys.exit("Không tìm thấy khai báo module kiểu ANSI")
    params = params_of(src)
    ports = []
    cur_dir, cur_rng = None, None
    for raw in m.group(4).split(","):
        t = raw.strip()
        if not t:
            continue
        d = re.match(r"(input|output|inout)\b", t)
        if d:
            cur_dir = {"input": "in", "output": "out", "inout": "inout"}[d.group(1)]
            rng = re.search(r"\[([^:\]]+):([^\]]+)\]", t)
            cur_rng = (rng.group(1), rng.group(2)) if rng else None
        name = re.findall(r"([A-Za-z_]\w*)\s*$", t)
        if not name:
            continue
        w = 1
        if cur_rng:
            hi, lo = ev(cur_rng[0], params), ev(cur_rng[1], params)
            w = (abs(hi - lo) + 1) if hi is not None and lo is not None else None
        ports.append((name[0], cur_dir, w))
    return m.group(1), ports


def iface(path):
    out, header = [], None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
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

        def col(*names):
            for i, h in enumerate(header):
                if h.startswith(names) and i < len(cells):
                    return cells[i]
            return ""
        w = col("giá trị số") or col("bit width") or col("width")
        m = re.search(r"\(\s*(\d+)\s*\)", w)
        if col("port name", "tên port"):
            out.append((col("port name", "tên port"), col("direction", "hướng").lower(),
                        int(w) if w.isdigit() else int(m.group(1)) if m else None))
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    mod, r = rtl_ports(sys.argv[1])
    s = iface(sys.argv[2])
    if not s:
        sys.exit(f"{sys.argv[2]}: không có bảng port (cột 'Port name')")
    rd = {p[0]: p for p in r}
    sd = {p[0]: p for p in s}
    errs, warns = [], []
    for n in sd:
        if n not in rd:
            errs.append(f"thiếu port '{n}' trong RTL")
    for n in rd:
        if n not in sd:
            errs.append(f"RTL có port '{n}' không có trong bảng port")
    for n in sd.keys() & rd.keys():
        _, sdir, sw = sd[n]
        _, rdir, rw = rd[n]
        if sdir != rdir:
            errs.append(f"{n}: hướng RTL={rdir}, bảng port={sdir}")
        if sw is not None and rw is not None and sw != rw:
            errs.append(f"{n}: width RTL={rw}, bảng port={sw}")
        if rw is None or sw is None:
            warns.append(f"{n}: không tính được width bằng số (RTL hoặc bảng port), kiểm bằng mắt")
    common = [p[0] for p in s if p[0] in rd]
    if common != [p[0] for p in r if p[0] in sd]:
        warns.append("thứ tự port khác với bảng port")
    print(f"== module {mod}: RTL {len(r)} port, bảng port {len(s)} port")
    for e in errs:
        print("[LỖI]      " + e)
    for w in warns:
        print("[CẢNH BÁO] " + w)
    print("KẾT QUẢ:", "KHỚP" if not errs else f"{len(errs)} lỗi")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()

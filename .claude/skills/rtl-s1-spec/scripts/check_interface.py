#!/usr/bin/env python3
"""
Kiểm tra bảng port của mọi module trong doc/spec/ (chế độ đơn và phân cấp).

Bảng port = bảng markdown có cột "Port name" (bản cũ: "Tên port"), nằm trong interface/<m>_interface.md nếu có,
không thì trong spec (doc/spec/<m>_spec.md hoặc architecture/<m>_spec.md).
  Bắt buộc : Port name | Direction | Width (số, hoặc "PARAM (8)")
  Tùy chọn : Type (CTRL/DATA/STATUS/CLK/RST) | Connects to (module.port, nhiều đích cách dấu phẩy, `external`)
  Tài liệu cũ dùng tiêu đề tiếng Việt (Tên port | Hướng | Loại | Nối tới, `ngoài`) vẫn được nhận.

Chế độ đơn (không có spec_status.md): mỗi module tự đứng, port nối ra ngoài → chỉ kiểm hướng,
width, tên trùng, hậu tố. Chế độ phân cấp: quan hệ cha–con lấy từ cột Parent của "Module list":
  - anh em (cùng cha):  out → in   (hướng ngược nhau)
  - cha ↔ con:          in(cha) → in(con), out(con) → out(cha)   (cùng hướng)
  và kiểm thêm: port treo của module con · tham chiếu không tồn tại · lệch width · input nhiều nguồn.
Thiếu spec_status.md nhưng spec cho thấy phân cấp (architecture/ có ≥ 2 spec, "Type: top|block",
"Parent: <m>") → [LỖI]: không đoán hierarchy, cần tạo spec_status.md.

Dùng: python3 check_interface.py [--root <project root>]   · Mã thoát 0 = không lỗi, 1 = có lỗi.
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

VALID_TYPES = {"CTRL", "DATA", "STATUS", "CLK/RST", "CLK", "RST"}
EXTERNAL = {"top", "ngoài", "ngoai", "external", "chân ip", "pin"}
NAME = re.compile(r"^[A-Za-z_]\w*$")
# Khóa máy đọc: tiếng Anh (chuẩn hiện tại) + tiếng Việt (tài liệu cũ)
PORT_COL = ("port name", "tên port")


def clean(s):
    return re.sub(r"[`*]", "", s).strip()


def num_width(s):
    """'8' → 8 · 'DATA_W (8)' → 8 · còn lại → None."""
    s = s.strip()
    if s.isdigit():
        return int(s)
    m = re.search(r"\(\s*(\d+)\s*\)", s)
    return int(m.group(1)) if m else None


def parse_ports(f: Path):
    ports, header = {}, None
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = [clean(c) for c in line.strip().strip("|").split("|")]
        if header is None:
            if any(c.lower().startswith(PORT_COL) for c in cells):
                header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue

        def col(*names):
            for n in names:
                for i, h in enumerate(header):
                    if h.startswith(n) and i < len(cells):
                        return cells[i]
            return None
        name = col(*PORT_COL)
        if name:
            w = col("giá trị số") or col("bit width", "width") or ""
            ports.setdefault(name, []).append({
                "dir": (col("direction", "hướng") or "").lower(), "width": num_width(w), "width_txt": w,
                "type": (col("type", "loại") or "").upper(), "has_type": col("type", "loại") is not None,
                "to": col("connects to", "nối tới"), "has_to": col("connects to", "nối tới") is not None})
    return ports


def spec_root(root):
    return root / "doc" / "spec"


def hier_signals(spec: Path):
    """Dấu hiệu phân cấp trong spec hiện có – dùng khi chưa có spec_status.md."""
    arch = sorted((spec / "architecture").glob("*_spec.md")) if (spec / "architecture").is_dir() else []
    why = [f"architecture/ có {len(arch)} spec"] if len(arch) >= 2 else []
    for f in sorted(spec.glob("*_spec.md")) + arch:
        head = "\n".join(f.read_text(encoding="utf-8").splitlines()[:15])
        kind = re.search(r"\b(?:Type|Loại)\s*:\s*\**\s*(top|block)\b", head, re.I)
        parent = re.search(r"\b(?:Parent|Cha)\s*:\s*\**\s*`?([A-Za-z_]\w*)", head, re.I)
        if kind or parent:
            why.append(f.name)
    return why


def module_sources(root: Path):
    """{module: file chứa bảng port}, parents {con: cha}, hierarchical?"""
    spec = spec_root(root)
    status = spec / "spec_status.md"
    par, names = {}, []
    if status.is_file():
        header, sec = None, False
        for line in status.read_text(encoding="utf-8").splitlines():
            if re.match(r"#+\s*(?:Module list|Danh sách module)", line, re.I):
                sec = True
                continue
            if not sec:
                continue
            if line.startswith("#"):
                break
            if not line.strip().startswith("|"):
                continue
            c = [clean(x) for x in line.strip().strip("|").split("|")]
            if header is None:
                header = [h.lower() for h in c]
                continue
            if not NAME.match(c[0]) or c[0].lower() == "module":
                continue
            names.append(c[0])
            idx = next((i for i, h in enumerate(header) if h.startswith(("cha", "parent"))), None)
            if idx is not None and idx < len(c) and NAME.match(c[idx]):
                par[c[0]] = c[idx]
    else:
        for d in (spec, spec / "architecture"):
            if d.is_dir():
                names += [p.name[: -len("_spec.md")] for p in sorted(d.glob("*_spec.md"))]
    if (spec / "interface").is_dir():
        names += [p.name[: -len("_interface.md")] for p in sorted((spec / "interface").glob("*_interface.md"))]
    names = list(dict.fromkeys(names))

    src = {}
    for m in names:
        cands = [spec / "interface" / f"{m}_interface.md", spec / f"{m}_spec.md",
                 spec / "architecture" / f"{m}_spec.md"]
        src[m] = next((c for c in cands if c.is_file() and parse_ports(c)), None)
    return src, par, status.is_file()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    root = Path(ap.parse_args().root).resolve()
    src, par, hier = module_sources(root)
    if not src:
        print("Không tìm thấy module nào (doc/spec/<m>_spec.md, architecture/<m>_spec.md, "
              "interface/<m>_interface.md hoặc spec_status.md)")
        sys.exit(1)

    errs, warns = [], []
    hint = [] if hier else hier_signals(spec_root(root))
    if hint:
        errs.append("Hierarchical design detected (" + ", ".join(hint) + ") nhưng thiếu doc/spec/spec_status.md "
                    "– tạo bảng 'Module list' (/rtl-s1-spec) để kiểm nối cha–con")
    mods = {}
    for m, f in src.items():
        if f is None:
            errs.append(f"{m}: không tìm thấy bảng port (cột 'Port name') trong spec hay interface")
            continue
        raw = parse_ports(f)
        mods[m] = {}
        for p, lst in raw.items():
            if len(lst) > 1:
                errs.append(f"{m}.{p}: khai báo {len(lst)} lần trong bảng port")
            mods[m][p] = lst[0]
    edges = set()  # (driver, load) dạng ((mod,port),(mod,port))

    def relation(a, b):
        if par.get(b) == a:
            return "parent"     # a là cha của b
        if par.get(a) == b:
            return "child"      # a là con của b
        return "sibling"

    for mod, ports in mods.items():
        for p, a in ports.items():
            if a["dir"] not in ("in", "out", "inout"):
                errs.append(f"{mod}.{p}: Direction '{a['dir']}' không hợp lệ (in/out/inout)")
            if a["width_txt"] and a["width"] is None:
                warns.append(f"{mod}.{p}: width '{a['width_txt']}' không có giá trị số – nên ghi dạng 'PARAM (8)'")
            if a["has_type"] and a["type"] and a["type"] not in VALID_TYPES:
                errs.append(f"{mod}.{p}: Type '{a['type']}' không hợp lệ")
            if a["dir"] == "in" and not re.search(r"_(i|ni|n_i)$", p) and not p.startswith("clk") and "*" not in p:
                warns.append(f"{mod}.{p}: input không có hậu tố _i")
            if a["dir"] == "out" and not re.search(r"_(o|no|n_o)$", p) and "*" not in p:
                warns.append(f"{mod}.{p}: output không có hậu tố _o")
            targets = [t.strip() for t in re.split(r"[,;]", a["to"] or "") if t.strip() not in ("", "–", "-")]
            if not targets:
                # module không có cha (đơn hoặc top) → port nối ra ngoài, không cần cột Nối tới
                if hier and mod in par:
                    errs.append(f"{mod}.{p}: cột 'Connects to' trống (port treo của module con)")
                continue
            for t in targets:
                if t.lower() in EXTERNAL or "." not in t:
                    continue
                tm, tp = t.split(".", 1)
                tm = re.sub(r"\[.*?\]$", "", tm)   # mac_lane[0].din_i → mac_lane
                if tm not in mods:
                    errs.append(f"{mod}.{p} → {t}: module '{tm}' không có bảng port")
                    continue
                if tp not in mods[tm]:
                    errs.append(f"{mod}.{p} → {t}: port '{tp}' không có trong {tm}")
                    continue
                b = mods[tm][tp]
                rel = relation(mod, tm)
                same = a["dir"] == b["dir"]
                if rel == "sibling" and same:
                    errs.append(f"{mod}.{p} ({a['dir']}) ↔ {t} ({b['dir']}): module ngang cấp phải ngược hướng")
                if rel != "sibling" and not same:
                    errs.append(f"{mod}.{p} ({a['dir']}) ↔ {t} ({b['dir']}): nối cha–con phải cùng hướng")
                if a["width"] is not None and b["width"] is not None and a["width"] != b["width"]:
                    errs.append(f"{mod}.{p} [{a['width']}] ↔ {t} [{b['width']}]: lệch width")
                x, y = (mod, p), (tm, tp)
                if rel == "sibling":
                    drv, load = (x, y) if a["dir"] == "out" else (y, x)
                elif rel == "parent":   # mod là cha
                    drv, load = (x, y) if a["dir"] == "in" else (y, x)
                else:                   # mod là con
                    drv, load = (y, x) if a["dir"] == "in" else (x, y)
                edges.add((drv, load))

    srcs = defaultdict(set)
    for drv, load in edges:
        srcs[load].add(drv)
    for load, s in srcs.items():
        if len(s) > 1:
            errs.append(f"{load[0]}.{load[1]}: có {len(s)} nguồn ({', '.join(m + '.' + q for m, q in sorted(s))})")

    for m in errs:
        print("[LỖI]      " + m)
    for m in warns:
        print("[CẢNH BÁO] " + m)
    print(f"Chế độ: {'phân cấp' if hier else 'phân cấp, thiếu spec_status.md' if hint else 'đơn'} · {len(mods)} module, "
          f"{sum(len(p) for p in mods.values())} port, {len(errs)} lỗi, {len(warns)} cảnh báo")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()

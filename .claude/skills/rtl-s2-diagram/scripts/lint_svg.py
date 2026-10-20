#!/usr/bin/env python3
"""
Lint file .svg của stage 2 (mọi level L0/L1/L2) theo references/diagram_conventions.md.

Dùng:
  python3 lint_svg.py <file.svg> [<file2.svg> ...] [--interface <file có bảng port>]

  --interface : file chứa bảng port (cột "Port name", bản cũ "Tên port") – doc/spec/<m>_spec.md hoặc
                interface/<m>_interface.md. Mọi port phải có nhãn trong diagram chính <m>.svg
                (clock được miễn; reset được miễn khi diagram không có reg_/mem_). Nhãn gom bus
                `s_apb_*` phủ mọi port bắt đầu bằng `s_apb_`.

Kiểm: XML hợp lệ · header (module, stage + level, source; scope cho file part) · chỉ đen/trắng ·
không <image>/<script>/<use>/marker/gradient · chữ chỉ tiếng Anh · id nhóm đúng tiền tố, không trùng ·
<desc id="model"> có mục phương trình cho mọi nhóm reg_/fsm_/mem_/cloud_/blk_/u_ và ngược lại ·
luật theo level · tên port không ghi bên trong khối u_/blk_/mem_ · đủ port.
Không kiểm bố cục (chồng chữ, dây lệch) – việc đó Claude tự rà khi viết SVG.
Mã thoát 0 = không lỗi, 1 = có lỗi.
"""
import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "{http://www.w3.org/2000/svg}"
PREFIXES = ("reg_", "fsm_", "mem_", "mux_", "gate_", "op_", "cloud_", "blk_", "u_", "bus_")
NEED_EQ = ("reg_", "fsm_", "mem_", "cloud_", "blk_", "u_")
SHAPE = {"reg_": "rect", "fsm_": "rect", "mem_": "rect", "blk_": "rect", "u_": "rect",
         "mux_": "path", "cloud_": "path", "bus_": "rect"}
INNER_TEXT_MAX = {"u_": 3, "blk_": 2, "mem_": 3}   # u_ mảng instance: thêm dòng "x N"
FORBIDDEN = {"image", "script", "foreignObject", "use", "symbol", "marker", "linearGradient",
             "radialGradient", "pattern", "filter", "mask", "a"}
COLORS = {"#000", "#000000", "black", "#fff", "#ffffff", "white", "none"}
HEADER = re.compile(r"<!--\s*(module|stage|source|param|scope)\s*:\s*(.*?)\s*-->", re.I)
SECTION = re.compile(r"^\s*\[([A-Za-z_]\w*)\]\s*$", re.M)
NON_EN = re.compile(r"[À-ɏḀ-ỿ]")
CLOCK = re.compile(r"(^|_)(clk|clock)(_|$)", re.I)
RESET = re.compile(r"(^|_)(rst|reset)(_|$)", re.I)
MANY = 60


def tag(e):
    return e.tag.replace(SVG_NS, "")


def translate(e):
    m = re.search(r"translate\(\s*([-\d.]+)[\s,]*([-\d.]*)\s*\)", e.get("transform", ""))
    return (float(m.group(1)), float(m.group(2) or 0)) if m else (0.0, 0.0)


def lint(path: Path, iface=None):
    errs, warns, info = [], [], {}
    raw = path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as ex:
        return [f"XML không hợp lệ: {ex}"], warns, info
    if tag(root) != "svg" or not root.tag.startswith(SVG_NS):
        return ["phần tử gốc phải là <svg xmlns=\"http://www.w3.org/2000/svg\">"], warns, info
    for a in ("width", "height", "viewBox", "font-family"):
        if not root.get(a):
            errs.append(f"<svg> thiếu thuộc tính {a}")

    # ---- header
    head = {k.lower(): v for k, v in HEADER.findall(raw)}
    for k in ("module", "stage", "source"):
        if k not in head:
            errs.append(f"thiếu header <!-- {k} : ... -->")
    lv = re.search(r"\b2\s*-\s*diagram\s+(L[012])\b", head.get("stage", ""), re.I)
    if "stage" in head and not lv:
        errs.append("header stage phải có dạng '2 - diagram L0|L1|L2'")
    level = lv.group(1).upper() if lv else ""
    mod = head.get("module", "")
    part = False
    if mod:
        if path.stem == mod:
            part = False
        elif path.stem.startswith(mod + "_"):
            part = True
            if "scope" not in head:
                errs.append(f"file part {path.name} thiếu header <!-- scope : from ... to ... -->")
        else:
            errs.append(f"tên file phải là {mod}.svg hoặc {mod}_<part>.svg (header module : {mod})")
    info.update(module=mod, level=level, part=part)

    # ---- elements: forbidden, colors, ids, text language
    ids, parent = {}, {c: p for p in root.iter() for c in p}
    for e in root.iter():
        t = tag(e)
        if t in FORBIDDEN:
            errs.append(f"không dùng <{t}> (chép hình trực tiếp, không ảnh/script/marker/gradient)")
        for a in ("marker-start", "marker-mid", "marker-end"):
            if e.get(a):
                errs.append(f"không dùng {a} (dây không có mũi tên)")
        vals = [e.get(a) for a in ("fill", "stroke", "color", "stop-color", "flood-color") if e.get(a)]
        css = (e.get("style") or "") + (e.text or "" if t == "style" else "")
        vals += re.findall(r"(?:fill|stroke|color)\s*:\s*([^;}\s]+)", css)
        for v in vals:
            if v.lower() not in COLORS and not v.lower().startswith("url("):
                errs.append(f"màu '{v}' – diagram chỉ đen/trắng (#000, #fff, none)")
            elif v.lower().startswith("url("):
                errs.append(f"không dùng tham chiếu màu {v}")
        i = e.get("id")
        if i:
            if i in ids:
                errs.append(f"id trùng: {i}")
            ids[i] = e
        if t in ("text", "tspan", "desc") and NON_EN.search("".join(e.itertext())):
            errs.append(f"chữ không phải tiếng Anh: {''.join(e.itertext()).strip()[:40]!r}")
    for c in re.findall(r"<!--(.*?)-->", raw, re.S):
        if NON_EN.search(c):
            errs.append(f"comment không phải tiếng Anh: {c.strip()[:40]!r}")

    groups = {i: e for i, e in ids.items() if tag(e) == "g" and i != "model"}
    for i in groups:
        if not i.startswith(PREFIXES) and not i.startswith("sym_"):
            warns.append(f"nhóm '{i}' không có tiền tố chuẩn ({', '.join(PREFIXES)})")

    # ---- model (equations)
    desc = ids.get("model")
    if desc is None or tag(desc) != "desc":
        errs.append('thiếu <desc id="model"> chứa phương trình từng khối')
        secs = set()
    else:
        secs = set(SECTION.findall("".join(desc.itertext())))
    for i in groups:
        if i.startswith(NEED_EQ) and i not in secs:
            errs.append(f"nhóm '{i}' chưa có mục [{i}] trong <desc id=\"model\">")
    for s in sorted(secs - set(groups)):
        errs.append(f"mục [{s}] trong model không có nhóm <g id=\"{s}\"> tương ứng")

    # ---- shape per prefix
    for i, e in groups.items():
        p = next((p for p in SHAPE if i.startswith(p)), None)
        if p and not any(tag(c) == SHAPE[p] for c in e.iter()):
            errs.append(f"nhóm '{i}' phải có <{SHAPE[p]}> (ký hiệu {p})")

    # ---- level rules
    has = lambda p: any(i.startswith(p) for i in groups)
    if level == "L2" and has("u_"):
        errs.append("L2 là leaf – không có khối instance u_")
    if level == "L2" and not part and (has("cloud_") or has("blk_")):
        warns.append("L2 vẽ tới từng gate – cloud_/blk_ chỉ giữ khi người dùng đã duyệt")
    if level == "L0" and not part and not has("u_"):
        errs.append("L0 phải vẽ mỗi module con thành một khối u_")
    prim = sum(1 for i in groups if i.startswith(("mux_", "gate_", "op_", "reg_", "fsm_")))
    if prim > MANY:
        warns.append(f"{prim} primitive – rất khó đọc; đề xuất người dùng gom cloud_/blk_ hoặc tách góc nhìn --from/--to")

    # ---- port names must sit on the wire outside u_/blk_/mem_ frames
    def offset(e):
        x = y = 0.0
        while e is not None:
            dx, dy = translate(e)
            x, y = x + dx, y + dy
            e = parent.get(e)
        return x, y

    for i, e in groups.items():
        p = next((p for p in INNER_TEXT_MAX if i.startswith(p)), None)
        rect = next((c for c in e.iter() if tag(c) == "rect"), None)
        if not p or rect is None:
            continue
        rx, ry = offset(parent.get(rect, e))
        x0, y0 = rx + float(rect.get("x", 0)), ry + float(rect.get("y", 0))
        x1, y1 = x0 + float(rect.get("width", 0)), y0 + float(rect.get("height", 0))
        inner = 0
        for t in root.iter(SVG_NS + "text"):
            ox, oy = offset(parent.get(t))
            tx, ty = ox + float(t.get("x", 0)), oy + float(t.get("y", 0))
            if x0 + 2 < tx < x1 - 2 and y0 + 2 < ty < y1 - 2:
                inner += 1
        if inner > INNER_TEXT_MAX[p]:
            errs.append(f"khối '{i}' có {inner} dòng chữ bên trong (tối đa {INNER_TEXT_MAX[p]} dòng nhãn) – "
                        "tên port ghi trên dây ngoài khung, sát cạnh")

    # ---- port coverage (main diagram only)
    if iface is not None and not part:
        names = set()
        for t in root.iter(SVG_NS + "text"):
            for tok in "".join(t.itertext()).split():
                names.add(re.sub(r"\[.*$", "", tok))
        bus = [n[:-1] for n in names if n.endswith("*")]   # nhãn gom bus `s_apb_*`
        regs = has("reg_") or has("fsm_") or has("mem_")
        miss = [p for p in iface if not CLOCK.search(p) and not (RESET.search(p) and not regs)
                and p not in names and not any(p.startswith(b) for b in bus)]
        for p in miss:
            errs.append(f"port '{p}' của bảng port không có nhãn trong diagram")
        info["cover"] = (len(iface) - len(miss), len(iface))
    return errs, warns, info


def iface_ports(md: Path):
    ports, header = [], None
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
        idx = next(i for i, h in enumerate(header) if h.startswith(("port name", "tên port")))
        if idx < len(cells) and cells[idx]:
            ports.append(cells[idx])
    return ports


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--interface")
    a = ap.parse_args()
    ports = iface_ports(Path(a.interface)) if a.interface else None
    if ports is not None and not ports:
        print(f"[LỖI]      {a.interface}: không có bảng port (cột 'Port name')")
        sys.exit(1)

    total = 0
    for f in map(Path, a.files):
        errs, warns, info = lint(f, ports)
        print(f"== {f}" + (f"  ({info['level']}{', part' if info.get('part') else ''})" if info.get("level") else ""))
        for e in errs:
            print("[LỖI]      " + e)
        for w in warns:
            print("[CẢNH BÁO] " + w)
        if "cover" in info:
            print(f"Phủ port: {info['cover'][0]}/{info['cover'][1]}")
        total += len(errs)
    print("KẾT QUẢ:", "OK" if total == 0 else f"{total} lỗi")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()

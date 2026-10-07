#!/usr/bin/env python3
"""
Lint file .mmd của stage 2 (mọi level L0/L1/L2) theo references/diagram_conventions.md.

Dùng:
  python3 lint_mermaid.py <file.mmd> [<file2.mmd> ...] [--interface <file có bảng port>] [--parse]

  --interface : file chứa bảng port (cột "Port name", bản cũ "Tên port") – doc/spec/<m>_spec.md hoặc
                interface/<m>_interface.md. Mọi port phải có node pi_/po_ (tính gộp trên mọi part).
                Node gom bus dạng `s_apb_*` phủ mọi port bắt đầu bằng `s_apb_`.
  --parse     : parse thêm bằng thư viện Mermaid thật qua Node.js
                (cần: npm install --prefix .claude/skills/rtl-s2-diagram/scripts)

Kiểm: cú pháp an toàn · nhãn trong nháy kép · subgraph/end · width trên port và thanh ghi ·
đủ port. Cảnh báo khi một file có quá nhiều node (dấu hiệu vẽ mức cổng thay vì kiến trúc).
Mã thoát 0 = không lỗi, 1 = có lỗi.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NODE_DEF = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(\[\/|\[\\|\(\[|\(\(|\{\{|\[\[|\[|\(|>|\{)")
EDGE = re.compile(r"(-\.->|==>|-->|---|-\.-)")
RESERVED = {"end", "graph", "flowchart", "subgraph", "class", "classdef", "style", "click", "linkstyle", "direction"}
MANY_NODES = 40


def lint(lines, iface_ports=None):
    errs, warns = [], []
    body = [(i + 1, l) for i, l in enumerate(lines) if l.strip() and not l.strip().startswith("%%")]
    if not body or not re.match(r"^\s*flowchart\s+(LR|TB|TD|RL|BT)\b", body[0][1]):
        errs.append("dòng đầu (không tính %% comment) phải là 'flowchart LR' (hoặc TB/TD)")

    depth = 0
    node_labels, classes = {}, {}
    for n, l in body:
        s = l.strip()
        if s.lower().startswith("subgraph"):
            depth += 1
        elif s == "end":
            depth -= 1
            if depth < 0:
                errs.append(f"L{n}: 'end' thừa")
        if s.lower().startswith("class "):
            parts = s.split()
            if len(parts) >= 3:
                for nid in parts[1].split(","):
                    classes[nid] = parts[2]
            continue
        if s.lower().startswith(("classdef", "style", "linkstyle", "direction", "subgraph", "flowchart")) or s == "end":
            continue
        # node định nghĩa ở đầu dòng hoặc sau mũi tên
        for seg in EDGE.split(s):
            seg = re.sub(r"^\|[^|]*\|\s*", "", seg.strip())
            m = NODE_DEF.match(seg)
            if not m:
                continue
            nid = m.group(1)
            if nid.lower() in RESERVED:
                errs.append(f"L{n}: id node '{nid}' là từ khóa Mermaid")
            if re.match(r"^[ox]", nid) and re.search(r"--\s*$|--$", s.split(nid)[0]):
                errs.append(f"L{n}: id '{nid}' bắt đầu bằng o/x ngay sau '--' dễ bị hiểu thành mũi tên tròn/chéo")
            rest = seg[len(nid):].strip()
            label = re.search(r'"([^"]*)"', rest)
            if rest and not label:
                warns.append(f"L{n}: nhãn node '{nid}' không đặt trong dấu nháy kép")
            if label:
                node_labels[nid] = label.group(1)
        if re.search(r"(-->|-\.->|==>|---)\s*(\|[^|]*\|\s*)?end\s*$", s):
            errs.append(f"L{n}: không dùng 'end' làm id node")
        for lab in re.findall(r"\|([^|]*)\|", s):
            if not (lab.startswith('"') and lab.endswith('"')):
                errs.append(f"L{n}: nhãn cạnh |{lab}| phải đặt trong nháy kép")
        if s.count('"') % 2:
            errs.append(f"L{n}: số dấu nháy kép lẻ")
    if depth != 0:
        errs.append(f"subgraph/end không cân bằng (lệch {depth})")

    has_width = re.compile(r"\[[^\]]*\d[^\]]*\]")
    for k, lab in node_labels.items():
        if k.startswith(("ff_", "reg_")):
            if classes.get(k) not in ("ff", "reg"):
                warns.append(f"node '{k}' chưa gán class reg")
            if not has_width.search(lab):
                errs.append(f"thanh ghi '{k}' thiếu width/kích thước dạng [..] trong nhãn")
        if k.startswith(("pi_", "po_")) and "*" not in lab and not re.search(r"\[\d+:\d+\]", lab):
            errs.append(f"port '{k}' thiếu width dạng [msb:0] trong nhãn (bus gom nhóm thì ghi dạng prefix_*)")
        if k.startswith("u_") and ":" not in lab:
            warns.append(f"instance '{k}' nên ghi nhãn '<instance> : <module>'")

    inner = [k for k in node_labels if not k.startswith(("pi_", "po_", "n_"))]
    if len(inner) > MANY_NODES:
        warns.append(f"{len(inner)} node bên trong – có vẻ đang vẽ mức cổng; gom logic nhỏ vào khối blk_")

    if iface_ports is not None:
        labels = " ".join(v for k, v in node_labels.items() if k.startswith(("pi_", "po_")))
        groups = re.findall(r"([A-Za-z_]\w*_)\*", labels)
        for p in iface_ports:
            if p.endswith("*") or any(p.startswith(g) for g in groups):
                continue
            if not re.search(rf"(^|\W){re.escape(p)}(\W|$)", labels):
                errs.append(f"port '{p}' của bảng port không có node pi_/po_ trong diagram")
    return errs, warns


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


def parse_real(files):
    node = shutil.which("node")
    if not node or not (HERE / "node_modules" / "mermaid").is_dir():
        print("[PARSE]    bỏ qua: cần Node.js và `npm install --prefix .claude/skills/rtl-s2-diagram/scripts`")
        return True
    r = subprocess.run([node, str(HERE / "mermaid_parse.mjs"), *[str(Path(f).resolve()) for f in files]],
                       capture_output=True, text=True, encoding="utf-8", cwd=HERE)
    print(r.stdout.strip())
    if r.returncode and r.stderr:
        print(r.stderr.strip()[:800])
    return r.returncode == 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--interface")
    ap.add_argument("--parse", action="store_true")
    a = ap.parse_args()
    files = [Path(f) for f in a.files]
    ports = iface_ports(Path(a.interface)) if a.interface else None
    if ports is not None and not ports:
        print(f"[LỖI]      {a.interface}: không có bảng port (cột 'Port name')")
        sys.exit(1)

    total_err = 0
    merged = []
    for f in files:
        lines = f.read_text(encoding="utf-8").splitlines()
        merged += [l for l in lines if not l.strip().startswith("flowchart")]
        errs, warns = lint(lines)
        print(f"== {f}")
        for e in errs:
            print("[LỖI]      " + e)
        for w in warns:
            print("[CẢNH BÁO] " + w)
        total_err += len(errs)

    if ports is not None:
        # phủ port tính trên toàn bộ các part, không tạo file tạm
        errs, _ = lint(["flowchart LR", *merged], ports)
        cov = [e for e in errs if "của bảng port" in e]
        for e in cov:
            print("[LỖI]      " + e)
        total_err += len(cov)
        print(f"Phủ port: {len(ports) - len(cov)}/{len(ports)}")

    if a.parse and not parse_real(files):
        total_err += 1

    print("KẾT QUẢ:", "OK" if total_err == 0 else f"{total_err} lỗi")
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()

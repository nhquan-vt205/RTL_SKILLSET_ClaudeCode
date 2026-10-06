#!/usr/bin/env python3
"""
Gate (điều kiện đầu vào) cho từng stage của RTL flow. Bản ở 5 skill dùng chung logic; bản của
rtl-s2-diagram có thêm --format và nhiều module cho stage 2 (stage 1, 3, 4, 5 hành vi không đổi,
nên copy bản này sang skill khác vẫn tương thích).

Chạy từ thư mục gốc project:
    python3 .claude/skills/<skill>/scripts/check_preconditions.py --stage 1
    python3 .claude/skills/<skill>/scripts/check_preconditions.py --stage 2 --module <m> [<m2> ...]
            [--level L0|L1|L2] [--format mermaid|html|both]

Mã thoát: 0 = đủ điều kiện về file · 1 = thiếu → skill dừng · 2 = gọi sai.

Stage 2 nhận mọi module của lệnh trong một lần gọi (mỗi module một khối kết quả); stage khác một module.
--format (chỉ stage 2, mặc định mermaid): html/both chỉ cho MỘT module, leaf, level L2.
HTML là bản xem trực quan của S2; gate S3 chỉ nhận doc/diagram/<m>/*.mmd.

Hai chế độ, tự nhận biết:
  - đơn      : không có doc/spec/spec_status.md và không có dấu hiệu phân cấp. Module = mỗi file
               doc/spec/<m>_spec.md; dòng đầu spec ghi "Loại · Level · Trạng thái".
  - phân cấp : có doc/spec/spec_status.md → bảng "Danh sách module" là hierarchy,
               "TRẠNG THÁI:" là gate chung.
spec_status.md là nơi ghi hierarchy, không phải dấu hiệu duy nhất. Thiếu nó mà spec cho thấy nhiều
module có quan hệ cha–con (architecture/ có ≥ 2 spec, spec ghi "Loại: top|block" hoặc "Cha: <m>")
→ coi là phân cấp thiếu hierarchy: S1 báo cần tạo, S2–S5 dừng. Không tạo spec_status.md giả để qua gate.
Bảng port (cột "Tên port") nằm trong interface/<m>_interface.md nếu có, không thì trong spec.
Không file nào khác (notes, 00_parameters, datapath/, controlpath/) là bắt buộc.

Script chỉ kiểm cái kiểm được bằng máy. Đánh giá nội dung là việc của Claude theo SKILL.md.
Dòng [INFO] là thông tin cho Claude dùng (file cần đọc, level, module con), không làm dừng.
"""
import argparse
import re
import sys
from pathlib import Path

PLACEHOLDERS = {".gitkeep", "readme.md", ".ds_store", "thumbs.db"}
RTL_EXT = (".sv", ".v")
LEVELS = ("L0", "L1", "L2")
FORMATS = ("mermaid", "html", "both")
NAME = re.compile(r"^[A-Za-z_]\w*$")


def real_files(folder: Path):
    if not folder.is_dir():
        return []
    return [p for p in folder.rglob("*") if p.is_file() and p.name.lower() not in PLACEHOLDERS]


def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "doc" / "spec").is_dir():
            return p
    return start


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def _cells(line):
    return [re.sub(r"[`*]", "", c).strip() for c in line.strip().strip("|").split("|")]


# ---------- spec / interface ----------

def spec_file(root: Path, mod: str):
    spec = root / "doc" / "spec"
    for cand in (spec / f"{mod}_spec.md", spec / "architecture" / f"{mod}_spec.md"):
        if cand.is_file():
            return cand
    return None


def has_port_table(p: Path) -> bool:
    for line in read(p).splitlines():
        if line.strip().startswith("|") and any(c.lower().startswith("tên port") for c in _cells(line)):
            return True
    return False


def interface_file(root: Path, mod: str):
    p = root / "doc" / "spec" / "interface" / f"{mod}_interface.md"
    if p.is_file():
        return p
    s = spec_file(root, mod)
    return s if s and has_port_table(s) else None


def header_field(p: Path, key: str):
    """Giá trị 'key: X' trong 15 dòng đầu file (vd. 'Loại: leaf · Level: L2 · Trạng thái: PASS')."""
    head = "\n".join(read(p).splitlines()[:15])
    m = re.search(rf"{key}\s*:\s*\**\s*([A-Za-z0-9_]+)", head, re.I)
    return m.group(1) if m else ""


def spec_modules(root: Path):
    spec = root / "doc" / "spec"
    out = []
    for d in (spec, spec / "architecture"):
        if d.is_dir():
            out += [p.name[: -len("_spec.md")] for p in sorted(d.glob("*_spec.md"))]
    return list(dict.fromkeys(out))


# ---------- chế độ phân cấp ----------

def hier_signals(root: Path):
    """Dấu hiệu phân cấp lấy từ spec hiện có (dùng khi chưa có spec_status.md)."""
    arch = root / "doc" / "spec" / "architecture"
    n_arch = len(list(arch.glob("*_spec.md"))) if arch.is_dir() else 0
    why = [f"architecture/ có {n_arch} spec"] if n_arch >= 2 else []
    for m in spec_modules(root):
        p = spec_file(root, m)
        kind, parent = header_field(p, "Loại").lower(), header_field(p, "Cha")
        if kind in ("top", "block"):
            why.append(f"`{m}` là {kind}")
        elif parent and parent != m:
            why.append(f"`{m}` có cha `{parent}`")
    return why


def status_file(root: Path):
    f = root / "doc" / "spec" / "spec_status.md"
    return f if f.is_file() else None


def global_status(f: Path):
    m = re.search(r"TRẠNG THÁI\s*:\s*\**\s*(PASS|FAIL)", read(f), re.I)
    return m.group(1).upper() if m else "UNKNOWN"


def module_table(f: Path):
    """Bảng 'Danh sách module' → [{name, parent, kind, level}] theo thứ tự.
    Cột nhận diện theo tiêu đề: Module | Cha | Loại | Level."""
    rows, header, in_sec = [], None, False
    for line in read(f).splitlines():
        if re.match(r"#+\s*Danh sách module", line, re.I):
            in_sec = True
            continue
        if not in_sec:
            continue
        if line.startswith("#"):
            break
        if not line.strip().startswith("|"):
            continue
        c = _cells(line)
        if header is None:
            header = [h.lower() for h in c]
            continue
        if set("".join(c)) <= set("-: "):
            continue

        def col(*names):
            for i, h in enumerate(header):
                if any(h.startswith(n) for n in names) and i < len(c):
                    return c[i]
            return ""
        name = c[0]
        if not NAME.match(name) or name.lower() in ("module", "tên_module"):
            continue
        parent = col("cha", "parent")
        lv = col("level").upper()
        rows.append({"name": name, "parent": parent if NAME.match(parent or "") else "",
                     "kind": col("loại", "kind").lower(), "level": lv if lv in LEVELS else ""})
    return rows


def descendants(rows, mod):
    out, todo = [], [mod]
    while todo:
        cur = todo.pop()
        kids = [r["name"] for r in rows if r["parent"] == cur]
        out += kids
        todo += kids
    return out


# ---------- diagram / rtl ----------

def rtl_file(root: Path, mod: str):
    for ext in RTL_EXT:
        for cand in (root / "rtl" / f"{mod}{ext}", root / "rtl" / mod / f"{mod}{ext}"):
            if cand.is_file():
                return cand
    return None


def diagram_level(root: Path, mod: str):
    """Level của diagram hiện có: header '%% stage : 2 - diagram Lx' trong .mmd, hoặc 'Level:' trong notes."""
    d = root / "doc" / "diagram" / mod
    if not d.is_dir():
        return ""
    for p in sorted(d.glob("*.mmd")):
        m = re.search(r"%%.*?\b(?:diagram|level)\b\s*:?\s*(L[012])\b", read(p), re.I)
        if m:
            return m.group(1).upper()
    for name in (f"{mod}_notes.md", f"{mod}_ff_notes.md"):
        if (d / name).is_file():
            m = re.search(r"Level\s*:\s*\**\s*(L[012])", read(d / name), re.I)
            if m:
                return m.group(1).upper()
            if name.endswith("_ff_notes.md"):
                return "L2"
    return ""


# ---------- gate ----------

def check(stage, mod, level_arg, root, skill_dir, fmt="mermaid"):
    ok, miss, info = [], [], []

    def need(cond, msg_ok, msg_miss):
        (ok if cond else miss).append(msg_ok if cond else msg_miss)

    spec = root / "doc" / "spec"

    if stage == 1:
        src = real_files(spec / "source")
        need(bool(src), f"doc/spec/source/ có {len(src)} file input",
             "doc/spec/source/ trống – chưa có tài liệu input")
        for f in src:
            info.append(f"input: {rel(root, f)}")
        sf = status_file(root)
        existing = spec_modules(root)
        hint = [] if sf else hier_signals(root)
        if sf or existing:
            info.append(f"spec đã có ({'phân cấp' if sf or hint else 'đơn'}): {', '.join(existing) or '–'} "
                        "→ chỉ sửa phần bị ảnh hưởng")
        if hint:
            info.append("phát hiện thiết kế phân cấp (" + "; ".join(hint) + ") nhưng thiếu spec_status.md "
                        "→ lần chạy này phải tạo spec_status.md với hierarchy thật")
        return ok, miss, info

    sf = status_file(root)
    rows = module_table(sf) if sf else []
    names = [r["name"] for r in rows] if sf else spec_modules(root)
    if not mod:
        miss.append(f"Chưa chỉ định module. Gọi lại kèm tên, ví dụ: /{skill_dir.name} <tên_module>")
        if names:
            miss.append("Các module hiện có: " + ", ".join(names))
        return ok, miss, info

    sp = spec_file(root, mod)
    if sf:
        info.append("chế độ: phân cấp (doc/spec/spec_status.md)")
        st = global_status(sf)
        need(st == "PASS", "spec_status.md: TRẠNG THÁI = PASS",
             f"Stage 1 chưa PASS (spec_status.md: {st}) – chạy /rtl-s1-spec trước")
        need(mod in names, f"module `{mod}` có trong hierarchy",
             f"module `{mod}` không có trong 'Danh sách module' của spec_status.md"
             + (f" (hiện có: {', '.join(names)})" if names else ""))
        row = next((r for r in rows if r["name"] == mod), {"parent": "", "kind": "", "level": ""})
    elif hier_signals(root):
        info.append("chế độ: phân cấp nhưng thiếu doc/spec/spec_status.md")
        miss.append("Phát hiện thiết kế phân cấp (" + "; ".join(hier_signals(root)) + ") nhưng thiếu "
                    "doc/spec/spec_status.md – chạy /rtl-s1-spec để khởi tạo/cập nhật hierarchy")
        lv = header_field(sp, "Level").upper() if sp else ""
        row = {"parent": header_field(sp, "Cha") if sp else "",
               "kind": header_field(sp, "Loại").lower() if sp else "", "level": lv if lv in LEVELS else ""}
    else:
        info.append("chế độ: đơn (không có spec_status.md)")
        st = header_field(sp, "Trạng thái").upper() if sp else ""
        if sp:
            need(st == "PASS", f"{rel(root, sp)}: Trạng thái = PASS",
                 f"{rel(root, sp)}: Trạng thái = {st or 'không ghi'} – chạy /rtl-s1-spec để chốt "
                 "(dòng 'Loại: … · Level: … · Trạng thái: PASS')")
        lv = header_field(sp, "Level").upper() if sp else ""
        row = {"parent": "", "kind": header_field(sp, "Loại").lower() if sp else "",
               "level": lv if lv in LEVELS else ""}

    need(sp is not None, f"spec: {rel(root, sp) if sp else ''}",
         f"thiếu spec của `{mod}` (doc/spec/{mod}_spec.md hoặc doc/spec/architecture/{mod}_spec.md)"
         + ("" if sf or not names else f" – module hiện có: {', '.join(names)}"))
    itf = interface_file(root, mod)
    need(itf is not None, f"bảng port: {rel(root, itf) if itf else ''}",
         f"không tìm thấy bảng port (cột 'Tên port') của `{mod}` trong spec hay interface/{mod}_interface.md")

    kids = [r["name"] for r in rows if r["parent"] == mod]
    info.append(f"loại: {row['kind'] or '?'} · cha: {row['parent'] or '–'} · "
                f"module con: {', '.join(kids) if kids else 'không có'}")
    extra = [rel(root, p) for p in (spec / "interface" / "00_parameters.md",
                                    spec / "register_file" / "register_map.md",
                                    spec / "controlpath" / f"{mod}_fsm.md") if p.is_file()]
    if extra:
        info.append("tài liệu tách riêng liên quan: " + ", ".join(extra))

    if stage == 2:
        for k in kids:
            need(interface_file(root, k) is not None, f"có bảng port module con {k}",
                 f"thiếu bảng port của module con `{k}` (spec hoặc interface/{k}_interface.md)")
        if level_arg:
            lv, why = level_arg, "theo --level"
        elif row["level"]:
            lv, why = row["level"], "theo spec_status.md" if sf else "theo dòng Level của spec"
        else:
            lv, why = ("L0", "module có module con") if kids else ("L2", "leaf, mặc định")
        info.append(f"level đề xuất: {lv} ({why})")
        old = diagram_level(root, mod)
        if old and old != lv:
            info.append(f"diagram hiện có ở {old} – đổi sang {lv} phải nêu lý do trong báo cáo")
        leaf = not kids and row["kind"] not in ("top", "block")
        if fmt != "mermaid":
            what = f"level {lv}, " + ("leaf" if leaf else f"không phải leaf (loại {row['kind'] or '?'}"
                                      + (f", module con: {', '.join(kids)}" if kids else "") + ")")
            need(lv == "L2" and leaf, f"--format {fmt}: `{mod}` là leaf, level L2",
                 f"--format {fmt} chỉ dùng cho module leaf ở L2 (`{mod}`: {what}) – "
                 f"gọi lại với --format mermaid; không tự chuyển định dạng")
        info.append(f"định dạng: {fmt}")
        ddir = root / "doc" / "diagram" / mod
        if fmt == "html" and (ddir / f"{mod}.mmd").is_file():
            info.append(f"đã có doc/diagram/{mod}/{mod}.mmd – HTML render từ chính file này, không vẽ lại "
                        "kiến trúc (muốn vẽ lại: --format both)")
        if fmt == "mermaid" and (ddir / f"{mod}.html").is_file():
            info.append(f"còn doc/diagram/{mod}/{mod}.html – vẽ lại .mmd thì xóa file này "
                        "(hoặc gọi --format both để cập nhật cả hai)")

    if stage == 3:
        ddir = root / "doc" / "diagram" / mod
        mmd = sorted(ddir.glob("*.mmd")) if ddir.is_dir() else []
        need(bool(mmd), f"diagram: {', '.join(rel(root, p) for p in mmd)}",
             f"thiếu diagram doc/diagram/{mod}/*.mmd – chạy /rtl-s2-diagram {mod} trước")
        notes = [p for p in (ddir / f"{mod}_notes.md", ddir / f"{mod}_ff_notes.md") if p.is_file()]
        if notes:
            info.append(f"ghi chú thiết kế: {rel(root, notes[0])}")
        lv = diagram_level(root, mod) or row["level"] or ("L0" if kids else "L2")
        info.append(f"level: {lv}")
        missing = [k for k in descendants(rows, mod) if rtl_file(root, k) is None]
        if missing:
            info.append("module con chưa có RTL (chỉ instance, không tự viết): " + ", ".join(missing))
        rules = real_files(skill_dir / "coding_rules")
        info.append(f"coding_rules/: {len(rules)} file" if rules
                    else "coding_rules/ trống → dùng references/default_rtl_rules.md")

    if stage in (4, 5):
        r = rtl_file(root, mod)
        need(r is not None, f"RTL: {rel(root, r) if r else ''}",
             f"chưa có rtl/{mod}.sv|.v – chạy /rtl-s3-rtl {mod} trước")
        sub = descendants(rows, mod)
        if sub:
            info.append(f"phạm vi tích hợp: DUT gồm {len(sub)} module con ({', '.join(sub)})")

    if stage == 4:
        tpl = real_files(skill_dir / "vplan_template")
        info.append(f"vplan_template/: {', '.join(p.name for p in tpl)}" if tpl
                    else "vplan_template/ trống → dùng định dạng mặc định trong references/test_selection.md")

    if stage == 5:
        vdir = root / "doc" / "vplan"
        vp = sorted(vdir.glob(f"{mod}_vplan.*")) if vdir.is_dir() else []
        need(bool(vp), f"vplan: {', '.join(p.name for p in vp)}",
             f"chưa có doc/vplan/{mod}_vplan.* – chạy /rtl-s4-vplan {mod} trước")
        for k in descendants(rows, mod):
            need(rtl_file(root, k) is not None, f"có RTL module con {k}",
                 f"thiếu RTL module con `{k}` – cần để mô phỏng {mod} (/rtl-s3-rtl {k})")
        rules = real_files(skill_dir / "tb_coding_rules")
        info.append(f"tb_coding_rules/: {len(rules)} file" if rules
                    else "tb_coding_rules/ trống → dùng references/default_tb_rules.md")

    return ok, miss, info


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=int, required=True, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--module", nargs="*", default=[])
    ap.add_argument("--level", default="", type=str.upper, choices=["", *LEVELS])
    ap.add_argument("--format", default="mermaid", type=str.lower, choices=FORMATS)
    ap.add_argument("--root", default="")
    a = ap.parse_args()
    mods = [m for arg in a.module for m in arg.replace(",", " ").split()]
    if a.stage != 2 and len(mods) > 1:
        ap.error(f"gate stage {a.stage} kiểm từng module một – gọi riêng cho mỗi module")
    if a.format != "mermaid" and a.stage != 2:
        ap.error("--format chỉ dùng cho stage 2")
    if a.format != "mermaid" and len(mods) > 1:
        ap.error(f"--format {a.format} chỉ dùng cho MỘT module leaf L2 (lệnh có {len(mods)} module: "
                 f"{', '.join(mods)}) – gọi riêng từng module, hoặc dùng --format mermaid")

    skill_dir = Path(__file__).resolve().parent.parent
    root = Path(a.root).resolve() if a.root else find_project_root(Path.cwd().resolve())
    failed = False
    for mod in mods or [""]:
        ok, miss, info = check(a.stage, mod, a.level, root, skill_dir, a.format)
        print(f"== GATE STAGE {a.stage}{' – ' + mod if mod else ''} ==  (root: {root})")
        for m in ok:
            print(f"[OK]    {m}")
        for m in info:
            print(f"[INFO]  {m}")
        for m in miss:
            print(f"[THIẾU] {m}")
        print("KẾT QUẢ:", "ĐỦ ĐIỀU KIỆN" if not miss else "KHÔNG ĐỦ ĐIỀU KIỆN – DỪNG")
        failed |= bool(miss)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

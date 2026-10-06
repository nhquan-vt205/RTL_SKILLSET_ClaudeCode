#!/usr/bin/env python3
"""
Đối chiếu log mô phỏng với danh sách test ID trong vplan.

Dùng:
  python3 check_sim_log.py <log> <vplan.md|.xlsx|.csv|.docx> [--id-re REGEX] [--pass-re REGEX] [--fail-re REGEX]

Mặc định:
  --id-re   'TC_[A-Z0-9_]+_\\d{3}'
  --pass-re '\\[TEST\\]\\s+(?P<id>\\S+)\\s+PASS'
  --fail-re '\\[TEST\\]\\s+(?P<id>\\S+)\\s+FAIL'
Mã thoát 0 = mọi test trong vplan đều PASS; 1 = có FAIL/thiếu.
"""
import argparse
import re
import sys
from pathlib import Path


def vplan_text(p: Path) -> str:
    ext = p.suffix.lower()
    if ext == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
        return "\n".join(" ".join(str(c) for c in row if c is not None)
                         for ws in wb.worksheets for row in ws.iter_rows(values_only=True))
    if ext == ".docx":
        import docx
        d = docx.Document(p)
        parts = [para.text for para in d.paragraphs]
        for t in d.tables:
            for r in t.rows:
                parts.append(" ".join(c.text for c in r.cells))
        return "\n".join(parts)
    return p.read_text(encoding="utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("vplan")
    ap.add_argument("--id-re", default=r"TC_[A-Z0-9_]+_\d{3}")
    ap.add_argument("--pass-re", default=r"\[TEST\]\s+(?P<id>\S+)\s+PASS")
    ap.add_argument("--fail-re", default=r"\[TEST\]\s+(?P<id>\S+)\s+FAIL")
    a = ap.parse_args()

    ids = list(dict.fromkeys(re.findall(a.id_re, vplan_text(Path(a.vplan)))))
    log = Path(a.log).read_text(encoding="utf-8", errors="replace")
    passed = {m.group("id").rstrip(":") for m in re.finditer(a.pass_re, log)}
    failed = {m.group("id").rstrip(":") for m in re.finditer(a.fail_re, log)}

    print(f"Vplan: {len(ids)} test · Log: {len(passed)} PASS, {len(failed)} FAIL")
    bad = 0
    for t in ids:
        if t in failed:
            st, bad = "FAIL", bad + 1
        elif t in passed:
            st = "PASS"
        else:
            st, bad = "KHÔNG CÓ KẾT QUẢ", bad + 1
        print(f"  {t:<28} {st}")
    extra = (passed | failed) - set(ids)
    for t in sorted(extra):
        print(f"  {t:<28} THỪA (không có trong vplan)")
    if re.search(r"\[TIMEOUT\]|\$fatal|FATAL", log):
        print("  Log có TIMEOUT/FATAL")
        bad += 1
    print("KẾT QUẢ:", "TẤT CẢ PASS" if bad == 0 and not extra else "CÓ VẤN ĐỀ")
    sys.exit(0 if bad == 0 and not extra else 1)


if __name__ == "__main__":
    main()

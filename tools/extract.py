#!/usr/bin/env python3
"""Достаёт таблицы и разделы из PDF по списку tools/manifest.py.

Запуск (из корня проекта):
    tools/.venv/bin/python tools/extract.py all        # таблицы и разделы
    tools/.venv/bin/python tools/extract.py tables     # только таблицы
    tools/.venv/bin/python tools/extract.py sections   # только разделы и вырезки

Результат:
    data/draft/tables/<id>.csv        таблица для проверки (разделитель «;»), коммитится
    tmp/tables_raw/<id>.txt           сырой текст тех же листов
    tmp/pages/<id>_pNN.png            картинка листа для сверки
    tmp/sections/<id>.txt             текст раздела с метками листов
    tmp/cut/<id>.pdf                  вырезка листов (схемы, формулы)
    tmp/review.html                   страница сверки: картинка рядом с таблицей
    tmp/report.txt                    краткий отчёт
Всё в tmp/ можно пересоздать этим скриптом, в git не попадает.
PDF никуда не загружаются, всё считается локально.
"""
import csv
import html
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

sys.path.insert(0, str(Path(__file__).resolve().parent))
from manifest import BOOKS, MISSING_BOOKS, SECTIONS, TABLES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DRAFT = ROOT / "data" / "draft"
TMP = ROOT / "tmp"  # generated, not committed
CUT = TMP / "cut"

_docs = {}


def open_book(key):
    if key not in _docs:
        _docs[key] = fitz.open(ROOT / BOOKS[key])
    return _docs[key]


# ---------------------------------------------------------------- поиск таблицы

def header_rx(num):
    """«Таблица N» в т.ч. с разрядкой «Т а б л и ц а  N» (так набран РПР-69)."""
    n = re.escape(num)
    word = r"Т\s?а\s?б\s?л\s?и\s?ц\s?а|Табл\."
    return re.compile(rf"^[ \t]*(?:{word})\s*{n}(?!\d)(?!\.\d)", re.I | re.M)


def squash(s):
    return re.sub(r"\s+", "", s).lower()


def find_table_sheet(entry):
    """Лист PDF с заголовком таблицы. Возвращает (лист, заголовок, все_совпадения)."""
    doc = open_book(entry["book"])
    rx = header_rx(entry["num"])
    hits = []
    for i in range(len(doc)):
        text = doc[i].get_text()
        m = rx.search(text)
        if m:
            tail = text[m.start(): m.start() + 220]
            title = " ".join(tail.split())[:110]
            kw_ok = squash(entry.get("kw", "")) in squash(tail)
            hits.append((i + 1, title, kw_ok))
    if not hits:
        return None, "", []
    hits.sort(key=lambda h: (not h[2], abs(h[0] - entry["page"])))
    return hits[0][0], hits[0][1], hits


# ---------------------------------------------------------------- извлечение

def clean_cell(v):
    return "" if v is None else re.sub(r"\s+", " ", str(v)).strip()


def tables_on_page(page):
    for strategy in ("lines", "text"):
        try:
            found = page.find_tables(strategy=strategy).tables
        except Exception:
            found = []
        found = [t for t in found if t.row_count >= 2 and t.col_count >= 2]
        if found:
            return found, strategy
    return [], None


def header_y(page, num):
    rx = header_rx(num)
    for b in page.get_text("blocks"):
        if rx.search(b[4]):
            return b[1]
    return 0


def extract_table(entry):
    sheet, title, hits = find_table_sheet(entry)
    res = dict(entry=entry, sheet=sheet, title=title, hits=[h[0] for h in hits], rows=[], note="", strategy=None, sheets=[])
    if entry.get("scan"):
        res["sheet"], res["sheets"] = entry["scan"], [entry["scan"]]
        res["note"] = "лист в PDF картинка без текстового слоя, нужна ручная сверка или OCR"
        return res
    if entry.get("sheet"):  # лист задан вручную: заголовок «Таблица N» в тексте не распознан
        sheet = res["sheet"] = entry["sheet"]
        res["title"] = " ".join(open_book(entry["book"])[sheet - 1].get_text().split())[:110]
    if sheet is None:
        res["note"] = "заголовок таблицы не найден в тексте"
        return res
    doc = open_book(entry["book"])
    for k in range(entry.get("pages", 1)):
        pno = sheet + k
        if pno > len(doc):
            break
        page = doc[pno - 1]
        res["sheets"].append(pno)
        found, strategy = tables_on_page(page)
        if k == 0:
            y = header_y(page, entry["num"])
            found = sorted([t for t in found if t.bbox[1] >= y - 5], key=lambda t: t.bbox[1])
        table = found[0] if found else None
        if table is None:
            res["note"] += f" на листе {pno} таблица не распознана;"
            continue
        res["strategy"] = strategy
        rows = [[clean_cell(c) for c in r] for r in table.extract()]
        if k > 0 and res["rows"] and rows and rows[0] == res["rows"][0]:
            rows = rows[1:]
        res["rows"].extend(rows)
    return res


def load_manual(entry, res):
    """Ручная расшифровка по картинке страницы (для плохо распознанных сканов)."""
    path = DRAFT / "manual" / f"{entry['id']}.csv"
    if path.exists():
        with open(path, encoding="utf-8-sig", newline="") as f:
            res["rows"] = list(csv.reader(f, delimiter=";"))
        res["manual"] = True
        res["note"] = (res["note"] + " ЗНАЧЕНИЯ ПЕРЕПИСАНЫ ВРУЧНУЮ С КАРТИНКИ, сверьте.").strip()
    return res


def quality(rows):
    if not rows:
        return 0, 0, 1.0
    cols = max(len(r) for r in rows)
    cells = sum(len(r) for r in rows)
    empty = sum(1 for r in rows for c in r if not c)
    return len(rows), cols, (empty / cells if cells else 1.0)


def render_page(key, pno, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    open_book(key)[pno - 1].get_pixmap(matrix=fitz.Matrix(1.6, 1.6)).save(out)


def run_tables():
    (DRAFT / "tables").mkdir(parents=True, exist_ok=True)
    results = []
    for entry in TABLES:
        res = load_manual(entry, extract_table(entry))
        results.append(res)
        tid = entry["id"]
        if res["sheets"]:
            text = "\n".join(
                f"===== лист PDF {p} =====\n{open_book(entry['book'])[p - 1].get_text()}" for p in res["sheets"]
            )
            (TMP / "tables_raw").mkdir(parents=True, exist_ok=True)
            (TMP / "tables_raw" / f"{tid}.txt").write_text(text, encoding="utf-8")
            for p in res["sheets"]:
                render_page(entry["book"], p, TMP / "pages" / f"{tid}_p{p}.png")
        if res["rows"]:
            with open(DRAFT / "tables" / f"{tid}.csv", "w", newline="", encoding="utf-8-sig") as f:
                csv.writer(f, delimiter=";").writerows(res["rows"])
    return results


# ---------------------------------------------------------------- разделы

def run_sections():
    (TMP / "sections").mkdir(parents=True, exist_ok=True)
    CUT.mkdir(parents=True, exist_ok=True)
    out = []
    for s in SECTIONS:
        a, b = s["sheets"]
        doc = open_book(s["book"])
        parts, chars, empty = [], 0, []
        for pno in range(a, b + 1):
            t = doc[pno - 1].get_text()
            chars += len(t)
            if len(t.strip()) < 40:
                empty.append(pno)
            parts.append(f"===== лист PDF {pno} =====\n{t}")
        (TMP / "sections" / f"{s['id']}.txt").write_text("\n".join(parts), encoding="utf-8")
        dst = fitz.open()
        dst.insert_pdf(doc, from_page=a - 1, to_page=b - 1)
        dst.save(CUT / f"{s['id']}.pdf")
        note = f", листы без текста: {empty}" if empty else ""
        out.append(f"[разд] {s['id']}: листы {a}-{b}, {chars} знаков{note} ({s['what']})")
    return out


# ---------------------------------------------------------------- отчёты

def build_review(results):
    rows = []
    for r in results:
        e = r["entry"]
        rows.append(f"<h2>Таблица {html.escape(e['num'])} · {html.escape(BOOKS[e['book']])} · {html.escape(e['id'])}</h2>")
        if not r["sheets"]:
            rows.append(f"<p class=bad>{html.escape(r['note'])}</p>")
            continue
        n, c, empty = quality(r["rows"])
        rows.append(
            f"<p>заголовок в книге: <b>{html.escape(r['title'])}</b><br>листы PDF {r['sheets']}, "
            f"строк {n}, столбцов {c}, пустых ячеек {empty:.0%} {html.escape(r['note'])}</p>"
        )
        rows.append("<div class=pair><div class=img>")
        for p in r["sheets"]:
            rows.append(f"<img src='pages/{e['id']}_p{p}.png' loading=lazy>")
        rows.append("</div><div class=tbl><table>")
        for row in r["rows"]:
            rows.append("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in row) + "</tr>")
        rows.append("</table></div></div>")
    css = (
        "body{font:14px system-ui;margin:20px;background:#fff;color:#111}"
        ".pair{display:flex;gap:16px;align-items:flex-start}.img{flex:1}.img img{width:100%;border:1px solid #ccc}"
        ".tbl{flex:1;overflow:auto}table{border-collapse:collapse}td{border:1px solid #999;padding:3px 6px}"
        "h2{margin-top:36px;border-top:2px solid #333;padding-top:10px}.bad{color:#b00}"
    )
    (TMP / "review.html").write_text(
        f"<!doctype html><meta charset=utf-8><title>Сверка таблиц</title><style>{css}</style>" + "\n".join(rows),
        encoding="utf-8",
    )


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    DRAFT.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, fname in BOOKS.items():
        if not (ROOT / fname).exists():
            lines.append(f"{key}: файл {fname} не найден")
        else:
            lines.append(f"{key}: листов {len(open_book(key))}")
    if cmd in ("all", "tables"):
        results = run_tables()
        build_review(results)
        lines.append("")
        for r in results:
            e = r["entry"]
            if not r["sheets"]:
                lines.append(f"[НЕТ ] {e['id']}: {r['note']}")
                continue
            n, c, empty = quality(r["rows"])
            if e.get("scan") and not r.get("manual"):
                lines.append(f"[СКАН] {e['id']}: лист {r['sheets']}, {r['note']}")
                continue
            flag = "РУЧН" if r.get("manual") else ("ok  " if n >= 2 and empty < 0.35 else "ПРОВ")
            multi = f", других совпадений: {[h for h in r['hits'] if h != r['sheet']]}" if len(r["hits"]) > 1 else ""
            lines.append(
                f"[{flag}] {e['id']}: лист {r['sheets']}, {n}x{c}, пустых {empty:.0%}{multi}"
                + (f", {r['note'].strip()}" if r["note"].strip() else "")
                + f"\n        заголовок: {r['title']}"
            )
    if cmd in ("all", "sections"):
        lines.append("")
        lines.extend(run_sections())
    lines.append("")
    for m in MISSING_BOOKS:
        lines.append(f"[нет книги] {m}")
    report = "\n".join(lines)
    (TMP / "report.txt").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()

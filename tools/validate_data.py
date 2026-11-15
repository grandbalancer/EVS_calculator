#!/usr/bin/env python3
"""Validate data/builtin/*.json and tests/golden/*.json. Standard library only.

Run from the project root:
    python3 tools/validate_data.py

Checks:
  1. Structure: format, category, unique ids, required fields, status values.
  2. Citations: known book, PDF sheet inside the book.
  3. Quantities: allowed unit, allowed key set, every number also appears in 'raw'.
  4. Cross-check with drafts: numbers of table-sourced values must occur in the
     reviewed CSV (data/draft/manual/<id>.csv, else data/draft/tables/<id>.csv).
  5. References: detonator ids in machine limits, source/wire ids in tests.
  6. Golden cases: recompute R, I, U and verdicts from the inputs with the
     formulas of evs_method.json and compare with 'expected'; list where the
     book itself differs.
Exit code 1 if any error. Book discrepancies and status counts are info only.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILTIN = ROOT / "data" / "builtin"
DRAFT = ROOT / "data" / "draft"
GOLDEN = ROOT / "tests" / "golden"

STATUSES = {"verified", "checked", "transcribed", "conflict", "derived"}
KINDS = {"table", "text", "example", "figure"}
UNITS = {"Ом", "Ом/км", "А", "В", "м", "мм", "мм²", "кг", "кг/км", "мкФ", "мДж", "кВт", "Гц",
         "А·ч", "мес", "лет", "°C", "шт", "пар", "раз", "1"}
QKEYS = [{"v"}, {"min", "max"}, {"max"}, {"min"}, {"v", "tol"}]
SCHEMES = {"series", "parallel", "pairs"}

errors, infos = [], []


def err(where, msg):
    errors.append(f"ОШИБКА {where}: {msg}")


def numbers_in(text):
    """All numbers in a string, decimal comma or point; '20 000' also yields 20000."""
    t = text.replace(" ", " ")
    out = {float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", t)}
    for a, b in re.findall(r"(?<![\d.,])(\d{1,3}) (\d{3})(?![\d.,])", t):
        out.add(float(a + b))
    return out


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        err(path.name, f"не читается JSON: {e}")
        return None


def draft_numbers(draft_id):
    for sub in ("manual", "tables"):
        p = DRAFT / sub / f"{draft_id}.csv"
        if p.exists():
            return numbers_in(p.read_text(encoding="utf-8-sig"))
    return None


def walk_quantities(obj, path=""):
    """Yield (path, dict) for every quantity-like dict (has 'unit')."""
    if isinstance(obj, dict):
        if "unit" in obj:
            yield path, obj
            return
        for k, v in obj.items():
            yield from walk_quantities(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_quantities(v, f"{path}[{i}]")


def check_quantity(where, q):
    if q.get("unit") not in UNITS:
        err(where, f"единица {q.get('unit')!r} не из списка")
    if "raw" not in q:
        err(where, "нет raw")
        return []
    keys = {k for k in q if k in ("v", "min", "max", "tol")}
    if keys not in QKEYS:
        err(where, f"недопустимый набор полей {sorted(keys)}")
    nums = [q[k] for k in keys]
    in_raw = numbers_in(q["raw"])
    for x in nums:
        if not isinstance(x, (int, float)):
            err(where, f"не число: {x!r}")
        elif float(x) not in in_raw:
            err(where, f"{x} нет в raw {q['raw']!r}")
    return nums


def check_source(where, s, books):
    if s.get("book") not in books:
        err(where, f"неизвестная книга {s.get('book')!r}")
        return
    if books[s["book"]] is None:  # web source: needs a locator instead of a sheet
        if not (s.get("locator") or s.get("table") or s.get("formula")):
            err(where, f"для веб-источника {s['book']} нужен locator")
        return
    if "sheet" not in s and s.get("locator"):
        return
    sheets = s.get("sheet")
    sheets = sheets if isinstance(sheets, list) else [sheets]
    for sh in sheets:
        if not isinstance(sh, int) or not 1 <= sh <= books[s["book"]]:
            err(where, f"лист {sh} вне книги {s['book']} (1..{books[s['book']]})")
    if "kind" in s and s["kind"] not in KINDS:
        err(where, f"kind {s['kind']!r}")
    if "draft" in s and draft_numbers(s["draft"]) is None:
        err(where, f"нет черновика {s['draft']}.csv")


def main():
    files = {p.stem: load(p) for p in sorted(BUILTIN.glob("*.json"))}
    if not files.get("books"):
        err("books.json", "нет файла")
        return report()
    books = {b["id"]: b.get("pdf_sheets") for b in files["books"]["items"]}
    for b in files["books"]["items"]:
        if not b.get("pdf_sheets") and not b.get("url") and not b.get("photos"):
            err(f"books:{b['id']}", "нужен pdf_sheets (PDF), url (веб-источник) или photos (фото страниц)")
        for ph in b.get("photos", []):
            if not (ROOT / ph).exists():
                err(f"books:{b['id']}", f"нет файла {ph}")

    ids, by_cat, statuses = {}, {}, Counter()
    for name, doc in files.items():
        if doc is None:
            continue
        if doc.get("format") != "evs-catalog/1":
            err(name, "format должен быть evs-catalog/1")
        by_cat[doc.get("category")] = doc.get("items", [])
        for it in doc.get("items", []):
            w = f"{name}:{it.get('id')}"
            for f in ("id", "name", "sources", "status"):
                if f not in it:
                    err(w, f"нет поля {f}")
            if not re.fullmatch(r"[a-z0-9_]+", str(it.get("id", ""))):
                err(w, "id только a-z0-9_")
            if it.get("id") in ids:
                err(w, f"id повторяется (уже в {ids[it['id']]})")
            ids[it.get("id")] = name
            if it.get("status") not in STATUSES:
                err(w, f"статус {it.get('status')!r}")
            statuses[it.get("status")] += 1
            for s in it.get("sources", []):
                check_source(w, s, books)
            for p, q in walk_quantities(it):
                check_quantity(f"{w}.{p}", q)
            cross_check(w, it, books)

    det_ids = {d["id"] for d in by_cat.get("detonators", [])}
    for it in by_cat.get("sources", []):
        for i, row in enumerate(it.get("limits", [])):
            w = f"sources:{it['id']}.limits[{i}]"
            if row.get("scheme") not in SCHEMES:
                err(w, f"схема {row.get('scheme')!r}")
            if row.get("ed") is not None and row["ed"] not in det_ids:
                err(w, f"нет ЭД {row['ed']!r}")
            check_source(w, row.get("source", {}), books)

    method = {m["id"]: m for m in by_cat.get("method", [])}
    sources = {s["id"]: s for s in by_cat.get("sources", [])}
    wires = {w["id"]: w for w in by_cat.get("wires", [])}
    golden(method, sources, wires, books)
    tasks(sources, wires, books)
    source_sizing(books)
    infos.append("статусы записей: " + ", ".join(f"{k} {v}" for k, v in sorted(statuses.items())))
    import subprocess
    chk = subprocess.run([sys.executable, str(ROOT / "tools" / "digest.py"), "--check"], capture_output=True, text=True)
    if chk.returncode != 0:
        err("docs/data_digest.md", (chk.stdout or chk.stderr).strip())
    return report()


def cross_check(w, it, books):
    """Table-sourced numbers must appear in the reviewed draft CSV."""
    for i, row in enumerate(it.get("limits", [])):
        d = row.get("source", {}).get("draft")
        nums = draft_numbers(d) if d else None
        if nums is None:
            continue
        for p, q in walk_quantities(row):
            for k in ("v", "min", "max"):
                if k in q and float(q[k]) not in nums:
                    err(f"{w}.limits[{i}].{p}", f"{q[k]} нет в черновике {d}")
    srcs = it.get("sources", [])
    if not srcs or any("draft" not in s for s in srcs):
        return  # params partly from running text: no draft to compare with
    nums = set()
    for s in srcs:
        nums |= draft_numbers(s["draft"]) or set()
    for p, q in walk_quantities(it.get("params", {})):
        for k in ("v", "min", "max", "tol"):
            if k in q and float(q[k]) not in nums:
                err(f"{w}.params.{p}", f"{q[k]} нет в черновиках {[s['draft'] for s in srcs]}")


def wire_r(inp, part):
    if f"r_{part}" in inp:
        return inp[f"r_{part}"]
    length = inp.get(f"L_{part}_used", inp.get("L_v_used") if part == "uch" else None)
    return length * inp[f"r_pr_{part}"] / 1000


def golden(method, sources, wires, books):
    path = GOLDEN / "evs_cases.json"
    doc = load(path) if path.exists() else None
    if not doc:
        return
    cur = {k: method[k]["params"] for k in ("i_series", "i_pairs") if k in method}
    for c in doc["cases"]:
        w = f"golden:{c['id']}"
        check_source(w, c["source"], books)
        inp, sch, ac = c["input"], c["scheme"], c["current"]
        r_m, r_uch = wire_r(inp, "m"), wire_r(inp, "uch")
        if sch == "series":
            R, I = r_m + r_uch + inp["m"] * inp["r_d"], cur["i_series"][ac]["v"]
        elif sch == "series_gzu":
            R, I = r_m + r_uch + inp["m"] * (inp["r_d"] + inp["r_g"]), cur["i_series"][ac]["v"]
        elif sch == "pairs":
            R, I = r_m + r_uch + inp["m_p"] * inp["r_d"] / 2, cur["i_pairs"][ac]["v"]
        elif sch == "parallel":
            R, I = r_m + (r_uch + inp["r_d"]) / inp["n"], inp["n"] * inp["i_single"]
        elif sch == "mixed":
            R = r_m + (r_uch + inp["m"] * inp["r_d"]) / inp["n"]
            I = inp["n"] * cur["i_series"][ac]["v"]
        else:
            err(w, f"схема {sch}")
            continue
        got = {"r_m": r_m, "r_uch": r_uch, "R": R, "I": I, "U": I * R}
        tol = c.get("tol", 0.01)
        for k, v in c["expected"].items():
            if k in got and abs(got[k] - v) > tol:
                err(w, f"{k}: пересчёт {got[k]:.4g}, в expected {v}")
        for k, v in c.get("book", {}).items():
            if k in got and abs(got[k] - v) > max(tol, 0.051):
                infos.append(f"книга расходится {c['id']}: {k} в книге {v}, по методу {got[k]:.4g}")
        count = inp.get("m_p") if sch == "pairs" else inp.get("m", inp.get("n"))
        for v in c.get("verdicts", []):
            s = sources.get(v["source"])
            if not s:
                err(w, f"нет источника {v['source']}")
                continue
            rows = [r for r in s["limits"] if r["scheme"] == sch and r["ed"] in (None, "edp")]
            ok = bool(rows) and all(
                count <= lim_val(r["max_count"]) and R <= lim_val(r["max_r"]) for r in rows[:1])
            if ok != v["usable"]:
                err(w, f"вывод по {v['source']}: пересчёт {ok}, ожидалось {v['usable']}")


def source_sizing(books):
    """RPR-69 art. 117-120: number of current sources in series / parallel / mixed."""
    import math
    path = GOLDEN / "source_sizing_cases.json"
    doc = load(path) if path.exists() else None
    if not doc:
        return
    for c in doc["cases"]:
        w = f"sources_golden:{c['id']}"
        check_source(w, c["source"], books)
        i, k = c["input"], c["kind"]
        got = {}
        if k in ("series", "mixed"):
            got["m_raw"] = i["U"] / i["U_src"]
            got["m"] = math.ceil(got["m_raw"] - 1e-9)
        if k == "series":
            got["U_bat"] = got["m"] * i["U_src"]
        if k in ("parallel", "mixed"):
            got["n_raw"] = i["I"] / i["I_src"]
            got["n"] = math.ceil(got["n_raw"] - 1e-9)
        if k == "mixed":
            got["N"] = got["m"] * got["n"]
        if k == "mixed_e0r0":
            got["m_raw"] = 2 * i["I"] * i["R"] / i["E0"]
            got["n_raw"] = 2 * i["I"] * i["R0"] / i["E0"]
            got["m"], got["n"] = math.ceil(got["m_raw"]), math.ceil(got["n_raw"])
            got["N"] = got["m"] * got["n"]
            ibat = lambda n: got["m"] * i["E0"] / (i["R"] + got["m"] * i["R0"] / n)
            got["I_bat"], got["I_bat_n7"] = ibat(got["n"]), ibat(got["n"] - 1)
            got["N_reduced"] = got["m"] * (got["n"] - 1)
        for key, v in c["expected"].items():
            if key in got and abs(got[key] - v) > 0.01:
                err(w, f"{key}: пересчёт {got[key]:.4g}, в expected {v}")
        for key, v in c.get("book", {}).items():
            if key in got and abs(got[key] - v) > 0.051:
                infos.append(f"книга расходится {c['id']}: {key} в книге {v}, точно {got[key]:.4g}")


def lim_val(q):
    return q.get("v", q.get("max"))


def tasks(sources, wires, books):
    path = GOLDEN / "prakt2023_tasks_1_4.json"
    doc = load(path) if path.exists() else None
    if not doc:
        return
    for t in doc["variants"]:
        w = f"tasks:{t['variant']}"
        check_source(w, t["source"], books)
        if t["wire"] != "choice" and t["wire"] not in wires:
            err(w, f"нет провода {t['wire']}")
        if t["current_source"] and t["current_source"] not in sources:
            err(w, f"нет источника {t['current_source']}")
        if t["scheme"] not in SCHEMES:
            err(w, f"схема {t['scheme']}")
    st = Counter(t["status"] for t in doc["variants"])
    infos.append("задания Практикума 1.4: " + ", ".join(f"{k} {v}" for k, v in sorted(st.items())))


def report():
    for line in infos:
        print("инфо:", line)
    for line in errors:
        print(line)
    print("ИТОГ:", "ошибок нет" if not errors else f"ошибок {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

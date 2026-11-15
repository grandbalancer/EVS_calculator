#!/usr/bin/env python3
"""Build docs/data_digest.md: a compact one-file view of data/builtin and tests/golden.

The JSON files stay the source of truth (the app loads them). The digest is what
Claude reads first when writing code: one line per record, key numbers, status,
citation. It is generated, never edited by hand.

    python3 tools/digest.py           # write docs/data_digest.md
    python3 tools/digest.py --check   # exit 1 if the file is out of date (used by validate_data.py)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / "data" / "builtin"
G = ROOT / "tests" / "golden"
OUT = ROOT / "docs" / "data_digest.md"

STATUS = {"verified": "✔✔", "checked": "✔", "transcribed": "…", "conflict": "⚠", "derived": "≈"}


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def q(x):
    """Quantity -> short text in book units."""
    if not isinstance(x, dict):
        return "—"
    if "text" in x:
        return x["text"]
    f = lambda v: f"{v:g}".replace(".", ",")
    if "v" in x and "tol" in x:
        s = f"{f(x['v'])}±{f(x['tol'])}"
    elif "v" in x:
        s = f(x["v"])
    elif "min" in x and "max" in x:
        s = f"{f(x['min'])}–{f(x['max'])}"
    elif "max" in x:
        s = f"≤{f(x['max'])}"
    else:
        s = f"≥{f(x['min'])}"
    return f"{s} {x['unit']}".replace(" 1", "") if x["unit"] == "1" else f"{s} {x['unit']}"


def cite(s):
    if isinstance(s, list):
        return "; ".join(cite(x) for x in s[:3]) + ("; …" if len(s) > 3 else "")
    sh = s.get("sheet")
    sh = "-".join(map(str, sh)) if isinstance(sh, list) else (str(sh) if sh else "")
    parts = [s["book"] + (f":л.{sh}" if sh else "")]
    for k, lab in (("table", "т."), ("article", "ст."), ("formula", "ф.")):
        if s.get(k):
            parts.append(f"{lab}{s[k]}")
    if s.get("locator") and not sh:
        parts.append(s["locator"][:40])
    elif s.get("locator") and s["book"] in ("rpr69s", "rpr69p"):
        page = s["locator"].split("стр.")[-1].strip()
        parts.append(f"стр.{page}")
    return " ".join(parts)


def book_error(c):
    """True for real book errors (arithmetic, wrong reference), not for rounding notes."""
    return any(("rithmetic error" in d) or ("cited as" in d) for d in c.get("discrepancies", []))


def row(*cells):
    return "| " + " | ".join(str(c).replace("|", "/") for c in cells) + " |"


def build():
    books, det, wires = load(B / "books.json"), load(B / "detonators.json"), load(B / "wires.json")
    src, met = load(B / "sources.json"), load(B / "evs_method.json")
    gold, sizing = load(G / "evs_cases.json"), load(G / "source_sizing_cases.json")
    tasks = load(G / "prakt2023_tasks_1_4.json")
    L = []
    a = L.append
    a("# Сводка данных ЭВС")
    a("")
    a("**Сгенерировано `tools/digest.py` из `data/builtin/*.json` и `tests/golden/*.json`. Не править руками:** исправления вносятся в JSON, затем `python3 tools/digest.py`. Источник истины и то, что загружает программа, это JSON; здесь краткий вид для разработки.")
    a("")
    a("Статус: ✔✔ сверено пользователем, ✔ проверено по второму источнику или скану оригинала, ⚠ источники расходятся, ≈ вычислено, … ждёт сверки. Ссылка `книга:л.N` это лист PDF; `стр.N` печатная страница оригинала РПР-69.")
    a("")

    a("## 1. Контракт загрузчика (для `core/`)")
    a("")
    a("- Файлы: `data/builtin/{books,detonators,wires,sources,evs_method}.json`, схема `data/schema/catalog.schema.json`. Пользовательский слой в `%APPDATA%` с той же схемой, id не пересекаются.")
    a("- Величина: `{v | min,max | max | min | v,tol, unit, raw}`; нечисловое `{text}`. `raw` только для показа и сверки.")
    a("- Перевод в СИ при загрузке: Ом, А, В, м, кг без изменений; `Ом/км` → ×0,001 Ом/м; `мм` → ×0,001 м; `мм²` → ×1e-6 м²; `мкФ` → ×1e-6 Ф; `мДж` → ×0,001 Дж; `кВт` → ×1000 Вт; `А·ч` → ×3600 Кл; `кг/км` → ×0,001 кг/м; `шт`, `пар`, `раз`, `1`, `мес`, `лет`, `°C`, `Гц` без пересчёта.")
    a("- Сопротивление линии из провода (`wires`): `cores=2, r_basis=wire` (СПП-2): R = r·L; `cores=2, r_basis=core` (СП-2, ЛТО, ЛТВ): R = 2·r·L; `cores=1` (СП-1, СПП-1, ВМВ): нужны два провода, R = r·(2L). L в км, запас длины по выбору пользователя (`line_margin`).")
    a("- Расчётное сопротивление ЭД `params.r_calc`; ток одиночного ЭД `i_calc_single_dc|ac` (для параллельной схемы).")
    a("- Источник `kind`: `capacitor_machine`, `magnetoelectric_machine` → проверка по `limits` (схема, ЭД, `max_count`, `max_r`); схемы нет в `limits` → не применяется. `accumulator` → Iист = `i_10h` (кислотные, 6СТ-75/190) или `i_8h` (щелочные), Uист = `u_10h` / `u_initial` / `u_nominal`. `dry_battery` → E0 = `u_initial`, R0 = `r_internal` (верх диапазона), Iист = E0/(2R0) без испытания. `power_station` → `u`, `i_nom`. `mains` → `u`, ток не ограничен.")
    a("- Формулы и константы методики берутся из `evs_method.json` по id (раздел 6), не из кода.")
    a("")

    a("## 2. Книги и источники")
    a("")
    a(row("id", "источник", "файл / адрес") )
    a(row("---", "---", "---"))
    for b in books["items"]:
        where = b.get("file") or (", ".join(b["photos"]) if b.get("photos") else b.get("url", ""))
        a(row(b["id"], b["name"], f"`{where}`"))
    a("")

    a("## 3. Электродетонаторы")
    a("")
    a(row("id", "имя", "r_calc", "r_cold", "I одиночн. пост/перем", "I группы пост/перем", "I безоп.", "ст.", "источник"))
    a(row(*["---"] * 9))
    for d in det["items"]:
        p = d["params"]
        a(row(d["id"], d["name"], q(p["r_calc"]), q(p["r_cold"]),
              f"{q(p['i_calc_single_dc'])} / {q(p['i_calc_single_ac'])}",
              f"{q(p['i_calc_group_dc'])} / {q(p['i_calc_group_ac'])}", q(p["i_safe"]),
              STATUS[d["status"]], cite(d["sources"])))
    a("")

    a("## 4. Провода и кабели")
    a("")
    a(row("id", "имя", "жил", "основа r", "r на 1 км", "петля линии, Ом/км", "сечение", "ст.", "источник"))
    a(row(*["---"] * 9))
    for w in wires["items"]:
        p = w["params"]
        r = p["r_per_km"]["v"]
        loop = r if (w["cores"] == 2 and w["r_basis"] == "wire") else 2 * r
        a(row(w["id"], w["name"], w["cores"], w["r_basis"], q(p["r_per_km"]), f"{loop:g}".replace(".", ","),
              q(p.get("core_section")), STATUS[w["status"]], cite(w["sources"])))
    a("")

    a("## 5. Источники тока")
    a("")
    a("### Машинки")
    a("")
    a(row("id", "имя", "набор", "U", "возможности: схема ЭД ≤шт ≤Ом", "ст.", "источник"))
    a(row(*["---"] * 7))
    for s in src["items"]:
        if "machine" not in s["kind"]:
            continue
        lims = "; ".join(f"{l['scheme']} {l['ed'] or '?'} {q(l['max_count'])} {q(l['max_r'])}" for l in s["limits"])
        u = q(s["params"].get("u_nom") or s["params"].get("u_at_290"))
        a(row(s["id"], s["name"], s["set"], u, lims, STATUS[s["status"]], cite(s["sources"][:1])))
    a("")
    a("### Аккумуляторы (Iист по решению 2026-11-15: длительный режим)")
    a("")
    a(row("id", "имя", "Uист", "Iист", "ёмкость", "справочно: стартерный/1-ч ток", "ст.", "источник"))
    a(row(*["---"] * 8))
    for s in src["items"]:
        if s["kind"] != "accumulator":
            continue
        p = s["params"]
        u = p.get("u_10h") or p.get("u_initial") or p.get("u_nominal")
        i = p.get("i_10h") or p.get("i_8h")
        cap = p.get("capacity_10h") or p.get("capacity")
        ref = p.get("i_starter") or p.get("i_1h")
        a(row(s["id"], s["name"], q(u), q(i), q(cap), q(ref), STATUS[s["status"]], cite(s["sources"][:1])))
    a("")
    a("### Сухие батареи и элементы (табл. 11)")
    a("")
    a(row("id", "имя (новое)", "E0 нач.", "U в конце гарантии", "R0 нач.", "нагрузка испыт.", "ст."))
    a(row(*["---"] * 7))
    for s in src["items"]:
        if s["kind"] != "dry_battery":
            continue
        p = s["params"]
        a(row(s["id"], f"{s['name']} ({', '.join(s.get('aliases', [])) or '—'})", q(p["u_initial"]), q(p["u_end_warranty"]),
              q(p["r_internal"]), q(p["r_test_load"]), STATUS[s["status"]]))
    a("")
    a("### Электростанции (табл. 15) и сети (ст. 96)")
    a("")
    a(row("id", "имя", "U", "I ном.", "род тока", "ст."))
    a(row(*["---"] * 6))
    for s in src["items"]:
        if s["kind"] in ("power_station", "mains"):
            p = s["params"]
            ck = p["current_kind"]["text"] + (f" {q(p['frequency'])}" if p.get("frequency") else "")
            a(row(s["id"], s["name"], q(p["u"]), q(p.get("i_nom")), ck, STATUS[s["status"]]))
    a("")

    a("## 6. Методика (evs_method.json)")
    a("")
    a("Порядок шагов и пояснения: `docs/methods/evs.md`.")
    a("")
    a(row("id", "формула / правило / значения", "ст.", "источник"))
    a(row(*["---"] * 4))
    for m in met["items"]:
        if m.get("formula"):
            body = f"`{m['formula']}`"
        elif m.get("params"):
            body = ", ".join(f"{k}: {q(v)}" for k, v in m["params"].items())
        elif m.get("rows"):
            body = "; ".join(f"≤{r['max_series_ed']} ЭД: 70-АМЦГ×{r['amcg70']['count']}, 100-АМЦГ×{r['amcg100']['count']}" for r in m["rows"])
        else:
            body = ""
        if m.get("formula") and m.get("params"):
            body += "; " + ", ".join(f"{k}: {q(v)}" for k, v in m["params"].items())
        if m.get("rule"):
            body += (" — " if body else "") + m["rule"]
        if m["id"] == "line_margin" and m.get("apply"):
            body += f" Применение: {m['apply']['main']} (магистраль), {m['apply']['section']} (участковые)."
        a(row(m["id"], body, STATUS[m["status"]], cite(m["sources"])))
    a("")

    a("## 7. Эталонные задачи (тесты ядра)")
    a("")
    a("Тесты C++ проверяют `expected` (точный расчёт), `book` хранится для справки. Допуск 0,01.")
    a("")
    a(row("id", "схема", "вход", "R, Ом", "I, А", "U, В", "ошибка книги"))
    a(row(*["---"] * 7))
    for c in gold["cases"]:
        e = c["expected"]
        inp = ", ".join(f"{k}={v}" for k, v in c["input"].items() if k != "wire")
        a(row(c["id"], c["scheme"], inp, f"{e['R']:g}", f"{e['I']:g}", f"{e['U']:g}",
              "да" if book_error(c) else ("округление" if c.get("discrepancies") else "—")))
    a("")
    a(row("id", "подбор источников", "вход", "ожидается", "ошибка книги"))
    a(row(*["---"] * 5))
    for c in sizing["cases"]:
        inp = ", ".join(f"{k}={v}" for k, v in c["input"].items() if k != "src")
        exp = ", ".join(f"{k}={v:g}" for k, v in c["expected"].items())
        a(row(c["id"], c["kind"], inp, exp, "да" if book_error(c) else "—"))
    a("")
    st = {}
    for t in tasks["variants"]:
        st.setdefault(t["status"], []).append(str(t["variant"]))
    a("Задания Практикума 1.4 (`prakt2023_tasks_1_4.json`, ответов в книге нет): " +
      "; ".join(f"{k}: {', '.join(v)}" for k, v in sorted(st.items())) + ".")
    a("")

    a("## 8. Что не входит в данные")
    a("")
    a("- Вкладки «Конструкции» и «Грунты»: ждут ТЗ пользователя; черновые таблицы зарядов лежат в `data/draft/tables/vzd2019_t1_*.csv`, в `data/builtin` не переносились.")
    a("- Мины: справочника нет.")
    a("- ЭДЗД, ЭДКЗ: электрических параметров в книгах нет.")
    spor = [i["id"] for f in (det, wires, src, met) for i in f["items"] if i["status"] == "conflict"]
    a(f"- Спорные записи (⚠): {', '.join(spor) or 'нет'}; подробности в заметках JSON и `docs/errata.md`.")
    return "\n".join(L) + "\n"


def main():
    text = build()
    if "--check" in sys.argv:
        cur = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if cur != text:
            print("docs/data_digest.md устарел: запустите python3 tools/digest.py")
            return 1
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"записано {OUT.relative_to(ROOT)}: {text.count(chr(10))} строк")
    return 0


if __name__ == "__main__":
    sys.exit(main())

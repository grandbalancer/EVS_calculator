# CLAUDE.md

Guidance for Claude (any model) continuing this project. State as of 2026-11-15: ЭВС data is complete and verified, no C++ yet.

**Read order:** this file → `docs/data_digest.md` (all ЭВС data in one page, generated) → `docs/methods/evs.md` (method passport, approved) → `PLAN.md` (architecture, roadmap, proposals) only when needed. `README.md` describes the app for the user.

## Project

A standalone offline desktop app for Windows 7 SP1+ with a minimalist Russian UI. Three tabs: (1) electric blasting network (ЭВС) editor and calculator, with a reverse mode that draws a network from entered parameters; (2) charge calculation and 2D layout for structures; (3) the same for soils and rock. Everything comes from cited sources. **No game integration, no network access**; the user's future game project is unrelated, ignore it.

## Language

- Talk to the user in Russian. `README.md`, `PLAN.md`, `docs/*.md` are in Russian.
- Code, identifiers, comments, commit messages, this file: English. UI strings Russian, wrapped in `tr()`.
- The folder is `проект взрыное дело` (sic). Always quote paths.

## Content and safety rules

The domain is military demolition. Work at the software-engineering and reference-tool level.

- Only formulas, tables and values transcribed from a cited source. Primary: the three PDFs in the root and the original RPR-69 scan. Open sources (standards, textbooks, manuals) may fill gaps (user permission 2026-11-15): register in `data/builtin/books.json` with `url`/`accessed`, cite a `locator`, prefer two agreeing sources. Never write explosive-effect formulas, charge masses, material constants or explosive data from model memory.
- Book errors are fixed and the correct value is used; keep the printed value (`corrections` in data, `book` in golden cases) and log it in `docs/errata.md`.
- Every record has `sources` and a `status` (`verified` by the user, `checked`, `transcribed`, `conflict`, `derived`). The UI shows everything that is not `verified` as unverified, and `conflict` distinctly. Only the user's confirmation sets `verified`.
- Nothing beyond the sources (new weapons data, optimising effects): ask the user. Do not pass CAPTCHAs or bot checks, do not download from file-sharing aggregators; ask the user.
- An earlier session's first answer was cut off by a safety classifier. If it happens, continue with the non-sensitive layers (architecture, UI, data pipeline), keep outputs short and source-traceable.

## Decisions (do not re-ask)

- C++17, Qt 5.15.2 (last Qt for Win7), Qt Widgets + QGraphicsView, CMake, MinGW 8.1 32-bit, `_WIN32_WINNT=0x0601`, no OpenGL, Inno Setup + `windeployqt`.
- Develop on macOS; Windows build and UI check on the user's Win10/11. Real Win7 smoke test is a release blocker (no Win7 machine yet).
- `core/` is Qt-free C++17, testable on the Mac. Pure functions return `Result + CalcTrace` (formula, substitution, result, source).
- ЭВС editor: free canvas, grid snapping, length and resistance above each wire. Reverse mode draws only with complete data. Charge layouts: 2D plan and section with dimensions.
- v1 extras: save/open network files, PNG/PDF export, print, user-defined elements.
- Order: ЭВС, then structures, then soils. Tabs 2-3 wait for the user's spec.
- Only Claude maintains the code: simple code, data in files, many tests. Light theme, Russian only.
- Both source-machine sets are included (RPR-69 legacy and 2019 textbook): a default the user never explicitly confirmed; change only if the user says so.
- Git: private GitHub repository `grandbalancer/EVS_calculator`, remote `origin` over SSH, branch `main` (2026-11-15). Commit and push only when the user asks. Never commit `tmp/`, `sources/` or the book PDFs (`.gitignore`).

User decisions on the ЭВС method (2026-11-15):
- СПП-2 75 Ом/км is the loop of both cores (RPR Table 5 confirms 37,5 per core).
- Wire margin (default ×1,125, RPR art. 121/123: 10-15 %) only when the user switches it on, separately for main and section wires.
- Accumulators: I_src is the 10-hour current as in RPR art. 117 (alkaline: 8-hour; 6СТ-75/190: C10/10). Starter current is reference only.
- Machine tables without a detonator type (vzd2019 3.1, 3.2, ПМ-4 text) apply to ЭДП, as in the Практикум.
- Mixed network: RPR art. 113 formula (8).

## Architecture (details in PLAN.md section 3)

UI (Qt Widgets) → application (projects, undo/redo, export, user elements) → core (domain, calc, drawing) + data (built-in JSON, user layer in `%APPDATA%`). Two ЭВС solvers: the textbook-method solver gives the verdict; a general circuit solver gives per-detonator currents and handles topologies outside the method, labelled "вне методики". One `Network` graph for editor and reverse mode; one `Drawing` model for tabs 2-3.

## Repository map

```
data/builtin/   books, detonators, wires, sources, evs_method (.json): SOURCE OF TRUTH, loaded by the app
data/schema/    catalog.schema.json
data/draft/     manual/*.csv (hand transcriptions), tables/*.csv (extracted): cross-check input for the validator
tests/golden/   evs_cases.json (8), source_sizing_cases.json (4), prakt2023_tasks_1_4.json (20 variants)
docs/           data_digest.md (generated), methods/evs.md, errata.md, original/ (never edit)
tools/          extract.py, manifest.py, pdfq.py, validate_data.py, digest.py, fix_reference_xlsx.py
sources/        web/RPR-69_sappers_org.pdf (original scan), photos/ (user's photos p. 84-85)   [git-ignored]
tmp/            page renders, review.html, cut PDFs, raw text, one-off scripts                 [git-ignored]
*.pdf (root)    the three source books                                                         [git-ignored]
planned: core/ app/ installer/
```

## Commands

- `python3 tools/validate_data.py`: schema, citations, raw-vs-number, cross-check with drafts, recompute golden cases, digest freshness. Must pass before any commit touching data.
- `python3 tools/digest.py`: regenerate `docs/data_digest.md` after any JSON change.
- `tools/.venv/bin/python tools/extract.py all|tables|sections`: CSVs to `data/draft/tables/`, everything else to `tmp/` (`tmp/review.html` is the user's side-by-side check page).
- `tools/.venv/bin/python tools/pdfq.py info|find|text|cut|gaps <pdf> ...` (sheets start at 1).
- Setup: `python3 -m venv tools/.venv && tools/.venv/bin/pip install -r tools/requirements.txt` (PyMuPDF pinned to 1.24.14; 2.x pulls onnxruntime). macOS has no `timeout`.

## Sources

| id | File | Notes |
|---|---|---|
| `rpr69` | `RPR-69.pdf` (403 sheets) | Partly retyped edition, garbled OCR digits, empty sheets 23, 59, 99…, pages 82-83 and 102-113 missing. Retyping errors exist (Table 11, Table 15 unit) |
| `rpr69s` | `sources/web/RPR-69_sappers_org.pdf` (233 sheets) | Original 1969 scan, image-only, **two printed pages per sheet**: cite sheet + locator with the printed page. Renders `tmp/pages/rpr69s_sheet<N>_<L|R>.png`. Wins over `rpr69`. Missing p. 84-85 |
| `rpr69p` | `sources/photos/*.webp` | User's photos of p. 84-85 (Tables 14, 15) |
| `vzd2019` | `Uchebnik_po_VZD_3__2019_polny.pdf` (459) | Born-digital, printed page = sheet; read formulas from images |
| `prakt2023` | `Praktikum_Vzryvnoe_delo_2023.pdf` (121) | Excerpt; worked problems contain arithmetic errors |
| `konspekt2021` | `pdfcoffee.com_-69-3-pdf-free.pdf` | Anonymous lecture notes, not RPR-69. Secondary only; do not use its charge or mine chapters |
| web | see `books.json` | ГОСТ 2190-77, ИР 3012165-0302-94, БГТУ battery textbook, Лукьянов «Взрывные работы», ПГУПС slide |

Cite PDF sheets, never printed pages (except `rpr69s`/`rpr69p` locators). The mines handbook is not provided.

Locations for tabs 2-3 (not yet specified): textbook charge tables 1.2-1.17 on sheets 51-109 (КЗ-6 is 1.9), chapters 4.1-4.3 from sheet 247, soils 5.1 sheet 286; Практикум 2.1-2.3, 3.1; RPR charges text sheets 20-28. Drafts exist in `data/draft/tables/vzd2019_t1_*.csv`, not in `data/builtin`.

Working economically: never read whole books; `pdfq.py find` to locate, read single page images; transcribe scans by hand into `data/draft/manual/*.csv`; do not trust RPR text-layer digits.

## Traps

Full list in `docs/errata.md`. Wire resistance basis (per core vs per wire, single-core lines count both ways) is the main 2× error source; it is handled by `cores` + `r_basis`. Table 3.2 is titled КПМ-3 but is КПМ-1А. ЭД-8Э/ЭД-8Ж share one column; ЭД-8-Ж cold resistance is a `conflict` (unused in the calculation). ЭДЗД/ЭДКЗ have no electrical data. Decimal comma and point are mixed. For tab 2: Table 1.6 has "2,5…2,5".

## Open items (waiting for the user)

1. Proposals in PLAN.md section 7: cloud Windows build (needs a private GitHub repo), Qt via `aqtinstall` on the Mac.
2. Specs for tabs 2 and 3.
3. A Win7 SP1 machine or VM; the mines handbook if mines are needed.

## Next steps

1. Stage 0: CMake skeleton, Qt-free `core` library with a JSON loader for `data/builtin` (SI conversion per `docs/data_digest.md` section 1), 3-tab window, tests, Windows build with `windeployqt`, Inno Setup installer.
2. Stage 2: textbook solver in `core/` per `docs/methods/evs.md`; C++ tests read `tests/golden/*.json` and assert `expected` (not `book`), tolerance 0,01.

## Conventions

- SI internally; display units as in the books; parse decimal comma and point.
- Record: `id`, `name`, quantities `{v|min,max|max|min|v,tol, unit, raw}` or `{text}`, `sources[{book, sheet|locator, table?, article?, formula?, kind, draft?}]`, `status`, `notes`, optional `corrections`. Built-in data read-only; user overlay uses the same schema.
- New data: page image → `data/draft/manual/*.csv` (+ manifest entry) → `extract.py tables` → user check in `tmp/review.html` → `data/builtin/*.json` → `digest.py` → `validate_data.py`.
- Temporary files only in `tmp/` (renders `tmp/pages/`, scripts `tmp/scripts/`, downloads `tmp/web/`).
- Ask before destructive actions. Do not touch `docs/original/`. Keep `README.md` and `PLAN.md` in sync when decisions change.

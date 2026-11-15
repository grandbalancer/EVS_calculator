"""Список того, что нужно достать из книг.

ВАЖНО: печатные номера страниц не всегда совпадают с листами PDF
(особенно для Учебника по ВЗД и Практикума). Поэтому:
  * таблицы ищутся по номеру и заголовку («Таблица 1.5»), а page
    нужен только для выбора между несколькими совпадениями;
  * разделы заданы номерами ЛИСТОВ PDF (sheets), проверенными по заголовкам.

Поля таблицы:
  id     имя файла результата
  book   ключ книги из BOOKS
  num    номер таблицы, как напечатан в книге
  kw     слово из названия таблицы (проверка, что нашли именно её)
  page   ориентировочная страница (подсказка при нескольких совпадениях)
  pages  сколько листов занимает таблица (по умолчанию 1)
  scan   номер листа, если страница в PDF является картинкой без текста
"""

BOOKS = {
    "rpr69": "RPR-69.pdf",
    "vzd2019": "Uchebnik_po_VZD_3__2019_polny.pdf",
    "prakt2023": "Praktikum_Vzryvnoe_delo_2023.pdf",
    # Anonymous lecture compilation (2021) downloaded by the user from pdfcoffee.com, page titled «РПР 69».
    # It is NOT RPR-69, but reproduces RPR-69 Table 5 (sapper wire), which is missing from RPR-69.pdf.
    "konspekt2021": "pdfcoffee.com_-69-3-pdf-free.pdf",
    # Original 1969 printing of RPR-69 from sappers.org: image-only scan, TWO printed pages per sheet
    # (left/right half). Printed pages 84-85 are missing in this scan. Has the pages missing in RPR-69.pdf.
    "rpr69s": "sources/web/RPR-69_sappers_org.pdf",
}

TABLES = [
    # --- РПР-69: провода ---
    # Table 5 is on an empty sheet of RPR-69.pdf; taken from the original scan (sheet 31, left half = printed p. 60)
    dict(id="rpr69_t05_sapernyi_provod", book="rpr69s", num="5", kw="", page=60, sheet=31),
    # Table 5 of RPR-69 as reproduced in the 2021 lecture compilation (no table number there)
    dict(id="konspekt2021_sapernye_provoda", book="konspekt2021", num="??", kw="", page=36, sheet=36),
    dict(id="rpr69_t06_kabeli", book="rpr69", num="6", kw="кабел", page=60),
    # --- РПР-69: источники тока ---
    dict(id="rpr69_t07_kpm1", book="rpr69", num="7", kw="кпм", page=66),
    dict(id="rpr69_t08_kpm1_dve", book="rpr69", num="8", kw="электродетонатор", page=68),
    dict(id="rpr69_t09_kpm2", book="rpr69", num="9", kw="кпм", page=69),
    dict(id="rpr69_t10_pm1", book="rpr69", num="10", kw="пм", page=73),
    dict(id="rpr69_t11_batarei", book="rpr69", num="11", kw="батаре", page=76, pages=2, sheet=77),
    dict(id="rpr69_t13_shchelochnye", book="rpr69s", num="13", kw="", page=83, sheet=42),
    dict(id="rpr69_t12_batarei_kolichestvo", book="rpr69", num="12", kw="батар", page=80),
    # Номер таблицы аккумуляторов не виден: печатные стр. 82-83 в PDF отсутствуют, лист задан вручную
    dict(id="rpr69_t_akkumulyatory", book="rpr69", num="??", kw="", page=84, sheet=81),
    dict(id="rpr69_t15_elstancii", book="rpr69", num="15", kw="станц", page=84),
    # --- Учебник по ВЗД (2019): электродетонаторы ---
    dict(id="vzd2019_t1_2_ed", book="vzd2019", num="1.2", kw="", page=49, pages=2),
    # --- Учебник по ВЗД (2019): заряды ---
    dict(id="vzd2019_t1_5_sz3a_sz6", book="vzd2019", num="1.5", kw="сз", page=33),
    dict(id="vzd2019_t1_6_sz4p", book="vzd2019", num="1.6", kw="сз", page=34),
    dict(id="vzd2019_t1_7_kz4", book="vzd2019", num="1.7", kw="кз", page=36),
    dict(id="vzd2019_t1_8_kz5", book="vzd2019", num="1.8", kw="кз", page=39),
    dict(id="vzd2019_t1_9_kz6", book="vzd2019", num="1.9", kw="кз-6", page=41),
    dict(id="vzd2019_t1_10_kz7", book="vzd2019", num="1.10", kw="кз-7", page=41),
    dict(id="vzd2019_t1_11_kzu", book="vzd2019", num="1.11", kw="кзу", page=43),
    dict(id="vzd2019_t1_12_kzu2", book="vzd2019", num="1.12", kw="кзу", page=45),
    dict(id="vzd2019_t1_13_umkz", book="vzd2019", num="1.13", kw="кз", page=46),
    dict(id="vzd2019_t1_14_lkz80", book="vzd2019", num="1.14", kw="кз", page=47),
    dict(id="vzd2019_t1_15_kzk", book="vzd2019", num="1.15", kw="кз", page=48),
    # --- Учебник по ВЗД (2019): зажигательные и взрывозажигательные заряды ---
    dict(id="vzd2019_t1_16_zz1", book="vzd2019", num="1.16", kw="зз-1", page=104),
    dict(id="vzd2019_t1_17_vzz2", book="vzd2019", num="1.17", kw="взз-2", page=109),
    # --- Учебник по ВЗД (2019): современные подрывные машинки (по ним решает Практикум) ---
    dict(id="vzd2019_t3_1", book="vzd2019", num="3.1", kw="", page=219),
    dict(id="vzd2019_t3_2", book="vzd2019", num="3.2", kw="", page=221),
    dict(id="vzd2019_t3_3", book="vzd2019", num="3.3", kw="", page=226),
]

# Разделы целиком: листы PDF (включительно), проверены по заголовкам.
# Текст попадает в tmp/sections/, листы вырезаются в tmp/cut/ (генерируется, не коммитится).
SECTIONS = [
    dict(id="rpr69_zaryady_vv", book="rpr69", sheets=(20, 24), what="сосредоточенные и др. заряды ВВ (п. 36-40)"),
    dict(id="rpr69_standartnye_zaryady", book="rpr69", sheets=(24, 28), what="стандартные заряды СЗ-1, СЗ-3, СЗ-3а, СЗ-6, СЗ-6м"),
    dict(id="vzd2019_evs_raschet", book="vzd2019", sheets=(237, 246), what="п. 3.3 Схемы ЭВС и их расчёт"),
    dict(id="vzd2019_provoda", book="vzd2019", sheets=(213, 216), what="3.1.2-3.1.3 средства ЭСВ, сапёрные провода СПП-1/СПП-2 (в РПР-69 таблица 5 отсутствует)"),
    dict(id="vzd2019_istochniki_toka", book="vzd2019", sheets=(217, 231), what="3.2.1-3.2.3 подрывные машинки КПМ-1А, КПМ-3, ПМ-4, КВП-4/100, источники тока (по ним решает Практикум)"),
    dict(id="prakt2023_evs_metodika", book="prakt2023", sheets=(7, 14), what="1.2 методика расчёта ЭВС, 1.3 схемы ЭВС и расчёт"),
    dict(id="prakt2023_evs_zadaniya", book="prakt2023", sheets=(15, 18), what="1.4 задания по расчёту ЭВС"),
]

# Нужная книга, которой нет в папке проекта
MISSING_BOOKS = ["Мины, взрыватели и боеприпасы РФ (справочник), разделы 2-4, стр. 3-26"]

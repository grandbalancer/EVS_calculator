#!/usr/bin/env python3
"""Лёгкие запросы к PDF без чтения книг целиком.

  pdfq.py info  <pdf>                 число страниц, наличие текстового слоя, метки страниц
  pdfq.py find  <pdf> <regex>         на каких страницах PDF встречается выражение (+ строка)
  pdfq.py text  <pdf> <от> <до>       текст страниц PDF (нумерация с 1) в stdout
  pdfq.py cut   <pdf> <от> <до> <out> вырезать страницы PDF (нумерация с 1) в новый PDF
  pdfq.py gaps  <pdf>                 пустые листы и пропуски печатных страниц (по номеру внизу листа)

Нумерация «стр. PDF» это номер листа в файле. Печатный номер страницы книги
может отличаться, смещение определяется командой find.
"""
import re
import sys

import fitz  # PyMuPDF


def cmd_info(path):
    doc = fitz.open(path)
    n = len(doc)
    empty = [i + 1 for i in range(n) if len(doc[i].get_text().strip()) < 40]
    print(f"{path}: страниц {n}, без текстового слоя {len(empty)}")
    if empty:
        print("  первые такие страницы:", empty[:20])
    labels = [doc[i].get_label() for i in range(min(n, 5))]
    print("  метки страниц (первые):", labels)


def cmd_find(path, pattern):
    rx = re.compile(pattern, re.I)
    doc = fitz.open(path)
    for i in range(len(doc)):
        for line in doc[i].get_text().splitlines():
            if rx.search(line):
                print(f"PDF-стр. {i + 1}: {line.strip()[:140]}")


def cmd_text(path, a, b):
    doc = fitz.open(path)
    for i in range(int(a) - 1, int(b)):
        print(f"===== PDF-стр. {i + 1} =====")
        print(doc[i].get_text())


def cmd_cut(path, a, b, out):
    src = fitz.open(path)
    dst = fitz.open()
    dst.insert_pdf(src, from_page=int(a) - 1, to_page=int(b) - 1)
    dst.save(out)
    print(f"сохранено {out}: страниц {len(dst)}")


def cmd_gaps(path):
    """Пустой лист = нет текста, картинок и векторной графики. Пропуск = печатный номер скачет."""
    doc = fitz.open(path)
    prev = None
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text().strip()
        if len(text) < 40 and not page.get_images() and not page.get_drawings():
            print(f"лист {i + 1}: ПУСТОЙ")
        nums = re.findall(r"(?m)^\s*(\d{1,3})\s*$", text)
        pn = int(nums[-1]) if nums else None
        if pn and prev and 1 < pn - prev < 20:
            print(f"лист {i + 1}: пропуск печатных стр. {prev + 1}-{pn - 1}")
        if pn:
            prev = pn


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
    elif args[0] == "info":
        cmd_info(args[1])
    elif args[0] == "find":
        cmd_find(args[1], args[2])
    elif args[0] == "text":
        cmd_text(args[1], args[2], args[3])
    elif args[0] == "gaps":
        cmd_gaps(args[1])
    elif args[0] == "cut":
        cmd_cut(args[1], args[2], args[3], args[4])
    else:
        print(__doc__)

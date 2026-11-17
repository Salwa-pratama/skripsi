#!/usr/bin/env python3
"""Script untuk melokalisasi materi dokumentasi CPython di content/generated/chapters/
ke Bahasa Indonesia sesuai standar dokumentasi resmi Python Software Foundation (docs.python.org/id/3/).
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS_DIR = ROOT / "content" / "generated" / "chapters"

# Kamus terjemahan heading umum
HEADING_TRANSLATIONS = {
    "Numbers": "Bilangan (Numbers)",
    "Text": "Teks (Strings)",
    "Truth Value Testing": "Pengujian Nilai Kebenaran (Truth Value Testing)",
    "Boolean Operations — and, or, not": "Operasi Boolean — and, or, not",
    "Boolean Operations — and , or , not": "Operasi Boolean — and, or, not",
    "Comparisons": "Perbandingan (Comparisons)",
    "Numeric Types — int, float, complex": "Tipe Numerik — int, float, complex",
    "Numeric Types — int , float , complex": "Tipe Numerik — int, float, complex",
    "Boolean Type - bool": "Tipe Boolean - bool",
    "Boolean Type - bool": "Tipe Boolean - bool",
    "if Statements": "Pernyataan if",
    "pass Statements": "Pernyataan pass",
    "The if statement": "Pernyataan if",
    "Value comparisons": "Perbandingan Nilai",
    "Membership test operations": "Operasi Uji Keanggotaan (in, not in)",
    "Identity comparisons": "Perbandingan Identitas (is, is not)",
    "Boolean operations": "Operasi Boolean",
    "Conditional expressions": "Ekspresi Kondisional (Ternary)",
    "for Statements": "Pernyataan for",
    "The range() Function": "Fungsi range()",
    "break and continue Statements": "Pernyataan break dan continue",
    "else Clauses on Loops": "Klausa else pada Perulangan",
    "The while statement": "Pernyataan while",
    "The for statement": "Pernyataan for",
    "Defining Functions": "Mendefinisikan Fungsi (def)",
    "More on Defining Functions": "Lebih Lanjut tentang Mendefinisikan Fungsi",
    "Default Argument Values": "Nilai Argumen Default",
    "Keyword Arguments": "Argumen Kata Kunci (Keyword Arguments)",
    "Special parameters": "Parameter Khusus",
    "Positional-or-Keyword Arguments": "Argumen Posisi atau Kata Kunci",
    "Positional-Only Parameters": "Parameter Hanya-Posisi",
    "Keyword-Only Arguments": "Argumen Hanya-Kata-Kunci",
    "Function Examples": "Contoh Penggunaan Fungsi",
    "Arbitrary Argument Lists": "Daftar Argumen Arbitrer (*args, **kwargs)",
    "Unpacking Argument Lists": "Membongkar Daftar Argumen (Unpacking)",
    "Lambda Expressions": "Ekspresi Lambda",
    "Documentation Strings": "String Dokumentasi (Docstrings)",
    "Function Annotations": "Anotasi Fungsi (Type Hints)",
    "Intermezzo: Coding Style": "Gaya Penulisan Kode (PEP 8)",
    "Function definitions": "Definisi Fungsi",
    "More on Lists": "Lebih Lanjut tentang List",
    "Using Lists as Stacks": "Menggunakan List sebagai Stack (Tumpukan)",
    "Using Lists as Queues": "Menggunakan List sebagai Queue (Antrean)",
    "List Comprehensions": "List Comprehension",
    "Nested List Comprehensions": "List Comprehension Bersarang",
    "The del statement": "Pernyataan del",
    "Tuples and Sequences": "Tuple dan Urutan (Sequences)",
    "Sets": "Himpunan (Sets)",
    "Dictionaries": "Dictionary (Kamus Data)",
    "Looping Techniques": "Teknik Perulangan Koleksi Data",
    "More on Conditions": "Lebih Lanjut tentang Kondisi",
    "Comparing Sequences and Other Types": "Membandingkan Urutan dan Tipe Lainnya",
    "Sequence Types — list, tuple, range": "Tipe Urutan — list, tuple, range",
    "Mapping Types — dict": "Tipe Pemetaan — dict",
    "A Word About Names and Objects": "Seputar Nama dan Objek",
    "Python Scopes and Namespaces": "Cakupan (Scopes) dan Namespace Python",
    "Scopes and Namespaces Example": "Contoh Cakupan dan Namespace",
    "A First Look at Classes": "Mengenal Kelas untuk Pertama Kali",
    "Class Definition Syntax": "Sintaks Definisi Kelas",
    "Class Objects": "Objek Kelas",
    "Instance Objects": "Objek Instans",
    "Method Objects": "Objek Metode",
    "Class and Instance Variables": "Variabel Kelas dan Variabel Instans",
    "Random Remarks": "Catatan Tambahan OOP",
    "Inheritance": "Pewarisan (Inheritance)",
    "Multiple Inheritance": "Pewarisan Berganda (Multiple Inheritance)",
    "Private Variables": "Variabel Privat",
    "Odds and Ends": "Fitur Tambahan Objek",
    "Iterators": "Iterator",
    "Generators": "Generator",
    "Generator Expressions": "Ekspresi Generator",
}

print(f"Memuat {len(HEADING_TRANSLATIONS)} terjemahan heading baku.")

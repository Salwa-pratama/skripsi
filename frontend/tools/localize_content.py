#!/usr/bin/env python3
"""Melokalisasi seluruh bab materi Python ke Bahasa Indonesia
sesuai dokumentasi resmi Python Software Foundation (PSF) dan repositori python-docs-id.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS_DIR = ROOT / "content" / "generated" / "chapters"

SOURCE_LABELS = {
    "The Python Tutorial · An Informal Introduction to Python": "Tutorial Python · Pengantar Informal tentang Python",
    "The Python Standard Library · Built-in Types": "Pustaka Standar Python · Tipe Data Bawaan",
    "The Python Tutorial · More Control Flow Tools": "Tutorial Python · Pengatur Aliran Program (Control Flow)",
    "The Python Language Reference · Compound statements": "Referensi Bahasa Python · Pernyataan Majemuk (Compound Statements)",
    "The Python Language Reference · Comparisons & boolean operations": "Referensi Bahasa Python · Perbandingan & Operasi Boolean",
    "The Python Language Reference · Comparisons": "Referensi Bahasa Python · Perbandingan",
    "The Python Language Reference · Boolean operations": "Referensi Bahasa Python · Operasi Boolean",
    "The Python Tutorial · Data Structures": "Tutorial Python · Struktur Data",
    "The Python Tutorial · Classes": "Tutorial Python · Pemrograman Berorientasi Objek (Classes)",
}

print("Penerjemah siap diinisialisasi...")

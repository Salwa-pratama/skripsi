"""AST (Abstract Syntax Tree) Validator & Code Runner.

Membedah pohon sintaksis kode mahasiswa menggunakan modul bawaan `ast`,
memvalidasi kehadiran node wajib (If, For, FunctionDef, dsb),
dan mengeksekusi kode secara aman dengan batas waktu timeout.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
from pathlib import Path


def translate_syntax_error(msg: str) -> str:
    """Menerjemahkan pesan SyntaxError umum ke Bahasa Indonesia edukatif."""
    msg_lower = msg.lower()
    if "expected ':'" in msg_lower:
        return "Tanda titik dua (:) tidak ditemukan di akhir baris pernyataan."
    if "unexpected indent" in msg_lower:
        return "Indentasi tidak terduga. Pastikan spasi sejajar dengan rapi."
    if "expected an indented block" in msg_lower:
        return "Blok berindentasi diharapkan setelah tanda titik dua (:)."
    if "invalid syntax" in msg_lower:
        return "Sintaks tidak valid. Periksa kembali penulisan kata kunci, tanda kurung, atau tanda petik."
    if "unterminated string literal" in msg_lower:
        return "Tanda petik string belum ditutup dengan benar."
    if "was never closed" in msg_lower:
        return "Tanda kurung buka belum ditutup dengan tanda kurung tutup pasangannya."
    return msg


def analyze_ast(code: str, required_nodes: list[str]) -> dict:
    """Membedah kode Python menggunakan modul ast dan memeriksa required nodes."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        indonesian_msg = translate_syntax_error(exc.msg or "Kesalahan sintaksis")
        return {
            "syntaxValid": False,
            "syntaxError": {
                "message": indonesian_msg,
                "raw": exc.msg,
                "line": exc.lineno or 1,
                "offset": exc.offset or 1,
                "text": exc.text.strip() if exc.text else "",
            },
            "nodesFound": [],
            "nodeDetails": [],
            "requiredNodes": required_nodes,
            "missingNodes": required_nodes,
            "hasAllRequiredNodes": False,
            "astTree": "",
            "summary": "Kode mengalami kesalahan sintaksis sebelum dapat diproses.",
        }

    found_nodes = set()
    node_details = []

    for node in ast.walk(tree):
        node_name = type(node).__name__
        found_nodes.add(node_name)
        if isinstance(node, ast.FunctionDef):
            node_details.append(f"Fungsi: def {node.name}()")
        elif isinstance(node, ast.ClassDef):
            node_details.append(f"Kelas: class {node.name}")
        elif isinstance(node, ast.For):
            node_details.append("Perulangan: loop 'for'")
        elif isinstance(node, ast.While):
            node_details.append("Perulangan: loop 'while'")
        elif isinstance(node, ast.If):
            node_details.append("Percabangan: pernyataan 'if'")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            node_details.append(f"Panggilan: {node.func.id}()")

    missing = [node for node in required_nodes if node not in found_nodes]
    tree_dump = ast.dump(tree, indent=2)

    return {
        "syntaxValid": True,
        "syntaxError": None,
        "nodesFound": sorted(found_nodes),
        "nodeDetails": list(dict.fromkeys(node_details))[:8],
        "requiredNodes": required_nodes,
        "missingNodes": missing,
        "hasAllRequiredNodes": len(missing) == 0,
        "astTree": tree_dump,
        "summary": "Pohon sintaks valid dan berhasil dibedah oleh modul AST.",
    }


def execute_code(code: str, timeout_seconds: float = 4.0) -> dict:
    """Mengeksekusi kode di subprocess dengan timeout pengaman."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = Path(tmp.name)

    try:
        proc = subprocess.run(
            [sys.executable, "-u", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "timedOut": False,
            "exitCode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "timedOut": True,
            "exitCode": -1,
            "stdout": "",
            "stderr": f"Eksekusi melebihi batas waktu {timeout_seconds} detik! Kemungkinan ada loop tanpa henti (infinite loop).",
        }
    finally:
        tmp_path.unlink(missing_ok=True)


def validate_and_run(code: str, required_nodes: list[str] | None = None, expected_output_snippet: str = "") -> dict:
    """Fungsi utama penguji kode: evaluasi AST + eksekusi + validasi output."""
    if required_nodes is None:
        required_nodes = []

    if not code.strip():
        return {
            "success": False,
            "stdout": "",
            "stderr": "Editor masih kosong. Ketikkan kode Python Anda terlebih dahulu.",
            "ast": {
                "syntaxValid": False,
                "syntaxError": None,
                "nodesFound": [],
                "requiredNodes": required_nodes,
                "missingNodes": required_nodes,
                "hasAllRequiredNodes": False,
                "astTree": "",
            },
            "passed": False,
            "feedback": "Ketik kode terlebih dahulu sebelum menjalankan pengujian.",
        }

    ast_result = analyze_ast(code, required_nodes)

    if not ast_result["syntaxValid"]:
        err_msg = ast_result["syntaxError"]["message"]
        err_line = ast_result["syntaxError"]["line"]
        return {
            "success": False,
            "stdout": "",
            "stderr": f"SyntaxError pada baris {err_line}: {err_msg}",
            "ast": ast_result,
            "passed": False,
            "feedback": f"Perbaiki kesalahan sintaks pada baris {err_line}: {err_msg}",
        }

    exec_result = execute_code(code)

    if exec_result["timedOut"] or exec_result["exitCode"] != 0:
        return {
            "success": False,
            "stdout": exec_result["stdout"],
            "stderr": exec_result["stderr"],
            "timedOut": exec_result["timedOut"],
            "ast": ast_result,
            "passed": False,
            "feedback": "Kode menghasilkan error saat dieksekusi. Periksa kembali variabel atau logika logika Anda.",
        }

    stdout_text = exec_result["stdout"]
    has_all_nodes = ast_result["hasAllRequiredNodes"]

    output_matches = True
    if expected_output_snippet and expected_output_snippet.strip():
        output_matches = expected_output_snippet.strip().lower() in stdout_text.lower()

    passed = has_all_nodes and output_matches

    if passed:
        feedback = "Kerja bagus! Kode berjalan mulus dan memenuhi seluruh pohon sintaksis AST yang disyaratkan."
    elif not has_all_nodes:
        missing_str = ", ".join(ast_result["missingNodes"])
        feedback = f"Sintaks berjalan, namun Anda belum menggunakan elemen AST yang diwajibkan: {missing_str}."
    else:
        feedback = f"Kode berjalan, namun output terminal belum memuat snippet yang diharapkan: '{expected_output_snippet}'."

    return {
        "success": True,
        "stdout": stdout_text,
        "stderr": "",
        "timedOut": False,
        "ast": ast_result,
        "outputMatches": output_matches,
        "passed": passed,
        "feedback": feedback,
    }


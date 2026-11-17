#!/usr/bin/env python3
"""Runner & Validator Pohon Sintaks Abstrak (AST) untuk Platform Koding Python.

Memvalidasi sintaksis kode mahasiswa menggunakan modul bawaan `ast`,
memeriksa kepatuhan simpul pohon sintaks (required AST nodes) sesuai silabus,
dan menjalankan kode secara aman di subproses dengan timeout.
"""

from __future__ import annotations

import ast
import json
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
            "requiredNodes": required_nodes,
            "missingNodes": required_nodes,
            "hasAllRequiredNodes": False,
            "astTree": "",
            "summary": "Kode mengalami kesalahan sintaksis sebelum dapat diproses.",
        }

    # Kumpulkan seluruh tipe node yang digunakan mahasiswa
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

    # Buat representasi pohon AST yang rapi
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


def main() -> None:
    raw_input = sys.stdin.read()
    if not raw_input.strip():
        print(json.dumps({"error": "Tidak ada data input yang diterima"}))
        return

    try:
        data = json.loads(raw_input)
    except Exception as exc:
        print(json.dumps({"error": f"JSON input tidak valid: {exc}"}))
        return

    code = data.get("code", "")
    required_nodes = data.get("requiredNodes", [])
    expected_snippet = data.get("expectedOutputSnippet", "")

    if not code.strip():
        print(
            json.dumps(
                {
                    "success": False,
                    "stdout": "",
                    "stderr": "Editor masih kosong. Ketikkan kode Python Anda terlebih dahulu.",
                    "ast": {
                        "syntaxValid": False,
                        "syntaxError": {"message": "Kode kosong", "line": 1},
                        "nodesFound": [],
                        "requiredNodes": required_nodes,
                        "missingNodes": required_nodes,
                        "hasAllRequiredNodes": False,
                        "astTree": "",
                    },
                    "passed": False,
                    "feedback": "Ketik kode manual di editor sesuai instruksi misi.",
                }
            )
        )
        return

    ast_analysis = analyze_ast(code, required_nodes)

    if not ast_analysis["syntaxValid"]:
        print(
            json.dumps(
                {
                    "success": False,
                    "stdout": "",
                    "stderr": ast_analysis["syntaxError"]["message"],
                    "ast": ast_analysis,
                    "passed": False,
                    "feedback": "Perbaiki kesalahan sintaksis sebelum kode dapat dieksekusi.",
                }
            )
        )
        return

    run_res = execute_code(code)

    stdout = run_res["stdout"]
    stderr = run_res["stderr"]
    exit_ok = run_res["exitCode"] == 0 and not run_res["timedOut"]

    output_match = True
    if expected_snippet and exit_ok:
        output_match = expected_snippet.lower() in stdout.lower()

    has_required = ast_analysis["hasAllRequiredNodes"]
    passed = exit_ok and has_required and output_match

    # Buat umpan balik edukatif bahasa Indonesia
    feedback_parts = []
    if passed:
        feedback_parts.append(
            "🎉 Luar biasa! Seluruh konstruksi algoritma terverifikasi oleh modul AST dan luaran program sesuai instruksi!"
        )
    else:
        if not exit_ok:
            feedback_parts.append("⚠️ Program mengalami kesalahan saat dijalankan (Runtime Error).")
        if not has_required:
            missing_names = [f"ast.{m}" for m in ast_analysis["missingNodes"]]
            feedback_parts.append(
                f"⚠️ Konstruksi algoritma belum lengkap. Anda belum menggunakan: {', '.join(missing_names)}."
            )
        elif not output_match and expected_snippet:
            feedback_parts.append(
                f"⚠️ Hasil luaran program belum mencakup nilai yang diharapkan ('{expected_snippet}')."
            )

    response = {
        "success": exit_ok,
        "stdout": stdout,
        "stderr": stderr,
        "timedOut": run_res["timedOut"],
        "ast": ast_analysis,
        "outputMatches": output_match,
        "passed": passed,
        "feedback": " ".join(feedback_parts),
    }

    print(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()

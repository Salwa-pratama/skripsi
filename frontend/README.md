# PyJourney

Jalur belajar **Python 3** dari dokumentasi resmi CPython — variabel dan tipe data,
percabangan, perulangan, fungsi, list & dictionary, sampai OOP dasar dan lanjutan.

Materi diambil langsung dari repositori `cpython/Doc` (tarball resmi Python
3.13.7), dibangun dengan **Sphinx JSON Builder** (`sphinx-build -b json`), lalu
dipetakan dengan **`objects.inv`** untuk indeks API. Frontend-nya **Next.js 16**
(App Router, React 19, TypeScript) dan seluruh environment belajar disiapkan di
**devcontainer Podman**.

> Teks materi resmi tetap dalam bahasa Inggris agar istilah teknis tidak bergeser.
> Lapisan bahasa Indonesia ada pada judul bab, tujuan belajar, poin kunci,
> latihan, dan antarmuka.

---

## Buka di VS Code (Podman)

Prasyarat di laptop:

- Podman (rootless).
- VS Code + ekstensi **Dev Containers** (`ms-vscode-remote.remote-containers`).
- Folder proyek ini.

Build container pertama akan mengunduh image dasar (±1,7 GB) dan Node.js,
lalu memasang dependensi Python/Node. Sediakan koneksi internet dan ruang
disk; build berikutnya memakai cache dan jauh lebih cepat.

Sekali saja, aktifkan socket Podman milik user:

```bash
systemctl --user enable --now podman.socket
```

Workspace ini sudah berisi `.vscode/settings.json` yang mengarahkan ekstensi
Dev Containers ke `podman`, dan `.devcontainer/devcontainer.json` yang memakai
`--userns=keep-id` supaya file di workspace tetap dimiliki user host (UID 1000).

Langkah membuka:

1. Buka folder proyek di VS Code.
2. Tekan `F1` → **Dev Containers: Reopen in Container**
   (atau klik ikon pojok kiri bawah → *Reopen in Container*).
3. Tunggu build pertama. `postCreateCommand` akan:
   - membuat `.venv` dan memasang Sphinx + BeautifulSoup + lxml,
   - menjalankan `npm install`,
   - memakai konten yang sudah ada di `content/generated/` (build Sphinx hanya
     dijalankan jika manifest belum ada).
4. Jalankan aplikasi:

```bash
npm run dev
```

Buka <http://localhost:3000>. Port 3000 sudah di-forward otomatis.

### Kalau Podman tidak terdeteksi

```bash
# cek socket
systemctl --user status podman.socket

# opsional: arahkan CLI devcontainer secara eksplisit
devcontainer up --docker-path podman --workspace-folder .
```

Di VS Code, pastikan setting berikut aktif (sudah ada di workspace):

```json
{
  "dev.containers.dockerPath": "podman"
}
```

Pada distro dengan SELinux, tambahkan opsi `:Z` pada mount workspace bila
muncul error permission. Di Ubuntu (mesin ini) biasanya tidak diperlukan.

---

## Perintah

| Perintah | Fungsi |
| --- | --- |
| `npm run dev` | Menjalankan Next.js di mode development. |
| `npm run build` | Build produksi (semua halaman di-prerender). |
| `npm run start` | Menjalankan hasil build produksi. |
| `npm run typecheck` | Cek TypeScript tanpa emit. |
| `npm run content:build` | Unduh source CPython, build Sphinx JSON, lalu regenerate konten. |
| `npm run content:build:fast` | Parse ulang cache Sphinx tanpa build ulang. |

Build konten membutuhkan Python 3.12+, Sphinx 8.2, BeautifulSoup, dan lxml.
Di devcontainer semuanya sudah dipasang di `.venv`. Di host biasa:

```bash
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements.txt
npm run content:build
```

---

## Pipeline konten

```
python.org tarball (Python-3.13.7.tar.xz)
        │
        ├── Doc/ ......................... sumber reStructuredText resmi
        └── Include/patchlevel.h ........ versi dokumentasi
                    │
                    ▼
        sphinx-build -b json
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
  *.fjson (HTML semantik)   objects.inv
        │                       │
        ▼                       ▼
  parser blok terstruktur   indeks API + chip referensi
        │
        ▼
content/generated/chapters/*.json
public/data/search-index.json
public/data/api-index.json
        │
        ▼
      Next.js
```

Detail penting:

- `content/curriculum.json` adalah satu-satunya konfigurasi kurikulum: slug,
  judul, tujuan, poin kunci, daftar section resmi yang diambil, dan API highlight.
- `tools/fetch_docs.py` mengunduh tarball resmi, mengekstrak `Doc/` +
  `Include/patchlevel.h`, menulis override `conf.py` (hanya dokumen yang dipakai),
  menjalankan Sphinx JSON Builder, lalu mem-parse `.fjson` dan `objects.inv`.
- `tools/build-content.sh` adalah pembungkus yang memakai `.venv` bila tersedia.
- Build dibatasi pada halaman yang relevan: tutorial, built-in types, language
  reference, built-in functions, exceptions, data model, expressions, dan
  glossary. Tidak ada scraping HTML dari docs.python.org.

### Dokumen yang dibangun

- `tutorial/introduction`, `tutorial/controlflow`, `tutorial/datastructures`,
  `tutorial/classes`
- `library/stdtypes`, `library/functions`, `library/exceptions`
- `reference/compound_stmts`, `reference/datamodel`, `reference/expressions`
- `glossary`

---

## Struktur proyek

```
app/
  page.tsx                 beranda
  materi/page.tsx          daftar kurikulum
  materi/[slug]/page.tsx   halaman bab (SSG)
  indeks/page.tsx          indeks API dari objects.inv
  sumber/page.tsx          metodologi, sumber, lisensi
  globals.css              design system + prose dokumentasi
components/                header, search, code block, quiz, notes, dll.
content/
  curriculum.json          konfigurasi 7 bab
  generated/               hasil pipeline (manifest, chapters, pygments.css)
lib/                       tipe, konten, progres, quiz
public/data/               search-index, api-index, LICENSE-PSF
tools/
  fetch_docs.py            pipeline utama
  build-content.sh         pembungkus build
  requirements.txt         pin dependensi Python
.devcontainer/             image Podman + post-create
```

Fitur antarmuka:

- 7 bab berurutan, dari variabel sampai OOP lanjutan.
- Teks resmi CPython dirender sebagai blok terstruktur (heading, kode, tabel,
  definition list, admonition) dengan tautan yang diarahkan ke docs.python.org.
- Pencarian lokal (`Ctrl/Cmd + K`) atas indeks materi.
- Indeks API yang dapat difilter, dibaca dari `objects.inv`.
- Progres bab dan catatan pribadi disimpan di `localStorage` browser.
- Latihan pilihan ganda dengan pembahasan.
- Tema terang/gelap, responsif, dan print-friendly.

---

## Lisensi & atribusi

- Teks dokumentasi Python: **Python Software Foundation License v2**.
  Salinan tersedia di [`public/data/LICENSE-PSF.txt`](public/data/LICENSE-PSF.txt)
  dan di <https://docs.python.org/3/license.html>.
- Sumber: <https://github.com/python/cpython/tree/v3.13.7/Doc> dan
  <https://docs.python.org/3.13/>.
- Kode aplikasi, desain antarmuka, ringkasan bahasa Indonesia, soal latihan,
  dan fitur progres adalah tambahan PyJourney, bukan bagian dari dokumentasi
  resmi. Proyek ini tidak berafiliasi resmi dengan Python Software Foundation.

Materi resmi tetap menjadi rujukan utama. Situs ini untuk belajar, bukan
menggantikan dokumentasi resmi.

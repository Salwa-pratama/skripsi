#!/usr/bin/env python3
"""
Scraper Dataset Bahasa Isyarat SIBI (Kamus SIBI Kemendikdasmen)
URL Sumber: https://pkplk.kemendikdasmen.go.id/sibi/

Struktur folder output mengikuti standar Computer Vision (Label-per-Folder):
dataset/sibi/
├── metadata.json
├── metadata.csv
├── abjad/
│   ├── A/
│   │   └── A.png
│   └── ...
├── angka/
│   ├── 1/
│   │   └── 01.webm
│   └── ...
├── imbuhan/
│   ├── Awalan-Ber/
│   │   └── Awalan-Ber.webm
│   └── ...
└── kata_dasar/
    ├── Makan/
    │   └── Makan.webm
    └── ...
"""

import os
import re
import csv
import json
import time
import string
import argparse
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://pkplk.kemendikdasmen.go.id/sibi/"
DEFAULT_OUTPUT_DIR = os.path.join("dataset", "sibi")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def sanitize_name(name: str) -> str:
    """Membersihkan karakter ilegal untuk nama folder dan file."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean if clean else "unnamed"


def get_encoded_url(url: str) -> str:
    """Meng-encode URL jika terdapat spasi atau karakter non-ASCII."""
    parts = url.split("://", 1)
    if len(parts) == 2:
        scheme, rest = parts
        domain, path = rest.split("/", 1)
        encoded_path = "/".join(quote(unquote(p)) for p in path.split("/"))
        return f"{scheme}://{domain}/{encoded_path}"
    return url


def scrape_abjad(delay: float = 0.3):
    """Mengambil 26 gambar isyarat abjad A-Z."""
    print("\n[+] Mengambil metadata: Abjad (A-Z)...")
    url = f"{BASE_URL}kosakata"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"[-] Gagal mengambil halaman abjad: {e}")
        return []

    items = []
    for div in soup.find_all("div", class_="abjadcss"):
        img = div.find("img")
        overlay = div.find("div", class_="overlayy")
        if img and overlay:
            label = overlay.get_text(strip=True)
            img_url = img.get("src")
            if img_url:
                items.append({
                    "kategori": "abjad",
                    "label": label,
                    "media_url": img_url,
                    "ext": ".png"
                })
    print(f"    Ditemukan {len(items)} huruf abjad.")
    time.sleep(delay)
    return items


def scrape_angka(delay: float = 0.3):
    """Mengambil video angka."""
    print("\n[+] Mengambil metadata: Angka...")
    url = f"{BASE_URL}kosakata/angka"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"[-] Gagal mengambil halaman angka: {e}")
        return []

    items = []
    for col in soup.find_all("div", class_="col-sm-4"):
        video = col.find("video")
        text_elem = col.find("p", class_="topText")
        if video and text_elem:
            src = video.find("source")
            if src and src.get("src"):
                items.append({
                    "kategori": "angka",
                    "label": text_elem.get_text(strip=True),
                    "media_url": src["src"],
                    "ext": ".webm"
                })
    print(f"    Ditemukan {len(items)} video angka.")
    time.sleep(delay)
    return items


def scrape_imbuhan(delay: float = 0.3):
    """Mengambil video imbuhan."""
    print("\n[+] Mengambil metadata: Imbuhan...")
    url = f"{BASE_URL}kosakata/imbuhan"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"[-] Gagal mengambil halaman imbuhan: {e}")
        return []

    items = []
    for col in soup.find_all("div", class_="col-sm-4"):
        video = col.find("video")
        text_elem = col.find("p", class_="topText")
        if video and text_elem:
            src = video.find("source")
            if src and src.get("src"):
                items.append({
                    "kategori": "imbuhan",
                    "label": text_elem.get_text(strip=True),
                    "media_url": src["src"],
                    "ext": ".webm"
                })
    print(f"    Ditemukan {len(items)} video imbuhan.")
    time.sleep(delay)
    return items


def scrape_kata_dasar(letters: str = "abcdefghijklmnopqrstuvwxyz", delay: float = 0.3):
    """Mengambil kata dasar SIBI per awalan huruf via endpoint pencarian."""
    print(f"\n[+] Mengambil metadata: Kata Dasar (Huruf: {letters.upper()})...")
    search_url = f"{BASE_URL}pencarian/pencariankata"
    items = []

    for char in letters.lower():
        if char not in string.ascii_lowercase:
            continue
        print(f"  -> Scraping awalan huruf '{char.upper()}'...", end="", flush=True)
        try:
            resp = requests.post(
                search_url,
                data={"key": char},
                headers=HEADERS,
                timeout=30
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            found = 0
            for col in soup.find_all("div", class_="col-sm-4"):
                video = col.find("video")
                text_elem = col.find("p", class_="topText")
                if video and text_elem:
                    src = video.find("source")
                    if src and src.get("src"):
                        label = text_elem.get_text(strip=True)
                        items.append({
                            "kategori": "kata_dasar",
                            "label": label,
                            "media_url": src["src"],
                            "ext": ".webm"
                        })
                        found += 1
            print(f" ({found} kata)")
        except Exception as e:
            print(f" [GAGAL: {e}]")

        time.sleep(delay)

    print(f"    Total kata dasar ditemukan: {len(items)}")
    return items


def download_media_file(url: str, dest_path: str, max_retries: int = 3) -> bool:
    """Download file streaming dengan auto-skip jika file sudah ada."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        return True

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    target_url = get_encoded_url(url)

    for attempt in range(1, max_retries + 1):
        try:
            with requests.get(target_url, headers=HEADERS, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
            return True
        except Exception as e:
            if attempt == max_retries:
                print(f"\n    [!] Gagal download {url}: {e}")
                if os.path.exists(dest_path):
                    try:
                        os.remove(dest_path)
                    except OSError:
                        pass
                return False
            time.sleep(1.0)
    return False


def extract_frames_from_video(video_path: str, frames_dir: str, fps_sample: int = 5):
    """
    Ekstrak frame dari video jika OpenCV (cv2) terpasang.
    Menghasilkan citra .jpg per frame untuk model computer vision.
    """
    try:
        import cv2
    except ImportError:
        return 0

    if not os.path.exists(video_path):
        return 0

    os.makedirs(frames_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    interval = max(1, int(round(video_fps / fps_sample)))

    frame_count = 0
    saved_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % interval == 0:
            frame_filename = os.path.join(frames_dir, f"frame_{saved_count:04d}.jpg")
            if not os.path.exists(frame_filename):
                cv2.imwrite(frame_filename, frame)
            saved_count += 1
        frame_count += 1

    cap.release()
    return saved_count


def save_metadata(items: list, output_dir: str):
    """Menyimpan manifest metadata ke file JSON dan CSV."""
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "metadata.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    csv_path = os.path.join(output_dir, "metadata.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["kategori", "label", "folder_path", "media_url", "ext"]
        )
        writer.writeheader()
        writer.writerows(items)

    print(f"\n[✓] Metadata berhasil disimpan:")
    print(f"    - JSON: {json_path}")
    print(f"    - CSV : {csv_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Scraper Dataset SIBI (Sistem Isyarat Bahasa Indonesia)"
    )
    parser.add_argument(
        "--category",
        choices=["all", "abjad", "angka", "imbuhan", "kata_dasar"],
        default="all",
        help="Kategori data yang ingin di-scrape (default: all)",
    )
    parser.add_argument(
        "--letters",
        type=str,
        default="abcdefghijklmnopqrstuvwxyz",
        help="Huruf awalan untuk kata_dasar (contoh: --letters ab atau --letters a, default: a-z)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Direktori output dataset (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Hanya scrape daftar metadata/URL tanpa mendownload file media",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="Batasan jumlah file yang diunduh (untuk testing cepat)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Jeda waktu antar request dalam detik (default: 0.3s)",
    )
    parser.add_argument(
        "--extract-frames",
        action="store_true",
        help="Ekstrak video menjadi frame citra .jpg ke dalam folder class (memerlukan opencv)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=5,
        help="Target FPS sampling untuk ekstraksi frame citra (default: 5 fps)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("      SCRAPER DATASET SIBI (KEMENDIKDASMEN)")
    print("=" * 60)
    print(f"Target Kategori : {args.category}")
    print(f"Output Folder   : {args.output_dir}")
    print(f"Download Media  : {'TIDAK (Metadata Only)' if args.metadata_only else 'YA'}")
    if args.extract_frames:
        print(f"Ekstrak Citra   : YA ({args.fps} FPS)")

    items = []
    cat = args.category

    if cat in ["all", "abjad"]:
        items.extend(scrape_abjad(delay=args.delay))

    if cat in ["all", "angka"]:
        items.extend(scrape_angka(delay=args.delay))

    if cat in ["all", "imbuhan"]:
        items.extend(scrape_imbuhan(delay=args.delay))

    if cat in ["all", "kata_dasar"]:
        items.extend(scrape_kata_dasar(letters=args.letters, delay=args.delay))

    if not items:
        print("[!] Tidak ada data yang berhasil dikumpulkan.")
        return

    # Tambahkan path folder standar labeling citra:
    # dataset/sibi/<kategori>/<label_bersih>/<label_bersih><ext>
    for item in items:
        safe_label = sanitize_name(item["label"])
        relative_folder = os.path.join(item["kategori"], safe_label)
        item["folder_path"] = os.path.join(args.output_dir, relative_folder)

    # Simpan manifest/metadata
    save_metadata(items, args.output_dir)

    # Download Media
    if not args.metadata_only:
        download_list = items if args.max_items is None else items[: args.max_items]
        total_dl = len(download_list)

        print(f"\n[+] Memulai pengunduhan {total_dl} file media...")
        print(
            "    Struktur: dataset/sibi/<kategori>/<label>/<nama_file>\n"
        )

        success = 0
        for i, item in enumerate(download_list, 1):
            safe_label = sanitize_name(item["label"])
            file_name = f"{safe_label}{item['ext']}"
            file_path = os.path.join(item["folder_path"], file_name)

            print(
                f"\r[{i}/{total_dl}] Mengunduh: [{item['kategori']}] {item['label']}",
                end="",
                flush=True,
            )

            if download_media_file(item["media_url"], file_path):
                success += 1
                if args.extract_frames and item["ext"] == ".webm":
                    frames_dir = os.path.join(item["folder_path"], "frames")
                    extract_frames_from_video(file_path, frames_dir, fps_sample=args.fps)
            time.sleep(0.05)

        print(f"\n\n[✓] Selesai! Berhasil mengunduh: {success}/{total_dl} file.")
        print(f"    Folder dataset tersimpan di: {os.path.abspath(args.output_dir)}")


if __name__ == "__main__":
    main()

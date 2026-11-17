export type QuestRequirement = {
  chapterSlug: string;
  title: string;
  summary: string;
  instructions: string[];
  starterCode: string;
  hints: string[];
  expectedOutputSnippet?: string;
  requiredNodes: string[];
  nodeExplanations: Record<string, string>;
};

export const quests: Record<string, QuestRequirement> = {
  "variabel-dan-tipe-data": {
    chapterSlug: "variabel-dan-tipe-data",
    title: "Misi 1: Variabel, Operasi Aritmetika & Tipe Data",
    summary:
      "Latihlah pemahaman dasar variabel dan tipe data dengan menghitung luas segitiga dan memeriksa tipe datanya.",
    instructions: [
      "Buat variabel 'alas' dengan nilai 12 (integer).",
      "Buat variabel 'tinggi' dengan nilai 8 (integer).",
      "Hitung 'luas' dengan rumus 0.5 * alas * tinggi.",
      "Cetak hasil luas menggunakan print(luas).",
      "Cetak tipe data dari variabel luas menggunakan print(type(luas)).",
    ],
    starterCode: `# Misi 1: Variabel & Tipe Data
# Ketik kode secara manual (fitur copy-paste dinonaktifkan)

alas = 12
tinggi = 8

# Hitung luas segitiga (0.5 * alas * tinggi)


# Cetak nilai luas dan tipe datanya

`,
    hints: [
      "Gunakan operator * untuk perkalian dan perkalian dengan 0.5 otomatis menghasilkan tipe float.",
      "Fungsi type() digunakan untuk memeriksa tipe objek, contoh: print(type(luas)).",
    ],
    expectedOutputSnippet: "48.0",
    requiredNodes: ["Assign", "BinOp", "Call"],
    nodeExplanations: {
      Assign: "Penetapan nilai ke variabel (assignment)",
      BinOp: "Operasi biner aritmetika (perkalian *)",
      Call: "Pemanggilan fungsi bawaan (print / type)",
    },
  },

  percabangan: {
    chapterSlug: "percabangan",
    title: "Misi 2: Pengambilan Keputusan (if - elif - else)",
    summary:
      "Terapkan logika percabangan untuk mengelompokkan nilai ujian mahasiswa ke dalam predikat huruf.",
    instructions: [
      "Inisialisasi variabel 'skor' bernilai 82.",
      "Gunakan struktur percabangan:",
      "- Jika skor >= 85, cetak 'Nilai: A'",
      "- Jika skor >= 70, cetak 'Nilai: B'",
      "- Selain itu (else), cetak 'Nilai: C'",
    ],
    starterCode: `# Misi 2: Percabangan if - elif - else
# Ketik kode secara manual untuk melatih struktur indentasi Python

skor = 82

# Tulis struktur if, elif, dan else di bawah ini:
if skor >= 85:
    print("Nilai: A")

`,
    hints: [
      "Perhatikan indentasi 4 spasi setelah tanda titik dua (:).",
      "Gunakan elif untuk memeriksa kondisi alternatif kedua.",
    ],
    expectedOutputSnippet: "Nilai: B",
    requiredNodes: ["If", "Compare", "Call"],
    nodeExplanations: {
      If: "Pernyataan kontrol alur percabangan (if)",
      Compare: "Operasi perbandingan (>= atau <=)",
      Call: "Pemanggilan fungsi print() untuk mencetak luaran",
    },
  },

  perulangan: {
    chapterSlug: "perulangan",
    title: "Misi 3: Akumulasi Data dengan Loop for & range",
    summary:
      "Bangun logika pengulangan untuk menjumlahkan deret angka dari 1 sampai 5 secara otomatis.",
    instructions: [
      "Buat variabel akumulator 'total' dengan nilai awal 0.",
      "Gunakan perulangan for dengan fungsi range(1, 6) untuk mengiterasi angka 1 hingga 5.",
      "Di dalam loop, tambahkan setiap angka iterasi ke dalam variabel 'total'.",
      "Setelah loop selesai, cetak hasil 'total'.",
    ],
    starterCode: `# Misi 3: Perulangan for & range
# Ketik secara mandiri tanpa menyalin kode

total = 0

# Tulis loop for menggunakan fungsi range(1, 6):


# Cetak total akumulasi di luar loop

`,
    hints: [
      "Fungsi range(1, 6) menghasilkan angka 1, 2, 3, 4, 5 (angka 6 tidak diikutkan).",
      "Untuk menambahkan ke total, gunakan total = total + i atau total += i.",
    ],
    expectedOutputSnippet: "15",
    requiredNodes: ["For", "Call"],
    nodeExplanations: {
      For: "Pernyataan loop for untuk iterasi data berurutan",
      Call: "Pemanggilan fungsi bawaan range() dan print()",
    },
  },

  fungsi: {
    chapterSlug: "fungsi",
    title: "Misi 4: Pembuatan Modul Fungsi (def & return)",
    summary:
      "Rancanglah sebuah fungsi perhitungan potongan harga belanja yang mengembalikan nilai menggunakan return.",
    instructions: [
      "Definisikan sebuah fungsi bernama 'hitung_diskon' yang menerima dua parameter: 'harga' dan 'persen'.",
      "Hitung nilai potongan: potongan = harga * (persen / 100).",
      "Kembalikan harga akhir setelah dipotong (harga - potongan) menggunakan pernyataan 'return'.",
      "Panggil fungsi tersebut dengan nilai harga 100000 dan diskon 20, lalu cetak hasilnya.",
    ],
    starterCode: `# Misi 4: Fungsi dengan def & return
# Latih pembuatan blok fungsi mandiri

def hitung_diskon(harga, persen):
    # Hitung dan kembalikan nilai harga akhir menggunakan return
    pass

# Panggil fungsi dan cetak hasilnya:

`,
    hints: [
      "Pernyataan return digunakan untuk mengirim kembali hasil olahan fungsi kepada pemanggilnya.",
      "Contoh pemanggilan: hasil = hitung_diskon(100000, 20) lalu print(hasil).",
    ],
    expectedOutputSnippet: "80000",
    requiredNodes: ["FunctionDef", "Return", "Call"],
    nodeExplanations: {
      FunctionDef: "Definisi fungsi baru dengan kata kunci def",
      Return: "Pernyataan pengembalian nilai hasil evaluasi fungsi",
      Call: "Pemanggilan fungsi buatan dan fungsi print",
    },
  },

  "list-dan-dictionary": {
    chapterSlug: "list-dan-dictionary",
    title: "Misi 5: Struktur Data Terstruktur (List & Dictionary)",
    summary:
      "Kelola data koleksi dengan memadukan tipe data List dan Dictionary standar Python.",
    instructions: [
      "Buat dictionary 'mahasiswa' dengan kunci 'nama' bernilai 'Budi' dan kunci 'nilai' berupa list angka [80, 85, 90].",
      "Tambahkan angka 95 ke dalam list nilai menggunakan metode .append().",
      "Hitung banyaknya data nilai menggunakan fungsi len().",
      "Cetak isi dictionary mahasiswa dan jumlah elemen nilainya.",
    ],
    starterCode: `# Misi 5: List & Dictionary
# Ketik struktur data secara manual

mahasiswa = {
    "nama": "Budi",
    "nilai": [80, 85, 90]
}

# Tambahkan nilai 95 ke list dengan .append():


# Cetak dictionary dan jumlah data nilai dengan len():

`,
    hints: [
      "Akses list di dalam dict dengan mahasiswa['nilai'], lalu panggil .append(95).",
      "Gunakan len(mahasiswa['nilai']) untuk menghitung banyaknya nilai.",
    ],
    expectedOutputSnippet: "95",
    requiredNodes: ["Dict", "List", "Call"],
    nodeExplanations: {
      Dict: "Pembuatan koleksi pasangan kunci-nilai (Dictionary)",
      List: "Pembuatan urutan data dinamis (List)",
      Call: "Pemanggilan metode .append(), len(), dan print()",
    },
  },

  "oop-dasar": {
    chapterSlug: "oop-dasar",
    title: "Misi 6: Pemrograman Berorientasi Objek (Class & Object)",
    summary:
      "Pelajari konstruksi dasar objek dengan membuat kelas, inisialisasi atribut __init__, dan metode objek.",
    instructions: [
      "Definisikan kelas bernama 'Robot'.",
      "Buat konstruktor __init__(self, nama) yang menyimpan parameter ke atribut self.nama.",
      "Buat metode 'sapa(self)' yang mencetak teks 'Halo, saya ' + self.nama.",
      "Instansiasi objek r = Robot('Alpha') lalu panggil r.sapa().",
    ],
    starterCode: `# Misi 6: Class & Object Dasar
# Ketik definisi class secara manual

class Robot:
    def __init__(self, nama):
        self.nama = nama

    def sapa(self):
        print(f"Halo, saya {self.nama}")

# Buat objek dan panggil metodenya:

`,
    hints: [
      "Self merujuk ke instans objek saat ini.",
      "Panggil metode sapa dengan r.sapa() setelah membuat objek.",
    ],
    expectedOutputSnippet: "Halo, saya",
    requiredNodes: ["ClassDef", "FunctionDef", "Call"],
    nodeExplanations: {
      ClassDef: "Pernyataan pendefinisian kelas baru (class)",
      FunctionDef: "Pernyataan metode di dalam kelas (__init__ dan sapa)",
      Call: "Instansiasi kelas dan pemanggilan metode",
    },
  },

  "oop-lanjutan": {
    chapterSlug: "oop-lanjutan",
    title: "Misi 7: Pewarisan Objek (Inheritance & Super)",
    summary:
      "Terapkan konsep pewarisan kelas turunan dari kelas induk menggunakan pemanggilan super().",
    instructions: [
      "Buat kelas induk 'Kendaraan' dengan metode bergerak(self) yang mencetak 'Kendaraan bergerak'.",
      "Buat kelas turunan 'Mobil' yang mewarisi 'Kendaraan'.",
      "Di dalam kelas Mobil, buat metode bergerak(self) yang memanggil super().bergerak() dan mencetak 'Mobil melaju cepat'.",
      "Buat objek m = Mobil() dan panggil m.bergerak().",
    ],
    starterCode: `# Misi 7: OOP Lanjutan - Inheritance
# Ketik secara mandiri

class Kendaraan:
    def bergerak(self):
        print("Kendaraan bergerak")

class Mobil(Kendaraan):
    def bergerak(self):
        super().bergerak()
        print("Mobil melaju cepat")

# Instansiasi objek dan panggil metodenya:

`,
    hints: [
      "Sintaks inheritance: class Anak(Induk):",
      "super() digunakan untuk memanggil implementasi dari kelas induk.",
    ],
    expectedOutputSnippet: "Mobil melaju cepat",
    requiredNodes: ["ClassDef", "FunctionDef", "Call"],
    nodeExplanations: {
      ClassDef: "Pendefinisian kelas pewarisan",
      FunctionDef: "Definisi metode override",
      Call: "Pemanggilan super() dan fungsi eksekusi",
    },
  },
};

export function getQuest(chapterSlug: string): QuestRequirement | undefined {
  return quests[chapterSlug];
}

import type { QuizQuestion } from "./types";

export const quizzes: Record<string, QuizQuestion[]> = {
  "variabel-dan-tipe-data": [
    {
      question: "Nilai 3.14 memiliki tipe data apa?",
      options: ["int", "float", "str", "bool"],
      answer: 1,
      explanation:
        "Angka dengan titik desimal adalah float. int untuk bilangan bulat, str untuk teks, dan bool untuk True/False.",
    },
    {
      question: "Apa hasil dari 10 // 3?",
      options: ["3", "3.33", "1", "4"],
      answer: 0,
      explanation:
        "// adalah floor division: hasil pembagian dibulatkan ke bawah. 10 / 3 = 3.33, sehingga 10 // 3 = 3.",
    },
    {
      question: "Nilai mana yang dianggap falsy oleh Python?",
      options: ['"0"', "[]", "[0]", '"False"'],
      answer: 1,
      explanation:
        "List kosong [] dianggap falsy. String non-kosong seperti \"0\" dan \"False\" tetap truthy.",
    },
  ],
  percabangan: [
    {
      question: "Keyword apa yang dipakai untuk cabang alternatif setelah if?",
      options: ["else if", "elif", "elseif", "otherwise"],
      answer: 1,
      explanation:
        "Python memakai elif, bukan else if. Rantai if/elif/else dievaluasi dari atas ke bawah.",
    },
    {
      question: "Apa yang menentukan batas blok kode di Python?",
      options: ["Kurung kurawal", "Indentasi", "Titik koma", "begin dan end"],
      answer: 1,
      explanation:
        "Python memakai indentasi untuk menentukan blok. Baris yang sejajar indentasinya berada dalam blok yang sama.",
    },
    {
      question:
        "Apa output dari kode ini?\n\nx = 7\nif x % 2 == 0:\n    print('genap')\nelse:\n    print('ganjil')",
      options: ["genap", "ganjil", "Error", "Tidak ada output"],
      answer: 1,
      explanation:
        "7 % 2 menghasilkan 1, jadi kondisi x % 2 == 0 bernilai False dan cabang else dijalankan.",
    },
  ],
  perulangan: [
    {
      question: "Fungsi apa yang biasanya dipakai untuk menghasilkan urutan angka pada for?",
      options: ["range()", "len()", "print()", "int()"],
      answer: 0,
      explanation:
        "range(start, stop, step) menghasilkan urutan angka. Nilai stop tidak ikut dihasilkan.",
    },
    {
      question: "Apa fungsi dari break di dalam loop?",
      options: [
        "Menghentikan loop terdekat",
        "Melewati satu iterasi",
        "Mengulang loop dari awal",
        "Keluar dari program",
      ],
      answer: 0,
      explanation:
        "break langsung keluar dari loop terdekat. Untuk melewati satu iterasi saja, gunakan continue.",
    },
    {
      question: "Berapa kali print(i) dijalankan oleh for i in range(1, 5)?",
      options: ["3 kali", "4 kali", "5 kali", "6 kali"],
      answer: 1,
      explanation:
        "range(1, 5) menghasilkan 1, 2, 3, 4 — empat nilai. Angka 5 tidak termasuk.",
    },
  ],
  fungsi: [
    {
      question: "Keyword apa yang dipakai untuk mendefinisikan fungsi?",
      options: ["func", "def", "function", "lambda"],
      answer: 1,
      explanation:
        "Fungsi didefinisikan dengan def nama_fungsi(parameter):. lambda membuat fungsi anonim, bukan definisi bernama.",
    },
    {
      question: "Apa yang dikembalikan fungsi yang tidak memiliki return?",
      options: ["None", "0", '""', "Error"],
      answer: 0,
      explanation:
        "Jika tidak ada return, Python mengembalikan None secara implisit.",
    },
    {
      question: "Apa itu parameter default?",
      options: [
        "Parameter yang punya nilai cadangan jika argumen tidak diberikan",
        "Parameter yang wajib diisi",
        "Parameter yang hanya bisa dipakai sebagai keyword",
        "Parameter yang tidak bisa diubah",
      ],
      answer: 0,
      explanation:
        "Contoh: def halo(nama='Dunia'). Jika pemanggil tidak memberi argumen, nilai 'Dunia' dipakai.",
    },
  ],
  "list-dan-dictionary": [
    {
      question: "Method apa yang menambahkan satu item ke akhir list?",
      options: ["append()", "add()", "push()", "insert()"],
      answer: 0,
      explanation:
        "list.append(x) menambahkan x ke akhir list. add() dipakai oleh set, sedangkan insert() butuh indeks.",
    },
    {
      question: "Bagaimana cara mengakses nilai dengan key 'nama' pada dict data?",
      options: ["data.nama", "data['nama']", "data(0)", "data->nama"],
      answer: 1,
      explanation:
        "Dictionary diakses dengan tanda kurung siku dan key-nya: data['nama']. Gunakan data.get('nama') jika key mungkin tidak ada.",
    },
    {
      question: "Apa hasil dari len({'a': 1, 'b': 2})?",
      options: ["1", "2", "3", "Error"],
      answer: 1,
      explanation:
        "len() pada dictionary menghitung jumlah pasangan key-value. Ada dua key, jadi hasilnya 2.",
    },
  ],
};

export function getQuiz(slug: string): QuizQuestion[] {
  return quizzes[slug] ?? [];
}

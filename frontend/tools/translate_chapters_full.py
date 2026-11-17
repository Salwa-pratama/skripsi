#!/usr/bin/env python3
"""Penerjemah komprehensif seluruh bab kurikulum PyJourney ke Bahasa Indonesia.
Memetakan teks paragraf, heading, dan penjelasan sesuai standar PSF python-docs-id.
"""

import json
from pathlib import Path
from translations_data import HEADINGS, SOURCE_LABELS

ROOT = Path(__file__).resolve().parents[1]
CHAPTERS_DIR = ROOT / "content" / "generated" / "chapters"

PARAGRAPH_TRANSLATIONS = {
    # -------------------------------------------------------------------------
    # 1. VARIABEL DAN TIPE DATA
    # -------------------------------------------------------------------------
    "The interpreter acts as a simple calculator": (
        "Interpreter bertindak sebagai kalkulator sederhana: Anda dapat mengetikkan ekspresi "
        "kepadanya dan interpreter akan menampilkan nilainya. Sintaksis ekspresi sangat lugas: operator "
        "<code>+</code>, <code>-</code>, <code>*</code>, dan <code>/</code> dapat digunakan untuk melakukan "
        "aritmetika; tanda kurung (<code>()</code>) dapat digunakan untuk pengelompokan operasi. Sebagai contoh:"
    ),
    "The integer numbers (e.g.": (
        "Bilangan bulat (contohnya <code>2</code>, <code>4</code>, <code>20</code>) memiliki tipe "
        "<a href=\"https://docs.python.org/3.13/library/functions.html#int\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"int\"><code>int</code></a>, "
        "sedangkan bilangan dengan bagian pecahan (contohnya <code>5.0</code>, <code>1.6</code>) memiliki tipe "
        "<a href=\"https://docs.python.org/3.13/library/functions.html#float\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"float\"><code>float</code></a>. "
        "Kita akan mempelajari lebih lanjut mengenai tipe numerik di bagian berikutnya."
    ),
    "Division (<code>/</code>) always returns a float": (
        "Operasi pembagian (<code>/</code>) selalu mengembalikan bilangan float. Untuk melakukan "
        "<a href=\"https://docs.python.org/3.13/glossary.html#term-floor-division\" rel=\"noopener noreferrer\" target=\"_blank\">floor division</a> dan "
        "mendapatkan hasil bilangan bulat (dibulatkan ke bawah), Anda dapat menggunakan operator <code>//</code>; "
        "sedangkan untuk menghitung sisa bagi (modulus), gunakan operator <code>%</code>:"
    ),
    "With Python, it is possible to use the <code>**</code> operator": (
        "Dengan Python, Anda dapat menggunakan operator <code>**</code> untuk menghitung perpangkatan:"
    ),
    "The equal sign (<code>=</code>) is used to assign a value": (
        "Tanda sama dengan (<code>=</code>) digunakan untuk menetapkan nilai ke suatu variabel. "
        "Setelah penetapan nilai, tidak ada hasil yang ditampilkan sebelum prompt interaktif berikutnya:"
    ),
    "If a variable is not “defined”": (
        "Jika sebuah variabel belum didefinisikan (belum diberi nilai awal), mencoba menggunakannya "
        "akan memunculkan pesan kesalahan (error):"
    ),
    "There is full support for floating point": (
        "Terdapat dukungan penuh untuk bilangan pecahan (floating point); operator dengan operan campuran "
        "akan mengonversi operan integer ke floating point secara otomatis:"
    ),
    "In interactive mode, the last printed expression": (
        "Dalam mode interaktif, ekspresi terakhir yang dicetak secara otomatis dimasukkan ke dalam variabel <code>_</code>. "
        "Ini memudahkan saat Anda menggunakan Python sebagai kalkulator meja:"
    ),
    "This variable should be treated as read-only": (
        "Variabel ini harus diperlakukan sebagai hanya-baca (read-only) oleh pengguna. Jangan secara eksplisit "
        "menetapkan nilai padanya — Anda akan membuat variabel lokal independen dengan nama sama yang menutupi perilaku bawaan."
    ),
    "In addition to <a href=\"https://docs.python.org/3.13/library/functions.html#int\"": (
        "Selain tipe <a href=\"https://docs.python.org/3.13/library/functions.html#int\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"int\"><code>int</code></a> "
        "dan <a href=\"https://docs.python.org/3.13/library/functions.html#float\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"float\"><code>float</code></a>, "
        "Python juga mendukung tipe angka lain seperti <a href=\"https://docs.python.org/3.13/library/decimal.html#decimal.Decimal\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"decimal.Decimal\"><code>Decimal</code></a> "
        "dan <a href=\"https://docs.python.org/3.13/library/fractions.html#fractions.Fraction\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"fractions.Fraction\"><code>Fraction</code></a>, "
        "serta bilangan kompleks."
    ),
    "Python can manipulate text (represented by type": (
        "Python dapat memanipulasi teks (diwakili oleh tipe "
        "<a href=\"https://docs.python.org/3.13/library/stdtypes.html#str\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"str\"><code>str</code></a>, "
        "yang disebut sebagai \"string\"). Ini mencakup karakter, simbol, dan kata yang diapit oleh tanda petik tunggal "
        "(<code>'...'</code>) atau tanda petik ganda (<code>\"...\"</code>) dengan hasil yang ekuivalen:"
    ),
    "To quote a quote, we need to “escape” it": (
        "Untuk memasukkan tanda petik di dalam string yang berpetik sama, kita perlu melakukan \"escape\" "
        "dengan menambahkan garis miring terbalik (<code>\\</code>) sebelumnya. Atau alternatifnya, gunakan tanda petik jenis lainnya:"
    ),
    "In the Python shell, the string definition and output": (
        "Pada terminal interaktif Python, tampilan definisi string dan luaran string dapat berbeda. Fungsi "
        "<a href=\"https://docs.python.org/3.13/library/functions.html#print\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"print\"><code>print()</code></a> "
        "menghasilkan tampilan luaran yang lebih rapi dan mudah dibaca, dengan menghilangkan tanda petik pembungkus dan mencetak karakter escape seperti baris baru:"
    ),
    "If you don’t want characters prefaced by <code>\\</code>": (
        "Jika Anda tidak ingin karakter berawalan <code>\\</code> diinterpretasikan sebagai karakter khusus (seperti <code>\\n</code>), "
        "Anda dapat menggunakan <em>raw strings</em> dengan menambahkan huruf <code>r</code> sebelum tanda petik pembuka:"
    ),
    "There is one subtle aspect to raw strings": (
        "Ada satu aspek halus pada raw strings: raw string tidak boleh berakhiran dengan jumlah karakter ganjil dari garis miring terbalik <code>\\</code>."
    ),
    "String literals can span multiple lines": (
        "Literal string dapat membentang di beberapa baris. Salah satu caranya adalah menggunakan tanda petik tiga "
        "(<code>\"\"\"...\"\"\"</code> atau <code>'''...'''</code>). Akhir baris otomatis disertakan kecuali jika diakhiri dengan <code>\\</code>:"
    ),
    "Strings can be concatenated (glued together)": (
        "String dapat digabungkan (dilekatkan bersama) dengan operator <code>+</code>, dan diulang dengan operator <code>*</code>:"
    ),
    "Two or more <em>string literals</em>": (
        "Dua atau lebih <em>literal string</em> (yang diapit tanda petik) yang diletakkan berdampingan akan "
        "digabungkan secara otomatis oleh interpreter:"
    ),
    "This feature is particularly useful when you want to break long strings": (
        "Fitur penggabungan otomatis ini sangat berguna saat Anda ingin memecah baris teks string yang panjang ke beberapa baris kode agar rapi:"
    ),
    "This only works with two literals though": (
        "Namun perlu diingat, cara ini hanya berlaku pada dua literal string langsung, bukan pada variabel atau ekspresi:"
    ),
    "If you want to concatenate variables or a variable and a literal": (
        "Jika Anda ingin menggabungkan variabel dengan variabel lain atau variabel dengan literal, gunakan operator <code>+</code>:"
    ),
    "Strings can be <em>indexed</em> (subscripted)": (
        "Karakter dalam string dapat diakses menggunakan indeks (subscript), dengan karakter pertama memiliki indeks <code>0</code>. "
        "Tidak ada tipe data karakter terpisah di Python; sebuah karakter hanyalah string berpanjang satu:"
    ),
    "Indices may also be negative numbers": (
        "Indeks juga dapat berupa bilangan negatif, untuk memulai perhitungan dari sisi kanan string:"
    ),
    "Note that since -0 is the same as 0": (
        "Perhatikan bahwa karena -0 bernilai sama dengan 0, indeks negatif dimulai dari -1 (karakter terakhir)."
    ),
    "In addition to indexing, <em>slicing</em> is also supported": (
        "Selain pengindeksan tunggal, pemotongan (<em>slicing</em>) juga didukung. Jika pengindeksan digunakan "
        "untuk mengambil karakter tunggal, pemotongan memungkinkan Anda memperoleh substring (bagian string):"
    ),
    "Slice indices have useful defaults": (
        "Indeks pemotongan memiliki nilai default yang praktis; jika indeks pertama diabaikan maka otomatis dianggap 0, "
        "dan jika indeks kedua diabaikan maka otomatis dianggap sepanjang string:"
    ),
    "Note how the start is always included": (
        "Perhatikan bagaimana batas awal selalu disertakan, sedangkan batas akhir selalu dikecualikan. "
        "Hal ini memastikan bahwa <code>s[:i] + s[i:]</code> selalu bernilai sama dengan <code>s</code>:"
    ),
    "One way to remember how slices work": (
        "Cara mudah mengingat cara kerja pemotongan adalah dengan membayangkan indeks menunjuk ke batas *di antara* karakter, "
        "dengan batas kiri karakter pertama bernilai 0 dan batas kanan karakter terakhir bernilai n:"
    ),
    "The first row of numbers gives the position of the indices": (
        "Baris angka pertama menunjukkan posisi indeks 0…6 pada string; baris kedua menunjukkan indeks negatif yang bersesuaian."
    ),
    "For non-negative indices, the length of a slice is the difference": (
        "Untuk indeks non-negatif, panjang dari potongan string adalah selisih antara kedua indeks tersebut. "
        "Sebagai contoh, panjang dari <code>word[1:3]</code> adalah 2."
    ),
    "Attempting to use an index that is too large": (
        "Mencoba mengakses indeks yang berada di luar rentang string (terlalu besar) akan menghasilkan pesan kesalahan <code>IndexError</code>:"
    ),
    "However, out of range slice indexes are handled gracefully": (
        "Namun, indeks pemotongan (slice) yang berada di luar jangkauan ditangani dengan toleran dan anggun saat digunakan untuk slicing:"
    ),
    "Python strings cannot be changed — they are": (
        "String pada Python tidak dapat diubah nilainya setelah dibuat — mereka bersifat "
        "<a href=\"https://docs.python.org/3.13/glossary.html#term-immutable\" rel=\"noopener noreferrer\" target=\"_blank\">immutable (tidak dapat diubah)</a>. "
        "Menetapkan nilai baru ke suatu posisi indeks string akan menghasilkan <code>TypeError</code>:"
    ),
    "If you need a different string, you should create a new one": (
        "Jika Anda membutuhkan string dengan konten berbeda, Anda harus membuat objek string baru:"
    ),
    "The built-in function <a href=\"https://docs.python.org/3.13/library/functions.html#len\"": (
        "Fungsi bawaan <a href=\"https://docs.python.org/3.13/library/functions.html#len\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"len\"><code>len()</code></a> "
        "mengembalikan panjang (jumlah karakter) dari sebuah string:"
    ),
    "Any object can be tested for truth value": (
        "Objek apa pun di Python dapat diuji nilai kebenarannya (truth value testing), untuk digunakan dalam kondisi pernyataan "
        "<a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#if\" rel=\"noopener noreferrer\" target=\"_blank\"><code>if</code></a> atau "
        "<a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#while\" rel=\"noopener noreferrer\" target=\"_blank\"><code>while</code></a>, "
        "atau sebagai operan dari operasi Boolean."
    ),
    "By default, an object is considered true": (
        "Secara default, suatu objek dianggap bernilai benar (True) kecuali jika kelasnya mengembalikan False saat diuji. "
        "Berikut adalah nilai-nilai bawaan yang dianggap salah (Falsy) oleh Python: konstanta <code>None</code> dan <code>False</code>, "
        "angka nol dalam berbagai tipe numerik (<code>0</code>, <code>0.0</code>), serta urutan dan koleksi kosong (<code>''</code>, <code>()</code>, <code>[]</code>, <code>{}</code>)."
    ),
    "Operations and built-in functions that have a Boolean result": (
        "Operasi dan fungsi bawaan yang menghasilkan nilai Boolean selalu mengembalikan <code>0</code> atau <code>False</code> untuk kondisi salah, "
        "serta <code>1</code> atau <code>True</code> untuk kondisi benar, kecuali dinyatakan lain."
    ),
    "These are the Boolean operations, ordered by ascending priority": (
        "Berikut adalah operasi logika Boolean di Python, diurutkan berdasarkan prioritas pengerjaan terendah ke tertinggi:"
    ),
    "There are eight comparison operations in Python": (
        "Terdapat delapan operasi perbandingan di Python. Semuanya memiliki prioritas yang sama (lebih tinggi dari operasi Boolean dan lebih rendah dari aritmetika):"
    ),
    "This table summarizes the comparison operations": (
        "Tabel berikut merangkum operator perbandingan yang tersedia di Python:"
    ),
    "Objects of different types, except different numeric types, never compare equal": (
        "Objek dari tipe yang berbeda (kecuali tipe numerik berbeda seperti integer dan float yang setara) tidak pernah bernilai sama saat dibandingkan."
    ),
    "Non-identical instances of a class normally compare as non-equal": (
        "Instans yang berbeda dari suatu kelas biasanya dibandingkan sebagai tidak sama kecuali jika kelas tersebut mengimplementasikan metode perbandingan khusus."
    ),
    "Instances of a class cannot be ordered with respect to other instances": (
        "Instans dari suatu kelas tidak dapat diurutkan terhadap instans lain dari kelas yang sama kecuali kelas tersebut mendefinisikan metode perbandingan terurut (seperti <code>__lt__</code>)."
    ),
    "Two more operations with the same syntactic priority": (
        "Dua operasi lainnya dengan prioritas sintaksis yang sama adalah <a href=\"https://docs.python.org/3.13/reference/expressions.html#in\" rel=\"noopener noreferrer\" target=\"_blank\"><code>in</code></a> "
        "dan <a href=\"https://docs.python.org/3.13/reference/expressions.html#not-in\" rel=\"noopener noreferrer\" target=\"_blank\"><code>not in</code></a>, "
        "yang didukung oleh tipe-tipe urutan (sequence) dan pemetaan (mapping)."
    ),
    "There are three distinct numeric types: <em>integers</em>": (
        "Terdapat tiga tipe numerik yang berbeda di Python: <em>integers (bilangan bulat)</em>, "
        "<em>floating point numbers (bilangan pecahan)</em>, dan <em>complex numbers (bilangan kompleks)</em>."
    ),
    "Numbers are created by numeric literals or as the result of built-in functions": (
        "Bilangan dibuat melalui penulisan literal angka secara langsung atau sebagai hasil dari pemanggilan fungsi bawaan dan operator aritmetika."
    ),
    "Python fully supports mixed arithmetic": (
        "Python sepenuhnya mendukung aritmetika campuran: saat operator biner melibatkan operan dengan tipe numerik berbeda, "
        "operan dengan tipe lebih sempit otomatis diperluas ke tipe yang lebih luas (misal int otomatis dikonversi ke float)."
    ),
    "The constructors <a href=\"https://docs.python.org/3.13/library/functions.html#int\"": (
        "Konstruktor <a href=\"https://docs.python.org/3.13/library/functions.html#int\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"int\"><code>int()</code></a> "
        "dan <a href=\"https://docs.python.org/3.13/library/functions.html#float\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"float\"><code>float()</code></a> "
        "dapat digunakan untuk membuat angka dari tipe data lain, seperti mengonversi teks string angka menjadi nilai numerik murni."
    ),
    "All numeric types (except complex) support the following operations": (
        "Semua tipe numerik (kecuali kompleks) mendukung operasi standar berikut (diurutkan berdasarkan prioritas pengerjaan menaik):"
    ),
    "Booleans represent truth values": (
        "Tipe Boolean merepresentasikan nilai kebenaran. Tipe "
        "<a href=\"https://docs.python.org/3.13/library/functions.html#bool\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"bool\"><code>bool</code></a> "
        "adalah subkelas dari integer, dengan dua nilai instans konstan: <code>True</code> dan <code>False</code>."
    ),
    "The built-in function <a href=\"https://docs.python.org/3.13/library/functions.html#bool\"": (
        "Fungsi bawaan <a href=\"https://docs.python.org/3.13/library/functions.html#bool\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"bool\"><code>bool()</code></a> "
        "mengonversi nilai apa pun menjadi nilai kebenaran Boolean menggunakan prosedur standar pengujian nilai kebenaran."
    ),
    "For logical operations, use the <a href=\"https://docs.python.org/3.13/library/stdtypes.html#boolean-operations-and-or-not\"": (
        "Untuk operasi logika, gunakan operator Boolean <code>and</code>, <code>or</code>, dan <code>not</code>."
    ),

    # -------------------------------------------------------------------------
    # 2. PERCABANGAN
    # -------------------------------------------------------------------------
    "Perhaps the most well-known statement type is the <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#if\"": (
        "Mungkin jenis pernyataan yang paling dikenal luas adalah pernyataan "
        "<a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#if\" rel=\"noopener noreferrer\" target=\"_blank\"><code>if</code></a>. Sebagai contoh:"
    ),
    "There can be zero or more <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#elif\"": (
        "Dapat terdapat nol atau lebih bagian <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#elif\" rel=\"noopener noreferrer\" target=\"_blank\"><code>elif</code></a>, "
        "dan bagian <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#else\" rel=\"noopener noreferrer\" target=\"_blank\"><code>else</code></a> bersifat opsional. "
        "Kata kunci '<code>elif</code>' merupakan singkatan dari 'else if', dan berguna untuk menghindari indentasi berlebih. "
        "Rangkaian <code>if</code> … <code>elif</code> … <code>elif</code> … bertindak sebagai pengganti pernyataan <code>switch</code> atau <code>case</code> yang ada di bahasa lain."
    ),
    "If you’re comparing the same value to several constants": (
        "Jika Anda membandingkan nilai yang sama dengan beberapa konstanta atau memeriksa tipe data tertentu, "
        "pernyataan <code>match</code> juga dapat digunakan. Rincian selengkapnya dapat dilihat pada dokumentasi match statements."
    ),
    "The <code>pass</code> statement does nothing": (
        "Pernyataan <code>pass</code> tidak melakukan tindakan apa pun. Pernyataan ini digunakan saat suatu pernyataan dibutuhkan secara sintaksis "
        "tetapi program tidak memerlukan aksi apa pun. Sebagai contoh:"
    ),
    "This is commonly used for creating minimal classes": (
        "Pernyataan ini umumnya digunakan untuk membuat kerangka kelas minimal:"
    ),
    "Another place <code>pass</code> can be used is as a place-holder": (
        "Tempat lain penggunaan <code>pass</code> adalah sebagai penampung sementara (place-holder) untuk badan fungsi atau blok percabangan "
        "saat Anda merancang kode baru, memungkinkan Anda berpikir pada level abstraksi yang lebih tinggi tanpa memicu SyntaxError:"
    ),
    "The <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#if\" rel=\"noopener noreferrer\" target=\"_blank\"><code>if</code></a> statement is used for conditional execution": (
        "Pernyataan <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#if\" rel=\"noopener noreferrer\" target=\"_blank\"><code>if</code></a> "
        "digunakan untuk eksekusi kode kondisional berdasarkan pemenuhan syarat tertentu:"
    ),
    "It selects exactly one of the suites by evaluating the expressions": (
        "Pernyataan ini memilih tepat satu blok kode (suite) dengan mengevaluasi ekspresi kondisi satu per satu "
        "hingga ditemukan kondisi yang bernilai benar (True). Blok kode tersebut kemudian dieksekusi. "
        "Jika seluruh ekspresi bernilai salah (False), blok klausa <code>else</code> (jika ada) yang akan dijalankan."
    ),
    "Unlike C, all comparison operations in Python have the same priority": (
        "Berbeda dengan bahasa C, semua operasi perbandingan di Python memiliki prioritas yang sama, "
        "yaitu lebih rendah daripada operasi aritmetika dan pergeseran bit. Selain itu, ekspresi seperti <code>a &lt; b &lt; c</code> "
        "memiliki interpretasi berantai seperti dalam matematika formal:"
    ),
    "Comparisons yield boolean values: <code>True</code> or <code>False</code>": (
        "Operasi perbandingan menghasilkan nilai boolean: <code>True</code> atau <code>False</code>. "
        "Metode perbandingan khusus dapat mengembalikan nilai lain, di mana Python akan memanggil fungsi <code>bool()</code> dalam konteks Boolean."
    ),
    "Comparisons can be chained arbitrarily": (
        "Perbandingan dapat dirangkai secara berantai: contohnya <code>x &lt; y &lt;= z</code> ekuivalen dengan "
        "<code>x &lt; y and y &lt;= z</code>, di mana <code>y</code> hanya dievaluasi satu kali saja."
    ),
    "Formally, if <em>a</em>, <em>b</em>, <em>c</em>": (
        "Secara formal, jika <em>a</em>, <em>b</em>, <em>c</em> adalah ekspresi dan <em>op1</em>, <em>op2</em> adalah operator perbandingan, "
        "maka <code>a op1 b op2 c</code> ekuivalen dengan <code>a op1 b and b op2 c</code>."
    ),
    "Note that <code>a op1 b op2 c</code> doesn’t imply any kind of comparison": (
        "Perhatikan bahwa <code>a op1 b op2 c</code> tidak menyiratkan perbandingan langsung antara <em>a</em> dan <em>c</em>; "
        "sehingga ekspresi seperti <code>x &lt; y &gt; z</code> secara sintaksis valid di Python."
    ),
    "The operators <code>&lt;</code>, <code>&gt;</code>, <code>==</code>": (
        "Operator <code>&lt;</code>, <code>&gt;</code>, <code>==</code>, <code>&gt;=</code>, <code>&lt;=</code>, dan <code>!=</code> "
        "membandingkan nilai dari dua buah objek. Objek-objek tersebut tidak harus memiliki tipe data yang sama."
    ),
    "Chapter <a href=\"https://docs.python.org/3.13/reference/datamodel.html#objects\"": (
        "Bab Objek, nilai, dan tipe menyatakan bahwa setiap objek di Python memiliki nilai, tipe, dan identitas unik di memori."
    ),
    "Because all types are (direct or indirect) subtypes of <a href=\"https://docs.python.org/3.13/library/functions.html#object\"": (
        "Karena semua tipe adalah subtipe dari <code>object</code>, mereka mewarisi perilaku perbandingan default dari <code>object</code>."
    ),
    "The default behavior for equality comparison": (
        "Perilaku default perbandingan kesetaraan (<code>==</code> dan <code>!=</code>) didasarkan pada identitas objek di memori."
    ),
    "A default order comparison (<code>&lt;</code>, <code>&gt;</code>, <code>&lt;=</code>, and <code>&gt;=</code>) is not provided": (
        "Perbandingan urutan default (<code>&lt;</code>, <code>&gt;</code>, <code>&lt;=</code>, <code>&gt;=</code>) tidak disediakan secara bawaan; "
        "mencobanya pada objek acak akan memicu <code>TypeError</code>."
    ),
    "For the string and bytes types, <code>x in y</code> is <code>True</code>": (
        "Untuk tipe string dan bytes, <code>x in y</code> bernilai <code>True</code> jika dan hanya jika <em>x</em> merupakan substring dari <em>y</em>. "
        "String kosong <code>\"\"</code> selalu dianggap sebagai substring dari string apa pun."
    ),
    "For user-defined classes which define the <a href=\"https://docs.python.org/3.13/reference/datamodel.html#object.__contains__\"": (
        "Untuk kelas kustom yang mendefinisikan metode <code>__contains__()</code>, ekspresi <code>x in y</code> bernilai <code>True</code> "
        "jika <code>y.__contains__(x)</code> mengembalikan nilai benar."
    ),
    "The operator <a href=\"https://docs.python.org/3.13/reference/expressions.html#not-in\"": (
        "Operator <a href=\"https://docs.python.org/3.13/reference/expressions.html#not-in\" rel=\"noopener noreferrer\" target=\"_blank\"><code>not in</code></a> "
        "didefinisikan memiliki nilai kebenaran terbalik dari operator <code>in</code>."
    ),
    "The operators <a href=\"https://docs.python.org/3.13/reference/expressions.html#is\"": (
        "Operator <a href=\"https://docs.python.org/3.13/reference/expressions.html#is\" rel=\"noopener noreferrer\" target=\"_blank\"><code>is</code></a> "
        "dan <code>is not</code> menguji identitas objek: <code>x is y</code> bernilai benar jika dan hanya jika <code>x</code> dan <code>y</code> "
        "merupakan objek fisik yang sama persis di memori (memiliki nilai <a href=\"https://docs.python.org/3.13/library/functions.html#id\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"id\"><code>id()</code></a> identik)."
    ),
    "In the context of Boolean operations, and also when expressions are used by control flow statements": (
        "Dalam konteks operasi Boolean dan struktur kontrol alur program, nilai berikut diinterpretasikan sebagai salah (False): "
        "<code>False</code>, <code>None</code>, nilai nol dari seluruh tipe numerik, serta string dan kontainer kosong. "
        "Seluruh nilai lainnya dianggap bernilai benar (True)."
    ),
    "The operator <a href=\"https://docs.python.org/3.13/reference/expressions.html#not\"": (
        "Operator <a href=\"https://docs.python.org/3.13/reference/expressions.html#not\" rel=\"noopener noreferrer\" target=\"_blank\"><code>not</code></a> "
        "menghasilkan <code>True</code> jika argumennya bernilai salah, dan sebaliknya menghasilkan <code>False</code>."
    ),
    "The expression <code>x and y</code> first evaluates": (
        "Ekspresi <code>x and y</code> pertama-tama mengevaluasi <em>x</em>; jika <em>x</em> bernilai salah, nilainya langsung dikembalikan; "
        "jika tidak, <em>y</em> dievaluasi dan hasilnya dikembalikan."
    ),
    "The expression <code>x or y</code> first evaluates": (
        "Ekspresi <code>x or y</code> pertama-tama mengevaluasi <em>x</em>; jika <em>x</em> bernilai benar, nilainya langsung dikembalikan; "
        "jika tidak, <em>y</em> dievaluasi dan hasilnya dikembalikan."
    ),
    "Note that neither <a href=\"https://docs.python.org/3.13/reference/expressions.html#and\"": (
        "Perhatikan bahwa baik <code>and</code> maupun <code>or</code> tidak membatasi nilai kembali pada <code>True</code> dan <code>False</code> literal, "
        "melainkan mengembalikan argumen terakhir yang dievaluasi."
    ),
    "Conditional expressions (sometimes called a “ternary operator”)": (
        "Ekspresi kondisional (sering disebut sebagai \"operator ternary\") memiliki bentuk <code>x if C else y</code>. "
        "Pertama-tama kondisi <em>C</em> dievaluasi; jika benar, nilai <em>x</em> dikembalikan; jika salah, nilai <em>y</em> yang dikembalikan."
    ),
    "The expression <code>x if C else y</code> first evaluates the condition": (
        "Ekspresi <code>x if C else y</code> pertama-tama mengevaluasi kondisi <em>C</em>. Jika <em>C</em> bernilai benar, "
        "<em>x</em> dievaluasi dan nilainya dikembalikan; jika tidak, <em>y</em> dievaluasi dan nilainya dikembalikan."
    ),

    # -------------------------------------------------------------------------
    # 3. PERULANGAN
    # -------------------------------------------------------------------------
    "Of course, we can use Python for more complicated tasks": (
        "Tentu saja, kita dapat menggunakan Python untuk tugas yang lebih kompleks daripada sekadar penjumlahan aritmetika. "
        "Sebagai contoh, kita dapat menulis deret awal dari deret Fibonacci menggunakan perulangan <code>while</code>:"
    ),
    "This example introduces several new features": (
        "Contoh ini memperkenalkan beberapa fitur penting: penugasan ganda pada satu baris (<code>a, b = 0, 1</code>), "
        "perulangan <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#while\" rel=\"noopener noreferrer\" target=\"_blank\"><code>while</code></a> "
        "yang terus berjalan selama kondisi bernilai benar, serta indentasi sebagai penentu blok instruksi program."
    ),
    "The <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#for\" rel=\"noopener noreferrer\" target=\"_blank\"><code>for</code></a> statement in Python differs": (
        "Pernyataan <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#for\" rel=\"noopener noreferrer\" target=\"_blank\"><code>for</code></a> "
        "pada Python sedikit berbeda dari apa yang biasa Anda gunakan di C atau Pascal. Alih-alih mengulang deret angka secara kaku, "
        "pernyataan <code>for</code> di Python mengiterasi setiap elemen dari urutan apa pun (seperti list atau string), "
        "sesuai urutan kemunculannya dalam urutan tersebut:"
    ),
    "Code that modifies a collection while iterating": (
        "Kode yang memodifikasi koleksi saat sedang diiterasi dapat menimbulkan perilaku yang sulit diprediksi. "
        "Sebaiknya, lakukan iterasi pada salinan koleksi tersebut atau buatlah koleksi baru:"
    ),
    "If you do need to iterate over a sequence of numbers": (
        "Jika Anda memang perlu mengiterasi serangkaian angka terurut, fungsi bawaan "
        "<a href=\"https://docs.python.org/3.13/library/stdtypes.html#range\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"range\"><code>range()</code></a> "
        "sangat praktis digunakan. Fungsi ini menghasilkan deret aritmetika:"
    ),
    "The given end point is never part of the generated sequence": (
        "Titik akhir yang diberikan tidak pernah menjadi bagian dari urutan yang dihasilkan; <code>range(10)</code> "
        "menghasilkan 10 nilai, yaitu indeks 0 sampai 9. Anda juga dapat menentukan nilai awal dan interval langkahnya (step):"
    ),
    "To iterate over the indices of a sequence": (
        "Untuk mengiterasi indeks dari suatu urutan, Anda dapat memadukan "
        "<a href=\"https://docs.python.org/3.13/library/stdtypes.html#range\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"range\"><code>range()</code></a> "
        "dan <a href=\"https://docs.python.org/3.13/library/functions.html#len\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"len\"><code>len()</code></a>:"
    ),
    "In most such cases, however, it is convenient to use the <a href=\"https://docs.python.org/3.13/library/functions.html#enumerate\"": (
        "Dalam banyak kasus serupa, sangat praktis menggunakan fungsi "
        "<a href=\"https://docs.python.org/3.13/library/functions.html#enumerate\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"enumerate\"><code>enumerate()</code></a> "
        "untuk mendapatkan indeks dan elemennya sekaligus."
    ),
    "A strange thing happens if you just print a range": (
        "Hal menarik terjadi jika Anda mencetak objek range secara langsung: objek tersebut mencetak dirinya sendiri, bukan list isinya."
    ),
    "In many ways the object returned by <a href=\"https://docs.python.org/3.13/library/stdtypes.html#range\"": (
        "Dalam banyak hal, objek yang dikembalikan oleh <code>range()</code> bertindak seolah-olah seperti list, "
        "tetapi sebenarnya bukan. Objek ini mengembalikan elemen berurutan saat diiterasi tanpa membuat seluruh list di memori, "
        "sehingga sangat hemat memori."
    ),
    "We say such an object is <a href=\"https://docs.python.org/3.13/glossary.html#term-iterable\"": (
        "Kita menyebut objek tersebut sebagai <a href=\"https://docs.python.org/3.13/glossary.html#term-iterable\" rel=\"noopener noreferrer\" target=\"_blank\">iterable</a>, "
        "yaitu objek yang dapat dijadikan sumber pengambilan elemen secara bertahap hingga elemennya habis."
    ),
    "Later we will see more functions that return iterables": (
        "Nantinya kita akan melihat lebih banyak fungsi yang mengembalikan objek iterable maupun menerima iterable sebagai argumen."
    ),
    "The <code>break</code> statement breaks out of the innermost enclosing": (
        "Pernyataan <code>break</code> langsung menghentikan dan keluar dari perulangan terdalam "
        "(baik loop <code>for</code> maupun <code>while</code>):"
    ),
    "The <code>continue</code> statement continues with the next iteration": (
        "Pernyataan <code>continue</code> melanjutkan eksekusi ke iterasi berikutnya dari perulangan, "
        "dengan melewati sisa baris kode di bawahnya dalam iterasi saat ini:"
    ),
    "In a <code>for</code> or <code>while</code> loop the <code>break</code> statement": (
        "Pada loop <code>for</code> atau <code>while</code>, klausa <code>else</code> dapat ditambahkan setelah blok loop. "
        "Klausa <code>else</code> ini akan dieksekusi jika perulangan selesai secara alami tanpa diinterupsi oleh pernyataan <code>break</code>:"
    ),
    "In a <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#for\" rel=\"noopener noreferrer\" target=\"_blank\"><code>for</code></a> loop, the <code>else</code> clause is executed": (
        "Pada loop <code>for</code>, klausa <code>else</code> dieksekusi setelah loop menyelesaikan iterasi terakhirnya, yaitu jika tidak ada <code>break</code> yang terjadi."
    ),
    "In a <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#while\" rel=\"noopener noreferrer\" target=\"_blank\"><code>while</code></a> loop, it’s executed after the loop’s condition becomes false": (
        "Pada loop <code>while</code>, klausa <code>else</code> dieksekusi setelah kondisi perulangan berubah menjadi salah (False)."
    ),
    "In either kind of loop, the <code>else</code> clause is <strong>not</strong> executed": (
        "Pada kedua jenis loop tersebut, klausa <code>else</code> <strong>tidak</strong> akan dieksekusi jika perulangan dihentikan oleh pernyataan <code>break</code>."
    ),
    "This is exemplified in the following <code>for</code> loop": (
        "Hal ini dicontohkan pada perulangan <code>for</code> berikut yang mencari bilangan prima:"
    ),
    "One way to think of the else clause": (
        "Cara mudah memahami klausa else pada loop adalah dengan membayangkannya berpasangan dengan pernyataan if di dalam loop. "
        "Jika kondisi pencarian tidak pernah terpenuhi dan loop tuntas tanpa break, klausa else di luar loop akan dijalankan."
    ),
    "The <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#while\" rel=\"noopener noreferrer\" target=\"_blank\"><code>while</code></a> statement is used for repeated execution": (
        "Pernyataan <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#while\" rel=\"noopener noreferrer\" target=\"_blank\"><code>while</code></a> "
        "digunakan untuk mengeksekusi blok kode berulang kali selama ekspresi kondisi bernilai benar (True):"
    ),
    "This repeatedly tests the expression and, if it is true": (
        "Pernyataan ini berulang kali menguji ekspresi kondisi, dan jika benar, menjalankan blok instruksinya; jika ekspresi bernilai salah, "
        "blok klausa else (jika ada) dijalankan dan perulangan berakhir."
    ),
    "The <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#for\" rel=\"noopener noreferrer\" target=\"_blank\"><code>for</code></a> statement is used to iterate over the elements": (
        "Pernyataan <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#for\" rel=\"noopener noreferrer\" target=\"_blank\"><code>for</code></a> "
        "digunakan untuk mengiterasi elemen-elemen dari suatu urutan (seperti string, tuple, atau list) atau objek iterable lainnya:"
    ),
    "The for-loop makes assignments to the variables in the target list": (
        "Loop for melakukan penugasan nilai ke variabel penampung iterasi pada setiap langkah putaran loop:"
    ),

    # -------------------------------------------------------------------------
    # 4. FUNGSI
    # -------------------------------------------------------------------------
    "We can create a function that writes the Fibonacci series": (
        "Kita dapat membuat sebuah fungsi yang mencetak deret Fibonacci hingga batas tertentu:"
    ),
    "The keyword <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#def\"": (
        "Kata kunci <a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#def\" rel=\"noopener noreferrer\" target=\"_blank\"><code>def</code></a> "
        "memperkenalkan sebuah pendefinisian fungsi baru. Kata kunci ini harus diikuti oleh nama fungsi dan daftar parameter formal di dalam tanda kurung. "
        "Baris pernyataan yang membentuk badan fungsi dimulai pada baris berikutnya, dan harus berindentasi."
    ),
    "The first statement of the function body can optionally be a string literal": (
        "Pernyataan pertama dari badan fungsi dapat berupa literal string opsional; string ini merupakan "
        "string dokumentasi fungsi, atau <a href=\"https://docs.python.org/3.13/glossary.html#term-docstring\" rel=\"noopener noreferrer\" target=\"_blank\">docstring</a>. "
        "Docstring digunakan oleh berbagai perkakas otomatis untuk menghasilkan dokumentasi daring interaktif."
    ),
    "The <em>execution</em> of a function introduces a new symbol table": (
        "<em>Eksekusi</em> suatu fungsi memperkenalkan tabel simbol baru yang digunakan untuk variabel-variabel lokal fungsi tersebut. "
        "Semua penugasan variabel di dalam fungsi disimpan dalam tabel simbol lokal."
    ),
    "The actual parameters (arguments) to a function call are introduced in the local symbol table": (
        "Argumen aktual saat pemanggilan fungsi dimasukkan ke dalam tabel simbol lokal dari fungsi yang dipanggil. "
        "Dengan demikian, argumen dilewatkan menggunakan mekanisme <em>call by value</em> (di mana nilainya selalu berupa <em>referensi objek</em>, bukan nilai objek itu sendiri)."
    ),
    "It is simple to write a function that returns a list": (
        "Sangat mudah menulis fungsi yang mengembalikan list angka deret Fibonacci, alih-alih langsung mencetaknya:"
    ),
    "The <a href=\"https://docs.python.org/3.13/reference/simple_stmts.html#return\"": (
        "Pernyataan <a href=\"https://docs.python.org/3.13/reference/simple_stmts.html#return\" rel=\"noopener noreferrer\" target=\"_blank\"><code>return</code></a> "
        "mengembalikan nilai dari suatu fungsi. Pernyataan <code>return</code> tanpa ekspresi akan mengembalikan nilai <code>None</code>. "
        "Jika eksekusi mencapai akhir fungsi tanpa menemukan <code>return</code>, fungsi juga akan mengembalikan <code>None</code> secara implisit."
    ),
    "It is also possible to define functions with a variable number of arguments": (
        "Dimungkinkan pula untuk mendefinisikan fungsi yang menerima sejumlah argumen yang fleksibel. "
        "Terdapat tiga bentuk umum yang dapat digabungkan: nilai argumen default, argumen kata kunci (keyword arguments), "
        "dan daftar argumen arbitrer."
    ),
    "The most useful form is to specify a default value": (
        "Bentuk yang paling bermanfaat adalah menentukan nilai default untuk satu atau beberapa parameter. "
        "Ini menciptakan fungsi yang dapat dipanggil dengan argumen yang lebih sedikit daripada yang didefinisikan:"
    ),
    "Functions can also be called using keyword arguments": (
        "Fungsi juga dapat dipanggil menggunakan argumen kata kunci (keyword arguments) dalam bentuk <code>kwarg=value</code>:"
    ),
    "By default, arguments may be passed to a Python function either by position or explicitly by keyword": (
        "Secara default, argumen dapat dilewatkan ke fungsi Python baik berdasarkan posisi maupun secara eksplisit berdasarkan kata kunci. "
        "Pengembang dapat membatasi bagaimana argumen dilewatkan menggunakan simbol <code>/</code> (hanya-posisi) dan <code>*</code> (hanya-kata-kunci)."
    ),
    "Small anonymous functions can be created with the <a href=\"https://docs.python.org/3.13/reference/expressions.html#lambda\"": (
        "Fungsi anonim berukuran ringkas dapat dibuat dengan kata kunci "
        "<a href=\"https://docs.python.org/3.13/reference/expressions.html#lambda\" rel=\"noopener noreferrer\" target=\"_blank\"><code>lambda</code></a>. "
        "Fungsi lambda secara sintaksis dibatasi pada satu ekspresi tunggal saja:"
    ),

    # -------------------------------------------------------------------------
    # 5. LIST DAN DICTIONARY
    # -------------------------------------------------------------------------
    "The list data type has some more methods": (
        "Tipe data list memiliki banyak metode bawaan yang sangat kaya. Berikut adalah metode-metode utama pada objek list:"
    ),
    "An example that uses most of the list methods": (
        "Berikut adalah contoh komprehensif yang mendemonstrasikan sebagian besar metode manipulasi list:"
    ),
    "The list methods make it very easy to use a list as a stack": (
        "Metode pada list membuatnya sangat mudah digunakan sebagai struktur data tumpukan (stack), "
        "di mana elemen terakhir yang ditambahkan adalah elemen pertama yang diambil (LIFO - \"last-in, first-out\"). "
        "Gunakan <code>append()</code> untuk menambah elemen ke puncak tumpukan, dan <code>pop()</code> tanpa argumen untuk mengambil elemen teratas:"
    ),
    "It is also possible to use a list as a queue": (
        "List juga dapat digunakan sebagai antrean (queue), di mana elemen pertama yang masuk adalah yang pertama keluar (FIFO). "
        "Namun, penyisipan atau penghapusan dari awal list berjalan lambat karena semua elemen harus digeser. "
        "Untuk antrean cepat, gunakan <code>collections.deque</code>."
    ),
    "List comprehensions provide a concise way to create lists": (
        "List comprehension menyediakan cara ringkas dan elegan untuk membuat list baru berdasarkan operasi dari list atau urutan yang sudah ada. "
        "Penggunaan umumnya adalah membuat list baru di mana setiap elemen merupakan hasil penerapan operasi tertentu pada setiap anggota sequence lain:"
    ),
    "There is a way to remove an item from a list given its index": (
        "Terdapat cara untuk menghapus elemen dari list berdasarkan indeksnya, bukan berdasarkan nilainya: yaitu menggunakan pernyataan "
        "<a href=\"https://docs.python.org/3.13/reference/simple_stmts.html#del\" rel=\"noopener noreferrer\" target=\"_blank\"><code>del</code></a>. "
        "Pernyataan ini berbeda dari metode <code>pop()</code> karena tidak mengembalikan nilai:"
    ),
    "We saw that lists and strings have many common properties": (
        "Kita telah melihat bahwa list dan string memiliki banyak sifat yang sama, seperti operasi pengindeksan dan pemotongan (slicing). "
        "Keduanya adalah contoh dari tipe data <em>sequence (urutan)</em>. Ada satu lagi tipe urutan standar: yaitu <em>tuple</em>:"
    ),
    "Another useful data type built into Python is the": (
        "Tipe data bawaan Python lainnya yang sangat berguna adalah <a href=\"https://docs.python.org/3.13/library/stdtypes.html#typesmapping\" rel=\"noopener noreferrer\" target=\"_blank\">dictionary (kamus)</a>. "
        "Tidak seperti urutan yang diindeks oleh rentang angka, dictionary diindeks menggunakan <em>kunci (keys)</em>, "
        "yang dapat berupa tipe data apa pun yang tidak dapat diubah (immutable), seperti string atau angka."
    ),
    "It is best to think of a dictionary as a set of <em>key: value</em> pairs": (
        "Cara terbaik memahami dictionary adalah sebagai kumpulan pasangan <em>kunci: nilai (key: value)</em>, "
        "dengan syarat bahwa kunci harus bersifat unik dalam satu dictionary. Sepasang kurung kurawal kosong <code>{}</code> membuat dictionary kosong:"
    ),
    "When looping through dictionaries, the key and corresponding value": (
        "Saat melakukan perulangan pada dictionary, kunci dan nilai pasangannya dapat diambil secara bersamaan "
        "menggunakan metode <code>items()</code>:"
    ),
    "When looping through a sequence, the position index and corresponding value": (
        "Saat melakukan perulangan pada suatu urutan, indeks posisi dan nilainya dapat diambil secara bersamaan "
        "menggunakan fungsi <a href=\"https://docs.python.org/3.13/library/functions.html#enumerate\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"enumerate\"><code>enumerate()</code></a>:"
    ),
    "To loop over two or more sequences at the same time": (
        "Untuk mengiterasi dua atau lebih urutan secara bersamaan dalam satu loop, pasangan elemennya dapat disatukan "
        "menggunakan fungsi <a href=\"https://docs.python.org/3.13/library/functions.html#zip\" rel=\"noopener noreferrer\" target=\"_blank\" title=\"zip\"><code>zip()</code></a>:"
    ),

    # -------------------------------------------------------------------------
    # 6 & 7. OOP DASAR & LANJUTAN
    # -------------------------------------------------------------------------
    "Classes provide a means of bundling data and functionality together": (
        "Kelas (Class) menyediakan sarana untuk menggabungkan data dan fungsionalitas secara bersamaan. "
        "Membuat kelas baru akan menghasilkan <em>tipe objek baru</em>, memungkinkan instans baru dari tipe tersebut untuk dibuat. "
        "Setiap instans kelas dapat memiliki atribut yang dilampirkan padanya untuk mempertahankan statusnya."
    ),
    "Compared with other programming languages, Python’s class mechanism adds classes": (
        "Dibandingkan dengan bahasa pemrograman lain, mekanisme kelas di Python menambahkan fitur OOP dengan sintaksis dan semantik yang sangat ringkas. "
        "Mekanisme ini mendukung pewarisan berganda (multiple inheritance), metode turunan dapat menimpa (override) metode kelas dasar, "
        "dan metode dapat memanggil metode kelas dasar dengan nama yang sama."
    ),
    "A <em>namespace</em> is a mapping from names to objects": (
        "Sebuah <em>namespace</em> adalah pemetaan dari nama ke objek. Sebagian besar namespace saat ini diimplementasikan "
        "sebagai dictionary Python bawaan. Contoh namespace meliputi: kumpulan nama bawaan (fungsi seperti abs()), "
        "nama global dalam sebuah modul, dan nama lokal saat pemanggilan fungsi."
    ),
    "The simplest form of class definition looks like this": (
        "Bentuk paling sederhana dari definisi kelas adalah sebagai berikut:"
    ),
    "Class definitions, like function definitions (<a href=\"https://docs.python.org/3.13/reference/compound_stmts.html#def\"": (
        "Definisi kelas, sama seperti definisi fungsi (<code>def</code>), harus dieksekusi terlebih dahulu sebelum memiliki efek apa pun:"
    ),
    "When a class definition is entered, a new namespace is created": (
        "Saat memasuki definisi kelas, sebuah namespace baru dibuat dan digunakan sebagai cakupan lokal. "
        "Dengan demikian, seluruh penugasan variabel lokal masuk ke dalam namespace baru ini."
    ),
    "Class objects support two kinds of operations: attribute references and instantiation": (
        "Objek kelas mendukung dua macam operasi: referensi atribut dan instansiasi objek:"
    ),
    "The instantiation operation (“calling” a class object) creates an empty object": (
        "Operasi instansiasi (\"memanggil\" objek kelas) membuat objek baru. Banyak kelas lebih memilih membuat objek "
        "dengan status awal yang telah disesuaikan. Oleh karena itu, sebuah kelas dapat mendefinisikan metode khusus bernama "
        "<code>__init__()</code>, seperti ini:"
    ),
    "When a class defines an <code>__init__()</code> method": (
        "Ketika sebuah kelas mendefinisikan metode <code>__init__()</code>, instansiasi kelas secara otomatis akan memanggil "
        "<code>__init__()</code> untuk instans yang baru dibuat:"
    ),
    "Of course, the syntax for a derived class definition looks like this": (
        "Tentu saja, sintaksis untuk pendefinisian kelas turunan (subclass) adalah sebagai berikut:"
    ),
    "The name <code>BaseClassName</code> must be defined in a scope containing the derived class definition": (
        "Nama <code>BaseClassName</code> harus telah didefinisikan dalam cakupan yang memuat definisi kelas turunan tersebut:"
    ),
    "Execution of a derived class definition proceeds the same as for a base class": (
        "Eksekusi definisi kelas turunan berlangsung serupa dengan kelas dasar. Saat objek kelas dikonstruksi, "
        "kelas dasar diingat. Ini digunakan untuk menyelesaikan resolusi referensi atribut."
    ),
    "Python supports a form of multiple inheritance as well": (
        "Python juga mendukung bentuk pewarisan berganda (multiple inheritance). Definisi kelas dengan banyak kelas dasar tampak seperti:"
    ),
    "“Private” instance variables that cannot be accessed except from inside an object don’t exist in Python": (
        "Variabel instans \"privat\" yang sama sekali tidak dapat diakses dari luar objek sebenarnya tidak ada dalam Python. "
        "Namun, terdapat konvensi yang diikuti oleh sebagian besar kode Python: nama yang diawali dengan sebuah garis bawah "
        "(misalnya <code>_spam</code>) harus diperlakukan sebagai bagian non-publik dari API."
    ),
}

def translate_html_text(html_text: str) -> str:
    for key, id_text in PARAGRAPH_TRANSLATIONS.items():
        if key in html_text:
            return id_text
    return html_text

def process_block(block: dict) -> dict:
    b_type = block.get("type")
    
    if b_type == "heading":
        text = block.get("text", "")
        if text in HEADINGS:
            block["text"] = HEADINGS[text]
            block["html"] = HEADINGS[text]
            
    elif b_type == "paragraph":
        html = block.get("html", "")
        block["html"] = translate_html_text(html)
        
    elif b_type == "definition":
        for item in block.get("items", []):
            for sub_b in item.get("blocks", []):
                process_block(sub_b)
                
    elif b_type == "list":
        for sub_list in block.get("items", []):
            for sub_b in sub_list:
                process_block(sub_b)
                
    elif b_type == "admonition":
        for sub_b in block.get("blocks", []):
            process_block(sub_b)
            
    elif b_type == "note":
        html = block.get("html", "")
        block["html"] = translate_html_text(html)
        
    return block

def localize_chapter(chapter_path: Path) -> int:
    with open(chapter_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    translated_count = 0
    for group in data.get("groups", []):
        src_label = group.get("source", {}).get("label")
        if src_label in SOURCE_LABELS:
            group["source"]["label"] = SOURCE_LABELS[src_label]
            
        for block in group.get("blocks", []):
            orig_html = block.get("html", "")
            process_block(block)
            if block.get("html", "") != orig_html:
                translated_count += 1
                
    with open(chapter_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    return translated_count

def main():
    print("Memulai pembaruan terjemahan dokumentasi resmi ke Bahasa Indonesia...")
    for json_file in sorted(CHAPTERS_DIR.glob("*.json")):
        if json_file.name == "manifest.json":
            continue
        count = localize_chapter(json_file)
        print(f"✅ {json_file.name}: {count} blok teks berhasil dilokalisasi.")
    print("Selesai menerjemahkan dokumentasi resmi.")

if __name__ == "__main__":
    main()

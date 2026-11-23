#include "tespin_config.h"
#include <Arduino.h>
#include <string.h>

// =========================================================================
//  DIAGNOSTIK SELURUH PIN GPIO ESP32-S3 (FREENOVE ESP32-S3 WROOM)
// =========================================================================
//  Cara kerja:
//   1. Tes pasif pull-up / pull-down internal
//      -> mendeteksi jalur yang tertahan GND (korslet) atau 3V3.
//   2. Tes drive output HIGH/LOW
//      -> mendeteksi transistor output GPIO yang rusak/terhambat.
//   3. Tes korslet ANTAR PIN (open-drain matrix)
//      -> satu pin ditarik LOW, semua pin lain dibaca. Kalau ikut LOW,
//         berarti ada sambungan/korslet (mis. kabel breadboard nyambung).
//
//  Pin yang SENGAJA TIDAK DISENTUH:
//    19, 20   : USB native D- / D+
//    26 - 37  : Flash internal + PSRAM octal (35, 36, 37)
//    43, 44   : UART0 / Serial Monitor (CH343)
//
//  Pin yang HANYA jadi DRIVER (tidak dibaca) saat scan korslet:
//    2        : LED onboard IO2 (selalu tertarik LOW oleh LED)
//    45, 46   : strapping + resistor pull-down onboard
//  Pin yang DIKECUALIKAN TOTAL dari scan korslet:
//    14       : SD INMP441 = pin OUTPUT dari mic (jangan di-drive!)
//    38,39,40 : slot microSD onboard
// =========================================================================

struct PinInfo {
  uint8_t     pin;
  const char* role;
  bool        driveSafe;    // boleh diuji OUTPUT HIGH/LOW
  bool        scanDriver;   // boleh ditarik LOW saat scan korslet
  bool        scanReader;   // boleh dibaca saat scan korslet
  bool        expectedLow;  // memang LOW by hardware (LED/pull-down board)
};

static const PinInfo pinTable[] = {
  { 0, "BOOT button / strapping",                true,  true,  true,  false },
  { 1, "I2S Speaker DIN MAX98357A (PIN BARU)",   true,  true,  true,  false },
  { 2, "LED onboard IO2 (JANGAN utk audio!)",    true,  true,  false, true  },
  { 3, "Strapping JTAG",                         true,  true,  true,  false },
  { 4, "Eks-kameraSIOD (SCCB Data)",         true,  true,  true,  false },
  { 5, "Eks-kameraSIOC (SCCB Clock)",        true,  true,  true,  false },
  { 6, "Eks-kameraVSYNC",                    true,  true,  true,  false },
  { 7, "Eks-kameraHREF",                     true,  true,  true,  false },
  { 8, "Eks-kameraD2",                       true,  true,  true,  false },
  { 9, "Eks-kameraD1",                       true,  true,  true,  false },
  {10, "Eks-kameraD3",                       true,  true,  true,  false },
  {11, "Eks-kameraD0",                       true,  true,  true,  false },
  {12, "Eks-kameraD4",                       true,  true,  true,  false },
  {13, "Eks-kameraPCLK",                     true,  true,  true,  false },
  {14, "Mic INMP441 SD (OUTPUT dari mic)",       false, false, false, false },
  {15, "Eks-kameraXCLK",                     true,  true,  true,  false },
  {16, "Eks-kameraD7",                       true,  true,  true,  false },
  {17, "Eks-kameraD6",                       true,  true,  true,  false },
  {18, "Eks-kameraD5",                       true,  true,  true,  false },
  {21, "OLED SCL (I2C)",                         true,  true,  true,  false },
  {38, "microSD CLK",                            false, false, false, false },
  {39, "microSD CMD",                            false, false, false, false },
  {40, "microSD D0",                             false, false, false, false },
  {41, "I2S WS/LRC (Speaker + Mic)",             true,  true,  true,  false },
  {42, "I2S BCLK/SCK (Speaker + Mic)",           true,  true,  true,  false },
  {45, "Strapping + pull-down onboard",          true,  true,  false, true  },
  {46, "Strapping + pull-down onboard",          true,  true,  false, true  },
  {47, "OLED SDA (I2C)",                         true,  true,  true,  false },
  {48, "WS2812 RGB LED onboard",                 true,  true,  true,  false },
};

static const int NUM_PINS = sizeof(pinTable) / sizeof(pinTable[0]);

static unsigned long lastTestRun = 0;
static int testIteration = 0;
static bool fullReportDone = false;
static bool pairReported[64][64];

// =========================================================================
// UTILITAS
// =========================================================================
static const char* yesNo(int v) {
  return (v == HIGH) ? "HIGH" : "LOW";
}

static bool isExternalPullupPin(int pin) {
  // OLED I2C punya resistor pull-up di modulnya.
  return (pin == 21 || pin == 47);
}

static void printWiringMap() {
  Serial.println("\n===================== PETA PIN PROJEK =====================");
  Serial.println("  GPIO 1  -> DIN MAX98357A  (PIN BARU, pindahkan jumper!)");
  Serial.println("  GPIO 2  -> LED onboard    (JANGAN dipakai audio)");
  Serial.println("  GPIO 14 -> SD INMP441     (data mic)");
  Serial.println("  GPIO 21 -> OLED SCL");
  Serial.println("  GPIO 41 -> I2S WS/LRC     (speaker + mic)");
  Serial.println("  GPIO 42 -> I2S BCLK/SCK   (speaker + mic)");
  Serial.println("  GPIO 47 -> OLED SDA");
  Serial.println("  GPIO 48 -> WS2812 RGB     (LED alamat, bukan merah fault)");
  Serial.println("===========================================================");
}

static void printLedNotes() {
  Serial.println("\n===================== TENTANG LAMPU MERAH =================");
  Serial.println("  1. LED MERAH kecil di dekat konektor USB = LED POWER.");
  Serial.println("     Selalu nyala selama board dapat daya. Itu NORMAL,");
  Serial.println("     bukan korslet dan bukan dinyalakan oleh firmware.");
  Serial.println("  2. LED di IO2 = LED user onboard.");
  Serial.println("     Kalau GPIO 2 dipakai I2S DIN, LED ini menyala/berkedip");
  Serial.println("     mengikuti data audio. Setelah DIN dipindah ke GPIO 1,");
  Serial.println("     LED ini dimatikan oleh firmware (digitalWrite LOW).");
  Serial.println("  3. LED RGB di IO48 = WS2812. Bisa sempat menyala acak");
  Serial.println("     saat boot; firmware mode 5 mematikannya (0,0,0).");
  Serial.println("===========================================================");
}

// =========================================================================
// TES 1 + 2: PULL-UP/PULL-DOWN & DRIVE PER PIN
// =========================================================================
static void testOnePin(const PinInfo &p, int &badPull, int &badDrive) {
  // --- Tes pasif ---
  pinMode(p.pin, INPUT_PULLUP);
  delayMicroseconds(900);
  int pu = digitalRead(p.pin);

  pinMode(p.pin, INPUT_PULLDOWN);
  delayMicroseconds(900);
  int pd = digitalRead(p.pin);

  pinMode(p.pin, INPUT);

  char verdict[96];
  bool pullBad = false;

  if (p.pin == 14) {
    snprintf(verdict, sizeof(verdict),
             "PIN OUTPUT MIC (hasil pasif tdk valid)");
  } else if (p.pin == 38 || p.pin == 39 || p.pin == 40) {
    snprintf(verdict, sizeof(verdict),
             "SLOT microSD (skipped)");
  } else if (pu == HIGH && pd == LOW) {
    snprintf(verdict, sizeof(verdict), "NORMAL");
  } else if (pu == LOW && pd == LOW) {
    if (p.expectedLow) {
      snprintf(verdict, sizeof(verdict), "NORMAL (LED/pull-down board)");
    } else {
      snprintf(verdict, sizeof(verdict),
               "BAHAYA: TERTAHAN LOW (korslet GND?)");
      pullBad = true;
    }
  } else if (pu == HIGH && pd == HIGH) {
    if (isExternalPullupPin(p.pin)) {
      snprintf(verdict, sizeof(verdict), "NORMAL (pull-up modul)");
    } else {
      snprintf(verdict, sizeof(verdict),
               "BAHAYA: TERTAHAN HIGH (korslet 3V3?)");
      pullBad = true;
    }
  } else {
    snprintf(verdict, sizeof(verdict), "FLUKTUATIF (pin goyang?)");
    pullBad = true;
  }

  if (pullBad) badPull++;

  // --- Tes drive output ---
  char driveStr[32];
  int hi = -1, lo = -1;

  if (!p.driveSafe) {
    snprintf(driveStr, sizeof(driveStr), "SKIP (aman)");
  } else {
    pinMode(p.pin, OUTPUT);
    digitalWrite(p.pin, HIGH);
    delayMicroseconds(500);
    hi = digitalRead(p.pin);

    digitalWrite(p.pin, LOW);
    delayMicroseconds(500);
    lo = digitalRead(p.pin);

    pinMode(p.pin, INPUT);

    if (hi == HIGH && lo == LOW) {
      snprintf(driveStr, sizeof(driveStr), "OK");
    } else {
      snprintf(driveStr, sizeof(driveStr), "GAGAL!");
      badDrive++;
    }
  }

  Serial.printf("GPIO %-2d | PU=%-4s PD=%-4s | DRIVE=%-10s | %-38s\n",
                p.pin, yesNo(pu), yesNo(pd), driveStr, verdict);
  Serial.printf("         | %s\n", p.role);
}

// =========================================================================
// TES 3: SCAN KORSLET ANTAR PIN (OPEN-DRAIN MATRIX)
// =========================================================================
static int scanShortMatrix(bool verbose) {
  memset(pairReported, 0, sizeof(pairReported));

  static uint8_t lowWith[64];       // berapa driver yang membuat pin ini ikut LOW
  static bool coupled[64][64];      // matriks pasangan yang terdeteksi
  memset(lowWith, 0, sizeof(lowWith));
  memset(coupled, 0, sizeof(coupled));

  int driverCount = 0;

  // Semua pin aman di-set INPUT_PULLUP dulu.
  for (int i = 0; i < NUM_PINS; i++) {
    if (pinTable[i].scanReader) {
      pinMode(pinTable[i].pin, INPUT_PULLUP);
    } else if (pinTable[i].scanDriver) {
      pinMode(pinTable[i].pin, INPUT);
    }
    if (pinTable[i].scanDriver) driverCount++;
  }
  delayMicroseconds(500);

  for (int d = 0; d < NUM_PINS; d++) {
    if (!pinTable[d].scanDriver) continue;

    pinMode(pinTable[d].pin, OUTPUT);
    digitalWrite(pinTable[d].pin, LOW);
    delayMicroseconds(800);

    for (int r = 0; r < NUM_PINS; r++) {
      if (r == d || !pinTable[r].scanReader) continue;

      if (digitalRead(pinTable[r].pin) == LOW) {
        uint8_t a = pinTable[d].pin;
        uint8_t b = pinTable[r].pin;
        lowWith[b]++;
        coupled[a][b] = true;
        coupled[b][a] = true;
      }
    }

    // Lepas pin driver, kembalikan ke pull-up untuk iterator berikutnya.
    pinMode(pinTable[d].pin, INPUT_PULLUP);
    delayMicroseconds(200);
  }

  int found = 0;

  // ---------------------------------------------------------------------
  // KASUS A: pin yang LOW terhadap HAMPIR SEMUA driver.
  // Ini bukan "korslet ke satu pin", tapi pin yang ditahan LOW terus
  // (korslet ke GND, atau memang di-drive LOW oleh modul yang terpasang).
  // ---------------------------------------------------------------------
  for (int i = 0; i < NUM_PINS; i++) {
    if (!pinTable[i].scanReader) continue;
    uint8_t p = pinTable[i].pin;

    if (lowWith[p] >= (uint8_t)(driverCount - 1)) {
      found++;
      if (verbose) {
        Serial.printf("  [TERTAHAN LOW] GPIO %d selalu LOW terhadap semua driver.\n", p);
        Serial.printf("                  Kemungkinan korslet ke GND ATAU ditahan modul (%s).\n",
                      pinTable[i].role);
        Serial.println("                  Cek kabel pin ini, atau lepas modulnya lalu scan ulang.");
      }
    }
  }

  // ---------------------------------------------------------------------
  // KASUS B: pasangan pin yang saling terhubung (hanya LOW satu sama lain).
  // ---------------------------------------------------------------------
  for (int i = 0; i < NUM_PINS; i++) {
    if (!pinTable[i].scanReader) continue;
    uint8_t a = pinTable[i].pin;
    if (lowWith[a] >= (uint8_t)(driverCount - 1)) continue; // sudah dilaporkan kasus A

    for (int j = 0; j < NUM_PINS; j++) {
      if (i == j || !pinTable[j].scanReader) continue;
      uint8_t b = pinTable[j].pin;
      if (!coupled[a][b]) continue;
      if (lowWith[b] >= (uint8_t)(driverCount - 1)) continue;
      if (pairReported[a][b] || pairReported[b][a]) continue;

      pairReported[a][b] = true;
      pairReported[b][a] = true;
      found++;
      if (verbose) {
        Serial.printf("  [KORSLET] GPIO %d  <-->  GPIO %d   (%s  <->  %s)\n",
                      a, b, pinTable[i].role, pinTable[j].role);
      }
    }
  }

  // Kembalikan semua ke input biasa (aman).
  for (int i = 0; i < NUM_PINS; i++) {
    pinMode(pinTable[i].pin, INPUT);
  }

  if (verbose && found == 0) {
    Serial.println("  (Tidak ada pasangan pin yang saling korslet)");
  }
  return found;
}

// =========================================================================
// LAPORAN PENUH
// =========================================================================
static void runFullDiagnostic(int iteration) {
  Serial.printf("\n\n=================== [DIAGNOSTIK PENUH #%d] ===================\n",
                iteration);
  Serial.println("Keterangan: PU = internal pull-up | PD = internal pull-down");
  Serial.println("            HIGH = 3.3V | LOW = 0V");
  Serial.println("---------------------------------------------------------------");
  Serial.printf("%-7s | %-19s | %-11s | %s\n",
                "PIN", "PULLUP / PULLDOWN", "DRIVE", "STATUS / KESIMPULAN");
  Serial.println("---------------------------------------------------------------");

  int badPull = 0;
  int badDrive = 0;

  for (int i = 0; i < NUM_PINS; i++) {
    testOnePin(pinTable[i], badPull, badDrive);
    delay(2);
  }

  Serial.println("\n------------------- SCAN KORSLET ANTAR PIN -------------------");
  Serial.println("Satu pin ditarik LOW, pin lain dibaca (metode open-drain).");
  Serial.println("Jika pin lain ikut LOW, berarti ada sambungan/korslet.");
  int shorts = scanShortMatrix(true);

  // Log ringkas format CSV supaya mudah disalin ke laporan/skripsi.
  Serial.println("\n------------------- LOG RINGKAS (CSV) -----------------------");
  Serial.println("pin,role,pullup,pulldown,drive");
  for (int i = 0; i < NUM_PINS; i++) {
    const PinInfo &p = pinTable[i];
    pinMode(p.pin, INPUT_PULLUP);
    delayMicroseconds(300);
    int pu = digitalRead(p.pin);
    pinMode(p.pin, INPUT_PULLDOWN);
    delayMicroseconds(300);
    int pd = digitalRead(p.pin);
    pinMode(p.pin, INPUT);
    Serial.printf("%d,\"%s\",%s,%s,%s\n",
                  p.pin, p.role, yesNo(pu), yesNo(pd),
                  p.driveSafe ? "TESTED" : "SKIP");
  }

  Serial.println("\n======================= KESIMPULAN ===========================");
  Serial.printf("  Pin tertahan / curiga korslet : %d\n", badPull);
  Serial.printf("  Pin gagal drive output        : %d\n", badDrive);
  Serial.printf("  Pasangan pin saling korslet   : %d\n", shorts);
  if (badPull == 0 && badDrive == 0 && shorts == 0) {
    Serial.println("  => SEMUA PIN YANG DIUJI SEHAT. Tidak ada korslet GPIO.");
    Serial.println("     Kalau speaker masih kemresek, cek fisik terminal speaker");
    Serial.println("     (serabut + dan - jangan menyentuh) dan pindahkan DIN");
    Serial.println("     MAX98357A dari GPIO 2 ke GPIO 1.");
  } else {
    Serial.println("  => ADA TEMUAN. Baca baris BAHAYA/[KORSLET] di atas.");
  }
  Serial.println("=============================================================");
}

// =========================================================================
// LAPORAN RINGKAS (berkala)
// =========================================================================
static void runCompactDiagnostic(int iteration) {
  Serial.printf("\n[DIAG #%d] Scan korslet cepat...\n", iteration);
  int shorts = scanShortMatrix(true);
  Serial.printf("[DIAG #%d] Hasil: %d pasangan korslet. (Tekan 'r' + Enter untuk laporan penuh)\n",
                iteration, shorts);
}

// =========================================================================
// SETUP
// =========================================================================
void setupTesPin() {
  Serial.begin(115200);
  delay(1500);

  // Pastikan LED onboard tidak mengganggu pengukuran.
  pinMode(2, OUTPUT);
  digitalWrite(2, LOW);
  neopixelWrite(48, 0, 0, 0);

  Serial.println("\n");
  Serial.println("================================================================================");
  Serial.println("   [DIAGNOSTIK TEGANGAN, DRIVE & KORSLET SELURUH GPIO ESP32-S3]                ");
  Serial.println("   Board: Freenove ESP32-S3 WROOM (N8R8)                                       ");
  Serial.println("================================================================================");
  Serial.println("Yang diuji:");
  Serial.println("  1. Pull-up/pull-down tiap pin  -> jalur tertahan GND / 3.3V");
  Serial.println("  2. Drive output HIGH & LOW     -> transistor GPIO rusak");
  Serial.println("  3. Matriks korslet antar-pin   -> kabel/breadboard saling sentuh");
  Serial.println("--------------------------------------------------------------------------------");
  Serial.println("TIDAK diuji (sengaja, pin internal board):");
  Serial.println("  GPIO 19,20 (USB) | GPIO 26-37 (Flash+PSRAM) | GPIO 43,44 (Serial)");
  Serial.println("Dilewati dari scan korslet:");
  Serial.println("  GPIO 14 (output mic) | GPIO 2,45,46 | GPIO 38,39,40 (microSD)");
  Serial.println("--------------------------------------------------------------------------------");
  Serial.println("TIPS AKURASI:");
  Serial.println("  * Untuk tes kelistrikan murni, cabut modul mic/kamera/SD dulu.");
  Serial.println("  * Tekan 'r' lalu Enter untuk memaksa laporan penuh ulang.");
  Serial.println("  * Terminal speaker TIDAK bisa dites lewat GPIO. Ukur pakai");
  Serial.println("    multimeter: harus sekitar 4-8 ohm, BUKAN 0 ohm.");
  Serial.println("================================================================================");

  printWiringMap();
  printLedNotes();

  lastTestRun = 0;
  fullReportDone = false;
}

// =========================================================================
// LOOP
// =========================================================================
void loopTesPin() {
  // Perintah 'r' = ulangi laporan penuh
  while (Serial.available() > 0) {
    int c = Serial.read();
    if (c == 'r' || c == 'R') {
      fullReportDone = false;
      lastTestRun = 0;
      Serial.println("\n>> Laporan penuh diminta ulang...");
    }
  }

  unsigned long now = millis();
  if (now - lastTestRun < 8000) {
    return;
  }
  lastTestRun = now;
  testIteration++;

  if (!fullReportDone) {
    runFullDiagnostic(testIteration);
    fullReportDone = true;
  } else {
    runCompactDiagnostic(testIteration);
  }
}

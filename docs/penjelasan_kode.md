# Penjelasan Kode `src/main.py`

Dokumen ini menjelaskan setiap **blok kode** dalam `src/main.py` menggunakan bahasa sederhana setingkat mahasiswa. Cocok dibaca sebelum presentasi video agar dapat menjelaskan cara kerja kode dengan lancar.

> **Tip Presentasi:** Untuk setiap blok, coba baca "Kalimat untuk Video" dengan lantang. Kalau terasa alami, berarti penjelasanmu sudah bagus!

---

## Blok 1 — Import dan Pengaturan Konstanta

**Lokasi:** Baris 1–108 (bagian header hingga `STATUS_TUTUP`, `TEKS`, `WARNA`, `FILE_LOG`)

```python
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from PIL import ImageGrab
import winsound, threading, csv, os, time, ctypes
from datetime import datetime

MODEL_BLAZEFACE  = "models/blaze_face_short_range.tflite"
FILE_MODEL_LBPH  = os.path.join("data", "pemilik_model.yml")
UKURAN_WAJAH     = (200, 200)
AMBANG_CONFIDENCE_AWAL = 70
BATAS_YAW_AWAL   = 0.35
BATAS_JARAK_CM_AWAL = 200
LAYAR_PENUH      = False
...
```

### Penjelasan Sederhana

- **`import cv2`** — OpenCV untuk membuka kamera, menggambar kotak wajah, dan menampilkan jendela.
- **`import mediapipe`** — Library Google untuk menjalankan model BlazeFace mendeteksi wajah.
- **`import numpy as np`** — Untuk operasi matriks pada gambar (gambar = matriks piksel).
- **`from PIL import ImageGrab`** — Mengambil tangkapan layar monitor secara utuh.
- **`import winsound`** — Membunyikan bunyi bip peringatan dari speaker Windows.
- **`import threading`** — Menjalankan bunyi alarm di "jalur terpisah" agar kamera tidak tersendat.
- **`LAYAR_PENUH = False`** — Selalu `False` saat pengembangan agar bisa menutup program kapan saja.
- **`TAHAN`** — Kamus yang menyimpan berapa detik suatu kondisi harus bertahan sebelum status resmi berubah. Ini mencegah status "berkedip" akibat deteksi yang tidak stabil.

### 🎙️ Kalimat untuk Video

> *"Di bagian atas kode, saya mengimpor semua library yang dibutuhkan: OpenCV untuk pengolahan citra, MediaPipe untuk deteksi wajah, dan beberapa library tambahan. Lalu saya mendefinisikan konstanta-konstanta pengaturan di sini, seperti lokasi file model, ukuran wajah, dan ambang batas parameter. Dengan meletakkan semua pengaturan di atas, saya dan penguji bisa dengan mudah mengubah nilai-nilai ini tanpa harus mencari ke dalam kode."*

---

## Blok 2 — Persiapan Sistem (Pra-Loop)

**Lokasi:** Baris 109–200 (folder, log, LBPH, BlazeFace, kamera, slider)

```python
# Membuat folder kejadian dan file log jika belum ada
os.makedirs(FOLDER_FOTO, exist_ok=True)
if not os.path.exists(FILE_LOG):
    with open(FILE_LOG, "w", ...) as f:
        penulis.writerow(HEADER_LOG)

# Memuat model LBPH jika tersedia
if os.path.exists(FILE_MODEL_LBPH):
    pengenal_lbph = cv2.face.LBPHFaceRecognizer_create()
    pengenal_lbph.read(FILE_MODEL_LBPH)
    mode_lbph_aktif = True
else:
    # Mode fallback: wajah terbesar = pemilik
    mode_lbph_aktif = False

# Membangun detektor BlazeFace
opsi_blazeface = vision.FaceDetectorOptions(...)
detektor = vision.FaceDetector.create_from_options(opsi_blazeface)

# Membuka kamera
kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Membuat jendela slider (trackbar)
cv2.namedWindow(NAMA_JENDELA_SLIDER, ...)
cv2.createTrackbar("Batas Yaw x100", ...)
...
```

### Penjelasan Sederhana

- **Pembuatan folder dan log** — Program membuat folder `data/kejadian/` dan file `log_kejadian.csv` secara otomatis saat pertama dijalankan. Ini mencegah error "folder tidak ditemukan".
- **Muat model LBPH** — Jika file `pemilik_model.yml` ada, model dimuat ke memori. Jika tidak ada, program tetap berjalan dengan *mode fallback* (wajah terbesar dianggap pemilik).
- **BlazeFace mode VIDEO** — Detektor dijalankan dalam `RunningMode.VIDEO` agar dapat menerima input berurutan berupa frame video, bukan foto tunggal.
- **`cv2.VideoCapture(0, cv2.CAP_DSHOW)`** — Membuka kamera pertama (indeks 0) menggunakan backend DirectShow khusus Windows. Tanpa `CAP_DSHOW`, kamera terkadang lambat diinisialisasi.
- **Slider / Trackbar** — Komponen GUI bawaan OpenCV untuk mengatur parameter secara langsung tanpa mengubah kode. Nilai trackbar hanya berupa bilangan bulat, sehingga nilai yaw (misalnya 0.35) disimpan sebagai 35 dan dibagi 100 kembali saat dibaca.

### 🎙️ Kalimat untuk Video

> *"Sebelum masuk ke loop utama, program melakukan persiapan awal: membuat folder penyimpanan, memuat model pengenal wajah LBPH, membangun detektor BlazeFace, membuka kamera, dan menyiapkan slider interaktif. Kalau file model LBPH tidak ada, program otomatis berpindah ke mode fallback agar tetap bisa berjalan meski belum ada pendaftaran wajah."*

---

## Blok 3 — Fungsi-Fungsi Pembantu

**Lokasi:** Baris 201–344 (semua fungsi `def ...():`)

### 3a. `hitung_kecerahan(frame_bgr)`

```python
def hitung_kecerahan(frame_bgr):
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    kanal_v = hsv[:, :, 2]
    return float(np.mean(kanal_v))
```

**Cara kerja:** Mengonversi gambar ke ruang warna HSV, lalu mengambil kanal V (Value/kecerahan) dan menghitung rata-ratanya. Nilai 0 = gelap total, 255 = sangat terang.

### 3b. `perbaiki_cahaya_clahe(frame_bgr)`

```python
def perbaiki_cahaya_clahe(frame_bgr):
    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_clahe = clahe_objek.apply(l)
    lab_hasil = cv2.merge((l_clahe, a, b))
    return cv2.cvtColor(lab_hasil, cv2.COLOR_LAB2BGR)
```

**Cara kerja:** Mengonversi ke ruang warna LAB, menerapkan CLAHE hanya pada kanal L (kecerahan), lalu menggabungkan kembali. Hasilnya: kontras meningkat tanpa mengubah warna asli.

> **Mengapa LAB, bukan HSV?** Kanal L pada LAB merepresentasikan kecerahan yang lebih konsisten secara perseptual visual dibandingkan kanal V pada HSV.

### 3c. `analisis_wajah(wajah, fokal_aktif)`

```python
def analisis_wajah(wajah, fokal_aktif):
    lebar_px = wajah.bounding_box.width
    jarak = fokal_aktif * LEBAR_WAJAH_CM / lebar_px   # Model lubang jarum
    # Keypoint: 0=mata kanan, 1=mata kiri, 2=ujung hidung
    tengah = (mata_a.x + mata_b.x) / 2
    yaw = (hidung.x - tengah) / jarak_mata
    return jarak, yaw
```

**Cara kerja:**
- **Jarak** dihitung dengan *model lubang jarum (pinhole camera)*:  
  `jarak = fokal × lebar_wajah_nyata / lebar_kotak_piksel`  
  Semakin kecil kotak wajah → semakin jauh orangnya.
- **Yaw** (sudut putaran kepala) dihitung dari posisi hidung relatif terhadap titik tengah kedua mata.  
  Jika hidung di tengah → `yaw ≈ 0` → wajah lurus ke depan.  
  Jika hidung jauh ke kiri/kanan → `|yaw|` besar → wajah menoleh.

### 3d. `uji_identitas_pemilik(frame, kotak, ambang)`

```python
def uji_identitas_pemilik(frame_asli, kotak_wajah, ambang_conf_aktif):
    potongan = frame_asli[y1:y2, x1:x2]          # Crop wajah
    abu = cv2.cvtColor(potongan, cv2.COLOR_BGR2GRAY)
    seragam = cv2.resize(abu, UKURAN_WAJAH)       # Resize 200x200
    label, confidence = pengenal_lbph.predict(seragam)
    return (label == 1 and confidence <= ambang), confidence
```

**Cara kerja:** Memotong area wajah dari frame, mengonversinya ke grayscale dan meresize ke 200×200 piksel (sama seperti saat pendaftaran), lalu meminta model LBPH untuk memprediksi. Skor confidence LBPH = jarak antara fitur wajah — semakin kecil = semakin mirip.

### 3e. `status_mentah(ada_wajah, ada_pemilik, daftar_orang_lain)`

```python
def status_mentah(...):
    if not ada_wajah:        return "PERGI"
    if not ada_pemilik:      return "ORANG_ASING"
    if tidak ada orang lain: return "AMAN"
    for menghadap, dekat in daftar_orang_lain:
        if menghadap and dekat: return "BAHAYA"
    return "WASPADA"
```

**Cara kerja:** Fungsi logika sederhana yang menentukan status sementara berdasarkan kondisi frame. Hasilnya belum langsung menjadi "status resmi" — masih diproses oleh stabilisasi waktu di loop utama.

### 3f. Fungsi-fungsi lain

| Fungsi | Kegunaan |
|--------|---------|
| `bunyikan_alarm(jenis)` | Membunyikan nada menggunakan `winsound.Beep()` di thread terpisah agar tidak membekukan kamera |
| `ambil_layar()` | Mengambil tangkapan layar monitor dengan `ImageGrab.grab()`, dikonversi ke format BGR OpenCV |
| `buramkan(layar, teks)` | Mengecilkan gambar, mengaburkan dengan Gaussian blur, membesarkan kembali (trik efisiensi), lalu menambahkan teks peringatan |
| `buka_overlay()` | Membuat jendela overlay penutup layar; jika `LAYAR_PENUH=True`, jendela ditampilkan penuh layar di atas semua jendela lain |
| `catat_log(...)` | Menambahkan satu baris ke `log_kejadian.csv` dengan cap waktu, status, jumlah wajah, jarak, dan keterangan |
| `simpan_foto_kejadian(frame)` | Menyimpan frame kamera ke `data/kejadian/` dengan nama file berstempel waktu |

### 🎙️ Kalimat untuk Video

> *"Semua logika pemrosesan saya pisahkan ke dalam fungsi-fungsi kecil agar kode mudah dibaca. Misalnya, fungsi `analisis_wajah` menghitung jarak dengan rumus model lubang jarum dan arah pandang dengan nilai yaw. Fungsi `uji_identitas_pemilik` menggunakan model LBPH untuk memeriksa apakah wajah yang terdeteksi adalah wajah pemilik yang sudah terdaftar."*

---

## Blok 4 — Variabel Kontrol

**Lokasi:** Baris 350–372

```python
status_aktif    = "AMAN"    # Status resmi saat ini
status_lama     = "AMAN"    # Status resmi sebelumnya (untuk deteksi perubahan)
kandidat        = None      # Status yang sedang "menunggu konfirmasi"
waktu_kandidat  = 0.0       # Waktu pertama kali kandidat status muncul

layar_asli      = None      # Tangkapan layar saat overlay pertama dibuka
gambar_buram    = None      # Gambar layar yang sudah diburamkan

sedang_jeda     = False     # True saat pengguna menekan tombol P
mode_cahaya     = "OTOMATIS"  # Mode CLAHE: OTOMATIS / PAKSA_ON / PAKSA_OFF
```

**Cara kerja sistem stabilisasi:**

```
Frame 1: status_mentah = "BAHAYA"
  → Berbeda dari status_aktif ("AMAN")
  → Simpan kandidat = "BAHAYA", catat waktu_kandidat

Frame 2–N: status_mentah masih "BAHAYA"
  → Hitung selisih waktu: sekarang - waktu_kandidat
  → Jika ≥ TAHAN["BAHAYA"] (0.5 detik) → status_aktif berubah menjadi "BAHAYA"

Jika tiba-tiba status_mentah berubah sebelum 0.5 detik:
  → kandidat direset → status_aktif tidak berubah
```

Ini mencegah layar berkedip-kedip akibat deteksi yang tidak konsisten antar frame.

### 🎙️ Kalimat untuk Video

> *"Sistem menggunakan mekanisme stabilisasi berbasis waktu. Artinya, status tidak langsung berubah begitu ada deteksi baru. Status baru harus bertahan selama waktu tertentu — misalnya 0,5 detik untuk BAHAYA — sebelum dianggap valid. Ini mencegah alarm berbunyi karena deteksi yang tidak konsisten sesaat."*

---

## Blok 5 — Siklus Utama: Baca Frame + CLAHE

**Lokasi:** Loop `while True:` — bagian pembacaan nilai slider dan frame

```python
while True:
    # Baca nilai slider
    pos_yaw  = cv2.getTrackbarPos("Batas Yaw x100", ...)
    batas_yaw_aktif = max(10, pos_yaw) / 100.0

    # Baca frame kamera
    ok, frame = kamera.read()
    frame = cv2.flip(frame, 1)   # Cermin horizontal

    # Hitung kecerahan, putuskan apakah CLAHE diterapkan
    kecerahan_sekarang = hitung_kecerahan(frame)
    if mode_cahaya == "PAKSA_ON":
        clahe_sedang_aktif = True
    elif mode_cahaya == "PAKSA_OFF":
        clahe_sedang_aktif = False
    else:  # OTOMATIS
        clahe_sedang_aktif = (kecerahan_sekarang < ambang_gelap_aktif)

    if clahe_sedang_aktif:
        frame_terproses = perbaiki_cahaya_clahe(frame)
    else:
        frame_terproses = frame.copy()
```

### Penjelasan Sederhana

- **`cv2.flip(frame, 1)`** — Membalik gambar secara horizontal (seperti cermin) agar gerakan tangan terasa alami.
- **CLAHE otomatis** — Jika kecerahan rata-rata di bawah ambang (default 80), CLAHE diterapkan otomatis sebelum deteksi wajah.
- **`frame_bersih`** — Salinan frame terproses tanpa gambar kotak atau teks. Digunakan untuk crop wajah LBPH agar prediksi tidak terpengaruh gambar dekorasi.

### 🎙️ Kalimat untuk Video

> *"Di setiap iterasi loop, program membaca satu frame dari kamera, lalu memeriksa kecerahannya. Jika terlalu gelap dan mode CLAHE aktif, frame diperbaiki kontrasnya terlebih dahulu menggunakan algoritma CLAHE. Baru setelah itu, frame yang sudah diperbaiki dikirim ke detektor wajah BlazeFace."*

---

## Blok 6 — Deteksi Wajah dan Identifikasi

**Lokasi:** Loop utama, bagian deteksi dan evaluasi wajah

```python
# Konversi ke format MediaPipe
rgb = cv2.cvtColor(frame_terproses, cv2.COLOR_BGR2RGB)
gambar_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

# Deteksi wajah
ts = int((sekarang - waktu_mulai) * 1000)   # Timestamp dalam ms
hasil = detektor.detect_for_video(gambar_mp, ts)
daftar_wajah = hasil.detections

# Identifikasi pemilik (mode LBPH)
for wajah in daftar_wajah:
    cocok, skor_conf = uji_identitas_pemilik(frame_bersih, wajah.bounding_box, ambang_conf_aktif)
    if cocok:
        kandidat_pemilik.append((wajah, skor_conf))

# Pemilik = wajah yang cocok dengan confidence terendah (paling mirip)
pemilik = kandidat_pemilik[0][0]
```

### Penjelasan Sederhana

- **Konversi RGB** — MediaPipe membutuhkan input dalam format RGB, sedangkan OpenCV menggunakan BGR. Konversi wajib dilakukan.
- **Timestamp (ts)** — Mode VIDEO pada MediaPipe membutuhkan cap waktu yang selalu bertambah (monoton). Timestamp dihitung dari selisih waktu sejak program dimulai, dikonversi ke milidetik.
- **Memilih pemilik terbaik** — Jika ada lebih dari satu wajah yang cocok (misalnya kembar), sistem memilih yang nilai confidence-nya paling kecil (paling mirip dengan data pendaftaran).

### 🎙️ Kalimat untuk Video

> *"BlazeFace mengembalikan daftar wajah yang terdeteksi, masing-masing dengan kotak bounding box dan titik kunci keypoint. Lalu untuk setiap wajah, model LBPH memberikan nilai confidence. Jika nilai confidence lebih kecil atau sama dengan ambang batas, wajah itu diakui sebagai pemilik. Wajah-wajah lainnya kemudian dinilai jarak dan arah pandangnya."*

---

## Blok 7 — Evaluasi Status dan Tindakan

**Lokasi:** Loop utama, bagian `if not sedang_jeda:` dan blok overlay

```python
if not sedang_jeda:
    mentah = status_mentah(ada_wajah, ada_pemilik, daftar_orang_lain)

    # Mekanisme stabilisasi berbasis waktu
    if mentah != kandidat:
        kandidat = mentah
        waktu_kandidat = sekarang
    elif sekarang - waktu_kandidat >= TAHAN[mentah]:
        status_aktif = mentah   # Status resmi berubah

    # Tindakan saat status berubah
    if status_aktif != status_lama:
        if status_aktif in STATUS_TUTUP:
            layar_asli = ambil_layar()
            buka_overlay()
            gambar_buram = buramkan(layar_asli, TEKS[status_aktif])
            if status_aktif in ("BAHAYA", "ORANG_ASING"):
                bunyikan_alarm(status_aktif)
                simpan_foto_kejadian(frame_terproses)
        else:
            cv2.destroyWindow(NAMA_OVERLAY)   # Tutup overlay
            if status_aktif == "WASPADA":
                bunyikan_alarm("WASPADA")
        catat_log(...)
        status_lama = status_aktif
```

### Penjelasan Sederhana

- **Jeda (`sedang_jeda`)** — Saat jeda aktif, seluruh blok evaluasi dan tindakan dilewati. Kamera tetap berjalan tetapi tidak ada overlay atau alarm.
- **`ambil_layar()`** hanya dipanggil **sekali** saat overlay pertama dibuka (`status_lama not in STATUS_TUTUP`). Ini menangkap tampilan layar *sebelum* overlay muncul.
- **Log dicatat** hanya saat `status_aktif != status_lama`, bukan setiap frame. Ini mencegah log membengkak dengan ribuan baris yang identik.

### 🎙️ Kalimat untuk Video

> *"Ketika status resmi berubah, barulah sistem mengambil tindakan: mengambil tangkapan layar, menampilkan overlay blur, membunyikan alarm, dan menyimpan foto kejadian. Semua kejadian dicatat ke file CSV. Penting: tindakan ini hanya dipicu saat status berubah, bukan setiap frame, sehingga log tidak dipenuhi data yang berulang."*

---

## Blok 8 — Tampilan dan Tombol Keyboard

**Lokasi:** Loop utama, bagian pita status, `cv2.imshow`, dan `cv2.waitKey`

```python
# Pita status berwarna di atas frame
warna_pita = WARNA.get(status_aktif)
cv2.rectangle(frame_terproses, (0,0), (lebar, 50), warna_pita, -1)
cv2.putText(frame_terproses, TEKS[status_aktif], ...)

# Tampilkan frame kamera dan overlay (jika aktif)
cv2.imshow("Pelindung Privasi Layar - Kamera", frame_terproses)
if status_aktif in STATUS_TUTUP and gambar_buram is not None:
    cv2.imshow(NAMA_OVERLAY, gambar_buram)

# Tangkap tombol
tombol = cv2.waitKey(1) & 0xFF
if tombol == ord("q") or tombol == 27:   # Q atau Esc
    catat_log(..., "Program dihentikan pengguna")
    break
if tombol == ord("c"):   # Ganti mode CLAHE
    ...
if tombol == ord("m"):   # Nyala/mati alarm
    ALARM_AKTIF = not ALARM_AKTIF
if tombol == ord("k") and pemilik is not None:   # Kalibrasi fokal
    FOKAL = pemilik.bounding_box.width * JARAK_KALIBRASI_CM / LEBAR_WAJAH_CM
if tombol == ord("p"):   # Jeda/lanjut
    sedang_jeda = not sedang_jeda
    catat_log(..., "dijeda/dilanjutkan")

# Setelah loop selesai
kamera.release()
cv2.destroyAllWindows()
```

### Penjelasan Sederhana

- **`cv2.waitKey(1)`** — Menunggu input keyboard selama 1 milidetik. Ini juga yang memberi waktu OpenCV untuk me-refresh tampilan jendela. Tanpa ini, jendela tidak akan muncul.
- **`& 0xFF`** — Masking bit untuk memastikan kode tombol terbaca benar di semua sistem operasi.
- **Kalibrasi (`K`)** — Menggunakan ukuran kotak wajah pemilik saat ini dan rumus model lubang jarum dibalik untuk menghitung panjang fokus kamera. Hanya valid jika pengguna berdiri tepat di jarak 50 cm.
- **`kamera.release()` dan `cv2.destroyAllWindows()`** — Menutup akses ke kamera dan menghancurkan semua jendela OpenCV. Tanpa ini, kamera bisa tetap aktif di latar belakang setelah program selesai.

### 🎙️ Kalimat untuk Video

> *"Di akhir setiap frame, program menampilkan hasil ke jendela kamera dan menunggu input keyboard. Tombol Q atau Esc untuk keluar, M untuk mematikan suara, K untuk kalibrasi jarak, P untuk jeda sementara, dan C untuk mengubah mode CLAHE. Setelah loop berakhir, kamera dilepaskan dan semua jendela ditutup agar tidak ada resource yang tertinggal."*

---

## Ringkasan Alur Kode

```
main.py
│
├─ [1] Import & Konstanta
│
├─ [2] Persiapan sistem (folder, log, LBPH, BlazeFace, kamera, slider)
│
├─ [3] Definisi fungsi-fungsi pembantu
│
├─ [4] Inisialisasi variabel kontrol status
│
└─ [5-8] LOOP UTAMA (while True):
      ├─ Baca slider
      ├─ Baca frame → flip → ukur kecerahan → CLAHE (jika perlu)
      ├─ BlazeFace → deteksi wajah
      ├─ LBPH → identifikasi pemilik
      ├─ Hitung jarak + yaw tiap orang lain
      ├─ status_mentah → stabilisasi waktu → status_aktif
      ├─ Tindakan (overlay/alarm/foto/log) jika status berubah
      ├─ Gambar pita status + telemetri di frame
      ├─ cv2.imshow (kamera + overlay)
      └─ cv2.waitKey → proses tombol (Q/Esc/M/K/P/C)
         └─ Jika Q/Esc → break → kamera.release() → destroyAllWindows()
```

# Sistem Pelindung Privasi Layar

**Judul Proyek:**  
Sistem Pelindung Privasi Layar Berbasis Deteksi Wajah dengan Penilaian Arah Pandang dan Jarak untuk Mencegah Pengintipan

**Mata Kuliah:** Pengolahan Citra Digital  
**Platform:** Windows 10/11 | Python 3.10+

---

## Deskripsi

Proyek ini membangun sistem yang secara otomatis **melindungi privasi layar komputer** saat ada orang lain yang terdeteksi mengintip. Sistem menggunakan webcam untuk mendeteksi wajah secara real-time, lalu menilai jarak dan arah pandang setiap orang yang terdeteksi. Jika ada ancaman pengintipan, layar dikaburkan secara otomatis dan alarm berbunyi.

---

## Rumusan Masalah

1. Bagaimana mendeteksi keberadaan wajah di sekitar pengguna secara real-time dengan webcam?
2. Bagaimana membedakan pemilik komputer dari orang asing menggunakan pengenalan wajah?
3. Bagaimana mengukur jarak dan menilai arah pandang orang lain tanpa sensor tambahan?
4. Bagaimana merespons ancaman (pengintipan) dengan menutup layar secara otomatis?
5. Bagaimana kinerja sistem dalam kondisi cahaya redup?

---

## Alur Sistem

```
Webcam → Frame BGR
    │
    ├─ Hitung kecerahan → jika redup → CLAHE (peningkatan kontras adaptif)
    │
    ├─ BlazeFace (MediaPipe) → daftar kotak bounding box + keypoint wajah
    │
    ├─ LBPH (OpenCV) → identifikasi pemilik (confidence ≤ AMBANG_CONFIDENCE)
    │        └─ Jika model tidak ada → fallback: wajah terbesar = pemilik
    │
    ├─ Tiap wajah bukan pemilik → hitung jarak (model lubang jarum) + yaw (arah pandang)
    │
    ├─ Evaluasi status mentah (AMAN/WASPADA/BAHAYA/PERGI/ORANG_ASING)
    │        └─ Stabilisasi berbasis waktu (tidak langsung ganti status)
    │
    └─ Tindakan sesuai status:
           • AMAN      → tampilkan kamera normal
           • WASPADA   → beep pendek sekali
           • BAHAYA    → kaburkan layar + alarm dua nada + foto kejadian + log
           • PERGI     → kaburkan layar + log
           • ORANG_ASING → kaburkan layar + alarm + foto + log
```

---

## Cara Memasang

### 1. Prasyarat
- Python 3.10 atau lebih baru
- Webcam yang terhubung
- Windows 10/11 (winsound hanya tersedia di Windows)

### 2. Buat dan aktifkan virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Pasang dependensi utama

```powershell
pip install -r requirements.txt
```

### 4. Pasang dependensi dasbor (opsional)

```powershell
pip install -r requirements-dasbor.txt
```

### 5. Unduh model BlazeFace

> **Penting:** File model `models/blaze_face_short_range.tflite` **tidak disertakan** di repositori ini karena ukurannya besar dan diabaikan oleh `.gitignore`.

Unduh manual dengan salah satu cara berikut:

**Cara A — Lewat Python (direkomendasikan):**

```python
import urllib.request, os
os.makedirs("models", exist_ok=True)
url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
urllib.request.urlretrieve(url, "models/blaze_face_short_range.tflite")
print("Model berhasil diunduh.")
```

Simpan skrip di atas sebagai `unduh_model.py` lalu jalankan:

```powershell
venv\Scripts\python.exe unduh_model.py
```

**Cara B — Lewat browser:**
Buka URL berikut, klik kanan → Simpan sebagai, lalu simpan ke folder `models/`:
```
https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite
```

---

## Cara Mendaftarkan Wajah Pemilik

Langkah ini **wajib** dilakukan sebelum menjalankan program utama agar pengenalan pemilik berfungsi (mode LBPH).

```powershell
venv\Scripts\python.exe src/daftar_pemilik.py
```

- Sistem akan mengambil **30 foto wajah** secara otomatis saat tepat satu wajah terdeteksi.
- Variasikan sedikit sudut kepala dan ekspresi untuk hasil terbaik.
- Pastikan pencahayaan ruangan sama seperti saat demo.
- Foto disimpan di `data/pemilik/` dan model LBPH di `data/pemilik_model.yml` (tidak masuk git).

---

## Cara Menjalankan

### Program Utama (perlindungan layar)

```powershell
venv\Scripts\python.exe src/main.py
```

### Dasbor Log Kejadian (di terminal terpisah)

```powershell
venv\Scripts\python.exe -m streamlit run dashboard/dasbor.py
```

Lalu buka browser di `http://localhost:8501`.

---

## Daftar Tombol Keyboard

| Tombol | Fungsi |
|--------|--------|
| `Q` atau `Esc` | Keluar dari program (selalu berfungsi, termasuk saat overlay aktif) |
| `M` | Nyalakan/matikan alarm suara |
| `K` | Kalibrasi jarak fokal (berdiri di jarak 50 cm, pastikan wajah pemilik terdeteksi) |
| `P` | Jeda/lanjut perlindungan (layar dibuka, alarm tidak berbunyi saat jeda) |
| `C` | Ganti mode CLAHE: OTOMATIS → PAKSA ON → PAKSA OFF → OTOMATIS |

---

## Nilai Parameter Awal

Parameter berikut dapat diubah secara langsung lewat **slider interaktif** di jendela "Pengaturan" saat program berjalan:

| Parameter | Nilai Awal | Keterangan |
|-----------|-----------|------------|
| `AMBANG_CONFIDENCE` | 70 | Batas confidence LBPH (makin kecil = lebih ketat; cocok jika ≤ nilai ini) |
| `BATAS_JARAK_CM` | 200 | Jarak maksimal orang lain dianggap berbahaya (cm) |
| `BATAS_YAW` | 0.35 | Batas sudut yaw; wajah dianggap menghadap jika \|yaw\| ≤ nilai ini |
| `AMBANG_GELAP` | 80 | Rata-rata kecerahan (kanal V) di bawah nilai ini dianggap redup |

---

## Struktur Folder

```
pcd-privacy-screen-guard/
│
├── src/
│   ├── main.py              ← Program utama (jalankan ini)
│   ├── daftar_pemilik.py    ← Pendaftaran wajah pemilik
│   └── tahap/               ← Riwayat pengembangan bertahap (untuk belajar)
│       ├── tahap2_deteksi_wajah.py
│       ├── tahap3_status.py
│       ├── ...
│       └── tahap9_cahaya.py
│
├── dashboard/
│   └── dasbor.py            ← Dasbor visualisasi log (Streamlit)
│
├── models/
│   └── blaze_face_short_range.tflite   ← Unduh manual (diabaikan git)
│
├── data/                    ← Dibuat otomatis saat program pertama dijalankan
│   ├── log_kejadian.csv     ← Catatan log kejadian (diabaikan git)
│   ├── pemilik/             ← Foto pendaftaran pemilik (diabaikan git)
│   ├── pemilik_model.yml    ← Model LBPH terlatih (diabaikan git)
│   └── kejadian/            ← Foto otomatis saat BAHAYA/ORANG_ASING (diabaikan git)
│
├── docs/
│   ├── tabel_pengujian.md   ← Template tabel uji untuk diisi mahasiswa
│   └── penjelasan_kode.md   ← Penjelasan blok kode untuk video presentasi
│
├── requirements.txt         ← Dependensi program utama
├── requirements-dasbor.txt  ← Dependensi dasbor Streamlit
└── README.md                ← Dokumen ini
```

---

## Keterbatasan Sistem (Jujur)

| Keterbatasan | Penjelasan |
|---|---|
| **LBPH sensitif cahaya** | Jika pencahayaan saat demo berbeda dengan saat pendaftaran, pengenalan bisa gagal |
| **LBPH sensitif sudut wajah** | Wajah profil (miring >45°) sering tidak dikenali sebagai pemilik |
| **Foto di HP bisa lolos** | Foto wajah pemilik yang didekatkan ke kamera bisa dikenali sebagai pemilik asli |
| **Jarak perkiraan kasar** | Estimasi jarak menggunakan model lubang jarum; akurasi bergantung pada kalibrasi dan lebar wajah rata-rata (14 cm) |
| **Wajah profil sering gagal deteksi** | BlazeFace dirancang untuk wajah frontal; wajah miring ekstrem sering tidak terdeteksi |
| **Satu kamera** | Hanya kamera webcam tunggal yang digunakan; tidak mencakup sudut samping atau belakang |
| **Satu monitor** | Overlay layar hanya menutup monitor utama (layar primer) |
| **Pemilik harus terdaftar** | Tanpa pendaftaran, sistem berjalan dalam mode fallback (wajah terbesar dianggap pemilik) |

---

## Pengembangan Lanjutan

- Integrasi dengan kamera sudut lebar atau multi-kamera
- Pengenalan wajah berbasis deep learning (ArcFace, FaceNet) untuk akurasi lebih tinggi
- Dukungan multi-monitor
- Enkripsi log kejadian
- Notifikasi jarak jauh (email/Telegram) saat insiden terdeteksi
- Versi lintas platform (Linux/macOS) tanpa winsound

---

> **Catatan Privasi:** Semua data wajah (foto pendaftaran, model LBPH, foto kejadian, log) disimpan hanya di lokal dalam folder `data/` dan **tidak pernah diunggah ke repositori git**.

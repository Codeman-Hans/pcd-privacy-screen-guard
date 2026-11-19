# Tahap 8: Pengenalan wajah pemilik menggunakan LBPH (Local Binary Patterns Histograms)
# Berbasis Tahap 7 (tahap7_log.py) dengan penambahan verifikasi identitas pemilik.
# Catatan penting: Metode LBPH sensitif terhadap perubahan pencahayaan dan sudut kemiringan wajah.
# Jika pencahayaan saat penggunaan berbeda drastis dengan saat pendaftaran, nilai confidence dapat meningkat.

# Mengimpor modul csv untuk menulis log kejadian ke file tabular
import csv
# Mengimpor modul os untuk memeriksa file dan folder
import os
# Mengimpor modul time untuk stabilisasi waktu, jeda, dan timestamp frame
import time
# Mengimpor datetime untuk format tanggal dan penamaan file foto kejadian
from datetime import datetime
# Mengimpor ctypes untuk mengatur DPI Awareness pada Windows
import ctypes
# Mengimpor threading agar proses membunyikan alarm tidak menghambat video kamera
import threading
# Mengimpor winsound untuk memainkan nada beep alarm Windows
import winsound
# Mengimpor OpenCV untuk pengolahan citra dan pemanggilan modul cv2.face
import cv2
# Mengimpor NumPy untuk pengolahan array matriks piksel
import numpy as np
# Mengimpor ImageGrab dari Pillow untuk menangkap layar monitor
from PIL import ImageGrab
# Mengimpor MediaPipe untuk deteksi wajah menggunakan BlazeFace
import mediapipe as mp
# Mengimpor komponen dasar MediaPipe Tasks
from mediapipe.tasks import python
# Mengimpor modul vision dari MediaPipe Tasks
from mediapipe.tasks.python import vision

# ==============================================================================
# KONSTANTA PENGATURAN
# ==============================================================================

# Menentukan lokasi file model deteksi wajah BlazeFace
MODEL_BLAZEFACE = "models/blaze_face_short_range.tflite"
# Menentukan lokasi file model pengenal wajah LBPH
FILE_MODEL_LBPH = os.path.join("data", "pemilik_model.yml")
# Menentukan dimensi seragam (lebar, tinggi) untuk cropping wajah sebelum prediksi LBPH
UKURAN_WAJAH = (200, 200)
# Menentukan batas ambang confidence LBPH (pada LBPH: makin KECIL nilainya, makin MIRIP)
# Nilai di bawah atau sama dengan ambang ini dianggap sebagai PEMILIK yang sah
AMBANG_CONFIDENCE = 70.0

# Menentukan apakah jendela penutup layar tampil satu layar penuh (tetap False untuk pengujian)
LAYAR_PENUH = False
# Menentukan faktor pengecilan citra layar sebelum diblur untuk menghemat komputasi
FAKTOR_KECIL = 0.25
# Menentukan judul jendela penutup layar
NAMA_OVERLAY = "Layar Terlindungi"
# Menentukan apakah sistem alarm audio aktif (dapat dinyalakan/dimatikan dengan tombol M)
ALARM_AKTIF = True

# Menentukan perkiraan lebar fisik wajah manusia rata-rata dalam sentimeter
LEBAR_WAJAH_CM = 14.0
# Menentukan jarak acuan saat melakukan kalibrasi fokal kamera (sentimeter)
JARAK_KALIBRASI_CM = 50.0
# Menentukan nilai awal panjang fokus kamera (diperbarui saat menekan tombol K)
FOKAL = 550.0
# Menentukan ambang jarak maksimum orang lain dianggap berisiko mendekat (sentimeter)
BATAS_JARAK_CM = 200.0
# Menentukan batas nilai yaw sudut kepala; jika di atas nilai ini maka dianggap menoleh
BATAS_YAW = 0.35

# Menentukan durasi waktu kondisi harus bertahan stabil sebelum status resmi berubah (detik)
TAHAN = {
    "AMAN": 1.0,
    "WASPADA": 0.6,
    "BAHAYA": 0.5,
    "PERGI": 1.5,
    "ORANG_ASING": 0.5,
}

# Menentukan kelompok status yang memicu penutupan layar
STATUS_TUTUP = ("BAHAYA", "PERGI", "ORANG_ASING")

# Menentukan teks keterangan untuk masing-masing status
TEKS = {
    "AMAN": "AMAN",
    "WASPADA": "WASPADA: ADA ORANG DI BELAKANG",
    "BAHAYA": "BAHAYA: ADA PENGINTIP",
    "PERGI": "PENGGUNA PERGI",
    "ORANG_ASING": "BAHAYA: PENGGUNA BUKAN PEMILIK",
}

# Menentukan warna indikator (format BGR) untuk masing-masing status
WARNA = {
    "AMAN": (0, 170, 0),
    "WASPADA": (0, 140, 255),
    "BAHAYA": (0, 0, 255),
    "PERGI": (110, 110, 110),
    "ORANG_ASING": (0, 0, 200),
}

# Menentukan lokasi berkas catatan log CSV
FILE_LOG = os.path.join("data", "log_kejadian.csv")
# Menentukan folder penyimpanan foto rekaman insiden bahaya
FOLDER_FOTO = os.path.join("data", "kejadian")
# Menentukan struktur kolom pada berkas log CSV
HEADER_LOG = ["waktu", "status", "jumlah_wajah", "jarak_terdekat_cm", "keterangan"]

# ==============================================================================
# PERSIAPAN AWAL
# ==============================================================================

# Mengaktifkan kesadaran DPI Windows agar koordinat tangkapan layar presisi
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# Memastikan folder kejadian tersedia di media penyimpanan
os.makedirs(FOLDER_FOTO, exist_ok=True)

# Membuat berkas log beserta baris judul jika belum ada
if not os.path.exists(FILE_LOG):
    with open(FILE_LOG, "w", newline="", encoding="utf-8") as f:
        penulis = csv.writer(f)
        penulis.writerow(HEADER_LOG)

# ==============================================================================
# MEMUAT MODEL PENGENAL WAJAH LBPH
# ==============================================================================

# Menyiapkan variabel objek pengenal LBPH
pengenal_lbph = None
# Penanda apakah model LBPH berhasil dimuat dan siap digunakan
mode_lbph_aktif = False

# Memeriksa ketersediaan file model LBPH yang sudah dilatih
if os.path.exists(FILE_MODEL_LBPH):
    try:
        # Membuat instance pengenal wajah LBPH
        pengenal_lbph = cv2.face.LBPHFaceRecognizer_create()
        # Membaca bobot model dari file yml
        pengenal_lbph.read(FILE_MODEL_LBPH)
        # Menandai bahwa pengenalan LBPH aktif
        mode_lbph_aktif = True
        print(f"[INFO] Model LBPH berhasil dimuat dari: {FILE_MODEL_LBPH}")
        print(f"[INFO] Ambang Confidence: {AMBANG_CONFIDENCE} (nilai <= ambang = Pemilik)")
    except Exception as e:
        print(f"[PERINGATAN] Gagal membaca model LBPH: {e}")
        print("[PERINGATAN] Mundur ke mode fallback: Wajah terbesar dianggap pemilik.")
else:
    print("=" * 70)
    print(f"[PERINGATAN] File model '{FILE_MODEL_LBPH}' tidak ditemukan!")
    print("Sistem akan berjalan dalam MODE FALLBACK (wajah terbesar = pemilik).")
    print("Untuk mengaktifkan pengenalan wajah asli, jalankan terlebih dahulu:")
    print("  python src/daftar_pemilik.py")
    print("=" * 70)

# ==============================================================================
# FUNGSI BANTUAN
# ==============================================================================


# Fungsi untuk menghitung jarak fisik dan sudut yaw arah pandang wajah
def analisis_wajah(wajah):
    lebar_px = max(wajah.bounding_box.width, 1)
    jarak = FOKAL * LEBAR_WAJAH_CM / lebar_px
    titik = wajah.keypoints
    if len(titik) < 3:
        return jarak, 9.9
    mata_a = titik[0]  # Mata kanan pada BlazeFace
    mata_b = titik[1]  # Mata kiri pada BlazeFace
    hidung = titik[2]  # Ujung hidung
    jarak_mata = abs(mata_a.x - mata_b.x)
    if jarak_mata < 1e-6:
        return jarak, 9.9
    tengah = (mata_a.x + mata_b.x) / 2
    yaw = (hidung.x - tengah) / jarak_mata
    return jarak, yaw


# Fungsi untuk menguji apakah potongan wajah cocok dengan pemilik via LBPH
def uji_identitas_pemilik(frame_asli, kotak_wajah):
    # Jika model LBPH belum dimuat, tidak bisa melakukan prediksi
    if not mode_lbph_aktif or pengenal_lbph is None:
        return False, 999.0

    tinggi_frame, lebar_frame = frame_asli.shape[:2]
    # Mengambil koordinat pembatas dengan batas aman dalam frame
    x1 = max(0, kotak_wajah.origin_x)
    y1 = max(0, kotak_wajah.origin_y)
    x2 = min(lebar_frame, kotak_wajah.origin_x + kotak_wajah.width)
    y2 = min(tinggi_frame, kotak_wajah.origin_y + kotak_wajah.height)

    # Validasi ukuran area potongan wajah
    if (x2 - x1 < 20) or (y2 - y1 < 20):
        return False, 999.0

    # Memotong wajah dari frame bersih
    potongan = frame_asli[y1:y2, x1:x2]
    # Mengubah ke grayscale
    abu = cv2.cvtColor(potongan, cv2.COLOR_BGR2GRAY)
    # Menyamakan resolusi ke ukuran standar model
    seragam = cv2.resize(abu, UKURAN_WAJAH, interpolation=cv2.INTER_AREA)

    # Melakukan prediksi menggunakan model LBPH
    # Nilai label adalah ID (1 untuk pemilik), confidence adalah jarak perbandingan
    label, confidence = pengenal_lbph.predict(seragam)

    # Pada LBPH, nilai confidence yang lebih rendah menunjukkan kemiripan yang lebih tinggi
    adalah_pemilik = (label == 1 and confidence <= AMBANG_CONFIDENCE)
    return adalah_pemilik, confidence


# Fungsi penentu status mentah sebelum distabilkan
def status_mentah(ada_wajah, ada_pemilik, daftar_orang_lain):
    # Jika tidak ada wajah sama sekali di depan layar
    if not ada_wajah:
        return "PERGI"

    # Jika ada wajah tetapi TIDAK ADA SATUPUN yang dikenali sebagai pemilik
    if not ada_pemilik:
        return "ORANG_ASING"

    # Jika pemilik hadir dan tidak ada orang lain sama sekali
    if len(daftar_orang_lain) == 0:
        return "AMAN"

    # Jika ada orang lain di sekitar pemilik, periksa apakah ada yang mengintip
    for menghadap, dekat in daftar_orang_lain:
        if menghadap and dekat:
            return "BAHAYA"

    # Ada orang lain tetapi tidak berada dalam jarak/sudut yang membahayakan
    return "WASPADA"


# Fungsi membunyikan alarm audio di background thread
def bunyikan_alarm(jenis):
    def _bunyi():
        # Membunyikan nada darurat ganda untuk bahaya pengintip atau orang asing
        if jenis in ("BAHAYA", "ORANG_ASING"):
            winsound.Beep(1000, 200)
            winsound.Beep(1400, 300)
        else:
            # Nada beep peringatan tunggal untuk status waspada
            winsound.Beep(800, 150)
    threading.Thread(target=_bunyi, daemon=True).start()


# Fungsi menangkap tampilan monitor saat ini
def ambil_layar():
    foto = ImageGrab.grab().convert("RGB")
    rgb = np.array(foto)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


# Fungsi memberikan efek blur dan teks pada citra layar
def buramkan(layar, teks):
    tinggi, lebar = layar.shape[:2]
    kecil = cv2.resize(layar, None, fx=FAKTOR_KECIL, fy=FAKTOR_KECIL,
                       interpolation=cv2.INTER_AREA)
    kecil = cv2.GaussianBlur(kecil, (31, 31), 0)
    buram = cv2.resize(kecil, (lebar, tinggi), interpolation=cv2.INTER_LINEAR)
    cv2.putText(buram, teks, (50, tinggi // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 4)
    return buram


# Fungsi menyiapkan jendela overlay penutup layar
def buka_overlay():
    cv2.namedWindow(NAMA_OVERLAY, cv2.WINDOW_NORMAL)
    if LAYAR_PENUH:
        cv2.setWindowProperty(NAMA_OVERLAY, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setWindowProperty(NAMA_OVERLAY, cv2.WND_PROP_TOPMOST, 1)
    else:
        cv2.resizeWindow(NAMA_OVERLAY, 960, 540)


# Fungsi mencatat baris riwayat kejadian ke CSV
def catat_log(status, jumlah_wajah, jarak_terdekat, keterangan=""):
    waktu_teks = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    jarak_teks = f"{jarak_terdekat:.1f}" if jarak_terdekat < 9999 else "-"
    with open(FILE_LOG, "a", newline="", encoding="utf-8") as f:
        penulis = csv.writer(f)
        penulis.writerow([waktu_teks, status, jumlah_wajah, jarak_teks, keterangan])


# Fungsi menyimpan bukti rekaman citra kamera saat insiden bahaya terjadi
def simpan_foto_kejadian(frame):
    nama_file = datetime.now().strftime("kejadian_%Y%m%d_%H%M%S_%f") + ".jpg"
    path_foto = os.path.join(FOLDER_FOTO, nama_file)
    cv2.imwrite(path_foto, frame)
    return path_foto


# ==============================================================================
# INISIALISASI DETEKTOR BLAZEFACE DAN KAMERA
# ==============================================================================

opsi_blazeface = vision.FaceDetectorOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL_BLAZEFACE),
    running_mode=vision.RunningMode.VIDEO,
    min_detection_confidence=0.5,
)
detektor = vision.FaceDetector.create_from_options(opsi_blazeface)

kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not kamera.isOpened():
    print("Error: Kamera tidak dapat dibuka!")
    raise SystemExit

# ==============================================================================
# VARIABEL STATUS DAN PELACAKAN WAKTU
# ==============================================================================

status_aktif = "AMAN"
status_lama = "AMAN"
kandidat = None
waktu_kandidat = 0.0

layar_asli = None
gambar_buram = None
waktu_pesan = -10.0

sedang_jeda = False
path_foto_terakhir = ""
waktu_foto_terakhir = -10.0
jarak_terdekat_frame = 9999.0

waktu_mulai = time.time()
ts_terakhir = -1

# ==============================================================================
# SIKLUS UTAMA APLIKASI
# ==============================================================================

while True:
    ok, frame = kamera.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)
    frame_bersih = frame.copy()

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    gambar_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    sekarang = time.time()
    ts = int((sekarang - waktu_mulai) * 1000)
    if ts <= ts_terakhir:
        ts = ts_terakhir + 1
    ts_terakhir = ts

    # Deteksi wajah menggunakan model BlazeFace
    hasil = detektor.detect_for_video(gambar_mp, ts)
    daftar_wajah = hasil.detections
    jumlah_wajah = len(daftar_wajah)

    # Identifikasi pemilik berdasarkan mode aktif
    pemilik = None
    data_evaluasi_wajah = []

    if mode_lbph_aktif:
        # MODE LBPH: Evaluasi tiap wajah dengan model pengenal
        kandidat_pemilik = []
        for wajah in daftar_wajah:
            cocok, skor_conf = uji_identitas_pemilik(frame_bersih, wajah.bounding_box)
            data_evaluasi_wajah.append((wajah, cocok, skor_conf))
            if cocok:
                # Kumpulkan semua wajah yang lolos ambang batas
                kandidat_pemilik.append((wajah, skor_conf))

        # Jika ada wajah yang cocok, pilih yang confidence paling kecil (paling mirip)
        if len(kandidat_pemilik) > 0:
            kandidat_pemilik.sort(key=lambda item: item[1])
            pemilik = kandidat_pemilik[0][0]
    else:
        # MODE FALLBACK: Jika model belum ada, wajah terluas dianggap pemilik
        if jumlah_wajah > 0:
            pemilik = max(
                daftar_wajah,
                key=lambda f: f.bounding_box.width * f.bounding_box.height,
            )
        for wajah in daftar_wajah:
            data_evaluasi_wajah.append((wajah, wajah is pemilik, 0.0))

    # Analisis orang lain dan gambar visualisasi pada frame kamera
    daftar_orang_lain = []
    jarak_terdekat_frame = 9999.0

    for wajah, cocok_identitas, skor_conf in data_evaluasi_wajah:
        kotak = wajah.bounding_box
        x, y, w, h = kotak.origin_x, kotak.origin_y, kotak.width, kotak.height

        # Menyiapkan teks nilai confidence untuk ditampilkan (membantu tuning ambang)
        teks_conf = f"conf:{skor_conf:.1f}" if mode_lbph_aktif else "fallback"

        if wajah is pemilik:
            # Visualisasi pemilik sah (kotak hijau)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"PEMILIK ({teks_conf})", (x, max(y - 8, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        else:
            # Wajah selain pemilik (orang lain di belakang, atau orang asing di depan)
            jarak, yaw = analisis_wajah(wajah)
            menghadap = abs(yaw) <= BATAS_YAW
            dekat = jarak <= BATAS_JARAK_CM
            daftar_orang_lain.append((menghadap, dekat))

            if jarak < jarak_terdekat_frame:
                jarak_terdekat_frame = jarak

            teks_arah = "MENGHADAP" if menghadap else "MENOLEH"

            # Jika tidak ada pemilik sah di frame, semua wajah adalah orang asing
            if pemilik is None:
                warna_kotak = (0, 0, 255)
                label_kotak = f"ORANG ASING ({teks_conf})"
            else:
                warna_kotak = (0, 0, 255) if (menghadap and dekat) else (0, 140, 255)
                label_kotak = f"{jarak:.0f}cm {teks_arah} ({teks_conf})"

            cv2.rectangle(frame, (x, y), (x + w, y + h), warna_kotak, 2)
            cv2.putText(frame, label_kotak, (x, max(y - 8, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, warna_kotak, 2)

    # ------------------------------------------------------------------
    # MANAJEMEN STATUS DAN OVERLAY
    # ------------------------------------------------------------------

    if not sedang_jeda:
        # Menentukan status mentah pada frame saat ini
        mentah = status_mentah(
            ada_wajah=(jumlah_wajah > 0),
            ada_pemilik=(pemilik is not None),
            daftar_orang_lain=daftar_orang_lain,
        )

        # Proses stabilisasi status berbasis waktu
        if mentah == status_aktif:
            kandidat = None
        else:
            if mentah != kandidat:
                kandidat = mentah
                waktu_kandidat = sekarang
            elif sekarang - waktu_kandidat >= TAHAN.get(mentah, 0.5):
                status_aktif = mentah
                kandidat = None

        # Penanganan jika terjadi perubahan status resmi
        if status_aktif != status_lama:
            if status_aktif in STATUS_TUTUP:
                if status_lama not in STATUS_TUTUP:
                    layar_asli = ambil_layar()
                    buka_overlay()
                gambar_buram = buramkan(layar_asli, TEKS[status_aktif])

                # Bunyikan alarm untuk bahaya pengintip atau orang asing yang menggunakan komputer
                if status_aktif in ("BAHAYA", "ORANG_ASING") and ALARM_AKTIF:
                    bunyikan_alarm(status_aktif)

                # Ambil foto kejadian otomatis saat terdeteksi BAHAYA atau ORANG_ASING
                if status_aktif in ("BAHAYA", "ORANG_ASING"):
                    path_foto_terakhir = simpan_foto_kejadian(frame)
                    waktu_foto_terakhir = sekarang
            else:
                if status_lama in STATUS_TUTUP:
                    cv2.destroyWindow(NAMA_OVERLAY)
                if status_aktif == "WASPADA" and ALARM_AKTIF:
                    bunyikan_alarm("WASPADA")

            # Catat log resmi pergantian status ke CSV
            ket_log = f"Berubah dari {status_lama}"
            if not mode_lbph_aktif:
                ket_log += " (mode fallback)"
            catat_log(
                status=status_aktif,
                jumlah_wajah=jumlah_wajah,
                jarak_terdekat=jarak_terdekat_frame,
                keterangan=ket_log,
            )
            status_lama = status_aktif

    # ------------------------------------------------------------------
    # TAMPILAN INFORMASI PADA FRAME KAMERA
    # ------------------------------------------------------------------

    warna_pita = (60, 60, 60) if sedang_jeda else WARNA.get(status_aktif, (0, 0, 0))
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), warna_pita, -1)

    if sedang_jeda:
        cv2.putText(frame, "PERLINDUNGAN DIJEDA", (10, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    else:
        cv2.putText(frame, TEKS.get(status_aktif, status_aktif), (10, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

    teks_layar = "TERTUTUP" if (status_aktif in STATUS_TUTUP and not sedang_jeda) else "TERBUKA"
    teks_suara = "ON" if ALARM_AKTIF else "OFF"
    teks_jeda = "JEDA" if sedang_jeda else "AKTIF"
    teks_mode = "LBPH" if mode_lbph_aktif else "FALLBACK"

    cv2.putText(frame,
                f"Wajah: {jumlah_wajah} | Layar: {teks_layar} | Suara: {teks_suara} | Mode: {teks_mode}",
                (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2)

    # Menampilkan peringatan jelas jika mode LBPH tidak aktif
    if not mode_lbph_aktif:
        cv2.putText(frame, "PERINGATAN: Model LBPH belum ada! Jalankan daftar_pemilik.py",
                    (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

    if sekarang - waktu_pesan < 2.0:
        cv2.putText(frame, f"Kalibrasi OK (fokal={FOKAL:.0f})", (10, 125),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    if sekarang - waktu_foto_terakhir < 2.0:
        nama_foto = os.path.basename(path_foto_terakhir)
        cv2.putText(frame, f"Foto Tersimpan: {nama_foto}", (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 2)

    cv2.putText(frame, "Q/Esc: keluar | M: suara | K: kalibrasi | P: jeda",
                (10, frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1)

    # Menampilkan frame kamera
    cv2.imshow("Tahap 8 - Kamera", frame)

    # Menampilkan overlay layar buram jika status mensyaratkan
    if status_aktif in STATUS_TUTUP and not sedang_jeda and gambar_buram is not None:
        cv2.imshow(NAMA_OVERLAY, gambar_buram)

    # ------------------------------------------------------------------
    # PEMROSESAN TOMBOL KEYBOARD
    # ------------------------------------------------------------------

    tombol = cv2.waitKey(1) & 0xFF
    if tombol == ord("q") or tombol == 27:
        catat_log(
            status=status_aktif,
            jumlah_wajah=jumlah_wajah,
            jarak_terdekat=jarak_terdekat_frame,
            keterangan="Program dihentikan pengguna",
        )
        break

    if tombol == ord("m"):
        ALARM_AKTIF = not ALARM_AKTIF

    # Kalibrasi fokal menggunakan pemilik yang teridentifikasi
    if tombol == ord("k") and pemilik is not None:
        FOKAL = (pemilik.bounding_box.width * JARAK_KALIBRASI_CM / LEBAR_WAJAH_CM)
        waktu_pesan = sekarang

    if tombol == ord("p"):
        sedang_jeda = not sedang_jeda
        if sedang_jeda:
            if status_aktif in STATUS_TUTUP:
                cv2.destroyWindow(NAMA_OVERLAY)
            catat_log(
                status=status_aktif,
                jumlah_wajah=jumlah_wajah,
                jarak_terdekat=jarak_terdekat_frame,
                keterangan="Perlindungan dijeda oleh pengguna (tombol P)",
            )
        else:
            status_lama = status_aktif
            catat_log(
                status=status_aktif,
                jumlah_wajah=jumlah_wajah,
                jarak_terdekat=jarak_terdekat_frame,
                keterangan="Perlindungan dilanjutkan oleh pengguna (tombol P)",
            )

kamera.release()
cv2.destroyAllWindows()

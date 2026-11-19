# Tahap 9: Peningkatan citra cahaya redup (CLAHE) dan pengaturan parameter interaktif (Slider)
# Berbasis Tahap 8 (tahap8_pemilik.py) dengan penambahan pengolahan kontras adaptif dan GUI trackbar.
# Catatan penting: CLAHE (Contrast Limited Adaptive Histogram Equalization) meningkatkan kecerahan
# dan ketajaman fitur wajah di kondisi gelap, sehingga deteksi BlazeFace tetap optimal.
# Namun, peningkatan kontras dapat sedikit menggeser nilai confidence pada LBPH karena variasi gradien piksel.

# Mengimpor modul csv untuk menulis berkas catatan kejadian tabular
import csv
# Mengimpor modul os untuk memeriksa ketersediaan berkas dan folder
import os
# Mengimpor modul time untuk stabilisasi waktu, jeda, dan perhitungan timestamp frame
import time
# Mengimpor datetime untuk format penanggalan dan penamaan file rekaman insiden
from datetime import datetime
# Mengimpor ctypes untuk mengaktifkan kesadaran DPI layar Windows
import ctypes
# Mengimpor threading agar pemutaran suara alarm tidak menghambat thread visual utama
import threading
# Mengimpor winsound untuk membunyikan frekuensi nada peringatan Windows
import winsound
# Mengimpor OpenCV untuk pemrosesan citra, ruang warna, detektor, dan antarmuka jendela
import cv2
# Mengimpor NumPy untuk kalkulasi matriks citra dan statistik kecerahan
import numpy as np
# Mengimpor ImageGrab dari Pillow untuk merekam citra desktop pengguna
from PIL import ImageGrab
# Mengimpor MediaPipe untuk menjalankan modul deteksi wajah BlazeFace
import mediapipe as mp
# Mengimpor komponen dasar MediaPipe Tasks
from mediapipe.tasks import python
# Mengimpor modul vision dari MediaPipe Tasks
from mediapipe.tasks.python import vision

# ==============================================================================
# KONSTANTA PENGATURAN AWAL
# ==============================================================================

# Menentukan lokasi berkas model deteksi wajah BlazeFace
MODEL_BLAZEFACE = "models/blaze_face_short_range.tflite"
# Menentukan lokasi berkas model pengenal wajah pemilik format YAML hasil pelatihan
FILE_MODEL_LBPH = os.path.join("data", "pemilik_model.yml")
# Menentukan dimensi baku potongan wajah untuk pengujian model LBPH
UKURAN_WAJAH = (200, 200)

# Menentukan nilai ambang confidence LBPH awal (makin kecil = makin mirip)
AMBANG_CONFIDENCE_AWAL = 70
# Menentukan nilai ambang kecerahan awal; di bawah nilai ini dianggap cahaya redup
AMBANG_GELAP_AWAL = 80
# Menentukan batas nilai yaw awal (wajah menghadap jika |yaw| <= BATAS_YAW)
BATAS_YAW_AWAL = 0.35
# Menentukan batas jarak maksimal orang lain dianggap dekat (sentimeter) awal
BATAS_JARAK_CM_AWAL = 200

# Menentukan apakah jendela penutup layar tampil satu layar penuh (tetap False untuk pengujian)
LAYAR_PENUH = False
# Menentukan faktor pengecilan citra layar sebelum diblur untuk mempercepat komputasi
FAKTOR_KECIL = 0.25
# Menentukan nama jendela penutup layar
NAMA_OVERLAY = "Layar Terlindungi"
# Menentukan nama jendela khusus untuk kendali slider / trackbar
NAMA_JENDELA_SLIDER = "Pengaturan"
# Menentukan apakah alarm suara aktif saat pertama kali dijalankan
ALARM_AKTIF = True

# Menentukan lebar fisik wajah nyata rata-rata manusia dalam sentimeter
LEBAR_WAJAH_CM = 14.0
# Menentukan jarak standar saat melakukan kalibrasi fokal kamera (sentimeter)
JARAK_KALIBRASI_CM = 50.0
# Menentukan nilai awal panjang fokus kamera (diperbarui saat tombol K ditekan)
FOKAL = 550.0

# Menentukan durasi waktu kondisi harus bertahan stabil sebelum status resmi berganti (detik)
TAHAN = {
    "AMAN": 1.0,
    "WASPADA": 0.6,
    "BAHAYA": 0.5,
    "PERGI": 1.5,
    "ORANG_ASING": 0.5,
}

# Menentukan daftar status yang memicu penutupan layar monitor
STATUS_TUTUP = ("BAHAYA", "PERGI", "ORANG_ASING")

# Menentukan teks label yang ditampilkan untuk masing-masing status
TEKS = {
    "AMAN": "AMAN",
    "WASPADA": "WASPADA: ADA ORANG DI BELAKANG",
    "BAHAYA": "BAHAYA: ADA PENGINTIP",
    "PERGI": "PENGGUNA PERGI",
    "ORANG_ASING": "BAHAYA: PENGGUNA BUKAN PEMILIK",
}

# Menentukan warna indikator visual (format BGR) untuk tiap status
WARNA = {
    "AMAN": (0, 170, 0),
    "WASPADA": (0, 140, 255),
    "BAHAYA": (0, 0, 255),
    "PERGI": (110, 110, 110),
    "ORANG_ASING": (0, 0, 200),
}

# Menentukan jalur penyimpanan catatan log CSV
FILE_LOG = os.path.join("data", "log_kejadian.csv")
# Menentukan jalur folder penyimpanan foto insiden pengintipan / orang asing
FOLDER_FOTO = os.path.join("data", "kejadian")
# Menentukan nama-nama kolom tabel log kejadian
HEADER_LOG = ["waktu", "status", "jumlah_wajah", "jarak_terdekat_cm", "keterangan"]

# ==============================================================================
# PERSIAPAN AWAL SISTEM
# ==============================================================================

# Mengaktifkan kesadaran DPI sistem Windows agar tangkapan layar presisi dan tidak terpotong
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# Membuat folder rekaman kejadian jika belum ada
os.makedirs(FOLDER_FOTO, exist_ok=True)

# Membuat berkas log beserta baris judulnya jika berkas belum ada di direktori
if not os.path.exists(FILE_LOG):
    with open(FILE_LOG, "w", newline="", encoding="utf-8") as f:
        penulis = csv.writer(f)
        penulis.writerow(HEADER_LOG)

# ==============================================================================
# INISIALISASI MODEL LBPH DAN DETEKTOR BLAZEFACE
# ==============================================================================

# Menyiapkan variabel penampung model pengenal LBPH
pengenal_lbph = None
# Penanda apakah sistem pengenalan wajah LBPH siap dan aktif
mode_lbph_aktif = False

# Memeriksa ketersediaan berkas model LBPH hasil pelatihan
if os.path.exists(FILE_MODEL_LBPH):
    try:
        # Menginstansiasi objek pengenal wajah LBPH dari modul cv2.face
        pengenal_lbph = cv2.face.LBPHFaceRecognizer_create()
        # Memuat parameter bobot model dari berkas yml
        pengenal_lbph.read(FILE_MODEL_LBPH)
        # Menandai bahwa mode LBPH berhasil diaktifkan
        mode_lbph_aktif = True
        print(f"[INFO] Model LBPH berhasil dimuat dari: {FILE_MODEL_LBPH}")
    except Exception as e:
        print(f"[PERINGATAN] Gagal membaca model LBPH: {e}")
        print("[PERINGATAN] Berpindah ke mode fallback: Wajah terbesar dianggap pemilik.")
else:
    print("=" * 70)
    print(f"[PERINGATAN] File model '{FILE_MODEL_LBPH}' tidak ditemukan!")
    print("Sistem akan berjalan dalam MODE FALLBACK (wajah terbesar = pemilik).")
    print("Untuk mendaftarkan wajah Anda, jalankan: python src/daftar_pemilik.py")
    print("=" * 70)

# Menyiapkan konfigurasi opsi detektor wajah BlazeFace
opsi_blazeface = vision.FaceDetectorOptions(
    base_options=python.BaseOptions(model_asset_path=MODEL_BLAZEFACE),
    running_mode=vision.RunningMode.VIDEO,
    min_detection_confidence=0.5,
)
# Membangun objek detektor wajah dari opsi
detektor = vision.FaceDetector.create_from_options(opsi_blazeface)

# Membuka kamera webcam bawaan (indeks 0) dengan backend DirectShow Windows
kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
# Memeriksa keberhasilan inisialisasi kamera
if not kamera.isOpened():
    print("Error: Kamera tidak dapat dibuka!")
    raise SystemExit

# ==============================================================================
# PENGATURAN JENDELA SLIDER (TRACKBAR)
# ==============================================================================


# Fungsi callback kosong yang diwajibkan oleh cv2.createTrackbar
def _callback_slider(pos):
    pass


# Membuat jendela terpisah untuk meletakkan slider pengaturan
cv2.namedWindow(NAMA_JENDELA_SLIDER, cv2.WINDOW_NORMAL)
# Mengatur ukuran jendela slider agar rapi dan mudah dijangkau
cv2.resizeWindow(NAMA_JENDELA_SLIDER, 420, 220)

# Membuat trackbar untuk batas yaw sudut kepala (rentang nilai integer 10 - 100 mewakili 0.10 - 1.00)
# Nilai pada trackbar dikalikan 100 karena OpenCV hanya menerima nilai integer
cv2.createTrackbar("Batas Yaw x100", NAMA_JENDELA_SLIDER, int(BATAS_YAW_AWAL * 100), 100, _callback_slider)
# Membuat trackbar untuk batas jarak pengintip dalam cm (rentang 50 - 400 cm)
cv2.createTrackbar("Batas Jarak (cm)", NAMA_JENDELA_SLIDER, BATAS_JARAK_CM_AWAL, 400, _callback_slider)
# Membuat trackbar untuk ambang batas confidence LBPH (rentang 30 - 120)
cv2.createTrackbar("Ambang Conf LBPH", NAMA_JENDELA_SLIDER, AMBANG_CONFIDENCE_AWAL, 120, _callback_slider)
# Membuat trackbar untuk ambang batas kecerahan redup (rentang 20 - 150)
cv2.createTrackbar("Ambang Kecerahan", NAMA_JENDELA_SLIDER, AMBANG_GELAP_AWAL, 150, _callback_slider)

# Menyiapkan objek CLAHE (Contrast Limited Adaptive Histogram Equalization)
# clipLimit=2.0 mencegah penguatan noise berlebih, tileGridSize=(8, 8) membagi citra ke dalam blok lokal
clahe_objek = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

# ==============================================================================
# FUNGSI PEMROSESAN CITRA DAN ALGORITMA
# ==============================================================================


# Fungsi menghitung nilai kecerahan rata-rata frame kamera
def hitung_kecerahan(frame_bgr):
    # Mengonversi citra BGR ke ruang warna HSV
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    # Mengambil kanal V (Value / Tingkat Kecerahan)
    kanal_v = hsv[:, :, 2]
    # Menghitung nilai rata-rata kecerahan dari seluruh piksel kanal V
    return float(np.mean(kanal_v))


# Fungsi meningkatkan kontras citra pada kondisi cahaya redup menggunakan CLAHE
def perbaiki_cahaya_clahe(frame_bgr):
    # Mengonversi citra BGR ke ruang warna LAB (L = Luminansi / Kecerahan, A & B = Krominansi / Warna)
    lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    # Memisahkan kanal L, A, dan B menjadi komponen terpisah
    kanal_l, kanal_a, kanal_b = cv2.split(lab)
    # Menerapkan algoritma perataan histogram adaptif (CLAHE) hanya pada kanal kecerahan L
    kanal_l_clahe = clahe_objek.apply(kanal_l)
    # Menggabungkan kembali kanal L yang sudah diperbaiki dengan kanal warna A dan B asli
    lab_hasil = cv2.merge((kanal_l_clahe, kanal_a, kanal_b))
    # Mengembalikan format citra kembali ke BGR agar kompatibel dengan OpenCV dan MediaPipe
    return cv2.cvtColor(lab_hasil, cv2.COLOR_LAB2BGR)


# Fungsi analisis jarak fokal dan estimasi sudut rotasi yaw wajah
def analisis_wajah(wajah, fokal_aktif):
    lebar_px = max(wajah.bounding_box.width, 1)
    jarak = fokal_aktif * LEBAR_WAJAH_CM / lebar_px
    titik = wajah.keypoints
    if len(titik) < 3:
        return jarak, 9.9
    mata_a = titik[0]  # Titik mata kanan
    mata_b = titik[1]  # Titik mata kiri
    hidung = titik[2]  # Titik ujung hidung
    jarak_mata = abs(mata_a.x - mata_b.x)
    if jarak_mata < 1e-6:
        return jarak, 9.9
    tengah = (mata_a.x + mata_b.x) / 2
    yaw = (hidung.x - tengah) / jarak_mata
    return jarak, yaw


# Fungsi verifikasi identitas pemilik menggunakan model pengenal LBPH
def uji_identitas_pemilik(frame_asli, kotak_wajah, ambang_conf_aktif):
    if not mode_lbph_aktif or pengenal_lbph is None:
        return False, 999.0

    tinggi_frame, lebar_frame = frame_asli.shape[:2]
    x1 = max(0, kotak_wajah.origin_x)
    y1 = max(0, kotak_wajah.origin_y)
    x2 = min(lebar_frame, kotak_wajah.origin_x + kotak_wajah.width)
    y2 = min(tinggi_frame, kotak_wajah.origin_y + kotak_wajah.height)

    if (x2 - x1 < 20) or (y2 - y1 < 20):
        return False, 999.0

    # Potong wajah dari frame asli bersih (tanpa garis gambar)
    potongan = frame_asli[y1:y2, x1:x2]
    # Konversi ke skala abu-abu seperti prosedur saat pendaftaran
    abu = cv2.cvtColor(potongan, cv2.COLOR_BGR2GRAY)
    # Samakan ukuran resolusi ke 200x200 piksel
    seragam = cv2.resize(abu, UKURAN_WAJAH, interpolation=cv2.INTER_AREA)

    # Prediksi menggunakan model LBPH
    label, confidence = pengenal_lbph.predict(seragam)
    adalah_pemilik = (label == 1 and confidence <= ambang_conf_aktif)
    return adalah_pemilik, confidence


# Fungsi evaluasi kondisi frame untuk menentukan status keamanan mentah
def status_mentah(ada_wajah, ada_pemilik, daftar_orang_lain):
    if not ada_wajah:
        return "PERGI"
    if not ada_pemilik:
        return "ORANG_ASING"
    if len(daftar_orang_lain) == 0:
        return "AMAN"
    for menghadap, dekat in daftar_orang_lain:
        if menghadap and dekat:
            return "BAHAYA"
    return "WASPADA"


# Fungsi membunyikan audio alarm nada peringatan di thread terpisah
def bunyikan_alarm(jenis):
    def _bunyi():
        if jenis in ("BAHAYA", "ORANG_ASING"):
            winsound.Beep(1000, 200)
            winsound.Beep(1400, 300)
        else:
            winsound.Beep(800, 150)
    threading.Thread(target=_bunyi, daemon=True).start()


# Fungsi menangkap citra tampilan monitor saat ini
def ambil_layar():
    foto = ImageGrab.grab().convert("RGB")
    rgb = np.array(foto)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


# Fungsi memberikan efek blur Gaussian dan teks peringatan pada citra layar
def buramkan(layar, teks):
    tinggi, lebar = layar.shape[:2]
    kecil = cv2.resize(layar, None, fx=FAKTOR_KECIL, fy=FAKTOR_KECIL,
                       interpolation=cv2.INTER_AREA)
    kecil = cv2.GaussianBlur(kecil, (31, 31), 0)
    buram = cv2.resize(kecil, (lebar, tinggi), interpolation=cv2.INTER_LINEAR)
    cv2.putText(buram, teks, (50, tinggi // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 4)
    return buram


# Fungsi membuka dan mengonfigurasi jendela overlay penutup layar
def buka_overlay():
    cv2.namedWindow(NAMA_OVERLAY, cv2.WINDOW_NORMAL)
    if LAYAR_PENUH:
        cv2.setWindowProperty(NAMA_OVERLAY, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setWindowProperty(NAMA_OVERLAY, cv2.WND_PROP_TOPMOST, 1)
    else:
        cv2.resizeWindow(NAMA_OVERLAY, 960, 540)


# Fungsi mencatat pergantian status resmi ke dalam berkas log CSV
def catat_log(status, jumlah_wajah, jarak_terdekat, keterangan=""):
    waktu_teks = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    jarak_teks = f"{jarak_terdekat:.1f}" if jarak_terdekat < 9999 else "-"
    with open(FILE_LOG, "a", newline="", encoding="utf-8") as f:
        penulis = csv.writer(f)
        penulis.writerow([waktu_teks, status, jumlah_wajah, jarak_teks, keterangan])


# Fungsi menyimpan bukti citra frame kamera saat terjadi bahaya pengintipan / orang asing
def simpan_foto_kejadian(frame):
    nama_file = datetime.now().strftime("kejadian_%Y%m%d_%H%M%S_%f") + ".jpg"
    path_foto = os.path.join(FOLDER_FOTO, nama_file)
    cv2.imwrite(path_foto, frame)
    return path_foto


# ==============================================================================
# VARIABEL KONTROL DAN STATUS WAKTU NYATA
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

# Pengaturan mode peningkatan citra cahaya redup: "OTOMATIS", "PAKSA_ON", atau "PAKSA_OFF"
mode_cahaya = "OTOMATIS"
# Penanda apakah pada frame saat ini perbaikan CLAHE sedang benar-benar diterapkan
clahe_sedang_aktif = False

waktu_mulai = time.time()
ts_terakhir = -1

# ==============================================================================
# SIKLUS UTAMA SISTEM (MAIN LOOP)
# ==============================================================================

while True:
    # ------------------------------------------------------------------
    # PEMBACAAN NILAI DINAMIS DARI SLIDER (TRACKBAR)
    # ------------------------------------------------------------------

    # Membaca nilai batas yaw dari trackbar dan mengonversi kembali ke desimal
    pos_yaw = cv2.getTrackbarPos("Batas Yaw x100", NAMA_JENDELA_SLIDER)
    # Mencegah nilai nol agar perhitungan perbandingan valid (minimal 0.10)
    batas_yaw_aktif = max(10, pos_yaw) / 100.0

    # Membaca batas jarak dalam cm (minimal 50 cm)
    pos_jarak = cv2.getTrackbarPos("Batas Jarak (cm)", NAMA_JENDELA_SLIDER)
    batas_jarak_aktif = float(max(50, pos_jarak))

    # Membaca ambang batas confidence LBPH (minimal 30)
    pos_conf = cv2.getTrackbarPos("Ambang Conf LBPH", NAMA_JENDELA_SLIDER)
    ambang_conf_aktif = float(max(30, pos_conf))

    # Membaca ambang batas kecerahan redup (minimal 20)
    pos_gelap = cv2.getTrackbarPos("Ambang Kecerahan", NAMA_JENDELA_SLIDER)
    ambang_gelap_aktif = float(max(20, pos_gelap))

    # Menampilkan visual kanvas mini pada jendela slider agar jendela ter-refresh
    kanvas_slider = np.full((120, 420, 3), 40, dtype=np.uint8)
    cv2.putText(kanvas_slider, f"Yaw: {batas_yaw_aktif:.2f} | Jarak: {batas_jarak_aktif:.0f}cm", (15, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.putText(kanvas_slider, f"Ambang Conf: {ambang_conf_aktif:.0f} | Ambang Gelap: {ambang_gelap_aktif:.0f}", (15, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.imshow(NAMA_JENDELA_SLIDER, kanvas_slider)

    # ------------------------------------------------------------------
    # PEMBACAAN FRAME DAN PENINGKATAN CAHAYA REDUP (CLAHE)
    # ------------------------------------------------------------------

    ok, frame = kamera.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)

    # Menghitung nilai kecerahan rata-rata frame asli sebelum dimodifikasi
    kecerahan_sekarang = hitung_kecerahan(frame)

    # Menentukan apakah filter CLAHE perlu diterapkan berdasarkan mode cahaya
    if mode_cahaya == "PAKSA_ON":
        clahe_sedang_aktif = True
    elif mode_cahaya == "PAKSA_OFF":
        clahe_sedang_aktif = False
    else:
        # Mode OTOMATIS: aktifkan jika kecerahan lebih rendah dari ambang slider
        clahe_sedang_aktif = (kecerahan_sekarang < ambang_gelap_aktif)

    # Jika CLAHE aktif, tingkatkan kontras frame untuk memudahkan deteksi BlazeFace
    if clahe_sedang_aktif:
        frame_terproses = perbaiki_cahaya_clahe(frame)
    else:
        frame_terproses = frame.copy()

    # Menyimpan frame terproses bersih untuk keperluan cropping wajah LBPH
    frame_bersih = frame_terproses.copy()

    # ------------------------------------------------------------------
    # DETEKSI WAJAH DENGAN MEDIAPIPE BLAZEFACE
    # ------------------------------------------------------------------

    rgb = cv2.cvtColor(frame_terproses, cv2.COLOR_BGR2RGB)
    gambar_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    sekarang = time.time()
    ts = int((sekarang - waktu_mulai) * 1000)
    if ts <= ts_terakhir:
        ts = ts_terakhir + 1
    ts_terakhir = ts

    hasil = detektor.detect_for_video(gambar_mp, ts)
    daftar_wajah = hasil.detections
    jumlah_wajah = len(daftar_wajah)

    # ------------------------------------------------------------------
    # IDENTIFIKASI PEMILIK DAN PENILAIAN WAJAH
    # ------------------------------------------------------------------

    pemilik = None
    data_evaluasi_wajah = []

    if mode_lbph_aktif:
        kandidat_pemilik = []
        for wajah in daftar_wajah:
            cocok, skor_conf = uji_identitas_pemilik(frame_bersih, wajah.bounding_box, ambang_conf_aktif)
            data_evaluasi_wajah.append((wajah, cocok, skor_conf))
            if cocok:
                kandidat_pemilik.append((wajah, skor_conf))

        if len(kandidat_pemilik) > 0:
            kandidat_pemilik.sort(key=lambda item: item[1])
            pemilik = kandidat_pemilik[0][0]
    else:
        if jumlah_wajah > 0:
            pemilik = max(
                daftar_wajah,
                key=lambda f: f.bounding_box.width * f.bounding_box.height,
            )
        for wajah in daftar_wajah:
            data_evaluasi_wajah.append((wajah, wajah is pemilik, 0.0))

    daftar_orang_lain = []
    jarak_terdekat_frame = 9999.0

    for wajah, cocok_identitas, skor_conf in data_evaluasi_wajah:
        kotak = wajah.bounding_box
        x, y, w, h = kotak.origin_x, kotak.origin_y, kotak.width, kotak.height
        teks_conf = f"conf:{skor_conf:.1f}" if mode_lbph_aktif else "fallback"

        if wajah is pemilik:
            cv2.rectangle(frame_terproses, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame_terproses, f"PEMILIK ({teks_conf})", (x, max(y - 8, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        else:
            jarak, yaw = analisis_wajah(wajah, FOKAL)
            menghadap = abs(yaw) <= batas_yaw_aktif
            dekat = jarak <= batas_jarak_aktif
            daftar_orang_lain.append((menghadap, dekat))

            if jarak < jarak_terdekat_frame:
                jarak_terdekat_frame = jarak

            teks_arah = "MENGHADAP" if menghadap else "MENOLEH"

            if pemilik is None:
                warna_kotak = (0, 0, 255)
                label_kotak = f"ORANG ASING ({teks_conf})"
            else:
                warna_kotak = (0, 0, 255) if (menghadap and dekat) else (0, 140, 255)
                label_kotak = f"{jarak:.0f}cm {teks_arah} ({teks_conf})"

            cv2.rectangle(frame_terproses, (x, y), (x + w, y + h), warna_kotak, 2)
            cv2.putText(frame_terproses, label_kotak, (x, max(y - 8, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, warna_kotak, 2)

    # ------------------------------------------------------------------
    # EVALUASI STATUS KEAMANAN DAN OVERLAY
    # ------------------------------------------------------------------

    if not sedang_jeda:
        mentah = status_mentah(
            ada_wajah=(jumlah_wajah > 0),
            ada_pemilik=(pemilik is not None),
            daftar_orang_lain=daftar_orang_lain,
        )

        if mentah == status_aktif:
            kandidat = None
        else:
            if mentah != kandidat:
                kandidat = mentah
                waktu_kandidat = sekarang
            elif sekarang - waktu_kandidat >= TAHAN.get(mentah, 0.5):
                status_aktif = mentah
                kandidat = None

        if status_aktif != status_lama:
            if status_aktif in STATUS_TUTUP:
                if status_lama not in STATUS_TUTUP:
                    layar_asli = ambil_layar()
                    buka_overlay()
                gambar_buram = buramkan(layar_asli, TEKS[status_aktif])

                if status_aktif in ("BAHAYA", "ORANG_ASING") and ALARM_AKTIF:
                    bunyikan_alarm(status_aktif)

                if status_aktif in ("BAHAYA", "ORANG_ASING"):
                    path_foto_terakhir = simpan_foto_kejadian(frame_terproses)
                    waktu_foto_terakhir = sekarang
            else:
                if status_lama in STATUS_TUTUP:
                    cv2.destroyWindow(NAMA_OVERLAY)
                if status_aktif == "WASPADA" and ALARM_AKTIF:
                    bunyikan_alarm("WASPADA")

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
    # PENGGAMBARAN PITA STATUS DAN INFORMASI TELEMETRI
    # ------------------------------------------------------------------

    warna_pita = (60, 60, 60) if sedang_jeda else WARNA.get(status_aktif, (0, 0, 0))
    cv2.rectangle(frame_terproses, (0, 0), (frame_terproses.shape[1], 50), warna_pita, -1)

    if sedang_jeda:
        cv2.putText(frame_terproses, "PERLINDUNGAN DIJEDA", (10, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    else:
        cv2.putText(frame_terproses, TEKS.get(status_aktif, status_aktif), (10, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)

    teks_layar = "TERTUTUP" if (status_aktif in STATUS_TUTUP and not sedang_jeda) else "TERBUKA"
    teks_suara = "ON" if ALARM_AKTIF else "OFF"
    teks_mode = "LBPH" if mode_lbph_aktif else "FALLBACK"
    teks_clahe = "ON" if clahe_sedang_aktif else "OFF"

    # Menampilkan baris telemetri sistem (wajah, status layar, audio, mode identitas)
    cv2.putText(frame_terproses,
                f"Wajah: {jumlah_wajah} | Layar: {teks_layar} | Suara: {teks_suara} | Mode: {teks_mode}",
                (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2)

    # Menampilkan baris informasi kecerahan dan status fitur CLAHE
    cv2.putText(frame_terproses,
                f"Kecerahan: {kecerahan_sekarang:.1f} (ambang: {ambang_gelap_aktif:.0f}) | CLAHE [{mode_cahaya}]: {teks_clahe}",
                (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (100, 255, 100) if clahe_sedang_aktif else (180, 180, 180), 2)

    if not mode_lbph_aktif:
        cv2.putText(frame_terproses, "PERINGATAN: Model LBPH belum ada! Jalankan daftar_pemilik.py",
                    (10, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

    if sekarang - waktu_pesan < 2.0:
        cv2.putText(frame_terproses, f"Kalibrasi OK (fokal={FOKAL:.0f})", (10, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    if sekarang - waktu_foto_terakhir < 2.0:
        nama_foto = os.path.basename(path_foto_terakhir)
        cv2.putText(frame_terproses, f"Foto Kejadian: {nama_foto}", (10, 175),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 2)

    # Petunjuk tombol pintas keyboard di bagian bawah frame
    cv2.putText(frame_terproses, "Q/Esc: keluar | C: mode CLAHE | M: suara | K: kalibrasi | P: jeda",
                (10, frame_terproses.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)

    # Menampilkan frame kamera utama
    cv2.imshow("Tahap 9 - Kamera", frame_terproses)

    # Menampilkan overlay jika layar dalam kondisi tertutup
    if status_aktif in STATUS_TUTUP and not sedang_jeda and gambar_buram is not None:
        cv2.imshow(NAMA_OVERLAY, gambar_buram)

    # ------------------------------------------------------------------
    # PENANGANAN TOMBOL PINTAS KEYBOARD
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

    # Tombol C: Mengubah mode peningkatan cahaya redup (OTOMATIS -> PAKSA_ON -> PAKSA_OFF)
    if tombol == ord("c"):
        if mode_cahaya == "OTOMATIS":
            mode_cahaya = "PAKSA_ON"
        elif mode_cahaya == "PAKSA_ON":
            mode_cahaya = "PAKSA_OFF"
        else:
            mode_cahaya = "OTOMATIS"
        print(f"[KONTROL] Mode perbaikan cahaya CLAHE diubah ke: {mode_cahaya}")

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

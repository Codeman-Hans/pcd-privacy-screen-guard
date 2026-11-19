# Tahap 7: Log kejadian, tombol jeda perlindungan, dan foto otomatis saat bahaya
# Berbasis Tahap 6 (tahap6_analisis.py), semua fitur lama dipertahankan.
# Tambahan baru ditandai komentar "# [BARU]" agar mudah ditemukan.

# Mengimpor modul csv untuk menulis file log ke format spreadsheet
import csv
# Mengimpor modul os untuk membuat folder dan mengecek keberadaan file
import os
# Mengimpor time untuk cap waktu frame, stabilisasi status, dan nama file foto
import time
# Mengimpor datetime untuk mengubah cap waktu menjadi format tanggal-jam yang terbaca
from datetime import datetime
# Mengimpor ctypes untuk mengatur kesadaran DPI Windows
import ctypes
# Mengimpor threading supaya bunyi alarm tidak membekukan program
import threading
# Mengimpor winsound untuk membunyikan nada di Windows
import winsound
# Mengimpor OpenCV untuk kamera, menggambar, dan jendela
import cv2
# Mengimpor NumPy untuk operasi array citra
import numpy as np
# Mengimpor ImageGrab dari Pillow untuk menangkap layar komputer
from PIL import ImageGrab
# Mengimpor MediaPipe untuk deteksi wajah
import mediapipe as mp
# Mengimpor modul dasar MediaPipe Tasks
from mediapipe.tasks import python
# Mengimpor modul penglihatan (vision) dari MediaPipe Tasks
from mediapipe.tasks.python import vision

# ==============================================================================
# KONSTANTA PENGATURAN
# ==============================================================================

# Menentukan lokasi file model deteksi wajah
MODEL = "models/blaze_face_short_range.tflite"
# Menentukan apakah penutup tampil layar penuh; tetap False sesuai aturan proyek
LAYAR_PENUH = False
# Menentukan faktor pengecilan gambar sebelum diblur supaya lebih cepat
FAKTOR_KECIL = 0.25
# Menentukan nama jendela penutup layar
NAMA_OVERLAY = "Layar Terlindungi"
# Menentukan apakah alarm suara aktif; tombol M mengubahnya saat program jalan
ALARM_AKTIF = True

# Menentukan lebar wajah nyata rata-rata dalam sentimeter
LEBAR_WAJAH_CM = 14.0
# Menentukan jarak saat kalibrasi dalam sentimeter
JARAK_KALIBRASI_CM = 50.0
# Menentukan panjang fokus awal (diperbarui saat tombol K ditekan)
FOKAL = 550.0
# Menentukan jarak maksimal orang lain dianggap dekat (sentimeter)
BATAS_JARAK_CM = 200.0
# Menentukan batas nilai yaw; di atas ini wajah dianggap menoleh
BATAS_YAW = 0.35

# Menentukan lama kondisi harus bertahan sebelum masuk ke tiap status
TAHAN = {"AMAN": 1.0, "WASPADA": 0.6, "BAHAYA": 0.5, "PERGI": 1.5}
# Menentukan status yang membuat layar tertutup
STATUS_TUTUP = ("BAHAYA", "PERGI")
# Menentukan teks untuk tiap status
TEKS = {
    "AMAN": "AMAN",
    "WASPADA": "WASPADA: ADA ORANG DI BELAKANG",
    "BAHAYA": "BAHAYA: ADA PENGINTIP",
    "PERGI": "PENGGUNA PERGI",
}
# Menentukan warna (format BGR) untuk tiap status
WARNA = {
    "AMAN": (0, 170, 0),
    "WASPADA": (0, 140, 255),
    "BAHAYA": (0, 0, 255),
    "PERGI": (110, 110, 110),
}

# [BARU] Menentukan lokasi file log kejadian di folder data
FILE_LOG = os.path.join("data", "log_kejadian.csv")
# [BARU] Menentukan folder tempat foto kejadian bahaya disimpan
FOLDER_FOTO = os.path.join("data", "kejadian")
# [BARU] Menentukan daftar nama kolom header file log CSV
HEADER_LOG = ["waktu", "status", "jumlah_wajah", "jarak_terdekat_cm", "keterangan"]

# ==============================================================================
# PERSIAPAN AWAL
# ==============================================================================

# Mencoba membuat program sadar pada skala tampilan Windows
try:
    # Mengatur DPI aware agar tangkapan layar tidak terpotong
    ctypes.windll.user32.SetProcessDPIAware()
# Mengabaikan kalau perintah ini tidak tersedia
except Exception:
    # Tidak melakukan apa-apa
    pass

# [BARU] Membuat folder data/kejadian/ kalau belum ada
os.makedirs(FOLDER_FOTO, exist_ok=True)

# [BARU] Membuat file log dengan header kalau belum ada
if not os.path.exists(FILE_LOG):
    # Membuka file baru untuk ditulis
    with open(FILE_LOG, "w", newline="", encoding="utf-8") as f:
        # Membuat penulis CSV
        penulis = csv.writer(f)
        # Menulis baris header
        penulis.writerow(HEADER_LOG)

# ==============================================================================
# DEFINISI FUNGSI
# ==============================================================================


# Membuat fungsi yang menghitung jarak dan arah menghadap satu wajah
def analisis_wajah(wajah):
    # Mengambil lebar kotak wajah dalam piksel
    lebar_px = max(wajah.bounding_box.width, 1)
    # Menghitung perkiraan jarak dengan model kamera lubang jarum
    jarak = FOKAL * LEBAR_WAJAH_CM / lebar_px
    # Mengambil daftar titik kunci wajah
    titik = wajah.keypoints
    # Kalau titik kunci kurang dari tiga, anggap wajah menoleh jauh
    if len(titik) < 3:
        # Mengembalikan jarak dan nilai yaw yang besar
        return jarak, 9.9
    # Mengambil titik mata kanan (indeks 0 dalam urutan BlazeFace)
    mata_a = titik[0]
    # Mengambil titik mata kiri (indeks 1 dalam urutan BlazeFace)
    mata_b = titik[1]
    # Mengambil titik ujung hidung (indeks 2 dalam urutan BlazeFace)
    hidung = titik[2]
    # Menghitung jarak horizontal antara kedua mata
    # Catatan: urutan mata kanan/kiri tidak mempengaruhi rumus yaw
    # karena yang dipakai hanya titik tengah dan selisih absolut keduanya
    jarak_mata = abs(mata_a.x - mata_b.x)
    # Kalau jarak mata hampir nol, wajah dianggap menoleh jauh
    if jarak_mata < 1e-6:
        # Mengembalikan jarak dan nilai yaw yang besar
        return jarak, 9.9
    # Menghitung titik tengah kedua mata secara horizontal
    tengah = (mata_a.x + mata_b.x) / 2
    # Menghitung yaw: pergeseran hidung dari tengah dibagi jarak mata
    # yaw mendekati 0 berarti hidung tepat di tengah = wajah menghadap kamera
    yaw = (hidung.x - tengah) / jarak_mata
    # Mengembalikan jarak dan yaw
    return jarak, yaw


# Membuat fungsi yang menentukan status mentah (sebelum distabilkan)
def status_mentah(pemilik, daftar_lain):
    # Kalau tidak ada pemilik, berarti tidak ada wajah sama sekali
    if pemilik is None:
        # Mengembalikan status pengguna pergi
        return "PERGI"
    # Kalau tidak ada orang lain, kondisi aman
    if len(daftar_lain) == 0:
        # Mengembalikan status aman
        return "AMAN"
    # Memeriksa setiap orang lain untuk mencari pengintip
    for menghadap, dekat in daftar_lain:
        # Orang yang dekat dan menghadap berarti pengintip
        if menghadap and dekat:
            # Mengembalikan status bahaya
            return "BAHAYA"
    # Ada orang lain tapi tidak dekat dan menghadap
    return "WASPADA"


# Membuat fungsi yang membunyikan alarm sesuai jenisnya
def bunyikan_alarm(jenis):
    # Membuat fungsi kecil yang berisi urutan nada
    def _bunyi():
        # Memeriksa apakah jenis alarm adalah bahaya
        if jenis == "BAHAYA":
            # Membunyikan nada 1000 Hz selama 200 milidetik
            winsound.Beep(1000, 200)
            # Membunyikan nada 1400 Hz selama 300 milidetik
            winsound.Beep(1400, 300)
        # Kalau bukan bahaya, berarti waspada
        else:
            # Membunyikan satu nada pendek 800 Hz
            winsound.Beep(800, 150)
    # Menjalankan urutan nada di thread terpisah supaya kamera tidak macet
    threading.Thread(target=_bunyi, daemon=True).start()


# Membuat fungsi yang menangkap layar komputer menjadi gambar OpenCV
def ambil_layar():
    # Mengambil tangkapan layar dan memastikan formatnya RGB
    foto = ImageGrab.grab().convert("RGB")
    # Mengubah gambar Pillow menjadi array NumPy
    rgb = np.array(foto)
    # Mengubah warna RGB menjadi BGR supaya sesuai dengan OpenCV
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


# Membuat fungsi yang mengaburkan layar dan menulis peringatan
def buramkan(layar, teks):
    # Mengambil tinggi dan lebar gambar layar
    tinggi, lebar = layar.shape[:2]
    # Mengecilkan gambar supaya proses blur lebih cepat
    kecil = cv2.resize(layar, None, fx=FAKTOR_KECIL, fy=FAKTOR_KECIL,
                       interpolation=cv2.INTER_AREA)
    # Mengaburkan gambar kecil dengan Gaussian blur
    kecil = cv2.GaussianBlur(kecil, (31, 31), 0)
    # Membesarkan kembali ke ukuran layar asli
    buram = cv2.resize(kecil, (lebar, tinggi),
                       interpolation=cv2.INTER_LINEAR)
    # Menulis teks peringatan di tengah layar buram
    cv2.putText(buram, teks, (50, tinggi // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 4)
    # Mengembalikan gambar yang sudah buram
    return buram


# Membuat fungsi yang membuka jendela penutup layar
def buka_overlay():
    # Membuat jendela yang ukurannya bisa diubah
    cv2.namedWindow(NAMA_OVERLAY, cv2.WINDOW_NORMAL)
    # Memeriksa apakah mode layar penuh diaktifkan
    if LAYAR_PENUH:
        # Mengatur jendela menjadi layar penuh
        cv2.setWindowProperty(NAMA_OVERLAY, cv2.WND_PROP_FULLSCREEN,
                              cv2.WINDOW_FULLSCREEN)
        # Mengatur jendela selalu berada di atas jendela lain
        cv2.setWindowProperty(NAMA_OVERLAY, cv2.WND_PROP_TOPMOST, 1)
    # Kalau tidak layar penuh (mode uji)
    else:
        # Mengatur ukuran jendela uji menjadi 960 x 540
        cv2.resizeWindow(NAMA_OVERLAY, 960, 540)


# [BARU] Membuat fungsi yang menulis satu baris kejadian ke file log CSV
def catat_log(status, jumlah_wajah, jarak_terdekat, keterangan=""):
    # Mengambil waktu sekarang dan memformatnya menjadi teks tanggal-jam
    waktu_teks = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Membulatkan jarak ke satu desimal; tulis "-" kalau tidak ada orang lain
    jarak_teks = f"{jarak_terdekat:.1f}" if jarak_terdekat < 9999 else "-"
    # Membuka file log dalam mode tambah (append) agar baris lama tidak hilang
    with open(FILE_LOG, "a", newline="", encoding="utf-8") as f:
        # Membuat penulis CSV
        penulis = csv.writer(f)
        # Menulis satu baris dengan semua kolom yang sudah ditentukan
        penulis.writerow([waktu_teks, status, jumlah_wajah, jarak_teks, keterangan])


# [BARU] Membuat fungsi yang menyimpan frame kamera sebagai foto kejadian
def simpan_foto_kejadian(frame):
    # Membuat nama file berdasarkan cap waktu agar tidak saling menimpa
    nama_file = datetime.now().strftime("kejadian_%Y%m%d_%H%M%S_%f") + ".jpg"
    # Menggabungkan nama folder dan nama file menjadi path lengkap
    path_foto = os.path.join(FOLDER_FOTO, nama_file)
    # Menyimpan frame kamera ke disk dalam format JPEG
    cv2.imwrite(path_foto, frame)
    # Mengembalikan path foto agar bisa ditampilkan di layar
    return path_foto


# ==============================================================================
# INISIALISASI DETEKTOR DAN KAMERA
# ==============================================================================

# Membuat opsi detektor wajah
opsi = vision.FaceDetectorOptions(
    # Menunjuk file model yang dipakai
    base_options=python.BaseOptions(model_asset_path=MODEL),
    # Memakai mode VIDEO karena kita memproses frame berurutan dari kamera
    running_mode=vision.RunningMode.VIDEO,
    # Hanya menerima deteksi dengan keyakinan minimal 50 persen
    min_detection_confidence=0.5,
)
# Membuat detektor wajah dari opsi di atas
detektor = vision.FaceDetector.create_from_options(opsi)

# Membuka kamera bawaan (0) dengan backend DirectShow agar stabil di Windows
kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
# Memeriksa apakah kamera berhasil dibuka
if not kamera.isOpened():
    # Menampilkan pesan kalau kamera gagal dibuka
    print("Kamera gagal dibuka")
    # Menghentikan program
    raise SystemExit

# ==============================================================================
# VARIABEL STATUS DAN KONTROL
# ==============================================================================

# Menyimpan status yang sedang berlaku (sudah distabilkan)
status_aktif = "AMAN"
# Menyimpan status sebelumnya untuk mendeteksi perubahan
status_lama = "AMAN"
# Menyimpan status kandidat yang sedang menunggu cukup lama
kandidat = None
# Menyimpan waktu kandidat pertama kali muncul
waktu_kandidat = 0.0
# Menyimpan tangkapan layar asli saat layar ditutup
layar_asli = None
# Menyimpan gambar buram yang sedang ditampilkan
gambar_buram = None
# Menyimpan waktu pesan kalibrasi terakhir
waktu_pesan = -10.0

# [BARU] Menyimpan apakah perlindungan sedang dijeda (tombol P)
sedang_jeda = False
# [BARU] Menyimpan path foto terakhir untuk ditampilkan sebagai konfirmasi
path_foto_terakhir = ""
# [BARU] Menyimpan waktu foto terakhir untuk menampilkan pesan selama 2 detik
waktu_foto_terakhir = -10.0
# [BARU] Menyimpan jarak orang terdekat di frame ini untuk dicatat ke log
jarak_terdekat_frame = 9999.0

# Mencatat waktu mulai sebagai patokan cap waktu
waktu_mulai = time.time()
# Menyimpan cap waktu terakhir untuk memastikan selalu naik
ts_terakhir = -1

# ==============================================================================
# LOOP UTAMA
# ==============================================================================

# Mengulang membaca frame terus-menerus
while True:
    # Membaca satu frame; ok bernilai True kalau berhasil
    ok, frame = kamera.read()
    # Menghentikan loop kalau frame gagal terbaca
    if not ok:
        break

    # Membalik frame secara horizontal supaya seperti cermin
    frame = cv2.flip(frame, 1)
    # Mengubah warna BGR (OpenCV) menjadi RGB (MediaPipe)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Membungkus array RGB menjadi objek gambar milik MediaPipe
    gambar_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    # Mengambil waktu sekarang
    sekarang = time.time()
    # Menghitung cap waktu dalam milidetik sejak program dimulai
    ts = int((sekarang - waktu_mulai) * 1000)
    # Memastikan cap waktu selalu lebih besar dari sebelumnya
    if ts <= ts_terakhir:
        # Menaikkan 1 milidetik kalau sama atau lebih kecil
        ts = ts_terakhir + 1
    # Menyimpan cap waktu ini sebagai yang terakhir
    ts_terakhir = ts

    # Menjalankan deteksi wajah pada frame ini
    hasil = detektor.detect_for_video(gambar_mp, ts)
    # Mengambil daftar wajah yang terdeteksi
    daftar_wajah = hasil.detections

    # Menyiapkan variabel pemilik; awalnya belum ada
    pemilik = None
    # Memeriksa apakah ada minimal satu wajah
    if len(daftar_wajah) > 0:
        # Memilih wajah dengan luas kotak terbesar sebagai pemilik
        pemilik = max(
            daftar_wajah,
            key=lambda f: f.bounding_box.width * f.bounding_box.height,
        )

    # Menyiapkan daftar penilaian untuk orang selain pemilik
    daftar_lain = []
    # [BARU] Mengatur ulang jarak terdekat setiap frame
    jarak_terdekat_frame = 9999.0
    # Mengulang untuk setiap wajah yang terdeteksi
    for wajah in daftar_wajah:
        # Mengambil kotak pembatas wajah
        kotak = wajah.bounding_box
        # Mengambil posisi kiri atas, lebar, dan tinggi kotak
        x, y, w, h = kotak.origin_x, kotak.origin_y, kotak.width, kotak.height
        # Memeriksa apakah wajah ini adalah pemilik
        if wajah is pemilik:
            # Menggambar kotak hijau untuk pemilik
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            # Menulis label pemilik
            cv2.putText(frame, "PEMILIK", (x, max(y - 8, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        # Kalau bukan pemilik, nilai jarak dan arah menghadapnya
        else:
            # Menghitung jarak dan yaw wajah ini
            jarak, yaw = analisis_wajah(wajah)
            # Menentukan apakah orang ini menghadap ke arah kamera
            menghadap = abs(yaw) <= BATAS_YAW
            # Menentukan apakah orang ini cukup dekat
            dekat = jarak <= BATAS_JARAK_CM
            # Menyimpan hasil penilaian ke daftar
            daftar_lain.append((menghadap, dekat))
            # [BARU] Memperbarui jarak terdekat kalau orang ini lebih dekat
            if jarak < jarak_terdekat_frame:
                # Menyimpan jarak terkecil yang ditemukan di frame ini
                jarak_terdekat_frame = jarak
            # Menentukan warna kotak: merah kalau berbahaya, oranye kalau tidak
            warna = (0, 0, 255) if (menghadap and dekat) else (0, 140, 255)
            # Menyusun teks arah menghadap
            teks_arah = "MENGHADAP" if menghadap else "MENOLEH"
            # Menggambar kotak di sekeliling wajah
            cv2.rectangle(frame, (x, y), (x + w, y + h), warna, 2)
            # Menulis jarak dan arah di atas kotak
            cv2.putText(frame, f"{jarak:.0f}cm {teks_arah}",
                        (x, max(y - 8, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, warna, 2)

    # ------------------------------------------------------------------
    # LOGIKA STATUS DAN JEDA
    # ------------------------------------------------------------------

    # [BARU] Kalau perlindungan dijeda, lewati semua logika status dan overlay
    if not sedang_jeda:
        # Menentukan status mentah dari kondisi frame ini
        mentah = status_mentah(pemilik, daftar_lain)
        # Memeriksa apakah status mentah sama dengan status yang berlaku
        if mentah == status_aktif:
            # Membatalkan kandidat karena kondisi kembali seperti semula
            kandidat = None
        # Kalau berbeda, mulai atau lanjutkan menghitung waktu kandidat
        else:
            # Memeriksa apakah ini kandidat baru
            if mentah != kandidat:
                # Menyimpan kandidat baru
                kandidat = mentah
                # Mencatat kapan kandidat pertama kali muncul
                waktu_kandidat = sekarang
            # Kalau kandidat sama dan sudah cukup lama, status resmi berubah
            elif sekarang - waktu_kandidat >= TAHAN[mentah]:
                # Menjadikan kandidat sebagai status yang berlaku
                status_aktif = mentah
                # Mengosongkan kandidat
                kandidat = None

        # Memeriksa apakah status yang berlaku berubah dari sebelumnya
        if status_aktif != status_lama:
            # Memeriksa apakah status baru termasuk yang menutup layar
            if status_aktif in STATUS_TUTUP:
                # Kalau sebelumnya layar masih terbuka, tangkap layar dan buka penutup
                if status_lama not in STATUS_TUTUP:
                    # Menangkap tampilan layar komputer saat ini
                    layar_asli = ambil_layar()
                    # Membuka jendela penutup
                    buka_overlay()
                # Membuat gambar buram dengan teks status yang baru
                gambar_buram = buramkan(layar_asli, TEKS[status_aktif])
                # Membunyikan alarm hanya untuk status bahaya
                if status_aktif == "BAHAYA" and ALARM_AKTIF:
                    # Memanggil alarm bahaya
                    bunyikan_alarm("BAHAYA")
                # [BARU] Menyimpan foto frame kamera otomatis saat masuk BAHAYA
                if status_aktif == "BAHAYA":
                    # Memanggil fungsi simpan foto dan mendapatkan path-nya
                    path_foto_terakhir = simpan_foto_kejadian(frame)
                    # Mencatat waktu foto untuk menampilkan pesan konfirmasi
                    waktu_foto_terakhir = sekarang
            # Kalau status baru tidak menutup layar
            else:
                # Kalau sebelumnya layar tertutup, tutup jendela penutup
                if status_lama in STATUS_TUTUP:
                    # Menutup jendela penutup
                    cv2.destroyWindow(NAMA_OVERLAY)
                # Membunyikan beep pendek kalau masuk status waspada
                if status_aktif == "WASPADA" and ALARM_AKTIF:
                    # Memanggil alarm waspada
                    bunyikan_alarm("WASPADA")
            # [BARU] Mencatat perubahan status ke file log CSV
            catat_log(
                status=status_aktif,
                jumlah_wajah=len(daftar_wajah),
                jarak_terdekat=jarak_terdekat_frame,
                keterangan=f"Berubah dari {status_lama}",
            )
            # Menyimpan status sekarang sebagai status lama
            status_lama = status_aktif

    # ------------------------------------------------------------------
    # MENGGAMBAR INFORMASI DI FRAME KAMERA
    # ------------------------------------------------------------------

    # [BARU] Menentukan warna pita: abu-abu gelap kalau jeda, sesuai status kalau aktif
    warna_pita = (60, 60, 60) if sedang_jeda else WARNA[status_aktif]
    # Menggambar pita berwarna di bagian atas frame sebagai latar status
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), warna_pita, -1)
    # [BARU] Menentukan teks yang ditampilkan di pita sesuai kondisi jeda
    if sedang_jeda:
        # Menulis teks jeda di pita saat perlindungan tidak aktif
        cv2.putText(frame, "PERLINDUNGAN DIJEDA", (10, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
    else:
        # Menulis teks status normal di pita
        cv2.putText(frame, TEKS[status_aktif], (10, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    # Menentukan teks kondisi layar
    teks_layar = "TERTUTUP" if (status_aktif in STATUS_TUTUP and not sedang_jeda) else "TERBUKA"
    # Menentukan teks kondisi suara
    teks_suara = "ON" if ALARM_AKTIF else "OFF"
    # [BARU] Menentukan teks kondisi jeda
    teks_jeda = "JEDA" if sedang_jeda else "AKTIF"
    # Menulis jumlah wajah, kondisi layar, suara, dan jeda di bawah pita
    cv2.putText(frame,
                f"Wajah: {len(daftar_wajah)} | Layar: {teks_layar} | Suara: {teks_suara} | Lindung: {teks_jeda}",
                (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
    # Menulis pesan kalibrasi selama 2 detik setelah tombol K ditekan
    if sekarang - waktu_pesan < 2.0:
        # Menulis pesan bahwa kalibrasi berhasil
        cv2.putText(frame, f"Kalibrasi OK (fokal={FOKAL:.0f})", (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 0), 2)
    # [BARU] Menulis konfirmasi foto selama 2 detik setelah foto disimpan
    if sekarang - waktu_foto_terakhir < 2.0:
        # Mengambil nama file saja dari path lengkap untuk ditampilkan
        nama_foto = os.path.basename(path_foto_terakhir)
        # Menulis nama file foto di layar sebagai konfirmasi
        cv2.putText(frame, f"Foto: {nama_foto}", (10, 135),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 255), 2)
    # Menulis petunjuk tombol di pojok kiri bawah (termasuk tombol P baru)
    cv2.putText(frame, "Q/Esc: keluar | M: suara | K: kalibrasi | P: jeda",
                (10, frame.shape[0] - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1)

    # ------------------------------------------------------------------
    # TAMPIL JENDELA
    # ------------------------------------------------------------------

    # Menampilkan frame kamera di jendela kamera
    cv2.imshow("Tahap 7 - Kamera", frame)
    # Kalau layar sedang tertutup, tidak dijeda, dan gambar sudah siap, tampilkan
    if status_aktif in STATUS_TUTUP and not sedang_jeda and gambar_buram is not None:
        # Menampilkan gambar buram di jendela penutup
        cv2.imshow(NAMA_OVERLAY, gambar_buram)

    # ------------------------------------------------------------------
    # PEMBACAAN TOMBOL
    # ------------------------------------------------------------------

    # Membaca tombol yang ditekan (menunggu 1 milidetik)
    tombol = cv2.waitKey(1) & 0xFF
    # Keluar dari loop kalau tombol Q atau Esc (kode 27) ditekan
    if tombol == ord("q") or tombol == 27:
        # [BARU] Mencatat ke log bahwa program dihentikan oleh pengguna
        catat_log(
            status=status_aktif,
            jumlah_wajah=len(daftar_wajah),
            jarak_terdekat=jarak_terdekat_frame,
            keterangan="Program dihentikan pengguna",
        )
        break
    # Membalik status alarm kalau tombol M ditekan
    if tombol == ord("m"):
        # Mengubah True menjadi False atau sebaliknya
        ALARM_AKTIF = not ALARM_AKTIF
    # Mengkalibrasi panjang fokus kalau tombol K ditekan dan ada pemilik
    if tombol == ord("k") and pemilik is not None:
        # Menghitung panjang fokus dari lebar kotak wajah pemilik
        FOKAL = (pemilik.bounding_box.width * JARAK_KALIBRASI_CM
                 / LEBAR_WAJAH_CM)
        # Mencatat waktu pesan kalibrasi
        waktu_pesan = sekarang
    # [BARU] Membalik status jeda kalau tombol P ditekan
    if tombol == ord("p"):
        # Mengubah True menjadi False atau sebaliknya
        sedang_jeda = not sedang_jeda
        # Memeriksa apakah baru saja masuk mode jeda
        if sedang_jeda:
            # Menutup overlay kalau sedang terbuka saat jeda dimulai
            if status_aktif in STATUS_TUTUP:
                # Menutup jendela penutup
                cv2.destroyWindow(NAMA_OVERLAY)
            # [BARU] Mencatat ke log bahwa perlindungan dijeda
            catat_log(
                status=status_aktif,
                jumlah_wajah=len(daftar_wajah),
                jarak_terdekat=jarak_terdekat_frame,
                keterangan="Perlindungan dijeda oleh pengguna (tombol P)",
            )
        # Kalau baru saja keluar dari mode jeda
        else:
            # Mengatur ulang status_lama agar perubahan status terdeteksi ulang
            status_lama = status_aktif
            # [BARU] Mencatat ke log bahwa perlindungan dilanjutkan
            catat_log(
                status=status_aktif,
                jumlah_wajah=len(daftar_wajah),
                jarak_terdekat=jarak_terdekat_frame,
                keterangan="Perlindungan dilanjutkan oleh pengguna (tombol P)",
            )

# ==============================================================================
# PENUTUPAN
# ==============================================================================

# Melepas kamera supaya lampu kamera mati
kamera.release()
# Menutup semua jendela OpenCV
cv2.destroyAllWindows()

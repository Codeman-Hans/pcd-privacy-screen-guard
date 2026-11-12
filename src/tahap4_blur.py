# Mengimpor time untuk membuat cap waktu (timestamp) tiap frame
import time
# Mengimpor OpenCV untuk membaca kamera, menggambar, dan menampilkan jendela
import cv2
# Mengimpor NumPy untuk membuat gambar layar simulasi
import numpy as np
# Mengimpor MediaPipe untuk deteksi wajah
import mediapipe as mp
# Mengimpor modul dasar MediaPipe Tasks
from mediapipe.tasks import python
# Mengimpor modul penglihatan (vision) dari MediaPipe Tasks
from mediapipe.tasks.python import vision

# Menentukan lokasi file model deteksi wajah
MODEL = "models/blaze_face_short_range.tflite"
# Menentukan ukuran kernel blur (harus ganjil); makin besar makin buram
UKURAN_BLUR = 99


# Membuat fungsi yang menentukan status berdasarkan jumlah wajah
def tentukan_status(jumlah_wajah):
    # Kalau tidak ada wajah, pengguna dianggap pergi
    if jumlah_wajah == 0:
        # Mengembalikan teks status dan warna oranye (format BGR)
        return "PENGGUNA PERGI", (0, 165, 255)
    # Kalau hanya satu wajah, kondisi aman
    if jumlah_wajah == 1:
        # Mengembalikan teks status dan warna hijau
        return "AMAN", (0, 200, 0)
    # Selain itu (dua wajah atau lebih), ada kemungkinan pengintip
    return "BAHAYA: ADA PENGINTIP", (0, 0, 255)


# Membuat fungsi yang menggambar layar simulasi berisi data palsu
def buat_layar_simulasi():
    # Membuat kanvas putih berukuran 400 x 640 piksel dengan 3 kanal warna
    layar = np.full((400, 640, 3), 255, dtype=np.uint8)
    # Menggambar pita biru di bagian atas sebagai judul dokumen
    cv2.rectangle(layar, (0, 0), (640, 60), (150, 80, 20), -1)
    # Menulis judul dokumen di atas pita
    cv2.putText(layar, "LAPORAN NILAI (DATA CONTOH)", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    # Menyiapkan beberapa baris isi dokumen palsu
    baris = [
        "Nama   : Mahasiswa Contoh",
        "NIM    : 0000000000",
        "Mata kuliah : Pengolahan Citra Digital",
        "Nilai tugas : 85",
        "Nilai UTS   : 78",
        "Nilai akhir : 82",
    ]
    # Mengulang untuk setiap baris beserta nomor urutnya
    for i, teks in enumerate(baris):
        # Menulis baris ke layar, tiap baris turun 50 piksel
        cv2.putText(layar, teks, (30, 120 + i * 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    # Mengembalikan gambar layar simulasi
    return layar


# Membuat layar simulasi versi jelas
layar_jelas = buat_layar_simulasi()
# Membuat versi buram dengan Gaussian blur (sigma 0 = dihitung otomatis)
layar_buram = cv2.GaussianBlur(layar_jelas, (UKURAN_BLUR, UKURAN_BLUR), 0)
# Menulis peringatan di atas layar buram supaya jelas sistem aktif
cv2.putText(layar_buram, "LAYAR DISEMBUNYIKAN", (110, 210),
            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)

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

# Membuat jendela layar pengguna lebih dulu supaya posisinya bisa diatur
cv2.namedWindow("Layar Pengguna")
# Memindahkan jendela layar pengguna ke kanan supaya tidak menumpuk kamera
cv2.moveWindow("Layar Pengguna", 720, 60)

# Mencatat waktu mulai sebagai patokan cap waktu
waktu_mulai = time.time()
# Menyimpan cap waktu terakhir untuk memastikan selalu naik
ts_terakhir = -1

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

    # Menghitung cap waktu dalam milidetik sejak program dimulai
    ts = int((time.time() - waktu_mulai) * 1000)
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
    # Menghitung jumlah wajah yang terdeteksi
    jumlah = len(daftar_wajah)

    # Menyiapkan variabel pemilik; awalnya belum ada
    pemilik = None
    # Memeriksa apakah ada minimal satu wajah
    if jumlah > 0:
        # Memilih wajah dengan luas kotak terbesar sebagai pemilik
        pemilik = max(
            daftar_wajah,
            key=lambda f: f.bounding_box.width * f.bounding_box.height,
        )

    # Mengulang untuk setiap wajah yang terdeteksi
    for wajah in daftar_wajah:
        # Mengambil kotak pembatas wajah
        kotak = wajah.bounding_box
        # Mengambil posisi kiri atas, lebar, dan tinggi kotak
        x, y, w, h = kotak.origin_x, kotak.origin_y, kotak.width, kotak.height
        # Kalau wajah ini adalah pemilik, kotaknya hijau; selain itu merah
        warna_kotak = (0, 255, 0) if wajah is pemilik else (0, 0, 255)
        # Menentukan label sesuai peran wajah
        label = "PEMILIK" if wajah is pemilik else "ORANG LAIN"
        # Menggambar kotak di sekeliling wajah
        cv2.rectangle(frame, (x, y), (x + w, y + h), warna_kotak, 2)
        # Menulis label di atas kotak
        cv2.putText(frame, label, (x, max(y - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, warna_kotak, 2)

    # Menentukan teks dan warna status berdasarkan jumlah wajah
    teks_status, warna_status = tentukan_status(jumlah)
    # Menggambar pita berwarna di bagian atas frame sebagai latar status
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), warna_status, -1)
    # Menulis teks status di atas pita
    cv2.putText(frame, f"STATUS: {teks_status}", (10, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    # Menulis jumlah wajah di bawah pita
    cv2.putText(frame, f"Jumlah wajah: {jumlah}", (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    # Menulis petunjuk keluar di pojok kiri bawah
    cv2.putText(frame, "Tekan Q untuk keluar", (10, frame.shape[0] - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    # Memilih layar jelas kalau aman (tepat satu wajah), selain itu layar buram
    layar_tampil = layar_jelas if jumlah == 1 else layar_buram

    # Menampilkan frame kamera di jendela pertama
    cv2.imshow("Tahap 4 - Kamera", frame)
    # Menampilkan layar simulasi (jelas atau buram) di jendela kedua
    cv2.imshow("Layar Pengguna", layar_tampil)
    # Keluar dari loop kalau tombol Q ditekan
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Melepas kamera supaya lampu kamera mati
kamera.release()
# Menutup semua jendela OpenCV
cv2.destroyAllWindows()
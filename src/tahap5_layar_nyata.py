# Mengimpor time untuk membuat cap waktu (timestamp) tiap frame
import time
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

# Menentukan lokasi file model deteksi wajah
MODEL = "models/blaze_face_short_range.tflite"
# Menentukan apakah penutup tampil layar penuh; mulai dengan False untuk uji
LAYAR_PENUH = True
# Menentukan berapa frame berturut-turut sebelum status layar berubah
BATAS_FRAME = 8
# Menentukan faktor pengecilan gambar sebelum diblur supaya lebih cepat
FAKTOR_KECIL = 0.25
# Menentukan nama jendela penutup layar
NAMA_OVERLAY = "Layar Terlindungi"
# Menentukan apakah alarm suara aktif; tombol M mengubahnya saat program jalan
ALARM_AKTIF = True

# Mencoba membuat program sadar pada skala tampilan Windows
try:
    # Mengatur DPI aware agar tangkapan layar tidak terpotong
    ctypes.windll.user32.SetProcessDPIAware()
# Mengabaikan kalau perintah ini tidak tersedia
except Exception:
    # Tidak melakukan apa-apa
    pass

# Membuat fungsi yang membunyikan alarm tanpa menghentikan program
def bunyikan_alarm():
    # Membuat fungsi kecil yang berisi urutan nada
    def _bunyi():
        # Membunyikan nada 1000 Hz selama 200 milidetik
        winsound.Beep(1000, 200)
        # Membunyikan nada 1400 Hz selama 300 milidetik
        winsound.Beep(1400, 300)
    # Menjalankan urutan nada di thread terpisah supaya kamera tidak macet
    threading.Thread(target=_bunyi, daemon=True).start()

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

# Menyimpan status apakah layar sedang tertutup
layar_tertutup = False
# Menyimpan gambar buram yang sedang ditampilkan
gambar_buram = None
# Menghitung berapa frame berturut-turut kondisi tidak aman
hitung_bahaya = 0
# Menghitung berapa frame berturut-turut kondisi aman
hitung_aman = 0

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

    # Memeriksa apakah kondisi saat ini tidak aman (bukan tepat satu wajah)
    if jumlah != 1:
        # Menambah hitungan frame tidak aman
        hitung_bahaya += 1
        # Mengosongkan hitungan frame aman
        hitung_aman = 0
    # Kalau kondisi aman
    else:
        # Menambah hitungan frame aman
        hitung_aman += 1
        # Mengosongkan hitungan frame tidak aman
        hitung_bahaya = 0

    # Menutup layar kalau belum tertutup dan bahaya bertahan cukup lama
    if not layar_tertutup and hitung_bahaya >= BATAS_FRAME:
        # Menangkap tampilan layar komputer saat ini
        layar_asli = ambil_layar()
        # Mengaburkan tangkapan layar dan menulis teks status
        gambar_buram = buramkan(layar_asli, teks_status)
        # Membuka jendela penutup
        buka_overlay()
        # Menandai bahwa layar sekarang tertutup
        layar_tertutup = True
    # Membuka layar kalau tertutup dan kondisi aman bertahan cukup lama
    elif layar_tertutup and hitung_aman >= BATAS_FRAME:
        # Menutup jendela penutup
        cv2.destroyWindow(NAMA_OVERLAY)
        # Menandai bahwa layar sekarang terbuka
        layar_tertutup = False
    # Membunyikan alarm kalau alarm sedang aktif
        if ALARM_AKTIF:
            # Memanggil fungsi alarm
            bunyikan_alarm()

    # Menggambar pita berwarna di bagian atas frame sebagai latar status
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), warna_status, -1)
    # Menulis teks status di atas pita
    cv2.putText(frame, f"STATUS: {teks_status}", (10, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    # Menentukan teks kondisi layar
    teks_layar = "TERTUTUP" if layar_tertutup else "TERBUKA"
    # Menulis jumlah wajah dan kondisi layar di bawah pita
    cv2.putText(frame, f"Wajah: {jumlah} | Layar: {teks_layar}", (10, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    # Menulis petunjuk keluar di pojok kiri bawah
    cv2.putText(frame, "Q / Esc untuk keluar", (10, frame.shape[0] - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

    # Menampilkan frame kamera di jendela kamera
    cv2.imshow("Tahap 5 - Kamera", frame)
    # Kalau layar sedang tertutup, tampilkan gambar buram di penutup
    if layar_tertutup:
        # Menampilkan gambar buram di jendela penutup
        cv2.imshow(NAMA_OVERLAY, gambar_buram)

    # Membaca tombol yang ditekan (menunggu 1 milidetik)
    tombol = cv2.waitKey(1) & 0xFF
    # Keluar dari loop kalau tombol Q atau Esc (kode 27) ditekan
    if tombol == ord("q") or tombol == 27:
        break
    # Membalik status alarm kalau tombol M ditekan
    if tombol == ord("m"):
        # Mengubah True menjadi False atau sebaliknya
        ALARM_AKTIF = not ALARM_AKTIF

# Melepas kamera supaya lampu kamera mati
kamera.release()
# Menutup semua jendela OpenCV
cv2.destroyAllWindows()
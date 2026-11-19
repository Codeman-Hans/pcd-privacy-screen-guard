# Skrip pendaftaran wajah pemilik dan pelatihan model pengenalan wajah LBPH
# Catatan penting: Metode LBPH (Local Binary Patterns Histograms) sensitif terhadap
# perubahan pencahayaan dan sudut kemiringan wajah. Disarankan mendaftar dengan
# pencahayaan yang mirip dengan tempat sistem akan digunakan.

# Mengimpor modul os untuk membuat direktori dan mengelola jalur file
import os
# Mengimpor modul time untuk memberi jeda antar pengambilan foto
import time
# Mengimpor OpenCV untuk menangani kamera, citra, dan pelatihan LBPH
import cv2
# Mengimpor NumPy untuk manipulasi array citra
import numpy as np
# Mengimpor MediaPipe untuk deteksi wajah menggunakan BlazeFace
import mediapipe as mp
# Mengimpor komponen python MediaPipe Tasks
from mediapipe.tasks import python
# Mengimpor komponen vision MediaPipe Tasks
from mediapipe.tasks.python import vision

# ==============================================================================
# KONSTANTA PENGATURAN
# ==============================================================================

# Menentukan lokasi file model BlazeFace untuk deteksi wajah
MODEL_DETEKTOR = "models/blaze_face_short_range.tflite"
# Menentukan folder penyimpanan foto wajah pemilik
FOLDER_FOTO_PEMILIK = os.path.join("data", "pemilik")
# Menentukan lokasi file keluaran model LBPH yang sudah dilatih
FILE_MODEL_LBPH = os.path.join("data", "pemilik_model.yml")
# Menentukan target jumlah foto wajah pemilik yang akan dikumpulkan
JUMLAH_FOTO_TARGET = 30
# Menentukan jeda waktu otomatis antar pengambilan foto dalam satuan detik
JEDA_FOTO_DETIK = 0.2
# Menentukan ukuran resolusi seragam (lebar, tinggi) untuk potongan wajah
UKURAN_WAJAH = (200, 200)

# ==============================================================================
# PERSIAPAN FOLDER DAN DETEKTOR
# ==============================================================================

# Membuat folder data/pemilik jika belum ada
os.makedirs(FOLDER_FOTO_PEMILIK, exist_ok=True)

# Menyiapkan konfigurasi opsi detektor wajah BlazeFace
opsi_detektor = vision.FaceDetectorOptions(
    # Mengarahkan aset model deteksi wajah
    base_options=python.BaseOptions(model_asset_path=MODEL_DETEKTOR),
    # Menggunakan mode VIDEO untuk aliran frame kamera
    running_mode=vision.RunningMode.VIDEO,
    # Menetapkan batas keyakinan deteksi minimal 50 persen
    min_detection_confidence=0.5,
)
# Membangun objek detektor wajah dari konfigurasi
detektor = vision.FaceDetector.create_from_options(opsi_detektor)

# Membuka kamera laptop/komputer indeks 0 menggunakan backend DirectShow Windows
kamera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
# Memeriksa apakah kamera siap dan berhasil terbuka
if not kamera.isOpened():
    # Menampilkan pesan kesalahan jika kamera tidak terhubung
    print("Error: Kamera tidak dapat dibuka!")
    # Keluar dari skrip
    raise SystemExit

# ==============================================================================
# PENGUMPULAN FOTO WAJAH PEMILIK
# ==============================================================================

# Menghitung jumlah foto yang sudah berhasil disimpan
foto_tersimpan = 0
# Mencatat cap waktu pengambilan foto terakhir
waktu_foto_terakhir = 0.0
# Mencatat waktu mulai untuk keperluan timestamp MediaPipe
waktu_mulai = time.time()
# Menyimpan timestamp terakhir agar nilai selalu bertambah naik
ts_terakhir = -1

# Menampilkan informasi awal di jendela terminal
print("=" * 60)
print("PROSES PENDAFTARAN WAJAH PEMILIK")
print(f"Target: {JUMLAH_FOTO_TARGET} foto wajah")
print("Petunjuk: Variasikan sedikit sudut kepala (tengok kiri/kanan sedikit,")
print("senyum/netral) dan pastikan pencahayaan cukup dan seragam.")
print("Tekan SPASI untuk ambil manual, atau biarkan otomatis.")
print("Tekan Q atau Esc kapan saja untuk membatalkan.")
print("=" * 60)

# Loop membaca frame dari kamera sampai jumlah foto mencukupi
while foto_tersimpan < JUMLAH_FOTO_TARGET:
    # Membaca satu frame dari perangkat kamera
    ok, frame = kamera.read()
    # Menghentikan perulangan jika gagal membaca frame kamera
    if not ok:
        print("Gagal membaca frame kamera.")
        break

    # Membalik citra kamera secara horizontal seperti cermin datar
    frame = cv2.flip(frame, 1)
    # Menyimpan salinan citra bersih sebelum digambari kotak/teks
    frame_asli = frame.copy()

    # Mengubah format warna BGR OpenCV menjadi RGB untuk MediaPipe
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Membungkus matriks citra ke tipe data citra milik MediaPipe
    gambar_mp = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    # Menghitung waktu sekarang
    sekarang = time.time()
    # Menghitung waktu berjalan dalam satuan milidetik
    ts = int((sekarang - waktu_mulai) * 1000)
    # Menjamin timestamp berikutnya selalu lebih besar dari sebelumnya
    if ts <= ts_terakhir:
        ts = ts_terakhir + 1
    ts_terakhir = ts

    # Menjalankan deteksi wajah pada frame video saat ini
    hasil = detektor.detect_for_video(gambar_mp, ts)
    # Mengambil daftar seluruh wajah yang tertangkap kamera
    daftar_wajah = hasil.detections
    # Menghitung banyak wajah yang terdeteksi
    jumlah_wajah = len(daftar_wajah)

    # Menyiapkan variabel penampung wajah target pemotongan
    wajah_terpilih = None
    # Menyiapkan penanda apakah syarat kondisi foto terpenuhi (hanya ada 1 wajah)
    siap_ambil = False

    # Memeriksa apakah kondisi tepat satu wajah di depan kamera
    if jumlah_wajah == 1:
        # Menandai kondisi sudah siap untuk pemotretan
        siap_ambil = True
        # Mengambil data wajah tunggal tersebut
        wajah_terpilih = daftar_wajah[0]
        # Mendapatkan koordinat kotak pembatas wajah
        kotak = wajah_terpilih.bounding_box
        x = kotak.origin_x
        y = kotak.origin_y
        w = kotak.width
        h = kotak.height

        # Menggambar kotak hijau pada wajah yang sedang didaftarkan
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # Menampilkan teks status siap ambil
        cv2.putText(frame, "Wajah Terdeteksi", (x, max(y - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    elif jumlah_wajah > 1:
        # Jika lebih dari 1 wajah, beri peringatan agar orang lain menyingkir
        cv2.putText(frame, "PERINGATAN: Harus tepat 1 wajah!", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    else:
        # Jika tidak ada wajah sama sekali
        cv2.putText(frame, "Posisikan wajah di depan kamera", (20, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

    # Memeriksa tombol keyboard yang ditekan pengguna
    tombol = cv2.waitKey(1) & 0xFF
    # Menghentikan proses pendaftaran jika pengguna menekan Q atau Esc
    if tombol == ord("q") or tombol == 27:
        print("\nPendaftaran dibatalkan oleh pengguna.")
        kamera.release()
        cv2.destroyAllWindows()
        raise SystemExit

    # Menentukan apakah tombol spasi ditekan untuk potret manual
    tekan_spasi = (tombol == ord(" "))
    # Menentukan apakah sudah waktunya ambil foto secara otomatis sesuai jeda
    waktu_otomatis = (sekarang - waktu_foto_terakhir >= JEDA_FOTO_DETIK)

    # Melakukan pengambilan foto jika syarat terpenuhi dan waktunya tiba
    if siap_ambil and (tekan_spasi or waktu_otomatis):
        # Mendapatkan batas dimensi citra frame asli
        tinggi_frame, lebar_frame = frame_asli.shape[:2]

        # Menghitung koordinat pemotongan dengan batas aman dalam citra
        x1 = max(0, kotak.origin_x)
        y1 = max(0, kotak.origin_y)
        x2 = min(lebar_frame, kotak.origin_x + kotak.width)
        y2 = min(tinggi_frame, kotak.origin_y + kotak.height)

        # Memastikan potongan memiliki lebar dan tinggi positif
        if (x2 - x1 > 20) and (y2 - y1 > 20):
            # Memotong area wajah dari frame asli bersih (tanpa garis/teks)
            potongan_wajah = frame_asli[y1:y2, x1:x2]
            # Mengubah potongan wajah menjadi format derajat keabuan (grayscale)
            wajah_abu = cv2.cvtColor(potongan_wajah, cv2.COLOR_BGR2GRAY)
            # Menyamakan ukuran potongan wajah ke dimensi baku (200x200 piksel)
            wajah_seragam = cv2.resize(wajah_abu, UKURAN_WAJAH, interpolation=cv2.INTER_AREA)

            # Menaikkan angka pencatat foto tersimpan
            foto_tersimpan += 1
            # Membentuk nama berkas foto wajah pemilik berurutan
            nama_file = f"pemilik_{foto_tersimpan:02d}.jpg"
            path_simpan = os.path.join(FOLDER_FOTO_PEMILIK, nama_file)
            # Menyimpan citra wajah abu-abu ke media penyimpanan
            cv2.imwrite(path_simpan, wajah_seragam)

            # Memperbarui waktu pengambilan foto terakhir
            waktu_foto_terakhir = sekarang
            # Menampilkan kemajuan di terminal
            print(f"Foto berhasil disimpan ({foto_tersimpan}/{JUMLAH_FOTO_TARGET}): {path_simpan}")

    # Menggambar pita status hitam di bagian atas jendela kamera
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 50), (40, 40, 40), -1)
    # Menampilkan progres jumlah foto yang sudah diambil
    teks_progres = f"PENDAFTARAN WAJAH: {foto_tersimpan}/{JUMLAH_FOTO_TARGET} Foto"
    cv2.putText(frame, teks_progres, (10, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)

    # Menampilkan petunjuk singkat di bagian bawah jendela kamera
    cv2.putText(frame, "SPASI: foto manual | Gerakkan kepala perlahan | Q/Esc: batal",
                (10, frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Menampilkan visualisasi pada jendela pendaftaran
    cv2.imshow("Pendaftaran Wajah Pemilik", frame)

# Menutup kamera dan jendela tampilan setelah pengambilan foto selesai
kamera.release()
cv2.destroyAllWindows()

# ==============================================================================
# PELATIHAN MODEL PENGENAL WAJAH LBPH
# ==============================================================================

print("\n" + "=" * 60)
print("MEMULAI PROSES PELATIHAN MODEL LBPH...")
print("=" * 60)

# Menyiapkan daftar penampung matriks citra wajah untuk pelatihan
daftar_citra_wajah = []
# Menyiapkan daftar label angka untuk tiap citra (label 1 mewakili pemilik)
daftar_label = []

# Membaca seluruh file foto wajah yang tersimpan di folder pemilik
for nama_berkas in os.listdir(FOLDER_FOTO_PEMILIK):
    # Memeriksa apakah berkas memiliki format gambar JPEG
    if nama_berkas.lower().endswith(".jpg") or nama_berkas.lower().endswith(".jpeg"):
        # Menyusun jalur lengkap ke berkas foto
        jalur_berkas = os.path.join(FOLDER_FOTO_PEMILIK, nama_berkas)
        # Membaca citra dalam format keabuan (grayscale)
        citra = cv2.imread(jalur_berkas, cv2.IMREAD_GRAYSCALE)
        # Memastikan citra berhasil terbaca
        if citra is not None:
            # Memastikan ukuran citra pas sesuai standar
            citra_pas = cv2.resize(citra, UKURAN_WAJAH)
            # Menambahkan citra ke daftar pelatihan
            daftar_citra_wajah.append(citra_pas)
            # Menetapkan label angka 1 untuk pemilik
            daftar_label.append(1)

# Memeriksa apakah data foto mencukupi untuk proses pelatihan model
if len(daftar_citra_wajah) == 0:
    print("Error: Tidak ada citra wajah yang ditemukan untuk dilatih!")
    raise SystemExit

# Mengubah daftar label menjadi array NumPy bertipe integer 32 bit
array_label = np.array(daftar_label, dtype=np.int32)

# Menginisialisasi objek pengenal wajah LBPH dari modul cv2.face
pengenal = cv2.face.LBPHFaceRecognizer_create()

# Melatih pengenal wajah dengan kumpulan citra dan label pemilik
print(f"Melatih model LBPH dengan {len(daftar_citra_wajah)} sampel wajah...")
pengenal.train(daftar_citra_wajah, array_label)

# Menyimpan hasil pelatihan ke file model format YAML
pengenal.write(FILE_MODEL_LBPH)
print(f"Model LBPH berhasil disimpan ke: {FILE_MODEL_LBPH}")
print("=" * 60)
print("PENDAFTARAN DAN PELATIHAN SELESAI DENGAN SUKSES!")
print("Sekarang Anda dapat menjalankan: python src/tahap8_pemilik.py")
print("=" * 60)

# Tabel Pengujian Sistem Pelindung Privasi Layar

**Nama / NIM  :** _______________________________________________  
**Tanggal uji :** _______________________________________________  
**Versi program:** `src/main.py` (v-final)  
**Perangkat    :** Laptop/PC | Webcam built-in / eksternal  

---

## Rumus Akurasi

$$
\text{Akurasi} = \frac{\text{Jumlah Hasil Benar}}{\text{Total Skenario}} \times 100\%
$$

> **Hasil Benar** = kolom "Benar/Salah" bernilai **B**

---

## Catatan Pengisian

| Kolom | Cara Mengisi |
|-------|-------------|
| **Skenario** | Nama skenario uji |
| **Jarak (cm)** | Perkiraan jarak wajah ke kamera (ukur dengan penggaris/meteran) |
| **Cahaya** | `Terang` / `Redup` (nyalakan/matikan lampu atau tutupi jendela) |
| **Menghadap / Menoleh** | `Menghadap` = wajah lurus ke kamera | `Menoleh` = kepala diputar ke samping |
| **Hasil Diharapkan** | Status yang seharusnya muncul di program (AMAN/WASPADA/BAHAYA/PERGI/ORANG_ASING) |
| **Hasil Sebenarnya** | Status yang benar-benar muncul di jendela kamera |
| **Benar/Salah** | **B** jika hasil sebenarnya = hasil diharapkan, **S** jika berbeda |

---

## Contoh Pengisian (Baris Pertama Sudah Diisi sebagai Panduan)

| No | Skenario | Jarak (cm) | Cahaya | Menghadap / Menoleh | Hasil Diharapkan | Hasil Sebenarnya | Benar / Salah |
|----|----------|-----------|--------|---------------------|-----------------|-----------------|--------------|
| 1 | Pemilik duduk sendiri di depan kamera | ±60 | Terang | Menghadap | AMAN | AMAN | B |
| 2 | | | | | | | |
| 3 | | | | | | | |
| 4 | | | | | | | |
| 5 | | | | | | | |
| 6 | | | | | | | |
| 7 | | | | | | | |
| 8 | | | | | | | |
| 9 | | | | | | | |
| 10 | | | | | | | |
| **TOTAL** | | | | | | **B:** ___ / **S:** ___ | **Akurasi: ____%** |

---

## Daftar Skenario yang Harus Diuji

Isi tabel di atas menggunakan skenario-skenario berikut (urutan bebas):

### Skenario 1 — Pemilik Duduk Sendiri
- **Situasi:** Hanya pemilik yang terdaftar di depan kamera, jarak normal ±60 cm, cahaya terang.  
- **Hasil diharapkan:** `AMAN`  
- **Catatan:** Gunakan ini sebagai baseline; jika gagal, cek pendaftaran ulang.

---

### Skenario 2 — Pemilik Pergi (Layar Kosong)
- **Situasi:** Pemilik keluar dari jangkauan kamera (berdiri atau menutup kamera dengan tangan).  
- **Hasil diharapkan:** `PERGI` (layar dikaburkan setelah ±1,5 detik)  
- **Catatan:** Periksa apakah overlay muncul dan layar benar-benar tertutup.

---

### Skenario 3 — Teman Dekat Menghadap Layar
- **Situasi:** Pemilik duduk seperti biasa; teman berdiri di belakang/samping pada jarak ≤200 cm dan menghadap ke kamera.  
- **Hasil diharapkan:** `BAHAYA` (alarm dua nada + foto kejadian tersimpan)  
- **Catatan:** Periksa folder `data/kejadian/` setelah uji ini.

---

### Skenario 4 — Teman Dekat Menoleh (Membuang Muka)
- **Situasi:** Situasi sama seperti Skenario 3, tetapi teman **menoleh** ke samping (kepala diputar >30°).  
- **Hasil diharapkan:** `WASPADA` (satu beep pendek, layar tidak dikaburkan)  
- **Catatan:** Putar kepala perlahan; amati kapan status berganti dari BAHAYA ke WASPADA.

---

### Skenario 5 — Teman Jauh (Di Luar Batas Jarak)
- **Situasi:** Teman berada di jarak >200 cm dari kamera (di ujung ruangan) dan menghadap kamera.  
- **Hasil diharapkan:** `WASPADA`  
- **Catatan:** Sesuaikan `BATAS_JARAK_CM` di slider jika perlu; catat nilai slider yang digunakan.

---

### Skenario 6 — Foto Wajah Pemilik di HP (Spoof)
- **Situasi:** Orang lain mendekatkan foto/foto pemilik yang ada di layar HP ke kamera.  
- **Hasil diharapkan:** Idealnya `ORANG_ASING`; jika sistem mengenali foto sebagai pemilik, catat sebagai kelemahan.  
- **Catatan:** Ini adalah uji ketahanan terhadap serangan spoofing sederhana.

---

### Skenario 7 — Orang Asing Duduk Menggantikan Pemilik
- **Situasi:** Pemilik pergi, lalu orang lain yang belum terdaftar duduk di depan kamera.  
- **Hasil diharapkan:** `ORANG_ASING` (layar dikaburkan + alarm + foto kejadian)  
- **Catatan:** Periksa apakah nilai confidence yang ditampilkan di atas kotak wajah > AMBANG_CONFIDENCE.

---

### Skenario 8 — Ruang Redup Tanpa CLAHE
- **Situasi:** Redupkan ruangan (matikan lampu, tutup tirai). Tekan `C` hingga mode CLAHE = `PAKSA_OFF`.  
- **Hasil diharapkan:** Deteksi wajah berkurang atau gagal; status mungkin `PERGI` meski pemilik ada.  
- **Catatan:** Amati nilai kecerahan yang ditampilkan di jendela kamera. Catat berapa nilai kecerahan saat deteksi mulai gagal.

---

### Skenario 9 — Ruang Redup Dengan CLAHE Aktif
- **Situasi:** Kondisi ruangan sama seperti Skenario 8. Tekan `C` hingga mode CLAHE = `PAKSA_ON`.  
- **Hasil diharapkan:** `AMAN` — deteksi wajah kembali berhasil meski cahaya redup.  
- **Catatan:** Bandingkan nilai confidence LBPH dengan dan tanpa CLAHE; catat perbedaannya.

---

## Ringkasan Hasil

| Skenario | Nomor Baris | Benar (B) / Salah (S) |
|----------|------------|----------------------|
| Pemilik sendiri | 1 | |
| Pemilik pergi | 2 | |
| Teman dekat menghadap | 3 | |
| Teman dekat menoleh | 4 | |
| Teman jauh | 5 | |
| Foto HP | 6 | |
| Orang asing menggantikan | 7 | |
| Ruang redup tanpa CLAHE | 8 | |
| Ruang redup dengan CLAHE | 9 | |
| **Total** | | **B: ___ / S: ___** |

**Akurasi keseluruhan:** _____ / 9 × 100% = _____%

---

## Analisis Singkat (Isi Setelah Uji)

**Skenario yang berhasil dengan baik:**  
> _Tulis di sini_

**Skenario yang gagal atau tidak sesuai:**  
> _Tulis di sini_

**Faktor penyebab kegagalan:**  
> _Contoh: pencahayaan berbeda dengan saat pendaftaran, sudut kepala terlalu miring, jarak slider terlalu besar_

**Saran perbaikan:**  
> _Tulis di sini_

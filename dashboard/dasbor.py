# Tahap 10: Dasbor visualisasi log pemantauan privasi berbasis web menggunakan Streamlit
# Skrip ini hanya membaca data/log_kejadian.csv untuk menampilkan statistik kejadian tanpa mengubah data asli.

# Mengimpor modul os untuk memeriksa ketersediaan berkas log
import os
# Mengimpor modul datetime untuk operasi perbandingan rentang tanggal
from datetime import datetime, date
# Mengimpor modul Streamlit untuk membangun antarmuka dasbor web interaktif
import streamlit as st
# Mengimpor modul Pandas untuk membaca dan mengolah data tabular
import pandas as pd

# ==============================================================================
# KONFIGURASI HALAMAN DASBOR
# ==============================================================================

# Mengatur konfigurasi dasar halaman web dasbor Streamlit
st.set_page_config(
    page_title="Dasbor Privasi Layar",
    page_icon="🛡️",
    layout="wide",
)

# Menentukan lokasi berkas log kejadian yang akan dibaca
FILE_LOG = os.path.join("data", "log_kejadian.csv")

# Menampilkan judul utama dan deskripsi aplikasi di bagian atas halaman
st.title("🛡️ Dasbor Log Pelindung Privasi Layar")
st.markdown(
    "Visualisasi rekaman riwayat insiden privasi: pengintipan, pengguna pergi, "
    "pengguna asing, serta jeda perlindungan."
)

# Menambahkan tombol muat ulang data di baris atas
col_refresh, _ = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Segarkan Data"):
        st.rerun()

# ==============================================================================
# PEMERIKSAAN DAN PEMBACAAN DATA LOG
# ==============================================================================

# Memeriksa apakah berkas log kejadian tersedia di folder data
if not os.path.exists(FILE_LOG):
    # Menampilkan pesan ramah jika berkas belum ada
    st.info(
        "ℹ️ Berkas log (`data/log_kejadian.csv`) belum ditemukan.\n\n"
        "Jalankan aplikasi deteksi (misalnya `src/tahap7_log.py`, `src/tahap8_pemilik.py`, "
        "atau `src/tahap9_cahaya.py`) terlebih dahulu untuk mulai merekam aktivitas."
    )
    # Menghentikan eksekusi lebih lanjut dari skrip
    st.stop()

# Memeriksa apakah ukuran berkas log 0 byte (kosong)
if os.path.getsize(FILE_LOG) == 0:
    st.warning("⚠️ Berkas log ditemukan tetapi masih kosong (0 byte).")
    st.stop()

# Mencoba membaca berkas CSV menggunakan Pandas dengan penanganan galat
try:
    # Membaca berkas CSV dengan enkoding UTF-8
    df = pd.read_csv(FILE_LOG, encoding="utf-8")
except Exception as e:
    st.error(f"❌ Terjadi kesalahan saat membaca berkas CSV: {e}")
    st.stop()

# Memeriksa apakah tabel hasil pembacaan tidak memiliki baris data sama sekali
if df.empty:
    st.info("ℹ️ Berkas log sudah memiliki kolom judul, namun belum ada baris kejadian yang dicatat.")
    st.stop()

# Memastikan kolom penting 'waktu' dan 'status' tersedia dalam data
if "waktu" not in df.columns or "status" not in df.columns:
    st.error("❌ Struktur berkas log tidak valid (kolom 'waktu' atau 'status' tidak ditemukan).")
    st.stop()

# Mengonversi kolom 'waktu' menjadi tipe data datetime agar dapat diurutkan dan difilter
df["waktu_dt"] = pd.to_datetime(df["waktu"], errors="coerce")
# Menghapus baris yang memiliki nilai waktu tidak valid (NaT) jika ada
df = df.dropna(subset=["waktu_dt"]).copy()

# Jika setelah pembersihan data menjadi kosong
if df.empty:
    st.info("ℹ️ Tidak ada data dengan format waktu yang valid di dalam berkas log.")
    st.stop()

# Mengekstrak tanggal saja untuk keperluan filter rentang tanggal
df["tanggal"] = df["waktu_dt"].dt.date
# Mengekstrak jam kejadian (00 - 23) untuk keperluan grafik distribusi per jam
df["jam"] = df["waktu_dt"].dt.hour

# Menambahkan kolom 'kategori' untuk membedakan kejadian jeda dari status biasa
# Jika kolom keterangan memuat kata 'dijeda' atau 'dilanjutkan', nilai kategori = 'JEDA'
# Selain itu, nilai kategori sama persis dengan nilai kolom status
if "keterangan" in df.columns:
    # Mendeteksi baris yang termasuk peristiwa jeda (penekanan tombol P)
    pola_jeda = df["keterangan"].astype(str).str.contains(
        "dijeda|dilanjutkan", case=False, na=False
    )
    # Menyalin kolom status sebagai nilai awal kategori
    df["kategori"] = df["status"].copy()
    # Mengganti nilai kategori menjadi 'JEDA' untuk baris yang cocok pola jeda
    df.loc[pola_jeda, "kategori"] = "JEDA"
else:
    # Jika kolom keterangan tidak ada, kategori langsung mengikuti status
    df["kategori"] = df["status"].copy()

# ==============================================================================
# PANEL FILTER DI BILAH SAMPING (SIDEBAR)
# ==============================================================================

st.sidebar.header("🔍 Filter Log Kejadian")

# Mendapatkan daftar unik seluruh kategori dari kolom 'kategori' (termasuk 'JEDA')
daftar_kategori_unik = sorted(df["kategori"].dropna().unique().tolist())

# Membuat komponen pilihan ganda (multiselect) untuk memfilter berdasarkan kategori
kategori_terpilih = st.sidebar.multiselect(
    "Pilih Kategori / Status:",
    options=daftar_kategori_unik,
    default=daftar_kategori_unik,
    help="Pilih satu atau beberapa kategori (termasuk JEDA) untuk ditampilkan.",
)

# Menentukan batas tanggal minimum dan maksimum yang ada di dalam dataset log
tanggal_min = df["tanggal"].min()
tanggal_max = df["tanggal"].max()

# Membuat filter rentang tanggal
if tanggal_min == tanggal_max:
    # Jika data hanya mencakup satu tanggal saja
    st.sidebar.info(f"📅 Data tercatat pada tanggal: **{tanggal_min}**")
    tanggal_mulai = tanggal_min
    tanggal_selesai = tanggal_max
else:
    rentang_tanggal = st.sidebar.date_input(
        "Pilih Rentang Tanggal:",
        value=(tanggal_min, tanggal_max),
        min_value=tanggal_min,
        max_value=tanggal_max,
        help="Pilih tanggal mulai dan tanggal akhir.",
    )
    # Memastikan pengguna memilih dua titik tanggal (mulai dan akhir)
    if isinstance(rentang_tanggal, (list, tuple)) and len(rentang_tanggal) == 2:
        tanggal_mulai, tanggal_selesai = rentang_tanggal
    elif isinstance(rentang_tanggal, (list, tuple)) and len(rentang_tanggal) == 1:
        tanggal_mulai = tanggal_selesai = rentang_tanggal[0]
    else:
        tanggal_mulai, tanggal_selesai = tanggal_min, tanggal_max

# Menerapkan filter kategori dan rentang tanggal ke dalam DataFrame
df_tersaring = df[
    (df["kategori"].isin(kategori_terpilih)) &
    (df["tanggal"] >= tanggal_mulai) &
    (df["tanggal"] <= tanggal_selesai)
].copy()

# ==============================================================================
# RINGKASAN METRIK KEJADIAN (ANGKA BESAR)
# ==============================================================================

st.subheader("📊 Ringkasan Jumlah Kejadian")

# Menghitung frekuensi kemunculan status berdasarkan data log nyata
total_semua = len(df_tersaring)
total_bahaya = len(df_tersaring[df_tersaring["kategori"] == "BAHAYA"])
total_waspada = len(df_tersaring[df_tersaring["kategori"] == "WASPADA"])
total_asing = len(df_tersaring[df_tersaring["kategori"] == "ORANG_ASING"])
total_pergi = len(df_tersaring[df_tersaring["kategori"] == "PERGI"])
# Menghitung kejadian jeda dari kolom kategori (nilai 'JEDA' berasal dari pola keterangan)
total_jeda = len(df_tersaring[df_tersaring["kategori"] == "JEDA"])

# Menata kartu metrik dalam 6 kolom horizontal yang rapi
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Total Kejadian", f"{total_semua}")
m2.metric("Bahaya (Pengintip)", f"{total_bahaya}", help="Status BAHAYA: ada orang lain dekat dan menghadap layar")
m3.metric("Waspada", f"{total_waspada}", help="Status WASPADA: ada orang di belakang tapi jauh/menoleh")
m4.metric("Orang Asing", f"{total_asing}", help="Status ORANG_ASING: pengguna di depan layar bukan pemilik sah")
m5.metric("Pengguna Pergi", f"{total_pergi}", help="Status PERGI: tidak ada wajah terdeteksi di depan monitor")
m6.metric("Perlindungan Dijeda", f"{total_jeda}", help="Jumlah penekanan tombol P untuk jeda perlindungan")

st.markdown("---")

# ==============================================================================
# GRAFIK VISUALISASI DATA
# ==============================================================================

# Menampilkan peringatan jika tidak ada data yang memenuhi kriteria filter
if df_tersaring.empty:
    st.warning("⚠️ Tidak ada catatan kejadian yang sesuai dengan filter yang dipilih.")
else:
    # Membagi visualisasi grafik ke dalam 2 kolom bersebelahan
    col_grafik1, col_grafik2 = st.columns(2)

    with col_grafik1:
        st.subheader("📌 Frekuensi Kejadian per Status")
        # Menghitung frekuensi kejadian untuk tiap kategori pada data yang tersaring
        kategori_counts = df_tersaring["kategori"].value_counts().reset_index()
        kategori_counts.columns = ["Kategori", "Jumlah"]
        # Menampilkan grafik batang berdasarkan kategori (termasuk JEDA)
        st.bar_chart(kategori_counts.set_index("Kategori"), color="#ff4b4b")

    with col_grafik2:
        st.subheader("⏰ Distribusi Kejadian per Jam (00 - 23)")
        # Menyiapkan kerangka 24 jam (00-23) dengan nilai awal 0 agar semua jam muncul
        jam_lengkap = pd.DataFrame({"Jam": range(24)})
        # Menghitung frekuensi kejadian per jam dari data yang tersaring
        frekuensi_jam = df_tersaring["jam"].value_counts().to_dict()
        # Memetakan frekuensi ke tiap jam; jam tanpa kejadian diisi 0
        jam_lengkap["Jumlah Kejadian"] = jam_lengkap["Jam"].map(frekuensi_jam).fillna(0).astype(int)
        # Membuat label jam dua digit (misal '00:00', '13:00') untuk sumbu x grafik
        jam_lengkap["Jam Label"] = jam_lengkap["Jam"].apply(lambda j: f"{j:02d}:00")
        # Menampilkan bar chart distribusi jam (bukan line chart) agar tiap jam terlihat jelas
        st.bar_chart(jam_lengkap.set_index("Jam Label")["Jumlah Kejadian"], color="#0083B8")

    st.markdown("---")

    # ==============================================================================
    # TABEL DATA LOG KEJADIAN
    # ==============================================================================

    st.subheader("📋 Tabel Riwayat Kejadian (Terbaru di Paling Atas)")

    # Mengurutkan tabel secara menurun (descending) berdasarkan cap waktu agar kejadian terkini di atas
    df_tabel = df_tersaring.sort_values(by="waktu_dt", ascending=False).copy()

    # Menyertakan kolom kategori agar JEDA dapat dibedakan dari status normal di tabel
    kolom_tampil = ["waktu", "kategori", "status", "jumlah_wajah", "jarak_terdekat_cm", "keterangan"]
    kolom_tersedia = [k for k in kolom_tampil if k in df_tabel.columns]

    # Menampilkan tabel interaktif yang dapat dicari dan disortir
    st.dataframe(
        df_tabel[kolom_tersedia],
        width="stretch",
        hide_index=True,
    )

    # Menyediakan tombol unduh data yang tersaring dalam format CSV
    csv_unduh = df_tabel[kolom_tersedia].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Unduh Data Tersaring (.CSV)",
        data=csv_unduh,
        file_name="riwayat_kejadian_privasi.csv",
        mime="text/csv",
    )

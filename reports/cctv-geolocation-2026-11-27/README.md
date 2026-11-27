# Geolokasi CCTV Bina Marga dan Cakupan Street View

**Tanggal:** 27 November 2026  
**Tujuan:** menguji apakah metadata KM/A-B Bina Marga dan citra street-level (KartaView) dapat memberi posisi atau bantuan kalibrasi untuk CCTV tol tanpa koordinat survei.  
**Sumber:** halaman CCTV Bina Marga, rekaman `SkyUnik/CCTV-Jakarta`, centerline OpenStreetMap, dan API KartaView.

---

## 1. Ringkasan

1. **258 kamera** Bina Marga di 16 ruas berhasil diparse. **222** punya koordinat, **206** punya KM; **166** memakai koordinat yang sudah ada, **56** diinterpolasi dari KM + centerline OSM, dan **20** terpaksa di-clamp ke ujung polyline.
2. **Tol Dalam Kota (Cawang–Pluit): 26 kamera**, semuanya dapat koordinat. **21** berstatus `provisional_stationing` (KM + arah A/B), **5** `interpolated_km`; ada **17 KM unik**. Koordinat existing meleset dari centerline OSM **median 21,8 m, maks 133,4 m** — cukup untuk menemukan ruas, tidak cukup untuk pose kamera.
3. **KartaView mencakup 26/26 kamera** dalam radius 300 m. Jarak citra usable **median 2,1 m, maks 6,5 m**; 10 kamera ≤2 m, 14 kamera 2–4 m, 2 kamera 4–6,5 m. Semua citra usable yang terpilih adalah **2020-05/06, proyeksi `PLANE`**.
4. Ada satu **panorama equirect 2023-11-03** (5760×2880) dekat Cawang KM 00+400, tetapi **210,05 m** dari posisi kamera. Matching SIFT/LoFTR terhadap frame CCTV hanya memberi **~25 inlier SIFT / ~12 inlier LoFTR** pada view terbaik. Tidak cukup untuk pose atau `f`.
5. Hasil **115/158 inlier** sebelumnya **tidak valid**. Thumbnail 1280×720 adalah pandangan perspektif (HFOV ≈120°), bukan equirect; mereproject thumbnail sebagai equirect menciptakan match palsu. Korelasi thumbnail dengan crop panorama pada yaw 0/FOV 120 adalah **0,886**, jadi thumbnail itu memang crop dari panorama, bukan citra independen.
6. **Kesimpulan:** street-level 3D localization bukan jalan pintas untuk Cawang dengan citra yang tersedia. KartaView berguna untuk verifikasi kasar ruas/arah, jumlah lajur, dan prior vanishing point; **bukan** anchor metrik. Jalur aktif tetap geometri marka jalan (dash + garis solid).

> **Batasan ground truth.** Referensi dash fit Cawang (`f=1082,58`, `w=3,60 m`) **bukan ground truth independen**; ia adalah hasil fitting dengan asumsi lebar lajur. Satu-satunya ground truth eksternal yang dipakai di riset ini adalah **kalibrasi XML SVLD-3D**. Karena itu, bagian street-view ini tidak boleh dipakai untuk mengklaim akurasi absolut `f`; ia hanya menguji apakah posisi kamera bisa dipersempit.

---

## 2. Metode

### 2.1 Geolokasi dari KM + arah A/B

`scripts/cctv_geolocate.py`:

- Membaca rekaman provider (`SkyUnik/CCTV-Jakarta`): 94 records, 46 dengan KM + A/B, 44 posisi unik.
- Mencocokkan `highway_id` + KM ke centerline OSM, lalu melakukan interpolasi sepanjang polyline.
- Mempertahankan koordinat existing bila ada; memberi status `provisional_stationing`, `interpolated_km`, `provisional_landmark`, `no_km`, atau `clamped_km`.
- Arah A/B mempersempit sisi jalan, tetapi tidak memberi posisi kamera yang tepat: kamera bisa berada 10–30 m dari centerline (tiang, median, atau sisi luar).

Perintah:

```powershell
& $py scripts\cctv_geolocate.py `
  --cameras out\cctv-geolocate\source\cameras.json `
  --out out\cctv-geolocate
```

### 2.2 Cakupan KartaView

`scripts/cctv_streetview_check.py`:

- Endpoint keyless: `https://api.kartaview.org/2.0/photo/?lat=..&lng=..&radius=300&page=..`.
- Endpoint lama `api.openstreetcam.org` sudah 404.
- Untuk citra Jakarta 2019–2020, `imageProcUrl` sering HTTP 500; `imageLthUrl` biasanya masih bekerja.
- Skrip memilih citra usable terdekat dan mencatat jarak, tanggal, dan proyeksi.

```powershell
& $py scripts\cctv_streetview_check.py `
  --cameras out\cctv-geolocate\cameras_dalam_kota.csv `
  --radius 300 --out out\cctv-geolocate
```

### 2.3 Matching CCTV ke street view

`scripts/cctv_streetview_match.py`:

- Untuk panorama equirect: reproyeksi ke view perspektif dengan sapuan yaw/pitch/FOV.
- Untuk citra `PLANE`: dipakai apa adanya.
- Matcher: SIFT + ratio test + RANSAC homografi; LoFTR `outdoor` sebagai pembanding.
- Homografi bukan pose kamera; jumlah inlier hanya dipakai sebagai uji kelayakan awal.

```powershell
& $py scripts\cctv_streetview_match.py `
  --frame out\streetview-proto\frames\cawang_t60.png `
  --lat -6.245114 --lon 106.877589 --radius 300 `
  --matcher both --out out\streetview-proto
```

---

## 3. Hasil

### 3.1 Geolokasi

| Ruas | Kamera | Koordinat | Interpolasi KM | Existing | Tanpa KM |
|---|---:|---:|---:|---:|---:|
| Tol Dalam Kota (Cawang–Pluit) | 26 | 26 | 5 | 21 | 0 |
| Tol JORR S | 46 | 35 | 0 | 35 | 19 |
| JORR E (Bambu Apus–Rorotan) | 35 | 35 | 12 | 23 | 0 |
| Tol Akses Tanjung Priok | 31 | 25 | 1 | 24 | 6 |
| Tol Jakarta–Bogor–Ciawi (Jagorawi) | 29 | 28 | 9 | 19 | 1 |
| Tol Jakarta–Tangerang | 15 | 13 | 3 | 10 | 2 |
| Tol Bekasi–Cawang–Kampung Melayu (Becakayu) | 15 | 11 | 0 | 11 | 10 |
| JORR W2S (Pondok Ranji–Ulujami–Pondok Pinang) | 13 | 7 | 5 | 2 | 6 |
| JORR W2U (Ulujami–Kembangan) | 11 | 7 | 7 | 0 | 4 |
| 6 Tol Dalam Kota (Kelapa Gading–Pulo Gebang) | 9 | 8 | 1 | 7 | 1 |
| JORR 2 (Serpong–Kunciran) | 8 | 8 | 8 | 0 | 0 |
| JORR W1 | 7 | 7 | 0 | 7 | 0 |
| JORR 2 (Kunciran–Cengkareng) | 4 | 4 | 0 | 4 | 2 |
| Tol Pelabuhan (Cawang–Tanjung Priok–Pluit) | 3 | 3 | 3 | 0 | 0 |
| Tol Depok–Antasari (Desari) | 3 | 3 | 0 | 3 | 0 |
| JORR 2 (Serpong–Cinere) | 3 | 2 | 2 | 0 | 1 |
| **Total** | **258** | **222** | **56** | **166** | **52** |

Catatan: `Interpolasi KM` adalah `coord_source=interpolated_km`; `Existing` adalah baris yang memakai koordinat yang sudah ada. 20 kamera berstatus `clamped_km` karena KM berada di luar ujung polyline OSM.

Untuk 26 kamera Dalam Kota:

- **17 KM unik**: 0,4; 0,7; 2,1; 3,8; 5,4; 6,0; 7,0; 10,1; 10,6; 11,0; 12,0; 13,2; 14,0; 16,1; 17,0; 18,2; 19,0.
- Offset koordinat existing terhadap centerline OSM: **median 21,8 m, maks 133,4 m** (21 baris yang punya koordinat existing).
- Offset ini adalah jarak lateral, bukan error posisi sepanjang jalan. Error sepanjang jalan bisa lebih besar karena interpolasi KM.

### 3.2 Cakupan KartaView

| Metrik | Nilai |
|---|---|
| Kamera diperiksa | 26 |
| Punya citra usable | 26/26 |
| Jarak citra usable, median | 2,1 m |
| Jarak citra usable, maks | 6,5 m |
| Sebaran ≤2 m / 2–4 m / 4–6,5 m | 10 / 14 / 2 |
| Tanggal citra usable | 2020-05 (4), 2020-06 (22) |
| Proyeksi | `PLANE` (26/26) |

Semua citra usable adalah **perspektif**, bukan 360°. Ini penting: `PLANE` tidak bisa diperlakukan sebagai equirect.

### 3.3 Panorama Cawang 2023 dan hasil matching

Metadata panorama:

- Photo ID: `1838190345`
- Tanggal: 2023-11-03
- Ukuran: 5760×2880 (equirect 2:1)
- Posisi: `-6.245114, 106.877589`
- Jarak ke koordinat sementara Cawang KM 00+400 (`-6.2466969, 106.8786261`): **210,05 m**

Hasil matching terhadap frame CCTV `cawang_t60.png`:

| View | Metode | Good matches | Inlier |
|---|---|---:|---:|
| Thumbnail mentah 1280×720 | SIFT | 71 | 12 |
| Equirect crop FOV 115°, yaw 0° | SIFT | 79 | 17 |
| Equirect crop FOV 100°, pitch −20°, yaw 0° | SIFT | 84 | **25** |
| Equirect crop FOV 120°, yaw 0° | LoFTR conf 0,2 | 74 | 12 |
| Equirect crop FOV 120°, yaw 0° | LoFTR conf 0,3 | 38 | 9 |

Angka 115/158 inlier yang sempat muncul **tidak dimasukkan** karena berasal dari memperlakukan thumbnail perspektif sebagai equirect. Dengan reproyeksi yang benar, hasilnya turun ke ~25 inlier SIFT dan ~12 inlier LoFTR.

### 3.4 Mengapa matching gagal

1. **Jarak viewpoint 210 m.** Kamera CCTV berada di interchange Cawang pada ketinggian ~9 m; panorama berada di permukaan jalan, 210 m dari titik itu. Paralaks, oklusi, dan perbedaan skala terlalu besar.
2. **Beda waktu 2023 vs 2026.** Bangunan, papan reklame, vegetasi, lajur, dan kendaraan berubah.
3. **Kualitas citra.** Frame CCTV berasal dari stream HLS 1280×720 yang terkompresi; crop panorama yang relevan juga turun resolusinya setelah reproyeksi.
4. **Tekstur repetitif.** Aspal, marka, dan pagar menghasilkan fitur generik; RANSAC bisa menemukan homografi yang salah dengan 20–25 inlier.
5. **Homografi bukan pose.** Bahkan dengan inlier cukup, homografi tidak memberi `f`, pitch, yaw, dan `h` secara terpisah tanpa asumsi tambahan.

### 3.5 Implikasi

Yang **bisa** dilakukan dengan KartaView:

- Memverifikasi bahwa kamera berada di ruas dan arah yang benar.
- Menghitung jumlah lajur dan lebar lajur secara kasar (dengan error beberapa puluh sentimeter).
- Memberi prior arah jalan/vanishing point untuk inisialisasi.
- Memeriksa apakah geometri jalan lurus atau melengkung.

Yang **tidak bisa** dilakukan:

- Menentukan `f` absolut.
- Menentukan pitch/yaw presisi tinggi.
- Menjadi anchor metrik tanpa pose kamera yang sebenarnya.

Jika jalur street-level 3D localization ingin dilanjutkan, syarat minimumnya adalah citra street view dalam **~10–20 m** dari kamera, pada ketinggian viewpoint yang sebanding, dengan perubahan scene yang kecil, dan solver pose (bukan hanya homografi). Untuk Cawang saat ini, syarat itu tidak terpenuhi.

---

## 4. Keterbatasan

- Akurasi centerline OSM dan pemetaan KM tidak diketahui; error sepanjang jalan bisa puluhan meter.
- Arah A/B tidak selalu tersedia; 52 kamera tidak punya KM.
- Citra KartaView 2020 sudah 6 tahun lebih tua dari CCTV 2026.
- Uji matching hanya satu frame dan satu panorama; multi-frame bisa menambah inlier tetapi tidak menghilangkan gap 210 m.
- GPS panorama punya error sendiri (biasanya 5–10 m).
- Cakupan KartaView di Jakarta relatif padat tetapi tua; kota lain bisa jauh lebih buruk.

---

## 5. Berkas

| Berkas | Isi |
|---|---|
| `dalam_kota_cameras.csv` | 26 kamera Cawang–Pluit: KM, arah, koordinat, status, offset |
| `streetview_coverage.csv` | 26 baris cakupan KartaView: jarak, tanggal, proyeksi, ID |
| `geolocate_summary.json` | Ringkasan 258 kamera dan per-ruas |
| `streetview_summary.json` | Ringkasan cakupan 26 kamera |
| `../../scripts/cctv_geolocate.py` | KM + OSM → koordinat sementara |
| `../../scripts/cctv_streetview_check.py` | Cakupan dan citra usable KartaView |
| `../../scripts/cctv_streetview_match.py` | Matching SIFT/LoFTR CCTV–street view |

---

## 6. Kesimpulan untuk arah riset

1. **Jangan jadikan street view sebagai sumber `f`.** Dengan citra yang ada, hasilnya lemah dan tidak reprodusibel.
2. **Pakai street view hanya sebagai sanity check** posisi/arah dan jumlah lajur.
3. **Prioritaskan geometri marka**: dash fit + garis solid, dengan lebar lajur diukur per lokasi. Ini jalur yang bisa memberi `f` tanpa koordinat survei.
4. **Ground truth eksternal tetap SVLD XML**, bukan dash fit Cawang. Dash fit Cawang hanya referensi konsistensi dengan asumsi `w=3,60 m`.

# Screening Dash Fit di 5+ CCTV Berbeda

**Tanggal:** 26 November 2026  
**Tujuan:** mencari ground truth `f`, pitch, yaw, dan `h` dari dash fit di beberapa CCTV baru, sebelum membandingkan GeoCalib/VP.  
**Sumber video:** `D:\Kerjaan\CCTVExplorer\recordings`  
**Salinan video:** `D:\Kerjaan\riset-carom\videos\`

---

## 1. Ringkasan

1. **Lima CCTV utama diuji**: Cawang, BELMERA KM 25+200, BORR KM 03+400, Pluit KM 24+800, dan CIAWI IC KM 48+200. Beberapa tambahan (CIAWI KM 55, Semarang, Priok, BORR 00+100/900) diuji sebagai pembanding.
2. **Hanya Cawang yang sepenuhnya identifiabel.** Cawang punya dua batas lajur putus-putus yang berdekatan + lebar lajur 3,60 m: 18 observasi, 6 parameter, DoF 12. Hasil `f=1082,58`, pitch `2,432°`, yaw `0,271°`, `h=8,876 m`, RMS `1,101 px`.
3. **BELMERA dan BORR hanya punya satu garis putus-putus.** Dengan 3 dash × 3 residual = 9 observasi dan 6 parameter, `f` tidak teridentifikasi: setelah `f` dipaku ke nilai lain, solver tetap memberi RMS yang sama. Angka `f` mereka **bukan ground truth**.
4. **Pluit, CIAWI IC, Semarang, BORR 00+100/900 gagal**: jalan melengkung, dash bergabung/terpisah, resolusi rendah, atau kontras rendah. CIAWI IC memberi RMS rendah tetapi `h=26 m` (tidak masuk akal), jadi ditolak.
5. **Priok tidak punya garis putus-putus** (hanya garis solid), sehingga dash fit tidak mungkin.
6. **GeoCalib sangat bervariasi antar kamera.** Pada Cawang (GT sah) error `−13 s/d −14%`; pada BELMERA/BORR perbedaan terhadap garis single-line `−10%` dan `+44%`, tetapi garis itu **bukan GT** karena f tidak identifiabel. Yang tetap valid: rentang f GeoCalib 823–1664 px dan uncertainty 22–35% di lima kamera. Ini alasan kuat untuk tidak memakai GeoCalib sebagai sumber f universal.

---

## 2. Video yang diuji

| Prioritas | CCTV | File | Resolusi | Durasi | Status dash fit |
|---|---|---|---|---:|---|
| 1 | Cawang KM 00+400 | `recording cawang.mp4` | 1280×720 | 600 s | **pass, identifiabel** |
| 2 | BELMERA KM 25+200 | `belmera_km25_200_2026-08-18.mp4` | 1280×720 | 176 s | underdetermined |
| 3 | BORR KM 03+400 | `borr_km03_400_2026-08-18.mp4` | 1024×768 | 219 s | underdetermined |
| 4 | Pluit KM 24+800 | `pluit_km24_800_2026-08-10.mp4` | 1280×720 | 600 s | gagal (kurva) |
| 5 | CIAWI IC KM 48+200 | `ciawi_ic_selatan_km48_2026-09-08.mp4` | 640×480 | 600 s | ditolak (h tidak fisik) |
| + | CIAWI KM 55+050 | `ciawi_km55_050_2026-09-08.mp4` | 704×576 | 600 s | gagal (kontras) |
| + | Semarang KM 425+700 | tidak disalin | 640×480 | 309 s | gagal (RMS 4,8) |
| + | Priok KM 13+200 | `priok_km13_200_2026-08-07.mp4` | 1280×720 | 600 s | gagal (tanpa dash) |
| + | BORR KM 00+100 | `borr_km00_100_2026-08-18.mp4` | 640×480 | 124 s | gagal (dash bergabung) |
| + | BORR KM 00+900 | `borr_km00_900_2026-08-21.mp4` | 640×480 | 150 s | gagal (<3 dash bersih) |

Semua frame referensi adalah **median temporal lokal 49 frame** di sekitar detik 30–80 (Pluit: 150–199), bukan frame tunggal.

---

## 3. Metode

- Deteksi kandidat dash: ambang putih di HSV, connected components, PCA untuk endpoint. Skrip: `scripts/calib_compare/detect_dashes.py`.
- Fit model kamera yang sama dengan Cawang:
  - `Y = Y0 - lane·w`, `X = Xp + row·PERIOD`, `PERIOD=13 m`, `DASH=5 m`, `w=3,60 m`.
  - Unknown: `f, pitch, yaw, h, Xp, Y0`.
  - Residual: `vFar`, `vNear`, `u` per dash.
- Dua mode:
  - **free fit** — semua parameter bebas.
  - **fixed f** — `f` dipaku, lalu fit pose; jika RMS tetap sama, `f` tidak teridentifikasi.
- Skrip: `scripts/calib_compare/fit_dash_line.mjs`.

**Catatan identifiabilitas:** 3 dash pada satu garis memberi 9 observasi. Free fit 6 parameter (DoF 3); fixed f 5 parameter (DoF 4). Kalau RMS fixed f sama dengan free fit, artinya pose dapat menyerap perubahan f — f tidak bisa dipercaya. Ini terjadi di BELMERA dan BORR.

---

## 4. Hasil dash fit

| CCTV | Garis | Dash | f (px) | Pitch | Yaw | h (m) | RMS (px) | Fixed-f RMS | Putusan |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Cawang | 2 lajur | 6 | **1082,58** | 2,432° | 0,271° | 8,876 | **1,101** | 2,168 (f=1082, median2) | **pass** |
| BELMERA | 1 garis | 3 | 1101,09 | 11,803° | 0,122° | 8,220 | 0,320 | 0,320 (f=989) | underdetermined |
| BORR | 1 garis | 3 | 1156,45 | 11,242° | 6,006° | 6,297 | 1,314 | 1,314 (f=1664) | underdetermined |
| Pluit | 1 garis (2-line gagal) | 3 | 3770,87 | 12,099° | −5,722° | 41,589 | 16,234 | — | gagal |
| CIAWI IC | 1 garis | 3 (manual) | 2046,89 | 9,736° | −3,796° | 26,016 | 1,864 | — | ditolak |
| Semarang | 1 garis | 3 | 2948,93 | 6,361° | −1,180° | 9,923 | 4,832 | — | gagal |
| BORR 00+100 | 1 garis | 3 | 3642,65 | 11,496° | −8,266° | 18,506 | 19,555 | — | gagal |

**Cawang** tetap satu-satunya referensi yang sah: dua batas lajur putus-putus, lebar lajur diketahui, dan fixed-f RMS memburuk (2,168 vs 1,101) — bukti f benar-benar dikonstrain.

**BELMERA/BORR** memberi RMS rendah, tetapi fixed-f RMS **identik** dengan free fit. Artinya nilai f mereka ditentukan oleh optimizer/initial guess, bukan oleh data. Jangan dipakai untuk klaim akurasi f.

**Pluit** adalah contoh penting: dua garis putus-putus ada, tetapi jalan melengkung. Fit satu garis jatuh ke `h=41,6 m` dengan RMS 16 px; percobaan dua garis tidak menghasilkan solusi fisik.

**CIAWI IC** memberi RMS 1,86 px, tetapi `h=26 m`; ini solusi salah yang kebetulan cocok. Ditolak.

---

## 5. GeoCalib vs dash fit

### 5.1 Cawang (referensi sah)

| Frame | f dash | f GeoCalib | Δf | Pitch dash | Pitch GeoCalib | Δpitch | RMS GeoCalib+VP |
|---|---:|---:|---:|---:|---:|---:|---:|
| t350 | 1082,43 | 928,50 | −14,22% | 2,482° | 1,987° | −0,494° | 4,674 px |
| t500 | 1082,03 | 944,10 | −12,75% | 2,485° | 2,103° | −0,382° | 4,285 px |

VP-only dengan f dash: RMS `1,323/1,374 px`, Δpitch `+0,165/+0,163°`, Δyaw `+0,311/+0,322°`. GeoCalib+VP tidak memperbaiki f.

### 5.2 BELMERA dan BORR (bukan GT; hanya konsistensi)

| CCTV | f garis | f GeoCalib | Δf | Pitch garis | Pitch GeoCalib | Δpitch | Roll GeoCalib | Uncertainty |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BELMERA | 1101,09 | 989,11 | −10,17% | 11,803° | 11,402° | −0,401° | −2,038° | 281,7 px (28,5%) |
| BORR | 1156,45 | 1663,67 | **+43,9%** | 11,242° | 8,259° | **−2,983°** | −1,134° | 505,2 px (30,4%) |

Karena f garis BELMERA/BORR tidak identifiabel, angka Δf ini **bukan akurasi absolut**. Tetapi variasi GeoCalib sangat besar: −10% di BELMERA, +44% di BORR, −13% di Cawang. GeoCalib sendiri memberi uncertainty 22–30% pada ketiganya — sinyal bahwa f tidak stabil.

**VP independen tidak tersedia untuk BELMERA/BORR.** `vpfit` hanya menemukan 3 komponen di BELMERA dan gagal di BORR; satu garis putus-putus tidak cukup untuk VP. Karena itu GeoCalib+VP tidak dihitung di sana; yang dibandingkan hanya f/pitch GeoCalib terhadap garis (yang juga tidak identifiabel). VP yang stabil hanya ada di Cawang, dari median2 49 frame.

### 5.3 GeoCalib di lima CCTV (tanpa GT untuk Pluit/CIAWI)

| CCTV | f GeoCalib | HFOV | Pitch | Roll | Uncertainty | Uncertainty/f |
|---|---:|---:|---:|---:|---:|---:|
| Cawang | 928,50–944,10 | 69,2–68,3° | 1,99–2,10° | −0,56° | 213 px | 22,6% |
| BELMERA | 989,11 | 65,8° | 11,40° | −2,04° | 282 px | 28,5% |
| BORR | 1663,67 | 34,2° | 8,26° | −1,13° | 505 px | 30,4% |
| Pluit | 926,63 | 69,3° | 0,11° | −0,40° | 221 px | 23,8% |
| CIAWI IC | 823,51 | 42,5° | 4,92° | 0,46° | 286 px | 34,7% |

Rentang f GeoCalib **823–1664 px** dan pitch **0,1–11,4°** pada lima kamera. Untuk Pluit dan CIAWI tidak ada GT dash fit, jadi angka ini bukan error; tetapi variasi sebesar itu menunjukkan model sangat bergantung pada scene. Uncertainty 22–35% pada semua kamera adalah red flag: GeoCalib sendiri tidak yakin.

---

## 6. Temuan utama

1. **Dash fit bukan ground truth universal.** Ia hanya identifiabel jika ada **dua batas lajur putus-putus yang berdekatan** (atau cukup banyak baris dash) dan lebar lajur/period/panjang dash diketahui. Cawang memenuhi; CCTV lain umumnya tidak.
2. **Satu garis putus-putus tidak cukup.** Tiga dash memberi 9 observasi; pose dapat menyerap f. Fixed-f RMS sama dengan free fit adalah bukti langsung.
3. **Jalan melengkung menghancurkan model garis lurus.** Pluit, Semarang, BORR 00+100 gagal; RMS tinggi atau solusi tidak fisik.
4. **Kontras/resolusi rendah** (CIAWI KM55, 704×576) membuat ekstraksi dash tidak stabil.
5. **GeoCalib tidak konsisten antar kamera.** −10% s/d +44%; uncertainty 22–30%. Gate `|Δf|<5%` tidak akan lulus di semua kamera ini.
6. **Untuk 5 CCTV, hanya Cawang yang bisa dipakai sebagai GT dash fit.** Sisanya memerlukan anchor fisik (kontainer/lebar lajur/tinggi kamera) atau data tambahan.

---

## 7. Implikasi

- **Jangan menganggap dash fit bisa menggantikan anchor di semua lokasi.** Ia alat site-specific, bukan pipeline otomatis universal.
- **Untuk produksi:** anchor-first tetap jalur utama. Dash fit dipakai hanya di situs yang geometrinya memenuhi syarat (dua lajur dash, jalan lurus, lebar lajur diketahui).
- **Untuk riset 5 kamera:** perlu memilih CCTV dengan dua batas lajur dash; atau menambahkan pengukuran `w`/`h` per situs. Tanpa itu, klaim akurasi f tidak sah.
- **GeoCalib:** tetap fallback/inisialisasi, bukan sumber f. Uncertainty >20% harus menjadi red flag.

---

## 8. Artefak

- Video: `videos/*.mp4` (8 video; `*.mp4` di-ignore git).
- Frame median: `videos/frames/*_tm*.png`, `videos/frames/*.ppm`.
- Kandidat dash: `videos/frames/*_dashes_candidates.csv`.
- Dash terpilih: `videos/frames/*_sel.json`.
- Fit: `videos/frames/*_fit.csv/json`.
- GeoCalib: `videos/frames/geocalib_belmera.json`, `videos/frames/geocalib_borr.json`.
- Screening: `videos/screening_5cctv.csv`.
- Skrip: `scripts/calib_compare/detect_dashes.py`, `scripts/calib_compare/fit_dash_line.mjs`.

---

## 9. Kesimpulan satu paragraf

Dari 5+ CCTV yang diuji, hanya Cawang yang memberikan dash fit identifiabel (`f=1082,58`, RMS `1,101 px`). BELMERA dan BORR memberi fit yang terlihat bagus (RMS 0,32/1,31 px) tetapi f-nya tidak teridentifikasi: fixed-f RMS sama dengan free fit, jadi f bisa digeser tanpa merusak fit. Pluit, CIAWI, Semarang, dan BORR 00 gagal karena kurva, dash bergabung/terpisah, kontras rendah, atau solusi tidak fisik; Priok tidak punya dash. GeoCalib memberi f 823–1664 px dan uncertainty 22–35%; pada Cawang GT error f −13 s/d −14%, sedangkan perbedaan −10%/+44% di BELMERA/BORR hanya konsistensi terhadap garis single-line yang bukan GT. Jadi dash fit adalah **alat site-specific**, bukan ground truth universal; untuk 5 kamera dibutuhkan anchor fisik atau CCTV dengan dua batas lajur dash yang jelas.

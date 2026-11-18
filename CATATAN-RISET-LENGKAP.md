# Catatan Riset Lengkap — CAROM Air untuk CCTV

Status: 18 November 2026
HEAD saat catatan dibuat: `1fadfc4`

Dokumen ini adalah **ringkasan master**. Detail ada di berkas yang ditautkan di §10.

---

## 1. Pertanyaan riset

1. Apakah metode CAROM Air (drone, keypoint + model bentuk) dapat diadaptasi untuk mengukur dimensi kendaraan dari CCTV statis?
2. Komponen mana yang transfer, mana yang tidak?
3. Akurasi apa yang realistis untuk panjang, lebar, dan tinggi?
4. Apakah standar kontainer bisa menjadi ground truth tanpa pengukuran lapangan?

## 2. Putusan saat ini

| Aspek | Status | Angka |
|---|---|---|
| Geometri pengukuran | **terbukti** | MAPE 0,36% dengan 8 sudut GT |
| Kalibrasi SVLD | **terverifikasi** | median reproyeksi 0,74 px |
| GeoCalib | **tidak reliabel di SVLD** | 1/5 scene lulus |
| Lebar/tinggi (mask) | **layak screening** | W 7,1%, H 7,6% |
| Panjang (mask) | **belum layak** | L 21,9% |
| Keypoint zero-shot | **belum cukup** | Car 44,1%, Bus 0% |
| Container-only 20 ft | **tervalidasi** | 6,046 vs 6,058 m (−0,2%) |
| Container-only 40 ft | **ambigu** | 13,99 m; 40 ft +14,7%, 45 ft +2,0% |

**Klaim yang sah:**

> "Kerangka geometri CAROM Air dapat diadaptasi untuk mengukur lebar dan tinggi dari CCTV statis; dengan titik 2D yang akurat, geometri mencapai <1%, dan mask-based memberi ~7% untuk W/H. Panjang tidak dapat diandalkan dari satu pandangan head-on; dibutuhkan sisi kendaraan, multi-frame, atau multi-kamera."

**Klaim yang tidak sah:**

> "CAROM Air dapat mengukur L/W/H dari CCTV dengan akurasi 10%."

---

## 3. Temuan teori penting

### 3.1 Anisotropi galat

$$
\sigma_{\text{lateral}}=\sqrt2\,\frac{z}{f}\sigma_{px},
\qquad
\sigma_{\text{kedalaman}}=\sqrt2\,\frac{z^2}{fh}\sigma_{px}
$$

Rasio anisotropi:

$$
\frac{\sigma_{\text{kedalaman}}}{\sigma_{\text{lateral}}}=\frac{z}{h}
$$

Tidak bergantung pada focal length atau resolusi. Pada Cawang ($h=8{,}876$ m, $\sigma_{px}=1{,}5$):

| Jarak | Lateral | Longitudinal | Anisotropi |
|---:|---:|---:|---:|
| 20 m | 3,9 cm | 8,8 cm | 2,2× |
| 30 m | 5,9 cm | 19,8 cm | 3,4× |
| 40 m | 7,8 cm | 35,2 cm | 4,5× |
| 50 m | 9,8 cm | 55,0 cm | 5,6× |

### 3.2 Degenerasi kalibrasi

Dari marka jalan saja, transformasi

$$
(f,\theta,h,w,Y_0)\longmapsto
\left(\lambda f,\frac{\theta}{\lambda},\frac{h}{\lambda},\frac{w}{\lambda},\frac{Y_0}{\lambda}\right)
$$

tidak mengubah citra. Yang terukur hanya $f\theta$, $fh$, $fw$, dan $w/h$. Satu anchor metrik wajib.

### 3.3 Batas panjang

Panjang tidak teramati bila sumbu optik hampir sejajar jalan. Ini bukan soal algoritma; informasi geometrinya tidak ada. Solusi: sisi kendaraan terlihat (kamera miring), multi-frame, atau multi-kamera.

### 3.4 Lima titik cukup

Dengan 4 kontak tanah + 1 sudut atap, MAPE 0,48%; 8 sudut 0,36%. Detektor tidak perlu 8 sudut box.

### 3.5 Standar kontainer

ISO 668: 20 ft = 6,058 m; 40 ft = 12,192 m; 45 ft = 13,716 m; lebar 2,438 m; tinggi 2,591 m (standar) / 2,896 m (high cube). Ini GT sah **untuk kontainer**, bukan truk total.

---

## 4. Temuan eksperimen

### 4.1 Kalibrasi Cawang REV2

| Parameter | Nilai |
|---|---:|
| $f$ | 1082,6 px |
| pitch | 2,432° |
| yaw | 0,271° |
| $h$ | 8,876 m |
| $w$ (anchor) | 3,60 m |
| RMS | 1,097 px |

Empat set parameter (A–D) memfit citra hampir sama; perbedaan proyeksi maksimum 1,37 px. Kalibrasi geometrik berhasil, identifikasi parameter tidak.

### 4.2 GeoCalib

- Rekaman 480×360: $f=616\pm30$ px, pitch 12,1°; VP 11,0° → selisih 1,1°.
- SVLD 5 scene: hanya **1/5** lulus f<5% dan pitch<2°; f meleset 2,1–51,0%, pitch 0,81–4,99°.
- Kesimpulan: GeoCalib berguna, tetapi **wajib divalidasi per scene**. Jangan jadikan satu-satunya sumber $f$.

### 4.3 SVLD-3D

- Test set: 2.237 citra, 8.142 objek; **7.396 Car, 745 Bus, 1 Truck**.
- Kalibrasi: `f`, `fi` = pitch, `theta` = yaw, `h` mm.
- Reproyeksi 8.142 objek: median **0,74 px**, p90 0,85, maks 1,08, 0 objek >2 px.
- Kamera SVLD menghadap jalan (sudut 4–29°), **bukan side-view**; tidak bisa memvalidasi panjang.

### 4.4 Geometri 50 objek

26 Car + 24 Bus, jarak 13,5–122,9 m, input 8 sudut 2D GT.

| Metrik | Mean | Median | p90 | Max |
|---|---:|---:|---:|---:|
| MAPE LWH | **0,36%** | 0,23% | 0,81% | 1,18% |
| L | 0,65% | 0,36% | 1,59% | 3,16% |
| W | 0,15% | 0,12% | 0,33% | 0,44% |
| H | 0,30% | 0,23% | 0,53% | 1,25% |
| RMS | 0,35 px | 0,35 px | 0,41 px | 0,46 px |

### 4.5 Sensitivitas noise

| $\sigma$ | MAPE | Gagal |
|---:|---:|---:|
| 0 | 0,36% | 0% |
| 1 px | 1,05% | 0% |
| 2 px | 1,91% | 0% |
| 3 px | 2,79% | 1,7% |
| 5 px | 4,57%* | 63,2% |

\* hanya 37% berhasil.

**Target keypoint: ≤3 px.**

### 4.6 Subset sudut

| Subset | MAPE | Gagal |
|---|---:|---:|
| 8 sudut | 0,36% | 0 |
| 6 sudut | 0,46% | 0 |
| **5 sudut** | **0,48%** | **0** |
| 4 kontak tanah | 2,39% | 1 |
| 4 sudut atap | 3,04% | 0 |
| 2 tanah + 2 atap | 4,27% | 0 |

### 4.7 Keypoint zero-shot

Model `vehicle-keypoints` (YOLO26-pose, 14 keypoint, MIT), 20 citra SVLD, 72 objek GT.

| Kelompok | GT | Cocok | 5/5 di antara cocok | 5/5 dari semua GT |
|---|---:|---:|---:|---:|
| Semua | 72 | 41 (56,9%) | 63,4% | 36,1% |
| Car | 59 | 33 (55,9%) | 78,8% | 44,1% |
| Bus | 13 | 8 (61,5%) | 0% | 0% |

### 4.8 Mask-based

YOLO11n-seg, 21 objek.

| Kelompok | n | MAPE | L | W | H | IoU |
|---|---:|---:|---:|---:|---:|---:|
| Semua | 21 | 12,19% | 21,92% | 7,11% | 7,55% | 0,796 |
| Car | 12 | 12,86% | 22,20% | 8,07% | 8,32% | 0,780 |
| Bus | 9 | 11,30% | 21,56% | 5,83% | 6,51% | 0,820 |

### 4.9 Cawang side-view / time-of-passage

Lower envelope mask + VP direction + back-projection ground.

| t (s) | Lane | Median L | Tafsiran |
|---:|---|---:|---|
| 32 | far | 11,56 m | 20 ft / box truck |
| 86 | far | 14,63 m | 40 ft container + kabin |
| 247 | near | 6,44 m | box truck kecil |
| 431 | far | 16,74 m | truk panjang |
| 567 | far | 17,37 m | truk panjang |
| 578 | near | 14,69 m | 40 ft container |

Truk SINKOR 40 ft: 14,04 m median (13,71–15,22); kecepatan 61,2 km/jam. Kontur mentah memberi 15,9 m — terlalu panjang.

Kecepatan batch 7–119 km/jam: **tidak stabil**, baseline 0,8 s terlalu pendek.

### 4.10 Grounded SAM 2 container-only

Grounding DINO tiny + SAM 2.1 tiny.

- Prompt teks `"shipping container."` → box mencakup kabin; mask whole-truck.
- Box prompt kontainer `[255,475,405,645]` → mask container-only 21.907 px; 0 piksel hijau (kabin); 75,2% piksel merah (kontainer).
- Fit 3D box dengan H=2,591:

| Kontainer | Standar | Fit | Galat | IoU |
|---|---:|---:|---:|---:|
| 20 ft TEMA | 6,058 m | **6,046 m** | **−0,2%** | 0,972 |
| 40 ft SINKOR | 12,192 m | 13,990 m | +14,7% | 0,741 |
| 40 ft SINKOR (jika 45 ft) | 13,716 m | 13,990 m | +2,0% | 0,741 |

20 ft TEMA adalah **validasi GT pertama yang bersih**. 40 ft SINKOR ambigu tipe.

---

## 5. Kesalahan dan koreksi

| # | Kesalahan | Dampak | Koreksi | Status |
|---:|---|---|---|---|
| 1 | REV1 mengklaim $f,h,w$ terukur | kalibrasi tidak sahih | REV2: degenerasi 1-parameter | selesai |
| 2 | Memakai `16-15-44.mp4` 480×360 @115 kbps | tidak layak ukur | audit; rekomendasi main stream | selesai |
| 3 | Menganggap CenterLoc3D 85% = 15% per sumbu | salah tafsir akurasi | 85% = jumlah 3 sumbu ≈15%, rata-rata ≈5% | selesai |
| 4 | Menganggap `theta` SVLD = pitch | kalibrasi tertukar | `fi` = pitch, `theta` = yaw | selesai |
| 5 | Endpoint kontur mentah | 40 ft jadi 15,9 m | lower envelope → 14,0–14,3 m | selesai |
| 6 | Container-only pakai mask warna | 13,81 m vs 12,19 (+13,3%) | SAM2 box prompt container-only | selesai |
| 7 | YOLO26-seg dianggap lebih baik | 17,5 m vs 14,04 m | tetap YOLO11/lower envelope | selesai |
| 8 | Prompt teks SAM2 mencakup kabin | mask whole-truck | box prompt kontainer-only | selesai |
| 9 | Kecepatan dari baseline 0,8 s | 7–119 km/jam | jangan pakai kecepatan; panjang lebih stabil | terbuka |
| 10 | `P` I24-3D dianggap 4×3 | potensi transpose salah | parser menerima 3×4/4×3; cek round-trip | siap |
| 11 | GeoCalib dipercaya tanpa cek | f salah di 4/5 SVLD | gerbang pitch vs VP | selesai |
| 12 | OpenPifPaf dianggap bisa langsung | build gagal (MSVC/torch 1.13.1) | ganti `vehicle-keypoints` | selesai |
| 13 | GSNet dianggap punya bobot | bobot pretrained dihapus | fitting manual; data ApolloCar3D NC | terbuka |
| 14 | SVLD dianggap punya truk | hanya 1 Truck | truk dari I24-3D/RoScenes | selesai |
| 15 | SVLD dianggap bisa uji panjang | kamera 4–29° (rear/front) | butuh data side-view | selesai |
| 16 | 40 ft SINKOR dianggap 40 ft | bisa 45 ft | perlu identifikasi tipe | terbuka |
| 17 | Ambiguitas 2 vs 3 lajur ATP | skala bisa 1,4× | belum diselesaikan | terbuka |
| 18 | Truk ATP 2,1 m vs harapan 2,6–2,9 m | galat 25–30% | hipotesis lajur/segmentasi | terbuka |

---

## 6. Kendala

| Kendala | Dampak | Status / workaround |
|---|---|---|
| Tanpa multi-kamera | panjang sulit | side-view 1 kamera, multi-frame, atau kamera miring |
| Tanpa plat | tidak bisa lookup dimensi | pure pixel; standar kontainer |
| Tanpa GPU | training/fine-tune lambat | CPU inference; model siap pakai |
| I24-3D pending | GT 50 kamera & truk belum tersedia | ajukan akses; SVLD sementara |
| Situs I24-3D menolak `curl` (WAF) | otomasi gagal | registrasi via browser |
| Tanpa GT lokal Indonesia | klaim akurasi terbatas | SVLD/Cawang proksi; field test |
| Cawang pitch 2,43° | degenerasi terburuk | anchor lebar lajur 3,60 m |
| Jalan Cawang melengkung | galat sistematis | batasi segmen lurus |
| Kalibrasi Cawang tanpa GT | hanya konsistensi | standar kontainer 20 ft |
| Mask body tanpa ban | panjang bias | lower envelope; SAM2 container-only |
| Kecepatan tidak stabil | time-of-passage mentah | track lebih panjang; garis crossing |
| Lisensi non-komersial | tidak untuk produk | validasi riset; data sendiri |
| SVLD hanya 1 Truck | truk tak teruji | I24-3D/RoScenes |
| 40 ft ambigu 40/45 | GT tidak pasti | identifikasi tipe/kode kontainer |
| Kontainer di atas sasis | back-projection ground salah | tinggi standar + 3D fit |
| Kamera SVLD bukan side-view | tak bisa validasi panjang | data side-view/I24-3D |

---

## 7. Pertanyaan terbuka

1. **2 vs 3 lajur ATP** — apakah jalan itu 2 atau 3 lajur? Skala bisa berubah 1,4×.
2. **40 ft SINKOR** — 40 ft atau 45 ft? Perlu identifikasi tipe.
3. **Generalisasi 20 ft** — apakah 3–5 kontainer 20 ft lain juga memberi 6,0–6,2 m?
4. **Detektor 5 titik** — apakah ada model yang mencapai ≤3 px pada mobil dan bus?
5. **Time-of-passage murni** — apakah $L=v\Delta t$ lebih stabil daripada side-view?
6. **Multi-frame 1 kamera** — apakah sudut pandang berubah cukup untuk panjang?
7. **Truk/bus side-view GT** — I24-3D satu kamera atau field test.
8. **Validasi Indonesia** — satu kendaraan diukur dengan meteran.
9. **Metrologi legal** — sertifikasi alat, ketertelusuran.
10. **Lisensi model** — OpenPifPaf AGPL, data NC; jalur produksi belum jelas.

---

## 8. Riset dan sumber penting

| Sumber | Kontribusi | Catatan |
|---|---|---|
| CAROM Air (Lu dkk., ICRA 2023) | keypoint + model bentuk, EKF, drone | weak perspective; tidak transfer langsung ke CCTV |
| CAROM (Lu dkk., ICRA 2021) | infrastruktur, mask + tangent hull | pendahulu untuk CCTV |
| GeoCalib (Veicht dkk., ECCV 2024) | f, pitch, roll dari 1 citra | 1/5 SVLD; wajib cek VP |
| SVLD-3D / CenterLoc3D (Tang dkk.) | 2.237 citra, GT L/W/H, kalibrasi | truk hanya 1; kamera rear/front |
| I24-3D (Gloudemans dkk., BMVC 2023) | 16–17 kamera, 877k box, P/H/VP | pending; GT terbaik |
| SKoPe3D (Pahadia dkk., ITSC 2023) | 25k CARLA, 33 keypoint, side CCTV | tidak ada bobot pretrained |
| GSNet (Ke dkk., ECCV 2020) | 79 mesh + PCA | bobot dihapus; data NC |
| OpenPifPaf | 24/66 keypoint | build gagal di Windows; AGPL |
| vehicle-keypoints | YOLO26-pose 14 keypoint | zero-shot Car 44,1%, Bus 0% |
| Grounding DINO + SAM 2 | container-only via box prompt | 20 ft −0,2%; 40 ft ambigu |
| TRUDI/TITUS (BMVC 2025) | 11.109 container, 2.780 trailer | CC BY-SA; MMDetection |
| naver/cctv (ICCV 2021) | kalibrasi dari track box | skala dari prior; sirkular untuk ODOL |
| MoGe-2 (NeurIPS 2025) | metric point map | wildcard; belum diuji |
| RoadTagger (AAAI 2020) | lane count dari satelit | 77%; untuk banyak ruas |
| ISO 668 | standar kontainer | 20/40/45 ft |

---

## 9. Peta berkas

| Berkas | Isi |
|---|---|
| `RISET-CAROM-Air-untuk-CCTV.md` | laporan riset utama |
| `SOP-KALIBRASI-CCTV.md` | SOP kalibrasi (GeoCalib §0.3, degenerasi §5) |
| `SOP-PENGUKURAN-DIMENSI-KENDARAAN.md` | SOP pengukuran L/W/H |
| `KALIBRASI-CCTV-CAWANG-REV2.md` | kalibrasi Cawang yang berlaku |
| `AUDIT-16-15-44.md` | studi kasus rekaman tidak layak |
| `PAPER-REPO-Untuk-Menutup-Kelemahan.md` | peta paper/repo |
| `PLAN-PENUTUPAN-KELEMAHAN.md` | rencana penutupan kelemahan per fase |
| `VALIDASI-PROTOCOL.md` | protokol dan ambang |
| `HASIL-VALIDASI-SVLD.md` | sintesis SVLD |
| `HASIL-TIMEPASS-CAWANG.md` | side-view, 20 ft, 40 ft |
| `CATATAN-RISET-LENGKAP.md` | dokumen ini |
| `reports/` | artefak validasi (lihat `reports/README.md`) |
| `reports/external-setup.md` | environment GeoCalib, YOLO, Grounded SAM 2 |
| `scripts/` | 14 skrip validasi (lihat `scripts/README.md`) |

Skrip penting:

| Skrip | Fungsi |
|---|---|
| `svld_reproj_check.py` | verifikasi kalibrasi SVLD |
| `svld_fit_dims.py` | fit 3D box, 50 objek |
| `svld_sensitivity.py` | sensitivitas noise |
| `svld_subsets.py` | subset sudut |
| `svld_kp_detectability.py` | keypoint zero-shot |
| `svld_mask_fit.py` | mask-based W/H/L |
| `cawang_timepass.py` | side-view/lower envelope |
| `grounded_sam2_container.py` | segmentasi container-only |
| `cawang_container_fit.py` | fit 3D box container-only |

---

## 10. Riwayat commit

| Commit | Isi |
|---|---|
| `a75c4ae` | riset CAROM Air, laporan, kalibrasi, SOP |
| `424dafe` | audit rekaman 16-15-44 |
| `a01e8bc` | kalibrasi ulang tanpa tepi kanan |
| `0e922fb` | uji GeoCalib |
| `65e4bf0` | GeoCalib sebagai alat utama di SOP |
| `e999229` | validasi eksternal SVLD |
| `8c0b344` | side-view Cawang 15,9 m |
| `d63d45f` | lower envelope, batch 6 kendaraan |
| `0bc9537` | container-only +13,3% |
| `b919ba0` | YOLO26-seg whole-truck |
| `f83c12b` | Grounded SAM 2 container-only |
| `1fadfc4` | validasi 20 ft −0,2% |

---

## 11. Rekomendasi berikutnya

**Prioritas 1 — validasi 20 ft berulang.** Uji 3–5 kontainer 20 ft lain dengan box prompt container-only. Jika semuanya 6,0–6,2 m, klaim validasi 20 ft kuat.

**Prioritas 2 — identifikasi 40 vs 45 ft.** Uji kontainer 40 ft yang jelas, atau baca kode ISO 6346 (bukan plat kendaraan). Tanpa tipe, 13,99 m tidak bisa disebut galat.

**Prioritas 3 — I24-3D satu kamera.** Cari kamera yang melihat sisi kendaraan; bandingkan dengan `veh_size`. Ini GT side-view yang sah.

**Prioritas 4 — detektor 5 titik.** Fine-tune `vehicle-keypoints` atau SKoPe3D; target ≤3 px. Butuh GPU.

**Prioritas 5 — time-of-passage murni.** Garis melintang $X_0$; bandingkan $v\Delta t$ dengan side-view.

**Prioritas 6 — field test Indonesia.** Satu kendaraan diukur dengan meteran. Ini tetap penentu akhir.

---

## 12. Catatan penutup

Yang sudah benar-benar kuat:

- Hukum galat dan anisotropi.
- Degenerasi $f$–$h$–$w$.
- Geometri pengukuran (0,36%).
- Lima titik cukup.
- Kalibrasi SVLD.
- Container-only 20 ft (−0,2%).

Yang masih rapuh:

- Panjang dari satu pandangan.
- Detektor 5 titik.
- Kecepatan.
- Generalisasi ke Indonesia.
- 40 vs 45 ft.
- Ambiguitas lajur ATP.

Jangan menambah dokumen baru sebelum salah satu dari lima prioritas di atas dieksekusi.

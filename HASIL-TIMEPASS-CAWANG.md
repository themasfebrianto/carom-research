# Hasil Time-of-Passage / Side-View — Cawang

## Tujuan

Menguji apakah panjang kendaraan bisa diukur dari **satu kamera, pure pixel, tanpa plat**, memakai sisi kendaraan yang terlihat saat melintas.

## Metode

1. Deteksi/segmentasi kendaraan dengan YOLO11n-seg (COCO).
2. Track kendaraan antar frame dengan IoU.
3. Ambil **lower envelope** mask: untuk tiap kolom, titik terbawah mask. Ini aproksimasi kontak tanah yang lebih baik daripada kontur mentah, yang sering berhenti di bumper.
4. Tentukan arah memanjang jalan dari vanishing point ($VP=(651{,}5,\;310{,}0)$); cari dua ujung lower envelope sepanjang arah VP.
5. Back-project kedua titik ke bidang jalan dengan kalibrasi Cawang:
   - $f=1082{,}6$ px, $h=8{,}876$ m, pitch $=2{,}432^\circ$, $c=(640,360)$.
   - $X$ dari baris $v$; $Y=(u-c_x)z/f$; $z=X\cos\theta+h\sin\theta$.
6. Panjang = jarak Euclidean kedua titik ground. Kecepatan = perubahan $X$ titik tengah ground.

Ini bukan time-of-passage murni; ia mengukur panjang dari dua kontak tanah di sisi kendaraan. Secara geometri setara, dan lebih sederhana karena tidak perlu mendeteksi waktu crossing secara eksplisit.

## Hasil

### Truk kontainer SINKOR (40 ft), t=86,0–86,4 s

| t (s) | Panjang (m) | $X_m$ (m) | Area mask |
|---:|---:|---:|---:|
| 86,0 | 14,04 | 31,6 | 57.216 |
| 86,2 | 15,22 | 32,8 | 52.688 |
| 86,4 | 13,71 | 38,4 | 34.440 |

- Median **14,04 m**; mean 14,32 m.
- Kecepatan dari titik tengah ground: **17,0 m/s = 61,2 km/jam**.
- Pembanding: kontainer 40 ft = 12,19 m; kabin + sasis ≈ 2,4 m; total ≈ 14,6 m. Galat ≈ **4%**.
- Kontur mentah (bukan lower envelope) memberi 15,9 m, sekitar 9% terlalu panjang. Lower envelope lebih dekat ke standar.
- Pada 86,6–86,8 s, mask mengecil (<30k px) dan panjang melonjak 19,9/13,9 m; frame ini dibuang.

### Batch 6 kendaraan besar

Semua memakai lower envelope, durasi 0,8 s, 5 fps, `min-area=15.000`.

| t (s) | Lane | Median panjang | Tafsiran standar |
|---:|---|---:|---|
| 32 | far | 11,56 m | 20 ft / box truck |
| 86 | far | 14,63 m | 40 ft container + kabin |
| 247 | near | 6,44 m | box truck kecil |
| 431 | far | 16,74 m | truk panjang / articulated |
| 567 | far | 17,37 m | truk panjang / articulated |
| 578 | near | 14,69 m | 40 ft container |

Kecepatan dari batch: 7–119 km/jam. Angka ini **tidak dipakai** karena baseline 0,8 s terlalu pendek dan mask jitter; panjang jauh lebih stabil daripada kecepatan.

## Interpretasi

1. **Lower envelope adalah perbaikan penting.** Truk 40 ft turun dari 15,9 m (kontur) ke 14,0–14,3 m, mendekati 14,6 m. Titik kontak tanah memang bukan kontur terluar; ia titik terbawah mask.
2. **Panjang masuk akal untuk beberapa kelas.** Cluster 6,4 / 11,6 / 14,6 / 14,7 / 16,7 / 17,4 m konsisten dengan box truck kecil, 20 ft, 40 ft, dan truk panjang.
3. **Kecepatan belum dapat dipercaya.** Baseline pendek dan jitter mask membuat kecepatan liar. Untuk time-of-passage murni, perlu track lebih panjang dan garis crossing eksplisit.
4. **Kelas YOLO tidak reliabel.** Mobil bisa terdeteksi sebagai bus; kelas hanya dipakai untuk filter kasar, bukan untuk keputusan.
5. **Ini proof of concept, bukan validasi.** Tidak ada GT; pembanding hanya standar kontainer. Diperlukan kendaraan yang diukur dengan meteran atau dataset GT.

## Container-only: hasil negatif

Standar kontainer 40 ft = 12,192 m; 20 ft = 6,058 m. Ini GT yang sah untuk **kontainer**, bukan truk total.

Uji container-only pada truk SINKOR:

| Parameter | Fit | Standar 40 ft | Galat |
|---|---:|---:|---:|
| $L$ | 13,81 m | 12,192 m | +13,3% |
| $W$ | 2,69 m | 2,438 m | +10,4% |
| $Z_0$ | 1,58 m | ±1,1 m | mentok batas |
| IoU | 0,816 | — | — |

Penyebab: mask warna parsial, ambiguitas skala $Z_0/L/W$, dan kontainer dilihat miring. Pipeline container-only **belum akurat**. Diperlukan anotasi manual 4 sudut atau segmentasi yang lebih baik (SAM 2), atau GT side-view/I24-3D.

## YOLO26-seg: uji tambahan

YOLO26n-seg mendeteksi truk SINKOR dengan confidence 0,74 dan mask yang lebih halus, tetapi mask-nya tetap **whole-truck** (kabin + kontainer), bukan kontainer saja.

| Model | Median lower-envelope | Catatan |
|---|---:|---|
| YOLO11n-seg | **14,04 m** | lebih dekat ke total 14,6 m |
| YOLO26n-seg | 17,50 m | mask mencakup bayangan/roda; lower envelope memanjang |

Kesimpulan: YOLO26-seg **bukan** solusi container-only. Ia tidak memisahkan kabin dari kontainer, dan untuk whole-truck justru memberi panjang yang lebih jauh. Bottleneck tetap: mask kontainer spesifik + ambiguitas skala.

## Grounded SAM 2: segmentasi container-only

Model yang dicoba: **Grounding DINO tiny + SAM 2.1 tiny** (Hugging Face `transformers`).

- Prompt teks `"shipping container."` mendeteksi box `[79, 439, 365, 714]` (score 0,641), tetapi box itu **mencakup kabin**; mask SAM 2 jadi whole-truck (area 57k px).
- Prompt box yang hanya kontainer `[80, 440, 310, 700]` memberi mask **kontainer saja** (area 46k px, kabin tidak ikut).
- Ini menunjukkan SAM 2 bisa memisahkan kontainer dari kabin **jika box prompt-nya benar**; prompt teks saja belum cukup.

Fit 3D box ke mask kontainer-only dengan $H=2{,}591$ m:

| Parameter | Fit |
|---|---:|
| $L$ | **13,99 m** |
| $W$ | 2,69 m |
| $Z_0$ | 1,43 m |
| yaw | −6,8° |
| IoU | 0,741 |

Perbandingan: 40 ft = 12,192 m (+14,7%); **45 ft = 13,716 m (+2,0%)**. Jenis kontainer tidak diketahui, jadi ini belum bisa disebut galat. Segmentasi sudah benar; yang tersisa adalah **identifikasi tipe kontainer** dan ambiguitas skala.

**Uji mask kedua (GrabCut):** L=**12,45 m** (+2,1% vs 40 ft), W=2,10 m (bias side-view), IoU 0,792. Bersama SAM2 13,99 m, rentang **12,45–13,99 m** mencakup 40 dan 45 ft; tipe belum bisa dipastikan. Jadi 40 ft SINKOR **belum bisa dipakai sebagai anchor kedua**.

## Validasi 20 ft: kontainer TEMA

Frame t=247 s; kontainer merah TEMA di lajur kiri. Box prompt SAM 2 `[255, 475, 405, 645]` memberi mask kontainer-only (21.907 px; bbox 252–418 × 473–635).

Fit 3D box dengan tinggi standar 2,591 m; crop `[230, 450, 430, 680]`:

| Parameter | Fit | Standar 20 ft | Galat |
|---|---:|---:|---:|
| $L$ | **6,046 m** | 6,058 m | **−0,2%** |
| $W$ | 2,437 m | 2,438 m | −0,04% |
| $Z_0$ | 1,772 m | ±1,1 m | — |
| IoU | 0,972 | — | — |

**Ini validasi ground truth pertama yang bersih.** Dengan mask kontainer-only dan tinggi standar, panjang 20 ft tereproduksi dalam 0,2%. Skrip: `scripts/cawang_container_fit.py`.

**Implikasi anchor:** karena kalibrasi Cawang memakai `w=3,6 m`, hasil 20 ft 6,046 m (−0,2%) juga **memvalidasi skala 3,6 m di Cawang**. Secara linear, kontainer memberi `w_est = 3,6 × 6,058/6,046 ≈ 3,607 m` (panjang) dan `3,602 m` (lebar) — median **≈3,60 m**. Ini bukan bukti universal: data SVLD memberi 2,7–3,56 m untuk scene lain. Detail: `reports/cawang-container-anchor/README.md`.

Implikasi:

- Segmentasi container-only + tinggi standar **bekerja** bila mask bersih dan tipe kontainer diketahui.
- Bottleneck bergeser dari segmentasi ke **identifikasi tipe kontainer** (20/40/45 ft) dan kualitas mask.
- 40 ft SINKOR 13,99 m tetap ambigu: 40 ft (+14,7%) atau 45 ft (+2,0%).

## Batas

- Hanya 6 kendaraan dalam batch; belum ada distribusi galat.
- Kamera Cawang melihat sisi kendaraan karena posisinya di tepi jalan; kamera yang tepat di belakang lajur tidak akan memberi sisi.
- Kalibrasi Cawang anchored pada lebar lajur 3,60 m; jalan melengkung; galat sistematis belum diukur.
- Lower envelope bisa mengambil bayangan atau bagian bawah bodi, bukan ban.
- Kecepatan dari 0,8 s tidak stabil.

## Langkah berikutnya

1. **10-20 truk kontainer/bus** dengan standar panjang diketahui (20 ft, 40 ft, bus 12 m); bangun distribusi galat. Identifikasi tipe 40 vs 45 ft dari kode ISO, bukan hanya panjang.
2. **Time-of-passage murni**: definisikan garis melintang pada $X_0$; catat waktu tepi depan/belakang melintas; bandingkan $L=v\,\Delta t$ dengan hasil side-view.
3. **I24-3D satu kamera** (GT) untuk validasi akurasi, setelah akses disetujui. Catatan: SVLD tidak cocok karena semua objek menghadap depan/belakang (sudut 4–29°).
4. **Perbaiki endpoint** dengan deteksi roda/kontak tanah, bukan lower envelope mentah.
5. **Container-only**: perlu anotasi manual 4 sudut atau SAM 2; fit warna saat ini +13,3%.

## Berkas

- `scripts/cawang_timepass.py`
- `scripts/grounded_sam2_container.py`
- `scripts/cawang_container_fit.py`
- `clips/cawang_032_kandidat.mp4`
- `clips/cawang_086_sinkor.mp4`
- `clips/cawang_247_20ft-tema.mp4`
- `clips/cawang_431_truk-panjang.mp4`
- `clips/cawang_567_truk-panjang.mp4`
- `clips/cawang_578_40ft.mp4`
- `out/timepass/lower/timepass_bus.csv`
- `out/timepass/cand2_*/timepass_bus.csv`
- `out/timepass/gsam2_20ft/container_mask_0.npy`
- `out/timepass/container20/container_fit.json`
- `out/timepass/truck86_endpoints.jpg`
- `out/timepass/truck86.jpg`

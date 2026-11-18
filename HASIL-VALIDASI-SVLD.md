# Hasil Validasi SVLD-3D

Ringkasan seluruh uji pada SVLD-3D: kalibrasi, geometri, sensitivitas, subset sudut, keypoint zero-shot, dan mask-based. Dokumen ini menjawab pertanyaan: **sejauh mana adaptasi CAROM Air ke kamera CCTV terbukti?**

## 1. Ringkasan eksekutif

| Komponen | Hasil | Status |
|---|---|---|
| Kalibrasi SVLD | reproyeksi 8.142 objek, median 0,74 px | **terverifikasi** |
| GeoCalib pada 5 scene SVLD | 1/5 lulus f<5% dan pitch<2° | **tidak reliabel** |
| Geometri 50 objek (8 sudut GT) | MAPE 0,36%, RMS 0,35 px | **terverifikasi** |
| Sensitivitas noise 3 px | MAPE 2,79%, 1,7% gagal | **target keypoint ≤3 px** |
| Subset 5 titik | MAPE 0,48% | **cukup** |
| Keypoint zero-shot (20 citra) | 5/5 36,1% semua GT; Car 44,1%, Bus 0% | **belum cukup** |
| Mask-based (21 objek) | W 7,1%, H 7,6%, **L 21,9%** | **W/H layak, L tidak** |

**Putusan:** geometri dan kalibrasi terbukti; persepsi untuk lebar/tinggi mendekati berguna; **panjang belum layak dari satu kamera**. Klaim "CAROM Air bisa diadaptasi" harus dibatasi pada W/H, atau menunggu multi-frame/multi-kamera.

## 2. Kalibrasi

SVLD menyediakan `f`, `fi` (pitch), `theta` (yaw), dan `h` per scene. Verifikasi dilakukan dengan memproyeksikan 8.142 box 3D GT ke citra dan membandingkannya dengan 8 sudut 2D anotasi:

- median RMS **0,74 px**
- persentil 90 **0,85 px**
- maksimum **1,08 px**
- 0 objek >2 px

Kalibrasi SVLD konsisten. Ini menjadi ground truth yang sah untuk geometri dan dimensi.

## 3. GeoCalib

Diuji pada satu citra per scene (5 scene). Hasil:

| Scene | Δf/f | Δpitch | Status |
|---|---:|---:|---|
| 0cam | 51,0% | 3,41° | gagal |
| 1cam | 10,4% | 4,94° | gagal |
| session0_centre | 2,1% | 1,46° | lulus |
| session0_right | 16,2% | 0,81° | gagal (f) |
| session6_right | 28,5% | 4,99° | gagal |

Hanya **1/5** lulus. Kalibrasi XML SVLD benar, jadi ini domain gap GeoCalib pada scene jalan dengan vegetasi dan kamera miring. Gerbang validasi silang SOP §0.3.2 bekerja; jangan memakai GeoCalib tanpa cek per scene.

## 4. Geometri

50 objek (26 Car, 24 Bus), jarak 13,5–122,9 m. Input: 8 sudut 2D GT + kalibrasi XML. Fit 6 parameter (X, Y, yaw, L, W, H).

| Metrik | Mean | Median | p90 | Max |
|---|---:|---:|---:|---:|
| MAPE LWH | **0,36%** | 0,23% | 0,81% | 1,18% |
| L | 0,65% | 0,36% | 1,59% | 3,16% |
| W | 0,15% | 0,12% | 0,33% | 0,44% |
| H | 0,30% | 0,23% | 0,53% | 1,25% |
| RMS | 0,35 px | 0,35 px | 0,41 px | 0,46 px |

Geometri, satuan, dan model kamera benar. Ini uji dengan sudut GT, bukan detektor.

## 5. Sensitivitas dan subset

Noise Gaussian pada 8 sudut 2D:

| σ | MAPE | Gagal |
|---:|---:|---:|
| 0 | 0,36% | 0% |
| 1 px | 1,05% | 0% |
| 2 px | 1,91% | 0% |
| 3 px | 2,79% | 1,7% |
| 5 px | 4,57%* | 63,2% |

\* hanya 37% yang berhasil.

Subset sudut:

| Subset | MAPE | Gagal |
|---|---:|---:|
| 8 sudut | 0,36% | 0 |
| 6 sudut | 0,46% | 0 |
| **5 sudut** | **0,48%** | **0** |
| 4 kontak tanah | 2,39% | 1 |
| 4 sudut atap | 3,04% | 0 |

**Target keypoint: 5 titik (4 kontak tanah + 1 atap), akurasi ≤3 px.** Delapan sudut tidak diperlukan.

## 6. Keypoint zero-shot

Model `vehicle-keypoints` (YOLO26-pose, 14 keypoint, MIT) pada 20 citra (10 Car, 10 Bus), 72 objek GT.

| Kelompok | GT | Cocok | 5/5 di antara cocok | 5/5 dari semua GT |
|---|---:|---:|---:|---:|
| Semua | 72 | 41 (56,9%) | 63,4% | 36,1% |
| Car | 59 | 33 (55,9%) | 78,8% | 44,1% |
| Bus | 13 | 8 (61,5%) | 0% | 0% |

Model ini tidak siap untuk bus. Untuk mobil, sinyalnya ada tetapi match rate rendah. Zero-shot tidak cukup; perlu fine-tuning pada sudut CCTV atau pendekatan lain.

## 7. Mask-based

YOLO11n-seg (COCO) pada 20 citra, 21 objek. Fit 3D box ke mask body dengan differential evolution.

| Kelompok | n | MAPE | L | W | H | Mask IoU |
|---|---:|---:|---:|---:|---:|---:|
| Semua | 21 | 12,19% | 21,92% | 7,11% | 7,55% | 0,796 |
| Car | 12 | 12,86% | 22,20% | 8,07% | 8,32% | 0,780 |
| Bus | 9 | 11,30% | 21,56% | 5,83% | 6,51% | 0,820 |

Lebar dan tinggi layak untuk screening (<10%); panjang tidak. Mask body tidak memuat kontak ban; box yang lebih besar dan lebih jauh bisa memberi siluet yang mirip. Ini konsisten dengan hukum anisotropi proyek: galat longitudinal tumbuh dengan $z^2$, lateral dengan $z$.

## 8. Apa yang terbukti dan tidak

**Terbukti:**

- Kalibrasi SVLD dapat dipercaya (0,74 px).
- Geometri pengukuran benar: dengan 2D sempurna, MAPE 0,36%.
- Lima titik cukup; target akurasi ≤3 px.
- Mask-based memberi W/H ~7%, cukup untuk screening.
- GeoCalib tidak reliabel pada 4/5 scene SVLD; gerbang SOP perlu.

**Belum terbukti:**

- Detektor 5 titik yang mencapai ≤3 px pada kendaraan nyata. Zero-shot gagal pada bus dan hanya 44,1% mobil.
- Panjang dari satu kamera. Mask-based 21,9%; ini batas fundamental, bukan sekadar detector.
- Adaptasi pada CCTV Indonesia. Semua data berasal dari AS/Cina/Eropa.

## 9. Implikasi untuk klaim riset

Klaim yang sah:

> "Kerangka geometri CAROM Air dapat diadaptasi untuk mengukur lebar dan tinggi kendaraan dari CCTV statis, dengan akurasi geometri <1% bila titik 2D tersedia, dan ~7% dengan mask-based. Panjang tidak dapat diandalkan dari satu kamera karena anisotropi."

Klaim yang tidak sah:

> "CAROM Air dapat mengukur L/W/H kendaraan dari CCTV dengan akurasi 10%."

Untuk panjang, diperlukan multi-frame, multi-kamera, atau model bentuk yang lebih kuat. Untuk bus/truk, diperlukan detektor yang dilatih pada kelas tersebut; model mobil tidak cukup.

## 10. Langkah berikutnya

1. **Hybrid** — mask untuk W/H, keypoint kontak tanah untuk L; uji pada 50 objek.
2. **Multi-frame/multi-kamera** — I24-3D (16–17 kamera) untuk membuktikan panjang bisa diselamatkan; tunggu akses.
3. **Fine-tune keypoint** — butuh GPU; `vehicle-keypoints` atau SKoPe3D.
4. **Validasi lapangan Indonesia** — satu kendaraan diukur dengan meteran; tetap diperlukan.

## 11. Berkas

- `out/svld/geocalib_mini.md`
- `out/svld/fit_dims_report.md`
- `out/svld/sensitivity_report.md`
- `out/svld/subsets_report.md`
- `out/keypoint/detectability_report.md`
- `out/keypoint/mask_fit_report.md`
- `scripts/svld_reproj_check.py`, `svld_fit_dims.py`, `svld_sensitivity.py`, `svld_subsets.py`, `svld_kp_detectability.py`, `svld_mask_fit.py`

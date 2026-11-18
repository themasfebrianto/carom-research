# Mask-Based Fitting — 20 Citra SVLD-3D

## Metode

- YOLO11n-seg (COCO) pada 20 citra SVLD; 21 objek GT yang cocok.
- Mask kendaraan (body) dari YOLO, dipotong 25% margin, 256×256.
- Fit 6 parameter: $X,Y$, yaw, $L,W,H$; alas di $Z=0$.
- Objektif: IoU antara siluet box yang diproyeksikan (convex hull 8 sudut) dan mask.
- Optimasi: differential evolution, 15 iterasi, seed 0.
- GT bbox dipakai hanya untuk mencocokkan deteksi, bukan untuk fitting.

## Hasil

| Kelompok | n | MAPE | L | W | H | Mask IoU |
|---|---:|---:|---:|---:|---:|---:|
| Semua | 21 | **12,19%** | 21,92% | 7,11% | 7,55% | 0,796 |
| Car | 12 | 12,86% | 22,20% | 8,07% | 8,32% | 0,780 |
| Bus | 9 | 11,30% | 21,56% | 5,83% | 6,51% | 0,820 |

Contoh terburuk panjang:

| Objek | Jarak | $L$ GT | $L$ fit | Galat |
|---|---:|---:|---:|---:|
| Bus | 86,7 m | 9,46 | 14,61 | +54,5% |
| Car | 82,2 m | 4,63 | 2,66 | −42,6% |
| Bus | 56,4 m | 12,00 | 8,21 | −31,6% |

## Interpretasi

1. **Lebar dan tinggi layak untuk screening.** Galat 6–8%, di bawah 10%.
2. **Panjang tidak layak.** Galat 21,6–22,2%; kasus terburuk >50%. Ini konsisten dengan hukum anisotropi proyek: galat longitudinal tumbuh dengan $z^2$, sedangkan lateral hanya $z$.
3. **Mask IoU tinggi tidak menjamin dimensi benar.** Pada Bus 86,7 m, mask IoU 0,898 tetapi panjang +54%. Box yang lebih besar dan lebih jauh bisa menghasilkan siluet yang mirip — ambiguitas skala-kedalaman.
4. **Mask body tidak memuat kontak ban.** YOLO-seg menandai bodi kendaraan, bukan roda/bayangan. Alas box di tanah, tetapi bukti visual untuk alas itu tidak ada di mask; optimizer bebas menggeser skala.
5. **Bus lebih baik daripada keypoint zero-shot.** Mask-based memberi Bus MAPE 11,3%; keypoint model memberi 0% 5/5. Untuk kendaraan besar, mask lebih tahan.

## Batas

- Hanya 21 objek; belum cukup untuk klaim populasi.
- Tidak ada oklusi/truncation berat.
- GT bbox dipakai untuk mencocokkan deteksi.
- Tidak ada fine-tuning YOLO; model COCO generik.
- Satu citra per kendaraan; belum ada fusi multi-frame.

## Implikasi

- **Untuk ODOL lebar/tinggi**, mask-based sudah mendekati berguna (6–8%). Untuk panjang, belum.
- **Untuk panjang**, perlu kontak ban (keypoint) atau multi-frame; mask body saja tidak cukup.
- Arsitektur yang masuk akal: mask untuk W/H + keypoint ground contact untuk L, atau fusi multi-frame.
- Jika target hanya screening lebar/tinggi, pipeline ini bisa dilanjutkan; jika target panjang/ODOL penuh, perlu komponen tambahan.

## Berkas

- `out/keypoint/mask_fit.csv`
- `out/keypoint/mask_fit_summary.json`
- `out/keypoint/mask_fit/*.jpg`

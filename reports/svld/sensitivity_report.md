# Analisis Sensitivitas — Noise pada 8 Sudut 2D

## Metode

- 50 objek yang sama (26 Car, 24 Bus), 20 pengulangan per level noise.
- Noise Gaussian independen pada setiap koordinat 8 sudut 2D: $\sigma$ = 0; 0,5; 1; 2; 3; 5 px.
- Urutan sudut dikunci dari fit noise-free; fitting dimulai dari solusi noise-free.
- Ini uji **sensitivitas lokal**, bukan benchmark detektor. Kesalahan berkorelasi dan kesalahan urutan sudut adalah mode kegagalan terpisah.

## Hasil

| $\sigma$ (px) | n | Gagal | MAPE mean | MAPE p90 | L mean | W mean | H mean |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 50 | 0 | 0,36% | 0,81% | 0,65% | 0,15% | 0,30% |
| 0,5 | 1.000 | 0 | 0,59% | 1,30% | 1,05% | 0,32% | 0,40% |
| 1 | 1.000 | 0 | 1,05% | 2,38% | 1,89% | 0,60% | 0,66% |
| 2 | 1.000 | 0 | 1,91% | 4,05% | 3,35% | 1,16% | 1,23% |
| 3 | 1.000 | 17 (1,7%) | 2,79% | 6,00% | 4,86% | 1,75% | 1,75% |
| 5 | 1.000 | 632 (63,2%) | 4,57%* | 10,26%* | 7,90%* | 2,98%* | 2,83%* |

\* Hanya objek yang berhasil; angka ini optimistis karena 63% fitting gagal.

## Interpretasi

1. **Target keypoint adalah ≤3 px**, bukan 5 px. Pada 3 px, MAPE 2,79% dan hanya 1,7% fitting gagal. Pada 5 px, 63% fitting gagal — detektor dengan akurasi 5 px tidak cukup andal.
2. **Margin geometri besar.** Bahkan dengan noise 3 px, galat dimensi masih di bawah 3%; target 10% memberi ruang untuk kesalahan detektor yang lebih besar, tetapi stabilitas fitting yang menentukan.
3. **Panjang tetap sumbu terburuk.** Pada 3 px, galat panjang 4,86% (mean); lebar dan tinggi 1,75%.
4. **Fitting mulai dari solusi benar.** Ini optimistis: detektor nyata juga bisa salah urutan sudut, salah inisialisasi, atau kehilangan sudut. Uji keypoint nyata harus mengukur kegagalan itu.

## Implikasi untuk Fase 4

- Target keypoint: **RMS reproyeksi ≤3 px** pada 20–30 m. Target 5 px di dokumen sebelumnya terlalu longgar.
- Jika keypoint detector mencapai 2–3 px, geometri bukan lagi penghambat; total MAPE diperkirakan 2–4%.
- Jika hanya mencapai 5 px, perlu robust fitting (RANSAC/urutan sudut adaptif) atau perbaikan detector sebelum klaim akurasi.
- Uji berikutnya: ganti sudut GT dengan prediksi keypoint nyata pada 50 objek yang sama, lalu bandingkan MAPE-nya dengan tabel ini.

## Batas

- Noise independen per koordinat; error detektor nyata bisa berkorelasi.
- Hanya Car/Bus; Truck tidak terwakili.
- Tidak ada oklusi/truncation.
- Fitting dimulai dari solusi noise-free; kegagalan global tidak sepenuhnya terukur.

# Uji Geometri 50 Kendaraan — SVLD-3D

## Metode

- 50 objek: **26 Car, 24 Bus**.
- Jarak 13,5–122,9 m; stratifikasi dekat/menengah/jauh.
- Input: **8 sudut 2D anotasi** (`vertex2d`) + kalibrasi XML SVLD.
- Fit 6 parameter: pusat $(X,Y)$, yaw, dan $L/W/H$. Alas di $Z=0$, atap di $Z=H$.
- Proyeksi memakai model CenterLoc3D: $R=R_x(\phi+\pi/2)R_z(\theta)$, $P_c=R(P-[0,0,h])$.
- Urutan sudut dicoba 8 varian (4 rotasi × 2 arah); varian dengan residual terkecil dipilih.

**Ini bukan uji detektor.** Sudut 2D berasal dari anotasi, bukan prediksi. Yang diuji adalah jalur kalibrasi → fitting → dimensi. Detektor/keypoint baru diuji di Fase 4.

## Hasil

| Metrik | Mean | Median | p90 | Max |
|---|---:|---:|---:|---:|
| MAPE $L/W/H$ | **0,36%** | 0,23% | 0,81% | 1,18% |
| Galat $L$ | 0,65% | 0,36% | 1,59% | 3,16% |
| Galat $W$ | 0,15% | 0,12% | 0,33% | 0,44% |
| Galat $H$ | 0,30% | 0,23% | 0,53% | 1,25% |
| RMS reproyeksi | 0,35 px | 0,35 px | 0,41 px | 0,46 px |

Per kelas:

| Kelas | n | MAPE mean | Median | Max |
|---|---:|---:|---:|---:|
| Car | 26 | 0,42% | 0,25% | 1,18% |
| Bus | 24 | 0,30% | 0,22% | 1,09% |

## Interpretasi

1. **Geometri, satuan, dan model kamera benar.** Galat <1,2% jauh di bawah target 10%.
2. **Bottleneck bukan kalibrasi.** Jika input 2D sempurna, dimensi hampir sempurna. Sisa galat berasal dari noise anotasi ±0,7 px dan fitting.
3. **Bottleneck berikutnya adalah persepsi.** Agar total <10%, keypoint/detektor harus menyumbang <±9%. Ini target Fase 4.
4. **Panjang tetap sumbu terburuk** (max 3,16%), konsisten dengan hipotesis proyek. Tetapi bahkan 3,16% masih jauh di bawah ambang.

## Batas

- Hanya Car dan Bus. Truck hanya 1 objek di test set.
- Tidak ada oklusi/truncation; kendaraan terlihat utuh.
- Sudut 2D adalah ground truth, bukan hasil detektor.
- Hanya 1 objek di atas 120 m; ekstrapolasi ke jarak jauh harus hati-hati.
- Hasil ini tidak membuktikan akurasi pada CCTV Indonesia; ini membuktikan geometri pipeline pada data SVLD.

## Langkah berikutnya

Ganti sudut 2D GT dengan prediksi keypoint (OpenPifPaf atau model SKoPe3D), lalu ulangi 50 objek yang sama. Selisih MAPE antara kedua runs adalah **anggaran galat persepsi**. Itu angka yang menentukan apakah klaim adaptasi layak.

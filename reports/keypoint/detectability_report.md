# Uji Detectability Keypoint — 20 Citra SVLD-3D

## Metode

- 20 citra: 10 Car, 10 Bus; 72 objek GT.
- Model: `kiselyovd/vehicle-keypoints` (YOLO26-pose, 14 keypoint, MIT), checkpoint `weights.pt`.
- Inferensi: `conf=0.01`, `imgsz=1920`, CPU.
- Target: 4 roda (keypoint 0–3) + 1 sudut atap (terbaik dari 9–12).
- Keypoint dihitung ada jika confidence ≥0,3 dan berada di dalam citra.
- GT dicocokkan ke deteksi dengan IoU tertinggi; ambang IoU 0,3.

## Hasil

| Kelompok | GT | Cocok | Match rate | 5/5 di antara cocok | 5/5 di antara semua GT | Roda (rata-rata) | Atap |
|---|---:|---:|---:|---:|---:|---:|---:|
| Semua | 72 | 41 | 56,9% | 63,4% | **36,1%** | 3,27/4 | 97,6% |
| Car | 59 | 33 | 55,9% | **78,8%** | **44,1%** | 3,61/4 | 100% |
| Bus | 13 | 8 | 61,5% | **0%** | **0%** | 1,88/4 | 87,5% |

Per jarak:

| Bin | GT | Cocok | Match rate | 5/5 di antara cocok |
|---|---:|---:|---:|---:|
| Dekat (<35 m) | 16 | 6 | 37,5% | 50,0% |
| Menengah (35–65 m) | 29 | 13 | 44,8% | 61,5% |
| Jauh (65–200 m) | 27 | 22 | 81,5% | 68,2% |

## Interpretasi

1. **Model ini tidak siap untuk bus.** Tidak ada satu pun bus yang mencapai 5/5; rata-rata hanya 1,88 dari 4 roda. Overlay menunjukkan bus tidak terdeteksi sama sekali pada citra penuh.
2. **Untuk mobil, sinyalnya ada tetapi belum cukup.** Di antara mobil yang cocok, 78,8% mencapai 5/5. Tetapi hanya 55,9% mobil GT yang cocok, sehingga 5/5 di antara semua mobil GT hanya **44,1%**.
3. **Match rate rendah.** Banyak kendaraan tidak terdeteksi atau IoU <0,3. Model dilatih pada CarFusion (close-up), bukan citra jalan lebar.
4. **Crop tidak menyelamatkan.** Dua crop yang diuji (satu mobil, satu bus) menghasilkan nol deteksi. Domain gap-nya bukan sekadar skala.
5. **Jarak jauh lebih baik dari dekat** (81,5% vs 37,5%). Kemungkinan kendaraan dekat terpotong tepi atau ukurannya di luar distribusi model. Ini perlu dicatat, bukan disimpulkan.

## Batas

- Hanya 20 citra; hasil bisa berubah pada sampel lain.
- Keypoint model bersifat semantik (pusat roda, sudut atap), bukan 8 sudut box GT. Kesesuaian geometri belum diukur.
- Ambang keypoint 0,3 dan IoU 0,3 adalah pilihan; ambang lain bisa mengubah angka.
- Tidak ada fine-tuning; ini murni zero-shot.

## Implikasi

- **Zero-shot keypoint tidak cukup** untuk klaim adaptasi. Model perlu dilatih/di-fine-tune pada sudut CCTV, atau diganti pendekatan mask-based.
- Untuk mobil, target 5 titik masih mungkin: 78,8% di antara deteksi yang cocok. Untuk bus/truk, model ini tidak berguna.
- SKoPe3D menyediakan data sudut CCTV, tetapi **tidak ada bobot pretrained** di halaman proyek. Melatih Keypoint R-CNN di CPU akan lambat.
- Jalur yang lebih realistis tanpa GPU: deteksi/segmentasi 2D (YOLO-seg) + fitting box dari mask dan bidang jalan, bukan keypoint.

## Berkas

- `out/keypoint/detectability.csv`
- `out/keypoint/detectability_summary.json`
- `out/keypoint/overlays/*.jpg`
- `out/keypoint/hf/weights.pt`

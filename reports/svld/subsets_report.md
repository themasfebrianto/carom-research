# Subset Sudut — Berapa Keypoint yang Dibutuhkan?

## Metode

- 50 objek yang sama (26 Car, 24 Bus).
- Subset: 8, 6, 5, dan 4 sudut.
- Dimensi diinisialisasi dari prior kelas (Car 4,5/1,8/1,5 m; Bus 11,0/2,7/2,9 m), bukan dari GT.
- $X/Y$/yaw diambil dari fit noise-free; ini uji kandungan informasi, bukan detektor.
- Gagal jika RMS >5 px atau parameter menyentuh batas.

## Hasil

| Subset | Sudut | Gagal | MAPE | L | W | H |
|---|---:|---:|---:|---:|---:|---:|
| all8 | 8 | 0 | 0,36% | 0,65% | 0,15% | 0,30% |
| bottom4_top2 | 6 | 0 | 0,46% | 0,81% | 0,18% | 0,38% |
| **bottom4_top1** | **5** | **0** | **0,48%** | **0,81%** | **0,20%** | **0,42%** |
| bottom4 | 4 | 1 | 2,39% | 2,03% | 1,11% | 4,02% |
| top4 | 4 | 0 | 3,04% | 2,15% | 1,96% | 5,00% |
| bottom2_top2 | 4 | 0 | 4,27% | 12,14% | 0,29% | 0,38% |

## Interpretasi

1. **Lima sudut sudah cukup.** Empat kontak tanah + satu sudut atap memberi MAPE 0,48% dan nol kegagalan. Hampir sama dengan delapan sudut (0,36%).
2. **Empat kontak tanah menentukan panjang dan lebar.** Tanpa mereka, `bottom2_top2` memberi galat panjang 12,14%.
3. **Tinggi butuh satu sudut atap.** `bottom4` saja memberi galat tinggi 4,02%; satu sudut atap menurunkannya ke 0,42%.
4. **Target detektor menjadi lebih realistis.** Detektor tidak perlu menemukan 8 sudut box; cukup 4 titik kontak ban + 1 sudut atap. Ini lebih dekat dengan keypoint yang biasa dideteksi (roda, lampu, atap).
5. **Empat sudut atap saja** masih memberi MAPE 3,04%, tetapi tinggi 5,00%; tidak cukup untuk ODOL.

## Implikasi

- Rancang keypoint detector untuk **4 ground contacts + 1 roof corner** (5 titik), bukan 8 box corners.
- Jika salah satu kontak tanah teroklusi, gunakan sudut atap tambahan atau model bentuk.
- Target akurasi tetap **≤3 px** per titik (dari analisis sensitivitas).
- Uji berikutnya: detektor nyata pada 50 objek yang sama, dengan 5 titik ini.

## Batas

- $X/Y$/yaw dari fit noise-free; detektor nyata tidak tahu posisi awal.
- Tidak ada oklusi/truncation.
- Hanya Car/Bus.
- Hasil ini mengukur informasi geometri, bukan kemampuan detektor.

# Uji Combo di Video Tes LearnPinhole

**Tanggal:** 19 November 2026  
**Tujuan:** menerapkan combo **GeoCalib + AnyCalib + VP dari garis + anchor lebar jalan** pada video tes LearnPinhole, lalu membandingkannya dengan baseline auto-calib LearnPinhole.

---

## 1. Data

| Item | Nilai |
|---|---|
| Video | `frontend/public/videos/clip-test-pengukuran.mp4` |
| Resolusi | 480×360 |
| fps / durasi | 30 fps / 15 s (300 frame) |
| Frame yang dipakai | 8 frame: t = 0, 2, 4, 6, 8, 10, 12, 14 s |
| Baseline LearnPinhole | `f≈502 px`, HFOV 51,1°, pitch 4,86°, yaw −1,75°, `h≈6,26 m` |
| Anchor baseline | lebar Toyota Avanza (1,730 m), bukan lebar lajur |

Baseline berasal dari `auto_calib.py`: GeoCalib shared-intrinsics untuk `f`, VP lajur untuk pitch/yaw, lalu tinggi dari lebar kendaraan acuan.

---

## 2. Hasil

| Metode | f (px) | HFOV | pitch | yaw | h | Catatan |
|---|---:|---:|---:|---:|---:|---|
| **LearnPinhole baseline** | 502,0 | 51,1° | 4,86° | −1,75° | 6,26 m | GeoCalib f + Avanza |
| **GeoCalib multi (8 frame)** | **501,80** | **51,12°** | 3,08°* | — | — | `f` cocok; pitch gravity, bukan pitch jalan |
| GeoCalib single frame 00 | 500,28 | 51,26° | 3,19°* | — | — | uncertainty 129 px |
| GeoCalib single frame 06 | 511,77 | 50,25° | 2,72°* | — | — | uncertainty 133 px |
| GeoCalib single frame 12 | 521,05 | 49,46° | 2,86°* | — | — | uncertainty 137 px |
| **AnyCalib simple (8 frame)** | **528,22** | — | — | — | — | range 510,10–597,90; **+5,2%** |
| **VP lajur (8 frame)** | 501,80 | 51,12° | **4,913°** | **−1,659°** | — | 30 inlier, RMS 1,87 px |

\* Pitch GeoCalib adalah arah gravitasi, bukan arah jalan. Baseline LearnPinhole memakai pitch dari VP, bukan pitch GeoCalib.

**Bacaan:**

- `f` GeoCalib multi **501,80** hampir identik dengan baseline **502**.
- VP lajur memberi pitch **4,913°** dan yaw **−1,659°**, dekat dengan baseline **4,86° / −1,75°**.
- AnyCalib median **528,22** (+5,2%), tetapi rentang antar frame **510–598** — tidak stabil untuk frame tunggal.
- GeoCalib single f **500–521**; multi-frame lebih stabil.
- GeoCalib pitch **2,7–3,2°** berbeda ~1,8° dari VP jalan; ini konsisten dengan temuan Cawang: gravity ≠ arah jalan.

---

## 3. Anchor lebar jalan: sensitivitas

Dengan `f=501,80`, pitch `4,913°`, yaw `−1,659°`, roll `0`, `cx=240`, `cy=180`, pada baris `y=340`:

| Gap piksel | h, jika `w=3,50 m` |
|---:|---:|
| 100 | 7,09 m |
| 110 | 6,44 m |
| 113,2 | **6,27 m** |
| 120 | 5,90 m |
| 130 | 5,45 m |

Untuk mencapai baseline `h=6,26 m`, gap yang dibutuhkan:

| Lebar lajur `w` | Gap piksel di `y=340` |
|---:|---:|
| 3,50 m | 113,2 px |
| 3,60 m | 116,4 px |
| 3,75 m | 121,3 px |

**Artinya:** h sangat sensitif terhadap gap dan lebar lajur. Perubahan gap 10 px mengubah h sekitar 0,5 m (±8%). Untuk h ±1%, tepi lajur harus akurat sekitar ±1–2 px **dan** `w` harus diukur, bukan diasumsikan.

Pada klip ini, batas kanan lajur mobil merah tidak konsisten terlihat: jalan bercabang/melengkung, garis kanan keluar frame di bagian bawah, dan pasangan garis dekat vs jauh memberi h yang berbeda. Karena itu **anchor lebar jalan tidak stabil di klip ini**.

---

## 4. Putusan

| Pertanyaan | Jawaban |
|---|---|
| GeoCalib + VP cukup untuk `f`/pose? | **Ya**, pada klip ini: f 501,8 vs 502; pitch/yaw VP 4,91/−1,66 vs 4,86/−1,75 |
| AnyCalib menambah akurasi? | **Tidak signifikan**: median +5,2%, range 510–598; hanya layak sebagai cek per frame |
| Anchor lebar jalan cukup? | **Belum**, karena jalan melengkung/bercabang dan batas kanan tidak utuh; h 5,4–7,1 m untuk gap 100–130 px, dan 5,9–6,3 m hanya jika gap 113–121 px |
| Baseline LearnPinhole salah? | **Tidak**; memakai Avanza sebagai anchor justru lebih stabil untuk klip ini |
| Combo bisa dipakai? | **Bisa untuk screening**, jika lane lurus, kedua tepi terlihat, dan `w` diukur; bukan untuk ODOL |

**Kesimpulan:** pada video tes LearnPinhole, **GeoCalib + VP sudah cukup untuk `f` dan pose**, tetapi **anchor lebar jalan bukan pengganti yang baik** untuk anchor kendaraan acuan. Ini justru memvalidasi keputusan LearnPinhole memakai lebar Avanza untuk `h`.

---

## 5. Artefak dan reproduksi

- `summary.csv` — tabel hasil.
- `lane_vp.json` — VP per frame + segmen.
- `geocalib_multi.json` — GeoCalib shared 8 frame.
- `geocalib_frame_00.json`, `geocalib_frame_06.json`, `geocalib_frame_12.json` — GeoCalib single.
- `anycalib_simple.json` — AnyCalib 8 frame.

Skrip di `scripts/calib_compare/`:

```powershell
$py = "C:\Users\omega\AppData\Local\Temp\opencode\carom-calib\env\Scripts\python.exe"
$out = "out\learnpinhole-video"

# frame sudah diekstrak ke $out\frames
& $py scripts\calib_compare\run_lane_vp.py $out\frames --out $out\lane_vp.json
& $py scripts\calib_compare\run_geocalib_multi.py $out\frames --out $out\geocalib_multi.json
& $py scripts\calib_compare\run_anycalib_batch.py $out\frames --model-id anycalib_pinhole --cam-id simple_pinhole --out $out\anycalib_simple.json
```

**Batas:** hanya 8 frame dari satu klip; tidak ada ground truth `h`/`w` di lokasi; lane width tidak diukur dengan meteran; model GeoCalib/AnyCalib general-purpose, bukan khusus CCTV Indonesia.

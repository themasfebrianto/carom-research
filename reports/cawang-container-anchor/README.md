# Cawang: Anchor dari Container Standar

**Tanggal:** 20 November 2026  
**Tujuan:** menguji skala Cawang tanpa akses lapangan, memakai kontainer ISO sebagai benda fisik standar.

---

## 1. Ringkasan

1. **Kontainer 20 ft TEMA memvalidasi skala Cawang**: panjang **6,046 m** vs standar **6,058 m** (**−0,2%**), lebar **2,437 m** vs **2,438 m** (**−0,04%**), IoU 0,972.
2. Karena kalibrasi Cawang memakai anchor `w=3,6 m`, hasil ini menunjukkan **3,6 m konsisten di Cawang** dalam ~0,2%. Ini bukan bukti bahwa semua jalan 3,6 m.
3. **Kontainer 40 ft SINKOR masih ambigu**: SAM2 memberi 13,99 m (+14,7% vs 40 ft, +2,0% vs 45 ft); GrabCut memberi 12,45 m (+2,1% vs 40 ft). Jenis 40 vs 45 ft belum diketahui, jadi **belum bisa dipakai sebagai anchor kedua**.
4. Lebar 40 ft dari side-view tidak reliabel (GrabCut W=2,10 m, bias −13,9%); panjangnya yang masuk akal. Lebar 20 ft justru sangat baik.
5. **Kesimpulan:** tanpa akses lapangan, kontainer 20 ft adalah physical anchor terbaik yang tersedia. Untuk lokasi lain, lebar lajur tetap harus diukur; data SVLD menunjukkan 2,7–3,56 m, bukan 3,6 m universal.

---

## 2. Metode

- Tinggi kontainer dipaku ke standar **2,591 m** (bukan high cube 2,896 m).
- Fit 3D box ke mask container-only; parameter bebas `X, Y, Z0, yaw, L, W`; objektif IoU siluet.
- 20 ft: mask SAM 2 container-only yang sudah terverifikasi; crop `[230, 450, 430, 680]`.
- 40 ft: dua mask berbeda untuk menunjukkan sensitivitas:
  - SAM2 container-only (hasil lama): L=13,99 m, W=2,69 m, IoU=0,741.
  - GrabCut side mask (baru): L=12,45 m, W=2,10 m, IoU=0,792.
- Standar: 20 ft = 6,058 × 2,438 m; 40 ft = 12,192 × 2,438 m.
- Tidak ada pengukuran lapangan; ini **consistency check** terhadap standar, bukan GT per kendaraan.

---

## 3. Hasil

| Objek | Mask | L fit | L standar | Galat L | W fit | W standar | Galat W | IoU |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 20 ft TEMA | SAM2 container-only | **6,046 m** | 6,058 m | **−0,2%** | **2,437 m** | 2,438 m | **−0,04%** | 0,972 |
| 40 ft SINKOR | SAM2 container-only | 13,99 m | 12,192 m | +14,7%* | 2,69 m | 2,438 m | +10,3% | 0,741 |
| 40 ft SINKOR | GrabCut side mask | 12,45 m | 12,192 m | **+2,1%** | 2,10 m | 2,438 m | −13,9% | 0,792 |

\* Jika kontainer sebenarnya **45 ft** (13,716 m), SAM2 hanya +2,0%. Jenis kontainer tidak diketahui, jadi angka ini belum bisa disebut galat.

**Yang gagal:** mask warna merah untuk frame `c20b_246.5/247.5` memberi L 9–10 m; GrabCut untuk frame yang sama menghasilkan mask terlalu kecil. Segmentasi warna tidak cukup untuk frame bergerak; angka tersebut tidak dipakai.

---

## 4. Interpretasi

### 4.1 Cawang 3,6 m konsisten

Kalibrasi Cawang (dash fit) memakai `w=3,6 m` untuk menetapkan skala. Kontainer 20 ft **tidak dipakai** dalam fit itu. Karena hasilnya 6,046 m (−0,2%) dan lebarnya 2,437 m (−0,04%), skala Cawang konsisten dengan benda standar pada level **~0,2–2%**.

Artinya:

- untuk **Cawang**, `w=3,6 m` bukan asumsi buta; ada bukti fisik yang mendukungnya;
- ini **bukan** bukti universal: SVLD memberi 2,7–3,56 m untuk scene lain;
- untuk lokasi baru, ukur lebar lajur atau gunakan kontainer 20 ft yang tipenya diketahui.

### 4.2 40 ft belum bisa jadi anchor

Dua mask yang sama-sama masuk akal memberi 12,45 m dan 13,99 m. Selisih 1,5 m itu persis rentang 40 ft vs 45 ft. Tanpa kode ISO/tipe kontainer, hasil ini **tidak bisa** dipakai untuk memilih 40 atau 45 ft. Yang bisa dikatakan: panjang 12,45–13,99 m konsisten dengan kontainer 40–45 ft, bukan dengan 20 ft.

### 4.3 Lebar side-view

Lebar 40 ft dari mask sisi memberi 2,10 m (−13,9%). Ini bias segmentasi/oklusi, bukan bukti kontainer lebih sempit. Untuk lebar, gunakan 20 ft atau pandangan yang lebih frontal; jangan memakai W dari side mask 40 ft.

### 4.4 Lebar lajur yang diimplikasikan kontainer

Kalau skala berubah linear terhadap anchor `w`, kontainer 20 ft memberi estimasi:

```
w_est (panjang) = 3,6 × 6,058 / 6,046 = 3,607 m
w_est (lebar)   = 3,6 × 2,438 / 2,437 = 3,602 m
median          ≈ 3,60 m
```

Sensitivitas panjang 20 ft jika `w` diubah (±0,2 m):

| `w` diasumsikan | L kontainer terskala | Galat vs 6,058 m |
|---:|---:|---:|
| 3,00 m | 5,038 m | −16,8% |
| 3,30 m | 5,541 m | −8,5% |
| **3,60 m** | **6,046 m** | **−0,2%** |
| 3,75 m | 6,298 m | +4,0% |

Jadi kontainer 20 ft **memilih 3,6 m** dan menolak 3,0–3,3 m untuk Cawang. Ini bukti lokal yang kuat, bukan asumsi buta. Untuk lokasi lain, kontainer/lajur harus diukur ulang.

---

## 5. Implikasi untuk anchor

1. **Gunakan kontainer 20 ft dengan tipe diketahui** sebagai anchor fisik. Hasil Cawang 0,2% adalah bukti terbaik yang ada tanpa lapangan.
2. **Jangan pakai 40 ft SINKOR** sampai tipe (40/45 ft) dipastikan dari kode ISO atau bentuk kontainer.
3. **Untuk lokasi lain**, ukur lebar lajur atau cari kontainer 20 ft. Data SVLD 2,7–3,56 m menunjukkan 3,6 m tidak universal.
4. **Error anchor 1:1**: jika anchor salah 5%, panjang/lebar/tinggi salah 5%. Laporkan anchor dan ketidakpastiannya.
5. **Container lebih kuat daripada lane width** karena dimensinya standar, bukan asumsi kelas jalan.

---

## 6. Reproduksi

```powershell
# 20 ft: hasil terverifikasi (SAM2 mask)
Get-Content out\timepass\container20\container_fit.json

# 40 ft: GrabCut side mask + fit
py scripts\cawang_container_anchor.py --out out\timepass\anchor
```

Artefak:

- `reports/cawang-container-anchor/container_anchor.csv` — ringkasan 2 objek.
- `reports/cawang-container-anchor/20ft_tema_fit.json` — fit 20 ft terverifikasi.
- `reports/cawang-container-anchor/40ft_sinkor_grabcut_fit.json` — fit 40 ft GrabCut.
- `out/timepass/container20/container_fit.json` — 20 ft asli.
- `out/timepass/anchor/container_anchor.csv` — hasil script.
- `out/timepass/anchor/truck86/container_fit.json` — 40 ft GrabCut.
- `out/timepass/anchor/masks/truck86_mask.npy` — mask GrabCut.

---

## 7. Batas

- Hanya **satu** kontainer 20 ft dengan tipe pasti; target 3–5 belum tercapai.
- 40 ft SINKOR tipenya tidak diketahui; 40 vs 45 ft belum terpisah.
- Tinggi kontainer dipaku 2,591 m; high cube 2,896 m akan mengubah L/W.
- Mask 20 ft berasal dari SAM2; mask 40 ft dari GrabCut. Kualitas mask memengaruhi hasil.
- Tidak ada pengukuran lapangan; ini consistency check terhadap standar, bukan GT per kendaraan.
- Warna/iluminasi frame lain membuat segmentasi otomatis gagal; hasilnya tidak dipakai.

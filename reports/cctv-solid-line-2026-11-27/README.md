# Dash + Garis Solid: Memutus Degenerasi `f` pada CCTV dengan Satu Garis Putus-Putus

**Tanggal:** 27 November 2026  
**Tujuan:** menguji apakah garis solid (tepi lajur atau median) dapat menjadi batas kedua sehingga `f` menjadi identifiabel pada CCTV yang hanya memiliki satu garis putus-putus.  
**Situs uji:** BELMERA KM 25+200 (lurus, satu dash + satu garis kuning median) dan BORR KM 03+400 (melengkung, sebagai kontrol negatif).

---

## 1. Ringkasan

1. **Dengan satu garis putus-putus, `f` tidak identifiabel.** BELMERA: free fit `f=1101,09`, RMS `0,320 px`; memaku `f=989,11` memberi RMS `0,320 px` juga. Pola dash hanya menentukan rasio panjang/period, bukan skala absolut.
2. **Garis solid satu lebar lajur dari garis dash memutus degenerasi.** BELMERA: `f=811,55`, pitch `15,551°`, yaw `−0,106°`, `h=10,438 m`, RMS `0,439 px`. Memaku `f=989,11` menaikkan RMS ke `1,674 px`; memaku `f=1101,09` menaikkan ke `2,469 px`.
3. **Scan `f` punya minimum jelas di ~810** (RMS `0,439 px`). Sigma statistik dari Jacobian `8,76 px` (`1,08%`), tetapi angka ini **menyesatkan**: ketidakpastian anchor lebar lajur dan standar dash jauh lebih besar.
4. **Lebar lajur adalah error sistematis dominan.** `w=3,0 → f=985,3`; `3,3 → 890,8`; `3,6 → 811,6`; `3,9 → 744,1`. Perubahan ±0,3 m menggeser `f` sekitar 8–10%.
5. **Standar dash juga sistematis.** Period 13,333 m/dash 5 m memberi `f=826,3` (RMS `0,488`); period 8 m/dash 3 m memberi `f=462,2` (RMS `0,488`). Keduanya punya rasio dash:period 0,375, jadi citra saja tidak bisa membedakan; konteks situs (tol = 5 m) yang memutuskan.
6. **Garis solid di frame ini lurus.** Near-only (v≥500) memberi `f=809,3`; far-only (v<500) memberi `f=819,0` — beda `1,2%`. Sisi yang salah (`offset +1`) memberi RMS `42,9`, ditolak.
7. **BORR tidak valid untuk model garis lurus.** Garis solid memang memutus degenerasi secara prinsip (`f=987,16`; fixed `f=1663,67` RMS `3,500` vs `1,436`), tetapi `u` dash naik dari 324 ke 494 terhadap jarak — jalan melengkung. Model garis lurus tidak berlaku.
8. **Kesimpulan:** metode ini menjanjikan untuk situs seperti BELMERA (lurus, satu dash + satu solid, lebar lajur terlihat), tetapi **bukan solusi universal**. `f` hanya identifiabel **bersyarat** pada lebar lajur dan standar dash yang dipilih. Lebar lajur harus diukur per lokasi; distorsi radial perlu ditambahkan sebelum klaim <2%.

---

## 2. Model

`scripts/calib_compare/fit_dash_line.mjs` memakai model kamera lubang jarum:

- Parameter: `f`, pitch `θ`, yaw `ψ`, tinggi `h`, posisi longitudinal `Xp`, posisi lateral `Y0`.
- Garis dash berada di `Y = Y0`; dash ke-`r` berada di `X = Xp + r·PERIOD`, dengan panjang `DASH`.
- Residual per dash: `v` ujung jauh, `v` ujung dekat, dan `u` tengah dash.
- Garis solid berada di `Y = Y0 + s·LANE_W` (`s = −1` berarti satu lajur di kanan garis dash). Garis solid diproyeksikan sebagai garis tak hingga dari dua titik `X=10 m` dan `X=100 m`; residual setiap titik solid adalah jarak tegak lurus ke garis proyeksi itu.

Identifiabilitas diuji dengan:

1. **Fixed-f RMS**: paku `f`, optimasi 5 parameter lain, bandingkan RMS. Jika RMS tidak berubah, `f` tidak identifiabel.
2. **Scan-f**: ulangi untuk beberapa `f`, cari kurva RMS(`f`).
3. **Kovarians Jacobian**: `σ² (JᵀJ)⁻¹`, hanya mencerminkan noise piksel, bukan ketidakpastian anchor.

Deteksi garis solid memakai `scripts/calib_compare/detect_solid_line.py`:

- Threshold warna (kuning/putih), komponen terhubung dengan rentang vertikal terbesar di ROI.
- Robust line fit `u = a·v + b`, lalu median `u` per bin `v`.
- Output JSON `[{u, v}, ...]`, langsung dipakai sebagai `--solid`.

Contoh:

```powershell
$py = "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe"

& $py scripts\calib_compare\detect_solid_line.py `
  videos\frames\belmera_tm30_001.png `
  --color yellow --roi 450,250,640,720 --vmin 300 --vmax 715 `
  --out videos\frames\belmera_solid_yellow.json

node scripts\calib_compare\fit_dash_line.mjs `
  --frame belmera_solid `
  --dashes videos\frames\belmera_sel.json `
  --width 1280 --height 720 `
  --period 13 --dash-length 5 --lane-width 3.6 `
  --solid videos\frames\belmera_solid_yellow.json --solid-offset -1 `
  --out videos\frames\belmera_solid_fit `
  --scan-f 700:950:10
```

---

## 3. Hasil BELMERA

### 3.1 Dash-only vs dash + solid

| Model | `f` | Pitch | Yaw | `h` | RMS | Fixed `f=989,11` | Fixed `f=1101,09` |
|---|---:|---:|---:|---:|---:|---:|---:|
| Dash only | 1101,09 | 11,803° | 0,122° | 8,220 m | 0,320 px | **0,320 px** | — |
| Dash + solid | 811,55 | 15,551° | −0,106° | 10,438 m | 0,439 px | **1,674 px** | **2,469 px** |

Dash-only tetap memberi RMS yang sama saat `f` dipaku ke 989,11 — degenerasi persis. Dengan garis solid, RMS naik tajam saat `f` dijauhkan dari optimum. Ini bukti kuantitatif bahwa garis solid menambah informasi lateral yang hilang.

### 3.2 Scan `f`

| `f` | RMS (px) |
|---:|---:|
| 700 | 1,362 |
| 750 | 0,809 |
| 800 | 0,455 |
| **810** | **0,439** |
| 820 | 0,447 |
| 850 | 0,587 |
| 900 | 0,967 |
| 950 | 1,370 |

Minimum di sekitar 810. Kurva naik mulus di kedua sisi, bukan flat seperti dash-only.

### 3.3 Sensitivitas lebar lajur

| `w` (m) | `f` | Pitch | `h` | RMS |
|---:|---:|---:|---:|---:|
| 3,0 | 985,32 | 12,909° | 8,800 m | 0,439 px |
| 3,3 | 890,79 | 14,226° | 9,627 m | 0,439 px |
| 3,6 | 811,55 | 15,551° | 10,438 m | 0,439 px |
| 3,9 | 744,07 | 16,884° | 11,231 m | 0,439 px |

RMS identik karena `w` adalah input, bukan observasi. `f` bergerak hampir linear terhadap `w`. Ini menunjukkan bahwa **angka `f` tidak lebih baik dari angka `w` yang dipakai**.

### 3.4 Sensitivitas standar dash

| Period / dash | `f` | Pitch | `h` | RMS | Catatan |
|---|---:|---:|---:|---:|---|
| 13,0 / 5 m | 811,55 | 15,551° | 10,438 m | 0,439 px | dipakai di fitting Cawang/BELMERA |
| 13,333 / 5 m | 826,34 | 15,193° | 10,409 m | 0,488 px | 5 m + gap 8,33 m (rasio 3:5) |
| 8,0 / 3 m | 462,16 | 25,899° | 9,703 m | 0,488 px | 3 m + gap 5 m (rasio 3:5) |

Dua varian terakhir punya rasio dash:period yang sama (0,375), sehingga bentuk pola di citra hampir identik. Yang membedakan hanyalah skala absolutnya; garis solid + lebar lajur **tidak** cukup untuk memilih 3 m vs 5 m, karena skala longitudinal tetap berasal dari standar. Konteks tol (kecepatan tinggi) memilih 5 m/13,33 m; jika situsnya jalan kota, 3 m/8 m lebih masuk akal.

### 3.5 Uji stabilitas

| Kasus | `f` | Pitch | Yaw | `h` | RMS | Interpretasi |
|---|---:|---:|---:|---:|---:|---|
| Semua 20 titik solid | 811,55 | 15,551° | −0,106° | 10,438 m | 0,439 px | baseline |
| 10 titik dekat (v≥500) | 809,30 | 15,565° | −0,132° | 10,431 m | 0,445 px | konsisten |
| 10 titik jauh (v<500) | 819,01 | 15,570° | 0,043° | 10,542 m | 0,299 px | konsisten |
| Offset sisi salah (+1) | 365,76 | −4,499° | −10,509° | 20,615 m | **42,921 px** | ditolak |

Near vs far berbeda `1,2%`; garis solid di frame ini praktis lurus dan distorsi radial tidak dominan. Sisi yang salah langsung memberi RMS puluhan piksel, jadi assignment sisi tidak ambigu.

### 3.6 Garis putih tepi kiri (kontrol negatif)

Garis putih tepi kiri BELMERA dideteksi dan dicoba sebagai batas kedua dengan `--solid-offset 2` (dua lajur di kiri garis dash):

| Input | `f` | Pitch | `h` | RMS |
|---|---:|---:|---:|---:|
| Garis kuning median, offset −1 | 811,55 | 15,551° | 10,438 m | 0,439 px |
| Garis putih tepi kiri, offset +2 | 412,94 | 32,993° | 20,960 m | 1,678 px |

Hasil garis putih tidak konsisten dan tidak fisik (pitch 33°, `h=21 m`). Kemungkinan penyebab: jumlah lajur ke garis putih bukan tepat 2, ada bahu jalan, atau garis tepi tidak sejajar sempurna. **Jangan pakai batas yang jumlah lajurnya tidak pasti.** Garis kuning median yang berbatasan langsung dengan lajur dash adalah anchor yang lebih bersih.

---

## 4. Hasil BORR (kontrol negatif)

| Model | `f` | Pitch | Yaw | `h` | RMS | Fixed `f=1663,67` |
|---|---:|---:|---:|---:|---:|---:|
| Dash only | 1156,45 | 11,242° | 6,006° | 6,297 m | 1,314 px | 1,314 px (degenerate) |
| Dash + solid | 987,16 | 13,600° | 7,162° | 7,718 m | 1,436 px | 3,500 px |

Garis solid memutus degenerasi secara prinsip, tetapi hasilnya tidak bisa dipercaya: `u` dash naik dari 324 (dekat) ke 494 (jauh), tanda jalan melengkung ke kanan. Model garis lurus memaksa yaw 7,16° dan residual 1,4 px. BORR membutuhkan model jalan melengkung atau segmen lurus pendek; jangan masukkan BORR ke rata-rata `f` dengan model ini.

---

## 5. Budget error

| Sumber | Rentang | Efek pada `f` |
|---|---|---:|
| Noise piksel (statistik) | 1σ | ±8,8 px (±1,1%) |
| Subset solid (near vs far) | — | ±1,2% |
| Lebar lajur | 3,0–3,6 m | −17,6% |
| Lebar lajur | 3,6–3,9 m | −8,3% |
| Period dash | 13,0–13,333 m | +1,8% |
| Standar dash | 5 m vs 3 m | −44% (826 → 462) |

Kesimpulan budget: **error statistik bukan batas akurasi sebenarnya**. Batas akurasi datang dari `w` dan standar dash. Untuk klaim `f` absolut <5%, lebar lajur harus diukur (bukan diasumsikan 3,6 m) dan standar dash harus dipastikan dari geometri jalan/kecepatan situs.

---

## 6. Keterbatasan

- Uji ini hanya satu frame BELMERA dan satu frame BORR. Belum ada multi-frame atau multi-situs.
- Deteksi garis solid masih manual-ROI; threshold warna perlu disesuaikan per kamera.
- Model belum memasukkan distorsi radial. Near/far konsisten di BELMERA, tetapi kamera lain bisa lebih terdistorsi.
- `w` dan period/dash adalah input standar, bukan hasil pengukuran lapangan.
- Garis solid hanya membantu jika benar-benar sejajar dan berjarak tepat satu lebar lajur dari garis dash. Garis tepi dengan bahu atau lajur tambahan tidak memenuhi asumsi.
- BORR dan jalan melengkung belum tertangani.

---

## 7. Berkas

| Berkas | Isi |
|---|---|
| `solid_fit_cases.csv` | 14 kasus: dash-only, solid, sweep `w`, sweep period, near/far, wrong side, BORR |
| `belmera_dash_fit.csv/.json` | Baseline dash-only BELMERA |
| `belmera_solid_fit.csv/.json` | Fit dash + solid kuning, `w=3,6 m`, period 13 m |
| `belmera_solid_fit_scan.csv` | Scan `f` 700–950 |
| `belmera_solid_yellow.json` | 20 titik garis kuning median |
| `borr_solid_fit.csv/.json` | Fit BORR (kontrol negatif) |
| `borr_solid_fit_scan.csv` | Scan `f` BORR |
| `../../scripts/calib_compare/fit_dash_line.mjs` | Model dash + solid, fixed-f, scan-f, kovarians |
| `../../scripts/calib_compare/detect_solid_line.py` | Deteksi garis solid dari warna |

---

## 8. Arah berikutnya

1. **Ukur lebar lajur per situs** — minimal dari satu kendaraan yang diketahui lebarnya, atau dari marka lain yang lebarnya standar. Tanpa ini, `f` hanya sebaik asumsi 3,6 m.
2. **Tambahkan distorsi radial (`k1`)** ke model, lalu uji ulang di Cawang dan SVLD. Garis solid yang lurus adalah constraint kuat untuk `k1`.
3. **Otomatiskan pemilihan garis solid** dan validasi jumlah lajur; jangan pakai garis tepi yang punya bahu.
4. **Uji multi-frame** pada kamera statis untuk menekan noise deteksi.
5. **Uji pada SVLD** dengan `f` GT: pilih frame yang punya satu dash + satu solid, lalu bandingkan `f` hasil fit dengan XML. Ini satu-satunya cara mengukur akurasi absolut metode ini terhadap ground truth eksternal.
6. **Jangan klaim `f` absolut** dari dash fit Cawang sebagai ground truth; itu referensi konsistensi dengan `w=3,60 m`, bukan kebenaran independen.

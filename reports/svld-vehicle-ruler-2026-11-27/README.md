# SVLD: Vehicle-Ruler L1/L2 — Kandidat, Tool, dan Pilot Otomatis

**Tanggal:** 27 November 2026  
**Status:** tooling + pilot otomatis selesai; angka **L1/L2 final menunggu anotasi manual** 20 kendaraan.

---

## 1. Ringkasan

1. **24 kandidat siap** (20 primer ≤10,2° + 4 oblique 12,7–14,5°), tersebar di 5 scene SVLD. Bus/truk besar diambil dari trainval karena 100 citra sampel didominasi mobil.
2. **Pipeline L1/L2 sudah diuji dengan titik simulasi + lane oracle:** 24/24 lulus; `eW` median **0,37%** (p90 1,20%), `ew` median **0,34%** (p90 1,08%). Ini validasi implementasi geometri, bukan akurasi fisik.
3. **Pilot otomatis pada citra nyata** menunjukkan bottleneck-nya:
   - Lebar bodi dari **bbox 2D** meleset **14,8%** median (p90 44,3%) terhadap lebar muka kendaraan.
   - Lebar bodi dari **YOLO-seg mask** meleset **7,1%** median (p90 27,1%).
   - Formula rasio piksel sendiri konsisten: **22/22 <5%** terhadap `w_ref` dari titik lajur yang sama (median 0,79%, p90 3,0%).
   - Detektor lajur otomatis **tidak layak untuk lebar absolut**: median error **134,5%** terhadap prior scene; hanya **3/22** dalam 10%.
4. **Kesimpulan:** formula benar; yang gagal adalah **pengukuran lebar muka kendaraan** dan **pemilihan garis lajur**. Karena itu anotasi manual 5 titik per kendaraan tetap diperlukan. Tool-nya sudah siap.

---

## 2. Kandidat

20 kendaraan primer, 4 per scene, semuanya ≤10,2° (19 di antaranya ≤10°):

| Scene | Bus/truk | Mobil |
|---|---|---|
| 0cam | `real_scene_cam0_000667` | `005254`, `004778`, `014640` |
| 1cam | `real_scene_cam1_002664` | `012704`, `005176`, `004098` |
| session0_centre | `session0_center_000617` | `002850`, `007499`, `004110` |
| session0_right | — | `008012`, `006781`, `007989`, `006690` |
| session6_right | `session6_right_000462` | `000674`, `000224`, `008281` |

Grup sensitivitas oblique (tidak masuk median utama):

| Scene | Objek | Sudut |
|---|---|---:|
| session0_centre | `session0_center_000630` (truk) | 14,5° |
| session6_right | `session6_right_000815` (truk) | 13,9° |
| session0_right | `session0_right_006645` (mobil) | 13,3° |
| session6_right | `session6_right_008293` (mobil) | 12,7° |

Contoh anchor:

| ID | Kelas | Jarak | bbox | Sudut | `W_preset` |
|---|---|---:|---:|---:|---:|
| `0cam_bus_000667` | Bus | 42,8 m | 339×404 | 1,7° | 2,75 m |
| `1cam_bus_002664` | Bus | 18,3 m | 263×449 | 5,8° | 2,76 m |
| `s0c_truck_000617` | Truk | 42,7 m | 336×362 | 9,8° | 3,20 m |
| `s6r_truck_000462` | Truk | 35,5 m | 387×322 | 9,8° | 2,58 m |
| `0cam_car_005254` | Mobil | 35,2 m | 251×214 | 2,8° | 1,89 m |
| `1cam_car_012704` | Mobil | 17,8 m | 125×208 | 1,9° | 1,73 m |
| `s0r_car_008012` | Mobil | 28,2 m | 266×240 | 0,5° | 1,70 m |
| `s6r_car_000674` | Mobil | 20,8 m | 326×359 | 7,1° | 1,82 m |

Catatan data: kandidat Higer `real_scene_cam0_003368` **tidak dipakai** karena bbox/vertex-nya terpotong di bawah citra (`bbox bottom=744`, tinggi citra 720). Penggantinya `000667`, yang masih terlihat penuh sampai baris kontak.

---

## 3. Metode

### 3.1 L1 — lebar bodi

Empat titik/dua garis:

- `body_left`, `body_right`: tepi kiri/kanan **muka depan atau belakang** kendaraan, di **baris kontak ban**, tanpa spion.
- `contact`: titik kontak tanah di tengah bawah bodi.

`contact` di-back-project ke bidang jalan `Z=0` memakai kalibrasi SVLD, menghasilkan kedalaman `Y_contact`. Sinar melalui kedua tepi bodi dipotong dengan bidang `Y=Y_contact`, lalu:

```text
W_meas = |X_left - X_right|
```

Bandingkan `W_meas` dengan `W_spec` pabrikan. Kalibrasi SVLD hanya dipakai sebagai penggaris untuk menilai, bukan input formula.

### 3.2 L2 — lebar lajur

```text
w_formula = W_spec × L_px / V_px
w_ref     = |X_lane_left - X_lane_right| pada Y = Y_contact
```

- `L_px`: jarak piksel kedua garis lajur di baris kontak.
- `V_px`: jarak piksel kedua tepi bodi di baris yang sama.
- `w_ref`: back-project kedua garis lajur ke `Z=0` dengan kalibrasi SVLD.

**Koreksi penting dari pilot:** lebar bodi harus diukur di **baris kontak**, bukan di mid-height bodi. Versi awal memakai mid-height dan memberi error formula sampai **6,3%** pada bus 1cam yang dekat; setelah pindah ke baris kontak, error maksimum turun ke **4,4%** dan 22/22 lulus <5%. Alasannya: `V_px` dan `L_px` harus berada di kedalaman yang sama.

### 3.3 Anotasi manual

Tool clicker: `scripts/svld_vehicle_ruler.py annotate`. Urutan klik:

1. `body-L` — tepi kiri bodi di baris kontak, tanpa spion.
2. `body-R` — tepi kanan bodi di baris kontak.
3. `lane-L` — garis lajur kiri di baris yang sama.
4. `lane-R` — garis lajur kanan di baris yang sama.
5. `contact` — kontak tanah di tengah bawah bodi.

Setelah 5 klik, isi model, `W_spec`, confidence, dan sumber datasheet. Double-annotate 4 dari 20 kendaraan.

---

## 4. Hasil

### 4.1 Validasi pipeline (titik simulasi + lane oracle)

Titik muka diambil dari `vertex2d` SVLD; garis lajur diproyeksikan dari prior lebar lajur scene. Ini **bukan** pengukuran independen — hanya cek implementasi.

| Metrik | n | Median | p90 | Lulus |
|---|---:|---:|---:|---:|
| `eW` (L1) | 24 | **0,37%** | 1,20% | 24/24 <3% |
| `ew` (L2) | 24 | **0,34%** | 1,08% | 24/24 <5% |

### 4.2 Ablasi sumber lebar bodi (citra nyata)

Perbandingan lebar muka (`face`) dengan bbox 2D dan YOLO-seg mask, diukur pada mid-height yang sama. Rasio >1 berarti silhouette lebih lebar dari muka kendaraan.

| Sumber | Error vs `W_preset` (median) | p90 | Rasio median | Rasio p90 |
|---|---:|---:|---:|---:|
| Face (`vertex2d`) | 0,51% | 1,56% | — | — |
| Bbox 2D | **14,75%** | 44,26% | 1,147 | 1,441 |
| YOLO-seg mask | **7,06%** | 27,15% | 1,077 | 1,280 |

Baris `face` adalah **self-consistency** (titik muka berasal dari box preset), bukan pengukuran independen. Bbox dan mask adalah pengukuran citra nyata; keduanya dibandingkan terhadap lebar muka yang sama.

Per sudut relatif:

| Sudut | n | Bbox/face | Mask/face |
|---|---:|---:|---:|
| 0–3° | 10 | 1,062 | 0,998 |
| 3–6° | 3 | 1,093 | 1,052 |
| 6–10° | 6 | **1,316** | **1,265** |
| 10–15° | 5 | **1,309** | **1,161** |

Per kelas:

| Kelas | n | Bbox/face | Mask/face |
|---|---:|---:|---:|
| Mobil | 18 | 1,100 | 1,051 |
| Bus | 2 | 1,128 | 1,059 |
| Truk | 4 | **1,509** | **1,189** |

**Bacaan:** pada kendaraan yang hampir frontal (≤3°), mask sudah cukup (rasio 1,00); bbox masih 6% terlalu lebar. Di atas 6°, bbox dan mask sama-sama membesar 27–32% karena ikut sisi samping. Truk paling parah (bbox 1,51×) karena panjangnya. Maka **anotasi muka kendaraan tidak bisa diganti bbox/mask**.

### 4.3 Formula dan detektor lajur

Pilot memakai titik lajur dari `detect_lane_vp` di baris kontak, lalu membandingkan:

- `w_formula` vs `w_ref` dari titik lajur yang sama → menguji formula/kedalaman.
- `w_ref` vs prior lebar lajur scene → menguji apakah detektor memilih garis yang benar.

| Metrik | n | Median | p90 | Maks | Lulus |
|---|---:|---:|---:|---:|---:|
| `w_formula` vs `w_ref` | 22 | **0,79%** | 3,00% | 4,41% | **22/22 <5%** |
| `w_ref` vs prior scene | 22 | **134,5%** | 242,7% | 298,4% | **3/22 <10%** |

Detektor lajur menemukan garis di 22/24 citra, tetapi garis yang dipilih sering bukan batas lajur kendaraan: lebar yang dihasilkan 2–4× prior. Formula tetap konsisten karena memakai titik yang sama; yang salah adalah **pemilihan garis**. Karena itu L2 final harus memakai garis lajur manual.

---

## 5. Temuan

1. **Formula rasio piksel benar.** Dengan titik lajur yang sama, `w_formula` dan `w_ref` berbeda <5% di 22/22 kasus. Implementasi geometri dan konversi kedalaman tidak bermasalah.
2. **Sumber lebar bodi adalah bottleneck utama.** Bbox 2D dan mask silhouette memasukkan sisi samping/spion; error tumbuh dari ~6% pada 0–3° menjadi ~30% pada 6–10°. Untuk anchor 5%, hanya muka kendaraan yang layak.
3. **Detektor lajur otomatis belum bisa dipakai untuk lebar absolut.** Hanya 3/22 dalam 10% dari prior. Ini konsisten dengan lane fit SVLD yang sebelumnya 0/45.
4. **Baris kontak adalah kunci.** Mengukur lebar bodi di mid-height menambah error hingga 6,3% pada objek dekat; same-row menurunkannya ke <4,4%.
5. **SVLD tetap validasi geometri, bukan armada Indonesia.** `W_preset` hanya placeholder; L1/L2 final harus memakai model dan datasheet pabrikan.

---

## 6. Yang belum selesai

- **L1/L2 final** belum dijalankan karena titik manual belum ada. Tool dan kandidat sudah siap; ini pekerjaan anotasi, bukan pekerjaan algoritma.
- `W_spec` masih kosong di `candidates.csv`; isi setelah model terbaca.
- L3 (f end-to-end) belum dijalankan; perlu lane boundary manual + median VP + `w_formula`.

---

## 7. Cara menjalankan

```powershell
# 1. Bangun kandidat + crop bergrid
& "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe" `
  scripts\svld_vehicle_ruler.py candidates

# 2. Cek pipeline dengan titik simulasi (bukan L1/L2 final)
& "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe" `
  scripts\svld_vehicle_ruler.py simulate
& "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe" `
  scripts\svld_vehicle_ruler.py eval --ann out\svld_vehicle_ruler\annotations_sim.csv

# 3. Anotasi manual 5 titik + model/spec
& "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe" `
  scripts\svld_vehicle_ruler.py annotate --ids 0cam_bus_000667,1cam_bus_002664

# 4. Evaluasi L1/L2 final
& "C:\Users\omega\AppData\Local\Temp\opencode\geoenv\Scripts\python.exe" `
  scripts\svld_vehicle_ruler.py eval --ann out\svld_vehicle_ruler\annotations_manual.csv

# 5. Pilot otomatis (bbox/mask/lane detector)
& "D:\Kerjaan\LearnPinhole\backend\.venv\Scripts\python.exe" `
  scripts\svld_vehicle_ruler_auto.py --limit 24 --imgsz 1280
```

`annotate` membuka jendela OpenCV. Klik 5 titik, lalu isi model/`W_spec` di terminal. Tekan `u` untuk undo, `s` untuk simpan, `n` untuk lanjut, `q` untuk keluar.

---

## 8. Berkas

| Berkas | Isi |
|---|---|
| `candidates.csv` | 24 kandidat: scene, kelas, bbox, jarak, sudut, `W_preset`, path citra/anotasi/kalibrasi |
| `auto_results.csv` | 24 baris pilot: `V_face`, `V_bbox`, `V_mask`, rasio, lane, `w_formula`, `w_ref`, error |
| `auto_summary.json` | Ringkasan ablasi body source, formula, dan lane detector |
| `sim_results.csv` | 24 baris validasi pipeline dengan titik simulasi + lane oracle |
| `sim_summary.json` | Ringkasan L1/L2 simulasi |
| `annotations_sim.csv` | Titik simulasi (muka + lane oracle); bukan anotasi independen |
| `overlays/*.jpg` | Contoh overlay 4 anchor: bus 0cam/1cam, truk session0_centre/session6_right |
| `../../scripts/svld_vehicle_ruler.py` | Kandidat, simulate, eval, clicker |
| `../../scripts/svld_vehicle_ruler_auto.py` | Pilot otomatis YOLO-seg + lane detector |

---

## 9. Batas

- Titik simulasi memakai `vertex2d`; `veh_size` SVLD adalah preset, bukan pengukuran fisik.
- Mask YOLO adalah model COCO; mask mid-height masih memasukkan sisi samping dan tidak membuang spion.
- Detektor lajur klasik gagal di 2/24 dan salah garis di sebagian besar sisanya; angka prior bukan GT.
- `W_spec` pada pilot = `W_preset`; belum ada datasheet pabrikan.
- SVLD bukan jalan Indonesia; hasilnya validasi geometri, bukan armada/spec Indonesia.
- Angka L1/L2 final belum ada; laporan ini adalah tooling + pilot.

---

## 10. Langkah berikutnya

1. Anotasi 20 kendaraan primer (5 titik + model/spec); double-annotate 4.
2. Evaluasi L1: target median **<3%**, p90 **<5%**.
3. Evaluasi L2: target median **<5%**, p90 **<10%**.
4. Kalau lulus, L3: garis lajur manual + median VP + `w_formula` → `f`, bandingkan dengan GT SVLD.
5. Ulangi protokol di Cawang/BELMERA dengan kendaraan Indonesia (Avanza, Innova, Elf, bus).

# Plan: Penutupan Kelemahan dengan Paper/Repo

## Tujuan

Membuktikan dengan data eksternal — bukan menambah teori — apakah:

1. GeoCalib cukup akurat pada kamera CCTV nyata;
2. pipeline pengukuran $L/W/H$ mencapai akurasi yang berguna;
3. komponen CAROM Air (keypoint + model bentuk) bisa dijalankan pada sudut kamera CCTV;
4. anchor bisa diperoleh tanpa survei, dan seberapa besar jebakan sirkularnya.

Dokumen acuan: `PAPER-REPO-Untuk-Menutup-Kelemahan.md`.
SOP acuan: `SOP-KALIBRASI-CCTV.md` §0.3, §3.4, §4.3, §5.4, §6, §7.

> **Catatan path.** Plan ini ditulis saat bekerja di folder `out/`. Di repo, artefak yang sudah dijalankan disalin ke `reports/`; `out/` tetap folder kerja yang di-.gitignore. Path `out/...` di bawah adalah path kerja; padanannya di repo ada di `reports/...`.

## Status pelaksanaan (18 November 2026)

| Fase | Status | Bukti / catatan |
|---|---|---|
| 0. Persiapan | **selesai** | I24-3D 50,04 GB + SVLD trainval 13,47 GB tersedia; environment GeoCalib siap; SKoPe3D/RoScenes belum |
| 1. Kalibrasi I24-3D | **dibatalkan** | `hg` bukan GT f/pose; EB vs WB Δf median 7,1%; GeoCalib pitch meleset 9–65°; lihat `reports/i24-3d-kalibrasi/README.md` |
| 2. Dimensi I24-3D | **siap dimulai** | 876.948 box, 720 objek; gunakan `P` untuk reproyeksi box dan `H` untuk ground-plane, bukan RQ(`P`) |
| 3. SVLD-3D | **sebagian** | Test 50 objek MAPE 0,36% (self-consistency); trainval 14.592 gambar, 700 Truck/1.166 Bus, 120+174 fit, RMS 0,34–0,39 px; **`veh_size` preset**; lihat `reports/svld-trainval/README.md` |
| 4. Keypoint + shape | **sebagian** | zero-shot Car 44,1%/Bus 0%; mask W/H ~7%, L 21,9%; fine-tune/GSNet belum |
| 5–8. Anchor, MoGe-2, lajur, sintesis | **belum** | — |
| Tambahan: container-only | **sebagian** | Grounded SAM 2 + tinggi standar; 20 ft 6,046 m (−0,2%); 40 ft masih ambigu 40/45 ft; lihat `HASIL-TIMEPASS-CAWANG.md` |

## Prinsip

- **Ground truth dulu, metode kemudian.** Jangan menguji pipeline sebelum kalibrasi dan satuan diverifikasi.
- **Satu fase, satu gerbang.** Jika gerbang gagal, jangan lanjut ke fase berikutnya; perbaiki atau dokumentasikan kegagalan.
- **Tidak ada klaim tanpa angka.** Setiap laporan memuat tabel, jumlah sampel, dan ketidakpastian.
- **Dataset non-komersial hanya untuk validasi.** Jangan dipakai melatih model produksi tanpa izin.
- **Reproduksibel.** Semua skrip, konfigurasi, dan daftar frame disimpan; hasil bisa diulang.

## Ruang lingkup

**Termasuk:**

- validasi kalibrasi dan dimensi pada I24-3D;
- benchmark bus pada SVLD-3D; truk dari I24-3D;
- keypoint + shape fitting pada SKoPe3D, OpenPifPaf, GSNet;
- uji anchor naver/cctv dan cek skala MoGe-2;
- penyelesaian ambiguitas 2 vs 3 lajur dengan OSM/satelit;
- sintesis keputusan.

**Tidak termasuk:**

- survei lapangan di Indonesia (kegiatan terpisah);
- deployment produksi;
- sertifikasi metrologi legal;
- fusi multi-kamera (kecuali waktu memungkinkan).

## Definisi selesai

| Fase | Metrik | Lulus jika |
|---|---|---|
| 1. Kalibrasi I24-3D | $\Delta f/f$, $\Delta\theta$ | median $\Delta f/f<5\%$, median $|\Delta\theta|<2^\circ$, ≥80% kamera lulus |
| 2A. Round-trip formula | galat rekonstruksi | <1% pada $L/W/H$ |
| 2B. Dimensi I24-3D | MAPE, bias | $W/H$ <10% pada 20–30 m; panjang dilaporkan terpisah |
| 3. SVLD-3D | MAPE per kelas | bus <15%; truk diuji di I24-3D; dibandingkan dengan presisi 85% |
| 4. Keypoint + shape | PCK@0.1, RMS, MAPE | PCK >80% pada 5 titik, RMS ≤3 px, $L/W/H$ <10% |
| 5. Anchor naver/cctv | pergeseran skala | <5% saat prior diubah ±5%; jika tidak, hanya inisialisasi |
| 6. MoGe-2 | selisih $h$ | <10% dari anchor; 10–20% peringatan; >20% buang |
| 7. Jumlah lajur | $N$ | konsisten antara OSM dan lebar satelit |
| 8. Sintesis | matriks keputusan | setiap kelemahan berstatus tertutup/sebagian/tidak |

---

## Steps

- [ ] 1. Fase 0 — persiapan: akses dataset, cek resource, environment, struktur folder, protokol
- [ ] 2. Fase 1 — I24-3D: parse kalibrasi GT, ekstrak frame, jalankan GeoCalib, hitung $\Delta f/f$ dan $\Delta\theta$, diagnosis
- [ ] 3. Fase 2 — I24-3D: round-trip formula, lalu pengukuran 50 kendaraan, analisis per jarak/kelas
- [ ] 4. Fase 3 — SVLD-3D: benchmark 200 citra (car/bus), bandingkan dengan CenterLoc3D
- [ ] 5. Fase 4 — keypoint: OpenPifPaf zero-shot, SKoPe3D, fine-tune CCTV, fitting GSNet
- [ ] 6. Fase 5 — naver/cctv: siapkan track, estimasi homografi, uji sensitivitas prior
- [ ] 7. Fase 6 — MoGe-2: point map metrik, fit bidang jalan, bandingkan tinggi kamera
- [ ] 8. Fase 7 — jumlah lajur: OSM + lebar satelit
- [ ] 9. Fase 8 — sintesis: matriks keputusan, perbarui dokumen, putusan go/no-go

---

## Fase 0 — Persiapan (0,5–1 hari)

### 0.1 Akses dataset

- [ ] Ajukan akun I24-3D di `https://i24motion.org` (non-komersial; akses komersial harus diminta).
- [ ] Unduh SVLD-3D dari tautan Google Drive di `https://github.com/stjuliet/SVLD-3D-DATASET`; mulai dari test set.
- [ ] Unduh SKoPe3D dari `https://skope3d.github.io/`; mulai dari subset 5.000 citra.
- [ ] Opsional: RoScenes via ModelScope (non-komersial), hanya jika butuh truk lebih banyak.
- [ ] Catat status lisensi tiap dataset di `out/00-akses.md`.

### 0.2 Cek resource

```powershell
nvidia-smi
Get-PSDrive D
ffmpeg -version
node --version
py --version
uv --version
```

- [ ] Catat GPU, VRAM, ruang disk, dan versi tool.
- [ ] Jika tidak ada GPU: rencanakan OpenPifPaf/Keypoint R-CNN/GSNet pada CPU atau subset kecil; MoGe-2 mungkin terlalu lambat, jalankan hanya 2–4 citra.
- [ ] Siapkan ruang disk: I24-3D berisi video 4K; SVLD-3D dan SKoPe3D lebih ringan.

### 0.3 Environment

GeoCalib sudah pernah dipasang di `C:\Users\omega\AppData\Local\Temp\opencode\geoenv`. Verifikasi dulu, lalu buat env terpisah untuk komponen lain agar dependensi tidak bentrok.

```powershell
$GEO="C:\Users\omega\AppData\Local\Temp\opencode\geoenv"
& "$GEO\Scripts\python.exe" -c "import torch, geocalib; print(torch.__version__)"

$EVAL="C:\Users\omega\AppData\Local\Temp\opencode\cctv-eval"
uv venv $EVAL --python 3.11
uv pip install --python "$EVAL\Scripts\python.exe" numpy scipy pandas opencv-python matplotlib
```

- [ ] Verifikasi GeoCalib.
- [ ] Buat env `cctv-eval` untuk parsing, metrik, dan plot.
- [ ] Buat env terpisah `openpifpaf` (AGPL, riset saja) dan `moge` (MIT).
- [ ] Catat semua versi di `out/00-environment.md`.

### 0.4 Struktur folder

```text
data/
  i24/
    video/
    hg/
    annotations/
  svld/
  skope3d/
out/
  i24/
    frames/
    geocalib/
  svld/
  keypoint/
  anchor/
  moge/
scripts/
  i24_parse.py
  i24_frames.py
  geocalib_batch.py
  eval_i24_calib.py
  eval_i24_dimensi.py
  svld_eval.py
  keypoint_eval.py
  gsnet_fit.py
  anchor_naver.py
  moge_height.py
```

- [ ] Buat folder.
- [ ] Tambahkan `data/` dan `out/` ke `.gitignore` (dilakukan saat Build mode).

### 0.5 Protokol

Tulis `out/00-protocol.md`:

- [ ] definisi sumbu dan satuan (meter; I24-3D kaki dikonversi 0,3048);
- [ ] definisi $L/W/H$ dan titik acuan (bottom-center rear untuk I24-3D);
- [ ] cara memilih frame (3 per kamera: 10 s, 30 s, 50 s);
- [ ] cara menghitung MAPE dan bias;
- [ ] aturan pembulatan dan pelaporan ketidakpastian;
- [ ] kriteria gagal yang objektif.

---

## Fase 1 — I24-3D: validasi kalibrasi (2–3 hari)

> **Update 19 November 2026 — gerbang ini dibatalkan.** Data lengkap sudah diperiksa.
>
> - `P[:,2]` adalah kolom VP vertikal dengan skala arbitrer; `scale_Z()` hanya mencocokkan tinggi box. RQ(`P`) bukan intrinsik fisik.
> - `f` dari dua kalibrasi kamera yang sama (EB vs WB) berbeda median **7,1%**, p90 **24,6%**, maks **30,6%**.
> - Ground RMS `H_inv` → `corr_pts` median **3,89 px**; **0/102** <1 px.
> - Ketinggian kamera median 34 m (90% di 28–45 m), pitch 17–75° (p2c3 hampir nadir). GeoCalib `f` meleset **−52% s/d +26%** (multi-frame; single-frame sampai −76%), pitch **9–65°**.
> - **Jangan** memakai Δf/f dan Δpitch terhadap `P` sebagai gerbang. Fase 1 diganti menjadi validasi ground-plane/dimensi (Fase 2) dan uji kalibrasi memakai SVLD-3D/pengukuran lapangan.
> - Laporan: `reports/i24-3d-kalibrasi/README.md`.

### 1.1 Parse kalibrasi GT

- [ ] Inspeksi `sceneX_hg.json`: bentuk `P`, `H`, `vps`, dan apakah `P` 3×4 atau 4×3.
- [ ] Tulis `scripts/i24_parse.py`:
  - muat `P`, transpos jika perlu;
  - RQ decomposition blok 3×3 → $K,R$;
  - normalisasi $K_{33}=1$;
  - ekstrak $f_x,c_x,c_y$;
  - hitung pitch dari VP longitudinal atau dari $R$;
  - konversi satuan jika perlu.
- [ ] Verifikasi round-trip: proyeksikan titik `space_pts` dengan `P`, bandingkan dengan `corr_pts`; residual harus <1 px.

### 1.2 Ekstrak frame

- [ ] Untuk tiap scene dan kamera, ambil 3 frame.
- [ ] Gunakan 1080p jika 4K terlalu berat; catat rasio skala terhadap `P`.

```powershell
ffmpeg -ss 10 -i data/i24/video/scene1/p1c1.mp4 -frames:v 1 out/i24/frames/scene1_p1c1_010.png
ffmpeg -ss 30 -i data/i24/video/scene1/p1c1.mp4 -frames:v 1 out/i24/frames/scene1_p1c1_030.png
ffmpeg -ss 50 -i data/i24/video/scene1/p1c1.mp4 -frames:v 1 out/i24/frames/scene1_p1c1_050.png
```

- [ ] Verifikasi frame tidak blur, tidak terpotong, dan berisi jalan.
- [ ] Simpan daftar frame di `out/i24/frames.csv`.

### 1.3 Jalankan GeoCalib

- [ ] Adaptasi `f2/geocalib_run.py` menjadi batch:
  - input folder/daftar frame;
  - output JSON per frame: `f_px`, `pitch_deg`, `roll_deg`, `horizon_row`;
  - tangani error per file tanpa menghentikan batch.
- [ ] Jalankan pada semua frame.
- [ ] Cek sebaran $f$ antar frame dalam satu kamera; jika >5%, tandai kamera tidak stabil.

### 1.4 Hitung metrik

- [ ] $\Delta f/f=|f_G-f_{GT}|/f_{GT}$.
- [ ] $\Delta\theta=|\theta_G-\theta_{GT}|$.
- [ ] Bandingkan juga roll; jika roll >2°, uji asumsi roll nol.
- [ ] Buat tabel per kamera: scene, kamera, $f_{GT}$, $f_G$, $\Delta f/f$, $\theta_{GT}$, $\theta_G$, $\Delta\theta$, status.
- [ ] Buat histogram $\Delta f/f$ dan $\Delta\theta$; tandai outlier.
- [ ] Hitung persentase kamera yang lulus.

**Gerbang 1:** median $\Delta f/f<5\%$, median $|\Delta\theta|<2^\circ$, ≥80% kamera lulus.

### 1.5 Diagnosis jika gagal

- [ ] Periksa distorsi lensa (uji §3.4) pada kamera terburuk.
- [ ] Periksa rolling shutter, interlacing, dan resolusi.
- [ ] Coba crop: buang langit dan kendaraan besar; jalankan ulang.
- [ ] Coba 2–3 skala resolusi; pastikan $K$ diskalakan.
- [ ] Catat apakah kegagalan sistematis (semua kamera) atau lokal (kamera tertentu).

### 1.6 Keluaran

- [ ] `VALIDASI-I24-3D-KALIBRASI.md`
- [ ] `out/i24/geocalib.json`
- [ ] `out/i24/calib_eval.csv`
- [ ] plot `out/i24/calib_f_error.png`, `out/i24/calib_pitch_error.png`

**Jika gerbang 1 gagal:** stop. Jangan lanjut ke Fase 2. Tulis catatan kegagalan dan revisi pendekatan kalibrasi.

---

## Fase 2 — I24-3D: validasi dimensi (3–4 hari)

> **Status 19 November 2026:** Fase 2 tetap layak. Gunakan `H`/`P` hanya untuk memproyeksikan box 3D dan mengukur `L/W/H`; **jangan** menurunkan `K` dari RQ(`P`). Data: 876.948 baris anotasi, 720 objek, satuan kaki. Untuk uji geometri murni, proyeksikan box GT dengan `P` lalu bandingkan dimensi; tidak perlu `K`.

### 2A — Round-trip formula (0,5–1 hari)

Tujuan: memastikan rumus dan konvensi benar sebelum menyentuh persepsi.

- [ ] Ambil 100 kendaraan dari I24-3D.
- [ ] Ambil box 3D GT, proyeksikan ke citra dengan $P$.
- [ ] Dari box 2D hasil proyeksi + $K$, rekonstruksi $L/W/H$ memakai rumus pipeline.
- [ ] Bandingkan dengan GT.
- [ ] Jika galat >1%, debug: urutan sudut, satuan kaki/meter, principal point, orientasi sumbu, tanda pitch.
- [ ] Simpan `out/i24/roundtrip.csv`.

**Gerbang 2A:** galat <1% pada ketiga sumbu.

### 2B — Pengukuran nyata (2–3 hari)

- [ ] Pilih 50 kendaraan stratifikasi:
  - jarak: 20–40 m, 40–70 m, 70–100 m;
  - kelas: sedan, pickup/van, semi/truck.
- [ ] Untuk tiap kendaraan, anotasi manual:
  - 2D box;
  - titik kontak ban;
  - sudut yang terlihat.
- [ ] Jalankan pipeline pengukuran yang ada (`measure.mjs` atau adaptasi `scripts/eval_i24_dimensi.py`).
- [ ] Hitung MAPE dan bias per sumbu, per kelas, per jarak.
- [ ] Uji anisotropi: $\sigma_z/\sigma_y$ versus $z/h$.
- [ ] Catat kegagalan: oklusi, kendaraan terpotong, bayangan, sudut pandang.

**Gerbang 2B:** $W/H$ MAPE <10% pada 20–30 m; panjang dilaporkan terpisah (boleh >10%, tetapi harus dijelaskan).

### 2C — Keluaran

- [ ] `VALIDASI-I24-3D-DIMENSI.md`
- [ ] `out/i24/dimensi.csv`
- [ ] plot galat vs jarak, galat vs kelas, bias per sumbu

---

## Fase 3 — SVLD-3D: bus dan kendaraan besar (2–3 hari)

> **Status 19 November 2026.** Trainval tersedia: 14.592 gambar, 39.477 objek (**700 Truck**, 1.166 Bus, 37.611 Car); 5 scene kalibrasi konsisten (median 0,73–0,84 px, 0 objek >2 px). Pilot fit 120 Truck + 174 Bus: RMS 0,34–0,39 px, MAPE median 0,20–0,32%, tetapi panjang memburuk >100 m (4,39% median di >150 m; maks 17,96%). **Penting: `veh_size` adalah preset, bukan pengukuran**; Fase 3 dipakai untuk stress-test geometri/kelas besar, bukan accuracy claim. Laporan: `reports/svld-trainval/README.md`.

- [ ] Parse `Calib/{scene_id}.xml` dan anotasi XML (test + trainval).
- [ ] Verifikasi satuan: `veh_size` meter; `vertex3d` milimeter; `bbox2d` = x, y, w, h.
- [ ] Catat distribusi test: 7.396 Car, 745 Bus, **1 Truck**; trainval: 37.611 Car, 1.166 Bus, **700 Truck**. `veh_size` preset — jangan klaim akurasi fisik.
- [ ] Pilih 200 citra test: 70 car, 130 bus; sebar jarak.
- [ ] Jalankan pipeline yang sama seperti Fase 2B.
- [ ] Hitung MAPE per kelas dan per sumbu.
- [ ] Bandingkan dengan CenterLoc3D: presisi 85% = jumlah galat tiga sumbu ≈15%, rata-rata ≈5% per sumbu.
- [ ] Analisis khusus panjang bus; cek apakah galat berasal dari sudut pandang atau oklusi.
- [ ] `VALIDASI-SVLD-3D.md` + CSV + plot.

**Gerbang 3:** bus MAPE <15%. Jika lebih buruk, dokumentasikan dan jangan klaim akurasi ODOL. Truk diuji terpisah di I24-3D.

---

## Fase 4 — Pipeline keypoint + shape (5–7 hari)

### 4A0 — Bukti dari SVLD (sudah dikerjakan)

- [x] Verifikasi kalibrasi SVLD: 8.142 objek, median RMS 0,74 px.
- [x] Fit 50 objek dengan 8 sudut GT: MAPE 0,36% (self-consistency; `veh_size` preset).
- [x] Sensitivitas: 3 px → 2,79%, 1,7% gagal; 5 px → 63,2% gagal.
- [x] Subset: 4 kontak tanah + 1 atap (5 titik) → MAPE 0,48%, 0 gagal.
- [x] Zero-shot `vehicle-keypoints`: 20 citra, match 56,9%, 5/5 di antara semua GT 36,1% (Car 44,1%, Bus 0%).
- Kesimpulan: target detektor adalah **5 titik dengan akurasi ≤3 px**, tetapi model zero-shot belum cukup; perlu fine-tune atau mask-based.
- Catatan: OpenPifPaf gagal build di Windows tanpa MSVC; `vehicle-keypoints` dipakai sebagai alternatif.

### 4A — Uji keypoint zero-shot (1 hari)

- [x] Pasang `vehicle-keypoints` (YOLO26-pose, MIT) + checkpoint Hugging Face.
- [x] Jalankan pada 20 citra SVLD (10 Car, 10 Bus).
- [x] Fokus pada 4 roda + 1 atap; hitung match rate dan 5/5.
- [x] Catat domain gap: bus 0%, mobil 44,1% dari semua GT.
- [ ] Jika ingin melanjutkan keypoint: fine-tune pada crop SVLD atau latih detector 5 titik; butuh GPU/waktu.

### 4A1 — Mask-based YOLO-seg (sudah dikerjakan)

- [x] YOLO11n-seg (COCO) pada 20 citra SVLD; 21 objek fit.
- [x] Fit 3D box ke mask: **W 7,11%, H 7,55%, L 21,92%**; mask IoU 0,796.
- [x] Kesimpulan: mask layak untuk lebar/tinggi, tidak untuk panjang. Mask body tidak memuat kontak ban.
- [ ] Berikutnya: hybrid mask untuk W/H + keypoint kontak tanah untuk L, atau fusi multi-frame.

### 4B — SKoPe3D + fine-tune (2–3 hari)

- [ ] Unduh subset SKoPe3D; inspeksi 33 keypoint.
- [ ] Tentukan strategi:
  - **Opsi A:** latih Keypoint R-CNN pada SKoPe3D (seperti paper), lalu fine-tune pada 100 frame CCTV.
  - **Opsi B:** petakan 33 keypoint SKoPe3D ke 24 keypoint Apollo, lalu fine-tune OpenPifPaf.
- [ ] Anotasi 100 frame CCTV (24 keypoint atau 8 sudut box).
- [ ] Latih/fine-tune; evaluasi PCK@0.1 dan reproyeksi.
- [ ] Simpan model dan konfigurasi.

### 4C — GSNet fitting (2–3 hari)

- [ ] Clone `lkeab/gsnet`; ambil 79 mesh + PCA.
- [ ] Catat: bobot pretrained sudah dihapus; fitting harus ditulis sendiri.
- [ ] Tulis `scripts/gsnet_fit.py`:
  - parameter pose (R, t) + shape $\mathbf{b}$;
  - proyeksi perspektif penuh (bukan weak perspective);
  - residual keypoint 2D;
  - regularizer bentuk ke mean shape.
- [ ] Uji pada 20 kendaraan yang punya GT $L/W/H$ (I24-3D/SVLD-3D).
- [ ] Hitung RMS reproyeksi dan galat dimensi.

**Gerbang 4:** PCK >80% pada 5 titik (4 kontak tanah + 1 atap), RMS ≤3 px pada 20-30 m, $L/W/H$ <10%. Pada SVLD, noise 5 px membuat 63% fitting gagal; 3 px hanya 1,7%. Jika gagal, tulis hasil negatif dan turunkan klaim adaptasi.

### 4D — Arsitektur hybrid (usulan)

- [ ] Gabungkan mask-based $W/H$ dengan keypoint/ground-contact $L$.
- [ ] Uji pada 50 objek yang sama; target $W/H$ <10%, $L$ <10%.
- [ ] Jika $L$ tetap >10%, coba fusi multi-frame atau hentikan klaim panjang.
- [ ] `PIPELINE-HYBRID.md`

### 4E — Keluaran

- [ ] `PIPELINE-KEYPOINT-SHAPE.md`
- [ ] `out/keypoint/pck.csv`
- [ ] `out/keypoint/gsnet_fit.csv`
- [ ] visual overlay keypoint dan mesh

---

## Fase 5 — naver/cctv: uji anchor (2–3 hari)

- [ ] Clone `https://github.com/naver/cctv`; pasang dependensi; unduh model pretrained.
- [ ] Siapkan track 2D:
  - YOLOv8 + SORT/BoT-SORT pada klip Cawang/ATP 5 menit;
  - ekspor ke format yang diminta repo.
- [ ] Jalankan estimasi homografi.
- [ ] Bandingkan $H$, $f$, pitch dengan GeoCalib/REV2.
- [ ] Uji sensitivitas: ubah prior dimensi ±5% dan ±10%; catat pergeseran skala.
- [ ] Uji pada BrnoCompSpeed hanya jika akses tersedia; jika tidak, lewati dan catat.
- [ ] `UJI-ANCHOR-NAVER.md` + CSV.

**Gerbang 5:** pergeseran skala <5% untuk perubahan prior ±5% → boleh untuk inisialisasi. Jika >5% → hanya inisialisasi, bukan anchor; jangan pakai untuk ODOL.

---

## Fase 6 — MoGe-2: cek skala (1–2 hari)

- [ ] Clone `microsoft/MoGe`; pasang di env terpisah.
- [ ] Jalankan pada 4 frame Cawang + 4 frame ATP.
- [ ] Masking jalan; ambil titik permukaan jalan.
- [ ] Fit bidang $\mathbf{n}^\top\mathbf{P}+d=0$; hitung $h=|d|/\|\mathbf{n}\|$.
- [ ] Bandingkan dengan anchor Cawang 8,876 m.
- [ ] `UJI-SKALA-MOGE.md`.

**Gerbang 6:** <10% → berguna sebagai cek cepat; 10–20% → peringatan; >20% → buang.

---

## Fase 7 — Jumlah lajur (0,5 hari)

- [ ] Query OSM `lanes` untuk ruas Cawang/ATP.
- [ ] Ukur lebar perkerasan di citra satelit.
- [ ] Hitung $N\approx W_{\text{perkerasan}}/w_{\text{lajur}}$, dengan $w_{\text{lajur}}$ 3,0–3,75 m.
- [ ] Bandingkan dengan hipotesis 2 vs 3 lajur.
- [ ] `CATATAN-LAJUR-ATP.md`.

---

## Fase 8 — Sintesis dan putusan (2 hari)

- [ ] Buat matriks keputusan:

| Kelemahan | Sumber | Hasil | Status | Bukti |
|---|---|---|---|---|
| Ground truth | I24-3D/SVLD-3D | | | |
| Kalibrasi | GeoCalib vs GT | | | |
| Dimensi | I24-3D/SVLD-3D | | | |
| Pipeline | SKoPe3D/OpenPifPaf/GSNet | | | |
| Anchor | naver/cctv | | | |
| Skala | MoGe-2 | | | |
| Lajur | OSM/satelit | | | |

- [ ] Tulis `HASIL-VALIDASI.md`.
- [ ] Perbarui `README.md`, `RISET-CAROM-Air-untuk-CCTV.md`, dan SOP jika hasilnya mengubah prosedur (dilakukan di Build mode).
- [ ] Putusan:
  - **GO:** lanjut ke validasi lapangan Indonesia;
  - **PIVOT:** fokus ke multi-kamera atau ruas lurus;
  - **STOP:** klaim adaptasi tidak terbukti.

---

## Timeline realistis

| Minggu | Fokus | Keluaran |
|---|---|---|
| 1 | Fase 0–1 | environment, akses, `VALIDASI-I24-3D-KALIBRASI.md` |
| 2 | Fase 2–3 | `VALIDASI-I24-3D-DIMENSI.md`, `VALIDASI-SVLD-3D.md` |
| 3 | Fase 4 | `PIPELINE-KEYPOINT-SHAPE.md` |
| 4 | Fase 5–8 | `UJI-ANCHOR-NAVER.md`, `UJI-SKALA-MOGE.md`, `HASIL-VALIDASI.md` |

**Jalur minimum (1 minggu):** Fase 0, 1, dan 2A. Ini sudah menguji apakah GeoCalib dan rumus dasar bekerja pada 50 kamera nyata. Jika gagal, tidak perlu lanjut.

**Perkiraan realistis:** 4–6 minggu, karena akses dataset, unduhan 4K, dan GPU. Perkiraan 2 minggu hanya berlaku jika akses dan GPU sudah siap.

---

## Risiko dan mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Akses I24-3D lambat | Fase 1 tertunda | Ajukan hari 0; mulai SVLD-3D paralel |
| Tidak ada GPU | OpenPifPaf/GSNet/MoGe lambat | Subset kecil; CPU; cloud sekali pakai |
| Video 4K besar | Disk/decode | Ekstrak frame 1080p; hapus video setelah frame |
| GT I24-3D ±15 cm | Klaim akurasi terbatas | Laporkan batas; jangan klaim <15 cm |
| Domain gap AS/Cina | Hasil tidak langsung berlaku di Indonesia | Sebut sebagai proksi; validasi lokal tetap perlu |
| Lisensi non-komersial | Tidak boleh untuk produk | Validasi riset; model produksi dari data sendiri |
| GSNet pretrained dihapus | Fitting lebih lama | Mulai dari mesh + PCA; anggarkan 2–3 hari |
| Skema keypoint 33 vs 24/66 | Mapping tidak langsung | Pilih Opsi A (Keypoint R-CNN) atau mapping eksplisit |
| naver/cctv butuh track | Kualitas H bergantung detektor | Uji dengan track manual pada 1 klip sebagai pembanding |
| Waktu melebihi rencana | Proyek berhenti di tengah | Jalur minimum 1 minggu; hentikan jika Gerbang 1 gagal |

---

## Berkas yang akan dihasilkan

| Berkas | Isi |
|---|---|
| `VALIDASI-I24-3D-KALIBRASI.md` | GeoCalib vs $P$ pada ~50 kamera |
| `VALIDASI-I24-3D-DIMENSI.md` | round-trip + 50 kendaraan |
| `VALIDASI-SVLD-3D.md` | bus, 200 citra; truk diuji di I24-3D |
| `PIPELINE-KEYPOINT-SHAPE.md` | keypoint + GSNet fitting |
| `UJI-ANCHOR-NAVER.md` | homografi dari track + sensitivitas prior |
| `UJI-SKALA-MOGE.md` | tinggi kamera dari point map |
| `CATATAN-LAJUR-ATP.md` | jumlah lajur |
| `HASIL-VALIDASI.md` | matriks keputusan dan putusan |
| `scripts/*.py` | parsing, evaluasi, fitting |
| `out/**` | CSV, JSON, plot, frame |

---

## Langkah pertama

1. **Hari 0:** ajukan akses I24-3D; unduh SVLD-3D test set.
2. **Hari 0:** cek GPU/disk; verifikasi GeoCalib.
3. **Hari 1:** parse `sceneX_hg.json`; uji round-trip `P` → `corr_pts`.
4. **Hari 1–2:** ekstrak 3 frame per kamera; jalankan GeoCalib.
5. **Hari 2–3:** hitung $\Delta f/f$ dan $\Delta\theta$; putuskan Gerbang 1.

Jika Gerbang 1 lulus, lanjut ke Fase 2. Jika tidak, berhenti dan revisi pendekatan kalibrasi — jangan menambah dokumen baru.

---

## Catatan Plan mode

Rencana ini belum dieksekusi. Tidak ada dataset yang diunduh, tidak ada skrip yang dijalankan, dan tidak ada berkas repo yang diubah. Untuk mulai, pindah ke Build mode dan kerjakan Fase 0.

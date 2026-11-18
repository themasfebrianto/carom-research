# Riset CAROM Air → CCTV

Kajian adaptasi metode CAROM Air (drone) untuk pengukuran dimensi kendaraan dari kamera CCTV statis, beserta kalibrasi pada rekaman nyata dan prosedur operasionalnya.

## Dokumen

| Berkas | Isi |
|---|---|
| `CATATAN-RISET-LENGKAP.md` | **Ringkasan master**: temuan penting, hasil riset, kesalahan/koreksi, kendala, pertanyaan terbuka |
| `RISET-CAROM-Air-untuk-CCTV.md` | Laporan riset utama: formulasi CAROM Air, analisis rezim geometri, derivasi formula pengukuran, anggaran galat, dan penilaian kelayakan |
| `KALIBRASI-CCTV-CAWANG-REV2.md` | Kalibrasi pada rekaman nyata (720p, jalan tol). **Dokumen kalibrasi yang berlaku** |
| `AUDIT-16-15-44.md` | Audit rekaman kedua (480×360 substream) — **tidak layak**, beserta analisis penyebabnya |
| `KALIBRASI-CCTV-CAWANG.md` | Revisi 1 kalibrasi. **Digantikan** — angka $f$, $h$, $w$ di dalamnya tidak sahih |
| `SOP-KALIBRASI-CCTV.md` | Prosedur operasional kalibrasi, berlaku umum untuk CCTV mana pun |
| `SOP-PENGUKURAN-DIMENSI-KENDARAAN.md` | Prosedur operasional pengukuran dimensi kendaraan |
| `PAPER-REPO-Untuk-Menutup-Kelemahan.md` | Peta paper/repo untuk menutup kelemahan: ground truth I24-3D/SVLD-3D, pipeline SKoPe3D/OpenPifPaf/GSNet, kalibrasi naver/cctv, skala MoGe-2 |
| `VALIDASI-PROTOCOL.md` | Protokol dan ambang validasi eksternal |
| `HASIL-VALIDASI-SVLD.md` | Sintesis validasi SVLD-3D: kalibrasi, geometri, sensitivitas, keypoint, mask; putusan W/H vs L |
| `HASIL-TIMEPASS-CAWANG.md` | Side-view/lower-envelope di Cawang: truk 40 ft 14,0–14,3 m; batch 6 kendaraan 6,4–17,4 m; proof of concept |

## Temuan pokok

1. **Anisotropi galat** — $\sigma_{\text{kedalaman}}/\sigma_{\text{lateral}} = z/h$, tidak bergantung pada focal length maupun resolusi.
2. **Degenerasi kalibrasi** — dari marka jalan saja, $f$, $h$, dan lebar lajur $w$ tidak teridentifikasi terpisah. Yang terukur hanya $f\theta$, $fh$, $fw$, dan $w/h$. Diperlukan satu anchor metrik.
3. **Batas pengukuran** — lebar dan tinggi layak pada 18–30 m; panjang tidak layak bila sumbu optik sejajar jalan.

## Perkakas utama

| Perkakas | Fungsi |
|---|---|
| **GeoCalib** (Veicht dkk., ECCV 2024) | focal length dan arah gravitasi dari satu citra — memutus degenerasi $f$–$h$ |
| `ffmpeg` / `ffprobe` | inspeksi, ekstraksi frame, median temporal (`tmedian`) |
| Node.js / Python | deteksi marka, fitting, analisis |

GeoCalib adalah alat kalibrasi utama: ia memberi $f$ dan pitch, lalu vanishing point memberi yaw, dan satu anchor metrik (tinggi kamera atau lebar lajur) menyelesaikan skalanya. Detail dan gerbang validasinya ada di `SOP-KALIBRASI-CCTV.md` §0.3.

## Skrip

Skrip teori memakai Node.js dan `ffmpeg`. Validasi eksternal memakai Python; lihat `scripts/README.md` untuk environment dan urutan pakai.

### Validasi eksternal

| Berkas | Fungsi |
|---|---|
| `scripts/i24_parse.py` | Parse `sceneX_hg.json` I24-3D; uji self-test 3×4/4×3 |
| `scripts/i24_frames.py` | Ekstrak frame dari video |
| `scripts/geocalib_batch.py` | Batch GeoCalib |
| `scripts/eval_i24_calib.py` | Bandingkan GeoCalib dengan ground truth |
| `scripts/parse_svld.py` | Inventaris SVLD-3D |
| `scripts/svld_reproj_check.py` | Verifikasi kalibrasi SVLD via reproyeksi |
| `scripts/svld_fit_dims.py` | Fit 3D box dan ukur $L/W/H$ |
| `scripts/svld_sensitivity.py` | Sensitivitas noise 2D |
| `scripts/svld_subsets.py` | Uji subset sudut |
| `scripts/svld_kp_detectability.py` | Detectability keypoint pada SVLD |
| `scripts/svld_mask_fit.py` | Fitting 3D box ke mask YOLO-seg |
| `scripts/cawang_timepass.py` | Side-view/time-of-passage di Cawang |
| `scripts/grounded_sam2_container.py` | Grounding DINO + SAM 2: segmentasi kontainer-only |
| `scripts/cawang_container_fit.py` | Fit 3D box ke mask kontainer-only |

### Verifikasi teori

| Berkas | Fungsi |
|---|---|
| `verify_geometry.mjs` | Verifikasi numerik proyeksi, kalibrasi VP, rekonstruksi, dan Jacobian |
| `worked_example.mjs` | Contoh numerik lengkap (laporan riset §8) |
| `sensitivity_check.mjs` | Sensitivitas per sumbu |
| `degeneracy.mjs` | Uji degenerasi 1-parameter |
| `check_claims.mjs` | Verifikasi klaim angka |

### Pipeline kalibrasi

| Berkas | Fungsi |
|---|---|
| `vpfit.mjs` | Estimasi vanishing point dari orientasi dash |
| `scan.mjs` | Penyapuan profil luma sepanjang garis lajur |
| `dash3.mjs` | Ekstraksi dash dengan tepi sub-piksel (final) |
| `calib3.mjs` | Fitting model kamera + kovarians (final) |
| `anchor.mjs` | Fitting dengan lebar lajur dipaku |
| `annotate.mjs` | Utilitas overlay validasi |

Berkas `marks.mjs`, `blobs.mjs`, `dashes.mjs`, `dash2.mjs`, `lines.mjs`, `lines2.mjs`, `calib.mjs`, `calib2.mjs`, `sens.mjs`, dan `measure.mjs` adalah iterasi yang mendahului versi final — disimpan sebagai catatan proses.

## Artefak

| Berkas | Isi |
|---|---|
| `frames/median.png` | Latar median-temporal (rata-rata, revisi 1) |
| `frames/median2.png` | Latar median-temporal sejati (revisi 2) |
| `frames/ann2.png` | Overlay validasi: garis lajur dan pusat dash prediksi |
| `frames/truck2.png` | Crop objek acuan dengan grid |
| `frames/*.json` | Hasil deteksi dan parameter |

## Catatan

Berkas video sumber (`recording cawang.mp4`, 179 MB) **tidak** disertakan dalam repositori. Ukurannya melampaui batas praktis git, dan rekaman berisi citra lalu lintas yang dapat diidentifikasi.

Seluruh angka dapat direproduksi dari video tersebut dengan perintah pada lampiran `KALIBRASI-CCTV-CAWANG-REV2.md`.

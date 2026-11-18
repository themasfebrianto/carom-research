# Uji Mini GeoCalib pada SVLD-3D

Kalibrasi SVLD diverifikasi dengan reproyeksi 8.142 objek: median RMS **0,74 px**, persentil 90 **0,85 px**, maksimum **1,08 px**, dan **0 objek >2 px**. Jadi ground truth kalibrasi SVLD konsisten dengan anotasi 3D-nya.

Perbandingan GeoCalib dengan kalibrasi SVLD (satu citra per scene):

| Scene | f GT (px) | f GeoCalib (px) | Δf/f | pitch GT | pitch GeoCalib | Δpitch | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| 0cam (1280×720) | 3743,8 | 1836,4 | 51,0% | 6,43° | 9,84° | 3,41° | GAGAL |
| 1cam (1280×720) | 1142,3 | 1023,5 | 10,4% | 19,12° | 14,18° | 4,94° | GAGAL |
| session0_centre (1920×1080) | 2878,1 | 2816,6 | 2,1% | 10,24° | 8,78° | 1,46° | **LULUS** |
| session0_right (1920×1080) | 3994,2 | 3348,8 | 16,2% | 9,01° | 9,82° | 0,81° | GAGAL (f) |
| session6_right (1920×1080) | 3384,3 | 2420,9 | 28,5% | 15,07° | 20,06° | 4,99° | GAGAL |

**Lulus: 1/5.** Gerbang 80% tidak terpenuhi.

## Kesimpulan

- Kalibrasi SVLD **dapat dipercaya**: reproyeksi 8.142 objek konsisten di bawah 1,1 px.
- GeoCalib **tidak dapat dipercaya** pada 4 dari 5 scene ini: f meleset 10–51%, pitch meleset 0,8–5,0°.
- Ini bukan kegagalan dataset. Ini domain gap GeoCalib pada scene jalan dengan banyak vegetasi, sedikit bangunan, dan kamera yang sangat miring.
- Gerbang validasi silang SOP §0.3.2 bekerja: jangan memakai f GeoCalib tanpa cek VP/reproyeksi.

## Implikasi

Untuk SVLD-3D, pakai kalibrasi XML sebagai ground truth, bukan GeoCalib. Untuk I24-3D, uji GeoCalib terhadap `P` tetap perlu; hasil SVLD ini menunjukkan bahwa gerbang 2° bisa gagal pada scene nyata dan harus diperiksa per kamera.

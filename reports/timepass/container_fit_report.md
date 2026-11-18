# Container-Only Fit — Hasil Negatif

## Tujuan

Memakai standar kontainer ISO sebagai ground truth: 40 ft = 12,192 m; 20 ft = 6,058 m; lebar 2,438 m; tinggi 2,591 m (standar) atau 2,896 m (high cube).

## Metode

- Frame Cawang t=86,0 s; truk SINKOR 40 ft.
- Mask kontainer dari threshold warna biru (HSV), komponen terbesar.
- Fit 3D box ke mask dengan tinggi kontainer **dipaku** 2,591 m.
- Parameter bebas: $X,Y,Z_0$, yaw, $L,W$.
- Objektif: IoU siluet box vs mask; differential evolution.

## Hasil

| Parameter | Hasil fit | Standar 40 ft | Galat |
|---|---:|---:|---:|
| Panjang $L$ | **13,81 m** | 12,192 m | **+13,3%** |
| Lebar $W$ | 2,69 m | 2,438 m | +10,4% |
| Tinggi $H$ | 2,591 m (dipaku) | 2,591 m | 0% |
| $Z_0$ (alas kontainer) | 1,58 m | ±1,1 m | mentok batas atas |
| IoU | 0,816 | — | — |

## Mengapa gagal

1. **Mask parsial.** Threshold warna mengambil sisi kontainer, tetapi tepi depan/dekat kabin dan sebagian tepi atas/bawah tidak lengkap. Mask bukan siluet kontainer penuh.
2. **Ambiguitas skala.** Dengan $H$ dipaku, optimizer masih bisa menukar $Z_0$, $L$, dan $W$ untuk mencocokkan mask. $Z_0$ mentok di batas atas (1,6 m), tanda solusi tidak terkendala.
3. **Kontainer dilihat miring.** Tepi atas/bawah tidak sejajar; pendekatan sumbu vertikal sederhana juga gagal (residual besar).
4. **Kontainer di atas sasis.** Alas kontainer tidak di tanah; back-projection ground langsung tidak berlaku.

## Kesimpulan

Standar kontainer **sah sebagai ground truth**, tetapi pipeline container-only saat ini **belum akurat**. Galat +13% terlalu besar untuk validasi.

Untuk memakai standar ini, diperlukan salah satu:

- anotasi manual 4 sudut kontainer (depan/belakang × atas/bawah), lalu solve 3D;
- model segmentasi yang lebih baik (SAM 2) untuk siluet kontainer penuh;
- data GT side-view (I24-3D satu kamera) atau pengukuran lapangan.

Sampai itu tersedia, hasil whole-truck 14,0–14,3 m hanya **konsisten** dengan 40 ft + kabin ~1,8–2,1 m; bukan bukti akurasi kontainer.

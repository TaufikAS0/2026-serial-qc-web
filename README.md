# Compact Serial QC Web

Aplikasi web lokal di laptop Windows untuk QC RS232/RS485 Compact QC Tester dan fixture slave Modbus RTU.

**Status: handoff dokumentasi saja. Aplikasi belum diimplementasikan atau diuji dalam repository ini.**

## Mulai untuk AI berikutnya

1. Baca [AGENTS.md](AGENTS.md).
2. Jalankan instruksi lengkap [IMPLEMENTATION_PROMPT.md](04_Dokumen/IMPLEMENTATION_PROMPT.md).
3. Perbarui [STATUS.md](04_Dokumen/STATUS.md) setelah tiap checkpoint.

Repository ini sengaja dipisahkan dari firmware. Audit dan reuse penguji laptop yang sudah ada di repository firmware sebelum menulis ulang.

## Referensi firmware

- Repository: https://github.com/TaufikAS0/compact-qc-tester-v2-r1
- Branch: `feature/qc-operator-ota`.
- Source baseline v1.5.0: [`fa0624ea3d979f2a87ff3db118a46c4ad6ca0387`](https://github.com/TaufikAS0/compact-qc-tester-v2-r1/tree/fa0624ea3d979f2a87ff3db118a46c4ad6ca0387).
- Checkpoint dokumentasi: `7481e0af5b6721083e6701bb8cf311ec0137ec9d`.
- Cari `tools/laptop-qc/`, `Start-Laptop-QC.ps1`, source serial QC/Modbus, dan `04_Dokumen/QC_OPERATOR_GUIDE.md` pada referensi tersebut.

## Penggunaan yang dituju

Launcher Windows membuka web lokal, default `http://127.0.0.1:8770`. Teknisi memilih COM dan mode, menjalankan tes, melihat PASS/FAIL, serta mengekspor CSV/JSON. Port 8769 pada pekerjaan sebelumnya adalah preview dashboard ESP, bukan aplikasi penguji ini.

Perintah install/run akan ditambahkan oleh AI implementor setelah aplikasi tersedia. Belum ada launcher dalam repository ini.

## Git

Bootstrap dokumentasi berada di `develop` sebagai default branch. Implementasi berikutnya memakai `feature/<nama>` dari `develop`, lalu PR ke `develop`. `main` dicadangkan untuk release yang disetujui; belum dibuat karena belum ada release aplikasi.

## Batas publikasi

Hanya spesifikasi dan handoff yang dipublikasikan. Jangan commit token, password privat, konfigurasi mesin, log produksi, atau hasil QC perangkat nyata. Tidak ada firmware yang diupload dalam bootstrap ini.

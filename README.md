# Serial Protocol Test Web

Web lokal Windows untuk mengirim, menerima, memantau, dan menguji data protokol melalui adapter USB–RS232 atau USB–RS485 pada berbagai perangkat.

**Status: spesifikasi/handoff saja; aplikasi dan layanan startup belum diimplementasikan.**

AI berikutnya wajib membaca [AGENTS.md](AGENTS.md), [prompt implementasi lengkap](04_Dokumen/IMPLEMENTATION_PROMPT.md), dan [checkpoint](04_Dokumen/STATUS.md), lalu mengerjakan implementasi di laptop pengguna.

## Cakupan

- Terminal ASCII/HEX, kirim manual dan periodik, log TX/RX.
- Modbus RTU master dan simulator slave, alamat/data configurable.
- Skenario request/response configurable dengan hasil PASS/FAIL berdasarkan aturan eksplisit.
- Profil perangkat, riwayat, export CSV/JSON.
- Backend lokal aktif di background, startup otomatis setelah login Windows, restart setelah crash, dan kontrol start/stop/status.

Default URL yang dituju: http://127.0.0.1:8770. Menutup tab tidak menghentikan backend. Laptop harus menyala dan tidak sleep untuk komunikasi terus berjalan; aplikasi tidak menjanjikan layanan saat shutdown/sleep.

RS232/RS485 adalah antarmuka listrik, bukan protokol pesan universal. COM terbuka atau data masuk bukan otomatis PASS. Compact QC hanya integrasi opsional; aplikasi inti tidak bergantung pada ESP, GPIO, IP, atau firmware tertentu.

## Git dan lanjutan pekerjaan

Repository publik: https://github.com/TaufikAS0/2026-serial-qc-web

Revisi cakupan berada di `feature/general-serial-protocol-handoff`, diajukan melalui PR ke `develop`. AI berikutnya harus memakai revisi ini; sebelum PR digabung, jangan memakai prompt lama pada develop sebagai scope aktif. Implementasi berikutnya melalui feature branch dan PR; tidak merge otomatis. Belum ada release/main produksi.

Nama sebelumnya `2026-compact-serial-qc-web` telah diganti; sejarah Git dipertahankan. Folder lokal mengikuti slug baru.

Perintah setup/run ditambahkan ketika implementasi tersedia. Tidak ada source aplikasi yang disalin atau firmware yang diupload pada handoff ini.

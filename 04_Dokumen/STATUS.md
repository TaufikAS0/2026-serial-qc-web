# Checkpoint — 14 Oktober 2026, Asia/Jakarta

## Lanjutan: akses LAN eksplisit

User meminta pola portal/ESP scanner untuk akses laptop lain. Ditambahkan enable-lan/disable-lan opt-in dan konfigurasi network di data per-user, bind IPv4 dengan guard exact Host/Origin dan client subnet RFC1918. COM tetap laptop server; owner tunggal. Layanan Windows hanya dikelola localhost. HTTP port aplikasi terpisah dari portal HTTPS 8443, tanpa perubahan portal/power/firmware. Firewall helper hanya membuka TCP app port/address/subnet; memerlukan UAC admin.

Verifikasi: 49 automated tests PASS (4.216s), termasuk 6 LAN tests (private subnet, Host/Origin, remote Windows-management denial, config persistence dan mock control); delapan lifecycle checks PASS. Browser nyata pada alamat LAN Connect MOCK + scenario Modbus PASS SIMULASI. Restart backend tetap HTTP health OK melalui LAN, connected=false/owner=null tanpa auto-send. Rule firewall aplikasi dibuat setelah persetujuan UAC dan Enabled=true, scoped ke IPv4 server/subnet lokal/TCP port aplikasi; konfigurasi mesin tetap di data per-user, tidak Git. Autostart tetap terpasang. Akses dari laptop kedua belum dibuktikan sampai user mencoba.

## Baseline

PR #1 OPEN; develop `2b0ea2a`. Implementasi dari spesifikasi `f7b811a50ee1a6323f95d9865bab580af71856d8`, branch `feature/serial-protocol-web`; PR ke develop bergantung spesifikasi #1. Tidak merge otomatis. Scope generik tanpa ESP/IP/Compact. Tidak membuka COM, mengirim payload hardware, upload firmware atau mengubah power policy.

## Tahap 1 selesai — core

Transport pyserial/COM/settings/reader/satu owner; terminal ASCII/HEX/manual/periodik/bounded log; Modbus FC01..04 master/slave/CRC/exception/types/endian/tag polling; profile v1/framing/assertions/repeats/timeout/PASS gate/cancellation; SQLite/preferences/history/recovery/CSV formula mitigation/JSON/retention. Tes awal 36 PASS; hardware PENDING.

## Tahap 2 selesai — UI dan lifecycle

Tujuh panel UI Indonesia, hasil/progress/error/owner/Stop; profil/preset import/export; JSON bukan tampilan utama. Flask/Waitress loopback dengan Host/Origin/token/CSP. Pythonw supervisor, HKCU Run per-user, Start/Stop/Restart/Status/Open, install/disable/uninstall, backoff 2..60s, rotated logs, instance locks.

Browser nyata: Connect MOCK; ASCII PING/PONG; HEX 00 FF 41; periodik/Stop; tag decoded 100; Start/Stop slave; scenario PASS dan CRC FAIL. Screenshot SIMULASI tersedia. Lifecycle isolated Windows: crash backend → recovery/disconnected/zero TX; run INCOMPLETE; double start same supervisor; backend duplicate blocked; restart/stop idempotent; start kembali tanpa auto-send. Delapan checks PASS.

Autostart install dua kali/uninstall dua kali/reinstall diverifikasi. Installed Run registry command dijalankan dari working directory berbeda → health OK. **Backend aktif dan autostart benar-benar terpasang pada laptop ini.** Login/reboot fisik tidak dilakukan; trigger nyata PENDING.

## Tahap 3 — hardening

Guard resume sebelum send mencegah worker mendahului reader saat wake. Simulated resume/unplug/busy diuji; CRC FAIL menyimpan RX/latency. Settings/tags/maps disimpan tanpa auto-open COM. Buffer/detail/history/DB/log dibatasi. 41 tests PASS sebelum perubahan terakhir schema/mock inject; final regression berikutnya.

Soak MOCK 120.0s: 12636 TX bytes dan RX sama; 1000 event cap; 3954 dropped; RSS 19,886,080 → 20,959,232 bytes; sampled peak sebelum final 20,590,592; temporary storage 94,576 bytes. Detail soak-simulation.json. Bukan bukti 24/7 atau hardware. Runtime dependencies audit nol vulnerabilities diketahui saat audit; Flask 3.1.3/Werkzeug 3.1.9/pyserial 3.5/Waitress 3.0.2. Sample reports PASS/FAIL dibuat dari fixture sementara sintetis, tidak dari produksi.

## Fakta / inferensi / asumsi / unknown

- Fakta: tests/browser/lifecycle di atas dijalankan; backend/autostart terpasang; COM tidak dibuka.
- Inferensi: single owner/strict codec mengurangi konflik; seluruh interoperability belum dibuktikan.
- Asumsi: adapter auto-direction benar dan profil sesuai DUT; pilihan RS485 di UI tidak mengubah hardware.
- Unknown: karakteristik listrik/timing/adapter/DUT, efek DTR/RTS, hasil master eksternal, reboot/login dan wake fisik. Checklist HARDWARE.md.

## Verifikasi akhir dan langkah berikutnya

Final regression: **43 tests PASS** (3.925s), delapan lifecycle checks PASS, registry autostart activation/idempotence PASS, pip check PASS. Runtime dependency audit: nol vulnerabilities diketahui. Mock inject slave melalui browser menghasilkan request 01 03 00 00 00 01 84 0A dan response 01 03 02 00 64 B9 AF. Raw scenario PASS/Modbus CRC FAIL diperiksa dan screenshot disimpan; error menyimpan actual RX. Browser ditutup/dibuka: koneksi MOCK, counters dan run ID sama. Dua tab: owner periodic terlihat pada kedua tab, Run dinonaktifkan, Stop dari tab kedua berhasil.

Setup/launcher/source/profiles/wiring/reports/UI evidence/Windows lifecycle/CI workflow selesai. Implementasi dipublish pada commit `f3137c34269c4b237fbede3ed0d81b94a8e481ac`; local HEAD, origin tracking dan ls-remote cocok, worktree bersih saat verifikasi. [PR #2](https://github.com/TaufikAS0/2026-serial-qc-web/pull/2) OPEN ke develop, 43 changed files termasuk baseline spesifikasi PR #1; tidak merge. Identitas author memakai noreply yang terverifikasi dan sama dengan baseline, tanpa mengubah Git global.

Hardware acceptance membutuhkan pemilihan adapter/DUT eksplisit; tidak menjalankan payload hardware. Compact belum diintegrasikan karena opsional. Autostart login/reboot fisik dan sleep/wake fisik tetap PENDING. Jangan menyatakan software PASS sebagai hardware acceptance. Backend tetap aktif, autostart terpasang; tidak ada periodic/poll/slave aktif setelah pemeriksaan browser.

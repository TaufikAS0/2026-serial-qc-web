# Prompt implementasi — aplikasi web penguji protokol serial umum

Kerjakan aplikasi web lokal yang terus tersedia di laptop Windows untuk menguji data protokol melalui USB–RS232 dan USB–RS485. Ini aplikasi umum untuk berbagai perangkat. Selesaikan implementasi, launcher, startup, tests, dan panduan; jangan berhenti pada mockup.

## 1. Scope dan fakta

Repository: https://github.com/TaufikAS0/2026-serial-qc-web
Baca README, AGENTS, STATUS. Prompt ini menggantikan scope lama yang khusus Compact QC.

RS232 dan RS485 adalah antarmuka listrik; format aplikasi bisa ASCII, binary custom, atau Modbus RTU. Jangan menciptakan satu paket universal lalu menganggap semua perangkat harus merespons. Tidak diperlukan ESP32, Wi-Fi, alamat IP device, atau protokol Compact untuk menjalankan fitur inti.

Handoff saat ini hanya dokumen. AI implementor mengerjakan source di laptop pengguna. Jangan mengklaim aplikasi telah berjalan dari status repository dokumen ini.

## 2. Arsitektur yang dituju

Backend lokal Python dengan pyserial dan frontend served same-origin adalah baseline sederhana. Boleh memilih framework ringan yang terpelihara setelah verifikasi dokumentasi resmi; jelaskan alasan bila mengganti stack. Browser tidak harus mengakses Web Serial karena backend mengelola COM.

Pisahkan transport/port manager, codec/parsers, protocol adapters, test runner, persistence/export, API, frontend, dan background-service management. Jangan duplikasi protokol di frontend. Dependensi dikunci, asset frontend lokal, dapat dipakai tanpa internet setelah setup.

Bind 127.0.0.1 secara default, port 8770 configurable. Tangani collision port tanpa menghentikan aplikasi lain. Tidak expose LAN secara otomatis. Validasi origin/host dan lindungi API mutasi dari request lintas origin. Single instance per konfigurasi layanan.

## 3. Selalu aktif di laptop

Sediakan installer/startup per-user Windows melalui Scheduled Task saat login atau mekanisme setara yang terdokumentasi. Default tidak memerlukan administrator. Jika operasi sebelum login diminta kelak, dokumentasikan opsi Windows Service terpisah.

Backend berjalan background tanpa terminal mengganggu, startup idempotent, automatic restart dengan bounded backoff saat crash, health endpoint dan log rotasi. Sediakan start, stop, restart, status, disable-autostart, uninstall-autostart, dan Open Web. Uninstall tidak menghapus hasil pengguna tanpa instruksi.

Menutup browser tidak mematikan backend. Membuka ulang browser menampilkan state backend yang sama. Browser tidak otomatis dibuka pada setiap restart layanan; hanya saat pengguna memilih Open Web.

Laptop sleep/shutdown menghentikan komunikasi. Jangan menjanjikan always-on selama itu, dan jangan mengubah power settings diam-diam. Setelah wake/restart, refresh port dan tandai run terputus INCOMPLETE. Jangan melanjutkan pengiriman command atau mengulang write otomatis. Backend tersedia bukan berarti port selalu dikuasai; port dibuka saat pengguna Connect dan dilepas saat Disconnect/cleanup.

## 4. Koneksi dan serial transport

Daftar COM dengan deskripsi/USB identity bila tersedia, Refresh, Connect/Disconnect, RS232/RS485 sebagai label fixture, baud, data bits, parity, stop bits, flow control. Default 9600/8N1/no flow control; jelaskan itu preset, bukan standar universal.

Pilihan mode di web tidak mengubah hardware adapter RS232 menjadi RS485. Teknisi memakai adapter sesuai jalur. Arah RS485 otomatis sebagai default umum; jika adapter butuh RTS direction control, tampilkan opsi hanya bila backend/adapter mendukung. Validasi settings sebelum membuka port.

Satu owner per port; terminal, test runner, Modbus master dan slave tidak boleh rebutan port. Bedakan status backend, port, dan test. Tangani port busy/hilang/berubah, USB unplug, izin, invalid setting, reconnect. Tidak memilih COM lain secara diam-diam setelah reconnect.

Wiring guide: RS232 TX ke RX, RX ke TX dan signal ground, bukan USB–TTL. RS485 sesuai polaritas datasheet, ground/terminasi/bias menurut topologi. Jangan mengarang nomor DB9 atau menyamakan label A/B seluruh vendor.

## 5. Terminal raw ASCII/HEX

Kirim manual, display ASCII/HEX, line ending none/CR/LF/CRLF, explicit encoding, validasi HEX, timestamp TX/RX, counter bytes, clear tampilan dan save log. Data tetap berupa bytes; display decode tidak boleh mengubah payload.

Kirim periodik configurable dengan Start/Stop eksplisit dan batas laju. Pisahkan TX/RX, tampilkan payload hex untuk binary. Membekukan scroll tidak menghentikan capture. Buffer tampilan dan queue harus bounded, laporkan dropped/truncated logs.

Tidak ada PASS otomatis pada terminal hanya karena data diterima. Terminal harus bisa digunakan tanpa test profile dan tanpa HTTP ke device.

## 6. Modbus RTU master

Laptop sebagai master untuk request ke slave eksternal. Sediakan FC01,02,03,04; slave ID 1..247 untuk read, alamat zero-based, count sesuai batas protokol dan UI, baud/parity/timeout/poll interval.

Daftar tag dinamis, bukan wajib dua: name, function, slave, address, length, data type, byte/word order, scale/offset bila diperlukan. Preset dua tag boleh tersedia. Unsigned/signed 16/32-bit, float32, coils/discrete bits; validasi count/encoding. Tampilkan raw registers dan decoded values.

Tampilkan request/response hex, CRC/exception/timeout, latency, age/stale data. Polling hanya satu request outstanding pada port. Dokumentasikan konversi notasi 40001 bila disediakan; source of truth tetap offset protokol.

Write FC05/06/15/16 boleh tahap lanjutan, bukan kebutuhan minimum. Bila ditambahkan harus aksi eksplisit, tidak auto polling/auto retry write yang outcome-nya ambigu.

## 7. Modbus RTU slave/server simulator

Laptop menjadi slave ketika perangkat eksternal master. Sediakan unit ID, maps coils/discrete inputs/holding/input registers, editable values dan presets import/export. Dukung read FC01..04 dan exception untuk alamat/function/count invalid sesuai spesifikasi.

Log request masuk/response dan decode. Nilai simulator sintetis tidak berarti transport-nya mock: tandai jelas REAL SERIAL + SYNTHETIC VALUES. Response terkirim bukan bukti master mengolahnya benar; pengujian end-to-end memerlukan hasil master atau konfirmasi user bila profil menyatakannya.

Jangan mengaktifkan master dan slave bersamaan pada port yang sama. Jangan mengaktifkan dua master pada satu bus tanpa skenario protokol yang memang mendukungnya.

## 8. Skenario pengujian configurable

Profil JSON tervalidasi/schema versioned: nama/protokol, serial settings, langkah TX ASCII/HEX atau Modbus read, expected response, timeout, repeats, inter-step interval, optional framing/delimiter/length sesuai protokol.

Minimum assertions: exact bytes, prefix/contains, length, serta nilai register dalam range/tolerance. CRC Modbus built-in; checksum custom hanya jika definisi lengkap tersedia. Jangan mengasumsikan checksum semua perangkat sama. Jika regex ditambahkan, batasi biaya/ukuran; jangan mengeksekusi script arbitrary dari profile.

Sediakan contoh profil raw request/response dengan responder simulator dan contoh Modbus read. Jelaskan DUT harus mendukung pesan profil. Jangan kirim payload demo secara otomatis ke device tak dikenal.

Loopback adalah skenario opsional adapter/kabel; beri label bahwa itu bukan bukti komunikasi DUT. Mode full-device harus memvalidasi respons sesuai kontrak dan menghindari local echo menjadi false PASS. Session/sequence ID hanya disisipkan jika protokol DUT mendukung, bukan dipaksakan pada raw protocol.

## 9. Kriteria dan tampilan hasil

Status BELUM DIUJI, BERJALAN, PASS, FAIL, ERROR SETUP, INCOMPLETE/DIBATALKAN. PASS hanya semua langkah/assertions wajib selesai valid. Stop/disconnect/restart tidak PASS. ERROR SETUP sebelum test tidak membuktikan hardware rusak.

Timeout/mismatch/CRC/exception dicatat dengan sebab. Retry terlihat dan tidak menghapus kegagalan; default QC nol error. Jika profil toleransi retry berbeda, simpan kebijakan itu dalam report. Jangan menyebut FAIL sebagai diagnosis komponen pasti tanpa bukti.

UI Bahasa Indonesia: Koneksi, Terminal, Modbus Master, Modbus Slave, Skenario QC, Riwayat, Pengaturan Layanan. Besarkan PASS/FAIL berwarna plus teks/ikon di panel aktif. Tampilkan progress, target/valid/error, elapsed, latency bila tersedia, alasan dan log rinci. Raw JSON bukan tampilan utama.

Disable config berbahaya selama run, Stop tetap tersedia, run ID unik, double-click/two tabs tidak membuat run ganda. Identitas device opsional/manual atau protocol-specific; tampilkan unknown jika tidak tersedia, jangan menuntut MAC ESP.

## 10. Persistensi dan export

Simpan profil, preferensi nonsecret, dan riwayat lokal di lokasi data per-user yang portable/configurable; repository bukan tempat log produksi. SQLite atau pilihan ringan lain dengan bounded retention/rotating logs. Simpan progress agar run terputus dapat direkonsiliasi sebagai INCOMPLETE.

Export CSV Excel UTF-8 dan JSON: run/profile version, waktu/zona, app version, identity jika ada, serial settings, mode/protokol, fixture REAL/MOCK/LOOPBACK, langkah/target/actual, raw data sesuai batas, duration/error/retry, status/alasan/catatan. CSV escaping dan formula injection ditangani. Jangan export secrets. Retention dan penghapusan data transparan.

## 11. Ketahanan dan pengujian

Tangani serial partial/combined frames, idle gaps/framing, noise, stale buffers, local echo, malformed responses, timeout, cancel, unplug, port busy, two tabs, crash, restart, resume sleep, invalid JSON profiles, log growth dan backend shutdown.

Test parser dengan golden vectors dari spesifikasi resmi/protokol yang dinyatakan. Test Modbus CRC, exception, address/count limits, endian, raw bytes, ownership, double start, assertions/PASS gate, cancellation, persistence recovery/export, UI bindings/API, installer idempotence/uninstall/autostart recovery. Verifikasi browser nyata dan laporkan batas hardware yang belum tersedia.

Simulasi transport diberi label SIMULASI dan tidak boleh masuk report sebagai REAL hardware PASS. Sertakan soak test terukur beserta durasi/memori/log, jangan mengklaim stabil terus-menerus dari test singkat.

## 12. Integrasi opsional Compact QC

Hanya setelah fitur generik: adapter profil terpisah untuk https://github.com/TaufikAS0/compact-qc-tester-v2-r1, baseline v1.5.0 commit fa0624ea3d979f2a87ff3db118a46c4ad6ca0387, branch feature/qc-operator-ota.

Cari tools/laptop-qc/, launcher dan serial protocol source, dokumentasikan frame/API sebenarnya dan reuse setelah audit lisensi/provenance. IP ESP, endpoint arm/heartbeat, GPIO4/5 dan selector MCP2A2 hanya milik profil tersebut. Core umum harus berjalan meski profil Compact tidak diinstall dan firmware reference tidak di-clone. Tidak ada kebutuhan upload firmware untuk menyelesaikan aplikasi generik.

## 13. Deliverable dan acceptance

Berikan source runnable, setup dependency reproducible, launcher/startup install/uninstall/status, README, wiring, schema/protocol docs, sample profiles, tests/results, screenshots UI, sample reports SIMULASI, checklist hardware dan STATUS checkpoint.

Acceptance inti: aplikasi membuka localhost tanpa ESP; port bisa dipilih; raw ASCII/HEX bekerja pada fixture; Modbus master dan slave bekerja sesuai peran; skenario PASS/FAIL mengikuti assertions; browser bisa ditutup/dibuka tanpa kehilangan state; service autostart/recovery diuji; tidak auto-send setelah reboot; export/history benar.

Audit repo/aturan terlebih dahulu, kerjakan feature branch dan PR tanpa merge otomatis. Jangan upload firmware. Jika hardware tidak tersedia, selesaikan source/tests dan dokumentasikan acceptance yang pending. Mulai dengan gap/arsitektur singkat lalu langsung implementasikan; update checkpoint tiap tahap supaya pekerjaan dapat dilanjutkan AI lain.

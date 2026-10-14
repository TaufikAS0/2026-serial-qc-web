# Serial Protocol Test Web

Workbench serial Windows: terminal ASCII/HEX, Modbus RTU master/slave FC01..04, profil request/response dengan assertions, riwayat CSV Excel/JSON. UI Bahasa Indonesia, backend lokal tanpa ESP/IP/firmware tertentu. **http://127.0.0.1:8770**.

**Software tersedia; acceptance hardware PENDING.** PASS berarti aturan profil terpenuhi; MOCK selalu SIMULASI. [Checkpoint/tests](04_Dokumen/STATUS.md), [format profil](04_Dokumen/PROFILES.md), [wiring/hardware](04_Dokumen/HARDWARE.md).

## Setup dan launcher

Python 3.11 diperlukan. Double-click **Setup.cmd**: buat `.venv`, install dependensi terkunci dari PyPI, install autostart per-user saat login, start backend background. Internet diperlukan hanya untuk setup. Asset UI lokal tanpa CDN; runtime offline. Untuk offline install, download wheels `python -m pip download -r requirements.txt -d wheels`, lalu install `--no-index --find-links wheels`.

Double-click **Serial Web.cmd** untuk Start + Open Web. Menutup browser tidak menghentikan backend. CLI dari folder checkout:

```bat
"Serial Web.cmd" start
"Serial Web.cmd" stop
"Serial Web.cmd" restart
"Serial Web.cmd" status
"Serial Web.cmd" open
"Serial Web.cmd" install-autostart
"Serial Web.cmd" disable-autostart
"Serial Web.cmd" uninstall-autostart
```

Install/uninstall idempotent, tidak perlu admin. Uninstall autostart tidak menghapus hasil atau menghentikan backend; Stop terpisah. HKCU Run menjalankan pythonw supervisor setelah login, bukan service sebelum login. Jangan memindahkan checkout/venv tanpa reinstall autostart.

Alternatif: `.venv\Scripts\python.exe launcher.py start --port 8771 --data "D:\SerialLabData"`. Pakai data/port yang sama pada semua kontrol dan install. `SERIALWEB_DATA` juga didukung. Satu autostart default per pengguna; instance lock per direktori data. Pengaturan Layanan menampilkan path data nyata.

## Mulai simulasi

1. Koneksi → SIMULASI → Connect; tidak membuka COM.
2. Terminal → ASCII PING, CRLF → Kirim sekali. Responder MOCK menjawab PONG CRLF; payload lain mock echo. Kirim HEX, periodik, Stop, freeze tampilan, save log tersedia. Terminal tidak memberi PASS.
3. Master → unit 1, FC03, alamat 0, count 1, uint16 → Baca sekali; nilai sintetis 100. Tag dinamis, endian/scale/offset, polling dan age/stale tersedia.
4. Skenario → demo Modbus/PING → Run. Normal PASS SIMULASI; corrupt/timeout/echo FAIL; Stop/disconnect INCOMPLETE. Semua assertions wajib; nol retry tersembunyi.
5. Slave → Start; Master sintetis → Inject request SIMULASI; RX/TX terlihat di Terminal. Import/export preset maps tersedia.
6. Riwayat → CSV Excel atau JSON. Profil JSON dapat diimport/export/edit dengan validator. [Contoh profil](examples/), [contoh PASS](examples/reports/simulation-pass.json), [contoh FAIL](examples/reports/simulation-fail.json).

## Hardware dan batas

### Akses dari laptop lain melalui LAN

LAN opsional diaktifkan secara eksplisit pada laptop server:

```bat
.venv\Scripts\python.exe launcher.py enable-lan --lan-host ALAMAT_IPV4_SERVER --lan-subnet CIDR_LAN
```

Contoh `--lan-host 192.168.1.122 --lan-subnet 192.168.1.0/24`; gunakan IP/subnet nyata laptop server. Buka `http://IP_SERVER:8770/` dari laptop lain pada jaringan yang sama. HTTP ini mengikuti pola ESP scanner; bukan HTTPS dan bukan port portal 8443. USB/COM tetap terpasang pada **laptop server**, bukan laptop client. Semua client berbagi state dan satu owner port; fitur Stop test tersedia dari LAN, pengelolaan layanan Windows hanya localhost. Perangkat pada subnet yang diizinkan dapat memakai aplikasi; tidak ada autentikasi pengguna pada mode LAN ini, jadi gunakan jaringan lab yang dipercaya.

Konfigurasi `network.json` disimpan di direktori data per-user, bukan Git; autostart/recovery memakainya. Double-click **Enable LAN Firewall.cmd** lalu setujui UAC untuk membuka firewall. Alternatif: helper `scripts/Set-LAN-Firewall.ps1` sebagai Administrator, parameter `-DataDirectory` sesuai Status; aturan terbatas TCP port aplikasi, IPv4 server dan subnet yang dipilih, tidak menonaktifkan firewall. Kategori jaringan Windows tidak diubah. Jika IP/subnet DHCP berubah, ulangi enable-lan dan helper firewall. `launcher.py disable-lan` mengembalikan backend ke loopback; helper `-Action Uninstall` menghapus aturan firewall aplikasi.

Pilih adapter/DUT dan COM secara eksplisit. COM terdeteksi bukan bukti jenis adapter atau DUT sehat. Gunakan [wiring/checklist](04_Dokumen/HARDWARE.md), settings dan kontrak payload datasheet. RS232/RS485 adalah antarmuka listrik, bukan protokol pesan universal. Demo tidak boleh dikirim ke DUT yang kontraknya tidak diketahui.

Master/slave/terminal/runner memakai satu owner, tidak dapat berebut port. Slave pada hardware berlabel **REAL SERIAL + SYNTHETIC VALUES**; respons TX belum membuktikan master eksternal mengolahnya. RS485 auto-direction baseline; RTS-only belum didukung. DTR/RTS dapat berubah saat driver membuka port.

Sleep/shutdown menghentikan komunikasi; power policy tidak diubah. Jeda sistem >5s menyebabkan disconnect/cancel, perlu Connect + Start manual. Setelah crash/reboot, run BERJALAN menjadi INCOMPLETE; tidak auto-open COM, polling, slave, atau periodik. Deteksi resume konservatif, bukan jaminan realtime; sleep/wake fisik masih PENDING.

## Arsitektur/operasi

Transport/ownership `engine.py`, codec `protocol.py`, validator `profiles.py`, SQLite/export `store.py`, Flask API `app.py`, Waitress/pythonw supervisor `lifecycle.py`, frontend lokal `static/`. Pilihan Python/pyserial + Waitress **8/10** untuk workbench lokal: sederhana dan driver Windows tersedia; batasnya jitter OS/USB, dependency Python, dan hardware interoperability belum dibuktikan. Tidak diklaim bersertifikasi Modbus. [Spesifikasi resmi](https://www.modbus.org/modbus-specifications), [pyserial API](https://pyserial.readthedocs.io/en/latest/pyserial_api.html).

Loopback-only, Host/Origin/token/CSP guards, tanpa CORS. Proses lain dengan akses akun Windows yang sama berada di luar batas keamanan ini. Collision port tidak mematikan aplikasi lain. Supervisor restart backend dengan backoff 2–60s; jika supervisornya dimatikan, Start/login diperlukan.

Data `%LOCALAPPDATA%\SerialProtocolTestWeb` (packaged Windows dapat memberi path virtual; lihat Status/UI), di luar repo. History max 200 run/64 MB, detail max 500 langkah/1 MB/run, SQLite ceiling 128 MiB, RX 8192 bytes, ring 1000 event × 4096 bytes. Logs backend/supervisor masing-masing 1 MB × 4 = 8 MB total. Truncation/dropped eksplisit; export sebelum retention. Hapus riwayat melalui aksi eksplisit UI.

## Verifikasi

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m tests.lifecycle_check
.venv\Scripts\python.exe -m tests.soak --seconds 120
.venv\Scripts\python.exe -m tests.sample_reports
```

Lifecycle test mengisolasi data/port 18770, tidak membuka COM, hanya mematikan backend child milik supervisor tes. `tests.autostart_check` melakukan Stop/Start layanan default untuk menguji registry command; jalankan tanpa run penting. [Screenshot](04_Dokumen/screenshots/simulasi-pass.png), [soak](04_Dokumen/soak-simulation.json), [audit dependencies](04_Dokumen/dependency-audit.json).

Baseline `f7b811a` dari spesifikasi PR #1 OPEN saat audit 14 Oktober 2026. Branch `feature/serial-protocol-web`, PR ke develop bergantung pada spesifikasi #1; tidak merge otomatis atau push main/develop. Tidak ada reuse/upload firmware Compact; integrasi tersebut opsional belum dilakukan.

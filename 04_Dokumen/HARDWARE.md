# Wiring dan acceptance hardware — PENDING

Belum membuka COM atau mengirim payload ke hardware selama implementasi; tidak flash firmware. COM discovery tidak membuktikan jenis adapter, wiring, atau DUT.

## Sebelum Connect

- Identifikasi adapter, driver, antarmuka listrik, DUT dan COM yang dipilih user. USB–TTL bukan USB–RS232.
- RS232: TX → RX, RX → TX, signal ground sesuai datasheet. Periksa null modem; nomor DB9 tidak universal.
- RS485: polaritas A/B sesuai datasheet kedua perangkat; nama vendor bisa berbeda. Common ground/reference, isolasi, bias dan terminasi sesuai topologi. Satu master aktif.
- Baud/bits/parity/stop/flow mengikuti DUT. Preset 9600/8N1 bukan standar universal. Auto-direction didukung baseline; RTS-only belum.
- Periksa efek DTR/RTS saat port dibuka. Driver dapat mengaktifkannya, menurut dokumentasi pyserial.
- Alamat/count/byte order/protokol mengikuti manual. Jangan kirim payload demo ke perangkat tak dikenal.

## Checklist acceptance

| Skenario | Bukti wajib | Status |
|---|---|---|
| RS232 ASCII/HEX DUT | adapter/settings/wiring + kontrak TX/RX | PENDING |
| RS485 auto-direction | polaritas/terminasi/bias + respons | PENDING |
| Loopback adapter/kabel | echo byte-for-byte; bukan DUT PASS | PENDING |
| Master FC01..04 | DUT nyata, CRC, addresses/counts, decoded values | PENDING |
| Slave FC01..04 | master eksternal membaca maps + bukti interpretasi master | PENDING |
| USB unplug / port busy | release port, error, run INCOMPLETE | PENDING |
| Sleep/wake fisik | INCOMPLETE, nol TX sesudah wake sampai Start manual | PENDING |
| Login/reboot fisik | hidden backend sehat, port terputus, nol TX | PENDING |
| Long soak hardware | RSS/disk/errors/latency dan durasi | PENDING |

Pilih REAL/COM manual setelah fixture dikenal; buat profil sesuai DUT; identity manual/unknown; simpan JSON/CSV dan notes wiring. Uji error terkontrol hanya jika aman. FAIL bukan diagnosis kerusakan komponen pasti. Hentikan run/Disconnect sebelum mengganti adapter/protokol. Prefix/length assertion saja biasanya tidak membuktikan seluruh fungsi DUT.

Software/mock PASS dan slave response TX tidak menggantikan acceptance ini. Windows/USB bukan timing deterministik; CRC/length diverifikasi, tetapi timing sub-ms dan inter-character memerlukan observasi hardware sebelum klaim kesesuaian penuh. [Serial guide resmi](https://www.modbus.org/file/secure/modbusoverserial.pdf), [pyserial API](https://pyserial.readthedocs.io/en/latest/pyserial_api.html).

Implementasi generik Serial Protocol Test Web mengganti repository handoff-only menjadi workbench lokal Windows: terminal ASCII/HEX, master/slave Modbus RTU FC01..04, profil/assertions, PASS/FAIL/INCOMPLETE, riwayat dan export CSV Excel/JSON. Satu backend owner mencegah terminal, polling, slave, runner dan tab lain berebut COM. MOCK ditandai SIMULASI; tidak auto-send setelah crash/restart/wake.

Launcher menyediakan hidden pythonw supervisor, per-user HKCU Run autostart, Start/Stop/Restart/Status/Open, install/uninstall idempotent, bounded recovery/logs/storage. UI same-origin loopback dan asset lokal. Format profil, wiring, sample simulation reports, hardware checklist dan checkpoint disertakan.

Validation: 43 automated tests PASS; eight isolated Windows lifecycle checks PASS (including forced backend crash, INCOMPLETE reconciliation and zero TX after recovery); autostart registry command activation/idempotence verified; real-browser ASCII/HEX, periodic Stop, master decoded values, slave mock injection, scenario PASS/CRC FAIL, browser reopen and two-tab ownership checked. 120-second MOCK soak records memory/log/disk metrics; runtime dependency audit found no known vulnerabilities. GitHub Actions Windows validation added.

Hardware tests were not performed and no COM was opened. Real login/reboot and physical sleep/wake remain pending; timing/interoperability is not claimed certified. RTS-only direction control and optional Compact integration are not implemented. See STATUS.md and HARDWARE.md for acceptance boundaries.

Depends on specification PR #1: this branch starts from f7b811a on feature/general-serial-protocol-handoff because #1 was OPEN at audit. Target develop; do not merge automatically. No firmware or Windows power changes.

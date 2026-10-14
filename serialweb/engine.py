import copy
import threading
import time
import uuid
from collections import deque
import serial
from serial.tools import list_ports
from . import VERSION
from .protocol import raw_bytes, request, response, decode, slave_response, checked
from .profiles import number, tag_valid, validate, assert_result
from .store import now


def ports():
    return [{'port': p.device, 'description': p.description, 'hwid': p.hwid, 'vid': p.vid, 'pid': p.pid, 'serial_number': p.serial_number} for p in list_ports.comports()]


def serial_config(config):
    result = dict(port=config.get('port', ''), baud=config.get('baud', 9600), bits=config.get('bits', 8), parity=config.get('parity', 'N'), stop=config.get('stop', 1), flow=config.get('flow', 'none'), fixture=config.get('fixture', 'MOCK'), interface=config.get('interface', 'RS232'))
    number(result['baud'], 300, 2000000, 'Baud', True)
    if result['bits'] not in (5, 6, 7, 8) or result['parity'] not in ('N', 'E', 'O', 'M', 'S') or result['stop'] not in (1, 1.5, 2) or result['flow'] not in ('none', 'rtscts', 'xonxoff', 'dsrdtr'):
        raise ValueError('Konfigurasi serial tidak valid')
    if result['fixture'] not in ('MOCK', 'REAL', 'LOOPBACK') or result['interface'] not in ('RS232', 'RS485'):
        raise ValueError('Fixture/interface tidak valid')
    if result['fixture'] != 'MOCK' and result['port'] not in [p['port'] for p in ports()]:
        raise ValueError('Pilih COM yang tersedia secara eksplisit')
    return result


class Engine:
    def __init__(self, store):
        self.store = store
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.handle = None
        self.connected = False
        self.config = {}
        self.owner = None
        self.cancel = threading.Event()
        self.reader_stop = threading.Event()
        self.events = deque(maxlen=1000)
        self.sequence = 0
        self.dropped = 0
        self.tx_count = self.rx_count = 0
        self.rx = bytearray()
        self.last_rx = 0
        self.last_tx = 0
        self.error = ''
        self.active = None
        self.tags = []
        self.slave = {'unit': 1, 'maps': {str(fc): {str(i): (i % 2 if fc < 3 else 100 + i) for i in range(20)} for fc in range(1, 5)}}
        self.mock_fault = 'none'
        self.worker = None
        self.last_reader_tick = time.monotonic()

    def log(self, direction, data=b'', message=''):
        with self.lock:
            self.sequence += 1
            if len(self.events) == self.events.maxlen:
                self.dropped += 1
            self.events.append(dict(seq=self.sequence, time=now(), direction=direction, hex=data[:4096].hex(' '), text=data[:4096].decode('utf-8', errors='replace'), message=message, truncated=len(data) > 4096))

    def state(self):
        with self.lock:
            return copy.deepcopy(dict(backend='AKTIF', app_version=VERSION, connected=self.connected, serial=self.config, owner=self.owner, error=self.error, tx_bytes=self.tx_count, rx_bytes=self.rx_count, dropped=self.dropped, logs=list(self.events), active=self.active, tags=self.tags, slave=self.slave, mock_fault=self.mock_fault))

    def connect(self, config):
        config = serial_config(config)
        with self.lock:
            if self.connected or self.owner:
                raise ValueError('Disconnect dahulu; port sedang digunakan')
            handle = None
            if config['fixture'] != 'MOCK':
                handle = serial.Serial(config['port'], baudrate=config['baud'], bytesize=config['bits'], parity=config['parity'], stopbits=config['stop'], timeout=0, write_timeout=1, rtscts=config['flow'] == 'rtscts', xonxoff=config['flow'] == 'xonxoff', dsrdtr=config['flow'] == 'dsrdtr')
            self.handle = handle
            self.config = config
            self.store.setting('serial', config)
            self.connected = True
            self.last_reader_tick = time.monotonic()
            self.error = ''
            self.rx.clear()
            self.reader_stop = threading.Event()
            self.reader = threading.Thread(target=self._reader, daemon=True)
            self.reader.start()
            self.log('INFO', message='SIMULASI' if handle is None else 'REAL SERIAL; perangkat belum diuji')

    def disconnect(self):
        self.cancel.set()
        self.reader_stop.set()
        with self.lock:
            self.connected = False
            if self.handle:
                self.handle.close()
                self.handle = None
            self.condition.notify_all()
        if self.worker and self.worker is not threading.current_thread():
            self.worker.join(3)
        reader = getattr(self, 'reader', None)
        if reader and reader is not threading.current_thread():
            reader.join(2)

    def _receive(self, data):
        with self.condition:
            self.rx_count += len(data)
            self.log('RX', data)
            self.rx.extend(data)
            if len(self.rx) > 8192:
                del self.rx[:-8192]
                self.log('INFO', message='Buffer RX terpotong pada 8192 bytes')
            self.last_rx = time.monotonic()
            self.condition.notify_all()

    def _reader(self):
        previous = time.monotonic()
        stop_event = self.reader_stop
        while not stop_event.wait(.005):
            current = time.monotonic()
            if current - previous > 5:
                self.error = 'Jeda sistem/sleep terdeteksi; reconnect manual diperlukan'
                self.log('ERROR', message=self.error)
                self.disconnect()
                return
            previous = current
            self.last_reader_tick = current
            try:
                with self.lock:
                    if not self.connected:
                        return
                    data = self.handle.read(min(4096, self.handle.in_waiting)) if self.handle else b''
                if data:
                    self._receive(data)
            except (serial.SerialException, OSError) as exc:
                self.error = 'Port hilang/busy: ' + str(exc)
                self.log('ERROR', message=self.error)
                self.disconnect()
                return

    def _claim(self, owner):
        with self.lock:
            if not self.connected:
                raise ValueError('ERROR SETUP: Connect terlebih dahulu')
            if self.owner:
                raise ValueError(f'Port digunakan oleh {self.owner}; Stop dahulu')
            self.owner = owner
            self.cancel = threading.Event()

    def _send(self, data):
        with self.lock:
            if time.monotonic() - self.last_reader_tick > 5:
                self.error = 'Jeda sistem/sleep terdeteksi; reconnect manual diperlukan'
                self.cancel.set()
                self.reader_stop.set()
                self.connected = False
                if self.handle:
                    self.handle.close()
                    self.handle = None
                self.log('ERROR', message=self.error)
                raise InterruptedError(self.error)
            if self.cancel.is_set() or not self.connected:
                raise InterruptedError('Dibatalkan / port terputus')
            if self.handle:
                if self.handle.write(data) != len(data):
                    raise ValueError('Write serial parsial')
            self.tx_count += len(data)
            self.last_tx = time.monotonic()
            self.log('TX', data)
            if not self.handle and self.owner != 'slave':
                reply = b'PONG\r\n' if data == b'PING\r\n' else data
                if len(data) == 8 and data[1] in (1, 2, 3, 4):
                    reply = slave_response(data, self.slave['unit'], self.slave['maps'])
                if self.mock_fault == 'timeout':
                    reply = b''
                elif self.mock_fault == 'corrupt' and reply:
                    reply = reply[:-1] + bytes([reply[-1] ^ 1])
                elif self.mock_fault == 'echo':
                    reply = data
                if reply:
                    self._receive(reply)

    def terminal(self, spec):
        data = raw_bytes(spec)
        self._claim('terminal')
        try:
            self._send(data)
        finally:
            with self.lock:
                self.owner = None

    def _exchange(self, data, step, modbus=False):
        started = time.monotonic()
        with self.condition:
            self.rx.clear()
            if self.handle:
                self.handle.reset_input_buffer()
            # RTU quiet interval; adapter scheduling is hardware-dependent.
            quiet = max(.00175, 3.5 * 11 / self.config['baud']) if modbus else 0
            remaining = quiet - (time.monotonic() - max(self.last_rx, self.last_tx))
            if remaining > 0:
                self.condition.wait(remaining)
            self._send(data)
            deadline = time.monotonic() + step.get('timeout', 1)
            while True:
                if self.cancel.is_set() or not self.connected:
                    raise InterruptedError('Dibatalkan / port terputus')
                current = bytes(self.rx)
                complete = False
                if modbus and len(current) >= 3:
                    size = 5 if current[1] & 0x80 else current[2] + 5
                    complete = len(current) >= size
                    if complete and len(current) != size:
                        raise ValueError('Frame gabungan/noise/local echo; respons ambigu')
                elif not modbus:
                    if step.get('length'):
                        complete = len(current) >= step['length']
                    elif step.get('delimiter_hex'):
                        complete = bytes.fromhex(step['delimiter_hex']) in current
                    else:
                        complete = bool(current) and time.monotonic() - self.last_rx >= step.get('idle_ms', 50) / 1000
                if complete:
                    if current == data and self.config['fixture'] != 'LOOPBACK':
                        raise ValueError('Respons sama dengan TX: kemungkinan local echo; PASS ditolak')
                    return current, round((time.monotonic() - started) * 1000, 3)
                if time.monotonic() >= deadline:
                    raise ValueError('Timeout / frame parsial: ' + current.hex(' '))
                self.condition.wait(min(.01, max(0, deadline - time.monotonic())))

    def read_tag(self, tag):
        tx = request(tag['unit'], tag['function'], tag['address'], tag['count'])
        rx, latency = self._exchange(tx, tag, True)
        values = response(rx, tag['unit'], tag['function'], tag['count'])
        return dict(tx=tx.hex(' '), rx=rx.hex(' '), registers=values, value=decode(values, tag), latency_ms=latency, updated=now(), monotonic=time.monotonic())

    def _start_worker(self, function):
        self.worker = threading.Thread(target=function, daemon=True)
        self.worker.start()

    def stop(self):
        self.cancel.set()
        with self.condition:
            self.condition.notify_all()
        if self.worker:
            self.worker.join(3)

    def periodic(self, spec):
        data = raw_bytes(spec)
        interval = number(spec.get('interval', 1), .05, 60, 'Interval')
        self._claim('periodic')
        def work():
            try:
                while not self.cancel.is_set():
                    self._send(data)
                    if self.cancel.wait(interval):
                        break
            except Exception as exc:
                self.error = str(exc)
                self.log('ERROR', message=str(exc))
            finally:
                with self.lock:
                    self.owner = None
        self._start_worker(work)

    def master(self, spec):
        tags = spec['tags']
        if not isinstance(tags, list) or not 1 <= len(tags) <= 100:
            raise ValueError('Master memerlukan 1..100 tag')
        interval = number(spec.get('interval', 1), .05, 60, 'Poll interval')
        for tag in tags:
            tag_valid(tag)
            number(tag.get('timeout', 1), .05, 30, 'Timeout')
        self._claim('master')
        self.store.setting('tags', tags)
        self.tags = [dict(config=tag, error='', stale=True) for tag in tags]
        def work():
            try:
                while not self.cancel.is_set():
                    for index, tag in enumerate(tags):
                        if self.cancel.is_set():
                            break
                        try:
                            result = self.read_tag(tag)
                            with self.lock:
                                self.tags[index] = dict(config=tag, **result, error='', stale=False)
                        except InterruptedError:
                            return
                        except Exception as exc:
                            with self.lock:
                                self.tags[index].update(error=str(exc), stale=True, tx=request(tag['unit'], tag['function'], tag['address'], tag['count']).hex(' '), rx=bytes(self.rx).hex(' '))
                            self.log('ERROR', message=str(exc))
                    if not spec.get('poll', False) or self.cancel.wait(interval):
                        break
            finally:
                with self.lock:
                    self.owner = None
        self._start_worker(work)

    def configure_slave(self, spec):
        number(spec['unit'], 1, 247, 'Unit', True)
        for function in ('1', '2', '3', '4'):
            table = spec['maps'][function]
            if not isinstance(table, dict) or len(table) > 2000:
                raise ValueError('Maksimum 2000 alamat per map')
            for address, value in table.items():
                number(int(address), 0, 65535, 'Alamat', True)
                if str(int(address)) != address:
                    raise ValueError('Alamat harus desimal canonical')
                number(value, 0, 1 if int(function) < 3 else 65535, 'Nilai', True)
        with self.lock:
            if self.owner:
                raise ValueError('Stop dahulu sebelum edit map')
            self.slave = copy.deepcopy(spec)
            self.store.setting('slave', spec)

    def inject(self, spec):
        data = raw_bytes(dict(format='HEX', payload=spec['hex']))
        with self.lock:
            if not self.connected or self.config['fixture'] != 'MOCK' or self.owner != 'slave':
                raise ValueError('Inject hanya untuk SIMULASI slave aktif')
            self._receive(data)

    def start_slave(self):
        self._claim('slave')
        with self.lock:
            self.rx.clear()
            if self.handle:
                self.handle.reset_input_buffer()
        self.log('INFO', message='REAL SERIAL + SYNTHETIC VALUES' if self.handle else 'SIMULASI slave; tidak ada master eksternal')
        def work():
            try:
                while not self.cancel.wait(.002):
                    with self.lock:
                        quiet = max(.00175, 3.5 * 11 / self.config['baud'])
                        if not self.rx or time.monotonic() - self.last_rx < quiet:
                            continue
                        pending = bytes(self.rx)
                        self.rx.clear()
                    # Read requests are 8 bytes. Unknown FC handled at RTU gap.
                    while pending:
                        size = 8 if len(pending) >= 2 and pending[1] in (1, 2, 3, 4) else len(pending)
                        incoming, pending = pending[:size], pending[size:]
                        try:
                            answer = slave_response(incoming, self.slave['unit'], self.slave['maps'])
                            if answer:
                                self._send(answer)
                        except ValueError as exc:
                            self.log('ERROR', incoming, str(exc))
            except Exception as exc:
                self.error = str(exc)
                self.log('ERROR', message=str(exc))
            finally:
                with self.lock:
                    self.owner = None
        self._start_worker(work)

    def run(self, profile, identity='unknown'):
        profile = copy.deepcopy(validate(profile))
        with self.lock:
            if profile.get('fixture', 'MOCK') != self.config.get('fixture'):
                raise ValueError('Fixture profil berbeda dari koneksi; edit secara eksplisit')
            expected_settings = profile.get('serial', {})
            if any(self.config.get(k) != v for k, v in expected_settings.items()):
                raise ValueError('Serial settings profil berbeda dari koneksi')
            self._claim('scenario')
            run = dict(id=str(uuid.uuid4()), profile=profile, status='BERJALAN', started=now(), fixture=self.config['fixture'], serial=copy.deepcopy(self.config), app_version=VERSION, identity=str(identity)[:200], results=[], completed=0, errors=0, target=len(profile['steps']) * profile.get('repeats', 1), reason='', retry_policy='zero errors; no retry')
            self.active = run
            self.store.save(run)
        def work():
            started = time.monotonic()
            try:
                for repetition in range(profile.get('repeats', 1)):
                    for index, step in enumerate(profile['steps']):
                        entry = dict(step=index + 1, repeat=repetition + 1, assertions=step['assertions'], tx='', rx='', error='')
                        step_started = time.monotonic()
                        try:
                            if profile['protocol'] == 'modbus':
                                entry['tx'] = request(step['unit'], step['function'], step['address'], step['count']).hex(' ')
                                entry.update(self.read_tag(step))
                                actual = bytes.fromhex(entry['rx'])
                                value = entry['value']
                            else:
                                payload = raw_bytes(step)
                                entry['tx'] = payload.hex(' ')
                                actual, latency = self._exchange(payload, step)
                                entry.update(rx=actual.hex(' '), latency_ms=latency)
                                value = None
                            assert_result(actual, value, step['assertions'])
                        except InterruptedError:
                            raise
                        except Exception as exc:
                            entry['error'] = str(exc)
                            entry['rx'] = bytes(self.rx).hex(' ')
                            entry['latency_ms'] = round((time.monotonic() - step_started) * 1000, 3)
                            run['errors'] += 1
                        with self.lock:
                            run['completed'] += 1
                            run['results'].append(entry)
                            # Bounded raw results: first 500; totals still exact.
                            if len(run['results']) > 500:
                                run['results'].pop(0)
                                run['truncated_results'] = run.get('truncated_results', 0) + 1
                            self.store.save(run)
                        if self.cancel.wait(profile.get('interval', .1)):
                            raise InterruptedError('Dibatalkan')
                run['status'] = 'FAIL' if run['errors'] else 'PASS'
                run['reason'] = f"{run['errors']} langkah gagal" if run['errors'] else 'Semua assertions terpenuhi' + (' — SIMULASI, bukan bukti hardware' if run['fixture'] == 'MOCK' else '')
            except InterruptedError as exc:
                run.update(status='INCOMPLETE', reason=str(exc))
            except Exception as exc:
                run.update(status='INCOMPLETE', reason=str(exc))
            finally:
                with self.lock:
                    run.update(ended=now(), duration_ms=round((time.monotonic() - started) * 1000, 3))
                    self.store.save(run)
                    self.owner = None
        self._start_worker(work)
        return run['id']

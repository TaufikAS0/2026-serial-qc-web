import json
import math
from .protocol import request, raw_bytes, decode


def number(value, low, high, name, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high or (integer and type(value) is not int):
        raise ValueError(f'{name}: harus {low}..{high}')
    return value


def tag_valid(tag):
    request(tag['unit'], tag['function'], tag['address'], tag['count'])
    for key in ('byte_order', 'word_order'):
        if tag.get(key, 'big') not in ('big', 'little'):
            raise ValueError('Order harus big/little')
    if tag['function'] < 3 and tag.get('type') != 'bits':
        raise ValueError('FC01/02 memerlukan tipe bits')
    if tag['function'] >= 3 and tag.get('type') == 'bits':
        raise ValueError('bits hanya FC01/02')
    if tag['function'] >= 3:
        decode([0] * tag['count'], tag)
    for key, default in [('scale', 1), ('offset', 0)]:
        number(tag.get(key, default), -1e12, 1e12, key)


def validate(profile):
    if not isinstance(profile, dict) or profile.get('version') != 1:
        raise ValueError('Profil memerlukan version: 1')
    if set(profile) - {'version', 'name', 'protocol', 'fixture', 'repeats', 'interval', 'serial', 'steps', 'notes'}:
        raise ValueError('Kolom profil tidak didukung; script/checksum/regex arbitrary tidak diizinkan')
    serial_settings = profile.get('serial', {})
    if not isinstance(serial_settings, dict) or set(serial_settings) - {'baud', 'bits', 'parity', 'stop', 'flow', 'interface'}:
        raise ValueError('Serial profil hanya settings portable; COM dipilih di Koneksi')
    if not isinstance(profile.get('notes', ''), str) or len(profile.get('notes', '')) > 1000:
        raise ValueError('Notes harus teks maksimum 1000 karakter')
    if 'baud' in serial_settings:
        number(serial_settings['baud'], 300, 2000000, 'Baud', True)
    for key, allowed in [('bits', (5,6,7,8)), ('parity', ('N','E','O','M','S')), ('stop', (1,1.5,2)), ('flow', ('none','rtscts','xonxoff','dsrdtr')), ('interface', ('RS232','RS485'))]:
        if key in serial_settings and serial_settings[key] not in allowed:
            raise ValueError(f'Serial {key} tidak valid')
    if not isinstance(profile.get('name'), str) or not 1 <= len(profile['name']) <= 100:
        raise ValueError('Nama profil 1..100 karakter')
    if profile.get('fixture', 'MOCK') not in ('MOCK', 'REAL', 'LOOPBACK'):
        raise ValueError('Fixture harus MOCK/REAL/LOOPBACK')
    if profile.get('protocol') not in ('raw', 'modbus'):
        raise ValueError('Protokol harus raw/modbus')
    number(profile.get('repeats', 1), 1, 1000, 'Repeats', True)
    number(profile.get('interval', .1), .01, 60, 'Interval')
    steps = profile.get('steps')
    if not isinstance(steps, list) or not 1 <= len(steps) <= 100:
        raise ValueError('Profil harus memiliki 1..100 langkah')
    if len(steps) * profile.get('repeats', 1) > 10000:
        raise ValueError('Maksimum 10000 langkah total')
    for step in steps:
        if not isinstance(step, dict) or set(step) - {'format', 'payload', 'encoding', 'ending', 'length', 'delimiter_hex', 'idle_ms', 'timeout', 'assertions', 'name', 'unit', 'function', 'address', 'count', 'type', 'byte_order', 'word_order', 'scale', 'offset'}:
            raise ValueError('Kolom langkah tidak didukung')
        number(step.get('timeout', 1), .05, 30, 'Timeout')
        if profile['protocol'] == 'raw':
            raw_bytes(step)
            if 'length' in step:
                number(step['length'], 1, 4096, 'Frame length', True)
            if 'delimiter_hex' in step and not 1 <= len(bytes.fromhex(step['delimiter_hex'])) <= 16:
                raise ValueError('Delimiter harus 1..16 bytes')
            number(step.get('idle_ms', 50), 5, 1000, 'Idle gap')
        else:
            tag_valid(step)
        assertions = step.get('assertions')
        if not isinstance(assertions, list) or not 1 <= len(assertions) <= 20:
            raise ValueError('Setiap langkah memerlukan assertions eksplisit')
        for assertion in assertions:
            if not isinstance(assertion, dict) or set(assertion) - {'kind', 'hex', 'value', 'min', 'max', 'target', 'tolerance'}:
                raise ValueError('Kolom assertion tidak didukung')
            kind = assertion.get('kind')
            if kind in ('exact', 'prefix', 'contains'):
                if not 1 <= len(bytes.fromhex(assertion['hex'])) <= 4096:
                    raise ValueError('Assertion bytes kosong/terlalu besar')
            elif kind == 'length':
                number(assertion['value'], 1, 4096, 'Panjang assertion', True)
            elif kind == 'range':
                number(assertion['min'], -1e30, 1e30, 'Minimum')
                number(assertion['max'], assertion['min'], 1e30, 'Maximum')
            elif kind == 'tolerance':
                number(assertion['target'], -1e30, 1e30, 'Target')
                number(assertion['tolerance'], 0, 1e30, 'Tolerance')
            else:
                raise ValueError('Assertion tidak dikenal')
    if len(json.dumps(profile)) > 200000:
        raise ValueError('Profil terlalu besar')
    return profile


def assert_result(data, value, assertions):
    for assertion in assertions:
        kind = assertion['kind']
        expected = bytes.fromhex(assertion['hex']) if kind in ('exact', 'prefix', 'contains') else None
        ok = {'exact': lambda: data == expected, 'prefix': lambda: data.startswith(expected),
              'contains': lambda: expected in data, 'length': lambda: len(data) == assertion['value'],
              'range': lambda: isinstance(value, (int, float)) and assertion['min'] <= value <= assertion['max'],
              'tolerance': lambda: isinstance(value, (int, float)) and abs(value - assertion['target']) <= assertion['tolerance']}[kind]()
        if not ok:
            raise ValueError(f'Assertion {kind} gagal; actual={data.hex(" ")}, value={value}')

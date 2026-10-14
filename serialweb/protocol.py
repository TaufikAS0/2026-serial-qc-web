"""Read-only Modbus RTU codec. Addresses are protocol offsets, never 4xxxx."""
import math
import struct


def crc(data):
    value = 0xffff
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xa001 if value & 1 else 0)
    return value.to_bytes(2, 'little')


def frame(data):
    return data + crc(data)


def checked(data):
    if len(data) < 4 or crc(data[:-2]) != data[-2:]:
        raise ValueError('CRC Modbus tidak valid / frame parsial')
    return data[:-2]


def request(unit, function, address, count):
    if any(type(value) is not int for value in (unit, function, address, count)):
        raise ValueError('Unit/fungsi/alamat/count harus integer')
    if not 1 <= unit <= 247 or function not in (1, 2, 3, 4):
        raise ValueError('Unit harus 1..247 dan fungsi FC01..04')
    if not 1 <= count <= (2000 if function < 3 else 125):
        raise ValueError('Jumlah di luar batas Modbus')
    if not 0 <= address <= 65535 or address + count > 65536:
        raise ValueError('Alamat zero-based tidak valid')
    return frame(struct.pack('>BBHH', unit, function, address, count))


def response(data, unit, function, count):
    body = checked(data)
    if body[0] != unit:
        raise ValueError('Unit respons berbeda')
    if body[1] == function | 0x80:
        if len(body) != 3:
            raise ValueError('Panjang exception tidak valid')
        raise ValueError(f'Modbus exception {body[2]}')
    expected = (count + 7) // 8 if function < 3 else count * 2
    if body[1] != function or len(body) != expected + 3 or body[2] != expected:
        raise ValueError('Fungsi/byte count/panjang respons berbeda')
    if function < 3:
        if count % 8 and body[-1] >> (count % 8):
            raise ValueError('Padding bits Modbus harus nol')
        return [bool(body[3 + i // 8] & (1 << (i % 8))) for i in range(count)]
    return list(struct.unpack('>' + 'H' * count, body[3:]))


def slave_response(data, unit, maps):
    body = checked(data)
    if body[0] != unit:  # includes read broadcasts: never reply
        return b''
    function = body[1]
    def exception(code):
        return frame(bytes([unit, function | 0x80, code]))
    if function not in (1, 2, 3, 4):
        return exception(1)
    if len(body) != 6:
        return exception(3)
    address, count = struct.unpack('>HH', body[2:])
    if not 1 <= count <= (2000 if function < 3 else 125):
        return exception(3)
    table = maps[str(function)]
    if address + count > 65536 or any(str(i) not in table for i in range(address, address + count)):
        return exception(2)
    values = [table[str(i)] for i in range(address, address + count)]
    if function < 3:
        payload = bytearray((count + 7) // 8)
        for i, value in enumerate(values):
            payload[i // 8] |= int(bool(value)) << (i % 8)
    else:
        payload = struct.pack('>' + 'H' * count, *values)
    return frame(bytes([unit, function, len(payload)]) + payload)


def decode(values, tag):
    kind = tag.get('type', 'uint16')
    if kind == 'bits':
        return values
    formats = {'uint16': 'H', 'int16': 'h', 'uint32': 'I', 'int32': 'i', 'float32': 'f'}
    if kind not in formats:
        raise ValueError('Tipe data tidak dikenal')
    width = 2 if kind in ('uint32', 'int32', 'float32') else 1
    if len(values) != width or any(type(v) is not int for v in values):
        raise ValueError('Panjang tag tidak sesuai tipe data')
    words = list(values)
    if tag.get('word_order', 'big') == 'little':
        words.reverse()
    payload = b''.join(v.to_bytes(2, 'big') for v in words)
    if tag.get('byte_order', 'big') == 'little':
        payload = b''.join(payload[i:i+2][::-1] for i in range(0, len(payload), 2))
    value = struct.unpack('>' + formats[kind], payload)[0]
    result = value * float(tag.get('scale', 1)) + float(tag.get('offset', 0))
    if not math.isfinite(result):
        raise ValueError('Nilai decode NaN/Infinity')
    return result


def raw_bytes(spec):
    mode = spec.get('format', 'ASCII')
    ending = {'none': b'', 'CR': b'\r', 'LF': b'\n', 'CRLF': b'\r\n'}
    if spec.get('ending', 'none') not in ending:
        raise ValueError('Line ending tidak valid')
    encoding = spec.get('encoding', 'ascii')
    if encoding not in ('ascii', 'utf-8', 'latin-1'):
        raise ValueError('Encoding harus ascii/utf-8/latin-1')
    if mode not in ('ASCII', 'HEX'):
        raise ValueError('Format harus ASCII/HEX')
    data = bytes.fromhex(spec.get('payload', '')) if mode == 'HEX' else spec.get('payload', '').encode(encoding)
    data += ending[spec.get('ending', 'none')]
    if not 1 <= len(data) <= 4096:
        raise ValueError('Payload harus 1..4096 bytes')
    return data

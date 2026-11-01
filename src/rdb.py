"""Read-only AO RDB lookup, adapted from TinkerParse's AoDbController.
Format reference: https://github.com/TheTinkeringIdiot/TinkerParse
Modified 2026-11-01 for AO Armor Packs: explicit paths, index-slot ownership and local-only extraction.
SPDX-License-Identifier: GPL-3.0-only
No database write operations are provided.
"""
from pathlib import Path
import struct

class Rdb:
    def __init__(self, root):
        self.root = Path(root)
        data = (self.root / 'ResourceDatabase.idx').read_bytes()
        self.block_offset = struct.unpack_from('<I', data, 12)[0]
        block = struct.unpack_from('<i', data, 72)[0]
        self.part_size = struct.unpack_from('<I', data, 184)[0]
        # The native client enforces these split low/high EOF markers. A raw
        # seek can otherwise "validate" a record the database engine rejects.
        with (self.root / 'ResourceDatabase.dat').open('rb') as stream:
            header = stream.read(144)
        self.allocated_end = struct.unpack_from('<I', header, 0)[0] | (struct.unpack_from('<I', header, 128)[0] << 32)
        self.logical_end = struct.unpack_from('<I', header, 8)[0] | (struct.unpack_from('<I', header, 136)[0] << 32)
        if self.logical_end > self.allocated_end:
            raise ValueError('Logical EOF exceeds allocated EOF')
        self.records = {}
        self.slots = {}
        visited = set()
        while block:
            if block in visited or not 0 <= block <= len(data) - 28:
                raise ValueError('Invalid index block')
            visited.add(block)
            nxt = struct.unpack_from('<i', data, block)[0]
            count = struct.unpack_from('<h', data, block + 8)[0]
            if count < 0 or block + 28 + count * 16 > len(data):
                raise ValueError('Invalid record count')
            for i in range(count):
                p = block + 28 + i * 16
                hi, lo = struct.unpack_from('<II', data, p)
                key = struct.unpack_from('>ii', data, p + 8)
                if key in self.records:
                    raise ValueError('Duplicate record')
                self.records[key] = (hi << 32) | lo
                self.slots[key] = p
            block = nxt

    def get(self, typ, instance):
        offset = self.records[typ, instance]
        if offset > self.logical_end:
            raise ValueError('Resource starts beyond database logical EOF')
        part = offset // self.part_size
        pos = offset - (self.part_size - self.block_offset) * part if part else offset
        path = self.root / ('ResourceDatabase.dat' + (f'.{part:03}' if part else ''))
        with path.open('rb') as stream:
            stream.seek(pos + 10)
            actual_type, actual_id, size = struct.unpack('<iii', stream.read(12))
            if (actual_type, actual_id) != (typ, instance) or not 0 < size < 64 * 1024 * 1024:
                raise ValueError('Record header mismatch or excessive size')
            if offset + 22 + size - 1 > self.logical_end:
                raise ValueError('Resource extends beyond database logical EOF')
            payload = stream.read(size)
            if len(payload) != size:
                raise ValueError('Truncated record')
        return payload, {'type': typ, 'id': instance, 'file': str(path), 'payload_offset': pos + 22, 'size': size}

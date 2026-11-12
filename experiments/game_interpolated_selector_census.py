"""Read the bounded first-member selector domain from a linked Game ELF.

This is a static data census, not evidence of runtime reachability. The caller
uses an options byte masked to seven bits and a three-bit column; other ways of
altering its row memory and out-of-bounds array accesses are outside the bound.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER

TABLE_VA = 0x8008CF00
TABLE_ROM = 0x2319C0
DECLARED_ROWS = 5
ROWS = 128
COLUMNS = 8
PAIR_SIZE = 4
SELECTED = (2, 3, 5)


def section_bytes(elf, address, size):
    if elf[:6] != b'\x7fELF\x01\x02':
        raise ValueError('expected a big-endian ELF32 image')
    header = ELF_HEADER.unpack_from(elf)
    sections = [SECTION_HEADER.unpack_from(elf, header[6] + i * header[11])
                for i in range(header[12])]
    ranges = [(section[4] + address - section[3], section[5]) for section in sections
              if section[1] == 1 and section[3] <= address
              and address + size <= section[3] + section[5]]
    if len(ranges) != 1:
        raise ValueError('requested address is not in exactly one file-backed section')
    start = ranges[0][0]
    if start + size > len(elf):
        raise ValueError('truncated section')
    return elf[start:start + size]


def scan_pairs(data):
    if len(data) != ROWS * COLUMNS * PAIR_SIZE:
        raise ValueError('unexpected selector byte count')
    hits = []
    for row in range(ROWS):
        for column in range(COLUMNS):
            offset = (row * COLUMNS + column) * PAIR_SIZE
            index, count = struct.unpack_from('>hh', data, offset)
            if index in SELECTED:
                hits.append(dict(row=row, column=column, index=index, count=count,
                                 address=f'0x{TABLE_VA + offset:08X}',
                                 declared=row < DECLARED_ROWS))
    return hits


def census(elf, rom):
    data = section_bytes(elf, TABLE_VA, ROWS * COLUMNS * PAIR_SIZE)
    declared_size = DECLARED_ROWS * COLUMNS * PAIR_SIZE
    if data[:declared_size] != rom[TABLE_ROM:TABLE_ROM + declared_size]:
        raise ValueError('declared table differs from the supplied retail image')
    hits = scan_pairs(data)
    return dict(elf_sha256=hashlib.sha256(elf).hexdigest(), rows=ROWS, columns=COLUMNS,
                declared_rows=DECLARED_ROWS, selected_hits=len(hits),
                declared_hits=sum(hit['declared'] for hit in hits),
                outside_hits=[hit for hit in hits if not hit['declared']],
                zero_count_hits=[hit for hit in hits if hit['count'] == 0],
                scope='static linked data only; no runtime reachability or memory-invariance claim')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('elf', type=Path)
    parser.add_argument('rom', type=Path, help='decompressed US conker.us.bin')
    args = parser.parse_args()
    print(json.dumps(census(args.elf.read_bytes(), args.rom.read_bytes()), indent=2))


if __name__ == '__main__':
    main()

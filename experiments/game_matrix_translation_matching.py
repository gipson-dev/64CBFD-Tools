"""Recover translation scheduling from the fingerprinted emitted C instructions."""
import csv
import hashlib
import io
import struct

from tools.pad_generated_object import parse_object

FUNCTION = 'func_15142314'
RAW_SHA256 = 'd18460a4fd940873c915b3896f1dbf3b1f8b5a7220fc65946c8ad55672e3c950'
RELOCATIONS = {0: [('R_MIPS_HI16', 'D_800C3E90')], 4: [('R_MIPS_LO16', 'D_800C3E90')]}


def source_identity(words):
    if len(words) != 49:
        raise ValueError('Expected complete 49-word translation source')
    canonical = list(words)
    for at in RELOCATIONS:
        canonical[at // 4] &= 0xFFFF0000
    if hashlib.sha256(struct.pack('>49I', *canonical)).hexdigest() != RAW_SHA256:
        raise ValueError('Stale complete translation source')


def ordinary_branch(word, displacement):
    if word >> 26 != 20 or word >> 16 & 31 or not 0 <= displacement < 32768:
        raise ValueError('Expected forward zero-test branch-likely')
    return (word & 0x03FF0000) | (4 << 26) | displacement


def normalize(words):
    source_identity(words)
    if words[5] != words[41] or words[48] != 0:
        raise ValueError('Expected duplicate float load and existing return no-op')
    if words[2] != words[6] or words[3] != words[7]:
        raise ValueError('Expected original repeated matrix address')
    if words[10] >> 26 != 15 or words[14] >> 26 != 17:
        raise ValueError('Expected source scale constant and FP transfer')
    out = list(words)
    # The taken likely delay load becomes the float block's existing first load.
    # Its common address work occupies the ordinary branch delay on both paths.
    float_target = 4 + 1 + (words[4] & 65535) - 1
    out[:11] = [words[0], words[1], words[2], words[10],
        ordinary_branch(words[4], float_target - 5), words[3], words[14],
        words[6], words[7], words[8], words[9]]
    # Hoisted scale materialization closes the gap before the arithmetic.
    out[14:39] = [*words[15:39], words[40]]
    # Restore the final fixed store before JR; reuse the emitted no-op as its delay.
    out[40] = words[48]
    return out


def guard_rows(path):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    start = target['value']
    if target['size'] != 196:
        raise ValueError('Expected complete unpadded translation source')
    payload = text[start:start + 196]
    if hashlib.sha256(payload).hexdigest() != RAW_SHA256:
        raise ValueError('Stale complete translation source')
    relative = {at - start: uses for at, uses in relocations.items() if start <= at < start + 196}
    if relative != RELOCATIONS:
        raise ValueError('Unexpected complete translation relocation map')
    words = list(struct.unpack('>49I', payload))
    rows = []
    for i, (before, after) in enumerate(zip(words, normalize(words))):
        if before == after:
            continue
        if i * 4 in relative:
            raise ValueError('Translation scheduling must not move a relocation')
        rows.append(dict(filename='game_16EE20', function=FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % before, replacement='0x%08X' % after,
            expected_relocations='-', replacement_relocations='-',
            note='Normalize certified translation constant branch and return delay schedules',
            insert_after='', insert_after_relocations='', omit='false'))
    if len(rows) != 34:
        raise ValueError('Expected exactly 34 derived translation scheduling words')
    return rows


def guard_bytes(before, obj):
    if not before.endswith(b'\n'):
        raise ValueError('Expected newline-terminated guard manifest')
    reader = csv.DictReader(io.StringIO(before.decode('ascii')))
    if any(row['function'] == FUNCTION for row in reader):
        raise ValueError('Translation guards are already present')
    stream = io.StringIO(newline='')
    csv.DictWriter(stream, fieldnames=reader.fieldnames, lineterminator='\n').writerows(guard_rows(obj))
    return before + stream.getvalue().encode('ascii')

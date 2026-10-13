"""Derive finalizer scheduling and GPR normalization from emitted C words."""
import csv
import hashlib
import io
import struct

from tools.experiments.game_actor_segment_selector_matching import fields
from tools.pad_generated_object import parse_object

FUNCTION = 'func_15034860'
RAW_SHA256 = 'cef29a96dfe1d477d242f6d6236c0e3e450976359dd1a3237e581c1cd32c0a09'
RELOCATIONS = {
    132: [('R_MIPS_HI16', 'D_80097D40')], 148: [('R_MIPS_LO16', 'D_80097D40')],
    180: [('R_MIPS_HI16', 'D_80097D44')], 184: [('R_MIPS_LO16', 'D_80097D44')],
    236: [('R_MIPS_HI16', 'D_80097D48')], 240: [('R_MIPS_LO16', 'D_80097D48')],
    248: [('R_MIPS_HI16', 'D_800C3EF0')], 320: [('R_MIPS_LO16', 'D_800C3EF0')],
    412: [('R_MIPS_HI16', 'D_80097D4C')], 416: [('R_MIPS_LO16', 'D_80097D4C')],
    420: [('R_MIPS_HI16', 'D_80097D50')], 424: [('R_MIPS_LO16', 'D_80097D50')],
    628: [('R_MIPS_26', 'func_150ADA20')], 744: [('R_MIPS_26', 'func_150ADA20')],
    880: [('R_MIPS_HI16', 'D_800BE9E4')], 884: [('R_MIPS_LO16', 'D_800BE9E4')],
    940: [('R_MIPS_HI16', 'D_80097D54')], 956: [('R_MIPS_LO16', 'D_80097D54')],
    964: [('R_MIPS_HI16', 'D_80097D58')], 968: [('R_MIPS_LO16', 'D_80097D58')],
    1016: [('R_MIPS_HI16', 'D_80097D5C')], 1024: [('R_MIPS_LO16', 'D_80097D5C')],
    1360: [('R_MIPS_26', 'func_150ADA20')],
    1552: [('R_MIPS_HI16', 'D_800BE9E4')], 1568: [('R_MIPS_LO16', 'D_800BE9E4')],
}


def gpr_cycle(word, cycle):
    if set(cycle) != set(cycle.values()) or not set(cycle) <= {3, 11, 12, 13, 14, 15, 24, 25}:
        raise ValueError('Expected a closed finalizer scratch-register cycle')
    op, fn, fmt = word >> 26, word & 63, word >> 21 & 31
    if op == 0:
        if fn not in (0, 3, 8, 13, 16, 18, 25, 26, 27, 33, 35, 37, 42, 43):
            raise ValueError('Unexpected R-format instruction in finalizer cycle')
        shifts = (21, 16, 11)
    elif op in (1, 4, 5, 6, 7, 9, 10, 11, 12, 13, 15, 20, 21, 22, 23, 32, 33, 35, 36, 37, 40, 41, 43):
        shifts = (21, 16)
    elif op in (49, 57):
        shifts = (21,)
    elif op == 17:
        shifts = (16,) if fmt in (0, 2, 4, 6) else ()
    elif op in (2, 3):
        shifts = ()
    else:
        raise ValueError('Unexpected opcode in finalizer cycle')
    for shift in shifts:
        value = word >> shift & 31
        word = word & ~(31 << shift) | cycle.get(value, value) << shift
    return word


def commute(word):
    return fields(word, rs=word >> 16 & 31, rt=word >> 21 & 31)


def normalize(words):
    if len(words) != 405 or words[:5] != [0x27BDFFB8, 0xAFBF0014, 0xAFA40048, 0xAFA60050, 0xAFA70054]:
        raise ValueError('Expected complete finalizer with original frame/homes')
    out = list(words)
    # Defer the cached value copy and limit constant to their common branch-delay/join positions.
    order = (20, 15, 16, 17, 18, 19, 21, 14, 23, 24, 25, 26, 27, 28, 29, 22)
    assert words[14] == 0x00401825 and words[20] == 0x24010069 and words[22] == 0x240A00FF
    out[14:30] = [words[i] for i in order]
    assert out[20] == 0x10610007
    out[20] = fields(out[20], rs=2)
    # Lower=40 is independent of the byte-to-float conversion and the scale-address load.
    assert words[61] == 0x24070028 and words[53] == 0x05E10004
    out[53:62] = [words[61], *words[53:61]]
    # Both incoming paths define the same second-channel home before its common gate.
    for index in (31, 230, 231):
        out[index] = gpr_cycle(out[index], {25: 11, 11: 25})
    # The four mutually exclusive velocity loads join at one final addition.
    for index in (152, 181, 183, 201, 203):
        out[index] = gpr_cycle(out[index], {12: 13, 13: 12})
    out[203] = commute(out[203])
    for index in (204, 205):
        out[index] = gpr_cycle(out[index], {13: 14, 14: 13})
    for index in (215, 216):
        out[index] = gpr_cycle(out[index], {15: 24, 24: 15})
    for index in (225, 227):
        out[index] = gpr_cycle(out[index], {24: 25, 25: 24})
    for index in range(252, 257):
        out[index] = gpr_cycle(out[index], {11: 12, 12: 11})
    row = {12: 3, 3: 15, 15: 11, 11: 14, 14: 25, 25: 13, 13: 24, 24: 12}
    for index in range(257, 277):
        out[index] = gpr_cycle(out[index], row)
    constants = {11: 12, 12: 15, 15: 11, 13: 24, 24: 13, 14: 25, 25: 14}
    for index in range(281, 296):
        out[index] = gpr_cycle(out[index], constants)
    assert out[315] == 0x144A0014
    out[315] = commute(out[315])
    tail = {11: 14, 14: 25, 25: 13, 13: 24, 24: 12, 12: 15, 15: 11}
    for index in range(345, 398):
        out[index] = gpr_cycle(out[index], tail)
    return out


def normalized_relocations(relative):
    if relative != RELOCATIONS:
        raise ValueError('Unexpected complete finalizer relocation map')
    result = {at: uses for at, uses in relative.items() if at not in (236, 240)}
    result[240] = relative[236]
    result[244] = relative[240]
    return result


def guard_rows(path):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    start = target['value']
    if target['size'] != 1620:
        raise ValueError('Expected the complete unpadded 405-word source object')
    payload = text[start:start + 1620]
    if hashlib.sha256(payload).hexdigest() != RAW_SHA256:
        raise ValueError('Stale complete finalizer object')
    relative = {at - start: uses for at, uses in relocations.items() if start <= at < start + 1620}
    moved = normalized_relocations(relative)
    words = list(struct.unpack('>405I', payload))
    out = normalize(words)
    names = lambda uses: ';'.join(kind + ':' + symbol for kind, symbol in uses) or '-'
    rows = []
    for i, (before, after) in enumerate(zip(words, out)):
        offset = i * 4
        if before == after and relative.get(offset, []) == moved.get(offset, []):
            continue
        rows.append(dict(filename='generated_61D10', function=FUNCTION, offset='0x%X' % offset,
            expected='0x%08X' % before, replacement='0x%08X' % after,
            expected_relocations=names(relative.get(offset, [])), replacement_relocations=names(moved.get(offset, [])),
            note='Normalize certified finalizer independent schedules and closed GPR lifetimes',
            insert_after='', insert_after_relocations='', omit='false'))
    if len(rows) != 76:
        raise ValueError('Expected exactly 76 derived finalizer words')
    return rows


def guard_bytes(before, obj):
    if not before.endswith(b'\n'):
        raise ValueError('Expected newline-terminated guard manifest')
    reader = csv.DictReader(io.StringIO(before.decode('ascii')))
    if any(row['function'] == FUNCTION for row in reader):
        raise ValueError('Finalizer guards are already present')
    stream = io.StringIO(newline='')
    csv.DictWriter(stream, fieldnames=reader.fieldnames, lineterminator='\n').writerows(guard_rows(obj))
    return before + stream.getvalue().encode('ascii')

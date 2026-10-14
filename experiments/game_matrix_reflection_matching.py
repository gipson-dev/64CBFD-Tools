"""Derive reflection register normalization from the complete emitted C object."""
import csv
import hashlib
import io
import struct

from tools.pad_generated_object import parse_object

FUNCTION = 'func_15034F30'
RAW_SHA256 = 'a904c1c26881f37fbdb461a11a0deb5a9967da4bcad388b5f4ee8c10b086473b'
RELOCATIONS = {at: [('R_MIPS_26', name)] for at, name in (
    (80, 'guMtxIdentF'), (192, 'guMtxL2F'), (240, 'func_150A7A48'),
    (288, 'bcopy'), (300, 'guMtxF2L2'), (1072, 'func_150A8050'),
    (1092, 'func_150A8050'), (1172, 'guMtxL2F'), (1220, 'bcopy'),
    (1272, 'func_150A7A48'), (1288, 'func_150A7A48'), (1304, 'func_150A7A48'),
    (1368, 'bcopy'), (1380, 'guMtxF2L2'), (1456, 'func_150AD960'),
    (1860, 'func_15034728'))}


def source_identity(words):
    if len(words) != 486 or words[0] != 0x27BDFE70:
        raise ValueError('Expected complete reflection object and original frame')
    canonical = list(words)
    for at in RELOCATIONS:
        if canonical[at // 4] >> 26 != 3:
            raise ValueError('Expected source JAL relocation')
        canonical[at // 4] &= 0xFC000000
    if hashlib.sha256(struct.pack('>486I', *canonical)).hexdigest() != RAW_SHA256:
        raise ValueError('Stale complete reflection object')


def replace_fields(word, shifts, cycle):
    for shift in shifts:
        value = word >> shift & 31
        word = word & ~(31 << shift) | cycle.get(value, value) << shift
    return word


def gpr_cycle(word, cycle):
    if set(cycle) != set(cycle.values()) or not set(cycle) <= {2, 8, 9, 10, 11, 12, 13, 14, 15, 17, 20, 21, 24, 25}:
        raise ValueError('Expected a closed reflection GPR lifetime cycle')
    op, fn, fmt = word >> 26, word & 63, word >> 21 & 31
    if op == 0:
        if fn not in (0, 2, 3, 8, 16, 18, 24, 25, 26, 27, 33, 35, 36, 37, 38, 39, 42, 43):
            raise ValueError('Unexpected R-format instruction in reflection cycle')
        shifts = (21, 16, 11)
    elif op in (1, 6, 7, 22, 23):
        shifts = (21,)
    elif op in (4, 5, 9, 10, 11, 12, 13, 14, 15, 20, 21, 32, 33, 35, 36, 37, 40, 41, 43):
        shifts = (21, 16)
    elif op in (49, 57):
        shifts = (21,)
    elif op == 17:
        shifts = (16,) if fmt in (0, 2, 4, 6) else ()
    elif op in (2, 3):
        shifts = ()
    else:
        raise ValueError('Unexpected opcode in reflection GPR cycle')
    return replace_fields(word, shifts, cycle)


def fpr_cycle(word, cycle):
    if set(cycle) != set(cycle.values()) or not set(cycle) <= {0, 2, 4, 6, 8, 10, 18}:
        raise ValueError('Expected a closed reflection scratch FPR cycle')
    op, fn, fmt = word >> 26, word & 63, word >> 21 & 31
    if op in (49, 57):
        shifts = (16,)
    elif op == 17:
        if fmt in (0, 4):
            shifts = (11,)
        elif fmt in (2, 6, 8):
            shifts = ()
        elif fmt in (16, 17, 20):
            if fn in (0, 1, 2, 3):
                shifts = (6, 11, 16)
            elif fn in (4, 5, 6, 7, 12, 13, 14, 15, 32, 33, 36):
                shifts = (6, 11)
            elif 48 <= fn <= 63:
                shifts = (11, 16)
            else:
                raise ValueError('Unexpected COP1 operation in reflection cycle')
        else:
            raise ValueError('Unexpected COP1 format in reflection cycle')
    else:
        shifts = ()
    return replace_fields(word, shifts, cycle)


def subtract_destination(word, destination):
    if word >> 26 != 17 or word >> 21 & 31 != 16 or word & 63 != 1 or destination not in (0, 4):
        raise ValueError('Expected single-precision dead-result SUB coalescing')
    return word & ~(31 << 6) | destination << 6


def commute_add(word):
    if word >> 26 != 0 or word & 63 != 33:
        raise ValueError('Expected commutative integer ADdu')
    return replace_fields(word, (21, 16), {word >> 21 & 31: word >> 16 & 31,
        word >> 16 & 31: word >> 21 & 31})


def commute_multiply(word):
    if word >> 26 != 17 or word >> 21 & 31 != 16 or word & 63 != 2:
        raise ValueError('Expected commutative single-precision MUL')
    return replace_fields(word, (11, 16), {word >> 11 & 31: word >> 16 & 31,
        word >> 16 & 31: word >> 11 & 31})


def normalize(words):
    source_identity(words)
    out = list(words)

    def g(indices, cycle):
        for i in indices:
            out[i] = gpr_cycle(out[i], cycle)

    def f(indices, cycle):
        for i in indices:
            out[i] = fpr_cycle(out[i], cycle)

    # Mode snapshots, conversion caches and offsets have separate live ranges.
    g((22, 24, 25, 26, 28, 32), {2: 14, 14: 15, 15: 2})
    g((27, 258), {21: 12, 12: 21})
    g(range(37, 81), {20: 21, 21: 20})
    g(range(277, 351), {20: 21, 21: 20})
    g((68, 71, 77, 80), {15: 24, 24: 25, 25: 15})
    out[71] = commute_add(out[71])
    g((87, 93), {25: 24, 24: 25})
    g((95, 99), {2: 25, 25: 2})
    g(range(87, 257), {8: 10, 10: 12, 12: 14, 14: 24, 24: 8,
        9: 11, 11: 13, 13: 15, 15: 25, 25: 9})
    g((275, 278), {2: 13, 13: 2})
    g((338, 341, 347, 350), {10: 14, 14: 10, 11: 15, 15: 11})
    out[341] = commute_add(out[341])
    g((370, 376), {24: 10, 10: 24})
    g(range(379, 456), {8: 12, 12: 24, 24: 10, 10: 14, 14: 25,
        25: 11, 11: 15, 15: 9, 9: 13, 13: 8})
    g((460, 462), {2: 25, 25: 2})
    g((461, 466), {17: 8, 8: 17})
    g((467, 468), {13: 9, 9: 13})

    # Caller-scratch FP webs; saved F20..F28 and every memory offset stay fixed.
    f(range(62, 66), {0: 2, 2: 0})
    f(range(86, 217), {0: 2, 2: 0})
    for i in (98, 216):
        out[i] = subtract_destination(out[i], 0)
    f((219,), {6: 4, 4: 6})
    f((220,), {4: 18, 18: 0, 0: 4})
    out[220] = commute_multiply(out[220])
    f((222,), {6: 4, 4: 18, 18: 6, 8: 0, 0: 8})
    f((223,), {8: 0, 0: 8})
    out[223] = subtract_destination(out[223], 0)
    f(range(227, 257), {10: 0, 0: 10, 18: 6, 6: 18})
    f((261, 264), {6: 10, 10: 6})
    f((263, 269), {4: 8, 8: 4})
    f(range(307, 364), {8: 18, 18: 6, 6: 10, 10: 4, 4: 8})
    f(range(366, 378), {4: 8, 8: 4, 0: 2, 2: 0})
    f(range(386, 416), {6: 10, 10: 6})
    f((416,), {0: 2, 2: 0})
    out[416] = subtract_destination(out[416], 0)
    out[419] = subtract_destination(out[419], 4)
    f((420,), {10: 18, 18: 8, 8: 0, 0: 10})
    out[420] = commute_multiply(out[420])
    f((422,), {4: 0, 0: 10, 10: 18, 18: 4})
    f((423,), {4: 0, 0: 4})
    out[423] = subtract_destination(out[423], 0)
    f(range(427, 456), {6: 0, 0: 8, 8: 6})
    return out


def guard_rows(path):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    start = target['value']
    if target['size'] != 1944:
        raise ValueError('Expected complete unpadded 486-word reflection source')
    payload = text[start:start + 1944]
    if hashlib.sha256(payload).hexdigest() != RAW_SHA256:
        raise ValueError('Stale complete reflection object')
    relative = {at - start: uses for at, uses in relocations.items() if start <= at < start + 1944}
    if relative != RELOCATIONS:
        raise ValueError('Unexpected complete reflection relocation map')
    words = list(struct.unpack('>486I', payload))
    rows = []
    for i, (before, after) in enumerate(zip(words, normalize(words))):
        if before == after:
            continue
        if i * 4 in relative:
            raise ValueError('Reflection normalization must not alter a relocation')
        rows.append(dict(filename='generated_61D10', function=FUNCTION, offset='0x%X' % (i * 4),
            expected='0x%08X' % before, replacement='0x%08X' % after,
            expected_relocations='-', replacement_relocations='-',
            note='Normalize certified reflection register lifetimes and commutative operands',
            insert_after='', insert_after_relocations='', omit='false'))
    if len(rows) != 238:
        raise ValueError('Expected exactly 238 derived reflection words')
    return rows


def guard_bytes(before, obj):
    if not before.endswith(b'\n'):
        raise ValueError('Expected newline-terminated guard manifest')
    reader = csv.DictReader(io.StringIO(before.decode('ascii')))
    if any(row['function'] == FUNCTION for row in reader):
        raise ValueError('Reflection guards are already present')
    stream = io.StringIO(newline='')
    csv.DictWriter(stream, fieldnames=reader.fieldnames, lineterminator='\n').writerows(guard_rows(obj))
    return before + stream.getvalue().encode('ascii')

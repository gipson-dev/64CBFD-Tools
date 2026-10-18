"""Closed register-role and independent-prologue layout of all 83 C words."""
import csv
import hashlib
import io
import struct

from tools.experiments import game_route_vector_saved_roles as source
from tools.experiments import game_route_projection_layout_normalizer as projection

NORMALIZED_SHA = '02521a70c7569f4f8f3fc52db453699d6aba888811af5529a32cd687b4cebead'
GP_CYCLE = {6: 7, 7: 6, 8: 10, 9: 11, 10: 12, 11: 8, 12: 9}
SPECIAL = {7: {8: 10}, 8: {9: 11}, 9: {10: 12}, 29: {24: 15}, 32: {24: 15},
           39: {6: 24}, 42: {6: 24, 24: 25}, 43: {24: 25}, 45: {25: 14},
           46: {14: 15}, 48: {25: 14, 14: 15, 15: 24}, 49: {15: 24}}
# Field-specific FP roles distinguish the overwritten speed from its product.
FP_ROLES = {17: {11: 8}, 40: {16: 16}, 41: {11: 8}, 43: {11: 4},
            44: {11: 8, 6: 10}, 47: {11: 4, 6: 0}, 49: {11: 6}, 51: {11: 6},
            52: {16: 16, 11: 0, 6: 18}, 53: {16: 18, 11: 10, 6: 4},
            54: {16: 4}, 56: {11: 6}, 58: {11: 6, 6: 8}, 59: {16: 8},
            61: {16: 18}, 63: {11: 18, 6: 4}, 64: {6: 10},
            65: {16: 10, 11: 4, 6: 6}, 67: {16: 6}, 68: {11: 8},
            70: {11: 8, 6: 16}, 71: {16: 16}}
GP_COMMUTED = (16, 23, 25, 27, 32, 37)
FP_COMMUTED = (63, 65)


def origins():
    order = list(range(83))
    order[5:11] = [10, 5, 6, 7, 8, 9]
    if len(order) != 83 or set(order) != set(range(83)):
        raise ValueError('Lost or duplicated vector source origin')
    return order


def fields(word):
    if word >> 26 == 10:
        return (21, 16), ()
    if word >> 26 == 0 and word & 63 == 35:
        return (21, 16, 11), ()
    return projection.fields(word)


def normalize(raw, bindings):
    if len(raw) != 332 or hashlib.sha256(raw).hexdigest() != source.RAW_SHA or bindings != source.BINDINGS:
        raise ValueError('Unknown complete vector input or bindings')
    words = struct.unpack('>83I', raw)
    order = origins()
    destination = {old: new for new, old in enumerate(order)}
    result = []
    for new, old in enumerate(order):
        word = words[old]
        gp, fp = fields(word)
        rename = dict(GP_CYCLE) if 18 <= old <= 78 else {}
        rename.update(SPECIAL.get(old, {}))
        for shift in gp:
            register = words[old] >> shift & 31
            word = word & ~(31 << shift) | rename.get(register, register) << shift
        for shift, register in FP_ROLES.get(old, {}).items():
            if shift not in fp:
                raise ValueError('Vector FP role is not a register field')
            word = word & ~(31 << shift) | register << shift
        if old in GP_COMMUTED:
            if word >> 26 not in (0, 4, 20) or word >> 26 == 0 and word & 63 != 33:
                raise ValueError('Unknown commutative vector GP operation')
            rs, rt = word >> 21 & 31, word >> 16 & 31
            word = word & ~((31 << 21) | (31 << 16)) | rs << 16 | rt << 21
        if old in FP_COMMUTED:
            if word >> 26 != 17 or word >> 21 & 31 != 16 or word & 63 not in (0, 2):
                raise ValueError('Unknown commutative vector FP operation')
            ft, fs = word >> 16 & 31, word >> 11 & 31
            word = word & ~((31 << 16) | (31 << 11)) | ft << 11 | fs << 16
        result.append(word)
    moved = {destination[at // 4] * 4: value for at, value in bindings.items()}
    normalized = struct.pack('>83I', *result)
    if hashlib.sha256(normalized).hexdigest() != NORMALIZED_SHA:
        raise ValueError('Changed vector layout recipe')
    return normalized, moved


def relocate(raw, bindings, anchors):
    return projection.relocate(raw, bindings, anchors)


def private_guards(before, raw, bindings):
    normalized, moved = normalize(raw, bindings)
    reader = csv.DictReader(io.StringIO(before.decode()))
    if any(row['filename'] == source.model.OWNER and row['function'] == source.model.FUNCTION for row in reader):
        raise ValueError('Vector guards already exist')
    if not before.endswith(b'\n'):
        raise ValueError('Unterminated vector guard prefix')
    spec = lambda entries: ';'.join(kind + ':' + name for kind, name in entries) or '-'
    rows = [dict(filename=source.model.OWNER, function=source.model.FUNCTION, offset='0x%X' % (i * 4),
                 expected='0x%08X' % old, replacement='0x%08X' % new,
                 expected_relocations=spec(bindings.get(i * 4, [])),
                 replacement_relocations=spec(moved.get(i * 4, [])),
                 note='Recover vector register roles and schedule from C word %d' % origins()[i],
                 insert_after='', insert_after_relocations='', omit='false')
            for i, (old, new) in enumerate(zip(struct.unpack('>83I', raw), struct.unpack('>83I', normalized)))]
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames,
                            lineterminator='\r\n' if before.endswith(b'\r\n') else '\n')
    writer.writerows(rows)
    return before + output.getvalue().encode()
